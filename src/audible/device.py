"""Device emulation for Audible authentication and API access.

This module provides the Device class for emulating different Audible-capable
devices (iPhone, Android, Fire Tablet, etc.) with complete device metadata
including OS versions, app versions, DRM capabilities, and codec support.

Device emulation enables:
- Access to device-specific features (e.g., Dolby Atmos on compatible devices)
- Proper User-Agent spoofing for API compatibility
- DRM type selection (FairPlay for iOS, Widevine for Android)
- Codec support negotiation
"""

from __future__ import annotations

import base64
import secrets
import uuid
from dataclasses import asdict, dataclass, field
from typing import TYPE_CHECKING, Any, ClassVar


if TYPE_CHECKING:
    pass


@dataclass
class Device:
    """Represents an Audible device configuration.

    This class encapsulates all device-specific data needed for:
    - Device registration with Audible servers
    - API authentication and requests
    - Token/cookie refresh operations
    - Feature detection (e.g., Dolby Atmos, spatial audio)
    - DRM and codec negotiation

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
        download_user_agent: HTTP User-Agent string for media downloads
            (may differ from main user_agent on Android).
        bundle_id: App bundle/package identifier.
            Examples: "com.audible.iphone", "com.audible.application"
        amzn_app_id: Amazon application identifier for login cookies.
        os_family: Operating system family.
            Examples: "ios", "android"
        os_version_number: Numeric OS version (Android SDK level).
            Examples: "34" (Android 14), "16" (iOS 16)
        device_product: Device product identifier (Android).
            Example: "sdk_phone64_x86_64"
        supported_codecs: Audio codecs supported by this device.
            Examples: ["mp4a.40.2", "ec+3"] (Dolby Atmos capable)
        supported_drm_types: DRM types supported by this device.
            Examples: ["FairPlay", "Adrm"] (iOS), ["Widevine"] (Android)
        domain: Registration domain (usually "Device").

    Example:
        Use predefined iPhone device::

            device = Device.IPHONE

        Create custom Android device::

            device = Device.ANDROID.copy(
                device_model="Pixel 7",
                os_version_number="33"
            )

        Create completely custom device::

            device = Device(
                device_type="CUSTOM123",
                device_model="My Device",
                app_version="3.60.0",
                os_version="16.0.0",
                software_version="36000078",
                supported_codecs=["mp4a.40.2", "ec+3"],
                supported_drm_types=["FairPlay", "Adrm"]
            )

    Note:
        Device instances are immutable after creation. Use :meth:`copy` to
        create modified versions.

    See Also:
        - :meth:`Authenticator.from_login` - Use device during registration
        - :meth:`Authenticator.update_device` - Update device metadata
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
    supported_codecs: list[str] = field(default_factory=lambda: ["mp4a.40.2"])
    supported_drm_types: list[str] = field(default_factory=lambda: ["Adrm"])
    domain: str = "Device"

    # Class-level constants for predefined devices
    _IPHONE_DEFAULTS: ClassVar[dict[str, Any]] = {
        "device_type": "A2CZJZGLK2JJVM",
        "device_model": "iPhone",
        "app_version": "3.56.2",
        "os_version": "15.0.0",
        "software_version": "35602678",
        "app_name": "Audible",
        "os_family": "ios",
        "os_version_number": "15",
        "bundle_id": "com.audible.iphone",
        "device_name": (
            "%FIRST_NAME%%FIRST_NAME_POSSESSIVE_STRING%%DUPE_"
            "STRATEGY_1ST%Audible for iPhone"
        ),
        "user_agent": (
            "Mozilla/5.0 (iPhone; CPU iPhone OS 15_0 like Mac OS X) "
            "AppleWebKit/605.1.15 (KHTML, like Gecko) Mobile/15E148"
        ),
        "amzn_app_id": "MAPiOSLib/6.0/ToHideRetailLink",
        "supported_codecs": ["mp4a.40.2", "mp4a.40.42", "ec+3"],
        "supported_drm_types": ["Mpeg", "Adrm", "FairPlay"],
    }

    _ANDROID_DEFAULTS: ClassVar[dict[str, Any]] = {
        "device_type": "A10KISP2GWF0E4",
        "device_model": "Android SDK built for x86_64",
        "app_version": "177102",
        "os_version": (
            "Android/sdk_phone64_x86_64:14/UE1A.230829.036.A1/11228894:"
            "userdebug/test-keys"
        ),
        "software_version": "130050002",
        "app_name": "com.audible.application",
        "os_family": "android",
        "os_version_number": "34",
        "device_product": "sdk_phone64_x86_64",
        "bundle_id": "com.audible.application",
        "device_name": (
            "%FIRST_NAME%%FIRST_NAME_POSSESSIVE_STRING%%DUPE_"
            "STRATEGY_1ST%Audible for Android"
        ),
        "user_agent": (
            "Dalvik/2.1.0 (Linux; U; Android 14; Android SDK built for "
            "x86_64 Build/UE1A.230829.036.A1)"
        ),
        "download_user_agent": (
            "com.audible.playersdk.player/3.96.1 (Linux;Android 14) "
            "AndroidXMedia3/1.3.0"
        ),
        "amzn_app_id": "MAPAndroidLib/6.0/ToHideRetailLink",
        "supported_codecs": ["mp4a.40.2", "mp4a.40.42", "ec+3", "ac-4"],
        "supported_drm_types": [
            "Adrm",
            "Hls",
            "PlayReady",
            "Mpeg",
            "Dash",
            "Widevine",
        ],
    }

    def __post_init__(self) -> None:
        """Validate and auto-generate derived fields if not provided."""
        # Auto-generate user_agent if not provided
        if not self.user_agent:
            self.user_agent = self._generate_user_agent()

        # Auto-generate download_user_agent if not provided and needed
        if not self.download_user_agent:
            if self.os_family == "android":
                self.download_user_agent = self._generate_download_user_agent()
            else:
                # iOS uses same user agent for downloads
                self.download_user_agent = self.user_agent

        # Auto-generate bundle_id if not provided
        if not self.bundle_id:
            self.bundle_id = self._generate_bundle_id()

        # Auto-generate amzn_app_id if not provided
        if not self.amzn_app_id:
            self.amzn_app_id = self._generate_amzn_app_id()

        # Auto-detect os_family if not provided
        if not self.os_family:
            self.os_family = self._detect_os_family()

        # Auto-generate os_version_number if not provided
        if not self.os_version_number:
            self.os_version_number = self._extract_os_version_number()

    def _generate_user_agent(self) -> str:
        """Generate User-Agent based on device type and OS."""
        if self.os_family == "ios" or "iPhone" in self.device_model:
            # iOS format: Replace dots with underscores for OS version
            os_version_ua = self.os_version.replace(".", "_")
            return (
                f"Mozilla/5.0 (iPhone; CPU iPhone OS {os_version_ua} like Mac OS X) "
                "AppleWebKit/605.1.15 (KHTML, like Gecko) Mobile/15E148"
            )
        elif self.os_family == "android" or "Android" in self.device_model:
            # Android format: Use device model and build info
            if "/" in self.os_version:
                # Full Android version string
                return (
                    f"Dalvik/2.1.0 (Linux; U; {self.os_version.split('/')[0]}; "
                    f"{self.device_model} Build/{self.os_version.split(':')[1].split('/')[0]})"
                )
            else:
                # Simple version
                return (
                    f"Dalvik/2.1.0 (Linux; U; Android {self.os_version}; "
                    f"{self.device_model})"
                )
        else:
            # Generic fallback
            return f"Audible/{self.app_version} ({self.device_model}; {self.os_version})"

    def _generate_download_user_agent(self) -> str:
        """Generate download User-Agent for Android devices."""
        if self.os_family == "android":
            # Extract Android version number
            android_version = self.os_version_number or "14"
            return (
                f"{self.app_name}/3.96.1 (Linux;Android {android_version}) "
                "AndroidXMedia3/1.3.0"
            )
        return self.user_agent

    def _generate_bundle_id(self) -> str:
        """Generate bundle ID based on OS family."""
        if self.os_family == "ios" or "iPhone" in self.device_model:
            return "com.audible.iphone"
        elif self.os_family == "android" or "Android" in self.device_model:
            return "com.audible.application"
        else:
            return "com.audible.app"

    def _generate_amzn_app_id(self) -> str:
        """Generate Amazon app ID based on OS family."""
        if self.os_family == "ios" or "iPhone" in self.device_model:
            return "MAPiOSLib/6.0/ToHideRetailLink"
        elif self.os_family == "android" or "Android" in self.device_model:
            return "MAPAndroidLib/6.0/ToHideRetailLink"
        else:
            return "MAPLib/6.0/ToHideRetailLink"

    def _detect_os_family(self) -> str:
        """Auto-detect OS family from device type or model."""
        if "iPhone" in self.device_model or "iOS" in self.os_version:
            return "ios"
        elif "Android" in self.device_model or "Android" in self.os_version:
            return "android"
        elif "Fire" in self.device_model:
            return "android"  # Fire OS is Android-based
        return ""

    def _extract_os_version_number(self) -> str:
        """Extract numeric OS version from os_version string."""
        if self.os_family == "ios":
            # Extract major version from "15.0.0" → "15"
            return self.os_version.split(".")[0]
        elif self.os_family == "android":
            # Extract SDK level from Android version string
            if ":" in self.os_version and "/" in self.os_version:
                # Format: "Android/device:14/build/..." → "14"
                try:
                    parts = self.os_version.split(":")
                    if len(parts) > 1:
                        return parts[1].split("/")[0]
                except (IndexError, ValueError):
                    pass
            # Fallback: try to extract from simple version
            return self.os_version.replace(".", "").replace("Android", "").strip()[:2]
        return ""

    def copy(self, **changes: Any) -> Device:
        """Create a copy of this device with modifications.

        Args:
            **changes: Attributes to override in the copy.

        Returns:
            A new Device instance with the specified changes.

        Example:
            Update app version::

                iphone = Device.IPHONE
                iphone_new = iphone.copy(
                    app_version="3.60.0",
                    software_version="36000078"
                )

            Change device model::

                android = Device.ANDROID.copy(
                    device_model="Pixel 7",
                    device_product="pixel7_x86_64"
                )
        """
        data = asdict(self)
        data.update(changes)
        # Generate new serial if not explicitly provided
        if "device_serial" not in changes:
            data["device_serial"] = uuid.uuid4().hex.upper()
        return Device(**data)

    def to_dict(self) -> dict[str, Any]:
        """Convert device to dictionary for serialization.

        Returns:
            Dictionary containing all device attributes.

        Example:
            Save device to JSON::

                device = Device.IPHONE
                device_dict = device.to_dict()
                # Use with json.dumps() or save to auth file
        """
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Device:
        """Create Device from dictionary.

        Args:
            data: Dictionary containing device attributes.

        Returns:
            New Device instance populated from dictionary.

        Example:
            Load device from JSON::

                device_dict = json.loads(json_string)
                device = Device.from_dict(device_dict)
        """
        return cls(**data)

    def build_client_id(self) -> str:
        """Build client ID for OAuth (serial#device_type in hex).

        Returns:
            Hexadecimal client ID string.

        Example:
            >>> device = Device.IPHONE
            >>> client_id = device.build_client_id()
            >>> print(client_id)  # doctest: +SKIP
            '414243313233...#A2CZJZGLK2JJVM' (in hex)
        """
        client_id = self.device_serial.encode() + b"#" + self.device_type.encode()
        return client_id.hex()

    def get_registration_data(self) -> dict[str, str]:
        """Get registration data for device registration API call.

        Returns:
            Dictionary with registration-specific fields.

        Example:
            Used internally during :meth:`Authenticator.from_login`::

                device = Device.ANDROID
                reg_data = device.get_registration_data()
                # Used in POST to /auth/register
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

        Example:
            Used internally during token refresh::

                refresh_data = device.get_token_refresh_data()
                # {"app_name": "Audible", "app_version": "3.56.2"}
        """
        return {
            "app_name": self.app_name,
            "app_version": self.app_version,
        }

    def get_init_cookies(self) -> dict[str, str]:
        """Build initial cookies for login (frc, map-md, amzn-app-id).

        Returns:
            Dictionary with login cookies to prevent CAPTCHA.

        Example:
            Used internally during login::

                cookies = device.get_init_cookies()
                # {"frc": "...", "map-md": "...", "amzn-app-id": "..."}
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

    def get_supported_media_features(self) -> dict[str, list[str]]:
        """Get supported codecs and DRM types for license requests.

        Returns:
            Dictionary with codec and DRM type lists.

        Example:
            Used in Dolby Atmos license requests::

                features = device.get_supported_media_features()
                # {
                #   "codecs": ["mp4a.40.2", "mp4a.40.42", "ec+3"],
                #   "drm_types": ["FairPlay", "Adrm", "Mpeg"]
                # }

        See Also:
            GitHub Issue: https://github.com/mkb79/audible-cli/issues/155
        """
        return {
            "codecs": self.supported_codecs.copy(),
            "drm_types": self.supported_drm_types.copy(),
        }

    @classmethod
    @property
    def IPHONE(cls) -> Device:
        """iPhone 15 running iOS 15.0 with Audible 3.56.2.

        Supports:
        - FairPlay DRM
        - Dolby Atmos (ec+3 codec)
        - AAC-LC and xHE-AAC codecs

        Example:
            >>> device = Device.IPHONE
            >>> print(device.device_type)
            A2CZJZGLK2JJVM
        """
        return cls(**cls._IPHONE_DEFAULTS)

    @classmethod
    @property
    def IPHONE_16(cls) -> Device:
        """iPhone 15 running iOS 16.0 with updated Audible app.

        Similar to IPHONE but with newer OS version.
        """
        data = cls._IPHONE_DEFAULTS.copy()
        data.update(
            {
                "app_version": "3.60.0",
                "os_version": "16.0.0",
                "os_version_number": "16",
                "software_version": "36000078",
                "user_agent": (
                    "Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X) "
                    "AppleWebKit/605.1.15 (KHTML, like Gecko) Mobile/15E148"
                ),
            }
        )
        return cls(**data)

    @classmethod
    @property
    def ANDROID(cls) -> Device:
        """Android device (SDK built for x86_64) with Audible app.

        Supports:
        - Widevine DRM
        - Dolby Atmos (ac-4 codec)
        - Multiple streaming protocols (HLS, DASH)
        - Extended codec support (XHE-AAC, AC-4)

        Example:
            >>> device = Device.ANDROID
            >>> print(device.device_type)
            A10KISP2GWF0E4
            >>> print("Widevine" in device.supported_drm_types)
            True

        Note:
            Based on real Android Audible app configuration from
            https://github.com/rmcrackan/AudibleApi/pull/55
        """
        return cls(**cls._ANDROID_DEFAULTS)

    @classmethod
    @property
    def ANDROID_PIXEL_7(cls) -> Device:
        """Google Pixel 7 running Android 13 with Audible app.

        Customized Android profile for real device.
        """
        data = cls._ANDROID_DEFAULTS.copy()
        data.update(
            {
                "device_model": "Pixel 7",
                "device_product": "pixel7_x86_64",
                "os_version": (
                    "Android/pixel7_x86_64:13/TP1A.220624.021/12345678:"
                    "user/release-keys"
                ),
                "os_version_number": "33",
                "user_agent": (
                    "Dalvik/2.1.0 (Linux; U; Android 13; Pixel 7 "
                    "Build/TP1A.220624.021)"
                ),
                "download_user_agent": (
                    "com.audible.playersdk.player/3.96.1 (Linux;Android 13) "
                    "AndroidXMedia3/1.3.0"
                ),
            }
        )
        return cls(**data)
