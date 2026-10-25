from __future__ import annotations

import logging
import time
import uuid

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.core.errors import AppError, ErrorCode
from app.core.logging import request_id_ctx

logger = logging.getLogger(__name__)

REQUEST_ID_HEADER = "X-Request-Id"
MAX_REQUEST_ID_LENGTH = 64


def _incoming_request_id(request: Request) -> str:
    candidate = request.headers.get("x-request-id") or request.headers.get("x-correlation-id")
    if candidate:
        cleaned = "".join(char for char in candidate if char.isalnum() or char in "-_").strip()
        if 6 <= len(cleaned) <= MAX_REQUEST_ID_LENGTH:
            return cleaned
    return f"req_{uuid.uuid4().hex[:24]}"


def error_response(
    *,
    status_code: int,
    code: str,
    message: str,
    request_id: str,
    field_errors: dict[str, list[str]] | None = None,
    retryable: bool = False,
    headers: dict[str, str] | None = None,
) -> JSONResponse:
    payload: dict[str, object] = {"code": code, "message": message, "requestId": request_id, "retryable": retryable}
    if field_errors:
        payload["fieldErrors"] = field_errors
    response_headers = {"Cache-Control": "no-store", REQUEST_ID_HEADER: request_id}
    if headers:
        response_headers.update(headers)
    return JSONResponse(status_code=status_code, content={"error": payload}, headers=response_headers)


def install_middleware(app: FastAPI) -> None:
    @app.middleware("http")
    async def correlation_and_security(request: Request, call_next):
        request_id = _incoming_request_id(request)
        token = request_id_ctx.set(request_id)
        started = time.perf_counter()
        try:
            response = await call_next(request)
        finally:
            duration_ms = round((time.perf_counter() - started) * 1000, 1)
            logger.info(
                "http_request",
                extra={
                    "extra_fields": {
                        "method": request.method,
                        "path": request.url.path,
                        "durationMs": duration_ms,
                    }
                },
            )
            request_id_ctx.reset(token)
        response.headers[REQUEST_ID_HEADER] = request_id
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["Referrer-Policy"] = "no-referrer"
        response.headers["Cross-Origin-Resource-Policy"] = "same-site"
        if request.url.path.startswith("/v1/"):
            response.headers.setdefault("Cache-Control", "no-store")
        return response

    @app.exception_handler(AppError)
    async def app_error_handler(request: Request, exc: AppError):
        request_id = request_id_ctx.get() or _incoming_request_id(request)
        if exc.status_code >= 500:
            logger.error(
                "application_error",
                extra={"extra_fields": {"code": exc.code, "path": request.url.path}},
            )
        return error_response(
            status_code=exc.status_code,
            code=exc.code,
            message=exc.message,
            request_id=request_id,
            field_errors=exc.field_errors,
            retryable=bool(exc.retryable),
            headers=exc.headers,
        )

    @app.exception_handler(RequestValidationError)
    async def validation_handler(request: Request, exc: RequestValidationError):
        attributes: dict[str, list[str]] = {}
        for error in exc.errors():
            location = [str(part) for part in error.get("loc", []) if part not in ("body", "query", "path")]
            key = ".".join(location) or "body"
            attributes.setdefault(key, []).append(_safe_validation_message(error))
        return error_response(
            status_code=422,
            code=ErrorCode.VALIDATION_ERROR,
            message="Verifique os campos enviados.",
            request_id=request_id_ctx.get() or _incoming_request_id(request),
            field_errors=attributes,
        )

    @app.exception_handler(StarletteHTTPException)
    async def http_exception_handler(request: Request, exc: StarletteHTTPException):
        mapping = {
            400: (ErrorCode.VALIDATION_ERROR, "O pedido está mal formado."),
            401: (ErrorCode.UNAUTHENTICATED, "É necessário autenticação."),
            403: (ErrorCode.FORBIDDEN, "O seu perfil não permite esta operação."),
            404: (ErrorCode.NOT_FOUND, "O recurso não foi encontrado."),
            405: (ErrorCode.VALIDATION_ERROR, "Método não permitido para este recurso."),
            409: (ErrorCode.CONFLICT, "O estado actual não permite esta operação."),
            429: (ErrorCode.RATE_LIMITED, "Demasiados pedidos."),
        }
        code, message = mapping.get(exc.status_code, (ErrorCode.INTERNAL_ERROR, "Não foi possível concluir o pedido."))
        return error_response(
            status_code=exc.status_code,
            code=code,
            message=message,
            request_id=request_id_ctx.get() or _incoming_request_id(request),
            retryable=exc.status_code >= 500,
            headers=getattr(exc, "headers", None),
        )

    @app.exception_handler(Exception)
    async def unhandled_handler(request: Request, exc: Exception): 
        request_id = request_id_ctx.get() or _incoming_request_id(request)
        logger.exception("unhandled_error", extra={"extra_fields": {"path": request.url.path}})
        return error_response(
            status_code=500,
            code=ErrorCode.INTERNAL_ERROR,
            message="Não foi possível concluir o pedido.",
            request_id=request_id,
            retryable=False,
        )


def _safe_validation_message(error: dict) -> str:
    kind = error.get("type", "")
    if kind == "missing":
        return "Campo obrigatório."
    if kind in ("string_too_short", "string_too_long", "too_short", "too_long"):
        return "Comprimento inválido."
    if kind in ("int_parsing", "int_type", "float_parsing", "bool_parsing"):
        return "Tipo inválido."
    if kind == "greater_than":
        return "Valor demasiado baixo."
    if kind == "less_than":
        return "Valor demasiado elevado."
    if kind == "datetime_from_date_parsing" or kind == "datetime_parsing":
        return "Data inválida (use ISO 8601 em UTC)."
    if kind.startswith("literal"):
        return "Valor não permitido."
    if kind == "value_error":
        message = str(error.get("msg", "Valor inválido."))
        return message.replace("Value error, ", "")[:160]
    if kind == "extra_forbidden":
        return "Campo não permitido."
    return "Valor inválido."
