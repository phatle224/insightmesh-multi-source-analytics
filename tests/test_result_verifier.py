from datetime import date
from decimal import Decimal

from connectors.base import QueryResult
from query.result_verifier import verify_result


def test_verify_result_preserves_numeric_and_temporal_semantics() -> None:
    verified = verify_result(
        QueryResult(
            columns=("product_name", "revenue", "sold_on"),
            rows=(("Wireless Keyboard", Decimal("237.00"), date(2026, 9, 22)),),
            truncated=False,
        ),
        expected_columns=["product_name", "revenue", "sold_on"],
        max_rows=10,
        duration_ms=32,
    )

    assert [column["type"] for column in verified.payload["columns"]] == [
        "string",
        "number",
        "temporal",
    ]
    assert verified.payload["rows"] == [["Wireless Keyboard", 237, "2026-09-22"]]
