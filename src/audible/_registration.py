"""Request building and response parsing for device registration.

Everything here is free of I/O and state: it builds the requests that
:mod:`audible.login` sends and turns the responses into values. The login
classes own the HTTP clients, the clock and the status, so the same
functions serve their sync and async methods alike.

What the requests report about the app and the device comes from a
:class:`~audible._device.DeviceProfile`, which every builder takes as its
first argument.
"""

from __future__ import annotations

import base64
import enum
import hashlib
import json
import math
import secrets
import time
import uuid
from typing import TYPE_CHECKING, Any, NamedTuple
from urllib.parse import parse_qs, urlencode, urlsplit

import httpx

from .exceptions import LoginFailedError
from .utils import build_access_token_header


if TYPE_CHECKING:
    from ._device import DeviceProfile
    from .localization import Locale


PRE_AMAZON_DOMAINS = ("de", "com", "co.uk")

# The code-pair list is the one confirmed live. The authorization-code flow
# keeps its long-standing list; the store cookie is saved but never read.
_CODE_PAIR_TOKEN_TYPES = ("bearer", "mac_dms", "website_cookies")
_AUTHORIZATION_CODE_TOKEN_TYPES = (
    *_CODE_PAIR_TOKEN_TYPES,
    "store_authentication_cookie",
)


class RequestSpec(NamedTuple):
    """A JSON POST request, described without sending it."""

    url: str
    body: dict[str, Any]
    headers: dict[str, str]


class CodePair(NamedTuple):
    """A code pair as returned by ``/auth/create/codepair``."""

    public_code: str
    private_code: str
    expires_in: float
    interval: float


class PollOutcome(enum.Enum):
    """How a code-pair registration attempt ended."""

    REGISTERED = enum.auto()
    PENDING = enum.auto()
    RETRY = enum.auto()
    REJECTED = enum.auto()


def build_device_serial() -> str:
    """Return a new random device serial."""
    return uuid.uuid4().hex.upper()


def build_client_id(device: DeviceProfile, serial: str) -> str:
    """Return the OAuth client id Amazon derives from serial and device type."""
    return f"{serial}#{device.device_type}".encode().hex()


def create_code_verifier() -> str:
    """Return a new PKCE code verifier."""
    return base64.urlsafe_b64encode(secrets.token_bytes(32)).rstrip(b"=").decode()


def _code_challenge(code_verifier: str) -> str:
    digest = hashlib.sha256(code_verifier.encode()).digest()
    return base64.urlsafe_b64encode(digest).rstrip(b"=").decode()


def verification_url(domain: str) -> str:
    """Return the page on which the user confirms a device code."""
    return f"https://www.amazon.{domain}/code"


def _device_code_headers(device: DeviceProfile, domain: str) -> dict[str, str]:
    return {
        "Accept": "application/json",
        "User-Agent": device.user_agent,
        "x-amzn-identity-auth-domain": f"api.amazon.{domain}",
    }


def _registration_body(
    device: DeviceProfile,
    domain: str,
    serial: str,
    auth_data: dict[str, Any],
    token_types: tuple[str, ...],
) -> dict[str, Any]:
    return {
        "requested_token_type": list(token_types),
        "cookies": {"website_cookies": [], "domain": f".amazon.{domain}"},
        "registration_data": {
            "domain": device.registration_domain,
            "app_version": device.app_version,
            "device_serial": serial,
            "device_type": device.device_type,
            "device_name": device.device_name,
            "os_version": device.os_version,
            "software_version": device.software_version,
            "device_model": device.device_model,
            "app_name": device.app_name,
        },
        "auth_data": auth_data,
        "requested_extensions": ["device_info", "customer_info"],
    }


def code_pair_request(device: DeviceProfile, domain: str, serial: str) -> RequestSpec:
    """Build the request that creates a code pair for a new device."""
    body = {
        "code_data": {
            "device_serial": serial,
            "device_type": device.device_type,
            "domain": "Device",
        },
        "code_properties": {"code_duration": "600", "code_length": "5"},
    }
    return RequestSpec(
        f"https://api.amazon.{domain}/auth/create/codepair",
        body,
        _device_code_headers(device, domain),
    )


def code_pair_registration_request(
    device: DeviceProfile, domain: str, serial: str, code_pair: CodePair
) -> RequestSpec:
    """Build the registration request that is polled with a code pair."""
    auth_data = {
        "code_pair": {
            "public_code": code_pair.public_code,
            "private_code": code_pair.private_code,
        },
        "use_global_authentication": "true",
    }
    return RequestSpec(
        f"https://api.amazon.{domain}/auth/register",
        _registration_body(device, domain, serial, auth_data, _CODE_PAIR_TOKEN_TYPES),
        _device_code_headers(device, domain),
    )


