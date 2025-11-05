"""Tests for JSON provider implementations."""

import pytest

from audible.json import (
    OrjsonProvider,
    RapidjsonProvider,
    StdlibProvider,
    UjsonProvider,
    get_json_provider,
    set_default_json_provider,
)


class TestStdlibProvider:
    """Tests for stdlib JSON provider."""

    def test_dumps_basic(self):
        provider = StdlibProvider()
        result = provider.dumps({"key": "value"})
        assert result == '{"key": "value"}'

    def test_dumps_indent(self):
        provider = StdlibProvider()
        result = provider.dumps({"key": "value"}, indent=4)
        assert '    "key"' in result

    def test_dumps_indent_2(self):
        provider = StdlibProvider()
        result = provider.dumps({"key": "value"}, indent=2)
        assert '  "key"' in result

    def test_dumps_separators(self):
        provider = StdlibProvider()
        result = provider.dumps({"key": "value"}, separators=(",", ":"))
        assert result == '{"key":"value"}'

    def test_dumps_ensure_ascii_true(self):
        provider = StdlibProvider()
        result = provider.dumps({"key": "über"}, ensure_ascii=True)
        assert "\\u00fc" in result

    def test_dumps_ensure_ascii_false(self):
        provider = StdlibProvider()
        result = provider.dumps({"key": "über"}, ensure_ascii=False)
        assert "über" in result

    def test_loads_string(self):
        provider = StdlibProvider()
        result = provider.loads('{"key": "value"}')
        assert result == {"key": "value"}

    def test_loads_bytes(self):
        provider = StdlibProvider()
        result = provider.loads(b'{"key": "value"}')
        assert result == {"key": "value"}

    def test_loads_complex(self):
        provider = StdlibProvider()
        data = {"string": "test", "number": 42, "float": 3.14, "bool": True, "null": None}
        result = provider.loads(provider.dumps(data))
        assert result == data

    def test_provider_name(self):
        provider = StdlibProvider()
        assert provider.provider_name == "stdlib"

    def test_roundtrip(self):
        provider = StdlibProvider()
        original = {"key": "value", "nested": {"inner": "data"}, "array": [1, 2, 3]}
        serialized = provider.dumps(original)
        deserialized = provider.loads(serialized)
        assert deserialized == original


class TestUjsonProvider:
    """Tests for ujson provider."""

    def test_import_available(self):
        """Test that UJSON_AVAILABLE flag is correct."""
        from audible.json.ujson_provider import UJSON_AVAILABLE
        try:
            import ujson  # noqa: F401
            assert UJSON_AVAILABLE is True
        except ImportError:
            assert UJSON_AVAILABLE is False

    def test_dumps_indent_4(self):
        try:
            provider = UjsonProvider()
        except ImportError:
            pytest.skip("ujson not installed")

        result = provider.dumps({"key": "value"}, indent=4)
        assert '    "key"' in result

    def test_dumps_compact(self):
        try:
            provider = UjsonProvider()
        except ImportError:
            pytest.skip("ujson not installed")

        result = provider.dumps({"key": "value"})
        # ujson might add spaces, just check it's valid
        assert "key" in result and "value" in result

    def test_separators_fallback(self):
        try:
            provider = UjsonProvider()
        except ImportError:
            pytest.skip("ujson not installed")

        # Should fallback to stdlib
        result = provider.dumps({"key": "value"}, separators=(",", ":"))
        assert result == '{"key":"value"}'

    def test_loads_string(self):
        try:
            provider = UjsonProvider()
        except ImportError:
            pytest.skip("ujson not installed")

        result = provider.loads('{"key": "value"}')
        assert result == {"key": "value"}

    def test_loads_bytes(self):
        try:
            provider = UjsonProvider()
        except ImportError:
            pytest.skip("ujson not installed")

        result = provider.loads(b'{"key": "value"}')
        assert result == {"key": "value"}

    def test_provider_name(self):
        try:
            provider = UjsonProvider()
        except ImportError:
            pytest.skip("ujson not installed")

        assert provider.provider_name == "ujson"

    def test_roundtrip(self):
        try:
            provider = UjsonProvider()
        except ImportError:
            pytest.skip("ujson not installed")

        original = {"key": "value", "number": 42, "nested": {"inner": "data"}}
        serialized = provider.dumps(original)
        deserialized = provider.loads(serialized)
        assert deserialized == original


