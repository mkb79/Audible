"""Fixtures for register/deregister tests (anonymized mock data)."""

from __future__ import annotations

from typing import Any

import pytest


@pytest.fixture
def mock_register_response_success() -> dict[str, Any]:
    """Fixture for successful registration response (anonymized mock data)."""
    return {
        "response": {
            "success": {
                "extensions": {
                    "device_info": {
                        "device_name": "Test User's Audible Device",
                        "device_serial_number": "MOCK1234567890ABCDEF",
                        "device_type": "A2CZJZGLK2JJVM",
                    },
                    "customer_info": {
                        "account_pool": "Amazon",
                        "user_id": "amzn1.account.MOCKUSERID123456",
                        "home_region": "NA",
                        "name": "Test User",
                        "given_name": "Test",
                    },
                },
                "tokens": {
                    "website_cookies": [
                        {
                            "Name": "session-id",
                            "Value": "mock-session-123",
                            "Domain": ".amazon.com",
                            "Path": "/",
                            "Secure": "true",
                            "HttpOnly": "false",
                            "Expires": "01 Jan 2030 00:00:00 GMT",
                        },
                        {
                            "Name": "ubid-main",
                            "Value": "mock-ubid-456",
                            "Domain": ".amazon.com",
                            "Path": "/",
                            "Secure": "true",
                            "HttpOnly": "false",
                            "Expires": "01 Jan 2030 00:00:00 GMT",
                        },
                        {
                            "Name": "x-main",
                            "Value": '"mock-x-value-789"',
                            "Domain": ".amazon.com",
                            "Path": "/",
                            "Secure": "true",
                            "HttpOnly": "false",
                            "Expires": "01 Jan 2030 00:00:00 GMT",
                        },
                    ],
                    "mac_dms": {
                        "device_private_key": "-----BEGIN RSA PRIVATE KEY-----\nMOCK_PRIVATE_KEY_DATA_HERE\n-----END RSA PRIVATE KEY-----\n",
                        "adp_token": "{enc:MOCK_ENCRYPTED_ADP_TOKEN}{key:MOCK_KEY}{iv:MOCK_IV}{name:MOCK_NAME}{serial:MOCK_SERIAL}",
                    },
                    "bearer": {
                        "access_token": "Atna|MOCK_ACCESS_TOKEN_1234567890",
                        "refresh_token": "Atnr|MOCK_REFRESH_TOKEN_0987654321",
                        "expires_in": "3600",
                    },
                    "store_authentication_cookie": {
                        "cookie": "MOCK_STORE_AUTH_COOKIE_DATA"
                    },
                },
                "customer_id": "amzn1.account.MOCKUSERID123456",
            }
        },
        "request_id": "mock-request-id-abcd-1234",
    }


@pytest.fixture
def mock_register_response_no_cookies() -> dict[str, Any]:
    """Fixture for registration response without website_cookies."""
    return {
        "response": {
            "success": {
                "extensions": {
                    "device_info": {
                        "device_name": "Test Device",
                        "device_serial_number": "MOCK_SERIAL",
                        "device_type": "A2CZJZGLK2JJVM",
                    },
                    "customer_info": {
                        "account_pool": "Amazon",
                        "user_id": "amzn1.account.TEST",
                        "home_region": "NA",
                        "name": "Test",
                        "given_name": "Test",
                    },
                },
                "tokens": {
                    "mac_dms": {
                        "device_private_key": "-----BEGIN RSA PRIVATE KEY-----\nMOCK_KEY\n-----END RSA PRIVATE KEY-----\n",
                        "adp_token": "{enc:MOCK}",
                    },
                    "bearer": {
                        "access_token": "Atna|MOCK_TOKEN",
                        "refresh_token": "Atnr|MOCK_TOKEN",
                        "expires_in": "3600",
                    },
                },
                "customer_id": "amzn1.account.TEST",
            }
        },
        "request_id": "mock-id",
    }


@pytest.fixture
def mock_deregister_response_success() -> dict[str, Any]:
    """Fixture for successful deregistration response."""
    return {
        "response": {"success": {}},
        "request_id": "mock-deregister-request-id-5678",
    }
