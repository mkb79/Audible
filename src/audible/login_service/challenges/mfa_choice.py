"""MFA device choice challenge handler and callback.

This module provides the handler and default callback for resolving multi-factor
authentication (MFA) device selection challenges during Amazon/Audible authentication.

The MFA choice challenge appears when a user has multiple MFA methods configured
(e.g., TOTP authenticator app, SMS, voice call) and must select which method to use
for the current login attempt.

The handler automatically:
1. Detects MFA device selection pages
2. Extracts available MFA device options
3. Calls the callback to select a device
4. Submits the selection to proceed to OTP entry

Example:
    .. code-block:: python

        from audible.login_service.challenges import (
            MFAChoiceHandler,
            DefaultMFAChoiceCallback,
        )

        callback = DefaultMFAChoiceCallback()
        handler = MFAChoiceHandler(
            username="user@example.com",
            password="secret",
            session=session,
            soup_page=page,
            callback=callback,
        )

        if handler.has_challenge():
            next_page = handler.resolve_challenge()

Note:
    This challenge is followed by an OTP challenge where the user enters
    the actual authentication code.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from urllib.parse import urljoin
from typing import TYPE_CHECKING

from bs4 import BeautifulSoup, Tag

from audible.login_service.base import (
    BaseChallengeCallback,
    BaseChallengeHandler,
    ChallengeContext,
    ChallengeType,
    MFADeviceOption,
    MfaMethod,
)
from audible.login_service.exceptions import MFAError
from audible.login_service.soup_page import SoupPage


if TYPE_CHECKING:
    pass


logger = logging.getLogger(__name__)


# ============================================================================
# Helper Functions
# ============================================================================


def extract_mfa_methods(soup: BeautifulSoup) -> list[MfaMethod]:
    """Extract available MFA methods from selection page.

    Parses the MFA-Choice page HTML structure to identify all available
    authentication methods. Language-agnostic approach using CSS classes
    and HTML structure rather than text content.

    Args:
        soup: BeautifulSoup object of MFA-Choice page

    Returns:
        List of MfaMethod objects, empty list if none found

    Raises:
        None - returns empty list on failure for graceful degradation

    Algorithm:
        1. Find all <div> elements with data-a-input-name="otpDeviceContext"
        2. Extract method type from CSS class (e.g., "auth-TOTP" → "TOTP")
        3. Find <input type="radio"> and extract name/value
        4. Extract label text from <span class="a-label">
        5. Check if input has "checked" attribute for default

    Example HTML:
        <div data-a-input-name="otpDeviceContext" class="a-radio auth-TOTP">
          <label>
            <input type="radio" name="otpDeviceContext" value="..., TOTP" checked/>
            <span class="a-label a-radio-label">Authenticator-App</span>
          </label>
        </div>

    Example:
        >>> html = '''<div data-a-input-name="otpDeviceContext" class="a-radio auth-TOTP">
        ...   <label>
        ...     <input type="radio" name="otpDeviceContext" value="tok123, TOTP" checked/>
        ...     <span class="a-label">Use TOTP</span>
        ...   </label>
        ... </div>'''
        >>> soup = BeautifulSoup(html, "html.parser")
        >>> methods = extract_mfa_methods(soup)
        >>> len(methods)
        1
        >>> methods[0].method_type
        'TOTP'
        >>> methods[0].is_default
        True
    """
    methods = []

    for node in soup.select("div[data-a-input-name=otpDeviceContext]"):
        # Extract method type from CSS class
        method_type = None
        classes = node.get("class", [])
        for cls in classes:
            if isinstance(cls, str) and cls.startswith("auth-"):
                method_type = cls.replace("auth-", "")
                break

        if not method_type:
            logger.debug(f"Skipping node without auth- class: {classes}")
            continue

        # Find radio input
        inp_node = node.find("input", {"type": "radio"})
        if not isinstance(inp_node, Tag):
            logger.debug(f"No radio input found in node for {method_type}")
            continue

        # Extract form field value
        value = inp_node.get("value")
        if not isinstance(value, str):
            logger.debug(f"Invalid value for {method_type}: {value}")
            continue

        # Extract label text
        label_node = node.find("span", class_="a-label")
        if isinstance(label_node, Tag):
            label = label_node.get_text(strip=True)
        else:
            label = method_type  # Fallback
            logger.debug(f"No label found for {method_type}, using type as label")

        # Check if default
        is_default = inp_node.has_attr("checked")

        methods.append(
            MfaMethod(
                method_type=method_type,
                value=value,
                label=label,
                is_default=is_default,
            )
        )
        logger.debug(
            f"Extracted MFA method: {method_type} ({label[:50]}) - default: {is_default}"
        )

    return methods


def select_mfa_method_by_priority(methods: list[MfaMethod]) -> MfaMethod:
    """Select MFA method by hardcoded priority order.

    Priority order (from most to least preferred):
        1. TOTP - Most secure, offline, no rate limits
        2. SMS - Widely supported, but rate-limited
        3. VOICE - Backup for SMS, same rate limits
        4. WhatsApp - Newer method, unknown limits
        5. Other - Any unrecognized method

    This function is used as fallback when user provides no callback
    or when callback returns None.

    Args:
        methods: List of available MFA methods

    Returns:
        Selected MfaMethod based on priority

    Raises:
        ValueError: If methods list is empty

    Example:
        >>> methods = [
        ...     MfaMethod("SMS", "val1", "Send SMS", False),
        ...     MfaMethod("TOTP", "val2", "Use App", False),
        ...     MfaMethod("WhatsApp", "val3", "WhatsApp", False),
        ... ]
        >>> selected = select_mfa_method_by_priority(methods)
        >>> selected.method_type
        'TOTP'

    Note:
        Priority is hardcoded (not configurable). Users wanting different
        priority can implement custom callback.
    """
    if not methods:
        raise ValueError("Cannot select from empty methods list")

    # Hardcoded priority (design decision 12.4)
    priority = ["TOTP", "SMS", "VOICE", "WhatsApp"]

    # Try to match by priority
    for preferred in priority:
        for method in methods:
            if preferred in method.method_type:
                logger.info(f"Selected MFA method by priority: {method.method_type}")
                return method

    # No match found, return first available
    logger.warning(
        f"No priority match found, using first available method: {methods[0].method_type}"
    )
    return methods[0]


# ============================================================================
# MFA Choice Callback
# ============================================================================


class DefaultMFAChoiceCallback(BaseChallengeCallback):
    """Default MFA choice callback - interactive selection with retry loop.

    This callback implements an interactive console-based selection for MFA
    device choice. It displays all available methods and prompts the user to
    choose one, with validation and retry on invalid input.

    User Experience:
        - Shows numbered list of methods with default marker
        - Press Enter → use default or priority-based selection
        - Enter number → select that method
        - Invalid input → retry with error message (infinite loop until valid)

    Attributes:
        challenge_type: Set to ChallengeType.MFA_CHOICE

    Example:
        .. code-block:: python

            callback = DefaultMFAChoiceCallback()
            context = ChallengeContext(
                challenge_type=ChallengeType.MFA_CHOICE,
                description="Select MFA device",
                mfa_options=[...]  # Populated by handler
            )
            selected_value = callback(context)  # Interactive prompt

    Design Decisions:
        - Invalid input → Retry loop (not auto-select by priority) (DD 4.1)
        - Empty input (Enter) → Use default or priority (DD 12.1)
        - Keyboard Interrupt (Ctrl+C) → Auto-select by priority

    Note:
        For automated selection, implement a custom callback that returns
        a method's input_value directly without user interaction.
    """

    challenge_type = ChallengeType.MFA_CHOICE

    def _resolve_challenge(self, context: ChallengeContext) -> str:
        """Select an MFA device interactively with retry loop.

        Args:
            context: Challenge context containing available MFA options.

        Returns:
            str: The value (not method_type!) of the selected MFA method.

        Raises:
            MFAError: If no MFA options are available in the context.
        """
        if not context.mfa_options:
            raise MFAError("No MFA options available in context")

        # Convert MFADeviceOptions to MfaMethod for enhanced UX
        methods = []
        for opt in context.mfa_options:
            methods.append(
                MfaMethod(
                    method_type=opt.method,
                    value=opt.input_value,
                    label=opt.label,
                    is_default=False,  # MFADeviceOption doesn't track this
                )
            )

        # Display available methods
        print("\n" + "=" * 50)
        print("MFA Method Selection")
        print("=" * 50)
        print("\nAvailable authentication methods:")

        for i, method in enumerate(methods, 1):
            default_marker = " (default)" if method.is_default else ""
            print(f"  {i}. {method.label}{default_marker}")

        print("\nTip: Press Enter to use priority-based selection (TOTP preferred)")
        print("=" * 50)

        # Retry loop until valid selection
        while True:
            try:
                choice = input(f"\nSelect method (1-{len(methods)}, or press Enter): ").strip()

                # Empty input → use priority
                if not choice:
                    # Try to find default method first
                    default_method = next((m for m in methods if m.is_default), None)
                    if default_method:
                        print(f"→ Using default method: {default_method.method_type}")
                        return default_method.value

                    # No default → use priority
                    selected = select_mfa_method_by_priority(methods)
                    print(f"→ Using priority-based selection: {selected.method_type}")
                    return selected.value

                # Parse numeric choice
                index = int(choice) - 1

                # Validate range
                if 0 <= index < len(methods):
                    selected = methods[index]
                    print(f"→ Selected: {selected.method_type}")
                    return selected.value
                else:
                    print(
                        f"❌ Invalid choice: {choice}. "
                        f"Please enter a number between 1 and {len(methods)}."
                    )

            except ValueError:
                print(f"❌ Invalid input: '{choice}'. Please enter a number or press Enter.")

            except KeyboardInterrupt:
                print("\n\n⚠️  Selection cancelled by user.")
                # On Ctrl+C, use priority-based selection
                selected = select_mfa_method_by_priority(methods)
                print(f"→ Using priority-based selection: {selected.method_type}")
                return selected.value

    def get_description(self) -> str:
        """Return description of this callback."""
        return "Interactive MFA device selection with retry loop"


# ============================================================================
# MFA Choice Handler
# ============================================================================


@dataclass
class MFAChoiceHandler(BaseChallengeHandler):
    """Handler for multi-factor authentication device selection.

    This handler manages the MFA device selection step that appears when a user
    has multiple authentication methods configured. It extracts available devices
    from the page, presents them to the callback for selection, and submits the
    chosen device.

    The handler inherits all attributes from BaseChallengeHandler:
    - username: Amazon account username (optional for this challenge)
    - password: Amazon account password (optional for this challenge)
    - session: HTTP client session
    - soup_page: Parsed page with MFA choice form
    - callback: MFA choice callback (REQUIRED)
    - log_errors: Enable error logging

    Amazon presents MFA options with specific HTML structure:
    - Form ID: "auth-select-device-form"
    - Device options: div[data-a-input-name=otpDeviceContext]
    - Device classes: "auth-TOTP", "auth-SMS", "auth-VOICE"

    Example:
        .. code-block:: python

            callback = DefaultMFAChoiceCallback()
            handler = MFAChoiceHandler(
                username=None,  # Not required for this challenge
                password=None,
                session=session,
                soup_page=page,
                callback=callback,
            )

            if handler.has_challenge():
                next_page = handler.resolve_challenge()

    Note:
        This challenge does NOT require username/password as it's selecting
        an already-authenticated MFA method. The actual authentication code
        is entered in the subsequent OTP challenge.
    """

    callback: BaseChallengeCallback

    def has_challenge(self) -> bool:
        """Check if MFA device selection form is present.

        Amazon uses a specific form ID for MFA device selection:
        "auth-select-device-form"

        Returns:
            bool: True if the MFA device selection form is found,
                False otherwise.

        Example:
            .. code-block:: python

                if handler.has_challenge():
                    print("MFA device selection required")
        """
        form = self.soup_page.soup.find("form", id="auth-select-device-form")
        return bool(form)

    def _extract_mfa_options(self) -> list[MFADeviceOption]:
        """Extract available MFA device options from the page.

        Parses the HTML structure to find all available MFA devices and their
        metadata. Each device is represented as a MFADeviceOption with:
        - method: The MFA method type (TOTP, SMS, VOICE, or UNKNOWN)
        - label: User-friendly description of the device
        - input_name: Form input name for selection
        - input_value: Form input value to submit when selected

        Returns:
            list[MFADeviceOption]: List of available MFA devices. May be empty
                if no valid options are found on the page.

        Example:
            .. code-block:: python

                options = handler._extract_mfa_options()
                for option in options:
                    print(f"{option.method}: {option.label}")
                # Output:
                # TOTP: Authenticator App
                # SMS: Phone ending in 1234

        Note:
            This method extracts options from div elements with the attribute
            data-a-input-name="otpDeviceContext" and inspects their classes
            to determine the MFA method type.
        """
        options = []

        for node in self.soup_page.soup.select("div[data-a-input-name=otpDeviceContext]"):
            inp_node = node.find("input")
            if not isinstance(inp_node, Tag):
                continue

            # Determine MFA method from CSS classes
            classes = node.get("class", [])
            if "auth-TOTP" in classes:
                method = "TOTP"
            elif "auth-SMS" in classes:
                method = "SMS"
            elif "auth-VOICE" in classes:
                method = "VOICE"
            else:
                method = "UNKNOWN"

            # Extract user-visible label
            label_node = node.find("span", class_="a-list-item")
            label = label_node.get_text(strip=True) if label_node else method

            # Extract form input data
            input_name = inp_node.get("name")
            input_value = inp_node.get("value")

            if isinstance(input_name, str) and isinstance(input_value, str):
                options.append(
                    MFADeviceOption(
                        method=method,
                        label=label,
                        input_name=input_name,
                        input_value=input_value,
                    )
                )

        return options

    def resolve_challenge(self) -> SoupPage:
        """Resolve MFA device selection with enhanced logging and rate limiting detection.

        This method performs the complete MFA device selection workflow:
        1. Extracts available MFA devices from the page
        2. Logs available methods for debugging
        3. Detects potential rate limiting (if configured)
        4. Builds ChallengeContext and calls callback
        5. Validates selection and submits to Amazon
        6. Returns the resulting page

        Returns:
            SoupPage: The parsed page after device selection submission,
                typically an OTP entry page.

        Raises:
            MFAError: If no MFA options are found on the page or the selected
                value doesn't match any available option.
            CallbackError: If callback execution fails.
            httpx.HTTPError: If the submission request fails.

        Design Decision (DD 12.1):
            Always call callback when MFA-Choice page appears. User can
            implement custom callback for auto-selection if desired.

        Design Decision (DD 12.2):
            Rate limiting detection logs warning but does NOT auto-select.
            User maintains full control over method selection.
        """
        mfa_options = self._extract_mfa_options()

        if not mfa_options:
            logger.error(
                "No MFA methods found on selection page. "
                "Amazon might have changed their HTML structure. "
                "Please report this issue."
            )
            raise MFAError("No MFA options found on MFA selection page")

        # Log available methods for debugging
        method_summary = ", ".join(f"{opt.method}" for opt in mfa_options)
        logger.info(f"Available MFA methods: {method_summary}")

        # Rate limiting detection (optional - needs state tracking)
        # TODO: Implement state tracking across login attempts
        # if hasattr(self, '_last_mfa_method'):
        #     has_previous = any(opt.method == self._last_mfa_method for opt in mfa_options)
        #     if not has_previous:
        #         logger.warning(
        #             f"Previously used method '{self._last_mfa_method}' is no longer available. "
        #             "This might indicate rate limiting."
        #         )

        # Additional heuristic: Very few methods might indicate restriction
        if len(mfa_options) < 2:
            logger.info(
                f"Only {len(mfa_options)} MFA method(s) available. "
                "Some methods might be temporarily unavailable."
            )

        # Build context and call callback (ALWAYS call - DD 12.1)
        context = ChallengeContext(
            challenge_type=ChallengeType.MFA_CHOICE,
            description="Multi-factor authentication device selection",
            soup_page=self.soup_page,
            mfa_options=mfa_options,
        )

        try:
            selected_value = self.callback(context)
            logger.info(f"MFA method selected (value: {selected_value[:20]}...)")
        except Exception as e:
            logger.error(f"MFA choice callback failed: {e}")
            # Fallback: Extract methods and use priority
            logger.warning("Falling back to priority-based selection")
            methods = []
            for opt in mfa_options:
                methods.append(
                    MfaMethod(opt.method, opt.input_value, opt.label, False)
                )
            selected = select_mfa_method_by_priority(methods)
            selected_value = selected.value
            logger.info(f"Auto-selected by priority: {selected.method_type}")

        # Validate selection
        for option in mfa_options:
            if option.input_value == selected_value:
                break
        else:
            raise MFAError("Selected value not in available options")

        # Submit selection via explicit MFA form to avoid posting to wrong endpoint
        form = self.soup_page.soup.find("form", id="auth-select-device-form")
        if not isinstance(form, Tag):
            logger.error("MFA selection form not found on page")
            raise MFAError("Unable to locate MFA selection form")

        inputs: dict[str, str] = {}
        for field in form.find_all("input"):
            name = field.get("name")
            if not isinstance(name, str):
                continue
            value = ""
            if field.get("type") == "hidden":
                value = field.get("value", "")
            inputs[name] = value

        inputs["otpDeviceContext"] = selected_value

        method = form.get("method", "GET")
        action = form.get("action") or ""
        current_url = str(self.soup_page.resp.url)
        target_url = urljoin(current_url, action)

        resp = self.session.request(method, target_url, data=inputs)
        return SoupPage(resp)
