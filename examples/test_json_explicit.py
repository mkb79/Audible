"""Example: Explicit JSON provider selection.

This example demonstrates how to explicitly select and configure JSON providers
for specific use cases or performance requirements.
"""

from audible.json_provider import (
    OrjsonProvider,
    StdlibProvider,
    UjsonProvider,
    get_json_provider,
    set_default_json_provider,
)


# Example data
data = {"asin": "B001", "title": "Book Title", "rating": 4.5}

print("=" * 60)
print("1. Using stdlib provider explicitly")
print("=" * 60)
try:
    stdlib = get_json_provider(StdlibProvider)
    print(f"Provider: {stdlib.provider_name}")
    print(f"Result: {stdlib.dumps(data, indent=4)}")
except ImportError as e:
    print(f"Error: {e}")

print("\n" + "=" * 60)
print("2. Using orjson provider")
print("=" * 60)
try:
    orjson = get_json_provider(OrjsonProvider)
    print(f"Provider: {orjson.provider_name}")
    print(f"Compact: {orjson.dumps(data)}")
    print(f"indent=2: {orjson.dumps(data, indent=2)}")
    print(f"indent=4 (uses fallback): {orjson.dumps(data, indent=4)}")
except ImportError as e:
    print(f"Error: {e}")

print("\n" + "=" * 60)
print("3. Using ujson provider")
print("=" * 60)
try:
    ujson = get_json_provider(UjsonProvider)
    print(f"Provider: {ujson.provider_name}")
    print(f"Result: {ujson.dumps(data, indent=4)}")
except ImportError as e:
    print(f"Error: {e}")

print("\n" + "=" * 60)
print("4. Setting a global default provider")
print("=" * 60)

# Set stdlib as the global default
set_default_json_provider(StdlibProvider)
default = get_json_provider()
print(f"Default provider: {default.provider_name}")

# Reset to auto-detection
set_default_json_provider(None)
auto = get_json_provider()
print(f"After reset: {auto.provider_name}")

print("\n" + "=" * 60)
print("5. Provider instance reuse")
print("=" * 60)

# Create an instance and reuse it
stdlib_instance = StdlibProvider()
provider1 = get_json_provider(stdlib_instance)
provider2 = get_json_provider(stdlib_instance)
print(f"Same instance: {provider1 is provider2}")
print(f"Same as input: {provider1 is stdlib_instance}")

print("\n" + "=" * 60)
print("Installation recommendations:")
print("=" * 60)
print("json-full (recommended): pip install audible[json-full]")
print("  └─ Includes: orjson + ujson (best coverage)")
print("")
print("json-fast: pip install audible[json-fast]")
print("  └─ Includes: orjson only (best for compact JSON)")
print("")
print("Individual providers:")
print("  - orjson: pip install audible[orjson]")
print("  - ujson: pip install audible[ujson]")
print("  - rapidjson: pip install audible[rapidjson]")
