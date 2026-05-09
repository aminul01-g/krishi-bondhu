import os
import logging
import warnings
from datetime import timedelta
from typing import Any

# ---------------------------------------------------------------------------
# Silence passlib + bcrypt >=4.1 version detection warning.
#
# passlib 1.7.4 tries to read ``bcrypt.__about__.__version__`` which was
# removed in bcrypt 4.1+.  We patch the attribute so passlib can read it
# without emitting "error reading bcrypt version" on every import.
# ---------------------------------------------------------------------------
try:
    import bcrypt as _bcrypt_mod

    if not hasattr(_bcrypt_mod, "__about__"):
        # Create a minimal __about__ namespace with the version string
        class _About:
            __version__ = getattr(_bcrypt_mod, "__version__", "4.0.0")

        _bcrypt_mod.__about__ = _About
except ImportError:
    pass  # bcrypt not installed — passlib will report its own error

from jose import JWTError, jwt
from passlib.context import CryptContext

logger = logging.getLogger(__name__)

# Load configuration from environment variables
# In a real production app, these should be in a .env file
SECRET_KEY = os.getenv("SECRET_KEY", "krishibondhu_super_secret_key_change_this_in_production")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "1440")) # Default 24h

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


# ---------------------------------------------------------------------------
# Bcrypt 72-byte password limit
# ---------------------------------------------------------------------------
# bcrypt internally operates on a maximum of 72 bytes.  Older bcrypt
# versions silently truncated; bcrypt >=4.1 raises ValueError instead.
#
# _prepare_password() encodes to UTF-8 and slices to 72 bytes *before*
# hashing so the same truncation is applied consistently during both
# hashing and verification.
#
# This is safe because:
#   • bcrypt has *always* only hashed the first 72 bytes — the extra bytes
#     were never part of the hash.  Truncating explicitly is identical
#     behaviour to what bcrypt <4.1 did silently.
#   • Existing hashes in the DB were created with the old bcrypt that
#     silently truncated at 72 bytes, so verifying with the same
#     truncation produces the same result.
# ---------------------------------------------------------------------------

_BCRYPT_MAX_BYTES = 72


def _prepare_password(password: str) -> str:
    """Truncate *password* to bcrypt's 72-byte limit (UTF-8 encoded).

    Returns the (possibly shortened) password as a ``str`` because
    passlib's CryptContext expects ``str``, not ``bytes``.
    """
    encoded = password.encode("utf-8")
    if len(encoded) > _BCRYPT_MAX_BYTES:
        logger.debug(
            "Password exceeds bcrypt 72-byte limit (%d bytes) — truncating.",
            len(encoded),
        )
        # Slice raw bytes, then decode.  ``errors='ignore'`` drops a
        # potentially incomplete multi-byte character at the boundary.
        encoded = encoded[:_BCRYPT_MAX_BYTES]
        return encoded.decode("utf-8", errors="ignore")
    return password


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify *plain_password* against a stored bcrypt hash.

    Applies the same 72-byte truncation used during hashing so that
    passwords longer than 72 bytes still verify correctly.
    """
    return pwd_context.verify(_prepare_password(plain_password), hashed_password)


def get_password_hash(password: str) -> str:
    """Hash *password* with bcrypt via passlib.

    Truncates to 72 UTF-8 bytes first to prevent ``ValueError`` on
    bcrypt >=4.1.
    """
    return pwd_context.hash(_prepare_password(password))

def create_access_token(data: dict, expires_delta: timedelta = None) -> str:
    to_encode = data.copy()
    expire = expires_delta if expires_delta else timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)

    # We'll use a custom 'exp' claim
    # Note: python-jose handles 'exp' as a unix timestamp
    from datetime import datetime, timezone
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
