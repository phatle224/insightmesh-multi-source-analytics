from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from api.schemas.datasources import (
    ConnectionTestResponse,
    DatasourceCreate,
    DatasourceDetail,
    DatasourceSummary,
    OnboardingStatusResponse,
    PostgreSQLConnectionInput,
    SemanticManifestResponse,
)
from persistence.database import get_session
from services import datasources as service
from services import semantic_manifests

router = APIRouter(prefix="/api/v1/datasources", tags=["datasources"])
SessionDependency = Annotated[Session, Depends(get_session)]


@router.get("", response_model=list[DatasourceSummary])
def list_datasources(session: SessionDependency) -> list[DatasourceSummary]:
    return service.list_datasources(session)


@router.post("/test", response_model=ConnectionTestResponse)
def test_connection(payload: PostgreSQLConnectionInput) -> ConnectionTestResponse:
    return service.test_connection(payload)


@router.post("", response_model=DatasourceDetail, status_code=status.HTTP_201_CREATED)
def create_datasource(payload: DatasourceCreate, session: SessionDependency) -> DatasourceDetail:
    return service.create_datasource(session, payload)


@router.get("/{datasource_id}", response_model=DatasourceDetail)
def get_datasource(datasource_id: UUID, session: SessionDependency) -> DatasourceDetail:
    return service.get_datasource_detail(session, datasource_id)


@router.post("/{datasource_id}/activate", response_model=DatasourceDetail)
def activate_datasource(datasource_id: UUID, session: SessionDependency) -> DatasourceDetail:
    return service.activate_datasource(session, datasource_id)


@router.post("/{datasource_id}/refresh", response_model=DatasourceDetail)
def refresh_datasource(datasource_id: UUID, session: SessionDependency) -> DatasourceDetail:
    return service.refresh_datasource_by_id(session, datasource_id)


@router.get("/{datasource_id}/onboarding-status", response_model=OnboardingStatusResponse)
def get_onboarding_status(
    datasource_id: UUID, session: SessionDependency
) -> OnboardingStatusResponse:
    return service.onboarding_status(session, datasource_id)


@router.get("/{datasource_id}/semantic-manifest", response_model=SemanticManifestResponse)
def get_semantic_manifest(
    datasource_id: UUID, session: SessionDependency
) -> SemanticManifestResponse:
    return semantic_manifests.get_latest_semantic_manifest(session, datasource_id)
