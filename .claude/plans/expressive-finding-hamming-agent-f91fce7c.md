# Device Module Refactoring Implementation Plan

## Executive Summary

This plan outlines the refactoring of `audible.device` module to:
1. Reduce predefined devices from 4 to 2 (IPHONE_OS26, ANDROID)
2. Hide device classes as internal implementation details
3. Expose factory functions for device customization (version parameters only)
4. Update Android device with values from widevine.py + latest app_version

This is a **BREAKING CHANGE** that removes old device constants and custom device creation.

---

## 1. New Device API Design

### 1.1 Factory Function Signatures

```python
def create_iphone_device(
    *,
    app_version: str = "4.56.2",
    os_version: str = "26.1",
    device_serial: str | None = None,
) -> BaseDevice:
    """Create an iPhone device with customizable versions.
    
    Args:
        app_version: Audible app version (e.g., "4.56.2")
        os_version: iOS version (e.g., "26.1", "25.0")
        device_serial: Optional custom device serial (auto-generated if None)
    
    Returns:
        Configured iPhone device instance
        
    Example:
        >>> device = create_iphone_device(app_version="4.60.0", os_version="26.2")
        >>> device = create_iphone_device()  # Use defaults
    """
    pass


def create_android_device(
    *,
    app_version: str = "177102",
    os_version: str = "11",
    device_serial: str | None = None,
) -> BaseDevice:
    """Create an Android device with customizable versions.
    
    Args:
        app_version: Audible app version code (e.g., "177102")
        os_version: Android OS version (e.g., "11", "13", "14")
        device_serial: Optional custom device serial (auto-generated if None)
    
    Returns:
        Configured Android device instance
        
    Example:
        >>> device = create_android_device(app_version="180000", os_version="14")
        >>> device = create_android_device()  # Use defaults
    """
    pass
```

### 1.2 Predefined Device Constants

```python
# Only 2 constants exposed
IPHONE_OS26: BaseDevice  # iPhone with iOS 26.1, app 4.56.2
ANDROID: BaseDevice       # OnePlus 8 with Android 11, app 177102
```

### 1.3 Interdependent Field Derivation

**iPhone:**
- `software_version` derived from `app_version`: `app_version.replace(".", "") + os_version.split(".")[0]`
  - Example: "4.56.2" + "26" → "45602826"
- `os_version_number` derived from `os_version`: `os_version.split(".")[0]`
  - Example: "26.1" → "26"

**Android:**
- `software_version`: Fixed at "130050002" (from widevine.py APP_VERSION)
- `os_version` (full): Constructed from template + OS version parameter
  - Template: `"OnePlus/OnePlus8/OnePlus8:{os_version}/RP1A.201005.001/2110102308:user/release-keys"`
  - Example with os_version="11": `"OnePlus/OnePlus8/OnePlus8:11/RP1A.201005.001/2110102308:user/release-keys"`
- `os_version_number`: Derived from `os_version` parameter directly
- `device_product`: Fixed at "OnePlus8"
- User agent uses: release="11", model="IN2013", build_id="RP1A.201005.001"

### 1.4 Customizable vs Fixed Fields

**Customizable:**
- `app_version` (both devices)
- `os_version` (both devices)
- `device_serial` (both devices, optional)

**Fixed (device-specific):**
- `device_type`: "A2CZJZGLK2JJVM" (iPhone), "A10KISP2GWF0E4" (Android)
- `device_model`: "iPhone", "IN2013" (OnePlus 8)
- `device_name`: Template strings
- `app_name`: "Audible" (iPhone), "com.audible.application" (Android)
- Android-specific: manufacturer="OnePlus", product="OnePlus8", build fingerprint

---

## 2. Internal Architecture

### 2.1 Keep Class Structure But Make Private

**Current:**
```python
class BaseDevice(ABC):  # Public
class iPhoneDevice(BaseDevice):  # Public
class AndroidDevice(BaseDevice):  # Public
```

