from __future__ import annotations

import logging
from collections.abc import Callable
from typing import TypeVar

from psycopg.errors import DeadlockDetected, SerializationFailure
from sqlalchemy.exc import DBAPIError, OperationalError

logger = logging.getLogger(__name__)

T = TypeVar("T")

RETRYABLE_SQLSTATES = {"40001", "40P01"}


def is_retryable_concurrency_error(exc: BaseException) -> bool:
    if isinstance(exc, (DeadlockDetected, SerializationFailure)):
        return True
    if isinstance(exc, (DBAPIError, OperationalError)):
        original = getattr(exc, "orig", None)
        sqlstate = getattr(original, "sqlstate", None) or getattr(original, "pgcode", None)
        if sqlstate in RETRYABLE_SQLSTATES:
            return True
    return False


def run_with_retry(operation: Callable[[], T], attempts: int = 3) -> T:
    last_error: BaseException | None = None
    for attempt in range(1, attempts + 1):
        try:
            return operation()
        except Exception as exc:
            if not is_retryable_concurrency_error(exc) or attempt == attempts:
                raise
            last_error = exc
            logger.warning(
                "transaction_retry",
                extra={"extra_fields": {"attempt": attempt, "reason": type(exc).__name__}},
            )
    raise last_error 
