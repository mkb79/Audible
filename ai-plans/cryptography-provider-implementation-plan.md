# Cryptography Provider Implementation Plan

**Generated:** 2025-10-28
**Last Updated:** 2025-10-29
**Target Branch:** feat/optional-pycryptodome-crypto-backend
**Goal:** Add `cryptography` library as additional crypto provider with type-safe class-based API

## Progress Tracker

- ✅ **1. CryptoProvider Protocol** - COMPLETED (`src/audible/crypto/protocols.py:136`)
- ✅ **2. Restructure Existing Providers** - COMPLETED (`src/audible/crypto/pycryptodome_provider.py:283`, `src/audible/crypto/legacy_provider.py:210`)
- ✅ **3. CryptographyProvider Implementation** - COMPLETED (`src/audible/crypto/cryptography_provider.py:301`)
- ✅ **4. Registry Updates** - COMPLETED (`src/audible/crypto/registry.py:1`)
- ✅ **5. API Exports** - COMPLETED (`src/audible/crypto/__init__.py:1`)
- ✅ **6. Dependencies Configuration** - COMPLETED (`pyproject.toml:35`, `noxfile.py:157`)
- ✅ **7. Provider Propagation** - COMPLETED (registry overrides, AESCipher & Authenticator injection, voucher flow)
- ⏳ **8. Documentation Updates** - PENDING
- ⏳ **9. Test Suite** - PENDING
- ⏳ **10. Manual Integration Tests** - PENDING

## Architecture Overview

### Design Goals

- Add `cryptography` library as optional high-performance crypto backend
- Use type-safe class-based API (no string-based provider selection)
- Enable custom user-provided crypto providers
- Auto-detection priority: `cryptography` → `pycryptodome` → `legacy`
- Maintain backward compatibility with existing code

### API Design

**Current API (stays compatible):**

```python
from audible.crypto import get_crypto_providers

providers = get_crypto_providers()  # Auto-detect
```

**New API (type-safe class-based):**

```python
from audible.crypto import (
    get_crypto_providers,
    CryptographyProvider,
    PycryptodomeProvider,
    LegacyProvider
)

# Auto-detect (default)
providers = get_crypto_providers()

# Explicit provider selection via class
providers = get_crypto_providers(CryptographyProvider)
providers = get_crypto_providers(PycryptodomeProvider)
providers = get_crypto_providers(LegacyProvider)

# Custom provider
class MyCustomProvider:
    @property
    def aes(self) -> AESProvider: ...
    @property
    def pbkdf2(self) -> PBKDF2Provider: ...
    @property
    def rsa(self) -> RSAProvider: ...
    @property
    def hash(self) -> HashProvider: ...
    @property
    def provider_name(self) -> str: ...

providers = get_crypto_providers(MyCustomProvider)
```

### Provider Priority (Auto-Detection)

1. **cryptography** - Modern, actively maintained, Rust-based (fastest)
2. **pycryptodome** - C-based, high performance
3. **legacy** - Pure Python (pyaes, rsa, pbkdf2)

### Dependencies Configuration (Option C)

```toml
[project.optional-dependencies]
cryptography = ["cryptography (>=42.0.0)"]
pycryptodome = ["pycryptodome (>=3.20.0)"]
```

**Installation scenarios:**

- `pip install audible[cryptography]` → only cryptography
- `pip install audible[pycryptodome]` → only pycryptodome
- `pip install audible[cryptography,pycryptodome]` → both (best for testing)

---

## 1. Create CryptoProvider Protocol

**Priority:** High
**Location:** `src/audible/crypto/protocols.py`
**Status:** ⏳ PENDING

### Implementation Steps

#### Step 1.1: Add CryptoProvider Protocol

Add to `protocols.py` after existing protocol definitions:

```python
@runtime_checkable
class CryptoProvider(Protocol):
    """Protocol for complete crypto provider implementations.

    This protocol defines the contract that all crypto providers must follow.
    Providers must implement all four sub-providers (AES, PBKDF2, RSA, Hash)
    to ensure complete cryptographic functionality.

    Custom providers can be created by implementing this protocol and passing
    the provider class to get_crypto_providers().

    Example:
        >>> class MyProvider:
        ...     @property
        ...     def aes(self) -> AESProvider: ...
        ...     @property
        ...     def pbkdf2(self) -> PBKDF2Provider: ...
        ...     @property
        ...     def rsa(self) -> RSAProvider: ...
        ...     @property
        ...     def hash(self) -> HashProvider: ...
        ...     @property
        ...     def provider_name(self) -> str:
        ...         return "my-custom-provider"
        >>> from audible.crypto import get_crypto_providers
        >>> providers = get_crypto_providers(MyProvider)
    """

    @property
    def aes(self) -> AESProvider:
        """Get the AES encryption/decryption provider.

        Returns:
            An AESProvider instance for AES-CBC operations.
        """
        ...

    @property
    def pbkdf2(self) -> PBKDF2Provider:
        """Get the PBKDF2 key derivation provider.

        Returns:
            A PBKDF2Provider instance for password-based key derivation.
        """
        ...

    @property
    def rsa(self) -> RSAProvider:
        """Get the RSA signing provider.

        Returns:
            An RSAProvider instance for RSA-PKCS#1 v1.5 signing.
        """
        ...

    @property
    def hash(self) -> HashProvider:
        """Get the cryptographic hash provider.

        Returns:
            A HashProvider instance for SHA-256 and SHA-1 operations.
        """
        ...

    @property
    def provider_name(self) -> str:
        """Get the human-readable provider name.

        Returns:
            Provider identifier (e.g., "cryptography", "pycryptodome", "legacy").
        """
        ...
```

#### Step 1.2: Update **all** exports

Update `protocols.py` to export the new protocol:

```python
__all__ = [
    "AESProvider",
    "PBKDF2Provider",
    "RSAProvider",
    "HashProvider",
    "CryptoProvider",  # Add this
]
```

#### Step 1.3: Verification

Run type checking:

```bash
uv run nox -s mypy
```

Expected: No type errors, new protocol recognized.

---

## 2. Restructure Existing Providers as Classes