class TestRapidjsonProvider:
    """Tests for rapidjson provider."""

    def test_import_available(self):
        """Test that RAPIDJSON_AVAILABLE flag is correct."""
        from audible.json.rapidjson_provider import RAPIDJSON_AVAILABLE
        try:
            import rapidjson  # noqa: F401
            assert RAPIDJSON_AVAILABLE is True
        except ImportError:
            assert RAPIDJSON_AVAILABLE is False

    def test_dumps_indent_4(self):
        try:
            provider = RapidjsonProvider()
        except ImportError:
            pytest.skip("python-rapidjson not installed")

        result = provider.dumps({"key": "value"}, indent=4)
        assert '    "key"' in result

    def test_separators_fallback(self):
        try:
            provider = RapidjsonProvider()
        except ImportError:
            pytest.skip("python-rapidjson not installed")

        # Should fallback to stdlib
        result = provider.dumps({"key": "value"}, separators=(",", ":"))
        assert result == '{"key":"value"}'

    def test_provider_name(self):
        try:
            provider = RapidjsonProvider()
        except ImportError:
            pytest.skip("python-rapidjson not installed")

        assert provider.provider_name == "rapidjson"

    def test_roundtrip(self):
        try:
            provider = RapidjsonProvider()
        except ImportError:
            pytest.skip("python-rapidjson not installed")

        original = {"key": "value", "number": 42, "nested": {"inner": "data"}}
        serialized = provider.dumps(original)
        deserialized = provider.loads(serialized)
        assert deserialized == original


class TestOrjsonProvider:
    """Tests for orjson provider with fallback logic."""

    def test_import_available(self):
        """Test that ORJSON_AVAILABLE flag is correct."""
        from audible.json.orjson_provider import ORJSON_AVAILABLE
        try:
            import orjson  # noqa: F401
            assert ORJSON_AVAILABLE is True
        except ImportError:
            assert ORJSON_AVAILABLE is False

    def test_dumps_compact(self):
        try:
            provider = OrjsonProvider()
        except ImportError:
            pytest.skip("orjson not installed")

        result = provider.dumps({"key": "value"})
        assert result == '{"key":"value"}'

    def test_dumps_indent_2(self):
        try:
            provider = OrjsonProvider()
        except ImportError:
            pytest.skip("orjson not installed")

        result = provider.dumps({"key": "value"}, indent=2)
        # orjson handles this natively
        assert '"key"' in result

    def test_dumps_indent_4_fallback(self):
        try:
            provider = OrjsonProvider()
        except ImportError:
            pytest.skip("orjson not installed")

        result = provider.dumps({"key": "value"}, indent=4)
        # Should fallback to ujson/rapidjson/stdlib
        assert '    "key"' in result

    def test_separators_fallback(self):
        try:
            provider = OrjsonProvider()
        except ImportError:
            pytest.skip("orjson not installed")

        # Should fallback to stdlib
        result = provider.dumps({"key": "value"}, separators=(",", ":"))
        assert result == '{"key":"value"}'

    def test_loads_string(self):
        try:
            provider = OrjsonProvider()
        except ImportError:
            pytest.skip("orjson not installed")

        result = provider.loads('{"key":"value"}')
        assert result == {"key": "value"}

    def test_loads_bytes(self):
        try:
            provider = OrjsonProvider()
        except ImportError:
            pytest.skip("orjson not installed")

        result = provider.loads(b'{"key":"value"}')
        assert result == {"key": "value"}

    def test_provider_name(self):
        try:
            provider = OrjsonProvider()
        except ImportError:
            pytest.skip("orjson not installed")

        assert provider.provider_name == "orjson"

    def test_roundtrip_compact(self):
        try:
            provider = OrjsonProvider()
        except ImportError:
            pytest.skip("orjson not installed")

        original = {"key": "value", "number": 42, "nested": {"inner": "data"}}
        serialized = provider.dumps(original)
        deserialized = provider.loads(serialized)
        assert deserialized == original

    def test_roundtrip_indent_4(self):
        try:
            provider = OrjsonProvider()
        except ImportError:
            pytest.skip("orjson not installed")

        original = {"key": "value", "number": 42}
        serialized = provider.dumps(original, indent=4)
        deserialized = provider.loads(serialized)
        assert deserialized == original


