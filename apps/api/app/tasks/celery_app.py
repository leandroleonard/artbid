from __future__ import annotations

from celery import Celery
from celery.schedules import schedule

from app.core.config import settings

celery_app = Celery(
    "artbid",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
    include=["app.tasks.jobs"],
)

celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="UTC",
    enable_utc=True,
    task_acks_late=True,              
    task_reject_on_worker_lost=True,
    worker_prefetch_multiplier=1,
    task_default_queue="artbid",
    broker_connection_retry_on_startup=True,
    result_expires=3600,
    beat_schedule={
        "lot-lifecycle-tick": {
            "task": "app.tasks.jobs.lot_lifecycle_tick",
            "schedule": schedule(run_every=settings.lot_tick_seconds),
        },
        "outbox-dispatch": {
            "task": "app.tasks.jobs.dispatch_outbox",
            "schedule": schedule(run_every=settings.outbox_dispatch_seconds),
        },
        "audit-checkpoint": {
            "task": "app.tasks.jobs.create_audit_checkpoint",
            "schedule": schedule(run_every=settings.audit_checkpoint_interval_seconds),
        },
        "audit-verify": {
            "task": "app.tasks.jobs.verify_audit_chains",
            "schedule": schedule(run_every=settings.audit_verify_seconds),
        },
        "idempotency-cleanup": {
            "task": "app.tasks.jobs.cleanup_idempotency",
            "schedule": schedule(run_every=settings.idempotency_cleanup_seconds),
        },
    },
)
