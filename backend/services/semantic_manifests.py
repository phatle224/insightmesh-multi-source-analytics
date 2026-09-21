"""Build and retain privacy-safe, immutable semantic-context snapshots."""

import hashlib
import json
from typing import Any
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from api.errors import AppError
from api.schemas.datasources import SemanticManifestResponse
from api.settings import Settings, get_settings
from persistence.models import (
    Datasource,
    Embedding,
    Entity,
    Field,
    MetricCandidate,
    ProfileStatistic,
    Relationship,
    SemanticManifest,
    SemanticTerm,
)
from skills.registry import get_skill

_PROFILE_KEYS = frozenset(
    {
        "excluded",
        "exclusion_reason",
        "null_ratio",
        "distinct_count",
        "minimum",
        "maximum",
        "candidate_values",
        "field_presence_rate",
        "data_type_distribution",
    }
)


def _hash_json(value: object) -> str:
    serialized = json.dumps(value, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(serialized.encode()).hexdigest()


def _semantic_content(value: object) -> object:
    """Remove trace-only IDs so equivalent refreshes reuse the same immutable version."""
    if isinstance(value, dict):
        return {
            key: _semantic_content(item)
            for key, item in value.items()
            if key not in {"id", "embedding_artifact_id"}
        }
    if isinstance(value, list):
        return [_semantic_content(item) for item in value]
    return value


def _safe_profile(statistic: ProfileStatistic | None) -> dict[str, object] | None:
    if statistic is None:
        return None
    raw = statistic.statistics
    if raw.get("excluded") is True:
        return {
            "excluded": True,
            "exclusion_reason": str(raw.get("exclusion_reason", "privacy_policy")),
        }
    return {key: raw[key] for key in sorted(_PROFILE_KEYS) if key in raw}


def _configuration(settings: Settings, datasource_type: str) -> dict[str, Any]:
    generation_model = (
        settings.gemini_model if settings.llm_provider == "gemini" else settings.llm_model
    )
    return {
        "model_config_version": settings.model_config_version,
        "retrieval_config_version": settings.retrieval_config_version,
        "generation_provider": settings.llm_provider,
        "generation_model": generation_model,
        "fallback_provider": settings.llm_fallback_provider,
        "fallback_model": settings.llm_fallback_model,
        "embedding_model": settings.embedding_model,
        "embedding_dimensions": settings.embedding_dimensions,
        "relationship_inferred_min_confidence": settings.relationship_inferred_min_confidence,
        "privacy_policy_version": "v1-local-profile",
        "skill_versions": {
            name: get_skill(name).version
            for name in (
                ("mysql-query-generation", "mysql-query-repair")
                if datasource_type == "mysql"
                else ("query-generation", "query-repair")
            )
        },
    }


def _build_artifacts(
    session: Session, datasource: Datasource, settings: Settings
) -> dict[str, Any]:
    entities = session.scalars(
        select(Entity)
        .where(Entity.datasource_id == datasource.id)
        .order_by(Entity.schema_name, Entity.name)
    ).all()
    fields = session.scalars(
        select(Field)
        .join(Entity, Field.entity_id == Entity.id)
        .where(Entity.datasource_id == datasource.id)
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
            .where(Entity.datasource_id == datasource.id)
        ).all()
    }
    terms_by_entity: dict[UUID, list[SemanticTerm]] = {}
    terms_by_field: dict[UUID, list[SemanticTerm]] = {}
    for term in session.scalars(
        select(SemanticTerm)
        .where(SemanticTerm.datasource_id == datasource.id)
        .order_by(SemanticTerm.term, SemanticTerm.id)
    ).all():
        if term.field_id is not None:
            terms_by_field.setdefault(term.field_id, []).append(term)
        elif term.entity_id is not None:
            terms_by_entity.setdefault(term.entity_id, []).append(term)

    metrics_by_entity: dict[UUID, list[MetricCandidate]] = {}
    for metric in session.scalars(
        select(MetricCandidate)
        .where(MetricCandidate.datasource_id == datasource.id)
        .order_by(MetricCandidate.name, MetricCandidate.id)
    ).all():
        if metric.entity_id is not None:
            metrics_by_entity.setdefault(metric.entity_id, []).append(metric)

    embeddings = {
        item.object_id: item.id
        for item in session.scalars(
            select(Embedding).where(
                Embedding.datasource_id == datasource.id,
                Embedding.object_type == "entity",
            )
        ).all()
    }

    def term_payload(term: SemanticTerm) -> dict[str, Any]:
        return {
            "id": str(term.id),
            "term": term.term,
            "description": term.description,
            "confidence": term.confidence,
            "source": term.source,
        }

    entity_payloads: list[dict[str, Any]] = []
    entity_by_id = {entity.id: entity for entity in entities}
    for entity in entities:
        field_payloads: list[dict[str, Any]] = []
        for field in fields_by_entity.get(entity.id, []):
            profile = profiles.get(field.id)
            safe_profile = _safe_profile(profile)
            field_payloads.append(
                {
                    "id": str(field.id),
                    "name": field.name,
                    "native_type": field.native_type,
                    "normalized_type": field.normalized_type,
                    "nullable": field.nullable,
                    "ordinal": field.ordinal,
                    "primary_key": bool(field.metadata_json.get("primary_key")),
                    "unique": bool(field.metadata_json.get("unique")),
                    "description": field.description,
                    "profile": safe_profile,
                    "profile_sample_size": profile.sample_size if profile else None,
                    "profile_excluded": bool(safe_profile and safe_profile.get("excluded")),
                    "semantic_terms": [
                        term_payload(term) for term in terms_by_field.get(field.id, [])
                    ],
                }
            )
        entity_payloads.append(
            {
                "id": str(entity.id),
                "schema_name": entity.schema_name,
                "name": entity.name,
                "entity_type": entity.entity_type,
                "description": entity.description,
                "semantic_terms": [
                    term_payload(term) for term in terms_by_entity.get(entity.id, [])
                ],
                "metrics": [
                    {
                        "id": str(metric.id),
                        "name": metric.name,
                        "expression": metric.expression,
                        "description": metric.description,
                        "confidence": metric.confidence,
                        "source": metric.source,
                        "verified": bool(metric.metadata_json.get("verified")),
                    }
                    for metric in metrics_by_entity.get(entity.id, [])
                ],
                "embedding_artifact_id": (
                    str(embeddings[entity.id]) if entity.id in embeddings else None
                ),
                "fields": field_payloads,
            }
        )

    relationship_payloads: list[dict[str, Any]] = []
    relationships = session.scalars(
        select(Relationship)
        .where(Relationship.datasource_id == datasource.id)
        .order_by(Relationship.source_entity_id, Relationship.target_entity_id, Relationship.id)
    ).all()
    for relationship in relationships:
        source_entity = entity_by_id.get(relationship.source_entity_id)
        target_entity = entity_by_id.get(relationship.target_entity_id)
        if source_entity is None or target_entity is None:
            continue
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
        if declared:
            evidence = [
                "database foreign key: "
                f"{source_name}.{source_field.name if source_field else '?'} -> "
                f"{target_name}.{target_field.name if target_field else '?'}"
            ]
        else:
            evidence = [f"privacy-safe relationship signal: source={relationship.source}"]
        relationship_payloads.append(
            {
                "id": str(relationship.id),
                "source": source_name,
                "target": target_name,
                "source_field": source_field.name if source_field else None,
                "target_field": target_field.name if target_field else None,
                "relationship_type": relationship.relationship_type,
                "provenance": "declared" if declared else "inferred",
                "confidence": relationship.confidence,
                "evidence": evidence,
                "generation_eligible": declared
                or relationship.confidence >= settings.relationship_inferred_min_confidence,
            }
        )

    return {
        "datasource_name": datasource.name,
        "datasource_type": datasource.source_type,
        "entities": entity_payloads,
        "relationships": relationship_payloads,
    }


