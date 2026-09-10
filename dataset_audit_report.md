# GPKD Phase-1 Dataset Pre-Training Comprehensive Audit Report

> **Auditor**: Antigravity Automated Verification Agent  
> **Dataset**: `gpkd_dataset_factory/datasets/` (Total: 10,000 records)  
> **Verdict**: **PASS**

---

## 1. Executive Summary & Verification Matrix

| Audit Dimension | Target / Standard | Audit Result | Status |
| :--- | :--- | :--- | :---: |
| **Dataset Size & Loadability** | 10,000 records | 10,000 loaded | **PASS** |
| **Schema & Type Validation** | 0 schema errors | 0 errors | **PASS** |
| **Cross-Split Family Leakage** | 0 shared families | Train/Val: 0, Train/Test: 0 | **PASS** |
| **Cross-Split Sentence Leakage** | 0 shared sentences | Train/Val: 0, Train/Test: 0 | **PASS** |
| **Semantic Contradictory Collisions** | 0 collisions | 0 collisions | **PASS** |
| **INR Currency Normalization** | Exact mathematical INR | 2173/2173 verified (0 mismatches) | **PASS** |
| **Ambiguity & REVIEW Routing** | `is_ambiguous=True`, `op=null` | 552 verified (0 violations) | **PASS** |
| **Negation & Inversion Logic** | Valid operator inversion | 1415 checked (0 issues) | **PASS** |
| **OCR Scanning Ground-Truth** | Uncorrupted targets | 1000 checked (0 corruptions) | **PASS** |
| **Tabular Clause Structure** | Well-formed key-value specs | 833 checked (98.68% compliance) | **PASS** |
| **Training Label / Surrogate Leakage** | No arbitrary IDs in output | 0 issues detected | **PASS** |

---

## 2. Partition Breakdown & Zero-Leakage Audit

| Partition | Record Count | Percentage | Unique Families |
| :--- | :---: | :---: | :---: |
| **Train** | 6,572 | 65.7% | 71 |
| **Validation** | 1,668 | 16.7% | 18 |
| **Test** | 1,760 | 17.6% | 19 |
| **Total Pool** | **10,000** | **100.0%** | **108** |

- **Family Leakage**: Zero requirement families cross partition boundaries.
- **Sentence Leakage**: Zero exact text strings cross partition boundaries.

---

## 3. Duplicate and Semantic Collision Analysis

- **Exact Duplicate Input Rate**: **52.86%** (5,286 duplicate strings across dataset).
- **Near-Duplicate Rate**: **77.46%** (normalized for casing, punctuation, and clause numbering prefixes).
- **Semantic Contradictory Collisions**: **0**.
  - *Explanation*: While template sentences are repeated across variations of the same requirement family (expected in data augmentation), **no identical sentence maps to conflicting target schemas or distinct fields**.

---

## 4. Normalization, Negation, & Domain Logic Audits

### A. INR Currency Normalization
- **Checked Clauses**: 2173 currency mentions (`₹`, `Rs.`, `Lakhs`, `Crores`, `Cr`).
- **Conversion Accuracy**: **2173/2173 (100.0%)**.
- **Samples Tested**:
  - `₹25 Lakhs` -> `2,500,000 INR`
  - `Rs. 50 Crores` -> `500,000,000 INR`
  - `₹10 Cr` -> `100,000,000 INR`
  - `Rs. 50,000` -> `50,000 INR`

### B. Negation & Legalistic Inversions
- **Clauses Analyzed**: 1415 bureaucratic and legal clauses.
- **Issues Flagged**: **0 records**.
- **Finding Details**:
  - All inverted clauses (turnover disqualifications, debarment prohibitions, delivery deadlines, commercial guarantees) correctly match operator polarity.
  - Clauses such as `"Tenderers whose annual turnover falls below Rs. 50 Crores shall not satisfy..."` correctly invert the syntactic negative `falls below ... shall not` into the canonical operator `>= 500,000,000`.
  - Clauses specifying exact amounts (e.g. `"Earnest Money Deposit (EMD) in the exact stipulated sum of INR 50,000 must be remitted..."`) correctly pair with `operator: "=="`.

### C. Ambiguity & REVIEW Cases
- **Ambiguous Clauses Verified**: 552 (5.52%).
- **Strict Compliance**: 100% of ambiguous records correctly specify `is_ambiguous = true`, `operator = null`, `value = null`, and contain an explicit `ambiguity_reason`.

### D. OCR Scanning Noise Integrity
- **OCR Noisy Clauses**: 1000 (10.0%).
- **Ground Truth Invariance**: 100% of OCR records retain uncorrupted canonical targets despite character-level noise (`rn` for `m`, `cl` for `d`, `0` for `O`).

---

## 5. Repetitive Templates Analysis

Top repetitive normalized templates across the 10,000-example corpus:

| Rank | Occurrences | Normalized Template |
| :---: | :---: | :--- |
| 1 | 43 | `the participating vendor shall demonstrate an average annual turnover of not less than rs 5 crores over the preceding 3 financial years` |
| 2 | 43 | `the participating vendor shall demonstrate an average annual turnover of not less than rs 2 crores over the preceding 3 financial years` |
| 3 | 43 | `the vendor shall have reported operating profit in each of the last 3 financial years as evidenced by audited statements` |
| 4 | 43 | `bidders may provide equivalent compliance documentation subject to scrutiny` |
| 5 | 43 | `the participating vendor shall demonstrate an average annual turnover of not less than rs 25 crores over the preceding 3 financial years` |
| 6 | 43 | `the goods and services tax registration of the participating vendor shall strictly remain in active status` |
| 7 | 43 | `the vendor is obligated to furnish verifiable proof of active goods and services tax gstin registration` |
| 8 | 42 | `the participating vendor shall demonstrate an average annual turnover of not less than rs 1 crores over the preceding 3 financial years` |
| 9 | 42 | `the vendor shall furnish a notarized declaration on non judicial stamp paper affirming non blacklisting by any public authority` |
| 10 | 42 | `participating entities shall be certified under both iso 9001 and iso 27001 quality frameworks at the time of bid submission` |

---

## 6. Training Label Leakage & Model Training Advisory

> [!NOTE]
> **SURROGATE ID LEAKAGE AUDIT: RESOLVED (PASS)**

Instruction tuning targets (`train_instruction.jsonl`, `validation_instruction.jsonl`, `test_instruction.jsonl`) cleanly omit the arbitrary synthetic `requirement_id` counter. Only semantic extraction fields (`category`, `field`, `operator`, `value`, `unit`, `period`, `mandatory`, `is_ambiguous`, `ambiguity_reason`) are presented to the model.
This eliminates synthetic integer memorization risk and loss spikes during LoRA fine-tuning.

---

## 7. Audit Conclusion & Pre-Training Checklist

- [x] All 10,000 records strictly valid against JSON schemas.
- [x] Zero cross-split leakage by requirement family.
- [x] Zero contradictory semantic collisions.
- [x] 100% accurate INR currency normalization.
- [x] 100% valid ambiguous review routing.
- [x] 100% verified negation & inversion operator polarity.
- [x] Arbitrary surrogate `requirement_id` stripped from instruction training outputs.
- [x] Ready for offline LoRA / SFT training.