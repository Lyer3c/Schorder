"""Alembic 运行环境。

要点：
- 连接串优先取 alembic 命令传入的 sqlalchemy.url（测试里用它指向临时库）
- 找不到时回落到 Settings()，与运行时完全一致，避免"迁移连 A 库、应用连 B 库"
- render_as_batch=True：SQLite 不支持大多数 ALTER，批处理模式会重建表
"""

from __future__ import annotations

import sys
from logging.config import fileConfig
from pathlib import Path

from alembic import context
from sqlalchemy import engine_from_config, pool

API_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(API_DIR / "src"))

import schorder.db.models  # noqa: E402,F401  - 必须导入，否则 autogenerate 看不到表
from schorder.config import Settings  # noqa: E402
from schorder.db.base import Base  # noqa: E402
from schorder.db.engine import ensure_sqlite_parent_dir  # noqa: E402

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata

_PLACEHOLDER_URL = "driver://user:pass@localhost/dbname"


def database_url() -> str:
    configured = config.get_main_option("sqlalchemy.url")
    if configured and configured != _PLACEHOLDER_URL:
        return str(configured)
    return Settings().database_url


def run_migrations_offline() -> None:
    context.configure(
        url=database_url(),
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        render_as_batch=True,
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    url = database_url()
    ensure_sqlite_parent_dir(url)

    section = config.get_section(config.config_ini_section, {}) or {}
    section["sqlalchemy.url"] = url

    connectable = engine_from_config(section, prefix="sqlalchemy.", poolclass=pool.NullPool)

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            render_as_batch=True,
            compare_type=True,
        )
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
