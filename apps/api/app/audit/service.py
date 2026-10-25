from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.audit.chain import (
    INTEGRITY_UNAVAILABLE,
    INTEGRITY_VERIFIED,
    ChainVerification,
    checkpoint_signing_payload,
    compute_event_hash,
    compute_heads_digest,
    event_canonical_payload,
    new_checkpoint_id,
    signing_available,
    sign_heads,
    verification_key_available,
    verification_unavailable,
    verify_chain_rows,
    verify_signature,
)
from app.core.config import settings
from app.core.ids import iso_utc, new_public_id, utcnow
from app.models import AuditCheckpoint, AuditEvent, Lot, OutboxEvent

CHAIN_TYPES = {
    "lot.created",
    "bid.accepted",
    "lot.extended",
    "lot.closed",
    "lot.cancelled",
    "lot.settled",
}


def _lock_lot(session: Session, lot_id: int) -> None:
    session.execute(select(Lot.id).where(Lot.id == lot_id).with_for_update())


def _last_event(session: Session, lot_id: int) -> AuditEvent | None:
    return session.scalar(
        select(AuditEvent)
        .where(AuditEvent.lot_id == lot_id)
        .order_by(AuditEvent.sequence.desc())
        .limit(1)
    )


def next_sequence(session: Session, lot: Lot) -> int:
    current = session.scalar(
        select(func.coalesce(func.max(AuditEvent.sequence), 0)).where(AuditEvent.lot_id == lot.id)
    )
    outbox_current = session.scalar(
        select(func.coalesce(func.max(OutboxEvent.sequence), 0)).where(OutboxEvent.lot_id == lot.id)
    )
    return max(int(current or 0), int(outbox_current or 0)) + 1


def append_event(
    session: Session,
    *,
    lot: Lot,
    type: str,
    data: dict[str, Any] | None = None,
    actor_alias: str | None = None,
    actor_ref: str | None = None,
    amount_cents: int | None = None,
    occurred_at: datetime | None = None,
    sequence: int | None = None,
) -> AuditEvent:
    if type not in CHAIN_TYPES: 
        raise ValueError(f"tipo de auditoria não encadeável: {type}")

    _lock_lot(session, lot.id)
    occurred = occurred_at or utcnow()
    seq = sequence or next_sequence(session, lot)
    previous = _last_event(session, lot.id)
    previous_hash = previous.hash if previous else None
    event_id = new_public_id("evt")

    canonical = event_canonical_payload(
        chain_version=settings.audit_chain_version,
        event_id=event_id,
        lot_id=lot.public_id,
        sequence=seq,
        type=type,
        actor_alias=actor_alias,
        actor_ref=actor_ref,
        amount_cents=amount_cents,
        data=data or {},
        occurred_at=occurred,
    )
    event_hash = compute_event_hash(canonical, previous_hash)

    record = AuditEvent(
        public_id=event_id,
        lot_id=lot.id,
        sequence=seq,
        type=type,
        actor_alias=actor_alias,
        actor_ref=actor_ref,
        amount_cents=amount_cents,
        data=data or {},
        occurred_at=occurred,
        hash=event_hash,
        previous_hash=previous_hash,
        chain_version=settings.audit_chain_version,
    )
    session.add(record)
    session.flush()
    return record


def enqueue_outbox(
    session: Session,
    *,
    lot: Lot,
    type: str,
    sequence: int,
    payload: dict[str, Any],
    occurred_at: datetime | None = None,
    event_id: str | None = None,
    visibility: str = "public",
    target_user_id: int | None = None,
) -> OutboxEvent:
    resolved_event_id = event_id or new_public_id("oevt")
    envelope = {
        "eventId": resolved_event_id,
        "lotId": lot.public_id,
        "sequence": sequence,
        "occurredAt": iso_utc(occurred_at or utcnow()),
        "type": type,
        **payload,
    }
    record = OutboxEvent(
        event_id=resolved_event_id,
        lot_id=lot.id,
        type=type,
        sequence=sequence,
        payload=envelope,
        visibility=visibility,
        target_user_id=target_user_id,
    )
    session.add(record)
    session.flush()
    return record


