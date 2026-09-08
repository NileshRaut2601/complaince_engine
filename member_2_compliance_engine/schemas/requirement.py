"""Pydantic schemas for tender requirements and compliance statuses."""

from enum import Enum
from typing import Any, Optional
from pydantic import BaseModel, Field, field_validator


class ComplianceStatus(str, Enum):
    """Auditable final compliance verdict."""
    COMPLIANT = "COMPLIANT"
    NON_COMPLIANT = "NON_COMPLIANT"
    MISSING = "MISSING"
    REVIEW = "REVIEW"


class ComplianceMethod(str, Enum):
    """Method used to arrive at the compliance verdict."""
    DETERMINISTIC_RULE = "deterministic_rule"
    MANUAL_REVIEW = "manual_review"


class RequirementType(str, Enum):
    """Categorization of requirement evaluation type."""
    NUMERIC_COMPARISON = "numeric_comparison"
    EXACT_MATCH = "exact_match"
    CONTAINS = "contains"
    INCLUDES_ALL = "includes_all"
    DOCUMENT_EXISTS = "document_exists"
    DATE_COMPARISON = "date_comparison"
    DURATION = "duration"
    BOOLEAN = "boolean"
    AMBIGUOUS = "ambiguous"


class OperatorEnum(str, Enum):
    """Supported rule evaluation operators."""
    EQ = "=="
    GTE = ">="
    LTE = "<="
    LT = "<"
    GT = ">"
    CONTAINS = "contains"
    INCLUDES_ALL = "includes_all"
    EXISTS = "exists"


class CategoryEnum(str, Enum):
    """Tender requirement domain category."""
    FINANCIAL = "financial"
    TECHNICAL = "technical"
    EXPERIENCE = "experience"
    COMPLIANCE = "compliance"
    LEGAL = "legal"
    GENERAL = "general"


class StructuredRequirement(BaseModel):
    """Machine-readable requirement extracted from a buyer's tender document."""

    rule_id: str = Field(
        ...,
        description="Unique identifier for the requirement rule (e.g., 'R001')",
        min_length=1,
    )
    category: str = Field(
        default="general",
        description="Requirement category (e.g., 'financial', 'technical')",
    )
    parameter: str = Field(
        ...,
        description="Specific metric or subject of requirement (e.g., 'annual_turnover', 'RAM')",
        min_length=1,
    )
    operator: str = Field(
        ...,
        description="Evaluation operator (e.g., '>=', '==', 'contains', 'exists')",
    )
    required_value: Any = Field(
        ...,
        description="Threshold, target string, quantity, or existence specification",
    )
    unit: Optional[str] = Field(
        default=None,
        description="Unit of measurement if applicable (e.g., 'lakhs', 'TB', 'years')",
    )
    currency: Optional[str] = Field(
        default=None,
        description="Currency code if applicable (e.g., 'INR')",
    )
    requirement_text: str = Field(
        ...,
        description="Exact raw requirement clause from the buyer's tender document",
        min_length=1,
    )
    requirement_type: str = Field(
        default=RequirementType.NUMERIC_COMPARISON.value,
        description="Type of evaluation required for this rule",
    )

    @field_validator("rule_id", "parameter", "requirement_text", mode="before")
    @classmethod
    def validate_non_empty_strings(cls, v: Any, info) -> Any:
        if isinstance(v, str):
            v_stripped = v.strip()
            if not v_stripped:
                raise ValueError(f"Field '{info.field_name}' cannot be empty or whitespace only.")
            return v_stripped
        return v

    @field_validator("operator", mode="before")
    @classmethod
    def normalize_operator(cls, v: Any) -> str:
        if not isinstance(v, str):
            raise ValueError("Operator must be a string.")
        op = v.strip().lower()
        mapping = {
            "=": "==",
            "==": "==",
            "eq": "==",
            "equals": "==",
            ">=": ">=",
            "gte": ">=",
            "<=": "<=",
            "lte": "<=",
            ">": ">",
            "gt": ">",
            "<": "<",
            "lt": "<",
            "contains": "contains",
            "contain": "contains",
            "includes": "contains",
            "includes_all": "includes_all",
            "include_all": "includes_all",
            "exists": "exists",
            "exist": "exists",
            "is_present": "exists",
        }
        if op not in mapping:
            raise ValueError(f"Unsupported operator '{v}'. Supported: {list(mapping.keys())}")
        return mapping[op]

    @field_validator("category", mode="before")
    @classmethod
    def normalize_category(cls, v: Any) -> str:
        if isinstance(v, str):
            return v.strip().lower()
        return str(v)

    @field_validator("requirement_type", mode="before")
    @classmethod
    def normalize_req_type(cls, v: Any) -> str:
        if isinstance(v, str):
            v_norm = v.strip().lower().replace(" ", "_").replace("-", "_")
            valid_types = {rt.value for rt in RequirementType}
            if v_norm in valid_types:
                return v_norm
            # If unrecognized, safely flag as ambiguous
            return RequirementType.AMBIGUOUS.value
        return str(v)
