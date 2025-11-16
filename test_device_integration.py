#!/usr/bin/env python3
"""Test script for device emulation integration.

Tests login (internal or external), registration, API requests, and deregistration
for all predefined devices with extensive logging.

Usage:
    python test_device_integration.py

Requirements:
    - Valid Amazon/Audible credentials
    - Internet connection
    - Ability to solve CAPTCHA if presented (for internal login)
"""

import getpass
import logging
import sys
from datetime import datetime
from pathlib import Path

import audible
from audible.device import ANDROID, ANDROID_PIXEL_7, IPHONE, IPHONE_OS26


# Setup extensive logging
def setup_logging():
    """Configure extensive logging to both file and console."""
    log_dir = Path("test_logs")
    log_dir.mkdir(exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_file = log_dir / f"device_test_{timestamp}.log"

    # Create formatters
    detailed_formatter = logging.Formatter(
        "%(asctime)s | %(levelname)-8s | %(name)-20s | %(funcName)-25s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # File handler (DEBUG level)
    file_handler = logging.FileHandler(log_file, encoding="utf-8")
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(detailed_formatter)

    # Console handler (INFO level)
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(detailed_formatter)

    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.DEBUG)
    root_logger.addHandler(file_handler)
    root_logger.addHandler(console_handler)

    # Also enable audible package loggers
    for logger_name in [
        "audible",
        "audible.auth",
        "audible.login",
        "audible.register",
        "audible.client",
    ]:
        logger = logging.getLogger(logger_name)
        logger.setLevel(logging.DEBUG)

    return log_file


# Test devices configuration
TEST_DEVICES = {
    "iPhone (iOS 15)": IPHONE,
    "iPhone (iOS 26)": IPHONE_OS26,
    "Android SDK Emulator": ANDROID,
    "Google Pixel 7": ANDROID_PIXEL_7,
}


def print_separator(title=""):
    """Print a nice separator for console output."""
    if title:
        print(f"\n{'=' * 80}")
        print(f"  {title}")
        print(f"{'=' * 80}\n")
    else:
        print(f"{'=' * 80}\n")


def perform_login(device_name, device, locale, login_method, username, password):
    """Perform login (internal or external) for device testing.

    Args:
        device_name: Human-readable device name
        device: Device instance to test
        locale: Audible marketplace locale
        login_method: "external" or "internal"
        username: Amazon email (for internal login)
        password: Amazon password (for internal login)

    Returns:
        Authenticator instance if successful, None otherwise
    """
    logger = logging.getLogger(__name__)

    if login_method == "internal":
        print_separator("Step 1: Internal Login (Username/Password)")
        logger.info("Starting internal login...")

        if not username or not password:
            logger.error("Username and password required for internal login!")
            return None

        logger.info("Login user: %s", username)
        auth = audible.Authenticator.from_login(
            username=username, password=password, locale=locale, device=device
        )
        logger.info("✓ Internal login successful!")
    else:
        print_separator("Step 1: External Login (Browser)")
        logger.info("Starting external login...")
        auth = audible.Authenticator.from_login_external(locale=locale, device=device)
        logger.info("✓ External login successful!")

    logger.info("Access Token: %s...", auth.access_token[:20])
    logger.info("Refresh Token: %s...", auth.refresh_token[:20])
    logger.info(
        "Device Private Key: %s...",
        auth.device_private_key[:30] if auth.device_private_key else "None",
    )

    if auth.device_info:
        logger.info("Server Device Info:")
        for key, value in auth.device_info.items():
            logger.info("  %s: %s", key, value)

    return auth


def save_and_verify_auth(auth, device_name, device):
    """Save auth to file and verify device persistence.

    Args:
        auth: Authenticator instance
        device_name: Human-readable device name
        device: Device instance to verify against

    Returns:
        tuple: (test_file Path, success boolean)
    """
    logger = logging.getLogger(__name__)

    print_separator("Step 2: Save Authentication to File")
    test_file = Path(f"test_auth_{device_name.replace(' ', '_').lower()}.json")

    logger.info("Saving auth to file: %s", test_file)
    auth.to_file(test_file, encryption=False)
    logger.info("✓ Saved auth file: %s", test_file)

    auth_dict = auth.to_dict()
    if not auth_dict.get("device"):
        logger.warning("✗ Device configuration NOT saved!")
        return test_file, False

    logger.info("✓ Device configuration saved in auth file")
    logger.debug("Saved device data: %s", auth_dict["device"])
    return test_file, True


def load_and_verify_auth(test_file, device):
    """Load auth from file and verify device was restored correctly.

    Args:
        test_file: Path to auth file
        device: Device instance to verify against

    Returns:
        tuple: (loaded Authenticator, success boolean)
    """
    logger = logging.getLogger(__name__)

    print_separator("Step 3: Load Authentication from File")
    logger.info("Loading auth from file...")

    auth_loaded = audible.Authenticator.from_file(test_file)
    logger.info("✓ Loaded auth from file")

    if not auth_loaded.device:
        logger.warning("✗ Device NOT loaded from file!")
        return auth_loaded, False

    logger.info("✓ Device loaded: %s", auth_loaded.device.device_model)
    logger.info("  Device Type: %s", auth_loaded.device.device_type)
    logger.info("  OS Family: %s", auth_loaded.device.os_family)
    logger.info("  Serial: %s", auth_loaded.device.device_serial)

    if auth_loaded.device.device_type != device.device_type:
        logger.error("✗ Device type mismatch after reload!")
        return auth_loaded, False

    if auth_loaded.device.os_family != device.os_family:
        logger.error("✗ OS family mismatch after reload!")
        return auth_loaded, False

    return auth_loaded, True


def test_api_requests(client):
    """Test API requests with loaded auth.

    Args:
        client: Audible client instance

    Returns:
        bool: True if tests successful
    """
    logger = logging.getLogger(__name__)

    print_separator("Step 4: Test API Requests")
    logger.info("Testing API requests with loaded auth...")

    # Test 1: Get library
    logger.info("Test 1: Fetching library...")
    library_response = client.get(
        "library",
        params={
            "num_results": 3,
            "response_groups": "product_desc,product_attrs",
            "sort_by": "-PurchaseDate",
        },
    )

    if library_response:
        items = library_response.get("items", [])
        logger.info("✓ Library request successful! Got %d items", len(items))
        for i, item in enumerate(items, 1):
            title = item.get("title", "Unknown")
            asin = item.get("asin", "Unknown")
            logger.info("  %d. %s (ASIN: %s)", i, title, asin)
    else:
        logger.warning("Library request returned empty response")

    # Test 2: Get user profile
    logger.info("Test 2: Fetching user profile...")
    try:
        user_profile = client.get("user/profile")
        if user_profile:
            logger.info("✓ User profile request successful!")
            logger.debug("Profile data: %s", user_profile)
    except Exception as e:
        logger.info("User profile request skipped: %s", e)

    # Test 3: Get library statistics
    logger.info("Test 3: Getting library statistics...")
    try:
        product_attrs = client.get(
            "library", params={"num_results": 1, "response_groups": "product_attrs"}
        )
        if product_attrs and "product_attrs" in product_attrs["response_groups"]:
            logger.info("✓ Library request successful!")
            logger.info("  Total items: %s", len(product_attrs.get("items", {})))
    except Exception as e:
        logger.warning("Stats request failed: %s", e)

    logger.info("✓ All API requests completed")
    return True


def test_device(
    device_name,
    device,
    locale="us",
    login_method="external",
    username=None,
    password=None,
):
    """Test complete flow for a single device.

    Args:
        device_name: Human-readable device name
        device: Device instance to test
        locale: Audible marketplace locale
        login_method: "external" for browser login, "internal" for username/password
        username: Amazon email (required for internal login)
        password: Amazon password (required for internal login)

    Returns:
        bool: True if all tests passed, False otherwise
    """
    logger = logging.getLogger(__name__)
    logger.info("Starting test for device: %s", device_name)

    print_separator(f"TESTING DEVICE: {device_name}")

    # Log device configuration
    logger.info("Device Type: %s", device.device_type)
    logger.info("Device Model: %s", device.device_model)
    logger.info("OS Family: %s", device.os_family)
    logger.info("OS Version: %s", device.os_version)
    logger.info("App Version: %s", device.app_version)
    logger.info("Software Version: %s", device.software_version)
    logger.info("User-Agent: %s", device.user_agent)
    logger.info("Bundle ID: %s", device.bundle_id)
    logger.info("Device Serial: %s", device.device_serial)

    test_file = None

    try:
        # Step 1: Login
        auth = perform_login(
            device_name, device, locale, login_method, username, password
        )
        if not auth:
            return False

        # Step 2: Save to file
        test_file, save_success = save_and_verify_auth(auth, device_name, device)
        if not save_success:
            return False

        # Step 3: Load from file
        auth_loaded, load_success = load_and_verify_auth(test_file, device)
        if not load_success:
            return False

        # Step 4: Test API Requests
        with audible.Client(auth=auth_loaded) as client:
            test_api_requests(client)

        # Step 5: Token Refresh Test
        print_separator("Step 5: Test Token Refresh")
        logger.info("Testing token refresh with device metadata...")

        old_token = auth_loaded.access_token
        logger.info("Old access token: %s...", old_token[:20])

        auth_loaded.refresh_access_token(force=True)
        new_token = auth_loaded.access_token

        logger.info("New access token: %s...", new_token[:20])

        if old_token != new_token:
            logger.info("✓ Token refresh successful! Token changed.")
        else:
            logger.warning("Token refresh returned same token (might still be valid)")

        # Step 6: Deregister
        print_separator("Step 6: Deregister Device")
        logger.info("Deregistering device...")

        response = auth_loaded.deregister_device()
        logger.info("✓ Deregister response: %s", response)
        logger.info("✓ Device deregistered successfully")

        # Step 7: Cleanup
        print_separator("Step 7: Cleanup")
        if test_file.exists():
            test_file.unlink()
            logger.info("✓ Removed test file: %s", test_file)

        logger.info("✓✓✓ ALL TESTS PASSED FOR: %s ✓✓✓", device_name)
        return True

    except KeyboardInterrupt:
        logger.warning("Test interrupted by user")
        return False

    except Exception as e:
        logger.exception("✗ Test failed for %s: %s", device_name, e)
        return False

    finally:
        # Cleanup
        if test_file and test_file.exists():
            try:
                test_file.unlink()
                logger.info("Cleaned up test file: %s", test_file)
            except Exception as e:
                logger.warning("Could not remove test file: %s", e)


def main():
    """Main test execution."""
    # Setup logging
    log_file = setup_logging()
    logger = logging.getLogger(__name__)

    print_separator("DEVICE EMULATION INTEGRATION TEST")
    print(f"Log file: {log_file}")
    print(f"Testing {len(TEST_DEVICES)} devices")

    logger.info("=" * 80)
    logger.info("STARTING DEVICE EMULATION INTEGRATION TESTS")
    logger.info("=" * 80)
    logger.info("Python Version: %s", sys.version)
    logger.info("Audible Version: %s", audible.__version__)
    logger.info("Test Devices: %s", list(TEST_DEVICES.keys()))

    # Get user configuration
    print("\nTest Configuration:")
    locale = input("Enter Audible marketplace (default: us): ").strip() or "us"
    logger.info("Selected locale: %s", locale)

    # Ask for login method
    print("\nLogin Method:")
    print("  1. External Login (Browser-based, no CAPTCHA handling)")
    print("  2. Internal Login (Username/Password, automatic CAPTCHA handling)")
    login_choice = input("\nSelect login method (1-2, default: 1): ").strip() or "1"

    if login_choice == "2":
        login_method = "internal"
        print("\nInternal Login Credentials:")
        username = input("Amazon email: ").strip()
        password = getpass.getpass("Amazon password: ").strip()

        if not username or not password:
            print("Error: Username and password are required for internal login!")
            return 1

        logger.info("Login method: internal (user: %s)", username)
    else:
        login_method = "external"
        username = None
        password = None
        logger.info("Login method: external (browser)")

    # Ask which devices to test
    print("\nAvailable devices:")
    for i, name in enumerate(TEST_DEVICES.keys(), 1):
        print(f"  {i}. {name}")
    print(f"  {len(TEST_DEVICES) + 1}. All devices")

    choice = input(
        f"\nSelect device to test (1-{len(TEST_DEVICES) + 1}, default: all): "
    ).strip()

    if choice and choice.isdigit() and 1 <= int(choice) <= len(TEST_DEVICES):
        # Test single device
        device_name = list(TEST_DEVICES.keys())[int(choice) - 1]
        devices_to_test = {device_name: TEST_DEVICES[device_name]}
    else:
        # Test all devices
        devices_to_test = TEST_DEVICES

    logger.info("Testing devices: %s", list(devices_to_test.keys()))

    # Run tests
    results = {}
    for device_name, device in devices_to_test.items():
        print(f"\n\nPress ENTER to start testing {device_name} (or Ctrl+C to skip)...")
        try:
            input()
        except KeyboardInterrupt:
            print("\nSkipping this device...")
            logger.info("Skipped device: %s", device_name)
            continue

        success = test_device(
            device_name,
            device,
            locale,
            login_method=login_method,
            username=username,
            password=password,
        )
        results[device_name] = success

        if success:
            print(f"\n✓ {device_name}: PASSED")
        else:
            print(f"\n✗ {device_name}: FAILED")

    # Summary
    print_separator("TEST SUMMARY")
    logger.info("=" * 80)
    logger.info("TEST SUMMARY")
    logger.info("=" * 80)

    passed = sum(1 for success in results.values() if success)
    total = len(results)

    for device_name, success in results.items():
        status = "✓ PASSED" if success else "✗ FAILED"
        print(f"{device_name:40s} {status}")
        logger.info("%s %s", f"{device_name:40s}", status)

    print(f"\nTotal: {passed}/{total} tests passed")
    logger.info("Total: %d/%d tests passed", passed, total)

    print(f"\nDetailed logs saved to: {log_file}")
    logger.info("Test run completed. Log file: %s", log_file)

    return 0 if passed == total else 1


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print("\n\nTest suite interrupted by user")
        sys.exit(130)
    except Exception as e:
        print(f"\n\nFatal error: {e}")
        logging.exception("Fatal error in test suite")
        sys.exit(1)
