"""Standardized logging system (FR-018).

Provides three output modes:
- Human mode: [LEVEL] message (colored if TTY)
- Verbose mode: [LEVEL][HH:MM:SS] message
- CI/JSON mode: {"level":"...","ts":"...","msg":"..."}
"""

import json
import logging
import sys
from datetime import UTC, datetime
from enum import Enum
from typing import Any, TextIO


class LogMode(Enum):
    """Logging output mode."""

    HUMAN = "human"
    VERBOSE = "verbose"
    JSON = "json"


# ANSI color codes
class Colors:
    """ANSI color codes for terminal output."""

    RESET = "\033[0m"
    GREEN = "\033[32m"
    YELLOW = "\033[33m"
    RED = "\033[31m"
    CYAN = "\033[36m"
    GRAY = "\033[90m"


# Level to color mapping
LEVEL_COLORS = {
    logging.DEBUG: Colors.GRAY,
    logging.INFO: Colors.GREEN,
    logging.WARNING: Colors.YELLOW,
    logging.ERROR: Colors.RED,
    logging.CRITICAL: Colors.RED,
}


def _is_tty(stream: TextIO | None = None) -> bool:
    """Check if the stream is a TTY (supports colors)."""
    if stream is None:
        stream = sys.stdout
    return hasattr(stream, "isatty") and stream.isatty()


class HumanFormatter(logging.Formatter):
    """Formatter for human-readable output.

    Format: [LEVEL] message
    With optional colors when output is a TTY.
    """

    def __init__(self, use_colors: bool = True) -> None:
        """Initialize human formatter.

        Args:
            use_colors: Whether to use ANSI colors
        """
        super().__init__()
        self.use_colors = use_colors and _is_tty()

    def format(self, record: logging.LogRecord) -> str:
        """Format a log record."""
        level_name = record.levelname

        if self.use_colors:
            color = LEVEL_COLORS.get(record.levelno, Colors.RESET)
            return f"{color}[{level_name}]{Colors.RESET} {record.getMessage()}"
        else:
            return f"[{level_name}] {record.getMessage()}"


class VerboseFormatter(logging.Formatter):
    """Formatter for verbose output with timestamps.

    Format: [LEVEL][HH:MM:SS] message
    With optional colors when output is a TTY.
    """

    def __init__(self, use_colors: bool = True) -> None:
        """Initialize verbose formatter.

        Args:
            use_colors: Whether to use ANSI colors
        """
        super().__init__()
        self.use_colors = use_colors and _is_tty()

    def format(self, record: logging.LogRecord) -> str:
        """Format a log record with timestamp."""
        level_name = record.levelname
        timestamp = datetime.now().strftime("%H:%M:%S")

        if self.use_colors:
            color = LEVEL_COLORS.get(record.levelno, Colors.RESET)
            return f"{color}[{level_name}]{Colors.RESET}[{timestamp}] {record.getMessage()}"
        else:
            return f"[{level_name}][{timestamp}] {record.getMessage()}"


class JSONFormatter(logging.Formatter):
    """Formatter for JSON lines output (machine-readable).

    Format: {"level":"INFO","ts":"2026-01-31T19:45:23Z","msg":"..."}
    """

    def format(self, record: logging.LogRecord) -> str:
        """Format a log record as JSON."""
        log_entry: dict[str, Any] = {
            "level": record.levelname,
            "ts": datetime.now(UTC).isoformat(),
            "msg": record.getMessage(),
        }

        # Add extra fields if present
        if hasattr(record, "extra_data"):
            log_entry.update(record.extra_data)

        return json.dumps(log_entry)


class chronicleLogger(logging.Logger):
    """Custom logger with structured logging support."""

    def structured(
        self,
        level: int,
        msg: str,
        **kwargs: Any,
    ) -> None:
        """Log a message with additional structured data.

        Args:
            level: Log level
            msg: Log message
            **kwargs: Additional data to include in JSON output
        """
        record = self.makeRecord(
            self.name,
            level,
            "(unknown)",
            0,
            msg,
            (),
            None,
        )
        if kwargs:
            record.extra_data = kwargs  # type: ignore
        self.handle(record)


# Set custom logger class
logging.setLoggerClass(chronicleLogger)


def get_logger(name: str = "chronicle") -> chronicleLogger:
    """Get an chronicle logger instance.

    Args:
        name: Logger name

    Returns:
        Configured chronicleLogger instance
    """
    return logging.getLogger(name)  # type: ignore


def setup_logging(
    mode: LogMode = LogMode.HUMAN,
    level: int = logging.INFO,
    stream: TextIO | None = None,
) -> None:
    """Configure logging with the specified mode.

    Args:
        mode: Output mode (human, verbose, json)
        level: Minimum log level
        stream: Output stream (default: stdout for info, stderr for errors)
    """
    logger = logging.getLogger("chronicle")
    logger.setLevel(level)

    # Remove existing handlers
    logger.handlers.clear()

    # Select formatter based on mode
    use_colors = _is_tty(stream)

    if mode == LogMode.JSON:
        formatter: logging.Formatter = JSONFormatter()
    elif mode == LogMode.VERBOSE:
        formatter = VerboseFormatter(use_colors=use_colors)
    else:
        formatter = HumanFormatter(use_colors=use_colors)

    # Create handler
    handler = logging.StreamHandler(stream or sys.stdout)
    handler.setFormatter(formatter)
    logger.addHandler(handler)


def configure_from_cli(
    verbose: bool = False,
    quiet: bool = False,
    ci: bool = False,
) -> None:
    """Configure logging based on CLI flags.

    Args:
        verbose: Enable verbose mode with timestamps
        quiet: Suppress info messages (warnings and errors only)
        ci: Enable JSON output for CI/CD
    """
    # Determine mode
    if ci:
        mode = LogMode.JSON
    elif verbose:
        mode = LogMode.VERBOSE
    else:
        mode = LogMode.HUMAN

    # Determine level
    if quiet:
        level = logging.WARNING
    elif verbose:
        level = logging.DEBUG
    else:
        level = logging.INFO

    setup_logging(mode=mode, level=level)
