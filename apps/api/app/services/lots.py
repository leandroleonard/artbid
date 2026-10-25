from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any

from sqlalchemy import Select, func, or_, select
from sqlalchemy.orm import Session

from app.audit.service import record_business_event
from app.core.aliases import user_alias_for_lot
from app.core.config import settings
from app.core.errors import AppError, ErrorCode, not_found, validation
from app.core.ids import format_lot_number, iso_utc, new_public_id, to_utc, utcnow
from app.integrations.art_institute import Artwork, get_aic_client
from app.models import Bid, Lot, LotSequence, User
from app.services.lot_state import (
    effective_status,
    private_lot_payload,
    public_lot_payload,
)

PUBLIC_SORTS = {
    "endingSoon": (Lot.ends_at.asc(), Lot.id.asc()),
    "recent": (Lot.created_at.desc(), Lot.id.desc()),
    "highestBid": (Lot.current_bid_cents.desc(), Lot.id.desc()),
}

PRIVATE_SORTS = {
    "recent": (Lot.created_at.desc(), Lot.id.desc()),
    "endingSoon": (Lot.ends_at.asc(), Lot.id.asc()),
}


def allocate_lot_number(session: Session) -> str:
    row = session.execute(
        select(LotSequence).where(LotSequence.id == 1).with_for_update()
    ).scalar_one_or_none()
    if row is None:
        row = LotSequence(id=1, next_value=1)
        session.add(row)
        session.flush()
    value = row.next_value
    row.next_value = value + 1
    session.flush()
    return format_lot_number(value)


def _apply_public_visibility(stmt: Select, now: datetime) -> Select:
    return stmt.where(Lot.cancelled_at.is_(None)).where(Lot.status != "cancelled")


def _apply_status_filter(stmt: Select, status: str | None, now: datetime) -> Select:
    if status == "scheduled":
        return stmt.where(Lot.status == "scheduled", Lot.starts_at > now, Lot.cancelled_at.is_(None))
    if status == "live":
        return stmt.where(
            Lot.status != "cancelled",
            Lot.closed_at.is_(None),
            Lot.starts_at <= now,
            Lot.ends_at > now,
        )
    if status == "ended":
        return stmt.where(
            Lot.status != "cancelled",
            or_(Lot.closed_at.is_not(None), Lot.ends_at <= now),
        )
    return stmt


def list_public_lots(
    session: Session,
    *,
    page: int,
    page_size: int,
    q: str | None,
    status: str | None,
    sort: str,
) -> tuple[list[dict[str, Any]], int]:
    now = utcnow()
    if sort not in PUBLIC_SORTS:
        raise validation("Ordenação não permitida.", {"sort": ["Valor inválido."]})
    if status is not None and status not in ("scheduled", "live", "ended"):
        raise validation("Estado não permitido.", {"status": ["Valor inválido."]})

    stmt = select(Lot)
    stmt = _apply_public_visibility(stmt, now)
    stmt = _apply_status_filter(stmt, status, now)
    if q:
        term = f"%{q.strip().lower()}%"
        stmt = stmt.where(
            or_(func.lower(Lot.title).like(term), func.lower(Lot.artist).like(term))
        )
    count_stmt = select(func.count()).select_from(stmt.subquery())
    total = int(session.scalar(count_stmt) or 0)
    rows = session.scalars(
        stmt.order_by(*PUBLIC_SORTS[sort]).offset((page - 1) * page_size).limit(page_size)
    ).all()
    return [public_lot_payload(lot, now) for lot in rows], total


def get_public_lot(session: Session, lot_public_id: str) -> Lot:
    lot = session.scalar(
        select(Lot).where(Lot.public_id == lot_public_id, Lot.cancelled_at.is_(None))
    )
    if lot is None:
        raise not_found("O lote não foi encontrado.")
    return lot


def get_owned_lot(session: Session, user: User, lot_public_id: str, *, lock: bool = False) -> Lot:
    stmt = select(Lot).where(Lot.public_id == lot_public_id)
    if lock:
        stmt = stmt.with_for_update()
    lot = session.scalar(stmt)
    if lot is None:
        raise not_found("O lote não foi encontrado.")
    if lot.auctioneer_id != user.id:
        raise not_found("O lote não foi encontrado.")
    return lot


