"""Login service for Audible authentication.

This module provides the LoginService class which orchestrates the complete
login flow including OAuth setup, credentials submission, and challenge handling.

The login process consists of:
1. HTTP session setup with device headers and cookies
2. OAuth URL generation with PKCE challenge
3. Initial login form submission (may require username-first flow)
4. Challenge resolution (CAPTCHA, MFA, OTP, CVF, Approval Alerts)
5. Authorization code extraction from final response

Example:
    .. code-block:: python

        from audible.device import IPHONE
        from audible.localization import Locale
        from audible.login_service import LoginService

        locale = Locale("us")
        with LoginService(device=IPHONE, locale=locale) as service:
            result = service.login(
                username="user@example.com",
                password="password",
            )
        print(result.authorization_code)

Note:
    The LoginService uses a context manager protocol to ensure proper cleanup
    of the HTTP session. Always use it with the `with` statement or manually
    call the cleanup methods.
"""

from __future__ import annotations

import logging
import os
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any
from urllib.parse import parse_qs

import httpx

from audible.login_service.base import (
    BaseChallengeCallback,
    BaseChallengeHandler,
    ChallengeContext,
)
from audible.login_service.challenges import (
    ApprovalAlertHandler,
    CaptchaChallengeHandler,
    CVFHandler,
    DefaultApprovalAlertCallback,
    DefaultCaptchaCallback,
    DefaultCVFCallback,
    DefaultMFAChoiceCallback,
    DefaultOTPCallback,
    MFAChoiceHandler,
    OTPHandler,
)
from audible.login_service.metadata1 import encrypt_metadata, meta_audible_app
from audible.login_service.pkce import PKCE
from audible.login_service.soup_page import SoupPage
from audible.login_service.url_builder import OAuthURLBuilder


if TYPE_CHECKING:
    from audible.device import BaseDevice
    from audible.localization import Locale


logger = logging.getLogger(__name__)


# ============================================================================
# Login Result
# ============================================================================


@dataclass
class LoginResult:
    """Result from successful login operation.

    This dataclass contains all information needed to complete device
    registration after successful authentication.

    Attributes:
        authorization_code: OAuth2 authorization code from Amazon. This code
            is exchanged for access/refresh tokens during device registration.
        pkce: PKCE instance containing the code verifier needed for token
            exchange. The verifier proves that the client requesting tokens
            is the same client that initiated the authorization.
        locale: Marketplace locale used for login (contains country code,
            domain, and marketplace ID).
        device: Device configuration that was used for login. Contains
            device serial, user agent, and other device-specific data.

    Example:
        .. code-block:: python

            result = LoginResult(
                authorization_code="amzn1.oa2-ac.example",
                pkce=PKCE.generate(),
                locale=Locale("us"),
                device=IPHONE,
            )

    Note:
        The authorization code has a short lifetime (typically 5 minutes).
        Use it immediately for device registration via the register module.
    """

    authorization_code: str
    pkce: PKCE
    locale: Locale
    device: BaseDevice

    @property
    def code_verifier(self) -> bytes:
        """Convenience property for PKCE verifier (for backward compatibility)."""
        return self.pkce.verifier

    @property
    def domain(self) -> str:
        """Convenience property for locale domain (for backward compatibility)."""
        return self.locale.domain

    @property
    def device_serial(self) -> str:
        """Convenience property for device serial (for backward compatibility)."""
        return self.device.device_serial


# ============================================================================
# Response Dumper (for debugging)
# ============================================================================


