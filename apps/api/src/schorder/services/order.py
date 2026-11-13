"""订单服务：定价、建单、支付。

三条硬规则：
1. 金额一律服务端算，请求里没有任何价格字段（DTO 用 extra="forbid" 兜底）
2. 库存用条件更新扣减，扣不动就整单回滚
3. 状态迁移用 CAS，rowcount 为 0 说明状态已被别人改过 → 409
"""

from __future__ import annotations

import json
import secrets
from dataclasses import dataclass
from datetime import datetime, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from schorder.db.models import (
    Address,
    Dish,
    DishOption,
    DishOptionGroup,
    Order,
    OrderItem,
    Stall,
)
from schorder.domain.business_hours import is_open, now_cn
from schorder.domain.errors import Conflict, NotFound, ValidationFailed
from schorder.infra.clock import parse_iso, to_iso, utc_now
from schorder.infra.ids import uuid7
from schorder.repositories import catalog as catalog_repo
from schorder.repositories import order as order_repo
from schorder.schemas.order import (
    AmountOut,
    CreateOrderIn,
    OrderItemOut,
    OrderOptionOut,
    OrderOut,
    PreviewOrderIn,
    PreviewOut,
)

ORDER_TTL_MINUTES = 15


@dataclass
class _PricedItem:
    dish: Dish
    options: list[DishOption]
    quantity: int
    unit_price_cents: int
    line_amount_cents: int


def preview(session: Session, payload: PreviewOrderIn) -> PreviewOut:
    stall = _get_active_stall(session, payload.stall_id)
    items, amount = _price(session, stall, payload)
    min_order_ok = amount.items_amount_cents >= stall.min_order_cents

    warnings: list[str] = []
    if not min_order_ok and payload.fulfillment_type == "delivery":
        warnings.append(f"还差 {stall.min_order_cents - amount.items_amount_cents} 分起送")

    return PreviewOut(
        stall_id=stall.id,
        stall_name=stall.name,
        fulfillment_type=payload.fulfillment_type,
        items=[_item_out(item) for item in items],
        amount=amount,
        min_order_ok=min_order_ok,
        min_order_cents=stall.min_order_cents,
        estimated_minutes=_estimated_minutes(stall),
        warnings=warnings,
    )


def create(session: Session, user_id: str, payload: CreateOrderIn) -> OrderOut:
    existing = order_repo.get_by_idempotency_key(session, user_id, payload.idempotency_key)
    if existing is not None:
        # 幂等：同一个 key 重复提交，直接返回第一次的结果
        return _to_order_out(session, existing)

    stall = _get_active_stall(session, payload.stall_id)
    items, amount = _price(session, stall, payload)

    if payload.fulfillment_type == "delivery" and amount.items_amount_cents < stall.min_order_cents:
        raise ValidationFailed("未达到起送金额", details={"minOrderCents": stall.min_order_cents})

    address_snapshot_json = None
    if payload.fulfillment_type == "delivery":
        address_snapshot_json = _address_snapshot(session, user_id, payload.address_id)

    # 先扣库存：任何一项扣不动都抛错，事务回滚，不会出现"扣了一半"
    for item in items:
        if not order_repo.decrement_stock(session, item.dish.id, item.quantity):
            raise Conflict(f"「{item.dish.name}」库存不足", details={"dishId": item.dish.id})

    now = utc_now()
    order = Order(
        id=uuid7(),
        order_no=_order_no(now_cn()),
        user_id=user_id,
        stall_id=stall.id,
        status="pending_payment",
        fulfillment_type=payload.fulfillment_type,
        address_snapshot_json=address_snapshot_json,
        contact_name=payload.contact_name,
        contact_phone=payload.contact_phone,
        tableware_count=payload.tableware_count,
        remark=payload.remark,
        items_amount_cents=amount.items_amount_cents,
        packing_fee_cents=amount.packing_fee_cents,
        delivery_fee_cents=amount.delivery_fee_cents,
        discount_cents=amount.discount_cents,
        payable_cents=amount.payable_cents,
        idempotency_key=payload.idempotency_key,
        expires_at=to_iso(now + timedelta(minutes=ORDER_TTL_MINUTES)),
    )
    order_repo.insert_order(session, order)

    order_repo.insert_items(
        session,
        [_order_item_row(order.id, item) for item in items],
    )
    order_repo.insert_status_log(
        session,
        order_id=order.id,
        from_status=None,
        to_status="pending_payment",
        actor_type="student",
        actor_id=user_id,
    )
    session.flush()
    return _to_order_out(session, order)


