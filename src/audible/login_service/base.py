"""Base classes and shared types for challenge handlers.

This module provides the foundational abstract base classes and data structures
used by all authentication challenge handlers. It defines:

- Challenge types enumeration
- Context objects passed to callbacks
- Abstract base classes for handlers and callbacks
- Custom exceptions for challenge resolution
- Shared constants and helper functions

The design uses Abstract Base Classes (ABC) instead of Protocols to enable
proper inheritance and code reuse across all challenge handlers.

Example:
    Creating a custom callback::

        from audible.login_service.base import BaseChallengeCallback, ChallengeContext

        class MyCustomCallback(BaseChallengeCallback):
            challenge_type = ChallengeType.CAPTCHA

            def _resolve_challenge(self, context: ChallengeContext) -> str:
                # Custom logic here
                return "my_solution"

Note:
    All challenge handlers must inherit from BaseChallengeHandler and implement
    the has_challenge() and resolve_challenge() methods.
"""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from collections.abc import Mapping
from dataclasses import dataclass
from enum import Enum
from typing import TYPE_CHECKING, Any, Final

from audible.login_service.exceptions import (
    CallbackError,
)


if TYPE_CHECKING:
    import httpx

    from audible.login_service.soup_page import SoupPage


# Module logger
logger = logging.getLogger(__name__)

# ============================================================================
# Form field constants
# ============================================================================

FORM_FIELD_GUESS: Final[str] = "guess"
FORM_FIELD_USE_IMAGE_CAPTCHA: Final[str] = "use_image_captcha"
FORM_FIELD_USE_AUDIO_CAPTCHA: Final[str] = "use_audio_captcha"
FORM_FIELD_NAME_SHOW_PASSWORD: Final[str] = "showPasswordChecked"  # noqa: S105
FORM_FIELD_NAME_EMAIL: Final[str] = "email"
FORM_FIELD_NAME_PASSWORD: Final[str] = "password"  # noqa: S105

# Form field values
TRUE_VALUE: Final[str] = "true"
FALSE_VALUE: Final[str] = "false"

# HTTP timeout
DEFAULT_HTTP_TIMEOUT: Final[float] = 10.0


# ============================================================================
# Challenge type definitions
# ============================================================================


class ChallengeType(str, Enum):
    """Enumeration of supported authentication challenge types.

    These challenge types correspond to the various authentication steps that
    Amazon/Audible may require during login. The order listed here reflects
    the typical order challenges appear during authentication.

    Attributes:
        CAPTCHA: Visual CAPTCHA image verification
        MFA_CHOICE: Multi-factor authentication device selection
        OTP: One-time password (2FA code) entry
        CVF: Credential verification form (email/SMS code)
        APPROVAL_ALERT: Approval notification via email/app
    """

    CAPTCHA = "captcha"
    MFA_CHOICE = "mfa_choice"
    OTP = "otp"
    CVF = "cvf"
    APPROVAL_ALERT = "approval_alert"


# ============================================================================
# Challenge context definitions
# ============================================================================


@dataclass(frozen=True, slots=True)
class MFADeviceOption:
    """Represents a single multi-factor authentication device option.

    When Amazon presents multiple MFA devices for selection (e.g., SMS, TOTP
    authenticator app, voice call), each option is represented by this class.

    Attributes:
        method: The MFA method type (e.g., "TOTP", "SMS", "VOICE")
        label: Human-readable label shown to the user
        input_name: HTML form input name for this option
        input_value: HTML form input value to submit when selected

    Example:
        >>> option = MFADeviceOption(
        ...     method="TOTP",
        ...     label="Authenticator App",
        ...     input_name="otpDeviceContext",
        ...     input_value="device123"
        ... )
    """

    method: str
    label: str
    input_name: str
    input_value: str


@dataclass(frozen=True, slots=True)
class MfaMethod:
    """Enhanced MFA method representation with user-friendly data.

    Extends MFADeviceOption with additional metadata for better UX.
    Used by enhanced MFA-Choice callback for interactive selection.

    Attributes:
        method_type: Type identifier (TOTP, SMS, VOICE, WhatsApp, etc.)
        value: Form value to submit when selecting this method
        label: Human-readable description from HTML
        is_default: Whether this option is pre-selected (checked attribute)

    Example:
        >>> method = MfaMethod(
        ...     method_type="TOTP",
        ...     value="deviceToken123, TOTP",
        ...     label="Authenticator-App eingeben",
        ...     is_default=True
        ... )
        >>> print(method.method_type)
        TOTP

    Note:
        This is similar to MFADeviceOption but focuses on user-facing data
        rather than raw form data. It's used for interactive selection.

    .. versionadded:: v0.11.0
        Enhanced MFA method representation for interactive device selection.
    """

    method_type: str
    value: str
    label: str
    is_default: bool


