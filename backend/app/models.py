"""SQLAlchemy 模型定义（与 backend/sql/schema.sql 保持一致）。

说明（对需求数据模型的两处必要扩展，已在 README 标注）：
1. mock_exams.answers_json —— 交卷后需要回显"逐题解析"，必须持久化考生作答；
2. submissions.mock_exam_id —— 模拟考试作答也写入 submissions，靠该字段与"普通做题统计"区分。
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

from .database import Base

# PostgreSQL 下使用 JSONB，SQLite（本地降级）下退回 JSON
JSONType = JSON().with_variant(JSONB, "postgresql")

PROBLEM_TYPES = ("single", "reading", "completion")
SOURCE_TAGS = ("original", "real", "adapted")
PROBLEM_STATUSES = ("pending", "approved", "rejected")
EXAM_NAMES = ("CSP-J", "CSP-S")


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
    created_at: Mapped[datetime] = mapped_column(UTCDateTime, default=utcnow, nullable=False)

    problems: Mapped[list["Problem"]] = relationship(back_populates="contributor", foreign_keys="Problem.contributor_id")


class Tag(Base):
    __tablename__ = "tags"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    category: Mapped[str] = mapped_column(String(32), nullable=False, default="知识点")


class ProblemTag(Base):
    __tablename__ = "problem_tags"

    problem_id: Mapped[int] = mapped_column(ForeignKey("problems.id", ondelete="CASCADE"), primary_key=True)
    tag_id: Mapped[int] = mapped_column(ForeignKey("tags.id", ondelete="CASCADE"), primary_key=True)


class Problem(Base):
    __tablename__ = "problems"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    type: Mapped[str] = mapped_column(String(16), nullable=False, index=True)          # single / reading / completion
    source_tag: Mapped[str] = mapped_column(String(16), nullable=False, default="original")  # original/real/adapted
    source_year: Mapped[int | None] = mapped_column(Integer, nullable=True)
    source_exam: Mapped[str | None] = mapped_column(String(16), nullable=True)         # CSP-J / CSP-S
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
        back_populates="problem", cascade="all, delete-orphan", order_by="SubQuestion.order_no", lazy="selectin"
    )
    tag_links: Mapped[list[ProblemTag]] = relationship(cascade="all, delete-orphan", lazy="selectin")

    __table_args__ = (
        Index("ix_problems_status_type", "status", "type"),
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
    error_type: Mapped[int | None] = mapped_column(Integer, nullable=True)       # 1概念不清 2方法不会 3粗心 4审题错误
    redo_status: Mapped[int] = mapped_column(Integer, nullable=False, default=0)  # 0待重做 1重做对 2重做错
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
    review_result: Mapped[int] = mapped_column(Integer, nullable=False)  # 1 对 / 0 错
    reviewed_at: Mapped[datetime] = mapped_column(UTCDateTime, default=utcnow, nullable=False)


class MockExam(Base):
    __tablename__ = "mock_exams"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    exam_type: Mapped[str] = mapped_column(String(8), nullable=False, default="J")   # J / S
    problem_ids: Mapped[list] = mapped_column(JSONType, nullable=False, default=list)
    answers_json: Mapped[dict] = mapped_column(JSONType, nullable=False, default=dict)  # 扩展：考生作答 {sub_id: "AB"}
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="ongoing")
    started_at: Mapped[datetime] = mapped_column(UTCDateTime, default=utcnow, nullable=False)
    submitted_at: Mapped[datetime | None] = mapped_column(UTCDateTime, nullable=True)
    score: Mapped[int | None] = mapped_column(Integer, nullable=True)


class Submission(Base):
    __tablename__ = "submissions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    problem_id: Mapped[int] = mapped_column(ForeignKey("problems.id", ondelete="CASCADE"), nullable=False)
    sub_question_id: Mapped[int] = mapped_column(ForeignKey("sub_questions.id", ondelete="CASCADE"), nullable=False)
    user_answer: Mapped[str] = mapped_column(String(16), nullable=False, default="")
    is_correct: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    mock_exam_id: Mapped[int | None] = mapped_column(
        ForeignKey("mock_exams.id", ondelete="SET NULL"), nullable=True, index=True
    )  # 扩展：非空代表本次作答属于模拟考试，不计入普通统计
    submitted_at: Mapped[datetime] = mapped_column(UTCDateTime, default=utcnow, nullable=False, index=True)

    __table_args__ = (Index("ix_sub_user_time", "user_id", "submitted_at"),)
