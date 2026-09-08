"""Centralized configuration for Member 2 Deterministic Compliance Engine.

Fully on-premise, offline-capable, and independent of external cloud APIs or LLMs.
"""

import os
from pydantic import BaseModel, Field


class ComplianceEngineConfig(BaseModel):
    """Configuration settings for Member 2 Deterministic Compliance Engine."""

    # Air-Gapped & Security Settings
    OFFLINE_MODE: bool = Field(
        default=True,
        description="Enforces 100% offline deterministic execution. Zero external network calls.",
    )

    # Compliance & Normalization Settings
    DEFAULT_CURRENCY: str = Field(
        default="INR",
        description="Standard tender baseline currency code (Indian Rupee)",
    )
    STORAGE_BINARY_CONVENTION: bool = Field(
        default=True,
        description="Binary storage conversion: 1 TB = 1024 GB",
    )

    # Audit & Logging Settings
    PRESERVE_ALL_EVIDENCE: bool = Field(
        default=True,
        description="Preserve original raw text, source filename, and page numbers exactly",
    )
    LOG_LEVEL: str = Field(
        default=os.getenv("LOG_LEVEL", "INFO"),
        description="Logging verbosity level",
    )


# Singleton configuration instance
config = ComplianceEngineConfig()
