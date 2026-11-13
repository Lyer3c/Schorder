"""认证与会话服务。

规则集中在这里，HTTP 层只负责取 Cookie、写 Cookie：

- 密码永不落日志，登录失败一律同一错误码（防枚举）
- 账号不存在也执行一次等价哈希（抹平时序差异）
- 连续失败 5 次锁定 15 分钟
- 会话令牌 32 字节随机，库里只存 SHA-256
- 空闲 30 分钟过期，绝对 12 小时过期，活跃时滑动续期
- 登录成功轮换会话（旧令牌立即吊销，防会话固定）
"""

from __future__ import annotations

import hashlib
import hmac
import re
from dataclasses import dataclass
from datetime import timedelta
from typing import NoReturn

from sqlalchemy.orm import Session

from schorder.config import Settings
from schorder.db.models import User, UserSession
from schorder.domain.errors import (
    Conflict,
    Forbidden,
    InvalidCredentials,
    RateLimited,
    Unauthenticated,
    ValidationFailed,
)
from schorder.infra.clock import parse_iso, utc_now
from schorder.infra.security import (
    hash_password,
    hash_token,
    needs_rehash,
    random_token,
    verify_password,
)
from schorder.repositories import security as security_repo
from schorder.repositories import session as session_repo
from schorder.repositories import user as user_repo

PHONE_RE = re.compile(r"^1[3-9]\d{9}$")
PASSWORD_MIN = 8
PASSWORD_MAX = 64
LOGIN_FAIL_LIMIT = 5
LOGIN_LOCK_MINUTES = 15


@dataclass(frozen=True)
class IssuedSession:
    """一次登录/注册的产物：原始令牌只在这里出现一次，之后只剩哈希。"""

    user: User
    csrf_token: str
    raw_token: str
    cookie_max_age: int


def validate_phone(phone: str) -> str:
    normalized = phone.strip()
    if not PHONE_RE.match(normalized):
        raise ValidationFailed("手机号格式不正确", details={"field": "phone"})
    return normalized


def validate_password(password: str) -> None:
    if not (PASSWORD_MIN <= len(password) <= PASSWORD_MAX):
        raise ValidationFailed(
            f"密码长度需在 {PASSWORD_MIN}-{PASSWORD_MAX} 位之间", details={"field": "password"}
        )
    if not re.search(r"[A-Za-z]", password) or not re.search(r"\d", password):
        raise ValidationFailed("密码需同时包含字母和数字", details={"field": "password"})


def validate_nickname(nickname: str) -> str:
    normalized = nickname.strip()
    if not 1 <= len(normalized) <= 30:
        raise ValidationFailed("昵称长度需在 1-30 字之间", details={"field": "nickname"})
    return normalized


def fingerprint(value: str | None, pepper: str) -> str | None:
    """IP / UA 只存 HMAC 指纹：能做关联分析，不能反查原始值。"""
    if not value:
        return None
    return hmac.new(pepper.encode(), value.encode(), hashlib.sha256).hexdigest()


def register(
    session: Session,
    settings: Settings,
    *,
    phone: str,
    password: str,
    nickname: str,
    ip: str | None = None,
    user_agent: str | None = None,
) -> IssuedSession:
    normalized_phone = validate_phone(phone)
    validate_password(password)
    normalized_nickname = validate_nickname(nickname)

    if user_repo.get_by_phone(session, normalized_phone) is not None:
        raise Conflict("该手机号已注册", details={"field": "phone"})

    password_hash, algo = hash_password(password)
    user = user_repo.insert(
        session,
        phone=normalized_phone,
        password_hash=password_hash,
        password_algo=algo,
        nickname=normalized_nickname,
        role="student",
    )

    security_repo.record_event(
        session,
        event_type="auth.register",
        actor_id=user.id,
        ip_hash=fingerprint(ip, settings.security_pepper),
        ua_hash=fingerprint(user_agent, settings.security_pepper),
    )
    return _issue(session, settings, user, ip=ip, user_agent=user_agent)


def login(
    session: Session,
    settings: Settings,
    *,
    phone: str,
    password: str,
    ip: str | None = None,
    user_agent: str | None = None,
    current_token: str | None = None,
) -> IssuedSession:
    normalized_phone = validate_phone(phone)
    attempt_key = f"login:{fingerprint(normalized_phone, settings.security_pepper)}"

    _assert_not_locked(session, attempt_key)

    user = user_repo.get_by_phone(session, normalized_phone)
    if user is None:
        # 账号不存在也走一次哈希校验，避免"是否存在"通过响应时间泄漏
        verify_password(password, _dummy_hash(), "argon2id")
        _on_failure(session, settings, attempt_key, ip=ip, user_agent=user_agent, user_id=None)
        raise InvalidCredentials("手机号或密码错误")

    if not verify_password(password, user.password_hash, user.password_algo):
        _on_failure(session, settings, attempt_key, ip=ip, user_agent=user_agent, user_id=user.id)
        raise InvalidCredentials("手机号或密码错误")

    if user.status != "active":
        raise Forbidden("账号已被停用")

    security_repo.clear_attempt(session, attempt_key)

    # 登录成功轮换会话：同一浏览器上的旧令牌立即作废
    if current_token:
        previous = session_repo.get_by_token_hash(session, hash_token(current_token))
        if previous is not None and previous.user_id == user.id:
            session_repo.revoke(session, previous)

    if needs_rehash(user.password_algo):
        new_hash, new_algo = hash_password(password)
        user_repo.update_password(session, user, new_hash, new_algo)

    user_repo.mark_login(session, user)
    security_repo.record_event(
        session,
        event_type="auth.login",
        actor_id=user.id,
        ip_hash=fingerprint(ip, settings.security_pepper),
        ua_hash=fingerprint(user_agent, settings.security_pepper),
    )
    return _issue(session, settings, user, ip=ip, user_agent=user_agent)


