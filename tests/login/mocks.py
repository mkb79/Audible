"""Mock callbacks for testing challenge handlers.

This module provides mock implementations of all challenge callbacks for use
in automated testing. Unlike the default callbacks which require user interaction
(console input, image display), these mocks return predetermined responses.

Mock callbacks are useful for:
- Unit testing challenge handlers
- Integration testing login flows
- CI/CD pipelines (no human interaction)
- Performance testing (no I/O delays)

Each mock callback:
- Inherits from BaseChallengeCallback
- Returns a configurable predetermined response
- Tracks call count for test assertions
- Stores the last context for verification

Example:
    >>> from tests.login.mocks import MockCaptchaCallback
    >>> from audible.login.base import ChallengeContext, ChallengeType
    >>>
    >>> callback = MockCaptchaCallback("test_solution")
    >>> context = ChallengeContext(
    ...     challenge_type=ChallengeType.CAPTCHA,
    ...     description="test",
    ...     captcha_url="https://example.com/captcha.jpg"
    ... )
    >>> solution = callback(context)
    >>> solution
    'test_solution'
    >>> callback.call_count
    1
    >>> callback.last_context.captcha_url
    'https://example.com/captcha.jpg'

Note:
    These mocks are ONLY for testing. They should never be imported into
    production code. The production code in src/audible/login/ should
    only use the Default callbacks.
"""

from __future__ import annotations

from audible.login.base import (
    BaseChallengeCallback,
    ChallengeContext,
    ChallengeType,
)


# ============================================================================
# Mock CAPTCHA Callback
# ============================================================================


class MockCaptchaCallback(BaseChallengeCallback):
    """Mock CAPTCHA callback for testing.

    This callback returns a predetermined response without user interaction,
    making it suitable for automated testing and CI/CD pipelines.

    Args:
        response: The response to return when called. Default is
            "mock_captcha_solution".

    Attributes:
        challenge_type: Set to ChallengeType.CAPTCHA

    Example:
        >>> callback = MockCaptchaCallback("test_solution")
        >>> context = ChallengeContext(
        ...     challenge_type=ChallengeType.CAPTCHA,
        ...     description="demo",
        ...     captcha_url="https://example.com/captcha.jpg"
        ... )
        >>> solution = callback(context)
        >>> solution
        'test_solution'
        >>> callback.call_count
        1
        >>> callback.last_context.captcha_url
        'https://example.com/captcha.jpg'
    """

    challenge_type = ChallengeType.CAPTCHA

    def __init__(self, response: str = "mock_captcha_solution") -> None:
        self.response = response
        self.call_count = 0
        self.last_context: ChallengeContext | None = None

    def _resolve_challenge(self, context: ChallengeContext) -> str:
        """Return predetermined response without user interaction.

        Args:
            context: Challenge context (stored for inspection).

        Returns:
            str: The predetermined response.
        """
        self.call_count += 1
        self.last_context = context
        return self.response

    def get_description(self) -> str:
        """Return description of this callback."""
        return f"Mock CAPTCHA callback returning '{self.response}'"


# ============================================================================
# Mock MFA Choice Callback
# ============================================================================


class MockMFAChoiceCallback(BaseChallengeCallback):
    """Mock MFA choice callback for testing.

    This callback returns a predetermined device selection without user
    interaction. Useful for testing MFA device selection flows.

    Args:
        selected_value: The device input_value to return when called.
            Default is "mock_device".

    Attributes:
        challenge_type: Set to ChallengeType.MFA_CHOICE

    Example:
        >>> callback = MockMFAChoiceCallback("device123")
        >>> context = ChallengeContext(
        ...     challenge_type=ChallengeType.MFA_CHOICE,
        ...     description="Select device",
        ...     mfa_options=[]
        ... )
        >>> selected = callback(context)
        >>> selected
        'device123'
        >>> callback.call_count
        1
    """

    challenge_type = ChallengeType.MFA_CHOICE

    def __init__(self, selected_value: str = "mock_device") -> None:
        self.selected_value = selected_value
        self.call_count = 0
        self.last_context: ChallengeContext | None = None

    def _resolve_challenge(self, context: ChallengeContext) -> str:
        """Return predetermined device selection.

        Args:
            context: Challenge context (stored for inspection).

        Returns:
            str: The predetermined device input_value.
        """
        self.call_count += 1
        self.last_context = context
        return self.selected_value

    def get_description(self) -> str:
        """Return description of this callback."""
        return f"Mock MFA choice callback selecting '{self.selected_value}'"


# ============================================================================
# Mock OTP Callback
# ============================================================================


