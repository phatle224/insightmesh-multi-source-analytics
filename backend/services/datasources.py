import hashlib
import json
from dataclasses import asdict
from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import delete, func, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from api.errors import AppError
from api.schemas.datasources import (
    ConnectionTestResponse,
    DatasourceCreate,
    DatasourceDetail,
    DatasourceSummary,
    EntitySummary,
    FieldSummary,
    OnboardingStatusResponse,
    PostgreSQLConnectionInput,
    RelationshipSummary,
)
from api.settings import Settings, get_settings
from connectors.base import ConnectionConfig, ConnectorError, RawDataSourceMetadata
from connectors.postgres import PostgresConnector
from persistence.credentials import CredentialCipher, CredentialDecryptionError
from persistence.models import Datasource, DatasourceCredential, Entity, Field, Relationship


def _connector_error(error: ConnectorError) -> AppError:
    client_error = error.code in {"authentication_failed", "unsupported_configuration"}
    return AppError(
        error.code,
        error.safe_message,
        status_code=400 if client_error else 503,
        retryable=error.retryable,
    )


def _config_from_input(value: PostgreSQLConnectionInput) -> ConnectionConfig:
    return ConnectionConfig(
        host=value.host,
        port=value.port,
        database=value.database,
        username=value.username,
        password=value.password.get_secret_value(),
        ssl_mode=value.ssl_mode,
        allowed_schemas=tuple(value.allowed_schemas),
    )


def _connector(config: ConnectionConfig, settings: Settings) -> PostgresConnector:
    return PostgresConnector(
        config,
        connect_timeout_seconds=settings.datasource_connect_timeout_seconds,
        statement_timeout_ms=settings.datasource_statement_timeout_ms,
    )


def test_connection(
    payload: PostgreSQLConnectionInput, settings: Settings | None = None
) -> ConnectionTestResponse:
    app_settings = settings or get_settings()
    connector = _connector(_config_from_input(payload), app_settings)
    try:
        result = connector.test_connection()
    except ConnectorError as exc:
        raise _connector_error(exc) from None
    finally:
        connector.close()
    return ConnectionTestResponse(
        database=result.database,
        server_version=result.server_version,
        read_only_transaction=result.read_only_transaction,
    )


def _credential_cipher(settings: Settings) -> CredentialCipher:
    return CredentialCipher(settings.credential_encryption_key.get_secret_value())


def _load_config(session: Session, datasource: Datasource, settings: Settings) -> ConnectionConfig:
    stored = session.get(DatasourceCredential, datasource.id)
    if stored is None:
        raise AppError(
            "credentials_missing", "Datasource credentials are unavailable", status_code=409
        )
    try:
        credentials = _credential_cipher(settings).decrypt(stored.encrypted_payload)
        username = credentials["username"]
        password = credentials["password"]
    except (CredentialDecryptionError, KeyError):
        raise AppError(
            "credentials_unavailable", "Datasource credentials are unavailable", status_code=500
        ) from None
    if not isinstance(username, str) or not isinstance(password, str):
        raise AppError(
            "credentials_unavailable", "Datasource credentials are unavailable", status_code=500
        )
    return ConnectionConfig(
        host=datasource.safe_host,
        port=datasource.port,
        database=datasource.database_name,
        username=username,
        password=password,
        ssl_mode=datasource.ssl_mode,
        allowed_schemas=tuple(datasource.allowed_schemas),
    )


