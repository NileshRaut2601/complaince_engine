"""Conflict analysis layer for bidder evidence across multiple pages/documents.

Detects genuine contradictory claims (e.g. Page 20: 65 Lakhs vs Page 45: 42 Lakhs for FY2025)
while distinguishing legitimate contextual variations (e.g. Turnover FY2024 vs FY2025).
"""

import re
from typing import List, Optional
from pydantic import BaseModel, Field

from member_2_compliance_engine.schemas.evidence import EvidenceItem
from member_2_compliance_engine.schemas.requirement import StructuredRequirement
from member_2_compliance_engine.normalization.normalizer import (
    NormalizationError,
    extract_evidence_numeric_value,
)


class ConflictAnalysisResult(BaseModel):
    """Result of analyzing multiple evidence items for contradictions."""

    has_conflict: bool = False
    conflict_reason: Optional[str] = None
    conflicting_items: List[EvidenceItem] = Field(default_factory=list)


def extract_contextual_markers(text: str) -> dict:
    """Extract contextual qualifiers such as financial years, dates, models, or scopes."""
    markers = {}

    # Financial year: e.g., FY 2023-24, FY24, FY2025, 2023-2024
    fy_match = re.search(
        r"\b(?:FY\s*[-:]?\s*(\d{2,4}(?:[-/]\d{2,4})?)|(\d{4}[-/]\d{2,4}))\b",
        text,
        re.IGNORECASE,
    )
    if fy_match:
        markers["financial_year"] = (fy_match.group(1) or fy_match.group(2)).strip().upper()

    # Specific date: e.g., as of 31/03/2024
    date_match = re.search(
        r"\b(?:as\s+of|dated?|on)\s+(\d{1,2}[-/]\d{1,2}[-/]\d{2,4})\b",
        text,
        re.IGNORECASE,
    )
    if date_match:
        markers["date"] = date_match.group(1).strip()

    # Model / Configuration: e.g., Model X, Config A
    model_match = re.search(
        r"\b(?:model|config(?:uration)?|variant)\s+([a-zA-Z0-9_\-]+)\b",
        text,
        re.IGNORECASE,
    )
    if model_match:
        markers["model"] = model_match.group(1).strip().lower()

    # Scope / Quantity: e.g., domestic vs export, standalone vs consolidated
    scope_match = re.search(
        r"\b(domestic|export|standalone|consolidated)\b",
        text,
        re.IGNORECASE,
    )
    if scope_match:
        markers["scope"] = scope_match.group(1).lower()

    return markers


def detect_evidence_conflict(
    requirement: StructuredRequirement,
    evidence_items: List[EvidenceItem],
) -> ConflictAnalysisResult:
    """Analyze retrieved evidence items for unresolved contradictory statements.

    Safety:
    - If Page A states 65 Lakhs and Page B states 42 Lakhs for the same parameter
      without distinct non-overlapping temporal or model contexts, flags as CONFLICT.
    - If Page A states FY2024: 42 Lakhs and Page B states FY2025: 65 Lakhs,
      recognizes context difference and does not automatically conflict.
    - If unable to safely determine whether they refer to the same condition,
      safely flags as CONFLICT (yielding REVIEW) rather than guessing.
    """
    if len(evidence_items) <= 1:
        return ConflictAnalysisResult(has_conflict=False)

    # Exclude non-quantitative requirements (string, contains, includes_all, document_exists)
    non_numeric_types = [
        "document_exists",
        "exact_match",
        "contains",
        "includes_all",
    ]
    non_numeric_ops = ["exists", "contains", "includes_all", "exact_match"]
    if requirement.requirement_type in non_numeric_types or requirement.operator in non_numeric_ops:
        return ConflictAnalysisResult(has_conflict=False)

    # Extract values and contexts
    extracted = []
    for item in evidence_items:
        try:
            val, unit = extract_evidence_numeric_value(
                item.text,
                parameter=requirement.parameter,
                unit=requirement.unit,
                currency=requirement.currency,
            )
            markers = extract_contextual_markers(item.text)
            extracted.append({
                "item": item,
                "value": val,
                "unit": unit,
                "markers": markers,
            })
        except NormalizationError:
            continue

    if len(extracted) < 2:
        return ConflictAnalysisResult(has_conflict=False)

    # Check pairwise comparisons for contradictory values
    for i in range(len(extracted)):
        for j in range(i + 1, len(extracted)):
            e1 = extracted[i]
            e2 = extracted[j]

            v1, v2 = e1["value"], e2["value"]
            # Check if values differ significantly
            if abs(v1 - v2) > 1e-4:
                m1, m2 = e1["markers"], e2["markers"]

                # Check contextual markers
                fy1 = m1.get("financial_year")
                fy2 = m2.get("financial_year")
                d1 = m1.get("date")
                d2 = m2.get("date")
                mod1 = m1.get("model")
                mod2 = m2.get("model")
                sc1 = m1.get("scope")
                sc2 = m2.get("scope")

                has_differentiating_context = (
                    (fy1 and fy2 and fy1 != fy2)
                    or (d1 and d2 and d1 != d2)
                    or (mod1 and mod2 and mod1 != mod2)
                    or (sc1 and sc2 and sc1 != sc2)
                )

                if not has_differentiating_context:
                    p1 = e1["item"].page
                    p2 = e2["item"].page
                    f1 = e1["item"].source_file
                    f2 = e2["item"].source_file

                    val1_str = e1["item"].text.strip()
                    val2_str = e2["item"].text.strip()

                    period_desc = f" for period {fy1}" if (fy1 and fy1 == fy2) else ""
                    conflict_msg = (
                        f"Conflicting values found in submitted documents for parameter '{requirement.parameter}'{period_desc}: "
                        f"{f1} (page {p1}) reports '{val1_str}' while "
                        f"{f2} (page {p2}) reports '{val2_str}'."
                    )
                    return ConflictAnalysisResult(
                        has_conflict=True,
                        conflict_reason=conflict_msg,
                        conflicting_items=[e1["item"], e2["item"]],
                    )

    return ConflictAnalysisResult(has_conflict=False)

