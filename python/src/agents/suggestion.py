"""
修改建议Agent — 多Agent流水线第四步。

职责：
1. 针对风险点和合规问题生成修改建议
2. 生成条款级语义diff（版本对比）
3. 按优先级排序建议
4. 输出Track Changes格式的修改建议
"""

from __future__ import annotations

import logging

from langchain_core.messages import HumanMessage, SystemMessage

from ..config import settings, get_llm
from ..parsers.json_parser import parse_llm_json
from ..pipeline.state import (
    ComplianceFinding,
    ComplianceStatus,
    ContractReviewState,
    RiskFinding,
    RiskLevel,
    Suggestion,
)
from ..resilience import get_agent_breaker, resilient_call
from .prompt_guard import wrap_untrusted

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """你是一名资深的合同修改顾问。请根据风险评估和合规检查结果，为合同条款提供具体的修改建议。

要求：
1. 每个修改建议必须包含原始文本和建议修改后的文本
2. 修改建议应该具体、可操作，而不是笼统的方向性建议
3. 保持法律语言的严谨性
4. 优先处理高风险和不合规问题

请输出严格的JSON格式（不要输出其他内容）：

{
  "suggestions": [
    {
      "clause_id": "条款ID",
      "original_text": "原始条款文本",
      "suggested_text": "建议修改后的文本",
      "reason": "修改原因",
      "priority": "high/medium/low"
    }
  ]
}"""


class SuggestionAgent:
    """修改建议Agent：生成修改建议 + 版本对比 + 优先级排序。"""

    def __init__(self):
        self.llm = None
        self._breaker = get_agent_breaker("suggestion")

    def _ensure_llm(self):
        if self.llm is None:
            self.llm = get_llm()

    async def __call__(self, state: ContractReviewState) -> dict:
        """LangGraph节点函数：生成修改建议。"""
        logger.info("修改建议Agent开始处理 review_id=%s", state.review_id)

        if not state.risk_findings and not state.compliance_findings:
            return {"suggestions": []}

        try:
            self._ensure_llm()
            suggestions = await resilient_call(
                self._generate_suggestions,
                state.clauses,
                state.risk_findings,
                state.compliance_findings,
                max_retries=settings.LLM_MAX_RETRIES,
                timeout_seconds=settings.LLM_TIMEOUT,
                circuit_breaker=self._breaker,
            )

            for missing in state.missing_clauses:
                suggestions.append(
                    Suggestion(
                        clause_id="new",
                        original_text="（缺失）",
                        suggested_text=f"建议添加{missing}相关条款",
                        reason=f"合同缺少必要的「{missing}」条款",
                        priority=RiskLevel.HIGH,
                    )
                )

            suggestions.sort(
                key=lambda s: {
                    RiskLevel.HIGH: 0,
                    RiskLevel.MEDIUM: 1,
                    RiskLevel.LOW: 2,
                    RiskLevel.NONE: 3,
                }[s.priority]
            )

            logger.info("修改建议生成完成：%d条建议", len(suggestions))
            return {"suggestions": suggestions}

        except Exception as e:
            logger.exception("修改建议Agent异常 review_id=%s", state.review_id)
            fallback = self._fallback_suggestions(
                state.risk_findings, state.compliance_findings
            )
            return {
                "suggestions": fallback,
                "errors": state.errors + [f"修改建议生成失败: {str(e)}"],
                "warnings": state.warnings + [f"修改建议异常：{type(e).__name__}: {e}"],
                "degraded_steps": state.degraded_steps | {"suggestion"},
                "schema_failures": state.schema_failures,
            }

    async def _generate_suggestions(
        self,
        clauses: list,
        risk_findings: list[RiskFinding],
        compliance_findings: list[ComplianceFinding],
    ) -> list[Suggestion]:
        """调用大模型生成修改建议。"""
        clause_map = {c.id: c for c in clauses}

        context_parts = []

        for rf in risk_findings:
            if rf.risk_level in (RiskLevel.HIGH, RiskLevel.MEDIUM):
                clause = clause_map.get(rf.clause_id)
                clause_text = f"{clause.title}: {clause.content}" if clause else "未找到对应条款"
                context_parts.append(
                    f"[风险-{rf.risk_level.value}] 条款ID={rf.clause_id}\n"
                    f"条款内容: {clause_text}\n"
                    f"风险: {rf.description}\n"
                    f"依据: {rf.rationale}"
                )

        for cf in compliance_findings:
            if cf.status != ComplianceStatus.COMPLIANT:
                clause = clause_map.get(cf.clause_id)
                clause_text = f"{clause.title}: {clause.content}" if clause else "未找到对应条款"
                context_parts.append(
                    f"[合规-{cf.status.value}] 条款ID={cf.clause_id}\n"
                    f"条款内容: {clause_text}\n"
                    f"问题: {cf.issue}\n"
                    f"法规: {cf.regulation}"
                )

        if not context_parts:
            return []

        messages = [
            SystemMessage(content=SYSTEM_PROMPT),
            HumanMessage(
                content=(
                    "请根据以下风险和合规问题生成修改建议：\n\n"
                    + wrap_untrusted("contract", "\n\n---\n\n".join(context_parts))
                )
            ),
        ]
        response = await self.llm.ainvoke(messages)
        content = response.content.strip()
        result = parse_llm_json(content)
        suggestions = []
        for item in result.get("suggestions", []):
            try:
                priority = RiskLevel(item.get("priority", "medium"))
            except ValueError:
                priority = RiskLevel.MEDIUM
            suggestions.append(
                Suggestion(
                    clause_id=item.get("clause_id", ""),
                    original_text=item.get("original_text", ""),
                    suggested_text=item.get("suggested_text", ""),
                    reason=item.get("reason", ""),
                    priority=priority,
                )
            )
        return suggestions

    def _fallback_suggestions(
        self,
        risk_findings: list[RiskFinding],
        compliance_findings: list[ComplianceFinding],
    ) -> list[Suggestion]:
        """LLM失败时的回退方案。"""
        suggestions = []
        for rf in risk_findings:
            if rf.risk_level in (RiskLevel.HIGH, RiskLevel.MEDIUM):
                suggestions.append(
                    Suggestion(
                        clause_id=rf.clause_id,
                        original_text="",
                        suggested_text=f"建议修改：{rf.description}",
                        reason=rf.rationale or rf.description,
                        priority=rf.risk_level,
                    )
                )
        for cf in compliance_findings:
            if cf.status == ComplianceStatus.NON_COMPLIANT:
                suggestions.append(
                    Suggestion(
                        clause_id=cf.clause_id,
                        original_text="",
                        suggested_text=cf.recommendation or f"需修正：{cf.issue}",
                        reason=f"{cf.regulation}: {cf.issue}",
                        priority=RiskLevel.HIGH,
                    )
                )
        return suggestions
