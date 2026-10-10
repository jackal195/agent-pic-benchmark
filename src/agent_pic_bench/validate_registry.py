"""Validate the dataset registry used to plan the PIC benchmark."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

REQUIRED_FIELDS = {
    "dataset_id",
    "canonical_name",
    "scene",
    "resource_type",
    "source_url",
    "unit",
    "has_full_trajectory",
    "has_request_order",
    "has_answer_or_reward",
    "train_role",
    "eval_role",
    "reusable_object",
    "main_failure_modes",
    "next_action",
    "provenance_confidence",
}


def validate_registry(records: list[dict[str, Any]]) -> None:
    """Raise ValueError if registry rows are incomplete or duplicated."""
    ids: set[str] = set()
    for index, record in enumerate(records):
        missing = sorted(REQUIRED_FIELDS - record.keys())
        if missing:
            raise ValueError(f"row {index} missing fields: {', '.join(missing)}")
        dataset_id = record["dataset_id"]
        if not isinstance(dataset_id, str) or not dataset_id:
            raise ValueError(f"row {index} has invalid dataset_id")
        if dataset_id in ids:
            raise ValueError(f"duplicate dataset_id: {dataset_id}")
        ids.add(dataset_id)
        if not isinstance(record["reusable_object"], list) or not record["reusable_object"]:
            raise ValueError(f"{dataset_id}: reusable_object must be a non-empty list")
        if not isinstance(record["main_failure_modes"], list):
            raise ValueError(f"{dataset_id}: main_failure_modes must be a list")


def load_registry(path: Path) -> list[dict[str, Any]]:
    records = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(records, list) or not records:
        raise ValueError("registry must be a non-empty JSON list")
    if not all(isinstance(item, dict) for item in records):
        raise ValueError("every registry row must be an object")
    validate_registry(records)
    return records


def main() -> None:
    parser = argparse.ArgumentParser(description="Validate the PIC dataset registry")
    parser.add_argument("path", type=Path)
    args = parser.parse_args()
    records = load_registry(args.path)
    scenes = sorted({record["scene"] for record in records})
    print(json.dumps({"datasets": len(records), "scenes": scenes}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
