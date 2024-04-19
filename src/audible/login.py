import base64
import hashlib
import io
import json
import logging
import re
import secrets
import uuid
from collections.abc import Callable
from textwrap import dedent
from typing import Any
from urllib.parse import parse_qs, urlencode

import httpx
from bs4 import BeautifulSoup, NavigableString, Tag
from PIL import Image

from .metadata import encrypt_metadata, meta_audible_app


logger = logging.getLogger("audible.login")

USER_AGENT = (
    "OnePlus/OnePlus8/OnePlus8:11/RP1A.201005.001/2110102308:user/release-keys"
)


def default_captcha_callback(captcha_url: str) -> str:
    """Helper function for handling captcha."""
    captcha = httpx.get(captcha_url).content
    f = io.BytesIO(captcha)
    img = Image.open(f)
    img.show()
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
    input("Please press ENTER when you approve the notification.")


def playwright_external_login_url_callback(url: str) -> str:
    """Helper function for login using playwright."""
    from playwright.sync_api import sync_playwright  # type: ignore[import-not-found]  # noqa: I001

    with sync_playwright() as p:
        iphone = p.devices["iPhone 12 Pro"]
        browser = p.webkit.launch(headless=False)
        context = browser.new_context(**iphone)
        cookies = []
        for name, value in build_init_cookies().items():
            cookies.append({"name": name, "value": value, "url": url})
        context.add_cookies(cookies)
        page = browser.new_page()
        page.goto(url)

        while True:
            page.wait_for_timeout(600)
            if "/ap/maplanding" in page.url:
                response_url: str = page.url
                break

        browser.close()

    return response_url


def default_login_url_callback(url: str) -> str:
    """Helper function for login with external browsers."""
    try:
        return playwright_external_login_url_callback(url)
    except ImportError:
        pass

    message = f"""\
        Please copy the following url and insert it into a web browser of your choice:

        {url}

        Now you have to login with your Amazon credentials. After submit your username
        and password you have to do this a second time and solving a captcha before
        sending the login form.

        After login, your browser will show you an error page (Page not found). Do not
        worry about this. It has to be like this. Please copy the url from the address
        bar in your browser now.

        IMPORTANT:
        If you are using MacOS and have trouble insert the login result url, simply
        import the readline module in your script.

        Please insert the copied url (after login):
    """
    print(dedent(message))
    return input()


def _extract_message_from_box(box: Tag) -> str:
    message = ""

    header = box.find("h4")
    if isinstance(header, Tag) and header.string:
        message += header.string.strip()

    for list_item in box.find_all("li"):
        if isinstance(list_item, Tag) and isinstance(list_item.find("span"), Tag):
            list_entry = list_item.find("span")
            if isinstance(list_entry, Tag) and list_entry.string:
                message += " " + list_entry.string.strip()
    return message


def _get_messages_in_soup(soup: BeautifulSoup) -> dict[str, str]:
    messages = {}

    error_box = soup.find(id="auth-error-message-box")
    if isinstance(error_box, Tag):
        error_message = _extract_message_from_box(error_box)
        if error_message:
            messages["error"] = error_message

    warning_box = soup.find(id="auth-warning-message-box")
    if isinstance(warning_box, Tag):
        warning_message = _extract_message_from_box(warning_box)
        if warning_message:
            messages["warning"] = warning_message

    ap_error = soup.find(id="ap_error_page_message")
    if isinstance(ap_error, Tag):
        ap_error_message = ap_error.find(recursive=False, text=True)
        if isinstance(ap_error_message, NavigableString):
            messages["aperror"] = ap_error_message.strip()

    return messages


def get_soup(resp: httpx.Response, log_errors: bool = True) -> BeautifulSoup:
    soup = BeautifulSoup(resp.text, "html.parser")

    if log_errors:
        soup_messages = _get_messages_in_soup(soup)
        if "error" in soup_messages:
            logger.error("Error message: %s", soup_messages["error"])
        if "warning" in soup_messages:
            logger.warning("Warning message: %s", soup_messages["warning"])
        if "aperror" in soup_messages:
            logger.error("Error message: %s", soup_messages["aperror"])
    return soup


