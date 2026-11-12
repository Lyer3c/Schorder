"""模型汇总：Alembic 和测试都从这里导入，保证 metadata 注册完整。

新增模型必须在这里导出，否则 autogenerate 看不到它，会生成"删表"的迁移。
"""

from __future__ import annotations

from schorder.db.models.catalog import (
    Category,
    Dish,
    DishOption,
    DishOptionGroup,
    MenuGroup,
    Stall,
    StallBusinessHour,
)
from schorder.db.models.order import Order, OrderItem, OrderStatusLog, Payment
from schorder.db.models.review import Review
from schorder.db.models.user import Address, LoginAttempt, SecurityEvent, User, UserSession

__all__ = [
    "Address",
    "Category",
    "Dish",
    "DishOption",
    "DishOptionGroup",
    "LoginAttempt",
    "MenuGroup",
    "Order",
    "OrderItem",
    "OrderStatusLog",
    "Payment",
    "Review",
    "SecurityEvent",
    "Stall",
    "StallBusinessHour",
    "User",
    "UserSession",
]
