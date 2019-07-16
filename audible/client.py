from datetime import datetime
import json
import logging

import requests

from .auth import (auth_login, auth_register, auth_deregister,
                   CertAuth, refresh_access_token, user_profile)
from .cryptography import AESCipher
from .utils import Storage


_client_logger = logging.getLogger('audible.client')


class Client:
    def __init__(self, data: Storage) -> None:
        self._data = data
        # discarded_kwargs = self._data.last_discarded_data()

    def __getattr__(self, attr):
        try:
            return getattr(self._data._boxed_data, attr)
        except AttributeError:
            try:
                return super().__getattr__(attr)
            except AttributeError:
                return None

    def __getitem__(self, item):
        try:
            return getattr(self._data._boxed_data, item)
        except AttributeError:
            raise KeyError('No such key: {}'.format(item))

    @classmethod
    def from_login(cls, username: str, password: str, locale, filename=None,
                   register=True, captcha_callback=None, otp_callback=None):

        data = Storage(locale=locale, filename=filename)

        response = auth_login(username, password, data.locale,
                              captcha_callback=captcha_callback,
                              otp_callback=otp_callback)

        if register:
            response = auth_register(**response, locale=data.locale)

        data.update_data(**response)

        return cls(data)

    @classmethod
    def from_json_file(cls, filename, locale=None):
        data = Storage(locale=locale, filename=filename)

        json_data = json.loads(data.filename.read_text())

        data.update_data(**json_data)

        _client_logger.warn("``from_json_file`` is deprecated. "
                            "``use from_file instead``")

        _client_logger.info((f"loaded data from file {filename} for "
                             f"locale {data.locale.locale_code}"))

        return cls(data)

    @classmethod
    def from_file(cls, filename, password=None, locale=None, encryption=False,
                  set_default=True, **kwargs):

        data = Storage(filename=filename, encryption=encryption)
        if data.encryption:
            data.update_data(crypter=AESCipher(password, **kwargs))
            file_data = data.crypter.from_file(data.filename, data.encryption)
        else:
            file_data = data.filename.read_text()

        json_data = json.loads(file_data)

        reset = False if set_default else True
        data.update_data(**json_data, locale=locale, reset_storage=reset)

        _client_logger.info((f"load data from file {filename} for "
                             f"locale {data.locale.locale_code}"))

        return cls(data)

    def to_json_file(self, filename=None, indent=4):
        _client_logger.warn("to_json_file is deprecated. use to_file instead.")
        if filename:
            filename = Storage(filename=filename).filename
        elif self.filename:
            filename = Storage(filename=self.filename).filename
        else:
            raise ValueError("No filename provided")

        body = {"login_cookies": self.login_cookies,
                "adp_token": self.adp_token,
                "access_token": self.access_token,
                "refresh_token": self.refresh_token,
                "device_private_key": self.device_private_key,
                "expires": self.expires,
                "locale_code": self.locale.locale_code}
        filename.write_text(json.dumps(body, indent=indent))

    def to_file(self, filename=None, password=None, encryption="default",
                indent=4, set_default=True, **kwargs):

        filename = filename or self.filename
        if not filename:
            raise ValueError("No filename provided")

        encryption = encryption if encryption != "default" else self.encryption

        if encryption is None:
            raise ValueError("No encryption provided")

        data = Storage(filename=filename, encryption=encryption)
        
        body = {"login_cookies": self.login_cookies,
                "adp_token": self.adp_token,
                "access_token": self.access_token,
                "refresh_token": self.refresh_token,
                "device_private_key": self.device_private_key,
                "expires": self.expires,
                "locale_code": self.locale.locale_code}
        json_body = json.dumps(body, indent=indent)

        if data.encryption is False:
            data.filename.write_text(json_body)
        else:
            if password:
                data.update_data(crypter=AESCipher(password, **kwargs))
            elif self.crypter:
                data.update_data(crypter=self.crypter)
            else:
                raise ValueError("No password provided")

            data.crypter.to_file(json_body, filename=data.filename,
                                 encryption=encryption, indent=indent)

        if set_default:
            self._data.update_data(**data)

    def re_login(self, username, password, captcha_callback=None,
                 otp_callback=None):

        login = auth_login(username,
                           password,
                           self.locale,
                           captcha_callback=captcha_callback,
                           otp_callback=otp_callback)

        self._data.update_data(**login)

    def register_device(self):
        register = auth_register(access_token=self.access_token,
                                 login_cookies=self.login_cookies,
                                 locale=self.locale)

        self._data.update_data(**register)

    def deregister_device(self):
        return auth_deregister(access_token=self.access_token,
                               login_cookies=self.login_cookies,
                               locale=self.locale)

    def refresh_access_token(self, force=False):
        if force or self.access_token_expired:
            refresh_data = refresh_access_token(
                refresh_token=self.refresh_token,
                locale=self.locale
            )
    
            self._data.update_data(**refresh_data)
        else:
            print("Access Token not expired. No refresh nessessary. "
                  "To force refresh please use force=True")

    def refresh_or_register(self, force=False):
        try:
            self.refresh_access_token(force=force)
        except:
            try:
                self.auth_deregister()
                self.auth_register()
            except:
                raise Exception("Could not refresh client.")

    def user_profile(self):
        return user_profile(access_token=self.access_token,
                            login_cookies=self.login_cookies,
                            locale=self.locale)

    @property
    def access_token_expires(self):
        return datetime.fromtimestamp(self.expires) - datetime.utcnow()

    @property
    def access_token_expired(self):
        if datetime.fromtimestamp(self.expires) <= datetime.utcnow():
            return True
        else:
            return False

    def _api_request(self, method, path, api_version="1.0", json_data=None,
                     auth=None, cookies=None, **params):
        url = "/".join((self.locale.audible_api, api_version, path))
        headers = {"Accept": "application/json",
                   "Content-Type": "application/json"}
        auth = auth or CertAuth(self.adp_token, self.device_private_key)
        resp = requests.request(method,
                                url,
                                json=json_data,
                                params=params,
                                headers=headers,
                                auth=auth,
                                cookies=cookies)
        resp.raise_for_status()

        return resp.json()

    def get(self, path, **params):
        return self._api_request("GET", path, **params)

    def post(self, path, body, **params):
        return self._api_request("POST", path, json_data=body, **params)

    def delete(self, path, **params):
        return self._api_request("DELETE", path, **params)
