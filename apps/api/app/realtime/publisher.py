from __future__ import annotations

import asyncio
import logging
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.ids import utcnow
from app.models import OutboxEvent
from app.realtime.broker import get_broker, in_process_broker

logger = logging.getLogger(__name__)


def fetch_pending(session: Session, limit: int = 100) -> list[OutboxEvent]:
    return list(
        session.scalars(
            select(OutboxEvent)
            .where(OutboxEvent.published_at.is_(None))
            .order_by(OutboxEvent.id.asc())
            .limit(limit)
            .with_for_update(skip_locked=True)
        ).all()
    )


async def publish_message(lot_public_id: str, message: dict[str, Any]) -> None:
    broker = get_broker()
    try:
        await broker.publish(lot_public_id, message)
    except Exception as exc:  
        logger.warning(
            "sse_publish_failed",
            extra={"extra_fields": {"lotId": lot_public_id, "error": type(exc).__name__}},
        )
        in_process_broker().publish_threadsafe(lot_public_id, message)


async def dispatch_pending_async(session: Session, limit: int = 100) -> int:
    events = fetch_pending(session, limit)
    published = 0
    for event in events:
        lot_public_id = event.payload.get("lotId")
        try:
            if lot_public_id:
                message = dict(event.payload)
                message["_visibility"] = event.visibility
                if event.target_user_id is not None:
                    message["_targetUserId"] = event.target_user_id
                await publish_message(lot_public_id, message)
            event.published_at = utcnow()
            event.publish_attempts += 1
            published += 1
        except Exception as exc: 
            event.publish_attempts += 1
            event.last_error = type(exc).__name__[:300]
    session.commit()
    return published


def dispatch_pending_sync(session: Session, limit: int = 100) -> int:
    return asyncio.run(dispatch_pending_async(session, limit))


def run_inline_dispatch(session_factory, limit: int = 50) -> None:
    async def runner() -> None:
        session = session_factory()
        try:
            await dispatch_pending_async(session, limit)
        finally:
            session.close()

    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        asyncio.run(runner())
        return
    loop.create_task(runner())
