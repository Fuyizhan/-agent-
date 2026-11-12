"""单文件上传、审查进度查询和 PDF 报告下载。"""

from __future__ import annotations

import io
from pathlib import Path

from fastapi import APIRouter, Depends, File, UploadFile
from fastapi.responses import StreamingResponse

from ...pipeline.state import ComplianceStatus, ContractReviewState, RiskLevel, StepEvent
from ...services.deps import get_review_service
from ...services.review_service import ReviewService
from ..auth.dependencies import CurrentUser, get_current_user
from ..exceptions import InvalidFileFormatError, ReviewNotFoundError
from ..schemas.review import DetailedReviewResponse, StepEventSchema, TaskResponse
from ..upload_guard import UploadValidationError, validate_upload

router = APIRouter(prefix="/api/v1", tags=["review"])
ALLOWED_EXTENSIONS = {".pdf", ".docx", ".txt"}


def _risk_score(state: ContractReviewState) -> float:
    weights = {RiskLevel.HIGH: 30, RiskLevel.MEDIUM: 15, RiskLevel.LOW: 5}
    score = sum(weights.get(item.risk_level, 0) for item in state.risk_findings)
    if state.overall_compliance == ComplianceStatus.NON_COMPLIANT:
        score += 10
    if state.missing_clauses:
        score += min(len(state.missing_clauses) * 5, 20)
    return round(min(score, 100), 1)


def _step_log(events: list[StepEvent]) -> list[StepEventSchema]:
    return [
        StepEventSchema(
            step=event.step,
            status=event.status,
            message=event.message,
            started_at=event.started_at.isoformat() if event.started_at else "",
            finished_at=event.finished_at.isoformat() if event.finished_at else None,
        )
        for event in events
    ]


def _to_detail(state: ContractReviewState) -> DetailedReviewResponse:
    return DetailedReviewResponse(
        review_id=state.review_id,
        status=state.status.value,
        contract_type=state.contract_type,
        filename=state.original_filename,
        created_at=state.created_at.isoformat() if state.created_at else "",
        updated_at=state.updated_at.isoformat() if state.updated_at else "",
        clauses=[clause.model_dump(mode="json") for clause in state.clauses],
        risk_findings=[finding.model_dump(mode="json") for finding in state.risk_findings],
        risk_summary=state.risk_summary,
        overall_risk_level=state.overall_risk_level.value,
        risk_score=_risk_score(state),
        compliance_findings=[finding.model_dump(mode="json") for finding in state.compliance_findings],
        missing_clauses=state.missing_clauses,
        overall_compliance=state.overall_compliance.value,
        suggestions=[suggestion.model_dump(mode="json") for suggestion in state.suggestions],
        errors=state.errors,
        current_step=state.current_step,
        progress=state.progress,
        step_log=_step_log(state.step_log),
        warnings=state.warnings,
        degraded_steps=sorted(state.degraded_steps),
        has_quality_issues=bool(state.warnings or state.degraded_steps or state.errors),
    )


@router.post("/review/upload", response_model=TaskResponse)
async def upload_review(
    file: UploadFile = File(...),
    svc: ReviewService = Depends(get_review_service),
    user: CurrentUser = Depends(get_current_user),
):
    if not file.filename:
        raise InvalidFileFormatError(format="(空文件名)")
    extension = Path(file.filename).suffix.lower()
    if extension not in ALLOWED_EXTENSIONS:
        raise InvalidFileFormatError(format=extension)

    content = await file.read()
    try:
        safe_name = validate_upload(file.filename, content)
    except UploadValidationError as exc:
        raise InvalidFileFormatError(format=str(exc)) from exc

    review_id = await svc.start_from_file(safe_name, content, user_id=user.id)
    return TaskResponse(review_id=review_id, status="pending", message="审查任务已提交")


@router.get("/review/{review_id}", response_model=DetailedReviewResponse)
async def get_review_detail(
    review_id: str,
    svc: ReviewService = Depends(get_review_service),
):
    state = await svc.get(review_id)
    if state is None:
        raise ReviewNotFoundError(review_id=review_id)
    return _to_detail(state)


@router.get("/review/{review_id}/report")
async def download_report(
    review_id: str,
    svc: ReviewService = Depends(get_review_service),
):
    state = await svc.get(review_id)
    if state is None:
        raise ReviewNotFoundError(review_id=review_id)

    from ...services.report_service import generate_report

    return StreamingResponse(
        io.BytesIO(generate_report(state)),
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="review_{review_id}.pdf"'},
    )
