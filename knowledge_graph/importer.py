"""Idempotent ingestion pipeline for Government Tender and Company Knowledge Graph.

Parses tenders.json and government_records.json, extracts strongly-typed graph models,
and executes parameterized MERGE operations to ensure zero duplicate entities upon repeat executions.
"""

from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional, Sequence

from knowledge_graph.connection import Neo4jConnection, KnowledgeGraphConnectionError
from knowledge_graph.models import (
    CompanyNode,
    DebarmentRecordNode,
    FinancialRecordNode,
    GSTRecordNode,
    OEMRecordNode,
    OrganizationNode,
    PANRecordNode,
    ProductNode,
    ProvenanceMetadata,
    RequirementNode,
    TenderNode,
    UdyamRecordNode,
)

logger = logging.getLogger("knowledge_graph.importer")


@dataclass
class ImportStats:
    """Tracks statistics of graph import operations."""
    companies_processed: int = 0
    tenders_processed: int = 0
    requirements_processed: int = 0
    gov_records_processed: int = 0
    nodes_created: int = 0
    nodes_updated: int = 0
    relationships_created: int = 0
    records_skipped: int = 0
    invalid_records: int = 0
    errors: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "companies_processed": self.companies_processed,
            "tenders_processed": self.tenders_processed,
            "requirements_processed": self.requirements_processed,
            "gov_records_processed": self.gov_records_processed,
            "nodes_created": self.nodes_created,
            "nodes_updated": self.nodes_updated,
            "relationships_created": self.relationships_created,
            "records_skipped": self.records_skipped,
            "invalid_records": self.invalid_records,
            "error_count": len(self.errors),
        }


def extract_product_from_title(title: str) -> tuple[str, str]:
    """Extract a standardized product name and slug from a tender title."""
    cleaned = title.strip()
    # Strip common prefixes like "Procurement of", "Supply of", etc.
    prefix_pattern = r"^(?:Supply,?\s*Delivery\s*and\s*Commissioning\s*of|Procurement\s*of|Supply\s*and\s*Installation\s*of|Supply\s*of|Annual\s*Maintenance\s*of)\s+"
    product_name = re.sub(prefix_pattern, "", cleaned, flags=re.IGNORECASE).strip()
    if not product_name:
        product_name = cleaned
    slug = re.sub(r"[^a-zA-Z0-9]+", "_", product_name).strip("_").lower()
    return slug, product_name