**New:**
```python
class BaseDevice(ABC):  # Keep public (needed for type hints, backward compat)
class _iPhoneDevice(BaseDevice):  # Private (renamed with underscore)
class _AndroidDevice(BaseDevice):  # Private (renamed with underscore)

# Internal helper for deserialization
_DEVICE_CLASS_MAP = {
    "ios": _iPhoneDevice,
    "android": _AndroidDevice,
}
```

**Rationale:**
- Keep class structure for maintainability and extensibility
- Rename concrete classes with underscore to signal internal use
- BaseDevice stays public for type hints (all functions return `BaseDevice`)
- Users interact only through factory functions and constants

### 2.2 Serialization/Deserialization Compatibility

**Current Approach (auth.py lines 422-441):**
```python
os_family = device_data.get("os_family", "")
if os_family == "ios":
    auth.device = iPhoneDevice.from_dict(device_data)
elif os_family == "android":
    auth.device = AndroidDevice.from_dict(device_data)
```

**New Approach:**
```python
# In device.py
def _device_from_dict(data: dict[str, Any]) -> BaseDevice:
    """Internal deserialization helper."""
    os_family = data.get("os_family", "")
    device_cls = _DEVICE_CLASS_MAP.get(os_family)
    
    if device_cls is None:
        logger.warning("Unknown os_family: %s. Falling back to iPhone.", os_family)
        device_cls = _iPhoneDevice
    
    return device_cls.from_dict(data)

# In auth.py (update from_dict)
if device_data:
    from .device import _device_from_dict
    auth.device = _device_from_dict(device_data)
```

**Backward Compatibility:**
- Old auth files with `iPhoneDevice` or `AndroidDevice` class names will still work
- Deserialization relies on `os_family` field, not class name
- No breaking change for existing auth files

---

## 3. Migration Strategy

### 3.1 Breaking Changes Summary

**REMOVED (Breaking):**
1. Constants: `IPHONE`, `ANDROID_PIXEL_7`
2. Direct class instantiation: `iPhoneDevice(...)`, `AndroidDevice(...)`
3. Custom device creation by subclassing `BaseDevice`

**KEPT (Backward Compatible):**
1. `BaseDevice` class (for type hints)
2. Device serialization format (os_family-based)
3. `device.copy(**changes)` method
4. All device methods: `build_client_id()`, `get_registration_data()`, etc.

### 3.2 Migration Guide for Users

**Old Code:**
```python
from audible.device import IPHONE, ANDROID, ANDROID_PIXEL_7, iPhoneDevice

# Using old constants
auth = Authenticator.from_login("user", "pass", "us", device=IPHONE)

# Custom device
my_iphone = iPhoneDevice(
    device_type="A2CZJZGLK2JJVM",
    device_model="iPhone",
    app_version="4.60.0",
    os_version="26.2",
    software_version="46000026",
)

# Customizing predefined device
android = ANDROID_PIXEL_7.copy(app_version="180000")
```

**New Code:**
```python
from audible.device import IPHONE_OS26, ANDROID, create_iphone_device, create_android_device

# Using new constants
auth = Authenticator.from_login("user", "pass", "us", device=IPHONE_OS26)

# Custom device versions
my_iphone = create_iphone_device(app_version="4.60.0", os_version="26.2")

# Still can use .copy() for further customization
android = ANDROID.copy(app_version="180000")

# Or create fresh with factory
android = create_android_device(app_version="180000", os_version="14")
```

### 3.3 Changes Needed in Integration Points

#### auth.py Changes

**Line 23:** Update import
```python
# Old
from .device import IPHONE, BaseDevice

# New
from .device import IPHONE_OS26, BaseDevice, _device_from_dict
```

**Lines 590-604:** Update default device in `from_login()`
```python
# Old
if device is None:
    from .device import IPHONE
    device = IPHONE.copy()

# New
if device is None:
    from .device import IPHONE_OS26
    device = IPHONE_OS26.copy()
```

**Lines 691-694:** Update default device in `from_login_external()`
```python
# Same change as above
```

**Lines 422-441:** Update deserialization in `from_dict()`
```python
# Old
if os_family == "ios":
    from .device import iPhoneDevice
    auth.device = iPhoneDevice.from_dict(device_data)
elif os_family == "android":
    from .device import AndroidDevice
    auth.device = AndroidDevice.from_dict(device_data)

# New
from .device import _device_from_dict
auth.device = _device_from_dict(device_data)
```

