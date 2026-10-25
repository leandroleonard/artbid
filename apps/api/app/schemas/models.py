from __future__ import annotations

from datetime import datetime
from typing import Literal, TypeVar

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.core.pagination import Pagination

T = TypeVar("T")

Role = Literal["bidder", "auctioneer"]
LotStatus = Literal["scheduled", "live", "ended"]
PrivateLotStatus = Literal["scheduled", "live", "ended", "cancelled"]


class ApiModel(BaseModel):
    model_config = ConfigDict(populate_by_name=True, extra="forbid")


class ErrorBody(BaseModel):
    code: str
    message: str
    fieldErrors: dict[str, list[str]] | None = None
    requestId: str
    retryable: bool


class ErrorEnvelope(BaseModel):
    error: ErrorBody


class RegisterRequest(ApiModel):
    displayName: str = Field(min_length=2, max_length=80)
    email: str = Field(max_length=254)
    password: str = Field(min_length=8, max_length=128)
    role: Role

    @field_validator("displayName")
    @classmethod
    def _strip_name(cls, value: str) -> str:
        cleaned = value.strip()
        if len(cleaned) < 2:
            raise ValueError("O nome deve ter pelo menos 2 caracteres.")
        return cleaned

    @field_validator("email")
    @classmethod
    def _email(cls, value: str) -> str:
        cleaned = value.strip()
        if "@" not in cleaned or "." not in cleaned.split("@")[-1] or len(cleaned) < 5:
            raise ValueError("Email inválido.")
        return cleaned

    @field_validator("role")
    @classmethod
    def _role(cls, value: str) -> str:
        if value not in ("bidder", "auctioneer"):
            raise ValueError("O papel deve ser bidder ou auctioneer.")
        return value


class LoginRequest(ApiModel):
    email: str = Field(max_length=254)
    password: str = Field(min_length=1, max_length=128)


class ProfileUpdateRequest(ApiModel):
    displayName: str = Field(min_length=2, max_length=80)


class UserOut(BaseModel):
    id: str
    displayName: str
    email: str
    role: Role
    createdAt: str


class AuthOut(BaseModel):
    user: UserOut
    accessToken: str
    expiresAt: str
    demo: bool = False


class LogoutOut(BaseModel):
    revoked: bool


class UserEnvelope(BaseModel):
    data: UserOut


class AuthEnvelope(BaseModel):
    data: AuthOut


class LogoutEnvelope(BaseModel):
    data: LogoutOut


class LotOut(BaseModel):
    id: str
    number: str
    title: str
    artist: str
    artworkDate: str
    description: str | None
    imageUrl: str
    imageAlt: str
    externalArtworkId: str | None
    status: LotStatus
    startingBidCents: int
    currentBidCents: int
    minimumIncrementCents: int
    nextMinimumBidCents: int
    startsAt: str
    endsAt: str
    bidCount: int
    createdAt: str


class PrivateLotOut(LotOut):
    status: PrivateLotStatus 
    cancelledAt: str | None
    cancellationReason: str | None
    finalAmountCents: int | None
    revenueCents: int | None
    winnerAlias: str | None


class LotEnvelope(BaseModel):
    data: LotOut


class PrivateLotEnvelope(BaseModel):
    data: PrivateLotOut


class PageMeta(Pagination):
    pass


class LotPage(BaseModel):
    data: list[LotOut]
    pagination: PageMeta


class PrivateLotPage(BaseModel):
    data: list[PrivateLotOut]
    pagination: PageMeta


class PublicBidOut(BaseModel):
    id: str
    bidderAlias: str
    amountCents: int
    createdAt: str


class ViewerPositionOut(BaseModel):
    status: Literal["none", "leading", "outbid", "won", "lost"]
    highestBidCents: int
    committedCents: int


class RoomOut(BaseModel):
    lot: LotOut
    publicBids: list[PublicBidOut]
    viewerPosition: ViewerPositionOut | None
    serverTime: str


class RoomEnvelope(BaseModel):
    data: RoomOut