def authorization_code_registration_request(
    device: DeviceProfile,
    domain: str,
    serial: str,
    authorization_code: str,
    code_verifier: str,
) -> RequestSpec:
    """Build the registration request of a pre-Amazon account."""
    auth_data = {
        "client_id": build_client_id(device, serial),
        "authorization_code": authorization_code,
        "code_verifier": code_verifier,
        "code_algorithm": "SHA-256",
        "client_domain": "DeviceLegacy",
    }
    return RequestSpec(
        f"https://api.audible.{domain}/auth/register",
        _registration_body(
            device, domain, serial, auth_data, _AUTHORIZATION_CODE_TOKEN_TYPES
        ),
        {},
    )


def pre_amazon_login_url(
    device: DeviceProfile, locale: Locale, serial: str, code_verifier: str
) -> str:
    """Build the browser sign-in URL for a pre-Amazon account."""
    params = {
        "openid.oa2.response_type": "code",
        "openid.oa2.code_challenge_method": "S256",
        "openid.oa2.code_challenge": _code_challenge(code_verifier),
        "openid.return_to": f"https://www.audible.{locale.domain}/ap/maplanding",
        "openid.assoc_handle": f"{device.sign_in_assoc_handle}_{locale.country_code}",
        "openid.identity": "http://specs.openid.net/auth/2.0/identifier_select",
        "pageId": device.sign_in_page_id,
        "accountStatusPolicy": "P1",
        "openid.claimed_id": "http://specs.openid.net/auth/2.0/identifier_select",
        "openid.mode": "checkid_setup",
        "openid.ns.oa2": "http://www.amazon.com/ap/ext/oauth/2",
        "openid.oa2.client_id": f"device:{build_client_id(device, serial)}",
        "openid.ns.pape": "http://specs.openid.net/extensions/pape/1.0",
        "marketPlaceId": locale.market_place_id,
        "openid.oa2.scope": "device_auth_access",
        "forceMobileLayout": "true",
        "openid.ns": "http://specs.openid.net/auth/2.0",
        "openid.pape.max_auth_age": "0",
    }
    return f"https://www.audible.{locale.domain}/ap/signin?{urlencode(params)}"


def extract_authorization_code(redirect_url: str, domain: str) -> str:
    """Return the authorization code from the URL the browser ended on.

    Only the ``/ap/maplanding`` page of the marketplace the login started on
    is accepted. The URL is parsed, never fetched.

    Args:
        redirect_url: The full URL from the browser's address bar.
        domain: The top level domain of the marketplace.

    Returns:
        The authorization code.

    Raises:
        ValueError: If the URL is not the expected page or does not carry
            exactly one authorization code.
    """
    parsed = urlsplit(redirect_url.strip())
    if (
        parsed.scheme != "https"
        or parsed.hostname != f"www.audible.{domain}"
        or parsed.path != "/ap/maplanding"
        or parsed.username is not None
        or parsed.password is not None
        or parsed.port not in (None, 443)
    ):
        raise ValueError(
            f"Expected the https://www.audible.{domain}/ap/maplanding URL the "
            "browser ended on."
        )
    codes = parse_qs(parsed.query, keep_blank_values=True).get(
        "openid.oa2.authorization_code", []
    )
    if len(codes) != 1 or not codes[0]:
        raise ValueError("The URL does not contain exactly one authorization code.")
    return codes[0]


def _json_object(response: httpx.Response) -> dict[str, Any]:
    try:
        data = response.json()
    except (json.JSONDecodeError, UnicodeDecodeError):
        return {}
    return data if isinstance(data, dict) else {}


def error_code(response: httpx.Response) -> str | None:
    """Return the lower-cased error code Amazon sent, if any."""
    data = _json_object(response)
    nested = data.get("response")
    error = data.get("error", nested.get("error") if isinstance(nested, dict) else None)
    if isinstance(error, str):
        return error.lower()
    if isinstance(error, dict):
        for key in ("code", "error_code", "error", "type"):
            value = error.get(key)
            if isinstance(value, str):
                return value.lower()
    return None


def _positive_number(value: Any, field: str) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError):
        number = math.nan
    if isinstance(value, bool) or not math.isfinite(number) or number <= 0:
        raise LoginFailedError(f"Invalid {field} in Amazon's response.")
    return number


def parse_code_pair(response: httpx.Response) -> CodePair:
    """Return the code pair from a ``/auth/create/codepair`` response.

    Args:
        response: The response to the code-pair request.

    Returns:
        The code pair with its lifetime and polling interval in seconds.

    Raises:
        LoginFailedError: If Amazon refused the request or the response lacks
            a field.
    """
    data = _json_object(response)
    code = error_code(response)
    if response.status_code != 200 or code is not None:
        raise LoginFailedError(
            f"Amazon refused to create a device code (HTTP "
            f"{response.status_code}, error {code}).",
            status_code=response.status_code,
            error_code=code,
        )
    public_code = data.get("public_code")
    private_code = data.get("private_code")
    if not (isinstance(public_code, str) and public_code) or not (
        isinstance(private_code, str) and private_code
    ):
        raise LoginFailedError("Amazon's code-pair response lacks a code.")
    interval = _positive_number(
        data.get("polling_interval_in_seconds"), "polling_interval_in_seconds"
    )
    return CodePair(
        public_code,
        private_code,
        _positive_number(data.get("expires_in"), "expires_in"),
        max(1.0, interval),
    )


