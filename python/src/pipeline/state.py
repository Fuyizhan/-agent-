"""LangGraph 四 Agent 审查流水线的共享状态。"""

from __future__ import annotations

import uuid
from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field


class RiskLevel(str, Enum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    NONE = "none"


class ComplianceStatus(str, Enum):
    COMPLIANT = "compliant"
    NON_COMPLIANT = "non_compliant"
    NEEDS_REVIEW = "needs_review"


class ClauseCategory(str, Enum):
    PAYMENT = "payment"
    LIABILITY = "liability"
    CONFIDENTIALITY = "confidentiality"
    TERMINATION = "termination"
    INTELLECTUAL_PROPERTY = "intellectual_property"
    DISPUTE_RESOLUTION = "dispute_resolution"
    FORCE_MAJEURE = "force_majeure"
    WARRANTY = "warranty"
    INDEMNIFICATION = "indemnification"
    GOVERNING_LAW = "governing_law"
    OTHER = "other"


class ReviewStatus(str, Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"


class ContractEntity(BaseModel):
    entity_type: str
    value: str
    location: str = ""


class Clause(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4())[:8])
    title: str
    content: str
    category: ClauseCategory = ClauseCategory.OTHER
    section_number: str = ""
    entities: list[ContractEntity] = Field(default_factory=list)


class RiskFinding(BaseModel):
    clause_id: str
    risk_level: RiskLevel
    risk_type: str
    description: str
    buyer_impact: str = ""
    seller_impact: str = ""
    rationale: str = ""


class ComplianceFinding(BaseModel):
    clause_id: str
    status: ComplianceStatus
    regulation: str
    issue: str
    recommendation: str = ""


class Suggestion(BaseModel):
    clause_id: str
    original_text: str
    suggested_text: str
    reason: str
    priority: RiskLevel


class StepEvent(BaseModel):
    step: str
    status: str
    message: str = ""
    started_at: datetime = Field(default_factory=datetime.now)
    finished_at: datetime | None = None


PIPELINE_STEPS = [
    "clause_extraction",
    "risk_identification",
    "compliance_check",
    "suggestion",
]

STEP_LABELS = {
    "clause_extraction": "条款提取",
    "risk_identification": "风险识别",
    "compliance_check": "合规检查",
    "suggestion": "修改建议",
}


class ContractReviewState(BaseModel):
    review_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    status: ReviewStatus = ReviewStatus.PENDING
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime | None = None

    document_path: str = ""
    original_filename: str = ""
    # 保留兼容字段，核心链路不再把全文写入状态。
    raw_text: str = ""

    clauses: list[Clause] = Field(default_factory=list)
    entities: list[ContractEntity] = Field(default_factory=list)
    contract_type: str = ""

    risk_findings: list[RiskFinding] = Field(default_factory=list)
    overall_risk_level: RiskLevel = RiskLevel.NONE
    risk_summary: str = ""

    compliance_findings: list[ComplianceFinding] = Field(default_factory=list)
    overall_compliance: ComplianceStatus = ComplianceStatus.NEEDS_REVIEW
    missing_clauses: list[str] = Field(default_factory=list)

    suggestions: list[Suggestion] = Field(default_factory=list)
    version_diff: str = ""
    needs_human_review: bool = False

    errors: list[str] = Field(default_factory=list)
    current_step: str = ""
    step_log: list[StepEvent] = Field(default_factory=list)
    progress: float = 0.0
    warnings: list[str] = Field(default_factory=list)
    degraded_steps: set[str] = Field(default_factory=set)
    schema_failures: list[dict] = Field(default_factory=list)
