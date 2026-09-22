from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Response
from sqlalchemy.orm import Session

from api.schemas.saved_analyses import (
    SavedAnalysisCreate,
    SavedAnalysisResponse,
    SavedAnalysisUpdate,
    saved_analysis_response,
)
from persistence.database import get_session
from services import saved_analyses as saved_analysis_service

router = APIRouter(prefix="/api/v1/saved-analyses", tags=["saved-analyses"])
SessionDependency = Annotated[Session, Depends(get_session)]


@router.get("", response_model=list[SavedAnalysisResponse])
def list_saved_analyses(session: SessionDependency) -> list[SavedAnalysisResponse]:
    return [
        saved_analysis_response(item, datasource_name)
        for item, datasource_name in saved_analysis_service.list_saved_analyses(session)
    ]


@router.post("", response_model=SavedAnalysisResponse, status_code=201)
def create_saved_analysis(
    payload: SavedAnalysisCreate, session: SessionDependency
) -> SavedAnalysisResponse:
    item = saved_analysis_service.create_saved_analysis(session, payload)
    _, datasource_name = saved_analysis_service.get_saved_analysis(session, item.id)
    return saved_analysis_response(item, datasource_name)


@router.get("/{analysis_id}", response_model=SavedAnalysisResponse)
def get_saved_analysis(analysis_id: UUID, session: SessionDependency) -> SavedAnalysisResponse:
    item, datasource_name = saved_analysis_service.get_saved_analysis(session, analysis_id)
    return saved_analysis_response(item, datasource_name)


@router.patch("/{analysis_id}", response_model=SavedAnalysisResponse)
def update_saved_analysis(
    analysis_id: UUID,
    payload: SavedAnalysisUpdate,
    session: SessionDependency,
) -> SavedAnalysisResponse:
    item = saved_analysis_service.update_saved_analysis(session, analysis_id, payload)
    _, datasource_name = saved_analysis_service.get_saved_analysis(session, analysis_id)
    return saved_analysis_response(item, datasource_name)


@router.delete("/{analysis_id}", status_code=204)
def delete_saved_analysis(analysis_id: UUID, session: SessionDependency) -> Response:
    saved_analysis_service.delete_saved_analysis(session, analysis_id)
    return Response(status_code=204)
