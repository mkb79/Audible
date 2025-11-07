"""Tests for audible.client module."""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, Mock, patch

import httpx
import pytest

from audible import exceptions
from audible.auth import Authenticator
from audible.client import (
    AsyncClient,
    Client,
    convert_response_content,
    default_response_callback,
    raise_for_status,
)
from audible.localization import Locale


@pytest.fixture
def mock_authenticator() -> Mock:
    """Fixture for mock Authenticator."""
    auth = Mock(spec=Authenticator)
    auth.locale = Locale("us")
    auth.access_token = "test_access_token"
    auth.adp_token = "test_adp_token"
    auth.device_private_key = "test_private_key"
    auth.refresh_access_token = Mock()
    auth.website_cookies = {}
    auth.user_profile = Mock(return_value={"name": "Test User"})
    return auth


@pytest.fixture
def mock_httpx_response() -> Mock:
    """Fixture for mock httpx.Response."""
    response = Mock(spec=httpx.Response)
    response.status_code = 200
    response.text = '{"data": "test"}'
    response.json = Mock(return_value={"data": "test"})
    response.raise_for_status = Mock()
    response.close = Mock()
    return response


class TestConvertResponseContent:
    """Tests for convert_response_content helper function."""

    def test_converts_valid_json(self) -> None:
        """Response with valid JSON is converted to dict."""
        response = Mock(spec=httpx.Response)
        response.text = '{"key": "value"}'

        result = convert_response_content(response)

        assert result == {"key": "value"}

    def test_returns_text_on_invalid_json(self) -> None:
        """Response with invalid JSON returns raw text."""
        response = Mock(spec=httpx.Response)
        response.text = "not valid json"

        result = convert_response_content(response)

        assert result == "not valid json"

    def test_handles_empty_response(self) -> None:
        """Empty response is handled gracefully."""
        response = Mock(spec=httpx.Response)
        response.text = ""

        result = convert_response_content(response)

        assert result == ""


class TestRaiseForStatus:
    """Tests for raise_for_status helper function."""

    def test_no_error_on_200_status(self, mock_httpx_response: Mock) -> None:
        """Status 200 does not raise exception."""
        mock_httpx_response.status_code = 200
        mock_httpx_response.raise_for_status = Mock()

        # Should not raise
        raise_for_status(mock_httpx_response)

        mock_httpx_response.raise_for_status.assert_called_once()

    def test_raises_bad_request_on_400(self, mock_httpx_response: Mock) -> None:
        """Status 400 raises BadRequest exception."""
        mock_httpx_response.status_code = 400
        mock_httpx_response.raise_for_status = Mock(
            side_effect=httpx.HTTPStatusError("", request=Mock(), response=Mock())
        )

        with pytest.raises(exceptions.BadRequest):
            raise_for_status(mock_httpx_response)

    def test_raises_unauthorized_on_401(self, mock_httpx_response: Mock) -> None:
        """Status 401 raises Unauthorized exception."""
        mock_httpx_response.status_code = 401
        mock_httpx_response.raise_for_status = Mock(
            side_effect=httpx.HTTPStatusError("", request=Mock(), response=Mock())
        )

        with pytest.raises(exceptions.Unauthorized):
            raise_for_status(mock_httpx_response)

    def test_raises_unauthorized_on_403(self, mock_httpx_response: Mock) -> None:
        """Status 403 raises Unauthorized exception."""
        mock_httpx_response.status_code = 403
        mock_httpx_response.raise_for_status = Mock(
            side_effect=httpx.HTTPStatusError("", request=Mock(), response=Mock())
        )

        with pytest.raises(exceptions.Unauthorized):
            raise_for_status(mock_httpx_response)

    def test_raises_not_found_on_404(self, mock_httpx_response: Mock) -> None:
        """Status 404 raises NotFoundError exception."""
        mock_httpx_response.status_code = 404
        mock_httpx_response.raise_for_status = Mock(
            side_effect=httpx.HTTPStatusError("", request=Mock(), response=Mock())
        )

        with pytest.raises(exceptions.NotFoundError):
            raise_for_status(mock_httpx_response)

    def test_raises_ratelimit_on_429(self, mock_httpx_response: Mock) -> None:
        """Status 429 raises RatelimitError exception."""
        mock_httpx_response.status_code = 429
        mock_httpx_response.raise_for_status = Mock(
            side_effect=httpx.HTTPStatusError("", request=Mock(), response=Mock())
        )

        with pytest.raises(exceptions.RatelimitError):
            raise_for_status(mock_httpx_response)

    def test_raises_server_error_on_503(self, mock_httpx_response: Mock) -> None:
        """Status 503 raises ServerError exception."""
        mock_httpx_response.status_code = 503
        mock_httpx_response.raise_for_status = Mock(
            side_effect=httpx.HTTPStatusError("", request=Mock(), response=Mock())
        )

        with pytest.raises(exceptions.ServerError):
            raise_for_status(mock_httpx_response)

    def test_raises_unexpected_error_on_other_codes(
        self, mock_httpx_response: Mock
    ) -> None:
        """Other error status codes raise UnexpectedError."""
        mock_httpx_response.status_code = 500
        mock_httpx_response.raise_for_status = Mock(
            side_effect=httpx.HTTPStatusError("", request=Mock(), response=Mock())
        )

        with pytest.raises(exceptions.UnexpectedError):
            raise_for_status(mock_httpx_response)


