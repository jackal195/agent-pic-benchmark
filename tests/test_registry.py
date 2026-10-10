import json
from pathlib import Path

from agent_pic_bench.validate_registry import load_registry


REGISTRY = Path(__file__).parents[1] / "data/dataset_registry.json"


def test_dataset_registry_is_valid_and_covers_core_scenes() -> None:
    records = load_registry(REGISTRY)
    scenes = {record["scene"] for record in records}
    assert len(records) >= 10
    assert {"deepresearch", "deepwiki", "swe_repo_based", "ai_game_multi_agent", "pic_kv_controlled"} <= scenes


def test_dataset_registry_separates_natural_and_controlled_resources() -> None:
    records = load_registry(REGISTRY)
    natural = [record for record in records if record["natural_reuse_evidence"] in {"analyze", "unknown"}]
    controlled = [record for record in records if record["resource_type"] in {"controlled_kv_eval", "synthetic_controlled_eval"}]
    assert natural
    assert controlled
    assert all(record["train_role"] == "no" for record in controlled)
