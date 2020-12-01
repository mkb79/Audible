import logging
import pathlib
import re
import time
from typing import Any, Dict, Optional, Union

from .aescipher import AESCipher
from .localization import Locale


logger = logging.getLogger("audible.utils")


def _check_website_cookies(value: Dict[str, str]) -> None:
    if not isinstance(value, dict):
        raise TypeError(f"website_cookies: Expected dict, "
                        f"got {type(value).__name__}.")
    if not set(map(type, value.values())) == {str}:
        raise TypeError("website_cookies: Value(s) of website_cookies have "
                        "wrong type.")


def _check_adp_token(value: str) -> None:
    if not isinstance(value, str):
        raise TypeError(f"adp_token: Expected str, "
                        f"got {type(value).__name__}.")

    fmt = (r"^{enc:(?P<enc>.*?)}{key:(?P<key>.*?)}{iv:(?P<iv>.*?)}"
           r"{name:(?P<name>.*?)}{serial:(?P<serial>Mg==)}$")
    if not re.match(fmt, value):
        raise ValueError("adp_token: Invalid token.")


def _check_access_token(value: str) -> None:
    if not isinstance(value, str):
        raise TypeError(f"access_token: Expected str, "
                        f"got {type(value).__name__}.")

    fmt = r"^(?P<access_token>Atna\|.*)$"
    if not re.match(fmt, value):
        raise ValueError("access_token: Invalid token.")


def _check_refresh_token(value: str) -> None:
    if not isinstance(value, str):
        raise TypeError(f"refresh_token: Expected str, "
                        f"got {type(value).__name__}.")

    fmt = r"^(?P<refresh_token>Atnr\|.*)$"
    if not re.match(fmt, value):
        raise ValueError("refresh_token: Invalid token.")


def _check_device_private_key(value: str) -> None:
    if not isinstance(value, str):
        raise TypeError(f"device_private_key: Expected str, "
                        f"got {type(value).__name__}.")

    fmt = (r"^(?P<device_private_key>-----BEGIN RSA PRIVATE KEY-----.*"
           r"-----END RSA PRIVATE KEY-----\n)$")
    if not re.match(fmt, value, re.S):
        raise ValueError("device_private_key: Invalid token.")


def _check_expires(value: Union[int, float, str]) -> Optional[float]:
    if not isinstance(value, (int, float, str)):
        raise TypeError(f"expires: Expected int/float/str, "
                        f"got {type(value).__name__}.")

    if isinstance(value, str):
        try:
            return float(value)
        except ValueError as exc:
            raise ValueError("expires: Got str. Converting to float "
                             "raises an error.") from exc


def _check_locale(value: Union[str, Locale]) -> Optional[Locale]:
    if not isinstance(value, (Locale, str)):
        raise TypeError(f"locales: Expected Locale/str, "
                        f"got {type(value).__name__}.")

    if isinstance(value, str):
        return Locale(value.lower())


def _check_filename(value) -> pathlib.Path:
    if not isinstance(value, pathlib.Path):
        try:
            return pathlib.Path(value)
        except Exception as exc:
            raise Exception(f"filename: Got {type(value).__name__}. Converting "
                            f"to Path raises an error.") from exc


def _check_crypter(value: AESCipher) -> None:
    if not isinstance(value, AESCipher):
        raise TypeError(f"crypter: Expected AESCipher, "
                        f"got {type(value).__name__}.")


def _check_encryption(value: Union[bool, str]) -> None:
    if not isinstance(value, (bool, str)):
        raise TypeError(f"encryption: Expected bool/str, "
                        f"got {type(value).__name__}.")

    if value not in [False, "json", "bytes"]:
        raise ValueError("encryption: Value are not allowed.")


string_function_map = {
    "website_cookies": _check_website_cookies,
    "adp_token": _check_adp_token,
    "access_token": _check_access_token,
    "refresh_token": _check_refresh_token,
    "device_private_key": _check_device_private_key,
    "expires": _check_expires,
    "locale": _check_locale,
    "filename": _check_filename,
    "crypter": _check_crypter,
    "encryption": _check_encryption
}


def test_convert(key: str, value: Any) -> Any:
    """Helper function to check and convert values for specific keys."""
    if key in string_function_map and value is not None:
        return string_function_map[key](value) or value

    return value


class ElapsedTime:
    def __init__(self):
        self.start_time = time.time()

    def __call__(self):
        return time.time() - self.start_time