**Priority:** High
**Locations:**

- `src/audible/crypto/pycryptodome_provider.py`
- `src/audible/crypto/legacy_provider.py`
  **Status:** ⏳ PENDING

### Implementation Steps

#### Step 2.1: Restructure PycryptodomeProvider

**Current structure:** Individual provider classes (PycryptodomeAESProvider, etc.)
**New structure:** Unified PycryptodomeProvider class implementing CryptoProvider protocol

Add to end of `pycryptodome_provider.py`:

```python
class PycryptodomeProvider:
    """Unified pycryptodome crypto provider.

    This provider implements all cryptographic operations using the pycryptodome
    library, which provides high-performance C-based implementations.

    Performance characteristics:
    - 5-10x faster AES operations vs pure Python
    - 10-20x faster RSA operations vs pure Python
    - 3-5x faster PBKDF2 key derivation vs pure Python
    - 5-10x faster hashing operations vs pure Python

    Example:
        >>> from audible.crypto import get_crypto_providers, PycryptodomeProvider
        >>> providers = get_crypto_providers(PycryptodomeProvider)
        >>> providers.provider_name
        'pycryptodome'
    """

    def __init__(self) -> None:
        """Initialize pycryptodome provider."""
        if not PYCRYPTODOME_AVAILABLE:
            raise ImportError(
                "pycryptodome is not installed. "
                "Install with: pip install audible[pycryptodome]"
            )

        self._aes = PycryptodomeAESProvider()
        self._pbkdf2 = PycryptodomePBKDF2Provider()
        self._rsa = PycryptodomeRSAProvider()
        self._hash = PycryptodomeHashProvider()

    @property
    def aes(self) -> PycryptodomeAESProvider:
        """Get the AES provider."""
        return self._aes

    @property
    def pbkdf2(self) -> PycryptodomePBKDF2Provider:
        """Get the PBKDF2 provider."""
        return self._pbkdf2

    @property
    def rsa(self) -> PycryptodomeRSAProvider:
        """Get the RSA provider."""
        return self._rsa

    @property
    def hash(self) -> PycryptodomeHashProvider:
        """Get the hash provider."""
        return self._hash

    @property
    def provider_name(self) -> str:
        """Get provider name."""
        return "pycryptodome"
```

Update `__all__` in `pycryptodome_provider.py`:

```python
__all__ = [
    "PYCRYPTODOME_AVAILABLE",
    "PycryptodomeAESProvider",
    "PycryptodomePBKDF2Provider",
    "PycryptodomeRSAProvider",
    "PycryptodomeHashProvider",
    "PycryptodomeProvider",  # Add this
]
```

#### Step 2.2: Restructure LegacyProvider

Add to end of `legacy_provider.py`:

```python
class LegacyProvider:
    """Unified legacy crypto provider using pure Python libraries.

    This provider uses pure Python implementations (pyaes, rsa, pbkdf2) and
    serves as a fallback when neither cryptography nor pycryptodome are available.

    Performance: Slower than native providers (5-20x) but requires no compilation.

    A UserWarning is shown on first use to encourage installing faster alternatives.

    Example:
        >>> from audible.crypto import get_crypto_providers, LegacyProvider
        >>> providers = get_crypto_providers(LegacyProvider)
        >>> providers.provider_name
        'legacy'
    """

    def __init__(self) -> None:
        """Initialize legacy provider."""
        self._aes = LegacyAESProvider()
        self._pbkdf2 = LegacyPBKDF2Provider()
        self._rsa = LegacyRSAProvider()
        self._hash = LegacyHashProvider()

        # Show warning on initialization (not on import)
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
```

Update `__all__` in `legacy_provider.py`:

```python
__all__ = [
    "LegacyAESProvider",
    "LegacyPBKDF2Provider",
    "LegacyRSAProvider",
    "LegacyHashProvider",
    "LegacyProvider",  # Add this
]
```

#### Step 2.3: Verification

Run tests to ensure existing functionality still works:

```bash
uv run nox -s tests
uv run nox -s mypy
```

Expected: All existing tests pass, no type errors.

---

## 3. Implement CryptographyProvider

**Priority:** High
**Location:** `src/audible/crypto/cryptography_provider.py` (NEW FILE)
**Status:** ⏳ PENDING

### Implementation Steps

#### Step 3.1: Create cryptography_provider.py

Create new file with complete implementation:

