"""Service classes for Audible login flow.

This module provides a class-based approach to the Audible login process,
separating concerns between login orchestration (LoginService) and challenge
handling (ChallengeHandler).

.. versionadded:: v0.11.0
"""

import logging
import time
from collections.abc import Callable
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

import httpx
from bs4 import BeautifulSoup, Tag

from .login import (
    build_init_cookies,
    build_oauth_url,
    check_for_approval_alert,
    check_for_captcha,
    check_for_choice_mfa,
    check_for_cvf,
    check_for_mfa,
    create_code_verifier,
    default_approval_alert_callback,
    default_captcha_callback,
    default_cvf_callback,
    default_otp_callback,
    extract_captcha_url,
    extract_code_from_url,
    get_inputs_from_soup,
    get_next_action_from_soup,
    get_soup,
    is_valid_email,
)
from .metadata import encrypt_metadata, meta_audible_app


if TYPE_CHECKING:
    from .device import BaseDevice


logger = logging.getLogger("audible.login_service")


@dataclass
class LoginResult:
    """Result from successful login operation.

    Attributes:
        authorization_code: OAuth2 authorization code from Amazon
        code_verifier: PKCE code verifier for token exchange
        domain: Amazon domain used for login (e.g., "com", "de")
        device_serial: Device serial number used for registration
        device: Device configuration used for login
    """

    authorization_code: str
    code_verifier: bytes
    domain: str
    device_serial: str
    device: "BaseDevice"


