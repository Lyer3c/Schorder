"""安全审计与登录失败计数。"""

from __future__ import annotations

from datetime import timedelta

from sqlalchemy.orm import Session

from schorder.db.models import LoginAttempt, SecurityEvent
from schorder.infra.clock import to_iso, utc_now
from schorder.infra.ids import uuid7


def record_event(
    session: Session,
    *,
    event_type: str,
    result: str = "ok",
    actor_id: str | None = None,
    reason: str | None = None,
    ip_hash: str | None = None,
    ua_hash: str | None = None,
) -> None:
    session.add(
        SecurityEvent(
            id=uuid7(),
            type=event_type,
            actor_id=actor_id,
            ip_hash=ip_hash,
            ua_hash=ua_hash,
            result=result,
            reason=reason,
        )
    )
    session.flush()


def get_attempt(session: Session, key: str) -> LoginAttempt | None:
    return session.get(LoginAttempt, key)


def bump_attempt(session: Session, key: str, *, limit: int, lock_minutes: int) -> LoginAttempt:
    """失败计数 +1；达到上限则写 locked_until。"""
    row = session.get(LoginAttempt, key)
    if row is None:
        row = LoginAttempt(key=key, count=0)
        session.add(row)

    row.count += 1
    if row.count >= limit:
        row.locked_until = to_iso(utc_now() + timedelta(minutes=lock_minutes))
    row.updated_at = to_iso(utc_now())
    session.flush()
    return row


def clear_attempt(session: Session, key: str) -> None:
    row = session.get(LoginAttempt, key)
    if row is not None:
        session.delete(row)
        session.flush()
