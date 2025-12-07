"""External login functionality for browser-based authentication.

This module provides functions for logging in to Audible using an external
browser (manual or automated with Playwright).
"""

from __future__ import annotations

import logging
from collections.abc import Callable
from textwrap import dedent
from typing import TYPE_CHECKING, Any, cast

import httpx

from audible.exceptions import AudibleError
from audible.localization import Locale

from audible.login import LoginResult, extract_authorization_code_from_url


if TYPE_CHECKING:
    from audible.device import BaseDevice


logger = logging.getLogger(__name__)


def playwright_external_login_url_callback(
    url: str, device: BaseDevice | None = None
) -> str:
    """Automated browser login using Playwright.

    Launches a headless browser, navigates to the OAuth URL, and waits for
    the user to complete login. Returns the redirect URL containing the
    authorization code.

    This requires playwright to be installed:
        pip install playwright
        playwright install chromium

    Args:
        url: The OAuth URL to navigate to.
        device: The device to use for cookies. If ``None``, uses default
            iPhone device.

    Returns:
        str: The redirect URL containing the authorization code.

    Raises:
        AudibleError: If timeout occurs during login or playwright encounters
            an error.

    Example:
        >>> url = "https://www.amazon.com/ap/signin?..."  # doctest: +SKIP
        >>> redirect_url = playwright_external_login_url_callback(url)  # doctest: +SKIP

    .. versionadded:: v0.11.0
           The device argument
    """
    from playwright.sync_api import (  # noqa: I001, PLC0415
        Error,
        TimeoutError as PlaywrightTimeoutError,
        sync_playwright,
    )

    timeout_seconds = 300

    # choose between chromium, webkit and firefox
    playwright_browser = "chromium"

    # Get cookies from device
    if device is None:
        from audible.device import IPHONE  # noqa: PLC0415

        device = IPHONE

    with sync_playwright() as p:
        iphone = p.devices["iPhone 15 Pro"]
        browser = p.__getitem__(playwright_browser).launch(headless=False)
        context = browser.new_context(**iphone)

        try:
            cookies = []
            for name, value in device.get_init_cookies().items():
                cookies.append({"name": name, "value": value, "url": url})
            context.add_cookies(cast(Any, cookies))

            page = browser.new_page()
            page.goto(url)

            with page.expect_request(
                "**/ap/maplanding*", timeout=timeout_seconds * 1000
            ) as request_info:
                request = request_info.value
                if "openid.oa2.authorization_code" in request.url:
                    request_url: str = request.url
        except PlaywrightTimeoutError:
            logger.error("Timeout during login.")
            raise AudibleError("Timeout during login using playwright.") from None
        except Error as error:
            logger.error(error.message)
            raise AudibleError(error.message) from None
        finally:
            context.close()
            browser.close()

    return request_url


def default_login_url_callback(url: str) -> str:
    """Default callback that prompts user to manually complete login.

    First attempts to use Playwright for automated login. If Playwright is not
    available, falls back to manual login where the user opens the URL in
    their browser and copies the redirect URL.

    Args:
        url: The OAuth URL to display to the user.

    Returns:
        str: The redirect URL provided by the user (or from Playwright).

    Example:
        >>> url = "https://www.amazon.com/ap/signin?..."  # doctest: +SKIP
        >>> redirect_url = default_login_url_callback(url)  # doctest: +SKIP
        # User opens browser, completes login, and pastes redirect URL
    """
    try:
        return playwright_external_login_url_callback(url)
    except ImportError:
        pass

    message = f"""\
        Please copy the following url and insert it into a web browser of your choice:

        {url}

        Now you have to login with your Amazon credentials. After submit your username
        and password you have to do this a second time and solving a captcha before
        sending the login form.

        After login, your browser will show you an error page (Page not found). Do not
        worry about this. It has to be like this. Please copy the url from the address
        bar in your browser now.

        IMPORTANT:
        If you are using MacOS and have trouble insert the login result url, simply
        import the readline module in your script.

        Please insert the copied url (after login):
    """
    print(dedent(message))
    return input()


def external_login(
    locale: Locale,
    with_username: bool = False,
    login_url_callback: Callable[[str], str] | None = None,
    device: BaseDevice | None = None,
) -> LoginResult:
    """Browser-based login to Amazon/Audible.

    Generates an OAuth URL, opens it in a browser (automated or manual), and
    extracts the authorization code from the redirect URL after successful login.

    This is an alternative to the automated LoginService for users who:
    - Prefer manual browser login
    - Want to see the login process
    - Have issues with automated CAPTCHA solving

    Note:
        If you are using MacOS and have trouble inserting the login result URL,
        simply import the readline module in your script. See
        `#34 <https://github.com/mkb79/Audible/issues/34#issuecomment-766408640>`_.

    Args:
        locale: Marketplace locale for login
        with_username: If ``True``, login with Audible username instead of
            Amazon account.
        login_url_callback: A custom callable for handling login with external
            browsers. If ``None``, :func:`default_login_url_callback` is used.
        device: The device to use for login. If ``None``, uses default iPhone
            device.

    Returns:
        LoginResult: Contains authorization code, PKCE verifier, locale,
            and device information needed for registration

    Example:
        >>> from audible.login import external_login  # doctest: +SKIP
        >>> result = external_login(  # doctest: +SKIP
        ...     locale=Locale("us"),
        ... )
        >>> print(result.authorization_code)  # doctest: +SKIP

    .. versionadded:: v0.11.0
           The device argument
    """
    from .pkce import PKCE  # noqa: PLC0415
    from .url_builder import OAuthURLBuilder  # noqa: PLC0415

    # Handle device parameter with backward compatibility
    if device is None:
        from audible.device import IPHONE  # noqa: PLC0415

        device = IPHONE.copy()

    # Generate PKCE
    pkce = PKCE.generate()

    # Build OAuth URL
    oauth_builder = OAuthURLBuilder(
        locale=locale,
        pkce=pkce,
        device=device,
        with_username=with_username,
    )
    oauth_url = oauth_builder.build()

    # Get redirect URL from callback
    if login_url_callback:
        _response_url = login_url_callback(oauth_url)
    else:
        _response_url = default_login_url_callback(oauth_url)

    response_url = httpx.URL(_response_url)
    authorization_code = extract_authorization_code_from_url(response_url)

    return LoginResult(
        authorization_code=authorization_code,
        pkce=pkce,
        locale=locale,
        device=device,
    )
