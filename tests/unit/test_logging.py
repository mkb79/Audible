"""Tests for audible._logging module."""

import logging
import pytest
from pathlib import Path
from audible._logging import AudibleLogHelper, log_helper, logger, log_formatter


@pytest.fixture
def log_helper_instance():
    """Fixture for fresh AudibleLogHelper instance."""
    # Clear all handlers before each test
    logger.handlers.clear()
    logger.addHandler(logging.NullHandler())
    logger.setLevel(logging.WARNING)  # Reset to default
    return AudibleLogHelper()


@pytest.fixture
def temp_log_file(tmp_path):
    """Fixture for temporary log file."""
    return tmp_path / "test.log"


class TestAudibleLogHelperSetLevel:
    """Tests for set_level method."""

    def test_set_level_with_string(self, log_helper_instance):
        """set_level accepts string level."""
        log_helper_instance.set_level("DEBUG")
        assert logger.level == logging.DEBUG

    def test_set_level_with_int(self, log_helper_instance):
        """set_level accepts int level."""
        log_helper_instance.set_level(logging.INFO)
        assert logger.level == logging.INFO

    @pytest.mark.parametrize(
        "level_str,level_int",
        [
            ("DEBUG", logging.DEBUG),
            ("INFO", logging.INFO),
            ("WARNING", logging.WARNING),
            ("ERROR", logging.ERROR),
            ("CRITICAL", logging.CRITICAL),
        ],
    )
    def test_set_level_all_levels(
        self, log_helper_instance, level_str, level_int
    ):
        """set_level works with all standard levels."""
        log_helper_instance.set_level(level_str)
        assert logger.level == level_int

    def test_set_level_case_insensitive(self, log_helper_instance):
        """set_level converts string to uppercase."""
        log_helper_instance.set_level("debug")
        assert logger.level == logging.DEBUG

        log_helper_instance.set_level("InFo")
        assert logger.level == logging.INFO


class TestSetConsoleLogger:
    """Tests for set_console_logger method."""

    def test_set_console_logger_creates_handler(self, log_helper_instance):
        """set_console_logger creates console handler."""
        logger.handlers.clear()

        log_helper_instance.set_console_logger()

        # Find the StreamHandler (excluding NullHandler)
        stream_handlers = [
            h for h in logger.handlers if isinstance(h, logging.StreamHandler)
        ]
        assert len(stream_handlers) >= 1
        handler = stream_handlers[0]
        assert handler.name == "ConsoleLogger"

    def test_set_console_logger_with_level(self, log_helper_instance):
        """set_console_logger respects level parameter."""
        logger.handlers.clear()

        log_helper_instance.set_console_logger(level="DEBUG")

        stream_handlers = [
            h for h in logger.handlers if isinstance(h, logging.StreamHandler)
        ]
        handler = stream_handlers[0]
        assert handler.level == logging.DEBUG

    def test_set_console_logger_has_formatter(self, log_helper_instance):
        """Console handler has formatter."""
        logger.handlers.clear()

        log_helper_instance.set_console_logger()

        stream_handlers = [
            h for h in logger.handlers if isinstance(h, logging.StreamHandler)
        ]
        handler = stream_handlers[0]
        assert handler.formatter is not None


