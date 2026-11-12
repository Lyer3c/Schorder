"""目录接口的出入参模型。"""

from __future__ import annotations

from typing import Literal

from schorder.schemas.common import ApiModel


class CategoryOut(ApiModel):
    id: str
    name: str
    icon_url: str | None = None
    sort_order: int


class StallSummaryOut(ApiModel):
    id: str
    name: str
    description: str | None = None
    logo_url: str | None = None
    category_id: str
    category_name: str
    rating: float
    rating_count: int
    monthly_sales: int
    min_order_cents: int
    packing_fee_cents: int
    delivery_fee_cents: int
    is_open: bool
    opens_at: str | None = None
    estimated_minutes: int


class BusinessHourOut(ApiModel):
    weekday: int
    open_time: str
    close_time: str


class DishOptionOut(ApiModel):
    id: str
    name: str
    price_delta_cents: int
    is_available: bool


class DishOptionGroupOut(ApiModel):
    id: str
    name: str
    required: bool
    min_select: int
    max_select: int
    options: list[DishOptionOut]


class DishOut(ApiModel):
    id: str
    name: str
    description: str | None = None
    image_url: str | None = None
    price_cents: int
    stock: int
    sold_count: int
    status: str
    option_groups: list[DishOptionGroupOut]


class MenuGroupOut(ApiModel):
    id: str
    name: str
    dishes: list[DishOut]


class StallDetailOut(StallSummaryOut):
    notice: str | None = None
    business_hours: list[BusinessHourOut]
    menu_groups: list[MenuGroupOut]


class PageMeta(ApiModel):
    next_cursor: str | None = None
    total: int | None = None


class CategoryListOut(ApiModel):
    ok: Literal[True] = True
    data: list[CategoryOut]


class StallListOut(ApiModel):
    ok: Literal[True] = True
    data: list[StallSummaryOut]
    meta: PageMeta


class StallDetailEnvelope(ApiModel):
    ok: Literal[True] = True
    data: StallDetailOut


class SearchResultOut(ApiModel):
    stalls: list[StallSummaryOut]
    dishes: list[DishOut]


class SearchEnvelope(ApiModel):
    ok: Literal[True] = True
    data: SearchResultOut
