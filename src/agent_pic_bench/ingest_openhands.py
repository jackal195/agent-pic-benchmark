"""Convert OpenHands SWE-Gym trajectory Parquet rows to Agent PIC JSONL."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any, Dict, Iterator, List, Optional, Set, Tuple


PATH_ARGUMENT_RE = re.compile(r'"path"\s*:\s*"([^"]+)"')
VIEW_RANGE_RE = re.compile(r'"view_range"\s*:\s*\[\s*(\d+)\s*,\s*(\d+)\s*\]')
NUMBERED_TAB_LINE_RE = re.compile(r"^\s*\d+\t(.*)$")
NUMBERED_PIPE_LINE_RE = re.compile(r"^\s*\d+\s*\|\s?(.*)$")


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


def _view_range_from_args(arguments: Dict[str, Any]) -> Optional[List[int]]:
    """Return an editor view range as [start_line, end_line] when present."""
    value = arguments.get("view_range")
    if isinstance(value, (list, tuple)) and len(value) == 2:
        try:
            start, end = int(value[0]), int(value[1])
        except (TypeError, ValueError):
            return None
        if start >= 1 and end >= start:
            return [start, end]
    return None


def _canonical_tool_output(text: str) -> str:
    """Remove OpenHands' ``cat -n`` wrapper while preserving code indentation."""
    lines = text.splitlines()
    canonical: List[str] = []
    for line in lines:
        match = NUMBERED_TAB_LINE_RE.match(line) or NUMBERED_PIPE_LINE_RE.match(line)
        if match:
            canonical.append(match.group(1))
    if canonical:
        return "\n".join(canonical) + ("\n" if text.endswith("\n") else "")
    return text


def _tool_specs(message: Dict[str, Any]) -> List[Tuple[str, Dict[str, Any], str]]:
    """Return (call_id, parsed arguments, function name) for tool calls."""
    specs: List[Tuple[str, Dict[str, Any], str]] = []
    for call in message.get("tool_calls") or []:
        function = call.get("function") or {}
        try:
            arguments = json.loads(function.get("arguments") or "{}")
        except (TypeError, json.JSONDecodeError):
            arguments = {}
        if not isinstance(arguments, dict):
            arguments = {}
        specs.append((call.get("id") or "", arguments, function.get("name") or ""))
    return specs


def _object_id(repo_id: str, path: str) -> str:
    return f"obj:{repo_id}:{path}"


def _editor_mutation(args: Dict[str, Any]) -> bool:
    return args.get("command") in {"create", "str_replace", "insert", "undo_edit"}


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
    pending_effects: Dict[str, Dict[str, Any]] = {}
    snapshot_number = 0
    snapshot_id: Optional[str] = "synthetic-snapshot-0000"
    state_known = True
    events: List[Dict[str, Any]] = []
    for event_index, message in enumerate(messages):
        role = message.get("role") or "unknown"
        content = message.get("content") or ""
        raw_text = content if content else _tool_call_text(message)
        normalized_text = (
            _canonical_tool_output(raw_text)
            if role == "tool" and message.get("name") == "str_replace_editor"
            else raw_text
        )
        source_objects: List[str] = []
        source_spans: List[Dict[str, Any]] = []
        changed_objects: Set[str] = set()
        state_effect = "none"
        observation_kind: Optional[str] = None
        is_mutation = False
        tool_command: Optional[str] = None
        event_path: Optional[str] = None

        if role == "tool":
            effect = pending_effects.pop(message.get("tool_call_id") or "", None)
            if effect:
                is_mutation = bool(effect.get("is_mutation", False))
                if effect.get("path"):
                    event_path = effect["path"]
                if effect.get("view_range"):
                    source_spans.append(
                        {
                            "path": effect.get("path"),
                            "start_line": effect["view_range"][0],
                            "end_line": effect["view_range"][1],
                        }
                    )
                observation_kind = effect.get("observation_kind") or observation_kind
                changed_objects.update(effect.get("changed_objects", []))
                if effect.get("unknown_state"):
                    state_effect = "unknown"
                    state_known = False
                    snapshot_id = None
                elif changed_objects:
                    state_effect = "object_changed"
                    if state_known:
                        snapshot_number += 1
                        snapshot_id = f"synthetic-snapshot-{snapshot_number:04d}"

        for call_id, arguments, function_name in _tool_specs(message):
            path = arguments.get("path")
            if isinstance(path, str):
                event_path = path
            command = arguments.get("command")
            if isinstance(command, str):
                tool_command = command
            object_id = _object_id(repo_id, path) if isinstance(path, str) else None
            if object_id:
                call_objects[call_id] = object_id
                if function_name == "str_replace_editor" and command == "view":
                    observation_kind = "code_view"
                    view_range = _view_range_from_args(arguments)
                    if view_range:
                        source_spans.append(
                            {
                                "path": path,
                                "start_line": view_range[0],
                                "end_line": view_range[1],
                            }
                        )
                    pending_effects[call_id] = {
                        "changed_objects": [],
                        "unknown_state": False,
                        "is_mutation": False,
                        "path": path,
                        "view_range": view_range,
                        "observation_kind": "code_view",
                    }
                elif function_name == "str_replace_editor" and _editor_mutation(arguments):
                    is_mutation = True
                    pending_effects[call_id] = {
                        "changed_objects": [object_id],
                        "unknown_state": False,
                        "is_mutation": True,
                    }
                elif function_name == "execute_bash":
                    pending_effects[call_id] = {
                        "changed_objects": [],
                        "unknown_state": True,
                        "is_mutation": False,
                    }
            elif function_name == "execute_bash":
                pending_effects[call_id] = {
                    "changed_objects": [],
                    "unknown_state": True,
                    "is_mutation": False,
                }

        path = _path_from_tool_call(message)
        if path:
            object_id = _object_id(repo_id, path)
            if not is_mutation:
                source_objects.append(object_id)
            for call in message.get("tool_calls") or []:
                if call.get("id"):
                    call_objects[call["id"]] = object_id

        tool_call_id = message.get("tool_call_id")
        if tool_call_id in call_objects:
            if role == "tool" and not is_mutation:
                source_objects.append(call_objects[tool_call_id])
                if observation_kind is None:
                    observation_kind = "tool_output"

        if role == "tool" and observation_kind is None and content:
            observation_kind = "shell_output" if event_path is None else "tool_output"

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
                "snapshot_id": snapshot_id,
                "state_effect": state_effect,
                "observation_kind": observation_kind,
                "is_mutation": is_mutation,
                "path": event_path,
                "view_range": source_spans[0] if source_spans else None,
                "tool_command": tool_command,
                "raw_text": raw_text,
                "normalized_text": normalized_text,
                "token_ids": [],
                "source_objects": sorted(set(source_objects)),
                "source_spans": source_spans,
                "changed_objects": sorted(changed_objects),
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
            "snapshot_id": "synthetic-snapshot-0000",
            "snapshot_source": "trajectory-derived-synthetic",
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
