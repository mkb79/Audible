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
        """Set logging level for the main logger."""
        self._set_level(logger, level)

    def _set_level(self, obj, level: Optional[Union[str, int]]) -> None:
        if level:
            level = level.upper() if isinstance(level, str) else level
            obj.setLevel(level)

        level_name = logging.getLevelName(obj.level)
        logger.info(f"set log level for {obj.name} to: {level_name}")

        if obj.level > 0 and obj.level < logger.level:
            warn(f"{obj.name} level is lower than {logger.name} logger level")

    def _set_handler(self, handler, name, level):
        handler.setFormatter(log_formatter)
        handler.set_name(name)
        logger.addHandler(handler)
        self._set_level(handler, level)

    def set_console_logger(self,
                           level: Optional[Union[str, int]] = None) -> None:
        """Set logging level for the stream handler."""
        handler = logging.StreamHandler()
        self._set_handler(handler, "ConsoleLogger", level)

    def set_file_logger(
            self, filename: str, level: Optional[Union[str, int]] = None
    ) -> None:
        """Set logging level and filename for the file handler."""
        filename = pathlib.Path(filename)
        handler = logging.FileHandler(filename)
        self._set_handler(handler, "FileLogger", level)

    def capture_warnings(self, status: bool = True) -> None:
        logging.captureWarnings(status)
        logger.info(
            f"Capture warnings {'activated' if status else 'deactivated'}"
        )


log_helper = AudibleLogHelper()
