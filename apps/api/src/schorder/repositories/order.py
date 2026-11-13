"""订单仓储：写入一律走 CAS，避免并发下状态错乱与超卖。"""

from __future__ import annotations

import json
from typing import Any, cast

from sqlalchemy import CursorResult, select, update
from sqlalchemy.orm import Session

from schorder.db.models import Dish, DishOption, Order, OrderItem, OrderStatusLog, Payment
from schorder.infra.clock import to_iso, utc_now


def get_dish(session: Session, dish_id: str) -> Dish | None:
    return session.get(Dish, dish_id)


def get_dishes(session: Session, dish_ids: list[str]) -> dict[str, Dish]:
    if not dish_ids:
        return {}
    rows = session.scalars(select(Dish).where(Dish.id.in_(dish_ids))).all()
    return {row.id: row for row in rows}


def get_options(session: Session, option_ids: list[str]) -> dict[str, DishOption]:
    if not option_ids:
        return {}
    rows = session.scalars(select(DishOption).where(DishOption.id.in_(option_ids))).all()
    return {row.id: row for row in rows}


def decrement_stock(session: Session, dish_id: str, quantity: int) -> bool:
    """条件扣库存：库存不足时 rowcount 为 0，调用方据此回滚整单。"""
    result = cast(
        "CursorResult[Any]",
        session.execute(
            update(Dish)
            .where(Dish.id == dish_id, Dish.stock >= quantity, Dish.status == "on_sale")
            .values(stock=Dish.stock - quantity, sold_count=Dish.sold_count + quantity)
        ),
    )
    return int(result.rowcount or 0) == 1


def get_by_idempotency_key(session: Session, user_id: str, key: str) -> Order | None:
    return session.scalar(
        select(Order).where(Order.user_id == user_id, Order.idempotency_key == key)
    )


def get_order(session: Session, order_id: str) -> Order | None:
    return session.get(Order, order_id)


def get_order_for_user(session: Session, order_id: str, user_id: str) -> Order | None:
    """带归属条件的读取——越权查询在 SQL 层就返回 None。"""
    return session.scalar(select(Order).where(Order.id == order_id, Order.user_id == user_id))


def insert_order(session: Session, order: Order) -> Order:
    session.add(order)
    session.flush()
    return order


def insert_items(session: Session, items: list[OrderItem]) -> None:
    session.add_all(items)
    session.flush()


def insert_status_log(
    session: Session,
    *,
    order_id: str,
    from_status: str | None,
    to_status: str,
    actor_type: str,
    actor_id: str | None,
    reason: str | None = None,
) -> None:
    session.add(
        OrderStatusLog(
            order_id=order_id,
            from_status=from_status,
            to_status=to_status,
            actor_type=actor_type,
            actor_id=actor_id,
            reason=reason,
        )
    )
    session.flush()


def insert_payment(
    session: Session, *, order_id: str, amount_cents: int, transaction_no: str
) -> Payment:
    now = to_iso(utc_now())
    payment = Payment(
        order_id=order_id,
        provider="mock",
        status="succeeded",
        amount_cents=amount_cents,
        transaction_no=transaction_no,
        paid_at=now,
    )
    session.add(payment)
    session.flush()
    return payment


def cas_status(
    session: Session,
    *,
    order_id: str,
    user_id: str,
    from_status: str,
    to_status: str,
    **fields: Any,
) -> bool:
    """状态迁移的乐观并发控制：只有当前状态仍是 from_status 时才会更新成功。"""
    values: dict[str, Any] = {"status": to_status, "updated_at": to_iso(utc_now())}
    values.update(fields)
    result = cast(
        "CursorResult[Any]",
        session.execute(
            update(Order)
            .where(
                Order.id == order_id,
                Order.user_id == user_id,
                Order.status == from_status,
            )
            .values(**values)
        ),
    )
    return int(result.rowcount or 0) == 1


def list_items(session: Session, order_ids: list[str]) -> dict[str, list[OrderItem]]:
    if not order_ids:
        return {}
    rows = session.scalars(
        select(OrderItem).where(OrderItem.order_id.in_(order_ids)).order_by(OrderItem.id)
    ).all()
    grouped: dict[str, list[OrderItem]] = {order_id: [] for order_id in order_ids}
    for row in rows:
        grouped.setdefault(row.order_id, []).append(row)
    return grouped


def list_orders_for_user(
    session: Session, user_id: str, *, status: str | None, limit: int, offset: int
) -> tuple[list[Order], int]:
    stmt = select(Order).where(Order.user_id == user_id)
    if status:
        stmt = stmt.where(Order.status == status)
    total = len(session.scalars(stmt).all())
    page = session.scalars(
        stmt.order_by(Order.created_at.desc(), Order.id).limit(limit).offset(offset)
    ).all()
    return list(page), total


def options_json(options: list[dict[str, Any]]) -> str:
    return json.dumps(options, ensure_ascii=False)
