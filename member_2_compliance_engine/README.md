# Member 2: Deterministic Tender Compliance Engine

A secure, fully on-premise, air-gapped **Government Tender Bid Compliance Engine** responsible for deterministically verifying whether bidder evidence satisfies buyer requirements.

---

## 1. System Overview & Scope Boundary

```text
                    TENDER DOCUMENT
                          │
                          ▼
                 MEMBER 1: DOCUMENT
                 INGESTION / OCR
                          │
                          ▼
                 TENDER TEXT CLAUSE
                          │
                          ▼
              ┌───────────────────────┐
              │       MEMBER 2        │
              │  REQUIREMENT PARSER   │
              │                       │
              │ Text → Structured Rule│
              └───────────┬───────────┘
                          │
                          ▼
                  STRUCTURED RULES
                          │
                          ▼
                 MEMBER 1: RAG
                          │
                          ▼
                BIDDER EVIDENCE
                + SOURCE + PAGE
                          │
                          ▼
              ┌───────────────────────┐
              │       MEMBER 2        │
              │   COMPLIANCE ENGINE   │
              │                       │
              │ Normalization         │
              │ Rule Evaluation       │
              │ Conflict Detection    │
              │ Ambiguity Detection   │
              └───────────┬───────────┘
                          │
                          ▼
           ┌──────────────┼──────────────┐
           ▼              ▼              ▼
     COMPLIANT      NON_COMPLIANT     MISSING
                          │
                          ▼
                        REVIEW
```

### Scope Boundary Principle
- **MEMBER 1 FINDS THE EVIDENCE.** (OCR, chunking, embeddings, ChromaDB, RAG search).
- **MEMBER 2 DETERMINISTICALLY JUDGES THE EVIDENCE AGAINST THE BUYER'S REQUIREMENT.**
- **BIDDER RISK PREDICTION IS A SEPARATE FUTURE MODULE.** It will consume the auditable compliance profile produced by Member 2. No risk prediction logic is implemented in this engine.

---

## 2. No LLM in the Compliance Engine

This engine operates with **ZERO LLM dependencies**:
- **NO** OpenAI, Gemini, Claude, Groq, Ollama, vLLM, or external cloud inference.
- **NO** cloud API keys, analytics, telemetry, or network calls.
- Runs 100% offline with the internet completely disconnected.
- Every verdict is generated using pure deterministic Python arithmetic, regex pattern matching, and rule trees.
- When an ambiguous, conditional, or contradictory statement is encountered, the system **never guesses** or uses probabilistic language models: it immediately routes the case to **`REVIEW`** (`manual_review`) for human procurement officer adjudication.

---

## 3. Member 1 ↔ Member 2 Integration Contract

### Step 1: Member 2 produces `StructuredRequirement`
Extracted from the tender text using rule-based parsing:
```json
{
  "rule_id": "R001",
  "category": "financial",
  "parameter": "annual_turnover",
  "operator": ">=",
  "required_value": 50,
  "unit": "lakhs",
  "currency": "INR",
  "requirement_text": "Vendor must have an annual turnover of at least ₹50 Lakhs.",
  "requirement_type": "numeric_comparison"
}
```

### Step 2: Member 1 provides `BidderEvidencePayload`
Retrieved from bidder documents via Member 1's RAG system:
```json
{
  "rule_id": "R001",
  "bidder_id": "B001",
  "evidence": [
    {
      "text": "The company's reported annual turnover is ₹65 Lakhs.",
      "source_file": "Financial_Statement.pdf",
      "page": 42
    }
  ]
}
```

### Step 3: Member 2 returns `ComplianceResult`
```json
{
  "bidder_id": "B001",
  "rule_id": "R001",
  "status": "COMPLIANT",
  "requirement": "Vendor must have an annual turnover of at least ₹50 Lakhs.",
  "required_value": "₹50 Lakhs",
  "observed_value": "₹65 Lakhs",
  "reason": "Observed annual_turnover (6500000.0 INR) satisfies minimum requirement (>= 5000000.0 INR).",
  "evidence": [
    {
      "text": "The company's reported annual turnover is ₹65 Lakhs.",
      "source_file": "Financial_Statement.pdf",
      "page": 42
    }
  ],
  "confidence": 1.0,
  "method": "deterministic_rule"
}
```

---

## 4. Decision Priority Flow

```text
                 Evidence
                    │
                    ▼
             Evidence exists?
              /            \
            NO              YES
            │                │
            ▼                ▼
         MISSING       Conflict/Ambiguity?
                         /       \
                       YES       NO
                       │          │
                       ▼          ▼
                     REVIEW    Deterministic
                                  │
                                  ▼
                              Evaluate
                              /      \
                            PASS     FAIL
                             │         │
                             ▼         ▼
                         COMPLIANT  NON_COMPLIANT
```

