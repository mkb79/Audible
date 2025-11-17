"""Manual smoke test for explicit provider selection.

Run with:
    uv run --extra cryptography --extra pycryptodome python examples/test_crypto_explicit.py
"""

from __future__ import annotations

from audible.crypto_provider import (
    CryptographyProvider,
    LegacyProvider,
    PycryptodomeProvider,
    get_crypto_providers,
)


PROVIDERS = [
    ("cryptography", CryptographyProvider),
    ("pycryptodome", PycryptodomeProvider),
    ("legacy", LegacyProvider),
]


def main() -> None:
    """Run AES smoke tests for each available provider."""
    key = bytes([0x01]) * 16
    iv = bytes([0x02]) * 16
    plaintext = "explicit provider smoke test"

    for name, provider_cls in PROVIDERS:
        print(f"\nAttempting provider: {name}")
        try:
            provider = get_crypto_providers(provider_cls)
        except ImportError as exc:  # provider not installed
            print(f"  unavailable: {exc}")
            continue

        ciphertext = provider.aes.encrypt(key, iv, plaintext)
        recovered = provider.aes.decrypt(key, iv, ciphertext)
        print(f"  AES round-trip ok: {recovered == plaintext}")
        print(f"  provider name: {provider.provider_name}")


if __name__ == "__main__":
    main()
