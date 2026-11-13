"""订单路由：试算、下单、支付、查询。

写操作都挂 require_csrf——下单和支付是这套系统里最需要防 CSRF 的两个动作。
"""

from __future__ import annotations

from typing import Annotated, Literal

from fastapi import APIRouter, Depends, Query

from schorder.api.deps import CurrentAuth, SessionDep, require_csrf
from schorder.schemas.catalog import PageMeta
from schorder.schemas.order import (
    CreateOrderIn,
    OrderEnvelope,
    OrderListOut,
    PreviewEnvelope,
    PreviewOrderIn,
)
from schorder.services import order as order_service
from schorder.services.catalog import decode_cursor, encode_cursor

router = APIRouter(prefix="/orders", tags=["orders"])


@router.post(
    "/preview",
    response_model=PreviewEnvelope,
    dependencies=[Depends(require_csrf)],
    summary="下单前试算",
)
def preview(payload: PreviewOrderIn, auth: CurrentAuth, session: SessionDep) -> PreviewEnvelope:
    return PreviewEnvelope(data=order_service.preview(session, payload))


@router.post(
    "",
    response_model=OrderEnvelope,
    status_code=201,
    dependencies=[Depends(require_csrf)],
    summary="创建订单",
)
def create_order(payload: CreateOrderIn, auth: CurrentAuth, session: SessionDep) -> OrderEnvelope:
    result = order_service.create(session, auth.user.id, payload)
    session.commit()
    return OrderEnvelope(data=result)


@router.post(
    "/{order_id}/pay",
    response_model=OrderEnvelope,
    dependencies=[Depends(require_csrf)],
    summary="模拟支付",
)
def pay_order(order_id: str, auth: CurrentAuth, session: SessionDep) -> OrderEnvelope:
    result = order_service.pay(session, auth.user.id, order_id)
    session.commit()
    return OrderEnvelope(data=result)


@router.get("", response_model=OrderListOut, summary="我的订单")
def list_orders(
    auth: CurrentAuth,
    session: SessionDep,
    status: Annotated[
        Literal[
            "pending_payment",
            "paid",
            "accepted",
            "preparing",
            "ready",
            "delivering",
            "completed",
            "cancelled",
        ]
        | None,
        Query(),
    ] = None,
    limit: Annotated[int, Query(ge=1, le=50)] = 20,
    cursor: Annotated[str | None, Query(max_length=200)] = None,
) -> OrderListOut:
    offset = decode_cursor(cursor)
    items, total = order_service.list_orders(
        session, auth.user.id, status=status, limit=limit, offset=offset
    )
    next_offset = offset + limit
    return OrderListOut(
        data=items,
        meta=PageMeta(
            next_cursor=encode_cursor(next_offset) if next_offset < total else None,
            total=total,
        ),
    )


@router.get("/{order_id}", response_model=OrderEnvelope, summary="订单详情")
def get_order(order_id: str, auth: CurrentAuth, session: SessionDep) -> OrderEnvelope:
    return OrderEnvelope(data=order_service.get_order(session, auth.user.id, order_id))