class CreateLotRequest(ApiModel):
    artworkId: str = Field(min_length=1, max_length=100)
    title: str = Field(min_length=3, max_length=160)
    description: str | None = Field(default=None, max_length=2000)
    startingBidCents: int = Field(gt=0)
    minimumIncrementCents: int = Field(gt=0)
    startsAt: datetime
    endsAt: datetime

    @field_validator("title")
    @classmethod
    def _title(cls, value: str) -> str:
        cleaned = " ".join(value.split())
        if len(cleaned) < 3:
            raise ValueError("O título deve ter pelo menos 3 caracteres.")
        return cleaned

    @field_validator("description")
    @classmethod
    def _description(cls, value: str | None) -> str | None:
        if value is None:
            return None
        cleaned = value.strip()
        return cleaned or None


class CancelLotRequest(ApiModel):
    confirmation: Literal["CANCELAR"]


class ResultsSummary(BaseModel):
    totalLots: int
    liveLots: int
    endedLots: int
    totalRevenueCents: int
    currency: Literal["BRL"]


class ResultsData(BaseModel):
    summary: ResultsSummary
    lots: list[PrivateLotOut]


class ResultsEnvelope(BaseModel):
    data: ResultsData
    pagination: PageMeta


class WalletOut(BaseModel):
    totalCents: int
    committedCents: int
    availableCents: int
    currency: Literal["BRL"]
    asOf: str


class MovementOut(BaseModel):
    id: str
    type: Literal["deposit", "hold", "release", "settlement"]
    amountCents: int
    description: str
    lotId: str | None
    balanceAfterCents: int
    createdAt: str


class WalletEnvelope(BaseModel):
    data: WalletOut


class DepositRequest(ApiModel):
    amountCents: int = Field(gt=0)


class DepositOut(BaseModel):
    movement: MovementOut
    wallet: WalletOut


class DepositEnvelope(BaseModel):
    data: DepositOut


class MovementPage(BaseModel):
    data: list[MovementOut]
    pagination: PageMeta


class CreateBidRequest(ApiModel):
    lotId: str = Field(min_length=1, max_length=64)
    amountCents: int = Field(gt=0)


class BidOut(BaseModel):
    id: str
    lotId: str
    lotTitle: str
    amountCents: int
    status: Literal["leading", "outbid", "won", "lost"]
    createdAt: str


class BidRoomState(BaseModel):
    currentBidCents: int
    nextMinimumBidCents: int
    endsAt: str
    bidCount: int


class BidAcceptedOut(BaseModel):
    bid: BidOut
    room: BidRoomState
    wallet: WalletOut


class BidAcceptedEnvelope(BaseModel):
    data: BidAcceptedOut


class BidPage(BaseModel):
    data: list[BidOut]
    pagination: PageMeta


class WonLotOut(BaseModel):
    lot: LotOut
    finalAmountCents: int
    settledAt: str
    receiptId: str


class WonPage(BaseModel):
    data: list[WonLotOut]
    pagination: PageMeta


class AuditEventOut(BaseModel):
    id: str
    sequence: int
    type: str
    actorAlias: str | None
    amountCents: int | None
    occurredAt: str
    hash: str
    previousHash: str | None


class IntegrityOut(BaseModel):
    status: Literal["verified", "failed", "unavailable"]
    checkedEventCount: int
    totalEventCount: int
    algorithm: str
    expectedHash: str | None
    calculatedHash: str | None
    verifiedAt: str
    verificationDataUrl: str | None


class AuditData(BaseModel):
    lotId: str
    events: list[AuditEventOut]
    integrity: IntegrityOut


class AuditEnvelope(BaseModel):
    data: AuditData
    pagination: PageMeta


class ReceiptOut(BaseModel):
    id: str
    lotId: str
    lotNumber: str
    title: str
    artist: str
    imageUrl: str
    finalAmountCents: int
    currency: Literal["BRL"]
    winnerAlias: str
    closedAt: str
    settledAt: str
    verificationId: str
    integrityStatus: Literal["verified", "failed", "unavailable"]


class ReceiptEnvelope(BaseModel):
    data: ReceiptOut


class ArtworkOut(BaseModel):
    id: str
    title: str
    artist: str
    date: str
    description: str | None
    imageUrl: str
    imageAlt: str
    source: Literal["Art Institute of Chicago"]


class ArtworkEnvelope(BaseModel):
    data: ArtworkOut


class ArtworkPage(BaseModel):
    data: list[ArtworkOut]
    pagination: PageMeta


__all__ = [name for name in dir() if name.endswith(("Request", "Out", "Envelope", "Page", "Body", "Meta"))] + [
    "Pagination",
]
