from __future__ import annotations

import re
import secrets
from datetime import UTC, datetime

_ALPHABET = "0123456789abcdefghjkmnpqrstvwxyz"
_ID_RE = re.compile(r"^[a-z]{3,5}_[0-9a-z]{8,40}$")


def new_public_id(prefix: str) -> str:
    return f"{prefix}_{''.join(secrets.choice(_ALPHABET) for _ in range(20))}"


def is_public_id(value: str, prefix: str | None = None) -> bool:
    if not isinstance(value, str) or len(value) > 64:
        return False
    if not _ID_RE.match(value):
        return False
    return prefix is None or value.startswith(f"{prefix}_")


def utcnow() -> datetime:
    return datetime.now(UTC)


def to_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


def iso_utc(value: datetime) -> str:
    normalized = to_utc(value).replace(microsecond=(to_utc(value).microsecond // 1000) * 1000)
    return normalized.strftime("%Y-%m-%dT%H:%M:%S.") + f"{normalized.microsecond // 1000:03d}Z"


def format_lot_number(sequence_value: int) -> str:
    return f"{sequence_value:04d}"
