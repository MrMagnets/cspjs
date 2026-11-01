"""题库路由：列表筛选、详情、投稿、编辑、审核、作答判分。"""
from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from .database import get_db
from .deps import get_current_user, get_optional_user, require_admin
from .models import Problem, ProblemTag, SubQuestion, Submission, Tag, User, WrongQuestion
from .schemas import (
    AnswerIn,
    AnswerItemResult,
    AnswerResult,
    ProblemDetail,
    ProblemIn,
    ProblemPage,
    ReviewIn,
    SubQuestionIn,
)
from .serializers import to_details, to_summary
from .services import is_correct, next_review_after_wrong

router = APIRouter(tags=["题库"])


# --------------------------------------------------------------------------- 内部工具
def _load_problem(db: Session, problem_id: int) -> Problem:
    problem = db.get(Problem, problem_id)
    if problem is None:
        raise HTTPException(status_code=404, detail="题目不存在")
    return problem


def _assert_can_view(problem: Problem, user: User | None) -> None:
    if problem.status == "approved":
        return
    if user is None or (user.role != "admin" and user.id != problem.contributor_id):
        raise HTTPException(status_code=403, detail="该题目尚未通过审核，暂不可见")


def _assert_can_edit(problem: Problem, user: User) -> None:
    if user.role == "admin":
        return
    if problem.contributor_id != user.id:
        raise HTTPException(status_code=403, detail="只能编辑自己提交的题目")
    if problem.status not in ("pending", "rejected"):
        raise HTTPException(status_code=403, detail="已通过的题目不可直接修改，如需修改请联系管理员")


def _replace_sub_questions(db: Session, problem: Problem, subs: list[SubQuestionIn]) -> None:
    for old in list(problem.sub_questions):
        db.delete(old)
    problem.sub_questions = []
    db.flush()
    for idx, item in enumerate(subs, start=1):
        problem.sub_questions.append(
            SubQuestion(
                order_no=idx,
                content_md=item.content_md,
                options_json=item.options,
                correct_answer=item.correct_answer.strip().upper(),
                analysis_md=item.analysis_md,
            )
        )


def _apply_tags(db: Session, problem: Problem, tag_ids: list[int]) -> None:
    valid_ids = set()
    if tag_ids:
        valid_ids = set(db.scalars(select(Tag.id).where(Tag.id.in_(tag_ids))).all())
    problem.tag_links = [ProblemTag(tag_id=tid) for tid in sorted(valid_ids)]


def _sub_map(problem: Problem) -> dict[int, SubQuestion]:
    return {sq.id: sq for sq in problem.sub_questions}


def _record_answer(
    db: Session,
    *,
    user: User,
    problem: Problem,
    answers: dict[str, str],
    mock_exam_id: int | None = None,
) -> AnswerResult:
    subs = _sub_map(problem)
    if not subs:
        raise HTTPException(status_code=400, detail="该题目没有小题，无法作答")

    items: list[AnswerItemResult] = []
    correct_count = 0
    wrong_ids: list[int] = []

    for sq in problem.sub_questions:
        raw = answers.get(str(sq.id))
        if raw is None:
            raw = next((v for k, v in answers.items() if str(k) == str(sq.id)), "")
        user_answer = (raw or "").strip().upper()
        ok = is_correct(user_answer, sq.correct_answer)
        correct_count += 1 if ok else 0

        db.add(
            Submission(
                user_id=user.id,
                problem_id=problem.id,
                sub_question_id=sq.id,
                user_answer=user_answer,
                is_correct=ok,
                mock_exam_id=mock_exam_id,
            )
        )

        if not ok and mock_exam_id is None and problem.status == "approved":
            wrong = db.scalar(
                select(WrongQuestion).where(
                    WrongQuestion.user_id == user.id,
                    WrongQuestion.problem_id == problem.id,
                    WrongQuestion.sub_question_id == sq.id,
                )
            )
            if wrong is None:
                wrong = WrongQuestion(
                    user_id=user.id,
                    problem_id=problem.id,
                    sub_question_id=sq.id,
                    redo_status=0,
                    consecutive_pass=0,
                    next_review_at=next_review_after_wrong(),
                )
                db.add(wrong)
                db.flush()
            else:
                wrong.redo_status = 0
                wrong.consecutive_pass = 0
                wrong.next_review_at = next_review_after_wrong()
            wrong_ids.append(wrong.id)

        items.append(
            AnswerItemResult(
                sub_question_id=sq.id,
                order_no=sq.order_no,
                user_answer=user_answer,
                correct_answer=sq.correct_answer,
                is_correct=ok,
                analysis_md=sq.analysis_md,
            )
        )

    db.commit()
    total = len(items)
    return AnswerResult(
        problem_id=problem.id,
        correct_count=correct_count,
        total_count=total,
        score_rate=round(correct_count / total, 4) if total else 0.0,
        items=items,
        wrong_question_ids=wrong_ids,
        answer_md=problem.answer_md,
    )


