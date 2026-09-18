import re
from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field, SecretStr, field_validator

SCHEMA_NAME = re.compile(r"^[A-Za-z_][A-Za-z0-9_$]{0,62}$")


class PostgreSQLConnectionInput(BaseModel):
    source_type: Literal["postgresql"] = "postgresql"
    host: str = Field(min_length=1, max_length=255)
    port: int = Field(default=5432, ge=1, le=65535)
    database: str = Field(min_length=1, max_length=255)
    username: str = Field(min_length=1, max_length=255)
    password: SecretStr
    ssl_mode: Literal["disable", "prefer", "require", "verify-ca", "verify-full"] = "prefer"
    allowed_schemas: list[str] = Field(
        default_factory=lambda: ["public"], min_length=1, max_length=20
    )

    @field_validator("host", "database", "username")
    @classmethod
    def strip_required_value(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("Value must not be blank")
        return stripped

    @field_validator("allowed_schemas")
    @classmethod
    def validate_schemas(cls, value: list[str]) -> list[str]:
        normalized = list(dict.fromkeys(item.strip() for item in value))
        if not normalized or any(not SCHEMA_NAME.fullmatch(item) for item in normalized):
            raise ValueError("Allowed schemas must be valid PostgreSQL identifiers")
        return normalized


class DatasourceCreate(PostgreSQLConnectionInput):
    name: str = Field(min_length=1, max_length=120)

    @field_validator("name")
    @classmethod
    def strip_name(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("Connection name must not be blank")
        return stripped


class ConnectionTestResponse(BaseModel):
    status: Literal["ok"] = "ok"
    database: str
    server_version: str
    read_only_transaction: bool


class DatasourceSummary(BaseModel):
    id: UUID
    name: str
    source_type: str
    database_name: str
    safe_host: str
    port: int
    ssl_mode: str
    allowed_schemas: list[str]
    status: str
    is_active: bool
    entity_count: int
    relationship_count: int
    last_refreshed_at: datetime | None
    last_error_code: str | None
    created_at: datetime
    updated_at: datetime


class FieldSummary(BaseModel):
    id: UUID
    name: str
    native_type: str
    normalized_type: str
    nullable: bool
    ordinal: int
    primary_key: bool
    unique: bool


class EntitySummary(BaseModel):
    id: UUID
    schema_name: str
    name: str
    entity_type: str
    fields: list[FieldSummary]


class RelationshipSummary(BaseModel):
    id: UUID
    name: str
    source: str
    target: str


class DatasourceDetail(DatasourceSummary):
    entities: list[EntitySummary]
    relationships: list[RelationshipSummary]


class OnboardingStatusResponse(BaseModel):
    datasource_id: UUID
    status: str
    entity_count: int
    relationship_count: int
    last_refreshed_at: datetime | None
    last_error_code: str | None
