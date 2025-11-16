"""Modern login implementation for Audible.

This package provides a clean, modular architecture for Amazon/Audible authentication.
It supersedes the old login_service.py with a more maintainable design based on
abstract base classes, dependency injection, and separation of concerns.

Main Components:
    - LoginService: Orchestrates the complete login flow
    - LoginResult: Dataclass containing authorization code and metadata
    - Challenge Handlers: Modular handlers for each authentication challenge
    - Default Callbacks: Console-based callbacks for user interaction
    - Base Classes: Abstract base classes for extending functionality

Supported Challenges:
    - CAPTCHA: Visual image verification
    - MFA Choice: Multi-factor authentication device selection
    - OTP: One-time password (2FA code) entry
    - CVF: Credential verification form (email/SMS code)
    - Approval Alert: Email/app notification approval

Example:
    Basic login flow::

        from audible.device import IPHONE
        from audible.localization import Locale
        from audible.login_service import LoginService

        locale = Locale("us")
        with LoginService(device=IPHONE, locale=locale) as service:
            result = service.login(
                username="user@example.com",
                password="password",
            )
            print(f"Authorization code: {result.authorization_code}")

    Custom callbacks::

        from audible.login_service import LoginService
        from audible.login_service.challenges import DefaultCaptchaCallback

        # Use custom timeout for CAPTCHA download
        custom_captcha = DefaultCaptchaCallback(timeout=30.0)

        with LoginService(
            device=IPHONE,
            locale=locale,
            captcha_callback=custom_captcha,
        ) as service:
            result = service.login("user@example.com", "password")

Note:
    This module is part of the audible package's public API. The old
    login_service.py is deprecated and will be removed in v0.12.0.

.. versionadded:: v0.11.0
   Complete rewrite with modular challenge handlers and abstract base classes.
"""

from __future__ import annotations

# Base classes for extensibility
from .base import (
    BaseChallengeCallback,
    BaseChallengeHandler,
    ChallengeContext,
    ChallengeType,
    MFADeviceOption,
    MfaMethod,
    OtpContext,
)

# Challenge handlers (advanced usage)
# Default callbacks (can be customized)
from .challenges import (
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

# Exceptions
from .exceptions import (
    CallbackError,
    CaptchaExtractionError,
    ChallengeError,
    MFAError,
)

# Core login functionality
from .login import LoginResult, LoginService

# Utility modules (typically used internally)
from .metadata1 import decrypt_metadata, encrypt_metadata, meta_audible_app
from .pkce import PKCE
from .soup_page import SoupPage
from .url_builder import OAuthURLBuilder


__all__ = [
    "PKCE",
    "ApprovalAlertHandler",
    "BaseChallengeCallback",
    "BaseChallengeHandler",
    "CVFHandler",
    "CallbackError",
    "CaptchaChallengeHandler",
    "CaptchaExtractionError",
    "ChallengeContext",
    "ChallengeError",
    "ChallengeType",
    "DefaultApprovalAlertCallback",
    "DefaultCVFCallback",
    "DefaultCaptchaCallback",
    "DefaultMFAChoiceCallback",
    "DefaultOTPCallback",
    "LoginResult",
    "LoginService",
    "MFAChoiceHandler",
    "MFADeviceOption",
    "MFAError",
    "MfaMethod",
    "OAuthURLBuilder",
    "OTPHandler",
    "OtpContext",
    "SoupPage",
    "decrypt_metadata",
    "encrypt_metadata",
    "meta_audible_app",
]
