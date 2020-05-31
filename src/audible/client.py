import asyncio
import json
import logging
from typing import Union, Optional
from urllib.parse import urlencode, urlparse


import aiohttp
import requests
import yarl

from .auth import sign_request, LoginAuthenticator, FileAuthenticator
from .errors import (BadRequest, NotFoundError, NotResponding, NetworkError,
                     ServerError, Unauthorized, UnexpectedError,
                     RatelimitError)
from .utils import test_convert
from .localization import LOCALE_TEMPLATES


logger = logging.getLogger('audible.client')


class AudibleAPI:

    REQUEST_LOG = '{method} {url} has received {text}, has returned {status}'

    def __init__(self, auth: Optional[Union[LoginAuthenticator, FileAuthenticator]] = None,
                 session=None, is_async=False, **options) -> None:
        self.auth = auth
        self.adp_token = options.get("adp_token", auth.adp_token)
        self.device_private_key = options.get(
            "device_private_key", auth.device_private_key
        )

        self.is_async = is_async
        self.session = (session or (aiohttp.ClientSession() if is_async
                        else requests.Session()))
        self.headers = {
            "Accept": "application/json",
            "Content-Type": "application/json"
        }

        locale = test_convert("locale", options.get("locale", auth.locale))
        domain = options.get("domain", locale.domain)
        self.api_root_url = options.get("url", f"https://api.audible.{domain}")

        self.timeout = options.get('timeout', 10)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.close()

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_value, traceback):
        await self.session.close()

    def __repr__(self):
        return f"<AudibleAPI Client async={self.is_async}>"

    def close(self):
        return self.session.close()

    def switch_marketplace(self, locale):
        locale = test_convert("locale", locale)
        domain = locale.domain
        self.api_root_url = f"https://api.audible.{domain}"

    @property
    def marketplace(self):
        for value in LOCALE_TEMPLATES.values():
            domain = value["domain"]
            api_root_for_domain = f"https://api.audible.{domain}"

            if api_root_for_domain == self.api_root_url:
                return value["countryCode"]

    def switch_user(self, auth: Union[LoginAuthenticator, FileAuthenticator]):
        self.auth = auth
        self.adp_token = auth.get("adp_token")
        self.device_private_key = auth.get("device_private_key")

    def get_user_profile(self):
        self.auth.refresh_access_token()
        return self.auth.user_profile()

    @property
    def user_name(self):
        user_profile = self.get_user_profile()
        return user_profile['name']

    def _raise_for_status(self, resp, text, *, method=None):
        try:
            data = json.loads(text)
        except json.JSONDecodeError:
            data = text
        code = getattr(resp, 'status', None) or getattr(resp, 'status_code')

        logger.debug(self.REQUEST_LOG.format(
            method=method or resp.request_info.method, url=resp.url,
            text=text, status=code
        ))

        if 300 > code >= 200:  # Request was successful
            return data, resp  # value, response
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

    def _sign_request(self, method, url, params, json_data):
        path = urlparse(url).path
        query = urlencode(params)
        json_body = json.dumps(json_data) if json_data else None
    
        if query:
            path += f"?{query}"

        return sign_request(path, method, json_body, self.adp_token,
                            self.device_private_key)

    async def _arequest(self, method, url, **kwargs):
        params = kwargs.pop("params", {})
        json_data = kwargs.get('json', {})
        timeout = kwargs.pop('timeout', self.timeout)

        headers = kwargs.pop("headers", {})
        signed_headers = self._sign_request(
            method, url, params, json_data
        )
        headers.update(self.headers)
        headers.update(signed_headers)

        url += "?" + urlencode(params)
        url = yarl.URL(url, encoded=True)

        try:
            async with self.session.request(
                method, url, timeout=timeout, headers=headers, **kwargs
            ) as resp:
                return self._raise_for_status(resp, await resp.text())
        except asyncio.TimeoutError:
            raise NotResponding
        except aiohttp.ServerDisconnectedError:
            raise NetworkError

    def _request(self, method, url, **kwargs):
        if self.is_async:  # return a coroutine
            return self._arequest(method, url, **kwargs)
        params = kwargs.get("params", {})
        json_data = kwargs.get('json', {})
        timeout = kwargs.pop('timeout', self.timeout)

        headers = kwargs.pop("headers", {})
        signed_headers = self._sign_request(method, url, params, json_data)
        headers.update(self.headers)
        headers.update(signed_headers)

        try:
            with self.session.request(
                method, url, timeout=timeout, headers=headers, **kwargs
            ) as resp:
                if resp.encoding == None:
                    resp.encoding = "utf-8"
                return self._raise_for_status(resp, resp.text, method=method)
        except requests.Timeout:
            raise NotResponding
        except requests.ConnectionError:
            raise NetworkError

    def _split_kwargs(self, **kwargs):
        requests_kwargs = [
            "method", "url", "params", "data", "json", "headers", "cookies",
            "files", "auth", "timeout", "allow_redirects", "proxies", "verify",
            "stream", "cert"
        ]
        params = kwargs.pop("params", {})
        for key in list(kwargs.keys()):
            if key not in requests_kwargs:
                params[key] = kwargs.pop(key)

        return params, kwargs

    def get(self, path, api_version="1.0", **kwargs):
        params, kwargs = self._split_kwargs(**kwargs)
        url = "/".join((self.api_root_url, api_version, path))
        return self._request("GET", url, params=params, **kwargs)

    def post(self, path, body, api_version="1.0", **kwargs):
        params, kwargs = self._split_kwargs(**kwargs)
        url = "/".join((self.api_root_url, api_version, path))
        return self._request("POST", url, params=params, json=body, **kwargs)

    def delete(self, path, api_version="1.0", **kwargs):
        params, kwargs = self._split_kwargs(**kwargs)
        url = "/".join((self.api_root_url, api_version, path))
        return self._request("DELETE", url, params=params, **kwargs)
