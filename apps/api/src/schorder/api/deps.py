"""FastAPI 依赖：按请求提供 Session、配置、当前用户与 CSRF 校验。"""

from __future__ import annotations

import hmac
from collections.abc import Iterator
from dataclasses import dataclass
from typing import Annotated

from fastapi import Depends, Request
from sqlalchemy.orm import Session, sessionmaker

from schorder.config import Settings
from schorder.db.models import User, UserSession
from schorder.domain.errors import Forbidden
from schorder.services import auth as auth_service


def get_session(request: Request) -> Iterator[Session]:
    factory: sessionmaker[Session] = request.app.state.sessionmaker
    session = factory()
    try:
        yield session
    finally:
        session.close()


def get_settings_dep(request: Request) -> Settings:
    settings: Settings = request.app.state.settings
    return settings


def get_request_id(request: Request) -> str:
    return str(getattr(request.state, "request_id", "unknown"))


def get_client_ip(request: Request) -> str | None:
    """直连地址。不信任 X-Forwarded-For，除非部署时显式配置代理层。"""
    return request.client.host if request.client else None


def get_user_agent(request: Request) -> str | None:
    return request.headers.get("user-agent")


SessionDep = Annotated[Session, Depends(get_session)]
SettingsDep = Annotated[Settings, Depends(get_settings_dep)]
RequestIdDep = Annotated[str, Depends(get_request_id)]
ClientIpDep = Annotated[str | None, Depends(get_client_ip)]
UserAgentDep = Annotated[str | None, Depends(get_user_agent)]


@dataclass(frozen=True)
class AuthContext:
    """一次已认证请求的最小上下文。"""

    user: User
    session_row: UserSession


def get_current_auth(request: Request, session: SessionDep, settings: SettingsDep) -> AuthContext:
    token = request.cookies.get(settings.cookie_name)
    user, row = auth_service.authenticate(session, settings, token)
    return AuthContext(user=user, session_row=row)


CurrentAuth = Annotated[AuthContext, Depends(get_current_auth)]


def require_csrf(request: Request, auth: CurrentAuth) -> None:
    """所有写操作的第二道闸：请求头里的令牌必须与会话里的一致。"""
    provided = request.headers.get("X-CSRF-Token")
    if not provided or not hmac.compare_digest(provided, auth.session_row.csrf_token):
        raise Forbidden("CSRF 令牌缺失或不匹配")


def require_role(*roles: str) -> object:
    """路由级角色守卫：`dependencies=[Depends(require_role('admin'))]`。"""

    def _guard(auth: CurrentAuth) -> AuthContext:
        if auth.user.role not in roles:
            # 越权一律 404，不暴露资源是否存在
            from schorder.domain.errors import NotFound

            raise NotFound("资源不存在")
        return auth

    return Depends(_guard)
