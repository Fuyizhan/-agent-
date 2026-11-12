from __future__ import annotations

import pytest

from src.pipeline.graph import create_review_pipeline
from src.pipeline.state import ContractReviewState, ReviewStatus


@pytest.mark.asyncio
async def test_four_agent_pipeline_degrades_without_llm_key(tmp_path):
    contract = tmp_path / "contract.txt"
    contract.write_text(
        "第一条 服务内容\n乙方为甲方提供软件开发服务。\n"
        "第二条 违约责任\n乙方违约需支付三倍赔偿。\n"
        "第三条 争议解决\n双方协商解决争议。\n",
        encoding="utf-8",
    )
    state = ContractReviewState(document_path=str(contract), original_filename=contract.name)
    result = await create_review_pipeline().ainvoke(
        state.model_dump(mode="json"),
        config={"configurable": {"thread_id": state.review_id}},
    )
    final = ContractReviewState.model_validate(result)

    assert final.status == ReviewStatus.COMPLETED
    assert final.clauses
    assert final.progress == 1.0
    assert {event.step for event in final.step_log} >= {
        "clause_extraction",
        "risk_identification",
        "compliance_check",
        "suggestion",
    }
    assert final.degraded_steps
    assert final.warnings
