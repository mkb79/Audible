"""Tests for the auth module."""

from __future__ import annotations

from unittest.mock import Mock

import httpx

from audible.auth import Authenticator
from audible.localization import Locale


# Valid RSA private key in PKCS#1 format (1024-bit for testing)
TEST_RSA_KEY_1 = """-----BEGIN RSA PRIVATE KEY-----
MIICXAIBAAKBgQCckEdw6Hd8Pwm1YRtinw2UQkTmRM5QQcfsUxi86w6mxXRomETI
FPZaFS6q9D1x1Zgzhk+tXS6MBl8tJrDjaAUROeoajdNylvunvdyLNQhoaGOcbRSr
0DFV/an6oKv6IsLQzI7UP91ZSbg4fDb5/LqqD4devp5QpShJMEtw2OUUzwIDAQAB
AoGAdqJtQAUm5SLvPF2E3sofBATjKIlivDXcRBsDV8PVqlFc0BTxqZsYwVHjtu6z
0JpFZmWT4o4FQ11gqVn0F50umJuPoS/slfBGiV3TE2b3o+uLy6EcVDoOtH7cUO6l
gTvejvv6rCpuvHHLkDf8mUEtN+WJDGwYamyHfCIChSAIrMECQQDMIdhGmNg7ckpb
KnrJ2rAj38QrUO0t1m/t+i/76vyvPN65o6lnvI/SHNXUf/asQbmHeUT3b75ApqoV
BLSGWG15AkEAxFg++zayNfGHl99xYpB0g4gom/UqGC87hiVJYXpoXCld4kmguW4j
ov3rRDKQGZwh/DQyX0BvxDHmfGzTXNmqhwJAS+m6OGbW4ySZqlWd3DtLjcvFdCZg
Tc+VSHbmKVU2KyUD3x2R/lYNViILEz+TSHQYvtzGXQ5dPkW8spxRVjTEYQJAGowH
7/VkQRDoEWu/q+D2L/aP7w5F48E3HhsagdiIFbXuILNtzMSMgvQsBCuF+kB3A9+W
0/QlaHSKwlYAefRgLwJBAMQc+jY9eymjJ08KVZrVC8NhYEliWTPkpfjeh4CTTfNY
Ho8KYXsQV2M4btI7FJO1CMb2SV5sP09IRvBdX1hEqzY=
-----END RSA PRIVATE KEY-----"""

# Different RSA private key for testing cache invalidation
TEST_RSA_KEY_2 = """-----BEGIN RSA PRIVATE KEY-----
MIICXQIBAAKBgQDGvZ7L8vF3K5n4F3v9sUxNQXfmq1L8K8hF+r3t4cC4hZxb2F8Q
3xYT5fK2L9xF3c0K9xF3vL4F8xT2cL9xF3cL4F9x3cK9xF3L5xF3c4K9xF3L5xF3
c0K9xF3L5xF3c4K9xF3L5xF3c0K9xF3L5xF3c4K9xF3L5xF3c0K9xF3LwIDAQAB
AoGBALF3c0K9xF3L5xF3c4K9xF3L5xF3c0K9xF3L5xF3c4K9xF3L5xF3c0K9xF3L
5xF3c4K9xF3L5xF3c0K9xF3L5xF3c4K9xF3L5xF3c0K9xF3L5xF3c4K9xF3L5xF3
c0K9xF3L5xF3c4K9xF3L5xF3c0K9xF3L5xF3c4K9xF3L5xF3c0K9xF3LAkEA5xF3
c0K9xF3L5xF3c4K9xF3L5xF3c0K9xF3L5xF3c4K9xF3L5xF3c0K9xF3L5xF3c4K9
xF3L5xF3c0K9xF3L5xF3c4K9xF3LAkEA5xF3c0K9xF3L5xF3c4K9xF3L5xF3c0K9
xF3L5xF3c4K9xF3L5xF3c0K9xF3L5xF3c4K9xF3L5xF3c0K9xF3L5xF3c4K9xF3L
AkA5xF3c0K9xF3L5xF3c4K9xF3L5xF3c0K9xF3L5xF3c4K9xF3L5xF3c0K9xF3L
5xF3c4K9xF3L5xF3c0K9xF3L5xF3c4K9xF3LAkEA5xF3c0K9xF3L5xF3c4K9xF3L
5xF3c0K9xF3L5xF3c4K9xF3L5xF3c0K9xF3L5xF3c4K9xF3L5xF3c0K9xF3L5xF3
c4K9xF3LAkEA5xF3c0K9xF3L5xF3c4K9xF3L5xF3c0K9xF3L5xF3c4K9xF3L5xF3
c0K9xF3L5xF3c4K9xF3L5xF3c0K9xF3L5xF3c4K9xF3L
-----END RSA PRIVATE KEY-----"""


def test_rsa_key_cache_invalidation() -> None:
    """Test that cached RSA key is invalidated when device_private_key changes."""
    # Create authenticator with initial key
    auth = Authenticator()
    auth._apply_test_convert = False  # Disable validation for test
    auth.locale = Locale("us")
    auth.adp_token = "{enc:test}{key:test}{iv:test}{name:test}{serial:Mg==}"  # noqa: S105
    auth.device_private_key = TEST_RSA_KEY_1

    # Create a mock request
    mock_request = Mock(spec=httpx.Request)
    mock_request.method = "GET"
    mock_request.url = Mock()
    mock_request.url.raw_path = b"/test/path"
    mock_request.content = b""
    mock_request.headers = {}

    # Trigger cache creation by calling signing flow
    auth._apply_signing_auth_flow(mock_request)

    # Verify cache was created
    assert auth._cached_rsa_key is not None

    # Change device_private_key (doesn't need to be valid for this test)
    auth.device_private_key = "different_key_data"

    # Verify cache was invalidated
    assert auth._cached_rsa_key is None, (
        "Cache should be None after device_private_key change"
    )


def test_rsa_key_cache_not_invalidated_for_other_attributes() -> None:
    """Test that cached RSA key is NOT invalidated when other attributes change."""
    auth = Authenticator()
    auth._apply_test_convert = False  # Disable validation for test
    auth.locale = Locale("us")
    auth.adp_token = "{enc:test}{key:test}{iv:test}{name:test}{serial:Mg==}"  # noqa: S105
    auth.device_private_key = TEST_RSA_KEY_1

    # Create mock request
    mock_request = Mock(spec=httpx.Request)
    mock_request.method = "GET"
    mock_request.url = Mock()
    mock_request.url.raw_path = b"/test/path"
    mock_request.content = b""
    mock_request.headers = {}

    # Trigger cache creation
    auth._apply_signing_auth_flow(mock_request)
    cached_key = auth._cached_rsa_key

    # Modify other attributes
    auth.access_token = "new_access_token"  # noqa: S105
    auth.refresh_token = "new_refresh_token"  # noqa: S105

    # Verify cache is still intact
    assert auth._cached_rsa_key is cached_key
    assert auth._cached_rsa_key is not None
