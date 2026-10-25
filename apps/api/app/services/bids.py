from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.audit.service import record_business_event
from app.core.aliases import user_alias_for_lot
from app.core.config import settings
from app.core.errors import AppError, ErrorCode, not_found, validation
from app.core.ids import iso_utc, new_public_id, utcnow
from app.models import Bid, Lot, User
from app.services import wallet as wallet_service
from app.services.lot_state import effective_status, next_minimum_bid_cents

BID_HOLD_DESCRIPTION = "Saldo reservado · {title}"
BID_RELEASE_DESCRIPTION = "Saldo libertado · lance ultrapassado"


def _lock_lot(session: Session, lot_public_id: str) -> Lot:
    lot = session.scalar(select(Lot).where(Lot.public_id == lot_public_id).with_for_update())
    if lot is None:
        raise not_found("O lote não foi encontrado.")
    return lot


def _validate_lot_open(lot: Lot, now: datetime) -> None:
    status = effective_status(lot, now)
    if status == "cancelled":
        raise AppError(409, ErrorCode.LOT_CANCELLED)
    if status == "ended":
        raise AppError(409, ErrorCode.LOT_ENDED)
    if status == "scheduled":
        raise AppError(409, ErrorCode.LOT_NOT_OPEN)


def _validate_amount(lot: Lot, amount_cents: int) -> None:
    if amount_cents < settings.bid_min_cents or amount_cents > settings.bid_max_cents:
        raise validation(
            "O valor do lance está fora dos limites permitidos.",
            {
                "amountCents": [
                    f"O lance deve estar entre {settings.bid_min_cents} e {settings.bid_max_cents} cêntimos."
                ]
            },
        )
    minimum = next_minimum_bid_cents(lot)
    if amount_cents < minimum:
        raise AppError(
            422,
            ErrorCode.BID_TOO_LOW,
            f"O lance deve ser de pelo menos {minimum / 100:.2f} {settings.currency}.",
            field_errors={
                "amountCents": [
                    "Valor inferior ao mínimo actual." if lot.bid_count
                    else "Valor inferior ao lance inicial."
                ]
            },
        )


def _apply_anti_sniping(lot: Lot, now: datetime) -> tuple[datetime, datetime] | None:
    window = timedelta(seconds=settings.anti_sniping_window_seconds)
    if lot.ends_at - now > window:
        return None
    if lot.extension_count >= settings.anti_sniping_max_extensions:
        return None
    previous_ends_at = lot.ends_at
    lot.ends_at = previous_ends_at + timedelta(seconds=settings.anti_sniping_extension_seconds)
    lot.extension_count += 1
    lot.revision += 1
    return previous_ends_at, lot.ends_at


def place_bid(
    session: Session,
    *,
    user: User,
    lot_public_id: str,
    amount_cents: int,
) -> dict[str, Any]:
    if user.role == "auctioneer":
        raise AppError(403, ErrorCode.AUCTIONEER_CANNOT_BID)
    if user.role != "bidder":
        raise AppError(403, ErrorCode.FORBIDDEN)

    now = utcnow()
    lot = _lock_lot(session, lot_public_id)
    if lot.auctioneer_id == user.id:
        raise AppError(403, ErrorCode.AUCTIONEER_CANNOT_BID)
    _validate_lot_open(lot, now)
    _validate_amount(lot, amount_cents)

    previous_leading: Bid | None = None
    if lot.leading_bid_id is not None:
        previous_leading = session.get(Bid, lot.leading_bid_id)
    if previous_leading is not None and previous_leading.bidder_id == user.id:
        raise AppError(409, ErrorCode.BIDDER_ALREADY_LEADING)

    wallet_ids = [user.id]
    if previous_leading is not None:
        wallet_ids.append(previous_leading.bidder_id)
    wallets = wallet_service.lock_wallets(session, wallet_ids)
    bidder_wallet = wallets[user.id]
    if wallet_service.available_cents(bidder_wallet) < amount_cents:
        raise AppError(
            422,
            ErrorCode.INSUFFICIENT_AVAILABLE_BALANCE,
            field_errors={"amountCents": ["Saldo disponível insuficiente."]},
        )

    bidder_alias = user_alias_for_lot(lot.public_id, user.public_id)

    if previous_leading is not None:
        previous_leading.status = "outbid"
        previous_leading.outbid_at = now
        session.flush()

    bid = Bid(
        public_id=new_public_id("bid"),
        lot_id=lot.id,
        bidder_id=user.id,
        amount_cents=amount_cents,
        status="leading",
        sequence_in_lot=lot.bid_count + 1,
        created_at=now,
    )
    session.add(bid)
    session.flush()

    wallet_service.reservation_for_bid(
        session,
        bidder_wallet,
        bid_id=bid.id,
        lot_id=lot.id,
        amount_cents=amount_cents,
        description=BID_HOLD_DESCRIPTION.format(title=lot.title),
    )

    if previous_leading is not None:
        previous_wallet = wallets.get(previous_leading.bidder_id)
        if previous_wallet is not None:
            already_released = session.scalar(
                select(func.count())
                .select_from(wallet_service.WalletMovement)
                .where(wallet_service.WalletMovement.dedupe_key == f"release:{previous_leading.id}")
            )
            if not already_released:
                wallet_service.release_reservation(
                    session,
                    previous_wallet,
                    bid_id=previous_leading.id,
                    lot_id=lot.id,
                    amount_cents=previous_leading.amount_cents,
                    description=BID_RELEASE_DESCRIPTION,
                )

    previous_current = lot.current_bid_cents
    lot.current_bid_cents = amount_cents
    lot.bid_count += 1
    lot.leading_bid_id = bid.id
    lot.status = "live"
    lot.revision += 1
    session.flush()

    extension = _apply_anti_sniping(lot, now)

    record_business_event(
        session,
        lot=lot,
        type="bid.accepted",
        actor_alias=bidder_alias,
        actor_ref=user.public_id,
        amount_cents=amount_cents,
        occurred_at=now,
        data={
            "bidId": bid.public_id,
            "bidderAlias": bidder_alias,
            "previousCurrentBidCents": previous_current,
            "bidCount": lot.bid_count,
            "previousBidId": previous_leading.public_id if previous_leading else None,
        },
        sse_type="bid.accepted",
        sse_payload={
            "bid": {
                "id": bid.public_id,
                "bidderAlias": bidder_alias,
                "amountCents": amount_cents,
                "createdAt": iso_utc(now),
            },
            "currentBidCents": lot.current_bid_cents,
            "nextMinimumBidCents": next_minimum_bid_cents(lot),
            "bidCount": lot.bid_count,
        },
    )

    if extension is not None:
        previous_ends_at, new_ends_at = extension
        record_business_event(
            session,
            lot=lot,
            type="lot.extended",
            actor_alias=bidder_alias,
            actor_ref=user.public_id,
            occurred_at=now,
            data={
                "previousEndsAt": iso_utc(previous_ends_at),
                "endsAt": iso_utc(new_ends_at),
                "extensionCount": lot.extension_count,
            },
            sse_type="lot.extended",
            sse_payload={
                "previousEndsAt": iso_utc(previous_ends_at),
                "endsAt": iso_utc(new_ends_at),
            },
        )

    if previous_leading is not None:
        from app.models import OutboxEvent

        private_event_id = new_public_id("oevt")
        sequence_value = session.scalar(
            select(func.coalesce(func.max(OutboxEvent.sequence), 0)).where(OutboxEvent.lot_id == lot.id)
        )
        session.add(
            OutboxEvent(
                event_id=private_event_id,
                lot_id=lot.id,
                type="bid.outbid",
                sequence=int(sequence_value or 0),
                visibility="private",
                target_user_id=previous_leading.bidder_id,
                payload={
                    "eventId": private_event_id,
                    "lotId": lot.public_id,
                    "sequence": int(sequence_value or 0),
                    "occurredAt": iso_utc(now),
                    "type": "bid.outbid",
                    "previousBidId": previous_leading.public_id,
                    "nextMinimumBidCents": next_minimum_bid_cents(lot),
                },
            )
        )
        session.flush()

    session.refresh(bidder_wallet)
    return {
        "bid": {
            "id": bid.public_id,
            "lotId": lot.public_id,
            "lotTitle": lot.title,
            "amountCents": bid.amount_cents,
            "status": "leading",
            "createdAt": iso_utc(bid.created_at),
        },
        "room": {
            "currentBidCents": lot.current_bid_cents,
            "nextMinimumBidCents": next_minimum_bid_cents(lot),
            "endsAt": iso_utc(lot.ends_at),
            "bidCount": lot.bid_count,
        },
        "wallet": wallet_service.wallet_payload(bidder_wallet),
    }


