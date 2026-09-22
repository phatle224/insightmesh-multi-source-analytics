"""Durable, user-facing query definitions independent of query-run retention."""

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from api.errors import AppError
from api.schemas.saved_analyses import SavedAnalysisCreate, SavedAnalysisUpdate
from persistence.models import Datasource, QueryRun, SavedAnalysis


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


def get_saved_analysis(session: Session, analysis_id: UUID) -> tuple[SavedAnalysis, str]:
    item = _saved_analysis(session, analysis_id)
    datasource_name = session.scalar(
        select(Datasource.name).where(Datasource.id == item.datasource_id)
    )
    if datasource_name is None:
        raise AppError("datasource_not_found", "Datasource was not found", status_code=404)
    return item, datasource_name
