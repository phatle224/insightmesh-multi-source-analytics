from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field

from persistence.models import QueryRun


class QueryRunCreate(BaseModel):
    datasource_id: UUID
    question: str = Field(min_length=3, max_length=1_000)


class QueryRunError(BaseModel):
    code: str
    message: str


class QueryRunResponse(BaseModel):
    run_id: UUID
    datasource_id: UUID
    question: str
    status: str
    generated_query: dict[str, Any] | None
    validation: dict[str, Any]
    result: dict[str, Any] | None
    repair_count: int
    visualization_type: str | None
    clarification_suggestions: list[str]
    warnings: list[str]
    error: QueryRunError | None
    created_at: datetime


class QueryTraceResponse(BaseModel):
    run_id: UUID
    status: str
    trace: list[dict[str, Any]]


def query_run_response(run: QueryRun) -> QueryRunResponse:
    raw_suggestions = run.validation_result.get("clarification_suggestions", [])
    suggestions = (
        [str(item) for item in raw_suggestions]
        if isinstance(raw_suggestions, list)
        else []
    )
    return QueryRunResponse(
        run_id=run.id,
        datasource_id=run.datasource_id,
        question=run.question,
        status=run.status,
        generated_query=run.generated_query or None,
        validation=run.validation_result,
        result=run.result_json,
        repair_count=run.repair_count,
        visualization_type=run.visualization_type,
        clarification_suggestions=suggestions,
        warnings=run.warnings,
        error=(
            QueryRunError(code=run.error_code, message=run.error_message or "Query run failed")
            if run.error_code is not None
            else None
        ),
        created_at=run.created_at,
    )
