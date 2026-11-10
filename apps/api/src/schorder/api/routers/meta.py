"""元信息路由：M0 阶段用它验证「Pydantic → OpenAPI → 前端类型」整条链路。"""

from __future__ import annotations

from datetime import UTC, datetime

from fastapi import APIRouter

from schorder.api.deps import SettingsDep
from schorder.schemas.meta import MetaEnvelope, MetaOut

router = APIRouter(tags=["meta"])


@router.get("/meta", response_model=MetaEnvelope, summary="服务元信息")
def read_meta(settings: SettingsDep) -> MetaEnvelope:
    return MetaEnvelope(
        data=MetaOut(
            name=settings.app_name,
            version=settings.version,
            env=settings.env,
            server_time=datetime.now(UTC),
        )
    )
