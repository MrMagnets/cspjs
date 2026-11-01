"""认证路由：注册 / 登录 / 当前用户。

约定：
- 路由前缀只有 ``/auth``，完整路径由 main.py 的 ``/api`` 前缀拼成
  ``/api/auth/login``，这里绝对不能再写 ``/api``。
- 所有响应都用 ``JSONResponse`` 显式返回 JSON，避免 Workers/代理链路上
  出现 200 + text/plain 的情况。
"""
from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, status
from fastapi.responses import JSONResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from .database import get_db
from .deps import get_current_user
from .models import User
from .schemas import LoginIn, RegisterIn, UserOut
from .security import create_access_token, hash_password, verify_password

router = APIRouter(prefix="/auth", tags=["认证"])
logger = logging.getLogger("cspjs.auth")


def _token_response(user: User, status_code: int = status.HTTP_200_OK) -> JSONResponse:
    """统一返回 access_token + token_type + user（前端 store 需要 user）。"""
    token = create_access_token(user.id, user.role)
    user_data = UserOut.model_validate(user).model_dump(mode="json")
    return JSONResponse(
        status_code=status_code,
        content={
            "access_token": token,
            "token_type": "bearer",
            "user": user_data,
        },
    )


def _error(message: str, status_code: int) -> JSONResponse:
    return JSONResponse(status_code=status_code, content={"detail": message})


@router.post("/register")
def register(payload: RegisterIn, db: Session = Depends(get_db)):
    try:
        exists = db.scalar(select(User).where(User.username == payload.username))
        if exists:
            return _error("用户名已被占用", status.HTTP_409_CONFLICT)

        user = User(
            username=payload.username,
            password_hash=hash_password(payload.password),
            role="user",
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        return _token_response(user, status_code=status.HTTP_201_CREATED)
    except Exception:  # noqa: BLE001 - 任何数据库异常都转成 JSON，避免 Worker 崩溃
        db.rollback()
        logger.exception("注册失败 username=%s", payload.username)
        return _error("注册失败，请稍后重试", status.HTTP_500_INTERNAL_SERVER_ERROR)


@router.post("/login")
def login(payload: LoginIn, db: Session = Depends(get_db)):
    try:
        user = db.scalar(select(User).where(User.username == payload.username))
    except Exception:  # noqa: BLE001
        db.rollback()
        logger.exception("登录查询失败 username=%s", payload.username)
        return _error("服务暂时不可用，请稍后重试", status.HTTP_500_INTERNAL_SERVER_ERROR)

    if user is None:
        # 不区分“用户不存在”和“密码错误”，避免账号枚举
        return _error("用户名或密码错误", status.HTTP_401_UNAUTHORIZED)

    try:
        password_ok = verify_password(payload.password, user.password_hash)
    except Exception:  # noqa: BLE001
        logger.exception("密码校验失败 username=%s", payload.username)
        return _error("密码错误", status.HTTP_401_UNAUTHORIZED)

    if not password_ok:
        return _error("密码错误", status.HTTP_401_UNAUTHORIZED)

    return _token_response(user, status_code=status.HTTP_200_OK)


@router.get("/me", response_model=UserOut)
def me(user: User = Depends(get_current_user)):
    return UserOut.model_validate(user)