@dataclass(frozen=True, slots=True)
class OtpContext:
    """Context information for OTP input prompts.

    Provides users with details about where the OTP was sent, enabling
    better user experience during authentication.

    Attributes:
        destination: Where OTP was sent, extracted from page text
            (e.g., "number ending in 964")
        method_type: How it was sent, inferred from keywords
            (e.g., "SMS", "WhatsApp", "Email", "Voice Call")
        raw_message: Raw HTML message text for debugging/logging

    Example:
        >>> context = OtpContext(
        ...     destination="number ending in 964",
        ...     method_type="SMS",
        ...     raw_message="Code gesendet an Telefonnummer ... 964 endet"
        ... )
        >>> print(f"OTP sent via {context.method_type} to {context.destination}")
        OTP sent via SMS to number ending in 964

    Note:
        Used by enhanced OTP callback to show context-aware prompts.
        Method type may be None if it cannot be determined from the page.

    .. versionadded:: v0.11.0
        OTP context extraction for enhanced user prompts.
    """

    destination: str
    method_type: str | None
    raw_message: str


@dataclass(frozen=True, slots=True)
class ChallengeContext:
    """Context object passed to challenge callbacks.

    This immutable dataclass contains all information a callback might need
    to resolve a specific challenge. Instead of passing primitive values
    (like just a CAPTCHA URL string), we pass rich context that includes
    the challenge type, description, and challenge-specific data.

    Attributes:
        challenge_type: Type of challenge being resolved
        description: Human-readable description of the challenge
        soup_page: The parsed HTML page containing the challenge (optional)
        captcha_url: URL of CAPTCHA image (CAPTCHA challenges only)
        mfa_options: Available MFA devices (MFA_CHOICE challenges only)
        otp_hint: Hint text for OTP entry (OTP challenges only)
        cvf_hint: Hint text for CVF code entry (CVF challenges only)
        approval_url: URL being polled for approval (APPROVAL_ALERT only)
        extra: Additional context data for future extensions

    Example:
        >>> from audible.login_service.base import ChallengeContext, ChallengeType
        >>> context = ChallengeContext(
        ...     challenge_type=ChallengeType.CAPTCHA,
        ...     description="Amazon CAPTCHA verification",
        ...     captcha_url="https://images-na.ssl-images-amazon.com/..."
        ... )

    Note:
        This class is immutable (frozen=True) to prevent accidental modification
        during challenge resolution. Challenge-specific fields may be None if
        not applicable to the current challenge type.
    """

    challenge_type: ChallengeType
    description: str
    soup_page: SoupPage | None = None

    # Challenge-specific fields
    captcha_url: str | None = None
    mfa_options: list[MFADeviceOption] | None = None
    otp_hint: str | None = None
    cvf_hint: str | None = None
    approval_url: str | None = None

    # For future extensions
    extra: Mapping[str, Any] | None = None


# ============================================================================
# Callback ABC - Base class for all challenge callbacks
# ============================================================================


