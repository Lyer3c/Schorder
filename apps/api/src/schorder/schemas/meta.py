"""服务元信息：前端启动时用它确认代理链路与后端版本。"""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from schorder.schemas.common import ApiModel


class MetaOut(ApiModel):
    name: str
    version: str
    env: str
    server_time: datetime


class MetaEnvelope(ApiModel):
    ok: Literal[True] = True
    data: MetaOut