**Lines 1090-1111:** Update `update_device()` fallback
```python
# Old
from .device import iPhoneDevice
self.device = iPhoneDevice(...)

# New
from .device import IPHONE_OS26
self.device = IPHONE_OS26.copy(...)
```

#### register.py Changes

No changes needed - uses `BaseDevice` type hint only.

#### login/login.py Changes

No changes needed - uses `BaseDevice` type hint only.

#### login/external.py Changes

Need to check for default device usage.

---

## 4. Android Device Specification

### 4.1 Data Source Mapping

**From widevine.py (lines 27-32, 455-462):**
```python
APP_NAME = "com.audible.application"          # → app_name
APK_VERSION_NAME = "3.79.0"                    # NOT USED (user wants 177102)
APK_VERSION_CODE = "160008"                    # NOT USED
APP_VERSION = "130050002"                      # → software_version
MAP_VERSION = "20240412N"                      # NOT USED in device

# Device properties (OnePlus 8)
"ro.build.fingerprint": "OnePlus/OnePlus8/OnePlus8:11/RP1A.201005.001/2110102308:user/release-keys"
"ro.build.id": "RP1A.201005.001"
"ro.build.version.release": "11"
"ro.product.build.version.sdk": "30"
"ro.product.manufacturer": "OnePlus"
"ro.product.model": "IN2013"
"ro.product.name": "OnePlus8"
```

**From current device.py ANDROID (lines 513-525):**
```python
app_version="177102"                           # KEEP (latest version user wants)
```

### 4.2 Final ANDROID Device Values

```python
ANDROID = _AndroidDevice(
    # Fixed identifiers
    device_type="A10KISP2GWF0E4",
    device_model="IN2013",                    # OnePlus 8 model number
    device_product="OnePlus8",                 # Product name
    
    # Versions (customizable via factory)
    app_version="177102",                      # Latest from current device.py
    os_version="OnePlus/OnePlus8/OnePlus8:11/RP1A.201005.001/2110102308:user/release-keys",
    os_version_number="30",                    # SDK 30 = Android 11
    software_version="130050002",              # From widevine.py APP_VERSION
    
    # Standard fields
    app_name="com.audible.application",
    device_name=(
        "%FIRST_NAME%%FIRST_NAME_POSSESSIVE_STRING%%DUPE_STRATEGY_1ST%"
        "Audible for Android"
    ),
)
```

### 4.3 Factory Function Implementation for Android

```python
def create_android_device(
    *,
    app_version: str = "177102",
    os_version: str = "11",
    device_serial: str | None = None,
) -> BaseDevice:
    """Create OnePlus 8 Android device with customizable versions."""
    
    # Map Android version to SDK level (simplified)
    sdk_map = {
        "11": "30", "12": "31", "13": "33", "14": "34"
    }
    os_version_number = sdk_map.get(os_version, "30")
    
    # Build full os_version string with user's version
    os_version_full = (
        f"OnePlus/OnePlus8/OnePlus8:{os_version}/"
        f"RP1A.201005.001/2110102308:user/release-keys"
    )
    
    return _AndroidDevice(
        device_type="A10KISP2GWF0E4",
        device_model="IN2013",
        device_product="OnePlus8",
        app_version=app_version,
        os_version=os_version_full,
        os_version_number=os_version_number,
        software_version="130050002",  # Fixed
        app_name="com.audible.application",
        device_serial=device_serial or uuid.uuid4().hex.upper(),
        device_name=(
            "%FIRST_NAME%%FIRST_NAME_POSSESSIVE_STRING%%DUPE_STRATEGY_1ST%"
            "Audible for Android"
        ),
    )
```

---

## 5. Testing Impact

### 5.1 Test Files Requiring Updates