def _metadata_hash(metadata: RawDataSourceMetadata) -> str:
    serialized = json.dumps(asdict(metadata), sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(serialized.encode()).hexdigest()


def _replace_metadata(
    session: Session, datasource: Datasource, metadata: RawDataSourceMetadata
) -> None:
    session.execute(delete(Entity).where(Entity.datasource_id == datasource.id))
    session.flush()
    entity_map: dict[tuple[str, str], Entity] = {}
    field_map: dict[tuple[str, str, str], Field] = {}
    for raw_entity in metadata.entities:
        entity = Entity(
            datasource_id=datasource.id,
            schema_name=raw_entity.schema_name,
            name=raw_entity.name,
            entity_type=raw_entity.entity_type,
            metadata_json={},
        )
        session.add(entity)
        session.flush()
        entity_map[(raw_entity.schema_name, raw_entity.name)] = entity
        for raw_field in raw_entity.fields:
            field = Field(
                entity_id=entity.id,
                name=raw_field.name,
                native_type=raw_field.native_type,
                normalized_type=raw_field.normalized_type,
                nullable=raw_field.nullable,
                ordinal=raw_field.ordinal,
                metadata_json={
                    "primary_key": raw_field.primary_key,
                    "unique": raw_field.unique,
                },
            )
            session.add(field)
            session.flush()
            field_map[(raw_entity.schema_name, raw_entity.name, raw_field.name)] = field
    for raw_relationship in metadata.relationships:
        source_entity = entity_map.get(
            (raw_relationship.source_schema, raw_relationship.source_entity)
        )
        target_entity = entity_map.get(
            (raw_relationship.target_schema, raw_relationship.target_entity)
        )
        source_field = field_map.get(
            (
                raw_relationship.source_schema,
                raw_relationship.source_entity,
                raw_relationship.source_field,
            )
        )
        target_field = field_map.get(
            (
                raw_relationship.target_schema,
                raw_relationship.target_entity,
                raw_relationship.target_field,
            )
        )
        if source_entity and target_entity:
            session.add(
                Relationship(
                    datasource_id=datasource.id,
                    source_entity_id=source_entity.id,
                    target_entity_id=target_entity.id,
                    source_field_id=source_field.id if source_field else None,
                    target_field_id=target_field.id if target_field else None,
                    relationship_type="foreign_key",
                    confidence=1.0,
                    source="introspection",
                )
            )


def refresh_datasource(
    session: Session, datasource: Datasource, settings: Settings | None = None
) -> DatasourceDetail:
    app_settings = settings or get_settings()
    datasource.status = "introspecting"
    datasource.last_error_code = None
    session.commit()
    connector = _connector(_load_config(session, datasource, app_settings), app_settings)
    try:
        metadata = connector.introspect()
        _replace_metadata(session, datasource, metadata)
        datasource.metadata_hash = _metadata_hash(metadata)
        datasource.last_refreshed_at = datetime.now(UTC)
        datasource.last_error_code = None
        datasource.status = "ready"
        session.commit()
    except ConnectorError as exc:
        session.rollback()
        datasource = _get_datasource(session, datasource.id)
        datasource.status = "failed"
        datasource.last_error_code = exc.code
        session.commit()
    finally:
        connector.close()
    return get_datasource_detail(session, datasource.id)


def refresh_datasource_by_id(
    session: Session, datasource_id: UUID, settings: Settings | None = None
) -> DatasourceDetail:
    return refresh_datasource(session, _get_datasource(session, datasource_id), settings)


def create_datasource(
    session: Session, payload: DatasourceCreate, settings: Settings | None = None
) -> DatasourceDetail:
    app_settings = settings or get_settings()
    test_connection(payload, app_settings)
    datasource = Datasource(
        name=payload.name,
        source_type=payload.source_type,
        database_name=payload.database,
        safe_host=payload.host,
        port=payload.port,
        ssl_mode=payload.ssl_mode,
        allowed_schemas=payload.allowed_schemas,
        status="introspecting",
    )
    session.add(datasource)
    try:
        session.flush()
        encrypted = _credential_cipher(app_settings).encrypt(
            {"username": payload.username, "password": payload.password.get_secret_value()}
        )
        session.add(DatasourceCredential(datasource_id=datasource.id, encrypted_payload=encrypted))
        session.commit()
    except IntegrityError:
        session.rollback()
        raise AppError(
            "datasource_name_conflict",
            "A datasource with this name already exists",
            status_code=409,
        ) from None
    return refresh_datasource(session, datasource, app_settings)


def _get_datasource(session: Session, datasource_id: UUID) -> Datasource:
    datasource = session.get(Datasource, datasource_id)
    if datasource is None:
        raise AppError("datasource_not_found", "Datasource was not found", status_code=404)
    return datasource


def _counts(session: Session, datasource_id: UUID) -> tuple[int, int]:
    entity_count = session.scalar(
        select(func.count()).select_from(Entity).where(Entity.datasource_id == datasource_id)
    )
    relationship_count = session.scalar(
        select(func.count())
        .select_from(Relationship)
        .where(Relationship.datasource_id == datasource_id)
    )
    return int(entity_count or 0), int(relationship_count or 0)


def _summary(session: Session, datasource: Datasource) -> DatasourceSummary:
    entity_count, relationship_count = _counts(session, datasource.id)
    return DatasourceSummary(
        id=datasource.id,
        name=datasource.name,
        source_type=datasource.source_type,
        database_name=datasource.database_name,
        safe_host=datasource.safe_host,
        port=datasource.port,
        ssl_mode=datasource.ssl_mode,
        allowed_schemas=list(datasource.allowed_schemas),
        status=datasource.status,
        is_active=datasource.is_active,
        entity_count=entity_count,
        relationship_count=relationship_count,
        last_refreshed_at=datasource.last_refreshed_at,
        last_error_code=datasource.last_error_code,
        created_at=datasource.created_at,
        updated_at=datasource.updated_at,
    )


def list_datasources(session: Session) -> list[DatasourceSummary]:
    datasources = session.scalars(select(Datasource).order_by(Datasource.created_at.desc())).all()
    return [_summary(session, datasource) for datasource in datasources]


def get_datasource_detail(session: Session, datasource_id: UUID) -> DatasourceDetail:
    datasource = _get_datasource(session, datasource_id)
    summary = _summary(session, datasource)
    entities = session.scalars(
        select(Entity)
        .where(Entity.datasource_id == datasource_id)
        .order_by(Entity.schema_name, Entity.name)
    ).all()
    entity_by_id = {entity.id: entity for entity in entities}
    fields = session.scalars(
        select(Field)
        .join(Entity, Field.entity_id == Entity.id)
        .where(Entity.datasource_id == datasource_id)
        .order_by(Field.entity_id, Field.ordinal)
    ).all()
    fields_by_entity: dict[UUID, list[Field]] = {}
    for field in fields:
        fields_by_entity.setdefault(field.entity_id, []).append(field)
    entity_responses = [
        EntitySummary(
            id=entity.id,
            schema_name=entity.schema_name,
            name=entity.name,
            entity_type=entity.entity_type,
            fields=[
                FieldSummary(
                    id=field.id,
                    name=field.name,
                    native_type=field.native_type,
                    normalized_type=field.normalized_type,
                    nullable=field.nullable,
                    ordinal=field.ordinal,
                    primary_key=bool(field.metadata_json.get("primary_key")),
                    unique=bool(field.metadata_json.get("unique")),
                )
                for field in fields_by_entity.get(entity.id, [])
            ],
        )
        for entity in entities
    ]
    relationships = session.scalars(
        select(Relationship).where(Relationship.datasource_id == datasource_id)
    ).all()
    relationship_responses: list[RelationshipSummary] = []
    for relationship in relationships:
        source_entity = entity_by_id.get(relationship.source_entity_id)
        target_entity = entity_by_id.get(relationship.target_entity_id)
        if source_entity and target_entity:
            relationship_responses.append(
                RelationshipSummary(
                    id=relationship.id,
                    name="foreign_key",
                    source=f"{source_entity.schema_name}.{source_entity.name}",
                    target=f"{target_entity.schema_name}.{target_entity.name}",
                )
            )
    return DatasourceDetail(
        **summary.model_dump(),
        entities=entity_responses,
        relationships=relationship_responses,
    )


def activate_datasource(session: Session, datasource_id: UUID) -> DatasourceDetail:
    datasource = _get_datasource(session, datasource_id)
    if datasource.status != "ready":
        raise AppError(
            "datasource_not_ready", "Only a ready datasource can be activated", status_code=409
        )
    session.execute(update(Datasource).values(is_active=False))
    datasource.is_active = True
    session.commit()
    return get_datasource_detail(session, datasource_id)


def onboarding_status(session: Session, datasource_id: UUID) -> OnboardingStatusResponse:
    datasource = _get_datasource(session, datasource_id)
    entity_count, relationship_count = _counts(session, datasource_id)
    return OnboardingStatusResponse(
        datasource_id=datasource.id,
        status=datasource.status,
        entity_count=entity_count,
        relationship_count=relationship_count,
        last_refreshed_at=datasource.last_refreshed_at,
        last_error_code=datasource.last_error_code,
    )