class BaseChallengeCallback(ABC):
    """Abstract base class for all challenge callbacks.

    This class defines the interface that all challenge callbacks must implement.
    Callbacks are responsible for obtaining user input or automated responses
    to authentication challenges.

    Using ABC ensures type safety and provides a consistent interface across
    different callback types. Each callback receives a ChallengeContext with
    all necessary information and returns a string response.

    Subclasses must:
    - Set the challenge_type class attribute (or leave None for generic callbacks)
    - Implement the _resolve_challenge() method

    The __call__() method is already implemented and handles:
    - Challenge type validation
    - Delegation to _resolve_challenge()

    Attributes:
        challenge_type: The specific challenge type this callback handles,
            or None for callbacks that can handle multiple types.

    Example:
        >>> class MyCallback(BaseChallengeCallback):
        ...     challenge_type = ChallengeType.CAPTCHA
        ...
        ...     def _resolve_challenge(self, context: ChallengeContext) -> str:
        ...         return "my_captcha_solution"
        ...
        ...     def get_description(self) -> str:
        ...         return "My custom CAPTCHA solver"

    Note:
        Callbacks should be stateless when possible to enable reuse across
        multiple challenge resolutions. If state is needed (e.g., call counting
        for testing), document it clearly.
    """

    challenge_type: ChallengeType | None = None

    def __call__(self, context: ChallengeContext) -> str:
        """Validate context and delegate to subclass implementation.

        This method is called by handlers to resolve challenges. It performs
        challenge type validation before delegating to _resolve_challenge().

        Args:
            context: Challenge context with all necessary information.

        Returns:
            str: The callback's response to the challenge (e.g., CAPTCHA
                solution, OTP code, selected device ID).

        Raises:
            CallbackError: If the context challenge type doesn't match the
                callback's supported type.

        Note:
            Subclasses should NOT override this method. Instead, implement
            _resolve_challenge().
        """
        expected = self.get_supported_challenge_type()
        if expected and context.challenge_type is not expected:
            msg = (
                f"{self.__class__.__name__} only supports {expected.value} "
                f"challenges; got {context.challenge_type.value}"
            )
            raise CallbackError(msg)

        return self._resolve_challenge(context)

    def get_supported_challenge_type(self) -> ChallengeType | None:
        """Return the challenge type this callback supports.

        Returns:
            ChallengeType | None: The supported challenge type, or None if
                the callback can handle multiple types.

        Note:
            The default implementation returns the challenge_type class attribute.
            Override this method if you need dynamic type determination.
        """
        return self.challenge_type

    @abstractmethod
    def _resolve_challenge(self, context: ChallengeContext) -> str:
        """Resolve the challenge and return the response.

        This is the core method that subclasses must implement. It receives
        a complete context object and returns the user's response.

        Args:
            context: Structured information about the current challenge,
                including challenge type, description, and challenge-specific
                data (CAPTCHA URL, MFA options, etc.).

        Returns:
            str: User's response to the challenge. The format depends on the
                challenge type:
                - CAPTCHA: The text solution to the CAPTCHA
                - MFA_CHOICE: The selected device's input_value
                - OTP: The one-time password code
                - CVF: The credential verification code
                - APPROVAL_ALERT: Any non-empty string (actual value ignored)

        Raises:
            CallbackError: If callback execution fails (e.g., network error,
                invalid input, user cancellation).

        Example:
            >>> def _resolve_challenge(self, context: ChallengeContext) -> str:
            ...     if context.challenge_type == ChallengeType.OTP:
            ...         code = input("Enter OTP: ")
            ...         return code.strip()
        """
        raise NotImplementedError

    def get_description(self) -> str:
        """Return a human-readable description of this callback.

        This method provides information about what the callback does,
        useful for logging, debugging, and user interfaces.

        Returns:
            str: Description of the callback's behavior.

        Example:
            .. code-block:: python

                callback = DefaultCaptchaCallback()
                print(callback.get_description())
                # 'Display CAPTCHA image and prompt for console input'

        Note:
            The default implementation returns a generic description based on
            the class name. Override this method to provide more detailed
            information about your callback's behavior.
        """
        return f"{self.__class__.__name__} callback"


# ============================================================================
# Handler ABC - Base class for all challenge handlers
# ============================================================================


