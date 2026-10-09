"""Convert OpenHands SWE-Gym trajectory Parquet rows to Agent PIC JSONL."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any, Dict, Iterable, Iterator, List, Optional


PATH_ARGUMENT_RE = re.compile(r'"path"\s*:\s*"([^"]+)"')


def _repo_id(instance_id: str) -> str:
    return instance_id.split("__", 1)[0]


def _tool_call_text(message: Dict[str, Any]) -> str:
    calls = message.get("tool_calls") or []
    if not calls:
        return message.get("content") or ""
    return json.dumps(calls, ensure_ascii=False, sort_keys=True)


def _path_from_tool_call(message: Dict[str, Any]) -> Optional[str]:
    for call in message.get("tool_calls") or []:
        function = call.get("function") or {}
        arguments = function.get("arguments") or ""
        try:
            parsed = json.loads(arguments)
        except (TypeError, json.JSONDecodeError):
            parsed = None
        if isinstance(parsed, dict) and isinstance(parsed.get("path"), str):
            return parsed["path"]
        match = PATH_ARGUMENT_RE.search(arguments)
        if match:
            return match.group(1)
    return None


def _event_type(role: str) -> str:
    return {
        "system": "agent_prompt",
        "user": "user_request",
        "assistant": "agent_response",
        "tool": "tool_output",
    }.get(role, "unknown")


def normalize_row(row: Dict[str, Any], source_dataset: str) -> Dict[str, Any]:
    """Normalize one OpenHands trajectory row without discarding raw messages."""
    instance_id = str(row["instance_id"])
    run_id = str(row["run_id"])
    trace_id = f"openhands:{instance_id}:{run_id}"
    repo_id = _repo_id(instance_id)
    messages = row.get("messages") or []

    call_objects: Dict[str, str] = {}
    events: List[Dict[str, Any]] = []
    for event_index, message in enumerate(messages):
        role = message.get("role") or "unknown"
        content = message.get("content") or ""
        raw_text = content if content else _tool_call_text(message)
        source_objects: List[str] = []

        path = _path_from_tool_call(message)
        if path:
            object_id = f"obj:{repo_id}:{path}"
            source_objects.append(object_id)
            for call in message.get("tool_calls") or []:
                if call.get("id"):
                    call_objects[call["id"]] = object_id

        tool_call_id = message.get("tool_call_id")
        if tool_call_id in call_objects:
            source_objects.append(call_objects[tool_call_id])

        events.append(
            {
                "event_id": f"event-{event_index:04d}",
                "trace_id": trace_id,
                "request_id": f"request-{event_index:04d}",
                "agent_id": "openhands",
                "event_index": event_index,
                "event_type": _event_type(role),
                "tool_type": message.get("name"),
                "tool_call_id": tool_call_id,
                "snapshot_id": None,
                "raw_text": raw_text,
                "normalized_text": raw_text,
                "token_ids": [],
                "source_objects": sorted(set(source_objects)),
                "dynamic_fields": [],
                "parent_event_id": (
                    f"event-{event_index - 1:04d}" if event_index else None
                ),
            }
        )

    return {
        "trace_id": trace_id,
        "scenario": "swe",
        "task_id": instance_id,
        "source_dataset": source_dataset,
        "run_id": run_id,
        "resolved": bool(row.get("resolved", False)),
        "agents": ["openhands"],
        "initial_state": {
            "repo_id": repo_id,
            "snapshot_id": None,
            "snapshot_source": "not-present-in-trajectory",
        },
        "events": events,
        "task_metadata": {
            "test_result": row.get("test_result"),
            "tools": row.get("tools"),
        },
    }


def _read_rows(path: Path, limit: Optional[int] = None) -> Iterator[Dict[str, Any]]:
    try:
        import pyarrow.parquet as parquet
    except ImportError as error:
        raise RuntimeError(
            "Parquet import requires `pip install -e '.[parquet]'`."
        ) from error

    parquet_file = parquet.ParquetFile(path)
    count = 0
    for batch in parquet_file.iter_batches():
        for row in batch.to_pylist():
            yield row
            count += 1
            if limit is not None and count >= limit:
                return


def main() -> None:
    parser = argparse.ArgumentParser(description="Import OpenHands SWE-Gym trajectories")
    parser.add_argument("input", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--limit", type=int)
    args = parser.parse_args()

    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", encoding="utf-8") as output:
        for row in _read_rows(args.input, args.limit):
            trace = normalize_row(
                row,
                source_dataset="SWE-Gym/OpenHands-Sampled-Trajectories",
            )
            output.write(json.dumps(trace, ensure_ascii=False) + "\n")

    print(f"wrote {args.output}")


if __name__ == "__main__":
    main()
