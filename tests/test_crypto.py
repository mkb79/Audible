"""Comprehensive tests for the crypto module and provider overrides."""

from __future__ import annotations

import concurrent.futures
import hashlib
import json
import os
import uuid
from typing import Any

import pytest

from audible.aescipher import AESCipher, decrypt_voucher_from_licenserequest
from audible.auth import Authenticator, sign_request
from audible.crypto import (
    CryptographyProvider,
    LegacyProvider,
    PycryptodomeProvider,
    get_crypto_providers,
    set_default_crypto_provider,
)


PROVIDER_CLASSES = {
    "legacy": LegacyProvider,
    "pycryptodome": PycryptodomeProvider,
    "cryptography": CryptographyProvider,
}


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(params=PROVIDER_CLASSES.keys(), ids=lambda name: name)
def provider_name_and_class(
    request: pytest.FixtureRequest, crypto_provider_availability: dict[str, bool]
) -> tuple[str, type]:
    """Yield provider name/class pairs, skipping unavailable backends."""
    name = request.param
    if name != "legacy" and not crypto_provider_availability[name]:
        pytest.skip(f"{name} provider is not installed")
    return name, PROVIDER_CLASSES[name]


@pytest.fixture
def provider_instance(
    provider_name_and_class: tuple[str, type],
) -> tuple[str, Any]:
    """Instantiate provider via the registry for tests."""
    name, provider_cls = provider_name_and_class
    return name, get_crypto_providers(provider_cls)


# ---------------------------------------------------------------------------
# Provider contract tests
# ---------------------------------------------------------------------------


def test_provider_name_matches_instance(provider_instance: tuple[str, Any]) -> None:
    """Providers should expose a matching provider_name."""
    name, provider = provider_instance
    assert provider.provider_name == name


def test_provider_aes_round_trip(provider_instance: tuple[str, Any]) -> None:
    """AES encrypt/decrypt round-trip works for every provider."""
    _, provider = provider_instance
    aes = provider.aes
    key = b"sixteen byte key"
    iv = b"sixteen byte iv!"
    plaintext = "crypto round trip"

    ciphertext = aes.encrypt(key, iv, plaintext)
    assert ciphertext != plaintext.encode()
    assert aes.decrypt(key, iv, ciphertext) == plaintext


def test_provider_aes_no_padding(provider_instance: tuple[str, Any]) -> None:
    """AES CBC without padding is supported uniformly."""
    _, provider = provider_instance
    aes = provider.aes
    key = b"sixteen byte key"
    iv = b"sixteen byte iv!"
    plaintext = "exactly16bytes!!"

    ciphertext = aes.encrypt(key, iv, plaintext, padding="none")
    assert aes.decrypt(key, iv, ciphertext, padding="none") == plaintext


def test_provider_aes_wrong_key_raises(provider_instance: tuple[str, Any]) -> None:
    """Decrypting with a wrong key raises ValueError across providers."""
    _, provider = provider_instance
    aes = provider.aes
    key = b"sixteen byte key"
    wrong_key = b"wrong_key_16byte"
    iv = b"sixteen byte iv!"
    ciphertext = aes.encrypt(key, iv, "payload")

    with pytest.raises(ValueError):
        aes.decrypt(wrong_key, iv, ciphertext)


def test_provider_pbkdf2_matches_reference(provider_instance: tuple[str, Any]) -> None:
    """PBKDF2 implementations align with hashlib reference output."""
    _, provider = provider_instance
    pbkdf2 = provider.pbkdf2
    password = os.environ.get("TEST_PASSWORD")
    if password is None:
        pytest.skip("TEST_PASSWORD env var not set")
    salt = b"test_salt_16byte"
    iterations = 1000
    key_size = 32

    expected = hashlib.pbkdf2_hmac(
        "sha256", password.encode("utf-8"), salt, iterations, key_size
    )
    derived = pbkdf2.derive_key(password, salt, iterations, key_size, hashlib.sha256)

    assert derived == expected


def test_provider_hashes(provider_instance: tuple[str, Any]) -> None:
    """Hash helpers mirror hashlib outputs."""
    _, provider = provider_instance
    data = b"hash me"

    assert provider.hash.sha256(data) == hashlib.sha256(data).digest()
    assert (
        provider.hash.sha1(data) == hashlib.sha1(data, usedforsecurity=False).digest()
    )


def test_provider_rsa_signatures(
    provider_instance: tuple[str, Any], rsa_private_key: str
) -> None:
    """RSA load/sign works for every provider."""
    _, provider = provider_instance

    key_obj = provider.rsa.load_private_key(rsa_private_key)
    signature = provider.rsa.sign(key_obj, b"data to sign")

    assert len(signature) > 0


@pytest.mark.parametrize("backend", ["pycryptodome"])
def test_pycryptodome_specific_invalid_hash(
    backend: str, crypto_provider_availability: dict[str, bool]
) -> None:
    """Pycryptodome raises ValueError for unsupported hash algorithms."""
    if not crypto_provider_availability["pycryptodome"]:
        pytest.skip("pycryptodome provider is not installed")

    provider = get_crypto_providers(PycryptodomeProvider)

    class UnsupportedHash:
        name = "unsupported_algo"

    with pytest.raises(ValueError, match="Unsupported hash algorithm"):
        provider.pbkdf2.derive_key(
            "password", b"salt", 1000, 32, lambda: UnsupportedHash()
        )


