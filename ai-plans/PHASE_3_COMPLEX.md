# Phase 3: Complex Modules - Test Coverage Plan

**Goal:** Increase coverage from ~71% to 85-90%
**Time Estimate:** 8-12 hours
**Modules:** aescipher.py, metadata.py, activation_bytes.py, register.py, login.py

---

## Implementation Guidelines

- All code in **English**
- Commit after each module
- Update `fail_under` after phase completion
- Known limitations documented

---

## 📦 Module 1: aescipher.py ✅ COMPLETED (19% → 82%)

**Effort:** 2 hours (completed)
**Status:** ✅ Complete (November 7, 2025)
**Coverage Achieved:** 82% (target: 85%, -3% but acceptable)
**Tests:** 25 comprehensive tests in test_aescipher.py
**Key Features Tested:**

- Encryption/decryption roundtrips (dict and bytes styles)
- File operations (JSON and bytes)
- Salt functions (create, pack, unpack)
- Low-level AES CBC operations
- Error handling (wrong password, invalid salt marker)
- Note: ASCII-only test data due to legacy crypto provider limitations

### Test File: `tests/unit/test_aescipher.py` ✅

```python
"""Tests for audible.aescipher module."""

import pytest
from audible.aescipher import AESCipher, detect_file_encryption


@pytest.fixture
def sample_password():
    """Fixture for test password."""
    return "test_password_123"


class TestAESCipherEncryption:
    """Tests for encryption."""

    def test_encrypt_text(self, sample_password):
        """encrypt() encrypts text correctly."""
        cipher = AESCipher(password=sample_password)
        plaintext = "This is a test message"
        encrypted = cipher.encrypt(plaintext)

        assert encrypted != plaintext
        assert isinstance(encrypted, (str, bytes))

    def test_encrypt_decrypt_roundtrip(self, sample_password):
        """Encrypt-decrypt roundtrip preserves data."""
        cipher = AESCipher(password=sample_password)
        original = "Test message with special chars: äöü!@#$%"

        encrypted = cipher.encrypt(original)
        decrypted = cipher.decrypt(encrypted)

        assert decrypted == original

    def test_decrypt_with_wrong_password_fails(self):
        """Decryption with wrong password fails."""
        cipher1 = AESCipher(password="password1")
        cipher2 = AESCipher(password="password2")

        encrypted = cipher1.encrypt("test")

        with pytest.raises(Exception):
            cipher2.decrypt(encrypted)


class TestFileEncryption:
    """Tests for file encryption."""

    def test_encrypt_file(self, sample_password, tmp_path):
        """encrypt_file() encrypts file."""
        plaintext_file = tmp_path / "plaintext.txt"
        encrypted_file = tmp_path / "encrypted.bin"

        plaintext_file.write_text("Test file content")

        cipher = AESCipher(password=sample_password)
        cipher.encrypt_file(str(plaintext_file), str(encrypted_file))

        assert encrypted_file.exists()
        assert encrypted_file.read_bytes() != plaintext_file.read_bytes()
```

### Commit

```bash
git commit -m "test: add aescipher tests (85% coverage)"
```

---

## 📦 Module 2: metadata.py (20% → 80%)

**Effort:** 2 hours

### Test File: `tests/unit/test_metadata.py`

```python
"""Tests for audible.metadata module."""

import pytest
from audible.metadata import parse_metadata, extract_asin


@pytest.fixture
def sample_api_response():
    """Fixture for sample API response."""
    return {
        "asin": "B07H8K9JXZ",
        "title": "Test Audiobook",
        "authors": [{"name": "John Doe"}],
        "runtime_length_min": 720,
    }


class TestMetadataParser:
    """Tests for metadata parsing."""

    def test_parse_metadata_basic_fields(self, sample_api_response):
        """parse_metadata extracts basic fields."""
        result = parse_metadata(sample_api_response)
        assert result["asin"] == "B07H8K9JXZ"
        assert result["title"] == "Test Audiobook"


class TestASINExtraction:
    """Tests for ASIN extraction."""

    def test_extract_asin_from_url(self):
        """extract_asin extracts ASIN from URL."""
        url = "https://www.audible.com/pd/B07H8K9JXZ"
        asin = extract_asin(url)
        assert asin == "B07H8K9JXZ"
```

### Commit

```bash
git commit -m "test: add metadata tests (80% coverage)"
```

---

## 📦 Module 3: activation_bytes.py (21% → 75%)

**Effort:** 2 hours

Focus on testable functions, mock file operations.

### Commit

```bash
git commit -m "test: add activation_bytes tests (75% coverage)"
```

---

## 📦 Module 4: register.py ✅ COMPLETED (13% → 100%)

**Effort:** 2 hours (completed)
**Status:** ✅ Complete (November 7, 2025)
**Coverage Achieved:** 100% (target: 75%, exceeded by 25%!)
**Tests:** 13 comprehensive tests using pytest-httpx
**Key Features Tested:**

- Device registration with Audible API
- Deregistration functionality
- Error handling (invalid codes, unauthorized)
- Request body structure validation
- Response parsing
- All using fully anonymized mock data (MOCK\_ prefix)
  **Refactoring:** Migrated to pytest-httpx, fixtures in tests/fixtures/register_fixtures.py

### Test File: `tests/unit/test_register.py` ✅

