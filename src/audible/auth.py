import base64
import json
import logging
from datetime import datetime, timedelta
from typing import (
    TYPE_CHECKING,
    Any,
    Callable,
    Dict,
    Generator,
    List,
    Literal,
    Optional,
    Union,
    overload,
)

import httpx
import rsa
from httpx import Cookies

from ._types import TrueFalseType
from .activation_bytes import get_activation_bytes as get_ab
from .aescipher import AESCipher, detect_file_encryption
from .exceptions import AuthFlowError, FileEncryptionError, NoRefreshToken
from .login import external_login, login
from .register import deregister as deregister_
from .register import register as register_
from .utils import test_convert


if TYPE_CHECKING:
    import pathlib

    from .localization import Locale


logger = logging.getLogger("audible.auth")


def refresh_access_token(
    refresh_token: str, domain: str, with_username: bool = False
) -> Dict[str, Any]:
    """Refreshes an access token.

    Args:
        refresh_token: The refresh token obtained after a device
            registration.
        domain: The top level domain of the requested Amazon server
            (e.g. com).
        with_username: If ``True`` uses `audible` domain instead of `amazon`.

    Returns:
        A dict with the new access token and expiration timestamp.

    Note:
        The new access token is valid for 60 minutes.

    .. versionadded:: v0.8
        The with_username argument
    """
    body = {
        "app_name": "Audible",
        "app_version": "3.56.2",
        "source_token": refresh_token,
        "requested_token_type": "access_token",
        "source_token_type": "refresh_token",
    }

    target_domain = "audible" if with_username else "amazon"

    resp = httpx.post(f"https://api.{target_domain}.{domain}/auth/token", data=body)
    resp.raise_for_status()
    resp_dict = resp.json()

    expires_in_sec = int(resp_dict["expires_in"])
    expires = (datetime.utcnow() + timedelta(seconds=expires_in_sec)).timestamp()

    return {"access_token": resp_dict["access_token"], "expires": expires}


def refresh_website_cookies(
    refresh_token: str, domain: str, cookies_domain: str, with_username: bool = False
) -> Dict[str, str]:
    """Fetches website cookies for a specific domain.

    Args:
        refresh_token: The refresh token obtained after a device
            registration.
        domain: The top level domain of the requested Amazon server
            (e.g. com, de, fr).
        cookies_domain: The top level domain scope for the cookies
            (e.g. com, de, fr).
        with_username: If ``True`` uses `audible` domain instead of `amazon`.

    Returns:
        The requested cookies for the Amazon and Audible website for the given
        `cookies_domain` scope.

    .. versionadded:: v0.8
        The with_username argument
    """
    target_domain = "audible" if with_username else "amazon"

    url = f"https://www.{target_domain}.{domain}/ap/exchangetoken/cookies"

    body = {
        "app_name": "Audible",
        "app_version": "3.56.2",
        "source_token": refresh_token,
        "requested_token_type": "auth_cookies",
        "source_token_type": "refresh_token",
        "domain": f".{target_domain}.{cookies_domain}",
    }

    resp = httpx.post(url, data=body)
    resp.raise_for_status()
    resp_dict = resp.json()

    raw_cookies = resp_dict["response"]["tokens"]["cookies"]
    website_cookies = {}
    for domain_cookies in raw_cookies:
        for cookie in raw_cookies[domain_cookies]:
            website_cookies[cookie["Name"]] = cookie["Value"].replace(r'"', r"")

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

    resp = httpx.get(f"https://api.amazon.{domain}/user/profile", headers=headers)
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

    resp = httpx.get(f"https://api.audible.{domain}/user/profile", headers=headers)
    resp.raise_for_status()

    return resp.json()


def sign_request(
    method: str, path: str, body: bytes, adp_token: str, private_key: str
) -> Dict[str, str]:
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
        "x-adp-signature": signature,
    }


