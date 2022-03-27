from datetime import datetime, timedelta
from typing import Any, Dict

import httpx

from .login import build_client_id


def register(
        authorization_code: str,
        code_verifier: bytes,
        domain: str,
        serial: str = None,
        with_username: bool = False
) -> Dict[str, Any]:
    """Registers a dummy Audible device. 

    Args:
        authorization_code: The code given after a successful authorization
        code_verifier: The verifier code from authorization
        domain: The top level domain of the requested Amazon server (e.g. com).
        serial: The device serial
        with_username: If ``True`` uses `audible` domain instead of `amazon`.
    
    Returns:
        Additional authentication data needed for access Audible API.

    .. versionadded:: v0.7.1
           The with_username argument
    """

    body = {
        "requested_token_type": [
            "bearer", "mac_dms", "website_cookies",
            "store_authentication_cookie"
        ],
        "cookies": {
            "website_cookies": [],
            "domain": f".amazon.{domain}"
        },
        "registration_data": {
            "domain": "Device",
            "app_version": "3.56.2",
            "device_serial": serial,
            "device_type": "A2CZJZGLK2JJVM",
            "device_name": (
                "%FIRST_NAME%%FIRST_NAME_POSSESSIVE_STRING%%DUPE_"
                "STRATEGY_1ST%Audible for iPhone"
            ),
            "os_version": "15.0.0",
            "software_version": "35602678",
            "device_model": "iPhone",
            "app_name": "Audible"
        },
        "auth_data": {
            "client_id": build_client_id(serial),
            "authorization_code": authorization_code,
            "code_verifier": code_verifier.decode(),
            "code_algorithm": "SHA-256",
            "client_domain": "DeviceLegacy"
        },
        "requested_extensions": ["device_info", "customer_info"]
    }

    reg_domain = f"amazon.{domain}"
    if with_username:
        reg_domain = f"audible.{domain}"

    resp = httpx.post(f"https://{reg_domain}/auth/register", json=body)

    resp_json = resp.json()
    if resp.status_code != 200:
        raise Exception(resp_json)

    success_response = resp_json["response"]["success"]

    tokens = success_response["tokens"]
    adp_token = tokens["mac_dms"]["adp_token"]
    device_private_key = tokens["mac_dms"]["device_private_key"]
    store_authentication_cookie = tokens["store_authentication_cookie"]
    access_token = tokens["bearer"]["access_token"]
    refresh_token = tokens["bearer"]["refresh_token"]
    expires_s = int(tokens["bearer"]["expires_in"])
    expires = (datetime.utcnow() + timedelta(seconds=expires_s)).timestamp()

    extensions = success_response["extensions"]
    device_info = extensions["device_info"]
    customer_info = extensions["customer_info"]

    website_cookies = dict()
    for cookie in tokens["website_cookies"]:
        website_cookies[cookie["Name"]] = cookie["Value"].replace(r'"', r'')

    return {
        "adp_token": adp_token,
        "device_private_key": device_private_key,
        "access_token": access_token,
        "refresh_token": refresh_token,
        "expires": expires,
        "website_cookies": website_cookies,
        "store_authentication_cookie": store_authentication_cookie,
        "device_info": device_info,
        "customer_info": customer_info
    }


def deregister(
        access_token: str, domain: str, deregister_all: bool = False
) -> Dict[str, Any]:
    """Deregister a previous registered Audible device.
    
    Note:
        Except of the ``access_token``, all authentication data will loose 
        validation immediately.

    Args:
        access_token: The access token from the previous registered device 
            which you want to deregister.
        domain: The top level domain of the requested Amazon server (e.g. com).
        deregister_all: If ``True``, deregister all Audible devices on Amazon.

    Returns:
        The response for the deregister request. Contains errors, if some occurs.
    """

    body = {"deregister_all_existing_accounts": deregister_all}
    headers = {"Authorization": f"Bearer {access_token}"}

    resp = httpx.post(
        f"https://api.amazon.{domain}/auth/deregister",
        json=body,
        headers=headers
    )

    resp_json = resp.json()
    if resp.status_code != 200:
        raise Exception(resp_json)

    return resp_json
