from __future__ import annotations

import logging
from datetime import datetime
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.audit.service import record_business_event
from app.core.aliases import receipt_id, user_alias_for_lot, verification_id
from app.core.config import settings
from app.core.errors import AppError, ErrorCode
from app.core.ids import iso_utc, new_public_id, utcnow
from app.models import Bid, Lot, OutboxEvent, Receipt, SettlementLock, User, WalletMovement
from app.services import wallet as wallet_service
from app.services.lot_state import next_minimum_bid_cents, room_snapshot

logger = logging.getLogger(__name__)


def _commission(amount_cents: int) -> tuple[int, int]:
    bps = settings.settlement_commission_bps
    commission = (amount_cents * bps) // 10_000
    return commission, amount_cents - commission


def close_and_settle_lot(session: Session, lot_id: int, *, now: datetime | None = None) -> dict[str, Any]:
    now = now or utcnow()
    lot = session.scalar(select(Lot).where(Lot.id == lot_id).with_for_update())
    if lot is None:
        return {"lotId": lot_id, "result": "missing"}
    if lot.cancelled_at is not None:
        return {"lotId": lot_id, "result": "cancelled", "publicId": lot.public_id}
    if lot.settled_at is not None:
        return {"lotId": lot_id, "result": "already_settled", "publicId": lot.public_id}
    if lot.ends_at > now:
        return {"lotId": lot_id, "result": "still_running", "publicId": lot.public_id}

    lock = session.get(SettlementLock, lot_id)
    if lock is not None and lock.completed_at is not None:
        return {"lotId": lot_id, "result": "already_settled", "publicId": lot.public_id}
    if lock is None:
        lock = SettlementLock(lot_id=lot_id, acquired_at=now)
        session.add(lock)
        session.flush()

    closed_at = lot.closed_at or now
    winning_bid: Bid | None = None
    if lot.leading_bid_id is not None:
        winning_bid = session.get(Bid, lot.leading_bid_id)
    if winning_bid is None and lot.bid_count > 0:
        winning_bid = session.scalar(
            select(Bid).where(Bid.lot_id == lot.id).order_by(Bid.amount_cents.desc(), Bid.id.desc()).limit(1)
        )

    lot.status = "ended"
    lot.closed_at = closed_at
    lot.revision += 1
    session.flush()

    if winning_bid is None:
        lot.final_amount_cents = None
        lot.revenue_cents = 0
        lot.settled_at = closed_at
        session.flush()
        _emit_closed(session, lot, closed_at, winner_alias=None, receipt_public_id=None, final_amount=None)
        record_business_event(
            session,
            lot=lot,
            type="lot.settled",
            occurred_at=closed_at,
            data={"outcome": "no_bids", "revenueCents": 0},
            sse_type="lot.state.changed",
            sse_payload=room_snapshot(lot, closed_at),
        )
        lock.completed_at = utcnow()
        session.flush()
        return {"lotId": lot_id, "result": "closed_without_winner", "publicId": lot.public_id}

    winner = session.get(User, winning_bid.bidder_id)
    assert winner is not None
    winner_alias = user_alias_for_lot(lot.public_id, winner.public_id)
    final_amount = winning_bid.amount_cents
    commission, revenue = _commission(final_amount)

    wallets = wallet_service.lock_wallets(session, [winner.id, lot.auctioneer_id])
    winner_wallet = wallets[winner.id]
    auctioneer_wallet = wallets[lot.auctioneer_id]

    settled_exists = session.scalar(
        select(WalletMovement.id).where(WalletMovement.dedupe_key == f"settlement:{winning_bid.id}")
    )
    if not settled_exists:
        wallet_service.settle_reservation(
            session,
            winner_wallet,
            bid_id=winning_bid.id,
            lot_id=lot.id,
            amount_cents=final_amount,
            description=f"Liquidação de lote arrematado · {lot.title}",
        )
    revenue_exists = session.scalar(
        select(WalletMovement.id).where(WalletMovement.dedupe_key == f"revenue:{lot.id}")
    )
    if not revenue_exists and revenue > 0:
        wallet_service.credit_revenue(
            session,
            auctioneer_wallet,
            lot_id=lot.id,
            amount_cents=revenue,
            description=f"Receita de lote liquidado · {lot.title}",
        )

    winning_bid.status = "won"
    for other in session.scalars(
        select(Bid).where(Bid.lot_id == lot.id, Bid.id != winning_bid.id, Bid.status.in_(("leading", "outbid")))
    ).all():
        other.status = "lost"

    lot.status = "ended"
    lot.winner_bid_id = winning_bid.id
    lot.winner_user_id = winner.id
    lot.final_amount_cents = final_amount
    lot.revenue_cents = revenue
    lot.commission_bps_applied = settings.settlement_commission_bps
    lot.settled_at = utcnow()
    lot.revision += 1
    session.flush()

    receipt = session.scalar(select(Receipt).where(Receipt.lot_id == lot.id))
    if receipt is None:
        receipt = Receipt(
            public_id=receipt_id(lot.number, f"{lot.public_id}:{winning_bid.public_id}"),
            lot_id=lot.id,
            bid_id=winning_bid.id,
            winner_user_id=winner.id,
            winner_alias=winner_alias,
            final_amount_cents=final_amount,
            commission_cents=commission,
            revenue_cents=revenue,
            currency=settings.currency,
            closed_at=closed_at,
            settled_at=utcnow(),
            verification_id=verification_id(f"{lot.public_id}:{winning_bid.public_id}:{final_amount}"),
            integrity_status="available",
        )
        try:
            session.add(receipt)
            session.flush()
        except IntegrityError: 
            session.rollback()
            raise AppError(409, ErrorCode.CONFLICT, "A liquidação já foi aplicada.")
    receipt.integrity_status = "verified" if _chain_ok(session, lot) else "failed"
    session.flush()

    _emit_closed(
        session,
        lot,
        closed_at,
        winner_alias=winner_alias,
        receipt_public_id=receipt.public_id,
        final_amount=final_amount,
    )
    record_business_event(
        session,
        lot=lot,
        type="lot.settled",
        occurred_at=utcnow(),
        data={
            "finalAmountCents": final_amount,
            "revenueCents": revenue,
            "commissionCents": commission,
            "commissionBps": settings.settlement_commission_bps,
            "winnerAlias": winner_alias,
            "receiptId": receipt.public_id,
        },
        sse_type="lot.state.changed",
        sse_payload=room_snapshot(lot),
    )
    lock.completed_at = utcnow()
    session.flush()
    logger.info(
        "lot_settled",
        extra={"extra_fields": {"lotId": lot.public_id, "finalAmountCents": final_amount, "revenueCents": revenue}},
    )
    return {
        "lotId": lot_id,
        "result": "settled",
        "publicId": lot.public_id,
        "receiptId": receipt.public_id,
        "finalAmountCents": final_amount,
        "revenueCents": revenue,
    }


