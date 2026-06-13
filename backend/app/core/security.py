"""
Password hashing, JWT token management, and security utilities.

Uses bcrypt directly (not via passlib) for maximum compatibility with
bcrypt >= 4.x / 5.x.  Existing ``$2b$...`` hashes remain fully compatible.
"""

import os
import logging
from datetime import datetime, timedelta, timezone
from typing import Any

import bcrypt
from jose import JWTError, jwt

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Application secrets & JWT config
# ---------------------------------------------------------------------------
DEFAULT_SECRET_KEY = "krishibondhu_super_secret_key_change_this_in_production"
SECRET_KEY = os.getenv("SECRET_KEY", DEFAULT_SECRET_KEY)
if SECRET_KEY == DEFAULT_SECRET_KEY:
    logger.warning(
        "SECRET_KEY is not configured. Using an insecure default secret. "
        "Set SECRET_KEY in the environment before deploying to production."
    )
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = int(
    os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "1440")
)  # Default 24 h


# ---------------------------------------------------------------------------
# Bcrypt 72‑byte password limit
# ---------------------------------------------------------------------------
# The bcrypt algorithm only processes the first 72 bytes of a password.
#
#   • bcrypt < 4.1 silently truncated longer inputs.
#   • bcrypt >= 4.1 raises ``ValueError`` instead.
#
# ``_prepare_password()`` normalises any input to ≤ 72 UTF‑8 bytes so
# that the same truncation is applied consistently during **both** hashing
# and verification.
#
# Why this is safe
# ~~~~~~~~~~~~~~~~
# bcrypt has *always* only hashed the first 72 bytes.  Bytes beyond
# position 72 were never part of any stored hash.  Explicit truncation
# is therefore *identical* to the behaviour of every bcrypt hash ever
# created – including those already in the database.
#
# Multi‑byte boundary handling
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# If the 72‑byte cut falls inside a multi‑byte UTF‑8 character, the
# incomplete trailing bytes are dropped (``errors="ignore"``).  The
# resulting string re‑encodes to *fewer* than 72 bytes, which is fine.
#
# Long‑term improvement (not implemented yet)
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# For arbitrarily long passwords without any truncation, consider:
#   • **bcrypt_sha256** – SHA‑256 pre‑hash → always 32 bytes → bcrypt.
#     Requires a lazy‑migration strategy for existing rows.
#   • **argon2** – memory‑hard, no length limit, PHC winner.
#     Can be introduced alongside bcrypt via passlib's deprecated‑scheme
#     mechanism for a gradual migration on next login.
# ---------------------------------------------------------------------------

_BCRYPT_MAX_BYTES = 72
_BCRYPT_DEFAULT_ROUNDS = 12


def _prepare_password(password: str) -> bytes:
    """Validate, normalise and encode *password* for bcrypt.

    Returns raw UTF‑8 ``bytes`` truncated to the 72‑byte bcrypt limit.
    Raises ``ValueError`` for empty or non‑string inputs.
    """
    # --- Input validation ---------------------------------------------------
    if not isinstance(password, str):
        raise ValueError("Password must be a string.")
    if not password:
        raise ValueError("Password must not be empty.")

    encoded = password.encode("utf-8")

    if len(encoded) > _BCRYPT_MAX_BYTES:
        logger.debug(
            "Password exceeds bcrypt %d‑byte limit (%d bytes) – truncating.",
            _BCRYPT_MAX_BYTES,
            len(encoded),
        )
        # Truncate raw bytes.  Decode then re‑encode so that an
        # incomplete multi‑byte character at the boundary is dropped
        # rather than producing invalid UTF‑8.
        truncated_str = encoded[:_BCRYPT_MAX_BYTES].decode(
            "utf-8", errors="ignore"
        )
        encoded = truncated_str.encode("utf-8")

    return encoded


# ---------------------------------------------------------------------------
# Public API – password hashing & verification
# ---------------------------------------------------------------------------

def get_password_hash(password: str) -> str:
    """Hash *password* with bcrypt.

    The password is truncated to 72 UTF‑8 bytes first to prevent
    ``ValueError`` on bcrypt ≥ 4.1.  Returns the hash as a string
    (e.g. ``$2b$12$...``).
    """
    secret = _prepare_password(password)
    hashed = bcrypt.hashpw(secret, bcrypt.gensalt(rounds=_BCRYPT_DEFAULT_ROUNDS))
    return hashed.decode("ascii")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify *plain_password* against a stored bcrypt hash.

    Applies the same 72‑byte truncation used during hashing so that
    passwords originally longer than 72 bytes still verify correctly.
    """
    try:
        secret = _prepare_password(plain_password)
    except ValueError:
        # Invalid input can never match a stored hash.
        return False

    if not hashed_password:
        return False

    try:
        return bcrypt.checkpw(secret, hashed_password.encode("ascii"))
    except (ValueError, TypeError) as exc:
        # Malformed hash string, encoding error, etc.
        logger.warning("Password verification failed: %s", exc)
        return False


# ---------------------------------------------------------------------------
# JWT helpers
# ---------------------------------------------------------------------------

def create_access_token(data: dict, expires_delta: timedelta = None) -> str:
    to_encode = data.copy()
    expire = expires_delta if expires_delta else timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)

    # python‑jose handles 'exp' as a unix timestamp
    expire = datetime.now(timezone.utc) + expire
    to_encode.update({"exp": expire})

    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def decode_access_token(token: str) -> dict:
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except JWTError:
        return None

