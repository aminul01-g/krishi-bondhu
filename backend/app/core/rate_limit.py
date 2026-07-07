"""
Shared rate limiter.

Defined in its own module so both ``app.main`` (which registers it on the app
and adds SlowAPIMiddleware) and individual routers (e.g. auth) can import the
*same* limiter instance without a circular import through ``app.main``.
"""

import os

from slowapi import Limiter
from slowapi.util import get_remote_address

# A generous global default catches abusive bursts on every route; hot/sensitive
# endpoints add stricter per-route overrides via ``@limiter.limit(...)``.
# Tune via RATE_LIMIT_DEFAULT (e.g. "240/minute"); set to "" to disable defaults.
_default_rate_limit = os.getenv("RATE_LIMIT_DEFAULT", "240/minute").strip()
DEFAULT_LIMITS = [_default_rate_limit] if _default_rate_limit else []

limiter = Limiter(key_func=get_remote_address, default_limits=DEFAULT_LIMITS)