**tests/test_device.py:**
- Line 10-11: Update imports (remove ANDROID_PIXEL_7, IPHONE; add IPHONE_OS26)
- Line 14-16: Update class imports (iPhoneDevice → _iPhoneDevice, etc.) OR remove direct class tests
- Line 347-357: Update `test_iphone_predefined_instance()` - change from IPHONE to IPHONE_OS26
- Line 359-367: Keep `test_iphone_os26_predefined_instance()` as is
- Line 479-490: Update `test_android_predefined_instance()` - change values to OnePlus 8 config
- Line 492-500: Remove `test_android_pixel7_predefined_instance()` (deprecated)
- Add new tests for factory functions:
  - `test_create_iphone_device_defaults()`
  - `test_create_iphone_device_custom_versions()`
  - `test_create_android_device_defaults()`
  - `test_create_android_device_custom_versions()`

**tests/test_auth.py:**
- Line 121-129: Update `test_authenticator_with_device_parameter()` - use IPHONE_OS26
- Line 144-153: Update `test_authenticator_to_dict_includes_device()` - keep ANDROID
- Line 165-187: Update `test_authenticator_from_dict_with_device_field()` - use IPHONE_OS26

### 5.2 New Tests to Add

```python
# tests/test_device.py

def test_create_iphone_device_defaults():
    """Test factory creates iPhone with default versions."""
    device = create_iphone_device()
    assert device.app_version == "4.56.2"
    assert device.os_version == "26.1"
    assert device.device_type == "A2CZJZGLK2JJVM"

def test_create_iphone_device_custom_versions():
    """Test factory accepts custom versions."""
    device = create_iphone_device(app_version="4.60.0", os_version="26.2")
    assert device.app_version == "4.60.0"
    assert device.os_version == "26.2"
    assert device.software_version == "46000026"  # Derived

def test_create_android_device_defaults():
    """Test factory creates Android with default versions."""
    device = create_android_device()
    assert device.app_version == "177102"
    assert device.device_model == "IN2013"
    assert device.software_version == "130050002"

def test_create_android_device_custom_versions():
    """Test factory accepts custom versions."""
    device = create_android_device(app_version="180000", os_version="14")
    assert device.app_version == "180000"
    assert "OnePlus8:14/" in device.os_version
    assert device.os_version_number == "34"

def test_factory_generated_serials_unique():
    """Test that factory generates unique serials."""
    device1 = create_iphone_device()
    device2 = create_iphone_device()
    assert device1.device_serial != device2.device_serial

def test_factory_respects_custom_serial():
    """Test that factory uses provided serial."""
    custom_serial = "CUSTOM123456"
    device = create_android_device(device_serial=custom_serial)
    assert device.device_serial == custom_serial

def test_deprecated_constants_removed():
    """Verify old constants are not accessible."""
    with pytest.raises(ImportError):
        from audible.device import IPHONE  # noqa: F401
    
    with pytest.raises(ImportError):
        from audible.device import ANDROID_PIXEL_7  # noqa: F401

def test_device_classes_not_public():
    """Verify device classes are internal."""
    with pytest.raises(ImportError):
        from audible.device import iPhoneDevice  # noqa: F401
    
    with pytest.raises(ImportError):
        from audible.device import AndroidDevice  # noqa: F401

def test_basedevice_still_public():
    """Verify BaseDevice remains accessible for type hints."""
    from audible.device import BaseDevice
    assert BaseDevice is not None
```

---

## 6. Documentation Updates

### 6.1 Module Docstring (device.py)

**Current (lines 1-40):**
```python
"""Device emulation for Audible authentication and API access.
...
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
...
"""
```

