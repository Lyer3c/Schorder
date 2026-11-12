"""目录服务：组装 DTO、计算派生字段（评分、营业状态、预计出餐）。

这里不碰 HTTP，也不知道 Request 的存在——路由层只负责取参数和套信封。
"""

from __future__ import annotations

import base64
import json
from typing import Any

from sqlalchemy.orm import Session

from schorder.db.models import Dish, DishOption, DishOptionGroup, Stall
from schorder.domain.business_hours import is_open, next_open_hint, now_cn
from schorder.domain.errors import NotFound
from schorder.repositories import catalog as repo
from schorder.schemas.catalog import (
    BusinessHourOut,
    CategoryOut,
    DishOptionGroupOut,
    DishOptionOut,
    DishOut,
    MenuGroupOut,
    SearchResultOut,
    StallDetailOut,
    StallSummaryOut,
)

MAX_LIMIT = 50


def encode_cursor(offset: int) -> str:
    return base64.urlsafe_b64encode(json.dumps({"o": offset}).encode()).decode()


def decode_cursor(cursor: str | None) -> int:
    if not cursor:
        return 0
    try:
        payload: dict[str, Any] = json.loads(base64.urlsafe_b64decode(cursor.encode()))
        return max(0, int(payload.get("o", 0)))
    except (ValueError, TypeError, KeyError):
        return 0


def _rating(stall: Stall) -> float:
    if stall.rating_count <= 0:
        return 0.0
    return round(stall.rating_sum / stall.rating_count, 1)


def _estimated_minutes(stall: Stall) -> int:
    """M1 的粗略估计：15 分钟起，单量大时加 5~10 分钟，上限 45。"""
    minutes = 15
    if stall.monthly_sales > 1500:
        minutes += 5
    if stall.monthly_sales > 3000:
        minutes += 5
    return min(minutes, 45)


def _hours_tuples(hours: list[Any]) -> list[tuple[int, str, str]]:
    return [(row.weekday, row.open_time, row.close_time) for row in hours]


def _summary(
    stall: Stall, category_name: str, hours: list[Any], now: Any = None
) -> StallSummaryOut:
    tuples = _hours_tuples(hours)
    opened = is_open(tuples, now)
    return StallSummaryOut(
        id=stall.id,
        name=stall.name,
        description=stall.description,
        logo_url=stall.logo_url,
        category_id=stall.category_id,
        category_name=category_name,
        rating=_rating(stall),
        rating_count=stall.rating_count,
        monthly_sales=stall.monthly_sales,
        min_order_cents=stall.min_order_cents,
        packing_fee_cents=stall.packing_fee_cents,
        delivery_fee_cents=stall.delivery_fee_cents,
        is_open=opened,
        opens_at=None if opened else next_open_hint(tuples, now),
        estimated_minutes=_estimated_minutes(stall),
    )


def list_categories(session: Session) -> list[CategoryOut]:
    return [
        CategoryOut(id=row.id, name=row.name, icon_url=row.icon_url, sort_order=row.sort_order)
        for row in repo.list_categories(session)
    ]


def list_stalls(
    session: Session,
    *,
    category_id: str | None = None,
    keyword: str | None = None,
    sort: str = "recommended",
    open_now: bool = False,
    limit: int = 20,
    cursor: str | None = None,
) -> tuple[list[StallSummaryOut], int, str | None]:
    rows = repo.list_active_stalls(session, category_id=category_id, keyword=keyword)
    now = now_cn()
    hours_map = repo.list_business_hours_for(session, [stall.id for stall, _ in rows])

    items = [_summary(stall, name, hours_map.get(stall.id, []), now) for stall, name in rows]

    if open_now:
        items = [item for item in items if item.is_open]

    if sort == "rating":
        items.sort(key=lambda item: (item.rating, item.monthly_sales), reverse=True)
    elif sort == "min_order":
        items.sort(key=lambda item: item.min_order_cents)
    elif sort == "sales":
        items.sort(key=lambda item: item.monthly_sales, reverse=True)
    else:  # recommended
        items.sort(key=lambda item: (item.monthly_sales, item.rating), reverse=True)

    offset = decode_cursor(cursor)
    bounded = min(max(limit, 1), MAX_LIMIT)
    page = items[offset : offset + bounded]
    next_offset = offset + bounded
    next_cursor = encode_cursor(next_offset) if next_offset < len(items) else None
    return page, len(items), next_cursor


def get_stall_detail(session: Session, stall_id: str) -> StallDetailOut:
    stall = repo.get_stall(session, stall_id)
    if stall is None or stall.status != "active":
        # 停业/待审核/不存在，对外一律 404，避免探测
        raise NotFound("档口不存在或已停业")

    category_name = repo.get_category_name(session, stall.category_id)
    hours = repo.list_business_hours(session, stall.id)
    now = now_cn()
    summary = _summary(stall, category_name, hours, now)

    groups, dishes, option_groups, options = repo.list_menu(session, stall.id)

    options_by_group: dict[str, list[DishOption]] = {}
    for option in options:
        options_by_group.setdefault(option.group_id, []).append(option)

    groups_by_dish: dict[str, list[DishOptionGroup]] = {}
    for option_group in option_groups:
        groups_by_dish.setdefault(option_group.dish_id, []).append(option_group)

    dishes_by_group: dict[str, list[Dish]] = {}
    for dish in dishes:
        if dish.status == "off_shelf":
            continue
        dishes_by_group.setdefault(dish.group_id, []).append(dish)

    menu: list[MenuGroupOut] = []
    for menu_group in groups:
        dish_outs = [
            DishOut(
                id=dish.id,
                name=dish.name,
                description=dish.description,
                image_url=dish.image_url,
                price_cents=dish.price_cents,
                stock=dish.stock,
                sold_count=dish.sold_count,
                status=dish.status,
                option_groups=[
                    DishOptionGroupOut(
                        id=option_group.id,
                        name=option_group.name,
                        required=option_group.required,
                        min_select=option_group.min_select,
                        max_select=option_group.max_select,
                        options=[
                            DishOptionOut(
                                id=option.id,
                                name=option.name,
                                price_delta_cents=option.price_delta_cents,
                                is_available=option.is_available,
                            )
                            for option in options_by_group.get(option_group.id, [])
                        ],
                    )
                    for option_group in groups_by_dish.get(dish.id, [])
                ],
            )
            for dish in dishes_by_group.get(menu_group.id, [])
        ]
        if dish_outs:
            menu.append(MenuGroupOut(id=menu_group.id, name=menu_group.name, dishes=dish_outs))

    return StallDetailOut(
        **summary.model_dump(),
        notice=stall.notice,
        business_hours=[
            BusinessHourOut(weekday=row.weekday, open_time=row.open_time, close_time=row.close_time)
            for row in hours
        ],
        menu_groups=menu,
    )


def search(session: Session, keyword: str, limit: int = 10) -> SearchResultOut:
    keyword = keyword.strip()
    if not keyword:
        return SearchResultOut(stalls=[], dishes=[])

    stalls, _, _ = list_stalls(session, keyword=keyword, limit=limit, sort="recommended")
    dishes = repo.search_dishes(session, keyword, limit=limit)

    return SearchResultOut(
        stalls=stalls,
        dishes=[
            DishOut(
                id=dish.id,
                name=dish.name,
                description=dish.description,
                image_url=dish.image_url,
                price_cents=dish.price_cents,
                stock=dish.stock,
                sold_count=dish.sold_count,
                status=dish.status,
                option_groups=[],
            )
            for dish in dishes
        ],
    )
