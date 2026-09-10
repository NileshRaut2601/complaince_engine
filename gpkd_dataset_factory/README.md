# GPKD Dataset Factory (Phase 1)
## Government Procurement Knowledge Dataset Factory

A standalone, air-gapped, 100% deterministic Python synthetic dataset generator engineered to create high-quality training and evaluation corpora for:
1. **Local LLM Fine-Tuning** (Natural Language Tender Requirement Extraction $\to$ Canonical JSON)
2. **Knowledge Graph Seeding** (Entity & Relationship generation)
3. **RAG Retrieval & Evaluator Benchmarking**
4. **Zero-Leakage Model Auditing**

---

## 1. Phase 1 Objective: Tender Requirement Extraction

Converts diverse procurement requirements into machine-readable canonical rules:

```text
Natural Language Clause (Tender Document)
                   │
                   ▼
       [ LOCAL FINE-TUNED LLM ]
                   │
                   ▼
       Canonical Structured Rule
```

### Pipeline Flow:
```text
  Canonical Seed Vocabulary (tenders.json Grounding)
                     │
                     ▼
          Requirement Families
       (11 Categories + Ambiguous)
                     │
                     ▼
       Syntactic Clause Generator
       • Easy (Direct imperative)
       • Medium (Modal, temporal scopes)
       • Hard (Legalistic inversions, double negatives)
       • Table-like specifications
       • Ambiguous clauses (REVIEW / Non-committal)
                     │
                     ▼
      Controlled Mutation & OCR Noise
                     │
                     ▼
     Strict Validation Gate (Fail-Loudly)
                     │
                     ▼
     Family-Based Zero-Leakage Split
     70% Train | 15% Val | 15% Test
                     │
                     ▼
   Dual Export: Canonical JSONL + Alpaca Instruction Format
```

---

## 2. Canonical Target Schema

Every training record pairs natural language tender text with a standardized target representation:

```json
{
  "id": "GPKD_000001",
  "input": "The participating bidder shall demonstrate an average annual turnover of not less than INR 5 Crore over the preceding three financial years.",
  "target": {
    "requirement_id": "REQ_000001",
    "category": "financial",
    "field": "annual_turnover",
    "operator": ">=",
    "value": 50000000,
    "unit": "INR",
    "period": "preceding 3 financial years",
    "mandatory": true,
    "is_ambiguous": false,
    "ambiguity_reason": null
  },
  "metadata": {
    "source": "synthetic",
    "family_id": "FAM_FIN_AVG_TURNOVER_3YR_5Cr",
    "category": "financial",
    "difficulty": "medium",
    "generation_method": "procurement_formal",
    "noise_type": null,
    "generator_version": "1.0"
  }
}
```

### Ambiguous Clauses (Mirroring Compliance Engine `REVIEW`):
```json
{
  "id": "GPKD_000042",
  "input": "Depending on configuration, the compute nodes may provide 8 × 192 GB OR 16 × 96 GB memory.",
  "target": {
    "requirement_id": "REQ_000042",
    "category": "ambiguous",
    "field": "RAM",
    "operator": null,
    "value": null,
    "unit": null,
    "period": null,
    "mandatory": true,
    "is_ambiguous": true,
    "ambiguity_reason": "Conditional disjunctive configuration (8 x 192 GB OR 16 x 96 GB) without firm commitment"
  },
  "metadata": {
    "source": "synthetic",
    "family_id": "FAM_AMB_RAM_DISJUNCTIVE",
    "category": "ambiguous",
    "difficulty": "medium",
    "generation_method": "ambiguous_disjunction",
    "noise_type": null,
    "generator_version": "1.0"
  }
}
```

---

## 3. Supported Categories & Vocabulary

Ground truth vocabulary is grounded in actual GeM tenders (`data/tenders.json`) and spans **11 procurement domains**:

1. **FINANCIAL**: `annual_turnover`, `average_turnover`, `net_worth`, `solvency`, `profitability` (normalized to base INR).
2. **TAX_STATUTORY**: `pan`, `gstin`, `gst_status`, `itr_filing`.
3. **MSME**: `udyam`, `msme_classification` (Micro/Small/Medium), `nsic_registration`.
4. **EXPERIENCE**: `years_of_experience`, `completed_projects`, `government_project_experience`.
5. **TECHNICAL**: `cpu_cores`, `gpu_memory`, `ram_capacity`, `storage_capacity`, `network_bandwidth`, `operating_temperature`.
6. **CERTIFICATION**: `iso_certification` (e.g. ISO 9001, ISO 27001), `bis_certification`, `stqc_certificate`, `cert_in_audit`.
7. **OEM**: `oem_authorization` (MAF), `authorized_distributor`, `authorization_validity_period`.
8. **LOCAL_CONTENT**: `local_content_percentage` (Make in India), `make_in_india_class`.
9. **LEGAL**: `is_debarred` (`false`), `non_blacklisting_declaration`, `litigation_history`.
10. **COMMERCIAL**: `emd_amount`, `bid_security_declaration`, `performance_bank_guarantee_percentage`.
11. **DELIVERY**: `delivery_period`, `installation_period`, `warranty_period`.
12. **AMBIGUOUS**: Clauses that should NOT produce a falsely precise rule.

