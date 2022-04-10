import inspect
import json
import logging
from typing import Any, Callable, Dict, Optional, Union

import httpx
from httpx import URL
from httpx._types import HeaderTypes

from .auth import Authenticator
from .exceptions import (
    BadRequest, NotFoundError, NotResponding, NetworkError, ServerError,
    Unauthorized, UnexpectedError, RatelimitError, RequestError
)
from .localization import LOCALE_TEMPLATES, Locale


logger = logging.getLogger("audible.client")

httpx_client_request_args = list(
    inspect.signature(httpx.Client.request).parameters.keys()
)


def default_response_callback(resp: httpx.Response) -> Union[Dict, str]:
    raise_for_status(resp)
    return convert_response_content(resp)


def raise_for_status(resp: httpx.Response) -> None:
    try:
        resp.raise_for_status()
    except httpx.HTTPStatusError as e:
        code = resp.status_code
        data = convert_response_content(resp)
        if code == 400:
            raise BadRequest(resp, data) from None
        elif code in (401, 403):  # Unauthorized request - Invalid credentials
            raise Unauthorized(resp, data) from None
        elif code == 404:  # not found
            raise NotFoundError(resp, data) from None
        elif code == 429:
            raise RatelimitError(resp, data) from None
        elif code == 503:  # Maintainence
            raise ServerError(resp, data) from None
        else:
            raise UnexpectedError(resp, data) from e


def convert_response_content(resp: httpx.Response) -> Union[Dict, str]:
    try:
        return resp.json()
    except json.JSONDecodeError:
        return resp.text