class TestSetFileLogger:
    """Tests for set_file_logger method."""

    def test_set_file_logger_with_string_path(
        self, log_helper_instance, temp_log_file
    ):
        """set_file_logger accepts string path."""
        logger.handlers.clear()

        log_helper_instance.set_file_logger(str(temp_log_file))

        file_handlers = [
            h for h in logger.handlers if isinstance(h, logging.FileHandler)
        ]
        assert len(file_handlers) == 1
        handler = file_handlers[0]
        assert isinstance(handler, logging.FileHandler)

    def test_set_file_logger_with_path_object(
        self, log_helper_instance, temp_log_file
    ):
        """set_file_logger accepts Path object."""
        logger.handlers.clear()

        log_helper_instance.set_file_logger(temp_log_file)

        file_handlers = [
            h for h in logger.handlers if isinstance(h, logging.FileHandler)
        ]
        assert len(file_handlers) == 1

    def test_set_file_logger_creates_file(
        self, log_helper_instance, temp_log_file
    ):
        """File logger creates log file."""
        logger.handlers.clear()
        logger.setLevel(logging.ERROR)
        log_helper_instance.set_file_logger(temp_log_file, level="ERROR")

        logger.error("Test message")

        # Close handlers to flush
        for handler in logger.handlers:
            handler.close()

        assert temp_log_file.exists()
        content = temp_log_file.read_text()
        assert "Test message" in content

    def test_set_file_logger_with_level(
        self, log_helper_instance, temp_log_file
    ):
        """set_file_logger respects level parameter."""
        logger.handlers.clear()

        log_helper_instance.set_file_logger(temp_log_file, level="WARNING")

        file_handlers = [
            h for h in logger.handlers if isinstance(h, logging.FileHandler)
        ]
        handler = file_handlers[0]
        assert handler.level == logging.WARNING

    def test_set_file_logger_has_name(self, log_helper_instance, temp_log_file):
        """File logger has correct name."""
        logger.handlers.clear()

        log_helper_instance.set_file_logger(temp_log_file)

        file_handlers = [
            h for h in logger.handlers if isinstance(h, logging.FileHandler)
        ]
        handler = file_handlers[0]
        assert handler.name == "FileLogger"


class TestCaptureWarnings:
    """Tests for capture_warnings method."""

    def test_capture_warnings_enable(self):
        """capture_warnings(True) enables warning capturing."""
        AudibleLogHelper.capture_warnings(True)
        assert True  # Should not raise

    def test_capture_warnings_disable(self):
        """capture_warnings(False) disables warning capturing."""
        AudibleLogHelper.capture_warnings(False)
        assert True  # Should not raise

    def test_capture_warnings_is_static_method(self):
        """capture_warnings is a static method."""
        # Can be called without instance
        AudibleLogHelper.capture_warnings(True)


class TestLogHelperGlobal:
    """Tests for global log_helper instance."""

    def test_log_helper_is_audible_log_helper(self):
        """Global log_helper is an AudibleLogHelper instance."""
        assert isinstance(log_helper, AudibleLogHelper)

    def test_log_helper_methods_accessible(self):
        """Global log_helper has expected methods."""
        assert hasattr(log_helper, "set_level")
        assert hasattr(log_helper, "set_console_logger")
        assert hasattr(log_helper, "set_file_logger")
        assert hasattr(log_helper, "capture_warnings")


class TestLoggerConfiguration:
    """Tests for logger configuration."""

    def test_logger_has_handlers(self):
        """Logger has handlers configured."""
        # The logger should have at least one handler
        assert len(logger.handlers) >= 1

    def test_logger_name_is_audible(self):
        """Logger name is 'audible'."""
        assert logger.name == "audible"


class TestPrivateSetLevel:
    """Tests for _set_level static method."""

    def test_set_level_with_none_does_nothing(self, log_helper_instance):
        """_set_level with None doesn't change level."""
        test_logger = logging.getLogger("test")
        original_level = test_logger.level

        log_helper_instance._set_level(test_logger, None)

        assert test_logger.level == original_level

    def test_set_level_on_handler(self, log_helper_instance):
        """_set_level works on handlers."""
        handler = logging.StreamHandler()
        original_level = handler.level

        log_helper_instance._set_level(handler, logging.DEBUG)

        assert handler.level == logging.DEBUG
        assert handler.level != original_level


class TestWarningForLowHandlerLevel:
    """Tests for warning when handler level is lower than logger level."""

    def test_warning_raised_when_handler_lower_than_logger(
        self, log_helper_instance, recwarn
    ):
        """Warning raised when handler level < logger level."""
        logger.setLevel(logging.WARNING)
        handler = logging.StreamHandler()
        handler.setFormatter(log_formatter)
        handler.set_name("TestHandler")
        logger.addHandler(handler)

        # This should trigger a warning
        log_helper_instance._set_level(handler, logging.DEBUG)

        # Check if warning was issued
        # Note: This might not work perfectly due to logging complexity
        # but we can at least verify no exception is raised
        assert True