def pay(session: Session, user_id: str, order_id: str) -> OrderOut:
    order = order_repo.get_order_for_user(session, order_id, user_id)
    if order is None:
        raise NotFound("订单不存在")

    now = utc_now()
    transaction_no = "MOCK" + secrets.token_hex(8).upper()

    # CAS：只有仍是待支付且未过期才改得动
    updated = order_repo.cas_status(
        session,
        order_id=order.id,
        user_id=user_id,
        from_status="pending_payment",
        to_status="paid",
        paid_at=to_iso(now),
    )
    if not updated:
        raise Conflict("订单当前状态不可支付")

    order_repo.insert_payment(
        session, order_id=order.id, amount_cents=order.payable_cents, transaction_no=transaction_no
    )
    order_repo.insert_status_log(
        session,
        order_id=order.id,
        from_status="pending_payment",
        to_status="paid",
        actor_type="system",
        actor_id=None,
        reason="mock payment",
    )
    session.flush()
    refreshed = order_repo.get_order_for_user(session, order.id, user_id)
    assert refreshed is not None
    return _to_order_out(session, refreshed)


def get_order(session: Session, user_id: str, order_id: str) -> OrderOut:
    order = order_repo.get_order_for_user(session, order_id, user_id)
    if order is None:
        raise NotFound("订单不存在")
    return _to_order_out(session, order)


def list_orders(
    session: Session, user_id: str, *, status: str | None, limit: int, offset: int
) -> tuple[list[OrderOut], int]:
    orders, total = order_repo.list_orders_for_user(
        session, user_id, status=status, limit=limit, offset=offset
    )
    return [_to_order_out(session, order) for order in orders], total


# ---------------------------------------------------------------- 内部


def _get_active_stall(session: Session, stall_id: str) -> Stall:
    stall = catalog_repo.get_stall(session, stall_id)
    if stall is None or stall.status != "active":
        raise NotFound("档口不存在或已停业")
    return stall


def _price(
    session: Session, stall: Stall, payload: PreviewOrderIn
) -> tuple[list[_PricedItem], AmountOut]:
    if not is_open(_stall_hours(session, stall.id), now_cn()):
        raise Conflict("档口当前休息中，暂不接单")

    dish_ids = [item.dish_id for item in payload.items]
    dishes = order_repo.get_dishes(session, dish_ids)
    option_ids = [option_id for item in payload.items for option_id in item.option_ids]
    options = order_repo.get_options(session, option_ids)

    priced: list[_PricedItem] = []
    for item in payload.items:
        dish = dishes.get(item.dish_id)
        if dish is None or dish.stall_id != stall.id:
            raise NotFound("菜品不存在")
        if dish.status != "on_sale":
            raise Conflict(f"「{dish.name}」已售罄或下架")
        if dish.stock < item.quantity:
            raise Conflict(f"「{dish.name}」库存不足", details={"dishId": dish.id})

        chosen: list[DishOption] = []
        for option_id in item.option_ids:
            option = options.get(option_id)
            if option is None:
                raise ValidationFailed("规格不存在", details={"optionId": option_id})
            chosen.append(option)

        _validate_options(session, dish, chosen)

        unit_price = dish.price_cents + sum(option.price_delta_cents for option in chosen)
        priced.append(
            _PricedItem(
                dish=dish,
                options=chosen,
                quantity=item.quantity,
                unit_price_cents=unit_price,
                line_amount_cents=unit_price * item.quantity,
            )
        )

    items_amount = sum(item.line_amount_cents for item in priced)
    packing_fee = stall.packing_fee_cents if priced else 0
    delivery_fee = stall.delivery_fee_cents if payload.fulfillment_type == "delivery" else 0

    return priced, AmountOut(
        items_amount_cents=items_amount,
        packing_fee_cents=packing_fee,
        delivery_fee_cents=delivery_fee,
        discount_cents=0,
        payable_cents=items_amount + packing_fee + delivery_fee,
    )


def _validate_options(session: Session, dish: Dish, chosen: list[DishOption]) -> None:
    """校验规格：必须属于该菜品、必选组要选满、每组不超上限。"""
    groups_by_id = {group.id: group for group in _dish_option_groups(session, dish.id)}
    chosen_by_group: dict[str, list[DishOption]] = {}
    for option in chosen:
        if option.group_id not in groups_by_id:
            raise ValidationFailed("规格不属于该菜品", details={"optionId": option.id})
        chosen_by_group.setdefault(option.group_id, []).append(option)

    for group_id, group in groups_by_id.items():
        picked = chosen_by_group.get(group_id, [])
        if group.required and len(picked) < max(group.min_select, 1):
            raise ValidationFailed(f"请选择「{group.name}」", details={"groupId": group_id})
        if len(picked) > group.max_select:
            raise ValidationFailed(
                f"「{group.name}」最多选 {group.max_select} 项", details={"groupId": group_id}
            )


