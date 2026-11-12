"""ContractReviewState 与 ORM 模型之间的持久化桥接。"""

from __future__ import annotations

import logging
from datetime import datetime

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from ..pipeline.state import (
    Clause,
    ClauseCategory,
    ComplianceFinding,
    ComplianceStatus,
    ContractEntity,
    ContractReviewState,
    RiskFinding,
    RiskLevel,
    ReviewStatus,
    StepEvent,
    Suggestion,
)
from .models import (
    ClauseRecord,
    ComplianceFindingRecord,
    ReviewRecord,
    RiskFindingRecord,
    SuggestionRecord,
)

logger = logging.getLogger(__name__)


def _save_children(db: AsyncSession, state: ContractReviewState) -> None:
    for clause in state.clauses:
        db.add(ClauseRecord(
            id=clause.id,
            review_id=state.review_id,
            title=clause.title,
            content=clause.content,
            category=clause.category.value,
            section_number=clause.section_number,
            entities=[e.model_dump() for e in clause.entities],
        ))
    for finding in state.risk_findings:
        db.add(RiskFindingRecord(
            review_id=state.review_id,
            clause_id=finding.clause_id,
            risk_level=finding.risk_level.value,
            risk_type=finding.risk_type,
            description=finding.description,
            buyer_impact=finding.buyer_impact,
            seller_impact=finding.seller_impact,
            rationale=finding.rationale,
        ))
    for finding in state.compliance_findings:
        db.add(ComplianceFindingRecord(
            review_id=state.review_id,
            clause_id=finding.clause_id,
            status=finding.status.value,
            regulation=finding.regulation,
            issue=finding.issue,
            recommendation=finding.recommendation,
        ))
    for suggestion in state.suggestions:
        db.add(SuggestionRecord(
            review_id=state.review_id,
            clause_id=suggestion.clause_id,
            original_text=suggestion.original_text,
            suggested_text=suggestion.suggested_text,
            reason=suggestion.reason,
            priority=suggestion.priority.value,
        ))


async def save_review(
    db: AsyncSession,
    state: ContractReviewState,
    tenant_id: str = "",
    user_id: str = "",
) -> str:
    result = await db.execute(select(ReviewRecord).where(ReviewRecord.id == state.review_id))
    review = result.scalar_one_or_none()
    if review is not None and review.tenant_id != tenant_id:
        raise PermissionError(f"审查 {state.review_id} 属于其他租户")

    values = {
        "tenant_id": tenant_id,
        "user_id": user_id,
        "status": state.status.value,
        "created_at": state.created_at,
        "updated_at": state.updated_at or datetime.now(),
        "document_path": state.document_path,
        "original_filename": state.original_filename,
        "raw_text": state.raw_text,
        "contract_type": state.contract_type,
        "overall_risk_level": state.overall_risk_level.value,
        "risk_summary": state.risk_summary,
        "overall_compliance": state.overall_compliance.value,
        "missing_clauses": state.missing_clauses,
        "version_diff": state.version_diff,
        "needs_human_review": state.needs_human_review,
        "errors": state.errors,
        "current_step": state.current_step,
        "step_log": [e.model_dump(mode="json") for e in state.step_log],
        "progress": state.progress,
    }

    if review is None:
        db.add(ReviewRecord(id=state.review_id, **values))
    else:
        for field, value in values.items():
            setattr(review, field, value)
        for model in (ClauseRecord, RiskFindingRecord, ComplianceFindingRecord, SuggestionRecord):
            await db.execute(delete(model).where(model.review_id == state.review_id))
        await db.flush()

    _save_children(db, state)
    return state.review_id


async def get_review(
    db: AsyncSession,
    review_id: str,
    tenant_id: str = "",
) -> ContractReviewState | None:
    stmt = select(ReviewRecord).where(ReviewRecord.id == review_id)
    if tenant_id:
        stmt = stmt.where(ReviewRecord.tenant_id == tenant_id)
    stmt = stmt.options(
        selectinload(ReviewRecord.clauses),
        selectinload(ReviewRecord.risk_findings),
        selectinload(ReviewRecord.compliance_findings),
        selectinload(ReviewRecord.suggestions),
    )
    record = (await db.execute(stmt)).scalar_one_or_none()
    if record is None:
        return None

    return ContractReviewState(
        review_id=record.id,
        status=ReviewStatus(record.status),
        created_at=record.created_at,
        updated_at=record.updated_at,
        document_path=record.document_path,
        original_filename=record.original_filename,
        raw_text=record.raw_text or "",
        contract_type=record.contract_type,
        clauses=[
            Clause(
                id=c.id,
                title=c.title,
                content=c.content,
                category=ClauseCategory(c.category),
                section_number=c.section_number,
                entities=[ContractEntity(**e) for e in (c.entities or [])],
            )
            for c in record.clauses
        ],
        risk_findings=[
            RiskFinding(
                clause_id=r.clause_id,
                risk_level=RiskLevel(r.risk_level),
                risk_type=r.risk_type,
                description=r.description,
                buyer_impact=r.buyer_impact,
                seller_impact=r.seller_impact,
                rationale=r.rationale,
            )
            for r in record.risk_findings
        ],
        overall_risk_level=RiskLevel(record.overall_risk_level),
        risk_summary=record.risk_summary,
        compliance_findings=[
            ComplianceFinding(
                clause_id=c.clause_id,
                status=ComplianceStatus(c.status),
                regulation=c.regulation,
                issue=c.issue,
                recommendation=c.recommendation,
            )
            for c in record.compliance_findings
        ],
        missing_clauses=record.missing_clauses or [],
        overall_compliance=ComplianceStatus(record.overall_compliance),
        suggestions=[
            Suggestion(
                clause_id=s.clause_id,
                original_text=s.original_text,
                suggested_text=s.suggested_text,
                reason=s.reason,
                priority=RiskLevel(s.priority),
            )
            for s in record.suggestions
        ],
        version_diff=record.version_diff or "",
        needs_human_review=record.needs_human_review,
        errors=record.errors or [],
        current_step=record.current_step or "",
        step_log=[StepEvent(**e) for e in (record.step_log or [])],
        progress=record.progress or 0.0,
    )
