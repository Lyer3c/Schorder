"""会话仓储：令牌只存哈希，查库按 token_hash 命中。"""

from __future__ import annotations

from datetime import timedelta
from typing import Any, cast

from sqlalchemy import CursorResult, select, update
from sqlalchemy.orm import Session

from schorder.db.models import UserSession
from schorder.infra.clock import to_iso, utc_now
from schorder.infra.ids import uuid7


def insert(
    session: Session,
    *,
    token_hash: str,
    user_id: str,
    csrf_token: str,
    idle_minutes: int,
    absolute_hours: int,
    ip_hash: str | None,
    ua_hash: str | None,
) -> UserSession:
    now = utc_now()
    row = UserSession(
        id=uuid7(),
        token_hash=token_hash,
        user_id=user_id,
        csrf_token=csrf_token,
        idle_expires_at=to_iso(now + timedelta(minutes=idle_minutes)),
        absolute_expires_at=to_iso(now + timedelta(hours=absolute_hours)),
        ip_hash=ip_hash,
        ua_hash=ua_hash,
        created_at=to_iso(now),
    )
    session.add(row)
    session.flush()
    return row


def get_by_token_hash(session: Session, token_hash: str) -> UserSession | None:
    return session.scalar(select(UserSession).where(UserSession.token_hash == token_hash))


def revoke(session: Session, row: UserSession) -> None:
    if row.revoked_at is None:
        row.revoked_at = to_iso(utc_now())
        session.flush()


def revoke_all_for_user(session: Session, user_id: str) -> int:
    result = cast(
        "CursorResult[Any]",
        session.execute(
            update(UserSession)
            .where(UserSession.user_id == user_id, UserSession.revoked_at.is_(None))
            .values(revoked_at=to_iso(utc_now()))
        ),
    )
    session.flush()
    return int(result.rowcount or 0)


def extend_idle(session: Session, row: UserSession, idle_minutes: int) -> None:
    row.idle_expires_at = to_iso(utc_now() + timedelta(minutes=idle_minutes))
    session.flush()