class KnowledgeGraphImporter:
    """Manages the idempotent ingestion of dataset files into Neo4j."""

    def __init__(self, conn: Optional[Neo4jConnection] = None) -> None:
        self.conn = conn

    def load_json_file(self, file_path: str | Path) -> Any:
        """Load and parse a JSON dataset safely."""
        p = Path(file_path)
        if not p.is_file():
            raise FileNotFoundError(f"Dataset file not found: {p.resolve()}")
        with open(p, "r", encoding="utf-8") as f:
            return json.load(f)

    def parse_tenders_data(
        self,
        tenders_data: list[dict[str, Any]],
        source_filename: str = "tenders.json",
    ) -> tuple[list[TenderNode], list[RequirementNode], list[ProductNode], list[str]]:
        """Parse raw tenders JSON into validated Tender, Requirement, and Product models."""
        tenders: list[TenderNode] = []
        requirements: list[RequirementNode] = []
        products: list[ProductNode] = []
        errors: list[str] = []

        now_iso = datetime.now(timezone.utc).isoformat()

        for idx, item in enumerate(tenders_data):
            ref_num = item.get("reference_number")
            if not ref_num:
                errors.append(f"Tender item at index {idx} is missing 'reference_number'. Skipping.")
                continue

            prov = ProvenanceMetadata(
                source_file=source_filename,
                source_record_id=str(item.get("id") or ref_num),
                source_type="tender_dataset",
                extraction_method="direct_ingestion",
                created_at=now_iso,
            )

            tender = TenderNode(
                reference_number=ref_num,
                tender_id=item.get("id"),
                title=item.get("title", "Untitled Tender"),
                description=item.get("description"),
                status=item.get("status", "PUBLISHED"),
                estimated_value=float(item["estimated_value"]) if item.get("estimated_value") is not None else None,
                minimum_turnover=float(item["minimum_turnover"]) if item.get("minimum_turnover") is not None else None,
                minimum_local_content=float(item["minimum_local_content"]) if item.get("minimum_local_content") is not None else None,
                provenance=prov,
            )
            tenders.append(tender)

            # Extract Product
            prod_id, prod_name = extract_product_from_title(tender.title)
            products.append(
                ProductNode(
                    product_id=prod_id,
                    name=prod_name,
                    category="Procurement Product",
                    provenance=prov,
                )
            )

            # Parse Requirements
            for r_idx, req in enumerate(item.get("requirements", [])):
                r_key = req.get("requirement_key")
                if not r_key:
                    errors.append(f"Tender {ref_num} requirement at index {r_idx} missing requirement_key.")
                    continue

                defn = req.get("definition", {})
                req_id = f"{ref_num}_{r_key}"

                requirements.append(
                    RequirementNode(
                        requirement_id=req_id,
                        tender_reference=ref_num,
                        requirement_key=r_key,
                        field=defn.get("field"),
                        type=defn.get("type"),
                        operator=defn.get("operator"),
                        value=defn.get("value"),
                        unit=defn.get("unit"),
                        currency=defn.get("currency", "INR"),
                        mandatory=bool(req.get("mandatory", True)),
                        active_required=defn.get("active_required"),
                        description=defn.get("description"),
                        provenance=prov,
                    )
                )

        return tenders, requirements, products, errors

    def parse_government_records_data(
        self,
        records_data: list[dict[str, Any]],
        source_filename: str = "government_records.json",
    ) -> tuple[
        list[CompanyNode],
        list[Any],  # Government Records
        list[OrganizationNode],
        list[str],  # Errors
    ]:
        """Parse raw government records JSON into validated Company, GovRecord, and Organization models."""
        companies: list[CompanyNode] = []
        gov_records: list[Any] = []
        organizations: list[OrganizationNode] = []
        errors: list[str] = []

        now_iso = datetime.now(timezone.utc).isoformat()

        for idx, item in enumerate(records_data):
            company_id = item.get("company_id")
            if not company_id:
                errors.append(f"Record at index {idx} missing 'company_id'. Skipping.")
                continue

            prov = ProvenanceMetadata(
                source_file=source_filename,
                source_record_id=company_id,
                source_type="government_registry_dataset",
                extraction_method="direct_ingestion",
                created_at=now_iso,
            )

            # Extract details from sub-records to build Company entity
            pan_rec = item.get("pan_record") or {}
            gst_rec = item.get("gst_record") or {}
            udyam_rec = item.get("udyam_record") or {}

            legal_name = pan_rec.get("legal_name") or gst_rec.get("legal_name")
            trade_name = gst_rec.get("trade_name")
            status = gst_rec.get("status") or pan_rec.get("status") or "ACTIVE"
            category = pan_rec.get("category")
            state_jur = gst_rec.get("state_jurisdiction")
            ent_type = udyam_rec.get("enterprise_type")
            maj_act = udyam_rec.get("major_activity")

            company = CompanyNode(
                company_id=company_id,
                legal_name=legal_name,
                trade_name=trade_name,
                status=status,
                category=category,
                state_jurisdiction=state_jur,
                enterprise_type=ent_type,
                major_activity=maj_act,
                provenance=prov,
            )
            companies.append(company)

            # 1. PAN Record
            if pan_rec and pan_rec.get("pan"):
                gov_records.append(
                    PANRecordNode(
                        record_id=pan_rec["pan"],
                        record_type="PAN",
                        company_id=company_id,
                        pan=pan_rec["pan"],
                        legal_name=pan_rec.get("legal_name"),
                        category=pan_rec.get("category"),
                        date_of_issue=pan_rec.get("date_of_issue"),
                        status=pan_rec.get("status"),
                        source="Income Tax Department",
                        provenance=prov,
                    )
                )

            # 2. GST Record
            if gst_rec and gst_rec.get("gstin"):
                gov_records.append(
                    GSTRecordNode(
                        record_id=gst_rec["gstin"],
                        record_type="GST",
                        company_id=company_id,
                        gstin=gst_rec["gstin"],
                        legal_name=gst_rec.get("legal_name"),
                        trade_name=gst_rec.get("trade_name"),
                        registration_date=gst_rec.get("registration_date"),
                        state_jurisdiction=gst_rec.get("state_jurisdiction"),
                        status=gst_rec.get("status"),
                        source="GSTN Portal",
                        provenance=prov,
                    )
                )

            # 3. Udyam Record
            if udyam_rec and udyam_rec.get("udyam_number"):
                gov_records.append(
                    UdyamRecordNode(
                        record_id=udyam_rec["udyam_number"],
                        record_type="UDYAM",
                        company_id=company_id,
                        udyam_number=udyam_rec["udyam_number"],
                        enterprise_name=udyam_rec.get("enterprise_name"),
                        enterprise_type=udyam_rec.get("enterprise_type"),
                        major_activity=udyam_rec.get("major_activity"),
                        date_of_commencement=udyam_rec.get("date_of_commencement"),
                        status="VALID",
                        source="Ministry of MSME",
                        provenance=prov,
                    )
                )

            # 4. Financial Records
            for f_rec in item.get("financial_records", []):
                fy = f_rec.get("financial_year")
                if fy:
                    rec_id = f"{company_id}_{fy}"
                    gov_records.append(
                        FinancialRecordNode(
                            record_id=rec_id,
                            record_type="FINANCIAL",
                            company_id=company_id,
                            pan=f_rec.get("pan"),
                            financial_year=fy,
                            turnover=float(f_rec.get("turnover", 0.0)),
                            net_profit=float(f_rec["net_profit"]) if f_rec.get("net_profit") is not None else None,
                            filing_date=f_rec.get("filing_date"),
                            status="FILED",
                            source="Audited Accounts / MCA",
                            provenance=prov,
                        )
                    )

            # 5. Debarment Record
            deb_rec = item.get("debarment_record")
            if deb_rec:
                gov_records.append(
                    DebarmentRecordNode(
                        record_id=f"DEBARMENT_{company_id}",
                        record_type="DEBARMENT",
                        company_id=company_id,
                        pan=deb_rec.get("pan"),
                        legal_name=deb_rec.get("legal_name"),
                        is_debarred=bool(deb_rec.get("is_debarred", False)),
                        debarment_agency=deb_rec.get("debarment_agency"),
                        start_date=deb_rec.get("start_date"),
                        end_date=deb_rec.get("end_date"),
                        status="DEBARRED" if deb_rec.get("is_debarred") else "CLEAN",
                        source="Central Public Procurement Debarment Registry",
                        provenance=prov,
                    )
                )

            # 6. OEM Authorization Record
            oem_rec = item.get("oem_record")
            if oem_rec and oem_rec.get("oem_name"):
                oem_name = oem_rec["oem_name"]
                auth_code = oem_rec.get("authorization_code", f"AUTH_{company_id}")
                gov_records.append(
                    OEMRecordNode(
                        record_id=auth_code,
                        record_type="OEM_AUTHORIZATION",
                        company_id=company_id,
                        oem_name=oem_name,
                        authorized_partner_pan=oem_rec.get("authorized_partner_pan"),
                        authorized_partner_name=oem_rec.get("authorized_partner_name"),
                        authorization_code=auth_code,
                        validity_end_date=oem_rec.get("validity_end_date"),
                        status="VALID",
                        source="OEM Partner Portal",
                        provenance=prov,
                    )
                )

                # OEM Organization Node
                org_slug = re.sub(r"[^a-zA-Z0-9]+", "_", oem_name).strip("_").lower()
                organizations.append(
                    OrganizationNode(
                        org_id=org_slug,
                        name=oem_name,
                        org_type="OEM",
                        provenance=prov,
                    )
                )

        return companies, gov_records, organizations, errors

    def import_all(
        self,
        tenders_file: str | Path,
        gov_records_file: str | Path,
        dry_run: bool = False,
    ) -> ImportStats:
        """Execute the full import pipeline from JSON files into Neo4j."""
        stats = ImportStats()

        logger.info("Loading tenders from: %s", tenders_file)
        tenders_raw = self.load_json_file(tenders_file)
        tenders, requirements, products, t_errors = self.parse_tenders_data(
            tenders_raw, source_filename=Path(tenders_file).name
        )
        stats.tenders_processed = len(tenders)
        stats.requirements_processed = len(requirements)
        stats.errors.extend(t_errors)

        logger.info("Loading government records from: %s", gov_records_file)
        gov_raw = self.load_json_file(gov_records_file)
        companies, gov_records, organizations, g_errors = self.parse_government_records_data(
            gov_raw, source_filename=Path(gov_records_file).name
        )
        stats.companies_processed = len(companies)
        stats.gov_records_processed = len(gov_records)
        stats.errors.extend(g_errors)

        if dry_run:
            logger.info("DRY-RUN mode active: validation complete. Skipping database writes.")
            stats.nodes_created = (
                len(tenders) + len(requirements) + len(products)
                + len(companies) + len(gov_records) + len(organizations)
            )
            stats.relationships_created = (
                len(requirements) + len(tenders)  # Tender->Req, Tender->Prod
                + len(gov_records) + len(organizations)  # Company->Records, Company->Org
            )
            return stats

        if not self.conn:
            raise KnowledgeGraphConnectionError("No active Neo4jConnection configured for import.")

        if not self.conn.ping():
            raise KnowledgeGraphConnectionError(
                f"Cannot import: Neo4j database is unreachable at {self.conn.config.uri}"
            )

        with self.conn.session() as session:
            # 1. Import Tenders and Products
            for t in tenders:
                session.run(
                    """
                    MERGE (t:Tender {reference_number: $reference_number})
                    ON CREATE SET
                        t.tender_id = $tender_id,
                        t.title = $title,
                        t.description = $description,
                        t.status = $status,
                        t.estimated_value = $estimated_value,
                        t.minimum_turnover = $minimum_turnover,
                        t.minimum_local_content = $minimum_local_content,
                        t.source_file = $source_file,
                        t.created_at = $created_at
                    ON MATCH SET
                        t.title = $title,
                        t.status = $status,
                        t.estimated_value = $estimated_value,
                        t.minimum_turnover = $minimum_turnover,
                        t.minimum_local_content = $minimum_local_content,
                        t.updated_at = $created_at
                    """,
                    {
                        "reference_number": t.reference_number,
                        "tender_id": t.tender_id,
                        "title": t.title,
                        "description": t.description,
                        "status": t.status,
                        "estimated_value": t.estimated_value,
                        "minimum_turnover": t.minimum_turnover,
                        "minimum_local_content": t.minimum_local_content,
                        "source_file": t.provenance.source_file,
                        "created_at": t.provenance.created_at,
                    },
                )
                stats.nodes_created += 1

            for p in products:
                session.run(
                    """
                    MERGE (p:Product {product_id: $product_id})
                    ON CREATE SET
                        p.name = $name,
                        p.category = $category,
                        p.source_file = $source_file,
                        p.created_at = $created_at
                    """,
                    {
                        "product_id": p.product_id,
                        "name": p.name,
                        "category": p.category,
                        "source_file": p.provenance.source_file,
                        "created_at": p.provenance.created_at,
                    },
                )
                stats.nodes_created += 1

            # Connect Tender -> Product
            for t, p in zip(tenders, products):
                session.run(
                    """
                    MATCH (t:Tender {reference_number: $reference_number})
                    MATCH (p:Product {product_id: $product_id})
                    MERGE (t)-[rel:FOR_PRODUCT]->(p)
                    ON CREATE SET rel.created_at = $created_at
                    """,
                    {
                        "reference_number": t.reference_number,
                        "product_id": p.product_id,
                        "created_at": t.provenance.created_at,
                    },
                )
                stats.relationships_created += 1

            # 2. Import Requirements and Connect to Tenders
            for r in requirements:
                session.run(
                    """
                    MERGE (req:Requirement {requirement_id: $requirement_id})
                    ON CREATE SET
                        req.tender_reference = $tender_reference,
                        req.requirement_key = $requirement_key,
                        req.field = $field,
                        req.type = $type,
                        req.operator = $operator,
                        req.value = $value,
                        req.unit = $unit,
                        req.currency = $currency,
                        req.mandatory = $mandatory,
                        req.active_required = $active_required,
                        req.description = $description,
                        req.source_file = $source_file,
                        req.created_at = $created_at
                    ON MATCH SET
                        req.mandatory = $mandatory,
                        req.updated_at = $created_at
                    """,
                    {
                        "requirement_id": r.requirement_id,
                        "tender_reference": r.tender_reference,
                        "requirement_key": r.requirement_key,
                        "field": r.field,
                        "type": r.type,
                        "operator": r.operator,
                        "value": r.value,
                        "unit": r.unit,
                        "currency": r.currency,
                        "mandatory": r.mandatory,
                        "active_required": r.active_required,
                        "description": r.description,
                        "source_file": r.provenance.source_file,
                        "created_at": r.provenance.created_at,
                    },
                )
                stats.nodes_created += 1

                # Link Tender -> Requirement
                session.run(
                    """
                    MATCH (t:Tender {reference_number: $tender_reference})
                    MATCH (req:Requirement {requirement_id: $requirement_id})
                    MERGE (t)-[rel:HAS_REQUIREMENT]->(req)
                    ON CREATE SET rel.created_at = $created_at
                    """,
                    {
                        "tender_reference": r.tender_reference,
                        "requirement_id": r.requirement_id,
                        "created_at": r.provenance.created_at,
                    },
                )
                stats.relationships_created += 1

            # 3. Import Companies
            for c in companies:
                session.run(
                    """
                    MERGE (cmp:Company {company_id: $company_id})
                    ON CREATE SET
                        cmp.legal_name = $legal_name,
                        cmp.trade_name = $trade_name,
                        cmp.status = $status,
                        cmp.category = $category,
                        cmp.state_jurisdiction = $state_jurisdiction,
                        cmp.enterprise_type = $enterprise_type,
                        cmp.major_activity = $major_activity,
                        cmp.source_file = $source_file,
                        cmp.created_at = $created_at
                    ON MATCH SET
                        cmp.legal_name = coalesce($legal_name, cmp.legal_name),
                        cmp.trade_name = coalesce($trade_name, cmp.trade_name),
                        cmp.status = coalesce($status, cmp.status),
                        cmp.category = coalesce($category, cmp.category),
                        cmp.state_jurisdiction = coalesce($state_jurisdiction, cmp.state_jurisdiction),
                        cmp.enterprise_type = coalesce($enterprise_type, cmp.enterprise_type),
                        cmp.major_activity = coalesce($major_activity, cmp.major_activity),
                        cmp.updated_at = $created_at
                    """,
                    {
                        "company_id": c.company_id,
                        "legal_name": c.legal_name,
                        "trade_name": c.trade_name,
                        "status": c.status,
                        "category": c.category,
                        "state_jurisdiction": c.state_jurisdiction,
                        "enterprise_type": c.enterprise_type,
                        "major_activity": c.major_activity,
                        "source_file": c.provenance.source_file,
                        "created_at": c.provenance.created_at,
                    },
                )
                stats.nodes_created += 1

            # 4. Import Organizations
            for org in organizations:
                session.run(
                    """
                    MERGE (o:Organization {name: $name})
                    ON CREATE SET
                        o.org_id = $org_id,
                        o.org_type = $org_type,
                        o.source_file = $source_file,
                        o.created_at = $created_at
                    """,
                    {
                        "org_id": org.org_id,
                        "name": org.name,
                        "org_type": org.org_type,
                        "source_file": org.provenance.source_file,
                        "created_at": org.provenance.created_at,
                    },
                )
                stats.nodes_created += 1

            # 5. Import Government Records & Relationships
            for rec in gov_records:
                r_type = rec.record_type
                r_id = rec.record_id
                cid = rec.company_id
                now_str = rec.provenance.created_at
                src_file = rec.provenance.source_file

                if isinstance(rec, PANRecordNode):
                    session.run(
                        """
                        MERGE (g:GovernmentRecord:PANRecord {record_id: $record_id})
                        ON CREATE SET
                            g.record_type = 'PAN',
                            g.company_id = $company_id,
                            g.pan = $pan,
                            g.legal_name = $legal_name,
                            g.status = $status,
                            g.category = $category,
                            g.date_of_issue = $date_of_issue,
                            g.source = $source,
                            g.source_file = $source_file,
                            g.created_at = $created_at
                        WITH g
                        MATCH (c:Company {company_id: $company_id})
                        MERGE (c)-[rel:HAS_PAN]->(g)
                        ON CREATE SET rel.created_at = $created_at
                        """,
                        {
                            "record_id": r_id,
                            "company_id": cid,
                            "pan": rec.pan,
                            "legal_name": rec.legal_name,
                            "status": rec.status,
                            "category": rec.category,
                            "date_of_issue": rec.date_of_issue,
                            "source": rec.source,
                            "source_file": src_file,
                            "created_at": now_str,
                        },
                    )
                    stats.nodes_created += 1
                    stats.relationships_created += 1

                elif isinstance(rec, GSTRecordNode):
                    session.run(
                        """
                        MERGE (g:GovernmentRecord:GSTRecord {record_id: $record_id})
                        ON CREATE SET
                            g.record_type = 'GST',
                            g.company_id = $company_id,
                            g.gstin = $gstin,
                            g.legal_name = $legal_name,
                            g.trade_name = $trade_name,
                            g.status = $status,
                            g.registration_date = $registration_date,
                            g.state_jurisdiction = $state_jurisdiction,
                            g.source = $source,
                            g.source_file = $source_file,
                            g.created_at = $created_at
                        WITH g
                        MATCH (c:Company {company_id: $company_id})
                        MERGE (c)-[rel:HAS_GST]->(g)
                        ON CREATE SET rel.created_at = $created_at
                        """,
                        {
                            "record_id": r_id,
                            "company_id": cid,
                            "gstin": rec.gstin,
                            "legal_name": rec.legal_name,
                            "trade_name": rec.trade_name,
                            "status": rec.status,
                            "registration_date": rec.registration_date,
                            "state_jurisdiction": rec.state_jurisdiction,
                            "source": rec.source,
                            "source_file": src_file,
                            "created_at": now_str,
                        },
                    )
                    stats.nodes_created += 1
                    stats.relationships_created += 1

                elif isinstance(rec, UdyamRecordNode):
                    session.run(
                        """
                        MERGE (g:GovernmentRecord:UdyamRecord {record_id: $record_id})
                        ON CREATE SET
                            g.record_type = 'UDYAM',
                            g.company_id = $company_id,
                            g.udyam_number = $udyam_number,
                            g.enterprise_name = $enterprise_name,
                            g.enterprise_type = $enterprise_type,
                            g.major_activity = $major_activity,
                            g.date_of_commencement = $date_of_commencement,
                            g.source = $source,
                            g.source_file = $source_file,
                            g.created_at = $created_at
                        WITH g
                        MATCH (c:Company {company_id: $company_id})
                        MERGE (c)-[rel:HAS_UDYAM]->(g)
                        ON CREATE SET rel.created_at = $created_at
                        """,
                        {
                            "record_id": r_id,
                            "company_id": cid,
                            "udyam_number": rec.udyam_number,
                            "enterprise_name": rec.enterprise_name,
                            "enterprise_type": rec.enterprise_type,
                            "major_activity": rec.major_activity,
                            "date_of_commencement": rec.date_of_commencement,
                            "source": rec.source,
                            "source_file": src_file,
                            "created_at": now_str,
                        },
                    )
                    stats.nodes_created += 1
                    stats.relationships_created += 1

                elif isinstance(rec, FinancialRecordNode):
                    session.run(
                        """
                        MERGE (g:GovernmentRecord:FinancialRecord {record_id: $record_id})
                        ON CREATE SET
                            g.record_type = 'FINANCIAL',
                            g.company_id = $company_id,
                            g.pan = $pan,
                            g.financial_year = $financial_year,
                            g.turnover = $turnover,
                            g.net_profit = $net_profit,
                            g.filing_date = $filing_date,
                            g.source = $source,
                            g.source_file = $source_file,
                            g.created_at = $created_at
                        WITH g
                        MATCH (c:Company {company_id: $company_id})
                        MERGE (c)-[rel:HAS_FINANCIAL_RECORD]->(g)
                        ON CREATE SET rel.created_at = $created_at
                        """,
                        {
                            "record_id": r_id,
                            "company_id": cid,
                            "pan": rec.pan,
                            "financial_year": rec.financial_year,
                            "turnover": rec.turnover,
                            "net_profit": rec.net_profit,
                            "filing_date": rec.filing_date,
                            "source": rec.source,
                            "source_file": src_file,
                            "created_at": now_str,
                        },
                    )
                    stats.nodes_created += 1
                    stats.relationships_created += 1

                elif isinstance(rec, DebarmentRecordNode):
                    session.run(
                        """
                        MERGE (g:GovernmentRecord:DebarmentRecord {record_id: $record_id})
                        ON CREATE SET
                            g.record_type = 'DEBARMENT',
                            g.company_id = $company_id,
                            g.pan = $pan,
                            g.legal_name = $legal_name,
                            g.is_debarred = $is_debarred,
                            g.debarment_agency = $debarment_agency,
                            g.start_date = $start_date,
                            g.end_date = $end_date,
                            g.source = $source,
                            g.source_file = $source_file,
                            g.created_at = $created_at
                        WITH g
                        MATCH (c:Company {company_id: $company_id})
                        MERGE (c)-[rel:HAS_DEBARMENT_RECORD]->(g)
                        ON CREATE SET rel.created_at = $created_at
                        """,
                        {
                            "record_id": r_id,
                            "company_id": cid,
                            "pan": rec.pan,
                            "legal_name": rec.legal_name,
                            "is_debarred": rec.is_debarred,
                            "debarment_agency": rec.debarment_agency,
                            "start_date": rec.start_date,
                            "end_date": rec.end_date,
                            "source": rec.source,
                            "source_file": src_file,
                            "created_at": now_str,
                        },
                    )
                    stats.nodes_created += 1
                    stats.relationships_created += 1

                elif isinstance(rec, OEMRecordNode):
                    session.run(
                        """
                        MERGE (g:GovernmentRecord:OEMRecord {record_id: $record_id})
                        ON CREATE SET
                            g.record_type = 'OEM_AUTHORIZATION',
                            g.company_id = $company_id,
                            g.oem_name = $oem_name,
                            g.authorized_partner_pan = $authorized_partner_pan,
                            g.authorized_partner_name = $authorized_partner_name,
                            g.authorization_code = $authorization_code,
                            g.validity_end_date = $validity_end_date,
                            g.source = $source,
                            g.source_file = $source_file,
                            g.created_at = $created_at
                        WITH g
                        MATCH (c:Company {company_id: $company_id})
                        MERGE (c)-[rel:HAS_OEM_AUTHORIZATION]->(g)
                        ON CREATE SET rel.created_at = $created_at
                        WITH c
                        MATCH (o:Organization {name: $oem_name})
                        MERGE (c)-[auth:AUTHORIZED_BY]->(o)
                        ON CREATE SET
                            auth.authorization_code = $authorization_code,
                            auth.validity_end_date = $validity_end_date,
                            auth.created_at = $created_at
                        """,
                        {
                            "record_id": r_id,
                            "company_id": cid,
                            "oem_name": rec.oem_name,
                            "authorized_partner_pan": rec.authorized_partner_pan,
                            "authorized_partner_name": rec.authorized_partner_name,
                            "authorization_code": rec.authorization_code,
                            "validity_end_date": rec.validity_end_date,
                            "source": rec.source,
                            "source_file": src_file,
                            "created_at": now_str,
                        },
                    )
                    stats.nodes_created += 1
                    stats.relationships_created += 2

        return stats

