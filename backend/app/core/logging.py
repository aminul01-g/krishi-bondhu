import logging
import sys

# ``structlog`` is an OPTIONAL dependency. When it is not installed (e.g. a
# minimal/offline environment), we transparently fall back to the stdlib
# ``logging`` module so every ``get_logger(name)`` caller keeps working with the
# same ``.info()/.warning()/.error()/.exception()`` interface.
try:
    import structlog
    _HAVE_STRUCTLOG = True
except ImportError:  # pragma: no cover - exercised only without structlog
    structlog = None
    _HAVE_STRUCTLOG = False

from typing import Any

def configure_logging():
    """
    Configures structured logging for the application.
    Uses JSON output for production and colorful console output for development.

    No-op when structlog is unavailable (stdlib logging handles output).
    """
    if not _HAVE_STRUCTLOG:
        return
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

def get_logger(name: str):
    """Returns a logger for the given module name.

    Returns a structlog BoundLogger when structlog is installed, otherwise a
    stdlib :class:`logging.Logger` — both expose the same call surface used
    across the app (``.info/.warning/.error/.exception/.debug``).
    """
    if _HAVE_STRUCTLOG:
        return structlog.get_logger(name)
    return logging.getLogger(name)

# Initialize logging on module load
configure_logging()
