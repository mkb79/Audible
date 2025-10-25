# Phase 1: Quick Wins - Test Coverage Plan

**Goal:** Increase coverage from 21% to ~46%  
**Time Estimate:** 2-3 hours  
**Modules:** exceptions.py, localization.py, _logging.py

---

## 📦 Module 1: exceptions.py

**Current:** 46% Coverage  
**Target:** 100% Coverage  
**Effort:** 30 minutes

### Missing Coverage Analysis
```
Missing lines: 20-31, 38-40, 47-49
- StatusError.__init__ (lines 20-31): Not tested
- NotResponding.__init__ (lines 38-40): Not tested
- NetworkError.__init__ (lines 47-49): Not tested
```

### Test Strategy

#### Test File: `tests/unit/test_exceptions.py`

```python
"""Tests for audible.exceptions module."""

import pytest
from unittest.mock import Mock
from audible import exceptions


class TestBaseExceptions:
    """Tests for base exception classes."""
    
    def test_audible_error_inherits_from_exception(self):
        """AudibleError inherits from Exception."""
        error = exceptions.AudibleError("test message")
        assert isinstance(error, Exception)
    
    def test_request_error_inherits_from_audible_error(self):
        """RequestError inherits from AudibleError."""
        error = exceptions.RequestError("test message")
        assert isinstance(error, exceptions.AudibleError)
    
    def test_status_error_inherits_from_request_error(self):
        """StatusError inherits from RequestError."""
        mock_response = Mock()
        mock_response.status_code = 400
        mock_response.reason_phrase = "Bad Request"
        error = exceptions.StatusError(mock_response, {"error": "test"})
        assert isinstance(error, exceptions.RequestError)


class TestStatusError:
    """Tests for StatusError and its attributes."""
    
    def test_status_error_with_dict_data_error_key(self):
        """StatusError processes dict with 'error' key correctly."""
        mock_response = Mock()
        mock_response.status_code = 400
        mock_response.reason_phrase = "Bad Request"
        mock_response.method = "GET"
        
        data = {"error": "Invalid parameter"}
        error = exceptions.StatusError(mock_response, data)
        
        assert error.code == 400
        assert error.reason == "Bad Request"
        assert error.error == "Invalid parameter"
        assert error.method == "GET"
        assert "Bad Request (400): Invalid parameter" in str(error)
    
    def test_status_error_with_dict_data_message_key(self):
        """StatusError prioritizes 'message' over 'error' key."""
        mock_response = Mock()
        mock_response.status_code = 404
        mock_response.reason_phrase = "Not Found"
        
        data = {"error": "old error", "message": "Resource not found"}
        error = exceptions.StatusError(mock_response, data)
        
        assert error.error == "Resource not found"
        assert "Not Found (404): Resource not found" in str(error)
    
    def test_status_error_with_non_dict_data(self):
        """StatusError processes string data correctly."""
        mock_response = Mock()
        mock_response.status_code = 500
        mock_response.reason_phrase = "Internal Server Error"
        mock_response.method = None
        
        error = exceptions.StatusError(mock_response, "Server crashed")
        
        assert error.code == 500
        assert error.error == "Server crashed"
        assert error.method is None
    
    def test_status_error_stores_response_object(self):
        """StatusError stores response object."""
        mock_response = Mock()
        mock_response.status_code = 403
        mock_response.reason_phrase = "Forbidden"
        
        error = exceptions.StatusError(mock_response, {})
        assert error.response is mock_response


class TestNotResponding:
    """Tests for NotResponding exception."""
    
    def test_not_responding_initialization(self):
        """NotResponding has correct default values."""
        error = exceptions.NotResponding()
        
        assert error.code == 504
        assert error.error == "API request timed out, please be patient."
        assert isinstance(error, exceptions.RequestError)
    
    def test_not_responding_error_message(self):
        """NotResponding shows correct error message."""
        error = exceptions.NotResponding()
        assert "API request timed out" in str(error)


class TestNetworkError:
    """Tests for NetworkError exception."""
    
    def test_network_error_initialization(self):
        """NetworkError has correct default values."""
        error = exceptions.NetworkError()
        
        assert error.code == 503
        assert error.error == "Network down."
        assert isinstance(error, exceptions.RequestError)
    
    def test_network_error_message(self):
        """NetworkError shows correct error message."""
        error = exceptions.NetworkError()
        assert "Network down" in str(error)


class TestHTTPStatusExceptions:
    """Tests for HTTP status-based exceptions."""
    
    def test_bad_request_inheritance(self):
        """BadRequest inherits from StatusError."""
        mock_response = Mock()
        mock_response.status_code = 400
        mock_response.reason_phrase = "Bad Request"
        
        error = exceptions.BadRequest(mock_response, {})
        assert isinstance(error, exceptions.StatusError)
    
    def test_not_found_error_inheritance(self):
        """NotFoundError inherits from StatusError."""
        mock_response = Mock()
        mock_response.status_code = 404
        mock_response.reason_phrase = "Not Found"
        
        error = exceptions.NotFoundError(mock_response, {})
        assert isinstance(error, exceptions.StatusError)
    
    def test_server_error_inheritance(self):
        """ServerError inherits from StatusError."""
        mock_response = Mock()
        mock_response.status_code = 500
        mock_response.reason_phrase = "Internal Server Error"
        
        error = exceptions.ServerError(mock_response, {})
        assert isinstance(error, exceptions.StatusError)
    
    def test_unauthorized_inheritance(self):
        """Unauthorized inherits from StatusError."""
        mock_response = Mock()
        mock_response.status_code = 401
        mock_response.reason_phrase = "Unauthorized"
        
        error = exceptions.Unauthorized(mock_response, {})
        assert isinstance(error, exceptions.StatusError)
    
    def test_ratelimit_error_inheritance(self):
        """RatelimitError inherits from StatusError."""
        mock_response = Mock()
        mock_response.status_code = 429
        mock_response.reason_phrase = "Too Many Requests"
        
        error = exceptions.RatelimitError(mock_response, {})
        assert isinstance(error, exceptions.StatusError)


class TestAuthFlowError:
    """Tests for AuthFlowError."""
    
    def test_auth_flow_error_inheritance(self):
        """AuthFlowError inherits from AudibleError."""
        error = exceptions.AuthFlowError("No auth method available")
        assert isinstance(error, exceptions.AudibleError)


class TestNoRefreshToken:
    """Tests for NoRefreshToken."""
    
    def test_no_refresh_token_inheritance(self):
        """NoRefreshToken inherits from AudibleError."""
        error = exceptions.NoRefreshToken("No token provided")
        assert isinstance(error, exceptions.AudibleError)


class TestFileEncryptionError:
    """Tests for FileEncryptionError."""
    
    def test_file_encryption_error_inheritance(self):
        """FileEncryptionError inherits from AudibleError."""
        error = exceptions.FileEncryptionError("Encryption failed")
        assert isinstance(error, exceptions.AudibleError)
```

