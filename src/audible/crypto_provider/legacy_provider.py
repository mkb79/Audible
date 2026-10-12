"""Legacy crypto provider using pure Python libraries.

This module implements the crypto protocols using the existing pure-Python
libraries: pyaes for AES, pbkdf2 for key derivation, and rsa for RSA signing.

These implementations are slower than native C extensions but are pure Python
and work in all environments without compilation.
"""

import hmac
import logging
import warnings
from base64 import b64decode
from collections.abc import Callable
from hashlib import sha1, sha256
from re import DOTALL, match
from typing import TYPE_CHECKING, Any

from pyasn1.codec.der import decoder
from pyasn1.type import namedtype, univ


if TYPE_CHECKING:
    from .protocols import HashAlgorithm

import rsa
from pbkdf2 import PBKDF2  # type: ignore[import-untyped]
from pyaes import (  # type: ignore[import-untyped]
    AESModeOfOperationCBC,
    Decrypter,
    Encrypter,
)


logger = logging.getLogger("audible.crypto_provider.legacy")


def _convert_pkcs8_der_rsa_to_pkcs1_der(pkcs8_der: bytes) -> bytes:
    """Converts a PKCS#8 DER RSA key to a PKCS#1 DER key.

    Args:
        pkcs8_der: An RSA key in PKCS#8 DER format.

    Returns:
        An RSA key in PKCS#1 DER format.

    Raises:
        ValueError: If PKCS#8 algorithm OID is not RSA
            (1.2.840.113549.1.1.1).
    """

    class PrivateKeyAlgorithm(univ.Sequence):
        componentType = namedtype.NamedTypes(  # noqa: N815
            namedtype.NamedType("algorithm", univ.ObjectIdentifier()),
            namedtype.NamedType("parameters", univ.Any()),
        )

    class PrivateKeyInfo(univ.Sequence):
        componentType = namedtype.NamedTypes(  # noqa: N815
            namedtype.NamedType("version", univ.Integer()),
            namedtype.NamedType("pkalgo", PrivateKeyAlgorithm()),
            namedtype.NamedType("key", univ.OctetString()),
        )

    logger.debug("Converting PKCS#8 RSA key to PKCS#1 (legacy provider)")
    (key_info, _) = decoder.decode(pkcs8_der, asn1Spec=PrivateKeyInfo())
    rsa_oid = univ.ObjectIdentifier((1, 2, 840, 113549, 1, 1, 1))
    if key_info["pkalgo"]["algorithm"] != rsa_oid:
        raise ValueError("key_info.pkalgo.algorithm: Algorithm is not RSA.")

    return bytes(key_info["key"])


def _load_rsa_private_key_legacy(pem_data: str) -> rsa.PrivateKey:
    """Load an RSA private key from PEM.

    Note:
        This function does NOT cache keys. Caching is the caller's
        responsibility (e.g., Authenticator._cached_rsa_key for performance).

    Args:
        pem_data: RSA private key in PEM format.

    Returns:
        A parsed rsa.PrivateKey object.

    Raises:
        ValueError: If the PEM data is in an incorrect format or if key type is not
            'PRIVATE KEY' or 'RSA PRIVATE KEY'.
    """
    pem_fmt = (
        r"^-----BEGIN (?P<private_key_type>(?:RSA )?PRIVATE KEY)-----"
        r"(?P<der_b64_str>.*)-----END \1-----\n$"
    )
    key_match = match(pem_fmt, pem_data, DOTALL)
    if not key_match:
        raise ValueError("pem_data: Invalid token.")

    private_key_type = key_match.group("private_key_type")
    private_key_der = b64decode(key_match.group("der_b64_str"))
    if private_key_type == "PRIVATE KEY":
        private_key_der = _convert_pkcs8_der_rsa_to_pkcs1_der(private_key_der)

    logger.debug("Loading RSA private key (legacy provider)")
    return rsa.PrivateKey.load_pkcs1(private_key_der, "DER")


class LegacyAESProvider:
    """AES-CBC provider using the pyaes library.

    This implementation uses pure Python AES from the pyaes library.
    While slower than native implementations, it works everywhere and
    requires no compilation.
    """

    def encrypt(
        self, key: bytes, iv: bytes, data: str, padding: str = "default"
    ) -> bytes:
        """Encrypt data using AES-CBC with pyaes.

        Args:
            key: The AES encryption key.
            iv: The initialization vector.
            data: The plaintext data to encrypt.
            padding: Padding mode ("default" for PKCS7, "none" for no padding).

        Returns:
            The encrypted ciphertext.
        """
        encrypter = Encrypter(AESModeOfOperationCBC(key, iv), padding=padding)
        encrypted: bytes = encrypter.feed(data) + encrypter.feed()
        return encrypted

    def decrypt(
        self, key: bytes, iv: bytes, encrypted_data: bytes, padding: str = "default"
    ) -> str:
        """Decrypt data using AES-CBC with pyaes.

        Args:
            key: The AES decryption key.
            iv: The initialization vector.
            encrypted_data: The ciphertext to decrypt.
            padding: Padding mode ("default" for PKCS7, "none" for no padding).

        Returns:
            The decrypted plaintext as a string.

        Raises:
            ValueError: If PKCS7 padding is invalid or UTF-8 decoding fails
                (wrong key/IV or corrupted data).
        """
        decrypter = Decrypter(AESModeOfOperationCBC(key, iv), padding=padding)
        decrypted: bytes = decrypter.feed(encrypted_data) + decrypter.feed()

        # Decode decrypted bytes to string
        try:
            return decrypted.decode("utf-8")
        except UnicodeDecodeError as e:
            msg = (
                "Failed to decode decrypted data as UTF-8 - possible decryption "
                "key/IV mismatch or corrupted ciphertext"
            )
            raise ValueError(msg) from e


