"""Tests for the device module."""

from __future__ import annotations

from dataclasses import dataclass

import pytest

from audible.device import (
    ANDROID,
    IPHONE,
    BaseDevice,
    _AndroidDevice,
    _iPhoneDevice,
    create_android_device,
    create_iphone_device,
)


# Test fixtures and helpers


@dataclass
class ConcreteDevice(BaseDevice):
    """Concrete implementation of BaseDevice for testing abstract class."""

    os_family: str = "test"

    def _generate_user_agent(self) -> str:
        """Generate test user agent."""
        return f"TestAgent/{self.app_version}"

    def _generate_bundle_id(self) -> str:
        """Generate test bundle ID."""
        return "com.test.app"

    def _detect_os_family(self) -> str:
        """Return test OS family."""
        return "test"


@pytest.fixture
def base_device() -> BaseDevice:
    """Create a concrete BaseDevice instance for testing."""
    return ConcreteDevice(
        device_type="TEST_TYPE",
        device_model="Test Device",
        app_version="1.0.0",
        os_version="1.0.0",
        software_version="10000",
    )


@pytest.fixture
def iphone_device() -> _iPhoneDevice:
    """Create an iPhone device instance for testing."""
    return _iPhoneDevice(
        device_type="A2CZJZGLK2JJVM",
        device_model="iPhone",
        app_version="3.56.2",
        os_version="15.0.0",
        software_version="35602678",
    )


@pytest.fixture
def android_device() -> _AndroidDevice:
    """Create an Android device instance for testing."""
    return _AndroidDevice(
        device_type="A10KISP2GWF0E4",
        device_model="Pixel 7",
        device_product="pixel7_x86_64",
        app_version="177102",
        os_version="Android/pixel7_x86_64:13/TP1A.220624.021/12345678:user/release-keys",
        os_version_number="33",
        software_version="130050002",
    )


# BaseDevice Tests


def test_base_device_post_init(base_device: BaseDevice) -> None:
    """Test that __post_init__ auto-generates fields."""
    assert base_device.user_agent == "TestAgent/1.0.0"
    assert base_device.bundle_id == "com.test.app"
    assert base_device.os_family == "test"
    assert base_device.download_user_agent == base_device.user_agent
    assert base_device.device_serial  # Should be auto-generated
    assert len(base_device.device_serial) == 32  # UUID hex without dashes


def test_base_device_custom_user_agent() -> None:
    """Test that custom user agent is not overwritten."""
    device = ConcreteDevice(
        device_type="TEST",
        device_model="Test",
        app_version="1.0",
        os_version="1.0",
        software_version="1000",
        user_agent="CustomAgent/2.0",
    )
    assert device.user_agent == "CustomAgent/2.0"


def test_base_device_custom_serial() -> None:
    """Test that custom device serial is preserved."""
    custom_serial = "CUSTOM123456"
    device = ConcreteDevice(
        device_type="TEST",
        device_model="Test",
        app_version="1.0",
        os_version="1.0",
        software_version="1000",
        device_serial=custom_serial,
    )
    assert device.device_serial == custom_serial


def test_base_device_copy(base_device: BaseDevice) -> None:
    """Test device copy with modifications."""
    # Copy with changes
    new_device = base_device.copy(app_version="2.0.0")

    # Original should be unchanged
    assert base_device.app_version == "1.0.0"

    # New device should have changes
    assert new_device.app_version == "2.0.0"
    assert new_device.device_model == base_device.device_model
    assert new_device.device_type == base_device.device_type

    # Serial should be different (auto-generated)
    assert new_device.device_serial != base_device.device_serial


def test_base_device_copy_preserves_custom_serial() -> None:
    """Test that copy() preserves custom serial if explicitly provided."""
    device = ConcreteDevice(
        device_type="TEST",
        device_model="Test",
        app_version="1.0",
        os_version="1.0",
        software_version="1000",
        device_serial="SERIAL123",
    )

    # Copy with explicit serial
    new_device = device.copy(device_serial="SERIAL456")
    assert new_device.device_serial == "SERIAL456"


