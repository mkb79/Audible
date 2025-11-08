import base64
import logging
import warnings
from datetime import datetime, timedelta, timezone
from typing import TYPE_CHECKING, Any

import httpx

from .login import build_client_id


if TYPE_CHECKING:
    from .device import BaseDevice


logger = logging.getLogger("audible.register")


def _convert_base64_der_to_pem(base64_key: str) -> str:
    """Convert Android base64-DER certificate to PEM format.

    Android returns private keys in PKCS#8 format (base64-encoded DER).
    This function decodes the PKCS#8 structure and extracts the RSA key,
    then converts it to PEM format.

    Args:
        base64_key: Base64-encoded DER certificate (Android PKCS#8 format)

    Returns:
        PEM-formatted private key string

    Raises:
        ValueError: If conversion fails
    """
    try:
        import rsa
        from pyasn1.codec.der import decoder
        from pyasn1.type import namedtype, univ

        class PrivateKeyAlgorithm(univ.Sequence):
            componentType = namedtype.NamedTypes(  # noqa: N815
                namedtype.NamedType("algorithm", univ.ObjectIdentifier()),
                namedtype.NamedType("parameters", univ.Any()),
            )

        class PrivateKeyInfo(univ.Sequence):
            componentType = namedtype.NamedTypes(  # noqa: N815
                namedtype.NamedType("version", univ.Integer()),
                namedtype.NamedType("pkalgo", PrivateKeyAlgorithm()),
                namedtype.NamedType("key", univ.OctetString()),
            )

        # Decode base64 to DER bytes
        encoded_key = base64.b64decode(base64_key)

        # Decode PKCS#8 structure
        (key_info, _) = decoder.decode(encoded_key, asn1Spec=PrivateKeyInfo())

        # Extract the octet string containing the actual RSA key
        key_octet_string = key_info["key"]

        # Load RSA key from DER format
        key = rsa.PrivateKey.load_pkcs1(key_octet_string, format="DER")

        # Save as PEM format
        return key.save_pkcs1().decode("utf-8")

    except Exception as e:
        raise ValueError(f"Failed to convert base64-DER to PEM format: {e}") from e


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

    # Convert base64-DER certificate to PEM format if needed
    # Check format by content (not by device type) for future-proofing
    if device_private_key.startswith("-----BEGIN RSA PRIVATE KEY-----"):
        # Already in PEM format (typically iOS devices)
        logger.debug("device_private_key is already in PEM format")
    elif device_private_key.startswith("MII"):
        # base64-DER format (typically Android devices) - convert to PEM
        logger.debug("Converting base64-DER certificate to PEM format")
        device_private_key = _convert_base64_der_to_pem(device_private_key)
        logger.debug("Certificate conversion successful")
    else:
        # Unknown format - log warning but don't fail
        logger.warning(
            "device_private_key has unexpected format (not PEM or base64-DER). "
            "First 30 chars: %s",
            device_private_key[:30],
        )

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
