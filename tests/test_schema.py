import json
from pathlib import Path

from agent_pic_bench.schema import ValidationError, validate_record
from agent_pic_bench.annotate_reuse import annotate_trace


EXAMPLE = Path(__file__).parents[1] / "data/examples/swe-mini.jsonl"


def test_example_trace_is_valid() -> None:
    record = json.loads(EXAMPLE.read_text(encoding="utf-8"))
    validate_record(record)


def test_event_must_belong_to_parent_trace() -> None:
    record = json.loads(EXAMPLE.read_text(encoding="utf-8"))
    record["events"][0]["trace_id"] = "other"
    try:
        validate_record(record)
    except ValidationError as error:
        assert "trace_id" in str(error)
    else:
        raise AssertionError("invalid trace_id was accepted")


def test_reuse_annotation_detects_exact_and_invalidation() -> None:
    record = json.loads(EXAMPLE.read_text(encoding="utf-8"))
    relations = annotate_trace(record)

    exact = next(item for item in relations if item["relation_id"] == "event-0001->event-0002")
    assert exact["relation_type"] == "exact_object_repeat"
    assert exact["state_compatible"] is True
    assert exact["reuse_distance_events"] == 1

    invalidated = next(item for item in relations if item["relation_id"] == "event-0001->event-0004")
    assert invalidated["relation_type"] == "invalidated_overlap"
    assert invalidated["state_compatible"] is False
    assert invalidated["state_relation"] == "object_changed_between_events"


def test_missing_snapshots_are_not_treated_as_compatible() -> None:
    record = json.loads(EXAMPLE.read_text(encoding="utf-8"))
    record["events"][0]["snapshot_id"] = None
    record["events"][1]["snapshot_id"] = None
    relation = next(
        item for item in annotate_trace(record)
        if item["relation_id"] == "event-0001->event-0002"
    )
    assert relation["relation_type"] == "exact_object_repeat_unverified"
    assert relation["state_compatible"] is False
    assert relation["state_relation"] == "snapshot_unknown"