def list_owned_lots(
    session: Session,
    *,
    user: User,
    page: int,
    page_size: int,
    status: str | None,
    sort: str = "recent",
) -> tuple[list[dict[str, Any]], int]:
    now = utcnow()
    stmt = select(Lot).where(Lot.auctioneer_id == user.id)
    if status == "cancelled":
        stmt = stmt.where(or_(Lot.status == "cancelled", Lot.cancelled_at.is_not(None)))
    elif status in ("scheduled", "live", "ended"):
        stmt = stmt.where(Lot.cancelled_at.is_(None))
        stmt = _apply_status_filter(stmt, status, now)
    elif status is not None:
        raise validation("Estado não permitido.", {"status": ["Valor inválido."]})
    total = int(session.scalar(select(func.count()).select_from(stmt.subquery())) or 0)
    rows = session.scalars(
        stmt.order_by(*PRIVATE_SORTS.get(sort, PRIVATE_SORTS["recent"]))
        .offset((page - 1) * page_size)
        .limit(page_size)
    ).all()
    alias_map = _winner_aliases(session, rows)
    return [private_lot_payload(lot, winner_alias=alias_map.get(lot.id), now=now) for lot in rows], total


def _winner_aliases(session: Session, lots: list[Lot]) -> dict[int, str]:
    ids = [lot.id for lot in lots if lot.winner_user_id]
    if not ids:
        return {}
    rows = session.execute(
        select(Lot.id, User.public_id).join(User, User.id == Lot.winner_user_id).where(Lot.id.in_(ids))
    ).all()
    by_lot: dict[int, str] = {}
    lot_map = {lot.id: lot for lot in lots}
    for lot_id, user_public_id in rows:
        lot = lot_map[lot_id]
        by_public_id = user_public_id
        by_lot[lot_id] = user_alias_for_lot(lot.public_id, by_public_id)
    return by_lot


def validate_schedule(starts_at: datetime, ends_at: datetime, now: datetime | None = None) -> None:
    now = now or utcnow()
    starts_at = to_utc(starts_at)
    ends_at = to_utc(ends_at)
    field_errors: dict[str, list[str]] = {}
    if ends_at <= starts_at:
        field_errors["endsAt"] = ["O fim deve ser posterior ao início."]
    else:
        duration = (ends_at - starts_at).total_seconds()
        if duration < settings.lot_min_duration_seconds:
            field_errors["endsAt"] = [
                f"A duração mínima do lote é {settings.lot_min_duration_seconds // 60} minutos."
            ]
        if duration > settings.lot_max_duration_seconds:
            field_errors["endsAt"] = [
                f"A duração máxima do lote é {settings.lot_max_duration_seconds // 86400} dias."
            ]
    if starts_at < now - timedelta(seconds=settings.lot_clock_skew_seconds):
        field_errors["startsAt"] = ["O início não pode estar no passado."]
    if starts_at > now + timedelta(seconds=settings.lot_max_lead_seconds):
        field_errors["startsAt"] = [
            f"O início não pode exceder {settings.lot_max_lead_seconds // 86400} dias de antecedência."
        ]
    if field_errors:
        raise validation("A agenda do lote é inválida.", field_errors)


def validate_amounts(starting_bid_cents: int, minimum_increment_cents: int) -> None:
    errors: dict[str, list[str]] = {}
    if not settings.lot_starting_bid_min_cents <= starting_bid_cents <= settings.lot_starting_bid_max_cents:
        errors["startingBidCents"] = [
            "O lance inicial deve estar entre "
            f"{settings.lot_starting_bid_min_cents} e {settings.lot_starting_bid_max_cents} cêntimos."
        ]
    if not settings.lot_min_increment_min_cents <= minimum_increment_cents <= settings.lot_min_increment_max_cents:
        errors["minimumIncrementCents"] = [
            "O incremento mínimo deve estar entre "
            f"{settings.lot_min_increment_min_cents} e {settings.lot_min_increment_max_cents} cêntimos."
        ]
    if minimum_increment_cents > starting_bid_cents:
        errors["minimumIncrementCents"] = ["O incremento não pode exceder o lance inicial."]
    if errors:
        raise validation("Os valores do lote são inválidos.", errors)


