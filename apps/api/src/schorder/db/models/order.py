"""订单域：订单、明细快照、状态日志、支付记录。"""

from __future__ import annotations

from sqlalchemy import CheckConstraint, ForeignKey, Index, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from schorder.db.base import Base
from schorder.infra.clock import utc_now_iso
from schorder.infra.ids import uuid7


class Order(Base):
    """订单主表。

    两条硬约束：
    - (user_id, idempotency_key) 唯一 —— 重复提交不会产生两单
    - payable_cents >= 0 —— 金额永远是服务端算出来的
    """

    __tablename__ = "orders"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid7)
    order_no: Mapped[str] = mapped_column(String(24), nullable=False, unique=True)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), nullable=False)
    stall_id: Mapped[str] = mapped_column(ForeignKey("stalls.id"), nullable=False)

    status: Mapped[str] = mapped_column(String(20), nullable=False, default="pending_payment")
    fulfillment_type: Mapped[str] = mapped_column(String(10), nullable=False)

    address_snapshot_json: Mapped[str | None] = mapped_column(Text)
    contact_name: Mapped[str] = mapped_column(String(30), nullable=False)
    contact_phone: Mapped[str] = mapped_column(String(20), nullable=False)
    tableware_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    expected_ready_at: Mapped[str | None] = mapped_column(String(24))
    remark: Mapped[str | None] = mapped_column(String(100))

    items_amount_cents: Mapped[int] = mapped_column(Integer, nullable=False)
    packing_fee_cents: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    delivery_fee_cents: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    discount_cents: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    payable_cents: Mapped[int] = mapped_column(Integer, nullable=False)

    idempotency_key: Mapped[str] = mapped_column(String(64), nullable=False)
    cancel_reason: Mapped[str | None] = mapped_column(String(200))

    expires_at: Mapped[str] = mapped_column(String(24), nullable=False)
    created_at: Mapped[str] = mapped_column(String(24), nullable=False, default=utc_now_iso)
    paid_at: Mapped[str | None] = mapped_column(String(24))
    accepted_at: Mapped[str | None] = mapped_column(String(24))
    ready_at: Mapped[str | None] = mapped_column(String(24))
    completed_at: Mapped[str | None] = mapped_column(String(24))
    cancelled_at: Mapped[str | None] = mapped_column(String(24))
    updated_at: Mapped[str] = mapped_column(
        String(24), nullable=False, default=utc_now_iso, onupdate=utc_now_iso
    )
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    __table_args__ = (
        UniqueConstraint("user_id", "idempotency_key", name="ux_orders_idem"),
        CheckConstraint(
            "status IN ('pending_payment', 'paid', 'accepted', 'preparing', "
            "'ready', 'delivering', 'completed', 'cancelled')",
            name="status",
        ),
        CheckConstraint("fulfillment_type IN ('pickup', 'delivery')", name="fulfillment"),
        CheckConstraint(
            "items_amount_cents >= 0 AND packing_fee_cents >= 0 "
            "AND delivery_fee_cents >= 0 AND discount_cents >= 0",
            name="fees",
        ),
        CheckConstraint("payable_cents >= 0", name="payable"),
        CheckConstraint(
            "fulfillment_type = 'pickup' OR address_snapshot_json IS NOT NULL",
            name="delivery_needs_address",
        ),
        Index("ix_orders_user_time", "user_id", "created_at"),
        Index("ix_orders_stall_state", "stall_id", "status", "created_at"),
        Index("ix_orders_state_exp", "status", "expires_at"),
    )


class OrderItem(Base):
    """订单明细：名称/单价/规格都是下单时的快照，菜品后续改价不影响历史。"""

    __tablename__ = "order_items"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid7)
    order_id: Mapped[str] = mapped_column(
        ForeignKey("orders.id", ondelete="CASCADE"), nullable=False
    )
    dish_id: Mapped[str] = mapped_column(ForeignKey("dishes.id"), nullable=False)
    dish_name: Mapped[str] = mapped_column(String(60), nullable=False)
    unit_price_cents: Mapped[int] = mapped_column(Integer, nullable=False)
    options_json: Mapped[str] = mapped_column(Text, nullable=False, default="[]")
    options_amount_cents: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    line_amount_cents: Mapped[int] = mapped_column(Integer, nullable=False)

    __table_args__ = (
        CheckConstraint("quantity > 0", name="quantity"),
        Index("ix_order_items_order", "order_id"),
    )


class OrderStatusLog(Base):
    """状态流转审计。订单详情的状态时间轴直接读这张表。"""

    __tablename__ = "order_status_logs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid7)
    order_id: Mapped[str] = mapped_column(
        ForeignKey("orders.id", ondelete="CASCADE"), nullable=False
    )
    from_status: Mapped[str | None] = mapped_column(String(20))
    to_status: Mapped[str] = mapped_column(String(20), nullable=False)
    actor_type: Mapped[str] = mapped_column(String(10), nullable=False)
    actor_id: Mapped[str | None] = mapped_column(String(36))
    reason: Mapped[str | None] = mapped_column(String(200))
    created_at: Mapped[str] = mapped_column(String(24), nullable=False, default=utc_now_iso)

    __table_args__ = (
        CheckConstraint(
            "actor_type IN ('student', 'merchant', 'admin', 'system')", name="actor_type"
        ),
        Index("ix_status_logs_order_time", "order_id", "created_at"),
    )


class Payment(Base):
    """支付/退款记录。当前 provider 固定为 mock，接真实通道时改这里。"""

    __tablename__ = "payments"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid7)
    order_id: Mapped[str] = mapped_column(ForeignKey("orders.id"), nullable=False)
    provider: Mapped[str] = mapped_column(String(20), nullable=False, default="mock")
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="succeeded")
    amount_cents: Mapped[int] = mapped_column(Integer, nullable=False)
    transaction_no: Mapped[str] = mapped_column(String(40), nullable=False, unique=True)
    paid_at: Mapped[str | None] = mapped_column(String(24))
    created_at: Mapped[str] = mapped_column(String(24), nullable=False, default=utc_now_iso)

    __table_args__ = (
        CheckConstraint("status IN ('succeeded', 'refunded')", name="status"),
        CheckConstraint("amount_cents >= 0", name="amount"),
        Index("ix_payments_order", "order_id"),
    )
