import base64
import io
import json
import logging
import re
import uuid
import secrets
from datetime import datetime, timedelta
from typing import Any, Callable, Dict, Optional, Tuple
from urllib.parse import urlencode, parse_qs

from bs4 import BeautifulSoup
from PIL import Image
import httpx

from .metadata import encrypt_metadata, meta_audible_app


logger = logging.getLogger("audible.login")

USER_AGENT = ("Mozilla/5.0 (iPhone; CPU iPhone OS 14_1 like Mac OS X) "
              "AppleWebKit/605.1.15 (KHTML, like Gecko) Mobile/15E148")


def default_captcha_callback(captcha_url: str) -> str:
    """Helper function for handling captcha."""
    # on error print captcha url instead of display captcha
    try:
        captcha = httpx.get(captcha_url).content
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
    """Helper function for handling cvf verifys.
    
    Amazon sends a verify code via Mail or SMS.
    """
    guess = input("CVF Code: ")
    return str(guess).strip().lower()


def default_approval_alert_callback() -> None:
    """Helper function for handling approval alerts."""
    print("Approval alert detected! Amazon sends you a mail.")
    input("Please press enter when you approve the notification.")


def default_login_url_callback(url: str) -> str:
    """Helper function for login with external browsers."""
    print("Please copy the following url and insert it in a webbrowser of "
          "your choice:")
    print("\n" + url + "\n")
    print("Now you have to login with your Amazon credentials. After submit "
          "your username and password you have to do this a second time "
          "and solving a captcha before sending the login form.\n")
    print("After login, your browser will show you a error page (not found). "
          "Do not worry about this. It has to be like this. Please copy the "
          "url from the address bar in your browser now.\n")
    print("IMPORTANT:")
    print("If you are using MacOS and have trouble insert the login result "
          "url, simply import the readline module in your script.\n")
    return input("Please insert the copied url (after login):\n")


def get_soup(resp):
    return BeautifulSoup(resp.text, "html.parser")


def get_inputs_from_soup(soup: BeautifulSoup) -> Dict[str, str]:
    """Extracts hidden form input fields from a Amazon login page."""
    inputs = {}
    for node in soup.select("input[type=hidden]"):
        if node.attrs.get("name") and node.attrs.get("value"):
            inputs[node["name"]] = node["value"]
    return inputs


def build_device_serial() -> str:
    return uuid.uuid4().hex.upper()


def build_client_id(serial: str) -> str:
    client_id = serial.encode() + b"#A2CZJZGLK2JJVM"
    return client_id.hex()


def build_oauth_url(
    country_code: str,
    domain: str,
    market_place_id: str,
    serial: Optional[str] = None,
    with_username=False
) -> Tuple[str, str]:
    """Builds the url to login to Amazon as an Audible device"""
    if with_username and domain.lower() not in ("de", "com", "co.uk"):
        raise ValueError("Login with username is only supported for DE, US "
                         "and UK marketplaces!")
        
    serial = serial or build_device_serial()
    client_id = build_client_id(serial)

    if with_username:
        base_url = f"https://www.audible.{domain}/ap/signin"
        return_to = f"https://www.audible.{domain}/ap/maplanding"
        assoc_handle = f"amzn_audible_ios_lap_{country_code}"
        page_id = "amzn_audible_ios_privatepool"
    else:
        base_url = f"https://www.amazon.{domain}/ap/signin"
        return_to = f"https://www.amazon.{domain}/ap/maplanding"
        assoc_handle = f"amzn_audible_ios_{country_code}"
        page_id = "amzn_audible_ios"

    oauth_params = {
        "openid.oa2.response_type": "token",
        "openid.return_to": return_to,
        "openid.assoc_handle": assoc_handle,
        "openid.identity": "http://specs.openid.net/auth/2.0/"
                           "identifier_select",
        "pageId": page_id,
        "accountStatusPolicy": "P1",
        "openid.claimed_id": "http://specs.openid.net/auth/2.0/"
                             "identifier_select",
        "openid.mode": "checkid_setup",
        "openid.ns.oa2": "http://www.amazon.com/ap/ext/oauth/2",
        "openid.oa2.client_id": f"device:{client_id}",
        "openid.ns.pape": "http://specs.openid.net/extensions/pape/1.0",
        "marketPlaceId": market_place_id,
        "openid.oa2.scope": "device_auth_access",
        "forceMobileLayout": "true",
        "openid.ns": "http://specs.openid.net/auth/2.0",
        "openid.pape.max_auth_age": "0"
    }

    return f"{base_url}?{urlencode(oauth_params)}", serial


