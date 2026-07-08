"""
Tests for the security hardening and central configuration added during
production hardening: JWT/password handling, the SECRET_KEY fail-fast, and the
typed Settings (CORS parsing, environment detection).
"""
import importlib
import os
import sys

import pytest


@pytest.fixture(autouse=True)
def _restore_env_and_modules():
    """These tests re-import app.core.{security,config} under mutated env to
    exercise the import-time SECRET_KEY fail-fast. Restore a clean dev-mode
    state afterward so module ordering can't contaminate the rest of the suite.
    """
    saved = {k: os.environ.get(k) for k in ("SECRET_KEY", "DEBUG", "ENVIRONMENT")}
    yield
    for k, v in saved.items():
        if v is None:
            os.environ.pop(k, None)
        else:
            os.environ[k] = v
    # Ensure a sane, importable dev-mode state is cached for later tests.
    os.environ.setdefault("DEBUG", "true")
    for m in ("app.core.security", "app.core.config"):
        sys.modules.pop(m, None)
    importlib.import_module("app.core.security")


# ---------------------------------------------------------------------------
# app.core.security — password hashing & JWT
# ---------------------------------------------------------------------------

def _fresh_security(env: dict):
    """Import app.core.security fresh under a given environment."""
    for k in ("SECRET_KEY", "DEBUG", "ENVIRONMENT"):
        os.environ.pop(k, None)
    os.environ.update(env)
    for m in list(sys.modules):
        if m.startswith("app.core.security") or m.startswith("app.core.config"):
            sys.modules.pop(m, None)
    return importlib.import_module("app.core.security")


@pytest.fixture
def security():
    return _fresh_security({"DEBUG": "true", "SECRET_KEY": "x" * 40})


def test_password_hash_and_verify_roundtrip(security):
    h = security.get_password_hash("s3cret-password")
    assert h.startswith("$2b$")
    assert security.verify_password("s3cret-password", h) is True
    assert security.verify_password("wrong", h) is False


def test_password_over_72_bytes_is_handled(security):
    # bcrypt only uses the first 72 bytes; hashing must not raise and must verify.
    long_pw = "a" * 200
    h = security.get_password_hash(long_pw)
    assert security.verify_password(long_pw, h) is True


def test_empty_password_rejected(security):
    with pytest.raises(ValueError):
        security.get_password_hash("")
    assert security.verify_password("", "$2b$12$" + "a" * 53) is False


def test_jwt_create_and_decode_roundtrip(security):
    token = security.create_access_token({"sub": "farmer1"})
    payload = security.decode_access_token(token)
    assert payload is not None
    assert payload["sub"] == "farmer1"
    assert "exp" in payload


def test_jwt_tampered_token_rejected(security):
    token = security.create_access_token({"sub": "farmer1"})
    tampered = token[:-3] + ("aaa" if not token.endswith("aaa") else "bbb")
    assert security.decode_access_token(tampered) is None


def test_jwt_signed_with_other_secret_rejected(security):
    # A token signed with a different key must not validate (forgery guard).
    from jose import jwt
    forged = jwt.encode({"sub": "attacker"}, "some-other-key", algorithm="HS256")
    assert security.decode_access_token(forged) is None


# ---------------------------------------------------------------------------
# SECRET_KEY fail-fast (C3)
# ---------------------------------------------------------------------------

def test_default_secret_refused_in_production():
    with pytest.raises(RuntimeError):
        _fresh_security({"ENVIRONMENT": "production"})  # no SECRET_KEY, no DEBUG


def test_default_secret_allowed_in_dev():
    mod = _fresh_security({"DEBUG": "true"})  # default secret tolerated in dev
    assert mod.SECRET_KEY == mod.DEFAULT_SECRET_KEY


def test_real_secret_boots_in_production():
    mod = _fresh_security({"ENVIRONMENT": "production", "SECRET_KEY": "prod-secret-value-123456"})
    assert mod.SECRET_KEY == "prod-secret-value-123456"
    # sanity: it can still mint/verify tokens
    tok = mod.create_access_token({"sub": "u"})
    assert mod.decode_access_token(tok)["sub"] == "u"


# ---------------------------------------------------------------------------
# app.core.config — typed Settings (M3)
# ---------------------------------------------------------------------------

def _settings_cls():
    sys.modules.pop("app.core.config", None)
    return importlib.import_module("app.core.config").Settings


def test_is_production_detection():
    Settings = _settings_cls()
    assert Settings(environment="production", debug=False).is_production is True
    assert Settings(environment="production", debug=True).is_production is False
    for dev in ("dev", "development", "local", "test", "testing"):
        assert Settings(environment=dev, debug=False).is_production is False


def test_using_default_secret_flag():
    from app.core.config import DEFAULT_SECRET_KEY
    Settings = _settings_cls()
    assert Settings(secret_key=DEFAULT_SECRET_KEY).using_default_secret is True
    assert Settings(secret_key="real").using_default_secret is False


def test_cors_origins_parsing_basic():
    Settings = _settings_cls()
    s = Settings(cors_allow_origins="http://a.com, http://b.com ,, http://c.com")
    assert s.cors_origins_list == ["http://a.com", "http://b.com", "http://c.com"]


def test_cors_wildcard_dropped_when_credentials_enabled():
    Settings = _settings_cls()
    s = Settings(cors_allow_origins="*,https://ok.com", cors_allow_credentials=True)
    assert "*" not in s.cors_origins_list
    assert s.cors_origins_list == ["https://ok.com"]


def test_cors_wildcard_allowed_without_credentials():
    Settings = _settings_cls()
    s = Settings(cors_allow_origins="*", cors_allow_credentials=False)
    assert s.cors_origins_list == ["*"]


def test_cors_empty_falls_back_to_localhost():
    Settings = _settings_cls()
    s = Settings(cors_allow_origins="   ,  ,")
    assert s.cors_origins_list == ["http://localhost", "http://localhost:3000"]