### Expected Results
- ✅ 100% coverage for exceptions.py
- ✅ All exception types tested
- ✅ All initialization paths covered
- ✅ Inheritance hierarchy validated

### Commit After Completion
```bash
git add tests/unit/test_exceptions.py
git commit -m "test: add comprehensive tests for exceptions module (100% coverage)"
```

---

## 📦 Module 2: localization.py

**Current:** 23% Coverage  
**Target:** 95% Coverage  
**Effort:** 60 minutes

### Test Strategy

#### Test File: `tests/unit/test_localization.py`

```python
"""Tests for audible.localization module."""

import pytest
from unittest.mock import Mock, patch
from httpcore import ConnectError
from audible.localization import (
    LOCALE_TEMPLATES,
    search_template,
    autodetect_locale,
    Locale,
)


class TestLocaleTemplates:
    """Tests for LOCALE_TEMPLATES constant."""
    
    def test_locale_templates_contain_expected_countries(self):
        """LOCALE_TEMPLATES contains all expected marketplaces."""
        expected_countries = [
            "germany", "united_states", "united_kingdom",
            "france", "canada", "italy", "australia",
            "india", "japan", "spain", "brazil"
        ]
        
        for country in expected_countries:
            assert country in LOCALE_TEMPLATES
    
    def test_locale_template_structure(self):
        """Each template has required fields."""
        required_keys = {"country_code", "domain", "market_place_id"}
        
        for country, locale in LOCALE_TEMPLATES.items():
            assert set(locale.keys()) == required_keys


class TestSearchTemplate:
    """Tests for search_template function."""
    
    def test_search_by_country_code_success(self):
        """Search by country_code finds correct template."""
        result = search_template("country_code", "de")
        
        assert result is not None
        assert result["country_code"] == "de"
        assert result["domain"] == "de"
    
    def test_search_by_domain_success(self):
        """Search by domain finds correct template."""
        result = search_template("domain", "co.uk")
        
        assert result is not None
        assert result["country_code"] == "uk"
    
    def test_search_not_found_returns_none(self):
        """Search with invalid value returns None."""
        result = search_template("country_code", "invalid")
        assert result is None


@pytest.fixture
def mock_httpx_response():
    """Fixture for mock HTTP response."""
    mock_resp = Mock()
    mock_resp.text = """
        var ue_mid = 'AN7V1F1VY261K';
        autocomplete_config.searchAlias = "audible-de";
    """
    return mock_resp


class TestAutodetectLocale:
    """Tests for autodetect_locale function."""
    
    def test_autodetect_locale_extracts_correctly(self, mock_httpx_response):
        """autodetect_locale extracts locale correctly."""
        with patch("audible.localization.httpx.get") as mock_get:
            mock_get.return_value = mock_httpx_response
            
            result = autodetect_locale("de")
            
            assert result["country_code"] == "de"
            assert result["domain"] == "de"
            assert result["market_place_id"] == "AN7V1F1VY261K"
    
    def test_autodetect_locale_raises_on_network_error(self):
        """autodetect_locale raises ConnectError on network failure."""
        with patch("audible.localization.httpx.get") as mock_get:
            mock_get.side_effect = ConnectError("Connection failed")
            
            with pytest.raises(ConnectError):
                autodetect_locale("invalid.domain")


class TestLocaleClass:
    """Tests for Locale class."""
    
    def test_locale_init_with_all_params(self):
        """Locale initializes with all parameters."""
        locale = Locale(
            country_code="de",
            domain="de",
            market_place_id="AN7V1F1VY261K"
        )
        
        assert locale.country_code == "de"
        assert locale.domain == "de"
        assert locale.market_place_id == "AN7V1F1VY261K"
    
    def test_locale_init_with_country_code_only(self):
        """Locale initializes with country_code only."""
        locale = Locale(country_code="us")
        
        assert locale.country_code == "us"
        assert locale.domain == "com"
    
    def test_locale_init_with_invalid_country_code_raises(self):
        """Locale with invalid country_code raises exception."""
        with pytest.raises(Exception, match="can't find locale"):
            Locale(country_code="invalid")
    
    def test_locale_to_dict(self):
        """Locale.to_dict() returns dict with all fields."""
        locale = Locale(country_code="fr")
        result = locale.to_dict()
        
        assert result == {
            "country_code": "fr",
            "domain": "fr",
            "market_place_id": "A2728XDNODOQ8T"
        }
    
    def test_locale_properties_are_read_only(self):
        """Locale properties cannot be modified."""
        locale = Locale(country_code="de")
        
        with pytest.raises(AttributeError):
            locale.country_code = "us"
```