---

## 4. Key Generator Features

- **Linguistic Diversity**:
  - **Easy**: Direct, unambiguous declarative or imperative sentences.
  - **Medium**: Formal procurement phrasing with modals ("shall demonstrate", "is obligated to show") and temporal scopes.
  - **Hard**: Complex legalistic prose, double negations, and syntactic inversions ("Firms whose turnover falls below INR 5 Cr shall not meet this condition").
- **Table-like Specifications**: Synthesizes snippets mimicking tender tables (`Parameter: Memory | Minimum Requirement: 192 GB`).
- **Controlled OCR Noise**: Injects scanning artifacts (subtle character substitutions, `₹` $\to$ `Rs.`) while preserving 100% clean target JSON (`noise_type: "ocr"`).
- **Negation Handling**: Accurately maps "not less than" to `>=`, "not exceeding" to `<=`.
- **Compound Clauses**: Supports multi-clause conditions (e.g., holding both ISO 9001 and ISO 27001 via `includes_all`).

---

## 5. Zero-Leakage Dataset Splitting Strategy

A common flaw in synthetic NLP datasets is splitting sentences randomly. When random splits are used:
- *Train*: "The bidder must have turnover of at least ₹5 crore."
- *Test*: "The vendor shall demonstrate turnover not below INR 5 crore."
The test set is contaminated by memorization.

**GPKD Solution**: We partition strictly by **Requirement Family ID** (`family_id`).
All linguistic formulations, table representations, and OCR variations of a given semantic requirement belong exclusively to **either** Train, Validation, or Test. The test split evaluates genuine generalization to unseen parameter combinations.

---

## 6. How to Run

### Step 1: Run the Unit Tests
```powershell
python -m pytest gpkd_dataset_factory/tests -v
```

### Step 2: Generate the 10,000-Example Dataset
```powershell
python -m gpkd_dataset_factory.scripts.generate_dataset --count 10000 --seed 42
```
*Output saved to:* `gpkd_dataset_factory/datasets/raw/raw_dataset.jsonl`.

### Step 3: Validate the Raw Dataset
```powershell
python -m gpkd_dataset_factory.scripts.validate_dataset --input gpkd_dataset_factory/datasets/raw/raw_dataset.jsonl
```

### Step 4: Partition into Train / Validation / Test (Zero Leakage)
```powershell
python -m gpkd_dataset_factory.scripts.split_dataset --input gpkd_dataset_factory/datasets/raw/raw_dataset.jsonl
```
*Outputs:*
- `datasets/train/train.jsonl` (7,000 examples)
- `datasets/validation/validation.jsonl` (1,500 examples)
- `datasets/test/test.jsonl` (1,500 examples)
- Also exports fine-tuning ready `*_instruction.jsonl` files (Alpaca / HuggingFace format).

### Step 5: Verify Zero Leakage Across Partitions
```powershell
python -m gpkd_dataset_factory.scripts.validate_dataset --check-splits
```

### Step 6: Generate Quality Statistics
```powershell
python -m gpkd_dataset_factory.scripts.statistics --input gpkd_dataset_factory/datasets/raw/raw_dataset.jsonl
```
*Output saved to:* `gpkd_dataset_factory/datasets/statistics.json`.

---

## 7. Integration with Local LLM Fine-Tuning

The exported `*_instruction.jsonl` files are immediately compatible with Unsloth, Llama-Factory, Axolotl, or HuggingFace TRL:

```json
{
  "instruction": "You are a government procurement compliance assistant. Extract the structured tender requirement from the following natural language clause into the canonical JSON schema. Return strictly valid JSON.",
  "input": "Consignment delivery must be completed within 30 days.",
  "output": "{\"requirement_id\": \"REQ_001234\", \"category\": \"delivery\", \"field\": \"delivery_period\", \"operator\": \"<=\", \"value\": 30, \"unit\": \"days\", \"period\": null, \"mandatory\": true, \"is_ambiguous\": false, \"ambiguity_reason\": null}"
}
```

