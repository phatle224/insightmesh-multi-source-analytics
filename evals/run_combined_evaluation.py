"""Run the release evaluation across both supported datasource engines."""

from __future__ import annotations

import argparse
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from evals.run_postgres_evaluation import main as run_datasource_evaluation

POSTGRES_FIXTURE = Path("/app/evals/postgres/cases.json")
MYSQL_FIXTURE = Path("/app/evals/mysql/cases.json")
POSTGRES_REPORT = Path("/app/evals/reports/postgres-latest.json")
MYSQL_REPORT = Path("/app/evals/reports/mysql-latest.json")
DEFAULT_REPORT = Path("/app/evals/reports/combined-latest.json")


def _ratio(matches: int, total: int) -> float | None:
    return round(matches / total, 4) if total else None


def _aggregate(reports: list[dict[str, Any]], strategy: str) -> dict[str, Any]:
    cases = [
        case
        for report in reports
        for case in report["strategies"][strategy]["cases"]
    ]
    analytical = [case for case in cases if case["category"] in {"easy", "medium", "hard"}]
    result_cases = [case for case in analytical if case["result_correct"] is not None]
    retrieval_cases = [case for case in analytical if case.get("retrieval")]
    category_groups: dict[str, list[dict[str, Any]]] = {}
    for case in cases:
        category_groups.setdefault(case["category"], []).append(case)
    difficulty_groups = {
        category: category_groups[category]
        for category in ("easy", "medium", "hard")
        if category in category_groups
    }

    def grouped_metrics(group: list[dict[str, Any]]) -> dict[str, Any]:
        group_results = [case for case in group if case["result_correct"] is not None]
        return {
            "cases": len(group),
            "status_accuracy": _ratio(
                sum(bool(case["status_correct"]) for case in group), len(group)
            ),
            "result_accuracy": _ratio(
                sum(bool(case["result_correct"]) for case in group_results),
                len(group_results),
            ),
        }

    return {
        "strategy": strategy,
        "case_count": len(cases),
        "status_accuracy": _ratio(
            sum(bool(case["status_correct"]) for case in cases), len(cases)
        ),
        "execution_rate": _ratio(
            sum(case["actual_status"] == "completed" for case in analytical),
            len(analytical),
        ),
        "result_accuracy": _ratio(
            sum(bool(case["result_correct"]) for case in result_cases),
            len(result_cases),
        ),
        "mean_entity_recall": _ratio(
            sum(case["retrieval"]["entity_recall"] for case in retrieval_cases),
            len(retrieval_cases),
        ),
        "mean_entity_precision": _ratio(
            sum(case["retrieval"]["entity_precision"] for case in retrieval_cases),
            len(retrieval_cases),
        ),
        "join_path_accuracy": _ratio(
            sum(bool(case["retrieval"]["join_path_success"]) for case in retrieval_cases),
            len(retrieval_cases),
        ),
        "by_difficulty": {
            category: grouped_metrics(group)
            for category, group in difficulty_groups.items()
        },
        "by_category": {
            category: grouped_metrics(group)
            for category, group in sorted(category_groups.items())
        },
        "provider_calls": {
            "generation": sum(case["generation_calls"] for case in cases),
            "embedding": sum(case["embedding_calls"] for case in cases),
            "fallback_generation": sum(
                case["fallback_generation_calls"] for case in cases
            ),
        },
        "cases": cases,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--strategy", choices=("hybrid", "vector"), default="hybrid")
    parser.add_argument("--postgres-name", default="Docker demo store")
    parser.add_argument("--mysql-name", default="Docker demo MySQL store")
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT)
    args = parser.parse_args()

    shared_args = ["--strategy", args.strategy]
    postgres_code = run_datasource_evaluation(
        default_fixture=POSTGRES_FIXTURE,
        default_report=POSTGRES_REPORT,
        default_source_type="postgresql",
        argv=[*shared_args, "--datasource-name", args.postgres_name],
    )
    mysql_code = run_datasource_evaluation(
        default_fixture=MYSQL_FIXTURE,
        default_report=MYSQL_REPORT,
        default_source_type="mysql",
        argv=[*shared_args, "--datasource-name", args.mysql_name],
    )
    if postgres_code or mysql_code:
        return postgres_code or mysql_code

    reports = [
        json.loads(POSTGRES_REPORT.read_text(encoding="utf-8")),
        json.loads(MYSQL_REPORT.read_text(encoding="utf-8")),
    ]
    combined = {
        "suite": "insightmesh_release_v1",
        "generated_at": datetime.now(UTC).isoformat(),
        "strategy": args.strategy,
        "datasources": [report["datasource"] for report in reports],
        "case_count": sum(report["strategies"][args.strategy]["case_count"] for report in reports),
        "by_datasource": {
            report["datasource"]["type"]: report["strategies"][args.strategy]
            for report in reports
        },
        "overall": _aggregate(reports, args.strategy),
    }
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(combined, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps(combined, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