def _chain_ok(session: Session, lot: Lot) -> bool:
    from app.audit.service import verify_lot_chain

    try:
        verification = verify_lot_chain(session, lot)
    except Exception: 
        return False
    return verification.status != "failed"


def _emit_closed(
    session: Session,
    lot: Lot,
    closed_at: datetime,
    *,
    winner_alias: str | None,
    receipt_public_id: str | None,
    final_amount: int | None,
) -> None:
    record_business_event(
        session,
        lot=lot,
        type="lot.closed",
        occurred_at=closed_at,
        amount_cents=final_amount,
        data={
            "finalAmountCents": final_amount,
            "winnerAlias": winner_alias,
            "receiptId": receipt_public_id,
            "bidCount": lot.bid_count,
        },
        sse_type="lot.closed",
        sse_payload={
            "finalAmountCents": final_amount,
            "winnerAlias": winner_alias,
            "receiptId": receipt_public_id,
            "bidCount": lot.bid_count,
        },
    )


def mark_live_lots(session: Session, now: datetime | None = None) -> int:
    now = now or utcnow()
    lots = session.scalars(
        select(Lot)
        .where(
            Lot.status == "scheduled",
            Lot.cancelled_at.is_(None),
            Lot.starts_at <= now,
            Lot.ends_at > now,
        )
        .with_for_update(skip_locked=True)
    ).all()
    changed = 0
    for lot in lots:
        lot.status = "live"
        lot.revision += 1
        _emit_state_changed(session, lot, now)
        changed += 1
    session.flush()
    return changed


