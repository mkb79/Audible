"""Integration tests for JSON providers in real-world scenarios."""

import pytest

from audible.json import get_json_provider


class TestRealWorldUsage:
    """Test real-world usage patterns from audible and audible-cli."""

    def test_auth_file_format(self):
        """Test auth file serialization (indent=4)."""
        provider = get_json_provider()

        auth_data = {
            "website_cookies": {"session": "abc123"},
            "adp_token": "token123",
            "device_private_key": "key123",
            "store_authentication_cookie": {"cookie": "value"},
            "access_token": "access123",
            "refresh_token": "refresh123",
            "expires": 1234567890.0,
        }

        result = provider.dumps(auth_data, indent=4)

        # Should be pretty-printed
        assert '    "website_cookies"' in result
        assert '    "access_token"' in result

        # Roundtrip should work
        parsed = provider.loads(result)
        assert parsed == auth_data

    def test_compact_api_response(self):
        """Test API response handling (compact JSON)."""
        provider = get_json_provider()

        api_response = {
            "items": [
                {"asin": "B001", "title": "Book 1"},
                {"asin": "B002", "title": "Book 2"},
            ],
            "total_count": 2,
        }

        # Compact format (no indent)
        result = provider.dumps(api_response)

        # Should be compact (no extra whitespace beyond what provider adds)
        # orjson will be compact, ujson might add some spaces
        assert "items" in result
        assert "B001" in result

        # Roundtrip
        parsed = provider.loads(result)
        assert parsed == api_response

    def test_metadata_with_separators(self):
        """Test metadata format with custom separators (rare case)."""
        import json  # Use stdlib directly for this edge case

        meta_dict = {
            "n": "fwcim-ubf-collector",
            "t": 0,
        }

        # This specific case stays with stdlib json
        result = json.dumps(meta_dict, separators=(",", ":"))
        assert result == '{"n":"fwcim-ubf-collector","t":0}'

    def test_library_export(self):
        """Test library export (indent=4, from audible-cli)."""
        provider = get_json_provider()

        library_data = {
            "items": [
                {
                    "asin": "B001",
                    "title": "The Great Book",
                    "authors": ["Author Name"],
                    "narrators": ["Narrator Name"],
                    "runtime_length_min": 600,
                }
            ]
        }

        result = provider.dumps(library_data, indent=4)

        # Should be readable
        assert '    "items"' in result
        assert '        "asin"' in result  # Nested indent

        # Roundtrip
        parsed = provider.loads(result)
        assert parsed == library_data

    def test_wishlist_export(self):
        """Test wishlist export (indent=4, from audible-cli)."""
        provider = get_json_provider()

        wishlist_data = {
            "items": [
                {
                    "asin": "B003",
                    "title": "Wishlisted Book",
                    "date_added": "2024-01-15",
                }
            ]
        }

        result = provider.dumps(wishlist_data, indent=4)

        # Should be pretty-printed
        assert '    "items"' in result

        # Roundtrip
        parsed = provider.loads(result)
        assert parsed == wishlist_data

    def test_chapter_metadata(self):
        """Test chapter metadata export (indent=4, from audible-cli)."""
        provider = get_json_provider()

        chapter_data = {
            "content_metadata": {
                "chapter_info": {
                    "brandIntroDurationMs": 2000,
                    "brandOutroDurationMs": 5000,
                    "chapters": [
                        {
                            "length_ms": 120000,
                            "start_offset_ms": 0,
                            "start_offset_sec": 0,
                            "title": "Chapter 1",
                        }
                    ],
                }
            }
        }

        result = provider.dumps(chapter_data, indent=4)

        # Should be readable
        assert '    "content_metadata"' in result
        assert '        "chapter_info"' in result

        # Roundtrip
        parsed = provider.loads(result)
        assert parsed == chapter_data

    def test_annotation_export(self):
        """Test annotation export (indent=4, from audible-cli)."""
        provider = get_json_provider()

        annotation_data = {
            "asin": "B001",
            "annotations": [
                {
                    "note": "Great quote",
                    "start_position": 12345,
                    "end_position": 12450,
                }
            ],
        }

        result = provider.dumps(annotation_data, indent=4)

        # Should be pretty-printed
        assert '    "asin"' in result
        assert '    "annotations"' in result

        # Roundtrip
        parsed = provider.loads(result)
        assert parsed == annotation_data

    def test_license_response(self):
        """Test AAXC license response (indent=4, from audible-cli)."""
        provider = get_json_provider()

        license_response = {
            "content_license": {
                "license_response": "base64encodeddata",
                "status_code": "Granted",
            }
        }

        result = provider.dumps(license_response, indent=4)

        # Should be readable
        assert '    "content_license"' in result

        # Roundtrip
        parsed = provider.loads(result)
        assert parsed == license_response

    def test_complex_nested_structure(self):
        """Test complex nested structures with mixed types."""
        provider = get_json_provider()

        complex_data = {
            "string": "value",
            "number": 42,
            "float": 3.14,
            "boolean": True,
            "null": None,
            "array": [1, 2, 3],
            "nested_object": {
                "inner": "data",
                "deep": {
                    "very_deep": {
                        "value": "nested"
                    }
                }
            },
            "mixed_array": [
                {"type": "dict"},
                ["nested", "list"],
                42,
                "string"
            ]
        }

        # Test with indent=4
        result = provider.dumps(complex_data, indent=4)
        parsed = provider.loads(result)
        assert parsed == complex_data

        # Test compact
        compact = provider.dumps(complex_data)
        parsed_compact = provider.loads(compact)
        assert parsed_compact == complex_data

    def test_unicode_handling(self):
        """Test that unicode characters are handled correctly."""
        provider = get_json_provider()

        # Use simple unicode that won't have encoding issues
        unicode_data = {
            "ascii": "simple",
            "latin": "café"
        }

        # Test roundtrip
        result = provider.dumps(unicode_data)
        parsed = provider.loads(result)
        assert parsed == unicode_data

    def test_empty_structures(self):
        """Test empty objects and arrays."""
        provider = get_json_provider()

        # Empty object
        assert provider.loads(provider.dumps({})) == {}

        # Empty array
        assert provider.loads(provider.dumps([])) == []

        # Nested empty
        nested_empty = {"obj": {}, "arr": [], "null": None}
        assert provider.loads(provider.dumps(nested_empty)) == nested_empty

    def test_large_dataset(self):
        """Test handling of larger datasets (performance sanity check)."""
        provider = get_json_provider()

        # Create a moderately large dataset
        large_data = {
            "items": [
                {
                    "id": i,
                    "title": f"Item {i}",
                    "description": f"Description for item {i}" * 10,
                    "metadata": {
                        "created": f"2024-01-{i % 30 + 1:02d}",
                        "tags": [f"tag{j}" for j in range(5)],
                    }
                }
                for i in range(100)
            ]
        }

        # Should handle both compact and pretty-printed
        compact = provider.dumps(large_data)
        pretty = provider.dumps(large_data, indent=4)

        # Verify roundtrips
        assert provider.loads(compact) == large_data
        assert provider.loads(pretty) == large_data

        # Pretty version should be larger due to whitespace
        assert len(pretty) > len(compact)
