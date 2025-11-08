"""Device emulation for Audible authentication and API access.

This module provides device classes for emulating different Audible-capable
devices (iPhone, Android, Fire Tablet, etc.) with complete device metadata
including OS versions, app versions, DRM capabilities, and codec support.

Device emulation enables:
- Access to device-specific features (e.g., Dolby Atmos on compatible devices)
- Proper User-Agent spoofing for API compatibility
- DRM type selection (FairPlay for iOS, Widevine for Android)
- Codec support negotiation

Example:
    Use predefined devices::

        from audible.device import IPHONE, ANDROID

        # Use iPhone for registration
        auth = Authenticator.from_login("user", "pass", "us", device=IPHONE)

        # Use Android device
        auth = Authenticator.from_login("user", "pass", "us", device=ANDROID)

    Create custom device::

        from audible.device import iPhoneDevice

        # Customize existing device
        my_iphone = iPhoneDevice(
            app_version="3.60.0",
            os_version="16.0.0"
        )

        # Create completely custom device
        from audible.device import BaseDevice

        class MyCustomDevice(BaseDevice):
            def _generate_user_agent(self) -> str:
                return f"MyApp/{self.app_version}"
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
        from .json import get_json_provider

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
class iPhoneDevice(BaseDevice):
    """iPhone/iOS device emulation.

    Implements iPhone-specific User-Agent generation, bundle IDs,
    and default configurations for iOS devices.

    Attributes:
        os_family: The OS family identifier (always "ios" for iPhoneDevice).
        app_name: The application name (always "Audible" for iPhoneDevice).

    Example:
        Use default iPhone configuration::

            from audible.device import IPHONE
            device = IPHONE

        Customize iPhone::

            from audible.device import iPhoneDevice

            my_iphone = iPhoneDevice(
                device_type="A2CZJZGLK2JJVM",
                device_model="iPhone",
                app_version="3.60.0",
                os_version="16.0.0",
                software_version="36000078"
            )

    See Also:
        - Predefined instances: :data:`IPHONE`, :data:`IPHONE_16`
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
class AndroidDevice(BaseDevice):
    """Android device emulation.

    Implements Android-specific User-Agent generation, package names,
    and default configurations for Android devices.

    Attributes:
        os_family: The OS family identifier (always "android" for AndroidDevice).
        app_name: The application package name (always "com.audible.application" for AndroidDevice).

    Example:
        Use default Android configuration::

            from audible.device import ANDROID
            device = ANDROID

        Customize Android device::

            from audible.device import AndroidDevice

            my_android = AndroidDevice(
                device_type="A10KISP2GWF0E4",
                device_model="Pixel 7",
                device_product="pixel7_x86_64",
                app_version="177102",
                os_version="Android/pixel7_x86_64:13/TP1A.220624.021/12345678:user/release-keys",
                os_version_number="33",
                software_version="130050002"
            )

    Note:
        Based on real Android Audible app configuration from
        https://github.com/rmcrackan/AudibleApi/pull/55

    See Also:
        - Predefined instances: :data:`ANDROID`, :data:`ANDROID_PIXEL_7`
    """

    os_family: str = "android"
    app_name: str = "com.audible.application"

    def _generate_user_agent(self) -> str:
        """Generate Android User-Agent string (Dalvik format)."""
        if "/" in self.os_version and ":" in self.os_version:
            # Full Android version string format
            android_version = (
                self.os_version.split("/")[0].replace("Android", "").strip()
            )
            build = self.os_version.split(":")[1].split("/")[0]
            return (
                f"Dalvik/2.1.0 (Linux; U; {android_version}; "
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

IPHONE = iPhoneDevice(
    device_type="A2CZJZGLK2JJVM",
    device_model="iPhone",
    app_version="3.56.2",
    os_version="15.0.0",
    os_version_number="15",
    software_version="35602678",
    device_name=(
        "%FIRST_NAME%%FIRST_NAME_POSSESSIVE_STRING%%DUPE_STRATEGY_1ST%"
        "Audible for iPhone"
    ),
)
"""iPhone 15 running iOS 15.0 with Audible 3.56.2.

Example:
    >>> from audible.device import IPHONE
    >>> auth = Authenticator.from_login("user", "pass", "us", device=IPHONE)
"""

IPHONE_OS26 = iPhoneDevice(
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

Latest iOS version with updated Audible app.
"""

ANDROID = AndroidDevice(
    device_type="A10KISP2GWF0E4",
    device_model="Android SDK built for x86_64",
    device_product="sdk_phone64_x86_64",
    app_version="177102",
    os_version="Android/sdk_phone64_x86_64:14/UE1A.230829.036.A1/11228894:userdebug/test-keys",
    os_version_number="34",
    software_version="130050002",
    device_name=(
        "%FIRST_NAME%%FIRST_NAME_POSSESSIVE_STRING%%DUPE_STRATEGY_1ST%"
        "Audible for Android"
    ),
)
"""Android device (SDK built for x86_64) with Audible app.

Based on real Android Audible app configuration.

Example:
    >>> from audible.device import ANDROID
    >>> auth = Authenticator.from_login("user", "pass", "us", device=ANDROID)
"""

ANDROID_PIXEL_7 = AndroidDevice(
    device_type="A10KISP2GWF0E4",
    device_model="Pixel 7",
    device_product="pixel7_x86_64",
    app_version="177102",
    os_version="Android/pixel7_x86_64:13/TP1A.220624.021/12345678:user/release-keys",
    os_version_number="33",
    software_version="130050002",
    device_name=(
        "%FIRST_NAME%%FIRST_NAME_POSSESSIVE_STRING%%DUPE_STRATEGY_1ST%"
        "Audible for Android"
    ),
)
"""Google Pixel 7 running Android 13 with Audible app.

Customized Android profile for a real device.
"""
