"""Approval Alert challenge handler and callback.

This module provides the handler and default callback for resolving approval
alert challenges during Amazon/Audible authentication.

An approval alert is Amazon's notification-based authentication method where:
1. Amazon sends a notification to the user's registered email or mobile app
2. User must click "Approve" in the notification
3. The login page polls Amazon's servers until approval is detected

This challenge appears when:
- Amazon requires additional verification
- User has notification-based authentication enabled
- Login attempt is from a new device or location

The handler automatically:
1. Detects approval alert pages
2. Notifies the user via callback
3. Polls the same URL repeatedly until approval is detected
4. Returns the page with successful authentication

Example:
    .. code-block:: python

        from audible.login.challenges import (
            ApprovalAlertHandler,
            DefaultApprovalAlertCallback,
        )

        callback = DefaultApprovalAlertCallback()
        handler = ApprovalAlertHandler(
            username="user@example.com",
            password="secret",
            session=session,
            soup_page=page,
            callback=callback,
            poll_interval=4.0,
            max_polls=60,
        )

        if handler.has_challenge():
            next_page = handler.resolve_challenge()

Note:
    Unlike other challenges, the approval alert doesn't require user input
    in the application. The user must check their email/app and click approve
    there. The handler simply waits by polling.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from typing import TYPE_CHECKING

from audible.login.base import (
    BaseChallengeCallback,
    BaseChallengeHandler,
    ChallengeContext,
    ChallengeType,
)
from audible.login.soup_page import SoupPage


if TYPE_CHECKING:
    pass


logger = logging.getLogger(__name__)


# ============================================================================
# Approval Alert Callback
# ============================================================================


class DefaultApprovalAlertCallback(BaseChallengeCallback):
    """Default Approval Alert callback - notifies user and waits for confirmation.

    This callback implements a simple console-based notification for approval
    alerts. It:
    1. Prints a message explaining the approval alert
    2. Waits for the user to press ENTER after approving

    The actual approval happens outside the application (in email or mobile app),
    so this callback's role is just to:
    - Inform the user what's happening
    - Pause execution until user confirms they've approved

    Attributes:
        challenge_type: Set to ChallengeType.APPROVAL_ALERT

    Example:
        .. code-block:: python

            callback = DefaultApprovalAlertCallback()
            context = ChallengeContext(
                challenge_type=ChallengeType.APPROVAL_ALERT,
                description="Approval pending",
                approval_url="https://www.amazon.com/ap/..."
            )
            result = callback(context)
            # Approval alert detected! Amazon sends you a mail.
            # Please press ENTER when you approve the notification.
            # result
            # 'approved'

    Note:
        The return value is always "approved" - it's just a signal to the handler
        that the callback has completed. The actual approval detection happens
        via polling in the handler.
    """

    challenge_type = ChallengeType.APPROVAL_ALERT

    def _resolve_challenge(self, context: ChallengeContext) -> str:
        """Notify user about approval alert and wait for confirmation.

        Args:
            context: Challenge context containing approval URL and description.

        Returns:
            str: Always returns "approved" after user presses ENTER.

        Example:
            .. code-block:: python

                # User presses ENTER after approving in email
                result = callback._resolve_challenge(context)
                # result
                # 'approved'
        """
        print("Approval alert detected! Amazon sends you a mail.")
        input("Please press ENTER when you approve the notification.")
        return "approved"

    def get_description(self) -> str:
        """Return description of this callback.

        Returns:
            str: Human-readable description of the callback's behavior.
        """
        return "Wait for user approval confirmation via console"


# ============================================================================
# Approval Alert Handler
# ============================================================================


@dataclass
class ApprovalAlertHandler(BaseChallengeHandler):
    """Handler for Approval Alert (email/app notification) challenges.

    This handler manages the approval alert workflow where users must approve
    the login attempt via email or mobile app notification. The handler:
    1. Detects approval alert pages
    2. Notifies the user via callback
    3. Polls the URL repeatedly until approval is detected or timeout occurs
    4. Returns the approved page

    The handler inherits username, password, session, soup_page, and log_errors
    from BaseChallengeHandler.

    Attributes:
        callback: Callback to notify user about approval alert. Required for
            this handler.
        poll_interval: Seconds to wait between polling attempts. Default: 4.0.
        max_polls: Maximum number of polling attempts before timeout.
            Default: 60 (= 4 minutes with default interval).

    Amazon approval alert pages are identified by:
    - id="resend-approval-alert" OR
    - id="resend-approval-form"

    The polling process:
    1. Call callback to notify user
    2. GET the same URL repeatedly
    3. Check if span.transaction-approval-word-break is still present
    4. If not present, approval was successful
    5. If still present after max_polls, raise TimeoutError

    Example:
        .. code-block:: python

            callback = DefaultApprovalAlertCallback()
            handler = ApprovalAlertHandler(
                username=None,  # Not required
                password=None,
                session=session,
                soup_page=page,
                callback=callback,
                poll_interval=4.0,
                max_polls=60,
            )

            if handler.has_challenge():
                next_page = handler.resolve_challenge()

    Note:
        The default timeout is 4 minutes (60 polls * 4 seconds). This gives
        users time to check their email or phone. Adjust poll_interval and
        max_polls if you need different timeout behavior.
    """

    callback: BaseChallengeCallback
    poll_interval: float = 4.0
    max_polls: int = 60

    def has_challenge(self) -> bool:
        """Check if approval alert is present.

        Amazon approval alert pages contain either:
        - Element with id="resend-approval-alert"
        - Element with id="resend-approval-form"

        Returns:
            bool: True if an approval alert is detected, False otherwise.

        Example:
            .. code-block:: python

                if handler.has_challenge():
                    print("Approval alert - check your email/app")
        """
        alert = self.soup_page.soup.find(
            id="resend-approval-alert"
        ) or self.soup_page.soup.find(id="resend-approval-form")
        return bool(alert)

    def resolve_challenge(self) -> SoupPage:
        """Resolve approval alert by polling until user approves.

        This method performs the complete approval alert workflow:
        1. Builds a ChallengeContext with approval URL
        2. Calls the callback to notify the user
        3. Starts polling loop:
            - GET the same URL
            - Check for approval indicator
            - Wait poll_interval seconds
            - Repeat until approval or timeout
        4. Returns the approved page

        The approval is detected by the ABSENCE of a specific HTML element:
        span.transaction-approval-word-break

        When this element is no longer present, the user has approved.

        Returns:
            SoupPage: The parsed page after approval is detected. This is
                typically the final logged-in state with authorization code
                in the URL.

        Raises:
            TimeoutError: If approval is not received within the timeout
                period (max_polls * poll_interval seconds).

        Example:
            .. code-block:: python

                try:
                    next_page = handler.resolve_challenge()
                    print("Approved successfully!")
                except TimeoutError as e:
                    logger.error(f"Timeout waiting for approval: {e}")

        Note:
            Each poll makes an HTTP GET request, so be mindful of the total
            number of requests. The default settings (60 polls * 4 seconds)
            make at most 60 requests over 4 minutes.
        """
        context = ChallengeContext(
            challenge_type=ChallengeType.APPROVAL_ALERT,
            description="Approval notification pending",
            soup_page=self.soup_page,
            approval_url=str(self.soup_page.resp.url),
        )

        # Notify user (callback may display GUI, print message, etc.)
        self.callback(context)

        url = str(self.soup_page.resp.url)
        poll_count = 0

        while poll_count < self.max_polls:
            resp = self.session.get(url)
            soup_page = SoupPage(resp)

            # Check if approval is still pending
            # When approved, the transaction-approval-word-break element disappears
            if not soup_page.soup.find(
                "span", {"class": "transaction-approval-word-break"}
            ):
                logger.info("Approval received!")
                return soup_page

            logger.info(
                "Still waiting for approval (%d/%d)...",
                poll_count + 1,
                self.max_polls,
            )
            time.sleep(self.poll_interval)
            poll_count += 1

        # Timeout - approval not received
        timeout_seconds = self.max_polls * self.poll_interval
        raise TimeoutError(f"Approval not received after {timeout_seconds}s")
