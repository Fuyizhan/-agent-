from __future__ import annotations

from src.pipeline.state import Clause, ClauseCategory, ContractReviewState, RiskFinding, RiskLevel, Suggestion
from src.services.report_service import generate_report


def test_pdf_report_contains_four_sections():
    state = ContractReviewState(original_filename="contract.txt", contract_type="服务合同")
    state.clauses = [Clause(title="第一条", content="服务内容", category=ClauseCategory.OTHER)]
    state.risk_findings = [RiskFinding(
        clause_id=state.clauses[0].id,
        risk_level=RiskLevel.HIGH,
        risk_type="unfair_penalty",
        description="违约金过高",
    )]
    state.suggestions = [Suggestion(
        clause_id=state.clauses[0].id,
        original_text="三倍赔偿",
        suggested_text="合理赔偿",
        reason="降低风险",
        priority=RiskLevel.HIGH,
    )]
    report = generate_report(state)
    assert report.startswith(b"%PDF")
    assert len(report) > 1000
