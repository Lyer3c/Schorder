"""迁移版本查询：给 /readyz 用，判断数据库结构是否落后于代码。"""

from __future__ import annotations

from pathlib import Path

from alembic.config import Config
from alembic.script import ScriptDirectory
from sqlalchemy import Connection, text
from sqlalchemy.exc import SQLAlchemyError

API_DIR = Path(__file__).resolve().parents[3]
ALEMBIC_INI = API_DIR / "alembic.ini"
ALEMBIC_DIR = API_DIR / "alembic"


def alembic_config() -> Config:
    config = Config(str(ALEMBIC_INI))
    config.set_main_option("script_location", str(ALEMBIC_DIR))
    return config


def head_revision() -> str | None:
    """代码侧的迁移头版本；没有任何迁移时返回 None。"""
    script = ScriptDirectory.from_config(alembic_config())
    return script.get_current_head()


def current_revision(conn: Connection) -> str | None:
    """数据库侧的当前版本；表还不存在时返回 None（尚未迁移）。"""
    try:
        value = conn.execute(text("SELECT version_num FROM alembic_version")).scalar_one_or_none()
    except SQLAlchemyError:
        return None
    return str(value) if value is not None else None