**New:**
```python
"""Device emulation for Audible authentication and API access.

This module provides device emulation for Audible-capable devices with
complete device metadata including OS versions, app versions, DRM capabilities,
and codec support.

Device emulation enables:
- Access to device-specific features (e.g., Dolby Atmos on compatible devices)
- Proper User-Agent spoofing for API compatibility
- DRM type selection (FairPlay for iOS, Widevine for Android)
- Codec support negotiation

Available Devices:
    Two predefined device configurations are provided:
    
    - IPHONE_OS26: iPhone with iOS 26.1 and Audible app 4.56.2
    - ANDROID: OnePlus 8 with Android 11 and Audible app 177102

Factory Functions:
    Create devices with custom versions using factory functions:
    
    - create_iphone_device(): Create iPhone with custom app/OS versions
    - create_android_device(): Create Android with custom app/OS versions

Example:
    Use predefined devices::

        from audible.device import IPHONE_OS26, ANDROID

        # Use iPhone for registration
        auth = Authenticator.from_login("user", "pass", "us", device=IPHONE_OS26)

        # Use Android device
        auth = Authenticator.from_login("user", "pass", "us", device=ANDROID)

    Create device with custom versions::

        from audible.device import create_iphone_device, create_android_device

        # iPhone with newer app version
        my_iphone = create_iphone_device(
            app_version="4.60.0",
            os_version="26.2"
        )
        
        # Android with different OS version
        my_android = create_android_device(
            app_version="180000",
            os_version="14"
        )
        
        # Use in authentication
        auth = Authenticator.from_login("user", "pass", "us", device=my_iphone)

    Modify existing device::

        from audible.device import IPHONE_OS26

        # Copy with changes
        updated_iphone = IPHONE_OS26.copy(app_version="4.60.0")

Note:
    Direct instantiation of device classes (iPhoneDevice, AndroidDevice) is
    not supported. Use factory functions or predefined constants instead.

Migration from v0.11.0:
    The following constants were removed:
    
    - IPHONE (replaced by IPHONE_OS26)
    - ANDROID_PIXEL_7 (use ANDROID or create_android_device())
    
    Direct class instantiation is no longer supported. Use factory functions:
    
    - Replace: iPhoneDevice(...) → create_iphone_device(...)
    - Replace: AndroidDevice(...) → create_android_device(...)
"""
```

### 6.2 Function Docstrings

Add comprehensive docstrings to factory functions (shown in section 1.1).

### 6.3 CHANGELOG.md Entry

```markdown
## [0.12.0] - YYYY-MM-DD

### Breaking Changes

**Device Module Refactoring:**
- **REMOVED**: `IPHONE` constant (use `IPHONE_OS26` instead)
- **REMOVED**: `ANDROID_PIXEL_7` constant (use `ANDROID` or `create_android_device()`)
- **REMOVED**: Direct instantiation of `iPhoneDevice` and `AndroidDevice` classes
- **REMOVED**: Custom device creation by subclassing `BaseDevice`

### Added

- Factory functions for device creation:
  - `create_iphone_device(app_version, os_version, device_serial)` - Create iPhone with custom versions
  - `create_android_device(app_version, os_version, device_serial)` - Create Android with custom versions
- New predefined device: `IPHONE_OS26` - iPhone with iOS 26.1 and Audible app 4.56.2

### Changed

- `ANDROID` device updated with OnePlus 8 configuration from widevine.py
- Device classes (`iPhoneDevice`, `AndroidDevice`) are now internal implementation details
- `BaseDevice` remains public for type hints but should not be subclassed

### Migration Guide

Replace direct class usage with factory functions:

```python
# Old (no longer works)
from audible.device import IPHONE, iPhoneDevice, AndroidDevice

device = iPhoneDevice(app_version="4.60.0", os_version="26.2", ...)
auth = Authenticator.from_login(..., device=IPHONE)

# New
from audible.device import IPHONE_OS26, create_iphone_device

device = create_iphone_device(app_version="4.60.0", os_version="26.2")
auth = Authenticator.from_login(..., device=IPHONE_OS26)
```

Existing auth files with device metadata remain compatible (no re-registration needed).
```

### 6.4 README.md Updates

Update any device usage examples to use new constants and factory functions.

---

## 7. Implementation Sequence

### Phase 1: Preparation (Read-Only)
1. Review all files that import device module
2. Document all device usage patterns
3. Create test plan for backward compatibility

