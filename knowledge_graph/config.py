"""Configuration settings for the Tender Knowledge Graph module.

Loads connection parameters and operational settings from environment variables
or an optional .env file with zero hardcoded credentials.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

# Try loading .env if python-dotenv is available
try:
    from dotenv import load_dotenv

    # Search for .env in project root or current directory
    env_path = Path(__file__).resolve().parent.parent / ".env"
    if env_path.is_file():
        load_dotenv(dotenv_path=env_path)
    else:
        load_dotenv()
except ImportError:
    pass


class KnowledgeGraphConfig:
    """Central configuration class for Neo4j database and Knowledge Graph."""

    def __init__(
        self,
        uri: str | None = None,
        username: str | None = None,
        password: str | None = None,
        database: str | None = None,
        tenders_path: str | None = None,
        gov_records_path: str | None = None,
        batch_size: int | None = None,
    ) -> None:
        self.uri: str = uri or os.getenv("NEO4J_URI", "bolt://localhost:7687")
        self.username: str = username or os.getenv("NEO4J_USERNAME", "neo4j")
        self.password: str = password or os.getenv("NEO4J_PASSWORD", "")
        self.database: str = database or os.getenv("NEO4J_DATABASE", "neo4j")

        # Default paths to data files in workspace
        root = Path(__file__).resolve().parent.parent
        default_tenders = str(root / "data" / "tenders.json")
        default_gov = str(root / "data" / "government_records.json")

        self.tenders_path: str = (
            tenders_path or os.getenv("TENDERS_DATA_PATH", default_tenders)
        )
        self.gov_records_path: str = (
            gov_records_path
            or os.getenv("GOVERNMENT_RECORDS_DATA_PATH", default_gov)
        )
        self.batch_size: int = int(
            batch_size or os.getenv("KG_BATCH_SIZE", "100")
        )
        self.log_level: str = os.getenv("KG_LOG_LEVEL", "INFO")

    @property
    def has_credentials(self) -> bool:
        """Check if minimum connection credentials (username & password) are provided."""
        return bool(self.username and self.password)

    def to_safe_dict(self) -> dict[str, Any]:
        """Return configuration dictionary with masked password for safe logging."""
        return {
            "uri": self.uri,
            "username": self.username,
            "password": "***" if self.password else "(empty)",
            "database": self.database,
            "tenders_path": self.tenders_path,
            "gov_records_path": self.gov_records_path,
            "batch_size": self.batch_size,
        }

    def __repr__(self) -> str:
        safe = self.to_safe_dict()
        return (
            f"KnowledgeGraphConfig(uri='{safe['uri']}', username='{safe['username']}', "
            f"database='{safe['database']}')"
        )


# Global default configuration instance
default_config = KnowledgeGraphConfig()