def create_semantic_manifest_snapshot(
    session: Session,
    datasource: Datasource,
    settings: Settings | None = None,
) -> SemanticManifest:
    if not datasource.metadata_hash or not datasource.profile_hash:
        raise AppError(
            "semantic_manifest_unavailable",
            "Refresh datasource metadata before inspecting its semantic manifest",
            status_code=409,
        )
    app_settings = settings or get_settings()
    configuration = _configuration(app_settings, datasource.source_type)
    artifacts = _build_artifacts(session, datasource, app_settings)
    manifest_hash = _hash_json(
        {
            "metadata_hash": datasource.metadata_hash,
            "profile_hash": datasource.profile_hash,
            "configuration": configuration,
            "artifacts": _semantic_content(artifacts),
        }
    )
    existing = session.scalar(
        select(SemanticManifest).where(
            SemanticManifest.datasource_id == datasource.id,
            SemanticManifest.manifest_hash == manifest_hash,
        )
    )
    if existing is not None:
        return existing
    latest_version = session.scalar(
        select(func.max(SemanticManifest.version)).where(
            SemanticManifest.datasource_id == datasource.id
        )
    )
    manifest = SemanticManifest(
        datasource_id=datasource.id,
        version=int(latest_version or 0) + 1,
        manifest_hash=manifest_hash,
        metadata_hash=datasource.metadata_hash,
        profile_hash=datasource.profile_hash,
        configuration_json=configuration,
        manifest_json=artifacts,
    )
    session.add(manifest)
    session.flush()
    return manifest


def _response(manifest: SemanticManifest) -> SemanticManifestResponse:
    artifacts = manifest.manifest_json
    return SemanticManifestResponse.model_validate(
        {
            "manifest_id": manifest.id,
            "datasource_id": manifest.datasource_id,
            "datasource_name": artifacts["datasource_name"],
            "datasource_type": artifacts["datasource_type"],
            "version": manifest.version,
            "manifest_hash": manifest.manifest_hash,
            "metadata_hash": manifest.metadata_hash,
            "profile_hash": manifest.profile_hash,
            "configuration": manifest.configuration_json,
            "entities": artifacts["entities"],
            "relationships": artifacts["relationships"],
            "created_at": manifest.created_at,
        }
    )


def get_latest_semantic_manifest(
    session: Session,
    datasource_id: UUID,
    settings: Settings | None = None,
) -> SemanticManifestResponse:
    datasource = session.get(Datasource, datasource_id)
    if datasource is None:
        raise AppError("datasource_not_found", "Datasource was not found", status_code=404)
    manifest = session.scalar(
        select(SemanticManifest)
        .where(SemanticManifest.datasource_id == datasource_id)
        .order_by(SemanticManifest.version.desc())
        .limit(1)
    )
    if manifest is None:
        manifest = create_semantic_manifest_snapshot(session, datasource, settings)
        session.commit()
        session.refresh(manifest)
    return _response(manifest)