def record_business_event(
    session: Session,
    *,
    lot: Lot,
    type: str,
    data: dict[str, Any] | None = None,
    actor_alias: str | None = None,
    actor_ref: str | None = None,
    amount_cents: int | None = None,
    occurred_at: datetime | None = None,
    sse_payload: dict[str, Any] | None = None,
    sse_type: str | None = None,
    sse_visibility: str = "public",
    target_user_id: int | None = None,
    sequence: int | None = None,
) -> tuple[AuditEvent, OutboxEvent]:
    if sequence is not None:
        _lock_lot(session, lot.id)
        seq = sequence
        event = append_event(
            session,
            lot=lot,
            type=type,
            data=data,
            actor_alias=actor_alias,
            actor_ref=actor_ref,
            amount_cents=amount_cents,
            occurred_at=occurred_at,
            sequence=seq,
        )
    else:
        event = append_event(
            session,
            lot=lot,
            type=type,
            data=data,
            actor_alias=actor_alias,
            actor_ref=actor_ref,
            amount_cents=amount_cents,
            occurred_at=occurred_at,
        )
        seq = event.sequence
    outbox = enqueue_outbox(
        session,
        lot=lot,
        type=sse_type or type,
        sequence=seq,
        payload=sse_payload or {},
        occurred_at=occurred_at or event.occurred_at,
        visibility=sse_visibility,
        target_user_id=target_user_id,
    )
    return event, outbox


def verify_lot_chain(session: Session, lot: Lot, limit: int | None = None) -> ChainVerification:
    total = session.scalar(
        select(func.count()).select_from(AuditEvent).where(AuditEvent.lot_id == lot.id)
    ) or 0
    if total == 0:
        return ChainVerification(INTEGRITY_VERIFIED, 0, 0, None, None, None, utcnow())

    stmt = select(AuditEvent).where(AuditEvent.lot_id == lot.id).order_by(AuditEvent.sequence.asc())
    if limit:
        stmt = stmt.limit(limit)
    rows = session.scalars(stmt).all()
    for row in rows:
        row.lot_public_id = lot.public_id

    result = verify_chain_rows(list(rows))
    if result.status != INTEGRITY_VERIFIED:
        return result

    checkpoint = latest_checkpoint_for_lot(session, lot)
    if checkpoint is None:
        if signing_available().available or verification_key_available():
            return ChainVerification(
                INTEGRITY_UNAVAILABLE,
                result.checked_event_count,
                total,
                result.expected_hash,
                result.calculated_hash,
                "checkpoint_pending",
                utcnow(),
            )
        return result
    if checkpoint.status == "failed":
        return ChainVerification(
            INTEGRITY_VERIFIED,
            result.checked_event_count,
            total,
            result.expected_hash,
            result.calculated_hash,
            "checkpoint_failed",
            utcnow(),
        )
    return result


def latest_checkpoint_for_lot(session: Session, lot: Lot) -> AuditCheckpoint | None:
    checkpoint = session.scalar(
        select(AuditCheckpoint).order_by(AuditCheckpoint.id.desc()).limit(1)
    )
    if checkpoint is None:
        return None
    heads = checkpoint.heads or []
    covered = {head.get("lotId") for head in heads}
    if lot.public_id not in covered:
        return None
    return checkpoint


def checkpoint_head_for_lot(session: Session, checkpoint: AuditCheckpoint, lot: Lot) -> str | None:
    for head in checkpoint.heads or []:
        if head.get("lotId") == lot.public_id:
            return head.get("lastHash")
    return None


