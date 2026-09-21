"""Run reproducible SQL result, retrieval, and safety evaluation suites."""

from __future__ import annotations

import argparse
import json
import math
from collections import defaultdict
from datetime import UTC, datetime
from decimal import Decimal, InvalidOperation
from pathlib import Path
from time import perf_counter
from typing import Any, Literal
from uuid import UUID

from api.settings import Settings, get_settings
from harness.runtime import run_query
from persistence.database import SessionLocal
from persistence.models import Datasource, Embedding, Entity, QueryRun, Relationship
from semantic.provider import LLMProvider, StructuredGenerationRequest
from services.datasources import build_embedding_provider, build_semantic_provider
from skills.registry import get_skill
from sqlalchemy import select

DEFAULT_FIXTURE = Path("/app/evals/postgres/cases.json")
DEFAULT_REPORT = Path("/app/evals/reports/postgres-latest.json")
ANALYTICAL_CATEGORIES = {"easy", "medium", "hard"}


class CountingProvider:
    """Count logical provider calls without recording prompt or response content."""

    def __init__(self, provider: LLMProvider) -> None:
        self.provider = provider
        self.generation_calls = 0
        self.embedding_calls = 0

    def generate_structured(
        self, request: StructuredGenerationRequest
    ) -> dict[str, Any]:
        self.generation_calls += 1
        return self.provider.generate_structured(request)

    def embed(self, inputs: list[str]) -> list[list[float]]:
        self.embedding_calls += 1
        return self.provider.embed(inputs)

    def close(self) -> None:
        self.provider.close()

    @property
    def fallback_generation_calls(self) -> int:
        value = getattr(self.provider, "fallback_generation_calls", 0)
        return int(value) if isinstance(value, int) else 0


