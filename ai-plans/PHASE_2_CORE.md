# Phase 2: Core Functionality - Test Coverage Plan

**Goal:** Increase coverage from ~46% to ~71%  
**Time Estimate:** 5-7 hours  
**Modules:** utils.py, client.py, auth.py

---

## Implementation Strategy

All tests must be written in **English** with English docstrings, comments, and variable names.

After each module:
```bash
git add tests/unit/test_<module>.py
git commit -m "test: add tests for <module> module (XX% coverage)"
```

After Phase 2 completion:
```bash
python scripts/update_coverage_threshold.py
git add pyproject.toml
git commit -m "chore: update fail_under to 71% after Phase 2 completion"
```

---

## 📦 Module 1: utils.py (20% → 90%)

**Effort:** 90 minutes

### Test File: `tests/unit/test_utils.py`

The specific tests will depend on the actual functions in utils.py. Common patterns:

```python
"""Tests for audible.utils module."""

import pytest
from unittest.mock import Mock, patch
from audible import utils


class TestUtilityFunctions:
    """Tests for utility functions."""
    
    def test_function_name_with_valid_input(self):
        """Function handles valid input correctly."""
        result = utils.some_function("valid_input")
        assert result == "expected_output"
    
    def test_function_name_with_edge_case(self):
        """Function handles edge case appropriately."""
        result = utils.some_function("")
        assert result is not None
    
    @pytest.mark.parametrize("input_val,expected", [
        ("input1", "output1"),
        ("input2", "output2"),
    ])
    def test_function_name_parametrized(self, input_val, expected):
        """Function works with various inputs."""
        assert utils.some_function(input_val) == expected
```

---

## 📦 Module 2: client.py (31% → 85%)

**Effort:** 3 hours

### Test File: `tests/unit/test_client.py`

```python
"""Tests for audible.client module."""

import pytest
import httpx
from unittest.mock import Mock, AsyncMock, patch
from audible.client import Client, AsyncClient
from audible import exceptions
from audible.auth import Authenticator
from audible.localization import Locale


@pytest.fixture
def mock_authenticator():
    """Fixture for mock Authenticator."""
    auth = Mock(spec=Authenticator)
    auth.locale = Locale(country_code="us")
    auth.access_token = "test_access_token"
    auth.adp_token = "test_adp_token"
    auth.device_private_key = "test_private_key"
    auth.refresh_access_token = Mock()
    return auth


@pytest.fixture
def mock_httpx_client():
    """Fixture for mock httpx.Client."""
    client = Mock(spec=httpx.Client)
    client.__enter__ = Mock(return_value=client)
    client.__exit__ = Mock(return_value=None)
    return client


class TestClientInitialization:
    """Tests for Client initialization."""
    
    def test_client_init_with_authenticator(self, mock_authenticator):
        """Client can be initialized with Authenticator."""
        client = Client(auth=mock_authenticator)
        assert client.auth is mock_authenticator


class TestClientGetRequest:
    """Tests for Client GET requests."""
    
    def test_client_get_success(self, mock_authenticator, mock_httpx_client):
        """Client GET request succeeds."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"data": "test"}
        mock_httpx_client.get.return_value = mock_response
        
        with patch("audible.client.httpx.Client", return_value=mock_httpx_client):
            with Client(auth=mock_authenticator) as client:
                result = client.get("library")
        
        assert result == {"data": "test"}


class TestClientErrorHandling:
    """Tests for Client error handling."""
    
    def test_client_handles_400_bad_request(self, mock_authenticator, mock_httpx_client):
        """Client raises BadRequest on 400."""
        mock_response = Mock()
        mock_response.status_code = 400
        mock_response.reason_phrase = "Bad Request"
        mock_response.json.return_value = {"error": "Invalid params"}
        mock_httpx_client.get.return_value = mock_response
        
        with patch("audible.client.httpx.Client", return_value=mock_httpx_client):
            with Client(auth=mock_authenticator) as client:
                with pytest.raises(exceptions.BadRequest):
                    client.get("library")


class TestAsyncClient:
    """Tests for AsyncClient."""
    
    @pytest.mark.asyncio
    async def test_async_client_get(self, mock_authenticator):
        """AsyncClient GET request works."""
        mock_response = AsyncMock()
        mock_response.status_code = 200
        mock_response.json = AsyncMock(return_value={"data": "test"})
        
        mock_async_client = AsyncMock(spec=httpx.AsyncClient)
        mock_async_client.__aenter__ = AsyncMock(return_value=mock_async_client)
        mock_async_client.__aexit__ = AsyncMock(return_value=None)
        mock_async_client.get = AsyncMock(return_value=mock_response)
        
        with patch("audible.client.httpx.AsyncClient", return_value=mock_async_client):
            async with AsyncClient(auth=mock_authenticator) as client:
                result = await client.get("library")
        
        assert result == {"data": "test"}
```

