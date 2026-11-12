"""目录路由：分类、档口列表、档口详情、搜索。

参数命名用 camelCase（与前端/契约一致），所以显式写了 alias。
"""

from __future__ import annotations

from typing import Annotated, Literal

from fastapi import APIRouter, Query

from schorder.api.deps import SessionDep
from schorder.schemas.catalog import (
    CategoryListOut,
    PageMeta,
    SearchEnvelope,
    StallDetailEnvelope,
    StallListOut,
)
from schorder.services import catalog as catalog_service

router = APIRouter(tags=["catalog"])


@router.get("/categories", response_model=CategoryListOut, summary="档口分类")
def list_categories(session: SessionDep) -> CategoryListOut:
    return CategoryListOut(data=catalog_service.list_categories(session))


@router.get("/stalls", response_model=StallListOut, summary="档口列表")
def list_stalls(
    session: SessionDep,
    category_id: Annotated[str | None, Query(alias="categoryId", max_length=36)] = None,
    keyword: Annotated[str | None, Query(max_length=50)] = None,
    sort: Annotated[
        Literal["recommended", "sales", "rating", "min_order"], Query()
    ] = "recommended",
    open_now: Annotated[bool, Query(alias="openNow")] = False,
    limit: Annotated[int, Query(ge=1, le=50)] = 20,
    cursor: Annotated[str | None, Query(max_length=200)] = None,
) -> StallListOut:
    items, total, next_cursor = catalog_service.list_stalls(
        session,
        category_id=category_id,
        keyword=keyword,
        sort=sort,
        open_now=open_now,
        limit=limit,
        cursor=cursor,
    )
    return StallListOut(data=items, meta=PageMeta(next_cursor=next_cursor, total=total))


@router.get("/stalls/{stall_id}", response_model=StallDetailEnvelope, summary="档口详情")
def get_stall(stall_id: str, session: SessionDep) -> StallDetailEnvelope:
    return StallDetailEnvelope(data=catalog_service.get_stall_detail(session, stall_id))


@router.get("/search", response_model=SearchEnvelope, summary="搜索档口与菜品")
def search(
    session: SessionDep,
    q: Annotated[str, Query(min_length=1, max_length=30)],
    limit: Annotated[int, Query(ge=1, le=20)] = 10,
) -> SearchEnvelope:
    return SearchEnvelope(data=catalog_service.search(session, q, limit))
