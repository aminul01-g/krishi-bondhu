"""
Centralized, typed application configuration.

This is the single source of truth for environment-derived settings. It replaces
the scattered ``os.getenv(...)`` calls that previously lived across the codebase
(security, CORS, DB, LLM keys, …) with one validated, importable object.

Usage
-----
    from app.core.config import settings

    if settings.is_production and settings.secret_key == settings.DEFAULT_SECRET_KEY:
        ...

Design notes
------------
* Backwards-compatible: existing ``os.getenv`` call sites keep working. New code
  should read from ``settings`` instead, and old sites can be migrated
  incrementally.
* ``extra="ignore"`` so the many unrelated env vars present in a real deployment
  (HF Space, Docker) don't cause validation errors.
* Secrets are typed as plain ``str`` (not ``SecretStr``) to avoid churn in the
  places that pass them straight to third-party SDKs; treat them as sensitive.
"""

from __future__ import annotations

import os
from functools import lru_cache
from typing import List

try:
    # pydantic-settings is already a declared dependency (requirements.txt).
    from pydantic_settings import BaseSettings, SettingsConfigDict
    from pydantic import field_validator
    _HAS_PYDANTIC_SETTINGS = True
except Exception:  # pragma: no cover - defensive fallback if the dep is absent
    _HAS_PYDANTIC_SETTINGS = False


DEFAULT_SECRET_KEY = "krishibondhu_super_secret_key_change_this_in_production"

_DEFAULT_CORS_ORIGINS = (
    "http://localhost,http://localhost:3000,"
    "https://huggingface.co,https://krishibondhu.hf.space"
)


if _HAS_PYDANTIC_SETTINGS:

    class Settings(BaseSettings):
        """Typed application settings loaded from the environment / .env."""

        model_config = SettingsConfigDict(
            env_file=".env",
            env_file_encoding="utf-8",
            case_sensitive=False,
            extra="ignore",
        )

        # --- Runtime / environment -----------------------------------------
        environment: str = "production"
        debug: bool = False

        # --- Security ------------------------------------------------------
        secret_key: str = DEFAULT_SECRET_KEY
        algorithm: str = "HS256"
        access_token_expire_minutes: int = 1440  # 24h

        # --- Database & cache ----------------------------------------------
        database_url: str = ""
        redis_url: str = ""

        # --- CORS ----------------------------------------------------------
        cors_allow_origins: str = _DEFAULT_CORS_ORIGINS
        cors_allow_credentials: bool = True

        # --- Uploads -------------------------------------------------------
        upload_dir: str = "/tmp/uploads"

        # --- LLM / external providers (optional) ---------------------------
        groq_api_key: str = ""
        gemini_api_key: str = ""
        huggingface_api_key: str = ""
        hf_token: str = ""
        weather_api_key: str = ""

        # -------------------------------------------------------------------
        # Derived helpers
        # -------------------------------------------------------------------
        @property
        def is_production(self) -> bool:
            if self.debug:
                return False
            return self.environment.lower() not in (
                "dev", "development", "local", "test", "testing"
            )

        @property
        def using_default_secret(self) -> bool:
            return self.secret_key == DEFAULT_SECRET_KEY

        @property
        def cors_origins_list(self) -> List[str]:
            """Parse the comma-separated CORS origins into a clean list.

            Mirrors the previous inline logic in ``main.py``: a ``*`` combined
            with credentials is unsafe, so the wildcard is dropped when
            credentials are enabled; an empty result falls back to localhost.
            """
            origins = [o.strip() for o in self.cors_allow_origins.split(",") if o.strip()]
            if "*" in origins:
                if self.cors_allow_credentials:
                    origins = [o for o in origins if o != "*"]
                else:
                    return ["*"]
            if not origins:
                return ["http://localhost", "http://localhost:3000"]
            return origins

        @field_validator("debug", mode="before")
        @classmethod
        def _coerce_debug(cls, v):
            if isinstance(v, str):
                return v.strip().lower() in ("1", "true", "yes", "on")
            return v

else:  # pragma: no cover

    class Settings:  # type: ignore
        """Minimal fallback used only if pydantic-settings is unavailable."""

        DEFAULT_SECRET_KEY = DEFAULT_SECRET_KEY

        def __init__(self) -> None:
            self.environment = os.getenv("ENVIRONMENT", "production")
            self.debug = os.getenv("DEBUG", "").lower() in ("1", "true", "yes", "on")
            self.secret_key = os.getenv("SECRET_KEY", DEFAULT_SECRET_KEY)
            self.algorithm = "HS256"
            self.access_token_expire_minutes = int(
                os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "1440")
            )
            self.database_url = os.getenv("DATABASE_URL", "")
            self.redis_url = os.getenv("REDIS_URL", "")
            self.cors_allow_origins = os.getenv("CORS_ALLOW_ORIGINS", _DEFAULT_CORS_ORIGINS)
            self.cors_allow_credentials = (
                os.getenv("CORS_ALLOW_CREDENTIALS", "true").lower() == "true"
            )
            self.upload_dir = os.getenv("UPLOAD_DIR", "/tmp/uploads")
            self.groq_api_key = os.getenv("GROQ_API_KEY", "")
            self.gemini_api_key = os.getenv("GEMINI_API_KEY", "")
            self.huggingface_api_key = os.getenv("HUGGINGFACE_API_KEY", "")
            self.hf_token = os.getenv("HF_TOKEN", "")
            self.weather_api_key = os.getenv("WEATHER_API_KEY", "")

        @property
        def is_production(self) -> bool:
            if self.debug:
                return False
            return self.environment.lower() not in (
                "dev", "development", "local", "test", "testing"
            )

        @property
        def using_default_secret(self) -> bool:
            return self.secret_key == DEFAULT_SECRET_KEY

        @property
        def cors_origins_list(self) -> List[str]:
            origins = [o.strip() for o in self.cors_allow_origins.split(",") if o.strip()]
            if "*" in origins:
                if self.cors_allow_credentials:
                    origins = [o for o in origins if o != "*"]
                else:
                    return ["*"]
            if not origins:
                return ["http://localhost", "http://localhost:3000"]
            return origins


@lru_cache
def get_settings() -> "Settings":
    """Return the process-wide singleton settings instance."""
    return Settings()


# Convenience module-level singleton for direct import.
settings = get_settings()
