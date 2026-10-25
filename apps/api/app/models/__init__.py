from __future__ import annotations

from datetime import datetime

from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Identity,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base

TS = DateTime(timezone=True)


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(TS, server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        TS, server_default=func.now(), onupdate=func.now(), nullable=False
    )


class User(Base, TimestampMixin):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(BigInteger, Identity(), primary_key=True)
    public_id: Mapped[str] = mapped_column(String(40), unique=True, nullable=False)
    display_name: Mapped[str] = mapped_column(String(80), nullable=False)
    email_normalized: Mapped[str] = mapped_column(String(254), unique=True, nullable=False)
    email_display: Mapped[str] = mapped_column(String(254), nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[str] = mapped_column(String(16), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("true"))

    wallet: Mapped["Wallet | None"] = relationship(back_populates="user", uselist=False)

    __table_args__ = (
        CheckConstraint("role IN ('bidder','auctioneer')", name="ck_users_role"),
        CheckConstraint("char_length(display_name) BETWEEN 2 AND 80", name="ck_users_display_name"),
        CheckConstraint("email_normalized = lower(email_normalized)", name="ck_users_email_lower"),
    )


class AccessToken(Base):
    __tablename__ = "access_tokens"

    id: Mapped[int] = mapped_column(BigInteger, Identity(), primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    token_hash: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    issued_at: Mapped[datetime] = mapped_column(TS, server_default=func.now(), nullable=False)
    expires_at: Mapped[datetime] = mapped_column(TS, nullable=False)
    revoked_at: Mapped[datetime] = mapped_column(TS, nullable=True)
    revoked_reason: Mapped[str | None] = mapped_column(String(32), nullable=True)
    last_used_at: Mapped[datetime] = mapped_column(TS, nullable=True)

    __table_args__ = (Index("ix_access_tokens_user_expires", "user_id", "expires_at"),)


class Lot(Base, TimestampMixin):
    __tablename__ = "lots"

    id: Mapped[int] = mapped_column(BigInteger, Identity(), primary_key=True)
    public_id: Mapped[str] = mapped_column(String(40), unique=True, nullable=False)
    number: Mapped[str] = mapped_column(String(8), unique=True, nullable=False)
    auctioneer_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"), nullable=False, index=True
    )

    title: Mapped[str] = mapped_column(String(160), nullable=False)
    artist: Mapped[str] = mapped_column(String(160), nullable=False)
    artwork_date: Mapped[str] = mapped_column(String(120), nullable=False, server_default="")
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    image_url: Mapped[str] = mapped_column(String(1024), nullable=False)
    image_alt: Mapped[str] = mapped_column(String(300), nullable=False, server_default="")
    external_artwork_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    artwork_source: Mapped[str] = mapped_column(
        String(64), nullable=False, server_default="Art Institute of Chicago"
    )
    artwork_snapshot: Mapped[dict] = mapped_column(JSONB, nullable=False, server_default=text("'{}'::jsonb"))

    status: Mapped[str] = mapped_column(String(16), nullable=False, server_default="scheduled")
    starting_bid_cents: Mapped[int] = mapped_column(BigInteger, nullable=False)
    minimum_increment_cents: Mapped[int] = mapped_column(BigInteger, nullable=False)
    current_bid_cents: Mapped[int] = mapped_column(BigInteger, nullable=False, server_default=text("0"))
    bid_count: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("0"))
    leading_bid_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    revision: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("1"))

    starts_at: Mapped[datetime] = mapped_column(TS, nullable=False)
    ends_at: Mapped[datetime] = mapped_column(TS, nullable=False)
    extension_count: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("0"))
    closed_at: Mapped[datetime] = mapped_column(TS, nullable=True)

    winner_bid_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    winner_user_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"), nullable=True
    )
    final_amount_cents: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    revenue_cents: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    commission_bps_applied: Mapped[int | None] = mapped_column(Integer, nullable=True)
    settled_at: Mapped[datetime] = mapped_column(TS, nullable=True)

    cancelled_at: Mapped[datetime] = mapped_column(TS, nullable=True)
    cancellation_reason: Mapped[str | None] = mapped_column(String(280), nullable=True)

    __table_args__ = (
        CheckConstraint("status IN ('scheduled','live','ended','cancelled')", name="ck_lots_status"),
        CheckConstraint("starting_bid_cents > 0", name="ck_lots_starting_positive"),
        CheckConstraint("minimum_increment_cents > 0", name="ck_lots_increment_positive"),
        CheckConstraint("current_bid_cents >= 0", name="ck_lots_current_nonneg"),
        CheckConstraint("bid_count >= 0", name="ck_lots_bid_count_nonneg"),
        CheckConstraint("ends_at > starts_at", name="ck_lots_window"),
        CheckConstraint(
            "current_bid_cents = 0 OR current_bid_cents >= starting_bid_cents",
            name="ck_lots_current_above_start",
        ),
        CheckConstraint(
            "(bid_count = 0 AND leading_bid_id IS NULL) OR (bid_count > 0 AND leading_bid_id IS NOT NULL)",
            name="ck_lots_leading_consistency",
        ),
        Index("ix_lots_status_ends_at", "status", "ends_at"),
        Index("ix_lots_public_feed", "status", "ends_at", "current_bid_cents"),
        Index("ix_lots_title_lower", func.lower(text("title"))),
        Index("ix_lots_artist_lower", func.lower(text("artist"))),
    )


