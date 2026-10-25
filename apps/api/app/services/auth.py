from __future__ import annotations

from datetime import timedelta
from typing import Any

from sqlalchemy import select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.errors import AppError, ErrorCode, unauthenticated, validation
from app.core.ids import iso_utc, new_public_id, utcnow
from app.core.logging import get_logger
from app.core.security import (
    burn_password_time,
    generate_opaque_token,
    hash_password,
    hash_token,
    validate_password,
    verify_password,
)
from app.models import AccessToken, User
from app.services.wallet import get_or_create_wallet

logger = get_logger(__name__)

ROLE_BIDDER = "bidder"
ROLE_AUCTIONEER = "auctioneer"


def normalize_email(email: str) -> str:
    return email.strip().lower()


def user_payload(user: User) -> dict[str, Any]:
    return {
        "id": user.public_id,
        "displayName": user.display_name,
        "email": user.email_display,
        "role": user.role,
        "createdAt": iso_utc(user.created_at),
    }


def _issue_token(session: Session, user: User) -> tuple[str, AccessToken]:
    raw_token = generate_opaque_token()
    expires_at = utcnow() + timedelta(seconds=settings.token_ttl_seconds)
    record = AccessToken(
        user_id=user.id,
        token_hash=hash_token(raw_token),
        expires_at=expires_at,
    )
    session.add(record)
    session.flush()
    return raw_token, record


def auth_payload(user: User, raw_token: str, record: AccessToken) -> dict[str, Any]:
    return {
        "user": user_payload(user),
        "accessToken": raw_token,
        "expiresAt": iso_utc(record.expires_at),
        "demo": False,
    }


def register(
    session: Session, *, display_name: str, email: str, password: str, role: str
) -> tuple[User, str, AccessToken]:
    if role not in (ROLE_BIDDER, ROLE_AUCTIONEER):
        raise validation(
            "O papel deve ser bidder ou auctioneer.", {"role": ["Papel não permitido."]}
        )
    validate_password(password)
    normalized = normalize_email(email)
    if len(normalized) > 254 or "@" not in normalized:
        raise validation("Email inválido.", {"email": ["Email inválido."]})

    existing = session.scalar(select(User.id).where(User.email_normalized == normalized))
    if existing is not None:
        raise AppError(
            409,
            ErrorCode.CONFLICT,
            "Não foi possível concluir o registo com estes dados.",
        )

    user = User(
        public_id=new_public_id("usr"),
        display_name=display_name.strip(),
        email_normalized=normalized,
        email_display=email.strip(),
        password_hash=hash_password(password),
        role=role,
    )
    session.add(user)
    try:
        session.flush()
    except IntegrityError as exc:
        session.rollback()
        raise AppError(
            409, ErrorCode.CONFLICT, "Não foi possível concluir o registo com estes dados."
        ) from exc

    if role == ROLE_BIDDER:
        get_or_create_wallet(session, user)

    raw_token, record = _issue_token(session, user)
    logger.info("user_registered", extra={"extra_fields": {"userId": user.public_id, "role": role}})
    return user, raw_token, record


def login(session: Session, *, email: str, password: str) -> tuple[User, str, AccessToken]:
    normalized = normalize_email(email)
    user = session.scalar(select(User).where(User.email_normalized == normalized))
    if user is None:
        burn_password_time()
        raise unauthenticated("Credenciais inválidas.")
    if not verify_password(password, user.password_hash):
        raise unauthenticated("Credenciais inválidas.")
    if not user.is_active:
        raise unauthenticated("Credenciais inválidas.")
    raw_token, record = _issue_token(session, user)
    logger.info("user_login", extra={"extra_fields": {"userId": user.public_id}})
    return user, raw_token, record


def resolve_token(session: Session, raw_token: str) -> tuple[User, AccessToken]:
    if not raw_token or len(raw_token) > 200:
        raise unauthenticated()
    token_hash = hash_token(raw_token)
    record = session.scalar(select(AccessToken).where(AccessToken.token_hash == token_hash))
    if record is None:
        raise unauthenticated()
    if record.revoked_at is not None:
        raise unauthenticated("A sessão foi terminada.")
    if record.expires_at <= utcnow():
        raise AppError(401, ErrorCode.TOKEN_EXPIRED)
    user = session.get(User, record.user_id)
    if user is None or not user.is_active:
        raise unauthenticated()
    return user, record


def touch_token(session: Session, record: AccessToken) -> None:
    now = utcnow()
    if record.last_used_at is None or (now - record.last_used_at).total_seconds() > 30:
        record.last_used_at = now


def logout(session: Session, record: AccessToken) -> bool:
    if record.revoked_at is None:
        record.revoked_at = utcnow()
        record.revoked_reason = "logout"
        session.flush()
    return True


def revoke_all_tokens(session: Session, user_id: int, reason: str = "revoked") -> int:
    result = session.execute(
        update(AccessToken)
        .where(AccessToken.user_id == user_id, AccessToken.revoked_at.is_(None))
        .values(revoked_at=utcnow(), revoked_reason=reason)
    )
    return int(result.rowcount or 0)


def update_profile(session: Session, user: User, display_name: str) -> User:
    cleaned = " ".join(display_name.split())
    if len(cleaned) < 2 or len(cleaned) > 80:
        raise validation(
            "O nome deve ter entre 2 e 80 caracteres.",
            {"displayName": ["Comprimento inválido."]},
        )
    user.display_name = cleaned
    session.flush()
    return user


def require_role(user: User, role: str) -> None:
    if user.role != role:
        raise AppError(403, ErrorCode.FORBIDDEN)
