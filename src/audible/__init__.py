from importlib.metadata import version

from ._logging import log_helper
from .auth import Authenticator
from .client import AsyncClient, Client
from .login_service import ChallengeHandler, LoginResult, LoginService
from .registration_service import RegistrationResult, RegistrationService


__version__ = version("audible")

__all__ = [
    "AsyncClient",
    "Authenticator",
    "ChallengeHandler",
    "Client",
    "LoginResult",
    "LoginService",
    "RegistrationResult",
    "RegistrationService",
    "__version__",
    "log_helper",
]
