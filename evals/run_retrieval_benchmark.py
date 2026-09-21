"""Run the Phase 6 retrieval benchmark against a live indexed datasource."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from sqlalchemy import select

from persistence.database import SessionLocal
from persistence.models import Datasource, Embedding
from services.retrieval import retrieve_context

DEFAULT_FIXTURE = Path("/app/evals/retrieval/postgres.json")


def _edge(left: str, right: str) -> tuple[str, str]:
    return (left, right) if left <= right else (right, left)


def _ratio(matches: int, total: int) -> float:
    return round(matches / total, 4) if total else 1.0


def _load_suite(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as fixture_file:
        suite: dict[str, Any] = json.load(fixture_file)
    return suite


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--fixture", type=Path, default=DEFAULT_FIXTURE)
    parser.add_argument("--datasource-name")
    parser.add_argument("--top-k", type=int)
    args = parser.parse_args()
    suite = _load_suite(args.fixture)

    case_results: list[dict[str, Any]] = []
    with SessionLocal() as session:
        datasource_query = select(Datasource).where(
            Datasource.source_type == "postgresql",
            Datasource.status == "ready",
            Datasource.semantic_status.in_(["ready", "stale"]),
            Datasource.metadata_hash.is_not(None),
            Datasource.profile_hash.is_not(None),
            select(Embedding.id)
            .where(Embedding.datasource_id == Datasource.id)
            .exists(),
        )
        datasource_name = args.datasource_name or suite.get("datasource_name")
        if datasource_name:
            datasource_query = datasource_query.where(Datasource.name == datasource_name)
        datasource = session.scalar(
            datasource_query.order_by(
                Datasource.is_active.desc(), Datasource.created_at.desc()
            )
        )
        if datasource is None:
            parser.error("No ready PostgreSQL semantic index matched the requested datasource")

        for case in suite["cases"]:
            response = retrieve_context(
                session,
                datasource.id,
                case["question"],
                top_k=args.top_k,
            )
            retrieved_entities = {
                f"{entity.schema_name}.{entity.name}" for entity in response.entities
            }
            expected_entities = set(case["expected_entities"])
            entity_matches = expected_entities & retrieved_entities

            retrieved_edges = {
                _edge(relationship.source, relationship.target)
                for relationship in response.relationships
            }
            expected_edges = {
                _edge(relationship[0], relationship[1])
                for relationship in case["expected_relationships"]
            }
            edge_matches = expected_edges & retrieved_edges
            case_results.append(
                {
                    "id": case["id"],
                    "run_id": str(response.run_id),
                    "question": case["question"],
                    "schema_selection_success": expected_entities <= retrieved_entities,
                    "entity_recall": _ratio(len(entity_matches), len(expected_entities)),
                    "entity_precision": _ratio(len(entity_matches), len(retrieved_entities)),
                    "join_path_success": expected_edges <= retrieved_edges,
                    "join_edge_recall": _ratio(len(edge_matches), len(expected_edges)),
                    "expected_entities": sorted(expected_entities),
                    "retrieved_entities": sorted(retrieved_entities),
                    "missing_entities": sorted(expected_entities - retrieved_entities),
                    "missing_relationships": [
                        list(edge) for edge in sorted(expected_edges - retrieved_edges)
                    ],
                }
            )

        case_count = len(case_results)
        report = {
            "suite": suite["suite"],
            "datasource_id": str(datasource.id),
            "datasource_name": datasource.name,
            "case_count": case_count,
            "schema_selection_accuracy": _ratio(
                sum(result["schema_selection_success"] for result in case_results),
                case_count,
            ),
            "mean_entity_recall": round(
                sum(result["entity_recall"] for result in case_results) / case_count, 4
            ),
            "mean_entity_precision": round(
                sum(result["entity_precision"] for result in case_results) / case_count, 4
            ),
            "join_path_accuracy": _ratio(
                sum(result["join_path_success"] for result in case_results), case_count
            ),
            "cases": case_results,
        }
    print(json.dumps(report, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
