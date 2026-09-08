"""Central Deterministic Compliance Classifier for Member 2.

Implements the strict government tender evaluation priority:
1. Validate requirement & evidence schemas
2. Check evidence existence -> MISSING if empty
3. Ambiguity detection -> REVIEW (manual_review) if conditional/disjunctive
4. Conflict detection -> REVIEW (manual_review) if contradictory values across pages
5. Deterministic rule evaluation -> COMPLIANT (deterministic_rule) or NON_COMPLIANT (deterministic_rule)
6. If evaluation is uncertain/unparseable -> REVIEW (manual_review)

Zero LLM dependency. 100% offline, explainable, and auditable.
"""

from typing import Any, Dict, List, Optional, Union
from pydantic import ValidationError

from member_2_compliance_engine.schemas.compliance_result import (
    ComplianceMethod,
    ComplianceResult,
    ComplianceStatus,
)
from member_2_compliance_engine.schemas.evidence import BidderEvidencePayload, EvidenceItem
from member_2_compliance_engine.schemas.requirement import (
    RequirementType,
    StructuredRequirement,
)
from member_2_compliance_engine.rule_engine.evaluator import RuleEvaluator
from member_2_compliance_engine.compliance.ambiguity_detector import detect_evidence_ambiguity
from member_2_compliance_engine.compliance.conflict_detector import detect_evidence_conflict


