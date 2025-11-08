# Device Emulation System - Implementation Roadmap

**Created:** 2025-01-08
**Status:** In Progress (Phase 2 of 4)
**Branch:** `claude/add-package-feature-011CUvFiPyJ6ALK3dcZ9BfNQ`

## Executive Summary

This document outlines the complete implementation plan for the Device Emulation System in the Audible library. The system enables users to:

- Emulate different Audible-capable devices (iPhone, Android, Fire Tablet)
- Access device-specific features (Dolby Atmos, Widevine DRM, etc.)
- Customize device metadata for API compatibility
- Update app/OS versions without re-registration

**Core Innovation:** Clean inheritance hierarchy (`BaseDevice` → `iPhoneDevice`/`AndroidDevice`) allowing users to create custom device implementations.

---

## Phase 1: Foundation ✅ COMPLETED

### 1.1 Device Class Architecture ✅

**Commits:**

- `4de5050` - Initial device system with comprehensive metadata
- `1f2b0d3` - Refactor to BaseDevice + iOS/Android subclasses

**Implemented:**

- `BaseDevice` (Abstract Base Class)

  - Abstract methods: `_generate_user_agent()`, `_generate_bundle_id()`, `_detect_os_family()`
  - 15+ device attributes (device_type, app_version, os_version, codecs, DRM types, etc.)
  - Shared helper methods: `copy()`, `to_dict()`, `from_dict()`, `get_registration_data()`, etc.

- `iPhoneDevice(BaseDevice)`

  - iOS-specific User-Agent generation (WebKit format)
  - FairPlay DRM support
  - Dolby Atmos codec support (ec+3)
  - Bundle ID: `com.audible.iphone`

- `AndroidDevice(BaseDevice)`
  - Android-specific User-Agent generation (Dalvik format)
  - Separate download User-Agent (player SDK format)
  - Widevine DRM support
  - Extended codec support (ac-4 for Dolby Atmos)
  - Bundle ID: `com.audible.application`

**Predefined Instances:**

- `IPHONE` - iPhone 15, iOS 15.0, Audible 3.56.2
- `IPHONE_OS26` - iPhone, iOS 26.1, Audible 4.56.2
- `ANDROID` - Android SDK x86_64, Android 14, Audible 177102
- `ANDROID_PIXEL_7` - Google Pixel 7, Android 13

**Files:**

- `src/audible/device.py` (600 lines)

### 1.2 Authenticator Integration ✅

**Implemented:**

- Added `device: BaseDevice | None` attribute to Authenticator
- Added `file_version: str = "1.0"` for future compatibility
- Extended `to_dict()` to serialize device metadata
- Extended `from_dict()` with smart device type detection from `os_family`
  - `os_family == "ios"` → `iPhoneDevice.from_dict()`
  - `os_family == "android"` → `AndroidDevice.from_dict()`
- Updated `from_file()` to use `from_dict()` (DRY principle)
- Backward compatibility warnings for legacy auth files
- Auto-generation of default device from `device_info` if missing

**New Methods:**

- `update_device(app_version, os_version, **kwargs)` - Update metadata without re-registration
- `set_device(device)` - Set completely new device configuration

**Enhanced Methods:**

- `refresh_access_token()` - Now uses device metadata (app_name, app_version)
- `set_website_cookies_for_country()` - Now uses device metadata
- Module-level functions also updated:
  - `refresh_access_token(refresh_token, domain, ..., app_name, app_version)`
  - `refresh_website_cookies(refresh_token, domain, ..., app_name, app_version)`

**Files Modified:**

- `src/audible/auth.py` (~200 lines changed)

---

## Phase 2: Integration 🚧 IN PROGRESS

### 2.1 Register & Login Functions ⏳ NEXT

**Status:** NOT STARTED
**Priority:** CRITICAL
**Estimated Effort:** 2-3 hours

**Current Problem:**