### Commit After Completion
```bash
git add tests/unit/test_localization.py
git commit -m "test: add tests for localization module (95% coverage)"
```

---

## 📦 Module 3: _logging.py

**Current:** 41% Coverage  
**Target:** 90% Coverage  
**Effort:** 45 minutes

### Test File: `tests/unit/test_logging.py`

```python
"""Tests for audible._logging module."""

import logging
import pytest
from audible._logging import AudibleLogHelper, log_helper, logger


@pytest.fixture
def log_helper_instance():
    """Fixture for fresh AudibleLogHelper instance."""
    return AudibleLogHelper()


@pytest.fixture
def temp_log_file(tmp_path):
    """Fixture for temporary log file."""
    return tmp_path / "test.log"


class TestAudibleLogHelperSetLevel:
    """Tests for set_level method."""
    
    def test_set_level_with_string(self, log_helper_instance):
        """set_level accepts string level."""
        log_helper_instance.set_level("DEBUG")
        assert logger.level == logging.DEBUG
    
    def test_set_level_with_int(self, log_helper_instance):
        """set_level accepts int level."""
        log_helper_instance.set_level(logging.INFO)
        assert logger.level == logging.INFO
    
    @pytest.mark.parametrize("level_str,level_int", [
        ("DEBUG", logging.DEBUG),
        ("INFO", logging.INFO),
        ("WARNING", logging.WARNING),
        ("ERROR", logging.ERROR),
    ])
    def test_set_level_all_levels(self, log_helper_instance, level_str, level_int):
        """set_level works with all standard levels."""
        log_helper_instance.set_level(level_str)
        assert logger.level == level_int


class TestSetConsoleLogger:
    """Tests for set_console_logger method."""
    
    def test_set_console_logger_creates_handler(self, log_helper_instance):
        """set_console_logger creates console handler."""
        logger.handlers.clear()
        
        log_helper_instance.set_console_logger()
        
        assert len(logger.handlers) == 1
        handler = logger.handlers[0]
        assert isinstance(handler, logging.StreamHandler)
        assert handler.name == "ConsoleLogger"


class TestSetFileLogger:
    """Tests for set_file_logger method."""
    
    def test_set_file_logger_with_string_path(
        self, log_helper_instance, temp_log_file
    ):
        """set_file_logger accepts string path."""
        logger.handlers.clear()
        
        log_helper_instance.set_file_logger(str(temp_log_file))
        
        assert len(logger.handlers) == 1
        handler = logger.handlers[0]
        assert isinstance(handler, logging.FileHandler)
    
    def test_set_file_logger_creates_file(
        self, log_helper_instance, temp_log_file
    ):
        """File logger creates log file."""
        logger.handlers.clear()
        log_helper_instance.set_file_logger(temp_log_file)
        
        logger.error("Test message")
        
        for handler in logger.handlers:
            handler.close()
        
        assert temp_log_file.exists()


class TestCaptureWarnings:
    """Tests for capture_warnings method."""
    
    def test_capture_warnings_enable(self):
        """capture_warnings(True) enables warning capturing."""
        AudibleLogHelper.capture_warnings(True)
        assert True  # Should not raise
    
    def test_capture_warnings_disable(self):
        """capture_warnings(False) disables warning capturing."""
        AudibleLogHelper.capture_warnings(False)
        assert True  # Should not raise
```

