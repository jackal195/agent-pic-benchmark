"""Generate method-independent reuse relations from one JSONL trace."""

from __future__ import annotations

import argparse
import json
from typing import Any, Dict, List, Optional, Set

from .overlap import longest_common_span
from .tokenizer import TokenizerAdapter, load_tokenizer


def _is_observation_event(event: Dict[str, Any]) -> bool:
    """Return whether an event represents content that entered a model request.

    Mutation calls and their tool outputs are deliberately excluded.  The
    previous prototype only checked ``source_objects`` and consequently could
    count an edit result as if it were a second read of the file.
    """
    if event.get("is_mutation"):
        return False
    if not event.get("source_objects"):
        return False
    event_type = event.get("event_type")
    return event_type in {"tool_output", "test_result", "agent_prompt"}


def _shared_objects(source: Dict[str, Any], target: Dict[str, Any]) -> List[str]:
    return sorted(
        set(source.get("source_objects", []))
        & set(target.get("source_objects", []))
    )


def _changed_objects_between(
    events: List[Dict[str, Any]], source_index: int, target_index: int
) -> Set[str]:
    changed: Set[str] = set()
    for event in events[source_index + 1 : target_index + 1]:
        changed.update(event.get("changed_objects", []))
    return changed


def annotate_pair(
    source: Dict[str, Any],
    target: Dict[str, Any],
    events: Optional[List[Dict[str, Any]]] = None,
    source_index: Optional[int] = None,
    target_index: Optional[int] = None,
    tokenizer: Optional[TokenizerAdapter] = None,
) -> Optional[Dict[str, Any]]:
    """Create one reuse relation for an ordered pair of events."""
    shared_objects = _shared_objects(source, target)
    if not shared_objects:
        return None

    raw_exact = source.get("raw_text") == target.get("raw_text")
    source_snapshot = source.get("snapshot_id")
    target_snapshot = target.get("snapshot_id")
    snapshots_known = source_snapshot is not None and target_snapshot is not None
    same_snapshot = snapshots_known and source_snapshot == target_snapshot
    cross_agent = source.get("agent_id") != target.get("agent_id")

    changed_objects: Set[str] = set()
    if events is not None and source_index is not None and target_index is not None:
        changed_objects = _changed_objects_between(events, source_index, target_index)

    relevant_change = bool(changed_objects & set(shared_objects))
    state_compatible = same_snapshot and not relevant_change

    if relevant_change:
        relation_type = "invalidated_exact_repeat" if raw_exact else "invalidated_overlap"
        state_relation = "object_changed_between_events"
    elif not snapshots_known:
        relation_type = (
            "exact_object_repeat_unverified"
            if raw_exact
            else "same_object_changed_view_unverified"
        )
        state_relation = "snapshot_unknown"
    elif raw_exact:
        relation_type = "exact_object_repeat"
        state_relation = "same_snapshot"
    else:
        relation_type = "same_object_changed_view"
        state_relation = "same_snapshot"

    active_tokenizer = tokenizer or load_tokenizer("whitespace-prototype")
    overlap = longest_common_span(
        source.get("normalized_text") or source.get("raw_text", ""),
        target.get("normalized_text") or target.get("raw_text", ""),
        active_tokenizer,
    )

    relation: Dict[str, Any] = {
        "relation_id": f"{source['event_id']}->{target['event_id']}",
        "source_event_id": source["event_id"],
        "target_event_id": target["event_id"],
        "shared_objects": shared_objects,
        "relation_type": relation_type,
        "scope": "cross_agent" if cross_agent else "same_agent",
        "source_agent_id": source["agent_id"],
        "target_agent_id": target["agent_id"],
        "source_snapshot_id": source.get("snapshot_id"),
        "target_snapshot_id": target.get("snapshot_id"),
        "raw_exact": raw_exact,
        **overlap,
        "tokenizer": active_tokenizer.name,
        "state_compatible": state_compatible,
        "state_relation": state_relation,
        "annotation_confidence": "exact" if raw_exact else "structural",
    }
    if source_index is not None and target_index is not None:
        relation["reuse_distance_events"] = target_index - source_index
    return relation


def annotate_trace(
    trace: Dict[str, Any], tokenizer: Optional[TokenizerAdapter] = None
) -> List[Dict[str, Any]]:
    events = trace["events"]
    relations: List[Dict[str, Any]] = []
    observation_indices = [
        index for index, event in enumerate(events) if _is_observation_event(event)
    ]
    for source_index in observation_indices:
        source = events[source_index]
        for target_index in observation_indices:
            if target_index <= source_index:
                continue
            relation = annotate_pair(
                source,
                events[target_index],
                events=events,
                source_index=source_index,
                target_index=target_index,
                tokenizer=tokenizer,
            )
            if relation is not None:
                relations.append(relation)
    return relations


def main() -> None:
    parser = argparse.ArgumentParser(description="Annotate Agent PIC reuse relations")
    parser.add_argument("path")
    parser.add_argument("--output", "-o", help="write relations as JSONL")
    parser.add_argument(
        "--tokenizer",
        default="whitespace-prototype",
        help="prototype name or Hugging Face model id",
    )
    args = parser.parse_args()

    with open(args.path, encoding="utf-8") as file:
        trace = json.loads(file.readline())

    relations = annotate_trace(trace, tokenizer=load_tokenizer(args.tokenizer))
    rendered = "\n".join(json.dumps(item, ensure_ascii=False) for item in relations) + "\n"
    if args.output:
        with open(args.output, "w", encoding="utf-8") as file:
            file.write(rendered)
    else:
        print(json.dumps(relations, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