- `register.py` uses hardcoded device values
- `login.py` uses hardcoded device values
- `Authenticator.from_login()` doesn't accept device parameter
- `Authenticator.from_login_external()` doesn't accept device parameter

**Required Changes:**

#### 2.1.1 Update `register.py`

**Current Code (lines 34-64):**

```python
def register(
    authorization_code: str,
    code_verifier: bytes,
    domain: str,
    serial: str,
    with_username: bool = False,
) -> dict[str, Any]:
    body = {
        "requested_token_type": [...],
        "cookies": {"website_cookies": [], "domain": f".amazon.{domain}"},
        "registration_data": {
            "domain": "Device",
            "app_version": "3.56.2",          # HARDCODED
            "device_serial": serial,
            "device_type": "A2CZJZGLK2JJVM",  # HARDCODED
            "device_name": (
                "%FIRST_NAME%%FIRST_NAME_POSSESSIVE_STRING%%DUPE_"
                "STRATEGY_1ST%Audible for iPhone"
            ),                                 # HARDCODED
            "os_version": "15.0.0",           # HARDCODED
            "software_version": "35602678",   # HARDCODED
            "device_model": "iPhone",         # HARDCODED
            "app_name": "Audible",
        },
        ...
    }
```

**New Code:**

```python
def register(
    authorization_code: str,
    code_verifier: bytes,
    domain: str,
    device: BaseDevice,  # NEW PARAMETER
    with_username: bool = False,
) -> dict[str, Any]:
    # Get registration data from device
    reg_data = device.get_registration_data()

    body = {
        "requested_token_type": [...],
        "cookies": {"website_cookies": [], "domain": f".amazon.{domain}"},
        "registration_data": reg_data,  # FROM DEVICE
        ...
    }
```

**Impact:**

- All callers of `register()` must be updated
- `Authenticator.from_login()` needs to pass device
- `Authenticator.from_login_external()` needs to pass device

#### 2.1.2 Update `login.py`

**Functions to Update:**

**A. `build_init_cookies()` (lines 305-321)**

Current:

```python
def build_init_cookies() -> dict[str, str]:
    map_md_dict = {
        "device_user_dictionary": [],
        "device_registration_data": {"software_version": "35602678"},  # HARDCODED
        "app_identifier": {
            "app_version": "3.56.2",      # HARDCODED
            "bundle_id": "com.audible.iphone"  # HARDCODED
        },
    }
    ...
```

New:

```python
def build_init_cookies(device: BaseDevice) -> dict[str, str]:
    # Use device.get_init_cookies() instead
    return device.get_init_cookies()
```

**B. `login()` function (lines 398-540)**

Current:

```python
def login(
    username: str,
    password: str,
    country_code: str,
    domain: str,
    market_place_id: str,
    serial: str | None = None,
    with_username: bool = False,
    ...
) -> dict[str, Any]:
    ...
    default_headers = {
        "User-Agent": USER_AGENT,  # HARDCODED
        ...
    }
    init_cookies = build_init_cookies()  # HARDCODED

    metadata = meta_audible_app(USER_AGENT, base_url)  # HARDCODED
```

New:

```python
def login(
    username: str,
    password: str,
    country_code: str,
    domain: str,
    market_place_id: str,
    device: BaseDevice,  # NEW PARAMETER
    with_username: bool = False,
    ...
) -> dict[str, Any]:
    ...
    default_headers = {
        "User-Agent": device.user_agent,  # FROM DEVICE
        ...
    }
    init_cookies = device.get_init_cookies()  # FROM DEVICE

    metadata = meta_audible_app(device.user_agent, base_url)  # FROM DEVICE
```

**C. `external_login()` function**

Similar updates needed.

**D. Module-level `USER_AGENT` constant**

Current:

```python
USER_AGENT = (
    "Mozilla/5.0 (iPhone; CPU iPhone OS 15_0 like Mac OS X) "
    "AppleWebKit/605.1.15 (KHTML, like Gecko) Mobile/15E148"
)
```

