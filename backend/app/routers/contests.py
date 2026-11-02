"""比赛：说明、列表、防切屏、交卷、管理员编辑 / 删除 / 判定。"""
from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload, selectinload

from database import get_db
from deps import get_current_user, get_optional_user, require_admin
from models import CheatLog, Contest, ContestProblem, ContestResult, Problem, Submission, User
from routers.audit import log_action
from schemas import (
    AntiCheatIn,
    ContestAnswersIn,
    ContestDetail,
    ContestIn,
    ContestJudgeIn,
    ContestProblemOut,
    ContestResultOut,
    ContestSummary,
    ContestUpdateIn,
    SubQuestionPublic,
)

router = APIRouter(tags=["比赛"])


def _utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def _status_of(contest: Contest, now: datetime | None = None) -> str:
    now = now or datetime.now(timezone.utc)
    start, end = _utc(contest.start_at), _utc(contest.end_at)
    if now < start:
        return "upcoming"
    if now <= end:
        return "ongoing"
    return "ended"


def _summary(contest: Contest) -> ContestSummary:
    return ContestSummary(
        id=contest.id,
        title=contest.title,
        contest_type=contest.contest_type,
        status=_status_of(contest),
        start_at=contest.start_at,
        end_at=contest.end_at,
        duration_minutes=contest.duration_minutes,
        problem_count=len(contest.problems),
        participant_count=len(contest.results),
    )


def _result_out(result: ContestResult) -> ContestResultOut:
    return ContestResultOut(
        user_id=result.user_id,
        username=result.user.username if result.user else "",
        score=result.score,
        cheat_count=result.cheat_count,
        status=result.status,
        submitted_at=result.submitted_at,
    )


def _load_contest(db: Session, contest_id: int) -> Contest:
    contest = db.scalars(
        select(Contest)
        .where(Contest.id == contest_id)
        .options(
            selectinload(Contest.problems)
            .selectinload(ContestProblem.problem)
            .selectinload(Problem.sub_questions),
            selectinload(Contest.results).joinedload(ContestResult.user),
            joinedload(Contest.creator),
        )
    ).unique().first()
    if contest is None:
        raise HTTPException(status_code=404, detail="比赛不存在")
    return contest


@router.get("/contests", response_model=list[ContestSummary])
def list_contests(
    contest_type: str | None = Query(None),
    db: Session = Depends(get_db),
):
    stmt = select(Contest).options(selectinload(Contest.problems), selectinload(Contest.results))
    if contest_type in ("personal", "official"):
        stmt = stmt.where(Contest.contest_type == contest_type)
    contests = db.scalars(stmt.order_by(Contest.start_at.desc())).all()
    return [_summary(c) for c in contests]


