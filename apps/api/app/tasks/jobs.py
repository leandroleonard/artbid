from __future__ import annotations

import logging
from datetime import timedelta

from celery import shared_task
from sqlalchemy import delete, select

from app.audit.service import create_checkpoint, export_checkpoint, verify_all_chains
from app.core.ids import utcnow
from app.db.session import SessionLocal
from app.models import RateLimitCounter
from app.services.settlement import mark_live_lots, settle_due_lots
from app.tasks.celery_app import celery_app  

logger = logging.getLogger(__name__)


def _session():
    return SessionLocal()


@shared_task(name="app.tasks.jobs.lot_lifecycle_tick", bind=True, max_retries=3)
def lot_lifecycle_tick(self) -> dict:
    session = _session()
    try:
        promoted = mark_live_lots(session)
        session.commit()
        result = settle_due_lots(session)
        return {"promoted": promoted, "settled": result["processed"]}
    except Exception as exc:
        session.rollback()
        logger.exception("lot_lifecycle_tick_failed")
        raise self.retry(exc=exc, countdown=5)
    finally:
        session.close()


@shared_task(name="app.tasks.jobs.settle_lot", bind=True, max_retries=5)
def settle_lot(self, lot_id: int) -> dict:
    from app.services.settlement import close_and_settle_lot

    session = _session()
    try:
        result = close_and_settle_lot(session, int(lot_id))
        session.commit()
        return result
    except Exception as exc:  
        session.rollback()
        raise self.retry(exc=exc, countdown=10)
    finally:
        session.close()


@shared_task(name="app.tasks.jobs.dispatch_outbox")
def dispatch_outbox() -> dict:
    from app.realtime.publisher import dispatch_pending_sync

    session = _session()
    try:
        published = dispatch_pending_sync(session, limit=200)
        return {"published": published}
    finally:
        session.close()


@shared_task(name="app.tasks.jobs.create_audit_checkpoint")
def create_audit_checkpoint() -> dict:
    session = _session()
    try:
        checkpoint = create_checkpoint(session)
        session.commit()
        if checkpoint is None:
            return {"checkpoint": None}
        export_checkpoint(checkpoint)
        return {
            "checkpointId": checkpoint.public_id,
            "status": checkpoint.status,
            "lotsCovered": checkpoint.lots_covered,
            "eventsCovered": checkpoint.events_covered,
        }
    finally:
        session.close()


@shared_task(name="app.tasks.jobs.verify_audit_chains")
def verify_audit_chains() -> dict:
    session = _session()
    try:
        return verify_all_chains(session)
    finally:
        session.close()


@shared_task(name="app.tasks.jobs.cleanup_idempotency")
def cleanup_idempotency() -> dict:
    from app.services.idempotency import cleanup_expired

    session = _session()
    try:
        removed = cleanup_expired(session)
        cutoff = utcnow() - timedelta(days=1)
        session.execute(delete(RateLimitCounter).where(RateLimitCounter.expires_at < cutoff))
        session.commit()
        return {"idempotencyRemoved": removed}
    finally:
        session.close()


__all__ = [
    "celery_app",
    "cleanup_idempotency",
    "create_audit_checkpoint",
    "dispatch_outbox",
    "lot_lifecycle_tick",
    "settle_lot",
    "verify_audit_chains",
    "select",
]
