"""Family-Based Anti-Leakage Dataset Partitioning CLI.

Splits synthetic examples into Train, Validation, and Test sets by Requirement Family.
Prevents paraphrases of the same requirement from leaking between train and test.
Also exports Alpaca-compatible instruction-tuning formatted JSONL files.

Usage:
    python -m gpkd_dataset_factory.scripts.split_dataset --input gpkd_dataset_factory/datasets/raw/raw_dataset.jsonl
"""

from __future__ import annotations

import argparse
import json
import random
import sys
from collections import defaultdict
from pathlib import Path

# Windows UTF-8 console output
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

from gpkd_dataset_factory.validators.dataset_validator import load_jsonl, save_jsonl, verify_zero_leakage


INSTRUCTION_PROMPT = (
    "You are a government procurement compliance assistant. Extract the structured tender requirement "
    "from the following natural language clause into the canonical JSON schema. Return strictly valid JSON."
)


def split_dataset_by_family(
    input_file: str | Path,
    output_dir: str | Path = "gpkd_dataset_factory/datasets",
    train_ratio: float = 0.70,
    val_ratio: float = 0.15,
    test_ratio: float = 0.15,
    seed: int = 42,
) -> dict[str, int]:
    """Partition records by requirement family to guarantee zero data leakage."""
    rng = random.Random(seed)
    records = load_jsonl(input_file)
    print(f"Loaded {len(records)} total records from {input_file}")

    # Group records by category and then by family_id for balanced category representation
    cat_to_families: dict[str, dict[str, list[dict]]] = defaultdict(lambda: defaultdict(list))
    for r in records:
        cat = r["metadata"]["category"]
        fam = r["metadata"]["family_id"]
        cat_to_families[cat][fam].append(r)

    train_records: list[dict] = []
    val_records: list[dict] = []
    test_records: list[dict] = []

    # Stratified split by category
    for cat, fam_dict in sorted(cat_to_families.items()):
        fams = sorted(fam_dict.keys())
        rng.shuffle(fams)

        n_fams = len(fams)
        n_val = max(1, int(round(n_fams * val_ratio)))
        n_test = max(1, int(round(n_fams * test_ratio)))
        n_train = n_fams - n_val - n_test

        if n_train < 1:
            # If a small category has only 1-2 families, ensure train gets at least one
            n_train = 1
            n_val = 1 if n_fams > 2 else 0
            n_test = n_fams - n_train - n_val

        train_f_keys = fams[:n_train]
        val_f_keys = fams[n_train:n_train + n_val]
        test_f_keys = fams[n_train + n_val:]

        for f in train_f_keys:
            train_records.extend(fam_dict[f])
        for f in val_f_keys:
            val_records.extend(fam_dict[f])
        for f in test_f_keys:
            test_records.extend(fam_dict[f])

    # Shuffle each partition independently
    rng.shuffle(train_records)
    rng.shuffle(val_records)
    rng.shuffle(test_records)

    # Verify zero leakage
    print("Verifying partition separation...")
    verify_zero_leakage(train_records, val_records, test_records)
    print("  [SUCCESS] Zero family and zero sentence leakage confirmed!")

    base = Path(output_dir)
    train_path = base / "train" / "train.jsonl"
    val_path = base / "validation" / "validation.jsonl"
    test_path = base / "test" / "test.jsonl"

    save_jsonl(train_records, train_path)
    save_jsonl(val_records, val_path)
    save_jsonl(test_records, test_path)

    # Export instruction-tuning format (Alpaca / HuggingFace style)
    def to_instruction_format(recs: list[dict]) -> list[dict]:
        inst_list = []
        for r in recs:
            # Strip synthetic surrogate requirement_id so downstream models do not hallucinate arbitrary IDs
            target_clean = {k: v for k, v in r["target"].items() if k != "requirement_id"}
            inst_list.append({
                "instruction": INSTRUCTION_PROMPT,
                "input": r["input"],
                "output": json.dumps(target_clean, ensure_ascii=False),
            })
        return inst_list

    save_jsonl(to_instruction_format(train_records), base / "train" / "train_instruction.jsonl")
    save_jsonl(to_instruction_format(val_records), base / "validation" / "validation_instruction.jsonl")
    save_jsonl(to_instruction_format(test_records), base / "test" / "test_instruction.jsonl")

    print(f"\n--- Split Summary ---")
    print(f"Train partition:      {len(train_records)} examples -> {train_path}")
    print(f"Validation partition: {len(val_records)} examples -> {val_path}")
    print(f"Test partition:       {len(test_records)} examples -> {test_path}")
    print(f"Instruction tuning formats also saved to {base}/*/*_instruction.jsonl")

    return {
        "train": len(train_records),
        "validation": len(val_records),
        "test": len(test_records),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Split dataset by requirement family (Anti-Leakage).")
    parser.add_argument(
        "--input",
        type=str,
        default="gpkd_dataset_factory/datasets/raw/raw_dataset.jsonl",
        help="Path to raw JSONL dataset",
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default="gpkd_dataset_factory/datasets",
        help="Base directory for splits",
    )
    parser.add_argument("--seed", type=int, default=42, help="Random seed for splitting")

    args = parser.parse_args()
    split_dataset_by_family(input_file=args.input, output_dir=args.output_dir, seed=args.seed)
    return 0


if __name__ == "__main__":
    sys.exit(main())