### Commit After Completion
```bash
git add tests/unit/test_logging.py
git commit -m "test: add tests for logging module (90% coverage)"
```

---

## 🎯 Phase 1 Completion

### After All Tests
```bash
# Run tests and measure coverage
uv run nox --session=tests
uv run nox --session=coverage

# Update fail_under threshold
python scripts/update_coverage_threshold.py

# Commit threshold update
git add pyproject.toml
git commit -m "chore: update fail_under to 46% after Phase 1 completion"

# Push to remote
git push origin feat/coverage-improvement
```

### Expected Results
- ✅ `exceptions.py`: 100% coverage
- ✅ `localization.py`: 95% coverage  
- ✅ `_logging.py`: 90% coverage
- ✅ **Overall: ≥46% coverage**
- ✅ `fail_under` updated to 46

---

## 📝 Implementation Checklist

### Setup (15 min)
- [ ] Create `tests/unit/` directory
- [ ] Create basic `conftest.py`
- [ ] Verify pytest runs correctly

### Exceptions Tests (30 min)
- [ ] Create `test_exceptions.py`
- [ ] Test all exception types
- [ ] Test StatusError edge cases
- [ ] Verify 100% coverage
- [ ] Commit changes

### Localization Tests (60 min)
- [ ] Create `test_localization.py`
- [ ] Test search_template
- [ ] Test autodetect_locale with mocks
- [ ] Test Locale class
- [ ] Verify 95% coverage
- [ ] Commit changes

### Logging Tests (45 min)
- [ ] Create `test_logging.py`
- [ ] Test handler setup
- [ ] Test level setting
- [ ] Test file logging
- [ ] Verify 90% coverage
- [ ] Commit changes

### Wrap-up (15 min)
- [ ] Run full test suite
- [ ] Generate coverage report
- [ ] Update fail_under
- [ ] Commit threshold update
- [ ] Review and proceed to Phase 2

---

**Time Estimate:** 2.5-3 hours  
**Next Step:** Read `PHASE_2_CORE.md`
