"""统一错误出口。

所有错误（领域错误、校验错误、HTTP 错误、未捕获异常）都收敛成同一个响应体：

    {"ok": false, "error": {"code", "message", "details", "traceId"}}

关键约定：Pydantic 校验失败默认是 422，本项目映射为 400 VALIDATION_ERROR，
与接口契约保持一致；前端只需要处理一种校验失败形态。
"""

from __future__ import annotations

from typing import Any

import structlog
from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from schorder.domain.errors import DomainError

logger = structlog.get_logger(__name__)


def _trace_id(request: Request) -> str | None:
    value = getattr(request.state, "request_id", None)
    return str(value) if value is not None else None


def _error_response(
    request: Request,
    *,
    status_code: int,
    code: str,
    message: str,
    details: dict[str, Any] | None = None,
) -> JSONResponse:
    return JSONResponse(
        status_code=status_code,
        content={
            "ok": False,
            "error": {
                "code": code,
                "message": message,
                "details": details or {},
                "traceId": _trace_id(request),
            },
        },
    )


def _validation_details(exc: RequestValidationError) -> dict[str, Any]:
    fields = [
        {
            "field": ".".join(str(part) for part in error.get("loc", ()) if part != "body"),
            "message": str(error.get("msg", "invalid")),
            "type": str(error.get("type", "value_error")),
        }
        for error in exc.errors()
    ]
    return {"fields": fields}


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(DomainError)
    async def _handle_domain(request: Request, exc: Exception) -> JSONResponse:
        assert isinstance(exc, DomainError)
        return _error_response(
            request,
            status_code=exc.http_status,
            code=exc.code,
            message=exc.message,
            details=exc.details,
        )

    @app.exception_handler(RequestValidationError)
    async def _handle_validation(request: Request, exc: Exception) -> JSONResponse:
        assert isinstance(exc, RequestValidationError)
        return _error_response(
            request,
            status_code=400,
            code="VALIDATION_ERROR",
            message="请求参数不合法",
            details=_validation_details(exc),
        )

    @app.exception_handler(StarletteHTTPException)
    async def _handle_http(request: Request, exc: Exception) -> JSONResponse:
        assert isinstance(exc, StarletteHTTPException)
        code_by_status = {
            401: "SESSION_EXPIRED",
            403: "FORBIDDEN",
            404: "RESOURCE_NOT_FOUND",
            405: "METHOD_NOT_ALLOWED",
            413: "PAYLOAD_TOO_LARGE",
            429: "RATE_LIMITED",
        }
        return _error_response(
            request,
            status_code=exc.status_code,
            code=code_by_status.get(exc.status_code, "HTTP_ERROR"),
            message=str(exc.detail) if exc.detail else "请求失败",
        )

    @app.exception_handler(Exception)
    async def _handle_unexpected(request: Request, exc: Exception) -> JSONResponse:
        logger.exception(
            "unhandled_exception",
            request_id=_trace_id(request),
            path=request.url.path,
            error_type=type(exc).__name__,
        )
        return _error_response(
            request,
            status_code=500,
            code="INTERNAL_ERROR",
            message="服务内部错误",
        )
