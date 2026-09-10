"""Validation engine for individual requirement targets and training examples.

Enforces strict structural, semantic, and boundary constraints.
Fails loudly on any schema deviation or corrupted targets.
"""

from __future__ import annotations

import re
from typing import Any

VALID_CATEGORIES = {
    "financial",
    "tax_statutory",
    "msme",
    "experience",
    "technical",
    "certification",
    "oem",
    "local_content",
    "legal",
    "commercial",
    "delivery",
    "ambiguous",
}

VALID_OPERATORS = {
    "==",
    "!=",
    ">",
    ">=",
    "<",
    "<=",
    "contains",
    "includes_all",
    "exists",
    None,
}

VALID_UNITS = {
    "INR",
    "GB",
    "TB",
    "MB",
    "Gbps",
    "cores",
    "Celsius",
    "years",
    "months",
    "days",
    "projects",
    "%",
    "units",
    None,
}


class ValidationError(Exception):
    """Raised when an example violates validation rules."""
    pass


def validate_canonical_target(target: dict[str, Any]) -> None:
    """Validate a canonical requirement target dictionary."""
    req_id = target.get("requirement_id")
    if not req_id or not re.match(r"^REQ_[0-9]{6}$", req_id):
        raise ValidationError(f"Invalid requirement_id format: '{req_id}'. Expected 'REQ_XXXXXX'.")

    cat = target.get("category")
    if cat not in VALID_CATEGORIES:
        raise ValidationError(f"Invalid category: '{cat}'. Allowed: {VALID_CATEGORIES}")

    op = target.get("operator")
    if op not in VALID_OPERATORS:
        raise ValidationError(f"Invalid operator: '{op}'. Allowed: {VALID_OPERATORS}")

    is_ambiguous = target.get("is_ambiguous")
    if is_ambiguous is None or not isinstance(is_ambiguous, bool):
        raise ValidationError(f"is_ambiguous must be a boolean, got: {type(is_ambiguous)}")

    if is_ambiguous:
        if op is not None:
            raise ValidationError(f"Ambiguous target must have operator=null, got: {op}")
        if target.get("value") is not None:
            raise ValidationError(f"Ambiguous target must have value=null, got: {target.get('value')}")
        if not target.get("ambiguity_reason"):
            raise ValidationError("Ambiguous target must specify an ambiguity_reason.")
        return

    # Non-ambiguous checks
    if op is None:
        raise ValidationError(f"Non-ambiguous target {req_id} cannot have operator=null.")

    val = target.get("value")
    if val is None:
        raise ValidationError(f"Non-ambiguous target {req_id} cannot have value=null.")

    # Numeric checks
    if isinstance(val, (int, float)):
        if val < 0:
            raise ValidationError(f"Impossible negative value: {val} in {req_id}")

    unit = target.get("unit")
    if unit not in VALID_UNITS:
        raise ValidationError(f"Unrecognized unit: '{unit}'. Allowed: {VALID_UNITS}")

    if not isinstance(target.get("mandatory"), bool):
        raise ValidationError(f"mandatory must be boolean, got: {target.get('mandatory')}")


def validate_training_example(example: dict[str, Any]) -> None:
    """Validate a full training record packaging input, target, and metadata."""
    ex_id = example.get("id")
    if not ex_id or not re.match(r"^GPKD_[0-9]{6}$", ex_id):
        raise ValidationError(f"Invalid example id: '{ex_id}'. Expected 'GPKD_XXXXXX'.")

    text = example.get("input")
    if not text or not isinstance(text, str) or len(text.strip()) < 5:
        raise ValidationError(f"Invalid input text in {ex_id}: '{text}'")

    target = example.get("target")
    if not target or not isinstance(target, dict):
        raise ValidationError(f"Missing target dictionary in {ex_id}")
    validate_canonical_target(target)

    meta = example.get("metadata")
    if not meta or not isinstance(meta, dict):
        raise ValidationError(f"Missing metadata in {ex_id}")

    if meta.get("source") != "synthetic":
        raise ValidationError(f"metadata.source must be 'synthetic', got: {meta.get('source')}")

    if not meta.get("family_id"):
        raise ValidationError(f"Missing family_id in metadata for {ex_id}")

    diff = meta.get("difficulty")
    if diff not in ("easy", "medium", "hard"):
        raise ValidationError(f"Invalid difficulty: '{diff}' in {ex_id}")

    noise = meta.get("noise_type")
    if noise not in ("ocr", "character_noise", None):
        raise ValidationError(f"Invalid noise_type: '{noise}' in {ex_id}")

