import base64
import json
import logging
from datetime import datetime, timedelta
from typing import Any, Callable, Dict, List, Generator, Optional, Union
from typing import TYPE_CHECKING

import httpx
import rsa
from httpx import Cookies

from .activation_bytes import get_activation_bytes as get_ab
from .aescipher import AESCipher, detect_file_encryption
from .exceptions import FileEncryptionError, AuthFlowError, NoRefreshToken
from .login import login, external_login
from .register import deregister as deregister_
from .register import register as register_
from .utils import test_convert

if TYPE_CHECKING:
    import pathlib
    from .localization import Locale

logger = logging.getLogger("audible.auth")


def refresh_access_token(refresh_token: str, domain: str) -> Dict[str, Any]:
    """Refreshes an access token.

    Args:    
        refresh_token: The refresh token obtained after a device
            registration.
        domain: The top level domain of the requested Amazon server
            (e.g. com).

    Returns:
        A dict with the new access token and expiration timestamp.

    Note:    
        The new access token is valid for 60 minutes.
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
    expires = (
            datetime.utcnow() + timedelta(seconds=expires_in_sec)).timestamp()

    return {"access_token": resp_dict["access_token"], "expires": expires}


def refresh_website_cookies(refresh_token: str,
                            domain: str,
                            cookies_domain: str) -> Dict[str, str]:
    """Fetches website cookies for a specific domain.

    Args:
        refresh_token: The refresh token obtained after a device
            registration.
        domain: The top level domain of the requested Amazon server
            (e.g. com, de, fr).
        cookies_domain: The top level domain scope for the cookies
            (e.g. com, de, fr).
    
    Returns:
        The requested cookies for the Amazon and Audible website for the given
        `cookies_domain` scope.
    """
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
            website_cookies[cookie["Name"]] = cookie["Value"].replace(
                r'"', r'')

    return website_cookies


def user_profile(access_token: str, domain: str) -> Dict[str, Any]:
    """Returns user profile from Amazon.

    Args:
        access_token: The valid access token for authentication.
        domain: The top level domain of the requested Amazon server
            (e.g. com, de, fr).
    
    Returns:
        The Amazon user profile for the authenticated user.
    """

    headers = {"Authorization": f"Bearer {access_token}"}

    resp = httpx.get(
        f"https://api.amazon.{domain}/user/profile", headers=headers)
    resp.raise_for_status()

    return resp.json()


def user_profile_audible(access_token: str, domain: str) -> Dict[str, Any]:
    """Returns user profile from Audible.

    Args:
        access_token: The valid access token for authentication.
        domain: The top level domain of the requested Audible server
            (e.g. com, de, fr).
    
    Returns:
        The Audible user profile for the authenticated user.
    """

    headers = {"Authorization": f"Bearer {access_token}"}

    resp = httpx.get(
        f"https://api.audible.{domain}/user/profile", headers=headers)
    resp.raise_for_status()

    return resp.json()


def sign_request(method: str,
                 path: str,
                 body: bytes,
                 adp_token: str,
                 private_key: str) -> Dict[str, str]:
    """Helper function who creates signed headers for http requests.

    Args:
        path: The requested http url path and query.
        method: The http request method (GET, POST, DELETE, ...).
        body: The http message body.
        adp_token: The adp token obtained after a device registration.
        private_key: The rsa key obtained after device registration.
    
    Returns:
        A dict with the signed headers.
    """
    date = datetime.utcnow().isoformat("T") + "Z"
    body = body.decode("utf-8")

    data = f"{method}\n{path}\n{date}\n{body}\n{adp_token}"

    key = rsa.PrivateKey.load_pkcs1(private_key.encode("utf-8"))
    cipher = rsa.pkcs1.sign(data.encode(), key, "SHA-256")
    signed_encoded = base64.b64encode(cipher)

    signature = f"{signed_encoded.decode()}:{date}"

    return {
        "x-adp-token": adp_token,
        "x-adp-alg": "SHA256withRSA:1.0",
        "x-adp-signature": signature
    }


class Authenticator(httpx.Auth):
    """Audible Authenticator class

    Note:
        A new class instance have to be instantiate with
        :meth:`Authenticator.from_login` or :meth:`Authenticator.from_file`.

    Attributes:
        access_token (:obj:`str`, :obj:`None`):
        activation_bytes (:obj:`str`, :obj:`None`):
        adp_token (:obj:`str`, :obj:`None`):
        crypter (:class:`~audible.aescipher.AESCipher`, :obj:`None`):
        customer_info (:obj:`dict`, :obj:`None`):
        device_info (:obj:`dict`, :obj:`None`):
        device_private_key (:obj:`str`, :obj:`None`):
        encryption (:obj:`str`, :obj:`bool`, :obj:`None`):
        expires (:obj:`float`, :obj:`None`):
        filename (:class:`pathlib.Path`, :obj:`None`):
        locale (:class:`~audible.localization.Locale`, :obj:`None`):
        refresh_token (:obj:`str`, :obj:`None`):
        store_authentication_cookie (:obj:`dict`, :obj:`None`):
        website_cookies (:obj:`dict`, :obj:`None`):
    """

    access_token: Optional[str] = None
    activation_bytes: Optional[str] = None
    adp_token: Optional[str] = None
    crypter: Optional[AESCipher] = None
    customer_info: Optional[Dict] = None
    device_info: Optional[Dict] = None
    device_private_key: Optional[str] = None
    encryption: Optional[Union[str, bool]] = None
    expires: Optional[float] = None
    filename: Optional["pathlib.Path"] = None
    locale: Optional["Locale"] = None
    refresh_token: Optional[str] = None
    store_authentication_cookie: Optional[Dict] = None
    website_cookies: Optional[Dict] = None
    requires_request_body: bool = True
    _forbid_new_attrs: bool = True
    _apply_test_convert: bool = True

    def __setattr__(self, attr, value):
        if self._forbid_new_attrs and not hasattr(self, attr):
            msg = (f"{self.__class__.__name__} is frozen, can't "
                   f"add attribute: {attr}.")
            logger.error(msg)
            raise AttributeError(msg)
                                 
        if self._apply_test_convert:
            value = test_convert(attr, value)
        object.__setattr__(self, attr, value)

    def __iter__(self):
        for i in self.__dict__:
            if self.__dict__[i] is not None and not i.startswith("_"):
                yield i

    def __len__(self):
        return len([i for i in self])

    def __repr__(self):
        return f"{type(self).__name__}({self.__dict__})"

    def _update_attrs(self, **kwargs) -> None:
        for attr, value in kwargs.items():
            setattr(self, attr, value)

    @classmethod
    def from_file(cls,
                  filename: Union[str, "pathlib.Path"],
                  password: Optional[str] = None,
                  locale: Optional[Union[str, "Locale"]] = None,
                  encryption: Optional[Union[bool, str]] = None,
                  **kwargs) -> "Authenticator":
        """Instantiate an Authenticator from authentication file.

        .. versionadded:: v0.5.0

        Args:
            filename:
                The name of the file with the authentication data.
            password: The password of the authentication file.
            locale: The country code of the Audible marketplace to interact
                with. If ``None`` the country code from file is used.
            encryption: The encryption style to use. Can be ``json`` or 
                ``bytes``. If ``None``, encryption will be auto detected.
            **kwargs: Keyword arguments are passed to the
                :class:`~audible.aescipher.AESCipher` class. See below.

        Keyword Arguments:
            key_size (int, Optional):
            salt_marker (Optional[bytes]):
            kdf_iterations (:obj:`int`, optional):
            hashmod:
            mac:

        Returns:
            A new Authenticator instance.
        """
        auth = cls()
        auth.filename = filename
        auth.encryption = encryption or detect_file_encryption(auth.filename)

        if auth.encryption:
            if password is None:
                message = "File is encrypted but no password provided."
                logger.critical(message)
                raise FileEncryptionError(message)
            auth.crypter = AESCipher(password, **kwargs)
            file_data = auth.crypter.from_file(auth.filename, auth.encryption)
        else:
            file_data = auth.filename.read_text()

        json_data = json.loads(file_data)

        locale_code = json_data.pop("locale_code", None)
        locale = locale or locale_code
        auth.locale = locale

        # login cookies where renamed to website cookies
        # old names must be adjusted
        login_cookies = json_data.pop("login_cookies", None)
        if login_cookies:
            json_data["website_cookies"] = login_cookies

        auth._update_attrs(**json_data)

        logger.info((f"load data from file {auth.filename} for "
                     f"locale {auth.locale.country_code}"))
        return auth

    @classmethod
    def from_login(cls,
                   username: str,
                   password: str,
                   locale: Union[str, "Locale"],
                   register: bool = False,
                   captcha_callback: Optional[Callable[[str], str]] = None,
                   otp_callback: Optional[Callable[[], str]] = None,
                   cvf_callback: Optional[Callable[[], str]] = None,
                   approval_callback: Optional[Callable[[], Any]] = None
                   ) -> "Authenticator":
        """Instantiate a new Authenticator with authentication data from login.

        .. versionadded:: v0.5.0

        Args:
            username: The Amazon email address.
            password: The Amazon password.
            locale: The ``country_code`` or :class:`audible.localization.Locale`
                instance for the marketplace to login.
            register: If ``True``, register a new device after login.
            captcha_callback: A custom callback to handle captcha requests
                during login.
            otp_callback: A custom callback to handle one-time password
                requests during login.
            cvf_callback: A custom callback to handle verify code requests
                during login.
            approval_callback: A custom Callable for handling approval alerts.

        Returns:
            An :class:`~audible.auth.Authenticator` instance.
        """
        auth = cls()
        auth.locale = locale

        auth.re_login(
            username=username,
            password=password,
            captcha_callback=captcha_callback,
            otp_callback=otp_callback,
            cvf_callback=cvf_callback,
            approval_callback=approval_callback)

        logger.info(f"logged in to Audible as {username}")

        if register:
            auth.register_device()
            logger.info("registered Audible device")

        return auth

    @classmethod
    def from_login_external(cls,
                            locale: Union[str, "Locale"],
                            register: bool = False,
                            login_url_callback: Optional[Callable[[str], str]] = None
                           ) -> "Authenticator":
        """Instantiate a new Authenticator from login with external browser.

        .. versionadded:: v0.5.1

        Args:
            locale: The ``country_code`` or :class:`audible.localization.Locale`
                instance for the marketplace to login.
            register: If ``True``, register a new device after login.
            login_url_callback: A custom Callable for handling login with 
                external browsers.

        Returns:
            An :class:`~audible.auth.Authenticator` instance.
        """
        auth = cls()
        auth.locale = locale

        auth.re_login_external(login_url_callback=login_url_callback)

        logger.info("logged in to Audible.")

        if register:
            auth.register_device()
            logger.info("registered Audible device")

        return auth

    def auth_flow(self,
                  request: httpx.Request
                  ) -> Generator[httpx.Request, httpx.Response, None]:
        """Auth flow to be executed on every request by :mod:`httpx`.

        Args:
            request: The request made by ``httpx``.

        Yields:
            The next request
        """
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
        headers = sign_request(method=request.method,
                               path=request.url.raw_path.decode(),
                               body=request.content,
                               adp_token=self.adp_token,
                               private_key=self.device_private_key)

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
        cookies = {
            name: value
            for (name, value) in self.website_cookies.items()
        }

        Cookies(cookies).set_cookie_header(request)
        logger.info("cookies auth flow applied to request")

    def sign_request(self, request: httpx.Request) -> None:
        """
        .. deprecated:: 0.5.0
           Use :meth:`self._apply_signing_auth_flow` instead.
        """
        self._apply_signing_auth_flow(request)

    @property
    def available_auth_modes(self) -> List:
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

    def to_file(self,
                filename: Union["pathlib.Path", str] = None,
                password: str = None,
                encryption: Union[bool, str] = "default",
                indent: int = 4,
                set_default: bool = True,
                **kwargs) -> None:
        """Save authentication data to file.
        
        .. versionadded:: 0.5.1
        
           Save activation bytes to auth file
       """

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
            "locale_code": self.locale.country_code,
            "activation_bytes": self.activation_bytes
        }
        json_body = json.dumps(body, indent=indent)

        if encryption is False:
            target_file.write_text(json_body)
            crypter = None
        else:
            if password:
                crypter = test_convert("crypter", AESCipher(
                    password, **kwargs))
            elif self.crypter:
                crypter = self.crypter
            else:
                raise ValueError("No password provided")

            crypter.to_file(
                json_body,
                filename=target_file,
                encryption=encryption,
                indent=indent)

        logger.info(f"saved data to file {target_file}")

        if set_default:
            self.filename = target_file
            self.encryption = encryption
            self.crypter = crypter

        logger.info(f"set filename {target_file} as default")

    def re_login(self,
                 username: str,
                 password: str,
                 captcha_callback: Optional[Callable[[str], str]] = None,
                 otp_callback: Optional[Callable[[], str]] = None,
                 cvf_callback: Optional[Callable[[], str]] = None,
                 approval_callback: Optional[Callable[[], Any]] = None) -> None:

        login_device = login(
            username=username,
            password=password,
            country_code=self.locale.country_code,
            domain=self.locale.domain,
            market_place_id=self.locale.market_place_id,
            captcha_callback=captcha_callback,
            otp_callback=otp_callback,
            cvf_callback=cvf_callback,
            approval_callback=approval_callback)

        self._update_attrs(**login_device)

    def re_login_external(self,
                          login_url_callback: Optional[Callable[[str], str]] = None
                         ) -> None:
        """Re-login with a external browser and refreshs the access token.

        .. versionadded:: v0.5.1

        Args:
            locale: The ``country_code`` or :class:`audible.localization.Locale`
                instance for the marketplace to login.
            register: If ``True``, register a new device after login.
            login_url_callback: A custom Callable for handling login with 
                external browsers.
        """
        login_device = external_login(
            country_code=self.locale.country_code,
            domain=self.locale.domain,
            market_place_id=self.locale.market_place_id,
            login_url_callback=login_url_callback)

        self._update_attrs(**login_device)

    def register_device(self) -> None:
        register_device = register_(
            access_token=self.access_token, domain=self.locale.domain)

        self._update_attrs(**register_device)

    def deregister_device(self, deregister_all: bool = False) -> Dict[
            str, Any]:
        return deregister_(
            access_token=self.access_token,
            deregister_all=deregister_all,
            domain=self.locale.domain)

    def refresh_access_token(self, force: bool = False) -> None:
        if force or self.access_token_expired:
            if self.refresh_token is None:
                message = "No refresh token found. Can't refresh access token."
                logger.critical(message)
                raise NoRefreshToken(message)
            refresh_data = refresh_access_token(
                refresh_token=self.refresh_token, domain=self.locale.domain)

            self._update_attrs(**refresh_data)
        else:
            logger.info("Access Token not expired. No refresh necessary. "
                        "To force refresh please use force=True")

    def set_website_cookies_for_country(self, country_code: str) -> None:
        cookies_domain = test_convert("locale", country_code).domain

        self.website_cookies = refresh_website_cookies(
            self.refresh_token, self.locale.domain, cookies_domain)

    def get_activation_bytes(self,
                             filename: Optional[
                                 Union["pathlib.Path", str]] = None,
                             extract: bool = True,
                             force_refresh: bool = False) -> Union[str, bytes]:
        """Get Activation bytes from Audible

        :param filename: [Optional] filename to save the activation blob
        :type filename: string, pathlib.Path
        :param extract: [Optional] if True, returns the extracted activation
                        bytes otherwise the whole activation blob
        :type force_refresh: [Optional] if True, existing activation bytes in 
                             auth file will be ignored and new activation bytes 
                             will be requested from server.

        .. versionadded:: 0.5.1
        
           The ``force_refresh`` argument. Fetched activation bytes are now 
           stored to `Authententicator.activation_bytes`.

        """
        if not force_refresh and extract and self.activation_bytes is not None:
            logger.debug(f"Activation bytes already fetched. Returned saved one.")
            return self.activation_bytes

        logger.debug("Fetch activation blob from server now.")
        ab = get_ab(self, filename, extract)
        
        if extract:
            logger.debug("Extract activation bytes from blob and store value"
                         "activation_bytes attribute.")
            logger.debug(f"Found activation bytes: {ab}")
            self.activation_bytes = ab

        return ab

    def user_profile(self) -> Dict:
        return user_profile(
            access_token=self.access_token, domain=self.locale.domain)

    @property
    def access_token_expires(self) -> timedelta:
        return datetime.fromtimestamp(self.expires) - datetime.utcnow()

    @property
    def access_token_expired(self) -> bool:
        return datetime.fromtimestamp(self.expires) <= datetime.utcnow()


class LoginAuthenticator:
    """Authenticator class to retrieve credentials from login.
    
    .. deprecated:: v0.5.0
    
       Use :meth:`audible.Authenticator.from_login` instead.
    """

    def __new__(cls,
                username: str,
                password: str,
                locale: Union[str, "Locale"],
                register: bool = False,
                captcha_callback: Optional[Callable[[str], str]] = None,
                otp_callback: Optional[Callable[[], str]] = None,
                cvf_callback: Optional[Callable[[], str]] = None
                ) -> "Authenticator":
        return Authenticator.from_login(username, password, locale, register,
                                        captcha_callback, otp_callback,
                                        cvf_callback)


class FileAuthenticator:
    """Authenticator class to retrieve credentials from stored file.
    
    .. deprecated:: v0.5.0
    
       Use :meth:`audible.Authenticator.from_file` instead.
    """

    def __new__(cls,
                filename: Union[str, "pathlib.Path"],
                password: Optional[str] = None,
                locale: Optional[Union[str, "Locale"]] = None,
                encryption: Optional[Union[bool, str]] = None,
                **kwargs) -> "Authenticator":
        return Authenticator.from_file(filename, password, locale, encryption,
                                       **kwargs)