class _ResponseDumper:
    """Utility class for persisting HTML responses during login debugging.

    This class writes HTTP response bodies to disk when enabled via environment
    variables. It's useful for debugging login issues by capturing the exact
    HTML returned by Amazon at each step.

    The dumper is controlled by environment variables:
    - AUDIBLE_DUMP_LOGIN_HTML: Set to any non-empty value to enable dumping
    - AUDIBLE_DUMP_LOGIN_DIR: Directory for dump files (default: "test_logs")

    Files are named with timestamps and sequential counters:
    login_response_20250115_143022_001_captcha.html

    Attributes:
        _enabled: Whether dumping is enabled
        _directory: Directory path for dump files
        _counter: Sequential counter for file naming

    Example:
        .. code-block:: python

            import os
            os.environ["AUDIBLE_DUMP_LOGIN_HTML"] = "1"
            dumper = _ResponseDumper()
            dumper.dump(response, "captcha_page")

    Note:
        This is an internal utility class. Most users won't interact with it
        directly. It's automatically used by LoginService when debugging.
    """

    def __init__(self) -> None:
        """Initialize response dumper based on environment variables."""
        self._enabled = bool(os.environ.get("AUDIBLE_DUMP_LOGIN_HTML"))
        dir_override = os.environ.get("AUDIBLE_DUMP_LOGIN_DIR", "test_logs")
        self._directory = Path(dir_override)
        self._counter = 0
        if self._enabled:
            self._directory.mkdir(parents=True, exist_ok=True)

    def dump(self, resp: httpx.Response | None, label: str = "o") -> None:
        """Write HTTP response to disk if dumping is enabled.

        Args:
            resp: The HTTP response to dump, or None to skip.
            label: Label to include in filename for identification.

        Note:
            This method fails silently if writing fails to avoid disrupting
            the login flow. Errors are logged as warnings.
        """
        if not self._enabled or resp is None:
            return

        self._counter += 1
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        safe_label = label.replace(" ", "_")
        filename = (
            self._directory
            / f"login_response_{timestamp}_{self._counter:03d}_{safe_label}.html"
        )

        # Ensure response body is read
        resp.read()

        try:
            filename.write_text(resp.text, encoding="utf-8")
            logger.debug(f"Dumped response to {filename}")
        except OSError as exc:
            logger.warning(f"Failed to dump login response to {filename}: {exc}")


# Global instance for use in response hooks
_response_dumper = _ResponseDumper()


# ============================================================================
# Challenge Orchestrator
# ============================================================================


