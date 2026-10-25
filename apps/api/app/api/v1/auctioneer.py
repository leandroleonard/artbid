from __future__ import annotations

from fastapi import APIRouter, Depends, Query, status
from fastapi.responses import JSONResponse

from app.api.deps import (
    AuctioneerUser,
    IdempotencyKey,
    PaginationDep,
    SessionDep,
    rate_limit,
)
from app.core.config import settings
from app.core.errors import validation
from app.db.session import SessionLocal
from app.integrations.art_institute import get_aic_client
from app.realtime.publisher import run_inline_dispatch
from app.schemas.models import (
    ArtworkEnvelope,
    ArtworkPage,
    CancelLotRequest,
    CreateLotRequest,
    PrivateLotEnvelope,
    PrivateLotPage,
    ResultsEnvelope,
)
from app.services import lots as lot_service
from app.services.idempotency import execute_idempotent

router = APIRouter(prefix="/auctioneer", tags=["auctioneer"])


@router.get(
    "/artworks",
    response_model=ArtworkPage,
    dependencies=[Depends(rate_limit("artwork_search", "rate_limit_artwork_search_per_minute", 60, per_user="user"))],
    summary="Pesquisar obras no catálogo",
)
def search_artworks(
    user: AuctioneerUser,
    q: str = Query(..., min_length=2, max_length=100),
    page: int = Query(1, ge=1),
    page_size: int = Query(12, ge=1, le=settings.aic_page_size_max, alias="pageSize"),
) -> dict:
    artworks, total_items = get_aic_client().search(q, page=page, page_size=page_size)
    return {
        "data": [artwork.to_payload() for artwork in artworks],
        "pagination": {
            "page": page,
            "pageSize": page_size,
            "totalItems": total_items,
            "totalPages": (total_items + page_size - 1) // page_size if total_items else 0,
        },
    }


@router.get(
    "/artworks/{artwork_id}",
    response_model=ArtworkEnvelope,
    dependencies=[Depends(rate_limit("artwork_detail", "rate_limit_artwork_search_per_minute", 60, per_user="user"))],
    summary="Detalhe de uma obra do catálogo",
)
def get_artwork(artwork_id: str, user: AuctioneerUser) -> dict:
    if len(artwork_id) > 100:
        raise validation("Identificador inválido.", {"artworkId": ["Comprimento inválido."]})
    return {"data": get_aic_client().get(artwork_id).to_payload()}


@router.get("/lots", response_model=PrivateLotPage, summary="Listar os meus lotes")
def list_my_lots(
    user: AuctioneerUser,
    session: SessionDep,
    paging: PaginationDep,
    status_filter: str | None = Query(None, alias="status"),
    sort: str = Query("recent"),
) -> dict:
    page, page_size = paging
    items, total = lot_service.list_owned_lots(
        session, user=user, page=page, page_size=page_size, status=status_filter, sort=sort
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


@router.post(
    "/lots",
    response_model=PrivateLotEnvelope,
    status_code=status.HTTP_201_CREATED,
    summary="Criar lote a partir de uma obra validada no backend",
)
def create_lot(
    payload: CreateLotRequest,
    user: AuctioneerUser,
    session: SessionDep,
    idempotency_key: IdempotencyKey,
) -> dict:
    from app.services.lot_state import private_lot_payload

    def handler(db):
        lot = lot_service.create_lot(
            db,
            user=user,
            artwork_id=payload.artworkId,
            title=payload.title,
            description=payload.description,
            starting_bid_cents=payload.startingBidCents,
            minimum_increment_cents=payload.minimumIncrementCents,
            starts_at=payload.startsAt,
            ends_at=payload.endsAt,
        )
        return 201, {"data": private_lot_payload(lot)}, lot.public_id

    outcome = execute_idempotent(
        session,
        user_id=user.id,
        operation="create_lot",
        key=idempotency_key,
        request_payload=payload.model_dump(mode="json"),
        handler=handler,
    )
    run_inline_dispatch(SessionLocal)
    return JSONResponse(status_code=outcome.status_code, content=outcome.body)


@router.post(
    "/lots/{lot_id}/cancel",
    response_model=PrivateLotEnvelope,
    summary="Cancelar um lote próprio sem lances",
)
def cancel_lot(
    lot_id: str,
    payload: CancelLotRequest,
    user: AuctioneerUser,
    session: SessionDep,
    idempotency_key: IdempotencyKey,
) -> dict:
    from app.services.lot_state import private_lot_payload

    def handler(db):
        lot = lot_service.cancel_lot(db, user=user, lot_public_id=lot_id)
        return 200, {"data": private_lot_payload(lot)}, lot.public_id

    outcome = execute_idempotent(
        session,
        user_id=user.id,
        operation="cancel_lot",
        key=idempotency_key,
        request_payload={"lotId": lot_id, "confirmation": payload.confirmation},
        handler=handler,
    )
    run_inline_dispatch(SessionLocal)
    return JSONResponse(status_code=outcome.status_code, content=outcome.body)


@router.get("/results", response_model=ResultsEnvelope, summary="Resultados e receita próprios")
def results(user: AuctioneerUser, session: SessionDep, paging: PaginationDep) -> dict:
    page, page_size = paging
    data, total = lot_service.results(session, user=user, page=page, page_size=page_size)
    return {
        "data": data,
        "pagination": {
            "page": page,
            "pageSize": page_size,
            "totalItems": total,
            "totalPages": (total + page_size - 1) // page_size,
        },
    }
