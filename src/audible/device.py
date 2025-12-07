"""Device emulation for Audible authentication and API access.

This module provides device emulation for Audible-capable devices with
complete device metadata including OS versions, app versions, User-Agent
strings, and registration data.

Two predefined device configurations are available:
- **IPHONE**: iPhone running iOS 26.1 with Audible 4.56.2
- **ANDROID**: OnePlus 8 running Android 11 with Audible 160008

Version customization is supported through factory functions that allow
updating OS and app versions to mimic real-world software updates.

Device emulation enables:
- Proper authentication and device registration
- User-Agent spoofing for API compatibility
- DRM type selection (FairPlay for iOS, Widevine for Android)
- Device-specific API features

Example:
    Use predefined devices::

        from audible.device import IPHONE, ANDROID

        # Use iPhone for registration
        auth = Authenticator.from_login("user", "pass", "us", device=IPHONE)

        # Use Android device
        auth = Authenticator.from_login("user", "pass", "us", device=ANDROID)

    Customize device versions::

        from audible.device import create_iphone_device, create_android_device

        # Create iPhone with custom version
        iphone = create_iphone_device(
            app_version="4.60.0",
            os_version="26.1"
        )

        # Create Android with custom app version
        android = create_android_device(app_version="170000")

        # Use customized device
        auth = Authenticator.from_login("user", "pass", "us", device=iphone)

Note:
    Direct instantiation of device classes is not supported. Use the
    predefined IPHONE/ANDROID constants or the factory functions
    create_iphone_device() and create_android_device() instead.
"""

from __future__ import annotations

import base64
import secrets
import uuid
from abc import ABC, abstractmethod
from dataclasses import asdict, dataclass, field
from typing import TYPE_CHECKING, Any


if TYPE_CHECKING:
    pass


