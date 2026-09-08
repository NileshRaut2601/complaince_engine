"""Unit tests for deterministic edge cases, ambiguity detection, conflict detection, and safeguards."""

import pytest
from pydantic import ValidationError

from member_2_compliance_engine.compliance.classifier import ComplianceClassifier
from member_2_compliance_engine.schemas import (
    BidderEvidencePayload,
    ComplianceMethod,
    ComplianceStatus,
    EvidenceItem,
    StructuredRequirement,
)


@pytest.fixture
def classifier():
    return ComplianceClassifier()


class TestEdgeCases:
    # 1. 65 >= 50 -> COMPLIANT
    def test_case_01_numeric_pass(self, classifier):
        req = StructuredRequirement(
            rule_id="R001",
            parameter="annual_turnover",
            operator=">=",
            required_value=50,
            unit="lakhs",
            currency="INR",
            requirement_text="Turnover >= 50 Lakhs",
        )
        payload = BidderEvidencePayload(
            rule_id="R001",
            bidder_id="B001",
            evidence=[EvidenceItem(text="Annual turnover is ₹65 Lakhs.", source_file="Doc.pdf", page=1)],
        )
        res = classifier.evaluate_bid(req, payload)
        assert res.status == ComplianceStatus.COMPLIANT
        assert res.method == ComplianceMethod.DETERMINISTIC_RULE

    # 2. 35 >= 50 -> NON_COMPLIANT
    def test_case_02_numeric_fail(self, classifier):
        req = StructuredRequirement(
            rule_id="R001",
            parameter="annual_turnover",
            operator=">=",
            required_value=50,
            unit="lakhs",
            currency="INR",
            requirement_text="Turnover >= 50 Lakhs",
        )
        payload = BidderEvidencePayload(
            rule_id="R001",
            bidder_id="B001",
            evidence=[EvidenceItem(text="Annual turnover is ₹35 Lakhs.", source_file="Doc.pdf", page=1)],
        )
        res = classifier.evaluate_bid(req, payload)
        assert res.status == ComplianceStatus.NON_COMPLIANT
        assert res.method == ComplianceMethod.DETERMINISTIC_RULE

    # 3. 50 >= 50 -> COMPLIANT
    def test_case_03_numeric_boundary(self, classifier):
        req = StructuredRequirement(
            rule_id="R001",
            parameter="annual_turnover",
            operator=">=",
            required_value=50,
            unit="lakhs",
            currency="INR",
            requirement_text="Turnover >= 50 Lakhs",
        )
        payload = BidderEvidencePayload(
            rule_id="R001",
            bidder_id="B001",
            evidence=[EvidenceItem(text="Turnover stands at ₹50 Lakhs.", source_file="Doc.pdf", page=1)],
        )
        res = classifier.evaluate_bid(req, payload)
        assert res.status == ComplianceStatus.COMPLIANT

    # 4. Missing document -> MISSING
    def test_case_04_missing_document(self, classifier):
        req = StructuredRequirement(
            rule_id="R002",
            parameter="Manufacturer Authorization Form",
            operator="exists",
            required_value="Manufacturer Authorization Form",
            requirement_text="Manufacturer Authorization Form must be submitted.",
            requirement_type="document_exists",
        )
        payload = BidderEvidencePayload(
            rule_id="R002",
            bidder_id="B001",
            evidence=[],  # No evidence found
        )
        res = classifier.evaluate_bid(req, payload)
        assert res.status == ComplianceStatus.MISSING
        assert "No evidence was retrieved" in res.reason

    # 5. Exact match -> COMPLIANT
    def test_case_05_exact_match_pass(self, classifier):
        req = StructuredRequirement(
            rule_id="R003",
            parameter="architecture",
            operator="==",
            required_value="x86-64",
            requirement_text="Architecture must be x86-64",
            requirement_type="exact_match",
        )
        payload = BidderEvidencePayload(
            rule_id="R003",
            bidder_id="B001",
            evidence=[EvidenceItem(text="x86-64", source_file="spec.pdf", page=2)],
        )
        res = classifier.evaluate_bid(req, payload)
        assert res.status == ComplianceStatus.COMPLIANT

    # 6. Exact mismatch -> NON_COMPLIANT
    def test_case_06_exact_match_fail(self, classifier):
        req = StructuredRequirement(
            rule_id="R003",
            parameter="architecture",
            operator="==",
            required_value="x86-64",
            requirement_text="Architecture must be x86-64",
            requirement_type="exact_match",
        )
        payload = BidderEvidencePayload(
            rule_id="R003",
            bidder_id="B001",
            evidence=[EvidenceItem(text="ARM64", source_file="spec.pdf", page=2)],
        )
        res = classifier.evaluate_bid(req, payload)
        assert res.status == ComplianceStatus.NON_COMPLIANT

    # 7. Contains -> COMPLIANT
    def test_case_07_contains_pass(self, classifier):
        req = StructuredRequirement(
            rule_id="R004",
            parameter="certification",
            operator="contains",
            required_value="ISO 27001",
            requirement_text="Bidder must have ISO 27001 certification",
            requirement_type="contains",
        )
        payload = BidderEvidencePayload(
            rule_id="R004",
            bidder_id="B001",
            evidence=[EvidenceItem(text="The organization maintains an ISO 27001:2022 certified ISMS.", source_file="cert.pdf", page=5)],
        )
        res = classifier.evaluate_bid(req, payload)
        assert res.status == ComplianceStatus.COMPLIANT

    # 8. Date comparison
    def test_case_08_date_comparison(self, classifier):
        req = StructuredRequirement(
            rule_id="R005",
            parameter="incorporation_date",
            operator="<=",
            required_value="01/01/2020",
            requirement_text="Company must be incorporated on or before 01/01/2020",
            requirement_type="date_comparison",
        )
        payload = BidderEvidencePayload(
            rule_id="R005",
            bidder_id="B001",
            evidence=[EvidenceItem(text="Certificate of Incorporation dated 12/04/2017.", source_file="incorporation.pdf", page=1)],
        )
        res = classifier.evaluate_bid(req, payload)
        assert res.status == ComplianceStatus.COMPLIANT

    # 9. Duration comparison
    def test_case_09_duration_comparison(self, classifier):
        req = StructuredRequirement(
            rule_id="R006",
            parameter="experience",
            operator=">=",
            required_value=5,
            unit="years",
            requirement_text="Relevant experience of at least 5 years.",
            requirement_type="duration",
        )
        payload = BidderEvidencePayload(
            rule_id="R006",
            bidder_id="B001",
            evidence=[EvidenceItem(text="The vendor has 7 years of domain experience.", source_file="profile.pdf", page=3)],
        )
        res = classifier.evaluate_bid(req, payload)
        assert res.status == ComplianceStatus.COMPLIANT

    # 10. TB/GB normalization
    def test_case_10_unit_conversion(self, classifier):
        # 2 TB should be comparable with 2048 GB
        req = StructuredRequirement(
            rule_id="R007",
            parameter="RAM",
            operator=">=",
            required_value=2,
            unit="TB",
            requirement_text="AI Workload Node RAM must be at least 2 TB.",
            requirement_type="numeric_comparison",
        )
        payload = BidderEvidencePayload(
            rule_id="R007",
            bidder_id="B001",
            evidence=[EvidenceItem(text="Server memory installed is 2048 GB.", source_file="datasheet.pdf", page=7)],
        )
        res = classifier.evaluate_bid(req, payload)
        assert res.status == ComplianceStatus.COMPLIANT

    # 11. Currency normalization
    def test_case_11_currency_normalization(self, classifier):
        req = StructuredRequirement(
            rule_id="R008",
            parameter="turnover",
            operator=">=",
            required_value=50,
            unit="lakhs",
            currency="INR",
            requirement_text="Turnover >= 50 Lakhs",
        )
        payload = BidderEvidencePayload(
            rule_id="R008",
            bidder_id="B001",
            evidence=[EvidenceItem(text="Total revenue: INR 50,00,000.", source_file="tax.pdf", page=2)],
        )
        res = classifier.evaluate_bid(req, payload)
        assert res.status == ComplianceStatus.COMPLIANT

    # 12. Ambiguous evidence ("8 × 192 GB OR 16 × 96 GB") -> REVIEW
    def test_case_12_ambiguous_evidence_detector(self, classifier):
        req = StructuredRequirement(
            rule_id="R009",
            parameter="GPU Memory",
            operator=">=",
            required_value=192,
            unit="GB",
            requirement_text="8 dedicated GPU units with minimum 192 GB memory per GPU.",
            requirement_type="numeric_comparison",
        )
        payload = BidderEvidencePayload(
            rule_id="R009",
            bidder_id="B001",
            evidence=[
                EvidenceItem(
                    text="Supports up to 8 full-size modules OR up to 16 half-size modules. Memory may be 8 × 192 GB OR 16 × 96 GB.",
                    source_file="GPU_Datasheet.pdf",
                    page=12,
                )
            ],
        )
        res = classifier.evaluate_bid(req, payload)
        assert res.status == ComplianceStatus.REVIEW
        assert res.method == ComplianceMethod.MANUAL_REVIEW
        assert "alternative configurations" in res.reason or "ambiguous" in res.reason.lower()

    # 13. Conflicting evidence for same financial period -> REVIEW
    def test_case_13_conflicting_evidence(self, classifier):
        req = StructuredRequirement(
            rule_id="R010",
            parameter="annual_turnover",
            operator=">=",
            required_value=50,
            unit="lakhs",
            currency="INR",
            requirement_text="Annual turnover must be at least ₹50 Lakhs.",
            requirement_type="numeric_comparison",
        )
        payload = BidderEvidencePayload(
            rule_id="R010",
            bidder_id="B001",
            evidence=[
                EvidenceItem(text="Annual turnover FY2025: ₹65 Lakhs.", source_file="Financials.pdf", page=20),
                EvidenceItem(text="Annual turnover FY2025: ₹42 Lakhs.", source_file="Financials.pdf", page=45),
            ],
        )
        res = classifier.evaluate_bid(req, payload)
        assert res.status == ComplianceStatus.REVIEW
        assert res.method == ComplianceMethod.MANUAL_REVIEW
        assert "Conflicting values found in submitted documents" in res.reason
        # Check both evidence items are preserved
        assert len(res.evidence) == 2
        assert res.evidence[0].page == 20
        assert res.evidence[1].page == 45

    # 14. Different financial years -> not automatically conflict
    def test_case_14_different_financial_years(self, classifier):
        req = StructuredRequirement(
            rule_id="R011",
            parameter="annual_turnover",
            operator=">=",
            required_value=50,
            unit="lakhs",
            currency="INR",
            requirement_text="Annual turnover >= 50 Lakhs",
            requirement_type="numeric_comparison",
        )
        payload = BidderEvidencePayload(
            rule_id="R011",
            bidder_id="B001",
            evidence=[
                EvidenceItem(text="Turnover FY2024: ₹42 Lakhs", source_file="Audited_Accounts.pdf", page=10),
                EvidenceItem(text="Turnover FY2025: ₹65 Lakhs", source_file="Audited_Accounts.pdf", page=20),
            ],
        )
        # Should NOT trigger automatic contradiction conflict because contexts (FY24 vs FY25) differ
        res = classifier.evaluate_bid(req, payload)
        assert res.status in [ComplianceStatus.COMPLIANT, ComplianceStatus.REVIEW]
        assert "Conflicting values found" not in res.reason

    # 15. Ambiguous clause wording in requirement -> REVIEW
    def test_case_15_ambiguous_requirement_wording(self, classifier):
        req = StructuredRequirement(
            rule_id="R012",
            parameter="delivery_timeline",
            operator="==",
            required_value="flexible",
            requirement_text="Delivery timeline may be 30 days or up to 60 days depending on configuration.",
            requirement_type="ambiguous",
        )
        payload = BidderEvidencePayload(
            rule_id="R012",
            bidder_id="B001",
            evidence=[EvidenceItem(text="Delivery timeline: 45 days.", source_file="Proposal.pdf", page=3)],
        )
        res = classifier.evaluate_bid(req, payload)
        assert res.status == ComplianceStatus.REVIEW
        assert res.method == ComplianceMethod.MANUAL_REVIEW
        assert "deferred to human procurement officer" in res.reason

    # 16. Empty evidence -> MISSING
    def test_case_16_empty_evidence(self, classifier):
        req = StructuredRequirement(
            rule_id="R015",
            parameter="GST",
            operator="exists",
            required_value="GST Registration Certificate",
            requirement_text="GST Certificate is required.",
        )
        payload = BidderEvidencePayload(rule_id="R015", bidder_id="B001", evidence=[])
        res = classifier.evaluate_bid(req, payload)
        assert res.status == ComplianceStatus.MISSING
        assert res.observed_value is None

    # 17. Multiple evidence items handled correctly for includes_all
    def test_case_17_multiple_evidence_items(self, classifier):
        req = StructuredRequirement(
            rule_id="R016",
            parameter="standards",
            operator="includes_all",
            required_value=["ISO 9001", "ISO 27001"],
            requirement_text="Vendor must hold ISO 9001 and ISO 27001",
            requirement_type="includes_all",
        )
        payload = BidderEvidencePayload(
            rule_id="R016",
            bidder_id="B001",
            evidence=[
                EvidenceItem(text="Quality management is certified under ISO 9001.", source_file="QMS.pdf", page=4),
                EvidenceItem(text="Information security complies with ISO 27001 standard.", source_file="Security.pdf", page=8),
            ],
        )
        res = classifier.evaluate_bid(req, payload)
        assert res.status == ComplianceStatus.COMPLIANT

    # 18. Invalid requirement schema raises ValidationError
    def test_case_18_invalid_requirement_schema(self):
        with pytest.raises(ValidationError):
            StructuredRequirement(
                rule_id="",  # Empty rule_id not allowed
                parameter="turnover",
                operator=">=",
                required_value=50,
                requirement_text="Some text",
            )

        with pytest.raises(ValidationError):
            StructuredRequirement(
                rule_id="R001",
                parameter="turnover",
                operator="INVALID_OPERATOR_SYMBOL_XYZ",
                required_value=50,
                requirement_text="Some text",
            )

    # 19. Unsafe normalization triggers REVIEW rather than false compliance
    def test_case_19_unsafe_normalization(self, classifier):
        req = StructuredRequirement(
            rule_id="R017",
            parameter="turnover",
            operator=">=",
            required_value=50,
            unit="lakhs",
            currency="INR",
            requirement_text="Turnover >= 50 Lakhs",
        )
        payload = BidderEvidencePayload(
            rule_id="R017",
            bidder_id="B001",
            evidence=[EvidenceItem(text="The vendor had substantial commercial activity.", source_file="Text.pdf", page=1)],
        )
        res = classifier.evaluate_bid(req, payload)
        assert res.status == ComplianceStatus.REVIEW
        assert res.method == ComplianceMethod.MANUAL_REVIEW

    # 20. Preserve exact source page numbers and evidence
    def test_case_20_preserve_exact_evidence_and_page(self, classifier):
        req = StructuredRequirement(
            rule_id="R018",
            parameter="experience",
            operator=">=",
            required_value=3,
            unit="years",
            requirement_text="Experience >= 3 years",
        )
        payload = BidderEvidencePayload(
            rule_id="R018",
            bidder_id="B009",
            evidence=[
                EvidenceItem(
                    text="The firm has 5 years of experience in system integration.",
                    source_file="Vendor_Profile_Final_v2.pdf",
                    page=47,
                )
            ],
        )
        res = classifier.evaluate_bid(req, payload)
        assert res.status == ComplianceStatus.COMPLIANT
        assert res.evidence[0].source_file == "Vendor_Profile_Final_v2.pdf"
        assert res.evidence[0].page == 47
        assert res.evidence[0].text == "The firm has 5 years of experience in system integration."
