from __future__ import annotations

import logging
import time

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.errors import rate_limited

logger = logging.getLogger(__name__)


class DatabaseRateLimiter:
    def __init__(self, session: Session) -> None:
        self.session = session

    def hit(self, bucket: str, identity: str, limit: int, window_seconds: int) -> None:
        if limit <= 0:
            return
        window_start = int(time.time() // window_seconds)
        key = f"{bucket}:{identity}:{window_seconds}:{window_start}"
        try:
            row = self.session.execute(
                text(
                    """
                    INSERT INTO rate_limit_counter (bucket_key, hits, window_started_at, expires_at)
                    VALUES (:key, 1, now(), now() + make_interval(secs => :ttl))
                    ON CONFLICT (bucket_key) DO UPDATE
                       SET hits = rate_limit_counter.hits + 1
                    RETURNING hits
                    """
                ),
                {"key": key, "ttl": window_seconds + 5},
            ).scalar_one()
            self.session.commit()
        except Exception as exc: 
            self.session.rollback()
            logger.warning(
                "rate_limit_backend_failure",
                extra={"extra_fields": {"bucket": bucket, "error": type(exc).__name__, "detail": str(exc)[:200]}},
            )
            return
        if row > limit:
            retry_after = max(1, (window_start + 1) * window_seconds - int(time.time()))
            raise rate_limited(retry_after)


class RedisRateLimiter:
    def __init__(self, client) -> None:
        self.client = client

    def hit(self, bucket: str, identity: str, limit: int, window_seconds: int) -> None:
        if limit <= 0:
            return
        window_start = int(time.time() // window_seconds)
        key = f"rl:{bucket}:{identity}:{window_seconds}:{window_start}"
        try:
            pipe = self.client.pipeline()
            pipe.incr(key)
            pipe.expire(key, window_seconds + 5, nx=True)
            hits = pipe.execute()[0]
        except Exception: 
            logger.warning("rate_limit_redis_failure", extra={"extra_fields": {"bucket": bucket}})
            return
        if hits > limit:
            retry_after = max(1, (window_start + 1) * window_seconds - int(time.time()))
            raise rate_limited(retry_after)


def client_identity(request) -> str:
    from app.core.config import settings

    if settings.trust_proxy_headers:
        forwarded = request.headers.get("x-forwarded-for")
        if forwarded:
            return forwarded.split(",")[0].strip()[:64]
    return (request.client.host if request.client else "unknown")[:64]
