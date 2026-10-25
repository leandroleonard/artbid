from __future__ import annotations

from app.core.config import settings
from app.core.security import hmac_sha256


def lot_alias(scope: str, subject: str) -> str:
    digest = hmac_sha256(settings.audit_alias_secret, f"alias:v1:{scope}:{subject}")
    return f"LIC-{digest[:4].upper()}"


def user_alias_for_lot(lot_public_id: str, user_public_id: str) -> str:
    return lot_alias(lot_public_id, user_public_id)


def verification_id(seed: str) -> str:
    digest = hmac_sha256(settings.audit_alias_secret, f"verify:v1:{seed}").upper()
    return f"VRF-{digest[:4]}-{digest[4:8]}"


def receipt_id(lot_number: str, seed: str) -> str:
    digest = hmac_sha256(settings.audit_alias_secret, f"receipt:v1:{seed}").upper()
    return f"AB-{lot_number}-{digest[:4]}"
