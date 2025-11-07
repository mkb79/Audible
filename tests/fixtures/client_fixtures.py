"""Fixtures for client tests (mock authenticators and responses)."""

from __future__ import annotations

from unittest.mock import Mock

import pytest

from audible.auth import Authenticator
from audible.localization import Locale


@pytest.fixture
def mock_authenticator() -> Mock:
    """Fixture for mock Authenticator."""
    auth = Mock(spec=Authenticator)
    auth.locale = Locale("us")
    auth.access_token = "test_access_token"  # noqa: S105
    auth.adp_token = "test_adp_token"  # noqa: S105
    auth.device_private_key = "test_private_key"
    auth.refresh_access_token = Mock()
    auth.website_cookies = {}
    auth.user_profile = Mock(return_value={"name": "Test User"})
    return auth
