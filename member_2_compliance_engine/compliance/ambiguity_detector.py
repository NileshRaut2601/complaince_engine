"""Deterministic Ambiguity Detector for bidder evidence and requirements.

Detects disjunctive, conditional, optional, or alternative configurations
without relying on an LLM.

Enforces government procurement audit standards:
When evidence contains ambiguous conditions, never guess or choose the
favorable interpretation. Immediately flag as REVIEW for human officer review.
"""

import re
from typing import List, Optional
from pydantic import BaseModel, Field

from member_2_compliance_engine.schemas.evidence import EvidenceItem
from member_2_compliance_engine.schemas.requirement import StructuredRequirement


class AmbiguityAnalysisResult(BaseModel):
    """Result of analyzing evidence for ambiguous or conditional statements."""

    is_ambiguous: bool = False
    ambiguity_reason: Optional[str] = None
    flagged_items: List[EvidenceItem] = Field(default_factory=list)


# Controlled ambiguous patterns in evidence text
AMBIGUITY_PATTERNS = [
    (re.compile(r"\b(?:or|either\b.*?\bor)\b", re.IGNORECASE), "Disjunctive choice / alternate configuration ('OR') detected"),
    (re.compile(r"\b(?:alternatively|alternate|alternative option)\b", re.IGNORECASE), "Alternative configuration specified"),
    (re.compile(r"\b(?:may be|might be|can be configured as)\b", re.IGNORECASE), "Non-committal specification ('may be')"),
    (re.compile(r"\b(?:up to\b.*?\bor)\b", re.IGNORECASE), "Conditional capacity specification ('up to ... or')"),
    (re.compile(r"\b(?:depending on configuration|based on configuration)\b", re.IGNORECASE), "Configuration-dependent commitment"),
    (re.compile(r"\b(?:optional|optionally|subject to|as applicable)\b", re.IGNORECASE), "Conditional or optional commitment"),
]


def detect_evidence_ambiguity(
    requirement: StructuredRequirement,
    evidence_items: List[EvidenceItem],
) -> AmbiguityAnalysisResult:
    """Analyze evidence items for ambiguous, conditional, or disjunctive constructs.

    Args:
        requirement: Buyer's StructuredRequirement
        evidence_items: Retrieved evidence snippets

    Returns:
        AmbiguityAnalysisResult indicating whether human review is required.
    """
    if not evidence_items:
        return AmbiguityAnalysisResult(is_ambiguous=False)

    flagged = []
    reasons = []

    for item in evidence_items:
        text = item.text.strip()

        # Check if evidence contains hardware/configuration multiplication disjunctions (e.g. 8x192GB OR 16x96GB)
        has_multiplication = bool(re.search(r"\d+\s*[×*xX]\s*\d+", text))
        has_or = bool(re.search(r"\b(?:or|either)\b", text, re.IGNORECASE))

        if has_multiplication and has_or:
            flagged.append(item)
            reasons.append(
                f"Evidence on page {item.page} of {item.source_file} specifies alternative configurations "
                f"('{text}') and does not firmly commit to the required specification."
            )
            continue

        # Check standard ambiguity patterns
        for pattern, desc in AMBIGUITY_PATTERNS:
            if pattern.search(text):
                # Check if it affects the requirement parameter
                flagged.append(item)
                reasons.append(
                    f"Evidence on page {item.page} of {item.source_file} contains ambiguous language: {desc}."
                )
                break

    if flagged:
        combined_reason = "; ".join(reasons)
        return AmbiguityAnalysisResult(
            is_ambiguous=True,
            ambiguity_reason=combined_reason,
            flagged_items=flagged,
        )

    return AmbiguityAnalysisResult(is_ambiguous=False)

