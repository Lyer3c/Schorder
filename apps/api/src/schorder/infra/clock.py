"""时间：全系统一律存 UTC 的 ISO-8601 文本，展示层再转本地时区。

为什么用文本而不是整数时间戳：
- SQLite 里可读，排查时一眼看出时间
- ISO-8601 定长格式可以按字典序比较、排序
- 换 PostgreSQL 时直接映射 timestamptz（迁移成本低）
"""

from __future__ import annotations

from datetime import UTC, datetime


def utc_now() -> datetime:
    return datetime.now(UTC)


def utc_now_iso() -> str:
    """毫秒精度、带 Z 后缀，例如 2026-11-12T05:30:00.123Z。"""
    return utc_now().isoformat(timespec="milliseconds").replace("+00:00", "Z")


def to_iso(value: datetime) -> str:
    return value.astimezone(UTC).isoformat(timespec="milliseconds").replace("+00:00", "Z")


def parse_iso(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(UTC)
