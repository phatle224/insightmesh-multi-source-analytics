import base64
import json
from datetime import datetime
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy import and_, func, or_, select
from sqlalchemy.orm import Session

from api.errors import AppError
from api.schemas.query_runs import (
    QueryRunClearResponse,
    QueryRunCreate,
    QueryRunPage,
    QueryRunResponse,
    QueryRunStatus,
    QueryRunSummary,
    QueryTraceResponse,
    query_run_response,
)
from harness.runtime import run_query
from persistence.database import get_session
from persistence.models import Datasource, QueryRun
from services.query_retention import clear_all_query_runs

router = APIRouter(prefix="/api/v1/query-runs", tags=["query-runs"])
SessionDependency = Annotated[Session, Depends(get_session)]


def _encode_cursor(created_at: datetime, run_id: UUID) -> str:
    payload = json.dumps(
        {"created_at": created_at.isoformat(), "run_id": str(run_id)},
        separators=(",", ":"),
    ).encode()
    return base64.urlsafe_b64encode(payload).decode().rstrip("=")


def _decode_cursor(cursor: str) -> tuple[datetime, UUID]:
    try:
        padding = "=" * (-len(cursor) % 4)
        payload = json.loads(base64.urlsafe_b64decode(cursor + padding))
        return datetime.fromisoformat(payload["created_at"]), UUID(payload["run_id"])
    except (ValueError, TypeError, KeyError, json.JSONDecodeError) as exc:
        raise AppError(
            "invalid_query_run_cursor",
            "Query-run cursor is invalid or expired",
            status_code=422,
        ) from exc


def _get_run(session: Session, run_id: UUID) -> QueryRun:
    run = session.get(QueryRun, run_id)
    if run is None:
        raise AppError("query_run_not_found", "Query run was not found", status_code=404)
    return run


@router.post("", response_model=QueryRunResponse)
def create_query_run(payload: QueryRunCreate, session: SessionDependency) -> QueryRunResponse:
    run = run_query(session, payload.datasource_id, payload.question)
    return query_run_response(run)


@router.delete("", response_model=QueryRunClearResponse)
def clear_query_runs(session: SessionDependency) -> QueryRunClearResponse:
    return QueryRunClearResponse(deleted_count=clear_all_query_runs(session))


@router.get("", response_model=QueryRunPage)
def list_query_runs(
    session: SessionDependency,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    cursor: Annotated[str | None, Query(min_length=1, max_length=500)] = None,
    status: QueryRunStatus | None = None,
    datasource_id: UUID | None = None,
    created_before: datetime | None = None,
    search: Annotated[str | None, Query(min_length=1, max_length=200)] = None,
) -> QueryRunPage:
    filters = []
    if status is not None:
        filters.append(QueryRun.status == status)
    if datasource_id is not None:
        filters.append(QueryRun.datasource_id == datasource_id)
    if created_before is not None:
        filters.append(QueryRun.created_at < created_before)
    if search is not None:
        escaped = search.strip().replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
        if escaped:
            filters.append(QueryRun.question.ilike(f"%{escaped}%", escape="\\"))

    total = session.scalar(select(func.count(QueryRun.id)).where(*filters)) or 0
    page_filters = list(filters)
    if cursor is not None:
        cursor_created_at, cursor_run_id = _decode_cursor(cursor)
        page_filters.append(
            or_(
                QueryRun.created_at < cursor_created_at,
                and_(
                    QueryRun.created_at == cursor_created_at,
                    QueryRun.id < cursor_run_id,
                ),
            )
        )
    rows = session.execute(
        select(QueryRun, Datasource.name)
        .join(Datasource, Datasource.id == QueryRun.datasource_id)
        .where(*page_filters)
        .order_by(QueryRun.created_at.desc(), QueryRun.id.desc())
        .limit(limit + 1)
    ).all()
    has_more = len(rows) > limit
    visible_rows = rows[:limit]
    next_cursor = (
        _encode_cursor(visible_rows[-1][0].created_at, visible_rows[-1][0].id)
        if has_more and visible_rows
        else None
    )
    return QueryRunPage(
        items=[
            QueryRunSummary(
                run_id=run.id,
                datasource_id=run.datasource_id,
                datasource_name=datasource_name,
                question=run.question,
                status=run.status,
                row_count=run.row_count,
                duration_ms=run.duration_ms,
                repair_count=run.repair_count,
                provider_call_count=run.provider_call_count,
                visualization_type=run.visualization_type,
                error_code=run.error_code,
                created_at=run.created_at,
            )
            for run, datasource_name in visible_rows
        ],
        limit=limit,
        total=total,
        next_cursor=next_cursor,
        has_more=has_more,
    )


@router.get("/{run_id}", response_model=QueryRunResponse)
def get_query_run(run_id: UUID, session: SessionDependency) -> QueryRunResponse:
    return query_run_response(_get_run(session, run_id))


@router.get("/{run_id}/trace", response_model=QueryTraceResponse)
def get_query_trace(run_id: UUID, session: SessionDependency) -> QueryTraceResponse:
    run = _get_run(session, run_id)
    return QueryTraceResponse(run_id=run.id, status=run.status, trace=run.trace_json)
