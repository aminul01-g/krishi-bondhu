"""
Shared rate limiter.

Defined in its own module so both ``app.main`` (which registers it on the app
and adds SlowAPIMiddleware) and individual routers (e.g. auth) can import the
*same* limiter instance without a circular import through ``app.main``.
"""

import os

# ``slowapi`` is an OPTIONAL dependency. When it is not installed (e.g. a
# minimal/offline environment), rate limiting simply degrades to a no-op so the
# app still imports and runs. The real Limiter is used whenever the package is
# present.
try:
    from slowapi import Limiter
    from slowapi.util import get_remote_address
    _HAVE_SLOWAPI = True
except ImportError:  # pragma: no cover - exercised only without slowapi
    Limiter = None
    get_remote_address = None
    _HAVE_SLOWAPI = False

# A generous global default catches abusive bursts on every route; hot/sensitive
# endpoints add stricter per-route overrides via ``@limiter.limit(...)``.
# Tune via RATE_LIMIT_DEFAULT (e.g. "240/minute"); set to "" to disable defaults.
_default_rate_limit = os.getenv("RATE_LIMIT_DEFAULT", "240/minute").strip()
DEFAULT_LIMITS = [_default_rate_limit] if _default_rate_limit else []


if _HAVE_SLOWAPI:
    limiter = Limiter(key_func=get_remote_address, default_limits=DEFAULT_LIMITS)
else:
    # No-op stand-in so routers can still use ``@limiter.limit(...)`` /
    # ``@limiter.exempt`` decorators without importing slowapi. Each decorator
    # simply returns the wrapped function untouched.
    class _NullLimiter:
        def limit(self, *args, **kwargs):
            def decorator(func):
                return func
            return decorator

        def exempt(self, func):
            return func

    limiter = _NullLimiter()
