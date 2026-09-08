"""Pydantic schema for the final auditable compliance verdict."""

from typing import Any, List, Optional
from pydantic import BaseModel, Field, field_validator

from .requirement import ComplianceStatus, ComplianceMethod
from .evidence import EvidenceItem


class ComplianceResult(BaseModel):
    """Standardized auditable compliance result returned by Member 2.

    Preserves the full audit trail:
    - Exactly which requirement was verified
    - Required vs observed values
    - Direct page citations and unchanged evidence snippets
    - Decision method (deterministic_rule or manual_review)
    - Confidence score
    """

    bidder_id: str = Field(
        ...,
        description="Unique identifier of the evaluated bidder",
    )
    rule_id: str = Field(
        ...,
        description="Requirement rule identifier",
    )
    status: ComplianceStatus = Field(
        ...,
        description="Final verdict: COMPLIANT, NON_COMPLIANT, MISSING, or REVIEW",
    )
    requirement: str = Field(
        ...,
        description="Buyer requirement statement or parameter description",
    )
    required_value: Any = Field(
        ...,
        description="Expected threshold, string, document, or specification",
    )
    observed_value: Optional[Any] = Field(
        default=None,
        description="Observed value extracted from bidder documentation",
    )
    reason: str = Field(
        ...,
        description="Detailed audit rationale for the verdict",
    )
    evidence: List[EvidenceItem] = Field(
        default_factory=list,
        description="Retrieved evidence snippets used to evaluate the rule",
    )
    confidence: float = Field(
        default=1.0,
        ge=0.0,
        le=1.0,
        description="Confidence score bounded in [0.0, 1.0]",
    )
    method: ComplianceMethod = Field(
        default=ComplianceMethod.DETERMINISTIC_RULE,
        description="Evaluation method: deterministic_rule or manual_review",
    )

    @field_validator("confidence")
    @classmethod
    def round_confidence(cls, v: float) -> float:
        return round(v, 4)

