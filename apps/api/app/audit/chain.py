from __future__ import annotations

import base64
import hashlib
import json
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import (
    Ed25519PrivateKey,
    Ed25519PublicKey,
)

from app.core.config import settings
from app.core.errors import ErrorCode
from app.core.ids import iso_utc, new_public_id, to_utc, utcnow

INTEGRITY_VERIFIED = "verified"
INTEGRITY_FAILED = "failed"
INTEGRITY_UNAVAILABLE = "unavailable"


def canonical_json(payload: Any) -> str:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def sha256_hex(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def event_canonical_payload(
    *,
    chain_version: int,
    event_id: str,
    lot_id: str | None,
    sequence: int,
    type: str,
    actor_alias: str | None,
    actor_ref: str | None,
    amount_cents: int | None,
    data: dict[str, Any],
    occurred_at: datetime,
) -> str:
    return canonical_json(
        {
            "v": chain_version,
            "id": event_id,
            "lotId": lot_id,
            "seq": sequence,
            "type": type,
            "actorAlias": actor_alias,
            "actorRef": actor_ref,
            "amountCents": amount_cents,
            "data": data,
            "occurredAt": iso_utc(occurred_at),
        }
    )


def compute_event_hash(canonical_payload: str, previous_hash: str | None) -> str:
    return sha256_hex(f"{canonical_payload}|{previous_hash or ''}")


def compute_heads_digest(heads: list[dict[str, str]]) -> str:
    normalized = sorted(
        ({"lotId": head["lotId"], "lastHash": head["lastHash"], "sequence": head["sequence"]}
         for head in heads),
        key=lambda head: head["lotId"],
    )
    return sha256_hex(canonical_json({"v": settings.audit_chain_version, "heads": normalized}))


def checkpoint_signing_payload(
    *, key_id: str, chain_version: int, heads_digest: str, lots_covered: int, events_covered: int
) -> bytes:
    return canonical_json(
        {
            "v": chain_version,
            "keyId": key_id,
            "headsDigest": heads_digest,
            "lotsCovered": lots_covered,
            "eventsCovered": events_covered,
        }
    ).encode("utf-8")


def _load_private_key(raw: str) -> Ed25519PrivateKey | None:
    raw = raw.strip()
    if not raw:
        return None
    if "BEGIN" in raw:
        return serialization.load_pem_private_key(raw.encode(), password=None) 
    try:
        return Ed25519PrivateKey.from_private_bytes(base64.b64decode(raw))
    except Exception:
        return None


def _load_public_key(raw: str) -> Ed25519PublicKey | None:
    raw = raw.strip()
    if not raw:
        return None
    if "BEGIN" in raw:
        return serialization.load_pem_public_key(raw.encode()) 
    try:
        return Ed25519PublicKey.from_public_bytes(base64.b64decode(raw))
    except Exception:
        return None


@dataclass
class SignatureState:
    available: bool
    reason: str | None = None


def signing_available() -> SignatureState:
    key = _load_private_key(settings.audit_checkpoint_private_key)
    if key is None:
        return SignatureState(False, "checkpoint_signing_key_not_configured")
    return SignatureState(True)


def verification_key_available() -> bool:
    return _load_public_key(settings.audit_checkpoint_public_key) is not None


def sign_heads(payload: bytes) -> str | None:
    key = _load_private_key(settings.audit_checkpoint_private_key)
    if key is None:
        return None
    return base64.b64encode(key.sign(payload)).decode("ascii")


def verify_signature(payload: bytes, signature_b64: str) -> bool:
    key = _load_public_key(settings.audit_checkpoint_public_key)
    if key is None:
        return False
    try:
        key.verify(base64.b64decode(signature_b64), payload)
        return True
    except (InvalidSignature, ValueError):
        return False


@dataclass
class ChainVerification:
    status: str
    checked_event_count: int
    total_event_count: int
    expected_hash: str | None
    calculated_hash: str | None
    reason: str | None = None
    verified_at: datetime | None = None


def verify_chain_rows(rows: list[Any]) -> ChainVerification:
    now = utcnow()
    if not rows:
        return ChainVerification(INTEGRITY_VERIFIED, 0, 0, None, None, None, now)

    previous_hash: str | None = None
    expected_sequence = rows[0].sequence
    for row in rows:
        if row.sequence != expected_sequence:
            return ChainVerification(
                INTEGRITY_FAILED,
                0,
                len(rows),
                row.hash,
                None,
                "sequence_gap_or_reorder",
                now,
            )
        expected_sequence += 1
        if (row.previous_hash or None) != previous_hash:
            return ChainVerification(
                INTEGRITY_FAILED, 0, len(rows), previous_hash, row.previous_hash, "previous_hash_mismatch", now
            )
        canonical = event_canonical_payload(
            chain_version=row.chain_version,
            event_id=row.public_id,
            lot_id=row.lot_public_id,
            sequence=row.sequence,
            type=row.type,
            actor_alias=row.actor_alias,
            actor_ref=row.actor_ref,
            amount_cents=row.amount_cents,
            data=row.data,
            occurred_at=row.occurred_at,
        )
        calculated = compute_event_hash(canonical, previous_hash)
        if calculated != row.hash:
            return ChainVerification(
                INTEGRITY_FAILED, 0, len(rows), row.hash, calculated, "hash_mismatch", now
            )
        previous_hash = row.hash

    return ChainVerification(
        INTEGRITY_VERIFIED, len(rows), len(rows), rows[-1].hash, rows[-1].hash, None, now
    )


def verification_unavailable(reason: str, total: int) -> ChainVerification:
    return ChainVerification(INTEGRITY_UNAVAILABLE, 0, total, None, None, reason, utcnow())


def error_for_integrity(status: str) -> str:
    if status == INTEGRITY_FAILED:
        return ErrorCode.UPSTREAM_INVALID_RESPONSE
    return ErrorCode.UPSTREAM_INVALID_RESPONSE


def new_checkpoint_id() -> str:
    return new_public_id("chk")


def normalize_dt(value: datetime) -> datetime:
    return to_utc(value)
