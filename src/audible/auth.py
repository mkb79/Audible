import base64
import json
import logging
from collections.abc import Callable, Generator, Iterator
from datetime import datetime, timedelta
from typing import (
    TYPE_CHECKING,
    Any,
    Literal,
    Optional,
    Union,
    cast,
    overload,
)

import httpx
import rsa
from httpx import Cookies

from .activation_bytes import get_activation_bytes as get_ab
from .aescipher import AESCipher, detect_file_encryption
from .exceptions import AuthFlowError, FileEncryptionError, NoRefreshToken
from .login import external_login, login
from .register import deregister as deregister_
from .register import register as register_
from .utils import test_convert


if TYPE_CHECKING:
    import pathlib

    from ._types import TrueFalseT
    from .localization import Locale


logger = logging.getLogger("audible.auth")


def refresh_access_token(
    refresh_token: str, domain: str, with_username: bool = False
) -> dict[str, Any]:
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
) -> dict[str, str]:
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


def user_profile(access_token: str, domain: str) -> dict[str, Any]:
    """Returns user profile from Amazon.

    Args:
        access_token: The valid access token for authentication.
        domain: The top level domain of the requested Amazon server
            (e.g. com, de, fr).

    Returns:
        The Amazon user profile for the authenticated user.

    Raises:
        Exception: If the user profile is malformed
    """
    headers = {"Authorization": f"Bearer {access_token}"}

    resp = httpx.get(f"https://api.amazon.{domain}/user/profile", headers=headers)
    resp.raise_for_status()
    profile = resp.json()

    if not isinstance(profile, dict) and "user_id" not in profile:
        raise Exception("Malformed user profile response.")

    return profile


def user_profile_audible(access_token: str, domain: str) -> dict[str, Any]:
    """Returns user profile from Audible.

    Args:
        access_token: The valid access token for authentication.
        domain: The top level domain of the requested Audible server
            (e.g. com, de, fr).

    Returns:
        The Audible user profile for the authenticated user.

    Raises:
        Exception: If the user profile is malformed
    """
    headers = {"Authorization": f"Bearer {access_token}"}

    resp = httpx.get(f"https://api.audible.{domain}/user/profile", headers=headers)
    resp.raise_for_status()
    profile = resp.json()

    if not isinstance(profile, dict) and "user_id" not in profile:
        raise Exception("Malformed user profile response.")

    return profile


