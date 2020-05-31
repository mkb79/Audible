import base64
import binascii
from datetime import datetime
import io
import json
import math
from typing import Any, Dict, List, Union
from urllib.parse import urlencode, parse_qs

from bs4 import BeautifulSoup
from PIL import Image
import requests


USER_AGENT = ("Mozilla/5.0 (iPhone; CPU iPhone OS 12_3_1 like Mac OS X) "
              "AppleWebKit/605.1.15 (KHTML, like Gecko) Mobile/15E148")


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


def default_cvf_callback() -> str:
    """
    Helper function for handling cvf verifys.
    Amazon sends a verify code via Mail or SMS.
    """
    guess = input("CVF Code: ")
    return str(guess).strip().lower()


def get_soup(resp):
    return BeautifulSoup(resp.text, "html.parser")


def get_inputs_from_soup(soup) -> Dict[str, str]:
    inputs = {}
    for node in soup.select("input[type=hidden]"):
        if node["name"] and node["value"]:
            inputs[node["name"]] = node["value"]
    return inputs


def build_oauth_url(countryCode: str, domain: str, marketPlaceId: str) -> str:
    oauth_params = {
        "openid.oa2.response_type": "token",
        "openid.return_to": f"https://www.amazon.{domain}/ap/maplanding",
        "openid.assoc_handle": f"amzn_audible_ios_{countryCode}",
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
        "openid.ns.pape": "http://specs.openid.net/extensions/pape/1.0",
        "marketPlaceId": marketPlaceId,
        "openid.oa2.scope": "device_auth_access",
        "forceMobileLayout": "true",
        "openid.ns": "http://specs.openid.net/auth/2.0",
        "openid.pape.max_auth_age": "0"
    }
    
    return f"https://www.amazon.{domain}/ap/signin?{urlencode(oauth_params)}"


def check_for_captcha(soup):
    captcha = soup.find("img", alt=lambda x: x and "CAPTCHA" in x)
    return True if captcha else False


def extract_captcha_url(soup):
    captcha = soup.find("img", alt=lambda x: x and "CAPTCHA" in x)
    return captcha["src"] if captcha else None


def check_for_mfa(soup):
    mfa = soup.find("form", id=lambda x: x and "auth-mfa-form" in x)
    return True if mfa else False


def check_for_choice_mfa(soup):
    mfa_choice = soup.find("form", id="auth-select-device-form")
    return True if mfa_choice else False


def check_for_cvf(soup):
    cvf = soup.find("div", id="cvf-page-content")
    return True if cvf else False


def extract_cookies_from_session(session):
    cookies = dict()
    for cookie in session.cookies:
        cookies[cookie.name] = cookie.value.replace(r'"', r'')
    return cookies


def extract_token_from_url(url):
    parsed_url = parse_qs(url)
    return parsed_url["openid.oa2.access_token"][0]


