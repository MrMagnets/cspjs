"""申诉中心：用户提交录像，管理员审核。"""
from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from database import get_db
from deps import get_current_user, get_current_user_lenient, require_admin
from models import Appeal, Contest, ContestResult, User
from schemas import AppealIn, AppealOut, AppealReviewIn

router = APIRouter(tags=["申诉"])


def _out(appeal: Appeal) -> AppealOut:
    return AppealOut(
        id=appeal.id,
        user_id=appeal.user_id,
        username=appeal.user.username if appeal.user else "",
        contest_id=appeal.contest_id,
        reason=appeal.reason,
        video_url=appeal.video_url,
        status=appeal.status,
        admin_note=appeal.admin_note,
        created_at=appeal.created_at,
        reviewed_at=appeal.reviewed_at,
    )


@router.post("/appeals", response_model=AppealOut, status_code=201)
def create_appeal(
    payload: AppealIn,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user_lenient),
):
    if not payload.video_url.startswith(("http://", "https://")):
        raise HTTPException(status_code=400, detail="录像链接必须以 http(s):// 开头")
    if payload.contest_id is not None and db.get(Contest, payload.contest_id) is None:
        raise HTTPException(status_code=404, detail="比赛不存在")
    appeal = Appeal(
        user_id=user.id,
        contest_id=payload.contest_id,
        reason=payload.reason,
        video_url=payload.video_url,
        status="pending",
    )
    db.add(appeal)
    db.commit()
    db.refresh(appeal)
    return _out(appeal)


@router.get("/appeals/me", response_model=list[AppealOut])
def my_appeals(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user_lenient),
):
    rows = db.scalars(select(Appeal).where(Appeal.user_id == user.id).order_by(Appeal.created_at.desc())).all()
    return [_out(a) for a in rows]


@router.get("/admin/appeals", response_model=list[AppealOut])
def all_appeals(
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
):
    rows = db.scalars(select(Appeal).order_by(Appeal.status.asc(), Appeal.created_at.desc())).all()
    return [_out(a) for a in rows]


@router.post("/admin/appeals/{appeal_id}/review", response_model=AppealOut)
def review_appeal(
    appeal_id: int,
    payload: AppealReviewIn,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
):
    appeal = db.get(Appeal, appeal_id)
    if appeal is None:
        raise HTTPException(status_code=404, detail="申诉不存在")
    if appeal.status != "pending":
        raise HTTPException(status_code=400, detail="该申诉已处理")
    appeal.status = "approved" if payload.action == "approve" else "rejected"
    appeal.admin_id = admin.id
    appeal.admin_note = payload.note
    appeal.reviewed_at = datetime.now(timezone.utc)

    if payload.action == "approve":
        target = db.get(User, appeal.user_id)
        if target is not None:
            target.status = "normal"
            target.ban_until = None
            target.credit_score = 100
            target.title = ""
            target.can_create_problem = True
        if appeal.contest_id is not None:
            result = db.scalar(
                select(ContestResult).where(
                    ContestResult.contest_id == appeal.contest_id,
                    ContestResult.user_id == appeal.user_id,
                )
            )
            if result is not None and result.status == "cheating":
                result.status = "submitted"
    db.commit()
    db.refresh(appeal)
    return _out(appeal)
