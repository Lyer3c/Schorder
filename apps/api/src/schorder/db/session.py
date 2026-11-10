"""会话工厂。

约定：
- autoflush=False —— 显式 flush，避免查询时被动写入
- expire_on_commit=False —— 提交后仍可读对象属性，省掉重复查询
- 事务边界由 Service 层的 ``with session.begin():`` 控制，这里不自动提交
"""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager

from sqlalchemy import Engine
from sqlalchemy.orm import Session, sessionmaker


def create_session_factory(engine: Engine) -> sessionmaker[Session]:
    return sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


@contextmanager
def session_scope(factory: sessionmaker[Session]) -> Iterator[Session]:
    session = factory()
    try:
        yield session
    finally:
        session.close()
