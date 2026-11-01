"""密码哈希与 JWT。

需求指定密码使用 SHA-256 存储：此处所有密码相关逻辑都收敛在 hash_password() /
verify_password()，日后替换为 bcrypt/argon2 只需改这两个函数。
"""
from __future__ import annotations

import hashlib
import hmac
from datetime import datetime, timedelta, timezone

from jose import JWTError, jwt

from config import settings


def hash_password(raw_password: str) -> str:
    """SHA-256(password) 的 64 位小写十六进制字符串，正好对应 password_hash char(64)。"""
    return hashlib.sha256(raw_password.encode("utf-8")).hexdigest()


def verify_password(raw_password: str, password_hash: str) -> bool:
    return hmac.compare_digest(hash_password(raw_password), password_hash or "")


def create_access_token(subject: str | int, role: str, expires_minutes: int | None = None) -> str:
    expire = datetime.now(timezone.utc) + timedelta(
        minutes=expires_minutes if expires_minutes is not None else settings.jwt_expire_minutes
    )
    payload = {"sub": str(subject), "role": role, "exp": expire, "iat": datetime.now(timezone.utc)}
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def decode_access_token(token: str) -> dict | None:
    try:
        return jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
    except JWTError:
        return None