@router.post("/contests", response_model=ContestDetail, status_code=status.HTTP_201_CREATED)
def create_contest(
    payload: ContestIn,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    if _utc(payload.end_at) <= _utc(payload.start_at):
        raise HTTPException(status_code=400, detail="结束时间必须晚于开始时间")
    contest_type = payload.contest_type
    if user.role != "admin":
        if contest_type == "official":
            raise HTTPException(status_code=403, detail="官方赛需联系管理员申办")
        contest_type = "personal"
    contest = Contest(
        title=payload.title.strip(),
        description=payload.description,
        contest_type=contest_type,
        status="upcoming",
        start_at=_utc(payload.start_at),
        end_at=_utc(payload.end_at),
        duration_minutes=payload.duration_minutes,
        created_by=user.id,
    )
    problem_ids = [item.problem_id for item in payload.problems]
    existing = set(db.scalars(select(Problem.id).where(Problem.id.in_(problem_ids))).all()) if problem_ids else set()
    for item in payload.problems:
        if item.problem_id not in existing:
            raise HTTPException(status_code=400, detail=f"题目 {item.problem_id} 不存在")
        contest.problems.append(
            ContestProblem(problem_id=item.problem_id, order_no=item.order_no, score=item.score)
        )
    db.add(contest)
    db.commit()
    return get_contest(contest.id, db=db, user=user)


@router.put("/contests/{contest_id}", response_model=ContestDetail)
def update_contest(
    contest_id: int,
    payload: ContestUpdateIn,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
):
    contest = db.get(Contest, contest_id)
    if contest is None:
        raise HTTPException(status_code=404, detail="比赛不存在")

    start = _utc(payload.start_at) if payload.start_at else _utc(contest.start_at)
    end = _utc(payload.end_at) if payload.end_at else _utc(contest.end_at)
    if end <= start:
        raise HTTPException(status_code=400, detail="结束时间必须晚于开始时间")

    if payload.title is not None:
        contest.title = payload.title.strip()
    if payload.description is not None:
        contest.description = payload.description
    if payload.contest_type is not None:
        contest.contest_type = payload.contest_type
    if payload.start_at is not None:
        contest.start_at = start
    if payload.end_at is not None:
        contest.end_at = end
    if payload.duration_minutes is not None:
        contest.duration_minutes = payload.duration_minutes

    if payload.problems is not None:
        ids = [item.problem_id for item in payload.problems]
        existing = set(db.scalars(select(Problem.id).where(Problem.id.in_(ids))).all()) if ids else set()
        missing = [pid for pid in ids if pid not in existing]
        if missing:
            raise HTTPException(status_code=400, detail=f"题目不存在：{missing}")
        contest.problems.clear()
        for item in payload.problems:
            contest.problems.append(
                ContestProblem(problem_id=item.problem_id, order_no=item.order_no, score=item.score)
            )

    log_action(db, admin, "update_contest", "contest", contest_id, f"更新比赛：{contest.title}")
    db.commit()
    return get_contest(contest_id, db=db, user=admin)


@router.delete("/contests/{contest_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_contest(
    contest_id: int,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
):
    contest = db.get(Contest, contest_id)
    if contest is None:
        raise HTTPException(status_code=404, detail="比赛不存在")
    title = contest.title
    db.delete(contest)
    log_action(db, admin, "delete_contest", "contest", contest_id, f"删除比赛：{title}")
    db.commit()


@router.get("/contests/{contest_id}", response_model=ContestDetail)
def get_contest(
    contest_id: int,
    db: Session = Depends(get_db),
    user: User | None = Depends(get_optional_user),
):
    contest = _load_contest(db, contest_id)
    problems = []
    for cp in contest.problems:
        p = cp.problem
        if p is None:
            continue
        problems.append(
            ContestProblemOut(
                problem_id=p.id,
                title=p.title,
                type=p.type,
                order_no=cp.order_no,
                score=cp.score,
                content_md=p.content_md,
                sub_questions=[
                    SubQuestionPublic(
                        id=sq.id,
                        order_no=sq.order_no,
                        content_md=sq.content_md,
                        options=sq.options_json or [],
                    )
                    for sq in p.sub_questions
                ],
            )
        )
    results = sorted(contest.results, key=lambda r: (-r.score, r.cheat_count, r.id))
    my_result = next((r for r in contest.results if user and r.user_id == user.id), None)
    return ContestDetail(
        **_summary(contest).model_dump(),
        description=contest.description,
        creator_name=contest.creator.username if contest.creator else "官方",
        problems=problems,
        my_result=_result_out(my_result) if my_result else None,
        results=[_result_out(r) for r in results],
    )


@router.post("/contests/{contest_id}/anti-cheat")
def anti_cheat(
    contest_id: int,
    payload: AntiCheatIn,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    contest = db.get(Contest, contest_id)
    if contest is None:
        raise HTTPException(status_code=404, detail="比赛不存在")
    result = db.scalar(
        select(ContestResult).where(
            ContestResult.contest_id == contest_id, ContestResult.user_id == user.id
        )
    )
    if result is None:
        result = ContestResult(contest_id=contest_id, user_id=user.id)
        db.add(result)
        db.flush()
    result.cheat_count += 1
    db.add(
        CheatLog(
            contest_id=contest_id,
            user_id=user.id,
            event=payload.event[:32] or "visibilitychange",
            detail=payload.detail[:500],
        )
    )
    force_submit = result.cheat_count >= 3
    if force_submit:
        result.status = "cheating"
    db.commit()
    return {
        "cheat_count": result.cheat_count,
        "force_submit": force_submit,
        "message": "第 3 次切屏，系统已强制交卷" if force_submit else f"警告：检测到切屏（第 {result.cheat_count} 次）",
    }


@router.post("/contests/{contest_id}/submit", response_model=ContestResultOut)
def submit_contest(
    contest_id: int,
    payload: ContestAnswersIn,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    contest = _load_contest(db, contest_id)
    if _status_of(contest) == "upcoming":
        raise HTTPException(status_code=400, detail="比赛尚未开始")

    result = db.scalar(
        select(ContestResult).where(
            ContestResult.contest_id == contest_id, ContestResult.user_id == user.id
        )
    )
    if result is None:
        result = ContestResult(contest_id=contest_id, user_id=user.id)
        db.add(result)
        db.flush()
    if result.status == "submitted":
        raise HTTPException(status_code=400, detail="你已经交卷")

    score = 0
    for cp in contest.problems:
        problem = cp.problem
        if problem is None:
            continue
        subs = list(problem.sub_questions)
        if not subs:
            continue
        per = max(1, round(cp.score / len(subs)))
        for sq in subs:
            raw = payload.answers.get(str(sq.id), "")
            answer = (raw or "").strip().upper()
            correct = answer == (sq.correct_answer or "").strip().upper()
            if correct:
                score += per
            db.add(
                Submission(
                    user_id=user.id,
                    problem_id=problem.id,
                    sub_question_id=sq.id,
                    user_answer=answer,
                    is_correct=correct,
                    time_spent=max(0, int(payload.time_spent)),
                    contest_id=contest_id,
                )
            )
    result.score = score
    result.status = "submitted"
    result.submitted_at = datetime.now(timezone.utc)
    if contest.contest_type == "official":
        user.monkey_score += score
    db.commit()
    db.refresh(result)
    return _result_out(result)


@router.post("/contests/{contest_id}/judge", response_model=ContestResultOut)
def judge_contest(
    contest_id: int,
    payload: ContestJudgeIn,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
):
    contest = db.get(Contest, contest_id)
    if contest is None:
        raise HTTPException(status_code=404, detail="比赛不存在")
    target = db.get(User, payload.user_id)
    if target is None:
        raise HTTPException(status_code=404, detail="用户不存在")
    if target.role == "admin":
        raise HTTPException(status_code=400, detail="不能对管理员执行作弊判定或封禁")

    result = db.scalar(
        select(ContestResult).where(
            ContestResult.contest_id == contest_id, ContestResult.user_id == target.id
        )
    )
    if result is None:
        result = ContestResult(contest_id=contest_id, user_id=target.id)
        db.add(result)

    if payload.cheat:
        target.monkey_score = 0
        target.credit_score = 50
        target.title = "作弊者"
        target.can_create_problem = False
        if payload.severe:
            target.status = "banned"
            target.ban_until = None
        else:
            target.status = "normal"
            target.ban_until = None
        result.status = "cheating"
        db.add(
            CheatLog(
                contest_id=contest_id,
                user_id=target.id,
                event="admin_judge",
                detail=(payload.reason or "管理员判定作弊")[:500],
            )
        )
    else:
        result.status = "submitted"

    log_action(
        db,
        admin,
        "judge_contest",
        "contest",
        contest_id,
        f"判定用户 {target.username}：{'作弊' if payload.cheat else '通过'}{'（严重）' if payload.severe else ''}",
    )
    db.commit()
    db.refresh(result)
    return _result_out(result)
