import json
from pathlib import Path

from agent_pic_bench.ingest_deepresearch import normalize_row


SOURCE = Path(__file__).parents[1] / "work/raw/deepresearch-traj/train-00000-of-00016.parquet"


def test_deepresearch_row_becomes_trace_events_and_objects() -> None:
    import pyarrow.parquet as parquet

    row = parquet.read_table(SOURCE, columns=["qid", "question", "answer", "messages", "status", "seed", "correct", "pass_rate"]).slice(0, 1).to_pylist()[0]
    trace = normalize_row(row)
    assert trace["scenario"] == "deepresearch"
    assert trace["events"]
    assert trace["reusable_objects"]
    assert any(event["observation_kind"] == "web_search_result" for event in trace["events"])
    assert all(obj["exchangeable"] == "unknown" for obj in trace["reusable_objects"])


def test_deepresearch_object_identity_is_content_based() -> None:
    base = {
        "qid": 1,
        "question": "q",
        "answer": "a",
        "status": "success",
        "seed": 42,
        "correct": True,
        "pass_rate": 1.0,
        "messages": [
            {"role": "tool", "name": "browser.search", "content": [{"text": "same result"}]},
            {"role": "tool", "name": "browser.search", "content": [{"text": "same result"}]},
        ],
    }
    trace = normalize_row(base)
    object_ids = [event["source_objects"][0] for event in trace["events"]]
    assert object_ids[0] == object_ids[1]
