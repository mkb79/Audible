"""Manual smoke test for crypto provider auto-detection.

Run with different extras to observe provider selection:
    uv run python examples/test_crypto_autodetect.py
    uv run --extra pycryptodome python examples/test_crypto_autodetect.py
    uv run --extra cryptography python examples/test_crypto_autodetect.py
    uv run --extra cryptography --extra pycryptodome python examples/test_crypto_autodetect.py
"""

from __future__ import annotations

from audible.crypto_provider import get_crypto_providers


def main() -> None:
    provider = get_crypto_providers()
    print(f"Auto-detected provider: {provider.provider_name}")

    key = bytes([0xAA]) * 16
    iv = bytes([0x55]) * 16
    plaintext = "auto-detect smoke test"

    ciphertext = provider.aes.encrypt(key, iv, plaintext)
    decrypted = provider.aes.decrypt(key, iv, ciphertext)

    print(f"AES round-trip ok: {decrypted == plaintext}")


if __name__ == "__main__":
    main()
