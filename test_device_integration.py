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
from audible.device import ANDROID, ANDROID_PIXEL_7, IPHONE, IPHONE_16


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
        datefmt="%Y-%m-%d %H:%M:%S"
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
    for logger_name in ["audible", "audible.auth", "audible.login", "audible.register", "audible.client"]:
        logger = logging.getLogger(logger_name)
        logger.setLevel(logging.DEBUG)

    return log_file


# Test devices configuration
TEST_DEVICES = {
    "iPhone (iOS 15)": IPHONE,
    "iPhone 16 (iOS 18)": IPHONE_16,
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


def test_device(device_name, device, locale="us", login_method="external", username=None, password=None):
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
    logger.info(f"Starting test for device: {device_name}")

    print_separator(f"TESTING DEVICE: {device_name}")

    # Log device configuration
    logger.info(f"Device Type: {device.device_type}")
    logger.info(f"Device Model: {device.device_model}")
    logger.info(f"OS Family: {device.os_family}")
    logger.info(f"OS Version: {device.os_version}")
    logger.info(f"App Version: {device.app_version}")
    logger.info(f"Software Version: {device.software_version}")
    logger.info(f"User-Agent: {device.user_agent}")
    logger.info(f"Bundle ID: {device.bundle_id}")
    logger.info(f"Device Serial: {device.device_serial}")

    auth = None
    test_file = None

    try:
        # Step 1: Login (External or Internal)
        if login_method == "internal":
            print_separator("Step 1: Internal Login (Username/Password)")
            logger.info("Starting internal login...")

            if not username or not password:
                logger.error("Username and password required for internal login!")
                return False

            logger.info(f"Login user: {username}")

            auth = audible.Authenticator.from_login(
                username=username,
                password=password,
                locale=locale,
                device=device
            )

            logger.info("✓ Internal login successful!")
        else:
            print_separator("Step 1: External Login (Browser)")
            logger.info("Starting external login...")

            auth = audible.Authenticator.from_login_external(
                locale=locale,
                device=device
            )

            logger.info("✓ External login successful!")

        logger.info(f"Access Token: {auth.access_token[:20]}...")
        logger.info(f"Refresh Token: {auth.refresh_token[:20]}...")
        logger.info(f"Device Private Key: {auth.device_private_key[:30] if auth.device_private_key else 'None'}...")

        # Log device info from server
        if auth.device_info:
            logger.info("Server Device Info:")
            for key, value in auth.device_info.items():
                logger.info(f"  {key}: {value}")

        # Step 2: Save to file
        print_separator("Step 2: Save Authentication to File")
        test_file = Path(f"test_auth_{device_name.replace(' ', '_').lower()}.json")

        logger.info(f"Saving auth to file: {test_file}")
        auth.to_file(test_file, encryption=False)
        logger.info(f"✓ Saved auth file: {test_file}")

        # Verify device is saved
        auth_dict = auth.to_dict()
        if auth_dict.get("device"):
            logger.info("✓ Device configuration saved in auth file")
            logger.debug(f"Saved device data: {auth_dict['device']}")
        else:
            logger.warning("✗ Device configuration NOT saved!")
            return False

        # Step 3: Load from file
        print_separator("Step 3: Load Authentication from File")
        logger.info("Loading auth from file...")

        auth_loaded = audible.Authenticator.from_file(test_file)
        logger.info("✓ Loaded auth from file")

        # Verify device was loaded correctly
        if auth_loaded.device:
            logger.info(f"✓ Device loaded: {auth_loaded.device.device_model}")
            logger.info(f"  Device Type: {auth_loaded.device.device_type}")
            logger.info(f"  OS Family: {auth_loaded.device.os_family}")
            logger.info(f"  Serial: {auth_loaded.device.device_serial}")

            # Verify device matches
            if auth_loaded.device.device_type != device.device_type:
                logger.error("✗ Device type mismatch after reload!")
                return False
            if auth_loaded.device.os_family != device.os_family:
                logger.error("✗ OS family mismatch after reload!")
                return False
        else:
            logger.warning("✗ Device NOT loaded from file!")
            return False

        # Step 4: Test API Requests
        print_separator("Step 4: Test API Requests")

        with audible.Client(auth=auth_loaded) as client:
            logger.info("Testing API requests with loaded auth...")

            # Test 1: Get library
            logger.info("Test 1: Fetching library...")
            library_response = client.get(
                "library",
                params={
                    "num_results": 3,
                    "response_groups": "product_desc,product_attrs",
                    "sort_by": "-PurchaseDate"
                }
            )

            if library_response:
                items = library_response.get("items", [])
                logger.info(f"✓ Library request successful! Got {len(items)} items")
                for i, item in enumerate(items, 1):
                    title = item.get("title", "Unknown")
                    asin = item.get("asin", "Unknown")
                    logger.info(f"  {i}. {title} (ASIN: {asin})")
            else:
                logger.warning("Library request returned empty response")

            # Test 2: Get user profile
            logger.info("Test 2: Fetching user profile...")
            try:
                # This endpoint might not work for all regions
                user_profile = client.get("user/profile")
                if user_profile:
                    logger.info("✓ User profile request successful!")
                    logger.debug(f"Profile data: {user_profile}")
            except Exception as e:
                logger.info(f"User profile request skipped: {e}")

            # Test 3: Get library statistics
            logger.info("Test 3: Getting library statistics...")
            try:
                stats = client.get(
                    "library",
                    params={
                        "num_results": 1,
                        "response_groups": "stats"
                    }
                )
                if stats and "stats" in stats:
                    logger.info("✓ Library stats request successful!")
                    logger.info(f"  Total items: {stats.get('stats', {}).get('total', 'Unknown')}")
            except Exception as e:
                logger.warning(f"Stats request failed: {e}")

        logger.info("✓ All API requests completed")

        # Step 5: Token Refresh Test
        print_separator("Step 5: Test Token Refresh")
        logger.info("Testing token refresh with device metadata...")

        old_token = auth_loaded.access_token
        logger.info(f"Old access token: {old_token[:20]}...")

        auth_loaded.refresh_access_token(force=True)
        new_token = auth_loaded.access_token

        logger.info(f"New access token: {new_token[:20]}...")

        if old_token != new_token:
            logger.info("✓ Token refresh successful! Token changed.")
        else:
            logger.warning("Token refresh returned same token (might still be valid)")

        # Step 6: Deregister
        print_separator("Step 6: Deregister Device")
        logger.info("Deregistering device...")

        response = auth_loaded.deregister_device()
        logger.info(f"✓ Deregister response: {response}")
        logger.info("✓ Device deregistered successfully")

        # Step 7: Cleanup
        print_separator("Step 7: Cleanup")
        if test_file.exists():
            test_file.unlink()
            logger.info(f"✓ Removed test file: {test_file}")

        logger.info(f"✓✓✓ ALL TESTS PASSED FOR: {device_name} ✓✓✓")
        return True

    except KeyboardInterrupt:
        logger.warning("Test interrupted by user")
        return False

    except Exception as e:
        logger.error(f"✗ Test failed for {device_name}: {e}", exc_info=True)
        return False

    finally:
        # Cleanup
        if test_file and test_file.exists():
            try:
                test_file.unlink()
                logger.info(f"Cleaned up test file: {test_file}")
            except Exception as e:
                logger.warning(f"Could not remove test file: {e}")


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
    logger.info(f"Python Version: {sys.version}")
    logger.info(f"Audible Version: {audible.__version__}")
    logger.info(f"Test Devices: {list(TEST_DEVICES.keys())}")

    # Get user configuration
    print("\nTest Configuration:")
    locale = input("Enter Audible marketplace (default: us): ").strip() or "us"
    logger.info(f"Selected locale: {locale}")

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

        logger.info(f"Login method: internal (user: {username})")
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

    choice = input(f"\nSelect device to test (1-{len(TEST_DEVICES) + 1}, default: all): ").strip()

    if choice and choice.isdigit() and 1 <= int(choice) <= len(TEST_DEVICES):
        # Test single device
        device_name = list(TEST_DEVICES.keys())[int(choice) - 1]
        devices_to_test = {device_name: TEST_DEVICES[device_name]}
    else:
        # Test all devices
        devices_to_test = TEST_DEVICES

    logger.info(f"Testing devices: {list(devices_to_test.keys())}")

    # Run tests
    results = {}
    for device_name, device in devices_to_test.items():
        print(f"\n\nPress ENTER to start testing {device_name} (or Ctrl+C to skip)...")
        try:
            input()
        except KeyboardInterrupt:
            print("\nSkipping this device...")
            logger.info(f"Skipped device: {device_name}")
            continue

        success = test_device(
            device_name,
            device,
            locale,
            login_method=login_method,
            username=username,
            password=password
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
        logger.info(f"{device_name:40s} {status}")

    print(f"\nTotal: {passed}/{total} tests passed")
    logger.info(f"Total: {passed}/{total} tests passed")

    print(f"\nDetailed logs saved to: {log_file}")
    logger.info(f"Test run completed. Log file: {log_file}")

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