### Phase 2: Device Module Core (device.py)
1. Rename classes: `iPhoneDevice` → `_iPhoneDevice`, `AndroidDevice` → `_AndroidDevice`
2. Add `_DEVICE_CLASS_MAP` for deserialization
3. Implement `_device_from_dict()` helper
4. Implement `create_iphone_device()` factory
5. Implement `create_android_device()` factory
6. Update IPHONE_OS26 constant (verify values)
7. Create new ANDROID constant with OnePlus 8 config
8. Remove old constants: IPHONE, ANDROID_PIXEL_7
9. Update module docstring and add function docstrings
10. Update `__all__` to export only: BaseDevice, IPHONE_OS26, ANDROID, factory functions

### Phase 3: Integration Points
1. Update auth.py imports and default device usage
2. Update auth.py deserialization to use `_device_from_dict()`
3. Check and update register.py (likely no changes)
4. Check and update login/ modules (likely no changes)
5. Update src/audible/__init__.py if needed (check __all__)

### Phase 4: Testing
1. Update test_device.py - remove old constant tests
2. Update test_device.py - update class imports for internal tests
3. Add new factory function tests
4. Add deprecation verification tests
5. Update test_auth.py - replace old constants with new
6. Run full test suite: `uv run nox --session=tests`
7. Fix any failures

### Phase 5: Documentation
1. Update CHANGELOG.md with breaking changes
2. Update README.md examples
3. Update any other documentation mentioning devices
4. Add migration guide to docs/

### Phase 6: Quality Checks
1. Run `uv run nox --session=pre-commit` (formatting, linting)
2. Run `uv run nox --session=mypy` (type checking)
3. Run `uv run nox --session=xdoctest` (docstring examples)
4. Run `uv run nox --session=docs-build` (documentation build)
5. Run full `uv run nox` (all checks)
6. Address any issues

---

## 8. Risk Assessment

### High Risk Areas

1. **Serialization Compatibility:**
   - Risk: Old auth files might break if deserialization fails
   - Mitigation: `_device_from_dict()` maintains same logic, just centralized
   - Test: Load auth files created with v0.11.0

2. **Type Checking:**
   - Risk: Renaming classes might break type hints in user code
   - Mitigation: BaseDevice remains public, all functions return BaseDevice
   - Test: Run mypy on example user code

3. **External Dependencies:**
   - Risk: Other projects might import iPhoneDevice/AndroidDevice directly
   - Mitigation: This is a breaking change, document clearly in CHANGELOG
   - Test: Search GitHub for usage patterns

### Medium Risk Areas

1. **Factory Function Logic:**
   - Risk: Incorrect derivation of interdependent fields
   - Mitigation: Extensive unit tests for all version combinations
   - Test: Verify software_version calculation for various inputs

2. **Android Device Config:**
   - Risk: Wrong values from widevine.py might break authentication
   - Mitigation: Test with real Audible API registration
   - Test: Integration test with actual login/register flow

### Low Risk Areas

1. **Docstring Updates:**
   - Risk: Examples might be wrong
   - Mitigation: xdoctest validates all examples
   - Test: `uv run nox --session=xdoctest`

2. **Import Changes:**
   - Risk: Missing imports cause runtime errors
   - Mitigation: Tests import from public API
   - Test: Run full test suite

---

## 9. Rollback Plan

If critical issues are discovered after merge:

1. **Immediate:** Revert the commit
2. **Short-term:** Pin users to v0.11.x in documentation
3. **Long-term:** Address issues and re-release as v0.12.1

---

## 10. Critical Files for Implementation

Based on analysis, these are the key files:

1. **/Users/marcel/Documents/GitHub/Audible/src/audible/device.py**
   - **Reason:** Core implementation - rename classes, add factories, update constants
   - **Lines of concern:** 1-40 (docstring), 317-378 (iPhoneDevice), 380-473 (AndroidDevice), 475-551 (constants)
   - **Estimated changes:** ~200 lines modified/added

2. **/Users/marcel/Documents/GitHub/Audible/src/audible/auth.py**
   - **Reason:** Main integration point - uses devices for login, updates deserialization
   - **Lines of concern:** 23 (imports), 422-441 (from_dict device loading), 590-604 (from_login default), 691-694 (from_login_external default), 1090-1111 (update_device fallback)
   - **Estimated changes:** ~30 lines modified

