"""Custom exceptions for login service and challenge handling.

This module defines all custom exceptions used by the login service module.
All exceptions inherit from the base ChallengeError class, making it easy
to catch all challenge-related errors with a single except clause.

Exception Hierarchy:
    ChallengeError (base)
    ├── CaptchaExtractionError
    ├── MFAError
    └── CallbackError

Example:
    Catching all challenge errors:

    .. code-block:: python

        from audible.login_service.exceptions import ChallengeError

        try:
            result = service.login(username, password)
        except ChallengeError as e:
            logger.error(f"Challenge failed: {e}")

    Catching specific errors:

    .. code-block:: python

        from audible.login_service.exceptions import CaptchaExtractionError

        try:
            handler.resolve_challenge()
        except CaptchaExtractionError:
            logger.error("Failed to extract CAPTCHA URL")

Note:
    All exceptions defined here are exported from the main
    login_service.__init__ module for convenient access.
"""

from __future__ import annotations


# ============================================================================
# Custom Exceptions
# ============================================================================


class ChallengeError(Exception):
    """Base exception for all challenge-related errors.

    This is the parent class for all exceptions that may occur during
    challenge detection or resolution. Catching this exception will catch
    all challenge-specific errors.

    Example:
        .. code-block:: python

            try:
                handler.resolve_challenge()
            except ChallengeError as e:
                logger.error(f"Challenge failed: {e}")
    """


class CaptchaExtractionError(ChallengeError):
    """Raised when CAPTCHA URL cannot be extracted from page.

    This exception occurs when the CAPTCHA image element or its URL attribute
    cannot be found or parsed from the Amazon login page structure.

    Example:
        .. code-block:: python

            try:
                captcha_url = handler._extract_captcha_url()
            except CaptchaExtractionError:
                logger.error("Could not find CAPTCHA image")
    """


class MFAError(ChallengeError):
    """Raised when MFA challenge cannot be resolved.

    This exception occurs when multi-factor authentication fails, such as
    when no MFA devices are available or the selected device is invalid.

    Example:
        .. code-block:: python

            try:
                handler.resolve_challenge()
            except MFAError as e:
                logger.error(f"MFA failed: {e}")
    """


class CallbackError(ChallengeError):
    """Raised when callback execution fails.

    This exception wraps errors that occur during callback execution, such as
    network errors when downloading CAPTCHA images or user input validation
    failures.

    Example:
        .. code-block:: python

            try:
                result = callback(context)
            except CallbackError as e:
                logger.error(f"Callback failed: {e}")
    """
