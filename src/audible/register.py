import warnings
from datetime import datetime, timedelta, timezone
from typing import TYPE_CHECKING, Any

import httpx

from .login import build_client_id


if TYPE_CHECKING:
    from .device import BaseDevice


def register(
    authorization_code: str,
    code_verifier: bytes,
    domain: str,
    serial: str | None = None,
    with_username: bool = False,
    device: "BaseDevice | None" = None,
) -> dict[str, Any]:
    """Registers a dummy Audible device.

    Args:
        authorization_code: The code given after a successful authorization
        code_verifier: The verifier code from authorization
        domain: The top level domain of the requested Amazon server (e.g. com).
        serial: The device serial. DEPRECATED: Use device parameter instead.
        with_username: If ``True`` uses `audible` domain instead of `amazon`.
        device: The device to register. If ``None``, uses default iPhone device.

    Returns:
        Additional authentication data needed for access Audible API.

    Raises:
        Exception: If response status code is not 200.

    .. versionadded:: v0.7.1
           The with_username argument
    .. versionadded:: v0.11.0
           The device argument
    .. deprecated:: v0.11.0
           The serial argument is deprecated. Use device parameter instead.
    """
    # Handle device parameter with backward compatibility
    if device is None:
        from .device import IPHONE

        device = IPHONE

    # Handle backward compatibility with serial parameter
    if serial is not None:
        warnings.warn(
            "The 'serial' parameter is deprecated and will be removed in v0.12.0. "
            "Use 'device' parameter instead.",
            DeprecationWarning,
            stacklevel=2,
        )
        # Use provided serial instead of device's serial
        device_serial = serial
    else:
        device_serial = device.device_serial

    # Get registration data from device
    registration_data = device.get_registration_data()
    registration_data["device_serial"] = device_serial

    body = {
        "requested_token_type": [
            "bearer",
            "mac_dms",
            "website_cookies",
            "store_authentication_cookie",
        ],
        "cookies": {"website_cookies": [], "domain": f".amazon.{domain}"},
        "registration_data": registration_data,
        "auth_data": {
            "client_id": build_client_id(device_serial),
            "authorization_code": authorization_code,
            "code_verifier": code_verifier.decode(),
            "code_algorithm": "SHA-256",
            "client_domain": "DeviceLegacy",
        },
        "requested_extensions": ["device_info", "customer_info"],
    }

    target_domain = "audible" if with_username else "amazon"

    resp = httpx.post(f"https://api.{target_domain}.{domain}/auth/register", json=body)

    resp_json = resp.json()
    if resp.status_code != 200:
        raise Exception(resp_json)

    success_response = resp_json["response"]["success"]

    tokens = success_response["tokens"]
    adp_token = tokens["mac_dms"]["adp_token"]
    device_private_key = tokens["mac_dms"]["device_private_key"]
    store_authentication_cookie = tokens.get("store_authentication_cookie")
    access_token = tokens["bearer"]["access_token"]
    refresh_token = tokens["bearer"]["refresh_token"]
    expires_s = int(tokens["bearer"]["expires_in"])
    expires = (datetime.now(timezone.utc) + timedelta(seconds=expires_s)).timestamp()

    extensions = success_response["extensions"]
    device_info = extensions["device_info"]
    customer_info = extensions["customer_info"]

    website_cookies = None
    if "website_cookies" in tokens:
        website_cookies = {}
        for cookie in tokens["website_cookies"]:
            website_cookies[cookie["Name"]] = cookie["Value"].replace(r'"', r"")

    return {
        "adp_token": adp_token,
        "device_private_key": device_private_key,
        "access_token": access_token,
        "refresh_token": refresh_token,
        "expires": expires,
        "website_cookies": website_cookies,
        "store_authentication_cookie": store_authentication_cookie,
        "device_info": device_info,
        "customer_info": customer_info,
        "device": device,
    }


def deregister(
    access_token: str,
    domain: str,
    deregister_all: bool = False,
    with_username: bool = False,
) -> Any:
    """Deregister a previous registered Audible device.

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

    .. versionadded:: v0.8
           The with_username argument
    """
    body = {"deregister_all_existing_accounts": deregister_all}
    headers = {"Authorization": f"Bearer {access_token}"}

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
