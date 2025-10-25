"""Tests for helper functions in audible.client."""

from __future__ import annotations

import httpx
import pytest

from audible.client import (
    convert_response_content,
    default_response_callback,
    raise_for_status,
)
from audible.exceptions import (
    BadRequest,
    NotFoundError,
    RatelimitError,
    ServerError,
    Unauthorized,
    UnexpectedError,
)


def make_response(
    status_code: int,
    *,
    json_data: dict[str, object] | None = None,
    text: str | None = None,
) -> httpx.Response:
    request = httpx.Request("GET", "https://example.com/api")
    if json_data is not None:
        return httpx.Response(status_code, json=json_data, request=request)
    content = text.encode() if text is not None else b""
    return httpx.Response(status_code, content=content, request=request)


class TestRaiseForStatus:
    """Tests for raise_for_status helper."""

    def test_success_does_not_raise(self) -> None:
        response = make_response(200, json_data={"value": 1})
        assert raise_for_status(response) is None

    def test_bad_request_raises_custom_exception(self) -> None:
        response = make_response(400, json_data={"error": "missing"})
        with pytest.raises(BadRequest):
            raise_for_status(response)

    @pytest.mark.parametrize("status", [401, 403])
    def test_unauthorized_errors(self, status: int) -> None:
        response = make_response(status, text="unauthorized")
        with pytest.raises(Unauthorized):
            raise_for_status(response)

    def test_not_found_error(self) -> None:
        response = make_response(404, json_data={"error": "gone"})
        with pytest.raises(NotFoundError):
            raise_for_status(response)

    def test_ratelimit_error(self) -> None:
        response = make_response(429, json_data={"error": "slow down"})
        with pytest.raises(RatelimitError):
            raise_for_status(response)

    def test_server_error(self) -> None:
        response = make_response(503, json_data={"error": "maintenance"})
        with pytest.raises(ServerError):
            raise_for_status(response)

    def test_unexpected_error(self) -> None:
        response = make_response(500, text="error")
        with pytest.raises(UnexpectedError):
            raise_for_status(response)


class TestConvertResponseContent:
    """Tests for convert_response_content helper."""

    def test_json_content_returns_dict(self) -> None:
        response = make_response(200, json_data={"ok": True})
        assert convert_response_content(response) == {"ok": True}

    def test_text_content_returns_string(self) -> None:
        response = make_response(200, text="plain text")
        assert convert_response_content(response) == "plain text"


class TestDefaultResponseCallback:
    """Tests for default response callback."""

    def test_returns_json_payload(self) -> None:
        response = make_response(200, json_data={"foo": "bar"})
        assert default_response_callback(response) == {"foo": "bar"}

    def test_raises_for_http_error(self) -> None:
        response = make_response(404, json_data={"error": "missing"})
        with pytest.raises(NotFoundError):
            default_response_callback(response)