def _dish_option_groups(session: Session, dish_id: str) -> list[DishOptionGroup]:
    return list(session.scalars(select(DishOptionGroup).where(DishOptionGroup.dish_id == dish_id)))


def _stall_hours(session: Session, stall_id: str) -> list[tuple[int, str, str]]:
    rows = catalog_repo.list_business_hours(session, stall_id)
    return [(row.weekday, row.open_time, row.close_time) for row in rows]


def _estimated_minutes(stall: Stall) -> int:
    minutes = 15
    if stall.monthly_sales > 1500:
        minutes += 5
    return min(minutes, 45)


def _address_snapshot(session: Session, user_id: str, address_id: str | None) -> str:
    if not address_id:
        raise ValidationFailed("配送订单需要选择地址", details={"field": "addressId"})
    address: Address | None = session.get(Address, address_id)
    if address is None or address.user_id != user_id:
        raise NotFound("地址不存在")
    return json.dumps(
        {
            "buildingCode": address.building_code,
            "buildingName": address.building_name,
            "room": address.room,
            "contactName": address.contact_name,
            "contactPhone": address.contact_phone,
        },
        ensure_ascii=False,
    )


def _order_no(now: datetime) -> str:
    return "SO" + now.strftime("%y%m%d%H%M%S") + secrets.token_hex(2).upper()


def _order_item_row(order_id: str, item: _PricedItem) -> OrderItem:
    return OrderItem(
        order_id=order_id,
        dish_id=item.dish.id,
        dish_name=item.dish.name,
        unit_price_cents=item.unit_price_cents,
        options_json=order_repo.options_json(
            [
                {
                    "id": option.id,
                    "name": option.name,
                    "priceDeltaCents": option.price_delta_cents,
                }
                for option in item.options
            ]
        ),
        options_amount_cents=sum(option.price_delta_cents for option in item.options),
        quantity=item.quantity,
        line_amount_cents=item.line_amount_cents,
    )


def _item_out(item: _PricedItem) -> OrderItemOut:
    return OrderItemOut(
        dish_id=item.dish.id,
        dish_name=item.dish.name,
        unit_price_cents=item.unit_price_cents,
        options=[
            OrderOptionOut(
                id=option.id, name=option.name, price_delta_cents=option.price_delta_cents
            )
            for option in item.options
        ],
        options_amount_cents=sum(option.price_delta_cents for option in item.options),
        quantity=item.quantity,
        line_amount_cents=item.line_amount_cents,
    )


def _to_order_out(session: Session, order: Order) -> OrderOut:
    rows = order_repo.list_items(session, [order.id]).get(order.id, [])
    stall = session.get(Stall, order.stall_id)
    now = utc_now()
    can_pay = order.status == "pending_payment" and parse_iso(order.expires_at) > now

    return OrderOut(
        id=order.id,
        order_no=order.order_no,
        status=order.status,
        fulfillment_type=order.fulfillment_type,
        stall_id=order.stall_id,
        stall_name=stall.name if stall else "",
        items=[
            OrderItemOut(
                dish_id=row.dish_id,
                dish_name=row.dish_name,
                unit_price_cents=row.unit_price_cents,
                options=[
                    OrderOptionOut(
                        id=option["id"],
                        name=option["name"],
                        price_delta_cents=int(option["priceDeltaCents"]),
                    )
                    for option in json.loads(row.options_json)
                ],
                options_amount_cents=row.options_amount_cents,
                quantity=row.quantity,
                line_amount_cents=row.line_amount_cents,
            )
            for row in rows
        ],
        amount=AmountOut(
            items_amount_cents=order.items_amount_cents,
            packing_fee_cents=order.packing_fee_cents,
            delivery_fee_cents=order.delivery_fee_cents,
            discount_cents=order.discount_cents,
            payable_cents=order.payable_cents,
        ),
        contact_name=order.contact_name,
        contact_phone=order.contact_phone,
        remark=order.remark,
        tableware_count=order.tableware_count,
        created_at=order.created_at,
        expires_at=order.expires_at,
        paid_at=order.paid_at,
        can_pay=can_pay,
        can_cancel=order.status == "pending_payment",
    )