def build_init_cookies() -> Dict[str, str]:
    """Build initial cookies to prevent captcha in most cases."""
    frc = secrets.token_bytes(313)
    frc = base64.b64encode(frc).decode("ascii").rstrip("=")

    map_md = {
        "device_user_dictionary": [],
        "device_registration_data": {
            "software_version": "33501644"
        },
        "app_identifier": {
            "app_version": "3.35.1",
            "bundle_id": "com.audible.iphone"
        }
    }
    map_md = json.dumps(map_md)
    map_md = base64.b64encode(map_md.encode()).decode().rstrip("=")

    amzn_app_id = "MAPiOSLib/6.0/ToHideRetailLink"

    return {"frc": frc, "map-md": map_md, "amzn-app-id": amzn_app_id}


def check_for_captcha(soup: BeautifulSoup) -> bool:
    """Checks a Amazon login page for a captcha form."""
    captcha = soup.find("img", alt=lambda x: x and "CAPTCHA" in x)
    return True if captcha else False


def extract_captcha_url(soup: BeautifulSoup) -> Optional[str]:
    """Returns the captcha url from a Amazon login page."""
    captcha = soup.find("img", alt=lambda x: x and "CAPTCHA" in x)
    return captcha["src"] if captcha else None


def check_for_mfa(soup: BeautifulSoup) -> bool:
    """Checks a Amazon login page for a multi-factor authentication form."""
    mfa = soup.find("form", id=lambda x: x and "auth-mfa-form" in x)
    return True if mfa else False


def check_for_choice_mfa(soup: BeautifulSoup) -> bool:
    """Checks a Amazon login page for a MFA selection form."""
    mfa_choice = soup.find("form", id="auth-select-device-form")
    return True if mfa_choice else False


def check_for_cvf(soup: BeautifulSoup) -> bool:
    cvf = soup.find("div", id="cvf-page-content")
    return True if cvf else False


def check_for_approval_alert(soup: BeautifulSoup) -> bool:
    """Checks a Amazon login page for an approval alert."""
    approval_alert = soup.find("div", id="resend-approval-alert")
    return True if approval_alert else False


def extract_cookies_from_session(session: httpx.Client) -> Dict[str, str]:
    """Extracts cookies from a httpx Client."""
    cookies = dict()
    for cookie in session.cookies.jar:
        cookies[cookie.name] = cookie.value.replace(r'"', r'')
    return cookies


def extract_token_from_url(url: httpx.URL) -> str:
    """Extracts the access token from url query after login."""
    parsed_url = parse_qs(url.query.decode())
    return parsed_url["openid.oa2.access_token"][0]


def is_valid_email(obj: str) -> bool:
    valid_mail = r"^[a-z0-9]+[\._]?[a-z0-9]+[@]\w+[.]\w+$"
    if re.match(valid_mail, obj):
        return True
    return False