class TestRegistry:
    """Tests for provider registry and auto-detection."""

    def test_auto_detect(self):
        provider = get_json_provider()
        assert provider.provider_name in {"orjson", "ujson", "rapidjson", "stdlib"}

    def test_explicit_stdlib(self):
        provider = get_json_provider(StdlibProvider)
        assert provider.provider_name == "stdlib"

    def test_explicit_stdlib_instance(self):
        instance = StdlibProvider()
        provider = get_json_provider(instance)
        assert provider.provider_name == "stdlib"
        assert provider is instance

    def test_set_default(self):
        # Save original state
        original = get_json_provider()

        try:
            # Set stdlib as default
            set_default_json_provider(StdlibProvider)
            provider = get_json_provider()
            assert provider.provider_name == "stdlib"

            # Test that it persists
            provider2 = get_json_provider()
            assert provider2.provider_name == "stdlib"
        finally:
            # Restore auto-detection
            set_default_json_provider(None)

        # Verify restoration
        restored = get_json_provider()
        assert restored.provider_name == original.provider_name

    def test_set_default_instance(self):
        try:
            instance = StdlibProvider()
            set_default_json_provider(instance)
            provider = get_json_provider()
            assert provider is instance
        finally:
            set_default_json_provider(None)

    def test_roundtrip_auto(self):
        provider = get_json_provider()
        original = {"key": "value", "number": 42, "nested": {"inner": "data"}}

        serialized = provider.dumps(original)
        deserialized = provider.loads(serialized)

        assert deserialized == original

    def test_roundtrip_with_indent(self):
        provider = get_json_provider()
        original = {"key": "value", "array": [1, 2, 3]}

        serialized = provider.dumps(original, indent=4)
        deserialized = provider.loads(serialized)

        assert deserialized == original

    def test_invalid_provider(self):
        """Test that invalid providers raise ImportError."""
        class NotAProvider:
            pass

        with pytest.raises(ImportError, match="not a JSONProvider"):
            get_json_provider(NotAProvider())

    def test_unavailable_provider(self):
        """Test that requesting unavailable provider raises ImportError."""
        # This test assumes at least one provider is not installed
        # We'll test by trying to force a provider that might not exist
        try:
            # Try to import all providers to see which ones exist
            from audible.json.orjson_provider import ORJSON_AVAILABLE
            from audible.json.ujson_provider import UJSON_AVAILABLE
            from audible.json.rapidjson_provider import RAPIDJSON_AVAILABLE

            # If all are available, skip this test
            if ORJSON_AVAILABLE and UJSON_AVAILABLE and RAPIDJSON_AVAILABLE:
                pytest.skip("All providers available, cannot test unavailability")

            # Test one that's not available
            if not ORJSON_AVAILABLE:
                with pytest.raises(ImportError):
                    get_json_provider(OrjsonProvider)
            elif not UJSON_AVAILABLE:
                with pytest.raises(ImportError):
                    get_json_provider(UjsonProvider)
            elif not RAPIDJSON_AVAILABLE:
                with pytest.raises(ImportError):
                    get_json_provider(RapidjsonProvider)
        except ImportError:
            pytest.skip("Could not determine provider availability")