class ChallengeOrchestrator:
    """Orchestrates all challenge handlers in sequence.

    This class manages the challenge resolution loop by:
    1. Creating handler instances for each challenge type
    2. Checking each handler in order until one matches
    3. Resolving the detected challenge
    4. Repeating until no more challenges are found
    5. Preventing infinite loops with iteration limits

    The challenge order is important and follows Amazon's typical flow:
    1. CAPTCHA (if flagged as suspicious)
    2. MFA device choice (if multiple devices configured)
    3. OTP (one-time password entry)
    4. CVF (credential verification)
    5. Approval alert (notification-based approval)

    Attributes:
        _session: HTTP client session shared across all handlers
        _username: User's Amazon username
        _password: User's Amazon password
        _callbacks: Dict mapping challenge types to callback instances

    Example:
        .. code-block:: python

            orchestrator = ChallengeOrchestrator(
                session=httpx.Client(),
                username="user@example.com",
                password="secret",
            )
            final_page, final_resp = orchestrator.handle_all_challenges(
                initial_page,
                initial_resp,
            )

    Note:
        This class is used internally by LoginService. Most users won't
        need to interact with it directly.
    """

    def __init__(
        self,
        session: httpx.Client,
        username: str,
        password: str,
        captcha_callback: BaseChallengeCallback | None = None,
        mfa_choice_callback: BaseChallengeCallback | None = None,
        otp_callback: BaseChallengeCallback | None = None,
        cvf_callback: BaseChallengeCallback | None = None,
        approval_callback: BaseChallengeCallback | None = None,
    ):
        """Initialize orchestrator with session, credentials, and callbacks.

        Args:
            session: HTTP client session for making requests
            username: Amazon username/email
            password: Amazon password
            captcha_callback: Custom CAPTCHA callback or None for default
            mfa_choice_callback: Custom MFA choice callback or None for default
            otp_callback: Custom OTP callback or None for default
            cvf_callback: Custom CVF callback or None for default
            approval_callback: Custom approval callback or None for default
        """
        self._session = session
        self._username = username
        self._password = password
        self._callbacks = {
            "captcha": captcha_callback or DefaultCaptchaCallback(),
            "mfa_choice": mfa_choice_callback or DefaultMFAChoiceCallback(),
            "otp": otp_callback or DefaultOTPCallback(),
            "cvf": cvf_callback or DefaultCVFCallback(),
            "approval": approval_callback or DefaultApprovalAlertCallback(),
        }

    def _create_handlers(self, soup_page: SoupPage) -> list[BaseChallengeHandler]:
        """Create handler instances with the current soup_page.

        This method creates fresh handler instances for each iteration
        of the challenge loop. Handlers are created in priority order.

        Args:
            soup_page: The current page to pass to handlers

        Returns:
            list: List of handler instances in priority order

        Note:
            Handlers are created fresh each iteration because the soup_page
            changes as challenges are resolved.
        """
        return [
            CaptchaChallengeHandler(
                username=self._username,
                password=self._password,
                session=self._session,
                soup_page=soup_page,
                callback=self._callbacks["captcha"],
            ),
            MFAChoiceHandler(
                username=self._username,
                password=self._password,
                session=self._session,
                soup_page=soup_page,
                callback=self._callbacks["mfa_choice"],
            ),
            OTPHandler(
                username=self._username,
                password=self._password,
                session=self._session,
                soup_page=soup_page,
                callback=self._callbacks["otp"],
            ),
            CVFHandler(
                username=self._username,
                password=self._password,
                session=self._session,
                soup_page=soup_page,
                callback=self._callbacks["cvf"],
            ),
            ApprovalAlertHandler(
                username=self._username,
                password=self._password,
                session=self._session,
                soup_page=soup_page,
                callback=self._callbacks["approval"],
            ),
        ]

    def handle_all_challenges(
        self, initial_page: SoupPage, initial_resp: httpx.Response
    ) -> tuple[SoupPage, httpx.Response]:
        """Handle all challenges until none remain or iteration limit reached.

        This method implements the main challenge resolution loop:
        1. Create handlers for current page
        2. Check each handler for challenge detection
        3. Resolve first detected challenge
        4. Update current page and repeat
        5. Exit when no challenges detected or max iterations reached

        Args:
            initial_page: The page after initial login submission
            initial_resp: The HTTP response containing initial_page

        Returns:
            tuple[SoupPage, httpx.Response]: The final page and response after
                all challenges are resolved. The response URL should contain
                the authorization code.

        Raises:
            RuntimeError: If too many challenge iterations occur (possible
                infinite loop due to continuously failing challenges).

        Example:
            .. code-block:: python

                final_page, final_resp = orchestrator.handle_all_challenges(
                    page, resp
                )
                # Check for authorization code in final_resp.url

        Note:
            The iteration limit (20) prevents infinite loops if a challenge
            continuously fails and re-presents itself. This typically indicates
            a bug in a handler or an unrecognized challenge variant.
        """
        current_page = initial_page
        last_resp = initial_resp
        max_iterations = 20
        iteration = 0

        while iteration < max_iterations:
            iteration += 1
            challenge_found = False

            # Create fresh handlers with current page
            handlers = self._create_handlers(current_page)

            # Check each handler in priority order
            for handler in handlers:
                if handler.has_challenge():
                    handler_name = handler.__class__.__name__
                    logger.info(f"Detected challenge: {handler_name}")

                    # Resolve challenge and update current page
                    current_page = handler.resolve_challenge()
                    last_resp = current_page.resp
                    _response_dumper.dump(last_resp, handler_name)

                    challenge_found = True
                    break  # Start over with new page

            if not challenge_found:
                logger.info("No more challenges detected")
                break

        if iteration >= max_iterations:
            raise RuntimeError(
                f"Too many challenge iterations ({iteration}) - possible infinite loop. "
                "This typically means a challenge is failing repeatedly."
            )

        return current_page, last_resp


# ============================================================================
# Login Service
# ============================================================================


