from datetime import datetime
import json

import requests

from .localization import Markets
from .utils import Storage
from .auth import (auth_login, auth_register, auth_deregister,
                   CertAuth, refresh_access_token, user_profile)


class Client:
    def __init__(self, **kwargs):
        self._data = kwargs.get("data", None) or Storage(**kwargs)
        # rejected_kwargs = self._data.last_rejected_data

    def __getattr__(self, attr):
        try:
            return getattr(self._data, attr)
        except AttributeError:
            try:
                return super().__getattr__(attr)
            except AttributeError:
                return None

    def __getitem__(self, item):
        try:
            return getattr(self._data, item)
        except AttributeError:
            raise KeyError('No such key: {}'.format(item))

    @classmethod
    def from_login(cls, username, password, market, filename=None,
                   register=True, captcha_callback=None, otp_callback=None):
        data = Storage(market=market, filename=filename)

        response = auth_login(
            username,
            password,
            data.market,
            captcha_callback=captcha_callback,
            otp_callback=otp_callback
        )
        if register:
            response = auth_register(**response, market=data.market)

        data.update_data(**response)

        return cls(data=data)

    @classmethod
    def from_json_file(cls, filename, market=None):
        data = Storage(market=market, filename=filename)

        json_data = json.loads(data.filename.read_text())

        data.update_data(**json_data)

        return cls(data=data)

    def to_json_file(self, filename=None, indent=4):
        if filename:
            filename = Storage(filename=filename).filename
        elif self.filename:
            filename = Storage(filename=self.filename).filename
        else:
            raise ValueError("No filename provided")

        body = {
            "login_cookies": self.login_cookies,
            "adp_token": self.adp_token,
            "access_token": self.access_token,
            "refresh_token": self.refresh_token,
            "device_private_key": self.device_private_key,
            "expires": self.expires,
            "market_code": self.market.market_code
        }
        filename.write_text(json.dumps(body, indent=indent))

    def re_login(self, username, password, captcha_callback=None,
                 otp_callback=None):
        login = auth_login(
            username,
            password,
            self.market,
            captcha_callback=captcha_callback,
            otp_callback=otp_callback
        )

        self._data.update_data(**login)

    def register_device(self):
        register = auth_register(
            access_token=self.access_token,
            login_cookies=self.login_cookies,
            market=self.market
        )

        self._data.update_data(**register)

    def deregister_device(self):
        return auth_deregister(
            access_token=self.access_token,
            login_cookies=self.login_cookies,
            market=self.market
        )

    def refresh_access_token(self, force=False):
        if force or self.access_token_expired:
            refresh_data = refresh_access_token(
                refresh_token=self.refresh_token,
                market=self.market
            )
    
            self._data.update_data(**refresh_data)
        else:
            print("Access Token not expired. No refresh nessessary. To force refresh please use force=True")

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
        return user_profile(
            access_token=self.access_token,
            login_cookies=self.login_cookies,
            market=self.market
        )

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
        url = "/".join((self.market.audible_api, api_version, path))
        headers = {
            "Accept": 'application/json',
            'Content-Type': 'application/json'
        }
        auth = auth or CertAuth(self.adp_token, self.device_private_key)
        resp = requests.request(
            method,
            url,
            json=json_data,
            params=params,
            headers=headers,
            auth=auth,
            cookies=cookies
        )
        resp.raise_for_status()

        return resp.json()

    def get(self, path, **params):
        return self._api_request("GET", path, **params)

    def post(self, path, body, **params):
        return self._api_request("POST", path, json_data=body, **params)

    def delete(self, path, **params):
        return self._api_request("DELETE", path, **params)
