import uuid
from datetime import datetime, timedelta
from typing import Any, Dict

import httpx


def get_random_device_serial() -> str:
    """Generates and prepares a random uuid version 4.
    
    Using a random serial prevents from unregister devices by other users
    with same `device_serial`.
    """
    return str(uuid.uuid4()).replace("-", "")


def register(access_token: str, domain: str) -> Dict[str, Any]:
    """Registers a dummy Audible device. 

    Args:
        access_token: An access token fetches from :func:`audible.auth.login`.
        domain: The top level domain of the requested Amazon server (e.g. com).
    
    Returns:
        Additional authentication data needed for access Audible API.
    """
    body = {
        "requested_token_type":
            ["bearer", "mac_dms", "website_cookies",
             "store_authentication_cookie"],
        "cookies": {
            "website_cookies": [],
            "domain": f".amazon.{domain}"},
        "registration_data": {
            "domain":
                "Device",
            "app_version":
                "3.26.1",
            "device_serial":
                get_random_device_serial(),
            "device_type":
                "A2CZJZGLK2JJVM",
            "device_name": (
                "%FIRST_NAME%%FIRST_NAME_POSSESSIVE_STRING%%DUPE_"
                "STRATEGY_1ST%Audible for iPhone"),
            "os_version":
                "13.5.1",
            "device_model":
                "iPhone",
            "app_name":
                "Audible"},
        "auth_data": {
            "access_token": access_token},
        "requested_extensions": ["device_info", "customer_info"]
    }

    resp = httpx.post(f"https://api.amazon.{domain}/auth/register", json=body)

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


def deregister(access_token: str, domain: str,
               deregister_all: bool = False) -> Dict[str, Any]:
    """Deregisters a dummy Audible device.
    
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
    if not resp.status_code == 200:
        raise Exception(resp_json)

    return resp_json
