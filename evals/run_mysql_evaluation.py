"""Run the Phase 12 MySQL evaluation with a separate fixture and report."""

from pathlib import Path

from evals.run_postgres_evaluation import main

if __name__ == "__main__":
    raise SystemExit(
        main(
            default_fixture=Path("/app/evals/mysql/cases.json"),
            default_report=Path("/app/evals/reports/mysql-latest.json"),
            default_source_type="mysql",
        )
    )
