"""Manual integration smoke test for Authenticator with crypto overrides.

Usage:
    export AUTH_FIXTURE_PASSWORD=test_password_123
    uv run --extra cryptography --extra pycryptodome python examples/test_auth_integration.py
"""

from __future__ import annotations

import json
import os
from pathlib import Path

from audible import Authenticator
from audible.aescipher import AESCipher
from audible.auth import sign_request
from audible.crypto_provider import (
    CryptographyProvider,
    LegacyProvider,
    PycryptodomeProvider,
)


FIXTURES_DIR = Path("tests/fixtures")
AUTH_JSON = FIXTURES_DIR / "auth_fixture.json"
AUTH_JSON_ENCRYPTED = FIXTURES_DIR / "auth_fixture_encrypted_json.json"
PASSWORD = os.environ.get("AUTH_FIXTURE_PASSWORD")


def _load_fixture() -> dict[str, str]:
    """Return the JSON payload backing the auth fixtures."""
    return json.loads(AUTH_JSON.read_text())


def smoke(auth: Authenticator) -> None:
    """Print signing headers for a configured authenticator."""
    request_headers = sign_request(
        method="GET",
        path="/test",
        body=b"",
        adp_token=auth.adp_token or "dummy",
        private_key=auth.device_private_key or "",
        crypto_provider=auth._get_crypto(),  # pragma: no cover - manual check
    )
    print("Signed headers:", sorted(request_headers))


PROVIDERS = [
    ("legacy", LegacyProvider),
    ("pycryptodome", PycryptodomeProvider),
    ("cryptography", CryptographyProvider),
]


def main() -> None:
    """Exercise authenticator flows under each available provider."""
    if PASSWORD is None:
        raise RuntimeError("Set AUTH_FIXTURE_PASSWORD environment variable")

    for name, provider_cls in PROVIDERS:
        print(f"\nTesting Authenticator with provider: {name}")
        data = _load_fixture()
        try:
            auth = Authenticator.from_dict(data, crypto_provider=provider_cls)
        except ImportError as exc:
            print(f"  unavailable: {exc}")
            continue

        print("  provider name:", auth._get_crypto().provider_name)
        smoke(auth)

    # Validate decrypting the encrypted JSON fixture via AESCipher
    print("\nDecrypting encrypted auth fixture via AESCipher...")
    cipher = AESCipher(password=PASSWORD, crypto_provider=LegacyProvider)
    decrypted = cipher.from_dict(json.loads(AUTH_JSON_ENCRYPTED.read_text()))
    print("  decrypted matches original:", json.loads(decrypted) == _load_fixture())


if __name__ == "__main__":
    main()
