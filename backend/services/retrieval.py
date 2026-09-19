"""Datasource-scoped vector retrieval, graph expansion, and compact context assembly."""

from collections import deque
from dataclasses import dataclass
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from api.errors import AppError
from api.schemas.retrieval import (
    RetrievalResponse,
    RetrievedEntity,
    RetrievedField,
    RetrievedMetric,
    RetrievedRelationship,
)
from api.settings import Settings, get_settings
from persistence.models import (
    Datasource,
    Embedding,
    Entity,
    Field,
    MetricCandidate,
    ProfileStatistic,
    QueryRun,
    Relationship,
    SemanticTerm,
)
from semantic.provider import LLMProvider, ProviderError
from services.datasources import build_embedding_provider


@dataclass(frozen=True)
class ScoredEntity:
    entity_id: UUID
    embedding_id: UUID
    similarity: float


def _shortest_path(
    start: UUID,
    target: UUID,
    adjacency: dict[UUID, list[tuple[UUID, UUID]]],
    max_hops: int,
) -> tuple[list[UUID], list[UUID]] | None:
    queue: deque[tuple[UUID, list[UUID], list[UUID]]] = deque([(start, [start], [])])
    visited = {start}
    while queue:
        current, entities, relationships = queue.popleft()
        if current == target:
            return entities, relationships
        if len(relationships) >= max_hops:
            continue
        for neighbor, relationship_id in adjacency.get(current, []):
            if neighbor in visited:
                continue
            visited.add(neighbor)
            queue.append(
                (neighbor, [*entities, neighbor], [*relationships, relationship_id])
            )
    return None


def _graph_expansion(
    seed_ids: list[UUID], relationships: list[Relationship], max_hops: int
) -> tuple[set[UUID], set[UUID]]:
    entity_ids = set(seed_ids)
    relationship_ids: set[UUID] = set()
    adjacency: dict[UUID, list[tuple[UUID, UUID]]] = {}
    for relationship in relationships:
        adjacency.setdefault(relationship.source_entity_id, []).append(
            (relationship.target_entity_id, relationship.id)
        )
        adjacency.setdefault(relationship.target_entity_id, []).append(
            (relationship.source_entity_id, relationship.id)
        )
    for index, start in enumerate(seed_ids):
        for target in seed_ids[index + 1 :]:
            path = _shortest_path(start, target, adjacency, max_hops)
            if path is None:
                continue
            path_entities, path_relationships = path
            entity_ids.update(path_entities)
            relationship_ids.update(path_relationships)
    return entity_ids, relationship_ids


def _semantic_search(
    session: Session, datasource_id: UUID, query_embedding: list[float], top_k: int
) -> list[ScoredEntity]:
    distance = Embedding.embedding.cosine_distance(query_embedding).label("distance")
    rows = session.execute(
        select(Embedding, distance)
        .where(
            Embedding.datasource_id == datasource_id,
            Embedding.object_type == "entity",
        )
        .order_by(distance)
        .limit(top_k)
    ).all()
    return [
        ScoredEntity(
            entity_id=embedding.object_id,
            embedding_id=embedding.id,
            similarity=max(-1.0, min(1.0, 1.0 - float(raw_distance))),
        )
        for embedding, raw_distance in rows
    ]


