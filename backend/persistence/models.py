"""Canonical V1 persistence schema. No datasource secret is exposed by these domain rows."""

from datetime import datetime
from typing import Any
from uuid import UUID, uuid4

from pgvector.sqlalchemy import Vector
from sqlalchemy import (
    JSON,
    BigInteger,
    Boolean,
    CheckConstraint,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    LargeBinary,
    String,
    Text,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from persistence.base import Base

JsonObject = dict[str, Any]


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class Datasource(TimestampMixin, Base):
    __tablename__ = "datasources"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    name: Mapped[str] = mapped_column(String(120), unique=True)
    source_type: Mapped[str] = mapped_column(String(24))
    database_name: Mapped[str] = mapped_column(String(255))
    safe_host: Mapped[str] = mapped_column(String(255))
    port: Mapped[int] = mapped_column(Integer)
    ssl_mode: Mapped[str] = mapped_column(String(16), default="prefer")
    allowed_schemas: Mapped[list[str]] = mapped_column(JSONB, default=lambda: ["public"])
    status: Mapped[str] = mapped_column(String(32), default="draft")
    is_active: Mapped[bool] = mapped_column(Boolean, default=False)
    metadata_hash: Mapped[str | None] = mapped_column(String(64))
    profile_hash: Mapped[str | None] = mapped_column(String(64))
    semantic_status: Mapped[str] = mapped_column(String(32), default="not_configured")
    semantic_error_code: Mapped[str | None] = mapped_column(String(80))
    last_refreshed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_error_code: Mapped[str | None] = mapped_column(String(80))

    __table_args__ = (
        CheckConstraint("source_type IN ('postgresql', 'mysql', 'mongodb')", name="source_type"),
        CheckConstraint("port > 0 AND port <= 65535", name="port"),
        CheckConstraint(
            "ssl_mode IN ('disable', 'prefer', 'require', 'verify-ca', 'verify-full')",
            name="ssl_mode",
        ),
        Index(
            "uq_datasources_one_active",
            "is_active",
            unique=True,
            postgresql_where=text("is_active"),
        ),
    )


class DatasourceCredential(Base):
    __tablename__ = "datasource_credentials"

    datasource_id: Mapped[UUID] = mapped_column(
        ForeignKey("datasources.id", ondelete="CASCADE"), primary_key=True
    )
    encrypted_payload: Mapped[bytes] = mapped_column(LargeBinary)
    key_id: Mapped[str] = mapped_column(String(80), default="local-v1")
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class Entity(TimestampMixin, Base):
    __tablename__ = "entities"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    datasource_id: Mapped[UUID] = mapped_column(ForeignKey("datasources.id", ondelete="CASCADE"))
    schema_name: Mapped[str] = mapped_column(String(255), default="public")
    name: Mapped[str] = mapped_column(String(255))
    entity_type: Mapped[str] = mapped_column(String(32))
    description: Mapped[str | None] = mapped_column(Text)
    metadata_json: Mapped[JsonObject] = mapped_column(JSONB, default=dict)

    __table_args__ = (UniqueConstraint("datasource_id", "schema_name", "name"),)


class Field(TimestampMixin, Base):
    __tablename__ = "fields"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    entity_id: Mapped[UUID] = mapped_column(ForeignKey("entities.id", ondelete="CASCADE"))
    name: Mapped[str] = mapped_column(String(255))
    native_type: Mapped[str] = mapped_column(String(255))
    normalized_type: Mapped[str] = mapped_column(String(32))
    nullable: Mapped[bool] = mapped_column(Boolean)
    ordinal: Mapped[int] = mapped_column(Integer)
    description: Mapped[str | None] = mapped_column(Text)
    metadata_json: Mapped[JsonObject] = mapped_column(JSONB, default=dict)

    __table_args__ = (UniqueConstraint("entity_id", "name"),)


class Relationship(Base):
    __tablename__ = "relationships"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    datasource_id: Mapped[UUID] = mapped_column(ForeignKey("datasources.id", ondelete="CASCADE"))
    source_entity_id: Mapped[UUID] = mapped_column(ForeignKey("entities.id", ondelete="CASCADE"))
    target_entity_id: Mapped[UUID] = mapped_column(ForeignKey("entities.id", ondelete="CASCADE"))
    source_field_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("fields.id", ondelete="SET NULL")
    )
    target_field_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("fields.id", ondelete="SET NULL")
    )
    relationship_type: Mapped[str] = mapped_column(String(40))
    confidence: Mapped[float] = mapped_column(Float, default=1.0)
    source: Mapped[str] = mapped_column(String(40), default="introspection")

    __table_args__ = (CheckConstraint("confidence >= 0 AND confidence <= 1", name="confidence"),)


