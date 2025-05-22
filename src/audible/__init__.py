from importlib.metadata import version

from ._logging import log_helper
from .auth import Authenticator
from .client import AsyncClient, Client


__version__ = version("audible")

__all__ = ["AsyncClient", "Authenticator", "Client", "__version__", "log_helper"]
