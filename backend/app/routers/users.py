"""用户 / 排行榜 / 管理员用户管理 / 头像 / 改名。"""
from __future__ import annotations

import re
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from routers.audit import log_action
from database import get_db
from deps import get_current_user, require_admin
from models import Submission, User
from schemas import (
    AvatarIn,
    AvatarReviewIn,
    ChangeUsernameIn,
    ChangeUsernameOut,
    CreatePermissionIn,
    RankingEntry,
    TitleIn,
    UserOut,
    UserPage,
)

router = APIRouter(tags=["用户"])


@router.get("/rankings", response_model=list[RankingEntry])
def rankings(db: Session = Depends(get_db), limit: int = Query(50, ge=1, le=200)):
    """按小猴值排行；一次性聚合做题数，避免逐用户查询。"""
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
            role=user.role,
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
            raise HTTPException(status_code=400, detail="修改失败：30天内只能修改一次用户名")

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
    admin: User = Depends(require_admin),
):
    user = db.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="用户不存在")

    user.status = "normal"
    user.ban_until = None
    cleaned = (user.title or "")
    for word in ("作弊者", "作弊", "棕名"):
        cleaned = cleaned.replace(word, "")
    user.title = cleaned.strip()
    user.credit_score = 100
    user.can_create_problem = True
    log_action(db, admin, "unban_user", "user", user.id, "解封并恢复信用分 100")

    try:
        db.commit()
    except Exception as exc:  # noqa: BLE001 - 解封失败不能静默
        db.rollback()
        raise HTTPException(status_code=500, detail="解封失败，请稍后重试") from exc
    db.refresh(user)
    return UserOut.model_validate(user)


@router.post("/admin/users/{user_id}/toggle-create-problem", response_model=UserOut)
def toggle_create_problem(
    user_id: int,
    payload: CreatePermissionIn,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
):
    user = db.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="用户不存在")
    if user.role == "admin":
        raise HTTPException(status_code=400, detail="不能限制管理员账号")
    user.can_create_problem = payload.can_create_problem
    log_action(db, admin, "toggle_create_problem", "user", user.id, f"出题权限={payload.can_create_problem}")
    db.commit()
    db.refresh(user)
    return UserOut.model_validate(user)


@router.post("/admin/users/{user_id}/title", response_model=UserOut)
def set_user_title(
    user_id: int,
    payload: TitleIn,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
):
    """授予 / 修改 / 清空用户称号（如：金牌选手、优秀出题人）。"""
    user = db.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="用户不存在")
    user.title = payload.title.strip()
    log_action(db, admin, "set_title", "user", user.id, f"称号={user.title or '（清空）'}")
    db.commit()
    db.refresh(user)
    return UserOut.model_validate(user)


@router.post("/admin/users/{user_id}/ban", response_model=UserOut)
def ban_user(
    user_id: int,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
):
    user = db.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="用户不存在")
    if user.role == "admin":
        raise HTTPException(status_code=400, detail="不能封禁管理员账号")
    user.status = "banned"
    user.credit_score = 50
    user.title = "作弊者"
    user.can_create_problem = False
    log_action(db, admin, "ban_user", "user", user.id, "严重封禁：信用分 50 / 作弊者")
    try:
        db.commit()
    except Exception as exc:  # noqa: BLE001
        db.rollback()
        raise HTTPException(status_code=500, detail="封禁失败，请稍后重试") from exc
    db.refresh(user)
    return UserOut.model_validate(user)


# --------------------------------------------------------------------------- 头像
@router.put("/users/avatar", response_model=UserOut)
def update_avatar(
    payload: AvatarIn,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    if not payload.avatar_url.startswith(("http://", "https://")):
        raise HTTPException(status_code=400, detail="头像链接必须以 http(s):// 开头")
    user.avatar_url = payload.avatar_url
    user.avatar_status = "approved" if user.role == "admin" else "pending"
    db.commit()
    db.refresh(user)
    return UserOut.model_validate(user)


@router.get("/admin/avatars", response_model=list[UserOut])
def pending_avatars(
    avatar_status: str = Query("pending", alias="status"),
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
):
    stmt = select(User).where(User.avatar_url.is_not(None))
    if avatar_status in ("pending", "approved", "rejected"):
        stmt = stmt.where(User.avatar_status == avatar_status)
    return [UserOut.model_validate(u) for u in db.scalars(stmt.order_by(User.id.desc())).all()]


@router.post("/admin/avatars/{user_id}/review", response_model=UserOut)
def review_avatar(
    user_id: int,
    payload: AvatarReviewIn,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
):
    user = db.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="用户不存在")
    user.avatar_status = "approved" if payload.action == "approve" else "rejected"
    log_action(db, admin, "avatar_review", "user", user.id, f"头像审核：{user.avatar_status}")
    db.commit()
    db.refresh(user)
    return UserOut.model_validate(user)
