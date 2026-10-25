from __future__ import annotations

import asyncio
import json
from datetime import timedelta

from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import StreamingResponse
from sqlalchemy import func, select

from app.api.deps import OptionalUser, PaginationDep, SearchTerm, SessionDep
from app.core.config import settings
from app.core.errors import AppError, ErrorCode
from app.core.ids import iso_utc, utcnow
from app.core.logging import request_id_ctx
from app.db.session import SessionLocal
from app.models import OutboxEvent
from app.realtime.broker import connection_limiter, get_broker
from app.schemas.models import LotEnvelope, LotPage, RoomEnvelope
from app.services import bids as bid_service
from app.services import lots as lot_service
from app.services.lot_state import public_lot_payload, room_snapshot

router = APIRouter(prefix="/lots", tags=["catalog"])


@router.get("", response_model=LotPage, summary="Listar lotes públicos")
def list_lots(
    session: SessionDep,
    paging: PaginationDep,
    q: SearchTerm = None,
    status_filter: str | None = Query(None, alias="status"),
    sort: str = Query("endingSoon"),
) -> dict:
    page, page_size = paging
    items, total = lot_service.list_public_lots(
        session, page=page, page_size=page_size, q=q, status=status_filter, sort=sort
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


@router.get("/{lot_id}", response_model=LotEnvelope, summary="Detalhe público de um lote")
def get_lot(lot_id: str, session: SessionDep) -> dict:
    lot = lot_service.get_public_lot(session, lot_id)
    return {"data": public_lot_payload(lot)}


@router.get("/{lot_id}/room", response_model=RoomEnvelope, summary="Sala do leilão (Bearer opcional)")
def get_room(lot_id: str, session: SessionDep, auth: OptionalUser = None) -> dict:
    lot = lot_service.get_public_lot(session, lot_id)
    user = auth[0] if auth else None
    position = bid_service.viewer_position(session, lot=lot, user=user) if user else None
    return {
        "data": {
            "lot": public_lot_payload(lot),
            "publicBids": bid_service.public_bids(session, lot=lot, limit=25),
            "viewerPosition": position,
            "serverTime": iso_utc(utcnow()),
        }
    }


def sse_frame(event_id: str, event_type: str, payload: dict) -> str:
    return f"id: {event_id}\nevent: {event_type}\ndata: {json.dumps(payload, separators=(',', ':'))}\n\n"


def event_is_visible(message: dict, *, lot_public_id: str, viewer_user_id: int | None) -> bool:
    """Filtro de privacidade do stream: eventos privados só para o licitante alvo."""
    if message.get("lotId") != lot_public_id:
        return False
    if message.get("_visibility") != "private":
        return True
    return viewer_user_id is not None and message.get("_targetUserId") == viewer_user_id


def _stream_context(lot_id: str) -> tuple[dict, int]:
    """Lê o snapshot inicial numa sessão curta (nunca mantém sessão aberta no stream)."""
    with SessionLocal() as probe:
        lot = lot_service.get_public_lot(probe, lot_id)
        snapshot = room_snapshot(lot)
        last_sequence = int(
            probe.scalar(
                select(func.coalesce(func.max(OutboxEvent.sequence), 0)).where(OutboxEvent.lot_id == lot.id)
            )
            or 0
        )
    return snapshot, last_sequence


@router.get(
    "/{lot_id}/events",
    summary="Stream SSE de eventos do lote",
    response_class=StreamingResponse,
    responses={200: {"content": {"text/event-stream": {}}}},
)
async def lot_events(lot_id: str, request: Request, auth: OptionalUser = None) -> StreamingResponse:
    snapshot, last_sequence = _stream_context(lot_id)

    viewer_user_id = auth[0].id if auth else None
    identity = (
        f"user:{viewer_user_id}"
        if viewer_user_id
        else (request.client.host if request.client else "unknown")
    )
    if not await connection_limiter.acquire(identity):
        raise AppError(429, ErrorCode.RATE_LIMITED, "Demasiadas ligações simultâneas ao stream.", retryable=True)

    async def event_stream():
        heartbeat = settings.sse_heartbeat_seconds
        deadline = utcnow() + timedelta(seconds=settings.sse_max_duration_seconds)
        try:
            # Sem replay por Last-Event-ID: enviamos um snapshot para o cliente revalidar
            # via REST (limitação documentada em docs/decisions.md #11).
            snapshot_id = iso_utc(utcnow())
            yield sse_frame(
                f"snap-{snapshot_id}",
                "lot.state.changed",
                {
                    "eventId": f"snap-{snapshot_id}",
                    "lotId": lot_id,
                    "sequence": last_sequence,
                    "occurredAt": snapshot_id,
                    "type": "lot.state.changed",
                    **snapshot,
                },
            )
            subscription = await get_broker().subscribe(lot_id)
            async with subscription:
                last_beat = utcnow()
                while True:
                    if await request.is_disconnected():
                        break
                    if utcnow() >= deadline:
                        break
                    try:
                        message = await asyncio.wait_for(subscription.get(), timeout=1.0)
                    except asyncio.TimeoutError:
                        message = None
                    if message is None:
                        if (utcnow() - last_beat).total_seconds() >= heartbeat:
                            yield ": ping\n\n"
                            last_beat = utcnow()
                        continue
                    last_beat = utcnow()
                    if not event_is_visible(
                        message, lot_public_id=lot_id, viewer_user_id=viewer_user_id
                    ):
                        continue
                    payload = {key: value for key, value in message.items() if not key.startswith("_")}
                    yield sse_frame(
                        str(payload.get("eventId", "")),
                        str(payload.get("type", "message")),
                        payload,
                    )
        except asyncio.CancelledError:  # cliente terminou a ligação
            raise
        finally:
            await connection_limiter.release(identity)

    headers = {
        "Cache-Control": "no-cache, no-store, no-transform",
        "X-Accel-Buffering": "no",
    }
    request_id = request_id_ctx.get()
    if request_id:
        headers["X-Request-Id"] = request_id
    return StreamingResponse(event_stream(), headers=headers, media_type="text/event-stream")


__all__ = ["router", "sse_frame", "event_is_visible", "Depends"]
