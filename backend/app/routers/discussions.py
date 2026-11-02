"""讨论区 / 评论 / 举报。"""
from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from database import get_db
from deps import get_current_user, require_admin
from models import Comment, Discussion, Problem, Report, User
from schemas import (
    CommentIn,
    CommentOut,
    DiscussionDetail,
    DiscussionIn,
    DiscussionSummary,
    ReportIn,
    ReportOut,
)

router = APIRouter(tags=["讨论"])


def _summary(discussion: Discussion, comment_count: int | None = None) -> DiscussionSummary:
    return DiscussionSummary(
        id=discussion.id,
        title=discussion.title,
        category=discussion.category,
        author_id=discussion.author_id,
        author_name=discussion.author.username if discussion.author else "已注销用户",
        is_pinned=discussion.is_pinned,
        is_locked=discussion.is_locked,
        comment_count=comment_count if comment_count is not None else len(discussion.comments),
        created_at=discussion.created_at,
        updated_at=discussion.updated_at,
    )


def _detail(discussion: Discussion) -> DiscussionDetail:
    return DiscussionDetail(
        **_summary(discussion).model_dump(),
        content_md=discussion.content_md,
        problem_id=discussion.problem_id,
        comments=[
            CommentOut(
                id=c.id,
                author_id=c.author_id,
                author_name=c.author.username if c.author else "已注销用户",
                content_md=c.content_md,
                created_at=c.created_at,
            )
            for c in discussion.comments
        ],
    )


@router.get("/discussions", response_model=list[DiscussionSummary])
def list_discussions(
    category: str | None = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=50),
    db: Session = Depends(get_db),
):
    stmt = select(Discussion).options(selectinload(Discussion.comments))
    if category in ("站务", "学术", "题目"):
        stmt = stmt.where(Discussion.category == category)
    rows = db.scalars(
        stmt.order_by(Discussion.is_pinned.desc(), Discussion.updated_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    ).all()
    return [_summary(d) for d in rows]


@router.post("/discussions", response_model=DiscussionDetail, status_code=status.HTTP_201_CREATED)
def create_discussion(
    payload: DiscussionIn,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    if payload.category == "站务" and user.role != "admin":
        raise HTTPException(status_code=403, detail="站务版仅管理员可发帖")
    if payload.problem_id is not None and db.get(Problem, payload.problem_id) is None:
        raise HTTPException(status_code=404, detail="关联题目不存在")
    discussion = Discussion(
        title=payload.title.strip(),
        content_md=payload.content_md,
        category=payload.category,
        author_id=user.id,
        problem_id=payload.problem_id,
    )
    db.add(discussion)
    db.commit()
    db.refresh(discussion)
    return _detail(discussion)


@router.get("/discussions/{discussion_id}", response_model=DiscussionDetail)
def get_discussion(discussion_id: int, db: Session = Depends(get_db)):
    discussion = db.scalars(
        select(Discussion)
        .where(Discussion.id == discussion_id)
        .options(selectinload(Discussion.comments))
    ).first()
    if discussion is None:
        raise HTTPException(status_code=404, detail="帖子不存在")
    return _detail(discussion)


@router.post("/discussions/{discussion_id}/comments", response_model=CommentOut, status_code=201)
def add_comment(
    discussion_id: int,
    payload: CommentIn,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    discussion = db.get(Discussion, discussion_id)
    if discussion is None:
        raise HTTPException(status_code=404, detail="帖子不存在")
    if discussion.is_locked:
        raise HTTPException(status_code=403, detail="帖子已被锁定")
    comment = Comment(discussion_id=discussion_id, author_id=user.id, content_md=payload.content_md)
    discussion.updated_at = datetime.now(timezone.utc)
    db.add(comment)
    db.commit()
    db.refresh(comment)
    return CommentOut(
        id=comment.id,
        author_id=comment.author_id,
        author_name=user.username,
        content_md=comment.content_md,
        created_at=comment.created_at,
    )


@router.post("/reports", response_model=ReportOut, status_code=201)
def create_report(
    payload: ReportIn,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    report = Report(
        reporter_id=user.id,
        target_type=payload.target_type,
        target_id=payload.target_id,
        reason=payload.reason,
    )
    db.add(report)
    db.commit()
    db.refresh(report)
    return ReportOut(
        id=report.id,
        reporter_id=report.reporter_id,
        reporter_name=user.username,
        target_type=report.target_type,
        target_id=report.target_id,
        reason=report.reason,
        status=report.status,
        created_at=report.created_at,
    )


@router.get("/admin/reports", response_model=list[ReportOut])
def list_reports(
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
):
    rows = db.execute(
        select(Report, User.username)
        .join(User, User.id == Report.reporter_id)
        .order_by(Report.status.asc(), Report.created_at.desc())
        .limit(200)
    ).all()
    return [
        ReportOut(
            id=r.id,
            reporter_id=r.reporter_id,
            reporter_name=name,
            target_type=r.target_type,
            target_id=r.target_id,
            reason=r.reason,
            status=r.status,
            created_at=r.created_at,
        )
        for r, name in rows
    ]


@router.post("/admin/reports/{report_id}/resolve", response_model=ReportOut)
def resolve_report(
    report_id: int,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
):
    report = db.get(Report, report_id)
    if report is None:
        raise HTTPException(status_code=404, detail="举报不存在")
    report.status = "resolved"
    report.resolved_by = admin.id
    report.resolved_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(report)
    return ReportOut(
        id=report.id,
        reporter_id=report.reporter_id,
        target_type=report.target_type,
        target_id=report.target_id,
        reason=report.reason,
        status=report.status,
        created_at=report.created_at,
    )
