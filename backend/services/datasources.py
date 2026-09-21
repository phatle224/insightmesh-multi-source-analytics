import hashlib
import json
from dataclasses import asdict
from datetime import UTC, datetime
from uuid import UUID

from pydantic import ValidationError
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
from connectors.base import (
    ConnectionConfig,
    ConnectorError,
    ProfileResult,
    ProfilingPolicy,
    RawDataSourceMetadata,
)
from connectors.postgres import PostgresConnector
from persistence.credentials import CredentialCipher, CredentialDecryptionError
from persistence.models import (
    Datasource,
    DatasourceCredential,
    Embedding,
    Entity,
    Field,
    MetricCandidate,
    ProfileStatistic,
    Relationship,
    SemanticTerm,
)
from semantic.enrichment import enrich_entity
from semantic.privacy import is_possible_pii
from semantic.provider import (
    FallbackProvider,
    GeminiProvider,
    LLMProvider,
    OpenRouterProvider,
    ProviderError,
)
from services.semantic_manifests import create_semantic_manifest_snapshot


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


def build_datasource_connector(
    session: Session,
    datasource: Datasource,
    settings: Settings,
) -> PostgresConnector:
    if datasource.source_type != "postgresql":
        raise AppError(
            "datasource_type_unsupported",
            "The datasource type is not supported by this query runtime",
            status_code=409,
        )
    return _connector(_load_config(session, datasource, settings), settings)


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


def _sync_metadata(
    session: Session, datasource: Datasource, metadata: RawDataSourceMetadata
) -> None:
    existing_entities = {
        (item.schema_name, item.name): item
        for item in session.scalars(
            select(Entity).where(Entity.datasource_id == datasource.id)
        ).all()
    }
    desired_entities = {(item.schema_name, item.name) for item in metadata.entities}
    for key, entity in existing_entities.items():
        if key not in desired_entities:
            session.delete(entity)
    session.flush()
    entity_map: dict[tuple[str, str], Entity] = {}
    field_map: dict[tuple[str, str, str], Field] = {}
    for raw_entity in metadata.entities:
        entity_key = (raw_entity.schema_name, raw_entity.name)
        stored_entity = existing_entities.get(entity_key)
        if stored_entity is None:
            stored_entity = Entity(
                datasource_id=datasource.id,
                schema_name=raw_entity.schema_name,
                name=raw_entity.name,
                entity_type=raw_entity.entity_type,
                metadata_json={},
            )
            session.add(stored_entity)
        else:
            stored_entity.entity_type = raw_entity.entity_type
        session.flush()
        entity_map[entity_key] = stored_entity
        existing_fields = {
            item.name: item
            for item in session.scalars(
                select(Field).where(Field.entity_id == stored_entity.id)
            ).all()
        }
        desired_fields = {item.name for item in raw_entity.fields}
        for name, stored_field in existing_fields.items():
            if name not in desired_fields:
                session.delete(stored_field)
        for raw_field in raw_entity.fields:
            field = existing_fields.get(raw_field.name)
            metadata_json = {
                "primary_key": raw_field.primary_key,
                "unique": raw_field.unique,
            }
            if field is None:
                field = Field(
                    entity_id=stored_entity.id,
                    name=raw_field.name,
                    native_type=raw_field.native_type,
                    normalized_type=raw_field.normalized_type,
                    nullable=raw_field.nullable,
                    ordinal=raw_field.ordinal,
                    metadata_json=metadata_json,
                )
                session.add(field)
            else:
                field.native_type = raw_field.native_type
                field.normalized_type = raw_field.normalized_type
                field.nullable = raw_field.nullable
                field.ordinal = raw_field.ordinal
                field.metadata_json = metadata_json
            session.flush()
            field_map[(raw_entity.schema_name, raw_entity.name, raw_field.name)] = field
    session.execute(delete(Relationship).where(Relationship.datasource_id == datasource.id))
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