class Bid(Base):
    __tablename__ = "bids"

    id: Mapped[int] = mapped_column(BigInteger, Identity(), primary_key=True)
    public_id: Mapped[str] = mapped_column(String(40), unique=True, nullable=False)
    lot_id: Mapped[int] = mapped_column(
        ForeignKey("lots.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    bidder_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    amount_cents: Mapped[int] = mapped_column(BigInteger, nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False, server_default="leading")
    sequence_in_lot: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[datetime] = mapped_column(TS, server_default=func.now(), nullable=False)
    outbid_at: Mapped[datetime] = mapped_column(TS, nullable=True)

    __table_args__ = (
        CheckConstraint("amount_cents > 0", name="ck_bids_amount_positive"),
        CheckConstraint("status IN ('leading','outbid','won','lost')", name="ck_bids_status"),
        UniqueConstraint("lot_id", "sequence_in_lot", name="uq_bids_lot_sequence"),
        Index("ix_bids_lot_amount", "lot_id", "amount_cents"),
        Index("ix_bids_bidder_created", "bidder_id", "created_at"),
        Index(
            "uq_bids_one_leading_per_lot",
            "lot_id",
            unique=True,
            postgresql_where=text("status = 'leading'"),
        ),
    )


class Wallet(Base, TimestampMixin):
    __tablename__ = "wallets"

    id: Mapped[int] = mapped_column(BigInteger, Identity(), primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"), unique=True, nullable=False
    )
    total_cents: Mapped[int] = mapped_column(BigInteger, nullable=False, server_default=text("0"))
    committed_cents: Mapped[int] = mapped_column(BigInteger, nullable=False, server_default=text("0"))
    version: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("1"))

    user: Mapped[User] = relationship(back_populates="wallet")

    __table_args__ = (
        CheckConstraint("total_cents >= 0", name="ck_wallets_total_nonneg"),
        CheckConstraint("committed_cents >= 0", name="ck_wallets_committed_nonneg"),
        CheckConstraint("committed_cents <= total_cents", name="ck_wallets_committed_le_total"),
    )


class WalletMovement(Base):
    __tablename__ = "wallet_movements"

    id: Mapped[int] = mapped_column(BigInteger, Identity(), primary_key=True)
    public_id: Mapped[str] = mapped_column(String(40), unique=True, nullable=False)
    wallet_id: Mapped[int] = mapped_column(
        ForeignKey("wallets.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    lot_id: Mapped[int | None] = mapped_column(
        ForeignKey("lots.id", ondelete="RESTRICT"), nullable=True
    )
    bid_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    type: Mapped[str] = mapped_column(String(16), nullable=False)
    amount_cents: Mapped[int] = mapped_column(BigInteger, nullable=False)
    committed_delta_cents: Mapped[int] = mapped_column(BigInteger, nullable=False, server_default=text("0"))
    balance_after_cents: Mapped[int] = mapped_column(BigInteger, nullable=False)
    committed_after_cents: Mapped[int] = mapped_column(BigInteger, nullable=False)
    description: Mapped[str] = mapped_column(String(200), nullable=False)
    dedupe_key: Mapped[str | None] = mapped_column(String(120), unique=True, nullable=True)
    created_at: Mapped[datetime] = mapped_column(TS, server_default=func.now(), nullable=False)

    __table_args__ = (
        CheckConstraint("type IN ('deposit','hold','release','settlement')", name="ck_movements_type"),
        CheckConstraint("balance_after_cents >= 0", name="ck_movements_balance_nonneg"),
        CheckConstraint("committed_after_cents >= 0", name="ck_movements_committed_nonneg"),
        CheckConstraint(
            "committed_after_cents <= balance_after_cents", name="ck_movements_committed_le_balance"
        ),
        Index("ix_movements_wallet_created", "wallet_id", "created_at"),
    )


class IdempotencyRecord(Base):
    __tablename__ = "idempotency_records"

    id: Mapped[int] = mapped_column(BigInteger, Identity(), primary_key=True)
    key_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    operation: Mapped[str] = mapped_column(String(64), nullable=False)
    request_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False, server_default="in_progress")
    response_status: Mapped[int | None] = mapped_column(Integer, nullable=True)
    response_body: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    resource_ref: Mapped[str | None] = mapped_column(String(64), nullable=True)
    created_at: Mapped[datetime] = mapped_column(TS, server_default=func.now(), nullable=False)
    completed_at: Mapped[datetime] = mapped_column(TS, nullable=True)
    expires_at: Mapped[datetime] = mapped_column(TS, nullable=False)

    __table_args__ = (
        UniqueConstraint("key_hash", "user_id", "operation", name="uq_idempotency_scope"),
        CheckConstraint(
            "status IN ('in_progress','completed')", name="ck_idempotency_status"
        ),
        Index("ix_idempotency_expires", "expires_at"),
    )


class AuditEvent(Base):
    __tablename__ = "audit_events"

    id: Mapped[int] = mapped_column(BigInteger, Identity(), primary_key=True)
    public_id: Mapped[str] = mapped_column(String(48), unique=True, nullable=False)
    lot_id: Mapped[int | None] = mapped_column(
        ForeignKey("lots.id", ondelete="RESTRICT"), nullable=True, index=True
    )
    sequence: Mapped[int] = mapped_column(Integer, nullable=False)
    type: Mapped[str] = mapped_column(String(48), nullable=False)
    actor_alias: Mapped[str | None] = mapped_column(String(16), nullable=True)
    actor_ref: Mapped[str | None] = mapped_column(String(64), nullable=True)
    amount_cents: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    data: Mapped[dict] = mapped_column(JSONB, nullable=False, server_default=text("'{}'::jsonb"))
    occurred_at: Mapped[datetime] = mapped_column(TS, nullable=False)
    hash: Mapped[str] = mapped_column(String(64), nullable=False)
    previous_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)
    chain_version: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("1"))
    created_at: Mapped[datetime] = mapped_column(TS, server_default=func.now(), nullable=False)

    __table_args__ = (
        UniqueConstraint("lot_id", "sequence", name="uq_audit_lot_sequence"),
        CheckConstraint("sequence > 0", name="ck_audit_sequence_positive"),
        Index("ix_audit_lot_occurred", "lot_id", "occurred_at"),
    )