# --------------------------------------------------------------------------- 列表 / 详情
@router.get("/problems", response_model=ProblemPage)
def list_problems(
    db: Session = Depends(get_db),
    user: User | None = Depends(get_optional_user),
    problem_type: str | None = Query(None, alias="type", description="single/reading/completion"),
    tag: str | None = Query(None, description="标签名或标签 id"),
    source_tag: str | None = Query(None, description="original/real/adapted"),
    year: int | None = None,
    exam: str | None = Query(None, description="CSP-J / CSP-S"),
    keyword: str | None = None,
    status_filter: str | None = Query(None, alias="status", description="approved/pending/rejected/mine/all"),
    mine: bool = False,
    page: int = Query(1, ge=1),
    page_size: int = Query(12, ge=1, le=50),
):
    stmt = select(Problem)

    wanted_status = (status_filter or "approved").lower()
    if mine:
        if user is None:
            raise HTTPException(status_code=401, detail="请先登录")
        stmt = stmt.where(Problem.contributor_id == user.id)
        if wanted_status in ("approved", "pending", "rejected"):
            stmt = stmt.where(Problem.status == wanted_status)
    elif wanted_status == "approved":
        stmt = stmt.where(Problem.status == "approved")
    elif wanted_status in ("pending", "rejected"):
        if user is None:
            raise HTTPException(status_code=401, detail="请先登录")
        stmt = stmt.where(Problem.status == wanted_status)
        if user.role != "admin":
            stmt = stmt.where(Problem.contributor_id == user.id)
    elif wanted_status in ("mine", "all"):
        if user is None:
            raise HTTPException(status_code=401, detail="请先登录")
        if user.role != "admin":
            stmt = stmt.where(Problem.contributor_id == user.id)
    else:
        raise HTTPException(status_code=400, detail="不支持的 status 取值")

    if problem_type and problem_type in ("single", "reading", "completion"):
        stmt = stmt.where(Problem.type == problem_type)
    if source_tag and source_tag in ("original", "real", "adapted"):
        stmt = stmt.where(Problem.source_tag == source_tag)
    if year:
        stmt = stmt.where(Problem.source_year == year)
    if exam:
        stmt = stmt.where(Problem.source_exam == exam)
    if keyword:
        kw = f"%{keyword.strip()}%"
        stmt = stmt.where(or_(Problem.title.ilike(kw), Problem.content_md.ilike(kw)))
    if tag:
        tag_obj = db.get(Tag, int(tag)) if tag.isdigit() else db.scalar(select(Tag).where(Tag.name == tag))
        if tag_obj is None:
            return ProblemPage(items=[], total=0, page=page, page_size=page_size)
        stmt = stmt.where(
            Problem.id.in_(select(ProblemTag.problem_id).where(ProblemTag.tag_id == tag_obj.id))
        )

    total = db.scalar(select(func.count()).select_from(stmt.subquery())) or 0
    rows = db.scalars(
        stmt.order_by(Problem.created_at.desc(), Problem.id.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    ).unique().all()

    tag_cache: dict = {}
    return ProblemPage(
        items=[to_summary(db, p, tag_cache) for p in rows],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/problems/{problem_id}", response_model=ProblemDetail)
def get_problem(
    problem_id: int,
    db: Session = Depends(get_db),
    user: User | None = Depends(get_optional_user),
):
    problem = _load_problem(db, problem_id)
    _assert_can_view(problem, user)
    return to_details(db, problem, include_answers=True)


# --------------------------------------------------------------------------- 投稿 / 编辑
@router.post("/problems", response_model=ProblemDetail, status_code=status.HTTP_201_CREATED)
def create_problem(
    payload: ProblemIn,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    is_admin = user.role == "admin"
    problem = Problem(
        title=payload.title.strip(),
        type=payload.type,
        source_tag=payload.source_tag,
        source_year=payload.source_year,
        source_exam=payload.source_exam,
        content_md=payload.content_md,
        answer_md=payload.answer_md,
        status="approved" if is_admin else "pending",
        contributor_id=user.id,
        reviewer_id=user.id if is_admin else None,
        reviewed_at=datetime.now(timezone.utc) if is_admin else None,
    )
    _replace_sub_questions(db, problem, payload.sub_questions)
    _apply_tags(db, problem, payload.tag_ids)
    db.add(problem)
    db.commit()
    db.refresh(problem)
    return to_details(db, problem)


@router.put("/problems/{problem_id}", response_model=ProblemDetail)
def update_problem(
    problem_id: int,
    payload: ProblemIn,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    problem = _load_problem(db, problem_id)
    _assert_can_edit(problem, user)

    problem.title = payload.title.strip()
    problem.type = payload.type
    problem.source_tag = payload.source_tag
    problem.source_year = payload.source_year
    problem.source_exam = payload.source_exam
    problem.content_md = payload.content_md
    problem.answer_md = payload.answer_md

    if user.role != "admin" and problem.status == "rejected":
        # 驳回后修改 → 重新进入待审队列
        problem.status = "pending"
        problem.reject_reason = None
        problem.reviewer_id = None
        problem.reviewed_at = None

    _replace_sub_questions(db, problem, payload.sub_questions)
    _apply_tags(db, problem, payload.tag_ids)
    db.commit()
    db.refresh(problem)
    return to_details(db, problem)


@router.delete("/problems/{problem_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_problem(
    problem_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    problem = _load_problem(db, problem_id)
    if user.role != "admin":
        if problem.contributor_id != user.id:
            raise HTTPException(status_code=403, detail="只能删除自己提交的题目")
        if problem.status == "approved":
            raise HTTPException(status_code=403, detail="已通过的题目不可删除")
    db.delete(problem)
    db.commit()


# --------------------------------------------------------------------------- 审核
@router.post("/problems/{problem_id}/review", response_model=ProblemDetail)
def review_problem(
    problem_id: int,
    payload: ReviewIn,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
):
    problem = _load_problem(db, problem_id)
    if problem.status != "pending":
        raise HTTPException(status_code=400, detail="只有待审核的题目可以审核")

    problem.reviewer_id = admin.id
    problem.reviewed_at = datetime.now(timezone.utc)
    if payload.action == "approve":
        problem.status = "approved"
        problem.reject_reason = None
    else:
        problem.status = "rejected"
        problem.reject_reason = (payload.reason or "").strip()
        if not problem.reject_reason:
            raise HTTPException(status_code=400, detail="驳回必须填写原因")

    db.commit()
    db.refresh(problem)
    return to_details(db, problem)


@router.get("/admin/pending", response_model=ProblemPage)
def admin_pending(
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=50),
):
    stmt = select(Problem).where(Problem.status == "pending")
    total = db.scalar(select(func.count()).select_from(stmt.subquery())) or 0
    rows = db.scalars(
        stmt.order_by(Problem.created_at.asc()).offset((page - 1) * page_size).limit(page_size)
    ).unique().all()
    tag_cache: dict = {}
    return ProblemPage(
        items=[to_summary(db, p, tag_cache) for p in rows], total=total, page=page, page_size=page_size
    )


# --------------------------------------------------------------------------- 作答
@router.post("/problems/{problem_id}/answer", response_model=AnswerResult)
def answer_problem(
    problem_id: int,
    payload: AnswerIn,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    problem = _load_problem(db, problem_id)
    _assert_can_view(problem, user)
    return _record_answer(db, user=user, problem=problem, answers=payload.answers)


@router.get("/problems/{problem_id}/submissions", response_model=list[AnswerItemResult])
def my_problem_submissions(
    problem_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    rows = db.execute(
        select(Submission, SubQuestion)
        .join(SubQuestion, SubQuestion.id == Submission.sub_question_id)
        .where(
            Submission.user_id == user.id,
            Submission.problem_id == problem_id,
            Submission.mock_exam_id.is_(None),
        )
        .order_by(Submission.submitted_at.desc())
    ).all()
    return [
        AnswerItemResult(
            sub_question_id=sq.id,
            order_no=sq.order_no,
            user_answer=sub.user_answer,
            correct_answer=sq.correct_answer,
            is_correct=sub.is_correct,
            analysis_md=sq.analysis_md,
        )
        for sub, sq in rows
    ]
