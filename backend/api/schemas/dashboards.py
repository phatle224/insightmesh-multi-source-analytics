from datetime import datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, Field, field_validator, model_validator

from persistence.models import Dashboard, DashboardWidget
from visualization.selection import compatible_chart_types

ChartType = Literal["table", "kpi", "bar", "line", "pie", "area"]


class DashboardCreate(BaseModel):
    name: str = Field(min_length=1, max_length=160)
    description: str | None = Field(default=None, max_length=1_000)

    @field_validator("name")
    @classmethod
    def strip_name(cls, value: str) -> str:
        if not (clean := value.strip()):
            raise ValueError("Dashboard name must not be blank")
        return clean


class DashboardSummary(BaseModel):
    id: UUID
    name: str
    description: str | None
    widget_count: int
    created_at: datetime
    updated_at: datetime


class DashboardWidgetCreate(BaseModel):
    query_run_id: UUID | None = None
    saved_analysis_id: UUID | None = None
    title: str = Field(min_length=1, max_length=160)
    chart_type: ChartType

    @field_validator("title")
    @classmethod
    def strip_title(cls, value: str) -> str:
        if not (clean := value.strip()):
            raise ValueError("Widget title must not be blank")
        return clean

    @model_validator(mode="after")
    def require_source(self) -> "DashboardWidgetCreate":
        if (self.query_run_id is None) == (self.saved_analysis_id is None):
            raise ValueError("Provide exactly one query run or saved analysis")
        return self


class DashboardWidgetUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=160)
    chart_type: ChartType | None = None
    position: int | None = Field(default=None, ge=0)

    @field_validator("title")
    @classmethod
    def strip_optional_title(cls, value: str | None) -> str | None:
        if value is None:
            return None
        if not (clean := value.strip()):
            raise ValueError("Widget title must not be blank")
        return clean


class DashboardWidgetResponse(BaseModel):
    id: UUID
    dashboard_id: UUID
    datasource_id: UUID
    source_query_run_id: UUID | None
    title: str
    question: str
    validated_query: dict[str, Any]
    query_type: str
    chart_type: str
    chart_config: dict[str, Any]
    compatible_chart_types: list[str]
    position: int
    result: dict[str, Any] | None
    status: str
    row_count: int | None
    duration_ms: int | None
    last_refreshed_at: datetime | None
    error: dict[str, str] | None
    created_at: datetime
    updated_at: datetime


class DashboardDetail(DashboardSummary):
    widgets: list[DashboardWidgetResponse]


def widget_response(widget: DashboardWidget) -> DashboardWidgetResponse:
    return DashboardWidgetResponse(
        id=widget.id,
        dashboard_id=widget.dashboard_id,
        datasource_id=widget.datasource_id,
        source_query_run_id=widget.source_query_run_id,
        title=widget.title,
        question=widget.question,
        validated_query=widget.validated_query,
        query_type=widget.query_type,
        chart_type=widget.chart_type,
        chart_config=widget.chart_config,
        compatible_chart_types=compatible_chart_types(widget.result_json),
        position=widget.position,
        result=widget.result_json,
        status=widget.status,
        row_count=widget.row_count,
        duration_ms=widget.duration_ms,
        last_refreshed_at=widget.last_refreshed_at,
        error=(
            {
                "code": widget.last_error_code,
                "message": widget.last_error_message or "Refresh failed",
            }
            if widget.last_error_code
            else None
        ),
        created_at=widget.created_at,
        updated_at=widget.updated_at,
    )


def dashboard_summary(dashboard: Dashboard, widget_count: int) -> DashboardSummary:
    return DashboardSummary(
        id=dashboard.id,
        name=dashboard.name,
        description=dashboard.description,
        widget_count=widget_count,
        created_at=dashboard.created_at,
        updated_at=dashboard.updated_at,
    )