def login(username: str, password: str, countryCode: str,
          domain: str, marketPlaceId: str, captcha_callback=None,
          otp_callback=None,
          cvf_callback=None) -> Dict[str, Any]:

    amazon_url = f"https://www.amazon.{domain}"
    sign_in_url = amazon_url + "/ap/signin"
    cvf_url = amazon_url + "/ap/cvf/verify"

    session = requests.Session()
    session.headers.update({"User-Agent": USER_AGENT})

    while "session-token" not in session.cookies:
        session.get(amazon_url)

    oauth_url = build_oauth_url(countryCode, domain, marketPlaceId)
    oauth_resp = session.get(oauth_url)
    oauth_soup = get_soup(oauth_resp)

    login_inputs = get_inputs_from_soup(oauth_soup)
    login_inputs["email"] = username
    login_inputs["password"] = password
    metadata = meta_audible_app(USER_AGENT, amazon_url)
    login_inputs["metadata1"] = encrypt_metadata(metadata)

    login_resp = session.post(sign_in_url, data=login_inputs)
    login_soup = get_soup(login_resp)

    # check for captcha
    while check_for_captcha(login_soup):
        captcha_url = extract_captcha_url(login_soup)
        if captcha_callback:
            guess = captcha_callback(captcha_url)
        else:
            guess = default_captcha_callback(captcha_url)

        inputs = get_inputs_from_soup(login_soup)
        inputs["guess"] = guess
        inputs["use_image_captcha"] = "true"
        inputs["use_audio_captcha"] = "false"
        inputs["showPasswordChecked"] = "false"
        inputs["email"] = username
        inputs["password"] = password

        login_resp = session.post(sign_in_url, data=inputs)
        login_soup = get_soup(login_resp)

    # check for choice mfa
    # https://www.amazon.de/ap/mfa/new-otp
    while check_for_choice_mfa(login_soup):
        inputs = get_inputs_from_soup(login_soup)
        for node in login_soup.select("div[data-a-input-name=otpDeviceContext]"):
            # auth-TOTP, auth-SMS, auth-VOICE
            if "auth-TOTP" in node["class"]:
                inp_node = node.find("input")
                inputs[inp_node["name"]] = inp_node["value"]

        login_resp = session.post(amazon_url + "/ap/mfa", data=inputs)
        login_soup = get_soup(login_resp)

    # check for mfa (otp_code)
    while check_for_mfa(login_soup):
        if otp_callback:
            otp_code = otp_callback()
        else:
            otp_code = default_otp_callback()

        inputs = get_inputs_from_soup(login_soup)
        inputs["otpCode"] = otp_code
        inputs["mfaSubmit"] = "Submit"
        inputs["rememberDevice"] = "false"

        login_resp = session.post(sign_in_url, data=inputs)
        login_soup = get_soup(login_resp)

    # check for cvf
    while check_for_cvf(login_soup):
        if cvf_callback:
            cvf_code = cvf_callback()
        else:
            cvf_code = default_cvf_callback()

        inputs = get_inputs_from_soup(login_soup)

        login_resp = session.post(cvf_url, data=inputs)
        login_soup = get_soup(login_resp)

        inputs = get_inputs_from_soup(login_soup)
        inputs["action"] = "code"
        inputs["code"] = cvf_code

        login_resp = session.post(cvf_url, data=inputs)
        login_soup = get_soup(login_resp)

    if login_resp.status_code != 404:
        raise Exception("Unable to login")

    access_token = extract_token_from_url(login_resp.url)
    login_cookies = extract_cookies_from_session(session)

    session.close()

    return {
        "access_token": access_token,
        "login_cookies": login_cookies
    }


# constants used for encrypt/decrypt metadata
WRAP_CONSTANT = 2654435769
CONSTANTS = [1888420705, 2576816180, 2347232058, 874813317]


def _data_to_int_list(data: Union[str, bytes]) -> List[int]:
    data_bytes = data.encode() if isinstance(data, str) else data
    data_list_int = []
    for i in range(0, len(data_bytes), 4):
        data_list_int.append(int.from_bytes(data_bytes[i:i+4], "little"))

    return data_list_int


def _list_int_to_bytes(data: List[int]) -> bytearray:
    data_list = data
    data_bytes = bytearray()
    for i in data_list:
        data_bytes += i.to_bytes(4, 'little')

    return data_bytes