def _emit_state_changed(session: Session, lot: Lot, now: datetime) -> None:
    event_id = new_public_id("oevt")
    sequence_value = session.scalar(
        select(func.coalesce(func.max(OutboxEvent.sequence), 0)).where(OutboxEvent.lot_id == lot.id)
    )
    session.add(
        OutboxEvent(
            event_id=event_id,
            lot_id=lot.id,
            type="lot.state.changed",
            sequence=int(sequence_value or 0),
            visibility="public",
            payload={
                "eventId": event_id,
                "lotId": lot.public_id,
                "sequence": int(sequence_value or 0),
                "occurredAt": iso_utc(now),
                "type": "lot.state.changed",
                **room_snapshot(lot, now),
            },
        )
    )


def settle_due_lots(session: Session, *, now: datetime | None = None, batch: int = 50) -> dict[str, Any]:
    now = now or utcnow()
    ids = session.scalars(
        select(Lot.id)
        .where(
            Lot.ends_at <= now,
            Lot.settled_at.is_(None),
            Lot.cancelled_at.is_(None),
        )
        .order_by(Lot.ends_at.asc())
        .limit(batch)
    ).all()
    results: list[dict[str, Any]] = []
    for lot_id in ids:
        try:
            results.append(close_and_settle_lot(session, lot_id, now=now))
            session.commit()
        except AppError as exc:
            session.rollback()
            results.append({"lotId": lot_id, "result": "error", "code": exc.code})
        except Exception as exc: 
            session.rollback()
            logger.exception("settlement_failure", extra={"extra_fields": {"lotId": lot_id}})
            results.append({"lotId": lot_id, "result": "error", "error": type(exc).__name__})
    return {"processed": len(results), "results": results}


def receipt_payload(receipt: Receipt, lot: Lot) -> dict[str, Any]:
    return {
        "id": receipt.public_id,
        "lotId": lot.public_id,
        "lotNumber": lot.number,
        "title": lot.title,
        "artist": lot.artist,
        "imageUrl": lot.image_url,
        "finalAmountCents": receipt.final_amount_cents,
        "currency": receipt.currency,
        "winnerAlias": receipt.winner_alias,
        "closedAt": iso_utc(receipt.closed_at),
        "settledAt": iso_utc(receipt.settled_at),
        "verificationId": receipt.verification_id,
        "integrityStatus": receipt.integrity_status,
    }


def get_public_receipt(session: Session, public_id: str) -> dict[str, Any]:
    row = session.execute(
        select(Receipt, Lot).join(Lot, Lot.id == Receipt.lot_id).where(Receipt.public_id == public_id)
    ).first()
    if row is None:
        raise AppError(404, ErrorCode.NOT_FOUND, "O comprovativo não foi encontrado.")
    receipt, lot = row
    if lot.settled_at is None:
        raise AppError(404, ErrorCode.NOT_FOUND, "O comprovativo ainda não está disponível.")
    return receipt_payload(receipt, lot)


def won_lots(session: Session, *, user: User, page: int, page_size: int) -> tuple[list[dict[str, Any]], int]:
    from app.services.lot_state import public_lot_payload

    stmt = (
        select(Receipt, Lot)
        .join(Lot, Lot.id == Receipt.lot_id)
        .where(Receipt.winner_user_id == user.id)
        .where(Lot.settled_at.is_not(None))
    )
    total = int(session.scalar(select(func.count()).select_from(stmt.subquery())) or 0)
    rows = session.execute(
        stmt.order_by(Receipt.settled_at.desc()).offset((page - 1) * page_size).limit(page_size)
    ).all()
    return [
        {
            "lot": public_lot_payload(lot),
            "finalAmountCents": receipt.final_amount_cents,
            "settledAt": iso_utc(receipt.settled_at),
            "receiptId": receipt.public_id,
        }
        for receipt, lot in rows
    ], total


def ensure_next_minimum_consistency(lot: Lot) -> None:
    if lot.bid_count > 0 and lot.current_bid_cents < lot.starting_bid_cents:
        raise AppError(500, ErrorCode.INTERNAL_ERROR, "Estado de lote inconsistente.")
    next_minimum_bid_cents(lot)
