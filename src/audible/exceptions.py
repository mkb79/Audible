class RequestError(Exception):
    """Base class for all errors"""


class StatusError(RequestError):
    """
    Base class for all errors except NotResponding and
    RatelimitDetectedError
    """

    def __init__(self, resp, data):
        self.response = resp
        self.code = getattr(resp, 'status_code')
        self.method = getattr(resp, 'method', None)
        self.reason = resp.reason_phrase
        if isinstance(data, dict):
            self.error = data.get('error')
            if 'message' in data:
                self.error = data.get('message')
        else:
            self.error = data
        self.fmt = '{0.reason} ({0.code}): {0.error}'.format(self)
        super().__init__(self.fmt)


class NotResponding(RequestError):
    """Raised if the API request timed out"""

    def __init__(self):
        self.code = 504
        self.error = 'API request timed out, please be patient.'
        super().__init__(self.error)


class NetworkError(RequestError):
    """Raised if there is an issue with the network
    (i.e. requests.ConnectionError)
    """

    def __init__(self):
        self.code = 503
        self.error = 'Network down.'
        super().__init__(self.error)


class BadRequest(StatusError):
    """Raised when status code 400 is returned.
    Typically when at least one search parameter
    was not provided
    """


class NotFoundError(StatusError):
    """Raised if no result is found"""


class ServerError(StatusError):
    """Raised if the api service is having issues"""


class Unauthorized(StatusError):
    """Raised if you passed invalid credentials."""


class RatelimitError(StatusError):
    """Raised if ratelimit is hit"""


class UnexpectedError(StatusError):
    """Raised if the error was not caught"""


class AuthFlowError(Exception):
    """Raised if no auth method available"""


class NoRefreshToken(Exception):
    """Raised if refresh token is needed but not provided"""


class FileEncryptionError(Exception):
    """Raised if something is wrong with file encryption"""
