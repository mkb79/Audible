from datetime import datetime, timedelta
import io
import json
import urllib.request

from bs4 import BeautifulSoup
from PIL import Image
import requests

from .crypto import encrypt_metadata, meta_audible_app, CertAuth
from .localization import localization


class Client:
    def __init__(self, username=None, password=None, filename=None, local="us"):
        self._local = localization.get(local)

        self._login_cookies = {}
        self._adp_token = str()
        self._access_token = str()
        self._refresh_token = str()
        self._device_private_key = str()
        self._expires = 0

        if (username and password):
            self.init_session(username, password)
            self.auth_register()
            if filename:
                self.to_json_file(filename)
                self.filename = filename

        elif filename:
            self.from_json_file(filename)
            self.filename = filename   

    @property
    def login_cookies(self):
        return self._login_cookies

    @property
    def adp_token(self):
        return self._adp_token

    @property
    def access_token(self):
        return self._access_token

    @property
    def refresh_token(self):
        return self._refresh_token

    @property
    def device_private_key(self):
        return self._device_private_key

    @property
    def expires(self):
        return datetime.fromtimestamp(self._expires) - datetime.utcnow()

    def expired(self):
        if datetime.fromtimestamp(self._expires) <= datetime.utcnow():
            return True
        else:
            return False
   
    def from_json_file(self, filename=None):
        filename = filename or self.filename
        with open(filename, "r") as infile:
            body = json.load(infile)

        self._login_cookies = body["login_cookies"]
        self._adp_token = body["adp_token"]
        self._access_token = body["access_token"]
        self._refresh_token = body["refresh_token"]
        self._device_private_key = body["device_private_key"]
        self._expires = body["expires"]

    def to_json_file(self, filename=None, indent=4):
        filename = filename or self.filename

        body = {}
        body["login_cookies"] = self._login_cookies
        body["adp_token"] = self._adp_token
        body["access_token"] = self._access_token
        body["refresh_token"] = self._refresh_token
        body["device_private_key"] = self._device_private_key
        body["expires"] = self._expires

        with open(filename, "w") as outfile:
            json.dump(body, outfile, indent=indent)

    def init_session(self, username, password):
        timeout = 30
        session = requests.Session()
        session.headers.update(
            {
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                "Accept-Charset": "utf-8",
                "Accept-Language": self._local["Accept-Language"],
                "Host": self._local["AMAZON_LOGIN"].netloc,
                "Origin": self._local["AMAZON_LOGIN"].geturl(),
                "User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 12_3_1 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Mobile/15E148"
            }
        )

        while "session-token" not in session.cookies:
            session.get(self._local["AMAZON_LOGIN"].geturl(), timeout=timeout)

        oauth_params = {
            'openid.oa2.response_type': 'token',
            'openid.return_to': self._local["AMAZON_LOGIN"].geturl() + '/ap/maplanding',
            'openid.assoc_handle': self._local["openid_assoc_handle"],
            'openid.identity': 'http://specs.openid.net/auth/2.0/identifier_select',
            'pageId': 'amzn_audible_ios',
            'accountStatusPolicy': 'P1',
            'openid.claimed_id': 'http://specs.openid.net/auth/2.0/identifier_select',
            'openid.mode': 'checkid_setup',
            'openid.ns.oa2': 'http://www.amazon.com/ap/ext/oauth/2',
            'openid.oa2.client_id': 'device:6a52316c62706d53427a5735505a76477a45375959566674327959465a6374424a53497069546d45234132435a4a5a474c4b324a4a564d',
            'language': self._local["oauth_lang"],
            'openid.ns.pape': 'http://specs.openid.net/extensions/pape/1.0',
            'marketPlaceId': self._local["marketPlaceId"],
            'openid.oa2.scope': 'device_auth_access',
            'forceMobileLayout': 'true',
            'openid.ns': 'http://specs.openid.net/auth/2.0',
            'openid.pape.max_auth_age': '0'
        }
        response = session.get(self._local["AMAZON_LOGIN"].geturl() + "/ap/signin", params=oauth_params, timeout=timeout)
        oauth_url = response.request.url

        inputs = {}

        body = BeautifulSoup(response.text, "html.parser")
        for node in body.select("input[type=hidden]"):
            if node["name"] and node["value"]:
                inputs[node["name"]] = node["value"]
        inputs["email"] = username
        inputs["password"] = password

        metadata = meta_audible_app(session.headers.get("User-Agent"), oauth_url)
        inputs["metadata1"] = encrypt_metadata(metadata)

        session.headers.update(
            {
                "Referer": oauth_url,
                "Content-Type": "application/x-www-form-urlencoded"
            }
        )
        response = session.post(self._local["AMAZON_LOGIN"].geturl() + "/ap/signin", data=inputs, timeout=timeout)

        # check for captcha
        body = BeautifulSoup(response.text, "html.parser")
        captcha = body.find("img", alt=lambda x: x and "CAPTCHA" in x)

        while captcha:
            with urllib.request.urlopen(captcha["src"]) as url:
                f = io.BytesIO(url.read())

            # on error print captcha url instead of display captcha
            try:
                img = Image.open(f)
                img.show()
            except:
                print(captcha["src"])

            guess = input("Answer for CAPTCHA: ")
            guess = str(guess).strip().lower()

            inputs = {}
            for node in body.select("input[type=hidden]"):
                if node["name"] and node["value"]:
                    inputs[node["name"]] = node["value"]
            inputs["guess"] = guess
            inputs["use_image_captcha"] = "true"
            inputs["use_audio_captcha"] = "false"
            inputs["showPasswordChecked"] = "false"
            inputs["email"] = username
            inputs["password"] = password

            response = session.post(self._local["AMAZON_LOGIN"].geturl() + "/ap/signin", data=inputs, timeout=timeout)
        
            body = BeautifulSoup(response.text, "html.parser")
            captcha = body.find("img", alt=lambda x: x and "CAPTCHA" in x)

        # check for cvf identity check
        body = BeautifulSoup(response.text, "html.parser")
        cvf = body.find("div", id="cvf-page-content")

        if cvf:
            inputs = {}
            for node in body.select('input[type=hidden]'):
                if node["name"] and node["value"]:
                    inputs[node["name"]] = node["value"]
            headers = {
                "Content-Type": "application/x-www-form-urlencoded",
                "Referer": response.url
            }
            response = session.post(self._local["AMAZON_LOGIN"].geturl() + "/ap/cvf/verify", headers=headers, data=inputs, timeout=timeout)
    
            body = BeautifulSoup(response.text, "html.parser")
            inputs = {}
            for node in body.select('input[type=hidden]'):
                if node["name"] and node["value"]:
                    inputs[node["name"]] = node["value"]
            headers = {
                "Content-Type": "application/x-www-form-urlencoded",
                "Referer": response.url
            }
            inputs["action"] = "code"
            inputs["code"] = input("Code: ")
            response = session.post(self._local["AMAZON_LOGIN"].geturl() + "/ap/cvf/verify", headers=headers, data=inputs, timeout=timeout)

        if response.status_code != 404:
            raise Exception("Unable to login")

        map_landing = urllib.parse.parse_qs(response.url)
        self._access_token = map_landing["openid.oa2.access_token"][0]
        for cookie in session.cookies:
            self._login_cookies[cookie.name] = cookie.value

    def auth_register(self):
        json_cookies = []
        request_cookies = {}
        for key, val in self._login_cookies.items():
            json_cookies.append({
                "Name": key,
                "Value": val.replace(r'"', r'')
            })
            request_cookies[key] = val.replace(r'"', r'')

        json_object = {
            "requested_token_type": ["bearer", "mac_dms", "website_cookies"],
            "cookies": {
                "website_cookies": json_cookies,
                "domain": self._local["auth_register_domain"]
            },
            "registration_data": {
                "domain": "Device",
                "app_version": "3.7",
                "device_serial": "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA",
                "device_type": "A2CZJZGLK2JJVM",
                "device_name": "%FIRST_NAME%%FIRST_NAME_POSSESSIVE_STRING%%DUPE_STRATEGY_1ST%Audible for iPhone",
                "os_version": "12.3.1",
                "device_model": "iPhone",
                "app_name": "Audible"
            },
            "auth_data": {
                "access_token": self._access_token
            },
            "requested_extensions": ["device_info", "customer_info"]
        }

        headers = {
            "Host": self._local["AMAZON_API"].netloc,
            "Content-Type": "application/json",
            "Accept-Charset": "utf-8",
            "x-amzn-identity-auth-domain": self._local["AMAZON_API"].netloc,
            "Accept": "application/json",
            "User-Agent": "AmazonWebView/Audible/3.7/iOS/12.3.1/iPhone",
            "Accept-Language": self._local["Accept-Language"]
        }

        url = self._local["AMAZON_API"].geturl() + "/auth/register"
        response = requests.post(url, json=json_object, headers=headers, cookies=request_cookies)

        body = response.json()
        if response.status_code != 200:
            raise Exception(body)

        tokens = body["response"]["success"]["tokens"]

        self._adp_token = tokens["mac_dms"]["adp_token"]
        self._device_private_key = tokens["mac_dms"]["device_private_key"]

        self._access_token = tokens["bearer"]["access_token"]
        self._refresh_token = tokens["bearer"]["refresh_token"]
        self._expires = (datetime.utcnow() + timedelta(seconds=int(tokens["bearer"]["expires_in"]))).timestamp()

        website_cookies = tokens["website_cookies"]
        for cookie in website_cookies:
            self._login_cookies[cookie["Name"]] = cookie["Value"]

    def auth_deregister(self):
        json_object = {
            "deregister_all_existing_accounts": "true"
        }
        headers = {
            "Host": self._local["AMAZON_API"].netloc,
            "Content-Type": "application/x-www-form-urlencoded",
            "Accept-Charset": "utf-8",
            "x-amzn-identity-auth-domain": self._local["AMAZON_API"].netloc,
            "Accept": "application/json",
            "User-Agent": "AmazonWebView/Audible/3.7/iOS/12.3.1/iPhone",
            "Accept-Language": self._local["Accept-Language"],
            "Authorization": f"Bearer {self._access_token}"
        }        

        request_cookies = {}
        for key, val in self._login_cookies.items():
            request_cookies[key] = val.replace(r'"', r'')

        url = self._local["AMAZON_API"].geturl() + "/auth/deregister"
        response = requests.post(url, json=json_object, headers=headers, cookies=request_cookies)

        body = response.json()
        if response.status_code != 200:
            raise Exception(body)
        self._adp_token = str()
        self._refresh_token = str()
        self._expires = 0

    def refresh_access_token(self, force=False):
        if force or self.expired():
            body = {
                "app_name": "Audible",
                "app_version": "3.7",
                "source_token": self._refresh_token,
                "requested_token_type": "access_token",
                "source_token_type": "refresh_token"
            }
    
            headers = {
                "Content-Type": "application/x-www-form-urlencoded",
                "x-amzn-identity-auth-domain": self._local["AMAZON_API"].netloc
            }
    
            url = self._local["AMAZON_API"].geturl() + "/auth/token"
            response = requests.post(url, data=body, headers=headers)
    
            body = response.json()
            if response.status_code != 200:
                raise Exception(body)
            self._access_token = body["access_token"]
            self._expires = (datetime.utcnow() + timedelta(seconds=int(body["expires_in"]))).timestamp()

    def user_profile(self):
        headers = {
            "Host": self._local["AMAZON_API"].netloc,
            "Accept-Charset": "utf-8",
            "User-Agent": "AmazonWebView/Audible/3.7/iOS/12.3.1/iPhone",
            "Accept-Language": self._local["Accept-Language"],
            "Authorization": f"Bearer {self._access_token}"
        }

        request_cookies = {}
        for key, val in self._login_cookies.items():
            request_cookies[key] = val.replace(r'"', r'')

        url = self._local["AMAZON_API"].geturl() + "/user/profile"
        response = requests.get(url, headers=headers, cookies=request_cookies)

        return response.json()

    def refresh_or_register(self, force=False):
        try:
            self.refresh_access_token(force=force)
        except:
            try:
                self.auth_deregister()
                self.auth_register()
            except:
                raise Exception("Could not refresh client.")

    def _api_request(self, method, path, api_version="1.0", json_data=None, auth=None, cookies=None, **params):
        url = "/".join((self._local["AUDIBLE_API"].geturl(), api_version, path))
        headers = {
            "Accept": 'application/json',
            'Content-Type': 'application/json'
        }
        auth = CertAuth(self._adp_token, self._device_private_key)
        resp = requests.request(
            method, url, json=json_data, params=params, headers=headers, auth=auth, cookies=cookies
        )
        resp.raise_for_status()

        return resp.json()

    def get(self, path, **params):
        return self._api_request("GET", path, **params)

    def post(self, path, body, **params):
        return self._api_request("POST", path, json_data=body, **params)

    def delete(self, path, **params):
        return self._api_request("DELETE", path, **params)

