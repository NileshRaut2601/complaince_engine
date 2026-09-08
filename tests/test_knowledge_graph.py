"""Unit and integration tests for the Tender Knowledge Graph layer.

Tests:
1. Neo4j connection handling & offline detection
2. Schema constraints & index DDL generation
3. Entity models & provenance validation
4. Tender & Requirement data transformation
5. Government records data transformation
6. Idempotence & dry-run consistency
7. Cypher query parameterization & security
8. Risk feature extraction & data boundaries (None for unrecorded data)
9. Invalid / malformed record handling
10. Live database integration tests (conditionally skipped if Neo4j offline)
"""

import json
from pathlib import Path
import pytest

from knowledge_graph.config import KnowledgeGraphConfig
from knowledge_graph.connection import (
    KnowledgeGraphConnectionError,
    Neo4jConnection,
)
from knowledge_graph.feature_extractor import RiskFeatureExtractor
from knowledge_graph.importer import (
    KnowledgeGraphImporter,
    extract_product_from_title,
)
from knowledge_graph.models import (
    BidderRiskFeatures,
    CompanyNode,
    ContractNode,
    DebarmentRecordNode,
    DocumentNode,
    FinancialRecordNode,
    GSTRecordNode,
    OEMRecordNode,
    OrganizationNode,
    PANRecordNode,
    PerformanceNode,
    ProductNode,
    ProvenanceMetadata,
    RequirementNode,
    TenderNode,
    UdyamRecordNode,
)
from knowledge_graph.queries import (
    CYPHER_FIND_COMPANIES_BY_PRODUCT,
    CYPHER_GET_BIDDER_FINANCIAL_HISTORY,
    CYPHER_GET_BIDDER_GOV_REGISTRATIONS,
    CYPHER_GET_BIDDER_HISTORICAL_CONTRACTS,
    CYPHER_GET_BIDDER_OEM_RELATIONSHIPS,
    CYPHER_GET_BIDDER_PERFORMANCE_HISTORY,
    CYPHER_GET_BIDDER_PROFILE,
    CYPHER_GET_BIDDERS_FOR_TENDER,
    CYPHER_GET_TENDER_REQUIREMENTS,
    CYPHER_GET_TENDERS_FOR_BIDDER,
)
from knowledge_graph.schema import CONSTRAINTS, INDEXES, get_all_schema_ddl

# Helper to check if Neo4j is running locally
def is_live_neo4j_available() -> bool:
    try:
        conn = Neo4jConnection()
        return conn.ping(timeout_seconds=1.0)
    except Exception:
        return False


# ===========================================================================
# 1. Configuration & Connection Tests
# ===========================================================================

class TestConfigAndConnection:
    """Test configuration parsing and safe connection handling."""

    def test_default_config_values(self):
        cfg = KnowledgeGraphConfig()
        assert cfg.uri.startswith("bolt://") or cfg.uri.startswith("neo4j://")
        assert cfg.database == "neo4j"
        assert cfg.batch_size == 100

    def test_mask_password_in_safe_dict_and_repr(self):
        cfg = KnowledgeGraphConfig(password="SuperSecretPassword123!")
        safe = cfg.to_safe_dict()
        assert safe["password"] == "***"
        assert "SuperSecretPassword123!" not in repr(cfg)

    def test_offline_ping_graceful_handling(self):
        # Configure non-existent port to test offline detection
        cfg = KnowledgeGraphConfig(uri="bolt://127.0.0.1:59999")
        conn = Neo4jConnection(cfg)
        # ping() must return False without crashing or throwing an unhandled exception
        assert conn.ping(timeout_seconds=0.5) is False
        conn.close()


# ===========================================================================
# 2. Schema DDL & Uniqueness Constraints Tests
# ===========================================================================

