"""HTTP 中间件：请求标识、体积上限、安全响应头。

顺序很重要（Starlette 后加的先执行）：
    SecurityHeaders  ->  RequestContext  ->  router
先写头再进业务，异常响应也能带上安全头。
"""

from __future__ import annotations

from uuid import uuid4

import structlog
from fastapi import Request, Response
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint

CSP = (
    "default-src 'self'; "
    "script-src 'self'; "
    "style-src 'self' 'unsafe-inline'; "
    "img-src 'self' data: blob:; "
    "font-src 'self'; "
    "connect-src 'self'; "
    "frame-ancestors 'none'; "
    "base-uri 'self'; "
    "form-action 'self'; "
    "object-src 'none'"
)


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    def __init__(self, app: object, *, is_prod: bool = False) -> None:
        super().__init__(app)  # type: ignore[arg-type]
        self.is_prod = is_prod

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        response = await call_next(request)
        headers = response.headers
        headers.setdefault("Content-Security-Policy", CSP)
        headers.setdefault("X-Content-Type-Options", "nosniff")
        headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
        headers.setdefault("X-Frame-Options", "DENY")
        headers.setdefault("Permissions-Policy", "camera=(), microphone=(), geolocation=(self)")
        headers.setdefault("Cross-Origin-Opener-Policy", "same-origin")
        headers.setdefault("Cache-Control", "no-store")
        if self.is_prod:
            headers.setdefault("Strict-Transport-Security", "max-age=31536000; includeSubDomains")
        return response


class RequestContextMiddleware(BaseHTTPMiddleware):
    """注入 request_id、限制请求体大小、回写 X-Request-Id。"""

    def __init__(self, app: object, *, max_body_bytes: int) -> None:
        super().__init__(app)  # type: ignore[arg-type]
        self.max_body_bytes = max_body_bytes

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        request_id = request.headers.get("X-Request-Id") or uuid4().hex
        request.state.request_id = request_id
        structlog.contextvars.bind_contextvars(request_id=request_id)

        try:
            content_length = _content_length(request)
            if content_length is not None and content_length > self.max_body_bytes:
                response: Response = JSONResponse(
                    status_code=413,
                    content={
                        "ok": False,
                        "error": {
                            "code": "PAYLOAD_TOO_LARGE",
                            "message": "请求体超过上限",
                            "details": {"maxBytes": self.max_body_bytes},
                            "traceId": request_id,
                        },
                    },
                )
            else:
                response = await call_next(request)
            response.headers["X-Request-Id"] = request_id
            return response
        finally:
            structlog.contextvars.clear_contextvars()


def _content_length(request: Request) -> int | None:
    raw = request.headers.get("content-length")
    if raw is None:
        return None
    try:
        return int(raw)
    except ValueError:
        return None
