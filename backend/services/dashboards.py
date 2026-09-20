"""Dashboard persistence and provider-free stored-query refresh."""

from collections.abc import Callable
from datetime import UTC, datetime
from time import perf_counter
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from api.errors import AppError
from api.schemas.dashboards import DashboardCreate, DashboardWidgetCreate, DashboardWidgetUpdate
from api.schemas.retrieval import RetrievedEntity, RetrievedField
from api.settings import Settings, get_settings
from connectors.base import ConnectorError, DataSourceConnector, QueryLimits
from persistence.models import Dashboard, DashboardWidget, Datasource, Entity, Field, QueryRun
from query.result_verifier import verify_result
from query.sql_validator import validate_postgres_sql
from services.datasources import build_datasource_connector
from visualization.selection import build_chart_config, compatible_chart_types

ConnectorFactory = Callable[[Session, Datasource, Settings], DataSourceConnector]


def _dashboard(session: Session, dashboard_id: UUID) -> Dashboard:
    dashboard = session.get(Dashboard, dashboard_id)
    if dashboard is None:
        raise AppError("dashboard_not_found", "Dashboard was not found", status_code=404)
    return dashboard


def _widget(session: Session, widget_id: UUID) -> DashboardWidget:
    widget = session.get(DashboardWidget, widget_id)
    if widget is None:
        raise AppError(
            "dashboard_widget_not_found", "Dashboard widget was not found", status_code=404
        )
    return widget


def list_dashboards(session: Session) -> list[tuple[Dashboard, int]]:
    return list(
        session.execute(
            select(Dashboard, func.count(DashboardWidget.id))
            .outerjoin(DashboardWidget, DashboardWidget.dashboard_id == Dashboard.id)
            .group_by(Dashboard.id)
            .order_by(Dashboard.updated_at.desc(), Dashboard.name)
        )
        .tuples()
        .all()
    )


def create_dashboard(session: Session, payload: DashboardCreate) -> Dashboard:
    dashboard = Dashboard(name=payload.name, description=payload.description)
    session.add(dashboard)
    session.commit()
    session.refresh(dashboard)
    return dashboard


def dashboard_widgets(
    session: Session, dashboard_id: UUID
) -> tuple[Dashboard, list[DashboardWidget]]:
    dashboard = _dashboard(session, dashboard_id)
    widgets = session.scalars(
        select(DashboardWidget)
        .where(DashboardWidget.dashboard_id == dashboard.id)
        .order_by(DashboardWidget.position)
    ).all()
    return dashboard, list(widgets)


def add_widget(
    session: Session, dashboard_id: UUID, payload: DashboardWidgetCreate
) -> DashboardWidget:
    _dashboard(session, dashboard_id)
    run = session.get(QueryRun, payload.query_run_id)
    if run is None:
        raise AppError("query_run_not_found", "Query run was not found", status_code=404)
    if run.status != "completed" or not run.result_json or not run.generated_query.get("sql"):
        raise AppError(
            "query_run_not_saveable",
            "Only a completed query result can be saved to a dashboard",
            status_code=409,
        )
    if payload.chart_type not in compatible_chart_types(run.result_json):
        raise AppError(
            "chart_type_incompatible",
            "The selected chart is not compatible with this result shape",
            status_code=409,
        )
    next_position = session.scalar(
        select(func.coalesce(func.max(DashboardWidget.position), -1) + 1).where(
            DashboardWidget.dashboard_id == dashboard_id
        )
    )
    widget = DashboardWidget(
        dashboard_id=dashboard_id,
        datasource_id=run.datasource_id,
        source_query_run_id=run.id,
        title=payload.title,
        question=run.question,
        validated_query=run.generated_query,
        query_type=run.query_type,
        chart_type=payload.chart_type,
        chart_config=build_chart_config(run.result_json, payload.chart_type),
        position=int(next_position or 0),
        result_json=run.result_json,
        status="empty" if run.result_json.get("row_count") == 0 else "ready",
        row_count=run.row_count,
        duration_ms=run.duration_ms,
        last_refreshed_at=datetime.now(UTC),
    )
    session.add(widget)
    session.commit()
    session.refresh(widget)
    return widget


def _reposition(session: Session, widgets: list[DashboardWidget]) -> None:
    for index, widget in enumerate(widgets):
        widget.position = -(index + 1)
    session.flush()
    for index, widget in enumerate(widgets):
        widget.position = index


