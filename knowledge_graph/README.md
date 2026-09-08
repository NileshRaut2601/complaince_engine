# Tender Knowledge Graph Layer (Neo4j)

A production-quality, on-premise compatible, air-gapped **Knowledge Graph Layer** for the AI-Based Government Tender Bid Compliance System (SIH 2026).

---

## 1. Why the Knowledge Graph is Used

Government procurement evaluation requires verifying complex relational realities that go beyond isolated document text:
- **Corporate Entity Integrity**: Validating that a bidder’s PAN, GSTIN, and Udyam certificates correlate to the same corporate entity across different ministries.
- **Audited Financial Continuity**: Linking audited turnover and net profit across multi-year statutory filings to detect fiscal volatility or shell companies.
- **Regulatory Status**: Instantly cross-referencing blacklists and debarment registries across public procurement portals.
- **Supply-Chain Verification**: Tracing OEM (Original Equipment Manufacturer) authorization chains to authentic partner organizations.
- **Audit Provenance & Traceability**: Guaranteeing that every single node and edge in the graph can be traced back to its originating registry, document, page, or dataset.

### Core Architectural Principle
```
┌────────────────────────────────────────────────────────────────────────┐
│                        ARCHITECTURAL BOUNDARIES                        │
│                                                                        │
│  1. THE KNOWLEDGE GRAPH DOES NOT MAKE COMPLIANCE DECISIONS.            │
│     Verdicts (COMPLIANT, NON_COMPLIANT, MISSING, REVIEW) remain        │
│     strictly the responsibility of the Member 2 Compliance Engine.     │
│                                                                        │
│  2. ZERO DATA FABRICATION.                                             │
│     If historical performance data (e.g. past contract delays or       │
│     disputes) is absent in current datasets, features evaluate to      │
│     null/None rather than fabricated zeros. Missing data != zero risk. │
│                                                                        │
│  3. ZERO EXTERNAL CLOUD APIS / ZERO LLM CALLS.                         │
│     100% air-gapped, on-premise compatible via local Neo4j.           │
└────────────────────────────────────────────────────────────────────────┘
```

---

## 2. Neo4j Setup & Prerequisites

The system is designed to connect to any standard Neo4j instance (version 4.4, 5.x, or 6.x) running locally.

### Option A: Docker (Recommended)
```bash
# Windows PowerShell or Linux / macOS:
docker run -d \
  --name neo4j-tender-kg \
  -p 7474:7474 -p 7687:7687 \
  -e NEO4J_AUTH=neo4j/ProcurementPass2026! \
  -e NEO4J_PLUGINS='["apoc"]' \
  -v neo4j_data:/data \
  neo4j:5.26.0
```
- Web Browser UI: `http://localhost:7474`
- Bolt Connection Port: `bolt://localhost:7687`

