"""Challenge handlers and callbacks for Amazon authentication.

This package contains implementations of all authentication challenge handlers
and their default callbacks. Each challenge type (CAPTCHA, MFA, OTP, CVF,
Approval Alert) is implemented in its own module for clarity and maintainability.

All handlers inherit from BaseChallengeHandler and all callbacks inherit from
BaseChallengeCallback (defined in audible.login.base).

Available Handlers:
    - CaptchaChallengeHandler: Visual CAPTCHA verification
    - MFAChoiceHandler: Multi-factor authentication device selection
    - OTPHandler: One-time password (2FA code) entry
    - CVFHandler: Credential verification form (email/SMS code)
    - ApprovalAlertHandler: Approval notification via email/app

Available Callbacks:
    - DefaultCaptchaCallback: Display CAPTCHA and prompt for console input
    - DefaultMFAChoiceCallback: Automatically select TOTP if available
    - DefaultOTPCallback: Prompt for OTP code via console
    - DefaultCVFCallback: Prompt for CVF code via console
    - DefaultApprovalAlertCallback: Wait for user approval confirmation

Note:
    Mock callbacks for testing are NOT exported from this package. They are
    available in tests/login_dir/mocks.py for use in test suites only.

Example:
    .. code-block:: python

        from audible.login.challenges import (
            CaptchaChallengeHandler,
            DefaultCaptchaCallback,
        )
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
"""

from __future__ import annotations

from .approval_alert import ApprovalAlertHandler, DefaultApprovalAlertCallback
from .captcha import CaptchaChallengeHandler, DefaultCaptchaCallback
from .cvf import CVFHandler, DefaultCVFCallback
from .mfa_choice import DefaultMFAChoiceCallback, MFAChoiceHandler
from .otp import DefaultOTPCallback, OTPHandler


__all__ = [
    "ApprovalAlertHandler",
    "CVFHandler",
    "CaptchaChallengeHandler",
    "DefaultApprovalAlertCallback",
    "DefaultCVFCallback",
    "DefaultCaptchaCallback",
    "DefaultMFAChoiceCallback",
    "DefaultOTPCallback",
    "MFAChoiceHandler",
    "OTPHandler",
]
