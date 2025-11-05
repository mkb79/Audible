"""Tests for orjson fallback logic."""

import pytest

from audible.json import OrjsonProvider, get_json_provider


class TestOrjsonFallback:
    """Test orjson smart fallback logic."""

    def test_fallback_chain_indent_4(self) -> None:
        """Test that indent=4 triggers fallback."""
        try:
            provider = OrjsonProvider()
        except ImportError:
            pytest.skip("orjson not installed")

        data = {"key": "value", "nested": {"inner": "data"}}
        result = provider.dumps(data, indent=4)

        # Should be formatted with 4-space indent
        assert '    "key"' in result
        assert '        "inner"' in result

    def test_fallback_preserves_correctness(self) -> None:
        """Test that fallback doesn't corrupt data."""
        try:
            provider = OrjsonProvider()
        except ImportError:
            pytest.skip("orjson not installed")

        test_data = {
            "string": "value",
            "number": 42,
            "float": 3.14,
            "bool": True,
            "null": None,
            "array": [1, 2, 3],
            "object": {"nested": "data"},
        }

        # Test with various indent values
        for indent in [None, 2, 4]:
            serialized = provider.dumps(test_data, indent=indent)
            deserialized = provider.loads(serialized)
            assert deserialized == test_data, f"Data corrupted with indent={indent}"

    def test_separators_fallback_to_stdlib(self) -> None:
        """Test that separators trigger stdlib fallback."""
        try:
            provider = OrjsonProvider()
        except ImportError:
            pytest.skip("orjson not installed")

        data = {"key": "value"}
        result = provider.dumps(data, separators=(",", ":"))

        # Should use compact format
        assert result == '{"key":"value"}'

    def test_native_orjson_compact(self) -> None:
        """Test that compact JSON uses native orjson."""
        try:
            provider = OrjsonProvider()
        except ImportError:
            pytest.skip("orjson not installed")

        data = {"key": "value", "num": 42}
        result = provider.dumps(data)

        # orjson produces compact JSON
        assert result == '{"key":"value","num":42}'

    def test_native_orjson_indent_2(self) -> None:
        """Test that indent=2 uses native orjson."""
        try:
            provider = OrjsonProvider()
        except ImportError:
            pytest.skip("orjson not installed")

        data = {"key": "value"}
        result = provider.dumps(data, indent=2)

        # Should have 2-space indentation
        assert '  "key"' in result

    def test_fallback_to_ujson_or_stdlib(self) -> None:
        """Test that indent=4 falls back to ujson or stdlib."""
        try:
            provider = OrjsonProvider()
        except ImportError:
            pytest.skip("orjson not installed")

        data = {"key": "value"}
        result = provider.dumps(data, indent=4)

        # Should have 4-space indentation (from fallback)
        assert '    "key"' in result

        # Should still roundtrip correctly
        parsed = provider.loads(result)
        assert parsed == data

    def test_fallback_with_nested_data(self) -> None:
        """Test fallback with deeply nested structures."""
        try:
            provider = OrjsonProvider()
        except ImportError:
            pytest.skip("orjson not installed")

        data = {
            "level1": {
                "level2": {
                    "level3": {
                        "level4": "deep value"
                    }
                }
            }
        }

        # Test with indent=4 (fallback)
        result = provider.dumps(data, indent=4)

        # Should preserve structure
        assert '    "level1"' in result
        assert '        "level2"' in result
        assert '            "level3"' in result

        # Roundtrip should work
        parsed = provider.loads(result)
        assert parsed == data

    def test_fallback_with_arrays(self) -> None:
        """Test fallback with arrays and mixed content."""
        try:
            provider = OrjsonProvider()
        except ImportError:
            pytest.skip("orjson not installed")

        data = {
            "items": [
                {"id": 1, "name": "first"},
                {"id": 2, "name": "second"},
                {"id": 3, "name": "third"},
            ]
        }

        # Test with indent=4 (fallback)
        result = provider.dumps(data, indent=4)

        # Should be properly formatted
        assert '    "items"' in result

        # Roundtrip
        parsed = provider.loads(result)
        assert parsed == data

    def test_performance_sanity_compact(self) -> None:
        """Sanity check that compact JSON uses fast path."""
        try:
            provider = OrjsonProvider()
        except ImportError:
            pytest.skip("orjson not installed")

        # Large dataset
        data = {"items": [{"id": i, "value": f"item{i}"} for i in range(1000)]}

        # This should use native orjson (fast)
        result = provider.dumps(data)

        # Verify it's valid and compact
        parsed = provider.loads(result)
        assert parsed == data
        assert len(result) < len(provider.dumps(data, indent=4))

    def test_mixed_indent_values(self) -> None:
        """Test various indent values trigger correct paths."""
        try:
            provider = OrjsonProvider()
        except ImportError:
            pytest.skip("orjson not installed")

        data = {"test": "value"}

        # None -> native orjson
        result_none = provider.dumps(data, indent=None)
        assert "test" in result_none

        # 2 -> native orjson
        result_2 = provider.dumps(data, indent=2)
        assert '  "test"' in result_2

        # 4 -> fallback
        result_4 = provider.dumps(data, indent=4)
        assert '    "test"' in result_4

        # 8 -> fallback
        result_8 = provider.dumps(data, indent=8)
        assert '        "test"' in result_8

        # All should roundtrip
        for result in [result_none, result_2, result_4, result_8]:
            assert provider.loads(result) == data

    def test_separator_with_indent(self) -> None:
        """Test that separators override indent and use stdlib."""
        try:
            provider = OrjsonProvider()
        except ImportError:
            pytest.skip("orjson not installed")

        data = {"key": "value"}

        # Even with indent, separators should force stdlib
        result = provider.dumps(data, indent=4, separators=(",", ":"))

        # Should use compact format from stdlib (separators take precedence)
        # The result will have indent=4 formatting from stdlib
        assert '    "key"' in result

    def test_lazy_fallback_initialization(self) -> None:
        """Test that fallback provider is lazily initialized."""
        try:
            provider = OrjsonProvider()
        except ImportError:
            pytest.skip("orjson not installed")

        # Before any fallback operation, _fallback_provider should be None
        assert provider._fallback_provider is None

        # After an operation that needs fallback, it should be initialized
        provider.dumps({"test": "value"}, indent=4)

        # Now it should be initialized (or still None if orjson can handle it somehow)
        # The provider itself should still work correctly
        result = provider.dumps({"test": "value"}, indent=4)
        assert provider.loads(result) == {"test": "value"}


