from __future__ import annotations

import re
from collections.abc import Iterator
from typing import Annotated

from fastapi import Depends, Header, Query, Request
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.errors import AppError, ErrorCode, validation
from app.core.ratelimit import DatabaseRateLimiter, RedisRateLimiter, client_identity
from app.db.session import get_session
from app.models import AccessToken, User
from app.services import auth as auth_service

IDEMPOTENCY_PATTERN = re.compile(r"^[A-Za-z0-9._:-]{36,100}$")

SessionDep = Annotated[Session, Depends(get_session)]


def bearer_token(request: Request) -> str | None:
    header = request.headers.get("authorization")
    if not header:
        return None
    match = re.match(r"^Bearer\s+([^\s]+)$", header, re.IGNORECASE)
    if not match:
        raise AppError(401, ErrorCode.UNAUTHENTICATED, "O header Authorization é inválido.")
    return match.group(1)


def optional_auth(request: Request, session: SessionDep) -> tuple[User, AccessToken] | None:
    """Bearer opcional (sala pública). Token inválido é simplesmente ignorado."""
    token = None
    try:
        token = bearer_token(request)
    except AppError:
        return None
    if not token:
        return None
    try:
        user, record = auth_service.resolve_token(session, token)
    except AppError:
        return None
    auth_service.touch_token(session, record)
    session.commit()
    return user, record


def require_auth(request: Request, session: SessionDep) -> tuple[User, AccessToken]:
    token = bearer_token(request)
    if not token:
        raise AppError(401, ErrorCode.UNAUTHENTICATED)
    user, record = auth_service.resolve_token(session, token)
    auth_service.touch_token(session, record)
    session.commit()
    return user, record


CurrentUser = Annotated[tuple[User, AccessToken], Depends(require_auth)]
OptionalUser = Annotated[tuple[User, AccessToken] | None, Depends(optional_auth)]


def require_bidder(auth: CurrentUser) -> User:
    user, _ = auth
    if user.role == "auctioneer":
        raise AppError(403, ErrorCode.AUCTIONEER_CANNOT_BID)
    if user.role != "bidder":
        raise AppError(403, ErrorCode.FORBIDDEN)
    return user


def require_auctioneer(auth: CurrentUser) -> User:
    user, _ = auth
    if user.role != "auctioneer":
        raise AppError(403, ErrorCode.FORBIDDEN)
    return user


BidderUser = Annotated[User, Depends(require_bidder)]
AuctioneerUser = Annotated[User, Depends(require_auctioneer)]


def idempotency_key(
    idempotency_key_header: Annotated[str | None, Header(alias="Idempotency-Key")] = None,
) -> str:
    if not idempotency_key_header:
        raise AppError(400, ErrorCode.VALIDATION_ERROR, "É necessária a chave de idempotência.")
    key = idempotency_key_header.strip()
    if not IDEMPOTENCY_PATTERN.match(key):
        raise validation(
            "A chave de idempotência é inválida.",
            {"Idempotency-Key": ["36–100 caracteres alfanuméricos, '.', '_', ':' ou '-'."]},
        )
    return key


IdempotencyKey = Annotated[str, Depends(idempotency_key)]


def _limiter(session: Session):
    if settings.redis_url:
        try:
            from redis import Redis

            client = Redis.from_url(settings.redis_url, socket_connect_timeout=1, socket_timeout=1)
            return RedisRateLimiter(client)
        except Exception:  # pragma: no cover
            return DatabaseRateLimiter(session)
    return DatabaseRateLimiter(session)


def rate_limit(bucket: str, limit_attr: str, window_seconds: int, *, per_user: str | None = None):
    """Fábrica de dependência de rate limiting.

    Uso: ``dependencies=[Depends(rate_limit("login", "rate_limit_login_per_minute", 60))]``.
    """

    def dependency(request: Request, session: SessionDep) -> None:
        if not settings.rate_limit_enabled:
            return
        limit = int(getattr(settings, limit_attr))
        identity = client_identity(request)
        if per_user == "user":
            token = request.headers.get("authorization", "")
            if token:
                from app.core.security import hash_token

                identity = "u:" + hash_token(token.split(" ")[-1])[:32]
        _limiter(session).hit(bucket, identity, limit, window_seconds)

    dependency.__name__ = f"rate_limit_{bucket}"
    return dependency


def pagination(page: int = Query(1, ge=1), page_size: int = Query(12, ge=1, le=50, alias="pageSize")) -> tuple[int, int]:
    return page, page_size


PaginationDep = Annotated[tuple[int, int], Depends(pagination)]


def safe_search_term(q: str | None = Query(None, max_length=100)) -> str | None:
    if q is None:
        return None
    cleaned = q.strip()
    if not cleaned:
        return None
    if len(cleaned) > 100:
        raise validation("Pesquisa demasiado longa.", {"q": ["Máximo 100 caracteres."]})
    return cleaned


SearchTerm = Annotated[str | None, Depends(safe_search_term)]


def session_iter() -> Iterator[Session]:  # pragma: no cover - utilitário
    yield from get_session()
