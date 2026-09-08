"""Command Line Interface for Knowledge Graph Management.

Usage:
    python -m knowledge_graph.cli ping
    python -m knowledge_graph.cli init-schema
    python -m knowledge_graph.cli import [--dry-run]
    python -m knowledge_graph.cli profile <company_id>
    python -m knowledge_graph.cli tender <reference_number>
    python -m knowledge_graph.cli features <company_id>
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

# Ensure UTF-8 output on Windows consoles
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

from knowledge_graph.config import KnowledgeGraphConfig, default_config
from knowledge_graph.connection import Neo4jConnection, KnowledgeGraphConnectionError
from knowledge_graph.feature_extractor import RiskFeatureExtractor
from knowledge_graph.importer import KnowledgeGraphImporter
from knowledge_graph.queries import (
    get_bidder_profile,
    get_tender_requirements,
    find_companies_by_product,
)
from knowledge_graph.schema import init_schema, get_all_schema_ddl


def cmd_ping(args: argparse.Namespace) -> int:
    """Test connection to Neo4j."""
    cfg = KnowledgeGraphConfig()
    print(f"Connecting to Neo4j instance at: {cfg.uri}")
    print(f"Target Database: {cfg.database}, Username: {cfg.username}")
    try:
        with Neo4jConnection(cfg) as conn:
            alive = conn.ping()
            if alive:
                print("STATUS: SUCCESS - Neo4j instance is reachable and responsive!")
                return 0
            else:
                print("STATUS: FAILED - Neo4j responded negatively or ping timed out.")
                return 1
    except Exception as e:
        print(f"STATUS: ERROR - Could not connect to Neo4j: {e}")
        return 1


def cmd_init_schema(args: argparse.Namespace) -> int:
    """Apply uniqueness constraints and indexes."""
    cfg = KnowledgeGraphConfig()
    if args.print_only:
        print("--- Schema DDL Statements ---")
        for stmt in get_all_schema_ddl():
            print(f"{stmt};")
        return 0

    print(f"Initializing Knowledge Graph schema on {cfg.uri}...")
    try:
        with Neo4jConnection(cfg) as conn:
            res = init_schema(conn)
            print("Successfully initialized schema:")
            print(f"  Constraints applied: {res['constraints_applied']}")
            print(f"  Indexes applied:     {res['indexes_applied']}")
            return 0
    except Exception as e:
        print(f"Error initializing schema: {e}")
        return 1


def cmd_import(args: argparse.Namespace) -> int:
    """Import datasets into Knowledge Graph."""
    cfg = KnowledgeGraphConfig()
    tenders_file = args.tenders or cfg.tenders_path
    gov_file = args.gov_records or cfg.gov_records_path

    print("=" * 65)
    print("  KNOWLEDGE GRAPH DATA IMPORTER")
    print("=" * 65)
    print(f"Tenders file:     {tenders_file}")
    print(f"Gov records file: {gov_file}")
    print(f"Dry-run mode:     {args.dry_run}")
    print("=" * 65)

    conn = None
    if not args.dry_run:
        try:
            conn = Neo4jConnection(cfg)
            if not conn.ping():
                print(f"ERROR: Neo4j database is not reachable at {cfg.uri}.")
                print("Tip: Run with --dry-run to validate and parse datasets without database.")
                return 1
        except Exception as e:
            print(f"ERROR: Could not establish Neo4j connection: {e}")
            return 1

    try:
        importer = KnowledgeGraphImporter(conn=conn)
        stats = importer.import_all(tenders_file, gov_file, dry_run=args.dry_run)

        print("\n--- Ingestion Summary ---")
        print(f"Companies processed:      {stats.companies_processed}")
        print(f"Tenders processed:        {stats.tenders_processed}")
        print(f"Requirements processed:   {stats.requirements_processed}")
        print(f"Gov records processed:    {stats.gov_records_processed}")
        print(f"Nodes mapped/created:     {stats.nodes_created}")
        print(f"Relationships created:    {stats.relationships_created}")
        print(f"Invalid / skipped:        {stats.invalid_records + stats.records_skipped}")
        if stats.errors:
            print(f"Warnings/Errors ({len(stats.errors)}):")
            for err in stats.errors[:5]:
                print(f"  - {err}")
            if len(stats.errors) > 5:
                print(f"  ... and {len(stats.errors) - 5} more.")
        print("Import completed successfully!")
        return 0
    except Exception as e:
        print(f"ERROR during import: {e}")
        return 1
    finally:
        if conn:
            conn.close()


def cmd_profile(args: argparse.Namespace) -> int:
    """Query bidder profile for a company ID."""
    cfg = KnowledgeGraphConfig()
    try:
        with Neo4jConnection(cfg) as conn:
            profile = get_bidder_profile(conn, args.company_id)
            if not profile:
                print(f"No company found with ID: {args.company_id}")
                return 1
            print(json.dumps(profile, indent=2, ensure_ascii=False, default=str))
            return 0
    except Exception as e:
        print(f"Error querying profile: {e}")
        return 1


def cmd_tender(args: argparse.Namespace) -> int:
    """Query requirements for a tender."""
    cfg = KnowledgeGraphConfig()
    try:
        with Neo4jConnection(cfg) as conn:
            res = get_tender_requirements(conn, args.reference_number)
            print(json.dumps(res, indent=2, ensure_ascii=False, default=str))
            return 0
    except Exception as e:
        print(f"Error querying tender: {e}")
        return 1


def cmd_features(args: argparse.Namespace) -> int:
    """Extract risk features for a company."""
    cfg = KnowledgeGraphConfig()
    try:
        with Neo4jConnection(cfg) as conn:
            extractor = RiskFeatureExtractor(conn)
            feats = extractor.extract_features(args.company_id)
            if not feats:
                print(f"No company found with ID: {args.company_id}")
                return 1
            print(json.dumps(feats.model_dump(), indent=2, ensure_ascii=False))
            return 0
    except Exception as e:
        print(f"Error extracting features: {e}")
        return 1


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Government Procurement Knowledge Graph Manager (Neo4j / Local)"
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    # ping
    subparsers.add_parser("ping", help="Test Neo4j connection")

    # init-schema
    p_init = subparsers.add_parser("init-schema", help="Initialize constraints and indexes")
    p_init.add_argument("--print-only", action="store_true", help="Print DDL statements without executing")

    # import
    p_imp = subparsers.add_parser("import", help="Import tenders.json and government_records.json")
    p_imp.add_argument("--dry-run", action="store_true", help="Parse and validate without database writes")
    p_imp.add_argument("--tenders", type=str, default=None, help="Path to tenders.json")
    p_imp.add_argument("--gov-records", type=str, default=None, help="Path to government_records.json")

    # profile
    p_prof = subparsers.add_parser("profile", help="Query bidder profile by company_id")
    p_prof.add_argument("company_id", type=str, help="e.g. CMP-00001")

    # tender
    p_tend = subparsers.add_parser("tender", help="Query tender requirements by reference_number")
    p_tend.add_argument("reference_number", type=str, help="e.g. GEM/2026/B/1000001")

    # features
    p_feat = subparsers.add_parser("features", help="Extract risk features for a company")
    p_feat.add_argument("company_id", type=str, help="e.g. CMP-00001")

    args = parser.parse_args()

    dispatch = {
        "ping": cmd_ping,
        "init-schema": cmd_init_schema,
        "import": cmd_import,
        "profile": cmd_profile,
        "tender": cmd_tender,
        "features": cmd_features,
    }

    handler = dispatch.get(args.command)
    if handler:
        return handler(args)
    parser.print_help()
    return 1


if __name__ == "__main__":
    sys.exit(main())

