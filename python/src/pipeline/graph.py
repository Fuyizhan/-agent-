"""LangGraph 四 Agent 审查流水线。"""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime
from typing import Any, Awaitable, Callable

from langgraph.graph import END, StateGraph

from ..agents.clause_extraction import ClauseExtractionAgent
from ..agents.compliance_check import ComplianceCheckAgent
from ..agents.risk_identification import RiskIdentificationAgent
from ..agents.suggestion import SuggestionAgent
from .state import (
    ContractReviewState,
    PIPELINE_STEPS,
    ReviewStatus,
    RiskLevel,
    STEP_LABELS,
    StepEvent,
)

logger = logging.getLogger(__name__)
_progress_callbacks: dict[str, Callable[[ContractReviewState], Awaitable[None]]] = {}


def set_progress_callback(
    review_id: str,
    callback: Callable[[ContractReviewState], Awaitable[None]] | None,
) -> None:
    if callback is None:
        _progress_callbacks.pop(review_id, None)
    else:
        _progress_callbacks[review_id] = callback


async def _fire_progress(state: ContractReviewState) -> None:
    callback = _progress_callbacks.get(state.review_id)
    if callback is not None:
        try:
            await callback(state)
        except Exception:
            logger.exception("进度回调失败 review_id=%s", state.review_id)


def _step_message(state: ContractReviewState, step: str) -> str:
    if step == "clause_extraction":
        return f"提取了 {len(state.clauses)} 条条款"
    if step == "risk_identification":
        high = sum(1 for item in state.risk_findings if item.risk_level == RiskLevel.HIGH)
        return f"发现 {len(state.risk_findings)} 个风险（高风险 {high} 个）"
    if step == "compliance_check":
        return f"合规检查完成，缺失 {len(state.missing_clauses)} 项必备条款"
    if step == "suggestion":
        return f"生成了 {len(state.suggestions)} 条修改建议"
    return f"{STEP_LABELS.get(step, step)}完成"


def _with_progress(step: str, agent: Any) -> Callable[[ContractReviewState], Awaitable[dict]]:
    async def wrapped(state: ContractReviewState) -> dict:
        event = StepEvent(
            step=step,
            status="running",
            message=f"{STEP_LABELS[step]}中...",
            started_at=datetime.now(),
        )
        state.step_log.append(event)
        state.current_step = step
        await _fire_progress(state)
        try:
            result = await agent(state) or {}
        except Exception as exc:
            event.status = "error"
            event.finished_at = datetime.now()
            event.message = f"{STEP_LABELS[step]}失败: {exc}"
            state.errors.append(f"{step}: {exc}")
            state.current_step = ""
            await _fire_progress(state)
            raise

        for key, value in result.items():
            if hasattr(state, key):
                setattr(state, key, value)
        event.status = "done"
        event.finished_at = datetime.now()
        event.message = _step_message(state, step)
        try:
            state.progress = round((PIPELINE_STEPS.index(step) + 1) / len(PIPELINE_STEPS), 3)
        except ValueError:
            state.progress = 1.0
        state.current_step = ""
        await _fire_progress(state)
        result.update({
            "step_log": state.step_log,
            "progress": state.progress,
            "current_step": state.current_step,
        })
        return result

    wrapped.__name__ = f"wrapped_{step}"
    return wrapped


async def _run_parallel_analysis(
    state: ContractReviewState,
    risk_agent: RiskIdentificationAgent,
    compliance_agent: ComplianceCheckAgent,
) -> dict:
    started_at = datetime.now()
    risk_event = StepEvent(
        step="risk_identification",
        status="running",
        message="风险识别中...",
        started_at=started_at,
    )
    compliance_event = StepEvent(
        step="compliance_check",
        status="running",
        message="合规检查中...",
        started_at=started_at,
    )
    state.step_log.extend([risk_event, compliance_event])
    state.current_step = "risk_identification,compliance_check"
    await _fire_progress(state)

    risk_state = state.model_copy(deep=True)
    compliance_state = state.model_copy(deep=True)
    try:
        risk_result, compliance_result = await asyncio.gather(
            risk_agent(risk_state),
            compliance_agent(compliance_state),
        )
    except Exception as exc:
        finished_at = datetime.now()
        for event in (risk_event, compliance_event):
            event.status = "error"
            event.finished_at = finished_at
            event.message = f"并行分析失败: {exc}"
        state.current_step = ""
        state.errors.append(f"parallel_analysis: {exc}")
        await _fire_progress(state)
        raise

    merged: dict[str, Any] = {}
    for result in (risk_result or {}, compliance_result or {}):
        for key, value in result.items():
            if key in ("errors", "warnings", "schema_failures"):
                merged.setdefault(key, [])
                merged[key].extend(value or [])
            elif key == "degraded_steps":
                merged.setdefault(key, set())
                merged[key] |= set(value or [])
            else:
                merged[key] = value

    for key, value in merged.items():
        if hasattr(state, key):
            setattr(state, key, value)

    finished_at = datetime.now()
    risk_event.status = "done"
    risk_event.finished_at = finished_at
    risk_event.message = _step_message(state, "risk_identification")
    compliance_event.status = "done"
    compliance_event.finished_at = finished_at
    compliance_event.message = _step_message(state, "compliance_check")
    state.progress = 0.75
    state.current_step = ""
    merged.update({
        "step_log": state.step_log,
        "progress": state.progress,
        "current_step": "",
    })
    await _fire_progress(state)
    return merged


def _complete_node(state: ContractReviewState) -> dict:
    return {"status": ReviewStatus.COMPLETED, "progress": 1.0, "current_step": ""}


def create_review_pipeline():
    graph = StateGraph(ContractReviewState)
    graph.add_node("clause_extraction", _with_progress("clause_extraction", ClauseExtractionAgent()))
    risk_agent = RiskIdentificationAgent()
    compliance_agent = ComplianceCheckAgent()

    async def run_parallel(state: ContractReviewState) -> dict:
        return await _run_parallel_analysis(state, risk_agent, compliance_agent)

    graph.add_node("parallel_analysis", run_parallel)
    graph.add_node("suggestion", _with_progress("suggestion", SuggestionAgent()))
    graph.add_node("complete", _complete_node)
    graph.set_entry_point("clause_extraction")
    graph.add_edge("clause_extraction", "parallel_analysis")
    graph.add_edge("parallel_analysis", "suggestion")
    graph.add_edge("suggestion", "complete")
    graph.add_edge("complete", END)
    return graph.compile()
