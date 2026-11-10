"""运维探针：存活用 /healthz，可用用 /readyz。

两者不进 OpenAPI（include_in_schema=False），它们不属于业务契约。
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Response, status
from sqlalchemy import text

from schorder.api.deps import SessionDep
from schorder.db.migrations import current_revision, head_revision

router = APIRouter(tags=["ops"])


@router.get("/healthz", include_in_schema=False)
def healthz() -> dict[str, str]:
    """进程存活。不碰数据库——数据库挂了不代表该重启进程。"""
    return {"status": "ok"}


@router.get("/readyz", include_in_schema=False)
def readyz(response: Response, session: SessionDep) -> dict[str, Any]:
    """能否对外提供服务：数据库可连 + 结构版本与代码一致。"""
    session.execute(text("SELECT 1"))

    current = current_revision(session.connection())
    head = head_revision()
    ready = current == head

    if not ready:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE

    return {
        "status": "ready" if ready else "schema_outdated",
        "schema": {"current": current, "head": head},
    }