def test_base_device_to_dict(base_device: BaseDevice) -> None:
    """Test device serialization to dictionary."""
    device_dict = base_device.to_dict()

    assert isinstance(device_dict, dict)
    assert device_dict["device_type"] == "TEST_TYPE"
    assert device_dict["device_model"] == "Test Device"
    assert device_dict["app_version"] == "1.0.0"
    assert device_dict["os_version"] == "1.0.0"
    assert device_dict["software_version"] == "10000"
    assert device_dict["user_agent"] == "TestAgent/1.0.0"
    assert device_dict["bundle_id"] == "com.test.app"
    assert device_dict["os_family"] == "test"


def test_base_device_from_dict() -> None:
    """Test device deserialization from dictionary."""
    device_data = {
        "device_type": "TEST_TYPE",
        "device_model": "Test Device",
        "app_version": "1.0.0",
        "os_version": "1.0.0",
        "software_version": "10000",
        "device_serial": "SERIAL123",
        "os_family": "test",
    }

    device = ConcreteDevice.from_dict(device_data)

    assert device.device_type == "TEST_TYPE"
    assert device.device_model == "Test Device"
    assert device.app_version == "1.0.0"
    assert device.device_serial == "SERIAL123"
    assert device.os_family == "test"


def test_base_device_round_trip_serialization(base_device: BaseDevice) -> None:
    """Test that to_dict() -> from_dict() preserves all data."""
    device_dict = base_device.to_dict()
    restored_device = ConcreteDevice.from_dict(device_dict)

    assert restored_device.device_type == base_device.device_type
    assert restored_device.device_model == base_device.device_model
    assert restored_device.app_version == base_device.app_version
    assert restored_device.device_serial == base_device.device_serial
    assert restored_device.user_agent == base_device.user_agent
    assert restored_device.bundle_id == base_device.bundle_id


def test_base_device_build_client_id(base_device: BaseDevice) -> None:
    """Test OAuth client ID generation."""
    client_id = base_device.build_client_id()

    # Should be hex string
    assert isinstance(client_id, str)
    int(client_id, 16)  # Should not raise

    # Should encode serial#device_type
    expected = (
        base_device.device_serial.encode() + b"#" + base_device.device_type.encode()
    )
    assert client_id == expected.hex()


def test_base_device_get_registration_data(base_device: BaseDevice) -> None:
    """Test registration data format."""
    reg_data = base_device.get_registration_data()

    assert reg_data["domain"] == "Device"
    assert reg_data["app_version"] == "1.0.0"
    assert reg_data["device_serial"] == base_device.device_serial
    assert reg_data["device_type"] == "TEST_TYPE"
    assert reg_data["device_model"] == "Test Device"
    assert reg_data["os_version"] == "1.0.0"
    assert reg_data["software_version"] == "10000"
    assert reg_data["app_name"] == "Audible"


def test_base_device_get_token_refresh_data(base_device: BaseDevice) -> None:
    """Test token refresh data format."""
    refresh_data = base_device.get_token_refresh_data()

    assert refresh_data["app_name"] == "Audible"
    assert refresh_data["app_version"] == "1.0.0"


def test_base_device_get_init_cookies(base_device: BaseDevice) -> None:
    """Test login cookies generation."""
    cookies = base_device.get_init_cookies()

    # Should contain required cookies
    assert "frc" in cookies
    assert "map-md" in cookies
    assert "amzn-app-id" in cookies

    # frc should be base64-encoded random bytes
    assert len(cookies["frc"]) > 100
    # Base64 can contain A-Z, a-z, 0-9, +, / (and = for padding which is stripped)
    import string

    valid_chars = set(string.ascii_letters + string.digits + "+/")
    assert all(c in valid_chars for c in cookies["frc"])

    # map-md should be base64-encoded JSON
    assert len(cookies["map-md"]) > 10

    # amzn-app-id should be the default
    assert "MAPLib" in cookies["amzn-app-id"]


