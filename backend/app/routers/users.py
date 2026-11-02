"""用户 / 排行榜 / 管理员用户管理。"""
from __future__ import annotations

import re
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from database import get_db
from deps import get_current_user, require_admin
from models import Submission, User
from schemas import (
    ChangeUsernameIn,
    ChangeUsernameOut,
    CreatePermissionIn,
    RankingEntry,
    UserOut,
    UserPage,
)

router = APIRouter(tags=["用户"])


@router.get("/rankings", response_model=list[RankingEntry])
def rankings(db: Session = Depends(get_db), limit: int = Query(50, ge=1, le=200)):
    """按小猴值排行；一次性聚合做题数，避免逐用户查询（N+1）。"""
    solved_subq = (
        select(Submission.user_id, func.count(func.distinct(Submission.problem_id)).label("solved"))
        .where(Submission.is_correct.is_(True), Submission.mock_exam_id.is_(None))
        .group_by(Submission.user_id)
        .subquery()
    )
    rows = db.execute(
        select(User, func.coalesce(solved_subq.c.solved, 0))
        .outerjoin(solved_subq, solved_subq.c.user_id == User.id)
        .where(User.status != "banned")
        .order_by(User.monkey_score.desc(), User.id.asc())
        .limit(limit)
    ).all()
    return [
        RankingEntry(
            rank=idx,
            user_id=user.id,
            username=user.username,
            title=user.title,
            monkey_score=user.monkey_score,
            credit_score=user.credit_score,
            status=user.status,
            solved_count=int(solved),
        )
        for idx, (user, solved) in enumerate(rows, start=1)
    ]


@router.put("/users/change-name", response_model=ChangeUsernameOut)
def change_username(
    payload: ChangeUsernameIn,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """修改用户名：普通用户 30 天冷却，管理员不受限制。"""
    new_username = payload.new_username.strip()
    if not 3 <= len(new_username) <= 20:
        raise HTTPException(status_code=400, detail="用户名长度需为 3–20 个字符")
    if not re.fullmatch(r"[A-Za-z0-9_\u4e00-\u9fa5-]+", new_username):
        raise HTTPException(status_code=400, detail="用户名只能包含中文、字母、数字、下划线或短横线")
    if new_username == user.username:
        raise HTTPException(status_code=400, detail="新用户名与当前用户名相同")

    exists = db.scalar(select(User).where(User.username == new_username, User.id != user.id))
    if exists is not None:
        raise HTTPException(status_code=400, detail="用户名已被占用")

    now = datetime.now(timezone.utc)
    if user.role != "admin" and user.last_username_change is not None:
        last = user.last_username_change
        if last.tzinfo is None:
            last = last.replace(tzinfo=timezone.utc)
        if now - last < timedelta(days=30):
            raise HTTPException(
                status_code=400,
                detail="修改失败：30天内只能修改一次用户名",
            )

    user.username = new_username
    user.last_username_change = now
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=400, detail="用户名已被占用") from None
    db.refresh(user)
    return ChangeUsernameOut(message="用户名修改成功", user=UserOut.model_validate(user))


@router.get("/users/{user_id}", response_model=UserOut)
def public_profile(user_id: int, db: Session = Depends(get_db)):
    user = db.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="用户不存在")
    return UserOut.model_validate(user)


@router.get("/admin/users", response_model=UserPage)
def admin_users(
    search: str = "",
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
):
    stmt = select(User)
    if search.strip():
        kw = f"%{search.strip()}%"
        stmt = stmt.where(or_(User.username.ilike(kw), User.title.ilike(kw)))
    total = db.scalar(select(func.count()).select_from(stmt.subquery())) or 0
    users = db.scalars(
        stmt.order_by(User.status.desc(), User.id.desc()).offset((page - 1) * page_size).limit(page_size)
    ).all()
    return UserPage(
        items=[UserOut.model_validate(u) for u in users],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.post("/admin/users/{user_id}/unban", response_model=UserOut)
def unban_user(
    user_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
):
    user = db.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="用户不存在")
    user.status = "normal"
    user.ban_until = None
    user.title = ""
    user.credit_score = 100  # 解封直接恢复满分信用
    user.can_create_problem = True
    db.commit()
    db.refresh(user)
    return UserOut.model_validate(user)


@router.post("/admin/users/{user_id}/toggle-create-problem", response_model=UserOut)
def toggle_create_problem(
    user_id: int,
    payload: CreatePermissionIn,
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
):
    user = db.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="用户不存在")
    user.can_create_problem = payload.can_create_problem
    db.commit()
    db.refresh(user)
    return UserOut.model_validate(user)


@router.post("/admin/users/{user_id}/ban", response_model=UserOut)
def ban_user(
    user_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
):
    user = db.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="用户不存在")
    user.status = "banned"
    user.credit_score = 50
    user.title = "棕名"
    user.can_create_problem = False
    db.commit()
    db.refresh(user)
    return UserOut.model_validate(user)
