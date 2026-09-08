"""Runnable Demonstration of the Member 2 Deterministic Compliance Engine.

Fully offline, reproducible, and explainable tender verification.
Zero LLM dependencies.

Demonstrates:
- Case 1 (COMPLIANT): Annual Turnover >= ₹50 Lakhs vs ₹65 Lakhs
- Case 2 (NON_COMPLIANT): Annual Turnover >= ₹50 Lakhs vs ₹35 Lakhs
- Case 3 (MISSING): Manufacturer Authorization Form mandatory vs None
- Case 4 (REVIEW): Memory per GPU >= 192 GB vs Ambiguous "8 × 192 GB OR 16 × 96 GB"
- Case 5 (CONFLICT): FY2025 Turnover ₹65 Lakhs (p.20) vs ₹42 Lakhs (p.45)
"""

import sys
from pathlib import Path

# Configure Windows console UTF-8 output encoding for currency symbols (₹)
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

# Ensure project root is in sys.path for direct script execution
project_root = Path(__file__).resolve().parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from member_2_compliance_engine.compliance.classifier import ComplianceClassifier
from member_2_compliance_engine.compliance.result import (
    format_audit_report,
    format_result_as_json,
)
from member_2_compliance_engine.evaluation.evaluator import run_benchmark
from member_2_compliance_engine.schemas import (
    BidderEvidencePayload,
    CategoryEnum,
    EvidenceItem,
    OperatorEnum,
    RequirementType,
    StructuredRequirement,
)


