"""SQLAlchemy 模型定义。

包含：用户 / 题库 / 题单 / 错题 / 模拟考试 / 比赛 / 讨论 / 举报 / 申诉 / 作弊日志。
所有外键均配置 ON DELETE 行为；SQLAlchemy 关系配置 cascade，保证删除题目或用户时
相关数据不会留下孤儿记录。
"""
from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    TypeDecorator,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database import Base

JSONType = JSON().with_variant(JSONB, "postgresql")

PROBLEM_TYPES = ("single", "reading", "completion")
SOURCE_TAGS = ("original", "real", "adapted")
PROBLEM_STATUSES = ("pending", "approved", "rejected")
EXAM_NAMES = ("CSP-J", "CSP-S")
POOL_TYPES = ("P", "T", "S")
CONTEST_TYPES = ("personal", "official")


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class UTCDateTime(TypeDecorator):
    """统一以「朴素 UTC」入库、以「带时区 UTC」出库，兼容 PostgreSQL 与 SQLite。"""

    impl = DateTime
    cache_ok = True

    def process_bind_param(self, value: datetime | None, dialect):
        if value is None:
            return None
        if value.tzinfo is None:
            value = value.replace(tzinfo=timezone.utc)
        return value.astimezone(timezone.utc).replace(tzinfo=None)

    def process_result_value(self, value: datetime | None, dialect):
        if value is None:
            return None
        if value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)
        return value.astimezone(timezone.utc)


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    username: Mapped[str] = mapped_column(String(50), unique=True, nullable=False, index=True)
    password_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    role: Mapped[str] = mapped_column(String(16), nullable=False, default="user")
    monkey_score: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    credit_score: Mapped[int] = mapped_column(Integer, nullable=False, default=100)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="normal")  # normal/banned
    ban_until: Mapped[datetime | None] = mapped_column(UTCDateTime, nullable=True)
    title: Mapped[str] = mapped_column(String(64), nullable=False, default="")
    can_create_problem: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    avatar_url: Mapped[str | None] = mapped_column(String(512), nullable=True)
    avatar_status: Mapped[str] = mapped_column(String(16), nullable=False, default="approved")
    last_username_change: Mapped[datetime | None] = mapped_column(UTCDateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime, default=utcnow, nullable=False)

    problems: Mapped[list["Problem"]] = relationship(
        back_populates="contributor", foreign_keys="Problem.contributor_id"
    )


class Tag(Base):
    __tablename__ = "tags"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    category: Mapped[str] = mapped_column(String(32), nullable=False, default="知识点")


class ProblemTag(Base):
    __tablename__ = "problem_tags"

    problem_id: Mapped[int] = mapped_column(ForeignKey("problems.id", ondelete="CASCADE"), primary_key=True)
    tag_id: Mapped[int] = mapped_column(ForeignKey("tags.id", ondelete="CASCADE"), primary_key=True)

    tag: Mapped["Tag"] = relationship(lazy="joined")


class Problem(Base):
    __tablename__ = "problems"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    type: Mapped[str] = mapped_column(String(16), nullable=False, index=True)
    source_tag: Mapped[str] = mapped_column(String(16), nullable=False, default="original")
    source_year: Mapped[int | None] = mapped_column(Integer, nullable=True)
    source_exam: Mapped[str | None] = mapped_column(String(16), nullable=True)
    pool_type: Mapped[str] = mapped_column(String(8), nullable=False, default="P", index=True)  # P/T/S
    problem_number: Mapped[str | None] = mapped_column(String(32), unique=True, nullable=True)
    content_md: Mapped[str] = mapped_column(Text, nullable=False, default="")
    answer_md: Mapped[str] = mapped_column(Text, nullable=False, default="")
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="pending", index=True)
    contributor_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    reviewer_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    reject_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime, default=utcnow, nullable=False)
    reviewed_at: Mapped[datetime | None] = mapped_column(UTCDateTime, nullable=True)

    contributor: Mapped[User] = relationship(back_populates="problems", foreign_keys=[contributor_id])
    reviewer: Mapped[User | None] = relationship(foreign_keys=[reviewer_id])
    sub_questions: Mapped[list["SubQuestion"]] = relationship(
        back_populates="problem",
        cascade="all, delete-orphan",
        order_by="SubQuestion.order_no",
        lazy="selectin",
    )
    tag_links: Mapped[list[ProblemTag]] = relationship(cascade="all, delete-orphan", lazy="selectin")

    __table_args__ = (
        Index("ix_problems_status_type", "status", "type"),
        Index("ix_problems_pool_status", "pool_type", "status"),
        Index("ix_problems_created_at", "created_at"),
    )


