"""Knowledge Graph Builder facade.

Coordinates schema initialization, dataset ingestion, and graph verification
into a unified builder interface.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Optional

from knowledge_graph.config import KnowledgeGraphConfig, default_config
from knowledge_graph.connection import Neo4jConnection, KnowledgeGraphConnectionError
from knowledge_graph.importer import ImportStats, KnowledgeGraphImporter
from knowledge_graph.schema import init_schema

logger = logging.getLogger("knowledge_graph.builder")


class KnowledgeGraphBuilder:
    """Builder that coordinates schema setup and dataset import for Neo4j."""

    def __init__(
        self,
        config: Optional[KnowledgeGraphConfig] = None,
        conn: Optional[Neo4jConnection] = None,
    ) -> None:
        self.config = config or default_config
        self.conn = conn or Neo4jConnection(self.config)
        self.importer = KnowledgeGraphImporter(self.conn)

    def build_graph(
        self,
        tenders_path: Optional[str | Path] = None,
        gov_records_path: Optional[str | Path] = None,
        dry_run: bool = False,
    ) -> ImportStats:
        """Initialize constraints and import datasets into Neo4j.

        Args:
            tenders_path: Path to tenders.json (defaults to config path).
            gov_records_path: Path to government_records.json (defaults to config path).
            dry_run: If True, validates data without writing to database.

        Returns:
            ImportStats summarizing entities and relationships created.
        """
        t_path = tenders_path or self.config.tenders_path
        g_path = gov_records_path or self.config.gov_records_path

        if not dry_run:
            logger.info("Initializing schema constraints and indexes...")
            init_schema(self.conn)

        logger.info("Importing datasets from %s and %s...", t_path, g_path)
        stats = self.importer.import_all(t_path, g_path, dry_run=dry_run)
        return stats

    def is_database_ready(self) -> bool:
        """Check if Neo4j is available and reachable."""
        return self.conn.ping()

    def close(self) -> None:
        """Close connection."""
        self.conn.close()

    def __enter__(self) -> "KnowledgeGraphBuilder":
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        self.close()

