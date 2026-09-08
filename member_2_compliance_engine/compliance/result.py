"""Auditable compliance result formatting and export helpers."""

import json
from typing import Any, Dict, List
from member_2_compliance_engine.schemas.compliance_result import ComplianceResult


def format_result_as_dict(result: ComplianceResult) -> Dict[str, Any]:
    """Convert ComplianceResult to a serializable dictionary with enum values."""
    return result.model_dump(mode="json")


def format_result_as_json(result: ComplianceResult, indent: int = 2) -> str:
    """Format ComplianceResult as indented, auditable JSON string."""
    return json.dumps(format_result_as_dict(result), indent=indent, ensure_ascii=False)


def format_audit_report(results: List[ComplianceResult], bidder_id: str) -> str:
    """Generate human-readable markdown audit summary for a bidder's evaluation."""
    lines = [
        f"# Bid Compliance Audit Report",
        f"**Bidder ID**: `{bidder_id}`",
        f"**Total Requirements Evaluated**: {len(results)}",
        "",
        "| Rule ID | Status | Method | Confidence | Observed Value | Rationale |",
        "| :--- | :--- | :--- | :--- | :--- | :--- |",
    ]

    for r in results:
        obs = str(r.observed_value or "None").replace("|", "\\|")
        reason = r.reason.replace("|", "\\|")
        lines.append(
            f"| `{r.rule_id}` | **{r.status.value}** | `{r.method.value}` | "
            f"{r.confidence:.2f} | {obs} | {reason} |"
        )

    lines.append("")
    return "\n".join(lines)

