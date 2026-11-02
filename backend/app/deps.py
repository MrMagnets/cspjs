"""FastAPI 依赖：JWT 认证 + 角色 / 封禁校验。"""
from __future__ import annotations

from datetime import datetime, timezone

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from database import get_db
from models import User
from security import decode_access_token

bearer_scheme = HTTPBearer(auto_error=False)


def _load_user(credentials: HTTPAuthorizationCredentials | None, db: Session) -> User | None:
    if credentials is None:
        return None
    payload = decode_access_token(credentials.credentials)
    if not payload or not payload.get("sub"):
        return None
    return db.get(User, int(payload["sub"]))


def _clear_expired_ban(user: User, db: Session) -> None:
    """封禁到期自动恢复，避免用户永远停留在 banned 状态。"""
    if user.status != "banned":
        return
    if user.ban_until is not None and user.ban_until <= datetime.now(timezone.utc):
        user.status = "normal"
        user.ban_until = None
        db.commit()


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    db: Session = Depends(get_db),
) -> User:
    if credentials is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="未登录或登录已过期")
    user = _load_user(credentials, db)
    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="用户不存在")
    _clear_expired_ban(user, db)
    if user.role != "admin" and user.status == "banned":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="您的账号已被封禁，可前往申诉中心提交录像申诉",
        )
    return user


def get_current_user_lenient(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    db: Session = Depends(get_db),
) -> User:
    """仅用于 /auth/me 等需要展示封禁状态的接口，不拦截 banned。"""
    if credentials is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="未登录或登录已过期")
    user = _load_user(credentials, db)
    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="用户不存在")
    _clear_expired_ban(user, db)
    return user


def get_optional_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    db: Session = Depends(get_db),
) -> User | None:
    """匿名可用接口：带了合法 token 就解析出用户，否则返回 None。"""
    return _load_user(credentials, db)


def require_admin(user: User = Depends(get_current_user)) -> User:
    if user.role != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="需要管理员权限")
    return user
