"""Unit tests for deterministic rule engines."""

from datetime import date
import pytest

from member_2_compliance_engine.rule_engine.numeric_rules import evaluate_numeric_comparison
from member_2_compliance_engine.rule_engine.string_rules import evaluate_string_rule
from member_2_compliance_engine.rule_engine.date_rules import evaluate_date_rule, evaluate_duration_rule
from member_2_compliance_engine.rule_engine.existence_rules import evaluate_existence_rule
from member_2_compliance_engine.rule_engine.evaluator import RuleEvaluator
from member_2_compliance_engine.schemas import (
    ComplianceStatus,
    EvidenceItem,
    StructuredRequirement,
)


class TestNumericRules:
    def test_numeric_gte_pass(self):
        # 65 >= 50 -> COMPLIANT
        passed, reason = evaluate_numeric_comparison(">=", required_value=50.0, observed_value=65.0)
        assert passed is True
        assert "satisfies minimum requirement" in reason

    def test_numeric_gte_boundary_pass(self):
        # 50 >= 50 -> COMPLIANT
        passed, reason = evaluate_numeric_comparison(">=", required_value=50.0, observed_value=50.0)
        assert passed is True

    def test_numeric_gte_fail(self):
        # 35 >= 50 -> NON_COMPLIANT
        passed, reason = evaluate_numeric_comparison(">=", required_value=50.0, observed_value=35.0)
        assert passed is False
        assert "is below the minimum required" in reason

    def test_numeric_equality(self):
        passed, _ = evaluate_numeric_comparison("==", required_value=100.0, observed_value=100.0)
        assert passed is True

        passed, _ = evaluate_numeric_comparison("==", required_value=100.0, observed_value=99.0)
        assert passed is False

    def test_numeric_lte(self):
        passed, _ = evaluate_numeric_comparison("<=", required_value=10.0, observed_value=5.0)
        assert passed is True

        passed, _ = evaluate_numeric_comparison("<=", required_value=10.0, observed_value=15.0)
        assert passed is False


class TestStringRules:
    def test_exact_match_success(self):
        passed, reason = evaluate_string_rule("==", required_value="ISO 9001:2015", observed_text="ISO 9001:2015")
        assert passed is True
        assert "exactly matches" in reason

    def test_exact_match_failure(self):
        passed, reason = evaluate_string_rule("==", required_value="ISO 9001:2015", observed_text="ISO 27001")
        assert passed is False
        assert "does not match" in reason

    def test_contains_success(self):
        text = "The vendor holds an active ISO 9001:2015 quality management system certification."
        passed, reason = evaluate_string_rule("contains", required_value="ISO 9001", observed_text=text)
        assert passed is True
        assert "contains the required string" in reason

    def test_includes_all_success(self):
        text = "Certifications include ISO 9001, ISO 27001, and CMMI Level 5."
        passed, reason = evaluate_string_rule("includes_all", required_value=["ISO 9001", "ISO 27001"], observed_text=text)
        assert passed is True
        assert "contains all" in reason

    def test_includes_all_failure(self):
        text = "Certifications include ISO 9001 only."
        passed, reason = evaluate_string_rule("includes_all", required_value=["ISO 9001", "ISO 27001"], observed_text=text)
        assert passed is False
        assert "missing required specifications" in reason


class TestDateAndDurationRules:
    def test_date_on_or_before(self):
        # Incorporation on or before 01/01/2020
        passed, reason = evaluate_date_rule("<=", required_date_val="01/01/2020", observed_date_val="15/06/2018")
        assert passed is True
        assert "on or before" in reason

    def test_date_fail(self):
        passed, reason = evaluate_date_rule("<=", required_date_val="01/01/2020", observed_date_val="15/06/2022")
        assert passed is False
        assert "after" in reason

    def test_duration_gte(self):
        passed, reason = evaluate_duration_rule(">=", required_duration_val="5 years", observed_duration_val="7 years")
        assert passed is True

        passed, reason = evaluate_duration_rule(">=", required_duration_val="5 years", observed_duration_val="60 months")
        assert passed is True

        passed, reason = evaluate_duration_rule(">=", required_duration_val="5 years", observed_duration_val="3 years")
        assert passed is False


class TestExistenceRules:
    def test_document_exists_success(self):
        evidence = [
            EvidenceItem(
                text="The Manufacturer Authorization Form signed by OEM is attached in Annexure A.",
                source_file="MAF_Annexure.pdf",
                page=1,
            )
        ]
        passed, reason = evaluate_existence_rule("Manufacturer Authorization Form", evidence)
        assert passed is True
        assert "confirmed present" in reason

    def test_document_exists_explicit_missing(self):
        evidence = [
            EvidenceItem(
                text="Manufacturer Authorization Form was not submitted by the bidder.",
                source_file="Checklist.pdf",
                page=3,
            )
        ]
        passed, reason = evaluate_existence_rule("Manufacturer Authorization Form", evidence)
        assert passed is False
        assert "explicitly recorded as missing" in reason


class TestRuleEvaluatorDispatch:
    def test_evaluator_numeric_turnover(self):
        req = StructuredRequirement(
            rule_id="R001",
            category="financial",
            parameter="annual_turnover",
            operator=">=",
            required_value=50,
            unit="lakhs",
            currency="INR",
            requirement_text="Vendor must have an annual turnover of at least ₹50 Lakhs.",
            requirement_type="numeric_comparison",
        )
        evidence = [
            EvidenceItem(
                text="Audited annual turnover for the year is ₹65 Lakhs.",
                source_file="Financials.pdf",
                page=14,
            )
        ]
        res = RuleEvaluator.evaluate(req, evidence)
        assert res.status == ComplianceStatus.COMPLIANT
        assert res.confidence == 1.0
        assert "65 Lakhs" in str(res.observed_value)

