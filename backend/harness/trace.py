"""Safe structured trace events; never stores prompts, rows, secrets, or reasoning."""

from datetime import UTC, datetime
from typing import Any

from harness.state import RuntimeStatus


def trace_event(
    sequence: int,
    state: RuntimeStatus,
    event: str,
    outcome: str,
    *,
    duration_ms: int | None = None,
    error_code: str | None = None,
    details: dict[str, Any] | None = None,
) -> dict[str, Any]:
    event_data: dict[str, Any] = {
        "sequence": sequence,
        "timestamp": datetime.now(UTC).isoformat(),
        "state": state.value,
        "event": event,
        "outcome": outcome,
    }
    if duration_ms is not None:
        event_data["duration_ms"] = duration_ms
    if error_code is not None:
        event_data["error_code"] = error_code
    if details:
        event_data["details"] = details
    return event_data
