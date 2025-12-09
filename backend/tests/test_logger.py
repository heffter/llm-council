"""Unit tests for logger module."""

import pytest
import json
from datetime import datetime
from backend.logger import StructuredLogger, LogLevel, get_logger


class TestStructuredLogger:
    """Tests for StructuredLogger class."""

    def test_info_log_format(self, capsys):
        """Info logs should have correct JSON format."""
        logger = StructuredLogger("test")
        logger.info("Test message", key1="value1", key2="value2")

        captured = capsys.readouterr()
        log_entry = json.loads(captured.out)

        assert log_entry["level"] == "info"
        assert log_entry["message"] == "Test message"
        assert log_entry["name"] == "test"
        assert log_entry["key1"] == "value1"
        assert log_entry["key2"] == "value2"
        assert "timestamp" in log_entry

    def test_error_log_format(self, capsys):
        """Error logs should have correct JSON format."""
        logger = StructuredLogger("test")
        logger.error("Error occurred", error_code=500)

        captured = capsys.readouterr()
        log_entry = json.loads(captured.err)

        assert log_entry["level"] == "error"
        assert log_entry["message"] == "Error occurred"
        assert log_entry["error_code"] == 500

    def test_warn_log_format(self, capsys):
        """Warn logs should have correct JSON format."""
        logger = StructuredLogger("test")
        logger.warn("Warning message", warning_type="test")

        captured = capsys.readouterr()
        log_entry = json.loads(captured.err)

        assert log_entry["level"] == "warn"
        assert log_entry["message"] == "Warning message"
        assert log_entry["warning_type"] == "test"

    def test_timestamp_iso8601_format(self, capsys):
        """Timestamp should be in ISO-8601 format with Z suffix."""
        logger = StructuredLogger("test")
        logger.info("Test")

        captured = capsys.readouterr()
        log_entry = json.loads(captured.out)

        # Should be valid ISO-8601
        timestamp = log_entry["timestamp"]
        assert timestamp.endswith("Z")
        # Should be parseable
        datetime.fromisoformat(timestamp.replace("Z", "+00:00"))

    def test_api_key_redacted(self, capsys):
        """API keys should be redacted in logs."""
        logger = StructuredLogger("test")
        logger.info("Request made", api_key="sk-1234567890abcdef")

        captured = capsys.readouterr()
        log_entry = json.loads(captured.out)

        # Should show last 4 chars only
        assert log_entry["api_key"] == "***cdef"
        # Original value should not appear
        assert "sk-1234567890abcdef" not in captured.out

    def test_token_redacted(self, capsys):
        """Tokens should be redacted in logs."""
        logger = StructuredLogger("test")
        logger.info("Auth request", token="bearer_token_12345678")

        captured = capsys.readouterr()
        log_entry = json.loads(captured.out)

        assert log_entry["token"] == "***5678"

    def test_secret_redacted(self, capsys):
        """Secrets should be redacted in logs."""
        logger = StructuredLogger("test")
        logger.info("Config loaded", secret="my_secret_value")

        captured = capsys.readouterr()
        log_entry = json.loads(captured.out)

        assert log_entry["secret"] == "***alue"

    def test_password_redacted(self, capsys):
        """Passwords should be redacted in logs."""
        logger = StructuredLogger("test")
        logger.info("Login attempt", password="secure_password_123")

        captured = capsys.readouterr()
        log_entry = json.loads(captured.out)

        assert log_entry["password"] == "***_123"

    def test_short_secret_redacted(self, capsys):
        """Short secrets (less than 4 chars) should be fully redacted."""
        logger = StructuredLogger("test")
        logger.info("Test", api_key="abc")

        captured = capsys.readouterr()
        log_entry = json.loads(captured.out)

        assert log_entry["api_key"] == "***"

    def test_case_insensitive_redaction(self, capsys):
        """Redaction should work case-insensitively."""
        logger = StructuredLogger("test")
        logger.info("Test", API_KEY="secret123", Token="token456")

        captured = capsys.readouterr()
        log_entry = json.loads(captured.out)

        # "secret123" -> last 4 chars are "t123"
        assert log_entry["API_KEY"] == "***t123"
        # "token456" -> last 4 chars are "n456"
        assert log_entry["Token"] == "***n456"

    def test_non_secret_fields_not_redacted(self, capsys):
        """Regular fields should not be redacted."""
        logger = StructuredLogger("test")
        logger.info("Test", user="john_doe", provider="openai", model="gpt-4")

        captured = capsys.readouterr()
        log_entry = json.loads(captured.out)

        assert log_entry["user"] == "john_doe"
        assert log_entry["provider"] == "openai"
        assert log_entry["model"] == "gpt-4"

    def test_custom_logger_name(self, capsys):
        """Logger should use custom name."""
        logger = StructuredLogger("custom-service")
        logger.info("Test")

        captured = capsys.readouterr()
        log_entry = json.loads(captured.out)

        assert log_entry["name"] == "custom-service"

    def test_multiple_fields(self, capsys):
        """Should handle multiple custom fields."""
        logger = StructuredLogger("test")
        logger.info(
            "Request",
            provider="openai",
            model="gpt-4",
            role="council",
            conversation_id="12345"
        )

        captured = capsys.readouterr()
        log_entry = json.loads(captured.out)

        assert log_entry["provider"] == "openai"
        assert log_entry["model"] == "gpt-4"
        assert log_entry["role"] == "council"
        assert log_entry["conversation_id"] == "12345"

    def test_log_level_enum_values(self):
        """LogLevel enum should have correct values."""
        assert LogLevel.INFO.value == "info"
        assert LogLevel.WARN.value == "warn"
        assert LogLevel.ERROR.value == "error"


class TestGetLogger:
    """Tests for get_logger function."""

    def test_returns_structured_logger(self):
        """get_logger should return a StructuredLogger instance."""
        logger = get_logger()
        assert isinstance(logger, StructuredLogger)

    def test_default_logger_name(self):
        """Default logger should have 'llm-council' name."""
        logger = get_logger()
        assert logger.name == "llm-council"

    def test_singleton_behavior(self):
        """get_logger should return the same instance."""
        logger1 = get_logger()
        logger2 = get_logger()
        assert logger1 is logger2
