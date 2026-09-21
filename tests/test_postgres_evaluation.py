import json
from pathlib import Path

from evals.run_postgres_evaluation import _comparison, _result_matches
from persistence.models import QueryRun


def test_phase_ten_fixture_covers_result_and_guardrail_groups() -> None:
    suite = json.loads(
        Path("/app/evals/postgres/cases.json").read_text(encoding="utf-8")
    )
    categories = {case["category"] for case in suite["cases"]}
    assert categories == {
        "easy",
        "medium",
        "hard",
        "ambiguous",
        "out_of_scope",
        "unsafe",
    }
    assert all("expected_sql" not in case for case in suite["cases"])
    assert any(case["id"] == "unsafe_prompt_injection" for case in suite["cases"])
    assert any(case["id"] == "valid_write_word_false_positive" for case in suite["cases"])


def test_result_comparison_is_sql_independent_and_normalizes_numbers_and_months() -> None:
    run = QueryRun(
        result_json={
            "rows": [["2025-01-01T00:00:00+00:00", "2.00"]],
        }
    )
    matches, issue = _result_matches(
        run,
        {
            "kind": "rows",
            "rows": [["2025-01", 2]],
            "temporal_granularity": "month",
        },
    )
    assert matches is True
    assert issue is None


def test_hybrid_gate_requires_precision_improvement_and_non_regression() -> None:
    comparison = _comparison(
        {
            "vector": {
                "result_accuracy": 0.8,
                "safety_blocking": 1.0,
                "false_block_rate": 0.0,
                "mean_entity_precision": 0.6,
            },
            "hybrid": {
                "result_accuracy": 0.8,
                "safety_blocking": 1.0,
                "false_block_rate": 0.0,
                "mean_entity_precision": 0.7,
            },
        }
    )
    assert comparison is not None
    assert comparison["gate_passed"] is True