def get_inputs_from_soup(
    soup: BeautifulSoup, search_field: dict[str, str] | None = None
) -> dict[str, str]:
    """Extracts hidden form input fields from a Amazon login page."""
    search_field = search_field or {"name": "signIn"}
    form = soup.find("form", search_field) or soup.find("form")

    if not isinstance(form, Tag):
        raise Exception("No form found in page or something other is going wrong.")

    inputs = {}
    for field in form.find_all("input"):
        try:
            inputs[field["name"]] = ""
            if field["type"] and field["type"] == "hidden":
                inputs[field["name"]] = field["value"]
        except BaseException:  # noqa: S110
            pass
    return inputs


def get_next_action_from_soup(
    soup: BeautifulSoup, search_field: dict[str, str] | None = None
) -> tuple[str, str]:
    search_field = search_field or {"name": "signIn"}
    form = soup.find("form", search_field) or soup.find("form")

    if not isinstance(form, Tag):
        raise Exception("No form found in page or something other is going wrong.")

    method = form.get("method", "GET")
    url = form["action"]

    if not isinstance(method, str) or not isinstance(url, str):
        raise Exception("Error during extraction of next action in page.")

    return method, url


def create_code_verifier(length: int = 32) -> bytes:
    verifier = secrets.token_bytes(length)
    return base64.urlsafe_b64encode(verifier).rstrip(b"=")


def create_s256_code_challenge(verifier: bytes) -> bytes:
    m = hashlib.sha256(verifier)
    return base64.urlsafe_b64encode(m.digest()).rstrip(b"=")


def build_device_serial() -> str:
    return uuid.uuid4().hex.upper()


def build_client_id(serial: str) -> str:
    client_id = serial.encode() + b"#A10KISP2GWF0E4"
    return client_id.hex()


def build_oauth_url(
    country_code: str,
    domain: str,
    market_place_id: str,
    code_verifier: bytes,
    serial: str | None = None,
    with_username: bool = False,
) -> tuple[str, str]:
    """Builds the url to login to Amazon as an Audible device."""
    if with_username and domain.lower() not in ("de", "com", "co.uk"):
        raise ValueError(
            "Login with username is only supported for DE, US " "and UK marketplaces!"
        )

    serial = serial or build_device_serial()
    client_id = build_client_id(serial)
    code_challenge = create_s256_code_challenge(code_verifier)

    base_url = f"https://www.amazon.{domain}/ap/signin"
    return_to = f"https://www.amazon.{domain}/ap/maplanding"
    assoc_handle = f"amzn_audible_android_aui_{country_code}"
    page_id = f"amzn_audible_android_aui_{country_code}"

    if with_username:
        base_url = f"https://www.audible.{domain}/ap/signin"
        return_to = f"https://www.audible.{domain}/ap/maplanding"
        assoc_handle = f"amzn_audible_ios_lap_{country_code}"
        page_id = "amzn_audible_ios_privatepool"

    oauth_params = {
        "openid.oa2.response_type": "code",
        "openid.oa2.code_challenge_method": "S256",
        "openid.oa2.code_challenge": code_challenge,
        "openid.return_to": return_to,
        "openid.assoc_handle": assoc_handle,
        "openid.identity": "http://specs.openid.net/auth/2.0/" "identifier_select",
        "pageId": page_id,
        "accountStatusPolicy": "P1",
        "openid.claimed_id": "http://specs.openid.net/auth/2.0/" "identifier_select",
        "openid.mode": "checkid_setup",
        "openid.ns.oa2": "http://www.amazon.com/ap/ext/oauth/2",
        "openid.oa2.client_id": f"device:{client_id}",
        "openid.ns.pape": "http://specs.openid.net/extensions/pape/1.0",
        "marketPlaceId": market_place_id,
        "openid.oa2.scope": "device_auth_access",
        "forceMobileLayout": "true",
        "openid.ns": "http://specs.openid.net/auth/2.0",
        "openid.pape.max_auth_age": "0",
    }

    return f"{base_url}?{urlencode(oauth_params)}", serial


