"""评价域：一单一评，评分聚合在 stalls.rating_sum / rating_count 上。"""

from __future__ import annotations

from sqlalchemy import CheckConstraint, ForeignKey, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from schorder.db.base import Base
from schorder.infra.clock import utc_now_iso
from schorder.infra.ids import uuid7


class Review(Base):
    __tablename__ = "reviews"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid7)
    order_id: Mapped[str] = mapped_column(
        ForeignKey("orders.id", ondelete="CASCADE"), nullable=False, unique=True
    )
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), nullable=False)
    stall_id: Mapped[str] = mapped_column(ForeignKey("stalls.id"), nullable=False)
    rating: Mapped[int] = mapped_column(Integer, nullable=False)
    content: Mapped[str | None] = mapped_column(Text)
    is_anonymous: Mapped[bool] = mapped_column(Integer, nullable=False, default=0)
    created_at: Mapped[str] = mapped_column(String(24), nullable=False, default=utc_now_iso)

    __table_args__ = (
        CheckConstraint("rating BETWEEN 1 AND 5", name="rating"),
        Index("ix_reviews_stall_time", "stall_id", "created_at"),
    )