class TestDefaultResponseCallback:
    """Tests for default_response_callback function."""

    def test_successful_response_returns_json(self, mock_httpx_response: Mock) -> None:
        """Successful response returns parsed JSON."""
        mock_httpx_response.status_code = 200
        mock_httpx_response.text = '{"result": "success"}'

        result = default_response_callback(mock_httpx_response)

        assert result == {"result": "success"}

    def test_error_response_raises_exception(self, mock_httpx_response: Mock) -> None:
        """Error response raises appropriate exception."""
        mock_httpx_response.status_code = 400
        mock_httpx_response.raise_for_status = Mock(
            side_effect=httpx.HTTPStatusError("", request=Mock(), response=Mock())
        )

        with pytest.raises(exceptions.BadRequest):
            default_response_callback(mock_httpx_response)


class TestClientInitialization:
    """Tests for Client initialization."""

    def test_client_init_with_authenticator(self, mock_authenticator: Mock) -> None:
        """Client can be initialized with Authenticator."""
        with Client(auth=mock_authenticator) as client:
            assert client.auth is mock_authenticator

    def test_client_init_with_country_code(self, mock_authenticator: Mock) -> None:
        """Client can override country code."""
        with Client(auth=mock_authenticator, country_code="de") as client:
            assert client.marketplace == "de"

    def test_client_init_with_custom_headers(self, mock_authenticator: Mock) -> None:
        """Client accepts custom headers."""
        custom_headers = {"X-Custom": "value"}

        with Client(auth=mock_authenticator, headers=custom_headers) as client:
            assert "X-Custom" in client.session.headers

    def test_client_init_with_custom_timeout(self, mock_authenticator: Mock) -> None:
        """Client accepts custom timeout."""
        with Client(auth=mock_authenticator, timeout=30) as client:
            assert client.session.timeout.read == 30

    def test_client_context_manager(self, mock_authenticator: Mock) -> None:
        """Client works as context manager."""
        with Client(auth=mock_authenticator) as client:
            assert isinstance(client, Client)

    def test_client_repr(self, mock_authenticator: Mock) -> None:
        """Client __repr__ returns marketplace info."""
        with Client(auth=mock_authenticator) as client:
            repr_str = repr(client)
            assert "Sync Client" in repr_str
            assert "us" in repr_str


class TestClientRequests:
    """Tests for Client HTTP requests."""

    @patch("httpx.Client.request")
    def test_client_get_success(
        self, mock_request: Mock, mock_authenticator: Mock, mock_httpx_response: Mock
    ) -> None:
        """Client GET request succeeds."""
        mock_request.return_value = mock_httpx_response

        with Client(auth=mock_authenticator) as client:
            result = client.get("library")

        assert result == {"data": "test"}
        mock_request.assert_called_once()

    @patch("httpx.Client.request")
    def test_client_post_success(
        self, mock_request: Mock, mock_authenticator: Mock, mock_httpx_response: Mock
    ) -> None:
        """Client POST request succeeds."""
        mock_request.return_value = mock_httpx_response

        with Client(auth=mock_authenticator) as client:
            result = client.post("library", body={"key": "value"})

        assert result == {"data": "test"}
        mock_request.assert_called_once()

    @patch("httpx.Client.request")
    def test_client_put_success(
        self, mock_request: Mock, mock_authenticator: Mock, mock_httpx_response: Mock
    ) -> None:
        """Client PUT request succeeds."""
        mock_request.return_value = mock_httpx_response

        with Client(auth=mock_authenticator) as client:
            result = client.put("library/item", body={"key": "value"})

        assert result == {"data": "test"}
        mock_request.assert_called_once()

    @patch("httpx.Client.request")
    def test_client_delete_success(
        self, mock_request: Mock, mock_authenticator: Mock, mock_httpx_response: Mock
    ) -> None:
        """Client DELETE request succeeds."""
        mock_request.return_value = mock_httpx_response

        with Client(auth=mock_authenticator) as client:
            result = client.delete("library/item")

        assert result == {"data": "test"}
        mock_request.assert_called_once()