```python
"""Cryptography provider using the cryptography library.

This module implements the crypto protocols using the cryptography library,
which provides modern, Rust-accelerated cryptographic operations.

The cryptography library is the recommended choice for new projects due to:
- Active maintenance and security updates
- Modern API design
- Rust-based performance optimizations
- Comprehensive cryptographic primitive support

This is the preferred provider when available, selected first during auto-detection.
"""

from __future__ import annotations

import logging
from collections.abc import Callable
from functools import lru_cache
from typing import Any


# Optional import - only available if cryptography is installed
try:
    from cryptography.hazmat.primitives import hashes, serialization
    from cryptography.hazmat.primitives.asymmetric import padding as asym_padding
    from cryptography.hazmat.primitives.asymmetric import rsa
    from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
    from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
    from cryptography.hazmat.primitives import padding as sym_padding

    CRYPTOGRAPHY_AVAILABLE = True
except ImportError:
    CRYPTOGRAPHY_AVAILABLE = False


logger = logging.getLogger("audible.crypto.cryptography")


# Module-level cached function for RSA key loading
@lru_cache(maxsize=8)
def _load_rsa_private_key_cryptography(pem_data: str) -> Any:
    """Load and cache an RSA private key from PEM using cryptography.

    This function caches up to 8 different keys. For the same PEM string,
    the cached key object will be returned instead of re-parsing.

    Args:
        pem_data: RSA private key in PEM format.

    Returns:
        Parsed RSA private key object.

    Raises:
        ValueError: If PEM data is invalid or not an RSA key.
    """
    try:
        key = serialization.load_pem_private_key(
            pem_data.encode("utf-8"),
            password=None
        )
        if not isinstance(key, rsa.RSAPrivateKey):
            raise ValueError("Key is not an RSA private key")
        return key
    except Exception as e:
        logger.error("Failed to load RSA private key: %s", e)
        raise


class CryptographyAESProvider:
    """AES provider using cryptography library.

    Implements AES-CBC encryption/decryption with PKCS7 padding support.
    Uses Rust-accelerated primitives from the cryptography library.
    """

    def encrypt(
        self, key: bytes, iv: bytes, data: str, padding: str = "default"
    ) -> bytes:
        """Encrypt data using AES-CBC.

        Args:
            key: AES key (16, 24, or 32 bytes for AES-128/192/256).
            iv: Initialization vector (16 bytes).
            data: Plaintext string to encrypt.
            padding: "default" for PKCS7 padding, "none" for no padding.

        Returns:
            Encrypted ciphertext as bytes.

        Raises:
            ValueError: If key/IV sizes are invalid or padding mode unknown.
        """
        if len(iv) != 16:
            raise ValueError(f"IV must be 16 bytes, got {len(iv)}")
        if len(key) not in (16, 24, 32):
            raise ValueError(f"Key must be 16, 24, or 32 bytes, got {len(key)}")

        plaintext = data.encode("utf-8")

        # Apply padding if requested
        if padding == "default":
            padder = sym_padding.PKCS7(128).padder()
            plaintext = padder.update(plaintext) + padder.finalize()
        elif padding != "none":
            raise ValueError(f"Unknown padding mode: {padding}")

        cipher = Cipher(algorithms.AES(key), modes.CBC(iv))
        encryptor = cipher.encryptor()
        ciphertext = encryptor.update(plaintext) + encryptor.finalize()

        return ciphertext

    def decrypt(
        self, key: bytes, iv: bytes, encrypted_data: bytes, padding: str = "default"
    ) -> str:
        """Decrypt data using AES-CBC.

        Args:
            key: AES key (16, 24, or 32 bytes).
            iv: Initialization vector (16 bytes).
            encrypted_data: Ciphertext to decrypt.
            padding: "default" for PKCS7 padding, "none" for no padding.

        Returns:
            Decrypted plaintext as string.

        Raises:
            ValueError: If key/IV sizes invalid, padding incorrect, or decryption fails.
        """
        if len(iv) != 16:
            raise ValueError(f"IV must be 16 bytes, got {len(iv)}")
        if len(key) not in (16, 24, 32):
            raise ValueError(f"Key must be 16, 24, or 32 bytes, got {len(key)}")

        cipher = Cipher(algorithms.AES(key), modes.CBC(iv))
        decryptor = cipher.decryptor()
        plaintext = decryptor.update(encrypted_data) + decryptor.finalize()

        # Remove padding if requested
        if padding == "default":
            try:
                unpadder = sym_padding.PKCS7(128).unpadder()
                plaintext = unpadder.update(plaintext) + unpadder.finalize()
            except ValueError as e:
                raise ValueError(f"Invalid padding: {e}") from e
        elif padding != "none":
            raise ValueError(f"Unknown padding mode: {padding}")

        return plaintext.decode("utf-8")


class CryptographyPBKDF2Provider:
    """PBKDF2 provider using cryptography library.

    Implements PBKDF2 key derivation with configurable hash algorithms.
    Uses Rust-accelerated KDF from the cryptography library.
    """

    def derive_key(
        self,
        password: str,
        salt: bytes,
        iterations: int,
        key_size: int,
        hashmod: Callable[[], Any],
    ) -> bytes:
        """Derive a key from password using PBKDF2.

        Args:
            password: Password string.
            salt: Random salt bytes.
            iterations: Number of PBKDF2 iterations (1-65535).
            key_size: Desired key length in bytes.
            hashmod: Hash function factory (e.g., hashlib.sha256).

        Returns:
            Derived key bytes.

        Raises:
            ValueError: If iterations out of range or parameters invalid.
        """
        if not (1 <= iterations <= 65535):
            raise ValueError(f"Iterations must be 1-65535, got {iterations}")

        # Map hashlib hash functions to cryptography hash algorithms
        hash_name = hashmod().name
        hash_algo_map = {
            "sha256": hashes.SHA256(),
            "sha1": hashes.SHA1(),
            "sha224": hashes.SHA224(),
            "sha384": hashes.SHA384(),
            "sha512": hashes.SHA512(),
            "md5": hashes.MD5(),
        }

        hash_algorithm = hash_algo_map.get(hash_name)
        if hash_algorithm is None:
            raise ValueError(f"Unsupported hash algorithm: {hash_name}")

        kdf = PBKDF2HMAC(
            algorithm=hash_algorithm,
            length=key_size,
            salt=salt,
            iterations=iterations,
        )

        return kdf.derive(password.encode("utf-8"))


class CryptographyRSAProvider:
    """RSA provider using cryptography library.

    Implements RSA private key loading and PKCS#1 v1.5 signing with SHA-256.
    Uses LRU caching for parsed keys to optimize performance.
    """

    def load_private_key(self, pem_data: str) -> Any:
        """Load and cache an RSA private key from PEM format.

        Uses module-level LRU cache to avoid re-parsing the same key.

        Args:
            pem_data: RSA private key in PEM format.

        Returns:
            Parsed RSA private key object.

        Raises:
            ValueError: If PEM is invalid or not an RSA key.
        """
        return _load_rsa_private_key_cryptography(pem_data)

    def sign(self, key: Any, data: bytes, algorithm: str = "SHA-256") -> bytes:
        """Sign data with RSA private key using PKCS#1 v1.5.

        Args:
            key: RSA private key from load_private_key().
            data: Data to sign.
            algorithm: Hash algorithm, only "SHA-256" supported (Audible API requirement).

        Returns:
            Signature bytes.

        Raises:
            ValueError: If algorithm is not "SHA-256" or key is invalid.
        """
        if algorithm != "SHA-256":
            raise ValueError(f"Only SHA-256 supported, got {algorithm}")

        if not isinstance(key, rsa.RSAPrivateKey):
            raise ValueError("Key must be an RSA private key")

        signature = key.sign(
            data,
            asym_padding.PKCS1v15(),
            hashes.SHA256()
        )

        return signature


class CryptographyHashProvider:
    """Hash provider using cryptography library.

    Implements SHA-256 and SHA-1 hash functions.
    Uses Rust-accelerated hash primitives.
    """

    def sha256(self, data: bytes) -> bytes:
        """Compute SHA-256 hash.

        Args:
            data: Data to hash.

        Returns:
            SHA-256 digest bytes (32 bytes).
        """
        from cryptography.hazmat.backends import default_backend
        digest = hashes.Hash(hashes.SHA256(), backend=default_backend())
        digest.update(data)
        return digest.finalize()

    def sha1(self, data: bytes) -> bytes:
        """Compute SHA-1 hash.

        Args:
            data: Data to hash.

        Returns:
            SHA-1 digest bytes (20 bytes).

        Note:
            SHA-1 is cryptographically broken. Only use for legacy compatibility.
        """
        from cryptography.hazmat.backends import default_backend
        digest = hashes.Hash(hashes.SHA1(), backend=default_backend())
        digest.update(data)
        return digest.finalize()


class CryptographyProvider:
    """Unified cryptography crypto provider.

    This provider implements all cryptographic operations using the cryptography
    library, which provides modern, Rust-accelerated implementations.

    Performance characteristics:
    - Comparable or better than pycryptodome
    - Modern API and active maintenance
    - Preferred choice for new installations

    Example:
        >>> from audible.crypto import get_crypto_providers, CryptographyProvider
        >>> providers = get_crypto_providers(CryptographyProvider)
        >>> providers.provider_name
        'cryptography'
    """

    def __init__(self) -> None:
        """Initialize cryptography provider.

        Raises:
            ImportError: If cryptography library is not installed.
        """
        if not CRYPTOGRAPHY_AVAILABLE:
            raise ImportError(
                "cryptography is not installed. "
                "Install with: pip install audible[cryptography]"
            )

        self._aes = CryptographyAESProvider()
        self._pbkdf2 = CryptographyPBKDF2Provider()
        self._rsa = CryptographyRSAProvider()
        self._hash = CryptographyHashProvider()

    @property
    def aes(self) -> CryptographyAESProvider:
        """Get the AES provider."""
        return self._aes

    @property
    def pbkdf2(self) -> CryptographyPBKDF2Provider:
        """Get the PBKDF2 provider."""
        return self._pbkdf2

    @property
    def rsa(self) -> CryptographyRSAProvider:
        """Get the RSA provider."""
        return self._rsa

    @property
    def hash(self) -> CryptographyHashProvider:
        """Get the hash provider."""
        return self._hash

    @property
    def provider_name(self) -> str:
        """Get provider name."""
        return "cryptography"


__all__ = [
    "CRYPTOGRAPHY_AVAILABLE",
    "CryptographyAESProvider",
    "CryptographyPBKDF2Provider",
    "CryptographyRSAProvider",
    "CryptographyHashProvider",
    "CryptographyProvider",
]
```