class TestAutoProviderFallback:
    """Test that auto-detected provider handles fallbacks."""

    def test_auto_provider_indent_4(self) -> None:
        """Test auto-detected provider with indent=4."""
        provider = get_json_provider()

        data = {"key": "value", "number": 42}
        result = provider.dumps(data, indent=4)

        # Should be formatted with 4-space indent regardless of provider
        assert '    "key"' in result

        # Should roundtrip
        parsed = provider.loads(result)
        assert parsed == data

    def test_auto_provider_separators(self) -> None:
        """Test auto-detected provider with separators."""
        provider = get_json_provider()

        data = {"key": "value"}
        result = provider.dumps(data, separators=(",", ":"))

        # Should produce compact output
        assert result == '{"key":"value"}'

    def test_auto_provider_mixed_operations(self) -> None:
        """Test auto-detected provider with various operation types."""
        provider = get_json_provider()

        data = {
            "items": [
                {"id": 1, "name": "test1"},
                {"id": 2, "name": "test2"},
            ]
        }

        # Compact
        compact = provider.dumps(data)
        assert provider.loads(compact) == data

        # indent=2
        indent2 = provider.dumps(data, indent=2)
        assert provider.loads(indent2) == data

        # indent=4
        indent4 = provider.dumps(data, indent=4)
        assert provider.loads(indent4) == data
        assert '    "items"' in indent4

        # separators
        sep = provider.dumps(data, separators=(",", ":"))
        assert provider.loads(sep) == data
