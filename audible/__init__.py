from .client import Client
from .auth import CertAuth, AccessTokenAuth
from .cryptography import encrypt_metadata, decrypt_metadata
from .localization import custom_locale, Locale, autodetect_locale
from ._logging import set_file_logger, set_console_logger


VERSION = (0, 2, 0)
__version__ = ".".join(map(str, VERSION))

__all__ = ["Client", "custom_locale", "Locale", "autodetect_locale",
           "encrypt_metadata", "decrypt_metadata", "CertAuth",
           "AccessTokenAuth", "__version__", "set_file_logger",
           "set_console_logger"]

__author__ = "mkb79"
__email__ = "mkb79@hackitall.de"
__status__ = "Development"