class TestClientErrorHandling:
    """Tests for Client error handling."""

    @patch("httpx.Client.request")
    def test_client_handles_connect_timeout(
        self, mock_request: Mock, mock_authenticator: Mock
    ) -> None:
        """Client raises NotResponding on connect timeout."""
        mock_request.side_effect = httpx.ConnectTimeout("")

        with Client(auth=mock_authenticator) as client:
            with pytest.raises(exceptions.NotResponding):
                client.get("library")

    @patch("httpx.Client.request")
    def test_client_handles_read_timeout(
        self, mock_request: Mock, mock_authenticator: Mock
    ) -> None:
        """Client raises NotResponding on read timeout."""
        mock_request.side_effect = httpx.ReadTimeout("")

        with Client(auth=mock_authenticator) as client:
            with pytest.raises(exceptions.NotResponding):
                client.get("library")

    @patch("httpx.Client.request")
    def test_client_handles_network_error(
        self, mock_request: Mock, mock_authenticator: Mock
    ) -> None:
        """Client raises NetworkError on network error."""
        mock_request.side_effect = httpx.NetworkError("")

        with Client(auth=mock_authenticator) as client:
            with pytest.raises(exceptions.NetworkError):
                client.get("library")

    @patch("httpx.Client.request")
    def test_client_handles_request_error(
        self, mock_request: Mock, mock_authenticator: Mock
    ) -> None:
        """Client raises RequestError on generic request error."""
        mock_request.side_effect = httpx.RequestError("")

        with Client(auth=mock_authenticator) as client:
            with pytest.raises(exceptions.RequestError):
                client.get("library")


class TestClientMarketplaceSwitching:
    """Tests for marketplace switching functionality."""

    def test_switch_marketplace(self, mock_authenticator: Mock) -> None:
        """Client can switch marketplace."""
        with Client(auth=mock_authenticator) as client:
            assert client.marketplace == "us"

            client.switch_marketplace("de")

            assert client.marketplace == "de"

    def test_marketplace_property_returns_country_code(
        self, mock_authenticator: Mock
    ) -> None:
        """marketplace property returns country code."""
        with Client(auth=mock_authenticator) as client:
            assert client.marketplace == "us"


class TestClientUserOperations:
    """Tests for user-related operations."""

    def test_get_user_profile(self, mock_authenticator: Mock) -> None:
        """get_user_profile calls auth methods."""
        with Client(auth=mock_authenticator) as client:
            profile = client.get_user_profile()

        assert profile == {"name": "Test User"}
        mock_authenticator.refresh_access_token.assert_called_once()
        mock_authenticator.user_profile.assert_called_once()

    def test_user_name_property(self, mock_authenticator: Mock) -> None:
        """user_name property returns name from profile."""
        with Client(auth=mock_authenticator) as client:
            name = client.user_name

        assert name == "Test User"

    def test_user_name_property_raises_on_missing_name(
        self, mock_authenticator: Mock
    ) -> None:
        """user_name raises exception if name is missing."""
        mock_authenticator.user_profile = Mock(return_value={})

        with Client(auth=mock_authenticator) as client:
            with pytest.raises(Exception, match="user profile has no key `name`"):
                _ = client.user_name


class TestClientRawRequest:
    """Tests for raw_request functionality."""

    @patch("httpx.Client.request")
    def test_raw_request_basic(
        self, mock_request: Mock, mock_authenticator: Mock, mock_httpx_response: Mock
    ) -> None:
        """raw_request makes direct httpx request."""
        mock_request.return_value = mock_httpx_response

        with Client(auth=mock_authenticator) as client:
            result = client.raw_request("GET", "https://example.com/api")

        assert result == mock_httpx_response
        mock_request.assert_called_once()

    @patch("httpx.Client.request")
    def test_raw_request_with_apply_auth_flow(
        self, mock_request: Mock, mock_authenticator: Mock, mock_httpx_response: Mock
    ) -> None:
        """raw_request can apply auth flow."""
        mock_request.return_value = mock_httpx_response

        with Client(auth=mock_authenticator) as client:
            result = client.raw_request(
                "GET", "https://example.com/api", apply_auth_flow=True
            )

        assert result == mock_httpx_response
        call_kwargs = mock_request.call_args[1]
        assert "auth" in call_kwargs

    @patch("httpx.Client.request")
    def test_raw_request_with_cookies(
        self, mock_request: Mock, mock_authenticator: Mock, mock_httpx_response: Mock
    ) -> None:
        """raw_request can apply cookies."""
        mock_authenticator.website_cookies = {"session": "abc"}
        mock_request.return_value = mock_httpx_response

        with Client(auth=mock_authenticator) as client:
            result = client.raw_request(
                "GET", "https://example.com/api", apply_cookies=True
            )

        assert result == mock_httpx_response
        call_kwargs = mock_request.call_args[1]
        assert "cookies" in call_kwargs


