from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.errors import AppError, ErrorCode, validation
from app.core.ids import iso_utc, new_public_id, utcnow
from app.models import User, Wallet, WalletMovement

MOVEMENT_LABELS = {
    "deposit": "Depósito de créditos",
    "hold": "Reserva de saldo para lance líder",
    "release": "Libertação de saldo reservado",
    "settlement": "Liquidação de lote arrematado",
}


def get_or_create_wallet(session: Session, user: User) -> Wallet:
    wallet = session.scalar(select(Wallet).where(Wallet.user_id == user.id))
    if wallet is not None:
        return wallet
    wallet = Wallet(user_id=user.id, total_cents=0, committed_cents=0)
    session.add(wallet)
    session.flush()
    return wallet


def lock_wallet(session: Session, user_id: int) -> Wallet:
    wallet = session.scalar(select(Wallet).where(Wallet.user_id == user_id).with_for_update())
    if wallet is None:
        user = session.get(User, user_id)
        if user is None:
            raise AppError(404, ErrorCode.NOT_FOUND)
        wallet = get_or_create_wallet(session, user)
        wallet = session.scalar(select(Wallet).where(Wallet.id == wallet.id).with_for_update())
    assert wallet is not None
    return wallet


def lock_wallets(session: Session, user_ids: list[int]) -> dict[int, Wallet]:
    if not user_ids:
        return {}
    ids = sorted(set(user_ids))
    rows = list(
        session.scalars(
            select(Wallet).where(Wallet.user_id.in_(ids)).order_by(Wallet.id.asc()).with_for_update()
        ).all()
    )
    by_user = {wallet.user_id: wallet for wallet in rows}
    for user_id in ids:
        if user_id not in by_user:
            user = session.get(User, user_id)
            if user is None: 
                continue
            created = get_or_create_wallet(session, user)
            locked = session.scalar(select(Wallet).where(Wallet.id == created.id).with_for_update())
            if locked is not None:
                by_user[user_id] = locked
    return by_user


def available_cents(wallet: Wallet) -> int:
    return wallet.total_cents - wallet.committed_cents


def wallet_payload(wallet: Wallet) -> dict[str, Any]:
    return {
        "totalCents": wallet.total_cents,
        "committedCents": wallet.committed_cents,
        "availableCents": wallet.total_cents - wallet.committed_cents,
        "currency": settings.currency,
        "asOf": iso_utc(max(wallet.updated_at or utcnow(), utcnow())),
    }


def movement_payload(movement: WalletMovement, *, lot_public_id: str | None) -> dict[str, Any]:
    return {
        "id": movement.public_id,
        "type": movement.type,
        "amountCents": movement.amount_cents,
        "description": movement.description,
        "lotId": lot_public_id,
        "balanceAfterCents": movement.balance_after_cents,
        "createdAt": iso_utc(movement.created_at),
    }


def apply_movement(
    session: Session,
    wallet: Wallet,
    *,
    type: str,
    amount_cents: int,
    total_delta_cents: int = 0,
    committed_delta_cents: int = 0,
    description: str,
    lot_id: int | None = None,
    bid_id: int | None = None,
    dedupe_key: str | None = None,
    user_id: int | None = None,
) -> WalletMovement:
    if type not in MOVEMENT_LABELS: 
        raise ValueError(f"tipo de movimento inválido: {type}")

    new_total = wallet.total_cents + total_delta_cents
    new_committed = wallet.committed_cents + committed_delta_cents

    if new_total < 0 or new_committed < 0 or new_committed > new_total:
        raise AppError(409, ErrorCode.CONFLICT, "Operação de carteira inválida.")

    wallet.total_cents = new_total
    wallet.committed_cents = new_committed
    wallet.version += 1
    wallet.updated_at = utcnow()

    movement = WalletMovement(
        public_id=new_public_id("mov"),
        wallet_id=wallet.id,
        user_id=user_id or wallet.user_id,
        lot_id=lot_id,
        bid_id=bid_id,
        type=type,
        amount_cents=amount_cents,
        committed_delta_cents=committed_delta_cents,
        balance_after_cents=new_total,
        committed_after_cents=new_committed,
        description=description[:200],
        dedupe_key=dedupe_key,
    )
    session.add(movement)
    session.flush()
    return movement


def ensure_max_total(user_wallet: Wallet, amount_cents: int) -> None:
    if user_wallet.total_cents + amount_cents > settings.wallet_max_total_cents:
        raise validation(
            "O saldo total excederia o limite máximo permitido.",
            {"amountCents": ["Limite de saldo excedido."]},
        )


def deposit(session: Session, user: User, amount_cents: int) -> tuple[Wallet, WalletMovement]:
    if amount_cents < settings.deposit_min_cents or amount_cents > settings.deposit_max_cents:
        raise validation(
            "O valor do depósito está fora dos limites permitidos.",
            {
                "amountCents": [
                    f"O depósito deve estar entre {settings.deposit_min_cents} e "
                    f"{settings.deposit_max_cents} cêntimos."
                ]
            },
        )
    wallet = lock_wallet(session, user.id)
    ensure_max_total(wallet, amount_cents)
    movement = apply_movement(
        session,
        wallet,
        type="deposit",
        amount_cents=amount_cents,
        total_delta_cents=amount_cents,
        description=MOVEMENT_LABELS["deposit"],
        user_id=user.id,
    )
    return wallet, movement


def reservation_for_bid(
    session: Session, wallet: Wallet, *, bid_id: int, lot_id: int, amount_cents: int, description: str
) -> WalletMovement:
    if available_cents(wallet) < amount_cents:
        raise AppError(422, ErrorCode.INSUFFICIENT_AVAILABLE_BALANCE)
    return apply_movement(
        session,
        wallet,
        type="hold",
        amount_cents=-amount_cents,
        total_delta_cents=0,
        committed_delta_cents=amount_cents,
        description=description,
        lot_id=lot_id,
        bid_id=bid_id,
        user_id=wallet.user_id,
        dedupe_key=f"hold:{bid_id}",
    )


def release_reservation(
    session: Session, wallet: Wallet, *, bid_id: int, lot_id: int, amount_cents: int, description: str
) -> WalletMovement:
    committed = min(amount_cents, wallet.committed_cents)
    return apply_movement(
        session,
        wallet,
        type="release",
        amount_cents=committed,
        total_delta_cents=0,
        committed_delta_cents=-committed,
        description=description,
        lot_id=lot_id,
        bid_id=bid_id,
        user_id=wallet.user_id,
        dedupe_key=f"release:{bid_id}",
    )


def settle_reservation(
    session: Session, wallet: Wallet, *, bid_id: int, lot_id: int, amount_cents: int, description: str
) -> WalletMovement:
    committed = min(amount_cents, wallet.committed_cents)
    return apply_movement(
        session,
        wallet,
        type="settlement",
        amount_cents=-amount_cents,
        total_delta_cents=-amount_cents,
        committed_delta_cents=-committed,
        description=description,
        lot_id=lot_id,
        bid_id=bid_id,
        user_id=wallet.user_id,
        dedupe_key=f"settlement:{bid_id}",
    )


def credit_revenue(
    session: Session, wallet: Wallet, *, lot_id: int, amount_cents: int, description: str
) -> WalletMovement:
    return apply_movement(
        session,
        wallet,
        type="settlement",
        amount_cents=amount_cents,
        total_delta_cents=amount_cents,
        committed_delta_cents=0,
        description=description,
        lot_id=lot_id,
        user_id=wallet.user_id,
        dedupe_key=f"revenue:{lot_id}",
    )


def movement_created_at(movement: WalletMovement) -> datetime:
    return movement.created_at