#### Step 3.2: Verification

Run type checking and basic import test:

```bash
uv run nox -s mypy
python -c "from audible.crypto.cryptography_provider import CryptographyProvider; print('Import OK')"
```

Expected: No type errors, import succeeds (if cryptography installed).

---

## 4. Update Registry for Class-Based API

**Priority:** High
**Location:** `src/audible/crypto/registry.py`
**Status:** ⏳ PENDING

### Implementation Steps

#### Step 4.1: Update Imports

Add at top of `registry.py`:

```python
from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .protocols import CryptoProvider
```

#### Step 4.2: Update CryptoProviderRegistry.**init**

Modify `__init__` to accept optional provider class:

```python
def __init__(self, provider_class: type[CryptoProvider] | None = None) -> None:
    """Initialize the registry.

    Args:
        provider_class: Optional provider class to use instead of auto-detection.
            Can be CryptographyProvider, PycryptodomeProvider, LegacyProvider,
            or any custom class implementing the CryptoProvider protocol.
    """
    if self._initialized:
        return

    self._provider_class = provider_class
    self._provider_instance: CryptoProvider | None = None
    self._initialized = True
```

#### Step 4.3: Update \_select_provider_class

Replace `_select_provider` method with `_select_provider_class`:

```python
def _select_provider_class(self) -> type[CryptoProvider]:
    """Auto-detect and select the best available crypto provider class.

    Returns:
        Provider class (CryptographyProvider, PycryptodomeProvider, or LegacyProvider).
    """
    # Try cryptography first (preferred)
    try:
        from .cryptography_provider import CRYPTOGRAPHY_AVAILABLE  # noqa: PLC0415

        if CRYPTOGRAPHY_AVAILABLE:
            from .cryptography_provider import CryptographyProvider  # noqa: PLC0415
            logger.info("Using cryptography crypto provider (Rust-accelerated)")
            return CryptographyProvider
    except ImportError:
        pass

    # Try pycryptodome second
    try:
        from .pycryptodome_provider import PYCRYPTODOME_AVAILABLE  # noqa: PLC0415

        if PYCRYPTODOME_AVAILABLE:
            from .pycryptodome_provider import PycryptodomeProvider  # noqa: PLC0415
            logger.info("Using pycryptodome crypto provider (C-based)")
            return PycryptodomeProvider
    except ImportError:
        pass

    # Fallback to legacy (always available)
    from .legacy_provider import LegacyProvider  # noqa: PLC0415
    logger.info("Using legacy crypto provider (pure Python)")
    return LegacyProvider
```

#### Step 4.4: Replace \_initialize_providers

Replace the old method with new class-based initialization:

```python
def _initialize_provider(self) -> None:
    """Lazy initialization of crypto provider.

    This method is called automatically on first provider access.
    """
    if self._provider_instance is not None:
        return  # Already initialized

    # Use explicitly provided class or auto-detect
    if self._provider_class is not None:
        provider_class = self._provider_class
    else:
        provider_class = self._select_provider_class()

    # Instantiate the provider
    try:
        self._provider_instance = provider_class()
        logger.debug("Initialized %s crypto provider", self._provider_instance.provider_name)
    except ImportError as e:
        raise ImportError(
            f"Failed to initialize {provider_class.__name__}: {e}. "
            f"Install the required library or let the system auto-detect."
        ) from e
```