class Client:
    _API_URL_TEMP = "https://api.audible."
    _API_VERSION = "1.0"
    _SESSION = httpx.Client
    _REQUEST_LOG = "{method} {url} has received {text}, has returned {status}"

    def __init__(
            self,
            auth: Authenticator,
            country_code: Optional[str] = None,
            headers: Optional[HeaderTypes] = None,
            timeout: int = 10,
            response_callback: Optional[
                Callable[[httpx.Response], Any]] = None,
            **session_kwargs
    ):
        locale = Locale(country_code.lower()) if country_code else auth.locale
        self._api_url = httpx.URL(self._API_URL_TEMP + locale.domain)

        default_headers = {
            "Accept": "application/json",
            "Accept-Charset": "utf-8",
            "Content-Type": "application/json"
        }
        if headers is not None:
            default_headers.update(headers)

        self.session = self._SESSION(
            headers=default_headers,
            timeout=timeout,
            auth=auth,
            **session_kwargs
        )

        if response_callback is None:
            response_callback = default_response_callback
        self._response_callback = response_callback

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.close()

    def __repr__(self):
        return f"<Sync Client for *{self.marketplace}* marketplace>"

    def close(self) -> None:
        self.session.close()

    def switch_marketplace(self, country_code: str) -> None:
        locale = Locale(country_code.lower())
        self._api_url = URL(self._API_URL_TEMP + locale.domain)

    @property
    def marketplace(self) -> str:
        api_url = str(self._api_url)
        slice_len = len(self._API_URL_TEMP)
        domain = api_url[slice_len:]

        for country in LOCALE_TEMPLATES.values():
            if domain == country["domain"]:
                return country["country_code"]

    @property
    def auth(self) -> Authenticator:
        return self.session.auth

    def switch_user(
            self,
            auth: Authenticator,
            switch_to_default_marketplace: bool = False) -> None:
        if switch_to_default_marketplace:
            self.switch_marketplace(auth.locale.country_code)
        self.session.auth = auth

    def get_user_profile(self) -> Dict:
        self.auth.refresh_access_token()
        return self.auth.user_profile()

    @property
    def user_name(self) -> str:
        user_profile = self.get_user_profile()
        return user_profile["name"]

    def _prepare_api_path(self, path: str) -> httpx.URL:
        if path.startswith("/"):
            path = path[1:]

        if path.startswith(self._API_VERSION) or path.startswith("0.0"):
            pass
        else:
            path = "/".join((self._API_VERSION, path))

        path = "/" + path
        return self._api_url.copy_with(path=path)

    def _request(
            self,
            method: str,
            path: str,
            response_callback: Optional[
                Callable[[httpx.Response], Any]] = None,
            **kwargs
    ) -> Any:
        url = self._prepare_api_path(path)

        if response_callback is None:
            response_callback = self._response_callback

        try:
            resp = self.session.request(method, url, **kwargs)

            logger.debug(
                self._REQUEST_LOG.format(
                    method=method,
                    url=resp.url,
                    text=resp.text,
                    status=resp.status_code
                )
            )

            return response_callback(resp)

        except (
            httpx.ConnectTimeout, httpx.ReadTimeout, httpx.WriteTimeout,
            httpx.PoolTimeout
        ):
            raise NotResponding
        except httpx.NetworkError:
            raise NetworkError
        except httpx.RequestError as exc:
            raise RequestError(exc)
        finally:
            try:
                resp.close()
            except UnboundLocalError:
                pass

    def raw_request(
            self,
            method: str,
            url: str,
            *,
            stream: bool = False,
            apply_auth_flow: bool = False,
            apply_cookies: bool = False,
            **kwargs) -> httpx.Response:
        """Sends a raw request with the underlying httpx Client.

        This method ignores a set api_url and allows send request to custom 
        hosts. The raw httpx response will be returned.

        Args:
            method: The http request method.
            url: The url to make requests to.
            stream: If `True`, streams the response
            apply_auth_flow: If `True`, the :meth:`Authenticator.auth_flow`
                will be applied to the request.
            apply_cookies: If `True`, website cookies from
                :attr:`Authenticator.website_cookies` will be added to
                request headers.

        Returns:
            A unprepared httpx Response object.
                
        .. versionadded:: v0.5.1
        
        """

        cookies = self.auth.website_cookies if apply_cookies else {}
        cookies = httpx.Cookies(cookies)
        cookies.update(kwargs.pop("cookies", {}))
        auth = self.session.auth if apply_auth_flow else None

        r = self.session.stream if stream else self.session.request
        return r(method, url, cookies=cookies, auth=auth, **kwargs)

    @staticmethod
    def _prepare_params(kwargs: Dict) -> None:
        params = kwargs.pop("params", {})
        for key in list(kwargs.keys()):
            if key not in httpx_client_request_args:
                params[key] = kwargs.pop(key)
        kwargs["params"] = params

    def get(
            self,
            path: str,
            response_callback: Optional[
                Callable[[httpx.Response], Any]] = None,
            **kwargs
    ) -> Any:
        self._prepare_params(kwargs)
        return self._request(
            method="GET",
            path=path,
            response_callback=response_callback,
            **kwargs
        )

    def post(
            self,
            path: str,
            body: Dict,
            response_callback: Optional[
                Callable[[httpx.Response], Any]] = None,
            **kwargs
    ) -> Any:
        self._prepare_params(kwargs)
        return self._request(
            method="POST",
            path=path,
            response_callback=response_callback,
            json=body,
            **kwargs
        )

    def delete(
            self,
            path: str,
            response_callback: Optional[
                Callable[[httpx.Response], Any]] = None,
            **kwargs
    ) -> Any:
        self._prepare_params(**kwargs)
        return self._request(
            method="DELETE",
            path=path,
            response_callback=response_callback,
            **kwargs
        )

    def put(
            self,
            path: str,
            body: Dict,
            response_callback: Optional[
                Callable[[httpx.Response], Any]] = None,
            **kwargs
    ) -> Any:
        self._prepare_params(kwargs)
        return self._request(
            method="PUT",
            path=path,
            response_callback=response_callback,
            json=body,
            **kwargs
        )


class AsyncClient(Client):
    _SESSION = httpx.AsyncClient

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_value, traceback):
        await self.close()

    def __repr__(self):
        return f"<AyncClient for *{self.marketplace}* marketplace>"

    async def close(self) -> None:
        await self.session.aclose()

    async def _request(
            self,
            method: str,
            path: str,
            response_callback: Optional[
                Callable[[httpx.Response], Any]] = None,
            **kwargs) -> Union[Dict, str]:
        url = self._prepare_api_path(path)

        if response_callback is None:
            response_callback = self._response_callback

        try:
            resp = await self.session.request(method, url, **kwargs)

            logger.debug(
                self._REQUEST_LOG.format(
                    method=method,
                    url=resp.url,
                    text=resp.text,
                    status=resp.status_code
                )
            )

            return response_callback(resp)

        except (
            httpx.ConnectTimeout, httpx.ReadTimeout, httpx.WriteTimeout,
            httpx.PoolTimeout
        ):
            raise NotResponding
        except httpx.NetworkError:
            raise NetworkError
        except httpx.RequestError as exc:
            raise RequestError(exc)
        finally:
            try:
                await resp.aclose()
            except UnboundLocalError:
                pass
