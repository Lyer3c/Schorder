"""数据库引擎构造：SQLite 的连接参数与 PRAGMA 在这里集中设置。

SQLite 的关键设置：
- journal_mode=WAL     读写不互斥，桌面/小规模场景吞吐明显更好
- foreign_keys=ON      SQLite 默认不开外键，必须每个连接显式打开
- busy_timeout=5000    遇到写锁时等待而不是立刻报 database is locked
- synchronous=NORMAL   WAL 下的安全/性能平衡点
"""

from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Any

from sqlalchemy import Engine, create_engine, event

SQLITE_PRAGMAS: tuple[str, ...] = (
    "PRAGMA journal_mode=WAL",
    "PRAGMA foreign_keys=ON",
    "PRAGMA busy_timeout=5000",
    "PRAGMA synchronous=NORMAL",
)


def create_db_engine(database_url: str) -> Engine:
    is_sqlite = database_url.startswith("sqlite")

    if is_sqlite:
        ensure_sqlite_parent_dir(database_url)

    connect_args: dict[str, Any] = {}
    if is_sqlite:
        # FastAPI 的同步依赖跑在线程池里，连接会跨线程使用
        connect_args = {"check_same_thread": False, "timeout": 5.0}

    engine = create_engine(database_url, connect_args=connect_args, pool_pre_ping=True)

    if is_sqlite:

        @event.listens_for(engine, "connect")
        def _set_sqlite_pragmas(dbapi_connection: sqlite3.Connection, _record: object) -> None:
            cursor = dbapi_connection.cursor()
            try:
                for pragma in SQLITE_PRAGMAS:
                    cursor.execute(pragma)
            finally:
                cursor.close()

    return engine


def ensure_sqlite_parent_dir(database_url: str) -> None:
    """SQLite 不会自动创建目录，这里补上，避免首次启动报 unable to open database file。"""
    prefix = "sqlite:///"
    if not database_url.startswith(prefix):
        return
    raw = database_url[len(prefix) :]
    if raw in {"", ":memory:"}:
        return
    Path(raw).expanduser().resolve().parent.mkdir(parents=True, exist_ok=True)