#### Step 4.5: Update Property Methods

Replace all property methods to delegate to provider instance:

```python
@property
def aes(self) -> "AESProvider":
    """Get the AES encryption/decryption provider."""
    self._initialize_provider()
    if self._provider_instance is None:
        raise RuntimeError("Provider initialization failed")
    return self._provider_instance.aes

@property
def pbkdf2(self) -> "PBKDF2Provider":
    """Get the PBKDF2 key derivation provider."""
    self._initialize_provider()
    if self._provider_instance is None:
        raise RuntimeError("Provider initialization failed")
    return self._provider_instance.pbkdf2

@property
def rsa(self) -> "RSAProvider":
    """Get the RSA signing provider."""
    self._initialize_provider()
    if self._provider_instance is None:
        raise RuntimeError("Provider initialization failed")
    return self._provider_instance.rsa

@property
def hash(self) -> "HashProvider":
    """Get the cryptographic hash provider."""
    self._initialize_provider()
    if self._provider_instance is None:
        raise RuntimeError("Provider initialization failed")
    return self._provider_instance.hash

@property
def provider_name(self) -> str:
    """Get the name of the active crypto provider."""
    self._initialize_provider()
    if self._provider_instance is None:
        raise RuntimeError("Provider initialization failed")
    return self._provider_instance.provider_name
```

#### Step 4.6: Update get_crypto_providers Function

Update the global function to support provider class parameter:

```python
def get_crypto_providers(
    provider: type[CryptoProvider] | None = None
) -> CryptoProvider:
    """Get the crypto provider.

    This is the main entry point for accessing crypto operations.

    Args:
        provider: Optional provider class to use. Can be:
            - None: Auto-detect best available provider (default)
            - CryptographyProvider: Force cryptography library
            - PycryptodomeProvider: Force pycryptodome library
            - LegacyProvider: Force legacy pure-Python libraries
            - Custom class implementing CryptoProvider protocol

    Returns:
        A CryptoProvider instance.

    Raises:
        ImportError: If specified provider is unavailable.

    Example:
        >>> from audible.crypto import get_crypto_providers
        >>> providers = get_crypto_providers()  # Auto-detect
        >>> providers.provider_name in {"cryptography", "pycryptodome", "legacy"}
        True

        >>> from audible.crypto import CryptographyProvider
        >>> providers = get_crypto_providers(CryptographyProvider)
        >>> providers.provider_name
        'cryptography'
    """
    if provider is None:
        # Use global singleton for auto-detection
        return _registry

    # Create new instance with specified provider
    return CryptoProviderRegistry(provider_class=provider)
```

#### Step 4.7: Update Module Docstring

Update the module docstring at the top of `registry.py`:

```python
"""Provider registry for crypto backend selection.

This module implements a registry that automatically detects and selects the best
available crypto provider at runtime, with support for explicit provider selection.

Auto-detection priority:
1. cryptography (Rust-accelerated, modern API)
2. pycryptodome (C-based, high performance)
3. legacy (pure Python fallback)

The registry supports both automatic detection and explicit provider selection via
type-safe class-based API. Custom providers can be created by implementing the
CryptoProvider protocol.

Example:
    >>> from audible.crypto import get_crypto_providers
    >>> providers = get_crypto_providers()  # Auto-detect
    >>> providers.provider_name
    'cryptography'

    >>> from audible.crypto import PycryptodomeProvider
    >>> providers = get_crypto_providers(PycryptodomeProvider)
    >>> providers.provider_name
    'pycryptodome'
"""
```

#### Step 4.8: Verification

Run comprehensive tests:

```bash
uv run nox -s mypy
uv run nox -s tests -- tests/test_crypto.py
```

Expected: Type checking passes, existing crypto tests pass.

---

## 5. Update API Exports

**Priority:** Medium
**Location:** `src/audible/crypto/__init__.py`
**Status:** ⏳ PENDING

### Implementation Steps

#### Step 5.1: Update crypto/**init**.py

Replace contents with:

```python
"""Crypto abstraction layer with support for multiple backends.

This module provides a clean abstraction layer for cryptographic operations,
supporting multiple backend libraries: cryptography, pycryptodome, and legacy
pure-Python implementations.

The provider is automatically selected at runtime based on availability:
1. cryptography (preferred - Rust-accelerated)
2. pycryptodome (C-based)
3. legacy (pure Python fallback)

Users can explicitly select a provider using the class-based API.

Example:
    >>> from audible.crypto import get_crypto_providers
    >>> providers = get_crypto_providers()  # Auto-detect
    >>> key = bytes([0]) * 16
    >>> iv = bytes([1]) * 16
    >>> ciphertext = providers.aes.encrypt(key, iv, "hello")
    >>> providers.aes.decrypt(key, iv, ciphertext)
    'hello'

    >>> from audible.crypto import CryptographyProvider
    >>> providers = get_crypto_providers(CryptographyProvider)
    >>> providers.provider_name
    'cryptography'
"""

from .registry import get_crypto_providers

# Import provider classes for type-safe API
from .cryptography_provider import CryptographyProvider
from .pycryptodome_provider import PycryptodomeProvider
from .legacy_provider import LegacyProvider


__all__ = [
    "get_crypto_providers",
    "CryptographyProvider",
    "PycryptodomeProvider",
    "LegacyProvider",
]
```

#### Step 5.2: Verification

Test imports and API:

```bash
python -c "from audible.crypto import get_crypto_providers, CryptographyProvider, PycryptodomeProvider, LegacyProvider; print('All imports OK')"
uv run nox -s mypy
```

Expected: Clean imports, no type errors.

---

## 6. Update Dependencies Configuration

**Priority:** Medium
**Locations:** `pyproject.toml`, `noxfile.py`
**Status:** ⏳ PENDING

### Implementation Steps

#### Step 6.1: Update pyproject.toml

Replace the `[project.optional-dependencies]` section:

```toml
[project.optional-dependencies]
cryptography = [
    "cryptography (>=42.0.0)",
]
pycryptodome = [
    "pycryptodome (>=3.20.0)",
]
```