@dataclass
class BaseChallengeHandler(ABC):
    """Abstract base class for all challenge handlers.

    This base class defines the common interface and shared attributes for all
    challenge handlers. Handlers are responsible for:
    - Detecting if a specific challenge type is present on a page
    - Resolving the challenge by interacting with the callback and server

    Using ABC instead of Protocol enables code reuse through inheritance and
    avoids repetition of attributes across handler classes.

    All concrete handlers must implement:
    - has_challenge(): Detect if this challenge type is present
    - resolve_challenge(): Resolve the challenge and return next page

    Attributes:
        username: User's Amazon account username/email. May be None for
            challenges that don't require credentials (e.g., approval alerts).
        password: User's Amazon account password. May be None for challenges
            that don't require credentials.
        session: HTTP client session for making authenticated requests.
            Shared across all handlers in a login flow.
        soup_page: Parsed HTML page containing the current challenge.
        callback: Callback instance for user interaction. NEVER None - each
            handler requires a concrete callback implementation.
        log_errors: Whether to log errors during challenge resolution.
            Default is True.

    Example:
        >>> @dataclass
        ... class MyHandler(BaseChallengeHandler):
        ...     def has_challenge(self) -> bool:
        ...         return bool(self.soup_page.soup.find("div", id="my-challenge"))
        ...
        ...     def resolve_challenge(self) -> SoupPage:
        ...         # Resolution logic here
        ...         return next_page

    Note:
        Subclasses can override __post_init__() to add their own validation
        logic. Always call super().__post_init__() to ensure base validation
        runs first.
    """

    username: str | None
    password: str | None
    session: httpx.Client
    soup_page: SoupPage
    callback: BaseChallengeCallback
    log_errors: bool = True

    @abstractmethod
    def has_challenge(self) -> bool:
        """Check if this handler's challenge type is present on the page.

        This method inspects the current soup_page to determine if the
        challenge can be detected. Each handler implements its own detection
        logic based on HTML structure, form IDs, or other page markers.

        Returns:
            bool: True if the challenge is detected in the current page,
                False otherwise.

        Example:
            .. code-block:: python

                if handler.has_challenge():
                    next_page = handler.resolve_challenge()

        Note:
            This method should be fast and side-effect free. It should only
            inspect the page structure, not make HTTP requests or modify state.
        """
        raise NotImplementedError

    @abstractmethod
    def resolve_challenge(self) -> SoupPage:
        """Resolve the detected challenge and return the resulting page.

        This method performs the complete challenge resolution workflow:
        1. Extract challenge data from the page
        2. Build a ChallengeContext with all necessary information
        3. Call the callback to get the user's response
        4. Submit the response to Amazon's servers
        5. Return the parsed response page

        The resulting page may be:
        - Another challenge page (e.g., OTP after successful CAPTCHA)
        - An error page (e.g., incorrect CAPTCHA solution)
        - The final logged-in state (authorization code in URL)

        Returns:
            SoupPage: The parsed page after challenge submission.

        Raises:
            ChallengeError: If challenge resolution fails. Specific exception
                types depend on the concrete handler implementation.

        Example:
            .. code-block:: python

                try:
                    next_page = handler.resolve_challenge()
                except CaptchaExtractionError as e:
                    logger.error(f"Failed to resolve: {e}")

        Note:
            This method may perform blocking I/O operations depending on the
            callback implementation. For example, the default CAPTCHA callback
            blocks on user input.
        """
        raise NotImplementedError

    def __post_init__(self) -> None:
        """Validate handler configuration after initialization.

        This method is called automatically by @dataclass after __init__.
        The base implementation validates that callback is a BaseChallengeCallback
        instance.

        Subclasses can override this to add their own validation logic, such as
        ensuring username and password are provided for challenges that require
        credentials.

        Raises:
            TypeError: If callback is not a BaseChallengeCallback instance.
            ValueError: If configuration is invalid (subclass-specific).

        Example:
            >>> def __post_init__(self) -> None:
            ...     super().__post_init__()  # Run base validation
            ...     if not self.username:
            ...         raise ValueError("Username required")

        Note:
            Always call super().__post_init__() when overriding to ensure base
            validation is performed.
        """
        if not isinstance(self.callback, BaseChallengeCallback):
            msg = (
                f"callback must be a BaseChallengeCallback instance, "
                f"got {type(self.callback).__name__}"
            )
            raise TypeError(msg)

    def _log_error(self, message: str, exc: Exception | None = None) -> None:
        """Log an error message if error logging is enabled.

        This is a convenience method for consistent error logging across
        all handlers. It respects the log_errors attribute.

        Args:
            message: Error message to log.
            exc: Optional exception to include in log. If provided, includes
                full traceback via exc_info=True.

        Example:
            .. code-block:: python

                try:
                    risky_operation()
                except Exception as e:
                    handler._log_error("Operation failed", e)
                    raise

        Note:
            This method only logs if log_errors is True. It does not suppress
            exceptions - callers should re-raise after logging if needed.
        """
        if self.log_errors:
            if exc is not None:
                logger.error(message, exc_info=True)
            else:
                logger.error(message)


# ============================================================================
# Helper Functions
# ============================================================================


def is_captcha_image(alt_text: str | None) -> bool:
    """Check if alt text indicates a CAPTCHA image.

    This helper function is used to identify CAPTCHA images in HTML by
    checking if the alt attribute contains the word "CAPTCHA".

    Args:
        alt_text: The alt attribute value of an img tag, may be None.

    Returns:
        bool: True if alt text contains "CAPTCHA" (case-sensitive),
            False otherwise or if alt_text is None.

    Example:
        >>> is_captcha_image("Enter CAPTCHA code")
        True
        >>> is_captcha_image("Amazon logo")
        False
        >>> is_captcha_image(None)
        False

    Note:
        This function performs case-sensitive matching. Amazon's CAPTCHA
        images consistently use uppercase "CAPTCHA" in alt text.
    """
    return alt_text is not None and "CAPTCHA" in alt_text
