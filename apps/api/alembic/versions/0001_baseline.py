"""baseline（空基线）

Revision ID: 0001_baseline
Revises:
Create Date: 2026-11-10

M0 只建立迁移机制本身：执行 `alembic upgrade head` 会创建 alembic_version 表。
真正的业务表从 M1 的 0002 开始，一律 references 此基线。
"""

from __future__ import annotations

from collections.abc import Sequence

revision: str = "0001_baseline"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """基线不建表。"""


def downgrade() -> None:
    """基线下无操作。"""
