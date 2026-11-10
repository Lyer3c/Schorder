"""FastAPI 依赖：按请求提供 Session 与配置。"""

from __future__ import annotations

from collections.abc import Iterator
from typing import Annotated

from fastapi import Depends, Request
from sqlalchemy.orm import Session, sessionmaker

from schorder.config import Settings


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


SessionDep = Annotated[Session, Depends(get_session)]
SettingsDep = Annotated[Settings, Depends(get_settings_dep)]
RequestIdDep = Annotated[str, Depends(get_request_id)]
