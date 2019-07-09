import base64
from datetime import datetime, timedelta
import io
import logging
from typing import Any, Dict, Union
from urllib.parse import parse_qs, urlparse

from bs4 import BeautifulSoup
from PIL import Image
import requests
from requests.auth import AuthBase
import rsa


from .crypto import encrypt_metadata, meta_audible_app
from .localization import Markets


_auth_logger = logging.getLogger('audible.auth')


def auth_login(username: str, password: str, market: Markets,
               captcha_callback=None, otp_callback=None) -> Dict[str, Any]:
    """
    Login to amazon oauth service simulating audible app for iOS.
    Returns access token and cookies needed for ``auth_register``.
    """

    session = requests.Session()
    headers = {"Accept": ("text/html,application/xhtml+xml,"
                          "application/xml;q=0.9,*/*;q=0.8"),
               "Accept-Charset": "utf-8",
               "Accept-Language": market.accept_language,
               "Host": urlparse(market.amazon_login).netloc,
               "Origin": market.amazon_login,
               "User-Agent": ("Mozilla/5.0 (iPhone; CPU iPhone OS 12_3_1 "
                              "like Mac OS X) AppleWebKit/605.1.15 "
                              "(KHTML, like Gecko) Mobile/15E148")}
    session.headers.update(headers)

    while "session-token" not in session.cookies:
        session.get(market.amazon_login)

    oauth_params = {"openid.oa2.response_type": "token",
                    "openid.return_to": market.amazon_login + "/ap/maplanding",
                    "openid.assoc_handle": market.openid_assoc_handle,
                    "openid.identity": ("http://specs.openid.net/auth/2.0/"
                                        "identifier_select"),
                    "pageId": "amzn_audible_ios",
                    "accountStatusPolicy": "P1",
                    "openid.claimed_id": ("http://specs.openid.net/auth/2.0/"
                                          "identifier_select"),
                    "openid.mode": "checkid_setup",
                    "openid.ns.oa2": "http://www.amazon.com/ap/ext/oauth/2",
                    "openid.oa2.client_id": ("device:6a52316c62706d53427a57355"
                                             "05a76477a45375959566674327959465"
                                             "a6374424a53497069546d45234132435"
                                             "a4a5a474c4b324a4a564d"),
                    "language": market.oauth_lang,
                    "openid.ns.pape": ("http://specs.openid.net/extensions/"
                                       "pape/1.0"),
                    "marketPlaceId": market.marketPlaceId,
                    "openid.oa2.scope": "device_auth_access",
                    "forceMobileLayout": "true",
                    "openid.ns": "http://specs.openid.net/auth/2.0",
                    "openid.pape.max_auth_age": "0"}

    response = session.get(market.amazon_login + "/ap/signin",
                           params=oauth_params)
    oauth_url = response.request.url

    body = BeautifulSoup(response.text, "html.parser")

    inputs = {}
    for node in body.select("input[type=hidden]"):
        if node["name"] and node["value"]:
            inputs[node["name"]] = node["value"]
    inputs["email"] = username
    inputs["password"] = password

    metadata = meta_audible_app(session.headers.get("User-Agent"), oauth_url)
    inputs["metadata1"] = encrypt_metadata(metadata)

    session.headers.update(
        {"Referer": oauth_url,
         "Content-Type": "application/x-www-form-urlencoded"}
    )
    response = session.post(market.amazon_login + "/ap/signin", data=inputs)

    # check for captcha
    body = BeautifulSoup(response.text, "html.parser")
    captcha = body.find("img", alt=lambda x: x and "CAPTCHA" in x)

    while captcha:
        captcha_url = captcha["src"]
        if captcha_callback is None:
            guess = default_captcha_callback(captcha_url)
        else:
            guess = captcha_callback(captcha_url)

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

        response = session.post(market.amazon_login + "/ap/signin",
                                data=inputs)

        body = BeautifulSoup(response.text, "html.parser")
        captcha = body.find("img", alt=lambda x: x and "CAPTCHA" in x)

    # check for 2FA
    body = BeautifulSoup(response.text, "html.parser")
    mfa = body.find("form", id=lambda x: x and "auth-mfa-form" in x)

    while mfa:
        if otp_callback is None:
            otp_code = default_otp_callback()
        else:
            otp_code = otp_callback()

        inputs = {}
        for node in body.select("input[type=hidden]"):
            if node["name"] and node["value"]:
                inputs[node["name"]] = node["value"]
        inputs["otpCode"] = otp_code
        inputs["mfaSubmit"] = "Submit"
        inputs["rememberDevice"] = "false"

        response = session.post(market.amazon_login + "/ap/signin",
                                data=inputs)

        body = BeautifulSoup(response.text, "html.parser")
        mfa = body.find("form", id=lambda x: x and "auth-mfa-form" in x)

    # check for cvf identity check
    body = BeautifulSoup(response.text, "html.parser")
    cvf = body.find("div", id="cvf-page-content")

    if cvf:
        inputs = {}
        for node in body.select('input[type=hidden]'):
            if node["name"] and node["value"]:
                inputs[node["name"]] = node["value"]
        headers = {"Content-Type": "application/x-www-form-urlencoded",
                   "Referer": response.url}
        response = session.post(market.amazon_login + "/ap/cvf/verify",
                                headers=headers, data=inputs)

        body = BeautifulSoup(response.text, "html.parser")
        inputs = {}
        for node in body.select('input[type=hidden]'):
            if node["name"] and node["value"]:
                inputs[node["name"]] = node["value"]
        headers = {"Content-Type": "application/x-www-form-urlencoded",
                   "Referer": response.url}
        inputs["action"] = "code"
        inputs["code"] = input("Code: ")
        response = session.post(market.amazon_login + "/ap/cvf/verify",
                                headers=headers, data=inputs)

    if response.status_code != 404:
        raise Exception("Unable to login")

    map_landing = parse_qs(response.url)
    access_token = map_landing["openid.oa2.access_token"][0]

    login_cookies = dict()
    for cookie in session.cookies:
        login_cookies[cookie.name] = cookie.value.replace(r'"', r'')

    login_credentials = {"access_token": access_token,
                         "login_cookies": login_cookies}

    return login_credentials


