"""OTP (One-Time Password) challenge handler and callback.

This module provides the handler and default callback for resolving one-time
password (OTP) challenges during Amazon/Audible authentication. OTP is also
commonly known as 2FA (two-factor authentication).

The OTP challenge appears after:
- Initial login with username/password
- MFA device selection (if multiple devices are configured)

The handler automatically:
1. Detects OTP entry forms
2. Calls the callback to get the OTP code from the user
3. Submits the code with appropriate form flags
4. Returns the resulting page

Example:
    .. code-block:: python

        from audible.login_service.challenges import OTPHandler, DefaultOTPCallback

        callback = DefaultOTPCallback()
        handler = OTPHandler(
            username="user@example.com",
            password="secret",
            session=session,
            soup_page=page,
            callback=callback,
        )

        if handler.has_challenge():
            next_page = handler.resolve_challenge()

Note:
    The OTP code is typically a 6-digit number from an authenticator app
    (TOTP) or received via SMS/voice call.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from typing import TYPE_CHECKING

from bs4 import BeautifulSoup, Tag

from audible.login_service.base import (
    BaseChallengeCallback,
    BaseChallengeHandler,
    ChallengeContext,
    ChallengeType,
    OtpContext,
)
from audible.login_service.soup_page import SoupPage


if TYPE_CHECKING:
    pass


logger = logging.getLogger(__name__)


# ============================================================================
# Helper Functions
# ============================================================================


def extract_otp_context(soup: BeautifulSoup) -> OtpContext | None:
    """Extract OTP context information from page.

    Provides context about where the OTP was sent and via which method.
    Language-agnostic approach using patterns and keywords rather than
    exact text matching.

    Args:
        soup: BeautifulSoup object of OTP input page

    Returns:
        OtpContext object with destination and method info, or None if not found

    Algorithm (multiple strategies for robustness):
        1. Strategy A: Find <p> tag near form with ending digits pattern
           - Pattern: digits followed by word (e.g., "964 endet", "ending in 964")
           - Extract method from keywords (telefon/phone → SMS, whatsapp → WhatsApp)
        2. Strategy B: Check deviceId hidden field for method hints
           - Some forms include method in value (e.g., "..., SMS")
        3. Strategy C: Fallback - return None (no context available)

    Language Support:
        - German: "Telefonnummer ... die auf 964 endet"
        - English: "phone number ending in 964"
        - Spanish: "número que termina en 964"
        - Keywords: telefon, phone, número, whatsapp, email, anruf, call

    Example HTML:
        <p>Für zusätzliche Sicherheit gib bitte den Code ein,
           der an eine Telefonnummer gesendet wurde, die auf 964 endet</p>
        <form id="auth-mfa-form">...</form>

    Example:
        >>> html = '''<p>Code gesendet an Telefonnummer die auf 964 endet</p>
        ...   <form id="auth-mfa-form">
        ...     <input type="hidden" name="deviceId" value="xyz"/>
        ...   </form>'''
        >>> soup = BeautifulSoup(html, "html.parser")
        >>> context = extract_otp_context(soup)
        >>> context.destination
        'number ending in 964'
        >>> context.method_type
        'SMS'
    """
    # Strategy 1: Find <p> tag with destination info
    form = soup.find("form", id=lambda x: x and "mfa-form" in str(x))
    if isinstance(form, Tag):
        # Look for <p> tag before/near form
        prev_p = form.find_previous("p")
        if isinstance(prev_p, Tag):
            message = prev_p.get_text(strip=True)

            if message:
                logger.debug(f"Found OTP message: {message[:100]}")

                # Extract ending digits (language-agnostic)
                # Patterns: "964 endet", "ending in 964", "termina en 964"
                match = re.search(r"(\d{3,4})\s+\w+\s*$", message)
                if not match:
                    # Alternative pattern: "ending/termina/endet + in/en + digits"
                    match = re.search(r"\w+\s+(?:in|en)\s+(\d{3,4})", message, re.IGNORECASE)

                if match:
                    digits = match.group(1)
                    destination = f"number ending in {digits}"

                    # Determine method type from keywords (case-insensitive)
                    method_keywords = {
                        "WhatsApp": ["whatsapp", "whatsapp-"],
                        "SMS": ["telefon", "phone", "número", "sms", "text"],
                        "Email": ["email", "e-mail", "mail"],
                        "Voice Call": ["anruf", "call", "llamada", "voice"],
                    }

                    method = None
                    message_lower = message.lower()
                    for method_type, keywords in method_keywords.items():
                        if any(kw in message_lower for kw in keywords):
                            method = method_type
                            break

                    logger.info(
                        f"Extracted OTP context: {method or 'unknown method'} to {destination}"
                    )

                    return OtpContext(
                        destination=destination,
                        method_type=method,
                        raw_message=message,
                    )

    # Strategy 2: Check deviceId hidden field
    device_id = soup.find("input", {"name": "deviceId"})
    if isinstance(device_id, Tag):
        value = device_id.get("value")
        if isinstance(value, str):
            # deviceId might contain method info: "tokenXYZ, SMS"
            for method_type in ["SMS", "VOICE", "WhatsApp", "TOTP", "Email"]:
                if method_type in value:
                    logger.info(f"Extracted method from deviceId: {method_type}")
                    return OtpContext(
                        destination="unknown",
                        method_type=method_type,
                        raw_message="",
                    )

    # Strategy 3: No context available
    logger.debug("Could not extract OTP context from page")
    return None


# ============================================================================
# OTP Callback
# ============================================================================


class DefaultOTPCallback(BaseChallengeCallback):
    """Default OTP callback - enhanced with context display.

    This callback implements a console-based prompt for OTP code entry with
    optional context information about where the code was sent.

    Enhanced Features:
        - Displays method type (SMS, WhatsApp, TOTP, etc.)
        - Shows destination (e.g., "number ending in 964")
        - Falls back to simple prompt if no context available

    Attributes:
        challenge_type: Set to ChallengeType.OTP

    Example (with context):
        .. code-block:: python

            callback = DefaultOTPCallback()
            # Context would be passed by enhanced OTPHandler
            context = ChallengeContext(
                challenge_type=ChallengeType.OTP,
                description="Enter OTP",
                otp_hint="Enter code from SMS",
                otp_context=OtpContext("number ending in 964", "SMS", "...")
            )
            code = callback(context)

            # Output:
            # OTP Code Required
            # ==================================================
            # Method: SMS
            # Sent to: number ending in 964
            # ==================================================
            #
            # Enter OTP Code: _

    Example (without context - backward compatible):
        .. code-block:: python

            context = ChallengeContext(
                challenge_type=ChallengeType.OTP,
                description="Enter OTP",
                otp_hint="OTP Code"
            )
            code = callback(context)
            # Output: OTP Code: _

    Note:
        Backward compatible with old behavior when no otp_context available.
    """

    challenge_type = ChallengeType.OTP

    def _resolve_challenge(self, context: ChallengeContext) -> str:
        """Prompt user for OTP code with enhanced context display.

        Args:
            context: Challenge context optionally containing OTP context.

        Returns:
            str: The OTP code entered by the user (stripped and lowercased).
        """
        # Check if we have enhanced context
        if hasattr(context, "otp_context") and context.otp_context:
            # Enhanced display with context
            otp_ctx = context.otp_context
            print("\n" + "=" * 50)
            print("OTP Code Required")
            print("=" * 50)
            print(f"Method: {otp_ctx.method_type or 'Unknown'}")
            print(f"Sent to: {otp_ctx.destination}")
            print("=" * 50)
            prompt = "\nEnter OTP Code: "
        else:
            # Fallback to original behavior (backward compatible)
            hint = context.otp_hint or "OTP Code"
            prompt = f"{hint}: "

        code = input(prompt)
        return code.strip().lower()

    def get_description(self) -> str:
        """Return description of this callback."""
        return "Prompt for OTP code with context display (backward compatible)"


# ============================================================================
# OTP Handler
# ============================================================================


@dataclass
class OTPHandler(BaseChallengeHandler):
    """Handler for One-Time Password (2FA) challenges.

    This handler manages the OTP entry step where users enter a code from
    their authenticator app, SMS, or voice call. It detects OTP forms,
    obtains the code from the callback, and submits it with the appropriate
    form fields.

    The handler inherits all attributes from BaseChallengeHandler:
    - username: Amazon account username (optional for this challenge)
    - password: Amazon account password (optional for this challenge)
    - session: HTTP client session
    - soup_page: Parsed page with OTP entry form
    - callback: OTP callback (REQUIRED)
    - log_errors: Enable error logging

    Amazon OTP forms are identified by specific form IDs:
    - "verification-code-form" (newer pages)
    - "auth-mfa-form" (older pages)

    The submission includes:
    - otpCode: The user's OTP code
    - mfaSubmit: "Submit" flag
    - rememberDevice: "false" (don't remember this device)

    Example:
        .. code-block:: python

            callback = DefaultOTPCallback()
            handler = OTPHandler(
                username=None,  # Not required for OTP submission
                password=None,
                session=session,
                soup_page=page,
                callback=callback,
            )

            if handler.has_challenge():
                next_page = handler.resolve_challenge()

    Note:
        This handler does NOT require username/password as the user has
        already authenticated with their primary credentials. The OTP is
        the second factor in two-factor authentication.
    """

    callback: BaseChallengeCallback

    def has_challenge(self) -> bool:
        """Check if OTP entry form is present.

        Amazon uses two possible form IDs for OTP entry:
        - "verification-code-form" (newer interface)
        - "auth-mfa-form" (older interface)

        Returns:
            bool: True if an OTP entry form is found, False otherwise.

        Example:
            .. code-block:: python

                if handler.has_challenge():
                    print("OTP entry required")
        """
        form = self.soup_page.soup.find(
            "form",
            id=lambda x: x and ("verification-code-form" in x or "auth-mfa-form" in x),
        )
        return bool(form)

    def resolve_challenge(self) -> SoupPage:
        """Resolve OTP challenge with enhanced context extraction.

        This method performs the complete OTP resolution workflow:
        1. Extracts OTP context from page (where code was sent)
        2. Logs context for debugging
        3. Builds ChallengeContext with OTP context
        4. Calls the callback to get the OTP code
        5. Submits the code to Amazon
        6. Returns the resulting page

        Returns:
            SoupPage: The parsed page after OTP submission. This is typically
                either a successful login or another challenge page.

        Raises:
            CallbackError: If callback execution fails.
            httpx.HTTPError: If the submission request fails.

        Note:
            The OTP context extraction is best-effort. If it fails, the callback
            receives None and shows a generic prompt (backward compatible).
        """
        # Step 1: Extract OTP context
        otp_context = extract_otp_context(self.soup_page.soup)

        if otp_context:
            logger.info(
                f"OTP sent via {otp_context.method_type or 'unknown method'} "
                f"to {otp_context.destination}"
            )
        else:
            logger.debug("No OTP context available (older page format?)")

        # Step 2: Build challenge context with OTP context
        context = ChallengeContext(
            challenge_type=ChallengeType.OTP,
            description="One-time password authentication",
            soup_page=self.soup_page,
            otp_hint="Enter your OTP code",
        )

        # Add OTP context as dynamic attribute (not in dataclass definition)
        if otp_context:
            object.__setattr__(context, "otp_context", otp_context)

        # Step 3: Call callback
        otp_code = self.callback(context)

        # Step 4: Build and submit form
        inputs = self.soup_page.get_form_inputs()
        inputs["otpCode"] = otp_code
        inputs["mfaSubmit"] = "Submit"
        inputs["rememberDevice"] = "false"

        method, url = self.soup_page.get_next_action()
        resp = self.session.request(method, url, data=inputs)

        return SoupPage(resp)
