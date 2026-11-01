"""做题统计路由：知识点 / 题型维度聚合（仅统计普通练习，不含模拟考试）。"""
from __future__ import annotations

from datetime import datetime, time, timezone

from fastapi import APIRouter, Depends
from sqlalchemy import case, func, select
from sqlalchemy.orm import Session

from .database import get_db
from .deps import get_current_user
from .models import Problem, ProblemTag, Submission, Tag, User, WrongQuestion
from .schemas import StatsOut, TagStat, TypeStat
from .services import MASTER_AFTER_CONSECUTIVE_PASS

router = APIRouter(prefix="/stats", tags=["统计"])


@router.get("/me", response_model=StatsOut)
def my_stats(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    base = (
        select(Submission)
        .where(Submission.user_id == user.id, Submission.mock_exam_id.is_(None))
    )
    total = db.scalar(select(func.count()).select_from(base.subquery())) or 0
    correct = db.scalar(
        select(func.count())
        .select_from(Submission)
        .where(
            Submission.user_id == user.id,
            Submission.mock_exam_id.is_(None),
            Submission.is_correct.is_(True),
        )
    ) or 0

    today_start = datetime.combine(datetime.now(timezone.utc).date(), time.min, tzinfo=timezone.utc)
    today = db.scalar(
        select(func.count())
        .select_from(Submission)
        .where(
            Submission.user_id == user.id,
            Submission.mock_exam_id.is_(None),
            Submission.submitted_at >= today_start,
        )
    ) or 0

    solved = db.scalar(
        select(func.count(func.distinct(Submission.problem_id))).where(
            Submission.user_id == user.id,
            Submission.mock_exam_id.is_(None),
            Submission.is_correct.is_(True),
        )
    ) or 0

    # 知识点维度：submissions → problems → problem_tags → tags(category=知识点)
    tag_rows = db.execute(
        select(
            Tag.name,
            func.count(Submission.id),
            func.sum(case((Submission.is_correct.is_(True), 1), else_=0)),
        )
        .select_from(Submission)
        .join(Problem, Problem.id == Submission.problem_id)
        .join(ProblemTag, ProblemTag.problem_id == Problem.id)
        .join(Tag, Tag.id == ProblemTag.tag_id)
        .where(
            Submission.user_id == user.id,
            Submission.mock_exam_id.is_(None),
            Tag.category == "知识点",
        )
        .group_by(Tag.name)
        .order_by(func.count(Submission.id).desc())
    ).all()

    type_rows = db.execute(
        select(
            Problem.type,
            func.count(Submission.id),
            func.sum(case((Submission.is_correct.is_(True), 1), else_=0)),
        )
        .select_from(Submission)
        .join(Problem, Problem.id == Submission.problem_id)
        .where(Submission.user_id == user.id, Submission.mock_exam_id.is_(None))
        .group_by(Problem.type)
    ).all()

    wrong_pending = db.scalar(
        select(func.count())
        .select_from(WrongQuestion)
        .where(
            WrongQuestion.user_id == user.id,
            WrongQuestion.consecutive_pass < MASTER_AFTER_CONSECUTIVE_PASS,
        )
    ) or 0

    return StatsOut(
        total_answers=total,
        correct_answers=correct,
        accuracy=round(correct / total, 4) if total else 0.0,
        today_answers=today,
        solved_problems=solved,
        by_tag=[
            TagStat(name=name, total=cnt, correct=int(ok or 0), accuracy=round(int(ok or 0) / cnt, 4))
            for name, cnt, ok in tag_rows
        ],
        by_type=[
            TypeStat(
                type=ptype,
                total=cnt,
                correct=int(ok or 0),
                accuracy=round(int(ok or 0) / cnt, 4),
            )
            for ptype, cnt, ok in type_rows
        ],
        wrong_pending=wrong_pending,
    )