class ComplianceClassifier:
    """Evaluates bidder evidence against buyer requirements to produce auditable verdicts."""

    def evaluate_bid(
        self,
        requirement: Union[StructuredRequirement, Dict[str, Any]],
        payload: Union[BidderEvidencePayload, Dict[str, Any]],
    ) -> ComplianceResult:
        """Evaluate a single requirement against retrieved evidence deterministically.

        Args:
            requirement: StructuredRequirement or raw dict
            payload: BidderEvidencePayload or raw dict delivered by Member 1's RAG system

        Returns:
            ComplianceResult: Auditable verdict with confidence, reason, and preserved evidence.

        Raises:
            ValidationError: If either requirement or evidence payload is malformed.
        """
        # 1. Validate requirement schema
        if isinstance(requirement, dict):
            req_model = StructuredRequirement.model_validate(requirement)
        elif isinstance(requirement, StructuredRequirement):
            req_model = requirement
        else:
            raise TypeError("Requirement must be a StructuredRequirement instance or valid dict.")

        # 2. Validate evidence payload schema
        if isinstance(payload, dict):
            pay_model = BidderEvidencePayload.model_validate(payload)
        elif isinstance(payload, BidderEvidencePayload):
            pay_model = payload
        else:
            raise TypeError("Payload must be a BidderEvidencePayload instance or valid dict.")

        # Ensure rule IDs match
        if req_model.rule_id != pay_model.rule_id:
            raise ValueError(
                f"Rule ID mismatch: requirement rule_id is '{req_model.rule_id}', "
                f"but payload rule_id is '{pay_model.rule_id}'."
            )

        req_val_str = self._format_required_value(req_model)

        # 3. Check evidence availability (Priority 1: Evidence exists?)
        if not pay_model.evidence:
            return ComplianceResult(
                bidder_id=pay_model.bidder_id,
                rule_id=req_model.rule_id,
                status=ComplianceStatus.MISSING,
                requirement=req_model.requirement_text,
                required_value=req_val_str,
                observed_value=None,
                reason=f"No evidence was retrieved for the required condition: '{req_model.requirement_text}'.",
                evidence=[],
                confidence=1.0,
                method=ComplianceMethod.DETERMINISTIC_RULE,
            )

        # 4. Check for Ambiguity (Priority 2a: Ambiguity Detection)
        if req_model.requirement_type == RequirementType.AMBIGUOUS.value:
            return ComplianceResult(
                bidder_id=pay_model.bidder_id,
                rule_id=req_model.rule_id,
                status=ComplianceStatus.REVIEW,
                requirement=req_model.requirement_text,
                required_value=req_val_str,
                observed_value="Ambiguous Requirement Specification",
                reason=f"Requirement '{req_model.requirement_text}' is flagged as ambiguous; deferred to human procurement officer.",
                evidence=pay_model.evidence,
                confidence=1.0,
                method=ComplianceMethod.MANUAL_REVIEW,
            )

        ambiguity_analysis = detect_evidence_ambiguity(req_model, pay_model.evidence)
        if ambiguity_analysis.is_ambiguous:
            return ComplianceResult(
                bidder_id=pay_model.bidder_id,
                rule_id=req_model.rule_id,
                status=ComplianceStatus.REVIEW,
                requirement=req_model.requirement_text,
                required_value=req_val_str,
                observed_value="Conditional / Disjunctive configuration",
                reason=ambiguity_analysis.ambiguity_reason or "Evidence contains conditional or alternative specifications requiring review.",
                evidence=pay_model.evidence,
                confidence=1.0,
                method=ComplianceMethod.MANUAL_REVIEW,
            )

        # 5. Check for Conflicts (Priority 2b: Conflict Detection)
        conflict_analysis = detect_evidence_conflict(req_model, pay_model.evidence)
        if conflict_analysis.has_conflict:
            return ComplianceResult(
                bidder_id=pay_model.bidder_id,
                rule_id=req_model.rule_id,
                status=ComplianceStatus.REVIEW,
                requirement=req_model.requirement_text,
                required_value=req_val_str,
                observed_value="Conflicting evidence across documents/pages",
                reason=conflict_analysis.conflict_reason or "Conflicting values were found in the submitted documents.",
                evidence=pay_model.evidence,
                confidence=1.0,
                method=ComplianceMethod.MANUAL_REVIEW,
            )

        # 5b. Safe Multi-Period Analysis:
        # If multiple evidence items report values for different periods/models (e.g. FY24 vs FY25)
        # where some pass and some fail, never arbitrarily choose the failing or passing one.
        if len(pay_model.evidence) > 1 and req_model.requirement_type == RequirementType.NUMERIC_COMPARISON.value:
            from member_2_compliance_engine.normalization.normalizer import extract_evidence_numeric_value
            from member_2_compliance_engine.compliance.conflict_detector import extract_contextual_markers
            multi_extracted = []
            for ev_item in pay_model.evidence:
                try:
                    num_val, _ = extract_evidence_numeric_value(
                        ev_item.text,
                        parameter=req_model.parameter,
                        unit=req_model.unit,
                        currency=req_model.currency,
                    )
                    ctx = extract_contextual_markers(ev_item.text)
                    multi_extracted.append((num_val, ctx, ev_item))
                except Exception:
                    pass

            if len(multi_extracted) > 1:
                unique_vals = {item[0] for item in multi_extracted}
                if len(unique_vals) > 1:
                    # Check if mixed pass/fail
                    # Compare each against required value
                    from member_2_compliance_engine.rule_engine.numeric_rules import evaluate_numeric_comparison
                    # Normalize required value
                    if req_model.currency or req_model.unit in ["lakh", "lakhs", "crore", "crores"]:
                        from member_2_compliance_engine.normalization.normalizer import normalize_currency
                        req_num = normalize_currency(req_model.required_value, unit=req_model.unit, currency=req_model.currency or "INR")[0]
                    else:
                        from member_2_compliance_engine.normalization.normalizer import normalize_number
                        req_num = normalize_number(req_model.required_value, unit=req_model.unit)

                    pass_flags = [(v[0] >= req_num) for v in multi_extracted]
                    if any(pass_flags) and not all(pass_flags):
                        summary_str = "; ".join(f"p.{v[2].page}: '{v[2].text.strip()}'" for v in multi_extracted)
                        return ComplianceResult(
                            bidder_id=pay_model.bidder_id,
                            rule_id=req_model.rule_id,
                            status=ComplianceStatus.REVIEW,
                            requirement=req_model.requirement_text,
                            required_value=req_val_str,
                            observed_value="Multiple periods with mixed values",
                            reason=(
                                f"Multiple distinct period values reported with mixed compliance ({summary_str}); "
                                "deferred to human procurement officer to verify applicable financial period."
                            ),
                            evidence=pay_model.evidence,
                            confidence=1.0,
                            method=ComplianceMethod.MANUAL_REVIEW,
                        )

        # 6. Apply Deterministic Python Rule Evaluation (Priority 3: Evaluate PASS / FAIL)
        rule_eval_res = RuleEvaluator.evaluate(req_model, pay_model.evidence)

        # Map to final ComplianceResult
        decision_method = (
            ComplianceMethod.MANUAL_REVIEW
            if rule_eval_res.status == ComplianceStatus.REVIEW
            else ComplianceMethod.DETERMINISTIC_RULE
        )

        return ComplianceResult(
            bidder_id=pay_model.bidder_id,
            rule_id=req_model.rule_id,
            status=rule_eval_res.status,
            requirement=req_model.requirement_text,
            required_value=req_val_str,
            observed_value=rule_eval_res.observed_value,
            reason=rule_eval_res.reason,
            evidence=pay_model.evidence,
            confidence=rule_eval_res.confidence,
            method=decision_method,
        )

    @staticmethod
    def _format_required_value(requirement: StructuredRequirement) -> str:
        """Format required value with unit or currency for clear auditable reporting."""
        val = requirement.required_value
        unit = requirement.unit
        currency = requirement.currency

        if currency == "INR" and unit and unit.lower() in ["lakh", "lakhs", "crore", "crores"]:
            return f"₹{val} {unit.capitalize()}"
        elif currency and unit:
            return f"{currency} {val} {unit}"
        elif unit:
            return f"{val} {unit}"
        elif currency:
            return f"{currency} {val}"
        return str(val)