def login(
    username: str,
    password: str,
    country_code: str,
    domain: str,
    market_place_id: str,
    serial: Optional[str] = None,
    with_username: bool = False,
    captcha_callback: Optional[Callable[[str], str]] = None,
    otp_callback: Optional[Callable[[], str]] = None,
    cvf_callback: Optional[Callable[[], str]] = None,
    approval_callback: Optional[Callable[[], Any]] = None
) -> Dict[str, Any]:
    """Login to Audible by simulating an Audible App for iOS.
    
    Args:
        username: The Amazon email address.
        password: The Amazon password.
        country_code: The country code for the Audible marketplace to login.
        domain: domain: The top level domain for the Audible marketplace to
            login.
        market_place_id: The id for the Audible marketplace to login.
        serial: The device serial. If ``None`` a custom one will be created.
        with_username: If ``True`` login with Audible username instead 
            of Amazon account.
        captcha_callback: A custom Callable for handling captcha requests. 
            If ``None`` :func:`default_captcha_callback` is used.
        otp_callback: A custom Callable for providing one-time passwords.
            If ``None`` :func:`default_otp_callback` is used.
        cvf_callback: A custom Callable for providing the answer for a CVF
            code. If ``None`` :func:`default_cvf_callback` is used.
        approval_callback: A custom Callable for handling approval alerts.
            If ``None`` :func:`default_approval_alert_callback` is used.
    
    Returns:
        An ``access_token`` with ``expires`` timestamp and the 
        ``website_cookies`` from the authorized Client.
    """
    if not with_username and not is_valid_email(username):
        raise ValueError("Username %s is not a valid mail address." % username)
    
    if with_username:
        base_url = f"https://www.audible.{domain}"
        logger.info("Login with Audible username.")                    
    else:
        base_url = f"https://www.amazon.{domain}"
        logger.info("Login with Amazon Account.")

    sign_in_url = base_url + "/ap/signin"
    cvf_url = base_url + "/ap/cvf/verify"
    mfa_url = base_url + "/ap/mfa"

    default_headers = {
        "User-Agent": USER_AGENT,
        "Accept-Language": "en-US",
        "Accept-Encoding": "gzip"
    }
    init_cookies = build_init_cookies()

    session = httpx.Client(headers=default_headers, cookies=init_cookies)

    while "session-token" not in session.cookies:
        session.get(base_url)

    oauth_url, serial = build_oauth_url(country_code=country_code,
                                        domain=domain,
                                        market_place_id=market_place_id,
                                        serial=serial,
                                        with_username=with_username)

    oauth_resp = session.get(oauth_url)
    oauth_soup = get_soup(oauth_resp)

    login_inputs = get_inputs_from_soup(oauth_soup)
    login_inputs["email"] = username
    login_inputs["password"] = password

    metadata = meta_audible_app(USER_AGENT, base_url)
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
        for node in login_soup.select(
            "div[data-a-input-name=otpDeviceContext]"
        ):
            # auth-TOTP, auth-SMS, auth-VOICE
            if "auth-TOTP" in node["class"]:
                inp_node = node.find("input")
                inputs[inp_node["name"]] = inp_node["value"]

        login_resp = session.post(mfa_url, data=inputs)
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

    # check for approval alert
    while check_for_approval_alert(login_soup):
        if approval_callback:
            approval_callback()
        else:
            default_approval_alert_callback()

        url = login_soup.find_all("a", class_="a-link-normal")[1]["href"]

        login_resp = session.get(url)
        login_soup = get_soup(login_resp)

    if login_resp.status_code != 404:
        raise Exception("Unable to login")

    access_token = extract_token_from_url(login_resp.url)
    website_cookies = extract_cookies_from_session(session)
    expires = (datetime.utcnow() + timedelta(seconds=3600)).timestamp()

    session.close()

    return {
        "access_token": access_token,
        "website_cookies": website_cookies,
        "expires": expires,
        "serial": serial
    }


def external_login(
    country_code: str,
    domain: str,
    market_place_id: str,
    serial: Optional[str] = None,
    with_username: bool = False,
    login_url_callback: Optional[Callable[[str], str]] = None
) -> Dict[str, Any]:
    """Gives the url to login with external browser and prompt for result.

    Note:
        If you are using MacOS and have trouble insert the login result url 
        simply import the readline module in your script. See
        `#34 <https://github.com/mkb79/Audible/issues/34#issuecomment-766408640>`_.
    
    Args:
        country_code: The country code for the Audible marketplace to login.
        domain: The top level domain for the Audible marketplace to
            login.
        market_place_id: The id for the Audible marketplace to login.
        serial: The device serial. If ``None`` a custom one will be created.
        with_username: If ``True`` login with Audible username instead 
            of Amazon account.
        login_url_callback: A custom Callable for handling login with external 
            browsers. If ``None`` :func:`default_login_url_callback` is used.

    Returns:
        An ``access_token`` with ``expires`` timestamp from the 
        authorized Client.
    """
    oauth_url, serial = build_oauth_url(country_code=country_code,
                                        domain=domain,
                                        market_place_id=market_place_id,
                                        serial=serial,
                                        with_username=with_username)

    if login_url_callback:
        response_url = login_url_callback(oauth_url)
    else:
        response_url = default_login_url_callback(oauth_url)

    response_url = httpx.URL(response_url)
    parsed_url = parse_qs(response_url.query.decode())

    access_token = parsed_url["openid.oa2.access_token"][0]

    auth_time = parsed_url["openid.pape.auth_time"][0]
    auth_time = datetime.strptime(auth_time, "%Y-%m-%dT%H:%M:%SZ")
    expires = (auth_time + timedelta(seconds=3600)).timestamp()

    return {
        "access_token": access_token,
        "expires": expires,
        "serial": serial
    }
