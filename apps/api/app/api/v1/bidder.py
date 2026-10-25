from __future__ import annotations

from fastapi import APIRouter, Depends, Query, status
from fastapi.responses import JSONResponse

from app.api.deps import BidderUser, IdempotencyKey, PaginationDep, SessionDep, rate_limit
from app.db.session import SessionLocal
from app.realtime.publisher import run_inline_dispatch
from app.schemas.models import (
    BidAcceptedEnvelope,
    BidPage,
    CreateBidRequest,
    DepositEnvelope,
    DepositRequest,
    MovementPage,
    WalletEnvelope,
    WonPage,
)
from app.services import bids as bid_service
from app.services import settlement as settlement_service
from app.services import wallet as wallet_service
from app.services.idempotency import execute_idempotent

router = APIRouter(tags=["bidder"])


@router.get("/me/wallet", response_model=WalletEnvelope, summary="Saldo oficial da carteira simulada")
def get_wallet(user: BidderUser, session: SessionDep) -> dict:
    wallet = wallet_service.get_or_create_wallet(session, user)
    session.commit()
    return {"data": wallet_service.wallet_payload(wallet)}


@router.post(
    "/me/wallet/deposits",
    response_model=DepositEnvelope,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(rate_limit("deposit", "rate_limit_deposit_per_minute", 60, per_user="user"))],
    summary="Adicionar créditos simulados (não é pagamento real)",
)
def create_deposit(
    payload: DepositRequest,
    user: BidderUser,
    session: SessionDep,
    idempotency_key: IdempotencyKey,
) -> JSONResponse:
    def handler(db):
        wallet, movement = wallet_service.deposit(db, user, payload.amountCents)
        return (
            201,
            {
                "data": {
                    "movement": wallet_service.movement_payload(movement, lot_public_id=None),
                    "wallet": wallet_service.wallet_payload(wallet),
                }
            },
            movement.public_id,
        )

    outcome = execute_idempotent(
        session,
        user_id=user.id,
        operation="wallet_deposit",
        key=idempotency_key,
        request_payload={"amountCents": payload.amountCents},
        handler=handler,
    )
    return JSONResponse(status_code=outcome.status_code, content=outcome.body)


@router.get("/me/movements", response_model=MovementPage, summary="Movimentos da carteira")
def list_movements(
    user: BidderUser,
    session: SessionDep,
    paging: PaginationDep,
) -> dict:
    from sqlalchemy import func, select

    from app.models import Lot, WalletMovement

    page, page_size = paging
    wallet = wallet_service.get_or_create_wallet(session, user)
    base = select(WalletMovement).where(WalletMovement.wallet_id == wallet.id)
    total = int(session.scalar(select(func.count()).select_from(base.subquery())) or 0)
    rows = session.execute(
        base.order_by(WalletMovement.created_at.desc(), WalletMovement.id.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    ).scalars().all()
    lot_ids = {row.lot_id for row in rows if row.lot_id}
    lot_map: dict[int, str] = {}
    if lot_ids:
        lot_map = {
            lot_id: public_id
            for lot_id, public_id in session.execute(
                select(Lot.id, Lot.public_id).where(Lot.id.in_(lot_ids))
            ).all()
        }
    return {
        "data": [
            wallet_service.movement_payload(row, lot_public_id=lot_map.get(row.lot_id) if row.lot_id else None)
            for row in rows
        ],
        "pagination": {
            "page": page,
            "pageSize": page_size,
            "totalItems": total,
            "totalPages": (total + page_size - 1) // page_size,
        },
    }


@router.post(
    "/bids",
    response_model=BidAcceptedEnvelope,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(rate_limit("bid", "rate_limit_bid_per_minute", 60, per_user="user"))],
    summary="Apresentar um lance (transaccional e idempotente)",
)
def create_bid(
    payload: CreateBidRequest,
    user: BidderUser,
    session: SessionDep,
    idempotency_key: IdempotencyKey,
) -> JSONResponse:
    def handler(db):
        result = bid_service.place_bid(
            db, user=user, lot_public_id=payload.lotId, amount_cents=payload.amountCents
        )
        return 201, {"data": result}, result["bid"]["id"]

    outcome = execute_idempotent(
        session,
        user_id=user.id,
        operation="place_bid",
        key=idempotency_key,
        request_payload={"lotId": payload.lotId, "amountCents": payload.amountCents},
        handler=handler,
    )
    # Publicação best-effort imediata; a outbox garante a entrega se falhar.
    run_inline_dispatch(SessionLocal)
    return JSONResponse(status_code=outcome.status_code, content=outcome.body)


@router.get("/me/bids", response_model=BidPage, summary="Histórico de lances do licitante")
def list_bids(
    user: BidderUser,
    session: SessionDep,
    paging: PaginationDep,
    status_filter: str | None = Query(None, alias="status"),
) -> dict:
    page, page_size = paging
    items, total = bid_service.list_my_bids(
        session, user=user, page=page, page_size=page_size, status=status_filter
    )
    return {
        "data": items,
        "pagination": {
            "page": page,
            "pageSize": page_size,
            "totalItems": total,
            "totalPages": (total + page_size - 1) // page_size,
        },
    }


@router.get("/me/won", response_model=WonPage, summary="Lotes ganhos e comprovativos")
def list_won(user: BidderUser, session: SessionDep, paging: PaginationDep) -> dict:
    page, page_size = paging
    items, total = settlement_service.won_lots(session, user=user, page=page, page_size=page_size)
    return {
        "data": items,
        "pagination": {
            "page": page,
            "pageSize": page_size,
            "totalItems": total,
            "totalPages": (total + page_size - 1) // page_size,
        },
    }