class AuditCheckpoint(Base):
    __tablename__ = "audit_checkpoints"

    id: Mapped[int] = mapped_column(BigInteger, Identity(), primary_key=True)
    public_id: Mapped[str] = mapped_column(String(48), unique=True, nullable=False)
    key_id: Mapped[str] = mapped_column(String(64), nullable=False)
    lots_covered: Mapped[int] = mapped_column(Integer, nullable=False)
    events_covered: Mapped[int] = mapped_column(Integer, nullable=False)
    heads_digest: Mapped[str] = mapped_column(String(64), nullable=False)
    heads: Mapped[list] = mapped_column(JSONB, nullable=False, server_default=text("'[]'::jsonb"))
    chain_version: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("1"))
    status: Mapped[str] = mapped_column(String(16), nullable=False, server_default="verified")
    signature: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(TS, server_default=func.now(), nullable=False)

    __table_args__ = (
        CheckConstraint("status IN ('verified','failed','unavailable')", name="ck_checkpoint_status"),
        Index("ix_checkpoints_created", "created_at"),
    )


class Receipt(Base):
    __tablename__ = "receipts"

    id: Mapped[int] = mapped_column(BigInteger, Identity(), primary_key=True)
    public_id: Mapped[str] = mapped_column(String(40), unique=True, nullable=False)
    lot_id: Mapped[int] = mapped_column(
        ForeignKey("lots.id", ondelete="RESTRICT"), unique=True, nullable=False
    )
    bid_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    winner_user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    winner_alias: Mapped[str] = mapped_column(String(16), nullable=False)
    final_amount_cents: Mapped[int] = mapped_column(BigInteger, nullable=False)
    commission_cents: Mapped[int] = mapped_column(BigInteger, nullable=False, server_default=text("0"))
    revenue_cents: Mapped[int] = mapped_column(BigInteger, nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False, server_default="BRL")
    closed_at: Mapped[datetime] = mapped_column(TS, nullable=False)
    settled_at: Mapped[datetime] = mapped_column(TS, nullable=False)
    verification_id: Mapped[str] = mapped_column(String(32), nullable=False)
    integrity_status: Mapped[str] = mapped_column(
        String(16), nullable=False, server_default="verified"
    )

    __table_args__ = (
        CheckConstraint("final_amount_cents >= 0", name="ck_receipts_amount_nonneg"),
        CheckConstraint("revenue_cents >= 0", name="ck_receipts_revenue_nonneg"),
    )


