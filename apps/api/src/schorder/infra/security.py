"""密码哈希：Argon2id，失败时退回标准库 scrypt。

只做两件事：把明文变成不可逆的哈希、把明文和哈希做恒定时间比对。
账户锁定、会话、令牌都不在这里（M2 的 auth 模块负责）。
"""

from __future__ import annotations

import hashlib
import hmac
import secrets

from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerifyMismatchError

# OWASP 推荐参数：m=19MiB, t=2, p=1
_ARGON2 = PasswordHasher(time_cost=2, memory_cost=19456, parallelism=1, hash_len=32, salt_len=16)

ALGO_ARGON2 = "argon2id"
ALGO_SCRYPT = "scrypt"

SCRYPT_N = 2**15
SCRYPT_R = 8
SCRYPT_P = 1


def hash_password(password: str) -> tuple[str, str]:
    """返回 (哈希, 算法名)。算法名入库，便于日后升级参数。"""
    try:
        return _ARGON2.hash(password), ALGO_ARGON2
    except Exception:  # pragma: no cover - 只在原生依赖不可用时触发
        salt = secrets.token_bytes(16)
        digest = hashlib.scrypt(
            password.encode(), salt=salt, n=SCRYPT_N, r=SCRYPT_R, p=SCRYPT_P, dklen=32
        )
        return f"scrypt${salt.hex()}${digest.hex()}", ALGO_SCRYPT


def verify_password(password: str, stored_hash: str, algo: str) -> bool:
    if algo == ALGO_SCRYPT:
        try:
            _, salt_hex, digest_hex = stored_hash.split("$")
        except ValueError:
            return False
        digest = hashlib.scrypt(
            password.encode(),
            salt=bytes.fromhex(salt_hex),
            n=SCRYPT_N,
            r=SCRYPT_R,
            p=SCRYPT_P,
            dklen=32,
        )
        return hmac.compare_digest(digest.hex(), digest_hex)

    try:
        return _ARGON2.verify(stored_hash, password)
    except (VerifyMismatchError, InvalidHashError):
        return False


def needs_rehash(algo: str) -> bool:
    """算法不是当前的 Argon2id 时，登录成功后应重算一次。"""
    return algo != ALGO_ARGON2


def random_token(nbytes: int = 32) -> str:
    """给会话令牌用：256 位随机，URL 安全。"""
    return secrets.token_urlsafe(nbytes)


def hash_token(token: str) -> str:
    """令牌只存哈希，数据库泄露也无法直接冒用。"""
    return hashlib.sha256(token.encode()).hexdigest()


__all__ = [
    "ALGO_ARGON2",
    "ALGO_SCRYPT",
    "hash_password",
    "hash_token",
    "needs_rehash",
    "random_token",
    "verify_password",
]
