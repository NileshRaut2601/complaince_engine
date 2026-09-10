"""Dataset Quality Statistics and Analytics Generator.

Analyzes raw or split dataset partitions and saves metrics to statistics.json.
Usage:
    python -m gpkd_dataset_factory.scripts.statistics --input gpkd_dataset_factory/datasets/raw/raw_dataset.jsonl
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path

# Windows UTF-8 output
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

from gpkd_dataset_factory.validators.dataset_validator import load_jsonl
from gpkd_dataset_factory.validators.duplicate_detector import check_duplicates


def generate_statistics(
    dataset_file: str | Path,
    output_path: str | Path = "gpkd_dataset_factory/datasets/statistics.json",
    splits_dir: str | Path | None = "gpkd_dataset_factory/datasets",
) -> dict:
    """Compute and save comprehensive dataset metrics."""
    records = load_jsonl(dataset_file)
    total = len(records)
    print(f"Analyzing {total} records from {dataset_file}...")

    dup_report = check_duplicates(records)

    cat_counter = Counter()
    op_counter = Counter()
    diff_counter = Counter()
    unit_counter = Counter()
    noise_counter = Counter()
    method_counter = Counter()
    ambiguous_count = 0
    compound_count = 0

    for r in records:
        meta = r.get("metadata", {})
        tgt = r.get("target", {})

        cat = meta.get("category", "unknown")
        cat_counter[cat] += 1

        diff = meta.get("difficulty", "unknown")
        diff_counter[diff] += 1

        noise = meta.get("noise_type") or "clean"
        noise_counter[noise] += 1

        method = meta.get("generation_method", "standard")
        method_counter[method] += 1

        op = str(tgt.get("operator"))
        op_counter[op] += 1

        unit = str(tgt.get("unit"))
        unit_counter[unit] += 1

        if tgt.get("is_ambiguous"):
            ambiguous_count += 1

        if tgt.get("operator") == "includes_all" or isinstance(tgt.get("value"), list):
            compound_count += 1

    # Check split counts if available
    split_counts = {}
    if splits_dir:
        sp = Path(splits_dir)
        for s_name in ["train", "validation", "test"]:
            s_file = sp / s_name / f"{s_name}.jsonl"
            if s_file.is_file():
                split_counts[s_name] = len(load_jsonl(s_file))

    stats = {
        "total_examples": total,
        "split_counts": split_counts,
        "duplicate_metrics": {
            "duplicate_id_count": dup_report.duplicate_id_count,
            "duplicate_input_count": dup_report.duplicate_input_count,
            "duplicate_rate": dup_report.duplicate_rate,
            "semantic_collision_count": dup_report.semantic_collision_count,
        },
        "special_subsets": {
            "ambiguous_examples": ambiguous_count,
            "ambiguous_percentage": round(ambiguous_count / total * 100, 2) if total else 0,
            "ocr_noise_examples": noise_counter.get("ocr", 0),
            "ocr_noise_percentage": round(noise_counter.get("ocr", 0) / total * 100, 2) if total else 0,
            "compound_examples": compound_count,
            "compound_percentage": round(compound_count / total * 100, 2) if total else 0,
        },
        "category_distribution": dict(cat_counter.most_common()),
        "operator_distribution": dict(op_counter.most_common()),
        "difficulty_distribution": dict(diff_counter.most_common()),
        "unit_distribution": dict(unit_counter.most_common()),
        "generation_methods": dict(method_counter.most_common()),
    }

    out_p = Path(output_path)
    out_p.parent.mkdir(parents=True, exist_ok=True)
    with open(out_p, "w", encoding="utf-8") as f:
        json.dump(stats, f, indent=2, ensure_ascii=False)

    print("\n" + "=" * 60)
    print("   GPKD DATASET FACTORY: QUALITY STATISTICS SUMMARY")
    print("=" * 60)
    print(f"Total Examples:           {total}")
    if split_counts:
        print(f"Split Partitions:         Train: {split_counts.get('train')}, Val: {split_counts.get('validation')}, Test: {split_counts.get('test')}")
    print(f"Duplicate Rate:           {dup_report.duplicate_rate * 100:.2f}% (collisions: {dup_report.semantic_collision_count})")
    print(f"Ambiguous Cases:          {ambiguous_count} ({stats['special_subsets']['ambiguous_percentage']}%)")
    print(f"OCR Noisy Clauses:        {noise_counter.get('ocr', 0)} ({stats['special_subsets']['ocr_noise_percentage']}%)")
    print(f"Compound Requirements:    {compound_count} ({stats['special_subsets']['compound_percentage']}%)")
    print("\n--- Category Breakdown ---")
    for cat, cnt in cat_counter.most_common():
        print(f"  {cat:<20}: {cnt:>5} ({cnt/total*100:5.1f}%)")
    print("\n--- Operator Distribution ---")
    for op, cnt in op_counter.most_common():
        print(f"  {op:<20}: {cnt:>5} ({cnt/total*100:5.1f}%)")
    print("\n--- Difficulty Tiers ---")
    for diff, cnt in diff_counter.most_common():
        print(f"  {diff:<20}: {cnt:>5} ({cnt/total*100:5.1f}%)")
    print("=" * 60)
    print(f"Detailed statistics saved to: {out_p}")

    return stats


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate dataset quality statistics.")
    parser.add_argument(
        "--input",
        type=str,
        default="gpkd_dataset_factory/datasets/raw/raw_dataset.jsonl",
        help="Path to dataset JSONL",
    )
    parser.add_argument(
        "--output",
        type=str,
        default="gpkd_dataset_factory/datasets/statistics.json",
        help="Target output statistics JSON path",
    )

    args = parser.parse_args()
    generate_statistics(dataset_file=args.input, output_path=args.output)
    return 0


if __name__ == "__main__":
    sys.exit(main())

