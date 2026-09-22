"""Retention helpers for short-lived query execution artifacts."""

from datetime import UTC, datetime

from sqlalchemy import delete, update
from sqlalchemy.orm import Session

from persistence.models import QueryRun

ACTIVE_STATUSES = {
    "received",
    "retrieve_context",
    "generate_query",
    "validate_query",
    "execute_query",
    "repair_query",
    "verify_result",
    "select_visualization",
}


def cleanup_expired_query_runs(
    session: Session, *, now: datetime | None = None
) -> tuple[int, int]:
    """Clear heavy artifacts first, then remove expired summary rows.

    The function is safe to call opportunistically at the start of a new run or
    from a scheduled worker. Active runs are never modified by retention.
    """

    effective_now = now or datetime.now(UTC)
    terminal_filter = QueryRun.status.not_in(ACTIVE_STATUSES)
    artifact_result = session.execute(
        update(QueryRun)
        .where(
            QueryRun.artifacts_expires_at.is_not(None),
            QueryRun.artifacts_expires_at <= effective_now,
            terminal_filter,
            (QueryRun.result_json.is_not(None)) | (QueryRun.trace_json != []),
        )
        .values(result_json=None, trace_json=[])
    )
    artifacts = int(getattr(artifact_result, "rowcount", 0) or 0)
    delete_result = session.execute(
        delete(QueryRun).where(
            QueryRun.expires_at.is_not(None),
            QueryRun.expires_at <= effective_now,
            terminal_filter,
        )
    )
    deleted = int(getattr(delete_result, "rowcount", 0) or 0)
    return artifacts, deleted


def clear_all_query_runs(session: Session) -> int:
    """Clear all user-visible recent activity, including stale interrupted runs."""

    result = session.execute(delete(QueryRun))
    deleted = int(getattr(result, "rowcount", 0) or 0)
    session.commit()
    return deleted
