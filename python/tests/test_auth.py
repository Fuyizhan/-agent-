from __future__ import annotations

from datetime import timedelta

import jwt

from src.api.auth.security import create_access_token, decode_access_token, hash_password, verify_password
from src.config import settings


def test_password_hash_and_verify():
    hashed = hash_password("secret123")
    assert hashed != "secret123"
    assert verify_password("secret123", hashed)
    assert not verify_password("wrong", hashed)


def test_jwt_round_trip():
    token = create_access_token("user-1", "admin", "tenant-1")
    payload = decode_access_token(token)
    assert payload is not None
    assert payload["sub"] == "user-1"
    assert payload["tenant_id"] == "tenant-1"


def test_expired_jwt_is_rejected():
    token = create_access_token("user-1", "admin", expires_delta=timedelta(seconds=-1))
    assert decode_access_token(token) is None


def test_tampered_jwt_is_rejected():
    token = create_access_token("user-1", "admin")
    tampered = token[:-4] + "XXXX"
    assert jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
    assert decode_access_token(tampered) is None
