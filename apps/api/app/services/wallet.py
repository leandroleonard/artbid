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
    "deposit": "Depósito simulado de créditos",
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
