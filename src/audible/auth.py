import base64
import json
import logging
from collections.abc import MutableMapping
from datetime import datetime, timedelta
from typing import Any, Dict, List, Union

import httpx
import rsa
from httpx import Cookies

from .activation_bytes import get_activation_bytes as get_ab
from .aescipher import AESCipher, detect_file_encryption
from .exceptions import FileEncryptionError, AuthFlowError, NoRefreshToken
from .login import login
from .register import deregister as deregister_
from .register import register as register_
from .utils import test_convert

logger = logging.getLogger('audible.auth')


def refresh_access_token(refresh_token: str, domain: str) -> Dict[str, Any]:
    """
    Refresh access token with refresh token.
    Access tokens are valid for 60 mins.
    
    """

    body = {
        "app_name": "Audible",
        "app_version": "3.26.1",
        "source_token": refresh_token,
        "requested_token_type": "access_token",
        "source_token_type": "refresh_token"
    }

    resp = httpx.post(f"https://api.amazon.{domain}/auth/token", data=body)
    resp.raise_for_status()
    resp_dict = resp.json()

    expires_in_sec = int(resp_dict["expires_in"])
    expires = (datetime.utcnow() + timedelta(seconds=expires_in_sec
                                             )).timestamp()

    return {"access_token": resp_dict["access_token"], "expires": expires}


def refresh_website_cookies(
        refresh_token: str, domain: str, cookies_domain: str
) -> Dict[str, str]:
    url = f"https://www.amazon.{domain}/ap/exchangetoken"

    body = {
        "app_name": "Audible",
        "app_version": "3.26.1",
        "source_token": refresh_token,
        "requested_token_type": "auth_cookies",
        "source_token_type": "refresh_token",
        "domain": f".amazon.{cookies_domain}"
    }

    resp = httpx.post(url, data=body)
    resp.raise_for_status()
    resp_dict = resp.json()

    raw_cookies = resp_dict["response"]["tokens"]["cookies"]
    website_cookies = dict()
    for cookies_domain in raw_cookies:
        for cookie in raw_cookies[cookies_domain]:
            website_cookies[cookie["Name"]] = cookie["Value"].replace(r'"',
                                                                      r'')

    return website_cookies


def user_profile(access_token: str, domain: str) -> Dict[str, Any]:
    """Returns user profile from amazon."""

    headers = {"Authorization": f"Bearer {access_token}"}

    resp = httpx.get(
        f"https://api.amazon.{domain}/user/profile", headers=headers
    )
    resp.raise_for_status()

    return resp.json()


def user_profile_audible(access_token: str, domain: str) -> Dict[str, Any]:
    """Returns user profile from audible."""

    headers = {"Authorization": f"Bearer {access_token}"}

    resp = httpx.get(
        f"https://api.audible.{domain}/user/profile", headers=headers
    )
    resp.raise_for_status()

    return resp.json()


def sign_request(
        method: str, path: str, body: bytes, adp_token: str, private_key: str
) -> Dict[str, str]:
    """
    Helper function who creates a signed header for requests.

    :param path: the requested url path and query
    :param method: the request method (GET, POST, DELETE, ...)
    :param body: the http message body
    :param adp_token: the token is obtained after register as device
    :param private_key: the rsa key obtained after register as device
    """
    date = datetime.utcnow().isoformat("T") + "Z"
    body = body.decode("utf-8")

    data = f"{method}\n{path}\n{date}\n{body}\n{adp_token}"

    key = rsa.PrivateKey.load_pkcs1(private_key)
    cipher = rsa.pkcs1.sign(data.encode(), key, "SHA-256")
    signed_encoded = base64.b64encode(cipher)

    signature = f"{signed_encoded.decode()}:{date}"

    return {
        "x-adp-token": adp_token,
        "x-adp-alg": "SHA256withRSA:1.0",
        "x-adp-signature": signature
    }


