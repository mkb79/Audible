"""Tests for helpers in audible.utils."""

from __future__ import annotations

import pathlib
import time

import pytest

from audible.aescipher import AESCipher
from audible.localization import Locale
from audible.utils import ElapsedTime, test_convert as utils_convert

try:
    from typeguard import TypeCheckError
except ImportError:  # pragma: no cover - fallback when typeguard absent
    TypeCheckError = TypeError


TYPE_ERRORS = (TypeError, TypeCheckError)


class TestTestConvertSuccess:
    """Successful validation paths for test_convert."""

    def test_unknown_key_returns_value(self) -> None:
        assert utils_convert("unknown", "value") == "value"

    def test_access_token_passthrough(self) -> None:
        token = "Atna|abcdef"
        assert utils_convert("access_token", token) == token

    def test_refresh_token_passthrough(self) -> None:
        token = "Atnr|12345"
        assert utils_convert("refresh_token", token) == token

    def test_adp_token_pattern(self) -> None:
        token = "{enc:encrypted}{key:keydata}{iv:initial}{name:device}{serial:Mg==}"
        assert utils_convert("adp_token", token) == token

    def test_device_private_key_pattern(self) -> None:
        private_key = (
            "-----BEGIN RSA PRIVATE KEY-----\n"
            "MIICWwIBAAKBgQC3kjHQm...\n"
            "-----END RSA PRIVATE KEY-----\n"
        )
        assert utils_convert("device_private_key", private_key) == private_key

    def test_website_cookies_validates_dict(self) -> None:
        cookies = {"session": "abc123"}
        assert utils_convert("website_cookies", cookies) == cookies

    def test_expires_converts_numeric_string(self) -> None:
        assert utils_convert("expires", "12.5") == pytest.approx(12.5)

    def test_locale_from_string(self) -> None:
        result = utils_convert("locale", "de")
        assert isinstance(result, Locale)
        assert result.country_code == "de"

    def test_filename_from_string(self) -> None:
        value = utils_convert("filename", "tests/unit")
        assert isinstance(value, pathlib.Path)
        assert value.name == "unit"

    def test_crypter_accepts_aescipher(self, auth_fixture_password: str) -> None:
        cipher = AESCipher(auth_fixture_password)
        assert utils_convert("crypter", cipher) is cipher

    @pytest.mark.parametrize("value", [False, "json", "bytes"])
    def test_encryption_accepts_allowed_values(self, value: bool | str) -> None:
        assert utils_convert("encryption", value) == value

    def test_none_value_is_returned_unchanged(self) -> None:
        assert utils_convert("access_token", None) is None


class TestTestConvertFailures:
    """Failure paths for test_convert validations."""

    def test_website_cookies_requires_dict(self) -> None:
        with pytest.raises(TYPE_ERRORS):
            utils_convert("website_cookies", ["not-a-dict"])

    def test_website_cookies_requires_string_values(self) -> None:
        with pytest.raises(TYPE_ERRORS):
            utils_convert("website_cookies", {"session": 123})

    def test_adp_token_requires_string(self) -> None:
        with pytest.raises(TYPE_ERRORS):
            utils_convert("adp_token", 123)

    def test_adp_token_requires_pattern(self) -> None:
        with pytest.raises(ValueError):
            utils_convert("adp_token", "{enc:only}")

    def test_access_token_requires_pattern(self) -> None:
        with pytest.raises(ValueError):
            utils_convert("access_token", "invalid")

    def test_refresh_token_requires_pattern(self) -> None:
        with pytest.raises(ValueError):
            utils_convert("refresh_token", "Atna|value")

    def test_device_private_key_requires_pattern(self) -> None:
        with pytest.raises(ValueError):
            utils_convert("device_private_key", "not-a-key")

    def test_expires_converts_invalid_string(self) -> None:
        with pytest.raises(ValueError):
            utils_convert("expires", "not-a-number")

    def test_expires_requires_numeric_types(self) -> None:
        with pytest.raises(TYPE_ERRORS):
            utils_convert("expires", ["not-valid"])

    def test_locale_requires_known_value(self) -> None:
        with pytest.raises(Exception, match="can't find locale"):
            utils_convert("locale", "zz")

    def test_locale_requires_locale_or_string(self) -> None:
        with pytest.raises(TYPE_ERRORS):
            utils_convert("locale", ["invalid"])

    def test_filename_requires_path_like(self) -> None:
        with pytest.raises(TYPE_ERRORS):
            utils_convert("filename", 123)

    def test_crypter_requires_aescipher(self) -> None:
        with pytest.raises(TYPE_ERRORS):
            utils_convert("crypter", "not-a-cipher")

    def test_encryption_requires_allowed_values(self) -> None:
        with pytest.raises(ValueError):
            utils_convert("encryption", True)

    def test_encryption_requires_bool_or_string(self) -> None:
        with pytest.raises(TYPE_ERRORS):
            utils_convert("encryption", 1)


class TestElapsedTime:
    """Tests for ElapsedTime utility."""

    def test_elapsed_time_reports_delta(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(time, "time", lambda: 100.0)
        timer = ElapsedTime()

        monkeypatch.setattr(time, "time", lambda: 101.5)
        assert timer() == pytest.approx(1.5)
