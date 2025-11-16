"""Service class for Audible device registration.

This module provides a class-based approach to device registration,
handling both registration and deregistration of Audible devices.

.. versionadded:: v0.11.0
"""

from __future__ import annotations

import base64
import logging
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import TYPE_CHECKING, Any

import httpx


if TYPE_CHECKING:
    from .device import BaseDevice


logger = logging.getLogger("audible.registration_service")


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


@dataclass
class RegistrationResult:
    """Result from successful registration operation.

    Attributes:
        adp_token: ADP token for device authentication
        device_private_key: RSA private key in PEM format
        access_token: Bearer access token
        refresh_token: Refresh token for obtaining new access tokens
        expires: Unix timestamp when access token expires
        website_cookies: Optional website cookies from registration
        store_authentication_cookie: Optional store authentication cookie
        device_info: Device information from server
        customer_info: Customer information from server
        device: Device configuration used for registration
    """

    adp_token: str
    device_private_key: str
    access_token: str
    refresh_token: str
    expires: float
    website_cookies: dict[str, str] | None
    store_authentication_cookie: Any
    device_info: dict[str, Any]
    customer_info: dict[str, Any]
    device: BaseDevice

    def to_dict(self):
        return self.__dict__


class RegistrationService:
    """Service for handling Audible device registration and deregistration.

    This class provides methods to register new Audible devices and
    deregister existing ones. It uses httpx directly for HTTP requests.

    Args:
        device: Device to register

    Example:
        >>> from audible.device import ANDROID  # doctest: +SKIP
        >>> service = RegistrationService(device=ANDROID)  # doctest: +SKIP
        >>> result = service.register(  # doctest: +SKIP
        ...     authorization_code="code_from_login",
        ...     code_verifier=b"verifier_from_login",
        ...     domain="com",
        ... )
        >>> print(result.access_token)  # doctest: +SKIP
    """

    def __init__(self, device: BaseDevice):
        self.device = device

    def register(
        self,
        authorization_code: str,
        code_verifier: bytes | str,
        domain: str,
        with_username: bool = False,
    ) -> RegistrationResult:
        """Register device with Audible.

        Args:
            authorization_code: OAuth2 authorization code from login
            code_verifier: PKCE code verifier from login (bytes or str)
            domain: Amazon domain (e.g., "com", "de")
            with_username: If True, use audible domain instead of amazon

        Returns:
            RegistrationResult with all authentication tokens and device info

        Raises:
            Exception: If registration fails (non-200 response)

        Complexity: ~5
        """
        # Build request
        body = self._build_request_body(
            authorization_code, code_verifier, domain, self.device.device_serial
        )
        url = self._build_url(domain, with_username)

        # Make request (httpx directly, no abstraction!)
        resp = httpx.post(url, json=body)
        if resp.status_code != 200:
            raise Exception(resp.json())

        # Parse response
        success_response = resp.json()["response"]["success"]
        tokens = self._parse_tokens(success_response)
        extensions = self._parse_extensions(success_response)

        return RegistrationResult(
            **tokens,
            **extensions,
            device=self.device,
        )

    def deregister(
        self,
        access_token: str,
        domain: str,
        deregister_all: bool = False,
        with_username: bool = False,
    ) -> Any:
        """Deregister device.

        Note:
            Except for the access_token, all authentication data will lose
            validation immediately.

        Args:
            access_token: Access token from registered device
            domain: Amazon domain (e.g., "com", "de")
            deregister_all: If True, deregister all Audible devices
            with_username: If True, use audible domain instead of amazon

        Returns:
            Server response (contains errors if any occurred)

        Raises:
            Exception: If deregistration fails (non-200 response)

        Complexity: ~3
        """
        body = {"deregister_all_existing_accounts": deregister_all}
        headers = {"Authorization": f"Bearer {access_token}"}
        url = self._build_url(domain, with_username, endpoint="deregister")

        # Make request (httpx directly)
        resp = httpx.post(url, json=body, headers=headers)
        if resp.status_code != 200:
            raise Exception(resp.json())

        return resp.json()

    # Private methods - each <30 lines, complexity <5

    def _build_request_body(
        self,
        authorization_code: str,
        code_verifier: bytes | str,
        domain: str,
        device_serial: str | None,
    ) -> dict[str, Any]:
        """Build registration request body.

        Args:
            authorization_code: OAuth2 authorization code
            code_verifier: PKCE code verifier (bytes or str)
            domain: Amazon domain
            device_serial: Optional device serial override

        Returns:
            Complete registration request body

        Complexity: ~3
        """
        # Use device serial or provided override
        serial = device_serial or self.device.device_serial

        # Get registration data from device
        registration_data = self.device.get_registration_data()
        registration_data["device_serial"] = serial

        # Handle both bytes and str code_verifier for backward compatibility
        verifier_str = (
            code_verifier.decode()
            if isinstance(code_verifier, bytes)
            else code_verifier
        )
        return {
            "requested_token_type": [
                "bearer",
                "mac_dms",
                "website_cookies",
                "store_authentication_cookie",
            ],
            "cookies": {"website_cookies": [], "domain": f".amazon.{domain}"},
            "registration_data": registration_data,
            "auth_data": {
                "client_id": self.device.build_client_id(),
                "authorization_code": authorization_code,
                "code_verifier": verifier_str,
                "code_algorithm": "SHA-256",
                "client_domain": "DeviceLegacy",
            },
            "requested_extensions": ["device_info", "customer_info"],
        }

    @staticmethod
    def _build_url(domain: str, with_username: bool, endpoint: str = "register") -> str:
        """Build registration URL.

        Args:
            domain: Amazon domain
            with_username: If True, use audible domain
            endpoint: API endpoint ("register" or "deregister")

        Returns:
            Full API URL

        Complexity: ~2
        """
        target_domain = "audible" if with_username else "amazon"
        return f"https://api.{target_domain}.{domain}/auth/{endpoint}"

    @staticmethod
    def _parse_tokens(success_response: dict[str, Any]) -> dict[str, Any]:
        """Parse tokens from registration response.

        Handles PEM vs PKCS#8 key format conversion for device_private_key.

        Args:
            success_response: Success portion of registration response

        Returns:
            Dict with tokens (adp_token, device_private_key, access_token, etc.)

        Complexity: ~8
        """
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
        expires = (
            datetime.now(timezone.utc) + timedelta(seconds=expires_s)
        ).timestamp()

        # Parse website cookies
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
        }

    @staticmethod
    def _parse_extensions(success_response: dict[str, Any]) -> dict[str, Any]:
        """Parse extensions (device_info, customer_info) from response.

        Args:
            success_response: Success portion of registration response

        Returns:
            Dict with device_info and customer_info

        Complexity: ~2
        """
        extensions = success_response["extensions"]
        return {
            "device_info": extensions["device_info"],
            "customer_info": extensions["customer_info"],
        }
