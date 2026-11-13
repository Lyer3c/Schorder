"""认证路由：注册、登录、会话、登出、改密。

Cookie 的三条约束写在这里：HttpOnly（JS 读不到）、SameSite=Lax、路径为 /。
生产环境用 ``__Host-`` 前缀 + Secure，具体值由配置决定。
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, Request, Response

from schorder.api.deps import (
    ClientIpDep,
    CurrentAuth,
    SessionDep,
    SettingsDep,
    UserAgentDep,
    require_csrf,
)
from schorder.config import Settings
from schorder.db.models import User
from schorder.schemas.auth import (
    ChangePasswordIn,
    LoginIn,
    OkData,
    OkEnvelope,
    RegisterIn,
    SessionDataOut,
    SessionEnvelope,
    UserOut,
)
from schorder.services import auth as auth_service

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=SessionEnvelope, status_code=201, summary="注册")
def register(
    payload: RegisterIn,
    response: Response,
    session: SessionDep,
    settings: SettingsDep,
    ip: ClientIpDep,
    user_agent: UserAgentDep,
) -> SessionEnvelope:
    issued = auth_service.register(
        session,
        settings,
        phone=payload.phone,
        password=payload.password,
        nickname=payload.nickname,
        ip=ip,
        user_agent=user_agent,
    )
    session.commit()
    _set_cookie(response, settings, issued)
    return SessionEnvelope(data=_to_data(issued.user, issued.csrf_token))


@router.post("/login", response_model=SessionEnvelope, summary="登录")
def login(
    payload: LoginIn,
    request: Request,
    response: Response,
    session: SessionDep,
    settings: SettingsDep,
    ip: ClientIpDep,
    user_agent: UserAgentDep,
) -> SessionEnvelope:
    issued = auth_service.login(
        session,
        settings,
        phone=payload.phone,
        password=payload.password,
        ip=ip,
        user_agent=user_agent,
        current_token=request.cookies.get(settings.cookie_name),
    )
    session.commit()
    _set_cookie(response, settings, issued)
    return SessionEnvelope(data=_to_data(issued.user, issued.csrf_token))


@router.get("/session", response_model=SessionEnvelope, summary="当前会话")
def read_session(auth: CurrentAuth, session: SessionDep) -> SessionEnvelope:
    # authenticate 可能做了滑动续期，这里提交一次
    session.commit()
    return SessionEnvelope(data=_to_data(auth.user, auth.session_row.csrf_token))


@router.post(
    "/logout",
    response_model=OkEnvelope,
    dependencies=[Depends(require_csrf)],
    summary="登出",
)
def logout(
    auth: CurrentAuth, response: Response, session: SessionDep, settings: SettingsDep
) -> OkEnvelope:
    auth_service.logout(session, auth.session_row)
    session.commit()
    _clear_cookie(response, settings)
    return OkEnvelope(data=OkData())


@router.post(
    "/password",
    response_model=OkEnvelope,
    dependencies=[Depends(require_csrf)],
    summary="修改密码",
)
def change_password(
    payload: ChangePasswordIn,
    auth: CurrentAuth,
    response: Response,
    session: SessionDep,
    settings: SettingsDep,
) -> OkEnvelope:
    auth_service.change_password(
        session,
        auth.user,
        old_password=payload.old_password,
        new_password=payload.new_password,
    )
    session.commit()
    # 改密后所有会话失效，当前 Cookie 一起清掉
    _clear_cookie(response, settings)
    return OkEnvelope(data=OkData())


def _to_data(user: User, csrf_token: str) -> SessionDataOut:
    return SessionDataOut(
        user=UserOut(
            id=user.id,
            phone=user.phone,
            nickname=user.nickname,
            role=user.role,
            avatar_url=user.avatar_url,
        ),
        csrf_token=csrf_token,
    )


def _set_cookie(response: Response, settings: Settings, issued: auth_service.IssuedSession) -> None:
    response.set_cookie(
        key=settings.cookie_name,
        value=issued.raw_token,
        max_age=issued.cookie_max_age,
        httponly=True,
        secure=settings.cookie_secure,
        samesite="lax",
        path="/",
    )


def _clear_cookie(response: Response, settings: Settings) -> None:
    response.delete_cookie(
        key=settings.cookie_name,
        path="/",
        httponly=True,
        secure=settings.cookie_secure,
        samesite="lax",
    )