Decision:

- Keep for backward compatibility
- Mark as deprecated in docstring
- Use device.user_agent in all new code

#### 2.1.3 Update `Authenticator.from_login()`

Current:

```python
@classmethod
def from_login(
    cls,
    username: str,
    password: str,
    locale: str | Locale,
    serial: str | None = None,  # Will be deprecated
    with_username: bool = False,
    ...
) -> Authenticator:
    auth = cls(crypto_provider=crypto_provider)
    auth.locale = cast("Locale", locale)

    login_device = login(
        username=username,
        password=password,
        country_code=auth.locale.country_code,
        domain=auth.locale.domain,
        market_place_id=auth.locale.market_place_id,
        serial=serial,  # HARDCODED SERIAL
        with_username=with_username,
        ...
    )
    register_device = register_(with_username=with_username, **login_device)
```

New:

```python
@classmethod
def from_login(
    cls,
    username: str,
    password: str,
    locale: str | Locale,
    device: BaseDevice | None = None,  # NEW PARAMETER
    serial: str | None = None,  # Deprecated, only for backward compat
    with_username: bool = False,
    ...
) -> Authenticator:
    auth = cls(crypto_provider=crypto_provider)
    auth.locale = cast("Locale", locale)

    # Create device if not provided
    if device is None:
        device = IPHONE
        if serial:
            device = device.copy(device_serial=serial)
            logger.warning(
                "serial parameter is deprecated. Use device parameter instead. "
                "Example: device=IPHONE.copy(device_serial='...')"
            )

    # Store device in authenticator
    auth.device = device

    login_device = login(
        username=username,
        password=password,
        country_code=auth.locale.country_code,
        domain=auth.locale.domain,
        market_place_id=auth.locale.market_place_id,
        device=device,  # PASS DEVICE
        with_username=with_username,
        ...
    )
    register_device = register_(
        device=device,  # PASS DEVICE
        with_username=with_username,
        **login_device
    )
```

**Backward Compatibility Strategy:**

- Keep `serial` parameter but mark as deprecated
- If `serial` is provided without `device`, create default device with that serial
- Log deprecation warning

#### 2.1.4 Update `Authenticator.from_login_external()`

Similar changes as `from_login()`.

**Testing Checklist:**

- [ ] Test registration with IPHONE
- [ ] Test registration with ANDROID
- [ ] Test registration with custom device
- [ ] Test backward compatibility with serial parameter
- [ ] Test login cookies generation
- [ ] Test User-Agent in login requests
- [ ] Verify device data stored in auth file
- [ ] Test re-loading device from auth file

---

## Phase 3: Device Data Storage ✅ SIMPLE

### 3.1 Objective

**Goal:** Ensure all device-related data returned by the Audible server during registration is properly stored in the auth file.

**What This Is:**

- Storing device_info from server response (already implemented)
- Ensuring complete round-trip: register → save → load → use

**What This Is NOT:**

