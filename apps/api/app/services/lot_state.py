from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.ids import iso_utc, utcnow
from app.models import Bid, Lot, User, Wallet


PUBLIC_STATUSES = ("scheduled", "live", "ended")


def effective_status(lot: Lot, now: datetime | None = None) -> str:
    """Estado oficial derivado do estado persistido e do relógio do servidor.

    O browser nunca fornece estado. ``cancelled`` ganha sempre; ``closed_at``
    (encerrado/liquidado) também. Caso contrário o estado é derivado da janela
    oficial [startsAt, endsAt).
    """
    now = now or utcnow()
    if lot.cancelled_at is not None or lot.status == "cancelled":
        return "cancelled"
    if lot.closed_at is not None or lot.status == "ended":
        return "ended"
    if now < lot.starts_at:
        return "scheduled"
    if now >= lot.ends_at:
        return "ended"
    return "live"


def is_open_for_bids(lot: Lot, now: datetime | None = None) -> bool:
    return effective_status(lot, now) == "live"


def next_minimum_bid_cents(lot: Lot) -> int:
    if lot.bid_count == 0:
        return lot.starting_bid_cents
    return lot.current_bid_cents + lot.minimum_increment_cents


def public_lot_payload(lot: Lot, now: datetime | None = None) -> dict[str, Any]:
    """Modelo público ``Lot`` do contrato (§3.1)."""
    status = effective_status(lot, now)
    return {
        "id": lot.public_id,
        "number": lot.number,
        "title": lot.title,
        "artist": lot.artist,
        "artworkDate": lot.artwork_date or "",
        "description": lot.description,
        "imageUrl": lot.image_url,
        "imageAlt": lot.image_alt or lot.title,
        "externalArtworkId": lot.external_artwork_id,
        "status": status,
        "startingBidCents": lot.starting_bid_cents,
        "currentBidCents": lot.current_bid_cents,
        "minimumIncrementCents": lot.minimum_increment_cents,
        "nextMinimumBidCents": next_minimum_bid_cents(lot),
        "startsAt": iso_utc(lot.starts_at),
        "endsAt": iso_utc(lot.ends_at),
        "bidCount": lot.bid_count,
        "createdAt": iso_utc(lot.created_at),
    }


def private_lot_payload(
    lot: Lot,
    *,
    winner_alias: str | None = None,
    now: datetime | None = None,
) -> dict[str, Any]:
    """Modelo privado do leiloeiro: acrescenta cancelamento, resultado e receita."""
    payload = public_lot_payload(lot, now)
    payload.update(
        {
            "cancelledAt": iso_utc(lot.cancelled_at) if lot.cancelled_at else None,
            "cancellationReason": lot.cancellation_reason,
            "finalAmountCents": lot.final_amount_cents,
            "revenueCents": lot.revenue_cents,
            "winnerAlias": winner_alias,
        }
    )
    return payload


def room_snapshot(lot: Lot, now: datetime | None = None) -> dict[str, Any]:
    """Payload do evento ``lot.state.changed`` (snapshot público mínimo)."""
    return {
        "status": effective_status(lot, now),
        "currentBidCents": lot.current_bid_cents,
        "nextMinimumBidCents": next_minimum_bid_cents(lot),
        "endsAt": iso_utc(lot.ends_at),
        "bidCount": lot.bid_count,
    }


def lot_by_public_id(session: Session, public_id: str) -> Lot | None:
    return session.scalar(select(Lot).where(Lot.public_id == public_id))


def get_lot_for_update(session: Session, public_id: str) -> Lot | None:
    """Bloqueio de linha do lote dentro da transacção corrente."""
    return session.scalar(
        select(Lot).where(Lot.public_id == public_id).with_for_update()
    )


def bidder_alias_map(session: Session, lot: Lot, bidder_ids: list[int]) -> dict[int, str]:
    from app.core.aliases import user_alias_for_lot

    if not bidder_ids:
        return {}
    rows = session.execute(select(User.id, User.public_id).where(User.id.in_(set(bidder_ids)))).all()
    return {user_id: user_alias_for_lot(lot.public_id, public_id) for user_id, public_id in rows}


def wallet_snapshot(wallet: Wallet, now: datetime | None = None) -> dict[str, Any]:
    now = now or utcnow()
    return {
        "totalCents": wallet.total_cents,
        "committedCents": wallet.committed_cents,
        "availableCents": wallet.total_cents - wallet.committed_cents,
        "currency": settings.currency,
        "asOf": iso_utc(wallet.updated_at or now),
    }


def public_bid_payload(bid: Bid, alias: str) -> dict[str, Any]:
    return {
        "id": bid.public_id,
        "bidderAlias": alias,
        "amountCents": bid.amount_cents,
        "createdAt": iso_utc(bid.created_at),
    }


def count_active_lots(session: Session, auctioneer_id: int) -> tuple[int, int]:
    total = session.scalar(select(func.count()).select_from(Lot).where(Lot.auctioneer_id == auctioneer_id))
    live = session.scalar(
        select(func.count())
        .select_from(Lot)
        .where(Lot.auctioneer_id == auctioneer_id, Lot.status == "live")
    )
    return int(total or 0), int(live or 0)
