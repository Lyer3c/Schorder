"""用户仓储。"""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from schorder.db.models import User
from schorder.infra.clock import to_iso, utc_now
from schorder.infra.ids import uuid7


def get_by_id(session: Session, user_id: str) -> User | None:
    return session.get(User, user_id)


def get_by_phone(session: Session, phone: str) -> User | None:
    return session.scalar(select(User).where(User.phone == phone))


def insert(
    session: Session,
    *,
    phone: str,
    password_hash: str,
    password_algo: str,
    nickname: str,
    role: str = "student",
) -> User:
    user = User(
        id=uuid7(),
        phone=phone,
        password_hash=password_hash,
        password_algo=password_algo,
        nickname=nickname,
        role=role,
        status="active",
    )
    session.add(user)
    session.flush()
    return user


def mark_login(session: Session, user: User) -> None:
    user.last_login_at = to_iso(utc_now())
    session.flush()


def update_password(session: Session, user: User, password_hash: str, password_algo: str) -> None:
    user.password_hash = password_hash
    user.password_algo = password_algo
    session.flush()


def set_status(session: Session, user: User, status: str) -> None:
    user.status = status
    session.flush()
