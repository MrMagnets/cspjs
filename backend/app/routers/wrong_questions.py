"""错题本路由：错题列表、错因标记、重做复习（间隔 1/3/7 天，连续答对两次掌握）。"""
from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from database import get_db
from deps import get_current_user
from models import Problem, SubQuestion, User, WrongQuestion, WrongReview
from schemas import WrongErrorTypeIn, WrongQuestionOut, WrongReviewIn
from services import MASTER_AFTER_CONSECUTIVE_PASS, apply_review_result

router = APIRouter(prefix="/wrong-questions", tags=["错题本"])


def _to_out(db: Session, wrong: WrongQuestion) -> WrongQuestionOut:
    problem = wrong.problem
    sq = wrong.sub_question
    review_count = db.scalar(
        select(func.count()).select_from(WrongReview).where(WrongReview.wrong_id == wrong.id)
    ) or 0
    return WrongQuestionOut(
        id=wrong.id,
        problem_id=wrong.problem_id,
        problem_title=problem.title if problem else "",
        problem_type=problem.type if problem else "",
        sub_question_id=wrong.sub_question_id,
        sub_question_order=sq.order_no if sq else 0,
        sub_question_content=sq.content_md if sq else "",
        error_type=wrong.error_type,
        redo_status=wrong.redo_status,
        consecutive_pass=wrong.consecutive_pass,
        next_review_at=wrong.next_review_at,
        created_at=wrong.created_at,
        review_count=review_count,
    )


def _get_owned(db: Session, wrong_id: int, user: User) -> WrongQuestion:
    wrong = db.get(WrongQuestion, wrong_id)
    if wrong is None:
        raise HTTPException(status_code=404, detail="错题不存在")
    if wrong.user_id != user.id:
        raise HTTPException(status_code=403, detail="无权访问他人的错题")
    return wrong


@router.get("/today-count")
def today_count(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    now = datetime.now(timezone.utc)
    due = db.scalar(
        select(func.count())
        .select_from(WrongQuestion)
        .where(
            WrongQuestion.user_id == user.id,
            WrongQuestion.consecutive_pass < MASTER_AFTER_CONSECUTIVE_PASS,
            WrongQuestion.next_review_at.is_not(None),
            WrongQuestion.next_review_at <= now,
        )
    ) or 0
    total = db.scalar(
        select(func.count()).select_from(WrongQuestion).where(WrongQuestion.user_id == user.id)
    ) or 0
    mastered = db.scalar(
        select(func.count())
        .select_from(WrongQuestion)
        .where(
            WrongQuestion.user_id == user.id,
            WrongQuestion.consecutive_pass >= MASTER_AFTER_CONSECUTIVE_PASS,
        )
    ) or 0
    return {"due": due, "total": total, "mastered": mastered}


@router.get("", response_model=list[WrongQuestionOut])
def list_wrong_questions(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
    scope: str = Query("due", description="due=待复习 / all / mastered"),
    limit: int = Query(100, ge=1, le=200),
):
    now = datetime.now(timezone.utc)
    stmt = select(WrongQuestion).where(WrongQuestion.user_id == user.id)
    if scope == "due":
        stmt = stmt.where(
            WrongQuestion.consecutive_pass < MASTER_AFTER_CONSECUTIVE_PASS,
            WrongQuestion.next_review_at.is_not(None),
            WrongQuestion.next_review_at <= now,
        ).order_by(WrongQuestion.next_review_at.asc())
    elif scope == "mastered":
        stmt = stmt.where(WrongQuestion.consecutive_pass >= MASTER_AFTER_CONSECUTIVE_PASS).order_by(
            WrongQuestion.created_at.desc()
        )
    else:
        stmt = stmt.order_by(WrongQuestion.created_at.desc(), WrongQuestion.id.asc())
    rows = db.scalars(stmt.limit(limit)).all()
    return [_to_out(db, w) for w in rows]


@router.get("/{wrong_id}", response_model=WrongQuestionOut)
def get_wrong_question(
    wrong_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)
):
    return _to_out(db, _get_owned(db, wrong_id, user))


@router.patch("/{wrong_id}", response_model=WrongQuestionOut)
def set_error_type(
    wrong_id: int,
    payload: WrongErrorTypeIn,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    wrong = _get_owned(db, wrong_id, user)
    wrong.error_type = payload.error_type
    db.commit()
    db.refresh(wrong)
    return _to_out(db, wrong)


@router.post("/{wrong_id}/review", response_model=WrongQuestionOut)
def review_wrong_question(
    wrong_id: int,
    payload: WrongReviewIn,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    wrong = _get_owned(db, wrong_id, user)
    redo_status, consecutive_pass, next_review_at, _mastered = apply_review_result(
        review_result=payload.review_result, consecutive_pass=wrong.consecutive_pass
    )
    wrong.redo_status = redo_status
    wrong.consecutive_pass = consecutive_pass
    wrong.next_review_at = next_review_at
    db.add(WrongReview(wrong_id=wrong.id, review_result=payload.review_result))
    db.commit()
    db.refresh(wrong)
    return _to_out(db, wrong)


@router.delete("/{wrong_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_wrong_question(
    wrong_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)
):
    wrong = _get_owned(db, wrong_id, user)
    db.delete(wrong)
    db.commit()


@router.get("/{wrong_id}/detail")
def wrong_question_detail(
    wrong_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)
):
    """重做时需要完整题干与选项（含正确答案，用于前端判分后调用 review）。"""
    wrong = _get_owned(db, wrong_id, user)
    problem = db.get(Problem, wrong.problem_id)
    sq = db.get(SubQuestion, wrong.sub_question_id)
    if problem is None or sq is None:
        raise HTTPException(status_code=404, detail="题目已被删除")
    return {
        "wrong_id": wrong.id,
        "problem_id": problem.id,
        "problem_title": problem.title,
        "problem_content_md": problem.content_md,
        "sub_question": {
            "id": sq.id,
            "order_no": sq.order_no,
            "content_md": sq.content_md,
            "options": sq.options_json or [],
            "correct_answer": sq.correct_answer,
            "analysis_md": sq.analysis_md,
        },
        "error_type": wrong.error_type,
        "consecutive_pass": wrong.consecutive_pass,
    }