def authenticate(
    session: Session, settings: Settings, raw_token: str | None
) -> tuple[User, UserSession]:
    """校验会话令牌，返回 (用户, 会话行)。过期/吊销/停用一律 401。"""
    if not raw_token:
        raise Unauthenticated("尚未登录")

    row = session_repo.get_by_token_hash(session, hash_token(raw_token))
    if row is None or row.revoked_at is not None:
        raise Unauthenticated("会话已失效")

    now = utc_now()
    if parse_iso(row.absolute_expires_at) <= now:
        session_repo.revoke(session, row)
        _persist_then_raise(session, Unauthenticated("会话已过期，请重新登录"))

    idle_deadline = parse_iso(row.idle_expires_at)
    if idle_deadline <= now:
        session_repo.revoke(session, row)
        _persist_then_raise(session, Unauthenticated("长时间未操作，请重新登录"))

    user = user_repo.get_by_id(session, row.user_id)
    if user is None or user.status != "active":
        session_repo.revoke(session, row)
        _persist_then_raise(session, Unauthenticated("会话已失效"))

    # 滑动续期：剩余不足一半窗口时才写库，避免每个请求都产生写操作
    half_window = timedelta(minutes=settings.session_idle_minutes / 2)
    if idle_deadline - now < half_window:
        session_repo.extend_idle(session, row, settings.session_idle_minutes)

    return user, row


def logout(session: Session, row: UserSession) -> None:
    session_repo.revoke(session, row)
    security_repo.record_event(session, event_type="auth.logout", actor_id=row.user_id)


def change_password(session: Session, user: User, *, old_password: str, new_password: str) -> None:
    if not verify_password(old_password, user.password_hash, user.password_algo):
        raise Unauthenticated("原密码不正确")
    validate_password(new_password)
    if old_password == new_password:
        raise ValidationFailed("新密码不能与原密码相同", details={"field": "newPassword"})

    new_hash, new_algo = hash_password(new_password)
    user_repo.update_password(session, user, new_hash, new_algo)
    revoked = session_repo.revoke_all_for_user(session, user.id)
    security_repo.record_event(
        session,
        event_type="auth.password_change",
        actor_id=user.id,
        reason=f"revoked={revoked}",
    )


def _issue(
    session: Session,
    settings: Settings,
    user: User,
    *,
    ip: str | None,
    user_agent: str | None,
) -> IssuedSession:
    raw_token = random_token(32)
    row = session_repo.insert(
        session,
        token_hash=hash_token(raw_token),
        user_id=user.id,
        csrf_token=random_token(24),
        idle_minutes=settings.session_idle_minutes,
        absolute_hours=settings.session_absolute_hours,
        ip_hash=fingerprint(ip, settings.security_pepper),
        ua_hash=fingerprint(user_agent, settings.security_pepper),
    )
    return IssuedSession(
        user=user,
        csrf_token=row.csrf_token,
        raw_token=raw_token,
        cookie_max_age=settings.session_absolute_hours * 3600,
    )


def _assert_not_locked(session: Session, attempt_key: str) -> None:
    row = security_repo.get_attempt(session, attempt_key)
    if row is None or row.locked_until is None:
        return
    if parse_iso(row.locked_until) > utc_now():
        retry_after = int((parse_iso(row.locked_until) - utc_now()).total_seconds())
        raise RateLimited(
            "登录尝试过于频繁，请稍后再试", details={"retryAfterSeconds": max(1, retry_after)}
        )


def _on_failure(
    session: Session,
    settings: Settings,
    attempt_key: str,
    *,
    ip: str | None,
    user_agent: str | None,
    user_id: str | None,
) -> None:
    security_repo.bump_attempt(
        session, attempt_key, limit=LOGIN_FAIL_LIMIT, lock_minutes=LOGIN_LOCK_MINUTES
    )
    security_repo.record_event(
        session,
        event_type="auth.login_failed",
        result="fail",
        actor_id=user_id,
        ip_hash=fingerprint(ip, settings.security_pepper),
        ua_hash=fingerprint(user_agent, settings.security_pepper),
    )
    # 失败路径没有业务写入，这里必须显式提交：否则随异常一起回滚，
    # 失败计数永远不涨，锁定就形同虚设。
    session.commit()


def _persist_then_raise(session: Session, error: Exception) -> NoReturn:
    """同上：吊销会话、写审计之后再抛错，需要先落盘。"""
    session.commit()
    raise error


def _dummy_hash() -> str:
    """账号不存在时用来消耗同等 CPU 的假哈希（进程内只算一次）。"""
    return _DUMMY_HASH


def _build_dummy_hash() -> str:
    digest, _algo = hash_password("timing-equalization-placeholder")
    return digest


_DUMMY_HASH = _build_dummy_hash()
