"""Datasource-scoped hybrid retrieval, graph expansion, and compact context assembly."""

import re
import unicodedata
from collections import deque
from dataclasses import dataclass
from typing import Literal, cast
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


@dataclass(frozen=True)
class RankedEntity:
    entity_id: UUID
    embedding_id: UUID | None
    lexical_score: float
    semantic_score: float | None
    fused_score: float
    selection_source: Literal["semantic", "lexical", "hybrid"]


TOKEN = re.compile(r"[a-z0-9]+", re.IGNORECASE)
STOP_WORDS = {
    "a",
    "an",
    "and",
    "are",
    "by",
    "for",
    "from",
    "how",
    "is",
    "of",
    "our",
    "the",
    "to",
    "what",
    "when",
    "which",
    "who",
    "with",
}


def _normalized(value: str) -> str:
    decomposed = unicodedata.normalize("NFKD", value.replace("_", " "))
    return "".join(
        character for character in decomposed if not unicodedata.combining(character)
    ).lower()


def _tokens(value: str) -> set[str]:
    result: set[str] = set()
    for token in TOKEN.findall(_normalized(value)):
        if token in STOP_WORDS:
            continue
        result.add(token)
        if len(token) > 4 and token.endswith("s") and not token.endswith("ss"):
            result.add(token[:-1])
    return result


def _lexical_scores(session: Session, datasource_id: UUID, question: str) -> dict[UUID, float]:
    question_tokens = _tokens(question)
    if not question_tokens:
        return {}
    normalized_question = " ".join(_normalized(question).split())
    entities = session.scalars(
        select(Entity).where(Entity.datasource_id == datasource_id)
    ).all()
    fields = session.scalars(
        select(Field).join(Entity, Field.entity_id == Entity.id).where(
            Entity.datasource_id == datasource_id
        )
    ).all()
    terms = session.scalars(
        select(SemanticTerm).where(SemanticTerm.datasource_id == datasource_id)
    ).all()
    metrics = session.scalars(
        select(MetricCandidate).where(MetricCandidate.datasource_id == datasource_id)
    ).all()
    fields_by_entity: dict[UUID, list[Field]] = {}
    for field in fields:
        fields_by_entity.setdefault(field.entity_id, []).append(field)
    terms_by_entity: dict[UUID, list[SemanticTerm]] = {}
    for term in terms:
        if term.entity_id is not None:
            terms_by_entity.setdefault(term.entity_id, []).append(term)
    metrics_by_entity: dict[UUID, list[MetricCandidate]] = {}
    for metric in metrics:
        if metric.entity_id is not None:
            metrics_by_entity.setdefault(metric.entity_id, []).append(metric)

    scores: dict[UUID, float] = {}
    denominator = max(8.0, len(question_tokens) * 8.0)
    for entity in entities:
        raw_score = 0.0
        entity_name = " ".join(_normalized(entity.name).split())
        if entity_name and entity_name in normalized_question:
            raw_score += 8.0
        raw_score += 4.0 * len(question_tokens & _tokens(entity.name))
        raw_score += len(question_tokens & _tokens(entity.description or ""))
        for field in fields_by_entity.get(entity.id, []):
            field_name = " ".join(_normalized(field.name).split())
            if field_name and field_name in normalized_question:
                raw_score += 6.0
            raw_score += 3.0 * len(question_tokens & _tokens(field.name))
            raw_score += len(question_tokens & _tokens(field.description or ""))
        for term in terms_by_entity.get(entity.id, []):
            term_name = " ".join(_normalized(term.term).split())
            if term_name and term_name in normalized_question:
                raw_score += 6.0 * term.confidence
            raw_score += 4.0 * term.confidence * len(question_tokens & _tokens(term.term))
            raw_score += term.confidence * len(
                question_tokens & _tokens(term.description or "")
            )
        for metric in metrics_by_entity.get(entity.id, []):
            metric_name = " ".join(_normalized(metric.name).split())
            if metric_name and metric_name in normalized_question:
                raw_score += 6.0 * metric.confidence
            raw_score += 4.0 * metric.confidence * len(
                question_tokens & _tokens(metric.name)
            )
            raw_score += metric.confidence * len(
                question_tokens & _tokens(metric.description or "")
            )
        if raw_score > 0:
            scores[entity.id] = round(min(1.0, raw_score / denominator), 6)
    return scores


