import json
import logging
from typing import Union, Optional

import httpx
from httpx import URL

from .auth import LoginAuthenticator, FileAuthenticator
from .exceptions import (
    BadRequest, NotFoundError, NotResponding, NetworkError, ServerError,
    Unauthorized, UnexpectedError, RatelimitError, RequestError
)
from .localization import LOCALE_TEMPLATES, Locale

logger = logging.getLogger('audible.client')


def convert_response_content(resp):
    try:
        return resp.json()
    except json.JSONDecodeError:
        return resp.text


class Client:
    _API_URL_TEMP = "https://api.audible."
    _API_VERSION = "1.0"
    _SESSION = httpx.Client
    _REQUEST_LOG = '{method} {url} has received {text}, has returned {status}'

    def __init__(
            self,
            auth: Optional[
                Union[LoginAuthenticator, FileAuthenticator]] = None,
            country_code: Optional[str] = None,
            timeout: int = 10
    ):
        locale = Locale(country_code.lower()) if country_code else auth.locale
        api_url = self._API_URL_TEMP + locale.domain
        headers = {
            "Accept": "application/json",
            "Accept-Charset": "utf-8",
            "Content-Type": "application/json"
        }
        self.session = self._SESSION(
            headers=headers, timeout=timeout, base_url=api_url, auth=auth
        )

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.close()

    def __repr__(self):
        return f"<Sync Client for *{self.marketplace}* marketplace>"

    def close(self):
        self.session.close()

    def switch_marketplace(self, country_code):
        locale = Locale(country_code.lower())
        self.session.base_url = URL(self._API_URL_TEMP + locale.domain)

    @property
    def marketplace(self):
        base_url = str(self.session.base_url)
        slice_len = len(self._API_URL_TEMP)
        domain = base_url[slice_len:]

        for country in LOCALE_TEMPLATES.values():
            if domain == country["domain"]:
                return country["country_code"]

    @property
    def auth(self):
        return self.session.auth

    def switch_user(
            self,
            auth: Union[LoginAuthenticator, FileAuthenticator],
            switch_to_default_marketplace: bool = False
    ):
        if switch_to_default_marketplace:
            self.switch_marketplace(auth.locale.country_code)
        self.session.auth = auth

    def get_user_profile(self):
        self.auth.refresh_access_token()
        return self.auth.user_profile()

    @property
    def user_name(self):
        user_profile = self.get_user_profile()
        return user_profile["name"]

    def _raise_for_status_error(self, resp):
        code = resp.status_code

        data = convert_response_content(resp)

        if 300 > code >= 200:  # Request was successful
            return
        elif code == 400:
            raise BadRequest(resp, data)
        elif code in (401, 403):  # Unauthorized request - Invalid credentials
            raise Unauthorized(resp, data)
        elif code == 404:  # not found
            raise NotFoundError(resp, data)
        elif code == 429:
            raise RatelimitError(resp, data)
        elif code == 503:  # Maintainence
            raise ServerError(resp, data)
        else:
            raise UnexpectedError(resp, data)

    def _prepare_path(self, path):
        if path.startswith("/"):
            path = path[1:]

        if path.startswith(self._API_VERSION):
            return path

        return "/".join((self._API_VERSION, path))

    def _request(self, method: str, path: str, **kwargs):
        url = self._prepare_path(path)

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

            resp.raise_for_status()

            return convert_response_content(resp)

        except (
                httpx.ConnectTimeout, httpx.ReadTimeout, httpx.WriteTimeout,
                httpx.PoolTimeout
        ):
            raise NotResponding
        except httpx.NetworkError:
            raise NetworkError
        except httpx.RequestError as exc:
            raise RequestError(exc)
        except httpx.HTTPStatusError as exc:
            self._raise_for_status_error(exc.response)

        finally:
            try:
                resp.close()
            except UnboundLocalError:
                pass

    def _split_kwargs(self, **kwargs):
        protected_kwargs = [
            "method", "url", "params", "data", "json", "headers", "cookies",
            "files", "auth", "timeout", "allow_redirects", "proxies", "verify",
            "stream", "cert"
        ]
        params = kwargs.pop("params", {})
        for key in list(kwargs.keys()):
            if key not in protected_kwargs:
                params[key] = kwargs.pop(key)

        return params, kwargs

    def get(self, path, **kwargs):
        params, kwargs = self._split_kwargs(**kwargs)
        return self._request("GET", path, params=params, **kwargs)

    def post(self, path, body, **kwargs):
        params, kwargs = self._split_kwargs(**kwargs)
        return self._request("POST", path, params=params, json=body, **kwargs)

    def delete(self, path, **kwargs):
        params, kwargs = self._split_kwargs(**kwargs)
        return self._request("DELETE", path, params=params, **kwargs)

    def put(self, path, body, **kwargs):
        params, kwargs = self._split_kwargs(**kwargs)
        return self._request("PUT", path, params=params, json=body, **kwargs)


class AsyncClient(Client):
    _SESSION = httpx.AsyncClient

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_value, traceback):
        await self.close()

    def __repr__(self):
        return f"<AyncClient for *{self.marketplace}* marketplace>"

    async def close(self):
        await self.session.aclose()

    async def _request(self, method: str, path: str, **kwargs):
        url = self._prepare_path(path)

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

            resp.raise_for_status()

            return convert_response_content(resp)

        except (
                httpx.ConnectTimeout, httpx.ReadTimeout, httpx.WriteTimeout,
                httpx.PoolTimeout
        ):
            raise NotResponding
        except httpx.NetworkError:
            raise NetworkError
        except httpx.RequestError as exc:
            raise RequestError(exc)
        except httpx.HTTPStatusError as exc:
            self._raise_for_status_error(exc.response)

        finally:
            try:
                await resp.aclose()
            except UnboundLocalError:
                pass
