"""Service class for Audible device registration.

This module provides a class-based approach to device registration,
handling both registration and deregistration of Audible devices.

.. versionadded:: v0.11.0
"""

import logging
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import TYPE_CHECKING, Any

import httpx

from .login import build_client_id
from .register import _convert_base64_der_to_pem


if TYPE_CHECKING:
    from .device import BaseDevice


logger = logging.getLogger("audible.registration_service")


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
    device: "BaseDevice"


class RegistrationService:
    """Service for handling Audible device registration and deregistration.

    This class provides methods to register new Audible devices and
    deregister existing ones. It uses httpx directly for HTTP requests.

    Args:
        device: Device to register

    Example:
        >>> from audible.registration_service import RegistrationService
        >>> from audible.device import ANDROID
        >>> service = RegistrationService(device=ANDROID)
        >>> result = service.register(
        ...     authorization_code="code_from_login",
        ...     code_verifier=b"verifier_from_login",
        ...     domain="com",
        ... )
        >>> print(result.access_token)
    """

    def __init__(self, device: "BaseDevice"):
        """Initialize registration service with device.

        Args:
            device: Device to register
        """
        self.device = device

    def register(
        self,
        authorization_code: str,
        code_verifier: bytes,
        domain: str,
        device_serial: str | None = None,
        with_username: bool = False,
    ) -> RegistrationResult:
        """Register device with Audible.

        Args:
            authorization_code: OAuth2 authorization code from login
            code_verifier: PKCE code verifier from login
            domain: Amazon domain (e.g., "com", "de")
            device_serial: Optional device serial (overrides device's serial)
            with_username: If True, use audible domain instead of amazon

        Returns:
            RegistrationResult with all authentication tokens and device info

        Raises:
            Exception: If registration fails (non-200 response)

        Complexity: ~5
        """
        # Build request
        body = self._build_request_body(
            authorization_code, code_verifier, domain, device_serial
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
        code_verifier: bytes,
        domain: str,
        device_serial: str | None,
    ) -> dict[str, Any]:
        """Build registration request body.

        Args:
            authorization_code: OAuth2 authorization code
            code_verifier: PKCE code verifier
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
                "client_id": build_client_id(serial),
                "authorization_code": authorization_code,
                "code_verifier": code_verifier.decode(),
                "code_algorithm": "SHA-256",
                "client_domain": "DeviceLegacy",
            },
            "requested_extensions": ["device_info", "customer_info"],
        }

    def _build_url(
        self, domain: str, with_username: bool, endpoint: str = "register"
    ) -> str:
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

    def _parse_tokens(self, success_response: dict[str, Any]) -> dict[str, Any]:
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

    def _parse_extensions(self, success_response: dict[str, Any]) -> dict[str, Any]:
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


# Backward compatible wrapper functions


def register(
    authorization_code: str,
    code_verifier: bytes,
    domain: str,
    device: "BaseDevice | None" = None,
    serial: str | None = None,
    with_username: bool = False,
) -> dict[str, Any]:
    """Register Audible device (backward compatible wrapper).

    This function maintains backward compatibility by wrapping RegistrationService.
    For new code, prefer using RegistrationService directly for better testability.

    Args:
        authorization_code: OAuth2 authorization code from login
        code_verifier: PKCE code verifier from login
        domain: Amazon domain (e.g., "com", "de")
        device: Device to register. If None, uses default iPhone device
        serial: DEPRECATED - Use device parameter instead
        with_username: If True, use audible domain instead of amazon

    Returns:
        Dict with all authentication tokens and device info

    Raises:
        Exception: If registration fails

    .. deprecated:: v0.11.0
        The serial parameter is deprecated. Use device parameter instead.

    .. versionchanged:: v0.11.0
        Now uses RegistrationService internally. The function signature remains
        the same for backward compatibility.

    Example:
        >>> from audible.registration_service import register
        >>> from audible.device import ANDROID
        >>> result = register(
        ...     authorization_code="code",
        ...     code_verifier=b"verifier",
        ...     domain="com",
        ...     device=ANDROID,
        ... )
    """
    import warnings

    # Handle device parameter with backward compatibility
    if device is None:
        from .device import IPHONE

        device = IPHONE

    # Handle backward compatibility with serial parameter
    device_serial = None
    if serial is not None:
        warnings.warn(
            "The 'serial' parameter is deprecated and will be removed in v0.12.0. "
            "Use 'device' parameter instead.",
            DeprecationWarning,
            stacklevel=2,
        )
        device_serial = serial

    # Use service class
    service = RegistrationService(device=device)
    result = service.register(
        authorization_code=authorization_code,
        code_verifier=code_verifier,
        domain=domain,
        device_serial=device_serial,
        with_username=with_username,
    )

    # Convert to dict for backward compatibility
    return {
        "adp_token": result.adp_token,
        "device_private_key": result.device_private_key,
        "access_token": result.access_token,
        "refresh_token": result.refresh_token,
        "expires": result.expires,
        "website_cookies": result.website_cookies,
        "store_authentication_cookie": result.store_authentication_cookie,
        "device_info": result.device_info,
        "customer_info": result.customer_info,
        "device": result.device,
    }


def deregister(
    access_token: str,
    domain: str,
    deregister_all: bool = False,
    with_username: bool = False,
) -> Any:
    """Deregister device (backward compatible wrapper).

    This function maintains backward compatibility by wrapping RegistrationService.
    For new code, prefer using RegistrationService directly for better testability.

    Args:
        access_token: Access token from registered device
        domain: Amazon domain (e.g., "com", "de")
        deregister_all: If True, deregister all Audible devices
        with_username: If True, use audible domain instead of amazon

    Returns:
        Server response (contains errors if any occurred)

    Raises:
        Exception: If deregistration fails

    .. versionchanged:: v0.11.0
        Now uses RegistrationService.deregister() internally.

    Example:
        >>> from audible.registration_service import deregister
        >>> result = deregister(
        ...     access_token="token",
        ...     domain="com",
        ... )
    """
    # Note: No device needed for deregister, but we need a dummy instance
    # This is OK because deregister only uses access_token
    from .device import IPHONE

    service = RegistrationService(device=IPHONE)
    return service.deregister(
        access_token=access_token,
        domain=domain,
        deregister_all=deregister_all,
        with_username=with_username,
    )
