from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import timedelta
from typing import Any, Callable

from sqlalchemy import delete, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.orm import Session

from app.audit.chain import canonical_json, sha256_hex
from app.core.config import settings
from app.core.errors import AppError, ErrorCode
from app.core.ids import utcnow
from app.core.security import idempotency_key_hash
from app.models import IdempotencyRecord

logger = logging.getLogger(__name__)

HandlerResult = tuple[int, dict[str, Any], str | None]


@dataclass
class IdempotentOutcome:
    replayed: bool
    status_code: int
    body: dict[str, Any]


def request_fingerprint(payload: dict[str, Any]) -> str:
    return sha256_hex(canonical_json(payload))


def _try_claim(session: Session, *, key_hash: str, user_id: int, operation: str, request_hash: str, expires_at) -> bool:
    statement = (
        pg_insert(IdempotencyRecord)
        .values(
            key_hash=key_hash,
            user_id=user_id,
            operation=operation,
            request_hash=request_hash,
            status="in_progress",
            expires_at=expires_at,
        )
        .on_conflict_do_nothing(constraint="uq_idempotency_scope")
        .returning(IdempotencyRecord.id)
    )
    return session.execute(statement).scalar_one_or_none() is not None


def _load_record(session: Session, key_hash: str, user_id: int, operation: str) -> IdempotencyRecord | None:
    return session.scalar(
        select(IdempotencyRecord).where(
            IdempotencyRecord.key_hash == key_hash,
            IdempotencyRecord.user_id == user_id,
            IdempotencyRecord.operation == operation,
        )
    )


def _store_response(
    session: Session,
    *,
    key_hash: str,
    user_id: int,
    operation: str,
    request_hash: str,
    status_code: int,
    body: dict[str, Any],
    resource_ref: str | None,
    expires_at,
) -> None:
    existing = _load_record(session, key_hash, user_id, operation)
    if existing is None:
        session.execute(
            pg_insert(IdempotencyRecord)
            .values(
                key_hash=key_hash,
                user_id=user_id,
                operation=operation,
                request_hash=request_hash,
                status="completed",
                response_status=status_code,
                response_body=body,
                resource_ref=resource_ref,
                expires_at=expires_at,
                completed_at=utcnow(),
            )
            .on_conflict_do_nothing(constraint="uq_idempotency_scope")
        )
        return
    existing.status = "completed"
    existing.response_status = status_code
    existing.response_body = body
    existing.resource_ref = resource_ref
    existing.completed_at = utcnow()


def execute_idempotent(
    session: Session,
    *,
    user_id: int,
    operation: str,
    key: str,
    request_payload: dict[str, Any],
    handler: Callable[[Session], HandlerResult],
) -> IdempotentOutcome:
    key_hash = idempotency_key_hash(key)
    request_hash = request_fingerprint(request_payload)
    ttl = timedelta(hours=settings.idempotency_ttl_hours)

    for _attempt in range(2):
        expires_at = utcnow() + ttl
        claimed = _try_claim(
            session,
            key_hash=key_hash,
            user_id=user_id,
            operation=operation,
            request_hash=request_hash,
            expires_at=expires_at,
        )
        if claimed:
            try:
                status_code, body, resource_ref = handler(session)
            except AppError as exc:
                session.rollback()
                if exc.retryable or exc.status_code >= 500:
                    raise
                error_body = {
                    "error": {
                        "code": exc.code,
                        "message": exc.message,
                        **({"fieldErrors": exc.field_errors} if exc.field_errors else {}),
                        "retryable": False,
                    }
                }
                _store_response(
                    session,
                    key_hash=key_hash,
                    user_id=user_id,
                    operation=operation,
                    request_hash=request_hash,
                    status_code=exc.status_code,
                    body=error_body,
                    resource_ref=None,
                    expires_at=utcnow() + ttl,
                )
                session.commit()
                raise
            except Exception:
                session.rollback()
                raise
            _store_response(
                session,
                key_hash=key_hash,
                user_id=user_id,
                operation=operation,
                request_hash=request_hash,
                status_code=status_code,
                body=body,
                resource_ref=resource_ref,
                expires_at=expires_at,
            )
            session.commit()
            logger.info(
                "idempotent_operation_completed",
                extra={"extra_fields": {"operation": operation, "status": status_code}},
            )
            return IdempotentOutcome(replayed=False, status_code=status_code, body=body)

        record = _load_record(session, key_hash, user_id, operation)
        if record is None:
            session.rollback()
            continue
        if record.expires_at <= utcnow():
            session.execute(
                delete(IdempotencyRecord).where(IdempotencyRecord.id == record.id)
            )
            session.commit()
            continue
        if record.request_hash != request_hash:
            session.rollback()
            raise AppError(409, ErrorCode.IDEMPOTENCY_CONFLICT)
        if record.status == "completed" and record.response_status is not None:
            body = dict(record.response_body or {})
            session.rollback()
            return IdempotentOutcome(
                replayed=True, status_code=record.response_status, body=body
            )
        session.rollback()
        raise AppError(409, ErrorCode.IDEMPOTENCY_IN_PROGRESS, retryable=True)

    raise AppError(409, ErrorCode.IDEMPOTENCY_IN_PROGRESS, retryable=True)


def cleanup_expired(session: Session) -> int:
    result = session.execute(
        delete(IdempotencyRecord).where(IdempotencyRecord.expires_at <= utcnow())
    )
    session.commit()
    return int(result.rowcount or 0)
