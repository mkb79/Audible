import asyncio
import json
import logging
from typing import Union, Optional
from urllib.parse import urlencode, urlparse
import warnings
import yarl

import aiohttp
import requests

from .auth import sign_request, LoginAuthenticator, FileAuthenticator, CertAuth
from .errors import (BadRequest, NotFoundError, NotResponding, NetworkError,
                     ServerError, Unauthorized, UnexpectedError,
                     RatelimitError)


_client_logger = logging.getLogger('audible.client')


class AudibleAPI:

    REQUEST_LOG = '{method} {url} has received {text}, has returned {status}'

    def __init__(self, auth: Optional[Union[LoginAuthenticator, FileAuthenticator]] = None,
                 session=None, is_async=False, **options) -> None:
        self.auth = auth
        self.adp_token = options.get("adp_token", auth.adp_token)
        self.device_private_key = options.get("device_private_key",
                                              auth.device_private_key)

        self.is_async = is_async
        self.session = (session or (aiohttp.ClientSession() if is_async
                        else requests.Session()))
        self.headers = {
            "Accept": "application/json",
            "Content-Type": "application/json"
        }

        self.api_root_url = options.get("url", auth.locale.audible_api)

        self.timeout = options.get('timeout', 10)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.close()

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_value, traceback):
        self.close()

    def __repr__(self):
        return f"<AudibleAPI Client async={self.is_async}>"

    def close(self):
        return self.session.close()

    def _raise_for_status(self, resp, text, *, method=None):
        try:
            data = json.loads(text)
        except json.JSONDecodeError:
            data = text
        code = getattr(resp, 'status', None) or getattr(resp, 'status_code')

        _client_logger.debug(self.REQUEST_LOG.format(
            method=method or resp.request_info.method, url=resp.url,
            text=text, status=code
        ))

        if 300 > code >= 200:  # Request was successful
            return data, resp  # value, response
        if code == 400:
            raise BadRequest(resp, data)
        if code in (401, 403):  # Unauthorized request - Invalid credentials
            raise Unauthorized(resp, data)
        if code == 404:  # not found
            raise NotFoundError(resp, data)
        if code == 429:
            raise RatelimitError(resp, data)
        if code == 503:  # Maintainence
            raise ServerError(resp, data)

        raise UnexpectedError(resp, data)

    def _sign_request(self, method, url, params, json_data):
        path = urlparse(url).path
        query = urlencode(params)
        json_body = json.dumps(json_data)
    
        if query:
            path += f"?{query}"
    
        return sign_request(path, method, json_body, self.adp_token,
                            self.device_private_key)

    async def _arequest(self, url, **params):
        method = params.pop('method', 'GET')
        json_data = params.pop('json', {})
        timeout = params.pop('timeout', None) or self.timeout

        signed_headers = self._sign_request(
            method, url, params, json_data
        )
        headers = self.headers.copy()
        for item in signed_headers:
            headers[item] = signed_headers[item]

        url += "?" + urlencode(params)
        url = yarl.URL(url, encoded=True)

        try:
            async with self.session.request(
                method, url, timeout=timeout, headers=headers, json=json_data
            ) as resp:
                return self._raise_for_status(resp, await resp.text())
        except asyncio.TimeoutError:
            raise NotResponding
        except aiohttp.ServerDisconnectedError:
            raise NetworkError

    def _request(self, url, **params):
        if self.is_async:  # return a coroutine
            return self._arequest(url, **params)

        method = params.pop('method', 'GET')
        json_data = params.pop('json', {})
        timeout = params.pop('timeout', None) or self.timeout

        signed_headers = self._sign_request(method, url, params, json_data)
        headers = self.headers.copy()
        for item in signed_headers:
            headers[item] = signed_headers[item]

        try:
            with self.session.request(
                method, url, timeout=timeout, headers=headers,
                params=params, json=json_data
            ) as resp:
                return self._raise_for_status(resp, resp.text, method=method)
        except requests.Timeout:
            raise NotResponding
        except requests.ConnectionError:
            raise NetworkError

    def get(self, path, **params):
        api_version = params.pop("api_version", "1.0")
        url = "/".join((self.api_root_url, api_version, path))
        return self._request(url, **params)

    def post(self, path, body, **params):
        api_version = params.pop("api_version", "1.0")
        url = "/".join((self.api_root_url, api_version, path))
        return self._request(url, method="POST", json=body, **params)

    def delete(self, path, **params):
        api_version = params.pop("api_version", "1.0")
        url = "/".join((self.api_root_url, api_version, path))
        return self._request(url, method="POST", **params)


class DeprecatedClient:
    """
    This client makes sure compatibility to audible package < v0.2.0
    """

    def __init__(self, username=None, password=None, filename=None, local="us",
                 captcha_callback=None, otp_callback=None):

        warnings.warn(
            "this Client is deprecated since v0.2.0, use AudibleAPI class instead",
            DeprecationWarning
        )

        if isinstance(local, dict):
            local = audible.Locale(**local)

        if username and password:
            self.auth = LoginAuthenticator(username, password, locale=local,
                                           captcha_callback=captcha_callback,
                                           otp_callback=otp_callback)
            if filename:
                self.auth._data.update(filename=filename, encryption=False)
                self.auth.to_file()

        elif filename:
            self.auth = FileAuthenticator(filename, locale=local)

        self.session = requests.Session()
        self.headers = {
            "Accept": "application/json",
            "Content-Type": "application/json"
        }

        self.api_root_url = self.auth.locale.audible_api

        self.timeout = 10

    @property
    def login_cookies(self):
        return self.auth.login_cookies
 
    @property
    def adp_token(self):
        return self.auth.adp_token
 
    @property
    def access_token(self):
        return self.auth.access_token
 
    @property
    def refresh_token(self):
        return self.auth.refresh_token
 
    @property
    def device_private_key(self):
        return self.auth.device_private_key
 
    @property
    def expires(self):
        return datetime.fromtimestamp(self.auth.expires) - datetime.utcnow()
 
    def expired(self):
        if datetime.fromtimestamp(self.auth.expires) <= datetime.utcnow():
            return True
        else:
            return False

    def from_json_file(self, filename=None):
        filename = filename or self.auth.filename

        self.auth = FileAuthenticator(filename, locale=self.auth.locale,
                                      set_default=False)

    def to_json_file(self, filename=None, indent=4):
        filename = filename or self.auth.filename
        self.auth.to_file(filename, encryption=False, indent=indent,
                          set_default=False)

    def auth_register(self):
        self.auth.register_device()

    def auth_deregister(self):
        self.auth.deregister_device()

    def refresh_access_token(self, force=False):
        self.auth.refresh_access_token(force=force)

    def user_profile(self):
        return self.auth.user_profile()

    def refresh_or_register(self, force=False):
        self.auth.refresh_or_register(force=force)

    def _api_request(self, method, path, api_version="1.0", json_data=None,
                     auth=None, cookies=None, **params):
        url = "/".join((self.api_root_url, api_version, path))

        auth = CertAuth(self.adp_token, self.device_private_key)

        resp = requests.request(
            method, url, json=json_data, params=params, headers=self.headers,
            auth=auth, cookies=cookies
        )
        resp.raise_for_status()
 
        return resp.json()
 
    def get(self, path, **params):
        return self._api_request("GET", path, **params)
 
    def post(self, path, body, **params):
        return self._api_request("POST", path, json_data=body, **params)
 
    def delete(self, path, **params):
        return self._api_request("DELETE", path, **params)
