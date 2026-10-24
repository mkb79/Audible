from typing import TYPE_CHECKING, Any


if TYPE_CHECKING:
    import httpx


class AudibleError(Exception):
    """Base class for all errors."""


class RequestError(AudibleError):
    """Base class for all request errors."""


class StatusError(RequestError):
    """Base class for all errors except NotResponding and RatelimitDetectedError."""

    def __init__(self, resp: "httpx.Response", data: Any) -> None:
        self.response = resp
        self.code = resp.status_code
        self.method = getattr(resp, "method", None)
        self.reason = resp.reason_phrase
        if isinstance(data, dict):
            self.error = data.get("error")
            if "message" in data:
                self.error = data.get("message")
        else:
            self.error = data
        self.fmt = f"{self.reason} ({self.code}): {self.error}"
        super().__init__(self.fmt)


class NotResponding(RequestError):
    """Raised if the API request timed out."""

    def __init__(self) -> None:
        self.code = 504
        self.error = "API request timed out, please be patient."
        super().__init__(self.error)


class NetworkError(RequestError):
    """Raised if there is an issue with the network (i.e. requests.ConnectionError)."""

    def __init__(self) -> None:
        self.code = 503
        self.error = "Network down."
        super().__init__(self.error)


class BadRequest(StatusError):
    """Raised when status code 400 is returned.

    Typically, when at least one search parameter was not provided.
    """


class NotFoundError(StatusError):
    """Raised if no result is found."""


class ServerError(StatusError):
    """Raised if the api service is having issues."""


class Unauthorized(StatusError):
    """Raised if you passed invalid credentials."""


class RatelimitError(StatusError):
    """Raised if ratelimit is hit."""


class UnexpectedError(StatusError):
    """Raised if the error was not caught."""


class AuthFlowError(AudibleError):
    """Raised if no auth method available."""


class NoRefreshToken(AudibleError):
    """Raised if refresh token is needed but not provided."""


class FileEncryptionError(AudibleError):
    """Raised if something is wrong with file encryption."""


class LoginError(AudibleError):
    """Base class for errors while registering a new device."""


class LoginStateError(LoginError):
    """Raised if a login method is called in a state that does not allow it."""


class LoginFailedError(LoginError):
    """Raised if Amazon or Audible rejects the login or answers unexpectedly.

    The arguments ``status_code`` and ``error_code`` are kept as attributes
    of the same name.

    Args:
        message: What went wrong.
        status_code: The HTTP status code of the rejecting response, if any.
        error_code: The error code Amazon sent with the response, if any.
    """

    def __init__(
        self,
        message: str,
        *,
        status_code: int | None = None,
        error_code: str | None = None,
    ) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.error_code = error_code


class LoginExpiredError(LoginError):
    """Raised if the device code expired before the user confirmed it."""


class LoginAbortedError(LoginError):
    """Raised if the login was cancelled."""