class ProfileStatistic(Base):
    __tablename__ = "profile_statistics"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    field_id: Mapped[UUID] = mapped_column(ForeignKey("fields.id", ondelete="CASCADE"))
    statistics: Mapped[JsonObject] = mapped_column(JSONB)
    profile_hash: Mapped[str] = mapped_column(String(64))
    sample_size: Mapped[int | None] = mapped_column(BigInteger)
    sampled_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (UniqueConstraint("field_id"),)


class SemanticTerm(Base):
    __tablename__ = "semantic_terms"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    datasource_id: Mapped[UUID] = mapped_column(ForeignKey("datasources.id", ondelete="CASCADE"))
    entity_id: Mapped[UUID | None] = mapped_column(ForeignKey("entities.id", ondelete="CASCADE"))
    field_id: Mapped[UUID | None] = mapped_column(ForeignKey("fields.id", ondelete="CASCADE"))
    term: Mapped[str] = mapped_column(String(255))
    description: Mapped[str | None] = mapped_column(Text)
    confidence: Mapped[float] = mapped_column(Float)
    source: Mapped[str] = mapped_column(String(40))
    generated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    __table_args__ = (CheckConstraint("confidence >= 0 AND confidence <= 1", name="confidence"),)


class MetricCandidate(Base):
    __tablename__ = "metric_candidates"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    datasource_id: Mapped[UUID] = mapped_column(ForeignKey("datasources.id", ondelete="CASCADE"))
    entity_id: Mapped[UUID | None] = mapped_column(ForeignKey("entities.id", ondelete="CASCADE"))
    name: Mapped[str] = mapped_column(String(255))
    expression: Mapped[str] = mapped_column(Text)
    description: Mapped[str | None] = mapped_column(Text)
    confidence: Mapped[float] = mapped_column(Float)
    source: Mapped[str] = mapped_column(String(40))
    metadata_json: Mapped[JsonObject] = mapped_column(JSONB, default=dict)

    __table_args__ = (CheckConstraint("confidence >= 0 AND confidence <= 1", name="confidence"),)


class QueryExample(Base):
    __tablename__ = "query_examples"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    datasource_id: Mapped[UUID] = mapped_column(ForeignKey("datasources.id", ondelete="CASCADE"))
    question: Mapped[str] = mapped_column(Text)
    native_query: Mapped[str] = mapped_column(Text)
    query_type: Mapped[str] = mapped_column(String(24))
    validated: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Embedding(Base):
    __tablename__ = "embeddings"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    datasource_id: Mapped[UUID] = mapped_column(ForeignKey("datasources.id", ondelete="CASCADE"))
    object_type: Mapped[str] = mapped_column(String(40))
    object_id: Mapped[UUID] = mapped_column(index=True)
    content: Mapped[str] = mapped_column(Text)
    embedding: Mapped[list[float]] = mapped_column(Vector())
    metadata_json: Mapped[JsonObject] = mapped_column(JSONB, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (UniqueConstraint("datasource_id", "object_type", "object_id"),)


class SemanticManifest(Base):
    __tablename__ = "semantic_manifests"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    datasource_id: Mapped[UUID] = mapped_column(ForeignKey("datasources.id", ondelete="CASCADE"))
    version: Mapped[int] = mapped_column(Integer)
    manifest_hash: Mapped[str] = mapped_column(String(64))
    metadata_hash: Mapped[str] = mapped_column(String(64))
    profile_hash: Mapped[str] = mapped_column(String(64))
    configuration_json: Mapped[JsonObject] = mapped_column(JSONB)
    manifest_json: Mapped[JsonObject] = mapped_column(JSONB)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        UniqueConstraint(
            "datasource_id", "version", name="uq_semantic_manifests_datasource_version"
        ),
        UniqueConstraint(
            "datasource_id", "manifest_hash", name="uq_semantic_manifests_datasource_hash"
        ),
        CheckConstraint("version > 0", name="version"),
        Index("ix_semantic_manifests_datasource_created", "datasource_id", "created_at"),
    )


