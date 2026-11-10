"""API 出入参基类。

三件事一次定好：
1. JSON 用 camelCase，Python 内部用 snake_case —— 只在这一层转换
2. extra="forbid" —— 多传字段直接失败，而不是被静默丢弃（防价格字段注入）
3. populate_by_name=True —— 内部代码仍可用 snake_case 构造
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict


def to_camel(value: str) -> str:
    head, *rest = value.split("_")
    return head + "".join(word[:1].upper() + word[1:] for word in rest)


class ApiModel(BaseModel):
    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
        extra="forbid",
    )