class LoginService:
    """Service for orchestrating the complete Audible login flow.

    This class provides a high-level interface for authenticating with Amazon/
    Audible and obtaining an OAuth2 authorization code. It handles:

    - HTTP session setup with device-specific headers and cookies
    - OAuth URL generation with PKCE challenge
    - Initial login form submission (including username-first flow)
    - All authentication challenges (CAPTCHA, MFA, OTP, CVF, approval alerts)
    - Authorization code extraction from redirect URL

    The service uses the context manager protocol to ensure proper cleanup
    of the HTTP session.

    Attributes:
        device: Device configuration to emulate (e.g., IPHONE, ANDROID)
        locale: Marketplace locale (country code, domain, marketplace ID)

    Example:
        .. code-block:: python

            from audible.device import IPHONE
            from audible.localization import Locale

            locale = Locale("us")
            with LoginService(device=IPHONE, locale=locale) as service:
                result = service.login(
                    username="user@example.com",
                    password="password",
                )
                print(f"Authorization code: {result.authorization_code}")

    Note:
        Always use LoginService as a context manager (with `with` statement)
        to ensure the HTTP session is properly closed. Alternatively, manually
        call __exit__() after login is complete.
    """

    def __init__(
        self,
        device: BaseDevice,
        locale: Locale,
        captcha_callback: BaseChallengeCallback | None = None,
        mfa_choice_callback: BaseChallengeCallback | None = None,
        otp_callback: BaseChallengeCallback | None = None,
        cvf_callback: BaseChallengeCallback | None = None,
        approval_callback: BaseChallengeCallback | None = None,
    ):
        """Initialize login service with device and locale configuration.

        Args:
            device: Device configuration to emulate during login
            locale: Marketplace locale for login
            captcha_callback: Custom CAPTCHA callback or None for default
            mfa_choice_callback: Custom MFA choice callback or None for default
            otp_callback: Custom OTP callback or None for default
            cvf_callback: Custom CVF callback or None for default
            approval_callback: Custom approval callback or None for default
        """
        self.device = device
        self.locale = locale
        self._captcha_callback = captcha_callback
        self._mfa_choice_callback = mfa_choice_callback
        self._otp_callback = otp_callback
        self._cvf_callback = cvf_callback
        self._approval_callback = approval_callback
        self._session: httpx.Client | None = None

    def __enter__(self) -> LoginService:
        """Context manager entry.

        Returns:
            LoginService: self for use in with statement
        """
        return self

    def __exit__(self, *args: Any) -> None:
        """Context manager exit - cleanup HTTP session.

        Args:
            *args: Exception information (unused)
        """
        if self._session:
            self._session.close()
            self._session = None

    def login(
        self,
        username: str,
        password: str,
        with_username: bool = False,
    ) -> LoginResult:
        """Perform complete login flow and return authorization code.

        This is the main entry point for authentication. It orchestrates:
        1. Session setup with device headers
        2. PKCE generation for OAuth
        3. OAuth URL building
        4. Initial login submission
        5. Challenge resolution (all types)
        6. Authorization code extraction

        Args:
            username: Amazon email address or Audible username
            password: Account password
            with_username: If True, login with Audible username instead of
                Amazon email (only supported for DE, US, UK marketplaces)

        Returns:
            LoginResult: Contains authorization code, PKCE verifier, locale,
                and device information needed for registration

        Raises:
            ValueError: If with_username is True for unsupported marketplace
            RuntimeError: If authorization code cannot be extracted or if
                too many challenge iterations occur
            ChallengeError: If any challenge resolution fails

        Example:
            .. code-block:: python

                with LoginService(IPHONE, Locale("us")) as service:
                    result = service.login("user@example.com", "password")
                    # Use result.authorization_code for registration

        Note:
            The with_username parameter is only supported for DE, US, and UK
            marketplaces due to Amazon's regional differences. For other
            regions, use standard Amazon email login.
        """
        # Setup session and OAuth
        self._session = self._setup_session(with_username)
        pkce = PKCE.generate()
        oauth_url = self._build_oauth_url(pkce, with_username)

        # Perform initial login
        soup_page, login_resp = self._perform_initial_login(
            username, password, oauth_url, with_username
        )

        # Handle all challenges
        orchestrator = ChallengeOrchestrator(
            session=self._session,
            username=username,
            password=password,
            captcha_callback=self._captcha_callback,
            mfa_choice_callback=self._mfa_choice_callback,
            otp_callback=self._otp_callback,
            cvf_callback=self._cvf_callback,
            approval_callback=self._approval_callback,
        )
        soup_page, last_resp = orchestrator.handle_all_challenges(soup_page, login_resp)

        # Extract authorization code
        authorization_code = self._extract_authorization_code(last_resp)

        return LoginResult(
            authorization_code=authorization_code,
            pkce=pkce,
            locale=self.locale,
            device=self.device,
        )

    def _setup_session(self, with_username: bool) -> httpx.Client:
        """Setup HTTP session with device headers and cookies.

        Args:
            with_username: Whether using Audible username login

        Returns:
            httpx.Client: Configured HTTP session
        """
        if with_username:
            base_url = f"https://www.audible.{self.locale.domain}"
            logger.info("Login with Audible username")
        else:
            base_url = f"https://www.amazon.{self.locale.domain}"
            logger.info("Login with Amazon Account")

        default_headers = {
            "User-Agent": self.device.user_agent,
            "Accept-Language": "en-US",
            "Accept-Encoding": "gzip",
        }

        return httpx.Client(
            base_url=base_url,
            headers=default_headers,
            cookies=self.device.get_init_cookies(),
            follow_redirects=True,
            event_hooks={"response": [lambda r: _response_dumper.dump(r)]},
        )

    def _build_oauth_url(self, pkce: PKCE, with_username: bool) -> str:
        """Build OAuth authorization URL.

        Args:
            pkce: PKCE instance with code verifier and challenge
            with_username: Whether using Audible username login

        Returns:
            str: Complete OAuth URL
        """
        builder = OAuthURLBuilder(
            locale=self.locale,
            pkce=pkce,
            device=self.device,
            with_username=with_username,
        )
        return builder.build()

    def _perform_initial_login(
        self,
        username: str,
        password: str,
        oauth_url: str,
        with_username: bool,
    ) -> tuple[SoupPage, httpx.Response]:
        """Perform initial login form submission.

        Args:
            username: Amazon username or email
            password: Account password
            oauth_url: OAuth authorization URL
            with_username: Whether using Audible username login

        Returns:
            tuple[SoupPage, httpx.Response]: Initial response page and HTTP response
        """
        assert self._session is not None

        base_url = (
            f"https://www.audible.{self.locale.domain}"
            if with_username
            else f"https://www.amazon.{self.locale.domain}"
        )

        # Get OAuth page
        oauth_resp = self._session.get(oauth_url)
        oauth_page = SoupPage(oauth_resp)

        # Build login form
        login_inputs = oauth_page.get_form_inputs()
        login_inputs["email"] = username
        login_inputs["password"] = password

        # Add encrypted metadata
        metadata = meta_audible_app(self.device.user_agent, base_url)
        login_inputs["metadata1"] = encrypt_metadata(metadata)

        return self._submit_initial_login_form(
            oauth_page, login_inputs, username, password
        )

    def _submit_initial_login_form(
        self,
        initial_page: SoupPage,
        login_inputs: dict[str, str],
        username: str,
        password: str,
    ) -> tuple[SoupPage, httpx.Response]:
        """Handle username-first flow if required.

        Amazon sometimes requires a two-step login:
        1. Submit username only
        2. Submit password on next page

        This method detects and handles both flows.

        Args:
            initial_page: OAuth page with login form
            login_inputs: Form inputs to submit
            username: Username for second step
            password: Password for second step

        Returns:
            tuple[SoupPage, httpx.Response]: Login response page and HTTP response
        """
        assert self._session is not None

        app_action = (login_inputs.get("appAction") or "").upper()
        sub_page = login_inputs.get("subPageType", "")
        requires_username_first = (
            app_action == "SIGNIN_PWD_COLLECT" or sub_page == "SignInClaimCollect"
        )

        if not requires_username_first:
            # Standard single-step login
            method, url = initial_page.get_next_action({"name": "signIn"})
            resp = self._session.request(method, url, data=login_inputs)
            return SoupPage(resp), resp

        # Username-first flow
        username_payload = dict(login_inputs)
        username_payload["email"] = username
        username_payload.pop("password", None)

        method, url = initial_page.get_next_action({"name": "signIn"})
        resp = self._session.request(method, url, data=username_payload)
        login_page = SoupPage(resp)

        # Now submit password
        password_inputs = login_page.get_form_inputs()
        password_inputs["email"] = username
        password_inputs["password"] = password

        method, url = login_page.get_next_action({"name": "signIn"})
        resp = self._session.request(method, url, data=password_inputs)
        return SoupPage(resp), resp

    def _extract_authorization_code(self, last_resp: httpx.Response) -> str:
        """Extract authorization code from response URL.

        Args:
            last_resp: Final HTTP response after all challenges

        Returns:
            str: OAuth2 authorization code

        Raises:
            RuntimeError: If authorization code not found in response
        """
        authcode_url = None

        # Check final URL
        if b"openid.oa2.authorization_code" in last_resp.url.query:
            authcode_url = last_resp.url
        # Check redirect history
        elif last_resp.history:
            for history in last_resp.history:
                if b"openid.oa2.authorization_code" in history.url.query:
                    authcode_url = history.url
                    break

        if authcode_url is None:
            raise RuntimeError(
                "Login failed - no authorization code in response. Check logs for errors."
            )

        parsed_url = parse_qs(authcode_url.query.decode())
        authorization_code = parsed_url["openid.oa2.authorization_code"][0]

        logger.debug("Login successful, authorization code extracted")
        return authorization_code
