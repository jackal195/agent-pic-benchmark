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


def test_mutation_events_are_not_counted_as_observations() -> None:
    record = json.loads(EXAMPLE.read_text(encoding="utf-8"))
    mutation = {
        "event_id": "event-0003",
        "trace_id": record["trace_id"],
        "request_id": "request-0003",
        "agent_id": "coder",
        "event_index": 2,
        "event_type": "tool_output",
        "tool_type": "str_replace_editor",
        "snapshot_id": "commit1",
        "raw_text": "updated src/auth.py",
        "normalized_text": "updated src/auth.py",
        "source_objects": ["obj-auth-validate"],
        "changed_objects": ["obj-auth-validate"],
        "is_mutation": True,
    }
    target = dict(record["events"][1])
    target["event_id"] = "event-0004"
    target["event_index"] = 3
    target["request_id"] = "request-0004"
    target["snapshot_id"] = "commit1"
    record["events"] = [record["events"][0], mutation, target]

    relations = annotate_trace(record)
    assert [item["relation_id"] for item in relations] == ["event-0001->event-0004"]
    assert relations[0]["state_relation"] == "object_changed_between_events"


def test_partial_overlap_reports_token_span() -> None:
    record = json.loads(EXAMPLE.read_text(encoding="utf-8"))
    record["events"][1]["raw_text"] = "src/auth.py:40: def validate(token, strict=False):\n"
    record["events"][1]["normalized_text"] = "def validate(token, strict=False):\n"
    relation = next(
        item for item in annotate_trace(record)
        if item["relation_id"] == "event-0001->event-0002"
    )
    assert relation["raw_exact"] is False
    assert relation["overlap_tokens"] >= 1
    assert relation["position_relation"] in {"prefix", "interior", "suffix"}