class SubQuestion(Base):
    __tablename__ = "sub_questions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    problem_id: Mapped[int] = mapped_column(ForeignKey("problems.id", ondelete="CASCADE"), nullable=False, index=True)
    order_no: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    content_md: Mapped[str] = mapped_column(Text, nullable=False, default="")
    options_json: Mapped[list] = mapped_column(JSONType, nullable=False, default=list)
    correct_answer: Mapped[str] = mapped_column(String(8), nullable=False, default="A")
    analysis_md: Mapped[str] = mapped_column(Text, nullable=False, default="")

    problem: Mapped[Problem] = relationship(back_populates="sub_questions")

    __table_args__ = (UniqueConstraint("problem_id", "order_no", name="uq_sub_problem_order"),)


class ProblemList(Base):
    __tablename__ = "problem_lists"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False, default="")
    creator_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    is_public: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime, default=utcnow, nullable=False)

    creator: Mapped[User] = relationship()
    items: Mapped[list["ProblemListItem"]] = relationship(
        cascade="all, delete-orphan", order_by="ProblemListItem.order_no", lazy="selectin"
    )


class ProblemListItem(Base):
    __tablename__ = "problem_list_items"

    list_id: Mapped[int] = mapped_column(ForeignKey("problem_lists.id", ondelete="CASCADE"), primary_key=True)
    problem_id: Mapped[int] = mapped_column(ForeignKey("problems.id", ondelete="CASCADE"), primary_key=True)
    order_no: Mapped[int] = mapped_column(Integer, nullable=False, default=1)


class WrongQuestion(Base):
    __tablename__ = "wrong_questions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    problem_id: Mapped[int] = mapped_column(ForeignKey("problems.id", ondelete="CASCADE"), nullable=False)
    sub_question_id: Mapped[int] = mapped_column(ForeignKey("sub_questions.id", ondelete="CASCADE"), nullable=False)
    error_type: Mapped[int | None] = mapped_column(Integer, nullable=True)
    redo_status: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    consecutive_pass: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    next_review_at: Mapped[datetime | None] = mapped_column(UTCDateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime, default=utcnow, nullable=False)

    __table_args__ = (
        UniqueConstraint("user_id", "problem_id", "sub_question_id", name="uq_wrong_user_problem_sub"),
        Index("ix_wrong_user_next_review", "user_id", "next_review_at"),
    )

    problem: Mapped[Problem] = relationship(lazy="selectin")
    sub_question: Mapped[SubQuestion] = relationship(lazy="selectin")
    reviews: Mapped[list["WrongReview"]] = relationship(cascade="all, delete-orphan", lazy="selectin")


class WrongReview(Base):
    __tablename__ = "wrong_reviews"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    wrong_id: Mapped[int] = mapped_column(ForeignKey("wrong_questions.id", ondelete="CASCADE"), nullable=False, index=True)
    review_result: Mapped[int] = mapped_column(Integer, nullable=False)
    reviewed_at: Mapped[datetime] = mapped_column(UTCDateTime, default=utcnow, nullable=False)


class MockExam(Base):
    __tablename__ = "mock_exams"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    exam_type: Mapped[str] = mapped_column(String(8), nullable=False, default="J")
    problem_ids: Mapped[list] = mapped_column(JSONType, nullable=False, default=list)
    answers_json: Mapped[dict] = mapped_column(JSONType, nullable=False, default=dict)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="ongoing")
    started_at: Mapped[datetime] = mapped_column(UTCDateTime, default=utcnow, nullable=False)
    submitted_at: Mapped[datetime | None] = mapped_column(UTCDateTime, nullable=True)
    score: Mapped[int | None] = mapped_column(Integer, nullable=True)


# ---------------------------------------------------------------------------
# 比赛 / 防作弊
# ---------------------------------------------------------------------------
class Contest(Base):
    __tablename__ = "contests"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False, default="")
    contest_type: Mapped[str] = mapped_column(String(16), nullable=False, default="official")  # personal/official
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="upcoming")  # upcoming/ongoing/ended
    start_at: Mapped[datetime] = mapped_column(UTCDateTime, nullable=False)
    end_at: Mapped[datetime] = mapped_column(UTCDateTime, nullable=False)
    duration_minutes: Mapped[int] = mapped_column(Integer, nullable=False, default=120)
    created_by: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime, default=utcnow, nullable=False)

    problems: Mapped[list["ContestProblem"]] = relationship(
        cascade="all, delete-orphan", order_by="ContestProblem.order_no", lazy="selectin"
    )
    results: Mapped[list["ContestResult"]] = relationship(
        cascade="all, delete-orphan", back_populates="contest", lazy="selectin"
    )


class ContestProblem(Base):
    __tablename__ = "contest_problems"

    contest_id: Mapped[int] = mapped_column(ForeignKey("contests.id", ondelete="CASCADE"), primary_key=True)
    problem_id: Mapped[int] = mapped_column(ForeignKey("problems.id", ondelete="CASCADE"), primary_key=True)
    order_no: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    score: Mapped[int] = mapped_column(Integer, nullable=False, default=10)

    problem: Mapped[Problem] = relationship(lazy="joined")


