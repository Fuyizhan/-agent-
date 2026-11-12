"""审查进度与报告响应模型。"""

from pydantic import BaseModel, Field


class TaskResponse(BaseModel):
    review_id: str
    status: str = "pending"
    message: str = ""


class StepEventSchema(BaseModel):
    step: str
    status: str
    message: str = ""
    started_at: str = ""
    finished_at: str | None = None


class DetailedReviewResponse(BaseModel):
    review_id: str
    status: str
    contract_type: str = ""
    filename: str = ""
    created_at: str = ""
    updated_at: str = ""
    clauses: list[dict] = Field(default_factory=list)
    risk_findings: list[dict] = Field(default_factory=list)
    risk_summary: str = ""
    overall_risk_level: str = "none"
    risk_score: float = 0.0
    compliance_findings: list[dict] = Field(default_factory=list)
    missing_clauses: list[str] = Field(default_factory=list)
    overall_compliance: str = "needs_review"
    suggestions: list[dict] = Field(default_factory=list)
    errors: list[str] = Field(default_factory=list)
    current_step: str = ""
    progress: float = 0.0
    step_log: list[StepEventSchema] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    degraded_steps: list[str] = Field(default_factory=list)
    has_quality_issues: bool = False
