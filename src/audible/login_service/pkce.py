from __future__ import annotations

import base64
import hashlib
import logging
import re
import secrets
from dataclasses import dataclass, field


logger = logging.getLogger(__name__)


# ----- RFC 7636 / PKCE -----

PKCE_MIN_LENGTH = 43
PKCE_MAX_LENGTH = 128


def _b64url_nopad(raw: bytes) -> bytes:
    """Return a base64url-encoded ASCII string without '=' padding."""
    return base64.urlsafe_b64encode(raw).rstrip(b"=")


@dataclass(slots=True, frozen=True)
class PKCE:
    """Immutable PKCE pair (code_verifier, code_challenge) using S256.

    Attributes:
        verifier: Base64url-encoded string without padding.
        challenge: Base64url-encoded SHA-256 hash of the verifier.
    """

    verifier: bytes
    challenge: bytes = field(init=False)

    def __post_init__(self) -> None:
        """Validate the verifier and compute the challenge once."""
        object.__setattr__(self, "challenge", self._compute_challenge())

    def _compute_challenge(self) -> bytes:
        """Compute the base64url-encoded SHA-256 challenge from the verifier."""
        digest = hashlib.sha256(self.verifier).digest()
        return _b64url_nopad(digest)

    @classmethod
    def generate(cls, num_bytes: int = 128) -> PKCE:
        """Generate a PKCE instance with a secure random verifier.

        Args:
            num_bytes: Number of random bytes prior to encoding.

        Returns:
            PKCE: Instance with valid verifier and precomputed challenge.
        """
        verifier = _b64url_nopad(secrets.token_bytes(128))
        if num_bytes < PKCE_MIN_LENGTH:
            num_bytes = PKCE_MIN_LENGTH
        elif num_bytes > PKCE_MAX_LENGTH:
            num_bytes = PKCE_MAX_LENGTH
        verifier = verifier[:num_bytes]
        return cls(verifier=verifier)