def _hash_json(value: object) -> str:
    serialized = json.dumps(value, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(serialized.encode()).hexdigest()


def _persist_profiles(
    session: Session, datasource: Datasource, profiles: ProfileResult
) -> dict[tuple[str, str, str], ProfileStatistic]:
    fields = session.execute(
        select(Field, Entity)
        .join(Entity, Field.entity_id == Entity.id)
        .where(Entity.datasource_id == datasource.id)
    ).all()
    field_map = {(entity.schema_name, entity.name, field.name): field for field, entity in fields}
    stored = {
        item.field_id: item
        for item in session.scalars(
            select(ProfileStatistic)
            .join(Field, ProfileStatistic.field_id == Field.id)
            .join(Entity, Field.entity_id == Entity.id)
            .where(Entity.datasource_id == datasource.id)
        ).all()
    }
    result: dict[tuple[str, str, str], ProfileStatistic] = {}
    now = datetime.now(UTC)
    for profile in profiles.fields:
        key = (profile.schema_name, profile.entity_name, profile.field_name)
        field = field_map.get(key)
        if field is None:
            continue
        profile_hash = _hash_json(
            {"sample_size": profile.sample_size, "statistics": profile.statistics}
        )
        statistic = stored.get(field.id)
        if statistic is None:
            statistic = ProfileStatistic(field_id=field.id)
            session.add(statistic)
        statistic.statistics = profile.statistics
        statistic.profile_hash = profile_hash
        statistic.sample_size = profile.sample_size
        statistic.sampled_at = now
        result[key] = statistic
    session.flush()
    datasource.profile_hash = _hash_json(
        [
            {
                "field": list(key),
                "hash": result[key].profile_hash,
            }
            for key in sorted(result)
        ]
    )
    return result


def _openrouter_provider(
    settings: Settings, *, model: str | None = None
) -> OpenRouterProvider | None:
    if settings.openrouter_api_key is None:
        return None
    key = settings.openrouter_api_key.get_secret_value().strip()
    if not key:
        return None
    return OpenRouterProvider(
        api_key=key,
        base_url=settings.openrouter_base_url,
        llm_model=model or settings.llm_fallback_model,
        embedding_model=settings.embedding_model,
        embedding_dimensions=settings.embedding_dimensions,
        timeout_seconds=settings.provider_timeout_seconds,
    )


def build_embedding_provider(settings: Settings) -> LLMProvider | None:
    """Build the dedicated embedding boundary without requiring an LLM key."""
    return _openrouter_provider(settings)


def build_semantic_provider(settings: Settings) -> LLMProvider | None:
    fallback = (
        _openrouter_provider(settings)
        if settings.llm_fallback_provider == "openrouter"
        else None
    )
    if settings.llm_provider == "gemini":
        if settings.gemini_api_key is None:
            if fallback is not None:
                fallback.close()
            return None
        key = settings.gemini_api_key.get_secret_value().strip()
        if not key:
            if fallback is not None:
                fallback.close()
            return None
        primary = GeminiProvider(
            api_key=key,
            base_url=settings.gemini_base_url,
            model=settings.gemini_model,
            timeout_seconds=settings.provider_timeout_seconds,
        )
        return FallbackProvider(primary, fallback)
    if settings.llm_provider == "openrouter":
        openrouter_primary = _openrouter_provider(settings, model=settings.llm_model)
        if openrouter_primary is None:
            return None
        if fallback is not None:
            fallback.close()
        return openrouter_primary
    if fallback is not None:
        fallback.close()
    return None


def _refresh_semantic_index(
    session: Session,
    datasource: Datasource,
    profiles: dict[tuple[str, str, str], ProfileStatistic],
    settings: Settings,
) -> None:
    provider = build_semantic_provider(settings)
    if provider is None:
        existing_count = session.scalar(
            select(func.count())
            .select_from(Embedding)
            .where(Embedding.datasource_id == datasource.id)
        )
        datasource.semantic_status = "stale" if existing_count else "configuration_required"
        datasource.semantic_error_code = (
            "gemini_api_key_missing"
            if settings.llm_provider == "gemini"
            else "provider_key_missing"
        )
        return
    entities = session.scalars(
        select(Entity)
        .where(Entity.datasource_id == datasource.id)
        .order_by(Entity.schema_name, Entity.name)
    ).all()
    relationships = session.scalars(
        select(Relationship).where(Relationship.datasource_id == datasource.id)
    ).all()
    try:
        datasource.semantic_status = "indexing"
        datasource.semantic_error_code = None
        for entity in entities:
            fields = session.scalars(
                select(Field).where(Field.entity_id == entity.id).order_by(Field.ordinal)
            ).all()
            payload_fields: list[dict[str, object]] = []
            for field in fields:
                profile = profiles.get((entity.schema_name, entity.name, field.name))
                payload_fields.append(
                    {
                        "name": field.name,
                        "native_type": field.native_type,
                        "normalized_type": field.normalized_type,
                        "nullable": field.nullable,
                        "primary_key": bool(field.metadata_json.get("primary_key")),
                        "unique": bool(field.metadata_json.get("unique")),
                        "profile": profile.statistics if profile else None,
                    }
                )
            relation_payload = [
                {
                    "source_entity_id": str(item.source_entity_id),
                    "target_entity_id": str(item.target_entity_id),
                    "type": item.relationship_type,
                }
                for item in relationships
                if item.source_entity_id == entity.id or item.target_entity_id == entity.id
            ]
            payload = {
                "datasource_type": datasource.source_type,
                "schema": entity.schema_name,
                "entity": entity.name,
                "entity_type": entity.entity_type,
                "fields": payload_fields,
                "relationships": relation_payload,
            }
            input_hash = _hash_json(
                {
                    "payload": payload,
                    "model": settings.llm_model,
                    "embedding_model": settings.embedding_model,
                    "config_version": settings.model_config_version,
                }
            )
            existing_embedding = session.scalar(
                select(Embedding).where(
                    Embedding.datasource_id == datasource.id,
                    Embedding.object_type == "entity",
                    Embedding.object_id == entity.id,
                )
            )
            if (
                entity.metadata_json.get("semantic_input_hash") == input_hash
                and existing_embedding is not None
            ):
                continue
            enrichment = enrich_entity(provider, payload)
            field_by_name = {field.name: field for field in fields}
            session.execute(delete(SemanticTerm).where(SemanticTerm.entity_id == entity.id))
            session.execute(delete(MetricCandidate).where(MetricCandidate.entity_id == entity.id))
            entity.description = enrichment.entity_description
            for term in enrichment.business_terms:
                session.add(
                    SemanticTerm(
                        datasource_id=datasource.id,
                        entity_id=entity.id,
                        term=term,
                        description=enrichment.entity_description,
                        confidence=enrichment.confidence,
                        source="llm_inferred",
                    )
                )
            for enriched_field in enrichment.fields:
                matched_field = field_by_name.get(enriched_field.name)
                if matched_field is None:
                    continue
                matched_field.description = enriched_field.description
                for term in enriched_field.business_terms:
                    session.add(
                        SemanticTerm(
                            datasource_id=datasource.id,
                            entity_id=entity.id,
                            field_id=matched_field.id,
                            term=term,
                            description=enriched_field.description,
                            confidence=enriched_field.confidence,
                            source="llm_inferred",
                        )
                    )
            for metric in enrichment.metrics:
                session.add(
                    MetricCandidate(
                        datasource_id=datasource.id,
                        entity_id=entity.id,
                        name=metric.name,
                        expression=metric.expression,
                        description=metric.description,
                        confidence=metric.confidence,
                        source="llm_inferred",
                        metadata_json={"verified": False},
                    )
                )
            content = json.dumps(
                {
                    "schema": entity.schema_name,
                    "entity": entity.name,
                    "description": enrichment.entity_description,
                    "terms": enrichment.business_terms,
                    "fields": [item.model_dump() for item in enrichment.fields],
                    "metrics": [item.model_dump() for item in enrichment.metrics],
                },
                sort_keys=True,
            )
            vector = provider.embed([content])[0]
            if existing_embedding is None:
                existing_embedding = Embedding(
                    datasource_id=datasource.id,
                    object_type="entity",
                    object_id=entity.id,
                )
                session.add(existing_embedding)
            existing_embedding.content = content
            existing_embedding.embedding = vector
            existing_embedding.metadata_json = {
                "content_hash": _hash_json(content),
                "model": settings.embedding_model,
                "config_version": settings.model_config_version,
            }
            entity.metadata_json = {
                **entity.metadata_json,
                "semantic_input_hash": input_hash,
                "semantic_source": "llm_inferred",
            }
            session.flush()
        datasource.semantic_status = "ready"
        datasource.semantic_error_code = None
    except (ProviderError, ValidationError) as exc:
        session.rollback()
        datasource = _get_datasource(session, datasource.id)
        existing_count = session.scalar(
            select(func.count())
            .select_from(Embedding)
            .where(Embedding.datasource_id == datasource.id)
        )
        datasource.semantic_status = "stale" if existing_count else "failed"
        datasource.semantic_error_code = (
            exc.code if isinstance(exc, ProviderError) else "semantic_schema_invalid"
        )
    finally:
        provider.close()


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
        _sync_metadata(session, datasource, metadata)
        excluded_fields = frozenset(
            (entity.schema_name, entity.name, field.name)
            for entity in metadata.entities
            for field in entity.fields
            if is_possible_pii(field.name)
        )
        profile_result = connector.profile(
            metadata,
            ProfilingPolicy(
                max_rows_per_entity=app_settings.datasource_profile_max_rows,
                timeout_ms=app_settings.datasource_profile_timeout_ms,
                enum_max_distinct=app_settings.datasource_profile_enum_max_distinct,
                excluded_fields=excluded_fields,
            ),
        )
        profiles = _persist_profiles(session, datasource, profile_result)
        datasource.metadata_hash = _metadata_hash(metadata)
        datasource.last_refreshed_at = datetime.now(UTC)
        datasource.last_error_code = None
        datasource.status = "ready"
        session.commit()
        datasource = _get_datasource(session, datasource.id)
        _refresh_semantic_index(session, datasource, profiles, app_settings)
        create_semantic_manifest_snapshot(session, datasource, app_settings)
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


def _counts(session: Session, datasource_id: UUID) -> dict[str, int]:
    entity_count = session.scalar(
        select(func.count()).select_from(Entity).where(Entity.datasource_id == datasource_id)
    )
    relationship_count = session.scalar(
        select(func.count())
        .select_from(Relationship)
        .where(Relationship.datasource_id == datasource_id)
    )
    profile_count = session.scalar(
        select(func.count())
        .select_from(ProfileStatistic)
        .join(Field, ProfileStatistic.field_id == Field.id)
        .join(Entity, Field.entity_id == Entity.id)
        .where(Entity.datasource_id == datasource_id)
    )
    semantic_term_count = session.scalar(
        select(func.count())
        .select_from(SemanticTerm)
        .where(SemanticTerm.datasource_id == datasource_id)
    )
    metric_count = session.scalar(
        select(func.count())
        .select_from(MetricCandidate)
        .where(MetricCandidate.datasource_id == datasource_id)
    )
    embedding_count = session.scalar(
        select(func.count()).select_from(Embedding).where(Embedding.datasource_id == datasource_id)
    )
    pii_excluded_count = session.scalar(
        select(func.count())
        .select_from(ProfileStatistic)
        .join(Field, ProfileStatistic.field_id == Field.id)
        .join(Entity, Field.entity_id == Entity.id)
        .where(
            Entity.datasource_id == datasource_id,
            ProfileStatistic.statistics["excluded"].as_boolean().is_(True),
        )
    )
    return {
        "entity_count": int(entity_count or 0),
        "relationship_count": int(relationship_count or 0),
        "profile_count": int(profile_count or 0),
        "semantic_term_count": int(semantic_term_count or 0),
        "metric_count": int(metric_count or 0),
        "embedding_count": int(embedding_count or 0),
        "pii_excluded_count": int(pii_excluded_count or 0),
    }


def _summary(session: Session, datasource: Datasource) -> DatasourceSummary:
    counts = _counts(session, datasource.id)
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
        **counts,
        semantic_status=datasource.semantic_status,
        semantic_error_code=datasource.semantic_error_code,
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
    field_by_id: dict[UUID, Field] = {}
    for field in fields:
        fields_by_entity.setdefault(field.entity_id, []).append(field)
        field_by_id[field.id] = field
    profiles = {
        item.field_id: item
        for item in session.scalars(
            select(ProfileStatistic)
            .join(Field, ProfileStatistic.field_id == Field.id)
            .join(Entity, Field.entity_id == Entity.id)
            .where(Entity.datasource_id == datasource_id)
        ).all()
    }
    terms_by_entity: dict[UUID, list[str]] = {}
    for term in session.scalars(
        select(SemanticTerm).where(
            SemanticTerm.datasource_id == datasource_id,
            SemanticTerm.field_id.is_(None),
        )
    ).all():
        if term.entity_id is not None:
            terms_by_entity.setdefault(term.entity_id, []).append(term.term)
    metrics_by_entity: dict[UUID, list[str]] = {}
    for metric in session.scalars(
        select(MetricCandidate).where(MetricCandidate.datasource_id == datasource_id)
    ).all():
        if metric.entity_id is not None:
            metrics_by_entity.setdefault(metric.entity_id, []).append(metric.name)
    entity_responses = [
        EntitySummary(
            id=entity.id,
            schema_name=entity.schema_name,
            name=entity.name,
            entity_type=entity.entity_type,
            description=entity.description,
            business_terms=terms_by_entity.get(entity.id, []),
            metrics=metrics_by_entity.get(entity.id, []),
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
                    description=field.description,
                    profile=profiles[field.id].statistics if field.id in profiles else None,
                    profile_sample_size=profiles[field.id].sample_size
                    if field.id in profiles
                    else None,
                    profile_excluded=bool(
                        profiles[field.id].statistics.get("excluded")
                        if field.id in profiles
                        else False
                    ),
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
    relationship_threshold = get_settings().relationship_inferred_min_confidence
    for relationship in relationships:
        source_entity = entity_by_id.get(relationship.source_entity_id)
        target_entity = entity_by_id.get(relationship.target_entity_id)
        if source_entity and target_entity:
            source_field = (
                field_by_id.get(relationship.source_field_id)
                if relationship.source_field_id is not None
                else None
            )
            target_field = (
                field_by_id.get(relationship.target_field_id)
                if relationship.target_field_id is not None
                else None
            )
            source_name = f"{source_entity.schema_name}.{source_entity.name}"
            target_name = f"{target_entity.schema_name}.{target_entity.name}"
            declared = relationship.source == "introspection"
            evidence = (
                [
                    "database foreign key: "
                    f"{source_name}.{source_field.name if source_field else '?'} -> "
                    f"{target_name}.{target_field.name if target_field else '?'}"
                ]
                if declared
                else [f"privacy-safe relationship signal: source={relationship.source}"]
            )
            relationship_responses.append(
                RelationshipSummary(
                    id=relationship.id,
                    name=relationship.relationship_type,
                    source=source_name,
                    target=target_name,
                    source_field=source_field.name if source_field else None,
                    target_field=target_field.name if target_field else None,
                    relationship_type=relationship.relationship_type,
                    provenance="declared" if declared else "inferred",
                    confidence=relationship.confidence,
                    evidence=evidence,
                    generation_eligible=declared
                    or relationship.confidence >= relationship_threshold,
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
    counts = _counts(session, datasource_id)
    return OnboardingStatusResponse(
        datasource_id=datasource.id,
        status=datasource.status,
        entity_count=counts["entity_count"],
        relationship_count=counts["relationship_count"],
        last_refreshed_at=datasource.last_refreshed_at,
        last_error_code=datasource.last_error_code,
    )