class Authenticator(httpx.Auth):
    """Audible Authenticator class.

    Note:
        A new class instance have to be instantiated with
        :meth:`Authenticator.from_login` or :meth:`Authenticator.from_file`.

    .. versionadded:: v0.8
        The with_username attribute.

    Note:
        Auth data saved with v0.8 or later
        can not be loaded with versions less than v0.8!
        If an auth file for a pre-Amazon account (with_username=True) was
        created with v0.7.1 or v0.7.2 set `auth.with_username` to `True` and
        save the data again. After this deregistration, refreshing access
        tokens and requesting cookies for another domain will work for
        pre-Amazon accounts.
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
    with_username: Optional[bool] = False
    requires_request_body: bool = True
    _forbid_new_attrs: bool = True
    _apply_test_convert: bool = True

    def __setattr__(self, attr, value):
        if self._forbid_new_attrs and not hasattr(self, attr):
            msg = (
                f"{self.__class__.__name__} is frozen, can't " f"add attribute: {attr}."
            )
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
        return len(list(self))

    def __repr__(self):
        return f"{type(self).__name__}({self.__dict__})"

    def _update_attrs(self, **kwargs) -> None:
        for attr, value in kwargs.items():
            setattr(self, attr, value)

    @classmethod
    def from_dict(
        cls, data: Dict, locale: Optional[Union[str, "Locale"]] = None
    ) -> "Authenticator":
        """Instantiate an Authenticator from authentication file.

        .. versionadded:: v0.7.1

        Args:
            data: A dictionary with the authentication data
            locale: The country code of the Audible marketplace to interact
                with. If ``None`` the country code from file is used.

        Returns:
            A new Authenticator instance.
        """
        auth = cls()

        locale_code = data.pop("locale_code", None)
        locale = locale or locale_code
        auth.locale = locale

        if "login_cookies" in data:
            auth.website_cookies = data.pop("login_cookies")

        auth._update_attrs(**data)

        logger.info("load data from dictionary for locale %s", auth.locale.country_code)

        return auth

    @classmethod
    def from_file(
        cls,
        filename: Union[str, "pathlib.Path"],
        password: Optional[str] = None,
        locale: Optional[Union[str, "Locale"]] = None,
        encryption: Optional[Union[bool, str]] = None,
        **kwargs,
    ) -> "Authenticator":
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

        Raises:
            FileEncryptionError: If file ist encrypted without providing a password
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
        if "login_cookies" in json_data:
            auth.website_cookies = json_data.pop("login_cookies")

        auth._update_attrs(**json_data)

        logger.info(
            "load data from file %s for locale %s",
            auth.filename,
            auth.locale.country_code,
        )
        return auth

    @classmethod
    def from_login(
        cls,
        username: str,
        password: str,
        locale: Union[str, "Locale"],
        serial: Optional[str] = None,
        with_username: bool = False,
        captcha_callback: Optional[Callable[[str], str]] = None,
        otp_callback: Optional[Callable[[], str]] = None,
        cvf_callback: Optional[Callable[[], str]] = None,
        approval_callback: Optional[Callable[[], Any]] = None,
    ) -> "Authenticator":
        """Instantiate a new Authenticator with authentication data from login.

        .. versionadded:: v0.5.0

        .. versionadded:: v0.5.4
           The serial argument
           The with_username argument

        Args:
            username: The Amazon email address.
            password: The Amazon password.
            locale: The ``country_code`` or :class:`audible.localization.Locale`
                instance for the marketplace to login.
            serial: The device serial. If ``None`` a custom one will be created.
            with_username: If ``True`` login with Audible username instead
                of Amazon account.
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

        login_device = login(
            username=username,
            password=password,
            country_code=auth.locale.country_code,
            domain=auth.locale.domain,
            market_place_id=auth.locale.market_place_id,
            serial=serial,
            with_username=with_username,
            captcha_callback=captcha_callback,
            otp_callback=otp_callback,
            cvf_callback=cvf_callback,
            approval_callback=approval_callback,
        )
        logger.info("logged in to Audible as %s", username)
        register_device = register_(with_username=with_username, **login_device)

        auth._update_attrs(with_username=with_username, **register_device)
        logger.info("registered Audible device")

        return auth

    @classmethod
    def from_login_external(
        cls,
        locale: Union[str, "Locale"],
        serial: Optional[str] = None,
        with_username: bool = False,
        login_url_callback: Optional[Callable[[str], str]] = None,
    ) -> "Authenticator":
        """Instantiate a new Authenticator from login with external browser.

        .. versionadded:: v0.5.1

        .. versionadded:: v0.5.4
           The serial argument
           The with_username argument

        Args:
            locale: The ``country_code`` or :class:`audible.localization.Locale`
                instance for the marketplace to login.
            serial: The device serial. If ``None`` a custom one will be created.
            with_username: If ``True`` login with Audible username instead
                of Amazon account.
            login_url_callback: A custom Callable for handling login with
                external browsers.

        Returns:
            An :class:`~audible.auth.Authenticator` instance.
        """
        auth = cls()
        auth.locale = locale

        login_device = external_login(
            country_code=auth.locale.country_code,
            domain=auth.locale.domain,
            market_place_id=auth.locale.market_place_id,
            serial=serial,
            with_username=with_username,
            login_url_callback=login_url_callback,
        )
        logger.info("logged in to Audible.")

        register_device = register_(with_username=with_username, **login_device)

        auth._update_attrs(with_username=with_username, **register_device)
        logger.info("registered Audible device")

        return auth

    def auth_flow(
        self, request: httpx.Request
    ) -> Generator[httpx.Request, httpx.Response, None]:
        """Auth flow to be executed on every request by :mod:`httpx`.

        Args:
            request: The request made by ``httpx``.

        Yields:
            The next request

        Raises:
            AuthFlowError: If no auth flow is available.
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
        headers = sign_request(
            method=request.method,
            path=request.url.raw_path.decode(),
            body=request.content,
            adp_token=self.adp_token,
            private_key=self.device_private_key,
        )

        request.headers.update(headers)
        logger.info("signing auth flow applied to request")

    def _apply_bearer_auth_flow(self, request: httpx.Request) -> None:
        if self.access_token_expired:
            self.refresh_access_token()

        headers = {"Authorization": "Bearer " + self.access_token, "client-id": "0"}
        request.headers.update(headers)
        logger.info("bearer auth flow applied to request")

    def _apply_cookies_auth_flow(self, request: httpx.Request) -> None:
        cookies = self.website_cookies.copy()

        Cookies(cookies).set_cookie_header(request)
        logger.info("cookies auth flow applied to request")

    def sign_request(self, request: httpx.Request) -> None:
        """Sign a request.

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

    def to_dict(self) -> Dict:
        """Returns authentication data as dict.

        .. versionadded:: 0.7.1

        .. versionadded:: v0.8
           The returned dict now contains the `with_username` attribute
        """
        data = {
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
            "with_username": self.with_username,
            "activation_bytes": self.activation_bytes,
        }
        return data

    def to_file(
        self,
        filename: Optional[Union["pathlib.Path", str]] = None,
        password: Optional[str] = None,
        encryption: Union[bool, str] = "default",
        indent: int = 4,
        set_default: bool = True,
        **kwargs,
    ) -> None:
        """Save authentication data to file.

        .. versionadded:: 0.5.1
           Save activation bytes to auth file

        .. versionadded:: v0.8
           The saved file now contains the `with_username` attribute
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

        data = self.to_dict()
        json_data = json.dumps(data, indent=indent)

        if encryption is False:
            target_file.write_text(json_data)
            crypter = None
        else:
            if password:
                crypter = test_convert("crypter", AESCipher(password, **kwargs))
            elif self.crypter:
                crypter = self.crypter
            else:
                raise ValueError("No password provided")

            crypter.to_file(
                json_data, filename=target_file, encryption=encryption, indent=indent
            )

        logger.info("saved data to file %s", target_file)

        if set_default:
            self.filename = target_file
            self.encryption = encryption
            self.crypter = crypter

        logger.info("set filename %s as default", target_file)

    def deregister_device(self, deregister_all: bool = False) -> Dict[str, Any]:
        self.refresh_access_token()
        return deregister_(
            access_token=self.access_token,
            deregister_all=deregister_all,
            domain=self.locale.domain,
            with_username=self.with_username,
        )

    def refresh_access_token(self, force: bool = False) -> None:
        if force or self.access_token_expired:
            if self.refresh_token is None:
                message = "No refresh token found. Can't refresh access token."
                logger.critical(message)
                raise NoRefreshToken(message)
            refresh_data = refresh_access_token(
                refresh_token=self.refresh_token,
                domain=self.locale.domain,
                with_username=self.with_username,
            )

            self._update_attrs(**refresh_data)
        else:
            logger.info(
                "Access Token not expired. No refresh necessary. "
                "To force refresh please use force=True"
            )

    def set_website_cookies_for_country(self, country_code: str) -> None:
        cookies_domain = test_convert("locale", country_code).domain

        self.website_cookies = refresh_website_cookies(
            self.refresh_token, self.locale.domain, cookies_domain, self.with_username
        )

    @overload
    def get_activation_bytes(
        self,
        filename: Optional[Union["pathlib.Path", str]] = ...,
        extract: Literal[True] = ...,
        force_refresh: bool = ...,
    ) -> str:
        ...

    @overload
    def get_activation_bytes(
        self,
        filename: Optional[Union["pathlib.Path", str]] = ...,
        *,
        extract: Literal[False],
        force_refresh: bool = ...,
    ) -> bytes:
        ...

    def get_activation_bytes(
        self,
        filename: Optional[Union["pathlib.Path", str]] = None,
        extract: TrueFalseType = True,
        force_refresh: bool = False,
    ) -> Union[str, bytes]:
        """Get Activation bytes from Audible.

        Args:
            filename: [Optional] filename to save the activation blob
            extract: [Optional] if True, returns the extracted activation
                bytes otherwise the whole activation blob
            force_refresh: [Optional] if True, existing activation bytes in
                auth file will be ignored and new activation bytes
                will be requested from server.

        Returns:
            The activation bytes

        .. versionadded:: 0.5.1
           The ``force_refresh`` argument. Fetched activation bytes are now
           stored to `Authententicator.activation_bytes`.
        """
        if not force_refresh and extract and self.activation_bytes is not None:
            logger.debug("Activation bytes already fetched. Returned saved one.")
            return self.activation_bytes

        logger.debug("Fetch activation blob from server now.")
        ab = get_ab(self, filename, extract)

        if extract:
            logger.debug(
                "Extract activation bytes from blob and store value"
                "activation_bytes attribute."
            )
            logger.debug("Found activation bytes: %s", ab)
            self.activation_bytes = ab

        return ab

    def user_profile(self) -> Dict:
        return user_profile(access_token=self.access_token, domain=self.locale.domain)

    @property
    def access_token_expires(self) -> timedelta:
        return datetime.fromtimestamp(self.expires) - datetime.utcnow()

    @property
    def access_token_expired(self) -> bool:
        return datetime.fromtimestamp(self.expires) <= datetime.utcnow()
