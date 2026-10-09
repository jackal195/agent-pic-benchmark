import json
from pathlib import Path

from agent_pic_bench.schema import ValidationError, validate_record


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