def run_demo():
    print("=" * 70)
    print("  GOVERNMENT TENDER BID COMPLIANCE SYSTEM - MEMBER 2 ENGINE")
    print("  (Deterministic, Zero-LLM, Fully Air-Gapped & Offline)")
    print("=" * 70)
    print("Role: Verification & Compliance Decision Engine")
    print("Boundary: Member 1 finds evidence. Member 2 deterministically judges.")
    print("Verdicts: COMPLIANT | NON_COMPLIANT | MISSING | REVIEW")
    print("=" * 70)
    print()

    # Instantiate pure deterministic classifier
    classifier = ComplianceClassifier()
    results = []

    # =========================================================================
    # CASE 1: COMPLIANT (Annual turnover >= ₹50 Lakhs vs ₹65 Lakhs)
    # =========================================================================
    print("----------------------------------------------------------------------")
    print("DEMO CASE 1 — COMPLIANT (Deterministic Numeric Rule)")
    print("----------------------------------------------------------------------")
    req1 = StructuredRequirement(
        rule_id="R001",
        category=CategoryEnum.FINANCIAL.value,
        parameter="annual_turnover",
        operator=OperatorEnum.GTE.value,
        required_value=50,
        unit="lakhs",
        currency="INR",
        requirement_text="Vendor must have an annual turnover of at least ₹50 Lakhs.",
        requirement_type=RequirementType.NUMERIC_COMPARISON.value,
    )
    pay1 = BidderEvidencePayload(
        rule_id="R001",
        bidder_id="B001",
        evidence=[
            EvidenceItem(
                text="The company's reported annual turnover is ₹65 Lakhs.",
                source_file="Financial_Statement.pdf",
                page=42,
            )
        ],
    )
    res1 = classifier.evaluate_bid(req1, pay1)
    results.append(res1)
    print(format_result_as_json(res1))
    print()

    # =========================================================================
    # CASE 2: NON_COMPLIANT (Annual turnover >= ₹50 Lakhs vs ₹35 Lakhs)
    # =========================================================================
    print("----------------------------------------------------------------------")
    print("DEMO CASE 2 — NON_COMPLIANT (Deterministic Numeric Rule)")
    print("----------------------------------------------------------------------")
    pay2 = BidderEvidencePayload(
        rule_id="R001",
        bidder_id="B002",
        evidence=[
            EvidenceItem(
                text="The company's reported annual turnover is ₹35 Lakhs.",
                source_file="Financial_Statement.pdf",
                page=12,
            )
        ],
    )
    res2 = classifier.evaluate_bid(req1, pay2)
    results.append(res2)
    print(format_result_as_json(res2))
    print()

    # =========================================================================
    # CASE 3: MISSING (Manufacturer Authorization Form required vs None)
    # =========================================================================
    print("----------------------------------------------------------------------")
    print("DEMO CASE 3 — MISSING (Document / Evidence Not Found)")
    print("----------------------------------------------------------------------")
    req3 = StructuredRequirement(
        rule_id="R003",
        category=CategoryEnum.COMPLIANCE.value,
        parameter="Manufacturer Authorization Form",
        operator=OperatorEnum.EXISTS.value,
        required_value="Manufacturer Authorization Form",
        unit=None,
        currency=None,
        requirement_text="Manufacturer Authorization Form is mandatory.",
        requirement_type=RequirementType.DOCUMENT_EXISTS.value,
    )
    pay3 = BidderEvidencePayload(
        rule_id="R003",
        bidder_id="B003",
        evidence=[],  # Member 1 RAG retrieved no document
    )
    res3 = classifier.evaluate_bid(req3, pay3)
    results.append(res3)
    print(format_result_as_json(res3))
    print()

    # =========================================================================
    # CASE 4: REVIEW (Ambiguous/Disjunctive: 8 × 192 GB OR 16 × 96 GB)
    # =========================================================================
    print("----------------------------------------------------------------------")
    print("DEMO CASE 4 — REVIEW (Ambiguity Detection — Conditional Configuration)")
    print("----------------------------------------------------------------------")
    req4 = StructuredRequirement(
        rule_id="R004",
        category=CategoryEnum.TECHNICAL.value,
        parameter="GPU Memory",
        operator=OperatorEnum.GTE.value,
        required_value=192,
        unit="GB",
        currency=None,
        requirement_text="8 dedicated GPU units with minimum 192 GB memory per GPU.",
        requirement_type=RequirementType.NUMERIC_COMPARISON.value,
    )
    pay4 = BidderEvidencePayload(
        rule_id="R004",
        bidder_id="B004",
        evidence=[
            EvidenceItem(
                text="Supports up to 8 full-size modules OR up to 16 half-size modules. Memory may be 8 × 192 GB OR 16 × 96 GB.",
                source_file="GPU_Datasheet.pdf",
                page=12,
            )
        ],
    )
    res4 = classifier.evaluate_bid(req4, pay4)
    results.append(res4)
    print(format_result_as_json(res4))
    print()

    # =========================================================================
    # CASE 5: CONFLICT (Page 20 FY2025 ₹65 Lakhs vs Page 45 FY2025 ₹42 Lakhs)
    # =========================================================================
    print("----------------------------------------------------------------------")
    print("DEMO CASE 5 — REVIEW (Conflict Detection — Contradictory Period Data)")
    print("----------------------------------------------------------------------")
    pay5 = BidderEvidencePayload(
        rule_id="R001",
        bidder_id="B005",
        evidence=[
            EvidenceItem(
                text="Annual turnover FY2025: ₹65 Lakhs",
                source_file="Financial_Statement.pdf",
                page=20,
            ),
            EvidenceItem(
                text="Annual turnover FY2025: ₹42 Lakhs",
                source_file="Financial_Statement.pdf",
                page=45,
            ),
        ],
    )
    res5 = classifier.evaluate_bid(req1, pay5)
    results.append(res5)
    print(format_result_as_json(res5))
    print()

    # =========================================================================
    # AUDIT TRAIL SUMMARY TABLE
    # =========================================================================
    print("======================================================================")
    print("AUDIT TRAIL SUMMARY REPORT")
    print("======================================================================")
    print(format_audit_report(results, bidder_id="DEMO_BATCH"))

    # =========================================================================
    # EVALUATION BENCHMARK
    # =========================================================================
    print("Running Benchmark Evaluation Metrics...")
    benchmark_dataset = [
        {"rule_id": "R001", "expected_status": "COMPLIANT", "predicted_status": res1.status.value},
        {"rule_id": "R002", "expected_status": "NON_COMPLIANT", "predicted_status": res2.status.value},
        {"rule_id": "R003", "expected_status": "MISSING", "predicted_status": res3.status.value},
        {"rule_id": "R004", "expected_status": "REVIEW", "predicted_status": res4.status.value},
        {"rule_id": "R005", "expected_status": "REVIEW", "predicted_status": res5.status.value},
    ]
    run_benchmark(benchmark_dataset)


if __name__ == "__main__":
    run_demo()