def list_my_bids(
    session: Session, *, user: User, page: int, page_size: int, status: str | None
) -> tuple[list[dict[str, Any]], int]:
    if user.role == "auctioneer":
        raise AppError(403, ErrorCode.AUCTIONEER_CANNOT_BID)
    stmt = (
        select(Bid, Lot)
        .join(Lot, Lot.id == Bid.lot_id)
        .where(Bid.bidder_id == user.id)
        .where(Bid.status != "lost")  
    )
    if status:
        if status not in ("leading", "outbid", "won", "lost"):
            raise validation("Estado não permitido.", {"status": ["Valor inválido."]})
        stmt = stmt.where(Bid.status == status)
    total = int(session.scalar(select(func.count()).select_from(stmt.subquery())) or 0)
    rows = session.execute(
        stmt.order_by(Bid.created_at.desc(), Bid.id.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    ).all()
    payload = [
        {
            "id": bid.public_id,
            "lotId": lot.public_id,
            "lotTitle": lot.title,
            "amountCents": bid.amount_cents,
            "status": bid.status,
            "createdAt": iso_utc(bid.created_at),
        }
        for bid, lot in rows
    ]
    return payload, total


def viewer_position(session: Session, *, lot: Lot, user: User) -> dict[str, Any] | None:
    if user.role != "bidder":
        return None
    my_bids = session.execute(
        select(Bid.amount_cents, Bid.status)
        .where(Bid.lot_id == lot.id, Bid.bidder_id == user.id)
        .order_by(Bid.amount_cents.desc())
    ).all()
    if not my_bids:
        return {"status": "none", "highestBidCents": 0, "committedCents": 0}
    highest = max(amount for amount, _ in my_bids)
    leading = any(status == "leading" for _, status in my_bids)
    won = any(status == "won" for _, status in my_bids)
    status = "leading" if leading else "won" if won else "outbid"
    wallet = wallet_service.get_or_create_wallet(session, user)
    committed = 0
    if leading:
        committed = min(highest, wallet.committed_cents)
    return {"status": status, "highestBidCents": highest, "committedCents": committed}


def public_bids(session: Session, *, lot: Lot, limit: int = 20) -> list[dict[str, Any]]:
    rows = session.execute(
        select(Bid, User.public_id)
        .join(User, User.id == Bid.bidder_id)
        .where(Bid.lot_id == lot.id)
        .order_by(Bid.created_at.desc(), Bid.id.desc())
        .limit(limit)
    ).all()
    return [
        {
            "id": bid.public_id,
            "bidderAlias": user_alias_for_lot(lot.public_id, bidder_public_id),
            "amountCents": bid.amount_cents,
            "createdAt": iso_utc(bid.created_at),
        }
        for bid, bidder_public_id in rows
    ]