def create_lot(
    session: Session,
    *,
    user: User,
    artwork_id: str,
    title: str,
    description: str | None,
    starting_bid_cents: int,
    minimum_increment_cents: int,
    starts_at: datetime,
    ends_at: datetime,
) -> Lot:
    if user.role != "auctioneer":
        raise AppError(403, ErrorCode.FORBIDDEN)
    validate_amounts(starting_bid_cents, minimum_increment_cents)
    validate_schedule(starts_at, ends_at)

    artwork: Artwork = get_aic_client().get(artwork_id)

    now = utcnow()
    lot = Lot(
        public_id=new_public_id("lot"),
        number=allocate_lot_number(session),
        auctioneer_id=user.id,
        title=title,
        artist=artwork.artist,
        artwork_date=artwork.date,
        description=description or artwork.description,
        image_url=artwork.image_url,
        image_alt=artwork.image_alt or f"{artwork.title} — {artwork.artist}",
        external_artwork_id=artwork.id,
        artwork_source=artwork.source,
        artwork_snapshot=artwork.snapshot(),
        status="scheduled" if to_utc(starts_at) > now else "live",
        starting_bid_cents=starting_bid_cents,
        minimum_increment_cents=minimum_increment_cents,
        current_bid_cents=0,
        bid_count=0,
        starts_at=to_utc(starts_at),
        ends_at=to_utc(ends_at),
    )
    session.add(lot)
    session.flush()

    record_business_event(
        session,
        lot=lot,
        type="lot.created",
        actor_ref=user.public_id,
        data={
            "number": lot.number,
            "startingBidCents": starting_bid_cents,
            "minimumIncrementCents": minimum_increment_cents,
            "startsAt": iso_utc(lot.starts_at),
            "endsAt": iso_utc(lot.ends_at),
            "externalArtworkId": artwork.id,
        },
        sse_type="lot.state.changed",
        sse_payload={"status": lot.status, "currentBidCents": 0, "nextMinimumBidCents": starting_bid_cents,
                     "endsAt": iso_utc(lot.ends_at), "bidCount": 0},
    )
    return lot


def cancel_lot(session: Session, *, user: User, lot_public_id: str) -> Lot:
    if user.role != "auctioneer":
        raise AppError(403, ErrorCode.FORBIDDEN)
    lot = get_owned_lot(session, user, lot_public_id, lock=True)
    if lot.cancelled_at is not None:
        return lot
    bid_count = session.scalar(select(func.count()).select_from(Bid).where(Bid.lot_id == lot.id)) or 0
    if bid_count > 0 or lot.bid_count > 0:
        raise AppError(409, ErrorCode.LOT_HAS_BIDS)
    now = utcnow()
    status = effective_status(lot, now)
    if status == "ended":
        raise AppError(409, ErrorCode.CANCELLATION_NOT_ALLOWED)
    lot.status = "cancelled"
    lot.cancelled_at = now
    lot.cancellation_reason = "Cancelado pelo leiloeiro antes do primeiro lance."
    lot.closed_at = now
    lot.revision += 1
    session.flush()

    record_business_event(
        session,
        lot=lot,
        type="lot.cancelled",
        actor_ref=user.public_id,
        data={"reason": "Cancelado pelo leiloeiro antes do primeiro lance.", "cancelledAt": iso_utc(now)},
        sse_type="lot.cancelled",
        sse_payload={"reason": "Cancelado pelo leiloeiro."},
    )
    return lot


def results(session: Session, *, user: User, page: int, page_size: int) -> tuple[dict[str, Any], int]:
    if user.role != "auctioneer":
        raise AppError(403, ErrorCode.FORBIDDEN)
    now = utcnow()
    base = select(Lot).where(Lot.auctioneer_id == user.id)
    total_lots = int(session.scalar(select(func.count()).select_from(base.subquery())) or 0)
    live_lots = int(
        session.scalar(
            select(func.count())
            .select_from(Lot)
            .where(
                Lot.auctioneer_id == user.id,
                Lot.cancelled_at.is_(None),
                Lot.closed_at.is_(None),
                Lot.starts_at <= now,
                Lot.ends_at > now,
            )
        )
        or 0
    )
    ended_lots = int(
        session.scalar(
            select(func.count())
            .select_from(Lot)
            .where(Lot.auctioneer_id == user.id, or_(Lot.closed_at.is_not(None), Lot.ends_at <= now))
        )
        or 0
    )
    total_revenue = int(
        session.scalar(
            select(func.coalesce(func.sum(Lot.revenue_cents), 0)).where(
                Lot.auctioneer_id == user.id, Lot.settled_at.is_not(None)
            )
        )
        or 0
    )
    rows = session.scalars(
        base.order_by(Lot.ends_at.desc(), Lot.id.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    ).all()
    alias_map = _winner_aliases(session, rows)
    summary = {
        "summary": {
            "totalLots": total_lots,
            "liveLots": live_lots,
            "endedLots": ended_lots,
            "totalRevenueCents": total_revenue,
            "currency": settings.currency,
        },
        "lots": [private_lot_payload(lot, winner_alias=alias_map.get(lot.id), now=now) for lot in rows],
    }
    return summary, total_lots