@dataclass
class BaseDevice(ABC):
    """Base class for Audible device emulation.

    This abstract base class defines the common interface and attributes
    for all Audible devices. Inherit from this class to create custom
    device implementations.

    Attributes:
        device_type: Amazon device type identifier.
            Examples: "A2CZJZGLK2JJVM" (iPhone), "A10KISP2GWF0E4" (Android)
        device_model: Human-readable device model.
            Examples: "iPhone", "Pixel 7", "Fire HD 10"
        app_version: Audible app version string.
            Examples: "3.56.2" (iOS), "177102" (Android)
        os_version: Operating system version string.
            Examples: "15.0.0" (iOS), "Android/sdk_phone64_x86_64:14/..."
        software_version: Numerical software version.
            Examples: "35602678" (iOS), "130050002" (Android)
        app_name: Application identifier/name.
            Examples: "Audible" (iOS), "com.audible.application" (Android)
        device_name: Device name template used during registration.
        device_serial: Unique device serial number (auto-generated if None).
        user_agent: HTTP User-Agent string for login/API requests.
        download_user_agent: HTTP User-Agent for media downloads.
        bundle_id: App bundle/package identifier.
        amzn_app_id: Amazon application identifier for login cookies.
        os_family: Operating system family ("ios", "android").
        os_version_number: Numeric OS version.
        device_product: Device product identifier (Android).
        domain: Registration domain (usually "Device").

    Example:
        Create custom device by inheriting::

            from audible.device import BaseDevice
            from dataclasses import dataclass

            @dataclass
            class FireTVDevice(BaseDevice):
                def _generate_user_agent(self) -> str:
                    return f"FireTV/{self.app_version}"

                def _generate_bundle_id(self) -> str:
                    return "com.audible.firetv"

    See Also:
        - :class:`iPhoneDevice` - iPhone/iOS implementation
        - :class:`AndroidDevice` - Android implementation
    """

    device_type: str
    device_model: str
    app_version: str
    os_version: str
    software_version: str
    app_name: str = "Audible"
    device_name: str = field(
        default_factory=lambda: (
            "%FIRST_NAME%%FIRST_NAME_POSSESSIVE_STRING%%DUPE_"
            "STRATEGY_1ST%Audible Device"
        )
    )
    device_serial: str = field(default_factory=lambda: uuid.uuid4().hex.upper())
    user_agent: str = ""
    download_user_agent: str = ""
    bundle_id: str = ""
    amzn_app_id: str = ""
    os_family: str = ""
    os_version_number: str = ""
    device_product: str = ""
    domain: str = "Device"

    def __post_init__(self) -> None:
        """Initialize derived fields after instance creation."""
        # Auto-generate fields if not provided
        if not self.user_agent:
            self.user_agent = self._generate_user_agent()
        if not self.download_user_agent:
            self.download_user_agent = self._generate_download_user_agent()
        if not self.bundle_id:
            self.bundle_id = self._generate_bundle_id()
        if not self.amzn_app_id:
            self.amzn_app_id = self._generate_amzn_app_id()
        if not self.os_family:
            self.os_family = self._detect_os_family()
        if not self.os_version_number:
            self.os_version_number = self._extract_os_version_number()

    @abstractmethod
    def _generate_user_agent(self) -> str:
        """Generate User-Agent header for HTTP requests.

        Returns:
            User-Agent string appropriate for this device type.
        """
        ...

    @abstractmethod
    def _generate_bundle_id(self) -> str:
        """Generate app bundle/package identifier.

        Returns:
            Bundle ID string (e.g., "com.audible.iphone").
        """
        ...

    @abstractmethod
    def _detect_os_family(self) -> str:
        """Detect OS family from device type or model.

        Returns:
            OS family string ("ios", "android", etc.).
        """
        ...

    def _generate_download_user_agent(self) -> str:
        """Generate User-Agent for media downloads.

        Default implementation returns the same as regular user_agent.
        Override in subclasses if download UA differs (e.g., Android).

        Returns:
            Download User-Agent string.
        """
        return self.user_agent

    def _generate_amzn_app_id(self) -> str:
        """Generate Amazon app ID for login cookies.

        Returns:
            Amazon app ID string.
        """
        return "MAPLib/6.0/ToHideRetailLink"

    def _extract_os_version_number(self) -> str:
        """Extract numeric OS version from os_version string.

        Returns:
            Numeric version string.
        """
        return ""

    def copy(self, **changes: Any) -> BaseDevice:
        """Create a copy of this device with modifications.

        Args:
            **changes: Attributes to override in the copy.

        Returns:
            A new device instance with the specified changes.

        Example:
            Update app version::

                iphone = IPHONE
                iphone_new = iphone.copy(
                    app_version="3.60.0",
                    software_version="36000078"
                )
        """
        data = asdict(self)
        data.update(changes)
        # Generate new serial if not explicitly provided
        if "device_serial" not in changes:
            data["device_serial"] = uuid.uuid4().hex.upper()
        return type(self)(**data)

    def to_dict(self) -> dict[str, Any]:
        """Convert device to dictionary for serialization.

        Returns:
            Dictionary containing all device attributes.
        """
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> BaseDevice:
        """Create device from dictionary.

        Args:
            data: Dictionary containing device attributes.

        Returns:
            New device instance populated from dictionary.

        Note:
            This method attempts to instantiate the specific subclass.
            For deserialization, the correct subclass must be used.
        """
        return cls(**data)

    def build_client_id(self) -> str:
        """Build client ID for OAuth (serial#device_type in hex).

        Returns:
            Hexadecimal client ID string.
        """
        client_id = self.device_serial.encode() + b"#" + self.device_type.encode()
        return client_id.hex()

    def get_registration_data(self) -> dict[str, str]:
        """Get registration data for device registration API call.

        Returns:
            Dictionary with registration-specific fields.
        """
        return {
            "domain": self.domain,
            "app_version": self.app_version,
            "device_serial": self.device_serial,
            "device_type": self.device_type,
            "device_name": self.device_name,
            "os_version": self.os_version,
            "software_version": self.software_version,
            "device_model": self.device_model,
            "app_name": self.app_name,
        }

    def get_token_refresh_data(self) -> dict[str, str]:
        """Get data for token/cookie refresh API calls.

        Returns:
            Dictionary with app name and version for refresh requests.
        """
        return {
            "app_name": self.app_name,
            "app_version": self.app_version,
        }

    def get_init_cookies(self) -> dict[str, str]:
        """Build initial cookies for login (frc, map-md, amzn-app-id).

        Returns:
            Dictionary with login cookies to prevent CAPTCHA.
        """
        from .json_provider import get_json_provider

        # FRC token (random bytes)
        token_bytes = secrets.token_bytes(313)
        frc = base64.b64encode(token_bytes).decode("ascii").rstrip("=")

        # MAP-MD metadata
        map_md_dict = {
            "device_user_dictionary": [],
            "device_registration_data": {"software_version": self.software_version},
            "app_identifier": {
                "app_version": self.app_version,
                "bundle_id": self.bundle_id,
            },
        }
        map_md_str = get_json_provider().dumps(map_md_dict)
        map_md = base64.b64encode(map_md_str.encode()).decode().rstrip("=")

        return {
            "frc": frc,
            "map-md": map_md,
            "amzn-app-id": self.amzn_app_id,
        }


