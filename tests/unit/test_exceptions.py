"""Tests for audible.exceptions module."""

import pytest
from unittest.mock import Mock
from audible import exceptions


class TestBaseExceptions:
    """Tests for base exception classes."""

    def test_audible_error_inherits_from_exception(self) -> None:
        """AudibleError inherits from Exception."""
        error = exceptions.AudibleError("test message")
        assert isinstance(error, Exception)

    def test_request_error_inherits_from_audible_error(self) -> None:
        """RequestError inherits from AudibleError."""
        error = exceptions.RequestError("test message")
        assert isinstance(error, exceptions.AudibleError)

    def test_status_error_inherits_from_request_error(self) -> None:
        """StatusError inherits from RequestError."""
        mock_response = Mock()
        mock_response.status_code = 400
        mock_response.reason_phrase = "Bad Request"
        error = exceptions.StatusError(mock_response, {"error": "test"})
        assert isinstance(error, exceptions.RequestError)


class TestStatusError:
    """Tests for StatusError and its attributes."""

    def test_status_error_with_dict_data_error_key(self) -> None:
        """StatusError processes dict with 'error' key correctly."""
        mock_response = Mock()
        mock_response.status_code = 400
        mock_response.reason_phrase = "Bad Request"
        mock_response.method = "GET"

        data = {"error": "Invalid parameter"}
        error = exceptions.StatusError(mock_response, data)

        assert error.code == 400
        assert error.reason == "Bad Request"
        assert error.error == "Invalid parameter"
        assert error.method == "GET"
        assert "Bad Request (400): Invalid parameter" in str(error)

    def test_status_error_with_dict_data_message_key(self) -> None:
        """StatusError prioritizes 'message' over 'error' key."""
        mock_response = Mock()
        mock_response.status_code = 404
        mock_response.reason_phrase = "Not Found"
        mock_response.method = "POST"

        data = {"error": "old error", "message": "Resource not found"}
        error = exceptions.StatusError(mock_response, data)

        assert error.error == "Resource not found"
        assert "Not Found (404): Resource not found" in str(error)

    def test_status_error_with_non_dict_data(self) -> None:
        """StatusError processes string data correctly."""
        mock_response = Mock()
        mock_response.status_code = 500
        mock_response.reason_phrase = "Internal Server Error"
        mock_response.method = None

        error = exceptions.StatusError(mock_response, "Server crashed")

        assert error.code == 500
        assert error.error == "Server crashed"
        assert error.method is None

    def test_status_error_stores_response_object(self) -> None:
        """StatusError stores response object."""
        mock_response = Mock()
        mock_response.status_code = 403
        mock_response.reason_phrase = "Forbidden"

        error = exceptions.StatusError(mock_response, {})
        assert error.response is mock_response

    def test_status_error_with_empty_dict(self) -> None:
        """StatusError handles empty dict data."""
        mock_response = Mock()
        mock_response.status_code = 500
        mock_response.reason_phrase = "Server Error"

        error = exceptions.StatusError(mock_response, {})
        assert error.error is None


class TestNotResponding:
    """Tests for NotResponding exception."""

    def test_not_responding_initialization(self) -> None:
        """NotResponding has correct default values."""
        error = exceptions.NotResponding()

        assert error.code == 504
        assert error.error == "API request timed out, please be patient."
        assert isinstance(error, exceptions.RequestError)

    def test_not_responding_error_message(self) -> None:
        """NotResponding shows correct error message."""
        error = exceptions.NotResponding()
        assert "API request timed out" in str(error)

    def test_not_responding_inherits_from_request_error(self) -> None:
        """NotResponding inherits from RequestError."""
        error = exceptions.NotResponding()
        assert isinstance(error, exceptions.RequestError)
        assert isinstance(error, exceptions.AudibleError)


class TestNetworkError:
    """Tests for NetworkError exception."""

    def test_network_error_initialization(self) -> None:
        """NetworkError has correct default values."""
        error = exceptions.NetworkError()

        assert error.code == 503
        assert error.error == "Network down."
        assert isinstance(error, exceptions.RequestError)

    def test_network_error_message(self) -> None:
        """NetworkError shows correct error message."""
        error = exceptions.NetworkError()
        assert "Network down" in str(error)

    def test_network_error_inherits_from_request_error(self) -> None:
        """NetworkError inherits from RequestError."""
        error = exceptions.NetworkError()
        assert isinstance(error, exceptions.RequestError)
        assert isinstance(error, exceptions.AudibleError)


