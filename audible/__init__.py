from .client import AudibleAPI
from .client import DeprecatedClient as Client  # backward comp
from .auth import LoginAuthenticator, FileAuthenticator
from .cryptography import encrypt_metadata, decrypt_metadata
from .localization import Locale, autodetect_locale
from .localization import custom_locale as custom_local  # backward comp
from ._logging import set_file_logger, set_console_logger


VERSION = (0, 2, 0)
__version__ = ".".join(map(str, VERSION))

__all__ = ["AudibleAPI", "LoginAuthenticator", "FileAuthenticator",
           "encrypt_metadata", "decrypt_metadata", "Locale",
           "autodetect_locale", "set_file_logger", "set_console_logger",
           "__version__", "Client", "custom_local"]

__author__ = "mkb79"
__email__ = "mkb79@hackitall.de"
__status__ = "Development"