def test_base_device_frc_randomness() -> None:
    """Test that frc tokens are unique (random)."""
    device = ConcreteDevice(
        device_type="TEST",
        device_model="Test",
        app_version="1.0",
        os_version="1.0",
        software_version="1000",
    )

    cookies1 = device.get_init_cookies()
    cookies2 = device.get_init_cookies()

    # frc should be different each time (random)
    assert cookies1["frc"] != cookies2["frc"]


# iPhone Device Tests


def test_iphone_device_user_agent(iphone_device: _iPhoneDevice) -> None:
    """Test iPhone User-Agent generation."""
    ua = iphone_device.user_agent

    assert "Mozilla/5.0 (iPhone; CPU iPhone OS" in ua
    assert "15_0_0" in ua  # OS version with underscores
    assert "like Mac OS X" in ua
    assert "AppleWebKit" in ua
    assert "Mobile/15E148" in ua


def test_iphone_device_bundle_id(iphone_device: _iPhoneDevice) -> None:
    """Test iPhone bundle ID generation."""
    assert iphone_device.bundle_id == "com.audible.iphone"


def test_iphone_device_amzn_app_id(iphone_device: _iPhoneDevice) -> None:
    """Test iPhone Amazon app ID."""
    assert iphone_device.amzn_app_id == "MAPiOSLib/6.0/ToHideRetailLink"


def test_iphone_device_os_family(iphone_device: _iPhoneDevice) -> None:
    """Test iPhone OS family detection."""
    assert iphone_device.os_family == "ios"


def test_iphone_device_os_version_extraction(iphone_device: _iPhoneDevice) -> None:
    """Test iOS version number extraction."""
    assert iphone_device.os_version_number == "15"


def test_iphone_device_os_version_extraction_various_formats() -> None:
    """Test OS version extraction with different formats."""
    # Standard format (x.y.z)
    device1 = _iPhoneDevice(
        device_type="A2CZJZGLK2JJVM",
        device_model="iPhone",
        app_version="3.56.2",
        os_version="16.2.1",
        software_version="35602678",
    )
    assert device1.os_version_number == "16"

    # Simple format (x.y)
    device2 = _iPhoneDevice(
        device_type="A2CZJZGLK2JJVM",
        device_model="iPhone",
        app_version="3.56.2",
        os_version="17.0",
        software_version="35602678",
    )
    assert device2.os_version_number == "17"

    # Single digit (should work)
    device3 = _iPhoneDevice(
        device_type="A2CZJZGLK2JJVM",
        device_model="iPhone",
        app_version="3.56.2",
        os_version="18",
        software_version="35602678",
    )
    assert device3.os_version_number == "18"


def test_iphone_predefined_instance() -> None:
    """Test IPHONE predefined instance (iOS 26.1)."""
    assert IPHONE.device_type == "A2CZJZGLK2JJVM"
    assert IPHONE.device_model == "iPhone"
    assert IPHONE.app_version == "4.56.2"
    assert IPHONE.os_version == "26.1"
    assert IPHONE.os_version_number == "26"
    assert IPHONE.software_version == "45602826"
    assert IPHONE.os_family == "ios"
    assert "Audible for iPhone" in IPHONE.device_name


def test_iphone_serialization_round_trip() -> None:
    """Test iPhone serialization and deserialization."""
    original = IPHONE.copy()
    device_dict = original.to_dict()
    restored = _iPhoneDevice.from_dict(device_dict)

    assert restored.device_type == original.device_type
    assert restored.device_model == original.device_model
    assert restored.app_version == original.app_version
    assert restored.os_version == original.os_version
    assert restored.os_family == original.os_family
    assert restored.user_agent == original.user_agent


# Android Device Tests


def test_android_device_user_agent_full_format(android_device: _AndroidDevice) -> None:
    """Test Android User-Agent generation with full version string."""
    ua = android_device.user_agent

    assert "Dalvik/2.1.0" in ua
    assert "Linux; U;" in ua
    assert "Pixel 7" in ua
    assert "Build/13" in ua  # Build version from :13/...


