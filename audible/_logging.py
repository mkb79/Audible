import logging
import pathlib
from typing import Union


LEVELS = {
    "debug": logging.DEBUG,
    "info": logging.INFO,
    "warn": logging.WARNING,
    "warning": logging.WARNING,
    "error": logging.ERROR,
    "critical": logging.CRITICAL
}


log_formatter = logging.Formatter(("%(asctime)s %(levelname)s [%(name)s] "
                                   "%(filename)s:%(lineno)d: %(message)s"))

logger = logging.getLogger("audible")
logger.setLevel(logging.CRITICAL)
logging.captureWarnings(True)


def set_global_level(level: Union[str, int]) -> None:
    """Set logging level for the main logger."""
    if isinstance(level, str):
        level = level.lower().strip()
        level = LEVELS.get(level, logging.NOTSET)
    elif not isinstance(level, int):
        raise TypeError((f"Level is from type {type(level)} but only "
                         f"str and int are allowed."))

    logger.setLevel(level)
    logger.log(logging.INFO, "set logging threshold to \"%s\"",
               logging.getLevelName(logger.level))


def set_console_logger(level: Union[str, int] = 0) -> None:
    """Set logging level for the stream handler."""
    stream_handler = logging.StreamHandler()
    stream_handler.setFormatter(log_formatter)
    stream_handler.set_name("ConsoleLogger")
    logger.addHandler(stream_handler)
    _setLevel(stream_handler, level)


def set_file_logger(filename: str, level: Union[str, int] = 0) -> None:
    """Set logging level and filename for the file handler."""
    try:
        filename = pathlib.Path(filename)
    except NotImplementedError:
        filename = pathlib.WindowsPath(filename)

    file_handler = logging.FileHandler(filename)
    file_handler.setFormatter(log_formatter)
    file_handler.set_name("FileLogger")
    logger.addHandler(file_handler)
    _setLevel(file_handler, level)


def _setLevel(handler, level: Union[str, int]) -> None:
    if isinstance(level, str):
        level = level.lower().strip()
        level = LEVELS.get(level, logging.NOTSET)
    elif not isinstance(level, int):
        raise TypeError((f"Level is from type {type(level)} but only "
                         f"str and int are allowed."))
        
    handler.setLevel(level)
    if handler.level < logger.level or logger.level == 0:
        logger.setLevel(handler.level)
    logger.log(logging.INFO, (f"set logging threshold for \"{handler.name}\" "
                              f"to \"{logging.getLevelName(handler.level)}\""))