def build_init_cookies() -> dict[str, str]:
    """Build initial cookies to prevent captcha in most cases."""
    token_bytes = secrets.token_bytes(313)
    frc = base64.b64encode(token_bytes).decode("ascii").rstrip("=")

    map_md_dict = {
        "device_user_dictionary": [],
        "device_registration_data": {"software_version": "35602678"},
        "app_identifier": {"app_version": "3.56.2", "bundle_id": "com.audible.iphone"},
    }
    map_md_str = json.dumps(map_md_dict)
    map_md = base64.b64encode(map_md_str.encode()).decode().rstrip("=")

    amzn_app_id = "MAPiOSLib/6.0/ToHideRetailLink"

    return {"frc": frc, "map-md": map_md, "amzn-app-id": amzn_app_id}


def check_for_captcha(soup: BeautifulSoup) -> bool:
    """Checks a Amazon login page for a captcha form."""
    captcha = soup.find("img", alt=lambda x: x and "CAPTCHA" in x)
    return True if captcha else False


def extract_captcha_url(soup: BeautifulSoup) -> str:
    """Returns the captcha url from a Amazon login page."""
    captcha = soup.find("img", alt=lambda x: x and "CAPTCHA" in x)
    if not isinstance(captcha, Tag) or not isinstance(captcha["src"], str):
        raise Exception("Error during extracting the captcha url.")
    return captcha["src"]


def check_for_mfa(soup: BeautifulSoup) -> bool:
    """Checks a Amazon login page for a multi-factor authentication form."""
    mfa = soup.find(
        "form",
        id=lambda x: x and ("verification-code-form" in x or "auth-mfa-form" in x),
    )
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
    approval_alert = soup.find(id="resend-approval-alert") or soup.find(
        id="resend-approval-form"
    )
    return True if approval_alert else False


def extract_code_from_url(url: httpx.URL) -> str:
    """Extracts the access token from url query after login."""
    parsed_url = parse_qs(url.query.decode())
    return parsed_url["openid.oa2.authorization_code"][0]


def is_valid_email(obj: str) -> bool:
    valid_mail = r"^[a-z0-9]+[\._-]?[a-z0-9]+[@]\w+[.]\w+$"
    if re.match(valid_mail, obj):
        return True
    return False