def retrieve_context(
    session: Session,
    datasource_id: UUID,
    question: str,
    *,
    top_k: int | None = None,
    settings: Settings | None = None,
    provider: LLMProvider | None = None,
) -> RetrievalResponse:
    app_settings = settings or get_settings()
    datasource = session.get(Datasource, datasource_id)
    if datasource is None:
        raise AppError("datasource_not_found", "Datasource was not found", status_code=404)
    if datasource.semantic_status not in {"ready", "stale"}:
        raise AppError(
            "semantic_index_not_ready",
            "Datasource semantic index is not ready",
            status_code=409,
        )
    effective_top_k = min(
        top_k or app_settings.retrieval_top_k,
        app_settings.retrieval_max_entities,
    )
    owns_provider = provider is None
    semantic_provider = provider or build_embedding_provider(app_settings)
    if semantic_provider is None:
        raise AppError(
            "embedding_provider_not_configured",
            "Embedding provider is not configured",
            status_code=409,
        )
    try:
        query_embedding = semantic_provider.embed([question])[0]
    except ProviderError as error:
        raise AppError(
            error.code,
            error.safe_message,
            status_code=503,
            retryable=error.retryable,
        ) from None
    finally:
        if owns_provider:
            semantic_provider.close()

    scored = _semantic_search(session, datasource.id, query_embedding, effective_top_k)
    if not scored:
        raise AppError(
            "semantic_index_empty", "Datasource semantic index is empty", status_code=409
        )
    all_relationships = session.scalars(
        select(Relationship).where(Relationship.datasource_id == datasource.id)
    ).all()
    seed_ids = [item.entity_id for item in scored]
    expanded_ids, relationship_ids = _graph_expansion(
        seed_ids, list(all_relationships), app_settings.retrieval_max_relationship_hops
    )
    ordered_entity_ids = [*seed_ids]
    ordered_entity_ids.extend(
        entity_id
        for entity_id in sorted(expanded_ids - set(seed_ids), key=str)
        if len(ordered_entity_ids) < app_settings.retrieval_max_entities
    )
    included_ids = set(ordered_entity_ids)
    included_relationships = [
        item
        for item in all_relationships
        if item.id in relationship_ids
        and item.source_entity_id in included_ids
        and item.target_entity_id in included_ids
    ]

    entities = session.scalars(
        select(Entity).where(Entity.id.in_(ordered_entity_ids))
    ).all()
    entity_by_id = {item.id: item for item in entities}
    fields = session.scalars(
        select(Field)
        .where(Field.entity_id.in_(ordered_entity_ids))
        .order_by(Field.entity_id, Field.ordinal)
    ).all()
    field_by_id = {item.id: item for item in fields}
    fields_by_entity: dict[UUID, list[Field]] = {}
    for field in fields:
        fields_by_entity.setdefault(field.entity_id, []).append(field)
    profiles = {
        item.field_id: item
        for item in session.scalars(
            select(ProfileStatistic).where(
                ProfileStatistic.field_id.in_([item.id for item in fields])
            )
        ).all()
    }
    terms = session.scalars(
        select(SemanticTerm)
        .where(
            SemanticTerm.datasource_id == datasource.id,
            SemanticTerm.entity_id.in_(ordered_entity_ids),
        )
        .order_by(SemanticTerm.confidence.desc())
    ).all()
    terms_by_entity: dict[UUID, list[SemanticTerm]] = {}
    for term in terms:
        if term.entity_id is not None:
            terms_by_entity.setdefault(term.entity_id, []).append(term)
    metrics = session.scalars(
        select(MetricCandidate)
        .where(
            MetricCandidate.datasource_id == datasource.id,
            MetricCandidate.entity_id.in_(ordered_entity_ids),
        )
        .order_by(MetricCandidate.confidence.desc())
    ).all()
    metrics_by_entity: dict[UUID, list[MetricCandidate]] = {}
    for metric in metrics:
        if metric.entity_id is not None:
            metrics_by_entity.setdefault(metric.entity_id, []).append(metric)

    score_by_id = {item.entity_id: item.similarity for item in scored}
    response_entities: list[RetrievedEntity] = []
    context_ids = [f"embedding:{item.embedding_id}" for item in scored]
    for entity_id in ordered_entity_ids:
        entity = entity_by_id.get(entity_id)
        if entity is None:
            continue
        entity_terms = terms_by_entity.get(entity.id, [])[:10]
        entity_metrics = metrics_by_entity.get(entity.id, [])[:8]
        context_ids.append(f"entity:{entity.id}")
        context_ids.extend(f"semantic_term:{item.id}" for item in entity_terms)
        context_ids.extend(f"metric:{item.id}" for item in entity_metrics)
        response_entities.append(
            RetrievedEntity(
                id=entity.id,
                schema_name=entity.schema_name,
                name=entity.name,
                description=entity.description,
                selection_source=(
                    "semantic" if entity.id in score_by_id else "relationship_expansion"
                ),
                similarity=score_by_id.get(entity.id),
                business_terms=list(dict.fromkeys(item.term for item in entity_terms)),
                fields=[
                    RetrievedField(
                        id=field.id,
                        name=field.name,
                        native_type=field.native_type,
                        normalized_type=field.normalized_type,
                        description=field.description,
                        primary_key=bool(field.metadata_json.get("primary_key")),
                        unique=bool(field.metadata_json.get("unique")),
                        profile=profiles[field.id].statistics
                        if field.id in profiles
                        else None,
                    )
                    for field in fields_by_entity.get(entity.id, [])[
                        : app_settings.retrieval_max_fields_per_entity
                    ]
                ],
                metrics=[
                    RetrievedMetric(
                        id=metric.id,
                        name=metric.name,
                        expression=metric.expression,
                        description=metric.description,
                        confidence=metric.confidence,
                    )
                    for metric in entity_metrics
                ],
            )
        )

    response_relationships: list[RetrievedRelationship] = []
    for relationship in included_relationships:
        source = entity_by_id.get(relationship.source_entity_id)
        target = entity_by_id.get(relationship.target_entity_id)
        if source is None or target is None:
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
        context_ids.append(f"relationship:{relationship.id}")
        response_relationships.append(
            RetrievedRelationship(
                id=relationship.id,
                source_entity_id=source.id,
                source=f"{source.schema_name}.{source.name}",
                source_field=source_field.name if source_field else None,
                target_entity_id=target.id,
                target=f"{target.schema_name}.{target.name}",
                target_field=target_field.name if target_field else None,
                relationship_type=relationship.relationship_type,
            )
        )

    query_run = QueryRun(
        datasource_id=datasource.id,
        question=question,
        retrieved_context_ids=context_ids,
        generated_query={},
        query_type=datasource.source_type,
        validation_result={},
        status="retrieve_context",
    )
    session.add(query_run)
    session.commit()
    return RetrievalResponse(
        run_id=query_run.id,
        datasource_id=datasource.id,
        question=question,
        top_k=effective_top_k,
        context_ids=context_ids,
        entities=response_entities,
        relationships=response_relationships,
    )