def _encrypt_data(data: List[int]) -> List[int]:
    temp2 = data
    rounds = len(temp2)
    minor_rounds = int(6 + (52 / rounds // 1))
    last = temp2[-1]
    inner_roll = 0

    for _ in range(minor_rounds):
        inner_roll += WRAP_CONSTANT
        inner_variable = inner_roll >> 2 & 3

        for i in range(rounds):
            first = temp2[(i + 1) % rounds]
            temp2[i] += ((last >> 5 ^ first << 2)
                         + (first >> 3 ^ last << 4) ^ (inner_roll ^ first)
                         + (CONSTANTS[i & 3 ^ inner_variable] ^ last))
            last = temp2[i] = temp2[i] & 0xffffffff

    return temp2


def _decrypt_data(data: List[int]) -> List[int]:
    temp2 = data
    rounds = len(temp2)
    minor_rounds = int(6 + (52 / rounds // 1))
    inner_roll = 0

    for _ in range(minor_rounds + 1):
        inner_roll += WRAP_CONSTANT
        inner_variable = inner_roll >> 2 & 3

    for _ in range(minor_rounds):
        inner_roll -= WRAP_CONSTANT
        inner_variable = inner_roll >> 2 & 3

        for i in range(rounds):
            i = rounds - i - 1

            first = temp2[(i + 1) % rounds]
            last = temp2[(i - 1) % rounds]

            temp2[i] -= ((last >> 5 ^ first << 2)
                         + (first >> 3 ^ last << 4) ^ (inner_roll ^ first)
                         + (CONSTANTS[i & 3 ^ inner_variable] ^ last))
            last = temp2[i] = temp2[i] & 0xffffffff

    return temp2


def _generate_hex_checksum(data: str) -> str:
    checksum_int = binascii.crc32(data.encode()) & 0xffffffff
    return checksum_int.to_bytes(4, byteorder='big').hex().upper()


def encrypt_metadata(metadata: str) -> str:
    """
    Encrypts metadata to be used to log in to amazon.

    """
    checksum = _generate_hex_checksum(metadata)

    object_str = f"{checksum}#{metadata}"

    object_list_int = _data_to_int_list(object_str)

    object_list_int_enc = _encrypt_data(object_list_int)

    object_bytes = _list_int_to_bytes(object_list_int_enc)

    object_base64 = base64.b64encode(object_bytes)

    return f"ECdITeCs:{object_base64.decode()}"


def decrypt_metadata(metadata: str) -> str:
    """Decrypt metadata. For testing purposes only."""
    object_base64 = metadata.lstrip("ECdITeCs:")

    object_bytes = base64.b64decode(object_base64)

    object_list_int = _data_to_int_list(object_bytes)

    object_list_int_dec = _decrypt_data(object_list_int)

    object_bytes = _list_int_to_bytes(object_list_int_dec).rstrip(b"\0")

    object_str = object_bytes.decode()

    checksum, metadata = object_str.split("#", 1)

    assert _generate_hex_checksum(metadata) == checksum

    return metadata


def now_to_unix_ms() -> int:
    return math.floor(datetime.now().timestamp()*1000)


def meta_audible_app(user_agent: str, oauth_url: str) -> str:
    """
    Returns json-formatted metadata to simulate sign-in from iOS audible app.
    """

    meta_dict = {
        "start": now_to_unix_ms(),
        "interaction": {
            "keys": 0,
            "keyPressTimeIntervals": [],
            "copies": 0,
            "cuts": 0,
            "pastes": 0,
            "clicks": 0,
            "touches": 0,
            "mouseClickPositions": [],
            "keyCycles": [],
            "mouseCycles": [],
            "touchCycles": []
        },
        "version": "3.0.0",
        "lsUbid": "X39-6721012-8795219:1549849158",
        "timeZone": -6,
        "scripts": {
            "dynamicUrls": [
                ("https://images-na.ssl-images-amazon.com/images/I/"
                 "61HHaoAEflL._RC|11-BZEJ8lnL.js,01qkmZhGmAL.js,71qOHv6nKaL."
                 "js_.js?AUIClients/AudibleiOSMobileWhiteAuthSkin#mobile"),
                ("https://images-na.ssl-images-amazon.com/images/I/"
                 "21T7I7qVEeL._RC|21T1XtqIBZL.js,21WEJWRAQlL.js,31DwnWh8lFL."
                 "js,21VKEfzET-L.js,01fHQhWQYWL.js,51TfwrUQAQL.js_.js?"
                 "AUIClients/AuthenticationPortalAssets#mobile"),
                ("https://images-na.ssl-images-amazon.com/images/I/"
                 "0173Lf6yxEL.js?AUIClients/AuthenticationPortalInlineAssets"),
                ("https://images-na.ssl-images-amazon.com/images/I/"
                 "211S6hvLW6L.js?AUIClients/CVFAssets"),
                ("https://images-na.ssl-images-amazon.com/images/G/"
                 "01/x-locale/common/login/fwcim._CB454428048_.js")
            ],
            "inlineHashes": [
                -1746719145,
                1334687281,
                -314038750,
                1184642547,
                -137736901,
                318224283,
                585973559,
                1103694443,
                11288800,
                -1611905557,
                1800521327,
                -1171760960,
                -898892073
            ],
            "elapsed": 52,
            "dynamicUrlCount": 5,
            "inlineHashesCount": 13
        },
        "plugins": "unknown||320-568-548-32-*-*-*",
        "dupedPlugins": "unknown||320-568-548-32-*-*-*",
        "screenInfo": "320-568-548-32-*-*-*",
        "capabilities": {
            "js": {
                "audio": True,
                "geolocation": True,
                "localStorage": "supported",
                "touch": True,
                "video": True,
                "webWorker": True
            },
            "css": {
                "textShadow": True,
                "textStroke": True,
                "boxShadow": True,
                "borderRadius": True,
                "borderImage": True,
                "opacity": True,
                "transform": True,
                "transition": True
            },
            "elapsed": 1
        },
        "referrer": "",
        "userAgent": user_agent,
        "location": oauth_url,
        "webDriver": None,
        "history": {
            "length": 1
        },
        "gpu": {
            "vendor": "Apple Inc.",
            "model": "Apple A9 GPU",
            "extensions": []
        },
        "math": {
            "tan": "-1.4214488238747243",
            "sin": "0.8178819121159085",
            "cos": "-0.5753861119575491"
        },
        "performance": {
            "timing": {
                "navigationStart": now_to_unix_ms(),
                "unloadEventStart": 0,
                "unloadEventEnd": 0,
                "redirectStart": 0,
                "redirectEnd": 0,
                "fetchStart": now_to_unix_ms(),
                "domainLookupStart": now_to_unix_ms(),
                "domainLookupEnd": now_to_unix_ms(),
                "connectStart": now_to_unix_ms(),
                "connectEnd": now_to_unix_ms(),
                "secureConnectionStart": now_to_unix_ms(),
                "requestStart": now_to_unix_ms(),
                "responseStart": now_to_unix_ms(),
                "responseEnd": now_to_unix_ms(),
                "domLoading": now_to_unix_ms(),
                "domInteractive": now_to_unix_ms(),
                "domContentLoadedEventStart": now_to_unix_ms(),
                "domContentLoadedEventEnd": now_to_unix_ms(),
                "domComplete": now_to_unix_ms(),
                "loadEventStart": now_to_unix_ms(),
                "loadEventEnd": now_to_unix_ms()
            }
        },
        "end": now_to_unix_ms(),
        "timeToSubmit": 108873,
        "form": {
            "email": {
                "keys": 0,
                "keyPressTimeIntervals": [],
                "copies": 0,
                "cuts": 0,
                "pastes": 0,
                "clicks": 0,
                "touches": 0,
                "mouseClickPositions": [],
                "keyCycles": [],
                "mouseCycles": [],
                "touchCycles": [],
                "width": 290,
                "height": 43,
                "checksum": "C860E86B",
                "time": 12773,
                "autocomplete": False,
                "prefilled": False
            },
            "password": {
                "keys": 0,
                "keyPressTimeIntervals": [],
                "copies": 0,
                "cuts": 0,
                "pastes": 0,
                "clicks": 0,
                "touches": 0,
                "mouseClickPositions": [],
                "keyCycles": [],
                "mouseCycles": [],
                "touchCycles": [],
                "width": 290,
                "height": 43,
                "time": 10353,
                "autocomplete": False,
                "prefilled": False
            }
        },
        "canvas": {
            "hash": -373378155,
            "emailHash": -1447130560,
            "histogramBins": []
        },
        "token": None,
        "errors": [],
        "metrics": [
            {
                "n": "fwcim-mercury-collector",
                "t": 0
            },
            {
                "n": "fwcim-instant-collector",
                "t": 0
            },
            {
                "n": "fwcim-element-telemetry-collector",
                "t": 2
            },
            {
                "n": "fwcim-script-version-collector",
                "t": 0
            },
            {
                "n": "fwcim-local-storage-identifier-collector",
                "t": 0
            },
            {
                "n": "fwcim-timezone-collector",
                "t": 0
            },
            {
                "n": "fwcim-script-collector",
                "t": 1
            },
            {
                "n": "fwcim-plugin-collector",
                "t": 0
            },
            {
                "n": "fwcim-capability-collector",
                "t": 1
            },
            {
                "n": "fwcim-browser-collector",
                "t": 0
            },
            {
                "n": "fwcim-history-collector",
                "t": 0
            },
            {
                "n": "fwcim-gpu-collector",
                "t": 1
            },
            {
                "n": "fwcim-battery-collector",
                "t": 0
            },
            {
                "n": "fwcim-dnt-collector",
                "t": 0
            },
            {
                "n": "fwcim-math-fingerprint-collector",
                "t": 0
            },
            {
                "n": "fwcim-performance-collector",
                "t": 0
            },
            {
                "n": "fwcim-timer-collector",
                "t": 0
            },
            {
                "n": "fwcim-time-to-submit-collector",
                "t": 0
            },
            {
                "n": "fwcim-form-input-telemetry-collector",
                "t": 4
            },
            {
                "n": "fwcim-canvas-collector",
                "t": 2
            },
            {
                "n": "fwcim-captcha-telemetry-collector",
                "t": 0
            },
            {
                "n": "fwcim-proof-of-work-collector",
                "t": 1
            },
            {
                "n": "fwcim-ubf-collector",
                "t": 0
            },
            {
                "n": "fwcim-timer-collector",
                "t": 0
            }
        ]
    }
    return json.dumps(meta_dict, separators=(',', ':'))
