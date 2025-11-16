"""CVF (Credential Verification Form) challenge handler and callback.

This module provides the handler and default callback for resolving credential
verification form (CVF) challenges during Amazon/Audible authentication.

CVF is Amazon's mechanism for verifying account ownership by sending a code
to the user's registered email address or phone number. The user must enter
this code to complete authentication.

The CVF process has two steps:
1. Select verification method (code via email/SMS)
2. Enter the verification code received

The handler automatically manages both steps:
1. Detects CVF pages
2. Calls the callback to get the verification code
3. Submits verification method selection
4. Submits the verification code
5. Returns the resulting page

Example:
    .. code-block:: python

        from audible.login_service.challenges import CVFHandler, DefaultCVFCallback

        callback = DefaultCVFCallback()
        handler = CVFHandler(
            username="user@example.com",
            password="secret",
            session=session,
            soup_page=page,
            callback=callback,
        )

        if handler.has_challenge():
            next_page = handler.resolve_challenge()

Note:
    CVF codes are typically sent via email or SMS and are usually 6-8 digits.
    The user must retrieve the code from their email/phone before entering it.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import TYPE_CHECKING

from audible.login_service.base import (
    BaseChallengeCallback,
    BaseChallengeHandler,
    ChallengeContext,
    ChallengeType,
)
from audible.login_service.soup_page import SoupPage


if TYPE_CHECKING:
    pass


logger = logging.getLogger(__name__)


# ============================================================================
# CVF Callback
# ============================================================================


class DefaultCVFCallback(BaseChallengeCallback):
    """Default CVF callback - prompts user for verification code via console.

    This callback implements a simple console-based prompt for CVF code entry.
    It displays a hint message (if provided in the context) and waits for
    user input.

    The callback automatically:
    - Displays the CVF hint or a default prompt
    - Strips whitespace from the entered code
    - Converts to lowercase (though CVF codes may be case-insensitive)

    Attributes:
        challenge_type: Set to ChallengeType.CVF

    Example:
        .. code-block:: python

            callback = DefaultCVFCallback()
            context = ChallengeContext(
                challenge_type=ChallengeType.CVF,
                description="Enter CVF code",
                cvf_hint="Enter code sent to your email"
            )
            code = callback(context)
            # Enter code sent to your email: 123456
            # code
            # '123456'

    Note:
        For automated testing, use MockCVFCallback from tests/login_dir/mocks.py
        to avoid user interaction.
    """

    challenge_type = ChallengeType.CVF

    def _resolve_challenge(self, context: ChallengeContext) -> str:
        """Prompt user for CVF verification code via console.

        Args:
            context: Challenge context optionally containing a CVF hint.

        Returns:
            str: The CVF code entered by the user (stripped and lowercased).

        Example:
            .. code-block:: python

                # User enters "123456" at the prompt
                code = callback._resolve_challenge(context)
                # code
                # '123456'
        """
        hint = context.cvf_hint or "CVF Code (sent via email/SMS)"
        code = input(f"{hint}: ")
        return code.strip().lower()

    def get_description(self) -> str:
        """Return description of this callback.

        Returns:
            str: Human-readable description of the callback's behavior.
        """
        return "Prompt for CVF code via console input"


# ============================================================================
# CVF Handler
# ============================================================================


@dataclass
class CVFHandler(BaseChallengeHandler):
    """Handler for Credential Verification Form challenges.

    This handler manages the two-step CVF process where users must verify
    their account by entering a code sent to their email or phone. CVF is
    Amazon's mechanism for additional security when:
    - Logging in from a new device or location
    - Account activity appears suspicious
    - Additional verification is required by security policies

    The handler performs a two-step submission:
    1. Select "code" as the verification method
    2. Submit the actual verification code

    The handler inherits all attributes from BaseChallengeHandler:
    - username: Amazon account username (optional for this challenge)
    - password: Amazon account password (optional for this challenge)
    - session: HTTP client session
    - soup_page: Parsed page with CVF form
    - callback: CVF callback (REQUIRED)
    - log_errors: Enable error logging

    Amazon CVF pages are identified by:
    - div#cvf-page-content

    The two-step process:
    1. First request: Submit form with existing inputs (selects code method)
    2. Second request: Submit with action="code" and code=<user_code>

    Example:
        .. code-block:: python

            callback = DefaultCVFCallback()
            handler = CVFHandler(
                username=None,  # Not required for CVF submission
                password=None,
                session=session,
                soup_page=page,
                callback=callback,
            )

            if handler.has_challenge():
                next_page = handler.resolve_challenge()

    Note:
        The callback is called BEFORE the two HTTP requests, allowing the user
        to retrieve the code from their email/SMS while the first request is
        being processed.
    """

    callback: BaseChallengeCallback

    def has_challenge(self) -> bool:
        """Check if CVF page is present.

        Amazon CVF pages contain a div with id "cvf-page-content".

        Returns:
            bool: True if a CVF page is detected, False otherwise.

        Example:
            .. code-block:: python

                if handler.has_challenge():
                    print("CVF verification required")
        """
        cvf = self.soup_page.soup.find("div", id="cvf-page-content")
        return bool(cvf)

    def resolve_challenge(self) -> SoupPage:
        """Resolve CVF challenge using two-step submission process.

        This method performs the complete CVF resolution workflow:
        1. Builds a ChallengeContext with CVF hint
        2. Calls the callback to get the verification code from user
        3. Submits first form to select "code" verification method
        4. Parses the response to get the code entry form
        5. Submits second form with action="code" and the verification code
        6. Returns the resulting page

        The two-step process is necessary because:
        - Amazon first asks you to SELECT how you want to verify (code/call/etc)
        - Then it shows you the code entry form

        Returns:
            SoupPage: The parsed page after CVF code submission. This is
                typically either a successful login (with authorization code
                in URL) or an error page (incorrect code).

        Raises:
            CallbackError: If callback execution fails.
            httpx.HTTPError: If either submission request fails.

        Example:
            .. code-block:: python

                try:
                    next_page = handler.resolve_challenge()
                    print("CVF code submitted successfully")
                except CallbackError as e:
                    logger.error(f"CVF verification failed: {e}")

        Note:
            The callback is invoked BEFORE the first submission, giving the
            user time to check their email/SMS for the code while the first
            request is in progress.
        """
        context = ChallengeContext(
            challenge_type=ChallengeType.CVF,
            description="Credential verification code",
            soup_page=self.soup_page,
            cvf_hint="Enter verification code sent to you",
        )

        # Get CVF code from callback first (gives user time to check email)
        cvf_code = self.callback(context)

        # Step 1: Select "code" verification method
        inputs = self.soup_page.get_form_inputs()
        method, url = self.soup_page.get_next_action()
        resp = self.session.request(method, url, data=inputs)
        soup_page = SoupPage(resp)

        # Step 2: Submit verification code
        inputs = soup_page.get_form_inputs()
        inputs["action"] = "code"
        inputs["code"] = cvf_code

        method, url = soup_page.get_next_action()
        resp = self.session.request(method, url, data=inputs)
        return SoupPage(resp)
