import json
from pathlib import Path

from agent_pic_bench.cross_trace import summarize_cross_trace


def _trace(trace_id: str, task_id: str, agent_id: str) -> dict:
    return {
        "trace_id": trace_id,
        "task_id": task_id,
        "events": [
            {
                "event_id": f"{trace_id}-event",
                "event_type": "tool_output",
                "agent_id": agent_id,
                "source_objects": ["obj:repo:file.py"],
                "normalized_text": "def shared(): pass",
                "raw_text": "def shared(): pass",
                "is_mutation": False,
            }
        ],
    }


def test_cross_trace_counts_prior_seen_and_cross_task(tmp_path: Path) -> None:
    path = tmp_path / "traces.jsonl"
    path.write_text(
        "\n".join(
            json.dumps(item)
            for item in [_trace("t1", "q1", "a1"), _trace("t2", "q2", "a2")]
        )
        + "\n",
        encoding="utf-8",
    )
    summary = summarize_cross_trace(path)
    assert summary["observation_events"] == 2
    assert summary["unique_object_versions"] == 1
    assert summary["prior_seen_object_events"] == 1
    assert summary["cross_task_object_events"] == 1
    assert summary["cross_agent_object_events"] == 1
