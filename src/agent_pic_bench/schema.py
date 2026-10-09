"""Small, dependency-free validation helpers for the v0.1 trace schema."""

from __future__ import annotations

from collections.abc import Mapping


REQUIRED_TRACE_FIELDS = {
    "trace_id",
    "scenario",
    "task_id",
    "source_dataset",
    "agents",
    "initial_state",
    "events",
}

REQUIRED_EVENT_FIELDS = {
    "event_id",
    "trace_id",
    "request_id",
    "agent_id",
    "event_index",
    "event_type",
    "raw_text",
    "normalized_text",
}


class ValidationError(ValueError):
    """Raised when a trace record violates the v0.1 schema."""


def _require_fields(record: Mapping[str, object], required: set[str], kind: str) -> None:
    missing = sorted(required - record.keys())
    if missing:
        raise ValidationError(f"{kind} missing required fields: {', '.join(missing)}")


def validate_trace(record: Mapping[str, object]) -> None:
    """Validate one trace-level JSON object."""
    _require_fields(record, REQUIRED_TRACE_FIELDS, "trace")
    if not isinstance(record["trace_id"], str) or not record["trace_id"]:
        raise ValidationError("trace_id must be a non-empty string")
    if not isinstance(record["agents"], list) or not all(
        isinstance(agent, str) and agent for agent in record["agents"]
    ):
        raise ValidationError("agents must be a list of non-empty strings")
    if not isinstance(record["events"], list) or not record["events"]:
        raise ValidationError("events must be a non-empty list")


def validate_event(record: Mapping[str, object], trace_id: str) -> None:
    """Validate one normalized event embedded in a trace."""
    _require_fields(record, REQUIRED_EVENT_FIELDS, "event")
    if record["trace_id"] != trace_id:
        raise ValidationError("event trace_id does not match parent trace_id")
    if not isinstance(record["event_index"], int) or record["event_index"] < 0:
        raise ValidationError("event_index must be a non-negative integer")
    for field in ("event_id", "request_id", "agent_id", "event_type"):
        if not isinstance(record[field], str) or not record[field]:
            raise ValidationError(f"{field} must be a non-empty string")
    for field in ("raw_text", "normalized_text"):
        if not isinstance(record[field], str):
            raise ValidationError(f"{field} must be a string")


def validate_record(record: Mapping[str, object]) -> None:
    """Validate a JSONL record containing a trace and its normalized events."""
    validate_trace(record)
    trace_id = record["trace_id"]
    if not isinstance(trace_id, str):
        raise ValidationError("trace_id must be a string")
    for event in record["events"]:
        if not isinstance(event, Mapping):
            raise ValidationError("each event must be a JSON object")
        validate_event(event, trace_id)

