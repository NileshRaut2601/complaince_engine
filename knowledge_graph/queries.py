"""Standard parameterized Cypher query functions for the Procurement Knowledge Graph.

Implements all 10 required domain queries with strict parameterization to eliminate
Cypher injection risks.
"""

from __future__ import annotations

import logging
from typing import Any, Optional
from knowledge_graph.connection import Neo4jConnection

logger = logging.getLogger("knowledge_graph.queries")


# ---------------------------------------------------------------------------
# Cypher Query Template Definitions (Parameterized)
# ---------------------------------------------------------------------------

CYPHER_GET_BIDDER_PROFILE = """
MATCH (c:Company {company_id: $company_id})
OPTIONAL MATCH (c)-[:HAS_PAN]->(pan:PANRecord)
OPTIONAL MATCH (c)-[:HAS_GST]->(gst:GSTRecord)
OPTIONAL MATCH (c)-[:HAS_UDYAM]->(udyam:UdyamRecord)
OPTIONAL MATCH (c)-[:HAS_DEBARMENT_RECORD]->(deb:DebarmentRecord)
OPTIONAL MATCH (c)-[:HAS_OEM_AUTHORIZATION]->(oem:OEMRecord)
OPTIONAL MATCH (c)-[:AUTHORIZED_BY]->(org:Organization)
OPTIONAL MATCH (c)-[:HAS_FINANCIAL_RECORD]->(fin:FinancialRecord)
WITH c, pan, gst, udyam, deb, oem, org, fin
ORDER BY fin.financial_year DESC
RETURN {
    company_id: c.company_id,
    legal_name: c.legal_name,
    trade_name: c.trade_name,
    status: c.status,
    category: c.category,
    state_jurisdiction: c.state_jurisdiction,
    enterprise_type: c.enterprise_type,
    major_activity: c.major_activity,
    pan_record: properties(pan),
    gst_record: properties(gst),
    udyam_record: properties(udyam),
    debarment_record: properties(deb),
    oem_record: properties(oem),
    oem_organization: properties(org),
    financial_records: collect(DISTINCT properties(fin))
} AS profile
"""

CYPHER_GET_TENDER_REQUIREMENTS = """
MATCH (t:Tender {reference_number: $reference_number})
OPTIONAL MATCH (t)-[:HAS_REQUIREMENT]->(r:Requirement)
RETURN t.reference_number AS reference_number,
       t.title AS tender_title,
       t.status AS tender_status,
       t.estimated_value AS estimated_value,
       collect(DISTINCT properties(r)) AS requirements
"""

CYPHER_GET_BIDDERS_FOR_TENDER = """
MATCH (t:Tender {reference_number: $reference_number})
OPTIONAL MATCH (c:Company)-[rel:BID_ON|WON]->(t)
RETURN t.reference_number AS reference_number,
       collect(DISTINCT {
           company_id: c.company_id,
           legal_name: c.legal_name,
           relationship: type(rel),
           status: c.status
       }) AS bidders
"""

CYPHER_GET_TENDERS_FOR_BIDDER = """
MATCH (c:Company {company_id: $company_id})
OPTIONAL MATCH (c)-[rel:BID_ON|WON]->(t:Tender)
RETURN c.company_id AS company_id,
       c.legal_name AS legal_name,
       collect(DISTINCT {
           reference_number: t.reference_number,
           title: t.title,
           relationship: type(rel),
           tender_status: t.status
       }) AS tenders
"""

CYPHER_GET_BIDDER_FINANCIAL_HISTORY = """
MATCH (c:Company {company_id: $company_id})-[:HAS_FINANCIAL_RECORD]->(f:FinancialRecord)
RETURN f.financial_year AS financial_year,
       f.turnover AS turnover,
       f.net_profit AS net_profit,
       f.filing_date AS filing_date,
       f.status AS status
ORDER BY f.financial_year DESC
"""

CYPHER_GET_BIDDER_GOV_REGISTRATIONS = """
MATCH (c:Company {company_id: $company_id})
OPTIONAL MATCH (c)-[:HAS_PAN]->(pan:PANRecord)
OPTIONAL MATCH (c)-[:HAS_GST]->(gst:GSTRecord)
OPTIONAL MATCH (c)-[:HAS_UDYAM]->(udyam:UdyamRecord)
OPTIONAL MATCH (c)-[:HAS_DEBARMENT_RECORD]->(deb:DebarmentRecord)
RETURN {
    company_id: c.company_id,
    legal_name: c.legal_name,
    pan: properties(pan),
    gst: properties(gst),
    udyam: properties(udyam),
    debarment: properties(deb)
} AS registrations
"""

CYPHER_GET_BIDDER_OEM_RELATIONSHIPS = """
MATCH (c:Company {company_id: $company_id})
OPTIONAL MATCH (c)-[:HAS_OEM_AUTHORIZATION]->(rec:OEMRecord)
OPTIONAL MATCH (c)-[auth:AUTHORIZED_BY]->(org:Organization)
RETURN collect(DISTINCT {
    oem_name: coalesce(rec.oem_name, org.name),
    authorization_code: coalesce(rec.authorization_code, auth.authorization_code),
    validity_end_date: coalesce(rec.validity_end_date, auth.validity_end_date),
    record_status: rec.status
}) AS oem_relationships
"""

CYPHER_GET_BIDDER_HISTORICAL_CONTRACTS = """
MATCH (c:Company {company_id: $company_id})
OPTIONAL MATCH (c)-[:EXECUTED]->(ct:Contract)
RETURN collect(DISTINCT properties(ct)) AS contracts
"""