class TestHTTPStatusExceptions:
    """Tests for HTTP status-based exceptions."""

    def test_bad_request_inheritance(self) -> None:
        """BadRequest inherits from StatusError."""
        mock_response = Mock()
        mock_response.status_code = 400
        mock_response.reason_phrase = "Bad Request"

        error = exceptions.BadRequest(mock_response, {})
        assert isinstance(error, exceptions.StatusError)
        assert isinstance(error, exceptions.RequestError)

    def test_not_found_error_inheritance(self) -> None:
        """NotFoundError inherits from StatusError."""
        mock_response = Mock()
        mock_response.status_code = 404
        mock_response.reason_phrase = "Not Found"

        error = exceptions.NotFoundError(mock_response, {})
        assert isinstance(error, exceptions.StatusError)
        assert isinstance(error, exceptions.RequestError)

    def test_server_error_inheritance(self) -> None:
        """ServerError inherits from StatusError."""
        mock_response = Mock()
        mock_response.status_code = 500
        mock_response.reason_phrase = "Internal Server Error"

        error = exceptions.ServerError(mock_response, {})
        assert isinstance(error, exceptions.StatusError)
        assert isinstance(error, exceptions.RequestError)

    def test_unauthorized_inheritance(self) -> None:
        """Unauthorized inherits from StatusError."""
        mock_response = Mock()
        mock_response.status_code = 401
        mock_response.reason_phrase = "Unauthorized"

        error = exceptions.Unauthorized(mock_response, {})
        assert isinstance(error, exceptions.StatusError)
        assert isinstance(error, exceptions.RequestError)

    def test_ratelimit_error_inheritance(self) -> None:
        """RatelimitError inherits from StatusError."""
        mock_response = Mock()
        mock_response.status_code = 429
        mock_response.reason_phrase = "Too Many Requests"

        error = exceptions.RatelimitError(mock_response, {})
        assert isinstance(error, exceptions.StatusError)
        assert isinstance(error, exceptions.RequestError)

    def test_unexpected_error_inheritance(self) -> None:
        """UnexpectedError inherits from StatusError."""
        mock_response = Mock()
        mock_response.status_code = 999
        mock_response.reason_phrase = "Unknown"

        error = exceptions.UnexpectedError(mock_response, {})
        assert isinstance(error, exceptions.StatusError)
        assert isinstance(error, exceptions.RequestError)


class TestAuthFlowError:
    """Tests for AuthFlowError."""

    def test_auth_flow_error_inheritance(self) -> None:
        """AuthFlowError inherits from AudibleError."""
        error = exceptions.AuthFlowError("No auth method available")
        assert isinstance(error, exceptions.AudibleError)
        assert isinstance(error, Exception)

    def test_auth_flow_error_message(self) -> None:
        """AuthFlowError stores and displays message."""
        message = "Authentication flow failed"
        error = exceptions.AuthFlowError(message)
        assert message in str(error)


class TestNoRefreshToken:
    """Tests for NoRefreshToken."""

    def test_no_refresh_token_inheritance(self) -> None:
        """NoRefreshToken inherits from AudibleError."""
        error = exceptions.NoRefreshToken("No token provided")
        assert isinstance(error, exceptions.AudibleError)
        assert isinstance(error, Exception)

    def test_no_refresh_token_message(self) -> None:
        """NoRefreshToken stores and displays message."""
        message = "Refresh token is required"
        error = exceptions.NoRefreshToken(message)
        assert message in str(error)


class TestFileEncryptionError:
    """Tests for FileEncryptionError."""

    def test_file_encryption_error_inheritance(self) -> None:
        """FileEncryptionError inherits from AudibleError."""
        error = exceptions.FileEncryptionError("Encryption failed")
        assert isinstance(error, exceptions.AudibleError)
        assert isinstance(error, Exception)

    def test_file_encryption_error_message(self) -> None:
        """FileEncryptionError stores and displays message."""
        message = "Failed to encrypt credentials file"
        error = exceptions.FileEncryptionError(message)
        assert message in str(error)


class TestExceptionRaising:
    """Tests for raising and catching exceptions."""

    def test_status_error_can_be_raised_and_caught(self) -> None:
        """StatusError can be raised and caught."""
        mock_response = Mock()
        mock_response.status_code = 400
        mock_response.reason_phrase = "Bad Request"

        with pytest.raises(exceptions.StatusError) as exc_info:
            raise exceptions.StatusError(mock_response, {"error": "test"})

        assert exc_info.value.code == 400

    def test_not_responding_can_be_raised_and_caught(self) -> None:
        """NotResponding can be raised and caught."""
        with pytest.raises(exceptions.NotResponding) as exc_info:
            raise exceptions.NotResponding()

        assert exc_info.value.code == 504

    def test_network_error_can_be_raised_and_caught(self) -> None:
        """NetworkError can be raised and caught."""
        with pytest.raises(exceptions.NetworkError) as exc_info:
            raise exceptions.NetworkError()

        assert exc_info.value.code == 503

    def test_catching_base_exception_catches_all(self) -> None:
        """Catching AudibleError catches all custom exceptions."""
        with pytest.raises(exceptions.AudibleError):
            raise exceptions.AuthFlowError("test")

        with pytest.raises(exceptions.AudibleError):
            raise exceptions.NoRefreshToken("test")

        with pytest.raises(exceptions.AudibleError):
            raise exceptions.FileEncryptionError("test")
