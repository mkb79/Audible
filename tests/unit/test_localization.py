"""Tests for audible.localization module."""

from __future__ import annotations

from unittest.mock import Mock, patch

import pytest
from httpcore import ConnectError

from audible.localization import (
    LOCALE_TEMPLATES,
    Locale,
    autodetect_locale,
    search_template,
)


class TestLocaleTemplates:
    """Tests for LOCALE_TEMPLATES constant."""

    def test_locale_templates_contain_expected_countries(self) -> None:
        """LOCALE_TEMPLATES contains all expected marketplaces."""
        expected_countries = [
            "germany",
            "united_states",
            "united_kingdom",
            "france",
            "canada",
            "italy",
            "australia",
            "india",
            "japan",
            "spain",
            "brazil",
        ]

        for country in expected_countries:
            assert country in LOCALE_TEMPLATES

    def test_locale_template_structure(self) -> None:
        """Each template has required fields."""
        required_keys = {"country_code", "domain", "market_place_id"}

        for _country, locale in LOCALE_TEMPLATES.items():
            assert set(locale.keys()) == required_keys


class TestSearchTemplate:
    """Tests for search_template function."""

    def test_search_by_country_code_success(self) -> None:
        """Search by country_code finds correct template."""
        result = search_template("country_code", "de")

        assert result is not None
        assert result["country_code"] == "de"
        assert result["domain"] == "de"

    def test_search_by_domain_success(self) -> None:
        """Search by domain finds correct template."""
        result = search_template("domain", "co.uk")

        assert result is not None
        assert result["country_code"] == "uk"

    def test_search_not_found_returns_none(self) -> None:
        """Search with invalid value returns None."""
        result = search_template("country_code", "invalid")
        assert result is None

    def test_search_by_market_place_id(self) -> None:
        """Search by market_place_id finds correct template."""
        result = search_template("market_place_id", "AN7V1F1VY261K")

        assert result is not None
        assert result["country_code"] == "de"


@pytest.fixture
def mock_httpx_response() -> Mock:
    """Fixture for mock HTTP response."""
    mock_resp = Mock()
    mock_resp.text = """
        var ue_mid = 'AN7V1F1VY261K';
        autocomplete_config.searchAlias = "audible-de";
    """
    return mock_resp


class TestAutodetectLocale:
    """Tests for autodetect_locale function."""

    def test_autodetect_locale_extracts_correctly(
        self, mock_httpx_response: Mock
    ) -> None:
        """autodetect_locale extracts locale correctly."""
        with patch("audible.localization.httpx.get") as mock_get:
            mock_get.return_value = mock_httpx_response

            result = autodetect_locale("de")

            assert result["country_code"] == "de"
            assert result["domain"] == "de"
            assert result["market_place_id"] == "AN7V1F1VY261K"

    def test_autodetect_locale_raises_on_network_error(self) -> None:
        """autodetect_locale raises ConnectError on network failure."""
        with patch("audible.localization.httpx.get") as mock_get:
            mock_get.side_effect = ConnectError("Connection failed")

            with pytest.raises(ConnectError):
                autodetect_locale("invalid.domain")

    def test_autodetect_locale_raises_on_missing_marketplace(self) -> None:
        """autodetect_locale raises Exception when marketplace not found."""
        mock_resp = Mock()
        mock_resp.text = "no marketplace here"

        with patch("audible.localization.httpx.get") as mock_get:
            mock_get.return_value = mock_resp

            with pytest.raises(Exception, match="can't find marketplace"):
                autodetect_locale("test.com")

    def test_autodetect_locale_raises_on_missing_country_code(self) -> None:
        """autodetect_locale raises Exception when country code not found."""
        mock_resp = Mock()
        mock_resp.text = "var ue_mid = 'AN7V1F1VY261K';"

        with patch("audible.localization.httpx.get") as mock_get:
            mock_get.return_value = mock_resp

            with pytest.raises(Exception, match="can't find country code"):
                autodetect_locale("test.com")

    def test_autodetect_locale_strips_leading_dot(
        self, mock_httpx_response: Mock
    ) -> None:
        """autodetect_locale strips leading dot from domain."""
        with patch("audible.localization.httpx.get") as mock_get:
            mock_get.return_value = mock_httpx_response

            result = autodetect_locale(".de")

            assert result["domain"] == "de"
            # Verify the correct URL was called (without leading dot)
            mock_get.assert_called_once()
            call_args = mock_get.call_args
            assert call_args[0][0] == "https://www.audible.de"


