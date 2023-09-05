import logging
import pathlib
from typing import Optional, Union
from warnings import warn


logger = logging.getLogger("audible")
logger.addHandler(logging.NullHandler())

log_formatter = logging.Formatter(
    "%(asctime)s %(levelname)s [%(name)s] %(filename)s:%(lineno)d: %(message)s"
)


class AudibleLogHelper:
    def set_level(self, level: Union[str, int]) -> None:
        """Set logging level for the audible package."""
        self._set_level(logger, level)

    @staticmethod
    def _set_level(obj, level: Optional[Union[str, int]]) -> None:
        if level:
            level = level.upper() if isinstance(level, str) else level
            obj.setLevel(level)

        level_name = logging.getLevelName(obj.level)
        logger.info("set log level for %s to: %s", obj.name, level_name)

        if 0 < obj.level < logger.level:
            warn(
                f"{obj.name} level is lower than {logger.name} logger level",
                stacklevel=1,
            )

    def _set_handler(self, handler, name, level):
        handler.setFormatter(log_formatter)
        handler.set_name(name)
        logger.addHandler(handler)
        self._set_level(handler, level)

    def set_console_logger(self, level: Optional[Union[str, int]] = None) -> None:
        """Set up a console logger to the audible package."""
        handler = logging.StreamHandler()
        # noinspection PyTypeChecker
        self._set_handler(handler, "ConsoleLogger", level)

    def set_file_logger(
        self, filename: str, level: Optional[Union[str, int]] = None
    ) -> None:
        """Set up a file logger to the audible package."""
        filename = pathlib.Path(filename)
        handler = logging.FileHandler(filename)
        # noinspection PyTypeChecker
        self._set_handler(handler, "FileLogger", level)

    @staticmethod
    def capture_warnings(status: bool = True) -> None:
        """Lets the logger capture warnings."""
        logging.captureWarnings(status)
        logger.info("Capture warnings %s", "activated" if status else "deactivated")


log_helper = AudibleLogHelper()