class TestAsyncClientInitialization:
    """Tests for AsyncClient initialization."""

    @pytest.mark.asyncio
    async def test_async_client_init(self, mock_authenticator: Mock) -> None:
        """AsyncClient can be initialized."""
        async with AsyncClient(auth=mock_authenticator) as client:
            assert client.auth is mock_authenticator

    @pytest.mark.asyncio
    async def test_async_client_context_manager(self, mock_authenticator: Mock) -> None:
        """AsyncClient works as async context manager."""
        async with AsyncClient(auth=mock_authenticator) as client:
            assert isinstance(client, AsyncClient)

    @pytest.mark.asyncio
    async def test_async_client_repr(self, mock_authenticator: Mock) -> None:
        """AsyncClient __repr__ returns marketplace info."""
        async with AsyncClient(auth=mock_authenticator) as client:
            repr_str = repr(client)
            assert "AyncClient" in repr_str
            assert "us" in repr_str


class TestAsyncClientRequests:
    """Tests for AsyncClient HTTP requests."""

    @pytest.mark.asyncio
    async def test_async_client_get_success(
        self, mock_authenticator: Mock
    ) -> None:
        """AsyncClient GET request succeeds."""
        mock_response = AsyncMock(spec=httpx.Response)
        mock_response.status_code = 200
        mock_response.text = '{"data": "test"}'
        mock_response.raise_for_status = Mock()
        mock_response.aclose = AsyncMock()

        with patch(
            "httpx.AsyncClient.request", new=AsyncMock(return_value=mock_response)
        ):
            async with AsyncClient(auth=mock_authenticator) as client:
                result = await client.get("library")

            assert result == {"data": "test"}

    @pytest.mark.asyncio
    async def test_async_client_post_success(
        self, mock_authenticator: Mock
    ) -> None:
        """AsyncClient POST request succeeds."""
        mock_response = AsyncMock(spec=httpx.Response)
        mock_response.status_code = 200
        mock_response.text = '{"data": "test"}'
        mock_response.raise_for_status = Mock()
        mock_response.aclose = AsyncMock()

        with patch(
            "httpx.AsyncClient.request", new=AsyncMock(return_value=mock_response)
        ):
            async with AsyncClient(auth=mock_authenticator) as client:
                result = await client.post("library", body={"key": "value"})

            assert result == {"data": "test"}

    @pytest.mark.asyncio
    async def test_async_client_put_success(
        self, mock_authenticator: Mock
    ) -> None:
        """AsyncClient PUT request succeeds."""
        mock_response = AsyncMock(spec=httpx.Response)
        mock_response.status_code = 200
        mock_response.text = '{"data": "test"}'
        mock_response.raise_for_status = Mock()
        mock_response.aclose = AsyncMock()

        with patch(
            "httpx.AsyncClient.request", new=AsyncMock(return_value=mock_response)
        ):
            async with AsyncClient(auth=mock_authenticator) as client:
                result = await client.put("library/item", body={"key": "value"})

            assert result == {"data": "test"}

    @pytest.mark.asyncio
    async def test_async_client_delete_success(
        self, mock_authenticator: Mock
    ) -> None:
        """AsyncClient DELETE request succeeds."""
        mock_response = AsyncMock(spec=httpx.Response)
        mock_response.status_code = 200
        mock_response.text = '{"data": "test"}'
        mock_response.raise_for_status = Mock()
        mock_response.aclose = AsyncMock()

        with patch(
            "httpx.AsyncClient.request", new=AsyncMock(return_value=mock_response)
        ):
            async with AsyncClient(auth=mock_authenticator) as client:
                result = await client.delete("library/item")

            assert result == {"data": "test"}