class ContestResult(Base):
    __tablename__ = "contest_results"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    contest_id: Mapped[int] = mapped_column(ForeignKey("contests.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    score: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    cheat_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="ongoing")  # ongoing/submitted/cheating
    submitted_at: Mapped[datetime | None] = mapped_column(UTCDateTime, nullable=True)

    contest: Mapped[Contest] = relationship(back_populates="results")
    user: Mapped[User] = relationship()

    __table_args__ = (UniqueConstraint("contest_id", "user_id", name="uq_contest_result_user"),)


class CheatLog(Base):
    __tablename__ = "cheat_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    contest_id: Mapped[int] = mapped_column(ForeignKey("contests.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    event: Mapped[str] = mapped_column(String(32), nullable=False, default="visibilitychange")
    detail: Mapped[str] = mapped_column(Text, nullable=False, default="")
    created_at: Mapped[datetime] = mapped_column(UTCDateTime, default=utcnow, nullable=False)


class Submission(Base):
    __tablename__ = "submissions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    problem_id: Mapped[int] = mapped_column(ForeignKey("problems.id", ondelete="CASCADE"), nullable=False)
    sub_question_id: Mapped[int] = mapped_column(ForeignKey("sub_questions.id", ondelete="CASCADE"), nullable=False)
    user_answer: Mapped[str] = mapped_column(String(16), nullable=False, default="")
    is_correct: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    time_spent: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    mock_exam_id: Mapped[int | None] = mapped_column(
        ForeignKey("mock_exams.id", ondelete="SET NULL"), nullable=True, index=True
    )
    contest_id: Mapped[int | None] = mapped_column(
        ForeignKey("contests.id", ondelete="SET NULL"), nullable=True, index=True
    )
    submitted_at: Mapped[datetime] = mapped_column(UTCDateTime, default=utcnow, nullable=False, index=True)

    __table_args__ = (Index("ix_sub_user_time", "user_id", "submitted_at"),)


# ---------------------------------------------------------------------------
# 讨论 / 评论 / 举报
# ---------------------------------------------------------------------------
class Discussion(Base):
    __tablename__ = "discussions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    content_md: Mapped[str] = mapped_column(Text, nullable=False, default="")
    category: Mapped[str] = mapped_column(String(16), nullable=False, default="学术")  # 站务/学术/题目
    author_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    problem_id: Mapped[int | None] = mapped_column(ForeignKey("problems.id", ondelete="SET NULL"), nullable=True)
    is_pinned: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    is_locked: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime, default=utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(UTCDateTime, default=utcnow, nullable=False)

    author: Mapped[User] = relationship(lazy="joined")
    comments: Mapped[list["Comment"]] = relationship(
        cascade="all, delete-orphan", order_by="Comment.created_at", lazy="selectin"
    )


class Comment(Base):
    __tablename__ = "comments"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    discussion_id: Mapped[int] = mapped_column(
        ForeignKey("discussions.id", ondelete="CASCADE"), nullable=False, index=True
    )
    author_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    content_md: Mapped[str] = mapped_column(Text, nullable=False, default="")
    created_at: Mapped[datetime] = mapped_column(UTCDateTime, default=utcnow, nullable=False)

    author: Mapped[User] = relationship(lazy="joined")


class Report(Base):
    __tablename__ = "reports"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    reporter_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    target_type: Mapped[str] = mapped_column(String(16), nullable=False)  # problem/discussion/comment
    target_id: Mapped[int] = mapped_column(Integer, nullable=False)
    reason: Mapped[str] = mapped_column(Text, nullable=False, default="")
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="pending")  # pending/resolved
    created_at: Mapped[datetime] = mapped_column(UTCDateTime, default=utcnow, nullable=False)
    resolved_by: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    resolved_at: Mapped[datetime | None] = mapped_column(UTCDateTime, nullable=True)


class Appeal(Base):
    __tablename__ = "appeals"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    contest_id: Mapped[int | None] = mapped_column(ForeignKey("contests.id", ondelete="SET NULL"), nullable=True)
    reason: Mapped[str] = mapped_column(Text, nullable=False, default="")
    video_url: Mapped[str] = mapped_column(String(512), nullable=False, default="")
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="pending")  # pending/approved/rejected
    admin_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    admin_note: Mapped[str] = mapped_column(Text, nullable=False, default="")
    created_at: Mapped[datetime] = mapped_column(UTCDateTime, default=utcnow, nullable=False)
    reviewed_at: Mapped[datetime | None] = mapped_column(UTCDateTime, nullable=True)

    user: Mapped[User] = relationship(foreign_keys=[user_id], lazy="joined")
    contest: Mapped[Contest | None] = relationship(lazy="joined")
