"""CAPTCHA challenge handler and callback.

This module provides the handler and default callback for resolving visual
CAPTCHA challenges during Amazon/Audible authentication.

The CAPTCHA challenge typically appears when:
- Logging in from a new device or location
- Multiple failed login attempts have occurred
- Amazon's fraud detection systems flag suspicious activity

The handler automatically:
1. Detects CAPTCHA challenges on the page
2. Extracts the CAPTCHA image URL
3. Calls the callback to get the user's solution
4. Submits the complete login form with credentials and CAPTCHA answer

Example:
    .. code-block:: python

        import httpx
        from audible.login_service.challenges import (
            CaptchaChallengeHandler,
            DefaultCaptchaCallback,
        )
        from audible.login_service.soup_page import SoupPage

        session = httpx.Client()
        page = SoupPage(response)
        callback = DefaultCaptchaCallback()

        handler = CaptchaChallengeHandler(
            username="user@example.com",
            password="secret",
            session=session,
            soup_page=page,
            callback=callback,
        )

        if handler.has_challenge():
            next_page = handler.resolve_challenge()

Note:
    For automated testing, use MockCaptchaCallback from tests/login_dir/mocks.py
    instead of DefaultCaptchaCallback to avoid user interaction.
"""

from __future__ import annotations

import io
import logging
from dataclasses import dataclass
from typing import TYPE_CHECKING

import httpx
from bs4 import Tag
from PIL import Image

from audible.login_service.base import (
    DEFAULT_HTTP_TIMEOUT,
    FALSE_VALUE,
    FORM_FIELD_EMAIL,
    FORM_FIELD_GUESS,
    FORM_FIELD_PASSWORD,
    FORM_FIELD_SHOW_PASSWORD,
    FORM_FIELD_USE_AUDIO_CAPTCHA,
    FORM_FIELD_USE_IMAGE_CAPTCHA,
    TRUE_VALUE,
    BaseChallengeCallback,
    BaseChallengeHandler,
    ChallengeContext,
    ChallengeType,
    is_captcha_image,
)
from audible.login_service.exceptions import CallbackError, CaptchaExtractionError
from audible.login_service.soup_page import SoupPage


if TYPE_CHECKING:
    pass


logger = logging.getLogger(__name__)


# ============================================================================
# CAPTCHA Callback
# ============================================================================


class DefaultCaptchaCallback(BaseChallengeCallback):
    """Default CAPTCHA callback that displays image and prompts for input.

    This callback downloads the CAPTCHA image from the provided URL, displays
    it using the system's default image viewer, and prompts the user for input
    via console.

    The callback handles:
    - Downloading CAPTCHA image with configurable timeout
    - Displaying image using PIL.Image.show()
    - Console input prompt with automatic whitespace stripping and lowercase

    Attributes:
        challenge_type: Set to ChallengeType.CAPTCHA
        timeout: HTTP timeout for downloading CAPTCHA image in seconds.
            Default is 10.0 seconds.

    Example:
        .. code-block:: python

            callback = DefaultCaptchaCallback(timeout=15.0)
            context = ChallengeContext(
                challenge_type=ChallengeType.CAPTCHA,
                description="demo",
                captcha_url="https://example.com/captcha.jpg"
            )
            solution = callback(context)
            # Answer for CAPTCHA: abc123
            # solution
            # 'abc123'

    Note:
        This callback performs blocking I/O operations and displays a GUI
        window. It is not suitable for:
        - Automated testing (use MockCaptchaCallback from tests/)
        - Headless environments (implement custom callback)
        - Concurrent operations (blocks on user input)
    """

    challenge_type = ChallengeType.CAPTCHA

    def __init__(self, timeout: float = DEFAULT_HTTP_TIMEOUT) -> None:
        """Initialize the CAPTCHA callback.

        Args:
            timeout: HTTP timeout in seconds for downloading CAPTCHA image.
                Default is 10.0 seconds.
        """
        self.timeout = timeout

    def _resolve_challenge(self, context: ChallengeContext) -> str:
        """Display CAPTCHA image and prompt user for solution.

        Args:
            context: Challenge context containing the CAPTCHA URL.

        Returns:
            str: User's CAPTCHA solution (lowercase, stripped of whitespace).

        Raises:
            CallbackError: If CAPTCHA image cannot be downloaded or displayed,
                or if the context is missing the captcha_url field.
        """
        if not context.captcha_url:
            msg = "ChallengeContext missing captcha_url for CAPTCHA challenge"
            raise CallbackError(msg)

        captcha_url = context.captcha_url

        try:
            response = httpx.get(captcha_url, timeout=self.timeout)
            response.raise_for_status()

            with io.BytesIO(response.content) as image_buffer:
                with Image.open(image_buffer) as img:
                    img.show()

            guess = input("Answer for CAPTCHA: ")
            return guess.strip().lower()

        except httpx.HTTPError as e:
            msg = f"Failed to download CAPTCHA from {captcha_url}: {e}"
            raise CallbackError(msg) from e
        except Exception as e:
            msg = f"Failed to display CAPTCHA: {e}"
            raise CallbackError(msg) from e

    def get_description(self) -> str:
        """Return description of this callback.

        Returns:
            str: Human-readable description of the callback's behavior.
        """
        return "Display CAPTCHA image and prompt for console input"


