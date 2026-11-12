"""业务枚举。

统一用 str 枚举：与数据库里存的字符串一致，序列化成 JSON 时也不用额外转换。
"""

from __future__ import annotations

from enum import StrEnum


class UserRole(StrEnum):
    STUDENT = "student"
    MERCHANT = "merchant"
    ADMIN = "admin"


class UserStatus(StrEnum):
    ACTIVE = "active"
    DISABLED = "disabled"


class StallStatus(StrEnum):
    PENDING = "pending"
    ACTIVE = "active"
    SUSPENDED = "suspended"


class DishStatus(StrEnum):
    ON_SALE = "on_sale"
    SOLD_OUT = "sold_out"
    OFF_SHELF = "off_shelf"


class FulfillmentType(StrEnum):
    PICKUP = "pickup"
    DELIVERY = "delivery"


class OrderStatus(StrEnum):
    PENDING_PAYMENT = "pending_payment"
    PAID = "paid"
    ACCEPTED = "accepted"
    PREPARING = "preparing"
    READY = "ready"
    DELIVERING = "delivering"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class PaymentStatus(StrEnum):
    SUCCEEDED = "succeeded"
    REFUNDED = "refunded"


class ActorType(StrEnum):
    STUDENT = "student"
    MERCHANT = "merchant"
    ADMIN = "admin"
    SYSTEM = "system"


def sql_in(enum_cls: type[StrEnum]) -> str:
    """把枚举展开成 SQL IN 子句里的字面量列表。"""
    return ", ".join(f"'{member.value}'" for member in enum_cls)
