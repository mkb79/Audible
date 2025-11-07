"""Fixtures for localization tests."""

from __future__ import annotations

from unittest.mock import Mock

import pytest


@pytest.fixture
def mock_autodetect_response_de() -> str:
    """Mock HTML response for German marketplace autodetection."""
    return """
        var ue_mid = 'AN7V1F1VY261K';
        autocomplete_config.searchAlias = "audible-de";
    """
