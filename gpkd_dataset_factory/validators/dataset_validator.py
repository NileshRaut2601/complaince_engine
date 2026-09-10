"""Full Dataset and Anti-Leakage Validator.

Validates large-scale dataset splits for structural correctness, category distributions,
and strictly verifies ZERO LEAKAGE between train, validation, and test partitions.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from gpkd_dataset_factory.validators.duplicate_detector import check_duplicates
from gpkd_dataset_factory.validators.requirement_validator import (
    ValidationError,
    validate_training_example,
)


class LeakageReport:
    """Summary of train/test leakage checks."""

    def __init__(self) -> None:
        self.has_leakage: bool = False
        self.leaked_families_train_test: list[str] = []
        self.leaked_families_train_val: list[str] = []
        self.leaked_inputs_train_test: list[str] = []

    def to_dict(self) -> dict[str, Any]:
        return {
            "has_leakage": self.has_leakage,
            "leaked_families_train_test_count": len(self.leaked_families_train_test),
            "leaked_families_train_val_count": len(self.leaked_families_train_val),
            "leaked_inputs_train_test_count": len(self.leaked_inputs_train_test),
        }


def validate_dataset_records(examples: list[dict[str, Any]]) -> dict[str, Any]:
    """Validate all individual records in a dataset list. Fails loudly on first error."""
    for idx, ex in enumerate(examples):
        try:
            validate_training_example(ex)
        except ValidationError as err:
            raise ValidationError(f"Validation failed at record index {idx} ({ex.get('id')}): {err}") from err

    dup_report = check_duplicates(examples)
    if dup_report.duplicate_id_count > 0:
        raise ValidationError(f"Duplicate IDs detected: {dup_report.duplicate_ids[:5]}")
    if dup_report.semantic_collision_count > 0:
        raise ValidationError(f"Semantic contradictory collisions detected: {dup_report.semantic_collisions[:3]}")

    return {
        "record_count": len(examples),
        "duplicate_report": dup_report.to_dict(),
        "is_valid": True,
    }


def verify_zero_leakage(
    train_records: list[dict[str, Any]],
    val_records: list[dict[str, Any]],
    test_records: list[dict[str, Any]],
) -> LeakageReport:
    """Strictly verify that requirement families and inputs do NOT leak across splits.

    Crucial Anti-Leakage Rule:
    The model being evaluated on the test split must NOT have seen paraphrases of
    the same requirement family during training!
    """
    report = LeakageReport()

    train_fams = {ex["metadata"]["family_id"] for ex in train_records if "metadata" in ex}
    val_fams = {ex["metadata"]["family_id"] for ex in val_records if "metadata" in ex}
    test_fams = {ex["metadata"]["family_id"] for ex in test_records if "metadata" in ex}

    # 1. Family leakage between Train and Test
    overlap_train_test = train_fams.intersection(test_fams)
    if overlap_train_test:
        report.has_leakage = True
        report.leaked_families_train_test = sorted(overlap_train_test)

    # 2. Family leakage between Train and Validation
    overlap_train_val = train_fams.intersection(val_fams)
    if overlap_train_val:
        report.has_leakage = True
        report.leaked_families_train_val = sorted(overlap_train_val)

    # 3. Exact input text leakage between Train and Test
    train_inputs = {ex.get("input", "").strip().lower() for ex in train_records}
    for ex in test_records:
        t_in = ex.get("input", "").strip().lower()
        if t_in in train_inputs:
            report.has_leakage = True
            report.leaked_inputs_train_test.append(ex.get("input", ""))

    if report.has_leakage:
        raise ValidationError(
            f"DATA LEAKAGE DETECTED! Overlapping families: train-test={len(report.leaked_families_train_test)}, "
            f"train-val={len(report.leaked_families_train_val)}, identical inputs={len(report.leaked_inputs_train_test)}"
        )

    return report


def load_jsonl(file_path: str | Path) -> list[dict[str, Any]]:
    """Load JSON Lines file."""
    records = []
    p = Path(file_path)
    if not p.is_file():
        raise FileNotFoundError(f"File not found: {p}")
    with open(p, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                records.append(json.loads(line))
    return records


def save_jsonl(records: list[dict[str, Any]], file_path: str | Path) -> None:
    """Save records to JSON Lines file."""
    p = Path(file_path)
    p.parent.mkdir(parents=True, exist_ok=True)
    with open(p, "w", encoding="utf-8") as f:
        for r in records:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")

