from __future__ import annotations

from typing import Any


class ErrorCode:
    VALIDATION_ERROR = "VALIDATION_ERROR"
    UNAUTHENTICATED = "UNAUTHENTICATED"
    TOKEN_EXPIRED = "TOKEN_EXPIRED"
    FORBIDDEN = "FORBIDDEN"
    NOT_FOUND = "NOT_FOUND"
    CONFLICT = "CONFLICT"
    BID_TOO_LOW = "BID_TOO_LOW"
    INSUFFICIENT_AVAILABLE_BALANCE = "INSUFFICIENT_AVAILABLE_BALANCE"
    LOT_NOT_OPEN = "LOT_NOT_OPEN"
    LOT_ENDED = "LOT_ENDED"
    LOT_CANCELLED = "LOT_CANCELLED"
    BIDDER_ALREADY_LEADING = "BIDDER_ALREADY_LEADING"
    AUCTIONEER_CANNOT_BID = "AUCTIONEER_CANNOT_BID"
    LOT_HAS_BIDS = "LOT_HAS_BIDS"
    CANCELLATION_NOT_ALLOWED = "CANCELLATION_NOT_ALLOWED"
    IDEMPOTENCY_CONFLICT = "IDEMPOTENCY_CONFLICT"
    IDEMPOTENCY_IN_PROGRESS = "IDEMPOTENCY_IN_PROGRESS"
    RATE_LIMITED = "RATE_LIMITED"
    UPSTREAM_TIMEOUT = "UPSTREAM_TIMEOUT"
    UPSTREAM_INVALID_RESPONSE = "UPSTREAM_INVALID_RESPONSE"
    UPSTREAM_UNAVAILABLE = "UPSTREAM_UNAVAILABLE"
    BACKEND_NOT_INTEGRATED = "BACKEND_NOT_INTEGRATED"
    INTERNAL_ERROR = "INTERNAL_ERROR"


RETRYABLE_CODES = {
    ErrorCode.RATE_LIMITED,
    ErrorCode.UPSTREAM_TIMEOUT,
    ErrorCode.UPSTREAM_UNAVAILABLE,
    ErrorCode.IDEMPOTENCY_IN_PROGRESS,
}

DEFAULT_MESSAGES = {
    ErrorCode.VALIDATION_ERROR: "Verifique os dados enviados.",
    ErrorCode.UNAUTHENTICATED: "É necessário autenticação para esta operação.",
    ErrorCode.TOKEN_EXPIRED: "A sessão expirou. Inicie sessão novamente.",
    ErrorCode.FORBIDDEN: "O seu perfil não permite esta operação.",
    ErrorCode.NOT_FOUND: "O recurso não foi encontrado.",
    ErrorCode.CONFLICT: "O estado actual do recurso não permite esta operação.",
    ErrorCode.BID_TOO_LOW: "O valor do lance é inferior ao mínimo permitido.",
    ErrorCode.INSUFFICIENT_AVAILABLE_BALANCE: "O saldo disponível é insuficiente para este lance.",
    ErrorCode.LOT_NOT_OPEN: "O lote não está aberto a lances.",
    ErrorCode.LOT_ENDED: "O prazo do lote terminou.",
    ErrorCode.LOT_CANCELLED: "O lote foi cancelado.",
    ErrorCode.BIDDER_ALREADY_LEADING: "Já lidera este lote com um lance igual ou superior.",
    ErrorCode.AUCTIONEER_CANNOT_BID: "Um leiloeiro não pode licitar.",
    ErrorCode.LOT_HAS_BIDS: "O lote já tem lances e não pode ser cancelado.",
    ErrorCode.CANCELLATION_NOT_ALLOWED: "O cancelamento não é permitido neste estado.",
    ErrorCode.IDEMPOTENCY_CONFLICT: "A chave de idempotência já foi usada com um pedido diferente.",
    ErrorCode.IDEMPOTENCY_IN_PROGRESS: "O pedido com esta chave está em processamento.",
    ErrorCode.RATE_LIMITED: "Demasiados pedidos. Tente novamente mais tarde.",
    ErrorCode.UPSTREAM_TIMEOUT: "O serviço não respondeu a tempo.",
    ErrorCode.UPSTREAM_INVALID_RESPONSE: "O serviço devolveu uma resposta inválida.",
    ErrorCode.UPSTREAM_UNAVAILABLE: "O serviço está indisponível.",
    ErrorCode.BACKEND_NOT_INTEGRATED: "Funcionalidade indisponível",
    ErrorCode.INTERNAL_ERROR: "Não foi possível concluir o pedido.",
}


class AppError(Exception):

    def __init__(
        self,
        status_code: int,
        code: str,
        message: str | None = None,
        *,
        field_errors: dict[str, list[str]] | None = None,
        retryable: bool | None = None,
        headers: dict[str, str] | None = None,
        extra: dict[str, Any] | None = None,
    ) -> None:
        self.status_code = status_code
        self.code = code
        self.message = message or DEFAULT_MESSAGES.get(code, "Não foi possível concluir o pedido.")
        self.field_errors = field_errors or None
        self.retryable = RETRYABLE_CODES.__contains__(code) if retryable is None else retryable
        self.headers = headers or {}
        self.extra = extra or {}
        super().__init__(self.message)


def unauthenticated(message: str | None = None) -> AppError:
    return AppError(401, ErrorCode.UNAUTHENTICATED, message)


def token_expired() -> AppError:
    return AppError(401, ErrorCode.TOKEN_EXPIRED)


def forbidden(message: str | None = None) -> AppError:
    return AppError(403, ErrorCode.FORBIDDEN, message)


def not_found(message: str | None = None) -> AppError:
    return AppError(404, ErrorCode.NOT_FOUND, message)


def validation(message: str | None = None, field_errors: dict[str, list[str]] | None = None) -> AppError:
    return AppError(422, ErrorCode.VALIDATION_ERROR, message, field_errors=field_errors)


def conflict(code: str = ErrorCode.CONFLICT, message: str | None = None) -> AppError:
    return AppError(409, code, message)


def rate_limited(retry_after: int) -> AppError:
    return AppError(
        429,
        ErrorCode.RATE_LIMITED,
        f"Demasiados pedidos. Tente novamente em {retry_after}s.",
        retryable=True,
        headers={"Retry-After": str(retry_after)},
    )
