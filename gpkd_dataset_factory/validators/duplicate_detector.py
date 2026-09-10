"""Duplicate and Collision Detector for Synthetic Datasets.

Monitors exact string collisions, identifier collisions, and semantic contradictions.
"""

from __future__ import annotations

from typing import Any


class DuplicateReport:
    """Detailed summary of duplicates detected in a dataset."""

    def __init__(self) -> None:
        self.total_records: int = 0
        self.duplicate_id_count: int = 0
        self.duplicate_input_count: int = 0
        self.semantic_collision_count: int = 0
        self.duplicate_ids: list[str] = []
        self.duplicate_inputs: list[str] = []
        self.semantic_collisions: list[dict[str, Any]] = []

    @property
    def duplicate_rate(self) -> float:
        if self.total_records == 0:
            return 0.0
        return round(self.duplicate_input_count / self.total_records, 4)

    def to_dict(self) -> dict[str, Any]:
        return {
            "total_records": self.total_records,
            "duplicate_id_count": self.duplicate_id_count,
            "duplicate_input_count": self.duplicate_input_count,
            "semantic_collision_count": self.semantic_collision_count,
            "duplicate_rate": self.duplicate_rate,
        }


def check_duplicates(examples: list[dict[str, Any]]) -> DuplicateReport:
    """Scan a collection of training examples for duplicates and collisions."""
    report = DuplicateReport()
    report.total_records = len(examples)

    seen_ids: set[str] = set()
    input_to_targets: dict[str, list[dict[str, Any]]] = {}

    for ex in examples:
        eid = ex.get("id", "")
        if eid in seen_ids:
            report.duplicate_id_count += 1
            report.duplicate_ids.append(eid)
        else:
            seen_ids.add(eid)

        raw_input = ex.get("input", "").strip().lower()
        if raw_input in input_to_targets:
            report.duplicate_input_count += 1
            report.duplicate_inputs.append(ex.get("input", ""))
            # Check if target differs (semantic collision / contradiction)
            first_target = input_to_targets[raw_input][0]
            curr_target = ex.get("target", {})
            if first_target.get("value") != curr_target.get("value") or first_target.get("operator") != curr_target.get("operator"):
                report.semantic_collision_count += 1
                report.semantic_collisions.append({
                    "input": ex.get("input"),
                    "target_1": first_target,
                    "target_2": curr_target,
                })
            input_to_targets[raw_input].append(curr_target)
        else:
            input_to_targets[raw_input] = [ex.get("target", {})]

    return report

