import logging
import pathlib
import re
from typing import Any, Dict

from box import Box

from .localization import Locale


_utils_logger = logging.getLogger('audible.utils')


class Storage:
    """
    Stores selected data and discards all other. Uses ``CheckData``
    to perform certain tests and change data type if possible.

    """
    def __init__(self, perform_tests: bool = True, **data: Any) -> None:
        self._last_discarded = dict()
        self._boxed_data = Box()
        self.update_data(**data, perform_tests=perform_tests)

    def update_data(self, *, reset_storage: bool = False,
                    perform_tests: bool = True, **data: Any) -> None:
        """Update stored data."""
        allowed_keywords = ["login_cookies", "adp_token", "access_token",
                            "refresh_token", "device_private_key", "expires",
                            "filename", "locale", "crypter", "encryption"]

        # perform certain tests and change data type if necessary
        if perform_tests:
            check_data = CheckData(**data)
            data = check_data.get_revised_data()
            # differences = check_data.get_differences()

        # sort out not allowed key/value pairs
        for key in list(data.keys()):
            if key not in allowed_keywords:
                self._last_discarded[key] = data.pop(key)

        if reset_storage:
            self.reset_data()

        self._boxed_data.update(**data)

    def reset_data(self) -> None:
        """Reset all stored data."""
        self._boxed_data.clear()

    def last_discarded_data(self) -> Dict[str, Any]:
        """Returns discarded data from last update."""
        return self._last_discarded

    def __getattr__(self, attr):
        try:
            return getattr(self._boxed_data, attr)
        except AttributeError:
            try:
                return super().__getattr__(attr)
            except AttributeError:
                return None

    def __getitem__(self, item):
        try:
            return getattr(self._boxed_data, item)
        except AttributeError:
            raise KeyError(f"No such key: {item}")


class CheckData:
    """Performs certain tests on given data and change data type."""
    def __init__(self, **data: Any):
        self._origin_data = data
        self._revised_data = data.copy()
        self._perform_all_tests()

    def get_revised_data(self) -> Dict[str, Any]:
        """Returns revised data."""
        return self._revised_data

    def get_origin_data(self) -> Dict[str, Any]:
        """Returns origin data."""
        return self._origin_data

    def get_differences(self) -> Dict[str, Any]:
        """Compare origin/revised data and returns diff."""
        origin_keys = self._origin_data.keys()
        revised_keys = self._revised_data.keys()

        if not origin_keys == revised_keys:
            raise KeyError("origin and revised keys are not equal")

        differences = dict()
        for key in origin_keys:
            origin_value = self._origin_data[key]
            revised_value = self._revised_data[key]
            if origin_value != revised_value:
                differences[key] = {"origin_value": origin_value,
                                    "origin_type": type(origin_value),
                                    "revised_value": revised_value,
                                    "revised_type": type(revised_value)}

        return differences

    def _perform_all_tests(self):
        methods = {}
        names = [x for x in dir(self) if x.startswith("_check_")]
        for name in names:
            attr = getattr(self, name)
            methods[name] = attr
        for _, method in methods.items():
            method()

    def _check_login_cookies(self):
        cookies = self._revised_data.get("login_cookies", None)

        if cookies is None:
            return
        if not isinstance(cookies, dict):
            raise TypeError("type of login_cookies is not dict")
        if not set(map(type, cookies.values())) == {str}:
            raise TypeError("login_cookies have wrong format")

    def _check_adp_token(self):
        adp_token = self._revised_data.get("adp_token", None)

        if adp_token is None:
            return
        if not isinstance(adp_token, str):
            raise TypeError("type of adp_token is not str")

        parts = re.findall(r"\{.*?\}", adp_token)
        if len(parts) != 5:
            raise ValueError("adp_token have wrong format")
    
        adp_token_as_dict = dict()
        for part in parts:
            search_pieces = re.search('\{(.*?)\:(.*?)\}', part)
            key = search_pieces.group(1)
            value = search_pieces.group(2)
            adp_token_as_dict[key] = value
    
            allowed_keys = {"enc", "key", "iv", "name", "serial"}
        if not adp_token_as_dict.keys() == allowed_keys:
            raise ValueError("adp_token have wrong format")

    def _check_access_token(self):
        access_token = self._revised_data.get("access_token", None)

        if access_token is None:
            return
        if not isinstance(access_token, str):
            raise TypeError("type of access_token is not str")
        if not access_token.startswith("Atna|"):
            raise ValueError('access_token have wrong format')

    def _check_refresh_token(self):
        refresh_token = self._revised_data.get("refresh_token", None)

        if refresh_token is None:
            return
        if not isinstance(refresh_token, str):
            raise TypeError("type of refresh_token is not str")
        if not refresh_token.startswith("Atnr|"):
            raise ValueError('refresh_token have wrong format')

    def _check_device_private_key(self):
        device_key = self._revised_data.get("device_private_key", None)

        if device_key is None:
            return

        if not isinstance(device_key, str):
            raise TypeError("type of device_private_key is not str")

        if not device_key.startswith("-----BEGIN RSA PRIVATE KEY-----"):
            raise ValueError('device_private_key have wrong format')

        if not device_key.endswith("-----END RSA PRIVATE KEY-----\n"):
            raise ValueError('device_private_key have wrong format')

    def _check_expires(self):
        expires = self._revised_data.get("expires", None)

        if expires is None:
            return
        if not isinstance(expires, (int, float, str)):
            raise ValueError("type of device_private_key is not int or float")

        if isinstance(expires, str):
            try:
                self._revised_data["expires"] = float(expires)
                return
            except ValueError:
                raise ValueError("type of device_private_key is str "
                                 "and can't be converted to float")

    def _check_locales(self):
        locale = self._revised_data.get("locale", None)
        locale_code = self._revised_data.get("locale_code", None)

        if locale is not None:
            if isinstance(locale, Locale):
                return
            elif isinstance(locale, str):
                self._revised_data["locale"] = Locale.from_locale_code(locale.lower())
            else:
                raise TypeError("Locale error")

        elif locale_code is not None:
            self._revised_data["locale"] = Locale.from_locale_code(locale_code.lower())

    def _check_filename(self):
        filename = self._revised_data.get("filename", None)

        if filename is None:
            return
        if not isinstance(filename, (pathlib.Path, pathlib.WindowsPath)):
            try:
                self._revised_data["filename"] = pathlib.Path(filename)
            except NotImplementedError:
                self._revised_data["filename"] = pathlib.WindowsPath(filename)
            except:
                raise Exception("File error")

    def _check_crypter(self):
        crypter = self._revised_data.get("crypter", None)

        if crypter is None:
            return
        # TODO: write checks

    def _check_encryption(self):
        encryption = self._revised_data.get("encryption", False)

        allowed_values = [False, "json", "bytes"]

        if not isinstance(encryption, (bool, str)):
            raise TypeError("encryption has wrong type")
        if encryption not in allowed_values:
            raise ValueError("encryption has wrong value")