```python
"""Tests for audible.register module."""

import pytest
from unittest.mock import Mock, patch
from audible.register import register_device
from audible.localization import Locale


@pytest.fixture
def mock_locale():
    """Fixture for mock Locale."""
    return Locale(country_code="us")


class TestDeviceRegistration:
    """Tests for device registration."""

    @patch("audible.register.httpx.post")
    def test_register_device_success(self, mock_post, mock_locale):
        """register_device registers device successfully."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "access_token": "new_access_token",
            "refresh_token": "new_refresh_token",
        }
        mock_post.return_value = mock_response

        result = register_device(
            authorization_code="test_code",
            locale=mock_locale
        )

        assert "access_token" in result
```

### Commit

```bash
git commit -m "test: add register tests (75% coverage)"
```

---

## 📦 Module 5: login.py (12% → 70%)

**Effort:** 4 hours

**Most Complex Module** - OAuth2 flow with CAPTCHA & 2FA.

### Strategy

- Mock browser interactions
- Mock HTTP requests/responses
- Focus on critical paths
- Accept 70% target (interactive components)

### Test File: `tests/unit/test_login.py`

```python
"""Tests for audible.login module."""

import pytest
from unittest.mock import Mock, patch
from audible.login import Login, external_login
from audible.localization import Locale


@pytest.fixture
def mock_locale():
    """Fixture for mock Locale."""
    return Locale(country_code="us")


class TestLoginInitialization:
    """Tests for Login initialization."""

    def test_login_init(self, mock_locale):
        """Login can be initialized."""
        login = Login(locale=mock_locale)
        assert login.locale == mock_locale


class TestOAuthFlow:
    """Tests for OAuth flow."""

    @patch("audible.login.httpx.get")
    def test_oauth_initiate_flow(self, mock_get, mock_locale):
        """OAuth flow can be initiated."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.text = "<html>Login page</html>"
        mock_get.return_value = mock_response

        login = Login(locale=mock_locale)
        # Test OAuth initiation


class TestExternalLogin:
    """Tests for external login."""

    @patch("audible.login.webbrowser.open")
    @patch("audible.login.start_local_server")
    def test_external_login_flow(self, mock_server, mock_browser, mock_locale):
        """external_login opens browser and waits for callback."""
        mock_server.return_value = "authorization_code_12345"

        result = external_login(locale=mock_locale)

        mock_browser.assert_called_once()
        assert result == "authorization_code_12345"
```

### Commit

```bash
git commit -m "test: add login tests (70% coverage)"
```

---

## 🎯 Phase 3 Completion

### Final Steps

```bash
# Run tests
uv run nox --session=tests
uv run nox --session=coverage

# Update threshold
python ai-plans/scripts/update_coverage_threshold.py

# Commit
git add pyproject.toml
git commit -m "chore: update fail_under to 85% after Phase 3 completion"

# Push
git push origin feat/coverage-improvement
```

### Expected Results

- ✅ `aescipher.py`: 85% coverage
- ✅ `metadata.py`: 80% coverage
- ✅ `activation_bytes.py`: 75% coverage
- ✅ `register.py`: 75% coverage
- ✅ `login.py`: 70% coverage
- ✅ **Overall: ≥85% coverage**
- ✅ `fail_under` updated to 85

---

## ⚠️ Known Limitations

### login.py Limitations

- Interactive components hard to fully test
- Browser integration only mocked
- 2FA/OTP input simulation limited
- **70% target is realistic, 100% not practical**

### activation_bytes.py Limitations

- Requires AAX file format knowledge
- Possibly proprietary algorithms
- **Integration tests more important than unit tests**

---

## 📝 Implementation Checklist

### AESCipher Tests ✅ COMPLETED (2 hours)

- [x] Create test_aescipher.py
- [x] Test encryption/decryption
- [x] Test file operations
- [x] Test edge cases
- [x] Verify 82% coverage (target: 85%, close enough)
- [x] Commit

### Metadata Tests ⬜ TODO (2 hours)

- [ ] Review metadata.py
- [ ] Create test_metadata.py
- [ ] Test parsing logic
- [ ] Verify 80% coverage
- [ ] Commit

### Activation Bytes Tests ⬜ TODO (2 hours)

- [ ] Review activation_bytes.py
- [ ] Create test_activation_bytes.py
- [ ] Test with mocks
- [ ] Verify 75% coverage
- [ ] Commit

### Register Tests ✅ COMPLETED (2 hours)

- [x] Create test_register.py
- [x] Test registration flow
- [x] Test error handling
- [x] Verify 100% coverage (target: 75%, exceeded!)
- [x] Commit
- [x] Refactor to pytest-httpx
- [x] Move fixtures to tests/fixtures/

### Login Tests ⬜ TODO (4 hours)

- [ ] Create test_login.py
- [ ] Test OAuth flow
- [ ] Mock CAPTCHA handling
- [ ] Mock 2FA handling
- [ ] Test external login
- [ ] Verify 70% coverage
- [ ] Commit

### Additional Refactoring ✅ COMPLETED

- [x] Remove redundant test_main.py
- [x] Refactor test_auth.py with pytest-httpx
- [x] Refactor test_localization.py with pytest-httpx
- [x] Move client fixtures to tests/fixtures/
- [x] Organize all fixtures in dedicated directory

### Final Steps (1 hour)

- [ ] Run full test suite
- [ ] Update fail_under
- [ ] Commit threshold
- [ ] Create PR

---

**Total Time:** 8-12 hours
**Next:** Create Pull Request for review
