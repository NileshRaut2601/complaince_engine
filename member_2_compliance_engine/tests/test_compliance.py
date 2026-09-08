"""Unit tests for end-to-end compliance classification and Member 1 interface."""

import pytest
from pydantic import ValidationError

from member_2_compliance_engine.compliance.classifier import ComplianceClassifier
from member_2_compliance_engine.compliance.result import format_result_as_json, format_audit_report
from member_2_compliance_engine.schemas import (
    BidderEvidencePayload,
    ComplianceMethod,
    ComplianceResult,
    ComplianceStatus,
    EvidenceItem,
    StructuredRequirement,
)


class TestMember1InterfaceAndAuditTrail:
    @pytest.fixture
    def classifier(self):
        return ComplianceClassifier()

    def test_member1_evidence_payload_consumption(self, classifier):
        # Exact Member 1 input contract
        raw_payload = {
            "rule_id": "R001",
            "bidder_id": "B001",
            "evidence": [
                {
                    "text": "The company's reported annual turnover is ₹65 Lakhs.",
                    "source_file": "Financial_Statement.pdf",
                    "page": 42,
                }
            ],
        }

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

        result: ComplianceResult = classifier.evaluate_bid(req, raw_payload)

        # Auditability checks
        assert result.bidder_id == "B001"
        assert result.rule_id == "R001"
        assert result.status == ComplianceStatus.COMPLIANT
        assert result.method == ComplianceMethod.DETERMINISTIC_RULE
        assert result.confidence == 1.0

        # Preserve exact evidence
        assert len(result.evidence) == 1
        assert result.evidence[0].source_file == "Financial_Statement.pdf"
        assert result.evidence[0].page == 42
        assert result.evidence[0].text == "The company's reported annual turnover is ₹65 Lakhs."

    def test_audit_json_serialization(self, classifier):
        req = StructuredRequirement(
            rule_id="R001",
            category="financial",
            parameter="annual_turnover",
            operator=">=",
            required_value=50,
            unit="lakhs",
            currency="INR",
            requirement_text="Vendor must have an annual turnover of at least ₹50 Lakhs.",
        )
        payload = BidderEvidencePayload(
            rule_id="R001",
            bidder_id="B001",
            evidence=[
                EvidenceItem(
                    text="Reported turnover ₹65 Lakhs.",
                    source_file="Audit.pdf",
                    page=10,
                )
            ],
        )
        res = classifier.evaluate_bid(req, payload)
        json_str = format_result_as_json(res)
        assert '"status": "COMPLIANT"' in json_str
        assert '"bidder_id": "B001"' in json_str
        assert '"page": 10' in json_str

        # Markdown audit report formatting
        report = format_audit_report([res], bidder_id="B001")
        assert "| `R001` | **COMPLIANT** |" in report

    def test_reject_mismatched_rule_id(self, classifier):
        req = StructuredRequirement(
            rule_id="R001",
            parameter="RAM",
            operator=">=",
            required_value=16,
            requirement_text="RAM >= 16 GB",
        )
        payload = {
            "rule_id": "R999",  # Mismatch!
            "bidder_id": "B001",
            "evidence": [{"text": "RAM is 32 GB", "source_file": "spec.pdf", "page": 1}],
        }
        with pytest.raises(ValueError, match="Rule ID mismatch"):
            classifier.evaluate_bid(req, payload)

    def test_reject_malformed_evidence_item(self):
        # Missing required field 'source_file'
        with pytest.raises(ValidationError):
            EvidenceItem.model_validate({"text": "Just text without source", "page": 5})

        # Empty text
        with pytest.raises(ValidationError):
            EvidenceItem.model_validate({"text": "", "source_file": "file.pdf", "page": 5})

        # Invalid page (zero or negative)
        with pytest.raises(ValidationError):
            EvidenceItem.model_validate({"text": "Valid text", "source_file": "file.pdf", "page": 0})

    def test_requirement_parser_dict_and_json(self):
        from member_2_compliance_engine.requirement_parser import RequirementParser

        raw_dict = {
            "rule_id": "R001",
            "category": "financial",
            "parameter": "annual_turnover",
            "operator": ">=",
            "required_value": 50,
            "unit": "lakhs",
            "currency": "INR",
            "requirement_text": "Vendor must have an annual turnover of at least ₹50 Lakhs.",
            "requirement_type": "numeric_comparison",
        }
        parsed = RequirementParser.parse(raw_dict)
        assert parsed.rule_id == "R001"
        assert parsed.operator == ">="

        # Parse from JSON string
        import json
        parsed_json = RequirementParser.parse(json.dumps(raw_dict))
        assert parsed_json.rule_id == "R001"

    def test_requirement_extractor_deterministic(self):
        from member_2_compliance_engine.requirement_extraction import RequirementExtractor

        extractor = RequirementExtractor()
        req = extractor.extract("Vendor must have an annual turnover of at least ₹50 Lakhs.", "R001")
        assert req.rule_id == "R001"
        assert req.parameter == "annual_turnover"
        assert req.required_value == 50
        assert req.unit == "lakhs"