def default_captcha_callback(captcha_url: str) -> str:
    """Helper function for handling captcha."""
    # on error print captcha url instead of display captcha
    try:
        captcha = requests.get(captcha_url).content
        f = io.BytesIO(captcha)
        img = Image.open(f)
        img.show()
    except:
        print(captcha_url)

    guess = input("Answer for CAPTCHA: ")
    return str(guess).strip().lower()


def default_otp_callback() -> str:
    """Helper function for handling 2-factor authentication."""
    guess = input("OTP Code: ")
    return str(guess).strip().lower()


def auth_register(access_token: str, login_cookies: dict,
                  market: Markets) -> Dict[str, Any]:
    """
    Register a dummy audible device with access token and cookies
    from ``auth_login``.
    Returns important credentials needed for access audible api.
    """
    json_cookies = []
    for key, val in login_cookies.items():
        json_cookies.append({
            "Name": key,
            "Value": val.replace(r'"', r'')
        })

    json_object = {
        "requested_token_type": ["bearer", "mac_dms", "website_cookies"],
        "cookies": {
            "website_cookies": json_cookies,
            "domain": market.auth_register_domain
        },
        "registration_data": {
            "domain": "Device",
            "app_version": "3.7",
            "device_serial": "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA",
            "device_type": "A2CZJZGLK2JJVM",
            "device_name": ("%FIRST_NAME%%FIRST_NAME_POSSESSIVE_STRING%%DUPE_"
                            "STRATEGY_1ST%Audible for iPhone"),
            "os_version": "12.3.1",
            "device_model": "iPhone",
            "app_name": "Audible"
        },
        "auth_data": {
            "access_token": access_token
        },
        "requested_extensions": ["device_info", "customer_info"]
    }

    headers = {
        "Host": urlparse(market.amazon_api).netloc,
        "Content-Type": "application/json",
        "Accept-Charset": "utf-8",
        "x-amzn-identity-auth-domain": urlparse(market.amazon_api).netloc,
        "Accept": "application/json",
        "User-Agent": "AmazonWebView/Audible/3.7/iOS/12.3.1/iPhone",
        "Accept-Language": market.accept_language
    }

    response = requests.post(market.amazon_api + "/auth/register",
                             json=json_object, headers=headers,
                             cookies=login_cookies)

    body = response.json()
    if response.status_code != 200:
        raise Exception(body)

    tokens = body["response"]["success"]["tokens"]

    adp_token = tokens["mac_dms"]["adp_token"]
    device_private_key = tokens["mac_dms"]["device_private_key"]

    access_token = tokens["bearer"]["access_token"]
    refresh_token = tokens["bearer"]["refresh_token"]
    expires_s = int(tokens["bearer"]["expires_in"])
    expires = (datetime.utcnow() + timedelta(seconds=expires_s)).timestamp()

    login_cookies_new = dict()
    for cookie in tokens["website_cookies"]:
        login_cookies_new[cookie["Name"]] = cookie["Value"].replace(r'"', r'')

    register_credentials = {"adp_token": adp_token,
                            "device_private_key": device_private_key,
                            "access_token": access_token,
                            "refresh_token": refresh_token,
                            "expires": expires,
                            "login_cookies": login_cookies_new}

    return register_credentials


