import inspect
import json
import logging
from abc import ABCMeta, abstractmethod
from collections.abc import Callable, Coroutine
from contextlib import AbstractAsyncContextManager, AbstractContextManager
from types import TracebackType
from typing import (
    Any,
    Generic,
    Literal,
    TypeVar,
    overload,
)

import httpx
from httpx import URL
from httpx._models import HeaderTypes  # type: ignore[attr-defined]

from ._types import TrueFalseT
from .auth import Authenticator
from .exceptions import (
    BadRequest,
    NetworkError,
    NotFoundError,
    NotResponding,
    RatelimitError,
    RequestError,
    ServerError,
    Unauthorized,
    UnexpectedError,
)
from .json import get_json_provider
from .localization import LOCALE_TEMPLATES, Locale


logger = logging.getLogger("audible.client")

ClientT = TypeVar("ClientT", httpx.AsyncClient, httpx.Client)

httpx_client_request_args = list(
    inspect.signature(httpx.Client.request).parameters.keys()
)


def default_response_callback(resp: httpx.Response) -> Any:
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


def convert_response_content(resp: httpx.Response) -> Any:
    try:
        return get_json_provider().loads(resp.text)
    except (json.JSONDecodeError, ValueError) as e:
        # Catches JSONDecodeError (stdlib, orjson) and ValueError (ujson, rapidjson)
        # Falls back to returning raw text if JSON parsing fails
        logger.debug("JSON parsing failed: %s", e, exc_info=True)
        return resp.text