# ---------------------------------------------------------------------------
# AESCipher behaviour (encrypted fixtures)
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("encryption", ["json", "bytes"])
def test_aescipher_decrypts_fixtures(
    provider_name_and_class: tuple[str, type],
    auth_fixture_password: str,
    auth_fixture_encrypted_json_data: dict[str, Any],
    auth_fixture_encrypted_bytes_data: bytes,
    auth_fixture_data: dict[str, Any],
    encryption: str,
) -> None:
    """Each provider can decrypt the pre-generated auth fixtures."""
    _, provider_cls = provider_name_and_class
    cipher = AESCipher(password=auth_fixture_password, crypto_provider=provider_cls)

    if encryption == "json":
        decrypted = cipher.from_dict(auth_fixture_encrypted_json_data)
    else:
        decrypted = cipher.from_bytes(auth_fixture_encrypted_bytes_data)

    assert json.loads(decrypted) == auth_fixture_data


def test_aescipher_wrong_password_raises(
    provider_name_and_class: tuple[str, type],
    auth_fixture_encrypted_json_data: dict[str, Any],
) -> None:
    """Decrypting with the wrong password fails under every provider."""
    _, provider_cls = provider_name_and_class
    wrong_password = os.environ.get("TEST_WRONG_PASSWORD") or uuid.uuid4().hex
    cipher = AESCipher(password=wrong_password, crypto_provider=provider_cls)

    with pytest.raises(ValueError):
        cipher.from_dict(auth_fixture_encrypted_json_data)


# ---------------------------------------------------------------------------
# Registry override / singleton behaviour
# ---------------------------------------------------------------------------


def test_set_default_crypto_provider_overrides(
    provider_name_and_class: tuple[str, type],
) -> None:
    """Default provider override should govern subsequent lookups."""
    name, provider_cls = provider_name_and_class

    set_default_crypto_provider(provider_cls)
    override = get_crypto_providers()
    again = get_crypto_providers()

    assert override is again
    assert override.provider_name == name


def test_set_default_crypto_provider_reset(
    provider_name_and_class: tuple[str, type],
) -> None:
    """Resetting default provider clears cached instances."""
    _, provider_cls = provider_name_and_class

    set_default_crypto_provider(provider_cls)
    overridden = get_crypto_providers()
    set_default_crypto_provider()
    auto = get_crypto_providers()

    assert overridden is not auto


def test_registry_singleton_thread_safety() -> None:
    """Singleton registry should remain stable across threads."""
    instances: list[Any] = []
    instance_ids: list[int] = []

    def create_registry() -> None:
        provider = get_crypto_providers()
        instances.append(provider)
        instance_ids.append(id(provider))

    with concurrent.futures.ThreadPoolExecutor(max_workers=20) as executor:
        futures = [executor.submit(create_registry) for _ in range(100)]
        concurrent.futures.wait(futures)

    unique_ids = set(instance_ids)
    assert len(unique_ids) == 1, f"Expected 1 singleton, found {len(unique_ids)}"
    assert all(inst is instances[0] for inst in instances)


# ---------------------------------------------------------------------------
# Authenticator / voucher integration
# ---------------------------------------------------------------------------


def _make_license_response() -> dict[str, Any]:
    """Construct a minimal license response for voucher helpers."""
    return {
        "content_license": {
            "asin": "TEST-ASIN",
            "license_response": "base64-voucher-placeholder",
        }
    }


def test_decrypt_voucher_forwards_crypto_override(
    auth_fixture_data: dict[str, Any], monkeypatch: pytest.MonkeyPatch
) -> None:
    """Explicit crypto provider for decrypt_voucher is forwarded downstream."""
    auth = Authenticator.from_dict(auth_fixture_data)
    explicit_provider = get_crypto_providers(LegacyProvider)
    captured: dict[str, Any] = {}

    def fake_decrypt(**kwargs: Any) -> dict[str, Any]:
        captured["crypto_provider"] = kwargs["crypto_provider"]
        return {"ok": True}

    monkeypatch.setattr(
        "audible.aescipher._decrypt_voucher",
        fake_decrypt,
    )

    result = decrypt_voucher_from_licenserequest(
        auth,
        _make_license_response(),
        crypto_provider=explicit_provider,
    )

    assert result == {"ok": True}
    assert captured["crypto_provider"] is explicit_provider


def test_decrypt_voucher_uses_auth_provider_when_unspecified(
    auth_fixture_data: dict[str, Any], monkeypatch: pytest.MonkeyPatch
) -> None:
    """When no override is supplied, Authenticator's provider is reused."""
    auth = Authenticator.from_dict(auth_fixture_data, crypto_provider=LegacyProvider)
    expected_provider = auth._get_crypto()
    captured: dict[str, Any] = {}

    def fake_decrypt(**kwargs: Any) -> dict[str, Any]:
        captured["crypto_provider"] = kwargs["crypto_provider"]
        return {"ok": True}

    monkeypatch.setattr(
        "audible.aescipher._decrypt_voucher",
        fake_decrypt,
    )

    decrypt_voucher_from_licenserequest(auth, _make_license_response())

    assert captured["crypto_provider"] is expected_provider


def test_sign_request_accepts_provider_instance(
    rsa_private_key: str,
) -> None:
    """sign_request should accept pre-instantiated providers."""
    provider = get_crypto_providers(LegacyProvider)
    token = os.environ.get("TEST_ADP_TOKEN", "dummy-token")
    headers = sign_request(
        method="GET",
        path="/test",
        body=b"",
        adp_token=token,
        private_key=rsa_private_key,
        crypto_provider=provider,
    )

    assert headers["x-adp-alg"] == "SHA256withRSA:1.0"
    assert headers["x-adp-token"] == token
    assert headers["x-adp-signature"]