- NOT about DRM/Widevine/FairPlay (that's for audible-cli later)
- NOT about codec/DRM type negotiation
- NOT about license requests

### 3.2 Current Status

**Already Implemented:**

```python
# register.py returns device_info from server
extensions = success_response["extensions"]
device_info = extensions["device_info"]
customer_info = extensions["customer_info"]

return {
    "device_info": device_info,  # Contains: device_serial_number, device_type, device_name
    "customer_info": customer_info,
    ...
}

# auth.py already stores it
def to_dict(self):
    return {
        "device_info": self.device_info,  # ✅ Already saved
        "device": self.device.to_dict(),  # ✅ Already saved
        ...
    }
```

**What device_info Contains (from server):**

- `device_serial_number` - Serial returned by server
- `device_type` - Device type confirmed by server
- `device_name` - Device name processed by server

### 3.3 Verification Needed

**Check:**

1. Does server return additional fields we're not storing?
2. Is there a device certificate/private key in the response? (Probably not - that's the RSA key for signing)
3. Are we correctly storing everything from `device_info`?

**Current Understanding:**

- `device_private_key` (in auth.py) is for **RSA request signing**, NOT for DRM
- `device_info` is server confirmation of registration
- DRM certificates (if any) would be handled in audible-cli for media download

### 3.4 Action Items

**Very Simple - Just Verify:**

- [ ] Review server response from `/auth/register` to confirm all fields are captured
- [ ] Ensure `device_info` is completely stored
- [ ] Test round-trip: register → save → load → verify device recreation

**Estimated Effort:** 30 minutes (mostly verification)

**Priority:** LOW (likely already complete)

---

## Phase 4: Testing & Quality Assurance

### 4.1 Unit Tests ⏳ TODO

**Required Tests:**

#### A. Device Classes (`tests/test_device.py`)

- [ ] Test `iPhoneDevice` instantiation
- [ ] Test `AndroidDevice` instantiation
- [ ] Test custom device creation (inherit from BaseDevice)
- [ ] Test User-Agent generation for iOS
- [ ] Test User-Agent generation for Android
- [ ] Test download User-Agent for Android
- [ ] Test bundle ID generation
- [ ] Test codec/DRM list for each device type
- [ ] Test `copy()` method
- [ ] Test `to_dict()` serialization
- [ ] Test `from_dict()` deserialization
- [ ] Test `get_registration_data()`
- [ ] Test `get_token_refresh_data()`
- [ ] Test `get_init_cookies()`
- [ ] Test `get_supported_media_features()`
- [ ] Test certificate handling in AndroidDevice

#### B. Authenticator Integration (`tests/test_auth.py`)

- [ ] Test auth file with device metadata
- [ ] Test loading auth file (iOS device)
- [ ] Test loading auth file (Android device)
- [ ] Test loading legacy auth file (no device)
- [ ] Test `update_device()` method
- [ ] Test `set_device()` method
- [ ] Test token refresh with device metadata
- [ ] Test cookie refresh with device metadata
- [ ] Test backward compatibility (old auth files)
- [ ] Test file_version handling

#### C. Registration & Login (`tests/test_register.py`, `tests/test_login.py`)

- [ ] Test registration with IPHONE
- [ ] Test registration with ANDROID
- [ ] Test registration with custom device
- [ ] Test login with device
- [ ] Test external login with device
- [ ] Test init cookies generation from device
- [ ] Test backward compatibility with serial parameter

#### D. Integration Tests

- [ ] Full auth flow: login → register → save → load → refresh
- [ ] Device switch: register as iPhone → deregister → register as Android
- [ ] Custom device end-to-end test

**Coverage Target:** 90%+

### 4.2 Type Checking

**mypy Compatibility:**

- [ ] All device classes pass mypy
- [ ] All authenticator changes pass mypy
- [ ] Abstract methods correctly typed
- [ ] Generic types for device subclasses

### 4.3 Linting

**ruff/pydoclint:**

- [ ] All docstrings follow Google style
- [ ] All public methods documented
- [ ] All classes have class-level docstrings
- [ ] Examples in docstrings are valid

### 4.4 Pre-commit Hooks

Before final PR:

- [ ] Run `uv run nox` (all sessions must pass)
- [ ] Run `uv run nox --session=pre-commit`
- [ ] Run `uv run nox --session=mypy`
- [ ] Run `uv run nox --session=tests`
- [ ] Run `uv run nox --session=docs-build`

---

## Phase 5: Documentation

### 5.1 Code Documentation ⏳ TODO

#### A. Module Docstrings

- [x] `src/audible/device.py` - Comprehensive module docstring with examples
- [ ] Update `src/audible/auth.py` docstring to mention device support
- [ ] Update `src/audible/register.py` docstring
- [ ] Update `src/audible/login.py` docstring

#### B. Class Docstrings

- [x] `BaseDevice` - Complete with inheritance example
- [x] `iPhoneDevice` - Complete with customization example
- [x] `AndroidDevice` - Complete with certificate note
- [x] `Authenticator` - Updated for device support
- [ ] All methods have proper docstrings

#### C. API Reference

All public APIs documented with:

- Purpose
- Parameters (with types and examples)
- Return values
- Exceptions
- Examples
- Version added/changed notes

### 5.2 User Documentation

#### A. README Updates (`README.md`)

**New Section:**

````markdown
## Device Emulation

Audible supports different device types with varying features. You can customize which device your authentication emulates:

### Using Predefined Devices

```python
from audible import Authenticator
from audible.device import IPHONE, ANDROID

# Register as iPhone (default)
auth = Authenticator.from_login("email", "password", "us")

# Register as Android
auth = Authenticator.from_login("email", "password", "us", device=ANDROID)
```
````

### Creating Custom Devices

```python
from audible.device import iPhoneDevice, AndroidDevice

# Customize iOS device
my_iphone = iPhoneDevice(
    device_type="A2CZJZGLK2JJVM",
    device_model="iPhone",
    app_version="3.60.0",
    os_version="16.0.0",
    software_version="36000078"
)

# Customize Android device
my_android = AndroidDevice(
    device_type="A10KISP2GWF0E4",
    device_model="Pixel 8",
    app_version="177102",
    os_version="Android 14",
    software_version="130050002"
)

auth = Authenticator.from_login("email", "password", "us", device=my_android)
```

### Updating Device Metadata

```python
# Update app version without re-registration
auth = Authenticator.from_file("auth.json")
auth.update_device(app_version="3.60.0", os_version="16.0.0")
auth.to_file()
```

### Device-Specific Features

**iPhone:**

- FairPlay DRM
- Dolby Atmos (ec+3 codec)

**Android:**

- Widevine DRM
- Dolby Atmos (ac-4 codec)
- Extended codec support

**Custom Devices:**

```python
from audible.device import BaseDevice
from dataclasses import dataclass

@dataclass
class FireTVDevice(BaseDevice):
    def _generate_user_agent(self) -> str:
        return f"FireTV/{self.app_version}"

    def _generate_bundle_id(self) -> str:
        return "com.audible.firetv"

    def _detect_os_family(self) -> str:
        return "android"

my_firetv = FireTVDevice(
    device_type="CUSTOMTYPE",
    device_model="Fire TV Stick 4K",
    app_version="3.56.2",
    os_version="9.0",
    software_version="35602678"
)
```

````

#### B. Examples (`examples/`)

**New Files:**
- `examples/device_basic.py` - Basic device usage
- `examples/device_custom.py` - Custom device creation
- `examples/device_android_certificate.py` - Android with certificate
- `examples/device_update.py` - Update device metadata
- `examples/device_switch.py` - Switch between device types

#### C. Sphinx Documentation

**New Pages:**
- `docs/source/device/index.rst` - Device emulation overview
- `docs/source/device/predefined.rst` - Predefined device profiles
- `docs/source/device/custom.rst` - Creating custom devices
- `docs/source/device/android_certificates.rst` - Android certificate guide
- `docs/source/device/api.rst` - Full API reference

**Update Existing:**
- `docs/source/auth/authentication.rst` - Add device parameter examples
- `docs/source/misc/load_save.rst` - Document device in auth files

### 5.3 Migration Guide

**For Users Upgrading from v0.10.x:**

```markdown
## Migration Guide: Device Emulation (v0.11.0)

### Changes

**Backward Compatible:**
- Auth files from v0.10.x can be loaded in v0.11.0
- No code changes required for basic usage
- Default device is IPHONE (same behavior as before)

**New Features:**
- Device emulation support
- Android device support
- Custom device creation
- Device metadata in auth files

### Upgrading

1. **No Action Required** - Existing code works as-is

2. **Optional: Add Device Metadata**
   ```python
   # Load old auth file
   auth = Authenticator.from_file("auth.json")

   # Device will be auto-generated from device_info
   # To explicitly set device:
   from audible.device import IPHONE
   auth.set_device(IPHONE)

   # Save with device metadata
   auth.to_file()  # Now includes device + file_version
````

3. **Using New Features**

   ```python
   from audible.device import ANDROID

   # Register as Android device
   auth = Authenticator.from_login(
       "email", "password", "us",
       device=ANDROID
   )
   ```

### Deprecations

**`serial` parameter (soft deprecation):**

```python
# Old way (still works, but deprecated):
auth = Authenticator.from_login("email", "password", "us", serial="ABC123")

# New way (recommended):
from audible.device import IPHONE
auth = Authenticator.from_login(
    "email", "password", "us",
    device=IPHONE.copy(device_serial="ABC123")
)
```

### Breaking Changes

**None** - Full backward compatibility maintained

````

### 5.4 CHANGELOG Entry

```markdown
## [0.11.0] - 2025-XX-XX

### Added

**Device Emulation System** - Major new feature for device management and emulation

- New `audible.device` module with comprehensive device emulation:
  - `BaseDevice` (ABC) - Abstract base class for device implementations
  - `iPhoneDevice` - iOS device emulation with FairPlay DRM support
  - `AndroidDevice` - Android device emulation with Widevine DRM support
  - Predefined instances: `IPHONE`, `IPHONE_OS26`, `ANDROID`, `ANDROID_PIXEL_7`

- Device metadata in authentication files:
  - `file_version` field for future compatibility tracking
  - `device` field stores complete device configuration
  - Smart device type detection on load (ios vs android)

- New `Authenticator` methods:
  - `update_device(app_version, os_version, ...)` - Update device metadata
  - `set_device(device)` - Replace device configuration

- Device-specific features:
  - iOS: FairPlay DRM, Dolby Atmos (ec+3 codec)
  - Android: Widevine DRM, Dolby Atmos (ac-4 codec), extended codec support
  - User-Agent generation per device type
  - Platform-specific bundle IDs and app identifiers

- Custom device creation:
  - Users can inherit from `BaseDevice` to create custom devices
  - Abstract methods enforce implementation of platform-specific logic
  - Full type safety with dataclasses + ABC

### Changed

- `Authenticator.from_login()` now accepts optional `device` parameter
- `Authenticator.from_login_external()` now accepts optional `device` parameter
- `refresh_access_token()` now uses device metadata (app_name, app_version)
- `refresh_website_cookies()` now uses device metadata (app_name, app_version)
- `register()` now accepts `device` parameter instead of hardcoded values
- `login()` now accepts `device` parameter for User-Agent and cookies
- Auth file format now includes `file_version` and `device` fields

### Deprecated

- `serial` parameter in `Authenticator.from_login()` (use `device=IPHONE.copy(device_serial="...")` instead)
- Hardcoded `USER_AGENT` constant in `login.py` (use device-specific user agents)

### Fixed

- Token refresh now respects app version from device metadata
- Cookie refresh now respects app version from device metadata

### Documentation

- New device emulation guide in README
- New examples: `device_basic.py`, `device_custom.py`, `device_android_certificate.py`
- New Sphinx documentation section for device management
- Migration guide for v0.10.x users
- Android certificate extraction guide

### Technical Details

- Based on real Android Audible app configuration from [AudibleApi PR#55](https://github.com/rmcrackan/AudibleApi/pull/55)
- Addresses Dolby Atmos support from [audible-cli Issue#155](https://github.com/mkb79/audible-cli/issues/155)
- Complete backward compatibility maintained
- Type-safe with mypy validation
- 90%+ test coverage

### Breaking Changes

**None** - Full backward compatibility maintained. Old auth files load seamlessly with auto-generated device metadata.

### Known Limitations

- Android Widevine DRM requires user-provided device certificates (not included)
- See documentation for certificate extraction guide

### Contributors

Special thanks to the AudibleApi project for Android device specifications.
````

---

## Phase 6: Future Enhancements

### 6.1 Additional Device Types

- Fire Tablet device class
- Alexa device class
- Windows/Mac desktop app emulation

### 6.2 Advanced Features

- Automatic app version detection from Audible servers
- Device capability negotiation
- Multi-device management (switch between registered devices)

### 6.3 DRM Integration (OUT OF SCOPE - audible-cli only)

**NOT in this package:**

- Widevine/FairPlay license requests
- Codec negotiation
- DRM certificate handling
- Media feature detection

**Rationale:**

- Core `audible` package handles authentication/registration only
- DRM features belong in `audible-cli` for media download
- Keeps core library focused and lightweight

---

## Critical Path Summary

**Must Complete Before Release:**

1. ✅ Phase 1: Foundation (DONE)
2. 🚧 Phase 2.1: Register & Login Integration (NEXT - 2-3 hours)
3. ✅ Phase 3: Device Data Storage (LIKELY DONE - verify only, ~30min)
4. ⏳ Phase 4: Tests (HIGH - 4-6 hours)
5. ⏳ Phase 5: Documentation (MEDIUM - 2-3 hours)

**Total Remaining Effort:** ~10-12 hours

**Blockers:**

- None currently

**Risks:**

- Audible API changes breaking device emulation

**Out of Scope (for audible-cli later):**

- DRM license requests (Widevine/FairPlay)
- Codec negotiation
- Media feature detection

---

## Implementation Checklist

### Phase 2: Integration

- [ ] Update `register()` to accept `device` parameter
- [ ] Update `login()` to accept `device` parameter
- [ ] Update `external_login()` to accept `device` parameter
- [ ] Update `Authenticator.from_login()` to accept `device` parameter
- [ ] Update `Authenticator.from_login_external()` to accept `device` parameter
- [ ] Add deprecation warning for `serial` parameter
- [ ] Test registration with IPHONE
- [ ] Test registration with ANDROID
- [ ] Test backward compatibility

### Phase 3: Device Data Storage

- [ ] Verify all fields from server `device_info` are stored
- [ ] Test round-trip: register → save → load
- [ ] Confirm no additional device data in server response
- [ ] Document device_info fields

### Phase 4: Testing

- [ ] Write device class unit tests
- [ ] Write authenticator integration tests
- [ ] Write register/login tests
- [ ] Achieve 90%+ coverage
- [ ] Pass mypy type checking
- [ ] Pass ruff linting
- [ ] Pass all nox sessions

### Phase 5: Documentation

- [ ] Update README with device section
- [ ] Create example files
- [ ] Write Sphinx documentation
- [ ] Write migration guide
- [ ] Update CHANGELOG
- [ ] Review all docstrings

---

## Notes & Decisions

**2025-01-08:**

- Decided on `BaseDevice` abstract class approach (cleaner than single class with if/else)
- Predefined devices as module constants (not class properties) for better type inference
- Backward compatibility is critical - no breaking changes
- **IMPORTANT:** Removed `supported_codecs` and `supported_drm_types` from device classes
  - These features belong in audible-cli, not core library
  - Core library only handles device emulation for authentication/registration
  - DRM license requests and codec negotiation are out of scope

**Key Design Principles:**

1. Clean separation of iOS vs Android logic
2. Easy extensibility for custom devices
3. Full backward compatibility
4. Type safety (ABC + dataclasses)
5. Comprehensive documentation
6. **IMPORTANT:** No DRM/codec features in core library (belongs in audible-cli)

---

**Last Updated:** 2025-01-08
**Next Review:** After Phase 2 completion