CYPHER_GET_BIDDER_PERFORMANCE_HISTORY = """
MATCH (c:Company {company_id: $company_id})
OPTIONAL MATCH (c)-[:EXECUTED]->(ct:Contract)-[:HAS_PERFORMANCE]->(pf:Performance)
RETURN collect(DISTINCT properties(pf)) AS performance_records
"""

CYPHER_FIND_COMPANIES_BY_PRODUCT = """
MATCH (p:Product)
WHERE toLower(p.name) CONTAINS toLower($product_term) OR toLower(p.product_id) CONTAINS toLower($product_term)
OPTIONAL MATCH (t:Tender)-[:FOR_PRODUCT]->(p)
OPTIONAL MATCH (c:Company)-[:BID_ON|WON]->(t)
OPTIONAL MATCH (c2:Company)-[:EXECUTED]->(:Contract)-[:FOR_PRODUCT]->(p)
WITH collect(DISTINCT c) + collect(DISTINCT c2) AS all_companies, p
UNWIND all_companies AS comp
WITH DISTINCT comp, p
WHERE comp IS NOT NULL
RETURN p.name AS product_name,
       p.product_id AS product_id,
       comp.company_id AS company_id,
       comp.legal_name AS legal_name,
       comp.major_activity AS major_activity
"""


# ---------------------------------------------------------------------------
# Query Execution Functions
# ---------------------------------------------------------------------------

def get_bidder_profile(conn: Neo4jConnection, company_id: str) -> Optional[dict[str, Any]]:
    """Query 1: Return full verified profile of a bidder."""
    params = {"company_id": company_id.strip()}
    records = conn.execute_query(CYPHER_GET_BIDDER_PROFILE, parameters=params)
    if records and records[0].get("profile"):
        profile = records[0]["profile"]
        if profile.get("company_id") is not None:
            return profile
    return None


def get_tender_requirements(conn: Neo4jConnection, reference_number: str) -> dict[str, Any]:
    """Query 2: Return all structured requirements for a tender."""
    params = {"reference_number": reference_number.strip()}
    records = conn.execute_query(CYPHER_GET_TENDER_REQUIREMENTS, parameters=params)
    if records:
        return records[0]
    return {"reference_number": reference_number, "requirements": []}


def get_bidders_for_tender(conn: Neo4jConnection, reference_number: str) -> list[dict[str, Any]]:
    """Query 3: Return all bidders associated with a tender."""
    params = {"reference_number": reference_number.strip()}
    records = conn.execute_query(CYPHER_GET_BIDDERS_FOR_TENDER, parameters=params)
    if records:
        return records[0].get("bidders", [])
    return []


def get_tenders_for_bidder(conn: Neo4jConnection, company_id: str) -> list[dict[str, Any]]:
    """Query 4: Return all tenders associated with a bidder."""
    params = {"company_id": company_id.strip()}
    records = conn.execute_query(CYPHER_GET_TENDERS_FOR_BIDDER, parameters=params)
    if records:
        return records[0].get("tenders", [])
    return []


def get_bidder_financial_history(conn: Neo4jConnection, company_id: str) -> list[dict[str, Any]]:
    """Query 5: Return 3-year audited financial records for a bidder."""
    params = {"company_id": company_id.strip()}
    return conn.execute_query(CYPHER_GET_BIDDER_FINANCIAL_HISTORY, parameters=params)


def get_bidder_government_registrations(conn: Neo4jConnection, company_id: str) -> Optional[dict[str, Any]]:
    """Query 6: Return verified statutory registrations (PAN, GST, Udyam, Debarment)."""
    params = {"company_id": company_id.strip()}
    records = conn.execute_query(CYPHER_GET_BIDDER_GOV_REGISTRATIONS, parameters=params)
    if records:
        return records[0].get("registrations")
    return None


def get_bidder_oem_relationships(conn: Neo4jConnection, company_id: str) -> list[dict[str, Any]]:
    """Query 7: Return OEM authorizations and organizations connected to a bidder."""
    params = {"company_id": company_id.strip()}
    records = conn.execute_query(CYPHER_GET_BIDDER_OEM_RELATIONSHIPS, parameters=params)
    if records:
        return records[0].get("oem_relationships", [])
    return []


def get_bidder_historical_contracts(conn: Neo4jConnection, company_id: str) -> list[dict[str, Any]]:
    """Query 8: Return historical contracts executed by a bidder."""
    params = {"company_id": company_id.strip()}
    records = conn.execute_query(CYPHER_GET_BIDDER_HISTORICAL_CONTRACTS, parameters=params)
    if records:
        return [c for c in records[0].get("contracts", []) if c]
    return []


def get_bidder_performance_history(conn: Neo4jConnection, company_id: str) -> list[dict[str, Any]]:
    """Query 9: Return performance records for a bidder's past contracts."""
    params = {"company_id": company_id.strip()}
    records = conn.execute_query(CYPHER_GET_BIDDER_PERFORMANCE_HISTORY, parameters=params)
    if records:
        return [p for p in records[0].get("performance_records", []) if p]
    return []


def find_companies_by_product(conn: Neo4jConnection, product_term: str) -> list[dict[str, Any]]:
    """Query 10: Find companies connected to a product category."""
    params = {"product_term": product_term.strip()}
    return conn.execute_query(CYPHER_FIND_COMPANIES_BY_PRODUCT, parameters=params)

