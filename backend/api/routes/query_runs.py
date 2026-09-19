from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from api.errors import AppError
from api.schemas.query_runs import (
    QueryRunCreate,
    QueryRunResponse,
    QueryTraceResponse,
    query_run_response,
)
from harness.runtime import run_postgres_query
from persistence.database import get_session
from persistence.models import QueryRun

router = APIRouter(prefix="/api/v1/query-runs", tags=["query-runs"])
SessionDependency = Annotated[Session, Depends(get_session)]


def _get_run(session: Session, run_id: UUID) -> QueryRun:
    run = session.get(QueryRun, run_id)
    if run is None:
        raise AppError("query_run_not_found", "Query run was not found", status_code=404)
    return run


@router.post("", response_model=QueryRunResponse)
def create_query_run(payload: QueryRunCreate, session: SessionDependency) -> QueryRunResponse:
    run = run_postgres_query(session, payload.datasource_id, payload.question)
    return query_run_response(run)


@router.get("/{run_id}", response_model=QueryRunResponse)
def get_query_run(run_id: UUID, session: SessionDependency) -> QueryRunResponse:
    return query_run_response(_get_run(session, run_id))


@router.get("/{run_id}/trace", response_model=QueryTraceResponse)
def get_query_trace(run_id: UUID, session: SessionDependency) -> QueryTraceResponse:
    run = _get_run(session, run_id)
    return QueryTraceResponse(run_id=run.id, status=run.status, trace=run.trace_json)