class OutboxEvent(Base):
    __tablename__ = "outbox_events"

    id: Mapped[int] = mapped_column(BigInteger, Identity(), primary_key=True)
    event_id: Mapped[str] = mapped_column(String(48), unique=True, nullable=False)
    lot_id: Mapped[int] = mapped_column(
        ForeignKey("lots.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    type: Mapped[str] = mapped_column(String(48), nullable=False)
    sequence: Mapped[int] = mapped_column(Integer, nullable=False)
    payload: Mapped[dict] = mapped_column(JSONB, nullable=False)
    visibility: Mapped[str] = mapped_column(String(16), nullable=False, server_default="public")
    target_user_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(TS, server_default=func.now(), nullable=False)
    published_at: Mapped[datetime] = mapped_column(TS, nullable=True)
    publish_attempts: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("0"))
    last_error: Mapped[str | None] = mapped_column(String(300), nullable=True)

    __table_args__ = (
        CheckConstraint("visibility IN ('public','private')", name="ck_outbox_visibility"),
        UniqueConstraint("lot_id", "event_id", name="uq_outbox_lot_event"),
        Index(
            "ix_outbox_pending",
            "id",
            postgresql_where=text("published_at IS NULL"),
        ),
    )


class LotSequence(Base):

    __tablename__ = "lot_number_sequence"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    next_value: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("1"))

    __table_args__ = (CheckConstraint("id = 1", name="ck_lot_sequence_single_row"),)


class RateLimitCounter(Base):
    __tablename__ = "rate_limit_counter"

    bucket_key: Mapped[str] = mapped_column(String(200), primary_key=True)
    hits: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("1"))
    window_started_at: Mapped[datetime] = mapped_column(TS, server_default=func.now(), nullable=False)
    expires_at: Mapped[datetime] = mapped_column(TS, nullable=False, index=True)


class SettlementLock(Base):

    __tablename__ = "settlement_locks"

    lot_id: Mapped[int] = mapped_column(
        ForeignKey("lots.id", ondelete="RESTRICT"), primary_key=True
    )
    acquired_at: Mapped[datetime] = mapped_column(TS, server_default=func.now(), nullable=False)
    completed_at: Mapped[datetime] = mapped_column(TS, nullable=True)


__all__ = [
    "AccessToken",
    "AuditCheckpoint",
    "AuditEvent",
    "Bid",
    "IdempotencyRecord",
    "Lot",
    "LotSequence",
    "OutboxEvent",
    "RateLimitCounter",
    "Receipt",
    "SettlementLock",
    "User",
    "Wallet",
    "WalletMovement",
]
