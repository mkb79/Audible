# -*- coding: utf-8 -*-
import logging
import os

from ._logging import log_helper
from ._version import __version__
from .auth import Authenticator
from .client import Client, AsyncClient

__all__ = [
    "__version__", "Authenticator", "log_helper", "Client", "AsyncClient"
]

logger = logging.getLogger(__name__)


try:
    if 'DISABLE_UVLOOP' in os.environ:
        msg = "uvloop is disabled"
        logger.debug(msg)
        raise ImportError
    import uvloop
    uvloop.install()
    logger.debug("using uvloop loop")
except ImportError:
    uvloop = None
    logger.debug("using asyncio loop")
