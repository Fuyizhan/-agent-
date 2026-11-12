"""核心 ORM 模型：用户、审查记录和四类审查结果。"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .session import Base


def _gen_uuid() -> str:
    return str(uuid.uuid4())[:8]


class UserRecord(Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id: Mapped[str] = mapped_column(String(36), index=True)
    username: Mapped[str] = mapped_column(String(50), unique=True, index=True)
    email: Mapped[str] = mapped_column(String(200), unique=True, index=True)
    hashed_password: Mapped[str] = mapped_column(String(200))
    role: Mapped[str] = mapped_column(String(20), default="viewer")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, onupdate=datetime.now)


class ReviewRecord(Base):
    __tablename__ = "reviews"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id: Mapped[str] = mapped_column(String(36), index=True)
    user_id: Mapped[str] = mapped_column(String(36), default="")
    status: Mapped[str] = mapped_column(String(20), default="pending")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, onupdate=datetime.now)

    document_path: Mapped[str] = mapped_column(String(500), default="")
    original_filename: Mapped[str] = mapped_column(String(255), default="")
    raw_text: Mapped[str] = mapped_column(Text, default="")
    contract_type: Mapped[str] = mapped_column(String(100), default="")

    overall_risk_level: Mapped[str] = mapped_column(String(10), default="none")
    risk_summary: Mapped[str] = mapped_column(Text, default="")
    overall_compliance: Mapped[str] = mapped_column(String(20), default="needs_review")
    missing_clauses: Mapped[list] = mapped_column(JSON, default=list)
    version_diff: Mapped[str] = mapped_column(Text, default="")
    needs_human_review: Mapped[bool] = mapped_column(Boolean, default=False)

    errors: Mapped[list] = mapped_column(JSON, default=list)
    current_step: Mapped[str] = mapped_column(String(50), default="")
    step_log: Mapped[list] = mapped_column(JSON, default=list)
    progress: Mapped[float] = mapped_column(Float, default=0.0)

    clauses: Mapped[list[ClauseRecord]] = relationship(
        back_populates="review", cascade="all, delete-orphan"
    )
    risk_findings: Mapped[list[RiskFindingRecord]] = relationship(
        back_populates="review", cascade="all, delete-orphan"
    )
    compliance_findings: Mapped[list[ComplianceFindingRecord]] = relationship(
        back_populates="review", cascade="all, delete-orphan"
    )
    suggestions: Mapped[list[SuggestionRecord]] = relationship(
        back_populates="review", cascade="all, delete-orphan"
    )


class ClauseRecord(Base):
    __tablename__ = "clauses"

    id: Mapped[str] = mapped_column(String(8), primary_key=True, default=_gen_uuid)
    review_id: Mapped[str] = mapped_column(ForeignKey("reviews.id"))
    title: Mapped[str] = mapped_column(String(200))
    content: Mapped[str] = mapped_column(Text)
    category: Mapped[str] = mapped_column(String(50), default="other")
    section_number: Mapped[str] = mapped_column(String(50), default="")
    entities: Mapped[list] = mapped_column(JSON, default=list)
    review: Mapped[ReviewRecord] = relationship(back_populates="clauses")


class RiskFindingRecord(Base):
    __tablename__ = "risk_findings"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    review_id: Mapped[str] = mapped_column(ForeignKey("reviews.id"))
    clause_id: Mapped[str] = mapped_column(String(8))
    risk_level: Mapped[str] = mapped_column(String(10))
    risk_type: Mapped[str] = mapped_column(String(100))
    description: Mapped[str] = mapped_column(Text)
    buyer_impact: Mapped[str] = mapped_column(Text, default="")
    seller_impact: Mapped[str] = mapped_column(Text, default="")
    rationale: Mapped[str] = mapped_column(Text, default="")
    review: Mapped[ReviewRecord] = relationship(back_populates="risk_findings")


class ComplianceFindingRecord(Base):
    __tablename__ = "compliance_findings"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    review_id: Mapped[str] = mapped_column(ForeignKey("reviews.id"))
    clause_id: Mapped[str] = mapped_column(String(8))
    status: Mapped[str] = mapped_column(String(20))
    regulation: Mapped[str] = mapped_column(String(200))
    issue: Mapped[str] = mapped_column(Text)
    recommendation: Mapped[str] = mapped_column(Text, default="")
    review: Mapped[ReviewRecord] = relationship(back_populates="compliance_findings")


class SuggestionRecord(Base):
    __tablename__ = "suggestions"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    review_id: Mapped[str] = mapped_column(ForeignKey("reviews.id"))
    clause_id: Mapped[str] = mapped_column(String(8))
    original_text: Mapped[str] = mapped_column(Text)
    suggested_text: Mapped[str] = mapped_column(Text)
    reason: Mapped[str] = mapped_column(Text)
    priority: Mapped[str] = mapped_column(String(10))
    review: Mapped[ReviewRecord] = relationship(back_populates="suggestions")