class TestSchemaInitialization:
    """Test Cypher schema DDL statements."""

    def test_required_uniqueness_constraints_present(self):
        names = [name for name, _ in CONSTRAINTS]
        required = [
            "company_id_unique",
            "tender_ref_unique",
            "requirement_id_unique",
            "gov_record_id_unique",
            "org_name_unique",
            "product_id_unique",
            "contract_id_unique",
            "performance_id_unique",
            "document_id_unique",
        ]
        for req in required:
            assert req in names, f"Missing constraint: {req}"

    def test_constraint_syntax_compliance(self):
        ddls = get_all_schema_ddl()
        assert len(ddls) >= 13
        for ddl in ddls:
            assert "IF NOT EXISTS" in ddl
            assert ddl.startswith("CREATE CONSTRAINT") or ddl.startswith("CREATE INDEX")


# ===========================================================================
# 3. Entity Models & Provenance Validation Tests
# ===========================================================================

class TestEntityModels:
    """Test Pydantic validation of graph node entities."""

    def test_provenance_metadata_defaults(self):
        prov = ProvenanceMetadata(
            source_file="tenders.json",
            source_record_id="GEM/001",
        )
        assert prov.source_file == "tenders.json"
        assert prov.source_type == "synthetic_dataset"
        assert prov.extraction_method == "direct_ingestion"
        assert prov.created_at is not None

    def test_company_node_creation(self):
        prov = ProvenanceMetadata(source_file="gov.json", source_record_id="CMP-001")
        cmp = CompanyNode(
            company_id="CMP-001",
            legal_name="Alpha Tech Ltd",
            trade_name="Alpha",
            status="ACTIVE",
            category="Company",
            state_jurisdiction="Maharashtra",
            provenance=prov,
        )
        assert cmp.company_id == "CMP-001"
        assert cmp.status == "ACTIVE"

    def test_tender_node_numeric_fields(self):
        prov = ProvenanceMetadata(source_file="tenders.json", source_record_id="T001")
        tender = TenderNode(
            reference_number="GEM/2026/B/1",
            title="Supply of 33kV Transformers",
            estimated_value=290000000.0,
            minimum_turnover=100000000.0,
            minimum_local_content=50.0,
            provenance=prov,
        )
        assert tender.estimated_value == 290000000.0
        assert tender.minimum_turnover == 100000000.0

    def test_requirement_node_composite_id(self):
        prov = ProvenanceMetadata(source_file="tenders.json", source_record_id="T001")
        req = RequirementNode(
            requirement_id="GEM/2026/B/1_turnover",
            tender_reference="GEM/2026/B/1",
            requirement_key="turnover",
            field="annual_turnover",
            type="numeric_threshold",
            operator=">=",
            value=50000000.0,
            currency="INR",
            mandatory=True,
            provenance=prov,
        )
        assert req.requirement_id == "GEM/2026/B/1_turnover"
        assert req.operator == ">="
        assert req.mandatory is True


# ===========================================================================
# 4. Dataset Transformation Tests (Against Actual Project Files)
# ===========================================================================

class TestDataTransformation:
    """Test data extraction against the actual project JSON files."""

    @pytest.fixture
    def importer(self):
        return KnowledgeGraphImporter()

    def test_parse_actual_tenders_dataset(self, importer):
        tenders_path = Path(__file__).resolve().parent.parent / "data" / "tenders.json"
        raw = importer.load_json_file(tenders_path)
        tenders, requirements, products, errors = importer.parse_tenders_data(raw)

        assert len(errors) == 0
        assert len(tenders) == 20
        assert len(products) == 20
        # Each of the 20 tenders has 7 structured requirements = 140
        assert len(requirements) == 140

        # Check reference number uniqueness
        ref_nums = [t.reference_number for t in tenders]
        assert len(set(ref_nums)) == 20

        # Check sample requirement mapping
        sample_req = requirements[0]
        assert sample_req.tender_reference.startswith("GEM/2026/B/")
        assert sample_req.provenance.source_file == "tenders.json"

    def test_parse_actual_government_records_dataset(self, importer):
        gov_path = Path(__file__).resolve().parent.parent / "data" / "government_records.json"
        raw = importer.load_json_file(gov_path)
        companies, gov_records, organizations, errors = importer.parse_government_records_data(raw)

        assert len(errors) == 0
        assert len(companies) == 100
        assert len(gov_records) == 800  # 100 * (1 PAN + 1 GST + 1 Udyam + 3 Fin + 1 Debarment + 1 OEM)
        assert len(organizations) == 100

        # Check company IDs uniqueness
        c_ids = [c.company_id for c in companies]
        assert len(set(c_ids)) == 100
        assert "CMP-00001" in c_ids
        assert "CMP-00100" in c_ids

    def test_extract_product_title_helper(self):
        slug, name = extract_product_from_title(
            "Supply, Delivery and Commissioning of 33kV Electrical Switchgears & Transformers"
        )
        assert name == "33kV Electrical Switchgears & Transformers"
        assert "switchgears" in slug


