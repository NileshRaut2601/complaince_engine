"""Central dispatcher for deterministic rule evaluation."""

import re
from typing import Any, List, Optional
from pydantic import BaseModel, Field

from member_2_compliance_engine.schemas.requirement import (
    ComplianceMethod,
    ComplianceStatus,
    RequirementType,
    StructuredRequirement,
)
from member_2_compliance_engine.schemas.evidence import EvidenceItem
from member_2_compliance_engine.normalization.normalizer import (
    NormalizationError,
    extract_evidence_numeric_value,
    normalize_currency,
    normalize_date,
    normalize_duration,
    normalize_number,
    normalize_unit,
    STORAGE_TO_GB,
    CURRENCY_MULTIPLIERS,
)
from .numeric_rules import evaluate_numeric_comparison
from .string_rules import evaluate_string_rule
from .date_rules import evaluate_date_rule, evaluate_duration_rule
from .existence_rules import evaluate_existence_rule


class RuleEvaluationResult(BaseModel):
    """Structured result returned by deterministic rule evaluation."""

    status: ComplianceStatus
    observed_value: Optional[Any] = None
    reason: str
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)
    method: ComplianceMethod = ComplianceMethod.DETERMINISTIC_RULE


class RuleEvaluator:
    """Evaluates StructuredRequirements against EvidenceItems deterministically."""

    @staticmethod
    def evaluate(
        requirement: StructuredRequirement,
        evidence_items: List[EvidenceItem],
    ) -> RuleEvaluationResult:
        """Evaluate evidence against requirement using deterministic Python rules.

        Args:
            requirement: StructuredRequirement object
            evidence_items: Non-empty list of EvidenceItem objects

        Returns:
            RuleEvaluationResult with status, observed value, and auditable reason.
        """
        if not evidence_items:
            return RuleEvaluationResult(
                status=ComplianceStatus.MISSING,
                observed_value=None,
                reason=f"No evidence retrieved for requirement '{requirement.requirement_text}'.",
                confidence=1.0,
                method=ComplianceMethod.DETERMINISTIC_RULE,
            )

        req_type = requirement.requirement_type.lower()
        operator = requirement.operator.lower()

        # Check if requirement is explicitly marked ambiguous
        if req_type == RequirementType.AMBIGUOUS.value:
            return RuleEvaluationResult(
                status=ComplianceStatus.REVIEW,
                observed_value=None,
                reason="Requirement is flagged as ambiguous; requires expert review or LLM reasoning.",
                confidence=0.8,
                method=ComplianceMethod.DETERMINISTIC_RULE,
            )

        # Dispatch based on type or operator
        if req_type == RequirementType.DOCUMENT_EXISTS.value or operator == "exists":
            return RuleEvaluator._evaluate_existence(requirement, evidence_items)

        if req_type == RequirementType.DATE_COMPARISON.value:
            return RuleEvaluator._evaluate_date(requirement, evidence_items)

        if req_type == RequirementType.DURATION.value:
            return RuleEvaluator._evaluate_duration(requirement, evidence_items)

        if req_type in [
            RequirementType.EXACT_MATCH.value,
            RequirementType.CONTAINS.value,
            RequirementType.INCLUDES_ALL.value,
        ] or operator in ["contains", "includes_all", "exact_match"]:
            return RuleEvaluator._evaluate_string(requirement, evidence_items)

        # Default to numeric comparison
        return RuleEvaluator._evaluate_numeric(requirement, evidence_items)

    @staticmethod
    def _evaluate_existence(
        requirement: StructuredRequirement,
        evidence_items: List[EvidenceItem],
    ) -> RuleEvaluationResult:
        doc_name = str(requirement.required_value or requirement.parameter)
        passed, reason = evaluate_existence_rule(doc_name, evidence_items)
        status = ComplianceStatus.COMPLIANT if passed else ComplianceStatus.MISSING
        return RuleEvaluationResult(
            status=status,
            observed_value=doc_name if passed else "Not Found",
            reason=reason,
            confidence=1.0,
            method=ComplianceMethod.DETERMINISTIC_RULE,
        )

    @staticmethod
    def _evaluate_string(
        requirement: StructuredRequirement,
        evidence_items: List[EvidenceItem],
    ) -> RuleEvaluationResult:
        combined_text = " ".join(item.text for item in evidence_items)
        op = requirement.operator
        req_val = requirement.required_value

        try:
            passed, reason = evaluate_string_rule(
                operator=op,
                required_value=req_val,
                observed_text=combined_text,
            )
            return RuleEvaluationResult(
                status=ComplianceStatus.COMPLIANT if passed else ComplianceStatus.NON_COMPLIANT,
                observed_value=combined_text[:100] + ("..." if len(combined_text) > 100 else ""),
                reason=reason,
                confidence=1.0,
                method=ComplianceMethod.DETERMINISTIC_RULE,
            )
        except ValueError as exc:
            return RuleEvaluationResult(
                status=ComplianceStatus.REVIEW,
                observed_value=None,
                reason=f"String evaluation error: {exc}",
                confidence=0.7,
                method=ComplianceMethod.DETERMINISTIC_RULE,
            )

    @staticmethod
    def _evaluate_date(
        requirement: StructuredRequirement,
        evidence_items: List[EvidenceItem],
    ) -> RuleEvaluationResult:
        combined_text = " ".join(item.text for item in evidence_items)
        req_date = str(requirement.required_value)

        # Extract date from evidence text
        date_pattern = re.compile(r"\b(\d{1,2}[-/]\d{1,2}[-/]\d{4}|\d{4}[-/]\d{1,2}[-/]\d{1,2})\b")
        match = date_pattern.search(combined_text)
        if not match:
            return RuleEvaluationResult(
                status=ComplianceStatus.REVIEW,
                observed_value=None,
                reason=f"Could not extract a valid date from evidence to verify '{requirement.parameter}'.",
                confidence=0.7,
                method=ComplianceMethod.DETERMINISTIC_RULE,
            )

        obs_date_str = match.group(0)
        try:
            passed, reason = evaluate_date_rule(
                operator=requirement.operator,
                required_date_val=req_date,
                observed_date_val=obs_date_str,
            )
            return RuleEvaluationResult(
                status=ComplianceStatus.COMPLIANT if passed else ComplianceStatus.NON_COMPLIANT,
                observed_value=obs_date_str,
                reason=reason,
                confidence=1.0,
                method=ComplianceMethod.DETERMINISTIC_RULE,
            )
        except (ValueError, NormalizationError) as exc:
            return RuleEvaluationResult(
                status=ComplianceStatus.REVIEW,
                observed_value=obs_date_str,
                reason=f"Date evaluation ambiguity: {exc}",
                confidence=0.7,
                method=ComplianceMethod.DETERMINISTIC_RULE,
            )

    @staticmethod
    def _evaluate_duration(
        requirement: StructuredRequirement,
        evidence_items: List[EvidenceItem],
    ) -> RuleEvaluationResult:
        combined_text = " ".join(item.text for item in evidence_items)
        unit = requirement.unit or "years"

        try:
            obs_val, obs_unit = extract_evidence_numeric_value(
                combined_text,
                parameter=requirement.parameter,
                unit=unit,
            )
            passed, reason = evaluate_duration_rule(
                operator=requirement.operator,
                required_duration_val=requirement.required_value,
                observed_duration_val=obs_val,
                unit=unit,
            )
            return RuleEvaluationResult(
                status=ComplianceStatus.COMPLIANT if passed else ComplianceStatus.NON_COMPLIANT,
                observed_value=f"{obs_val} {obs_unit}",
                reason=reason,
                confidence=1.0,
                method=ComplianceMethod.DETERMINISTIC_RULE,
            )
        except (ValueError, NormalizationError) as exc:
            return RuleEvaluationResult(
                status=ComplianceStatus.REVIEW,
                observed_value=None,
                reason=f"Duration evaluation ambiguity: {exc}",
                confidence=0.7,
                method=ComplianceMethod.DETERMINISTIC_RULE,
            )

    @staticmethod
    def _evaluate_numeric(
        requirement: StructuredRequirement,
        evidence_items: List[EvidenceItem],
    ) -> RuleEvaluationResult:
        combined_text = " ".join(item.text for item in evidence_items)

        # Check for conditional disjunction indicators in evidence text (e.g. "OR", "either", "up to ... or")
        # that indicate an ambiguous configuration rather than a simple numeric figure
        disjunction_match = re.search(r"\b(or|either\b.*?\bor)\b", combined_text, re.IGNORECASE)
        if disjunction_match and ("×" in combined_text or "*" in combined_text or "/" in combined_text):
            return RuleEvaluationResult(
                status=ComplianceStatus.REVIEW,
                observed_value=combined_text.strip(),
                reason="Evidence specifies alternate configurations/disjunctions; requires semantic review.",
                confidence=0.85,
                method=ComplianceMethod.DETERMINISTIC_RULE,
            )

        unit = requirement.unit
        currency = requirement.currency
        req_val_raw = requirement.required_value

        # Normalize required value
        try:
            if currency or (unit and unit.lower() in CURRENCY_MULTIPLIERS):
                req_norm, curr_code = normalize_currency(
                    req_val_raw, unit=unit, currency=currency or "INR"
                )
                display_unit = f"{curr_code}"
            elif unit and unit.lower() in STORAGE_TO_GB:
                req_norm, storage_unit = normalize_unit(req_val_raw, unit=unit, target_unit="GB")
                display_unit = "GB"
            else:
                req_norm = normalize_number(req_val_raw, unit=unit)
                display_unit = unit or ""
        except NormalizationError as exc:
            return RuleEvaluationResult(
                status=ComplianceStatus.REVIEW,
                observed_value=None,
                reason=f"Failed to normalize required value '{req_val_raw}': {exc}",
                confidence=0.7,
                method=ComplianceMethod.DETERMINISTIC_RULE,
            )

        # Extract and normalize observed value from evidence
        try:
            obs_norm, obs_unit = extract_evidence_numeric_value(
                combined_text,
                parameter=requirement.parameter,
                unit=unit,
                currency=currency,
            )
        except NormalizationError as exc:
            return RuleEvaluationResult(
                status=ComplianceStatus.REVIEW,
                observed_value=None,
                reason=f"Could not safely extract numeric value for parameter '{requirement.parameter}': {exc}",
                confidence=0.7,
                method=ComplianceMethod.DETERMINISTIC_RULE,
            )

        # Run deterministic numeric comparison
        try:
            passed, reason = evaluate_numeric_comparison(
                operator=requirement.operator,
                required_value=req_norm,
                observed_value=obs_norm,
                parameter=requirement.parameter,
                unit_label=display_unit,
            )

            # Format pretty observed value for auditable result
            if currency or (unit and unit.lower() in CURRENCY_MULTIPLIERS):
                if obs_norm >= 10_000_000:
                    obs_display = f"₹{obs_norm / 10_000_000:g} Crores"
                elif obs_norm >= 100_000:
                    obs_display = f"₹{obs_norm / 100_000:g} Lakhs"
                else:
                    obs_display = f"₹{obs_norm:,.2f}"
            elif unit and unit.lower() in STORAGE_TO_GB:
                obs_display = f"{obs_norm} GB"
            else:
                obs_display = f"{obs_norm} {obs_unit or ''}".strip()

            return RuleEvaluationResult(
                status=ComplianceStatus.COMPLIANT if passed else ComplianceStatus.NON_COMPLIANT,
                observed_value=obs_display,
                reason=reason,
                confidence=1.0,
                method=ComplianceMethod.DETERMINISTIC_RULE,
            )
        except ValueError as exc:
            return RuleEvaluationResult(
                status=ComplianceStatus.REVIEW,
                observed_value=str(obs_norm),
                reason=f"Numeric comparison error: {exc}",
                confidence=0.7,
                method=ComplianceMethod.DETERMINISTIC_RULE,
            )