3. **/Users/marcel/Documents/GitHub/Audible/tests/test_device.py**
   - **Reason:** Comprehensive device tests need updates for new API
   - **Lines of concern:** 1-20 (imports), 347-500 (predefined instance tests), need to add ~100 lines for factory tests
   - **Estimated changes:** ~150 lines modified/added

4. **/Users/marcel/Documents/GitHub/Audible/tests/test_auth.py**
   - **Reason:** Tests device integration with Authenticator
   - **Lines of concern:** 119-200 (device parameter tests)
   - **Estimated changes:** ~20 lines modified

5. **/Users/marcel/Documents/GitHub/Audible/src/widevine.py**
   - **Reason:** Reference for Android device values (read-only, no changes)
   - **Lines of concern:** 27-32 (constants), 455-462 (device props)
   - **Estimated changes:** 0 (reference only)

---

## Additional Notes

### Android OS Version SDK Mapping

For `create_android_device()` factory, map user-friendly versions to SDK levels:

| Android Version | SDK Level | Notes |
|----------------|-----------|-------|
| 11 | 30 | Default (from widevine.py OnePlus 8) |
| 12 | 31 | |
| 13 | 33 | |
| 14 | 34 | Current in device.py |

### Software Version Calculation

**iPhone:**
```python
def _calculate_iphone_software_version(app_version: str, os_version: str) -> str:
    """Calculate software_version from app and OS versions.
    
    Formula: app_version (no dots) + os_version (major only)
    Example: "4.56.2" + "26" → "45602826"
    """
    app_part = app_version.replace(".", "")
    os_part = os_version.split(".")[0]
    return app_part + os_part
```

**Android:**
```python
# Fixed value from widevine.py
software_version = "130050002"  # No calculation needed
```

### User Agent Generation

**iPhone:**
- Uses `os_version` with dots replaced by underscores
- Example: "26.1" → "26_1" in UA string

**Android:**
- Uses device props: release="11", model="IN2013", build="RP1A.201005.001"
- Format: "Dalvik/2.1.0 (Linux; U; Android 11; IN2013 Build/RP1A.201005.001)"

---

## Success Criteria

Implementation is complete when:

1. ✅ Only 2 predefined devices exist: IPHONE_OS26, ANDROID
2. ✅ Factory functions work: create_iphone_device(), create_android_device()
3. ✅ Old constants removed: IPHONE, ANDROID_PIXEL_7
4. ✅ Device classes are private: _iPhoneDevice, _AndroidDevice
5. ✅ All tests pass: `uv run nox`
6. ✅ Type checking passes: `uv run nox --session=mypy`
7. ✅ Documentation builds: `uv run nox --session=docs-build`
8. ✅ Docstring examples work: `uv run nox --session=xdoctest`
9. ✅ Old auth files still load (backward compatibility)
10. ✅ Android device uses OnePlus 8 config from widevine.py + latest app_version

---

## Timeline Estimate

- **Phase 1 (Preparation):** 1 hour
- **Phase 2 (Device Module Core):** 3-4 hours
- **Phase 3 (Integration Points):** 1-2 hours
- **Phase 4 (Testing):** 2-3 hours
- **Phase 5 (Documentation):** 1-2 hours
- **Phase 6 (Quality Checks):** 1 hour

**Total:** 9-13 hours

---

## Questions for User

Before implementation, clarify:

1. **Android app_version:** Confirm using "177102" (current) vs "160008" (widevine.py APK_VERSION_CODE)?
   - **User stated:** Use latest from device.py (177102) ✅

2. **Android software_version:** Confirm using "130050002" (widevine.py APP_VERSION)?
   - **User stated:** Combine widevine.py constants with latest app version ✅

3. **Breaking change timing:** This is v0.12.0 - confirm ready for breaking change?
   - **Assumed:** Yes, user requested breaking change explicitly

4. **Factory function parameters:** Should we allow customization of other fields later (device_model, etc.)?
   - **User stated:** Only OS version and app version customization

5. **Deprecation warnings:** Should we add warnings before v0.12.0 or go straight to removal?
   - **Assumed:** Go straight to removal (breaking change in v0.12.0)
