from __future__ import annotations

import hashlib
import hmac
import secrets

from pwdlib import PasswordHash
from pwdlib.hashers.argon2 import Argon2Hasher

from app.core.config import settings
from app.core.errors import validation

_password_hash = PasswordHash((Argon2Hasher(),))

_DUMMY_HASH = _password_hash.hash("artbid-GsKA3Cg3tfxjTdPjmNd8qxXBlT9IF3ckmJt4ALDTGWk")

MIN_PASSWORD_LENGTH_HARD = 8


def hash_password(password: str) -> str:
    return _password_hash.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    try:
        return _password_hash.verify(password, password_hash)
    except Exception: 
        return False


def burn_password_time() -> None:
    _password_hash.verify("artbid-GsKA3Cg3tfxjTdPjmNd8qxXBlT9IF3ckmJt4ALDTGWk", _DUMMY_HASH)


def password_problems(password: str) -> list[str]:
    problems: list[str] = []
    if len(password) < settings.password_min_length:
        problems.append(f"A palavra-passe deve ter pelo menos {settings.password_min_length} caracteres.")
    if len(password) > settings.password_max_length:
        problems.append(f"A palavra-passe não pode exceder {settings.password_max_length} caracteres.")
    if not any(char.isalpha() for char in password) or not any(char.isdigit() for char in password):
        problems.append("A palavra-passe deve combinar letras e números.")
    if password.lower() in {"password", "palavra-passe", "123456789012"}:
        problems.append("A palavra-passe é demasiado comum.")
    return problems


def validate_password(password: str) -> None:
    problems = password_problems(password)
    if problems:
        raise validation("A palavra-passe não cumpre os requisitos.", {"password": problems})


TOKEN_PREFIX = "artbid_"


def generate_opaque_token() -> str:
    return TOKEN_PREFIX + secrets.token_urlsafe(32)


def hash_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def constant_time_equals(left: str, right: str) -> bool:
    return hmac.compare_digest(left, right)


def idempotency_key_hash(key: str) -> str:
    return hashlib.sha256(key.encode("utf-8")).hexdigest()


def hmac_sha256(secret: str, message: str) -> str:
    return hmac.new(secret.encode("utf-8"), message.encode("utf-8"), hashlib.sha256).hexdigest()
