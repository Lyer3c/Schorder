"""订单接口的出入参。"""

from __future__ import annotations

from typing import Literal

from pydantic import Field

from schorder.schemas.catalog import PageMeta
from schorder.schemas.common import ApiModel


class OrderItemIn(ApiModel):
    dish_id: str
    quantity: int = Field(ge=1, le=20)
    option_ids: list[str] = Field(default_factory=list, max_length=10)


class PreviewOrderIn(ApiModel):
    stall_id: str
    fulfillment_type: Literal["pickup", "delivery"] = "pickup"
    items: list[OrderItemIn] = Field(min_length=1, max_length=20)
    address_id: str | None = None
    tableware_count: int = Field(default=0, ge=0, le=10)


class CreateOrderIn(PreviewOrderIn):
    contact_name: str = Field(min_length=1, max_length=30)
    contact_phone: str = Field(min_length=6, max_length=20)
    remark: str | None = Field(default=None, max_length=100)
    idempotency_key: str = Field(min_length=8, max_length=64)


class OrderOptionOut(ApiModel):
    id: str
    name: str
    price_delta_cents: int


class OrderItemOut(ApiModel):
    dish_id: str
    dish_name: str
    unit_price_cents: int
    options: list[OrderOptionOut]
    options_amount_cents: int
    quantity: int
    line_amount_cents: int


class AmountOut(ApiModel):
    items_amount_cents: int
    packing_fee_cents: int
    delivery_fee_cents: int
    discount_cents: int
    payable_cents: int


class PreviewOut(ApiModel):
    stall_id: str
    stall_name: str
    fulfillment_type: str
    items: list[OrderItemOut]
    amount: AmountOut
    min_order_ok: bool
    min_order_cents: int
    estimated_minutes: int
    warnings: list[str]


class PreviewEnvelope(ApiModel):
    ok: Literal[True] = True
    data: PreviewOut


class OrderOut(ApiModel):
    id: str
    order_no: str
    status: str
    fulfillment_type: str
    stall_id: str
    stall_name: str
    items: list[OrderItemOut]
    amount: AmountOut
    contact_name: str
    contact_phone: str
    remark: str | None = None
    tableware_count: int
    created_at: str
    expires_at: str
    paid_at: str | None = None
    can_pay: bool
    can_cancel: bool


class OrderEnvelope(ApiModel):
    ok: Literal[True] = True
    data: OrderOut


class OrderListOut(ApiModel):
    ok: Literal[True] = True
    data: list[OrderOut]
    meta: PageMeta
