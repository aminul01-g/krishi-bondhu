import logging
import sys
import structlog
from typing import Any

def configure_logging():
    """
    Configures structured logging for the application.
    Uses JSON output for production and colorful console output for development.
    """
    # Shared processors
    shared_processors = [
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
    ]

    structlog.configure(
        processors=shared_processors + [
            structlog.dev.ConsoleRenderer() # Default to console for dev. In prod, this would be JSON renderer.
        ],
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(),
        wrapper_class=structlog.BoundLogger,
        cache_logger_on_first_use=True,
    )

def get_logger(name: str) -> structlog.BoundLogger:
    """Returns a structured logger for the given module name."""
    return structlog.get_logger(name)

# Initialize logging on module load
configure_logging()