Note: Remove the old `crypto` meta-extra (Option C - users can install both with comma-separated syntax).

#### Step 6.2: Update noxfile.py

Update `uv_extras` in two locations:

**Line 168 (tests session):**

```python
@session(python=PYTHON_VERSIONS, uv_groups=[TESTS_GROUP], uv_extras=["cryptography", "pycryptodome"])
def tests(s: nox.Session) -> None:
```

**Line 197 (typeguard session):**

```python
@session(
    python=DEFAULT_PYTHON_VERSION, uv_groups=[TYPEGUARD_GROUP], uv_extras=["cryptography", "pycryptodome"]
)
def typeguard(s: nox.Session) -> None:
```

#### Step 6.3: Verification

Test dependency resolution:

```bash
uv sync --extra cryptography
uv sync --extra pycryptodome
uv sync --extra cryptography --extra pycryptodome
uv run nox -s tests
```

Expected: Dependencies install correctly, tests pass with both providers.

---

## 7. Provider Propagation (Option A - Hybrid Approach)

**Priority:** High
**Status:** ⏳ PENDING

### Objectives

- Allow a global default provider override via `set_default_crypto_provider()` in `src/audible/crypto/registry.py`.
- Support per-instance provider injection in `AESCipher` (`src/audible/aescipher.py:38`, `src/audible/aescipher.py:400`) and `Authenticator` (`src/audible/auth.py:208`, `src/audible/auth.py:561`).
- Ensure module-level helpers respect overrides while keeping backward compatibility.
- Document the new configuration flow and add regression tests.

### Step 7.1: Registry Override API

Add global override handling in `src/audible/crypto/registry.py`:

```python
_default_provider_override: type[CryptoProvider] | None = None

def set_default_crypto_provider(
    provider: type[CryptoProvider] | None = None,
) -> None:
    """Set or reset the global default crypto provider.

    Args:
        provider: Provider class to enforce, or None to restore auto-detection.
    """
    global _default_provider_override, _auto_detect_instance
    _default_provider_override = provider
    _auto_detect_instance = None  # reset cached auto-detected instance
```

Update `get_crypto_providers()` to prioritise explicit `provider`, then the global override, then the cached auto-detected instance. Keep error messages aligned with existing style.

### Step 7.2: AESCipher Provider Injection

- Add optional `crypto_provider: type[CryptoProvider] | None` parameter to `AESCipher.__init__`.
- Store it on the instance and introduce a `_get_crypto()` helper returning `get_crypto_providers(self._crypto_provider)`.
- Update helper functions (`aes_cbc_encrypt`, `aes_cbc_decrypt`, `derive_from_pbkdf2`, etc.) to call `self._get_crypto()` when running inside class context, or accept an optional override parameter for standalone helpers as needed.
- Ensure voucher helpers (`_decrypt_voucher` at `src/audible/aescipher.py:390` and `decrypt_voucher_from_licenserequest` at `src/audible/aescipher.py:420`) accept the injected provider and forward it when delegating.
- Document new argument in class docstring and public API docs.

### Step 7.3: Authenticator Provider Injection

- Add optional `crypto_provider` parameter to factory constructors and `Authenticator` itself.
- Thread the parameter through request-signing logic (`_sign_request`, `_decrypt_credentials`, etc.) by using a `_get_crypto()` helper mirroring the `AESCipher` pattern.
- Ensure existing call sites (fixtures, tests, examples) continue to work without changes.

### Step 7.4: Verification

- Unit tests covering:
  - Global override (`set_default_crypto_provider`) changes all subsequent calls.
  - Per-instance overrides on `AESCipher`/`Authenticator`, including voucher decryption helpers.
  - Resetting to `None` falls back to auto-detection.
- Documentation updates (see Section 8).
- Run `uv run nox --session=tests` and `uv run nox --session=typeguard` after implementation.

### Status

- ✅ Registry override API implemented (`src/audible/crypto/registry.py`) with instance-based override caching
- ✅ AESCipher supports provider injection & voucher helpers updated (`src/audible/aescipher.py`)
- ✅ Authenticator constructors/signing flow honour overrides (`src/audible/auth.py`) using direct registry lookups

### Follow-up

- Document API changes (Section 8)
- Expand tests per Section 9

---

## 8. Update Documentation

**Priority:** High
**Locations:** `README.md`, `docs/source/intro/install.rst`, `CLAUDE.md`
**Status:** ⏳ PENDING

### Implementation Steps

#### Step 8.1: Update README.md

Replace the crypto installation section (lines 33-67) with:

````markdown
### Recommended: With Performance Optimizations

For significantly better performance (5-100x faster cryptographic operations), install with optional high-performance crypto backends:

**Option 1: cryptography (Recommended)**

Modern, actively maintained, Rust-accelerated library:

```bash
pip install audible[cryptography]
```
````

**Option 2: pycryptodome**

Mature, C-based library:

```bash
pip install audible[pycryptodome]
```

**Option 3: Both (Best for development/testing)**

Install both libraries for maximum flexibility:

```bash
pip install audible[cryptography,pycryptodome]
```

**Using uv:**

```bash
# With cryptography
uv pip install audible[cryptography]

# With pycryptodome
uv pip install audible[pycryptodome]

# With both
uv pip install audible[cryptography,pycryptodome]

# Or run with extras (in project context)
uv run --extra cryptography your_script.py
```

The library automatically selects the best available provider:

1. **cryptography** (preferred) - Rust-accelerated, modern API
2. **pycryptodome** - C-based, high performance
3. **legacy** - Pure Python fallback (pyaes, rsa, pbkdf2)

Performance improvements with optimized backends:

- **5-10x faster** AES encryption/decryption
- **10-20x faster** RSA operations
- **3-5x faster** key derivation (PBKDF2)
- **5-10x faster** hashing (SHA-256, SHA-1)

**Explicit Provider Selection:**

```python
from audible.crypto import get_crypto_providers, CryptographyProvider

# Force specific provider
providers = get_crypto_providers(CryptographyProvider)
```

````

