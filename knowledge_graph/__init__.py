"""Government Tender Bid Compliance System - Knowledge Graph Layer.

Provides local, air-gapped Knowledge Graph modeling, idempotent ingestion,
parameterized Cypher queries, and structured risk feature extraction for
the Procurement System.
"""

from knowledge_graph.builder import KnowledgeGraphBuilder
from knowledge_graph.config import KnowledgeGraphConfig, default_config
from knowledge_graph.connection import (
    KnowledgeGraphConnectionError,
    Neo4jConnection,
)
from knowledge_graph.feature_extractor import RiskFeatureExtractor
from knowledge_graph.importer import ImportStats, KnowledgeGraphImporter
from knowledge_graph.models import (
    BidderRiskFeatures,
    CompanyNode,
    ContractNode,
    DebarmentRecordNode,
    DocumentNode,
    FinancialRecordNode,
    GovernmentRecordNode,
    GSTRecordNode,
    OEMRecordNode,
    OrganizationNode,
    PANRecordNode,
    PerformanceNode,
    ProductNode,
    ProvenanceMetadata,
    RecordTypeEnum,
    RequirementNode,
    TenderNode,
    UdyamRecordNode,
)
from knowledge_graph.queries import (
    find_companies_by_product,
    get_bidder_financial_history,
    get_bidder_government_registrations,
    get_bidder_historical_contracts,
    get_bidder_oem_relationships,
    get_bidder_performance_history,
    get_bidder_profile,
    get_bidders_for_tender,
    get_tenders_for_bidder,
    get_tender_requirements,
)
from knowledge_graph.schema import get_all_schema_ddl, init_schema

__version__ = "1.0.0"

__all__ = [
    "KnowledgeGraphConfig",
    "default_config",
    "Neo4jConnection",
    "KnowledgeGraphConnectionError",
    "KnowledgeGraphBuilder",
    "KnowledgeGraphImporter",
    "ImportStats",
    "RiskFeatureExtractor",
    "init_schema",
    "get_all_schema_ddl",
    # Models
    "ProvenanceMetadata",
    "CompanyNode",
    "TenderNode",
    "RequirementNode",
    "GovernmentRecordNode",
    "PANRecordNode",
    "GSTRecordNode",
    "UdyamRecordNode",
    "FinancialRecordNode",
    "DebarmentRecordNode",
    "OEMRecordNode",
    "OrganizationNode",
    "ProductNode",
    "ContractNode",
    "PerformanceNode",
    "DocumentNode",
    "BidderRiskFeatures",
    "RecordTypeEnum",
    # Queries
    "get_bidder_profile",
    "get_tender_requirements",
    "get_bidders_for_tender",
    "get_tenders_for_bidder",
    "get_bidder_financial_history",
    "get_bidder_government_registrations",
    "get_bidder_oem_relationships",
    "get_bidder_historical_contracts",
    "get_bidder_performance_history",
    "find_companies_by_product",
]