def test_android_device_user_agent_simple_format() -> None:
    """Test Android User-Agent generation with simple version string."""
    device = _AndroidDevice(
        device_type="A10KISP2GWF0E4",
        device_model="Test Android",
        app_version="177102",
        os_version="14.0",
        software_version="130050002",
    )

    ua = device.user_agent
    assert "Dalvik/2.1.0" in ua
    assert "Linux; U; Android 14.0" in ua
    assert "Test Android" in ua


def test_android_device_download_user_agent(android_device: _AndroidDevice) -> None:
    """Test Android download User-Agent generation."""
    download_ua = android_device.download_user_agent

    assert "com.audible.application" in download_ua
    assert "Linux;Android 33" in download_ua
    assert "AndroidXMedia3" in download_ua


def test_android_device_bundle_id(android_device: _AndroidDevice) -> None:
    """Test Android package name generation."""
    assert android_device.bundle_id == "com.audible.application"


def test_android_device_amzn_app_id(android_device: _AndroidDevice) -> None:
    """Test Android Amazon app ID."""
    assert android_device.amzn_app_id == "MAPAndroidLib/6.0/ToHideRetailLink"


def test_android_device_os_family(android_device: _AndroidDevice) -> None:
    """Test Android OS family detection."""
    assert android_device.os_family == "android"


def test_android_device_app_name(android_device: _AndroidDevice) -> None:
    """Test Android app name (package name)."""
    assert android_device.app_name == "com.audible.application"


def test_android_device_os_version_extraction() -> None:
    """Test Android OS version extraction from full format."""
    # Full format: "Android/device:13/build/..."
    # Create device without explicit os_version_number to test auto-extraction
    device = _AndroidDevice(
        device_type="A10KISP2GWF0E4",
        device_model="Pixel 7",
        app_version="177102",
        os_version="Android/pixel7_x86_64:13/TP1A.220624.021/12345678:user/release-keys",
        software_version="130050002",
    )
    assert device.os_version_number == "13"


def test_android_device_os_version_extraction_various_formats() -> None:
    """Test OS version extraction with different Android formats."""
    # SDK format
    device1 = _AndroidDevice(
        device_type="A10KISP2GWF0E4",
        device_model="Android",
        app_version="177102",
        os_version="Android/sdk_phone64_x86_64:14/UE1A.230829.036.A1/11228894:userdebug/test-keys",
        software_version="130050002",
    )
    assert device1.os_version_number == "14"

    # Simple format fallback
    device2 = _AndroidDevice(
        device_type="A10KISP2GWF0E4",
        device_model="Android",
        app_version="177102",
        os_version="13.0",
        software_version="130050002",
    )
    # Fallback extraction should get "13"
    assert device2.os_version_number == "13"


def test_android_predefined_instance() -> None:
    """Test ANDROID predefined instance (OnePlus 8, Android 11)."""
    assert ANDROID.device_type == "A10KISP2GWF0E4"
    assert ANDROID.device_model == "IN2013"
    assert ANDROID.device_product == "OnePlus8"
    assert ANDROID.app_version == "160008"
    assert "OnePlus/OnePlus8/OnePlus8:11" in ANDROID.os_version
    assert ANDROID.os_version_number == "30"
    assert ANDROID.software_version == "130050002"
    assert ANDROID.os_family == "android"
    assert "Audible for Android" in ANDROID.device_name


def test_android_serialization_round_trip() -> None:
    """Test Android serialization and deserialization."""
    original = ANDROID.copy()
    device_dict = original.to_dict()
    restored = _AndroidDevice.from_dict(device_dict)

    assert restored.device_type == original.device_type
    assert restored.device_model == original.device_model
    assert restored.app_version == original.app_version
    assert restored.os_version == original.os_version
    assert restored.os_family == original.os_family
    assert restored.user_agent == original.user_agent
    assert restored.download_user_agent == original.download_user_agent


# Cross-Device Tests


