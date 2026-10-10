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
from typing import Any, Dict, Set

from .annotate_reuse import _is_observation_event
from .tokenizer import load_tokenizer


def _content_hash(event: Dict[str, Any]) -> str:
    text = event.get("normalized_text") or event.get("raw_text") or ""
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def summarize_cross_trace(path: Path, tokenizer_name: str = "whitespace-prototype") -> Dict[str, Any]:
    tokenizer = load_tokenizer(tokenizer_name)
    seen_content_tasks: Dict[str, Set[str]] = defaultdict(set)
    seen_path_tasks: Dict[str, Set[str]] = defaultdict(set)
    seen_content_agents: Dict[str, Set[str]] = defaultdict(set)
    task_content_seen: Dict[str, Set[str]] = defaultdict(set)
    task_path_seen: Dict[str, Set[str]] = defaultdict(set)
    task_count = 0
    first_introduction_events = 0
    unique_content_versions: Set[str] = set()
    unique_path_versions: Set[str] = set()
    prior_seen_events = 0
    cross_task_events = 0
    same_path_cross_task_events = 0
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
                event_tokens = tokenizer.count(
                    event.get("normalized_text") or event.get("raw_text") or ""
                )
                event_content_keys = set()
                event_path_keys = set()
                for object_id in object_ids:
                    content_key = _content_hash(event)
                    path_key = f"{object_id}|sha256:{content_key}"
                    event_content_keys.add(content_key)
                    event_path_keys.add(path_key)
                    unique_content_versions.add(content_key)
                    unique_path_versions.add(path_key)
                for content_key in event_content_keys:
                    prior_agents = seen_content_agents[content_key]
                    if prior_agents - {str(event.get("agent_id") or "unknown")}:
                        cross_agent_events += 1
                    seen_content_agents[content_key].add(
                        str(event.get("agent_id") or "unknown")
                    )
                    if content_key in task_content_seen[task_id]:
                        continue
                    task_content_seen[task_id].add(content_key)
                    first_introduction_events += 1
                    prior_tasks = seen_content_tasks[content_key]
                    if prior_tasks:
                        prior_seen_events += 1
                        prior_seen_tokens += event_tokens
                    if prior_tasks - {task_id}:
                        cross_task_events += 1
                        cross_task_tokens += event_tokens
                    seen_content_tasks[content_key].add(task_id)
                for path_key in event_path_keys:
                    if path_key in task_path_seen[task_id]:
                        continue
                    task_path_seen[task_id].add(path_key)
                    if seen_path_tasks[path_key] - {task_id}:
                        same_path_cross_task_events += 1
                    seen_path_tasks[path_key].add(task_id)

    return {
        "traces": task_count,
        "first_introduction_events": first_introduction_events,
        "unique_content_versions": len(unique_content_versions),
        "unique_path_versions": len(unique_path_versions),
        "prior_seen_content_introductions": prior_seen_events,
        "cross_task_content_introductions": cross_task_events,
        "same_path_cross_task_introductions": same_path_cross_task_events,
        "cross_agent_content_introductions": cross_agent_events,
        "prior_seen_token_proxy": prior_seen_tokens,
        "cross_task_token_proxy": cross_task_tokens,
        "prior_seen_event_rate": prior_seen_events / first_introduction_events
        if first_introduction_events
        else 0.0,
        "cross_task_event_rate": cross_task_events / first_introduction_events
        if first_introduction_events
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