def auth_deregister(access_token: str, login_cookies: dict,
                    market: Markets) -> Dict[str, Any]:
    """Deregister any device."""
    json_object = {"deregister_all_existing_accounts": "true"}
    headers = {
        "Host": urlparse(market.amazon_api).netloc,
        "Content-Type": "application/x-www-form-urlencoded",
        "Accept-Charset": "utf-8",
        "x-amzn-identity-auth-domain": urlparse(market.amazon_api).netloc,
        "Accept": "application/json",
        "User-Agent": "AmazonWebView/Audible/3.7/iOS/12.3.1/iPhone",
        "Accept-Language": market.accept_language,
        "Authorization": f"Bearer {access_token}"
    }

    response = requests.post(market.amazon_api + "/auth/deregister",
                             json=json_object, headers=headers,
                             cookies=login_cookies)

    body = response.json()
    if response.status_code != 200:
        raise Exception(body)

    return body


def refresh_access_token(refresh_token: str, market: Markets) -> Dict[str, Any]:
    """
    Refresh access token with refresh token. Access tokens are valid for 60 mins.
    
    """
    
    body = {"app_name": "Audible",
            "app_version": "3.7",
            "source_token": refresh_token,
            "requested_token_type": "access_token",
            "source_token_type": "refresh_token"}

    headers = {
        "Content-Type": "application/x-www-form-urlencoded",
        "x-amzn-identity-auth-domain": urlparse(market.amazon_api).netloc
    }

    response = requests.post(market.amazon_api + "/auth/token",
                             data=body, headers=headers)

    body = response.json()
    if response.status_code != 200:
        raise Exception(body)

    expires_in = int(body["expires_in"])
    expires = (datetime.utcnow() + timedelta(seconds=expires_in)).timestamp()
    refresh_result = {"access_token": body["access_token"],
                      "expires": expires}

    return refresh_result


def user_profile(access_token: str, login_cookies: dict,
                 market: Markets) -> Dict[str, Any]:
    """Returns user profile."""

    headers = {"Host": urlparse(market.amazon_api).netloc,
               "Accept-Charset": "utf-8",
               "User-Agent": "AmazonWebView/Audible/3.7/iOS/12.3.1/iPhone",
               "Accept-Language": market.accept_language,
               "Authorization": f"Bearer {access_token}"}

    response = requests.get(market.amazon_api + "/user/profile",
                            headers=headers, cookies=login_cookies)
    response.raise_for_status()

    return response.json()


class CertAuth(AuthBase):
    def __init__(self, adp_token: str, device_cert: str):
        self.adp_token = adp_token
        self.device_cert = device_cert

    def __call__(self, r):
        parsed_url = urlparse(r.url)
        path = parsed_url.path
        query = parsed_url.query

        if query:
            path += f"?{query}"

        headers = sign_request(path, r.method, r.body,
                               self.adp_token, self.device_cert)
        for item in headers:
            r.headers[item] = headers[item]

        return r


def sign_request(url: str, method: str, body: str, adp_token: str,
                 private_key: str) -> Dict[str, str]:
    """
    Helper function who creates a signed header for requests.

    :param url: the requested url
    :param method: the request method (GET, POST, DELETE, ...)
    :param body: the http message body
    :param adp_token: the token is obtained after register as device
    :param private_key: the rsa key obtained after register as device
    """
    date = datetime.utcnow().isoformat("T") + "Z"

    data = f"{method}\n{url}\n{date}\n"
    if body:
        data += body
    data += "\n"
    data += adp_token

    key = rsa.PrivateKey.load_pkcs1(private_key)
    cipher = rsa.pkcs1.sign(data.encode(), key, "SHA-256")
    signed_encoded = base64.b64encode(cipher)

    signature = f"{signed_encoded.decode()}:{date}"

    return {"x-adp-token": adp_token,
            "x-adp-alg": "SHA256withRSA:1.0",
            "x-adp-signature": signature}


class AccessTokenAuth(AuthBase):
    def __init__(self, access_token: str, client_id: Union[int, str]=0):
        self.access_token = access_token
        self.client_id = client_id

    def __call__(self, r):
        r.headers["Authorization"] = f"Bearer {self.access_token}"
        r.headers["client-id"] = self.client_id

        return r