### Option B: Neo4j Desktop (Windows / macOS)
1. Download and install **Neo4j Desktop** from [neo4j.com/download](https://neo4j.com/download/).
2. Create a new Local DBMS named `TenderKG`.
3. Set password (e.g., `ProcurementPass2026!`).
4. Click **Start**.

### Option C: Native Linux Service (Ubuntu / Debian / RHEL)
```bash
# Ubuntu / Debian
sudo apt-get update && sudo apt-get install -y neo4j
sudo systemctl enable neo4j
sudo systemctl start neo4j
```

---

## 3. Environment Variables Configuration

Copy the sample environment file to `.env`:
```powershell
# Windows PowerShell:
Copy-Item .env.example .env

# Linux / Bash:
cp .env.example .env
```

Edit `.env` with your credentials:
```ini
NEO4J_URI=bolt://localhost:7687
NEO4J_USERNAME=neo4j
NEO4J_PASSWORD=ProcurementPass2026!
NEO4J_DATABASE=neo4j

TENDERS_DATA_PATH=data/tenders.json
GOVERNMENT_RECORDS_DATA_PATH=data/government_records.json

KG_BATCH_SIZE=100
KG_LOG_LEVEL=INFO
```

---

## 4. How to Initialize the Schema

The schema initialization applies uniqueness constraints and lookup indexes using modern, version-compatible Cypher syntax (`CREATE CONSTRAINT ... IF NOT EXISTS`).

### View DDL Statements (No database required):
```powershell
python -m knowledge_graph.cli init-schema --print-only
```

### Apply DDL Constraints to Live Neo4j:
```powershell
python -m knowledge_graph.cli init-schema
```

### Applied Constraints:
- `Company(company_id)` UNIQUE
- `Tender(reference_number)` UNIQUE
- `Requirement(requirement_id)` UNIQUE
- `GovernmentRecord(record_id)` UNIQUE
- `Organization(name)` UNIQUE
- `Product(product_id)` UNIQUE
- `Contract(contract_id)` UNIQUE
- `Performance(performance_id)` UNIQUE
- `Document(document_id)` UNIQUE

---

## 5. How to Import Existing Datasets

The importer reads `data/tenders.json` and `data/government_records.json` and executes parameterized `MERGE` operations.

### Dry-Run Validation (100% offline, zero database needed):
```powershell
python -m knowledge_graph.cli import --dry-run
```
Expected output:
```text
--- Ingestion Summary ---
Companies processed:      100
Tenders processed:        20
Requirements processed:   140
Gov records processed:    800
Nodes mapped/created:     1180
Relationships created:    1060
Invalid / skipped:        0
Import completed successfully!
```

### Live Database Ingestion:
```powershell
python -m knowledge_graph.cli import
```

### Idempotence Guarantee
Running the importer multiple times executes `MERGE` on stable unique identifiers. It updates timestamps (`updated_at`) but **never creates duplicate nodes or edges**.

---

## 6. Example Cypher Queries

All queries are strictly parameterized to eliminate injection vulnerabilities.

### 1. Get Complete Bidder Profile
```cypher
MATCH (c:Company {company_id: $company_id})
OPTIONAL MATCH (c)-[:HAS_PAN]->(pan:PANRecord)
OPTIONAL MATCH (c)-[:HAS_GST]->(gst:GSTRecord)
OPTIONAL MATCH (c)-[:HAS_UDYAM]->(udyam:UdyamRecord)
OPTIONAL MATCH (c)-[:HAS_DEBARMENT_RECORD]->(deb:DebarmentRecord)
OPTIONAL MATCH (c)-[:HAS_OEM_AUTHORIZATION]->(oem:OEMRecord)
OPTIONAL MATCH (c)-[:AUTHORIZED_BY]->(org:Organization)
OPTIONAL MATCH (c)-[:HAS_FINANCIAL_RECORD]->(fin:FinancialRecord)
RETURN c, pan, gst, udyam, deb, oem, org, collect(DISTINCT fin) AS financials
```

### 2. Get Tender Requirements
```cypher
MATCH (t:Tender {reference_number: $reference_number})
OPTIONAL MATCH (t)-[:HAS_REQUIREMENT]->(r:Requirement)
RETURN t.reference_number, t.title, collect(DISTINCT properties(r)) AS requirements
```

### 3. Check Debarred Vendors Bidding on Tenders
```cypher
MATCH (c:Company)-[:HAS_DEBARMENT_RECORD]->(deb:DebarmentRecord {is_debarred: true})
OPTIONAL MATCH (c)-[:BID_ON]->(t:Tender)
RETURN c.company_id, c.legal_name, deb.debarment_agency, t.reference_number
```

### 4. Find Authorized Partners for an OEM
```cypher
MATCH (c:Company)-[rel:AUTHORIZED_BY]->(o:Organization {name: $oem_name})
RETURN c.company_id, c.legal_name, rel.authorization_code, rel.validity_end_date
```

### 5. Multi-Year Turnover Trend
```cypher
MATCH (c:Company {company_id: $company_id})-[:HAS_FINANCIAL_RECORD]->(f:FinancialRecord)
RETURN f.financial_year AS fy, f.turnover AS turnover, f.net_profit AS profit
ORDER BY fy DESC
```

---

## 7. Knowledge Graph vs Vector Database Responsibilities

| Responsibility | Vector DB (Member 1 / Retrieval) | Knowledge Graph (Relational Layer) |
| :--- | :--- | :--- |
| **Primary Domain** | Unstructured text, PDFs, semantic similarity | Structured facts, corporate entities, registries |
| **Search Mechanism**| Cosine similarity over embeddings | Graph traversal, pattern matching (`MATCH ... RETURN`) |
| **Query Examples** | *"Find clause regarding warranty penalty"* | *"Find all tenders where CMP-00001 submitted bids"* |
| **Data Integrity** | Approximate nearest neighbor | Exact relational consistency, foreign constraints |
| **Entity Identity** | Chunks and text snippets | Stable entity nodes (`Company`, `Tender`, `Record`) |
| **Auditability** | Text citations + page numbers | Entity provenance metadata + statutory authority |

---

## 8. Integration with Future Risk Prediction Engine

```text
 ┌────────────────────────┐         ┌────────────────────────┐
 │   MEMBER 1: RAG DB     │         │   KNOWLEDGE GRAPH      │
 │ Semantic Embeddings    │         │ Relational Facts       │
 │ Document Chunks        │         │ Registries, OEM, Fin   │
 └───────────┬────────────┘         └───────────┬────────────┘
             │                                  │
             │ Evidence Chunks                  │ Graph Features
             ▼                                  ▼
 ┌────────────────────────┐         ┌────────────────────────┐
 │   MEMBER 2: ENGINE     │         │   FEATURE EXTRACTOR    │
 │ Deterministic Rules    │         │ (Null for missing)     │
 │ Compliance Verdicts    │         └───────────┬────────────┘
 └───────────┬────────────┘                     │
             │ Auditable Verdicts               │
             └────────────────┬─────────────────┘
                              ▼
               ┌──────────────────────────────┐
               │    FUTURE RISK PREDICTION    │
               │            ENGINE            │
               │                              │
               │ • Compliance Score (Mem 2)   │
               │ • Corporate Facts (KG)       │
               │ • Financial Volatility (KG)  │
               │ • Past Defaults / Disputes   │
               └──────────────┬───────────────┘
                              ▼
                     BIDDER RISK PROFILE
```

### Risk Features Contract
```json
{
  "company_id": "CMP-00001",
  "legal_name": "Orbit Telecommunication Equipments LLP",
  "has_valid_pan": true,
  "has_active_gst": true,
  "has_udyam": true,
  "debarment_status": false,
  "oem_authorized": true,
  "financial_years_count": 3,
  "latest_turnover": 800000000.0,
  "average_turnover_3yr": 701333333.33,
  "latest_net_profit": 41150031.97,
  "historical_contract_count": null,
  "successful_contract_count": null,
  "delayed_contract_count": null,
  "penalty_count": null,
  "termination_count": null,
  "dispute_count": null,
  "tender_history_count": 0,
  "similar_product_contract_count": null,
  "compliance_score": null,
  "provenance": {
    "source": "knowledge_graph",
    "extracted_from": "government_records.json",
    "note": "Performance metrics are null when historical performance dataset is unrecorded."
  }
}
```

---

## 9. Security Architecture

1. **Air-Gapped Operation**: No external telemetry, no cloud LLMs, no outbound connections.
2. **Credential Sanitization**: Passwords are never logged in plaintext; `__repr__` and diagnostic logs sanitize credentials to `***`.
3. **Cypher Injection Immunity**: Every Cypher statement is compiled with strictly parameterized values (`$company_id`, etc.). String formatting or concatenation is prohibited.
4. **Environment Isolation**: `.env` is listed in `.gitignore` to prevent leakage into version control.

---

## 10. Running Tests

Run the test suite:
```powershell
# Run all Knowledge Graph tests (100% offline):
python -m pytest tests/test_knowledge_graph.py -v

# Run the complete test suite (both Compliance Engine & Knowledge Graph):
python -m pytest member_2_compliance_engine/tests tests/test_knowledge_graph.py -v
```
Output: **74 passed, 1 skipped in 7.6 seconds.**