def sign_request(
    method: str, path: str, body: bytes, adp_token: str, private_key: str
) -> dict[str, str]:
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
    str_body = body.decode("utf-8")

    data = f"{method}\n{path}\n{date}\n{str_body}\n{adp_token}"

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

    access_token: str | None = None
    activation_bytes: str | None = None
    adp_token: str | None = None
    crypter: AESCipher | None = None
    customer_info: dict[str, Any] | None = None
    device_info: dict[str, Any] | None = None
    device_private_key: str | None = None
    encryption: str | bool | None = None
    expires: float | None = None
    filename: Optional["pathlib.Path"] = None
    locale: Optional["Locale"] = None
    refresh_token: str | None = None
    store_authentication_cookie: dict[str, Any] | None = None
    website_cookies: dict[str, Any] | None = None
    with_username: bool | None = False
    requires_request_body: bool = True
    _forbid_new_attrs: bool = True
    _apply_test_convert: bool = True

    def __setattr__(self, attr: str, value: Any) -> None:
        if self._forbid_new_attrs and not hasattr(self, attr):
            msg = (
                f"{self.__class__.__name__} is frozen, can't " f"add attribute: {attr}."
            )
            logger.error(msg)
            raise AttributeError(msg)

        if self._apply_test_convert:
            value = test_convert(attr, value)
        object.__setattr__(self, attr, value)

    def __iter__(self) -> Iterator[str]:
        for i in self.__dict__:
            if self.__dict__[i] is not None and not i.startswith("_"):
                yield i

    def __len__(self) -> int:
        return len(list(iter(self)))

    def __repr__(self) -> str:
        return f"{type(self).__name__}({self.__dict__})"

    def _update_attrs(self, **kwargs: Any) -> None:
        for attr, value in kwargs.items():
            setattr(self, attr, value)

    @classmethod
    def from_dict(
        cls, data: dict[str, Any], locale: Union[str, "Locale"] | None = None
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

        locale_code: str | None = data.pop("locale_code", None)
        auth.locale = cast("Locale", locale or locale_code)

        if "login_cookies" in data:
            auth.website_cookies = data.pop("login_cookies")

        auth._update_attrs(**data)

        logger.info("load data from dictionary for locale %s", auth.locale.country_code)

        return auth

    @classmethod
    def from_file(
        cls,
        filename: Union[str, "pathlib.Path"],
        password: str | None = None,
        locale: Union[str, "Locale"] | None = None,
        encryption: bool | str | None = None,
        **kwargs: Any,
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
        auth.filename = cast("pathlib.Path", filename)
        auth.encryption = encryption or detect_file_encryption(auth.filename)

        if isinstance(auth.encryption, str):
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
        auth.locale = cast("Locale", locale)

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
        serial: str | None = None,
        with_username: bool = False,
        captcha_callback: Callable[[str], str] | None = None,
        otp_callback: Callable[[], str] | None = None,
        cvf_callback: Callable[[], str] | None = None,
        approval_callback: Callable[[], Any] | None = None,
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
        auth.locale = cast("Locale", locale)

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
        serial: str | None = None,
        with_username: bool = False,
        login_url_callback: Callable[[str], str] | None = None,
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
        auth.locale = cast("Locale", locale)

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
        if self.adp_token is None or self.device_private_key is None:
            raise Exception("No signing data found.")

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

        if self.access_token is None:
            raise Exception("No access token found.")

        headers = {"Authorization": "Bearer " + self.access_token, "client-id": "0"}
        request.headers.update(headers)
        logger.info("bearer auth flow applied to request")

    def _apply_cookies_auth_flow(self, request: httpx.Request) -> None:
        if self.website_cookies is None:
            raise Exception("No website cookies found.")
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
    def available_auth_modes(self) -> list[str]:
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

    def to_dict(self) -> dict[str, Any]:
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
            "locale_code": self.locale.country_code if self.locale else None,
            "with_username": self.with_username,
            "activation_bytes": self.activation_bytes,
        }
        return data

    def to_file(
        self,
        filename: Union["pathlib.Path", str] | None = None,
        password: str | None = None,
        encryption: bool | str = "default",
        indent: int = 4,
        set_default: bool = True,
        **kwargs: Any,
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
            target_file: "pathlib.Path" = test_convert("filename", filename)
        elif self.filename:
            target_file = self.filename
        else:
            raise ValueError("No filename provided")

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

    def deregister_device(self, deregister_all: bool = False) -> Any:
        self.refresh_access_token()

        if self.access_token is None:
            raise Exception("No access token found.")
        if self.locale is None:
            raise Exception("No locale found.")

        return deregister_(
            access_token=self.access_token,
            deregister_all=deregister_all,
            domain=self.locale.domain,
            with_username=self.with_username or False,
        )

    def refresh_access_token(self, force: bool = False) -> None:
        if force or self.access_token_expired:
            if self.refresh_token is None:
                message = "No refresh token found. Can't refresh access token."
                logger.critical(message)
                raise NoRefreshToken(message)
            if self.locale is None:
                raise Exception("No locale found.")

            refresh_data = refresh_access_token(
                refresh_token=self.refresh_token,
                domain=self.locale.domain,
                with_username=self.with_username or False,
            )

            self._update_attrs(**refresh_data)
        else:
            logger.info(
                "Access Token not expired. No refresh necessary. "
                "To force refresh please use force=True"
            )

    def set_website_cookies_for_country(self, country_code: str) -> None:
        cookies_domain = test_convert("locale", country_code).domain

        if self.refresh_token is None:
            raise Exception("No refresh token found.")
        if self.locale is None:
            raise Exception("No locale found.")

        self.website_cookies = refresh_website_cookies(
            self.refresh_token,
            self.locale.domain,
            cookies_domain,
            self.with_username or False,
        )

    @overload
    def get_activation_bytes(
        self,
        filename: Union["pathlib.Path", str] | None = ...,
        extract: Literal[True] = ...,
        force_refresh: bool = ...,
    ) -> str:
        ...

    @overload
    def get_activation_bytes(
        self,
        filename: Union["pathlib.Path", str] | None = ...,
        *,
        extract: Literal[False],
        force_refresh: bool = ...,
    ) -> bytes:
        ...

    def get_activation_bytes(
        self,
        filename: Union["pathlib.Path", str] | None = None,
        extract: "TrueFalseT" = True,
        force_refresh: bool = False,
    ) -> str | bytes:
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
        ab = get_ab(self, filename, extract)  # type: ignore[arg-type]

        if extract:
            logger.debug(
                "Extract activation bytes from blob and store value"
                "activation_bytes attribute."
            )
            logger.debug("Found activation bytes: %s", ab)
            self.activation_bytes = ab

        return ab

    def user_profile(self) -> dict[str, Any]:
        if self.access_token is None:
            raise Exception("No access token found.")
        if self.locale is None:
            raise Exception("No locale found.")

        return user_profile(access_token=self.access_token, domain=self.locale.domain)

    @property
    def access_token_expires(self) -> timedelta:
        if self.expires is None:
            raise Exception("No expires timestamp found.")
        return datetime.fromtimestamp(self.expires) - datetime.utcnow()

    @property
    def access_token_expired(self) -> bool:
        if self.expires is None:
            raise Exception("No expires timestamp found.")
        return datetime.fromtimestamp(self.expires) <= datetime.utcnow()
