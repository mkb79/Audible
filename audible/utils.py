import pathlib
import re

from box import Box

from .localization import Markets


class Storage:
    """
    This class stores our data and call `CheckData` to perform some \
    checks and transform data. *For internal purpose only*
    """
    def __init__(self, **kwargs):
        self._last_rejected = dict()
        self.reset_storage()
        self.update_data(**kwargs)

    def update_data(self, *, reset_storage=False, perform_tests=True,
                    **kwargs):
        allowed_keywords = [
            "login_cookies", "adp_token", "access_token", "refresh_token",
            "device_private_key", "expires", "filename", "market"
        ]

        # do some tests and transform some data if necessary
        if perform_tests:
            kwargs = CheckData(**kwargs).get_revised_data()

        # sort out not allowed key/value pairs
        for key in list(kwargs.keys()):
            if key not in allowed_keywords:
                self._last_rejected[key] = kwargs.pop(key)

        if reset_storage:
            self.reset_storage()

        self._boxed_data.update(**kwargs)

    def reset_storage(self):
        self._boxed_data = Box()

    @property
    def last_rejected_data(self):
        return self._last_rejected

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
            raise KeyError('No such key: {}'.format(item))


class CheckData:
    def __init__(self, **data):
        self._origin_data = data
        self._revised_data = data.copy()
        self._perform_all_checks()

    def get_revised_data(self):
        return self._revised_data

    def get_origin_data(self):
        return self._origin_data

    def get_differences(self):
        # TODO: return difference between input/output
        raise NotImplementedError

    def _perform_all_checks(self):
        methods = {}
        names = [x for x in dir(self) if x.startswith("_check_")]
        for name in names:
            attr = getattr(self, name)
            methods[name] = attr
        for name, method in methods.items():
            # print("calling: {}".format(name))
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

            # TODO: check parts of adp_token
            # allowed_startswith = ["{enc:", "{key:", "{iv:", "{name:", "{serial:"]
            # print(all(x in re.search(r"\{.*?\}", y).group() for x in allowed_keys for y in parts))

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
        device_private_key = self._revised_data.get("device_private_key", None)
        if device_private_key is None:
            return
        if not isinstance(device_private_key, str):
            raise TypeError("type of device_private_key is not str")
        if not device_private_key.startswith("-----BEGIN RSA PRIVATE KEY-----"):
            raise ValueError('device_private_key have wrong format')
        if device_private_key.endswith("-----END RSA PRIVATE KEY-----"):
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
                raise ValueError("type of device_private_key is str and can't be converted to float")

    def _check_market(self):
        market = self._revised_data.get("market", None)
        market_code = self._revised_data.get("market_code", None)

        if market is not None:
            if isinstance(market, Markets):
                return
            elif isinstance(market, str):
                self._revised_data["market"] = Markets.from_market_code(market.lower())
            else:
                raise TypeError("Market error")

        elif market_code is not None:
            self._revised_data["market"] = Markets.from_market_code(market_code.lower())

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