def update_widget(
    session: Session, widget_id: UUID, payload: DashboardWidgetUpdate
) -> DashboardWidget:
    widget = _widget(session, widget_id)
    if payload.title is not None:
        widget.title = payload.title
    if payload.chart_type is not None:
        if payload.chart_type not in compatible_chart_types(widget.result_json):
            raise AppError(
                "chart_type_incompatible",
                "The selected chart is not compatible with this result shape",
                status_code=409,
            )
        widget.chart_type = payload.chart_type
        widget.chart_config = build_chart_config(widget.result_json or {}, payload.chart_type)
    if payload.position is not None:
        widgets = list(
            session.scalars(
                select(DashboardWidget)
                .where(DashboardWidget.dashboard_id == widget.dashboard_id)
                .order_by(DashboardWidget.position)
            ).all()
        )
        widgets.remove(widget)
        widgets.insert(min(payload.position, len(widgets)), widget)
        _reposition(session, widgets)
    session.commit()
    session.refresh(widget)
    return widget


def delete_widget(session: Session, widget_id: UUID) -> None:
    widget = _widget(session, widget_id)
    dashboard_id = widget.dashboard_id
    session.delete(widget)
    session.flush()
    remaining = list(
        session.scalars(
            select(DashboardWidget)
            .where(DashboardWidget.dashboard_id == dashboard_id)
            .order_by(DashboardWidget.position)
        ).all()
    )
    _reposition(session, remaining)
    session.commit()


def _validation_entities(session: Session, datasource_id: UUID) -> list[RetrievedEntity]:
    entities = list(
        session.scalars(
            select(Entity).where(Entity.datasource_id == datasource_id).order_by(Entity.name)
        ).all()
    )
    fields = (
        list(
            session.scalars(
                select(Field).where(Field.entity_id.in_([entity.id for entity in entities]))
            ).all()
        )
        if entities
        else []
    )
    fields_by_entity: dict[UUID, list[Field]] = {}
    for field in fields:
        fields_by_entity.setdefault(field.entity_id, []).append(field)
    return [
        RetrievedEntity(
            id=entity.id,
            schema_name=entity.schema_name,
            name=entity.name,
            description=entity.description,
            selection_source="semantic",
            similarity=None,
            business_terms=[],
            metrics=[],
            fields=[
                RetrievedField(
                    id=field.id,
                    name=field.name,
                    native_type=field.native_type,
                    normalized_type=field.normalized_type,
                    description=field.description,
                    primary_key=bool(field.metadata_json.get("primary_key", False)),
                    unique=bool(field.metadata_json.get("unique", False)),
                    profile=None,
                )
                for field in sorted(
                    fields_by_entity.get(entity.id, []), key=lambda item: item.ordinal
                )
            ],
        )
        for entity in entities
    ]


def refresh_widget(
    session: Session,
    widget_id: UUID,
    *,
    settings: Settings | None = None,
    connector_factory: ConnectorFactory = build_datasource_connector,
) -> DashboardWidget:
    widget = _widget(session, widget_id)
    datasource = session.get(Datasource, widget.datasource_id)
    if datasource is None or datasource.status != "ready":
        raise AppError(
            "datasource_not_ready", "The widget datasource is not ready", status_code=409
        )
    app_settings = settings or get_settings()
    connector: DataSourceConnector | None = None
    try:
        generated_sql = str(widget.validated_query.get("sql", ""))
        expected = widget.validated_query.get("expected_columns", [])
        expected_columns = [str(value) for value in expected] if isinstance(expected, list) else []
        validation = validate_postgres_sql(
            generated_sql,
            _validation_entities(session, datasource.id),
            set(datasource.allowed_schemas),
        )
        if not validation.valid or validation.query is None:
            raise AppError(
                validation.error_code or "stored_query_invalid",
                "The stored query no longer passes deterministic validation",
                status_code=409,
            )
        connector = connector_factory(session, datasource, app_settings)
        limits = QueryLimits(
            timeout_ms=app_settings.datasource_statement_timeout_ms,
            max_rows=app_settings.datasource_max_rows,
        )
        connector.explain(validation.query, limits)
        started = perf_counter()
        result = connector.execute_readonly(validation.query, limits)
        duration_ms = round((perf_counter() - started) * 1000)
        verified = verify_result(result, expected_columns, limits.max_rows, duration_ms)
        widget.result_json = verified.payload
        widget.row_count = len(result.rows)
        widget.duration_ms = duration_ms
        widget.status = "empty" if not result.rows else "ready"
        widget.last_refreshed_at = datetime.now(UTC)
        widget.last_error_code = None
        widget.last_error_message = None
        if widget.chart_type not in compatible_chart_types(verified.payload):
            widget.chart_type = "table"
            widget.chart_config = {}
        else:
            widget.chart_config = build_chart_config(verified.payload, widget.chart_type)
    except (AppError, ConnectorError, TypeError, ValueError) as error:
        widget.status = "stale" if widget.result_json else "failed"
        widget.last_error_code = getattr(error, "code", "widget_refresh_failed")
        widget.last_error_message = getattr(
            error,
            "safe_message",
            getattr(error, "message", "The widget could not be refreshed safely"),
        )
    finally:
        if connector is not None:
            connector.close()
    session.commit()
    session.refresh(widget)
    return widget
