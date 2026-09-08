"""Pydantic schemas for bidder evidence retrieved by Member 1's RAG system."""

from typing import Any, List, Union
from pydantic import BaseModel, Field, field_validator


class EvidenceItem(BaseModel):
    """An atomic snippet of evidence retrieved from a bidder's document.

    Preserves the exact raw text, source file name, and page number to maintain
    a 100% auditable government tender compliance trail.
    """

    text: str = Field(
        ...,
        description="Exact raw excerpt retrieved from the bidder's submitted document",
        min_length=1,
    )
    source_file: str = Field(
        ...,
        description="Filename of the source document (e.g., 'Financial_Statement.pdf')",
        min_length=1,
    )
    page: Union[int, str] = Field(
        ...,
        description="Page number or section identifier in the source document",
    )

    @field_validator("text", "source_file", mode="before")
    @classmethod
    def validate_non_empty(cls, v: Any, info) -> str:
        if not isinstance(v, str) or not v.strip():
            raise ValueError(f"Field '{info.field_name}' must be a non-empty string.")
        return v.strip()

    @field_validator("page", mode="before")
    @classmethod
    def validate_page(cls, v: Any) -> Union[int, str]:
        if isinstance(v, int):
            if v < 1:
                raise ValueError("Page number must be >= 1.")
            return v
        if isinstance(v, str):
            v_stripped = v.strip()
            if not v_stripped:
                raise ValueError("Page identifier cannot be empty.")
            # If string is numeric integer, convert to int
            if v_stripped.isdigit():
                val = int(v_stripped)
                if val < 1:
                    raise ValueError("Page number must be >= 1.")
                return val
            return v_stripped
        raise ValueError(f"Invalid page specification: {v}")


class BidderEvidencePayload(BaseModel):
    """Payload format delivered by Member 1's RAG system to Member 2."""

    rule_id: str = Field(
        ...,
        description="Target rule ID being verified (matches buyer requirement rule_id)",
        min_length=1,
    )
    bidder_id: str = Field(
        ...,
        description="Unique identifier for the participating bidder (e.g., 'B001')",
        min_length=1,
    )
    evidence: List[EvidenceItem] = Field(
        default_factory=list,
        description="List of retrieved evidence snippets relevant to the rule",
    )

    @field_validator("rule_id", "bidder_id", mode="before")
    @classmethod
    def validate_ids(cls, v: Any, info) -> str:
        if not isinstance(v, str) or not v.strip():
            raise ValueError(f"Field '{info.field_name}' must be a non-empty string.")
        return v.strip()

