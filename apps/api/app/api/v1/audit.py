
from __future__ import annotations

from fastapi import APIRouter, Query

from app.api.deps import PaginationDep, SessionDep
from app.audit.service import verify_lot_chain
from app.core.config import settings
from app.core.errors import not_found
from app.core.ids import iso_utc, utcnow
from app.models import AuditEvent
from app.schemas.models import AuditEnvelope, ReceiptEnvelope
from app.services import settlement as settlement_service
from app.services.lots import get_public_lot
from sqlalchemy import func, select

router = APIRouter(tags=["audit"])

ALGORITHM = "SHA-256"


@router.get("/audit", response_model=AuditEnvelope, summary="Auditoria de um lote")
def get_audit(
    session: SessionDep,
    paging: PaginationDep,
    lot_id: str = Query(..., alias="lotId", min_length=1, max_length=64),
) -> dict:
    page, page_size = paging
    lot = get_public_lot(session, lot_id)

    base = select(AuditEvent).where(AuditEvent.lot_id == lot.id)
    total = int(session.scalar(select(func.count()).select_from(base.subquery())) or 0)
    rows = session.scalars(
        base.order_by(AuditEvent.sequence.asc()).offset((page - 1) * page_size).limit(page_size)
    ).all()

    verification = verify_lot_chain(session, lot)
    return {
        "data": {
            "lotId": lot.public_id,
            "events": [
                {
                    "id": row.public_id,
                    "sequence": row.sequence,
                    "type": row.type,
                    "actorAlias": row.actor_alias,
                    "amountCents": row.amount_cents,
                    "occurredAt": iso_utc(row.occurred_at),
                    "hash": row.hash,
                    "previousHash": row.previous_hash,
                }
                for row in rows
            ],
            "integrity": {
                "status": verification.status,
                "checkedEventCount": verification.checked_event_count,
                "totalEventCount": verification.total_event_count or total,
                "algorithm": ALGORITHM,
                "expectedHash": verification.expected_hash,
                "calculatedHash": verification.calculated_hash,
                "verifiedAt": iso_utc(verification.verified_at or utcnow()),
                "verificationDataUrl": f"{settings.api_prefix}/receipts",
            },
        },
        "pagination": {
            "page": page,
            "pageSize": page_size,
            "totalItems": total,
            "totalPages": (total + page_size - 1) // page_size,
        },
    }


@router.get("/receipts/{receipt_id}", response_model=ReceiptEnvelope, summary="Comprovativo")
def get_receipt(receipt_id: str, session: SessionDep) -> dict:
    if len(receipt_id) > 64:
        raise not_found("O comprovativo não foi encontrado.")
    return {"data": settlement_service.get_public_receipt(session, receipt_id)}