#### Step 8.2: Update docs/source/intro/install.rst

Replace the "Optional Dependencies" section (starting around line 19):

```rst
Optional Dependencies
=====================

For significantly improved performance, you can optionally install high-performance
cryptographic backends:

* **cryptography** - Modern, Rust-accelerated library (recommended)
* **pycryptodome** - Mature, C-based library

The library automatically detects and uses the best available backend, with priority:

1. ``cryptography`` (preferred)
2. ``pycryptodome``
3. Legacy pure-Python implementations (``pyaes``, ``rsa``, ``pbkdf2``)

Performance Improvements
------------------------

Installing ``cryptography`` or ``pycryptodome`` provides:

* **5-10x faster** AES encryption/decryption
* **10-20x faster** RSA signing operations
* **3-5x faster** PBKDF2 key derivation
* **5-10x faster** SHA-256 and SHA-1 hashing

This is especially beneficial for applications that:

* Make many API requests (RSA signing on each request)
* Handle authentication frequently (PBKDF2 key derivation)
* Encrypt/decrypt large amounts of data

Installation
============

Standard Installation
---------------------

The easiest way to install the latest version from PyPI is by using pip::

    pip install audible

Using uv (faster alternative to pip)::

    uv pip install audible

Recommended: With Performance Optimizations
--------------------------------------------

**Option 1: cryptography (Recommended)**

Install with the modern Rust-accelerated backend::

    pip install audible[cryptography]

Using uv::

    uv pip install audible[cryptography]

**Option 2: pycryptodome**

Install with the mature C-based backend::

    pip install audible[pycryptodome]

Using uv::

    uv pip install audible[pycryptodome]

**Option 3: Both**

Install both backends for maximum flexibility::

    pip install audible[cryptography,pycryptodome]

Using uv::

    uv pip install audible[cryptography,pycryptodome]

In a project context, run with extras::

    uv run --extra cryptography your_script.py

Explicit Provider Selection
----------------------------

You can explicitly select which crypto provider to use::

    from audible.crypto import get_crypto_providers, CryptographyProvider

    # Force cryptography provider
    providers = get_crypto_providers(CryptographyProvider)

    # Auto-detect (default)
    providers = get_crypto_providers()

Development Installation
------------------------

You can also use Git to clone the repository from GitHub to install the latest
development version::

    git clone https://github.com/mkb79/audible.git
    cd Audible
    pip install .

With optional dependencies::

    pip install .[cryptography]
    # or
    pip install .[pycryptodome]
    # or both
    pip install .[cryptography,pycryptodome]

Using uv::

    uv pip install -e .[cryptography,pycryptodome]

Or when working in the project::

    uv sync --extra cryptography --extra pycryptodome

Alternatively, install it directly from the GitHub repository::

    pip install git+https://github.com/mkb79/audible.git

With optional dependencies::

    pip install "audible[cryptography] @ git+https://github.com/mkb79/audible.git"
````

#### Step 8.3: Update CLAUDE.md (Key Dependencies section)

Update the Key Dependencies section (around line 98):

```markdown
## Key Dependencies

- **httpx**: HTTP client library (sync/async)
- **Pillow**: Image processing (CAPTCHA handling)
- **beautifulsoup4**: HTML parsing (login flows)
- **rsa**: RSA encryption (legacy fallback)
- **pyaes**: AES encryption (legacy fallback)
- **pbkdf2**: Key derivation (legacy fallback)

**Optional (recommended for performance):**

- **cryptography**: Rust-accelerated crypto operations (preferred)
- **pycryptodome**: C-based crypto operations
```

#### Step 8.4: Verification

Build and check documentation:

```bash
uv run nox -s docs-build
uv run nox -s xdoctest
```

Expected: Documentation builds successfully, all examples pass.

---

## 9. Test Suite

**Priority:** High
**Locations:** `tests/test_crypto.py`, `tests/test_auth.py`, `tests/conftest.py`
**Status:** ⏳ PENDING

### Implementation Steps

#### Step 9.1: Replace Hard-Coded Credentials with Fixtures

- Remove inline RSA keys and auth payloads from `tests/test_auth.py:14` and `tests/test_crypto.py:30`.
- Reuse `auth_fixture_data`, `auth_fixture_encrypted_json_data`, and `auth_fixture_encrypted_bytes_data` from `tests/conftest.py`.
- Introduce fixture helpers as needed (e.g., `rsa_private_key_fixture`) so tests no longer duplicate PEM blobs.
- Ensure fixtures expose any additional derived data required by tests and reset state between cases.
- ✅ RSA fixtures consumed by `tests/test_auth.py` and `tests/test_crypto.py`.

#### Step 9.2: Add CryptographyProvider Coverage

- Parametrise AES/PBKDF2/RSA/hash tests across providers, including `CryptographyProvider`.
- Extend registry assertions (`tests/test_crypto.py:400-517`) to expect `"cryptography"` when the dependency is installed.
- Skip gracefully when `cryptography` or `pycryptodome` are unavailable, matching existing skip behaviour.

#### Step 9.3: Provider Override Scenarios

- After Section 7 lands, add tests for `set_default_crypto_provider()` global overrides and per-instance overrides on `AESCipher` and `Authenticator`.
- Cover voucher decryption flows (`_decrypt_voucher`, `decrypt_voucher_from_licenserequest`) to confirm they honour custom providers.
- Use fixtures to reset overrides (`yield` fixture or `addfinalizer`) to keep tests isolated.
- Assert that overrides respect fixture-driven data (decrypt fixtures with explicit provider selections).

#### Step 9.4: Regression & Encrypted Fixture Coverage

- Leverage the encrypted fixtures (`auth_fixture_encrypted_json_data`, `auth_fixture_encrypted_bytes_data`) to verify round-trips under each provider.
- Ensure `tests/test_auth.py` checks encryption/decryption parity using the shared fixtures instead of bespoke strings.
- Add coverage for decryption failure paths (wrong password/provider) using anonymised fixture data.

#### Step 9.5: Run Automated Checks

```bash
uv run nox --session=tests
uv run nox --session=typeguard
uv run nox --session=coverage  # optional merge of parallel runs
```

- ✅ Session coverage: pre-commit, safety, mypy, tests, typeguard, xdoctest, docs-build
  Expected: Tests pass with and without optional dependencies; overrides restored to defaults after each test.

## 10. Manual Integration Tests

**Priority:** Medium
**Status:** ⏳ PENDING

### Implementation Steps

#### Step 10.1: Test Auto-Detection Priority

Create test script `test_autodetect.py`:

```python
#!/usr/bin/env python3
"""Manual test for crypto provider auto-detection."""