# ===========================================================================
# 5. Idempotent Import Tests
# ===========================================================================

class TestIdempotentImport:
    """Verify that importing multiple times produces identical data models."""

    def test_dry_run_import_stats_stability(self):
        importer = KnowledgeGraphImporter()
        tenders_path = Path(__file__).resolve().parent.parent / "data" / "tenders.json"
        gov_path = Path(__file__).resolve().parent.parent / "data" / "government_records.json"

        stats1 = importer.import_all(tenders_path, gov_path, dry_run=True)
        stats2 = importer.import_all(tenders_path, gov_path, dry_run=True)

        assert stats1.companies_processed == stats2.companies_processed == 100
        assert stats1.tenders_processed == stats2.tenders_processed == 20
        assert stats1.requirements_processed == stats2.requirements_processed == 140
        assert stats1.nodes_created == stats2.nodes_created == 1180
        assert stats1.relationships_created == stats2.relationships_created == 1060
        assert stats1.invalid_records == stats2.invalid_records == 0


# ===========================================================================
# 6. Cypher Query Parameterization & Security Tests
# ===========================================================================

class TestCypherSecurity:
    """Verify that all Cypher queries are strictly parameterized without string formatting."""

    def test_no_unsafe_string_interpolation_in_queries(self):
        queries = [
            CYPHER_GET_BIDDER_PROFILE,
            CYPHER_GET_TENDER_REQUIREMENTS,
            CYPHER_GET_BIDDERS_FOR_TENDER,
            CYPHER_GET_TENDERS_FOR_BIDDER,
            CYPHER_GET_BIDDER_FINANCIAL_HISTORY,
            CYPHER_GET_BIDDER_GOV_REGISTRATIONS,
            CYPHER_GET_BIDDER_OEM_RELATIONSHIPS,
            CYPHER_GET_BIDDER_HISTORICAL_CONTRACTS,
            CYPHER_GET_BIDDER_PERFORMANCE_HISTORY,
            CYPHER_FIND_COMPANIES_BY_PRODUCT,
        ]
        for q in queries:
            assert "$" in q, "Query must contain parameters ($param)"
            # Ensure no python f-string or percent formatting markers remain in raw queries
            assert "%s" not in q
            assert "{company_id}" not in q
            assert "{reference_number}" not in q


# ===========================================================================
# 7. Risk Feature Extractor & Data Boundaries Tests
# ===========================================================================