class Authenticator(MutableMapping, httpx.Auth):
    """Base Class for retrieve and handle credentials."""

    requires_request_body = True

    def __getitem__(self, key):
        return self.__dict__[key]

    def __getattr__(self, attr):
        try:
            return self.__getitem__(attr)
        except KeyError:
            return None

    def __delitem__(self, key):
        del self.__dict__[key]

    def __setitem__(self, key, value):
        self.__dict__[key] = test_convert(key, value)

    def __setattr__(self, attr, value):
        self.__setitem__(attr, value)

    def __iter__(self):
        return iter(self.__dict__)

    def __len__(self):
        return len(self.__dict__)

    def __repr__(self):
        return f"{type(self).__name__}({self.__dict__})"

    @classmethod
    def from_file(
        cls, filename, password=None, locale=None, encryption=None, **kwargs
    ) -> "Authenticator":
        """Instantiate a new Authenticator with authentication data from file

        .. versionadded:: v0.5.0
        """
        cls = cls()
        cls.filename = filename
        cls.encryption = encryption or detect_file_encryption(cls.filename)

        if cls.encryption:
            if password is None:
                message = "File is encrypted but no password provided."
                logger.critical(message)
                raise FileEncryptionError(message)
            cls.crypter = AESCipher(password, **kwargs)
            file_data = cls.crypter.from_file(cls.filename, cls.encryption)
        else:
            file_data = cls.filename.read_text()

        json_data = json.loads(file_data)

        locale_code = json_data.pop("locale_code", None)
        locale = locale or locale_code
        cls.locale = locale

        # login cookies where renamed to website cookies
        # old names must be adjusted
        login_cookies = json_data.pop("login_cookies", None)
        if login_cookies:
            json_data["website_cookies"] = login_cookies

        cls.update(**json_data)

        logger.info(
            (
                f"load data from file {cls.filename} for "
                f"locale {cls.locale.country_code}"
            )
        )
        return cls

    @classmethod
    def from_login(
        cls,
        username: str,
        password: str,
        locale,
        register=False,
        captcha_callback=None,
        otp_callback=None,
        cvf_callback=None
    ) -> "Authenticator":
        """Instantiate a new Authenticator with authentication data from login

        .. versionadded:: v0.5.0
        """
        cls = cls()
        cls.locale = locale

        resp = login(
            username=username,
            password=password,
            country_code=cls.locale.country_code,
            domain=cls.locale.domain,
            market_place_id=cls.locale.market_place_id,
            captcha_callback=captcha_callback,
            otp_callback=otp_callback,
            cvf_callback=cvf_callback
        )

        logger.info(f"logged in to audible as {username}")

        if register:
            resp = register_(resp["access_token"], cls.locale.domain)
            logger.info("registered audible device")

        cls.update(**resp)
        return cls

    def auth_flow(self, request: httpx.Request):
        available_modes = self.available_auth_modes

        if "signing" in available_modes:
            self._apply_signing_auth_flow(request)
        elif "bearer" in available_modes:
            self._apply_bearer_auth_flow(request)
        else:
            message = "signing or bearer auth flow are not available."
            logger.critical(message)
            raise AuthFlowError(message)

        yield request

    def _apply_signing_auth_flow(self, request: httpx.Request) -> None:
        method = request.method
        path = request.url.path
        query = request.url.query
        body = request.content

        if query:
            path += f"?{query}"

        headers = sign_request(
            method, path, body, self.adp_token, self.device_private_key
        )

        request.headers.update(headers)
        logger.info("signing auth flow applied to request")

    def _apply_bearer_auth_flow(self, request: httpx.Request) -> None:
        if self.access_token_expired:
            self.refresh_access_token()

        headers = {
            "Authorization": "Bearer " + self.access_token,
            "client-id": "0"
        }

        request.headers.update(headers)
        logger.info("bearer auth flow applied to request")

    def _apply_cookies_auth_flow(self, request: httpx.Request) -> None:
        cookies = {name: value for (name, value) in self.website_cookies.items()}

        Cookies(cookies).set_cookie_header(request)
        logger.info("cookies auth flow applied to request")

    def sign_request(self, request: httpx.Request) -> None:
        """
        .. deprecated:: 0.5.0
           Use :met:`self._apply_signing_auth_flow` instead.
        """
        self._apply_signing_auth_flow(request)

    @property
    def available_auth_modes(self):
        available_modes = []

        if self.adp_token and self.device_private_key:
            available_modes.append("signing")

        if self.access_token:
            if self.access_token_expired and not self.refresh_token:
                pass
            else:
                available_modes.append("bearer")

        if self.website_cookies:
            available_modes.append("cookies")

        return available_modes

    def to_file(
            self,
            filename=None,
            password=None,
            encryption="default",
            indent=4,
            set_default=True,
            **kwargs
    ):

        if not (filename or self.filename):
            raise ValueError("No filename provided")

        if filename:
            filename = test_convert("filename", filename)

        target_file = filename or self.filename

        if encryption != "default":
            encryption = test_convert("encryption", encryption)
        else:
            encryption = self.encryption or False

        body = {
            "website_cookies": self.website_cookies,
            "adp_token": self.adp_token,
            "access_token": self.access_token,
            "refresh_token": self.refresh_token,
            "device_private_key": self.device_private_key,
            "store_authentication_cookie": self.store_authentication_cookie,
            "device_info": self.device_info,
            "customer_info": self.customer_info,
            "expires": self.expires,
            "locale_code": self.locale.country_code
        }
        json_body = json.dumps(body, indent=indent)

        if encryption is False:
            target_file.write_text(json_body)
            crypter = None
        else:
            if password:
                crypter = test_convert("crypter",
                                       AESCipher(password, **kwargs))
            elif self.crypter:
                crypter = self.crypter
            else:
                raise ValueError("No password provided")

            crypter.to_file(
                json_body,
                filename=target_file,
                encryption=encryption,
                indent=indent
            )

        logger.info(f"saved data to file {filename}")

        if set_default:
            self.filename = target_file
            self.encryption = encryption
            self.crypter = crypter

        logger.info(f"set filename {target_file} as default")

    def re_login(
            self,
            username,
            password,
            captcha_callback=None,
            otp_callback=None,
            cvf_callback=None
    ):

        login_device = login(
            username=username,
            password=password,
            country_code=self.locale.country_code,
            domain=self.locale.domain,
            market_place_id=self.locale.market_place_id,
            captcha_callback=captcha_callback,
            otp_callback=otp_callback,
            cvf_callback=cvf_callback
        )

        self.update(**login_device)

    def register_device(self):
        register_device = register_(
            access_token=self.access_token, domain=self.locale.domain
        )

        self.update(**register_device)

    def deregister_device(self, deregister_all: bool = False):
        return deregister_(
            access_token=self.access_token,
            deregister_all=deregister_all,
            domain=self.locale.domain
        )

    def refresh_access_token(self, force=False):
        if force or self.access_token_expired:
            if self.refresh_token is None:
                message = "No refresh token found. Can't refresh access token."
                logger.critical(message)
                raise NoRefreshToken(message)
            refresh_data = refresh_access_token(
                refresh_token=self.refresh_token, domain=self.locale.domain
            )

            self.update(**refresh_data)
        else:
            logger.info(
                "Access Token not expired. No refresh nessessary. "
                "To force refresh please use force=True"
            )

    def set_website_cookies_for_country(self, country_code):
        cookies_domain = test_convert("locale", country_code).domain

        self.website_cookies = refresh_website_cookies(
            self.refresh_token, self.locale.domain, cookies_domain
        )

    def get_activation_bytes(self, filename=None):
        return get_ab(self, filename)

    def user_profile(self):
        return user_profile(
            access_token=self.access_token, domain=self.locale.domain
        )

    @property
    def access_token_expires(self):
        return datetime.fromtimestamp(self.expires) - datetime.utcnow()

    @property
    def access_token_expired(self):
        return datetime.fromtimestamp(self.expires) <= datetime.utcnow()


class LoginAuthenticator:
    """Authenticator class to retrieve credentials from login.
    
    .. deprecated:: v0.5.0
    
       Use :classmethod:`audible.auth.Authenticator.from_login` instead.

    """

    def __new__(
            cls,
            username: str,
            password: str,
            locale,
            register=False,
            captcha_callback=None,
            otp_callback=None,
            cvf_callback=None
    ) -> Authenticator:
        return Authenticator.from_login(
            username,
            password,
            locale,
            register,
            captcha_callback,
            otp_callback,
            cvf_callback)


class FileAuthenticator:
    """Authenticator class to retrieve credentials from stored file.
    
    .. deprecated:: v0.5.0
    
       Use :classmethod:`audible.auth.Authenticator.from_file` instead.

    """

    def __new__(
            cls, filename, password=None, locale=None, encryption=None,
            **kwargs
    ) -> Authenticator:

        return Authenticator.from_file(
            filename, password, locale, encryption, **kwargs)