class ChallengeHandler:
    """Handles all login challenges (CAPTCHA, MFA, OTP, CVF, approval alerts).

    Separates challenge handling logic from main login flow to avoid monster class.
    Each challenge type has dedicated detection and handling methods.

    Args:
        session: HTTP session for making requests
        username: Amazon username (for CAPTCHA retry)
        password: Amazon password (for CAPTCHA retry)
        captcha_callback: Function to solve CAPTCHA
        otp_callback: Function to get OTP code
        cvf_callback: Function to get CVF code
        approval_callback: Function to handle approval alerts

    Example:
        >>> handler = ChallengeHandler(  # doctest: +SKIP
        ...     session=httpx.Client(),
        ...     username="user@example.com",
        ...     password="password",
        ... )
        >>> soup = handler.handle_all_challenges(initial_soup)  # doctest: +SKIP
    """

    def __init__(
        self,
        session: httpx.Client,
        username: str,
        password: str,
        captcha_callback: Callable[[str], str] | None = None,
        otp_callback: Callable[[], str] | None = None,
        cvf_callback: Callable[[], str] | None = None,
        approval_callback: Callable[[], Any] | None = None,
    ):
        self._session = session
        self._username = username
        self._password = password
        self._captcha_callback = captcha_callback or default_captcha_callback
        self._otp_callback = otp_callback or default_otp_callback
        self._cvf_callback = cvf_callback or default_cvf_callback
        self._approval_callback = approval_callback or default_approval_alert_callback

    def handle_all_challenges(
        self, soup: BeautifulSoup, initial_resp: httpx.Response
    ) -> tuple[BeautifulSoup, httpx.Response]:
        """Handle all login challenges in sequence.

        Loops through each challenge type until all are resolved.
        Order: CAPTCHA → MFA choice → OTP → CVF → Approval alert

        Args:
            soup: Initial BeautifulSoup from login response
            initial_resp: Initial HTTP response (needed for auth code extraction)

        Returns:
            Tuple of (final_soup, last_response)

        Complexity: ~8 (multiple while loops)
        """
        last_resp = initial_resp

        # Handle each challenge type until all resolved
        while self._has_captcha(soup):
            soup, last_resp = self._handle_captcha(soup)

        while self._has_mfa_choice(soup):
            soup, last_resp = self._handle_mfa_choice(soup)

        while self._has_otp(soup):
            soup, last_resp = self._handle_otp(soup)

        while self._has_cvf(soup):
            soup, last_resp = self._handle_cvf(soup)

        while self._has_approval_alert(soup):
            soup, last_resp = self._handle_approval_alert(soup, last_resp)

        return soup, last_resp

    def _handle_captcha(
        self, soup: BeautifulSoup
    ) -> tuple[BeautifulSoup, httpx.Response]:
        """Handle CAPTCHA challenge.

        Extracts CAPTCHA URL, gets user solution via callback,
        and submits the guess with login credentials.

        Args:
            soup: Page with CAPTCHA challenge

        Returns:
            Tuple of (next_soup, response)

        Complexity: ~4
        """
        captcha_url = extract_captcha_url(soup)
        guess = self._captcha_callback(captcha_url)

        inputs = get_inputs_from_soup(soup)
        inputs["guess"] = guess
        inputs["use_image_captcha"] = "true"
        inputs["use_audio_captcha"] = "false"
        inputs["showPasswordChecked"] = "false"
        inputs["email"] = self._username
        inputs["password"] = self._password

        method, url = get_next_action_from_soup(soup, {"name": "signIn"})
        login_resp = self._session.request(method, url, data=inputs)
        return get_soup(login_resp), login_resp

    def _handle_mfa_choice(
        self, soup: BeautifulSoup
    ) -> tuple[BeautifulSoup, httpx.Response]:
        """Handle MFA device selection.

        Automatically selects TOTP (authenticator app) if available.

        Args:
            soup: Page with MFA device choice

        Returns:
            Tuple of (next_soup, response)

        Complexity: ~4
        """
        inputs = get_inputs_from_soup(soup)

        for node in soup.select("div[data-a-input-name=otpDeviceContext]"):
            # auth-TOTP, auth-SMS, auth-VOICE
            if "auth-TOTP" in node["class"]:
                inp_node = node.find("input")
                if (
                    isinstance(inp_node, Tag)
                    and isinstance(inp_node["name"], str)
                    and isinstance(inp_node["value"], str)
                ):
                    inputs[inp_node["name"]] = inp_node["value"]

        method, url = get_next_action_from_soup(soup)
        login_resp = self._session.request(method, url, data=inputs)
        return get_soup(login_resp), login_resp

    def _handle_otp(self, soup: BeautifulSoup) -> tuple[BeautifulSoup, httpx.Response]:
        """Handle OTP (One-Time Password) challenge.

        Gets OTP code from callback and submits it.

        Args:
            soup: Page with OTP challenge

        Returns:
            Tuple of (next_soup, response)

        Complexity: ~3
        """
        otp_code = self._otp_callback()

        inputs = get_inputs_from_soup(soup)
        inputs["otpCode"] = otp_code
        inputs["mfaSubmit"] = "Submit"
        inputs["rememberDevice"] = "false"

        method, url = get_next_action_from_soup(soup)
        login_resp = self._session.request(method, url, data=inputs)
        return get_soup(login_resp), login_resp

    def _handle_cvf(self, soup: BeautifulSoup) -> tuple[BeautifulSoup, httpx.Response]:
        """Handle CVF (Credential Verification Form) challenge.

        Gets CVF code from callback and submits it in two steps:
        1. Select "code" action
        2. Submit the verification code

        Args:
            soup: Page with CVF challenge

        Returns:
            Tuple of (next_soup, response)

        Complexity: ~5
        """
        cvf_code = self._cvf_callback()

        # Step 1: Select code verification method
        inputs = get_inputs_from_soup(soup)
        method, url = get_next_action_from_soup(soup)
        login_resp = self._session.request(method, url, data=inputs)
        soup = get_soup(login_resp)

        # Step 2: Submit verification code
        inputs = get_inputs_from_soup(soup)
        inputs["action"] = "code"
        inputs["code"] = cvf_code

        method, url = get_next_action_from_soup(soup)
        login_resp = self._session.request(method, url, data=inputs)
        return get_soup(login_resp), login_resp

    def _handle_approval_alert(
        self, soup: BeautifulSoup, response: httpx.Response
    ) -> tuple[BeautifulSoup, httpx.Response]:
        """Handle approval alert notification.

        Waits for user to approve via email/app notification.
        Polls the same URL until approval is detected.

        Args:
            soup: Page with approval alert

        Returns:
            Tuple of (next_soup, response)

        Complexity: ~5
        """
        self._approval_callback()

        url = str(response.url)
        login_resp = self._session.get(url)
        soup = get_soup(login_resp)

        while soup.find("span", {"class": "transaction-approval-word-break"}):
            login_resp = self._session.get(url)
            soup = get_soup(login_resp)
            logger.info("still waiting for approval")
            time.sleep(4)

        return soup, login_resp

    # Challenge detection helpers - each <10 lines, complexity 1-2

    def _has_captcha(self, soup: BeautifulSoup) -> bool:
        """Check if CAPTCHA challenge present."""
        return check_for_captcha(soup)

    def _has_mfa_choice(self, soup: BeautifulSoup) -> bool:
        """Check if MFA device choice present."""
        return check_for_choice_mfa(soup)

    def _has_otp(self, soup: BeautifulSoup) -> bool:
        """Check if OTP challenge present."""
        return check_for_mfa(soup)

    def _has_cvf(self, soup: BeautifulSoup) -> bool:
        """Check if CVF challenge present."""
        return check_for_cvf(soup)

    def _has_approval_alert(self, soup: BeautifulSoup) -> bool:
        """Check if approval alert present."""
        return check_for_approval_alert(soup)


