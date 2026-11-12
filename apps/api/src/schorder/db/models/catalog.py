"""目录域：分类、档口、营业时段、菜单分组、菜品、规格。"""

from __future__ import annotations

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column

from schorder.db.base import Base
from schorder.infra.clock import utc_now_iso
from schorder.infra.ids import uuid7


class Category(Base):
    """档口分类：盖浇饭、面食、饮品……"""

    __tablename__ = "categories"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid7)
    name: Mapped[str] = mapped_column(String(30), nullable=False, unique=True)
    icon_url: Mapped[str | None] = mapped_column(String(200))
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)


class Stall(Base):
    """档口。

    金额相关的三个字段（起送价、包装费、配送费）在建单时由服务端读取，
    前端传来的值一律忽略。
    """

    __tablename__ = "stalls"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid7)
    owner_user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), nullable=False)
    category_id: Mapped[str] = mapped_column(ForeignKey("categories.id"), nullable=False)
    name: Mapped[str] = mapped_column(String(60), nullable=False)
    description: Mapped[str | None] = mapped_column(String(200))
    logo_url: Mapped[str | None] = mapped_column(String(200))
    cover_url: Mapped[str | None] = mapped_column(String(200))
    notice: Mapped[str | None] = mapped_column(String(200))
    contact_phone: Mapped[str | None] = mapped_column(String(20))

    min_order_cents: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    packing_fee_cents: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    delivery_fee_cents: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    rating_sum: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    rating_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    monthly_sales: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    monthly_sales_period: Mapped[str] = mapped_column(String(7), nullable=False, default="")

    status: Mapped[str] = mapped_column(String(20), nullable=False, default="pending")
    reviewed_by: Mapped[str | None] = mapped_column(String(36))
    reviewed_at: Mapped[str | None] = mapped_column(String(24))

    created_at: Mapped[str] = mapped_column(String(24), nullable=False, default=utc_now_iso)
    updated_at: Mapped[str] = mapped_column(
        String(24), nullable=False, default=utc_now_iso, onupdate=utc_now_iso
    )
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    __table_args__ = (
        CheckConstraint("status IN ('pending', 'active', 'suspended')", name="status"),
        CheckConstraint(
            "min_order_cents >= 0 AND packing_fee_cents >= 0 AND delivery_fee_cents >= 0",
            name="fees",
        ),
        Index("ix_stalls_category_status", "category_id", "status"),
        Index("ix_stalls_owner", "owner_user_id"),
    )


class StallBusinessHour(Base):
    """每周营业时段。支持跨夜：关门时间小于开门时间表示到次日。"""

    __tablename__ = "stall_business_hours"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid7)
    stall_id: Mapped[str] = mapped_column(
        ForeignKey("stalls.id", ondelete="CASCADE"), nullable=False
    )
    weekday: Mapped[int] = mapped_column(Integer, nullable=False)  # 1=周一 … 7=周日
    open_time: Mapped[str] = mapped_column(String(5), nullable=False)  # "08:00"
    close_time: Mapped[str] = mapped_column(String(5), nullable=False)

    __table_args__ = (
        CheckConstraint("weekday BETWEEN 1 AND 7", name="weekday"),
        Index("ix_business_hours_stall", "stall_id", "weekday"),
    )


class MenuGroup(Base):
    """档口内的菜单分组：招牌、主食、加料……"""

    __tablename__ = "menu_groups"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid7)
    stall_id: Mapped[str] = mapped_column(
        ForeignKey("stalls.id", ondelete="CASCADE"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(30), nullable=False)
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    __table_args__ = (Index("ix_menu_groups_stall", "stall_id", "sort_order"),)


class Dish(Base):
    """菜品。价格单位是分，库存为 0 即售罄。"""

    __tablename__ = "dishes"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid7)
    stall_id: Mapped[str] = mapped_column(
        ForeignKey("stalls.id", ondelete="CASCADE"), nullable=False
    )
    group_id: Mapped[str] = mapped_column(ForeignKey("menu_groups.id"), nullable=False)
    name: Mapped[str] = mapped_column(String(60), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    image_url: Mapped[str | None] = mapped_column(String(200))

    price_cents: Mapped[int] = mapped_column(Integer, nullable=False)
    stock: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    sold_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="on_sale")
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    created_at: Mapped[str] = mapped_column(String(24), nullable=False, default=utc_now_iso)
    updated_at: Mapped[str] = mapped_column(
        String(24), nullable=False, default=utc_now_iso, onupdate=utc_now_iso
    )
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    __table_args__ = (
        CheckConstraint("price_cents >= 0", name="price"),
        CheckConstraint("stock >= 0", name="stock"),
        CheckConstraint("status IN ('on_sale', 'sold_out', 'off_shelf')", name="status"),
        Index("ix_dishes_stall_group", "stall_id", "group_id", "sort_order"),
    )


class DishOptionGroup(Base):
    """规格组：辣度（必选单选）、加料（可选多选）。"""

    __tablename__ = "dish_option_groups"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid7)
    dish_id: Mapped[str] = mapped_column(
        ForeignKey("dishes.id", ondelete="CASCADE"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(30), nullable=False)
    required: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    min_select: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    max_select: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    __table_args__ = (
        CheckConstraint("min_select >= 0 AND max_select >= min_select", name="select_range"),
        Index("ix_option_groups_dish", "dish_id", "sort_order"),
    )


class DishOption(Base):
    """规格项：微辣、加蛋（+3 元）。"""

    __tablename__ = "dish_options"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid7)
    group_id: Mapped[str] = mapped_column(
        ForeignKey("dish_option_groups.id", ondelete="CASCADE"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(30), nullable=False)
    price_delta_cents: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    is_available: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    __table_args__ = (
        CheckConstraint("price_delta_cents >= 0", name="price_delta"),
        Index("ix_options_group", "group_id", "sort_order"),
    )