def test_device_serial_uniqueness() -> None:
    """Test that device copies have unique serial numbers."""
    device1 = IPHONE.copy()
    device2 = IPHONE.copy()
    device3 = ANDROID.copy()

    # All should have different serials
    serials = {device1.device_serial, device2.device_serial, device3.device_serial}
    assert len(serials) == 3

    # Serials should be valid UUIDs (hex format)
    for serial in serials:
        assert len(serial) == 32
        int(serial, 16)  # Should not raise


def test_device_serial_format() -> None:
    """Test that auto-generated serials are uppercase hex."""
    device = IPHONE.copy()

    # Should be uppercase hex string
    assert device.device_serial.isupper()
    assert all(c in "0123456789ABCDEF" for c in device.device_serial)


def test_client_id_uniqueness() -> None:
    """Test that different devices produce different client IDs."""
    iphone = IPHONE.copy()
    android = ANDROID.copy()

    client_id_1 = iphone.build_client_id()
    client_id_2 = android.build_client_id()

    assert client_id_1 != client_id_2


def test_registration_data_contains_required_fields() -> None:
    """Test that registration data contains all required fields."""
    required_fields = [
        "domain",
        "app_version",
        "device_serial",
        "device_type",
        "device_name",
        "os_version",
        "software_version",
        "device_model",
        "app_name",
    ]

    for device in [IPHONE, ANDROID]:
        reg_data = device.get_registration_data()
        for field in required_fields:
            assert field in reg_data, f"Missing field: {field}"
            assert reg_data[field], f"Empty field: {field}"


def test_init_cookies_base64_encoding() -> None:
    """Test that init cookies are properly base64 encoded."""
    import base64

    device = IPHONE.copy()
    cookies = device.get_init_cookies()

    # map-md should decode to valid JSON
    try:
        map_md_decoded = base64.b64decode(cookies["map-md"] + "==")
        # Should be valid UTF-8 JSON
        map_md_str = map_md_decoded.decode("utf-8")
        assert "device_registration_data" in map_md_str
        assert "app_identifier" in map_md_str
    except Exception as e:
        pytest.fail(f"map-md cookie is not valid base64 JSON: {e}")


def test_device_copy_changes_only_specified_fields() -> None:
    """Test that copy only changes the specified fields."""
    original = IPHONE
    modified = original.copy(app_version="999.999.999")

    # Changed field
    assert modified.app_version == "999.999.999"

    # Unchanged fields (except serial which is auto-regenerated)
    assert modified.device_type == original.device_type
    assert modified.device_model == original.device_model
    assert modified.os_version == original.os_version
    assert modified.software_version == original.software_version
    assert modified.os_family == original.os_family

    # Serial should be different
    assert modified.device_serial != original.device_serial


def test_device_dict_can_be_used_for_serialization() -> None:
    """Test that to_dict produces JSON-serializable output."""
    import json

    for device in [IPHONE, ANDROID]:
        device_dict = device.to_dict()

        # Should be JSON-serializable
        try:
            json_str = json.dumps(device_dict)
            recovered = json.loads(json_str)
            assert recovered == device_dict
        except (TypeError, ValueError) as e:
            pytest.fail(f"Device dict not JSON-serializable: {e}")


# Factory Function Tests


def test_create_iphone_device_default() -> None:
    """Test creating iPhone device with default parameters."""
    device = create_iphone_device()

    # Should return IPHONE with same attributes
    assert device.device_model == "iPhone"
    assert device.os_family == "ios"
    assert device.device_type == IPHONE.device_type
    assert device.app_version == IPHONE.app_version
    assert device.os_version == IPHONE.os_version
    # Serial should be different (copy generates new serial)
    assert device.device_serial != IPHONE.device_serial


def test_create_iphone_device_custom_app_version() -> None:
    """Test creating iPhone device with custom app version."""
    device = create_iphone_device(app_version="4.60.0")

    assert device.app_version == "4.60.0"
    assert device.os_version == IPHONE.os_version  # Should keep default
    assert device.device_model == "iPhone"