# ============================================================================
# CAPTCHA Handler
# ============================================================================


@dataclass
class CaptchaChallengeHandler(BaseChallengeHandler):
    """Handler for Amazon login CAPTCHA challenges.

    This class manages the detection and resolution of CAPTCHA challenges
    during the Amazon authentication process. It automatically extracts the
    CAPTCHA image URL, obtains a solution from the user via callback, and
    submits the complete login form with credentials and CAPTCHA answer.

    The handler inherits all attributes from BaseChallengeHandler:
    - username: Amazon account email (REQUIRED)
    - password: Amazon account password (REQUIRED)
    - session: HTTP client session
    - soup_page: Parsed page with CAPTCHA challenge
    - callback: CAPTCHA callback (REQUIRED)
    - log_errors: Enable error logging

    The CAPTCHA submission includes:
    - User credentials (email and password)
    - CAPTCHA answer from callback
    - CAPTCHA type flags (image/audio)
    - Password visibility flag

    Example:
        .. code-block:: python

            import httpx
            from audible.login_service.soup_page import SoupPage

            session = httpx.Client()
            page = SoupPage(response)
            callback = DefaultCaptchaCallback()

            handler = CaptchaChallengeHandler(
                username="user@example.com",
                password="secret",
                session=session,
                soup_page=page,
                callback=callback,
            )

            if handler.has_challenge():
                next_page = handler.resolve_challenge()

    Note:
        For testing, use MockCaptchaCallback to avoid user interaction:

        .. code-block:: python

            from tests.login_dir.mocks import MockCaptchaCallback
            callback = MockCaptchaCallback("test_solution")
            handler = CaptchaChallengeHandler(..., callback=callback)
    """

    callback: BaseChallengeCallback

    def __post_init__(self) -> None:
        """Validate CAPTCHA handler configuration.

        Ensures username, password, and callback are provided, as they are
        required for CAPTCHA resolution.

        Raises:
            TypeError: If callback is not BaseChallengeCallback.
            ValueError: If username or password is None.
        """
        super().__post_init__()  # Validates callback type

        if not self.username:
            msg = "Username is required for CAPTCHA resolution"
            raise ValueError(msg)

        if not self.password:
            msg = "Password is required for CAPTCHA resolution"
            raise ValueError(msg)

    def _find_captcha_element(self) -> Tag | None:
        """Find the CAPTCHA image element in the page.

        Searches for an img tag with an alt attribute containing "CAPTCHA".
        This is Amazon's standard CAPTCHA image identification.

        Returns:
            Tag | None: The CAPTCHA img element if found, None otherwise.

        Example:
            .. code-block:: python

                captcha = handler._find_captcha_element()
                if captcha:
                    print(captcha.get("src"))
        """
        return self.soup_page.soup.find("img", alt=is_captcha_image)

    def has_challenge(self) -> bool:
        """Check if a CAPTCHA challenge is present on the current page.

        Returns:
            bool: True if a CAPTCHA image element is found, False otherwise.

        Example:
            .. code-block:: python

                if handler.has_challenge():
                    print("CAPTCHA detected")
        """
        return self._find_captcha_element() is not None

    def _extract_captcha_url(self) -> str:
        """Extract the CAPTCHA image URL from the login page.

        Returns:
            str: The URL of the CAPTCHA image.

        Raises:
            CaptchaExtractionError: If CAPTCHA element is not found, is not
                a valid Tag, or does not have a valid src attribute.

        Example:
            .. code-block:: python

                url = handler._extract_captcha_url()
                # url
                # 'https://images-na.ssl-images-amazon.com/captcha/...'
        """
        captcha = self._find_captcha_element()

        if captcha is None:
            msg = "No CAPTCHA element found in page"
            raise CaptchaExtractionError(msg)

        if not isinstance(captcha, Tag):
            msg = "CAPTCHA element is not a valid Tag"
            raise CaptchaExtractionError(msg)

        src = captcha.get("src")
        if not isinstance(src, str):
            msg = "CAPTCHA src attribute is missing or invalid"
            raise CaptchaExtractionError(msg)

        return src

    def _build_form_inputs(self, captcha_guess: str) -> dict[str, str]:
        """Build form input data with credentials and CAPTCHA guess.

        This method takes the base form inputs from the page and adds:
        - User's CAPTCHA solution
        - Login credentials (email and password)
        - CAPTCHA-specific flags

        Args:
            captcha_guess: User's CAPTCHA solution.

        Returns:
            dict[str, str]: Complete form data ready for submission to
                Amazon's login endpoint.

        Note:
            This method modifies a copy of the form inputs obtained from
            the page, so the original page data remains unchanged.
        """
        inputs = self.soup_page.get_form_inputs()
        inputs[FORM_FIELD_GUESS] = captcha_guess
        inputs[FORM_FIELD_USE_IMAGE_CAPTCHA] = TRUE_VALUE
        inputs[FORM_FIELD_USE_AUDIO_CAPTCHA] = FALSE_VALUE
        inputs[FORM_FIELD_SHOW_PASSWORD] = FALSE_VALUE
        inputs[FORM_FIELD_EMAIL] = self.username  # type: ignore[assignment]
        inputs[FORM_FIELD_PASSWORD] = self.password  # type: ignore[assignment]
        return inputs

    def resolve_challenge(self) -> SoupPage:
        """Resolve the CAPTCHA challenge by submitting user input.

        This method performs the complete CAPTCHA resolution workflow:
        1. Extracts the CAPTCHA image URL from the page
        2. Calls the callback to obtain user's solution
        3. Builds complete form data with credentials and CAPTCHA answer
        4. Submits the form to Amazon's login endpoint
        5. Returns the resulting page

        The resulting page may be:
        - Another challenge page (e.g., MFA after successful CAPTCHA)
        - An error page (e.g., incorrect CAPTCHA solution)
        - The final logged-in state

        Returns:
            SoupPage: The parsed page after CAPTCHA submission.

        Raises:
            CaptchaExtractionError: If CAPTCHA URL cannot be extracted from
                the page structure.
            CallbackError: If callback execution fails.
            httpx.HTTPError: If the submission request fails due to network
                errors or server responses.
            ValueError: If credentials are invalid or missing.

        Example:
            .. code-block:: python

                try:
                    next_page = handler.resolve_challenge()
                    print("CAPTCHA resolved successfully")
                except CaptchaExtractionError as e:
                    logger.error(f"Failed to find CAPTCHA: {e}")

        Note:
            This method may perform blocking I/O operations depending on
            the callback implementation. The default callback blocks on
            user input.
        """
        try:
            captcha_url = self._extract_captcha_url()
            context = ChallengeContext(
                challenge_type=ChallengeType.CAPTCHA,
                description="Amazon image CAPTCHA challenge",
                soup_page=self.soup_page,
                captcha_url=captcha_url,
            )
            guess = self.callback(context)
            inputs = self._build_form_inputs(guess)

            method, url = self.soup_page.get_next_action({"name": "signIn"})
            login_resp = self.session.request(method, url, data=inputs)

            return SoupPage(login_resp)

        except (CaptchaExtractionError, CallbackError):
            # Re-raise challenge-specific errors without logging
            # (they're already descriptive)
            raise
        except Exception as e:
            self._log_error("CAPTCHA resolution failed", e)
            raise
