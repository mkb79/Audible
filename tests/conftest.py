"""Shared fixtures and configuration for all tests.

This file contains common fixtures used across multiple test modules.
pytest automatically discovers and loads this file.
"""

from unittest.mock import Mock

import pytest


@pytest.fixture
def mock_response():
    """Create a mock HTTP response object.

    Returns:
        Mock object configured to simulate an httpx Response.
    """
    response = Mock()
    response.status_code = 200
    response.reason_phrase = "OK"
    response.method = "GET"
    response.json = Mock(return_value={})
    return response


@pytest.fixture
def sample_credentials():
    """Provide sample authentication credentials for testing.

    Returns:
        Dictionary with test credentials.
    """
    return {
        "access_token": "test_access_token_123",
        "refresh_token": "test_refresh_token_456",
        "device_private_key": "test_private_key_789",
        "adp_token": "test_adp_token_abc",
        "expires": 3600,
    }


# Configure pytest
def pytest_configure(config):
    """Configure pytest with custom markers."""
    config.addinivalue_line(
        "markers", "slow: marks tests as slow (deselect with '-m \"not slow\"')"
    )
    config.addinivalue_line("markers", "integration: marks tests as integration tests")
