"""将审查状态生成 PDF 报告。"""

from __future__ import annotations

import io
from datetime import datetime
from html import escape

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.cidfonts import UnicodeCIDFont
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from ..pipeline.state import ContractReviewState

_FONT = "STSong-Light"
pdfmetrics.registerFont(UnicodeCIDFont(_FONT))
_PRIMARY = colors.HexColor("#1a56db")
_BORDER = colors.HexColor("#d1d5db")
_LIGHT = colors.HexColor("#f3f4f6")


def _styles():
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(
        name="CNTitle", parent=styles["Title"], fontName=_FONT,
        fontSize=24, leading=30, textColor=_PRIMARY, spaceAfter=12,
    ))
    styles.add(ParagraphStyle(
        name="CNSection", parent=styles["Heading2"], fontName=_FONT,
        fontSize=14, leading=18, textColor=_PRIMARY, spaceBefore=16, spaceAfter=8,
    ))
    styles.add(ParagraphStyle(
        name="CNBody", parent=styles["Normal"], fontName=_FONT,
        fontSize=10, leading=14, spaceAfter=5,
    ))
    return styles


def _table(headers: list[str], rows: list[list[str]], widths: list[float] | None = None) -> Table:
    escaped_rows = [
        [Paragraph(escape(str(cell)), _BODY_STYLE) for cell in row]
        for row in rows
    ]
    table = Table([headers] + escaped_rows, colWidths=widths, repeatRows=1)
    table.setStyle(TableStyle([
        ("FONTNAME", (0, 0), (-1, -1), _FONT),
        ("BACKGROUND", (0, 0), (-1, 0), _PRIMARY),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("GRID", (0, 0), (-1, -1), 0.5, _BORDER),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, _LIGHT]),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))
    return table


_BODY_STYLE: ParagraphStyle


def generate_report(state: ContractReviewState) -> bytes:
    global _BODY_STYLE
    styles = _styles()
    _BODY_STYLE = styles["CNBody"]
    output = io.BytesIO()
    doc = SimpleDocTemplate(
        output,
        pagesize=A4,
        topMargin=2 * cm,
        bottomMargin=2 * cm,
        leftMargin=2 * cm,
        rightMargin=2 * cm,
    )
    story = [
        Paragraph("合同审查报告", styles["CNTitle"]),
        Paragraph(f"审查编号：{escape(state.review_id)}", styles["CNBody"]),
        Paragraph(f"原始文件：{escape(state.original_filename or '未命名')}", styles["CNBody"]),
        Paragraph(f"合同类型：{escape(state.contract_type or '未识别')}", styles["CNBody"]),
        Paragraph(f"生成时间：{datetime.now().strftime('%Y-%m-%d %H:%M')}", styles["CNBody"]),
        Spacer(1, 10),
        Paragraph("一、审查摘要", styles["CNSection"]),
        _table(["指标", "结果"], [
            ["风险等级", state.overall_risk_level.value],
            ["合规状态", state.overall_compliance.value],
            ["条款数", str(len(state.clauses))],
            ["风险发现数", str(len(state.risk_findings))],
            ["合规发现数", str(len(state.compliance_findings))],
            ["修改建议数", str(len(state.suggestions))],
        ], [6 * cm, 10 * cm]),
    ]
    if state.risk_summary:
        story.extend([Spacer(1, 6), Paragraph(escape(state.risk_summary), styles["CNBody"])])

    story.append(Paragraph("二、条款提取", styles["CNSection"]))
    if state.clauses:
        story.append(_table(
            ["编号", "标题", "类别", "内容"],
            [[c.id, c.title, c.category.value, c.content[:120]] for c in state.clauses],
            [2 * cm, 3.5 * cm, 2.5 * cm, 8 * cm],
        ))
    else:
        story.append(Paragraph("未提取到条款。", styles["CNBody"]))

    story.append(Paragraph("三、风险识别", styles["CNSection"]))
    if state.risk_findings:
        story.append(_table(
            ["条款", "等级", "类型", "说明"],
            [[r.clause_id, r.risk_level.value, r.risk_type, r.description] for r in state.risk_findings],
            [2 * cm, 2 * cm, 3.5 * cm, 8.5 * cm],
        ))
    else:
        story.append(Paragraph("未发现风险条款。", styles["CNBody"]))

    story.append(Paragraph("四、合规检查", styles["CNSection"]))
    if state.compliance_findings:
        story.append(_table(
            ["条款", "状态", "法规", "问题"],
            [[c.clause_id, c.status.value, c.regulation, c.issue] for c in state.compliance_findings],
            [2 * cm, 2 * cm, 4 * cm, 8 * cm],
        ))
    else:
        story.append(Paragraph("未发现合规问题。", styles["CNBody"]))
    if state.missing_clauses:
        story.append(Paragraph("缺失条款：" + escape("、".join(state.missing_clauses)), styles["CNBody"]))

    story.append(Paragraph("五、修改建议", styles["CNSection"]))
    if state.suggestions:
        for index, suggestion in enumerate(state.suggestions, 1):
            story.extend([
                Paragraph(f"建议 {index}（{suggestion.priority.value}）", styles["CNBody"]),
                Paragraph("原文：" + escape(suggestion.original_text or "无"), styles["CNBody"]),
                Paragraph("建议：" + escape(suggestion.suggested_text), styles["CNBody"]),
                Paragraph("原因：" + escape(suggestion.reason), styles["CNBody"]),
                Spacer(1, 6),
            ])
    else:
        story.append(Paragraph("无需修改。", styles["CNBody"]))

    quality_notes = list(dict.fromkeys(state.warnings + state.errors))
    if state.degraded_steps:
        quality_notes.append("降级步骤：" + "、".join(sorted(state.degraded_steps)))
    if quality_notes:
        story.append(Paragraph("备注", styles["CNSection"]))
        for note in quality_notes:
            story.append(Paragraph(escape(note), styles["CNBody"]))

    doc.build(story)
    return output.getvalue()
