"""Example: Auto-detection of JSON providers.

This example demonstrates how the JSON provider system automatically detects
and uses the best available JSON library for optimal performance.

Priority order:
1. orjson (Rust-based, 4-5x faster) - for compact JSON
2. ujson (C-based, 2-3x faster) - fallback for indent=4
3. rapidjson (C++ based, 2-3x faster) - alternative fallback
4. stdlib json (always available) - baseline

The library automatically uses the fastest available provider while maintaining
full backward compatibility with stdlib json.
"""

from audible.json_provider import get_json_provider


# Get the auto-detected provider
provider = get_json_provider()
print(f"Auto-detected provider: {provider.provider_name}")

# Example data
data = {
    "title": "The Great Book",
    "author": "Jane Doe",
    "chapters": [
        {"number": 1, "title": "Introduction", "duration": 300},
        {"number": 2, "title": "The Journey Begins", "duration": 450},
    ],
}

# Compact JSON (orjson excels here)
compact = provider.dumps(data)
print(f"\nCompact JSON ({len(compact)} bytes):")
print(compact)

# Pretty-printed JSON with indent=4 (uses ujson/rapidjson/stdlib)
pretty = provider.dumps(data, indent=4)
print(f"\nPretty JSON ({len(pretty)} bytes):")
print(pretty)

# Verify roundtrip
parsed = provider.loads(compact)
assert parsed == data
print("\n✓ Roundtrip successful!")

# Performance characteristics by provider:
print("\nPerformance characteristics:")
print("- orjson: 4-5x faster than stdlib (compact JSON)")
print("- ujson: 2-3x faster than stdlib (all operations)")
print("- rapidjson: 2-3x faster than stdlib (all operations)")
print("- stdlib: Baseline performance (always available)")