def classify_poll(response: httpx.Response) -> PollOutcome:
    """Classify the response to a code-pair registration attempt.

    Until the user confirms the code, Amazon answers ``401`` with the error
    code ``Unauthorized``. That combination is the only one observed while
    waiting; any other error ends the login instead of polling until the
    code expires.

    Args:
        response: The response to the polled registration request.

    Returns:
        The outcome of the attempt.
    """
    if response.status_code == 429 or 500 <= response.status_code <= 599:
        return PollOutcome.RETRY
    nested = _json_object(response).get("response")
    if response.status_code == 200 and isinstance(nested, dict) and "success" in nested:
        return PollOutcome.REGISTERED
    if response.status_code == 401 and error_code(response) == "unauthorized":
        return PollOutcome.PENDING
    return PollOutcome.REJECTED


def retry_delay(
    response: httpx.Response | None, interval: float, failures: int
) -> float:
    """Return the delay before retrying after an overload or a network error.

    Args:
        response: The failed response, or ``None`` after a network error.
        interval: The polling interval Amazon asked for.
        failures: The number of consecutive failed attempts, at least 1.

    Returns:
        The delay in seconds: exponential backoff capped at 60 seconds, but
        never shorter than a numeric ``Retry-After`` header.
    """
    delay = min(60.0, interval * 2.0 ** min(failures, 4))
    if response is not None:
        try:
            retry_after = float(response.headers.get("retry-after", "0"))
        except ValueError:
            retry_after = 0.0
        if math.isfinite(retry_after):
            delay = max(delay, retry_after)
    return max(interval, delay)


def registration_credentials(response: httpx.Response, serial: str) -> dict[str, Any]:
    """Return the credentials from a successful ``/auth/register`` response.

    Args:
        response: The response to a registration request.
        serial: The serial the device was registered with.

    Returns:
        The registration data as keyword arguments for an
        :class:`~audible.auth.Authenticator`.

    Raises:
        LoginFailedError: If the registration was refused, the response lacks
            credentials or belongs to another device.
    """
    nested = _json_object(response).get("response")
    success = nested.get("success") if isinstance(nested, dict) else None
    if response.status_code != 200 or not isinstance(success, dict):
        code = error_code(response)
        raise LoginFailedError(
            f"The device registration was refused (HTTP {response.status_code}, "
            f"error {code}).",
            status_code=response.status_code,
            error_code=code,
        )

    try:
        tokens = success["tokens"]
        bearer, mac_dms = tokens["bearer"], tokens["mac_dms"]
        credentials = {
            "access_token": bearer["access_token"],
            "refresh_token": bearer["refresh_token"],
            "adp_token": mac_dms["adp_token"],
            "device_private_key": mac_dms["device_private_key"],
        }
        lifetime = _positive_number(bearer["expires_in"], "expires_in")
    except (KeyError, TypeError) as exc:
        raise LoginFailedError("The registration response lacks credentials.") from exc
    if not all(isinstance(value, str) and value for value in credentials.values()):
        raise LoginFailedError("The registration response lacks credentials.")

    extensions = success.get("extensions")
    extensions = extensions if isinstance(extensions, dict) else {}
    device_info = extensions.get("device_info")
    if isinstance(device_info, dict):
        returned_serial = device_info.get(
            "device_serial_number", device_info.get("device_serial")
        )
        if returned_serial and returned_serial != serial:
            raise LoginFailedError("The registration belongs to another device.")

    website_cookies = {
        cookie["Name"]: str(cookie["Value"]).replace('"', "")
        for cookie in tokens.get("website_cookies") or []
        if isinstance(cookie, dict) and "Name" in cookie and "Value" in cookie
    }

    return {
        **credentials,
        "expires": time.time() + lifetime,
        "website_cookies": website_cookies or None,
        "store_authentication_cookie": tokens.get("store_authentication_cookie"),
        "device_info": device_info,
        "customer_info": extensions.get("customer_info"),
    }


def deregister(
    access_token: str,
    domain: str,
    deregister_all: bool = False,
    with_username: bool = False,
) -> Any:
    """Deregister a previously registered Audible device.

    Note:
        Except of the ``access_token``, all authentication data will lose
        validation immediately.

    Args:
        access_token: The access token from the previous registered device
            which you want to deregister.
        domain: The top level domain of the requested Amazon server (e.g. com).
        deregister_all: If ``True``, deregister all Audible devices on Amazon.
        with_username: If ``True`` uses `audible` domain instead of `amazon`.

    Returns:
        The response for the deregister request. Contains errors, if some occurs.

    Raises:
        Exception: If response status code is not 200.
    """
    body = {"deregister_all_existing_accounts": deregister_all}
    headers = build_access_token_header(access_token)

    target_domain = "audible" if with_username else "amazon"

    resp = httpx.post(
        f"https://api.{target_domain}.{domain}/auth/deregister",
        json=body,
        headers=headers,
    )

    resp_json = resp.json()
    if resp.status_code != 200:
        raise Exception(resp_json)

    return resp_json
