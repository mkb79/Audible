from datetime import datetime, timedelta
from random import choices
import string
from typing import Any, Dict

import requests


def get_random_device_serial() -> str:
    """
    Generates a random text (str + int) with a length of 40 chars.
    
    Use of random serial prevents unregister device by other users
    with same `device_serial`.
    """
    return "".join(choices(string.ascii_uppercase + string.digits, k=40))


def register(access_token: str, domain: str) -> Dict[str, Any]:
    """
    Register a dummy audible device with access token and cookies
    from ``auth_login``.
    Returns important credentials needed for access audible api.
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
            "app_version": "3.7",
            "device_serial": get_random_device_serial(),
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

    resp = requests.post(
        f"https://api.amazon.{domain}/auth/register", json=body
    )

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

    login_cookies_new = dict()
    for cookie in tokens["website_cookies"]:
        login_cookies_new[cookie["Name"]] = cookie["Value"].replace(r'"', r'')

    return {
        "adp_token": adp_token,
        "device_private_key": device_private_key,
        "access_token": access_token,
        "refresh_token": refresh_token,
        "expires": expires,
        "login_cookies": login_cookies_new,
        "store_authentication_cookie": store_authentication_cookie,
        "device_info": device_info,
        "customer_info": customer_info
    }


def deregister(access_token: str, domain: str,
               deregister_all: bool = False) -> Dict[str, Any]:
    """
    Deregister device which was previously registered with `access_token`.

    `access_token` is valid until expiration. All other credentials will
    be invalid immediately.
    
    If `deregister_all=True` all registered devices will be deregistered.
    """
    body = {"deregister_all_existing_accounts": deregister_all}
    headers = {"Authorization": f"Bearer {access_token}"}

    resp = requests.post(
        f"https://api.amazon.{domain}/auth/deregister",
        json=body, headers=headers
    )

    resp_json = resp.json()
    if resp.status_code == 200:
        return resp_json
    else:
        raise Exception(resp_json)
