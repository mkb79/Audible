# -*- coding: utf-8 -*-

from .client import AudibleAPI
from .client import DeprecatedClient as Client  # backward comp
from .auth import LoginAuthenticator, FileAuthenticator
from .cryptography import encrypt_metadata, decrypt_metadata
from .localization import Locale, autodetect_locale
from .localization import custom_locale as custom_local  # backward comp
from ._logging import set_file_logger, set_console_logger
from ._version import *


__all__ = [
    "__version__", "AudibleAPI", "LoginAuthenticator", "FileAuthenticator",
    "encrypt_metadata", "decrypt_metadata", "Locale", "autodetect_locale",
    "set_file_logger", "set_console_logger", "Client", "custom_local"
]