def create_checkpoint(session: Session) -> AuditCheckpoint | None:
    heads_rows = session.execute(
        select(
            Lot.public_id,
            func.max(AuditEvent.sequence),
            func.count(AuditEvent.id),
        )
        .join(AuditEvent, AuditEvent.lot_id == Lot.id)
        .group_by(Lot.public_id)
        .order_by(Lot.public_id)
        .limit(settings.audit_checkpoint_batch_lots)
    ).all()
    if not heads_rows:
        return None

    heads: list[dict[str, str | int]] = []
    events_covered = 0
    for public_id, max_sequence, event_count in heads_rows:
        last = session.execute(
            select(AuditEvent.hash)
            .join(Lot, Lot.id == AuditEvent.lot_id)
            .where(Lot.public_id == public_id)
            .order_by(AuditEvent.sequence.desc())
            .limit(1)
        ).scalar_one_or_none()
        if last is None:
            continue
        heads.append({"lotId": public_id, "lastHash": last, "sequence": int(max_sequence)})
        events_covered += int(event_count)

    heads_digest = compute_heads_digest(heads)
    signature_state = signing_available()
    signature: str | None = None
    status = INTEGRITY_UNAVAILABLE
    if signature_state.available:
        payload = checkpoint_signing_payload(
            key_id=settings.audit_checkpoint_key_id,
            chain_version=settings.audit_chain_version,
            heads_digest=heads_digest,
            lots_covered=len(heads),
            events_covered=events_covered,
        )
        signature = sign_heads(payload)
        status = INTEGRITY_VERIFIED if signature else INTEGRITY_UNAVAILABLE

    checkpoint = AuditCheckpoint(
        public_id=new_checkpoint_id(),
        key_id=settings.audit_checkpoint_key_id,
        lots_covered=len(heads),
        events_covered=events_covered,
        heads_digest=heads_digest,
        heads=heads,
        chain_version=settings.audit_chain_version,
        status=status,
        signature=signature,
    )
    session.add(checkpoint)
    session.flush()
    return checkpoint


def export_checkpoint(checkpoint: AuditCheckpoint) -> None:
    import json
    import os

    directory = os.getenv("AUDIT_CHECKPOINT_EXPORT_DIR", "").strip()
    if not directory:
        return
    os.makedirs(directory, exist_ok=True)
    path = os.path.join(directory, "audit-checkpoints.jsonl")
    line = json.dumps(
        {
            "checkpointId": checkpoint.public_id,
            "keyId": checkpoint.key_id,
            "chainVersion": checkpoint.chain_version,
            "lotsCovered": checkpoint.lots_covered,
            "eventsCovered": checkpoint.events_covered,
            "headsDigest": checkpoint.heads_digest,
            "status": checkpoint.status,
            "signature": checkpoint.signature,
            "createdAt": iso_utc(checkpoint.created_at or utcnow()),
        },
        sort_keys=True,
        separators=(",", ":"),
    )
    with open(path, "a", encoding="utf-8") as handle:
        handle.write(line + "\n")
        handle.flush()
        os.fsync(handle.fileno())


def verify_checkpoint_signature(checkpoint: AuditCheckpoint) -> bool | None:
    if checkpoint.signature is None:
        return None
    payload = checkpoint_signing_payload(
        key_id=checkpoint.key_id,
        chain_version=checkpoint.chain_version,
        heads_digest=checkpoint.heads_digest,
        lots_covered=checkpoint.lots_covered,
        events_covered=checkpoint.events_covered,
    )
    return verify_signature(payload, checkpoint.signature)


def verify_all_chains(session: Session) -> dict[str, int]:
    totals = {"lots": 0, "failed": 0, "unavailable": 0}
    lot_ids = session.scalars(select(Lot.id).order_by(Lot.id)).all()
    for lot_id in lot_ids:
        lot = session.get(Lot, lot_id)
        if lot is None:
            continue
        verification = verify_lot_chain(session, lot)
        totals["lots"] += 1
        if verification.status == "failed":
            totals["failed"] += 1
        elif verification.status == INTEGRITY_UNAVAILABLE:
            totals["unavailable"] += 1
    return totals


def unavailable_result(reason: str, total: int = 0) -> ChainVerification:
    return verification_unavailable(reason, total)
