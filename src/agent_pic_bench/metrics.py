"""Summaries for normalized Agent PIC traces and reuse relations."""

from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path
from typing import Any, Dict, Iterable, List

from .annotate_reuse import annotate_trace


def _percentile(values: List[int], percentile: float) -> int:
    if not values:
        return 0
    values = sorted(values)
    index = int((len(values) - 1) * percentile)
    return values[index]


def summarize_traces(path: Path) -> Dict[str, Any]:
    trace_count = 0
    resolved = Counter()
    event_types: Counter[str] = Counter()
    tool_types: Counter[str] = Counter()
    state_effects: Counter[str] = Counter()
    relation_types: Counter[str] = Counter()
    state_relations: Counter[str] = Counter()
    relation_scopes: Counter[str] = Counter()
    repos = set()
    total_events = 0
    events_with_objects = 0
    observation_events = 0
    mutation_events = 0
    relations = []

    with path.open(encoding="utf-8") as stream:
        for line in stream:
            if not line.strip():
                continue
            trace = json.loads(line)
            trace_count += 1
            resolved[str(bool(trace.get("resolved", False)))] += 1
            initial_state = trace.get("initial_state") or {}
            if initial_state.get("repo_id"):
                repos.add(initial_state["repo_id"])
            for event in trace.get("events", []):
                total_events += 1
                event_types[event.get("event_type", "unknown")] += 1
                tool_types[event.get("tool_type") or "none"] += 1
                state_effects[event.get("state_effect", "none")] += 1
                events_with_objects += bool(event.get("source_objects"))
                observation_events += bool(
                    event.get("source_objects")
                    and not event.get("is_mutation")
                    and event.get("event_type")
                    in {"tool_output", "test_result", "agent_prompt"}
                )
                mutation_events += bool(event.get("is_mutation"))
            relations.extend(annotate_trace(trace))

    distances = [int(item["reuse_distance_events"]) for item in relations]
    relation_types.update(item["relation_type"] for item in relations)
    state_relations.update(item["state_relation"] for item in relations)
    relation_scopes.update(item["scope"] for item in relations)

    return {
        "traces": trace_count,
        "repos": len(repos),
        "resolved": dict(resolved),
        "events": total_events,
        "events_with_objects": events_with_objects,
        "observation_events": observation_events,
        "mutation_events": mutation_events,
        "event_types": dict(event_types),
        "tool_types": dict(tool_types),
        "state_effects": dict(state_effects),
        "relations": len(relations),
        "raw_exact_relations": sum(bool(item["raw_exact"]) for item in relations),
        "overlap_tokens": sum(int(item.get("overlap_tokens", 0)) for item in relations),
        "prefix_relations": sum(
            item.get("position_relation") == "prefix" for item in relations
        ),
        "non_prefix_relations": sum(
            item.get("position_relation") in {"interior", "suffix"}
            for item in relations
        ),
        "state_compatible_relations": sum(
            bool(item["state_compatible"]) for item in relations
        ),
        "relation_types": dict(relation_types),
        "state_relations": dict(state_relations),
        "relation_scopes": dict(relation_scopes),
        "reuse_distance_events": {
            "p50": _percentile(distances, 0.50),
            "p90": _percentile(distances, 0.90),
            "max": max(distances) if distances else 0,
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Summarize Agent PIC traces")
    parser.add_argument("path", type=Path)
    args = parser.parse_args()
    print(json.dumps(summarize_traces(args.path), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