1. **Evidence Availability**: If `evidence` list is empty (`[]`), immediately returns **`MISSING`** with confidence `1.0`.
2. **Ambiguity Detection**: If evidence contains conditional/disjunctive constructs (`OR`, `either`, `alternatively`, `may be`, `up to ... or`, `depending on configuration`), returns **`REVIEW`** (`manual_review`).
3. **Conflict Detection**: If multiple evidence items report contradictory values for the same parameter and period, returns **`REVIEW`** (`manual_review`) preserving all evidence references.
4. **Deterministic Evaluation**: Pure Python comparison yields **`COMPLIANT`** or **`NON_COMPLIANT`** (`deterministic_rule`, confidence `1.0`).

---

## 5. Core Engine Modules

### Normalization Layer (`normalization/normalizer.py`)
- **Currencies**: Normalizes `₹50 Lakhs`, `50 lakh`, `₹50,00,000`, `INR 50,00,000`, `5 Crores` to base numeric values. Does not guess unadorned bare numbers.
- **Storage**: Uses binary convention `1 TB = 1024 GB`. `2 TB` directly equates to `2048 GB`.
- **Duration**: Normalizes years, months, and days to standard baseline years.
- **Dates**: Safely parses `DD/MM/YYYY`, `DD-MM-YYYY`, `YYYY-MM-DD`.

### Deterministic Rule Engine (`rule_engine/`)
- `numeric_rules.py`: Evaluates `==`, `>=`, `<=`, `<`, `>` with $10^{-6}$ precision tolerance.
- `string_rules.py`: Evaluates `exact_match`, `contains`, and `includes_all`.
- `date_rules.py`: Evaluates date validity and duration periods.
- `existence_rules.py`: Evaluates mandatory document presence while detecting negative clauses ("not submitted", "is missing").
- `evaluator.py`: Central dispatcher coordinating evaluation.

### Ambiguity & Conflict Detectors (`compliance/`)
- `ambiguity_detector.py`: Scans evidence text for non-committal or alternate configurations.
- `conflict_detector.py`: Analyzes multiple evidence snippets, checking for temporal qualifiers (`FY2024` vs `FY2025`), dates, models, and scopes to differentiate valid historical reporting from genuine contradictions.

---

## 6. How to Run

### 1. Run Interactive Demo:
```powershell
$env:PYTHONIOENCODING="utf-8"
python member_2_compliance_engine/main.py
```

### 2. Run Test Suite (54 Tests, 100% Offline):
```powershell
python -m pytest member_2_compliance_engine/tests -v
```

### 3. Run Benchmark Metrics:
```powershell
python -c "from member_2_compliance_engine.evaluation import run_benchmark; run_benchmark()"
```

---

## 7. Project Structure

```text
member_2_compliance_engine/
│
├── config.py                 # Centralized configuration (100% offline settings)
├── requirements.txt          # Minimal dependencies (pydantic, dateutil, pytest, scikit-learn)
├── README.md                 # System documentation & Member 1 contract
├── main.py                   # Complete runnable demonstration (Cases 1–5)
│
├── schemas/
│   ├── __init__.py
│   ├── requirement.py        # StructuredRequirement, ComplianceStatus, OperatorEnum
│   ├── evidence.py           # EvidenceItem, BidderEvidencePayload (Member 1 contract)
│   └── compliance_result.py  # ComplianceResult (auditable verdict)
│
├── requirement_extraction/
│   ├── __init__.py
│   ├── extractor.py          # Deterministic rule-based requirement extractor
│   └── patterns.py           # Controlled dictionaries & regex patterns
│
├── requirement_parser/
│   ├── __init__.py
│   └── parser.py             # Schema parser & validator
│
├── normalization/
│   ├── __init__.py
│   └── normalizer.py         # Currency, storage (1 TB=1024 GB), date, duration normalizers
│
├── rule_engine/
│   ├── __init__.py
│   ├── numeric_rules.py      # Deterministic arithmetic comparisons (==, >=, <=, <, >)
│   ├── string_rules.py       # exact_match, contains, includes_all
│   ├── date_rules.py         # Date & duration rules
│   ├── existence_rules.py    # Document presence & negative assertion detection
│   └── evaluator.py          # Central rule dispatcher
│
├── compliance/
│   ├── __init__.py
│   ├── classifier.py         # Central coordinator (priority decision tree)
│   ├── conflict_detector.py  # Multi-page contradiction detector
│   ├── ambiguity_detector.py # Conditional/disjunctive construct detector
│   └── result.py             # JSON & Markdown audit report serializers
│
├── evaluation/
│   ├── __init__.py
│   └── evaluator.py          # Accuracy, Precision, Recall, F1, 4x4 Confusion Matrix
│
├── examples/
│   ├── sample_requirements.json
│   ├── sample_evidence.json
│   └── sample_results.json
│
└── tests/
    ├── __init__.py
    ├── test_rules.py         # Tests for numeric, string, date, existence rules
    ├── test_normalization.py # Tests for currency, storage, duration, date normalizers
    ├── test_compliance.py    # Tests for Member 1 interface & audit reports
    └── test_edge_cases.py    # 20 edge-case tests (missing, ambiguous, conflict, etc.)
```