class MockOTPCallback(BaseChallengeCallback):
    """Mock OTP callback for testing.

    This callback returns a predetermined OTP code without user interaction.
    Useful for testing OTP entry flows.

    Args:
        code: The OTP code to return when called. Default is "123456".

    Attributes:
        challenge_type: Set to ChallengeType.OTP

    Example:
        >>> callback = MockOTPCallback("123456")
        >>> context = ChallengeContext(
        ...     challenge_type=ChallengeType.OTP,
        ...     description="Enter OTP",
        ...     otp_hint="Enter code"
        ... )
        >>> code = callback(context)
        >>> code
        '123456'
        >>> callback.call_count
        1
    """

    challenge_type = ChallengeType.OTP

    def __init__(self, code: str = "123456") -> None:
        self.code = code
        self.call_count = 0
        self.last_context: ChallengeContext | None = None

    def _resolve_challenge(self, context: ChallengeContext) -> str:
        """Return predetermined OTP code.

        Args:
            context: Challenge context (stored for inspection).

        Returns:
            str: The predetermined OTP code.
        """
        self.call_count += 1
        self.last_context = context
        return self.code

    def get_description(self) -> str:
        """Return description of this callback."""
        return f"Mock OTP callback returning '{self.code}'"


# ============================================================================
# Mock CVF Callback
# ============================================================================


class MockCVFCallback(BaseChallengeCallback):
    """Mock CVF callback for testing.

    This callback returns a predetermined CVF verification code without user
    interaction. Useful for testing CVF flows.

    Args:
        code: The CVF code to return when called. Default is "123456".

    Attributes:
        challenge_type: Set to ChallengeType.CVF

    Example:
        >>> callback = MockCVFCallback("654321")
        >>> context = ChallengeContext(
        ...     challenge_type=ChallengeType.CVF,
        ...     description="Enter CVF code",
        ...     cvf_hint="Enter code from email"
        ... )
        >>> code = callback(context)
        >>> code
        '654321'
        >>> callback.call_count
        1
    """

    challenge_type = ChallengeType.CVF

    def __init__(self, code: str = "123456") -> None:
        self.code = code
        self.call_count = 0
        self.last_context: ChallengeContext | None = None

    def _resolve_challenge(self, context: ChallengeContext) -> str:
        """Return predetermined CVF code.

        Args:
            context: Challenge context (stored for inspection).

        Returns:
            str: The predetermined CVF code.
        """
        self.call_count += 1
        self.last_context = context
        return self.code

    def get_description(self) -> str:
        """Return description of this callback."""
        return f"Mock CVF callback returning '{self.code}'"


# ============================================================================
# Mock Approval Alert Callback
# ============================================================================


class MockApprovalAlertCallback(BaseChallengeCallback):
    """Mock approval alert callback for testing.

    This callback returns immediately without waiting for user approval.
    Useful for testing approval alert flows without delays.

    Args:
        auto_approve: Whether to auto-approve. Always True for mock,
            parameter exists for compatibility. Default is True.

    Attributes:
        challenge_type: Set to ChallengeType.APPROVAL_ALERT

    Example:
        >>> callback = MockApprovalAlertCallback()
        >>> context = ChallengeContext(
        ...     challenge_type=ChallengeType.APPROVAL_ALERT,
        ...     description="Approve login",
        ...     approval_url="https://example.com/approve"
        ... )
        >>> result = callback(context)
        >>> result
        'approved'
        >>> callback.call_count
        1
    """

    challenge_type = ChallengeType.APPROVAL_ALERT

    def __init__(self, auto_approve: bool = True) -> None:
        self.auto_approve = auto_approve
        self.call_count = 0
        self.last_context: ChallengeContext | None = None

    def _resolve_challenge(self, context: ChallengeContext) -> str:
        """Return immediate approval without waiting.

        Args:
            context: Challenge context (stored for inspection).

        Returns:
            str: Always returns "approved".
        """
        self.call_count += 1
        self.last_context = context
        return "approved"

    def get_description(self) -> str:
        """Return description of this callback."""
        return "Mock approval alert callback (auto-approves immediately)"


# ============================================================================
# Convenience: All Mocks Dictionary
# ============================================================================

ALL_MOCKS = {
    "captcha": MockCaptchaCallback,
    "mfa_choice": MockMFAChoiceCallback,
    "otp": MockOTPCallback,
    "cvf": MockCVFCallback,
    "approval": MockApprovalAlertCallback,
}
"""Dictionary mapping challenge type names to mock callback classes.

This is useful for programmatically creating mock callbacks in tests.

Example:
    >>> from tests.login.mocks import ALL_MOCKS
    >>> captcha_mock = ALL_MOCKS["captcha"]("my_solution")
    >>> otp_mock = ALL_MOCKS["otp"]("999999")
"""