class QueryRun(Base):
    __tablename__ = "query_runs"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    datasource_id: Mapped[UUID] = mapped_column(ForeignKey("datasources.id", ondelete="CASCADE"))
    question: Mapped[str] = mapped_column(Text)
    retrieved_context_ids: Mapped[list[str]] = mapped_column(JSON, default=list)
    generated_query: Mapped[JsonObject] = mapped_column(JSONB, default=dict)
    query_type: Mapped[str] = mapped_column(String(24))
    validation_result: Mapped[JsonObject] = mapped_column(JSONB, default=dict)
    status: Mapped[str] = mapped_column(String(40))
    row_count: Mapped[int | None] = mapped_column(BigInteger)
    duration_ms: Mapped[int | None] = mapped_column(Integer)
    repair_count: Mapped[int] = mapped_column(Integer, default=0)
    provider_call_count: Mapped[int] = mapped_column(Integer, default=0)
    visualization_type: Mapped[str | None] = mapped_column(String(40))
    error_code: Mapped[str | None] = mapped_column(String(80))
    error_message: Mapped[str | None] = mapped_column(Text)
    result_json: Mapped[JsonObject | None] = mapped_column(JSONB)
    trace_json: Mapped[list[JsonObject]] = mapped_column(JSONB, default=list)
    warnings: Mapped[list[str]] = mapped_column(JSONB, default=list)
    artifacts_expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        CheckConstraint("repair_count >= 0 AND repair_count <= 2", name="repair_count"),
        CheckConstraint("provider_call_count >= 0", name="provider_call_count"),
        Index(
            "ix_query_runs_artifacts_expires_at",
            "artifacts_expires_at",
            postgresql_where=text("result_json IS NOT NULL OR trace_json <> '[]'::jsonb"),
        ),
        Index("ix_query_runs_expires_at", "expires_at"),
        Index("ix_query_runs_datasource_created", "datasource_id", "created_at", "id"),
    )


class SavedAnalysis(TimestampMixin, Base):
    """A user-facing query and result snapshot that survives query-run retention."""

    __tablename__ = "saved_analyses"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    datasource_id: Mapped[UUID] = mapped_column(ForeignKey("datasources.id", ondelete="CASCADE"))
    name: Mapped[str] = mapped_column(String(160))
    description: Mapped[str | None] = mapped_column(Text)
    question: Mapped[str] = mapped_column(Text)
    validated_query: Mapped[JsonObject] = mapped_column(JSONB)
    query_type: Mapped[str] = mapped_column(String(24))
    visualization_type: Mapped[str | None] = mapped_column(String(40))
    result_json: Mapped[JsonObject | None] = mapped_column(JSONB)
    tags: Mapped[list[str]] = mapped_column(JSONB, default=list)
    source_query_run_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("query_runs.id", ondelete="SET NULL")
    )

    __table_args__ = (
        Index("ix_saved_analyses_datasource_updated", "datasource_id", "updated_at"),
    )


class Dashboard(TimestampMixin, Base):
    __tablename__ = "dashboards"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    name: Mapped[str] = mapped_column(String(160))
    description: Mapped[str | None] = mapped_column(Text)


class DashboardWidget(TimestampMixin, Base):
    __tablename__ = "dashboard_widgets"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    dashboard_id: Mapped[UUID] = mapped_column(ForeignKey("dashboards.id", ondelete="CASCADE"))
    datasource_id: Mapped[UUID] = mapped_column(ForeignKey("datasources.id", ondelete="RESTRICT"))
    title: Mapped[str] = mapped_column(String(160))
    question: Mapped[str] = mapped_column(Text)
    validated_query: Mapped[JsonObject] = mapped_column(JSONB)
    query_type: Mapped[str] = mapped_column(String(24))
    chart_type: Mapped[str] = mapped_column(String(40))
    chart_config: Mapped[JsonObject] = mapped_column(JSONB, default=dict)
    position: Mapped[int] = mapped_column(Integer)
    source_query_run_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("query_runs.id", ondelete="SET NULL")
    )
    result_json: Mapped[JsonObject | None] = mapped_column(JSONB)
    status: Mapped[str] = mapped_column(String(24), default="ready")
    row_count: Mapped[int | None] = mapped_column(BigInteger)
    duration_ms: Mapped[int | None] = mapped_column(Integer)
    last_refreshed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_error_code: Mapped[str | None] = mapped_column(String(80))
    last_error_message: Mapped[str | None] = mapped_column(Text)

    __table_args__ = (
        UniqueConstraint("dashboard_id", "position"),
        CheckConstraint("status IN ('ready', 'empty', 'stale', 'failed')", name="status"),
    )
