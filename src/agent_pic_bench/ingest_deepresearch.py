"""Normalize DeepResearch trajectory Parquet rows into PIC events."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any, Dict, Iterable, List


def _message_text(message: Dict[str, Any]) -> str:
    parts: List[str] = []
    for content in message.get("content") or []:
        text = content.get("text") if isinstance(content, dict) else None
        if text:
            parts.append(str(text))
    return "\n".join(parts)


def _event_type(message: Dict[str, Any]) -> str:
    role = message.get("role") or "unknown"
    if role == "tool":
        return "tool_output"
    if role == "user":
        return "user_request"
    if role == "assistant":
        return "tool_call" if message.get("recipient") else "agent_response"
    if role in {"system", "developer"}:
        return "agent_prompt"
    return "unknown"


def _object_type(text: str, message: Dict[str, Any]) -> str:
    lowered = text.lower()
    name = str(message.get("name") or message.get("recipient") or "").lower()
    if "web-search://" in lowered or "browser.search" in name:
        return "web_search_result"
    if "web-page://" in lowered or "browser.open" in name:
        return "web_page"
    if message.get("role") == "tool":
        return "tool_output"
    return "none"


def _content_hash(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def normalize_row(row: Dict[str, Any], source_dataset: str = "DeepResearch-traj") -> Dict[str, Any]:
    """Convert one dataset row while retaining message text and provenance."""
    qid = row.get("qid")
    seed = row.get("seed")
    trace_id = f"deepresearch:{qid}:seed-{seed}"
    events: List[Dict[str, Any]] = []
    objects: Dict[str, Dict[str, Any]] = {}

    for index, message in enumerate(row.get("messages") or []):
        text = _message_text(message)
        event_type = _event_type(message)
        object_type = _object_type(text, message)
        source_objects: List[str] = []
        if object_type != "none" and text:
            digest = _content_hash(text)
            object_id = f"obj:deepresearch:{object_type}:{digest[:16]}"
            source_objects.append(object_id)
            objects.setdefault(
                object_id,
                {
                    "object_id": object_id,
                    "object_type": object_type,
                    "content_hash": f"sha256:{digest}",
                    "raw_text": text,
                    "dynamic_fields": [],
                    "exchangeable": "unknown",
                    "order_sensitive": "unknown",
                    "partial_span_safe": "unknown",
                },
            )
        events.append(
            {
                "event_id": f"event-{index:04d}",
                "trace_id": trace_id,
                "request_id": f"request-{index:04d}",
                "agent_id": "research-agent",
                "event_index": index,
                "event_type": event_type,
                "tool_type": message.get("name") or message.get("recipient"),
                "raw_text": text,
                "normalized_text": text,
                "source_objects": source_objects,
                "observation_kind": object_type if object_type != "none" else None,
                "is_mutation": False,
                "snapshot_id": None,
            }
        )

    return {
        "trace_id": trace_id,
        "scenario": "deepresearch",
        "task_id": f"qid-{qid}",
        "source_dataset": source_dataset,
        "model_family": "unknown",
        "agents": ["research-agent"],
        "initial_state": {"snapshot_id": None, "snapshot_source": "not-present"},
        "question": row.get("question"),
        "reference_answer": row.get("answer"),
        "outcome": {
            "status": row.get("status"),
            "correct": row.get("correct"),
            "pass_rate": row.get("pass_rate"),
            "latency_s": row.get("latency_s"),
        },
        "events": events,
        "reusable_objects": list(objects.values()),
    }


def iter_parquet(path: Path, limit: int | None = None) -> Iterable[Dict[str, Any]]:
    import pyarrow.parquet as parquet

    table = parquet.read_table(path)
    rows = table.to_pylist()
    yield from rows[:limit] if limit is not None else rows


def main() -> None:
    parser = argparse.ArgumentParser(description="Normalize DeepResearch trajectories")
    parser.add_argument("input", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--limit", type=int)
    args = parser.parse_args()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", encoding="utf-8") as stream:
        for row in iter_parquet(args.input, args.limit):
            stream.write(json.dumps(normalize_row(row), ensure_ascii=False) + "\n")


if __name__ == "__main__":
    main()
