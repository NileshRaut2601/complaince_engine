"""Dataset Generation Orchestrator CLI.

Generates large-scale synthetic training examples for tender requirement extraction.
Usage:
    python -m gpkd_dataset_factory.scripts.generate_dataset --count 10000 --seed 42
"""

from __future__ import annotations

import argparse
import random
import sys
from pathlib import Path

# Windows UTF-8 stdout configuration
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

from gpkd_dataset_factory.generators.clause_generator import ClauseGenerator
from gpkd_dataset_factory.generators.requirement_generator import RequirementGenerator
from gpkd_dataset_factory.generators.variation_generator import VariationGenerator
from gpkd_dataset_factory.validators.dataset_validator import save_jsonl
from gpkd_dataset_factory.validators.requirement_validator import validate_training_example


def generate_synthetic_dataset(
    count: int = 10000,
    seed: int = 42,
    output_path: str | Path | None = None,
) -> list[dict]:
    """Generate N validated training examples across requirement families."""
    rng = random.Random(seed)
    req_gen = RequirementGenerator()
    clause_gen = ClauseGenerator(seed=seed)
    var_gen = VariationGenerator(seed=seed)

    families = req_gen.families
    num_families = len(families)

    # Base examples per family to reach target count
    per_family_base = count // num_families
    remainder = count % num_families

    examples: list[dict] = []
    ex_counter = 1

    # Ingestion tracking
    ocr_quota = int(count * 0.10)
    ocr_applied = 0

    for idx, family in enumerate(families):
        fam_count = per_family_base + (1 if idx < remainder else 0)
        clauses = clause_gen.generate_clauses_for_family(family, count=fam_count)

        for cl in clauses:
            raw_text = cl["text"]
            diff = cl["difficulty"]
            method = cl["method"]
            noise_type = None

            # Apply synonym variations on non-tabular text
            if not cl.get("is_table") and not family.is_ambiguous:
                raw_text = var_gen.apply_synonym_variation(raw_text)

            # Apply OCR noise to meet quota
            if ocr_applied < ocr_quota and rng.random() < 0.20:
                raw_text, noise_type = var_gen.inject_ocr_noise(raw_text)
                ocr_applied += 1

            # Occasionally add clause numbering
            if rng.random() < 0.30 and not cl.get("is_table"):
                raw_text = var_gen.add_clause_numbering(raw_text)

            req_id_str = f"REQ_{ex_counter:06d}"
            gpkd_id_str = f"GPKD_{ex_counter:06d}"

            record = {
                "id": gpkd_id_str,
                "input": raw_text,
                "target": family.to_canonical_dict(req_id_str),
                "metadata": {
                    "source": "synthetic",
                    "family_id": family.family_id,
                    "category": family.category,
                    "difficulty": diff,
                    "generation_method": method,
                    "noise_type": noise_type,
                    "generator_version": "1.0",
                },
            }

            # Immediate fail-loudly validation
            validate_training_example(record)
            examples.append(record)
            ex_counter += 1

    # Shuffle dataset
    rng.shuffle(examples)

    if output_path:
        out_p = Path(output_path)
        save_jsonl(examples, out_p)
        print(f"Successfully generated and saved {len(examples)} examples to: {out_p}")

    return examples


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Generate synthetic procurement requirement extraction dataset."
    )
    parser.add_argument("--count", type=int, default=10000, help="Number of examples to generate")
    parser.add_argument("--seed", type=int, default=42, help="Random seed for deterministic generation")
    parser.add_argument(
        "--output",
        type=str,
        default="gpkd_dataset_factory/datasets/raw/raw_dataset.jsonl",
        help="Target output JSONL path",
    )

    args = parser.parse_args()

    print("=" * 65)
    print("  GPKD DATASET FACTORY: REQUIREMENT EXTRACTION GENERATOR")
    print("=" * 65)
    print(f"Target count: {args.count}")
    print(f"Random seed:  {args.seed}")
    print(f"Output file:  {args.output}")
    print("=" * 65)

    generate_synthetic_dataset(count=args.count, seed=args.seed, output_path=args.output)
    return 0


if __name__ == "__main__":
    sys.exit(main())