def login(
    username: str,
    password: str,
    country_code: str,
    domain: str,
    market_place_id: str,
    serial: str | None = None,
    with_username: bool = False,
    captcha_callback: Callable[[str], str] | None = None,
    otp_callback: Callable[[], str] | None = None,
    cvf_callback: Callable[[], str] | None = None,
    approval_callback: Callable[[], Any] | None = None,
) -> dict[str, Any]:
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
        An ``authorization_code``, a ``code_verifier`` and the
        ``device serial`` from the authorized Client.

    Raises:
        Exception: If authorization_code is not in response url.
    """
    if with_username:
        base_url = f"https://www.audible.{domain}"
        logger.info("Login with Audible username.")
    else:
        if not is_valid_email(username):
            logger.warning("Username %s is not a valid mail address.", username)
        base_url = f"https://www.amazon.{domain}"
        logger.info("Login with Amazon Account.")

    default_headers = {
        "User-Agent": USER_AGENT,
        "Accept-Language": "en-US",
        "Accept-Encoding": "gzip",
    }
    init_cookies = build_init_cookies()

    session = httpx.Client(
        base_url=base_url,
        headers=default_headers,
        cookies=init_cookies,
        follow_redirects=True,
    )
    code_verifier = create_code_verifier()

    oauth_url, serial = build_oauth_url(
        country_code=country_code,
        domain=domain,
        market_place_id=market_place_id,
        code_verifier=code_verifier,
        serial=serial,
        with_username=with_username,
    )

    oauth_resp = session.get(oauth_url)
    oauth_soup = get_soup(oauth_resp)

    login_inputs = get_inputs_from_soup(oauth_soup)
    login_inputs["email"] = username
    login_inputs["password"] = password

    metadata = meta_audible_app(USER_AGENT, base_url)
    login_inputs["metadata1"] = encrypt_metadata(metadata)

    method, url = get_next_action_from_soup(oauth_soup, {"name": "signIn"})

    login_resp = session.request(method, url, data=login_inputs)
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

        method, url = get_next_action_from_soup(login_soup, {"name": "signIn"})

        login_resp = session.request(method, url, data=inputs)
        login_soup = get_soup(login_resp)

    # check for choice mfa
    # https://www.amazon.de/ap/mfa/new-otp
    while check_for_choice_mfa(login_soup):
        inputs = get_inputs_from_soup(login_soup)
        for node in login_soup.select("div[data-a-input-name=otpDeviceContext]"):
            # auth-TOTP, auth-SMS, auth-VOICE
            if "auth-TOTP" in node["class"]:
                inp_node = node.find("input")
                if (
                    isinstance(inp_node, Tag)
                    and isinstance(inp_node["name"], str)
                    and isinstance(inp_node["value"], str)
                ):
                    inputs[inp_node["name"]] = inp_node["value"]

        method, url = get_next_action_from_soup(login_soup)

        login_resp = session.request(method, url, data=inputs)
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

        method, url = get_next_action_from_soup(login_soup)

        login_resp = session.request(method, url, data=inputs)
        login_soup = get_soup(login_resp)

    # check for cvf
    while check_for_cvf(login_soup):
        if cvf_callback:
            cvf_code = cvf_callback()
        else:
            cvf_code = default_cvf_callback()

        inputs = get_inputs_from_soup(login_soup)

        method, url = get_next_action_from_soup(login_soup)

        login_resp = session.request(method, url, data=inputs)
        login_soup = get_soup(login_resp)

        inputs = get_inputs_from_soup(login_soup)
        inputs["action"] = "code"
        inputs["code"] = cvf_code

        method, url = get_next_action_from_soup(login_soup)

        login_resp = session.request(method, url, data=inputs)
        login_soup = get_soup(login_resp)

    # check for approval alert
    while check_for_approval_alert(login_soup):
        if approval_callback:
            approval_callback()
        else:
            default_approval_alert_callback()

        # url = login_soup.find(id="resend-approval-link")["href"]
        url = str(login_resp.url)

        login_resp = session.get(url)
        login_soup = get_soup(login_resp)

        while login_soup.find(
            "span", {"class": "transaction-approval-word-break"}
        ):  # a-size-base-plus transaction-approval-word-break a-text-bold
            login_resp = session.get(url)
            login_soup = get_soup(login_resp)
            logger.info("still waiting for redirect")

    session.close()

    authcode_url = None
    if b"openid.oa2.authorization_code" in login_resp.url.query:
        authcode_url = login_resp.url
    elif len(login_resp.history) > 0:
        for history in login_resp.history:
            if b"openid.oa2.authorization_code" in history.url.query:
                authcode_url = history.url
                break

    if authcode_url is None:
        raise Exception("Login failed. Please check the log.")

    logger.debug("Login confirmed for %s", username)

    authorization_code = extract_code_from_url(authcode_url)

    return {
        "authorization_code": authorization_code,
        "code_verifier": code_verifier,
        "domain": domain,
        "serial": serial,
    }


def external_login(
    country_code: str,
    domain: str,
    market_place_id: str,
    serial: str | None = None,
    with_username: bool = False,
    login_url_callback: Callable[[str], str] | None = None,
) -> dict[str, Any]:
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
        An ``authorization_code``, a ``code_verifier`` and the
        ``device serial`` from the authorized Client.
    """
    code_verifier = create_code_verifier()
    oauth_url, serial = build_oauth_url(
        country_code=country_code,
        domain=domain,
        market_place_id=market_place_id,
        code_verifier=code_verifier,
        serial=serial,
        with_username=with_username,
    )

    if login_url_callback:
        _response_url = login_url_callback(oauth_url)
    else:
        _response_url = default_login_url_callback(oauth_url)

    response_url = httpx.URL(_response_url)
    parsed_url = parse_qs(response_url.query.decode())

    authorization_code = parsed_url["openid.oa2.authorization_code"][0]

    return {
        "authorization_code": authorization_code,
        "code_verifier": code_verifier,
        "domain": domain,
        "serial": serial,
    }
