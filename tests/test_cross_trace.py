import json
from pathlib import Path

from agent_pic_bench.cross_trace import summarize_cross_trace


def _trace(trace_id: str, task_id: str, agent_id: str, object_id: str = "obj:repo:file.py") -> dict:
    return {
        "trace_id": trace_id,
        "task_id": task_id,
        "events": [
            {
                "event_id": f"{trace_id}-event",
                "event_type": "tool_output",
                "agent_id": agent_id,
                "source_objects": [object_id],
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
            for item in [
                _trace("t1", "q1", "a1"),
                _trace("t1-retry", "q1", "a1"),
                _trace("t2", "q2", "a2", "obj:other:renamed.py"),
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    summary = summarize_cross_trace(path)
    assert summary["first_introduction_events"] == 2
    assert summary["unique_content_versions"] == 1
    assert summary["unique_path_versions"] == 2
    assert summary["prior_seen_content_introductions"] == 1
    assert summary["cross_task_content_introductions"] == 1
    assert summary["same_path_cross_task_introductions"] == 0
    assert summary["cross_agent_content_introductions"] == 1
