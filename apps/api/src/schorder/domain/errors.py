"""领域异常：带稳定错误码与 HTTP 状态，由 API 层统一映射为响应体。

原则：错误码是契约的一部分，前端按 code 分支，不解析 message。
"""

from __future__ import annotations

from typing import Any


class DomainError(Exception):
    """所有业务错误的基类。"""

    code: str = "DOMAIN_ERROR"
    http_status: int = 400

    def __init__(self, message: str, *, details: dict[str, Any] | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.details: dict[str, Any] = details or {}


class ValidationFailed(DomainError):
    code = "VALIDATION_ERROR"
    http_status = 400


class Unauthenticated(DomainError):
    code = "SESSION_EXPIRED"
    http_status = 401


class Forbidden(DomainError):
    code = "FORBIDDEN"
    http_status = 403


class NotFound(DomainError):
    """资源不存在或无权访问——两者对外不区分，避免探测。"""

    code = "RESOURCE_NOT_FOUND"
    http_status = 404


class Conflict(DomainError):
    code = "CONFLICT"
    http_status = 409


class RateLimited(DomainError):
    code = "RATE_LIMITED"
    http_status = 429


class InternalError(DomainError):
    code = "INTERNAL_ERROR"
    http_status = 500
