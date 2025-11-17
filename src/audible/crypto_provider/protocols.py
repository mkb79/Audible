"""Protocol definitions for crypto providers.

This module defines the contracts that all crypto provider implementations
must follow. Using Python's Protocol allows for type-safe duck typing and
enables static type checking with mypy.
"""

from collections.abc import Callable
from typing import Any, Protocol, runtime_checkable


@runtime_checkable
class HashAlgorithm(Protocol):
    """Protocol for hash algorithm objects.

    This protocol defines the interface that hash objects must provide.
    Compatible with hashlib hash objects (e.g., hashlib.sha256()).

    Attributes:
        name: The name of the hash algorithm (e.g., 'sha256', 'sha1').
    """

    name: str


@runtime_checkable
class AESProvider(Protocol):
    """Protocol for AES-CBC encryption/decryption operations.

    Implementations must provide AES encryption in CBC mode with configurable
    padding. Both "default" (PKCS7) and "none" (no padding) modes must be
    supported.
    """

    def encrypt(
        self, key: bytes, iv: bytes, data: str, padding: str = "default"
    ) -> bytes:
        """Encrypt data using AES-CBC.

        Args:
            key: The AES encryption key (16, 24, or 32 bytes).
            iv: The initialization vector (16 bytes).
            data: The plaintext data to encrypt.
            padding: Padding mode - "default" for PKCS7, "none" for no padding.

        Returns:
            The encrypted data as bytes.
        """
        ...

    def decrypt(
        self, key: bytes, iv: bytes, encrypted_data: bytes, padding: str = "default"
    ) -> str:
        """Decrypt data using AES-CBC.

        Args:
            key: The AES decryption key (16, 24, or 32 bytes).
            iv: The initialization vector (16 bytes).
            encrypted_data: The ciphertext to decrypt.
            padding: Padding mode - "default" for PKCS7, "none" for no padding.

        Returns:
            The decrypted plaintext as a string.
        """
        ...


@runtime_checkable
class PBKDF2Provider(Protocol):
    """Protocol for PBKDF2 key derivation operations.

    Implementations must provide PBKDF2 (Password-Based Key Derivation
    Function 2) with configurable hash functions and iteration counts.
    """

    def derive_key(
        self,
        password: str,
        salt: bytes,
        iterations: int,
        key_size: int,
        hashmod: Callable[..., "HashAlgorithm"],
    ) -> bytes:
        """Derive a cryptographic key from a password using PBKDF2.

        Args:
            password: The password to derive the key from.
            salt: Random salt for key derivation.
            iterations: Number of iterations (1-65535).
            key_size: Desired key size in bytes.
            hashmod: Hash function factory (e.g., hashlib.sha256).

        Returns:
            The derived key as bytes.
        """
        ...


@runtime_checkable
class RSAProvider(Protocol):
    """Protocol for RSA signing operations.

    Implementations must provide RSA private key loading and PKCS#1 v1.5
    signing with SHA-256. Implementations should cache parsed keys for
    performance.
    """

    def load_private_key(self, pem_data: str) -> Any:
        """Load and cache an RSA private key from PEM format.

        This method should implement caching to avoid re-parsing the same
        key multiple times, as key loading can be expensive.

        Args:
            pem_data: RSA private key in PEM format.

        Returns:
            The loaded RSA private key object.
        """
        ...

    def sign(self, key: Any, data: bytes, algorithm: str = "SHA-256") -> bytes:
        """Sign data with an RSA private key using PKCS#1 v1.5.

        Args:
            key: A parsed RSA private key (from load_private_key).
            data: The data to sign.
            algorithm: The hash algorithm to use. Currently only "SHA-256"
                is supported to match Audible API requirements (SHA256withRSA).

        Returns:
            The RSA signature as bytes.
        """
        ...


@runtime_checkable
class HashProvider(Protocol):
    """Protocol for cryptographic hash operations.

    Implementations must provide SHA-256 and SHA-1 hash functions.
    """

    def sha256(self, data: bytes) -> bytes:
        """Compute SHA-256 digest.

        Args:
            data: The data to hash.

        Returns:
            The SHA-256 hash digest as bytes.
        """
        ...

    def sha1(self, data: bytes) -> bytes:
        """Compute SHA-1 digest.

        Args:
            data: The data to hash.

        Returns:
            The SHA-1 hash digest as bytes.

        Note:
            SHA-1 is considered cryptographically broken and should only be
            used for non-security-critical purposes (e.g., legacy compatibility).
        """
        ...


@runtime_checkable
class CryptoProvider(Protocol):
    """Protocol for complete crypto provider implementations.

    This protocol defines the contract that all crypto providers must follow.
    Providers must implement all four sub-providers (AES, PBKDF2, RSA, Hash)
    to ensure complete cryptographic functionality.

    Custom providers can be created by implementing this protocol and passing
    the provider class to get_crypto_providers().

    Example:
        >>> class MyProvider:  # doctest: +SKIP
        ...     @property
        ...     def aes(self) -> AESProvider:
        ...         return MyAESProvider()
        ...     @property
        ...     def pbkdf2(self) -> PBKDF2Provider:
        ...         return MyPBKDF2Provider()
        ...     @property
        ...     def rsa(self) -> RSAProvider:
        ...         return MyRSAProvider()
        ...     @property
        ...     def hash(self) -> HashProvider:
        ...         return MyHashProvider()
        ...     @property
        ...     def provider_name(self) -> str:
        ...         return "my-custom-provider"
        >>> from audible.crypto_provider import get_crypto_providers  # doctest: +SKIP
        >>> providers = get_crypto_providers(MyProvider)  # doctest: +SKIP
        >>> providers.provider_name  # doctest: +SKIP
        'my-custom-provider'
    """

    @property
    def aes(self) -> AESProvider:
        """Return the AES encryption/decryption provider.

        Returns:
            The AES encryption/decryption provider instance.
        """
        ...

    @property
    def pbkdf2(self) -> PBKDF2Provider:
        """Return the PBKDF2 key derivation provider.

        Returns:
            The PBKDF2 key derivation provider instance.
        """
        ...

    @property
    def rsa(self) -> RSAProvider:
        """Return the RSA signing provider.

        Returns:
            The RSA signing provider instance.
        """
        ...

    @property
    def hash(self) -> HashProvider:
        """Return the cryptographic hash provider.

        Returns:
            The cryptographic hash provider instance.
        """
        ...

    @property
    def provider_name(self) -> str:
        """Return the human-readable provider name.

        Returns:
            The human-readable provider name (e.g., 'cryptography',
            'pycryptodome', 'legacy').
        """
        ...


__all__ = [
    "AESProvider",
    "CryptoProvider",
    "HashAlgorithm",
    "HashProvider",
    "PBKDF2Provider",
    "RSAProvider",
]
