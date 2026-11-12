"""账号域：用户、会话、安全审计、登录失败计数、地址簿。"""

from __future__ import annotations

from sqlalchemy import Boolean, CheckConstraint, ForeignKey, Index, Integer, String, text
from sqlalchemy.orm import Mapped, mapped_column

from schorder.db.base import Base
from schorder.infra.clock import utc_now_iso
from schorder.infra.ids import uuid7


class User(Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid7)
    phone: Mapped[str] = mapped_column(String(20), nullable=False, unique=True)
    password_hash: Mapped[str] = mapped_column(String(200), nullable=False)
    password_algo: Mapped[str] = mapped_column(String(20), nullable=False, default="argon2id")
    nickname: Mapped[str] = mapped_column(String(30), nullable=False)
    avatar_url: Mapped[str | None] = mapped_column(String(200))
    role: Mapped[str] = mapped_column(String(20), nullable=False, default="student")
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="active")

    created_at: Mapped[str] = mapped_column(String(24), nullable=False, default=utc_now_iso)
    updated_at: Mapped[str] = mapped_column(
        String(24), nullable=False, default=utc_now_iso, onupdate=utc_now_iso
    )
    last_login_at: Mapped[str | None] = mapped_column(String(24))

    __table_args__ = (
        CheckConstraint("role IN ('student', 'merchant', 'admin')", name="role"),
        CheckConstraint("status IN ('active', 'disabled')", name="status"),
    )


class UserSession(Base):
    """服务端不透明会话。库里只存令牌的 SHA-256，泄库也无法直接冒用。"""

    __tablename__ = "sessions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid7)
    token_hash: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), nullable=False)
    csrf_token: Mapped[str] = mapped_column(String(64), nullable=False)
    idle_expires_at: Mapped[str] = mapped_column(String(24), nullable=False)
    absolute_expires_at: Mapped[str] = mapped_column(String(24), nullable=False)
    revoked_at: Mapped[str | None] = mapped_column(String(24))
    ip_hash: Mapped[str | None] = mapped_column(String(64))
    ua_hash: Mapped[str | None] = mapped_column(String(64))
    created_at: Mapped[str] = mapped_column(String(24), nullable=False, default=utc_now_iso)

    __table_args__ = (Index("ix_sessions_user", "user_id", "revoked_at"),)


class SecurityEvent(Base):
    """安全审计，只追加不修改（部署时可用触发器禁止 UPDATE/DELETE）。"""

    __tablename__ = "security_events"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid7)
    type: Mapped[str] = mapped_column(String(40), nullable=False)
    actor_id: Mapped[str | None] = mapped_column(String(36))
    target_type: Mapped[str | None] = mapped_column(String(20))
    target_id: Mapped[str | None] = mapped_column(String(36))
    ip_hash: Mapped[str | None] = mapped_column(String(64))
    ua_hash: Mapped[str | None] = mapped_column(String(64))
    result: Mapped[str] = mapped_column(String(20), nullable=False, default="ok")
    reason: Mapped[str | None] = mapped_column(String(200))
    created_at: Mapped[str] = mapped_column(String(24), nullable=False, default=utc_now_iso)

    __table_args__ = (Index("ix_security_events_type_time", "type", "created_at"),)


class LoginAttempt(Base):
    """登录失败计数与锁定。key 是 phone:hash 或 ip:hash。"""

    __tablename__ = "login_attempts"

    key: Mapped[str] = mapped_column(String(80), primary_key=True)
    count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    locked_until: Mapped[str | None] = mapped_column(String(24))
    updated_at: Mapped[str] = mapped_column(
        String(24), nullable=False, default=utc_now_iso, onupdate=utc_now_iso
    )

    __table_args__ = (CheckConstraint("count >= 0", name="count"),)


class Address(Base):
    """宿舍地址簿。每个用户最多一个默认地址（部分唯一索引保证）。"""

    __tablename__ = "addresses"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid7)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), nullable=False)
    building_code: Mapped[str] = mapped_column(String(20), nullable=False)
    building_name: Mapped[str] = mapped_column(String(40), nullable=False)
    room: Mapped[str] = mapped_column(String(20), nullable=False)
    contact_name: Mapped[str] = mapped_column(String(30), nullable=False)
    contact_phone: Mapped[str] = mapped_column(String(20), nullable=False)
    is_default: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[str] = mapped_column(String(24), nullable=False, default=utc_now_iso)
    updated_at: Mapped[str] = mapped_column(
        String(24), nullable=False, default=utc_now_iso, onupdate=utc_now_iso
    )

    __table_args__ = (
        Index(
            "ux_addresses_default",
            "user_id",
            unique=True,
            sqlite_where=text("is_default = 1"),
        ),
    )
