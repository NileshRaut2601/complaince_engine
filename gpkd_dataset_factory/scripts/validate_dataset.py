"""Dataset Validation CLI.

Runs comprehensive checks for schema compliance, duplicate rates,
and verifies zero train/test leakage.
Usage:
    python -m gpkd_dataset_factory.scripts.validate_dataset --input gpkd_dataset_factory/datasets/raw/raw_dataset.jsonl
    python -m gpkd_dataset_factory.scripts.validate_dataset --check-splits
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

# Windows UTF-8 console output
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

from gpkd_dataset_factory.validators.dataset_validator import (
    load_jsonl,
    validate_dataset_records,
    verify_zero_leakage,
)
from gpkd_dataset_factory.validators.duplicate_detector import check_duplicates
from gpkd_dataset_factory.validators.requirement_validator import ValidationError


def validate_file(file_path: str | Path) -> bool:
    """Validate a single JSONL dataset file."""
    p = Path(file_path)
    print(f"Validating dataset file: {p.resolve()}")
    try:
        records = load_jsonl(p)
        print(f"Loaded {len(records)} records.")
        res = validate_dataset_records(records)
        print("  [PASS] JSON Schema & Type constraints satisfied.")
        print(f"  [PASS] Duplicate input rate: {res['duplicate_report']['duplicate_rate'] * 100:.2f}%.")
        return True
    except (ValidationError, FileNotFoundError, Exception) as err:
        print(f"  [FAIL] Validation Error: {err}")
        return False


def validate_splits(base_dir: str | Path = "gpkd_dataset_factory/datasets") -> bool:
    """Validate train, validation, and test splits and check for leakage."""
    b = Path(base_dir)
    train_p = b / "train" / "train.jsonl"
    val_p = b / "validation" / "validation.jsonl"
    test_p = b / "test" / "test.jsonl"

    for p in [train_p, val_p, test_p]:
        if not p.is_file():
            print(f"Split file missing: {p}. Please run split_dataset.py first.")
            return False

    print("Loading split partitions...")
    train_recs = load_jsonl(train_p)
    val_recs = load_jsonl(val_p)
    test_recs = load_jsonl(test_p)

    print(f"  Train:      {len(train_recs)} records")
    print(f"  Validation: {len(val_recs)} records")
    print(f"  Test:       {len(test_recs)} records")

    try:
        print("Checking for train/validation/test leakage...")
        leak_report = verify_zero_leakage(train_recs, val_recs, test_recs)
        print("  [PASS] ZERO LEAKAGE CONFIRMED: No requirement family or sentence overlaps.")
        return True
    except ValidationError as err:
        print(f"  [FAIL] LEAKAGE DETECTED: {err}")
        return False


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate synthetic procurement datasets.")
    parser.add_argument("--input", type=str, default=None, help="Path to single dataset JSONL file")
    parser.add_argument("--check-splits", action="store_true", help="Validate train/validation/test partitions and test for leakage")

    args = parser.parse_args()

    if args.check_splits:
        success = validate_splits()
        return 0 if success else 1

    input_path = args.input or "gpkd_dataset_factory/datasets/raw/raw_dataset.jsonl"
    success = validate_file(input_path)
    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())
