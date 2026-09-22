from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field, field_validator

from persistence.models import SavedAnalysis


class SavedAnalysisCreate(BaseModel):
    query_run_id: UUID
    name: str = Field(min_length=1, max_length=160)
    description: str | None = Field(default=None, max_length=1_000)
    tags: list[str] = Field(default_factory=list, max_length=12)

    @field_validator("name")
    @classmethod
    def strip_name(cls, value: str) -> str:
        if not (clean := value.strip()):
            raise ValueError("Saved analysis name must not be blank")
        return clean

    @field_validator("description")
    @classmethod
    def strip_description(cls, value: str | None) -> str | None:
        return value.strip() if value and value.strip() else None

    @field_validator("tags")
    @classmethod
    def normalize_tags(cls, value: list[str]) -> list[str]:
        normalized = []
        for tag in value:
            clean = tag.strip().lower()
            if clean and clean not in normalized:
                normalized.append(clean)
        return normalized


class SavedAnalysisUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=160)
    description: str | None = Field(default=None, max_length=1_000)
    tags: list[str] | None = Field(default=None, max_length=12)

    @field_validator("name")
    @classmethod
    def strip_name(cls, value: str | None) -> str | None:
        if value is None:
            return None
        if not (clean := value.strip()):
            raise ValueError("Saved analysis name must not be blank")
        return clean

    @field_validator("description")
    @classmethod
    def strip_description(cls, value: str | None) -> str | None:
        return value.strip() if value and value.strip() else None

    @field_validator("tags")
    @classmethod
    def normalize_tags(cls, value: list[str] | None) -> list[str] | None:
        if value is None:
            return None
        normalized = []
        for tag in value:
            clean = tag.strip().lower()
            if clean and clean not in normalized:
                normalized.append(clean)
        return normalized


class SavedAnalysisResponse(BaseModel):
    id: UUID
    datasource_id: UUID
    datasource_name: str
    name: str
    description: str | None
    question: str
    validated_query: dict[str, Any]
    query_type: str
    visualization_type: str | None
    result: dict[str, Any] | None
    tags: list[str]
    source_query_run_id: UUID | None
    created_at: datetime
    updated_at: datetime


def saved_analysis_response(item: SavedAnalysis, datasource_name: str) -> SavedAnalysisResponse:
    return SavedAnalysisResponse(
        id=item.id,
        datasource_id=item.datasource_id,
        datasource_name=datasource_name,
        name=item.name,
        description=item.description,
        question=item.question,
        validated_query=item.validated_query,
        query_type=item.query_type,
        visualization_type=item.visualization_type,
        result=item.result_json,
        tags=item.tags,
        source_query_run_id=item.source_query_run_id,
        created_at=item.created_at,
        updated_at=item.updated_at,
    )
