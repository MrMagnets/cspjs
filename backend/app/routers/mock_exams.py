"""模拟考试路由：按真实结构组卷（15 单选 + 3 阅读 + 2 完善）、限时 120 分钟、自动判分。"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import case, func, select
from sqlalchemy.orm import Session

from .config import settings
from .database import get_db
from .deps import get_current_user
from .models import MockExam, Problem, ProblemTag, Submission, Tag, User
from .schemas import (
    AnswerItemResult,
    MockExamCreate,
    MockExamDetail,
    MockExamProblem,
    MockExamResult,
    MockExamSubmitIn,
    MockExamSummary,
    ProblemDetail,
    SubQuestionPublic,
    TagStat,
    TypeStat,
)
from .serializers import to_details
from .services import MOCK_STRUCTURE, is_correct, mock_exam_plan

router = APIRouter(prefix="/mock-exams", tags=["模拟考试"])


def _deadline(exam: MockExam) -> datetime:
    return exam.started_at + timedelta(minutes=settings.mock_exam_minutes)


def _summary(exam: MockExam, problem_count: int | None = None) -> MockExamSummary:
    now = datetime.now(timezone.utc)
    deadline = _deadline(exam)
    remaining = max(0, int((deadline - now).total_seconds())) if exam.status == "ongoing" else None
    return MockExamSummary(
        id=exam.id,
        exam_type=exam.exam_type,
        status=exam.status,
        score=exam.score,
        started_at=exam.started_at,
        submitted_at=exam.submitted_at,
        problem_count=problem_count if problem_count is not None else len(exam.problem_ids or []),
        deadline_at=deadline if exam.status == "ongoing" else None,
        remaining_seconds=remaining,
    )


def _get_owned(db: Session, exam_id: int, user: User) -> MockExam:
    exam = db.get(MockExam, exam_id)
    if exam is None:
        raise HTTPException(status_code=404, detail="模拟考试不存在")
    if exam.user_id != user.id:
        raise HTTPException(status_code=403, detail="无权访问他人的模拟考试")
    return exam


def _load_problems(db: Session, exam: MockExam) -> list[Problem]:
    ids = [int(i) for i in (exam.problem_ids or [])]
    rows = db.scalars(select(Problem).where(Problem.id.in_(ids))).unique().all()
    by_id = {p.id: p for p in rows}
    return [by_id[i] for i in ids if i in by_id]


def _points_by_problem(exam: MockExam) -> dict[int, float]:
    """按组卷顺序（exam.problem_ids）还原每题分值：单选 2 分 ×15，阅读 13/13/14，完善 15/15。

    以 problem_ids 的顺序为准而不是"当前仍存在的题目"，即使考卷中有题目被删除，
    其余题目的分值也不会错位。
    """
    plan = mock_exam_plan()
    points: dict[int, float] = {}
    for idx, raw_id in enumerate(exam.problem_ids or []):
        points[int(raw_id)] = plan[idx][1] if idx < len(plan) else 0.0
    return points


@router.post("", response_model=MockExamDetail, status_code=status.HTTP_201_CREATED)
def create_mock_exam(
    payload: MockExamCreate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    picked: dict[str, list[Problem]] = {}
    missing: list[str] = []
    labels = {"single": "单选题", "reading": "阅读程序题", "completion": "完善程序题"}
    for ptype, need in MOCK_STRUCTURE.items():
        rows = db.scalars(
            select(Problem)
            .where(Problem.status == "approved", Problem.type == ptype)
            .order_by(func.random())
            .limit(need)
        ).unique().all()
        if len(rows) < need:
            missing.append(f"{labels[ptype]} 需要 {need} 道，题库仅有 {len(rows)} 道")
        picked[ptype] = rows
    if missing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="题库数量不足，无法组卷：" + "；".join(missing) + "。请先通过审核补充题目。",
        )

    ordered = picked["single"] + picked["reading"] + picked["completion"]
    exam = MockExam(user_id=user.id, exam_type=payload.exam_type, problem_ids=[p.id for p in ordered])
    db.add(exam)
    db.commit()
    db.refresh(exam)
    return _detail(db, exam)


def _detail(db: Session, exam: MockExam) -> MockExamDetail:
    problems = _load_problems(db, exam)
    summary = _summary(exam, len(problems))
    return MockExamDetail(
        **summary.model_dump(),
        problems=[
            MockExamProblem(
                id=p.id,
                title=p.title,
                type=p.type,
                content_md=p.content_md,
                sub_questions=[
                    SubQuestionPublic(
                        id=sq.id, order_no=sq.order_no, content_md=sq.content_md, options=sq.options_json or []
                    )
                    for sq in p.sub_questions
                ],
            )
            for p in problems
        ],
        answers={} if exam.status == "ongoing" else (exam.answers_json or {}),
    )


@router.get("", response_model=list[MockExamSummary])
def list_my_exams(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
    limit: int = 20,
):
    rows = db.scalars(
        select(MockExam).where(MockExam.user_id == user.id).order_by(MockExam.started_at.desc()).limit(limit)
    ).all()
    return [_summary(e) for e in rows]


@router.get("/{exam_id}", response_model=MockExamDetail)
def get_mock_exam(
    exam_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)
):
    return _detail(db, _get_owned(db, exam_id, user))


@router.post("/{exam_id}/submit", response_model=MockExamResult)
def submit_mock_exam(
    exam_id: int,
    payload: MockExamSubmitIn,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    exam = _get_owned(db, exam_id, user)
    if exam.status != "ongoing":
        raise HTTPException(status_code=400, detail="该场考试已交卷")

    problems = _load_problems(db, exam)
    points = _points_by_problem(exam)
    answers = {str(k): (v or "").strip().upper() for k, v in (payload.answers or {}).items()}

    items: list[AnswerItemResult] = []
    typed_items: list[tuple[str, AnswerItemResult]] = []
    total_score = 0.0
    details: list[ProblemDetail] = []
    now = datetime.now(timezone.utc)

    for problem in problems:
        problem_points = points.get(problem.id, 0.0)
        subs = list(problem.sub_questions)
        per_sub = problem_points / len(subs) if subs else 0.0
        for sq in subs:
            user_answer = answers.get(str(sq.id), "")
            ok = is_correct(user_answer, sq.correct_answer)
            if ok:
                total_score += per_sub
            db.add(
                Submission(
                    user_id=user.id,
                    problem_id=problem.id,
                    sub_question_id=sq.id,
                    user_answer=user_answer,
                    is_correct=ok,
                    mock_exam_id=exam.id,
                    submitted_at=now,
                )
            )
            item = AnswerItemResult(
                sub_question_id=sq.id,
                order_no=sq.order_no,
                user_answer=user_answer,
                correct_answer=sq.correct_answer,
                is_correct=ok,
                analysis_md=sq.analysis_md,
            )
            items.append(item)
            typed_items.append((problem.type, item))
        details.append(to_details(db, problem, include_answers=True))

    exam.status = "submitted"
    exam.submitted_at = now
    exam.answers_json = answers
    exam.score = int(round(total_score))
    db.commit()
    db.refresh(exam)

    # 题型维度得分率（按小题计）
    by_type: list[TypeStat] = []
    for ptype in ("single", "reading", "completion"):
        sel = [it for ptype_, it in typed_items if ptype_ == ptype]
        if not sel:
            continue
        correct = sum(1 for it in sel if it.is_correct)
        by_type.append(
            TypeStat(type=ptype, total=len(sel), correct=correct, accuracy=round(correct / len(sel), 4))
        )

    # 知识点维度得分率
    tag_rows = db.execute(
        select(Tag.name, func.count(Submission.id), func.sum(case((Submission.is_correct.is_(True), 1), else_=0)))
        .select_from(Submission)
        .join(ProblemTag, ProblemTag.problem_id == Submission.problem_id)
        .join(Tag, Tag.id == ProblemTag.tag_id)
        .where(Submission.mock_exam_id == exam.id, Tag.category == "知识点")
        .group_by(Tag.name)
    ).all()
    by_tag = [
        TagStat(name=name, total=cnt, correct=int(ok or 0), accuracy=round(int(ok or 0) / cnt, 4))
        for name, cnt, ok in tag_rows
    ]

    duration = int((exam.submitted_at - exam.started_at).total_seconds()) if exam.submitted_at else None
    return MockExamResult(
        **_summary(exam, len(problems)).model_dump(),
        problems=details,
        answers=answers,
        items=items,
        by_type=by_type,
        by_tag=by_tag,
        duration_seconds=duration,
    )

@router.get("/{exam_id}/result", response_model=MockExamResult)
def mock_exam_result(
    exam_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)
):
    exam = _get_owned(db, exam_id, user)
    if exam.status != "submitted":
        raise HTTPException(status_code=400, detail="考试尚未交卷")
    problems = _load_problems(db, exam)
    answers = {str(k): v for k, v in (exam.answers_json or {}).items()}

    items: list[AnswerItemResult] = []
    typed_items: list[tuple[str, AnswerItemResult]] = []
    details: list[ProblemDetail] = []
    for problem in problems:
        for sq in problem.sub_questions:
            user_answer = answers.get(str(sq.id), "")
            item = AnswerItemResult(
                sub_question_id=sq.id,
                order_no=sq.order_no,
                user_answer=user_answer,
                correct_answer=sq.correct_answer,
                is_correct=is_correct(user_answer, sq.correct_answer),
                analysis_md=sq.analysis_md,
            )
            items.append(item)
            typed_items.append((problem.type, item))
        details.append(to_details(db, problem, include_answers=True))

    by_type: list[TypeStat] = []
    for ptype in ("single", "reading", "completion"):
        sel = [it for ptype_, it in typed_items if ptype_ == ptype]
        if not sel:
            continue
        correct = sum(1 for it in sel if it.is_correct)
        by_type.append(
            TypeStat(type=ptype, total=len(sel), correct=correct, accuracy=round(correct / len(sel), 4))
        )

    tag_rows = db.execute(
        select(Tag.name, func.count(Submission.id), func.sum(case((Submission.is_correct.is_(True), 1), else_=0)))
        .select_from(Submission)
        .join(ProblemTag, ProblemTag.problem_id == Submission.problem_id)
        .join(Tag, Tag.id == ProblemTag.tag_id)
        .where(Submission.mock_exam_id == exam.id, Tag.category == "知识点")
        .group_by(Tag.name)
    ).all()
    by_tag = [
        TagStat(name=name, total=cnt, correct=int(ok or 0), accuracy=round(int(ok or 0) / cnt, 4))
        for name, cnt, ok in tag_rows
    ]
    duration = int((exam.submitted_at - exam.started_at).total_seconds()) if exam.submitted_at else None
    return MockExamResult(
        **_summary(exam, len(problems)).model_dump(),
        problems=details,
        answers=answers,
        items=items,
        by_type=by_type,
        by_tag=by_tag,
        duration_seconds=duration,
    )
