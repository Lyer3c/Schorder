"""测试基础设施：每个用例一个独立的 SQLite 文件，互不污染。"""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient

from schorder.config import Settings
from schorder.db.migrations import ALEMBIC_DIR, API_DIR
from schorder.main import create_app


def make_settings(db_path: Path) -> Settings:
    return Settings(env="test", database_url=f"sqlite:///{db_path.as_posix()}")


@pytest.fixture()
def settings(tmp_path: Path) -> Settings:
    return make_settings(tmp_path / "schorder.db")


@pytest.fixture()
def client(settings: Settings) -> Iterator[TestClient]:
    """未迁移的库：用来验证 /readyz 能发现结构落后。"""
    with TestClient(create_app(settings)) as test_client:
        yield test_client


@pytest.fixture()
def migrated_client(tmp_path: Path) -> Iterator[TestClient]:
    """跑过 alembic upgrade head 的库：用来验证正常路径。"""
    url = f"sqlite:///{(tmp_path / 'migrated.db').as_posix()}"
    config = Config(str(API_DIR / "alembic.ini"))
    config.set_main_option("script_location", str(ALEMBIC_DIR))
    config.set_main_option("sqlalchemy.url", url)
    command.upgrade(config, "head")

    with TestClient(create_app(Settings(env="test", database_url=url))) as test_client:
        yield test_client
