"""Cross-trace first-introduction analysis.

This module measures content opportunity across independent task traces.  It
does not claim online arrival time when the source JSONL has no timestamps: the
file order is an explicit, reproducible ordering assumption.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from collections import defaultdict
from pathlib import Path
from typing import Any, Dict, Iterable, List, Set

from .annotate_reuse import _is_observation_event
from .tokenizer import load_tokenizer


def _content_key(object_id: str, event: Dict[str, Any]) -> str:
    text = event.get("normalized_text") or event.get("raw_text") or ""
    digest = hashlib.sha256(text.encode("utf-8")).hexdigest()
    return f"{object_id}|sha256:{digest}"


def summarize_cross_trace(path: Path, tokenizer_name: str = "whitespace-prototype") -> Dict[str, Any]:
    tokenizer = load_tokenizer(tokenizer_name)
    seen_tasks: Dict[str, Set[str]] = defaultdict(set)
    seen_agents: Dict[str, Set[str]] = defaultdict(set)
    seen_keys: Set[str] = set()
    task_count = 0
    observation_events = 0
    unique_keys: Set[str] = set()
    prior_seen_events = 0
    cross_task_events = 0
    cross_agent_events = 0
    prior_seen_tokens = 0
    cross_task_tokens = 0
    records_with_missing_task_id = 0

    with path.open(encoding="utf-8") as stream:
        for line in stream:
            if not line.strip():
                continue
            trace = json.loads(line)
            task_id = str(trace.get("task_id") or trace.get("trace_id") or "unknown")
            if not trace.get("task_id"):
                records_with_missing_task_id += 1
            task_count += 1
            for event in trace.get("events", []):
                if not _is_observation_event(event):
                    continue
                object_ids = event.get("source_objects") or []
                if not object_ids:
                    continue
                observation_events += 1
                event_tokens = tokenizer.count(
                    event.get("normalized_text") or event.get("raw_text") or ""
                )
                for object_id in object_ids:
                    key = _content_key(str(object_id), event)
                    unique_keys.add(key)
                    prior_tasks = seen_tasks[key]
                    prior_agents = seen_agents[key]
                    if prior_tasks or prior_agents:
                        prior_seen_events += 1
                        prior_seen_tokens += event_tokens
                    if prior_tasks - {task_id}:
                        cross_task_events += 1
                        cross_task_tokens += event_tokens
                    if prior_agents - {str(event.get("agent_id") or "unknown")}:
                        cross_agent_events += 1
                    seen_tasks[key].add(task_id)
                    seen_agents[key].add(str(event.get("agent_id") or "unknown"))
                    seen_keys.add(key)

    return {
        "traces": task_count,
        "observation_events": observation_events,
        "unique_object_versions": len(unique_keys),
        "prior_seen_object_events": prior_seen_events,
        "cross_task_object_events": cross_task_events,
        "cross_agent_object_events": cross_agent_events,
        "prior_seen_token_proxy": prior_seen_tokens,
        "cross_task_token_proxy": cross_task_tokens,
        "prior_seen_event_rate": prior_seen_events / observation_events
        if observation_events
        else 0.0,
        "cross_task_event_rate": cross_task_events / observation_events
        if observation_events
        else 0.0,
        "ordering_assumption": "JSONL trace order; no wall-clock timestamps inferred",
        "task_id_missing_records": records_with_missing_task_id,
        "tokenizer": tokenizer.name,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Summarize cross-task content reuse")
    parser.add_argument("path", type=Path)
    parser.add_argument("--tokenizer", default="whitespace-prototype")
    args = parser.parse_args()
    print(json.dumps(summarize_cross_trace(args.path, args.tokenizer), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