class LegacyPBKDF2Provider:
    """PBKDF2 provider using the pbkdf2 library.

    This implementation uses pure Python PBKDF2 from the pbkdf2 library.
    """

    def derive_key(
        self,
        password: str,
        salt: bytes,
        iterations: int,
        key_size: int,
        hashmod: Callable[..., "HashAlgorithm"],
    ) -> bytes:
        """Derive a key using PBKDF2 with the pbkdf2 library.

        Args:
            password: The password to derive from.
            salt: Random salt for derivation.
            iterations: Number of iterations (clamped to 65535 max).
            key_size: Desired key size in bytes.
            hashmod: Hash function factory.

        Returns:
            The derived key.
        """
        kdf = PBKDF2(password, salt, min(iterations, 65535), hashmod, hmac)
        key: bytes = kdf.read(key_size)
        return key


class LegacyRSAProvider:
    """RSA provider using the rsa library.

    This implementation uses pure Python RSA from the rsa library.
    """

    def load_private_key(self, pem_data: str) -> rsa.PrivateKey:
        """Load an RSA private key from PEM.

        Note:
            Caching is the caller's responsibility for optimal performance.

        Args:
            pem_data: RSA private key in PEM format.

        Returns:
            A parsed rsa.PrivateKey object.
        """
        return _load_rsa_private_key_legacy(pem_data)

    def sign(self, key: Any, data: bytes, algorithm: str = "SHA-256") -> bytes:
        """Sign data with an RSA private key using PKCS#1 v1.5.

        Args:
            key: A parsed rsa.PrivateKey object.
            data: The data to sign.
            algorithm: The hash algorithm (default: "SHA-256").

        Returns:
            The signature bytes.

        Raises:
            TypeError: If key is not an rsa.PrivateKey instance.
        """
        if not isinstance(key, rsa.PrivateKey):
            raise TypeError(f"Expected rsa.PrivateKey, got {type(key).__name__}")
        return rsa.pkcs1.sign(data, key, algorithm)


class LegacyHashProvider:
    """Hash provider using Python's standard hashlib.

    This implementation uses the standard library hashlib module.
    """

    _sha1_warning_shown = False

    def sha256(self, data: bytes) -> bytes:
        """Compute SHA-256 digest using hashlib.

        Args:
            data: The data to hash.

        Returns:
            The SHA-256 digest.
        """
        return sha256(data).digest()

    def sha1(self, data: bytes) -> bytes:
        """Compute SHA-1 digest using hashlib.

        Args:
            data: The data to hash.

        Returns:
            The SHA-1 digest.

        Note:
            SHA-1 is cryptographically broken. Use only for legacy compatibility.
        """
        if not self.__class__._sha1_warning_shown:
            warnings.warn(
                "SHA-1 is deprecated and should only be used for legacy compatibility",
                DeprecationWarning,
                stacklevel=2,
            )
            self.__class__._sha1_warning_shown = True

        return sha1(data, usedforsecurity=False).digest()


class LegacyProvider:
    """Unified legacy crypto provider using pure Python libraries.

    This provider uses pure Python implementations (pyaes, rsa, pbkdf2) and
    serves as a fallback when neither cryptography nor pycryptodome are available.

    Performance: Slower than native providers (5-20x) but requires no compilation.

    A UserWarning is shown on first use to encourage installing faster alternatives.

    Example:
        >>> from audible.crypto_provider import get_crypto_providers, LegacyProvider
        >>> providers = get_crypto_providers(LegacyProvider)
        >>> providers.provider_name
        'legacy'
    """

    def __init__(self) -> None:
        self._aes = LegacyAESProvider()
        self._pbkdf2 = LegacyPBKDF2Provider()
        self._rsa = LegacyRSAProvider()
        self._hash = LegacyHashProvider()

        # Show warning on initialization
        warnings.warn(
            "Using legacy crypto libraries (pyaes, rsa, pbkdf2). "
            "For better performance, install cryptography or pycryptodome: "
            "pip install audible[cryptography] or pip install audible[pycryptodome]",
            UserWarning,
            stacklevel=4,
        )

    @property
    def aes(self) -> LegacyAESProvider:
        """Get the AES provider."""
        return self._aes

    @property
    def pbkdf2(self) -> LegacyPBKDF2Provider:
        """Get the PBKDF2 provider."""
        return self._pbkdf2

    @property
    def rsa(self) -> LegacyRSAProvider:
        """Get the RSA provider."""
        return self._rsa

    @property
    def hash(self) -> LegacyHashProvider:
        """Get the hash provider."""
        return self._hash

    @property
    def provider_name(self) -> str:
        """Get provider name."""
        return "legacy"


__all__ = [
    "LegacyAESProvider",
    "LegacyHashProvider",
    "LegacyPBKDF2Provider",
    "LegacyProvider",
    "LegacyRSAProvider",
]