@dataclass
class _iPhoneDevice(BaseDevice):
    """iPhone/iOS device emulation (internal implementation).

    This is an internal implementation class. Users should use the IPHONE
    constant or create_iphone_device() factory function instead.

    Implements iPhone-specific User-Agent generation, bundle IDs,
    and default configurations for iOS devices.

    Attributes:
        os_family: The OS family identifier (always "ios").
        app_name: The application name (always "Audible").
    """

    os_family: str = "ios"
    app_name: str = "Audible"

    def _generate_user_agent(self) -> str:
        """Generate iOS User-Agent string."""
        os_version_ua = self.os_version.replace(".", "_")
        return (
            f"Mozilla/5.0 (iPhone; CPU iPhone OS {os_version_ua} like Mac OS X) "
            "AppleWebKit/605.1.15 (KHTML, like Gecko) Mobile/15E148"
        )

    def _generate_bundle_id(self) -> str:
        """Generate iOS bundle identifier."""
        return "com.audible.iphone"

    def _generate_amzn_app_id(self) -> str:
        """Generate iOS Amazon app ID."""
        return "MAPiOSLib/6.0/ToHideRetailLink"

    def _detect_os_family(self) -> str:
        """Return iOS as OS family."""
        return "ios"

    def _extract_os_version_number(self) -> str:
        """Extract major iOS version (e.g., '15.0.0' -> '15')."""
        return (
            self.os_version.split(".")[0] if "." in self.os_version else self.os_version
        )


@dataclass
class _AndroidDevice(BaseDevice):
    """Android device emulation (internal implementation).

    This is an internal implementation class. Users should use the ANDROID
    constant or create_android_device() factory function instead.

    Implements Android-specific User-Agent generation, package names,
    and default configurations for Android devices.

    Attributes:
        os_family: The OS family identifier (always "android").
        app_name: The application package name (always "com.audible.application").

    Note:
        Based on real Android Audible app configuration from
        https://github.com/rmcrackan/AudibleApi/pull/55
    """

    os_family: str = "android"
    app_name: str = "com.audible.application"

    def _generate_user_agent(self) -> str:
        """Generate Android User-Agent string (Dalvik format)."""
        if "/" in self.os_version and ":" in self.os_version:
            # Full Android version string format
            # Extract build ID from the version string
            build = self.os_version.split(":")[1].split("/")[0]
            # Use os_version_number for the Android version (e.g., "14", "13")
            android_version = self.os_version_number or build
            return (
                f"Dalvik/2.1.0 (Linux; U; Android {android_version}; "
                f"{self.device_model} Build/{build})"
            )
        else:
            # Simple version format
            return (
                f"Dalvik/2.1.0 (Linux; U; Android {self.os_version}; "
                f"{self.device_model})"
            )

    def _generate_download_user_agent(self) -> str:
        """Generate Android download User-Agent (player SDK format)."""
        android_version = self.os_version_number or "14"
        return (
            f"{self.app_name}/3.96.1 (Linux;Android {android_version}) "
            "AndroidXMedia3/1.3.0"
        )

    def _generate_bundle_id(self) -> str:
        """Generate Android package name."""
        return "com.audible.application"

    def _generate_amzn_app_id(self) -> str:
        """Generate Android Amazon app ID."""
        return "MAPAndroidLib/6.0/ToHideRetailLink"

    def _detect_os_family(self) -> str:
        """Return android as OS family."""
        return "android"

    def _extract_os_version_number(self) -> str:
        """Extract Android SDK level from version string."""
        if ":" in self.os_version and "/" in self.os_version:
            # Format: "Android/device:14/build/..." -> "14"
            try:
                parts = self.os_version.split(":")
                if len(parts) > 1:
                    return parts[1].split("/")[0]
            except (IndexError, ValueError):
                pass
        # Fallback: extract from simple version
        return self.os_version.replace(".", "").replace("Android", "").strip()[:2]


# Predefined device instances

IPHONE = _iPhoneDevice(
    device_type="A2CZJZGLK2JJVM",
    device_model="iPhone",
    app_version="4.56.2",
    os_version="26.1",
    os_version_number="26",
    software_version="45602826",
    device_name=(
        "%FIRST_NAME%%FIRST_NAME_POSSESSIVE_STRING%%DUPE_STRATEGY_1ST%"
        "Audible for iPhone"
    ),
)
"""iPhone running iOS 26.1 with Audible 4.56.2.

This is the primary iPhone device configuration for Audible authentication.

Example:
    >>> from audible.device import IPHONE
    >>> auth = Authenticator.from_login("user", "pass", "us", device=IPHONE)
    >>>
    >>> # Customize version
    >>> from audible.device import create_iphone_device
    >>> custom_iphone = create_iphone_device(app_version="4.60.0", os_version="27.0")
"""

