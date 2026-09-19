"""Deterministic post-execution checks and JSON-safe result serialization."""

import base64
import json
from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

from connectors.base import QueryResult


def _json_safe(value: Any) -> Any:
    if value is None or isinstance(value, str | int | float | bool):
        return value
    if isinstance(value, Decimal):
        return str(value)
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, date):
        return value.isoformat()
    if isinstance(value, UUID):
        return str(value)
    if isinstance(value, bytes):
        return base64.b64encode(value).decode("ascii")
    if isinstance(value, dict):
        return {str(key): _json_safe(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_safe(item) for item in value]
    raise TypeError(f"Unsupported result value type: {type(value).__name__}")


def _type_name(values: list[Any]) -> str:
    value = next((item for item in values if item is not None), None)
    if value is None:
        return "unknown"
    if isinstance(value, bool):
        return "boolean"
    if isinstance(value, int | float | Decimal):
        return "number"
    if isinstance(value, date | datetime):
        return "temporal"
    if isinstance(value, dict | list | tuple):
        return "structured"
    return "string"


@dataclass(frozen=True)
class VerifiedResult:
    payload: dict[str, Any]
    warnings: tuple[str, ...]


def verify_result(
    result: QueryResult,
    expected_columns: list[str],
    max_rows: int,
    duration_ms: int,
) -> VerifiedResult:
    warnings: list[str] = []
    if len(result.rows) > max_rows:
        raise ValueError("Connector returned more rows than the configured maximum")
    missing = {
        name.lower() for name in expected_columns
    } - {name.lower() for name in result.columns}
    if missing:
        warnings.append("Generated result omitted expected columns: " + ", ".join(sorted(missing)))
    if not result.rows:
        warnings.append("Query completed with an empty result")
    if result.truncated:
        warnings.append("Result was truncated at the configured row limit")
    if any(value is None for row in result.rows for value in row):
        warnings.append("Result contains null values")

    safe_rows = [[_json_safe(value) for value in row] for row in result.rows]
    columns = [
        {
            "name": name,
            "type": _type_name([row[index] for row in result.rows]),
            "semantic_type": (
                "metric"
                if _type_name([row[index] for row in result.rows]) == "number"
                else "dimension"
            ),
        }
        for index, name in enumerate(result.columns)
    ]
    payload: dict[str, Any] = {
        "columns": columns,
        "rows": safe_rows,
        "row_count": len(safe_rows),
        "truncated": result.truncated,
        "duration_ms": duration_ms,
        "warnings": warnings,
    }
    json.dumps(payload)
    return VerifiedResult(payload, tuple(warnings))
