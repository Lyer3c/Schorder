"""目录仓储：只写查询，不写业务规则。

注意：M1 的目录规模很小（几十个档口），列表的"营业中"过滤与排序在 Service 层
用内存完成。等数据量上去（>1000）再把这些条件下推到 SQL。
"""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from schorder.db.models import (
    Category,
    Dish,
    DishOption,
    DishOptionGroup,
    MenuGroup,
    Stall,
    StallBusinessHour,
)


def list_categories(session: Session) -> list[Category]:
    stmt = (
        select(Category)
        .where(Category.is_active.is_(True))
        .order_by(Category.sort_order, Category.name)
    )
    return list(session.scalars(stmt))


def list_active_stalls(
    session: Session, *, category_id: str | None = None, keyword: str | None = None
) -> list[tuple[Stall, str]]:
    """返回 (档口, 分类名)。只包含 active 状态——待审核和停业不对外。"""
    stmt = (
        select(Stall, Category.name)
        .join(Category, Stall.category_id == Category.id)
        .where(Stall.status == "active")
    )
    if category_id:
        stmt = stmt.where(Stall.category_id == category_id)
    if keyword:
        stmt = stmt.where(Stall.name.contains(keyword))
    stmt = stmt.order_by(Stall.monthly_sales.desc(), Stall.id)
    return [(stall, category_name) for stall, category_name in session.execute(stmt)]


def get_stall(session: Session, stall_id: str) -> Stall | None:
    return session.get(Stall, stall_id)


def get_category_name(session: Session, category_id: str) -> str:
    category = session.get(Category, category_id)
    return category.name if category else ""


def list_business_hours(session: Session, stall_id: str) -> list[StallBusinessHour]:
    stmt = (
        select(StallBusinessHour)
        .where(StallBusinessHour.stall_id == stall_id)
        .order_by(StallBusinessHour.weekday, StallBusinessHour.open_time)
    )
    return list(session.scalars(stmt))


def list_business_hours_for(
    session: Session, stall_ids: list[str]
) -> dict[str, list[StallBusinessHour]]:
    """批量取营业时段，避免列表页 N+1 查询。"""
    if not stall_ids:
        return {}
    stmt = (
        select(StallBusinessHour)
        .where(StallBusinessHour.stall_id.in_(stall_ids))
        .order_by(StallBusinessHour.weekday, StallBusinessHour.open_time)
    )
    grouped: dict[str, list[StallBusinessHour]] = {stall_id: [] for stall_id in stall_ids}
    for row in session.scalars(stmt):
        grouped.setdefault(row.stall_id, []).append(row)
    return grouped


def list_menu(
    session: Session, stall_id: str
) -> tuple[list[MenuGroup], list[Dish], list[DishOptionGroup], list[DishOption]]:
    """一次性取回菜单的四层结构，由 Service 组装。"""
    groups = list(
        session.scalars(
            select(MenuGroup)
            .where(MenuGroup.stall_id == stall_id)
            .order_by(MenuGroup.sort_order, MenuGroup.name)
        )
    )
    dishes = list(
        session.scalars(
            select(Dish).where(Dish.stall_id == stall_id).order_by(Dish.sort_order, Dish.name)
        )
    )
    dish_ids = [dish.id for dish in dishes]
    option_groups: list[DishOptionGroup] = []
    options: list[DishOption] = []

    if dish_ids:
        option_groups = list(
            session.scalars(
                select(DishOptionGroup)
                .where(DishOptionGroup.dish_id.in_(dish_ids))
                .order_by(DishOptionGroup.sort_order)
            )
        )
    group_ids = [group.id for group in option_groups]
    if group_ids:
        options = list(
            session.scalars(
                select(DishOption)
                .where(DishOption.group_id.in_(group_ids))
                .order_by(DishOption.sort_order)
            )
        )
    return groups, dishes, option_groups, options


def search_dishes(session: Session, keyword: str, limit: int = 20) -> list[Dish]:
    stmt = (
        select(Dish)
        .join(Stall, Dish.stall_id == Stall.id)
        .where(Stall.status == "active")
        .where(Dish.status == "on_sale")
        .where(Dish.name.contains(keyword))
        .order_by(Dish.sold_count.desc())
        .limit(limit)
    )
    return list(session.scalars(stmt))
