"""序列化辅助：把 ORM 对象转成响应模型（含标签、小题答案控制）。"""
from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from  import models
from schemas import (
    ProblemDetail,
    ProblemSummary,
    SubQuestionOut,
    SubQuestionPublic,
    TagOut,
    UserOut,
)


def tags_map(db: Session, tag_ids: set[int]) -> dict[int, TagOut]:
    if not tag_ids:
        return {}
    rows = db.scalars(select(models.Tag).where(models.Tag.id.in_(tag_ids))).all()
    return {t.id: TagOut.model_validate(t) for t in rows}


def problem_tags(db: Session, problem: models.Problem, cache: dict[int, TagOut] | None = None) -> list[TagOut]:
    cache = cache if cache is not None else {}
    missing = {link.tag_id for link in problem.tag_links} - cache.keys()
    if missing:
        cache.update(tags_map(db, missing))
    return [cache[link.tag_id] for link in problem.tag_links if link.tag_id in cache]


def to_summary(
    db: Session,
    problem: models.Problem,
    tag_cache: dict[int, TagOut] | None = None,
) -> ProblemSummary:
    return ProblemSummary(
        id=problem.id,
        title=problem.title,
        type=problem.type,
        source_tag=problem.source_tag,
        source_year=problem.source_year,
        source_exam=problem.source_exam,
        status=problem.status,
        contributor_id=problem.contributor_id,
        contributor_name=problem.contributor.username if problem.contributor else None,
        tags=problem_tags(db, problem, tag_cache),
        sub_question_count=len(problem.sub_questions),
        created_at=problem.created_at,
        reviewed_at=problem.reviewed_at,
        reject_reason=problem.reject_reason,
    )


def to_details(
    db: Session,
    problem: models.Problem,
    *,
    include_answers: bool = True,
    tag_cache: dict[int, TagOut] | None = None,
) -> ProblemDetail:
    summary = to_summary(db, problem, tag_cache)
    subs = []
    for sq in problem.sub_questions:
        if include_answers:
            subs.append(
                SubQuestionOut(
                    id=sq.id,
                    order_no=sq.order_no,
                    content_md=sq.content_md,
                    options=sq.options_json or [],
                    correct_answer=sq.correct_answer,
                    analysis_md=sq.analysis_md,
                )
            )
        else:
            subs.append(
                SubQuestionPublic(
                    id=sq.id,
                    order_no=sq.order_no,
                    content_md=sq.content_md,
                    options=sq.options_json or [],
                )
            )  # type: ignore[arg-type]
    return ProblemDetail(
        **summary.model_dump(),
        content_md=problem.content_md,
        answer_md=problem.answer_md,
        sub_questions=subs,  # type: ignore[arg-type]
    )


def user_out(user: models.User) -> UserOut:
    return UserOut.model_validate(user)