def _load_suite(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as fixture_file:
        suite: dict[str, Any] = json.load(fixture_file)
    return suite


def _ratio(matches: int, total: int) -> float | None:
    return round(matches / total, 4) if total else None


def _percentile(values: list[int], percentile: float) -> int | None:
    if not values:
        return None
    ordered = sorted(values)
    index = max(0, math.ceil(percentile * len(ordered)) - 1)
    return ordered[index]


def _edge(left: str, right: str) -> tuple[str, str]:
    return (left, right) if left <= right else (right, left)


def _number(value: object) -> Decimal | None:
    if isinstance(value, bool) or value is None:
        return None
    if isinstance(value, int | float | Decimal):
        return Decimal(str(value)).normalize()
    if isinstance(value, str):
        try:
            return Decimal(value).normalize()
        except InvalidOperation:
            return None
    return None


def _cell(value: object, *, temporal_granularity: str | None = None) -> str:
    number = _number(value)
    if number is not None:
        return f"number:{number}"
    text = "" if value is None else str(value).strip()
    if temporal_granularity == "month" and len(text) >= 7:
        text = text[:7]
    return f"value:{text.casefold()}"


def _result_matches(run: QueryRun, expected: dict[str, Any]) -> tuple[bool, str | None]:
    if run.result_json is None:
        return False, "completed run did not retain a verified result"
    rows = run.result_json.get("rows")
    if not isinstance(rows, list):
        return False, "verified result rows were unavailable"
    kind = expected.get("kind")
    if kind == "scalar":
        if len(rows) != 1 or not isinstance(rows[0], list) or len(rows[0]) != 1:
            return False, "expected exactly one scalar cell"
        matches = _cell(rows[0][0]) == _cell(expected.get("value"))
        return matches, None if matches else "scalar value differed"
    if kind != "rows":
        return False, "unsupported expected-result assertion"
    expected_rows = expected.get("rows")
    if not isinstance(expected_rows, list):
        return False, "fixture rows were invalid"
    granularity = expected.get("temporal_granularity")

    def canonical(row: object) -> tuple[str, ...]:
        if not isinstance(row, list):
            return ("invalid-row",)
        return tuple(
            _cell(value, temporal_granularity=granularity if index == 0 else None)
            for index, value in enumerate(row)
        )

    actual = [canonical(row) for row in rows]
    wanted = [canonical(row) for row in expected_rows]
    if actual and wanted and len(actual[0]) > len(wanted[0]):

        def contains(actual_row: tuple[str, ...], wanted_row: tuple[str, ...]) -> bool:
            position = 0
            for value in actual_row:
                if position < len(wanted_row) and value == wanted_row[position]:
                    position += 1
            return position == len(wanted_row)

        unmatched = list(actual)
        for wanted_row in wanted:
            match_index = next(
                (
                    index
                    for index, actual_row in enumerate(unmatched)
                    if contains(actual_row, wanted_row)
                ),
                None,
            )
            if match_index is None:
                return False, "result rows differed"
            unmatched.pop(match_index)
        return len(unmatched) == 0, None if not unmatched else "result rows differed"
    if not bool(expected.get("order_sensitive", False)):
        actual.sort()
        wanted.sort()
    matches = actual == wanted
    return matches, None if matches else "result rows differed"


def _retrieval_evidence(
    session: Any,
    run: QueryRun,
    expected_entities: set[str],
    expected_relationships: set[tuple[str, str]],
) -> dict[str, Any]:
    entity_ids: list[UUID] = []
    relationship_ids: list[UUID] = []
    for context_id in run.retrieved_context_ids:
        kind, _, raw_id = context_id.partition(":")
        try:
            parsed = UUID(raw_id)
        except (ValueError, AttributeError):
            continue
        if kind == "entity":
            entity_ids.append(parsed)
        elif kind == "relationship":
            relationship_ids.append(parsed)
    entities = session.scalars(select(Entity).where(Entity.id.in_(entity_ids))).all()
    entity_names = {item.id: f"{item.schema_name}.{item.name}" for item in entities}
    retrieved_entities = set(entity_names.values())
    relationships = session.scalars(
        select(Relationship).where(Relationship.id.in_(relationship_ids))
    ).all()
    retrieved_relationships = {
        _edge(entity_names[item.source_entity_id], entity_names[item.target_entity_id])
        for item in relationships
        if item.source_entity_id in entity_names
        and item.target_entity_id in entity_names
    }
    entity_matches = expected_entities & retrieved_entities
    relationship_matches = expected_relationships & retrieved_relationships
    return {
        "entity_recall": _ratio(len(entity_matches), len(expected_entities)),
        "entity_precision": _ratio(len(entity_matches), len(retrieved_entities)),
        "join_path_success": expected_relationships <= retrieved_relationships,
        "join_edge_recall": _ratio(
            len(relationship_matches), len(expected_relationships)
        ),
        "retrieved_entities": sorted(retrieved_entities),
        "missing_entities": sorted(expected_entities - retrieved_entities),
        "missing_relationships": [
            list(item)
            for item in sorted(expected_relationships - retrieved_relationships)
        ],
    }


def _case_result(
    session: Any,
    datasource: Datasource,
    case: dict[str, Any],
    strategy: Literal["vector", "hybrid"],
    settings: Settings,
    generation: CountingProvider,
    embedding: CountingProvider,
) -> dict[str, Any]:
    generation_before = generation.generation_calls
    embedding_before = embedding.embedding_calls
    fallback_before = generation.fallback_generation_calls
    started = perf_counter()
    try:
        run = run_query(
            session,
            datasource.id,
            str(case["question"]),
            settings=settings,
            generation_provider=generation,
            retrieval_provider=embedding,
            retrieval_strategy=strategy,
        )
    except Exception as error:  # noqa: BLE001 - evaluation must retain safe failure evidence
        session.rollback()
        return {
            "id": case["id"],
            "category": case["category"],
            "question": case["question"],
            "expected_status": case["expected_status"],
            "actual_status": "runner_error",
            "status_correct": False,
            "result_correct": False,
            "error": type(error).__name__,
            "latency_ms": round((perf_counter() - started) * 1000),
            "generation_calls": generation.generation_calls - generation_before,
            "embedding_calls": embedding.embedding_calls - embedding_before,
            "fallback_generation_calls": (
                generation.fallback_generation_calls - fallback_before
            ),
        }
    latency_ms = round((perf_counter() - started) * 1000)
    status_correct = run.status == case["expected_status"]
    expected_result = case.get("expected_result")
    result_correct: bool | None = None
    result_issue: str | None = None
    if isinstance(expected_result, dict):
        result_correct, result_issue = _result_matches(run, expected_result)
    expected_entities = set(case.get("expected_entities", []))
    expected_relationships = {
        _edge(str(item[0]), str(item[1]))
        for item in case.get("expected_relationships", [])
    }
    retrieval = (
        _retrieval_evidence(session, run, expected_entities, expected_relationships)
        if expected_entities
        else None
    )
    trace_details = next(
        (
            event.get("details")
            for event in run.trace_json
            if event.get("event") == "evaluate_context"
        ),
        None,
    )
    return {
        "id": case["id"],
        "category": case["category"],
        "question": case["question"],
        "run_id": str(run.id),
        "expected_status": case["expected_status"],
        "actual_status": run.status,
        "status_correct": status_correct,
        "result_correct": result_correct,
        "result_issue": result_issue,
        "repair_count": run.repair_count,
        "error_code": run.error_code,
        "latency_ms": latency_ms,
        "generation_calls": generation.generation_calls - generation_before,
        "embedding_calls": embedding.embedding_calls - embedding_before,
        "fallback_generation_calls": generation.fallback_generation_calls
        - fallback_before,
        "retrieval": retrieval,
        "retrieval_scores": trace_details,
    }


def _summarize(strategy: str, cases: list[dict[str, Any]]) -> dict[str, Any]:
    analytical = [item for item in cases if item["category"] in ANALYTICAL_CATEGORIES]
    with_result = [item for item in analytical if item["result_correct"] is not None]
    unsafe = [item for item in cases if item["category"] == "unsafe"]
    out_of_scope = [item for item in cases if item["category"] == "out_of_scope"]
    ambiguous = [item for item in cases if item["category"] == "ambiguous"]
    repair_attempted = [item for item in cases if item.get("repair_count", 0) > 0]
    retrieval_cases = [item for item in analytical if item.get("retrieval")]
    entity_recalls = [
        item["retrieval"]["entity_recall"]
        for item in retrieval_cases
        if item["retrieval"]["entity_recall"] is not None
    ]
    entity_precisions = [
        item["retrieval"]["entity_precision"]
        for item in retrieval_cases
        if item["retrieval"]["entity_precision"] is not None
    ]
    category_results: dict[str, dict[str, Any]] = {}
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for item in cases:
        grouped[item["category"]].append(item)
    for category, items in sorted(grouped.items()):
        result_items = [item for item in items if item["result_correct"] is not None]
        category_results[category] = {
            "cases": len(items),
            "status_accuracy": _ratio(
                sum(bool(item["status_correct"]) for item in items), len(items)
            ),
            "result_accuracy": _ratio(
                sum(bool(item["result_correct"]) for item in result_items),
                len(result_items),
            ),
        }
    return {
        "strategy": strategy,
        "case_count": len(cases),
        "status_accuracy": _ratio(
            sum(bool(item["status_correct"]) for item in cases), len(cases)
        ),
        "execution_rate": _ratio(
            sum(item["actual_status"] == "completed" for item in analytical),
            len(analytical),
        ),
        "result_accuracy": _ratio(
            sum(bool(item["result_correct"]) for item in with_result), len(with_result)
        ),
        "mean_entity_recall": (
            round(sum(entity_recalls) / len(entity_recalls), 4)
            if entity_recalls
            else None
        ),
        "mean_entity_precision": (
            round(sum(entity_precisions) / len(entity_precisions), 4)
            if entity_precisions
            else None
        ),
        "join_path_accuracy": _ratio(
            sum(
                bool(item["retrieval"]["join_path_success"]) for item in retrieval_cases
            ),
            len(retrieval_cases),
        ),
        "repair_success": _ratio(
            sum(item["actual_status"] == "completed" for item in repair_attempted),
            len(repair_attempted),
        ),
        "repair_attempted": len(repair_attempted),
        "safety_blocking": _ratio(
            sum(item["actual_status"] == "blocked" for item in unsafe), len(unsafe)
        ),
        "out_of_scope_blocking": _ratio(
            sum(item["actual_status"] == "out_of_scope" for item in out_of_scope),
            len(out_of_scope),
        ),
        "ambiguity_detection": _ratio(
            sum(
                item["actual_status"] == "clarification_required" for item in ambiguous
            ),
            len(ambiguous),
        ),
        "false_block_rate": _ratio(
            sum(
                item["actual_status"] in {"blocked", "out_of_scope"}
                for item in analytical
            ),
            len(analytical),
        ),
        "provider_calls": {
            "generation": sum(item["generation_calls"] for item in cases),
            "embedding": sum(item["embedding_calls"] for item in cases),
            "fallback_generation": sum(
                item["fallback_generation_calls"] for item in cases
            ),
        },
        "latency_ms": {
            "p50": _percentile([item["latency_ms"] for item in cases], 0.50),
            "p95": _percentile([item["latency_ms"] for item in cases], 0.95),
        },
        "by_category": category_results,
        "cases": cases,
    }


def _run_strategy(
    session: Any,
    datasource: Datasource,
    suite: dict[str, Any],
    strategy: Literal["vector", "hybrid"],
    settings: Settings,
) -> dict[str, Any]:
    generation_provider = build_semantic_provider(settings)
    embedding_provider = build_embedding_provider(settings)
    if generation_provider is None or embedding_provider is None:
        if generation_provider is not None:
            generation_provider.close()
        if embedding_provider is not None:
            embedding_provider.close()
        raise RuntimeError("Generation and embedding providers must be configured")
    generation = CountingProvider(generation_provider)
    embedding = CountingProvider(embedding_provider)
    try:
        cases = [
            _case_result(
                session,
                datasource,
                case,
                strategy,
                settings,
                generation,
                embedding,
            )
            for case in suite["cases"]
        ]
    finally:
        generation.close()
        embedding.close()
    return _summarize(strategy, cases)


def _comparison(reports: dict[str, dict[str, Any]]) -> dict[str, Any] | None:
    vector = reports.get("vector")
    hybrid = reports.get("hybrid")
    if vector is None or hybrid is None:
        return None
    result_non_regression = (hybrid["result_accuracy"] or 0) >= (
        vector["result_accuracy"] or 0
    )
    safety_non_regression = (hybrid["safety_blocking"] or 0) >= (
        vector["safety_blocking"] or 0
    ) and (hybrid["false_block_rate"] or 0) <= (vector["false_block_rate"] or 0)
    precision_improved = (hybrid["mean_entity_precision"] or 0) > (
        vector["mean_entity_precision"] or 0
    )
    return {
        "result_accuracy_non_regression": result_non_regression,
        "safety_non_regression": safety_non_regression,
        "retrieval_precision_improved": precision_improved,
        "gate_passed": result_non_regression
        and safety_non_regression
        and precision_improved,
        "vector_result_accuracy": vector["result_accuracy"],
        "hybrid_result_accuracy": hybrid["result_accuracy"],
        "vector_mean_entity_precision": vector["mean_entity_precision"],
        "hybrid_mean_entity_precision": hybrid["mean_entity_precision"],
    }


def main(
    *,
    default_fixture: Path = DEFAULT_FIXTURE,
    default_report: Path = DEFAULT_REPORT,
    default_source_type: str = "postgresql",
) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--fixture", type=Path, default=default_fixture)
    parser.add_argument("--report", type=Path, default=default_report)
    parser.add_argument(
        "--datasource-type",
        choices=("postgresql", "mysql"),
        default=default_source_type,
    )
    parser.add_argument("--datasource-name")
    parser.add_argument(
        "--strategy", choices=("vector", "hybrid", "both"), default="both"
    )
    args = parser.parse_args()
    suite = _load_suite(args.fixture)
    settings = get_settings()
    strategies: list[Literal["vector", "hybrid"]] = (
        ["vector", "hybrid"] if args.strategy == "both" else [args.strategy]
    )
    with SessionLocal() as session:
        datasource_query = select(Datasource).where(
            Datasource.source_type == args.datasource_type,
            Datasource.status == "ready",
            Datasource.semantic_status.in_(["ready", "stale"]),
            Datasource.metadata_hash.is_not(None),
            Datasource.profile_hash.is_not(None),
            select(Embedding.id)
            .where(Embedding.datasource_id == Datasource.id)
            .exists(),
        )
        if args.datasource_name:
            datasource_query = datasource_query.where(
                Datasource.name == args.datasource_name
            )
        datasource = session.scalar(
            datasource_query.order_by(
                Datasource.is_active.desc(), Datasource.created_at.desc()
            )
        )
        if datasource is None:
            parser.error(
                f"No ready {args.datasource_type} datasource matched the request"
            )
        strategy_reports: dict[str, dict[str, Any]] = {}
        for strategy in strategies:
            strategy_reports[strategy] = _run_strategy(
                session, datasource, suite, strategy, settings
            )
        report = {
            "suite": suite["suite"],
            "generated_at": datetime.now(UTC).isoformat(),
            "datasource": {
                "id": str(datasource.id),
                "name": datasource.name,
                "type": datasource.source_type,
                "seed_version": suite["datasource_seed_version"],
                "metadata_hash": datasource.metadata_hash,
                "profile_hash": datasource.profile_hash,
            },
            "configuration": {
                "model_config_version": settings.model_config_version,
                "generation_provider": settings.llm_provider,
                "generation_model": settings.llm_model,
                "fallback_provider": settings.llm_fallback_provider,
                "fallback_model": settings.llm_fallback_model,
                "embedding_model": settings.embedding_model,
                "embedding_dimensions": settings.embedding_dimensions,
                "retrieval_config_version": settings.retrieval_config_version,
                "retrieval_top_k": settings.retrieval_top_k,
                "retrieval_semantic_weight": settings.retrieval_semantic_weight,
                "retrieval_lexical_weight": settings.retrieval_lexical_weight,
                "retrieval_hybrid_relative_threshold": (
                    settings.retrieval_hybrid_relative_threshold
                ),
                "retrieval_max_entities": settings.retrieval_max_entities,
                "retrieval_max_relationship_hops": (
                    settings.retrieval_max_relationship_hops
                ),
                "query_max_repair_attempts": settings.query_max_repair_attempts,
                "skill_versions": {
                    name: get_skill(name).version
                    for name in (
                        ("mysql-query-generation", "mysql-query-repair")
                        if args.datasource_type == "mysql"
                        else ("query-generation", "query-repair")
                    )
                },
            },
            "strategies": strategy_reports,
            "comparison": _comparison(strategy_reports),
        }
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(
        json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    print(json.dumps(report, indent=2, ensure_ascii=False))
    comparison = report["comparison"]
    if comparison is not None and not comparison["gate_passed"]:
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
