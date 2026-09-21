from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field


class RetrievalRequest(BaseModel):
    datasource_id: UUID
    question: str = Field(min_length=3, max_length=1_000)
    top_k: int | None = Field(default=None, ge=1, le=10)


class RetrievedField(BaseModel):
    id: UUID
    name: str
    native_type: str
    normalized_type: str
    description: str | None
    primary_key: bool
    unique: bool
    profile: dict[str, object] | None


class RetrievedMetric(BaseModel):
    id: UUID
    name: str
    expression: str
    description: str | None
    confidence: float


class RetrievedEntity(BaseModel):
    id: UUID
    schema_name: str
    name: str
    description: str | None
    selection_source: Literal["semantic", "lexical", "hybrid", "relationship_expansion"]
    similarity: float | None
    lexical_score: float | None = None
    semantic_score: float | None = None
    fused_score: float | None = None
    business_terms: list[str]
    fields: list[RetrievedField]
    metrics: list[RetrievedMetric]


class RetrievedRelationship(BaseModel):
    id: UUID
    source_entity_id: UUID
    source: str
    source_field: str | None
    target_entity_id: UUID
    target: str
    target_field: str | None
    relationship_type: str


class RetrievalResponse(BaseModel):
    run_id: UUID
    datasource_id: UUID
    question: str
    top_k: int
    strategy: Literal["vector", "hybrid"]
    config_version: str
    context_ids: list[str]
    entities: list[RetrievedEntity]
    relationships: list[RetrievedRelationship]