def test_create_iphone_device_custom_os_version() -> None:
    """Test creating iPhone device with custom OS version."""
    device = create_iphone_device(os_version="27.0")

    assert device.os_version == "27.0"
    assert device.os_version_number == "27"  # Should be extracted
    assert device.app_version == IPHONE.app_version  # Should keep default


def test_create_iphone_device_custom_versions() -> None:
    """Test creating iPhone device with both custom versions."""
    device = create_iphone_device(app_version="4.60.0", os_version="27.0")

    assert device.app_version == "4.60.0"
    assert device.os_version == "27.0"
    assert device.os_version_number == "27"
    assert device.device_model == "iPhone"
    assert device.os_family == "ios"


def test_create_iphone_device_custom_serial() -> None:
    """Test creating iPhone device with custom serial."""
    device = create_iphone_device(device_serial="CUSTOM123")

    assert device.device_serial == "CUSTOM123"
    assert device.app_version == IPHONE.app_version
    assert device.os_version == IPHONE.os_version


def test_create_android_device_default() -> None:
    """Test creating Android device with default parameters."""
    device = create_android_device()

    # Should return ANDROID with same attributes
    assert device.device_model == "IN2013"
    assert device.os_family == "android"
    assert device.device_type == ANDROID.device_type
    assert device.app_version == ANDROID.app_version
    assert device.os_version == ANDROID.os_version
    # Serial should be different (copy generates new serial)
    assert device.device_serial != ANDROID.device_serial


def test_create_android_device_custom_app_version() -> None:
    """Test creating Android device with custom app version."""
    device = create_android_device(app_version="170000")

    assert device.app_version == "170000"
    assert device.os_version == ANDROID.os_version  # Should keep default
    assert device.device_model == "IN2013"


def test_create_android_device_custom_os_version() -> None:
    """Test creating Android device with custom OS version (build fingerprint)."""
    custom_os = (
        "OnePlus/OnePlus8/OnePlus8:12/SP1A.210812.016/2112142300:user/release-keys"
    )
    device = create_android_device(os_version=custom_os)

    assert device.os_version == custom_os
    assert device.os_version_number == "12"  # Should be extracted from ":12/"
    assert device.app_version == ANDROID.app_version  # Should keep default


def test_create_android_device_custom_versions() -> None:
    """Test creating Android device with both custom versions."""
    custom_os = (
        "OnePlus/OnePlus8/OnePlus8:12/SP1A.210812.016/2112142300:user/release-keys"
    )
    device = create_android_device(app_version="170000", os_version=custom_os)

    assert device.app_version == "170000"
    assert device.os_version == custom_os
    assert device.os_version_number == "12"
    assert device.device_model == "IN2013"
    assert device.os_family == "android"


def test_create_android_device_custom_serial() -> None:
    """Test creating Android device with custom serial."""
    device = create_android_device(device_serial="ANDROID123")

    assert device.device_serial == "ANDROID123"
    assert device.app_version == ANDROID.app_version
    assert device.os_version == ANDROID.os_version


def test_factory_functions_return_basedevice_type() -> None:
    """Test that factory functions return BaseDevice type."""
    iphone = create_iphone_device()
    android = create_android_device()

    assert isinstance(iphone, BaseDevice)
    assert isinstance(android, BaseDevice)
    # They should also be private class instances
    assert isinstance(iphone, _iPhoneDevice)
    assert isinstance(android, _AndroidDevice)


def test_private_classes_not_exported() -> None:
    """Test that private classes cannot be imported from public API."""
    # This test verifies the classes are marked private
    # The actual import blocking is tested by attempting imports
    from audible import device

    # Private classes should exist in module but not be in __all__
    assert hasattr(device, "_iPhoneDevice")
    assert hasattr(device, "_AndroidDevice")
    assert "_iPhoneDevice" not in device.__all__
    assert "_AndroidDevice" not in device.__all__

    # Public items should be in __all__
    assert "IPHONE" in device.__all__
    assert "ANDROID" in device.__all__
    assert "create_iphone_device" in device.__all__
    assert "create_android_device" in device.__all__
    assert "BaseDevice" in device.__all__