### Required Dependencies
```bash
uv add --group=tests pytest-asyncio
```

---

## 📦 Module 3: auth.py (21% → 80%)

**Effort:** 2.5 hours

### Test File: `tests/unit/test_auth.py`

```python
"""Tests for audible.auth module."""

import pytest
from unittest.mock import Mock, patch
from audible.auth import Authenticator
from audible.localization import Locale
from audible import exceptions


@pytest.fixture
def sample_credentials():
    """Fixture for sample credentials."""
    return {
        "access_token": "test_access_token",
        "refresh_token": "test_refresh_token",
        "device_private_key": "test_private_key",
        "adp_token": "test_adp_token",
        "expires": 3600,
    }


@pytest.fixture
def mock_locale():
    """Fixture for mock Locale."""
    return Locale(country_code="us")


class TestAuthenticatorInitialization:
    """Tests for Authenticator initialization."""
    
    def test_authenticator_init_from_credentials(self, sample_credentials, mock_locale):
        """Authenticator can be initialized with credentials."""
        auth = Authenticator(locale=mock_locale, **sample_credentials)
        
        assert auth.access_token == "test_access_token"
        assert auth.refresh_token == "test_refresh_token"
        assert auth.locale == mock_locale


class TestAuthenticatorTokenManagement:
    """Tests for token management."""
    
    def test_access_token_property(self, sample_credentials, mock_locale):
        """access_token property returns token."""
        auth = Authenticator(locale=mock_locale, **sample_credentials)
        assert auth.access_token == "test_access_token"
    
    @patch("audible.auth.httpx.post")
    def test_refresh_access_token_success(self, mock_post, sample_credentials, mock_locale):
        """refresh_access_token renews token successfully."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "access_token": "new_access_token",
            "expires_in": 3600
        }
        mock_post.return_value = mock_response
        
        auth = Authenticator(locale=mock_locale, **sample_credentials)
        auth.refresh_access_token()
        
        assert auth.access_token == "new_access_token"


class TestAuthenticatorCredentialStorage:
    """Tests for credential storage."""
    
    def test_to_dict(self, sample_credentials, mock_locale):
        """to_dict exports all credentials."""
        auth = Authenticator(locale=mock_locale, **sample_credentials)
        result = auth.to_dict()
        
        assert "access_token" in result
        assert result["access_token"] == "test_access_token"
    
    def test_to_file_creates_file(self, sample_credentials, mock_locale, tmp_path):
        """to_file creates credential file."""
        cred_file = tmp_path / "credentials.json"
        auth = Authenticator(locale=mock_locale, **sample_credentials)
        auth.to_file(cred_file)
        
        assert cred_file.exists()
```

---

## 🎯 Phase 2 Completion

### Final Steps
```bash
# Run tests
uv run nox --session=tests
uv run nox --session=coverage

# Update threshold
python scripts/update_coverage_threshold.py

# Commit
git add pyproject.toml
git commit -m "chore: update fail_under to 71% after Phase 2 completion"
```

### Expected Results
- ✅ `utils.py`: 90% coverage
- ✅ `client.py`: 85% coverage
- ✅ `auth.py`: 80% coverage
- ✅ **Overall: ≥71% coverage**
- ✅ `fail_under` updated to 71

---

## 📝 Implementation Checklist

### Dependencies (15 min)
- [ ] Install pytest-asyncio: `uv add --group=tests pytest-asyncio`
- [ ] Add async fixtures to conftest.py

### Utils Tests (90 min)
- [ ] Review utils.py code
- [ ] Create test_utils.py
- [ ] Test all functions
- [ ] Verify 90% coverage
- [ ] Commit

### Client Tests (3 hours)
- [ ] Create test_client.py
- [ ] Test sync Client
- [ ] Test async AsyncClient
- [ ] Test error handling
- [ ] Verify 85% coverage
- [ ] Commit

### Auth Tests (2.5 hours)
- [ ] Create test_auth.py
- [ ] Test token management
- [ ] Test file storage
- [ ] Test refresh flow
- [ ] Verify 80% coverage
- [ ] Commit

### Wrap-up (30 min)
- [ ] Run full test suite
- [ ] Update fail_under
- [ ] Commit threshold
- [ ] Proceed to Phase 3

---

**Total Time:** 5-7 hours  
**Next:** `PHASE_3_COMPLEX.md`