ANDROID = _AndroidDevice(
    device_type="A10KISP2GWF0E4",
    device_model="IN2013",
    device_product="OnePlus8",
    app_version="160008",
    os_version="OnePlus/OnePlus8/OnePlus8:11/RP1A.201005.001/2110102308:user/release-keys",
    os_version_number="30",
    software_version="130050002",
    device_name=(
        "%FIRST_NAME%%FIRST_NAME_POSSESSIVE_STRING%%DUPE_STRATEGY_1ST%"
        "Audible for Android"
    ),
)
"""OnePlus 8 running Android 11 with Audible 160008.

This is the primary Android device configuration based on real device
specifications from widevine.py DRM implementation.

Example:
    >>> from audible.device import ANDROID
    >>> auth = Authenticator.from_login("user", "pass", "us", device=ANDROID)
    >>>
    >>> # Customize version
    >>> from audible.device import create_android_device
    >>> custom_android = create_android_device(app_version="170000")
"""


# Factory functions for device customization


def create_iphone_device(
    app_version: str | None = None,
    os_version: str | None = None,
    device_serial: str | None = None,
) -> BaseDevice:
    """Create iPhone device with custom version parameters.

    This function creates an iPhone device based on the IPHONE constant,
    allowing customization of version parameters to mimic OS/app updates
    on a real iPhone.

    Args:
        app_version: Audible app version (e.g., "4.60.0").
            If None, uses default from IPHONE constant.
        os_version: iOS version (e.g., "27.0").
            If None, uses default from IPHONE constant.
        device_serial: Unique device serial number.
            If None, auto-generates a new UUID-based serial.

    Returns:
        BaseDevice: Configured iPhone device instance.

    Example:
        >>> from audible.device import create_iphone_device
        >>>
        >>> # Create device with custom app version
        >>> device = create_iphone_device(app_version="4.60.0")
        >>>
        >>> # Create device with custom OS and app versions
        >>> device = create_iphone_device(
        ...     app_version="4.60.0",
        ...     os_version="27.0"
        ... )
        >>>
        >>> # Create device with custom serial (for multi-device support)
        >>> device = create_iphone_device(device_serial="CUSTOM123")

    Note:
        Only version parameters can be customized. Hardware-specific
        attributes (device_type, device_model) remain fixed to match
        real iPhone behavior where only software updates are possible.
    """
    changes: dict[str, Any] = {}
    if app_version:
        changes["app_version"] = app_version
        # Note: software_version could be derived from app_version
        # but we keep it simple and let users handle it if needed
    if os_version:
        changes["os_version"] = os_version
        # Extract os_version_number from os_version
        os_version_number = (
            os_version.split(".")[0] if "." in os_version else os_version
        )
        changes["os_version_number"] = os_version_number
    if device_serial:
        changes["device_serial"] = device_serial
    # Always copy to generate new serial (unless explicitly provided)
    return IPHONE.copy(**changes)


def create_android_device(
    app_version: str | None = None,
    os_version: str | None = None,
    device_serial: str | None = None,
) -> BaseDevice:
    """Create Android device with custom version parameters.

    This function creates an Android device based on the ANDROID constant
    (OnePlus 8), allowing customization of version parameters to mimic
    OS/app updates on a real Android device.

    Args:
        app_version: Audible app version code (e.g., "170000").
            If None, uses default from ANDROID constant.
        os_version: Android build fingerprint string.
            If None, uses default from ANDROID constant.
            Format: "Manufacturer/Product/Device:Version/BuildID/..."
        device_serial: Unique device serial number.
            If None, auto-generates a new UUID-based serial.

    Returns:
        BaseDevice: Configured Android device instance.

    Example:
        >>> from audible.device import create_android_device
        >>>
        >>> # Create device with custom app version
        >>> device = create_android_device(app_version="170000")
        >>>
        >>> # Create device with custom build fingerprint
        >>> device = create_android_device(
        ...     os_version="OnePlus/OnePlus8/OnePlus8:12/SP1A.210812.016/2112142300:user/release-keys"
        ... )
        >>>
        >>> # Create device with custom serial
        >>> device = create_android_device(device_serial="ANDROID123")

    Note:
        Only version parameters can be customized. Hardware-specific
        attributes (device_type, device_model, device_product) remain
        fixed to match real Android behavior.
    """
    changes: dict[str, Any] = {}
    if app_version:
        changes["app_version"] = app_version
    if os_version:
        changes["os_version"] = os_version
        # Extract os_version_number (SDK level) from build fingerprint
        if ":" in os_version and "/" in os_version:
            try:
                parts = os_version.split(":")
                if len(parts) > 1:
                    sdk_level = parts[1].split("/")[0]
                    changes["os_version_number"] = sdk_level
            except (IndexError, ValueError):
                pass  # Keep default if parsing fails
    if device_serial:
        changes["device_serial"] = device_serial
    # Always copy to generate new serial (unless explicitly provided)
    return ANDROID.copy(**changes)


__all__ = [
    "ANDROID",
    "IPHONE",
    "BaseDevice",
    "create_android_device",
    "create_iphone_device",
]