class LoginService:
    """Service for handling Audible login flow.

    Orchestrates login process: session setup, OAuth, initial login,
    challenge handling (delegated to ChallengeHandler), and result extraction.

    Args:
        device: Device to emulate
        captcha_callback: Function to solve CAPTCHA
        otp_callback: Function to get OTP code
        cvf_callback: Function to get CVF code
        approval_callback: Function to handle approval alerts

    Example:
        >>> with LoginService(device=IPHONE) as service:  # doctest: +SKIP
        ...     result = service.login(
        ...         username="user@example.com",
        ...         password="password",
        ...         country_code="us",
        ...         domain="com",
        ...         market_place_id="AF2M0KC94RCEA",
        ...     )
        >>> print(result.authorization_code)  # doctest: +SKIP
    """

    def __init__(
        self,
        device: "BaseDevice",
        captcha_callback: Callable[[str], str] | None = None,
        otp_callback: Callable[[], str] | None = None,
        cvf_callback: Callable[[], str] | None = None,
        approval_callback: Callable[[], Any] | None = None,
    ):
        self.device = device
        self._captcha_callback = captcha_callback
        self._otp_callback = otp_callback
        self._cvf_callback = cvf_callback
        self._approval_callback = approval_callback
        self._session: httpx.Client | None = None

    def __enter__(self) -> "LoginService":
        """Context manager entry."""
        return self

    def __exit__(self, *args: Any) -> None:
        """Context manager exit - cleanup session."""
        if self._session:
            self._session.close()

    def login(
        self,
        username: str,
        password: str,
        country_code: str,
        domain: str,
        market_place_id: str,
        with_username: bool = False,
    ) -> LoginResult:
        """Perform login flow.

        Args:
            username: Amazon email address or Audible username
            password: Amazon password
            country_code: Country code for Audible marketplace
            domain: Top level domain (e.g., "com", "de")
            market_place_id: Marketplace ID
            with_username: If True, login with Audible username instead of Amazon

        Returns:
            LoginResult with authorization code and device info

        Complexity: ~5
        """
        # Setup
        self._session = self._setup_session(domain, with_username, username)
        oauth_url, device_serial = self._build_oauth_url(
            country_code, domain, market_place_id, with_username
        )

        # Initial login
        code_verifier, soup, login_resp = self._perform_initial_login(
            username, password, oauth_url, domain, with_username
        )

        # Handle challenges (delegated to ChallengeHandler)
        challenge_handler = ChallengeHandler(
            self._session,
            username,
            password,
            self._captcha_callback,
            self._otp_callback,
            self._cvf_callback,
            self._approval_callback,
        )
        soup, last_resp = challenge_handler.handle_all_challenges(soup, login_resp)

        # Extract result
        authorization_code = self._extract_authorization_data(username, last_resp)

        return LoginResult(
            authorization_code=authorization_code,
            code_verifier=code_verifier,
            domain=domain,
            device_serial=device_serial,
            device=self.device,
        )

    def _setup_session(
        self, domain: str, with_username: bool, username: str
    ) -> httpx.Client:
        """Setup HTTP session with device headers.

        Args:
            domain: Top level domain
            with_username: Whether logging in with Audible username
            username: Username for validation logging

        Returns:
            Configured httpx.Client

        Complexity: ~3
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
            "User-Agent": self.device.user_agent,
            "Accept-Language": "en-US",
            "Accept-Encoding": "gzip",
        }
        init_cookies = build_init_cookies(self.device)

        return httpx.Client(
            base_url=base_url,
            headers=default_headers,
            cookies=init_cookies,
            follow_redirects=True,
        )

    def _build_oauth_url(
        self,
        country_code: str,
        domain: str,
        market_place_id: str,
        with_username: bool,
    ) -> tuple[str, str]:
        """Build OAuth URL and device serial.

        Args:
            country_code: Country code
            domain: Top level domain
            market_place_id: Marketplace ID
            with_username: Whether using Audible username

        Returns:
            Tuple of (oauth_url, device_serial)

        Complexity: ~2
        """
        code_verifier = create_code_verifier()
        oauth_url, device_serial = build_oauth_url(
            country_code=country_code,
            domain=domain,
            market_place_id=market_place_id,
            code_verifier=code_verifier,
            serial=self.device.device_serial,
            with_username=with_username,
        )
        # Store code_verifier for later extraction
        self._code_verifier = code_verifier
        return oauth_url, device_serial

    def _perform_initial_login(
        self,
        username: str,
        password: str,
        oauth_url: str,
        domain: str,
        with_username: bool,
    ) -> tuple[bytes, BeautifulSoup, httpx.Response]:
        """Perform initial login POST.

        Args:
            username: Username
            password: Password
            oauth_url: OAuth authorization URL
            domain: Top level domain
            with_username: Whether using Audible username

        Returns:
            Tuple of (code_verifier, response_soup, response)

        Complexity: ~4
        """
        assert self._session is not None, "Session not initialized"  # noqa: S101

        base_url = (
            f"https://www.audible.{domain}"
            if with_username
            else f"https://www.amazon.{domain}"
        )

        # Get OAuth page
        oauth_resp = self._session.get(oauth_url)
        oauth_soup = get_soup(oauth_resp)

        # Build login form data
        login_inputs = get_inputs_from_soup(oauth_soup)
        login_inputs["email"] = username
        login_inputs["password"] = password

        # Add encrypted metadata
        metadata = meta_audible_app(self.device.user_agent, base_url)
        login_inputs["metadata1"] = encrypt_metadata(metadata)

        # Submit login
        method, url = get_next_action_from_soup(oauth_soup, {"name": "signIn"})
        login_resp = self._session.request(method, url, data=login_inputs)
        login_soup = get_soup(login_resp)

        return self._code_verifier, login_soup, login_resp

    def _extract_authorization_data(
        self, username: str, last_resp: httpx.Response
    ) -> str:
        """Extract authorization code from response.

        Checks the final response URL and response history for the authorization code.

        Args:
            username: Username for logging
            last_resp: Last HTTP response after all challenges

        Returns:
            Authorization code

        Raises:
            Exception: If authorization code not found in response

        Complexity: ~4
        """
        # Check if auth code in final response URL
        authcode_url = None
        if b"openid.oa2.authorization_code" in last_resp.url.query:
            authcode_url = last_resp.url
        # Otherwise check response history (redirects)
        elif len(last_resp.history) > 0:
            for history in last_resp.history:
                if b"openid.oa2.authorization_code" in history.url.query:
                    authcode_url = history.url
                    break

        if authcode_url is None:
            raise Exception("Login failed. Please check the log.")

        logger.debug("Login confirmed for %s", username)

        return extract_code_from_url(authcode_url)


# Backward compatible wrapper function
def login(
    username: str,
    password: str,
    country_code: str,
    domain: str,
    market_place_id: str,
    device: "BaseDevice | None" = None,
    serial: str | None = None,
    with_username: bool = False,
    captcha_callback: Callable[[str], str] | None = None,
    otp_callback: Callable[[], str] | None = None,
    cvf_callback: Callable[[], str] | None = None,
    approval_callback: Callable[[], Any] | None = None,
) -> dict[str, Any]:
    """Login to Audible (backward compatible wrapper).

    This function maintains backward compatibility by wrapping LoginService.
    For new code, prefer using LoginService directly for better testability and control.

    Args:
        username: The Amazon email address
        password: The Amazon password
        country_code: The country code for the Audible marketplace
        domain: The top level domain for the Audible marketplace
        market_place_id: The id for the Audible marketplace
        device: The device to use for login. If None, uses default iPhone device
        serial: DEPRECATED - Use device parameter instead
        with_username: If True, login with Audible username instead of Amazon account
        captcha_callback: Custom callback for handling CAPTCHA
        otp_callback: Custom callback for providing OTP codes
        cvf_callback: Custom callback for providing CVF codes
        approval_callback: Custom callback for handling approval alerts

    Returns:
        Dict with authorization_code, code_verifier, domain, serial, and device

    .. deprecated:: v0.11.0
        The serial parameter is deprecated. Use device parameter instead.

    .. versionchanged:: v0.11.0
        Now uses LoginService internally. The function signature remains the same
        for backward compatibility.

    Example:
        >>> from audible.login_service import login  # doctest: +SKIP
        >>> from audible.device import IPHONE  # doctest: +SKIP
        >>> result = login(  # doctest: +SKIP
        ...     username="user@example.com",
        ...     password="password",
        ...     country_code="us",
        ...     domain="com",
        ...     market_place_id="AF2M0KC94RCEA",
        ...     device=IPHONE,
        ... )
    """
    import warnings  # noqa: PLC0415

    # Handle device parameter with backward compatibility
    if device is None:
        from .device import IPHONE  # noqa: PLC0415

        device = IPHONE

    # Handle backward compatibility with serial parameter
    if serial is not None:
        warnings.warn(
            "The 'serial' parameter is deprecated and will be removed in v0.12.0. "
            "Use 'device' parameter instead.",
            DeprecationWarning,
            stacklevel=2,
        )
        # Create a copy of device with the provided serial
        device = device.copy(device_serial=serial)

    # Use service class
    with LoginService(
        device=device,
        captcha_callback=captcha_callback,
        otp_callback=otp_callback,
        cvf_callback=cvf_callback,
        approval_callback=approval_callback,
    ) as service:
        result = service.login(
            username=username,
            password=password,
            country_code=country_code,
            domain=domain,
            market_place_id=market_place_id,
            with_username=with_username,
        )

    # Convert to dict for backward compatibility
    return {
        "authorization_code": result.authorization_code,
        "code_verifier": result.code_verifier,
        "domain": result.domain,
        "serial": result.device_serial,
        "device": result.device,
    }