class TestRiskFeatureExtractor:
    """Verify feature extraction logic, data boundaries, and null handling."""

    def test_features_calculated_from_profile(self):
        extractor = RiskFeatureExtractor()
        mock_profile = {
            "company_id": "CMP-00001",
            "legal_name": "Test Technologies Ltd",
            "pan_record": {"pan": "ABCDE1234F", "status": "VALID"},
            "gst_record": {"gstin": "27ABCDE1234F1Z5", "status": "ACTIVE"},
            "udyam_record": {"udyam_number": "UDYAM-MH-01-0001234"},
            "debarment_record": {"is_debarred": False},
            "oem_record": {"authorization_code": "OEM-123"},
            "financial_records": [
                {"financial_year": "2023-2024", "turnover": 900000000.0, "net_profit": 45000000.0},
                {"financial_year": "2022-2023", "turnover": 600000000.0, "net_profit": 30000000.0},
            ],
        }

        feats = extractor.extract_features_from_profile_dict(mock_profile)

        assert feats.company_id == "CMP-00001"
        assert feats.has_valid_pan is True
        assert feats.has_active_gst is True
        assert feats.has_udyam is True
        assert feats.debarment_status is False
        assert feats.oem_authorized is True
        assert feats.financial_years_count == 2
        assert feats.latest_turnover == 900000000.0
        assert feats.average_turnover_3yr == 750000000.0
        assert feats.latest_net_profit == 45000000.0

    def test_missing_contracts_strictly_return_none_not_zero(self):
        """CRITICAL DATA BOUNDARY: Do NOT fabricate 0s for unrecorded historical performance."""
        extractor = RiskFeatureExtractor()
        mock_profile = {
            "company_id": "CMP-00002",
            "pan_record": {"status": "VALID"},
        }
        # When contracts list is None (dataset does not contain contract tracking)
        feats = extractor.extract_features_from_profile_dict(mock_profile, contracts=None)

        assert feats.historical_contract_count is None
        assert feats.successful_contract_count is None
        assert feats.delayed_contract_count is None
        assert feats.penalty_count is None
        assert feats.termination_count is None
        assert feats.dispute_count is None
        assert feats.similar_product_contract_count is None

        # Compliance score must also be None (owned by compliance engine)
        assert feats.compliance_score is None

    def test_debarred_company_flagged(self):
        extractor = RiskFeatureExtractor()
        mock_profile = {
            "company_id": "CMP-DEBARRED",
            "debarment_record": {"is_debarred": True},
        }
        feats = extractor.extract_features_from_profile_dict(mock_profile)
        assert feats.debarment_status is True


# ===========================================================================
# 8. Malformed & Edge Case Record Handling Tests
# ===========================================================================

class TestMalformedRecordHandling:
    """Test resilience against missing or invalid records."""

    def test_skip_tender_without_reference_number(self):
        importer = KnowledgeGraphImporter()
        malformed = [
            {"title": "No Ref Tender", "requirements": []},
            {"reference_number": "GEM/VALID/1", "title": "Valid Tender"},
        ]
        tenders, reqs, prods, errors = importer.parse_tenders_data(malformed)
        assert len(tenders) == 1
        assert tenders[0].reference_number == "GEM/VALID/1"
        assert len(errors) == 1
        assert "missing 'reference_number'" in errors[0]

    def test_skip_company_without_company_id(self):
        importer = KnowledgeGraphImporter()
        malformed = [
            {"pan_record": {"pan": "ABCDE1234F"}},
            {"company_id": "CMP-VALID-1", "pan_record": {"pan": "XYZ123"}},
        ]
        companies, recs, orgs, errors = importer.parse_government_records_data(malformed)
        assert len(companies) == 1
        assert companies[0].company_id == "CMP-VALID-1"
        assert len(errors) == 1
        assert "missing 'company_id'" in errors[0]

    def test_skip_requirement_without_key(self):
        importer = KnowledgeGraphImporter()
        tender_with_bad_req = [
            {
                "reference_number": "GEM/REQ/1",
                "requirements": [
                    {"definition": {"field": "pan"}},  # Missing requirement_key
                    {"requirement_key": "valid_key", "definition": {"field": "gstin"}},
                ],
            }
        ]
        tenders, reqs, prods, errors = importer.parse_tenders_data(tender_with_bad_req)
        assert len(reqs) == 1
        assert reqs[0].requirement_key == "valid_key"
        assert len(errors) == 1


# ===========================================================================
# 9. Live Database Integration Tests (Conditional)
# ===========================================================================

@pytest.mark.skipif(not is_live_neo4j_available(), reason="Neo4j instance is not running locally")
class TestLiveNeo4jIntegration:
    """Integration tests running only when a live Neo4j instance is available."""

    def test_live_schema_and_import(self):
        from knowledge_graph.builder import KnowledgeGraphBuilder
        with KnowledgeGraphBuilder() as builder:
            stats = builder.build_graph()
            assert stats.nodes_created >= 0
            assert stats.invalid_records == 0

