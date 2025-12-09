"""Structured logging for the application."""

import json
import sys
from datetime import datetime
from typing import Any, Dict, Optional
from enum import Enum


class LogLevel(str, Enum):
    """Log levels."""
    DEBUG = "debug"
    INFO = "info"
    WARN = "warn"
    ERROR = "error"


class StructuredLogger:
    """Structured logger that outputs JSON formatted logs."""

    def __init__(self, name: str = "llm-council"):
        """
        Initialize structured logger.

        Args:
            name: Logger name
        """
        self.name = name
        self._redact_patterns = ["api_key", "token", "secret", "password"]

    def _format_log(
        self,
        level: LogLevel,
        message: str,
        **fields: Any
    ) -> str:
        """
        Format log entry as JSON.

        Args:
            level: Log level
            message: Log message
            **fields: Additional structured fields

        Returns:
            JSON formatted log string
        """
        log_entry = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "level": level.value,
            "name": self.name,
            "message": message,
        }

        # Add additional fields, redacting sensitive data
        for key, value in fields.items():
            if any(pattern in key.lower() for pattern in self._redact_patterns):
                # Redact sensitive fields
                if isinstance(value, str) and len(value) > 4:
                    log_entry[key] = f"***{value[-4:]}"
                else:
                    log_entry[key] = "***"
            else:
                log_entry[key] = value

        return json.dumps(log_entry)

    def debug(self, message: str, **fields: Any) -> None:
        """Log debug message."""
        print(self._format_log(LogLevel.DEBUG, message, **fields), file=sys.stdout)

    def info(self, message: str, **fields: Any) -> None:
        """Log info message."""
        print(self._format_log(LogLevel.INFO, message, **fields), file=sys.stdout)

    def warn(self, message: str, **fields: Any) -> None:
        """Log warning message."""
        print(self._format_log(LogLevel.WARN, message, **fields), file=sys.stderr)

    def error(self, message: str, **fields: Any) -> None:
        """Log error message."""
        print(self._format_log(LogLevel.ERROR, message, **fields), file=sys.stderr)


# Global logger instance
_logger: Optional[StructuredLogger] = None


def get_logger(name: str = "llm-council") -> StructuredLogger:
    """
    Get or create global logger instance.

    Args:
        name: Logger name

    Returns:
        StructuredLogger instance
    """
    global _logger
    if _logger is None:
        _logger = StructuredLogger(name)
    return _logger