class TestLocaleClass:
    """Tests for Locale class."""

    def test_locale_init_with_all_params(self) -> None:
        """Locale initializes with all parameters."""
        locale = Locale(country_code="de", domain="de", market_place_id="AN7V1F1VY261K")

        assert locale.country_code == "de"
        assert locale.domain == "de"
        assert locale.market_place_id == "AN7V1F1VY261K"

    def test_locale_init_with_country_code_only(self) -> None:
        """Locale initializes with country_code only."""
        locale = Locale(country_code="us")

        assert locale.country_code == "us"
        assert locale.domain == "com"

    def test_locale_init_with_domain_only(self) -> None:
        """Locale initializes with domain only."""
        locale = Locale(domain="co.uk")

        assert locale.country_code == "uk"
        assert locale.domain == "co.uk"

    def test_locale_init_with_invalid_country_code_raises(self) -> None:
        """Locale with invalid country_code raises exception."""
        with pytest.raises(Exception, match="can't find locale"):
            Locale(country_code="invalid")

    def test_locale_init_with_invalid_domain_raises(self) -> None:
        """Locale with invalid domain raises exception."""
        with pytest.raises(Exception, match="can't find locale"):
            Locale(domain="invalid.domain")

    def test_locale_to_dict(self) -> None:
        """Locale.to_dict() returns dict with all fields."""
        locale = Locale(country_code="fr")
        result = locale.to_dict()

        assert result == {
            "country_code": "fr",
            "domain": "fr",
            "market_place_id": "A2728XDNODOQ8T",
        }

    def test_locale_properties_are_read_only(self) -> None:
        """Locale properties cannot be modified."""
        locale = Locale(country_code="de")

        with pytest.raises(AttributeError):
            locale.country_code = "us"  # type: ignore[misc]

        with pytest.raises(AttributeError):
            locale.domain = "com"  # type: ignore[misc]

        with pytest.raises(AttributeError):
            locale.market_place_id = "NEWID"  # type: ignore[misc]

    def test_locale_repr(self) -> None:
        """Locale __repr__ shows domain and marketplace."""
        locale = Locale(country_code="jp")

        repr_str = repr(locale)
        assert "co.jp" in repr_str
        assert "A1QAP3MOU4173J" in repr_str

    def test_locale_with_partial_params_fills_missing(self) -> None:
        """Locale fills missing params when partial info provided."""
        # Provide country_code and domain, but not market_place_id
        locale = Locale(country_code="de", domain="de")

        assert locale.country_code == "de"
        assert locale.domain == "de"
        assert locale.market_place_id == "AN7V1F1VY261K"

    def test_locale_all_marketplaces_accessible(self) -> None:
        """All predefined marketplaces can be initialized."""
        test_cases = [
            ("de", "de", "AN7V1F1VY261K"),
            ("us", "com", "AF2M0KC94RCEA"),
            ("uk", "co.uk", "A2I9A3Q2GNFNGQ"),
            ("fr", "fr", "A2728XDNODOQ8T"),
            ("ca", "ca", "A2CQZ5RBY40XE"),
            ("it", "it", "A2N7FU2W2BU2ZC"),
            ("au", "com.au", "AN7EY7DTAW63G"),
            ("in", "in", "AJO3FBRUE6J4S"),
            ("jp", "co.jp", "A1QAP3MOU4173J"),
            ("es", "es", "ALMIKO4SZCSAR"),
            ("br", "com.br", "A10J1VAYUDTYRN"),
        ]

        for country_code, domain, marketplace_id in test_cases:
            locale = Locale(country_code=country_code)
            assert locale.country_code == country_code
            assert locale.domain == domain
            assert locale.market_place_id == marketplace_id
