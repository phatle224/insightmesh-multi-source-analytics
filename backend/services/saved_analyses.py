"""Durable, user-facing query definitions independent of query-run retention."""

from collections.abc import Callable
from time import perf_counter
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from api.errors import AppError
from api.schemas.saved_analyses import SavedAnalysisCreate, SavedAnalysisUpdate
from api.settings import Settings, get_settings
from connectors.base import ConnectorError, DataSourceConnector, QueryLimits
from persistence.models import Datasource, QueryRun, SavedAnalysis
from query.result_verifier import verify_result
from query.sql_validator import validate_mysql_sql, validate_postgres_sql
from services.dashboards import _validation_entities
from services.datasources import build_datasource_connector
from visualization.selection import select_visualization

ConnectorFactory = Callable[[Session, Datasource, Settings], DataSourceConnector]


def _saved_analysis(session: Session, analysis_id: UUID) -> SavedAnalysis:
    item = session.get(SavedAnalysis, analysis_id)
    if item is None:
        raise AppError("saved_analysis_not_found", "Saved analysis was not found", status_code=404)
    return item


def list_saved_analyses(session: Session) -> list[tuple[SavedAnalysis, str]]:
    return list(
        session.execute(
            select(SavedAnalysis, Datasource.name)
            .join(Datasource, Datasource.id == SavedAnalysis.datasource_id)
            .order_by(SavedAnalysis.updated_at.desc(), SavedAnalysis.name)
        )
        .tuples()
        .all()
    )


def create_saved_analysis(session: Session, payload: SavedAnalysisCreate) -> SavedAnalysis:
    run = session.get(QueryRun, payload.query_run_id)
    if run is None:
        raise AppError("query_run_not_found", "Query run was not found", status_code=404)
    if run.status != "completed" or not run.generated_query.get("sql"):
        raise AppError(
            "query_run_not_saveable",
            "Only a completed query can be saved as an analysis",
            status_code=409,
        )
    item = SavedAnalysis(
        datasource_id=run.datasource_id,
        name=payload.name,
        description=payload.description,
        question=run.question,
        validated_query=run.generated_query,
        query_type=run.query_type,
        visualization_type=run.visualization_type,
        result_json=run.result_json,
        tags=payload.tags,
        source_query_run_id=run.id,
    )
    session.add(item)
    session.commit()
    session.refresh(item)
    return item


def update_saved_analysis(
    session: Session, analysis_id: UUID, payload: SavedAnalysisUpdate
) -> SavedAnalysis:
    item = _saved_analysis(session, analysis_id)
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(item, key, value)
    session.commit()
    session.refresh(item)
    return item


def delete_saved_analysis(session: Session, analysis_id: UUID) -> None:
    item = _saved_analysis(session, analysis_id)
    session.delete(item)
    session.commit()


def refresh_saved_analysis(
    session: Session,
    analysis_id: UUID,
    *,
    settings: Settings | None = None,
    connector_factory: ConnectorFactory = build_datasource_connector,
) -> SavedAnalysis:
    """Refresh a saved analysis in place without creating a new query-run history item."""
    item = _saved_analysis(session, analysis_id)
    datasource = session.get(Datasource, item.datasource_id)
    if datasource is None or datasource.status != "ready":
        raise AppError(
            "datasource_not_ready",
            "The saved analysis datasource is not ready",
            status_code=409,
        )

    generated_sql = str(item.validated_query.get("sql", ""))
    expected = item.validated_query.get("expected_columns", [])
    expected_columns = [str(value) for value in expected] if isinstance(expected, list) else []
    validator = (
        validate_mysql_sql if datasource.source_type == "mysql" else validate_postgres_sql
    )
    validation = validator(
        generated_sql,
        _validation_entities(session, datasource.id),
        set(datasource.allowed_schemas),
    )
    if not validation.valid or validation.query is None:
        raise AppError(
            validation.error_code or "stored_query_invalid",
            "The saved query no longer passes deterministic validation",
            status_code=409,
        )

    app_settings = settings or get_settings()
    connector: DataSourceConnector | None = None
    try:
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
        item.result_json = verified.payload
        item.visualization_type = select_visualization(verified.payload)
        session.commit()
        session.refresh(item)
        return item
    except ConnectorError as error:
        raise AppError(
            error.code,
            error.safe_message,
            status_code=409,
            retryable=error.retryable,
        ) from error
    except (TypeError, ValueError) as error:
        raise AppError(
            "saved_analysis_refresh_failed",
            "The saved analysis could not be refreshed safely",
            status_code=409,
        ) from error
    finally:
        if connector is not None:
            connector.close()


def get_saved_analysis(session: Session, analysis_id: UUID) -> tuple[SavedAnalysis, str]:
    item = _saved_analysis(session, analysis_id)
    datasource_name = session.scalar(
        select(Datasource.name).where(Datasource.id == item.datasource_id)
    )
    if datasource_name is None:
        raise AppError("datasource_not_found", "Datasource was not found", status_code=404)
    return item, datasource_name
