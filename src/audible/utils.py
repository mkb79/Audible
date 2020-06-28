import logging
import pathlib
import re
import time
from typing import Any, Optional, Union

from .localization import Locale


logger = logging.getLogger('audible.utils')


def _check_website_cookies(value) -> None:
    if not isinstance(value, dict):
        raise TypeError("type of login_cookies is not dict")
    if not set(map(type, value.values())) == {str}:
        raise TypeError("login_cookies have wrong format")


def _check_adp_token(value) -> None:
    if not isinstance(value, str):
        raise TypeError("type of adp_token is not str")

    parts = re.findall(r"{.*?}", value)
    if len(parts) != 5:
        raise ValueError("adp_token have wrong format")

    adp_token_as_dict = dict()
    for part in parts:
        search_pieces = re.search('{(.*?):(.*?)}', part)
        key = search_pieces.group(1)
        value = search_pieces.group(2)
        adp_token_as_dict[key] = value

    allowed_keys = {"enc", "key", "iv", "name", "serial"}
    if not adp_token_as_dict.keys() == allowed_keys:
        raise ValueError("adp_token have wrong format")


def _check_access_token(value) -> None:
    if not isinstance(value, str):
        raise TypeError("type of access_token is not str")

    if not value.startswith("Atna|"):
        raise ValueError('access_token have wrong format')


def _check_refresh_token(value) -> None:
    if not isinstance(value, str):
        raise TypeError("type of refresh_token is not str")
    if not value.startswith("Atnr|"):
        raise ValueError('refresh_token have wrong format')


def _check_device_private_key(value) -> None:
    if not isinstance(value, str):
        raise TypeError("type of device_private_key is not str")

    if not value.startswith("-----BEGIN RSA PRIVATE KEY-----"):
        raise ValueError('device_private_key have wrong format')

    if not value.endswith("-----END RSA PRIVATE KEY-----\n"):
        raise ValueError('device_private_key have wrong format')


def _check_expires(value) -> Optional[float]:
    if not isinstance(value, (int, float, str)):
        raise ValueError("type of device_private_key is not int or float")

    if isinstance(value, str):
        try:
            return float(value)
        except ValueError:
            raise ValueError("type of device_private_key is str "
                             "and can't be converted to float")


def _check_locales(value) -> Optional[Locale]:
    if isinstance(value, str):
        return Locale(value.lower())

    if not isinstance(value, Locale):
        raise TypeError("Locale error")


def _check_filename(value) -> Union[pathlib.Path, pathlib.WindowsPath]:
    if not isinstance(value, (pathlib.Path, pathlib.WindowsPath)):
        try:
            return pathlib.Path(value)
        except NotImplementedError:
            return pathlib.WindowsPath(value)
        except:
            raise Exception("File error")


def _check_crypter(value) -> Any:
    # TODO: write checks
    return value


def _check_encryption(value) -> None:
    allowed_values = [False, "json", "bytes"]

    if not isinstance(value, (bool, str)):
        raise TypeError("encryption has wrong type")
    if value not in allowed_values:
        raise ValueError("encryption has wrong value")


string_function_map = {
    "website_cookies": _check_website_cookies,
    "adp_token": _check_adp_token,
    "access_token": _check_access_token,
    "refresh_token": _check_refresh_token,
    "device_private_key": _check_device_private_key,
    "expires": _check_expires,
    "locale": _check_locales,
    "filename": _check_filename,
    "crypter": _check_crypter,
    "encryption": _check_encryption
}


def test_convert(key: str, value: Any) -> Any:
    if key in string_function_map and value is not None:
        return string_function_map[key](value) or value

    return value


class ElapsedTime:
    def __init__(self):
        self.start_time = time.time()

    def __call__(self):
        return time.time() - self.start_time