from audible.crypto import get_crypto_providers

providers = get_crypto_providers()
print(f"Auto-detected provider: {providers.provider_name}")

# Test basic operations
key = bytes([7]) * 16
iv = bytes([8]) * 16
plaintext = "Integration test"

ciphertext = providers.aes.encrypt(key, iv, plaintext)
print(f"Encrypted: {ciphertext.hex()[:32]}...")

decrypted = providers.aes.decrypt(key, iv, ciphertext)
print(f"Decrypted: {decrypted}")

assert decrypted == plaintext
print("✓ Auto-detection test passed")
```

Run in different environments:

```bash
# With both installed
uv run --extra cryptography --extra pycryptodome python test_autodetect.py

# With only cryptography
uv run --extra cryptography python test_autodetect.py

# With only pycryptodome
uv run --extra pycryptodome python test_autodetect.py

# With neither (legacy fallback)
uv run python test_autodetect.py
```

Expected output sequence:

1. Both installed → "cryptography"
2. Only cryptography → "cryptography"
3. Only pycryptodome → "pycryptodome"
4. Neither → "legacy" (with warning)

#### Step 10.2: Test Explicit Provider Selection

Create test script `test_explicit.py`:

```python
#!/usr/bin/env python3
"""Manual test for explicit provider selection."""

from audible.crypto import (
    get_crypto_providers,
    CryptographyProvider,
    PycryptodomeProvider,
    LegacyProvider,
)

# Test each provider explicitly
for provider_class in [CryptographyProvider, PycryptodomeProvider, LegacyProvider]:
    try:
        providers = get_crypto_providers(provider_class)
        print(f"✓ {providers.provider_name} provider works")

        # Quick smoke test
        key = bytes([9]) * 16
        iv = bytes([10]) * 16
        ciphertext = providers.aes.encrypt(key, iv, "test")
        decrypted = providers.aes.decrypt(key, iv, ciphertext)
        assert decrypted == "test"

    except ImportError as e:
        print(f"✗ {provider_class.__name__} not available: {e}")
```

Run:

```bash
uv run --extra cryptography --extra pycryptodome python test_explicit.py
```

Expected: All three providers work.

#### Step 10.3: Test in Real Audible Usage

Create integration test with actual auth flow:

```python
#!/usr/bin/env python3
"""Test crypto providers in real Audible usage."""

from audible import Authenticator
from audible.crypto import get_crypto_providers, CryptographyProvider

# Test with explicit provider
providers = get_crypto_providers(CryptographyProvider)
print(f"Using provider: {providers.provider_name}")

# Create authenticator (will use the crypto provider)
# Note: This requires valid credentials
auth = Authenticator.from_file("test_credentials.json")

print(f"✓ Loaded credentials using {providers.provider_name}")
print(f"  Device name: {auth.device_info.get('device_name', 'N/A')}")
```

Run:

```bash
uv run --extra cryptography python test_real_usage.py
```

Expected: Credentials load successfully with cryptography provider.

#### Step 10.4: Performance Benchmark (Optional)

Create benchmark script:

```python
#!/usr/bin/env python3
"""Benchmark crypto provider performance."""

import time
from audible.crypto import (
    get_crypto_providers,
    CryptographyProvider,
    PycryptodomeProvider,
    LegacyProvider,
)

key = bytes([11]) * 16
iv = bytes([12]) * 16
plaintext = "Benchmark test data" * 10

def benchmark_aes(provider_class, iterations=1000):
    """Benchmark AES encryption."""
    try:
        providers = get_crypto_providers(provider_class)
    except ImportError:
        return None

    start = time.time()
    for _ in range(iterations):
        ciphertext = providers.aes.encrypt(key, iv, plaintext)
        providers.aes.decrypt(key, iv, ciphertext)
    elapsed = time.time() - start

    return elapsed

print("AES Benchmark (1000 encrypt+decrypt cycles):")
print("-" * 50)

for provider in [CryptographyProvider, PycryptodomeProvider, LegacyProvider]:
    elapsed = benchmark_aes(provider)
    if elapsed:
        print(f"{provider.__name__:25s}: {elapsed:.3f}s")
    else:
        print(f"{provider.__name__:25s}: Not available")
```

Expected: cryptography ≈ pycryptodome << legacy (5-10x difference)

---

## Verification Checklist

After completing all steps, verify:

- [ ] All nox sessions pass: `uv run nox`
- [ ] Type checking passes: `uv run nox -s mypy`
- [ ] Tests pass: `uv run nox -s tests`
- [ ] Documentation builds: `uv run nox -s docs-build`
- [ ] Auto-detection works correctly in all scenarios
- [ ] Explicit provider selection works for all three providers
- [ ] Custom providers can be implemented and used
- [ ] Performance improvements are observable with optimized backends
- [ ] Backward compatibility maintained (existing code works unchanged)

---

## Rollback Plan

If critical issues are found:

1. Revert registry changes: `git checkout HEAD -- src/audible/crypto/registry.py`
2. Remove new provider: `rm src/audible/crypto/cryptography_provider.py`
3. Revert dependencies: `git checkout HEAD -- pyproject.toml noxfile.py`
4. Revert docs: `git checkout HEAD -- README.md docs/source/intro/install.rst`
5. Run tests to confirm stability: `uv run nox -s tests`

---

## Next Steps After Completion

1. Create PR with comprehensive description
2. Request code review focusing on:
   - Type safety of class-based API
   - Auto-detection priority logic
   - Documentation clarity
   - Test coverage
3. Update CHANGELOG.md with new features
4. Consider adding performance benchmarks to CI