class BaseClient(Generic[ClientT], metaclass=ABCMeta):
    _API_URL_TEMP = "https://api.audible."
    _API_VERSION = "1.0"
    _REQUEST_LOG = "{method} {url} has received {text}, has returned {status}"

    def __init__(
        self,
        auth: Authenticator,
        country_code: str | None = None,
        headers: HeaderTypes | None = None,
        timeout: int = 10,
        response_callback: Callable[[httpx.Response], Any] | None = None,
        **session_kwargs: Any,
    ):
        locale = Locale(country_code.lower()) if country_code else auth.locale
        if not isinstance(locale, Locale):
            raise Exception("Authenticator has no `Locale` class set.")
        self._api_url = httpx.URL(self._API_URL_TEMP + locale.domain)

        default_headers = httpx.Headers(
            {
                "Accept": "application/json",
                "Accept-Charset": "utf-8",
                "Content-Type": "application/json",
            }
        )
        if headers is not None:
            default_headers.update(headers)

        self.session: ClientT = self._get_session(
            headers=default_headers, timeout=timeout, auth=auth, **session_kwargs
        )

        if response_callback is None:
            response_callback = default_response_callback
        self._response_callback = response_callback

    @abstractmethod
    def _get_session(self, *args: Any, **kwargs: Any) -> ClientT: ...

    @abstractmethod
    def _request(
        self,
        method: str,
        path: str,
        response_callback: Callable[[httpx.Response], Any] | None = None,
        **kwargs: Any,
    ) -> Any: ...

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

        return "unknown"

    @property
    def auth(self) -> Authenticator:
        if not isinstance(self.session.auth, Authenticator):
            auth_type = type(self.session.auth)
            raise Exception(
                f"`session.auth` has type {auth_type}, expected `Authenticator`."
            )
        return self.session.auth

    def switch_user(
        self, auth: Authenticator, switch_to_default_marketplace: bool = False
    ) -> None:
        if switch_to_default_marketplace:
            if not isinstance(auth.locale, Locale):
                raise Exception("Authenticator has no `Locale` class set.")
            self.switch_marketplace(auth.locale.country_code)
        self.session.auth = auth

    def get_user_profile(self) -> dict[str, Any]:
        self.auth.refresh_access_token()
        return self.auth.user_profile()

    @property
    def user_name(self) -> str:
        user_profile = self.get_user_profile()
        if "name" not in user_profile:
            raise Exception("user profile has no key `name`.")

        user_name = user_profile["name"]
        if not isinstance(user_name, str):
            user_name_type = type(user_name)
            raise Exception(f"username has type {user_name_type}, expected `str`.")
        return user_name

    def _prepare_api_path(self, path: str) -> httpx.URL:
        if httpx.URL(path).is_absolute_url:
            return httpx.URL(path)

        if path.startswith("/"):
            path = path[1:]

        if not (path.startswith(self._API_VERSION) or path.startswith("0.0")):
            path = "/".join((self._API_VERSION, path))

        path = "/" + path
        path_bytes = path.encode()
        return self._api_url.copy_with(raw_path=path_bytes)

    @overload
    def raw_request(
        self: "BaseClient[httpx.Client]",
        method: str,
        url: str,
        *,
        stream: Literal[False] = ...,
        apply_auth_flow: bool = ...,
        apply_cookies: bool = ...,
        **kwargs: Any,
    ) -> httpx.Response: ...

    @overload
    def raw_request(
        self: "BaseClient[httpx.Client]",
        method: str,
        url: str,
        *,
        stream: Literal[True],
        apply_auth_flow: bool = ...,
        apply_cookies: bool = ...,
        **kwargs: Any,
    ) -> AbstractContextManager[httpx.Response]: ...

    @overload
    def raw_request(
        self: "BaseClient[httpx.AsyncClient]",
        method: str,
        url: str,
        *,
        stream: Literal[False] = ...,
        apply_auth_flow: bool = ...,
        apply_cookies: bool = ...,
        **kwargs: Any,
    ) -> Coroutine[Any, Any, httpx.Response]: ...

    @overload
    def raw_request(
        self: "BaseClient[httpx.AsyncClient]",
        method: str,
        url: str,
        *,
        stream: Literal[True],
        apply_auth_flow: bool = ...,
        apply_cookies: bool = ...,
        **kwargs: Any,
    ) -> AbstractAsyncContextManager[httpx.Response]: ...

    def raw_request(
        self,
        method: str,
        url: str,
        *,
        stream: TrueFalseT = False,
        apply_auth_flow: bool = False,
        apply_cookies: bool = False,
        **kwargs: Any,
    ) -> httpx.Response | (
        Coroutine[Any, Any, httpx.Response]
        | (
            AbstractContextManager[httpx.Response]
            | AbstractAsyncContextManager[httpx.Response]
        )
    ):
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
            **kwargs: keyword args supported by :class:`httpx.AsyncClient.stream`,
                :class:`httpx.Client.stream`, :class:`httpx.AsyncClient.request`,
                :class:`httpx.Client.request`.

        Returns:
            An unprepared httpx Response object.

        .. versionadded:: v0.5.1
        """
        request_params = {"method": method, "url": url, **kwargs}

        if apply_cookies:
            cookies = httpx.Cookies(self.auth.website_cookies)
            cookies.update(kwargs.pop("cookies", {}))
            request_params["cookies"] = cookies

        if apply_auth_flow:
            request_params["auth"] = self.auth

        if stream:
            return self.session.stream(**request_params)
        return self.session.request(**request_params)

    @staticmethod
    def _prepare_params(kwargs: dict[str, Any]) -> None:
        params = kwargs.pop("params", {})
        for key in list(kwargs.keys()):
            if key not in httpx_client_request_args:
                params[key] = kwargs.pop(key)
        kwargs["params"] = params

    @abstractmethod
    def get(
        self,
        path: str,
        response_callback: Callable[[httpx.Response], Any] | None = None,
        **kwargs: dict[str, Any],
    ) -> Any: ...

    @abstractmethod
    def post(
        self,
        path: str,
        body: Any,
        response_callback: Callable[[httpx.Response], Any] | None = None,
        **kwargs: dict[str, Any],
    ) -> Any: ...

    @abstractmethod
    def delete(
        self,
        path: str,
        response_callback: Callable[[httpx.Response], Any] | None = None,
        **kwargs: dict[str, Any],
    ) -> Any: ...

    @abstractmethod
    def put(
        self,
        path: str,
        body: Any,
        response_callback: Callable[[httpx.Response], Any] | None = None,
        **kwargs: dict[str, Any],
    ) -> Any: ...


class Client(BaseClient[httpx.Client]):
    def _get_session(self, *args: Any, **kwargs: Any) -> httpx.Client:
        return httpx.Client(*args, **kwargs)

    def __enter__(self) -> "Client":
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None = None,
        exc_value: BaseException | None = None,
        traceback: TracebackType | None = None,
    ) -> None:
        self.close()

    def __repr__(self) -> str:
        return f"<Sync Client for *{self.marketplace}* marketplace>"

    def close(self) -> None:
        self.session.close()

    def _request(
        self,
        method: str,
        path: str,
        response_callback: Callable[[httpx.Response], Any] | None = None,
        **kwargs: Any,
    ) -> Any:
        url = self._prepare_api_path(path)

        if response_callback is None:
            response_callback = self._response_callback

        try:
            resp = self.session.request(method, url, **kwargs)

            logger.debug(
                self._REQUEST_LOG.format(
                    method=method, url=resp.url, text=resp.text, status=resp.status_code
                )
            )

            return response_callback(resp)

        except (
            httpx.ConnectTimeout,
            httpx.ReadTimeout,
            httpx.WriteTimeout,
            httpx.PoolTimeout,
        ):
            raise NotResponding from None
        except httpx.NetworkError:
            raise NetworkError from None
        except httpx.RequestError as exc:
            raise RequestError(exc) from None
        finally:
            try:
                resp.close()
            except UnboundLocalError:
                pass

    def get(
        self,
        path: str,
        response_callback: Callable[[httpx.Response], Any] | None = None,
        **kwargs: dict[str, Any],
    ) -> Any:
        self._prepare_params(kwargs)
        return self._request(
            method="GET", path=path, response_callback=response_callback, **kwargs
        )

    def post(
        self,
        path: str,
        body: Any,
        response_callback: Callable[[httpx.Response], Any] | None = None,
        **kwargs: dict[str, Any],
    ) -> Any:
        self._prepare_params(kwargs)
        return self._request(
            method="POST",
            path=path,
            response_callback=response_callback,
            json=body,
            **kwargs,
        )

    def delete(
        self,
        path: str,
        response_callback: Callable[[httpx.Response], Any] | None = None,
        **kwargs: dict[str, Any],
    ) -> Any:
        self._prepare_params(kwargs)
        return self._request(
            method="DELETE", path=path, response_callback=response_callback, **kwargs
        )

    def put(
        self,
        path: str,
        body: Any,
        response_callback: Callable[[httpx.Response], Any] | None = None,
        **kwargs: dict[str, Any],
    ) -> Any:
        self._prepare_params(kwargs)
        return self._request(
            method="PUT",
            path=path,
            response_callback=response_callback,
            json=body,
            **kwargs,
        )


class AsyncClient(BaseClient[httpx.AsyncClient]):
    def _get_session(self, *args: Any, **kwargs: Any) -> httpx.AsyncClient:
        return httpx.AsyncClient(*args, **kwargs)

    async def __aenter__(self) -> "AsyncClient":
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None = None,
        exc_value: BaseException | None = None,
        traceback: TracebackType | None = None,
    ) -> None:
        await self.close()

    def __repr__(self) -> str:
        return f"<AyncClient for *{self.marketplace}* marketplace>"

    async def close(self) -> None:
        await self.session.aclose()

    async def _request(
        self,
        method: str,
        path: str,
        response_callback: Callable[[httpx.Response], Any] | None = None,
        **kwargs: Any,
    ) -> Any:
        url = self._prepare_api_path(path)

        if response_callback is None:
            response_callback = self._response_callback

        try:
            resp = await self.session.request(method, url, **kwargs)

            logger.debug(
                self._REQUEST_LOG.format(
                    method=method, url=resp.url, text=resp.text, status=resp.status_code
                )
            )

            return response_callback(resp)

        except (
            httpx.ConnectTimeout,
            httpx.ReadTimeout,
            httpx.WriteTimeout,
            httpx.PoolTimeout,
        ):
            raise NotResponding from None
        except httpx.NetworkError:
            raise NetworkError from None
        except httpx.RequestError as exc:
            raise RequestError(exc) from None
        finally:
            try:
                await resp.aclose()
            except UnboundLocalError:
                pass

    async def get(
        self,
        path: str,
        response_callback: Callable[[httpx.Response], Any] | None = None,
        **kwargs: dict[str, Any],
    ) -> Any:
        self._prepare_params(kwargs)
        return await self._request(
            method="GET", path=path, response_callback=response_callback, **kwargs
        )

    async def post(
        self,
        path: str,
        body: Any,
        response_callback: Callable[[httpx.Response], Any] | None = None,
        **kwargs: dict[str, Any],
    ) -> Any:
        self._prepare_params(kwargs)
        return await self._request(
            method="POST",
            path=path,
            response_callback=response_callback,
            json=body,
            **kwargs,
        )

    async def delete(
        self,
        path: str,
        response_callback: Callable[[httpx.Response], Any] | None = None,
        **kwargs: dict[str, Any],
    ) -> Any:
        self._prepare_params(kwargs)
        return await self._request(
            method="DELETE", path=path, response_callback=response_callback, **kwargs
        )

    async def put(
        self,
        path: str,
        body: Any,
        response_callback: Callable[[httpx.Response], Any] | None = None,
        **kwargs: dict[str, Any],
    ) -> Any:
        self._prepare_params(kwargs)
        return await self._request(
            method="PUT",
            path=path,
            response_callback=response_callback,
            json=body,
            **kwargs,
        )