class TestAsyncClientErrorHandling:
    """Tests for AsyncClient error handling."""

    @pytest.mark.asyncio
    async def test_async_client_handles_timeout(
        self, mock_authenticator: Mock
    ) -> None:
        """AsyncClient raises NotResponding on timeout."""
        with patch(
            "httpx.AsyncClient.request",
            new=AsyncMock(side_effect=httpx.ConnectTimeout("")),
        ):
            async with AsyncClient(auth=mock_authenticator) as client:
                with pytest.raises(exceptions.NotResponding):
                    await client.get("library")

    @pytest.mark.asyncio
    async def test_async_client_handles_network_error(
        self, mock_authenticator: Mock
    ) -> None:
        """AsyncClient raises NetworkError on network error."""
        with patch(
            "httpx.AsyncClient.request",
            new=AsyncMock(side_effect=httpx.NetworkError("")),
        ):
            async with AsyncClient(auth=mock_authenticator) as client:
                with pytest.raises(exceptions.NetworkError):
                    await client.get("library")


class TestClientPrepareParams:
    """Tests for _prepare_params method."""

    def test_prepare_params_moves_non_httpx_args(
        self, mock_authenticator: Mock
    ) -> None:
        """Non-httpx arguments are moved to params."""
        with Client(auth=mock_authenticator) as client:
            kwargs: dict[str, Any] = {"response_group": "media", "timeout": 10}
            client._prepare_params(kwargs)

            assert "params" in kwargs
            assert kwargs["params"]["response_group"] == "media"
            assert "response_group" not in kwargs
            assert "timeout" in kwargs  # httpx arg stays


class TestClientAuthProperty:
    """Tests for auth property."""

    def test_auth_property_returns_authenticator(
        self, mock_authenticator: Mock
    ) -> None:
        """auth property returns Authenticator instance."""
        with Client(auth=mock_authenticator) as client:
            assert isinstance(client.auth, Mock)
            assert client.auth is mock_authenticator

    def test_auth_property_raises_on_wrong_type(
        self, mock_authenticator: Mock
    ) -> None:
        """auth property raises if session.auth is not Authenticator."""
        with Client(auth=mock_authenticator) as client:
            # Directly set session's internal _auth to wrong type to test validation
            client.session._auth = "not_an_authenticator"  # type: ignore[assignment]

            with pytest.raises(Exception, match="expected `Authenticator`"):
                _ = client.auth


class TestClientSwitchUser:
    """Tests for switch_user functionality."""

    def test_switch_user_changes_auth(self, mock_authenticator: Mock) -> None:
        """switch_user changes the authenticator."""
        new_auth = Mock(spec=Authenticator)
        new_auth.locale = Locale("de")

        with Client(auth=mock_authenticator) as client:
            client.switch_user(new_auth)

            assert client.session.auth is new_auth

    def test_switch_user_with_marketplace_switch(
        self, mock_authenticator: Mock
    ) -> None:
        """switch_user can also switch marketplace."""
        new_auth = Mock(spec=Authenticator)
        new_auth.locale = Locale("de")

        with Client(auth=mock_authenticator) as client:
            client.switch_user(new_auth, switch_to_default_marketplace=True)

            assert client.marketplace == "de"


class TestClientPrepareApiPath:
    """Tests for _prepare_api_path method."""

    def test_prepare_api_path_with_relative_path(
        self, mock_authenticator: Mock
    ) -> None:
        """Relative paths get API version prepended."""
        with Client(auth=mock_authenticator) as client:
            url = client._prepare_api_path("library")

            assert "1.0/library" in str(url)

    def test_prepare_api_path_with_leading_slash(
        self, mock_authenticator: Mock
    ) -> None:
        """Paths with leading slash are handled."""
        with Client(auth=mock_authenticator) as client:
            url = client._prepare_api_path("/library")

            assert "1.0/library" in str(url)

    def test_prepare_api_path_with_absolute_url(
        self, mock_authenticator: Mock
    ) -> None:
        """Absolute URLs are returned as-is."""
        with Client(auth=mock_authenticator) as client:
            url = client._prepare_api_path("https://example.com/test")

            assert str(url) == "https://example.com/test"

    def test_prepare_api_path_with_version_prefix(
        self, mock_authenticator: Mock
    ) -> None:
        """Paths already containing version are not double-prefixed."""
        with Client(auth=mock_authenticator) as client:
            url = client._prepare_api_path("1.0/library")

            path_str = str(url)
            # Should not have 1.0/1.0/library
            assert path_str.count("1.0") == 1