def _rank_entities(
    semantic: list[ScoredEntity],
    lexical: dict[UUID, float],
    *,
    strategy: Literal["vector", "hybrid"],
    top_k: int,
    semantic_weight: float,
    lexical_weight: float,
    hybrid_relative_threshold: float,
) -> list[RankedEntity]:
    semantic_by_id = {item.entity_id: item for item in semantic}
    candidate_ids = set(semantic_by_id)
    if strategy == "hybrid":
        candidate_ids.update(lexical)
    weight_total = semantic_weight + lexical_weight
    ranked: list[RankedEntity] = []
    for entity_id in candidate_ids:
        semantic_item = semantic_by_id.get(entity_id)
        semantic_score = semantic_item.similarity if semantic_item is not None else None
        semantic_component = (
            max(0.0, min(1.0, (semantic_score + 1.0) / 2.0))
            if semantic_score is not None
            else 0.0
        )
        lexical_score = lexical.get(entity_id, 0.0) if strategy == "hybrid" else 0.0
        fused_score = (
            semantic_component
            if strategy == "vector"
            else (
                semantic_component * semantic_weight + lexical_score * lexical_weight
            )
            / weight_total
        )
        if strategy == "vector" or lexical_score == 0:
            source: Literal["semantic", "lexical", "hybrid"] = "semantic"
        elif semantic_item is None:
            source = "lexical"
        else:
            source = "hybrid"
        ranked.append(
            RankedEntity(
                entity_id=entity_id,
                embedding_id=semantic_item.embedding_id if semantic_item else None,
                lexical_score=lexical_score,
                semantic_score=semantic_score,
                fused_score=round(fused_score, 6),
                selection_source=source,
            )
        )
    ranked.sort(
        key=lambda item: (
            -item.fused_score,
            -item.lexical_score,
            -(item.semantic_score if item.semantic_score is not None else -1.0),
            str(item.entity_id),
        )
    )
    if strategy == "hybrid" and ranked:
        cutoff = ranked[0].fused_score * hybrid_relative_threshold
        ranked = [item for item in ranked if item.fused_score >= cutoff]
    return ranked[:top_k]


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
    query_run: QueryRun | None = None,
    strategy: Literal["vector", "hybrid"] | None = None,
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
    effective_strategy = cast(
        Literal["vector", "hybrid"], strategy or app_settings.retrieval_strategy
    )
    if effective_strategy not in {"vector", "hybrid"}:
        raise ValueError(f"Unsupported retrieval strategy: {effective_strategy}")
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

    semantic_limit = (
        effective_top_k
        if effective_strategy == "vector"
        else min(app_settings.retrieval_max_entities, effective_top_k * 3)
    )
    semantic = _semantic_search(session, datasource.id, query_embedding, semantic_limit)
    if not semantic:
        raise AppError(
            "semantic_index_empty", "Datasource semantic index is empty", status_code=409
        )
    lexical = (
        _lexical_scores(session, datasource.id, question)
        if effective_strategy == "hybrid"
        else {}
    )
    ranked = _rank_entities(
        semantic,
        lexical,
        strategy=effective_strategy,
        top_k=effective_top_k,
        semantic_weight=app_settings.retrieval_semantic_weight,
        lexical_weight=app_settings.retrieval_lexical_weight,
        hybrid_relative_threshold=app_settings.retrieval_hybrid_relative_threshold,
    )
    all_relationships = session.scalars(
        select(Relationship).where(Relationship.datasource_id == datasource.id)
    ).all()
    seed_ids = [item.entity_id for item in ranked]
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

    score_by_id = {item.entity_id: item for item in ranked}
    response_entities: list[RetrievedEntity] = []
    context_ids = [
        f"embedding:{item.embedding_id}"
        for item in ranked
        if item.embedding_id is not None
    ]
    for entity_id in ordered_entity_ids:
        entity = entity_by_id.get(entity_id)
        if entity is None:
            continue
        entity_terms = terms_by_entity.get(entity.id, [])[:10]
        entity_metrics = metrics_by_entity.get(entity.id, [])[:8]
        ranking = score_by_id.get(entity.id)
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
                    ranking.selection_source if ranking else "relationship_expansion"
                ),
                similarity=ranking.semantic_score if ranking else None,
                lexical_score=ranking.lexical_score if ranking else None,
                semantic_score=ranking.semantic_score if ranking else None,
                fused_score=ranking.fused_score if ranking else None,
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

    if query_run is None:
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
    else:
        if query_run.datasource_id != datasource.id or query_run.question != question:
            raise ValueError("Query run does not match the retrieval request")
        query_run.retrieved_context_ids = context_ids
        query_run.status = "retrieve_context"
    session.commit()
    return RetrievalResponse(
        run_id=query_run.id,
        datasource_id=datasource.id,
        question=question,
        top_k=effective_top_k,
        strategy=effective_strategy,
        config_version=app_settings.retrieval_config_version,
        context_ids=context_ids,
        entities=response_entities,
        relationships=response_relationships,
    )
