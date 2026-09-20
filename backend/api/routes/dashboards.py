from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Response
from sqlalchemy.orm import Session

from api.schemas.dashboards import (
    DashboardCreate,
    DashboardDetail,
    DashboardSummary,
    DashboardWidgetCreate,
    DashboardWidgetResponse,
    DashboardWidgetUpdate,
    dashboard_summary,
    widget_response,
)
from persistence.database import get_session
from services import dashboards as dashboard_service

router = APIRouter(prefix="/api/v1", tags=["dashboards"])
SessionDependency = Annotated[Session, Depends(get_session)]


@router.get("/dashboards", response_model=list[DashboardSummary])
def list_dashboards(session: SessionDependency) -> list[DashboardSummary]:
    return [
        dashboard_summary(item, count) for item, count in dashboard_service.list_dashboards(session)
    ]


@router.post("/dashboards", response_model=DashboardSummary, status_code=201)
def create_dashboard(payload: DashboardCreate, session: SessionDependency) -> DashboardSummary:
    return dashboard_summary(dashboard_service.create_dashboard(session, payload), 0)


@router.get("/dashboards/{dashboard_id}", response_model=DashboardDetail)
def get_dashboard(dashboard_id: UUID, session: SessionDependency) -> DashboardDetail:
    dashboard, widgets = dashboard_service.dashboard_widgets(session, dashboard_id)
    return DashboardDetail(
        **dashboard_summary(dashboard, len(widgets)).model_dump(),
        widgets=[widget_response(widget) for widget in widgets],
    )


@router.post(
    "/dashboards/{dashboard_id}/widgets",
    response_model=DashboardWidgetResponse,
    status_code=201,
)
def add_widget(
    dashboard_id: UUID, payload: DashboardWidgetCreate, session: SessionDependency
) -> DashboardWidgetResponse:
    return widget_response(dashboard_service.add_widget(session, dashboard_id, payload))


@router.patch("/dashboard-widgets/{widget_id}", response_model=DashboardWidgetResponse)
def update_widget(
    widget_id: UUID, payload: DashboardWidgetUpdate, session: SessionDependency
) -> DashboardWidgetResponse:
    return widget_response(dashboard_service.update_widget(session, widget_id, payload))


@router.delete("/dashboard-widgets/{widget_id}", status_code=204)
def delete_widget(widget_id: UUID, session: SessionDependency) -> Response:
    dashboard_service.delete_widget(session, widget_id)
    return Response(status_code=204)


@router.post("/dashboard-widgets/{widget_id}/refresh", response_model=DashboardWidgetResponse)
def refresh_widget(widget_id: UUID, session: SessionDependency) -> DashboardWidgetResponse:
    return widget_response(dashboard_service.refresh_widget(session, widget_id))
