"""Knowledge Graph schema initialization, uniqueness constraints, and indexes.

Ensures idempotent database initialization using standard Neo4j Cypher syntax.
"""

from __future__ import annotations

import logging
from typing import Optional
from knowledge_graph.connection import Neo4jConnection, KnowledgeGraphConnectionError

logger = logging.getLogger("knowledge_graph.schema")

# Standard uniqueness constraints (Neo4j 4.4+ / 5.x / 6.x compatible)
CONSTRAINTS: list[tuple[str, str]] = [
    (
        "company_id_unique",
        "CREATE CONSTRAINT company_id_unique IF NOT EXISTS FOR (c:Company) REQUIRE c.company_id IS UNIQUE",
    ),
    (
        "tender_ref_unique",
        "CREATE CONSTRAINT tender_ref_unique IF NOT EXISTS FOR (t:Tender) REQUIRE t.reference_number IS UNIQUE",
    ),
    (
        "requirement_id_unique",
        "CREATE CONSTRAINT requirement_id_unique IF NOT EXISTS FOR (r:Requirement) REQUIRE r.requirement_id IS UNIQUE",
    ),
    (
        "gov_record_id_unique",
        "CREATE CONSTRAINT gov_record_id_unique IF NOT EXISTS FOR (g:GovernmentRecord) REQUIRE g.record_id IS UNIQUE",
    ),
    (
        "org_name_unique",
        "CREATE CONSTRAINT org_name_unique IF NOT EXISTS FOR (o:Organization) REQUIRE o.name IS UNIQUE",
    ),
    (
        "product_id_unique",
        "CREATE CONSTRAINT product_id_unique IF NOT EXISTS FOR (p:Product) REQUIRE p.product_id IS UNIQUE",
    ),
    (
        "contract_id_unique",
        "CREATE CONSTRAINT contract_id_unique IF NOT EXISTS FOR (ct:Contract) REQUIRE ct.contract_id IS UNIQUE",
    ),
    (
        "performance_id_unique",
        "CREATE CONSTRAINT performance_id_unique IF NOT EXISTS FOR (pf:Performance) REQUIRE pf.performance_id IS UNIQUE",
    ),
    (
        "document_id_unique",
        "CREATE CONSTRAINT document_id_unique IF NOT EXISTS FOR (d:Document) REQUIRE d.document_id IS UNIQUE",
    ),
]

# Secondary query indexes
INDEXES: list[tuple[str, str]] = [
    (
        "tender_status_index",
        "CREATE INDEX tender_status_index IF NOT EXISTS FOR (t:Tender) ON (t.status)",
    ),
    (
        "gov_record_type_index",
        "CREATE INDEX gov_record_type_index IF NOT EXISTS FOR (g:GovernmentRecord) ON (g.record_type)",
    ),
    (
        "company_legal_name_index",
        "CREATE INDEX company_legal_name_index IF NOT EXISTS FOR (c:Company) ON (c.legal_name)",
    ),
    (
        "requirement_key_index",
        "CREATE INDEX requirement_key_index IF NOT EXISTS FOR (r:Requirement) ON (r.requirement_key)",
    ),
]


def get_all_schema_ddl() -> list[str]:
    """Return all DDL statements for constraints and indexes."""
    return [stmt for _, stmt in CONSTRAINTS] + [stmt for _, stmt in INDEXES]


def init_schema(conn: Neo4jConnection) -> dict[str, int]:
    """Execute all schema DDL statements against the connected Neo4j instance.

    Returns:
        Summary dict containing counts of created/verified constraints and indexes.
    """
    if not conn.ping():
        raise KnowledgeGraphConnectionError(
            f"Cannot initialize schema: Neo4j database is unreachable at {conn.config.uri}"
        )

    constraints_applied = 0
    indexes_applied = 0

    with conn.session() as session:
        for name, ddl in CONSTRAINTS:
            try:
                session.run(ddl)
                constraints_applied += 1
                logger.info("Applied constraint: %s", name)
            except Exception as e:
                logger.warning("Error applying constraint %s: %s", name, str(e))

        for name, ddl in INDEXES:
            try:
                session.run(ddl)
                indexes_applied += 1
                logger.info("Applied index: %s", name)
            except Exception as e:
                logger.warning("Error applying index %s: %s", name, str(e))

    return {
        "constraints_applied": constraints_applied,
        "indexes_applied": indexes_applied,
    }

