"""Choose presentation types from verified result metadata without an LLM."""

from typing import Any, Final

CHART_TYPES: Final[tuple[str, ...]] = ("table", "kpi", "bar", "line", "pie", "area")


def _columns(result: dict[str, Any]) -> list[dict[str, Any]]:
    raw = result.get("columns", [])
    return [item for item in raw if isinstance(item, dict)] if isinstance(raw, list) else []


def _row_count(result: dict[str, Any]) -> int:
    value = result.get("row_count", 0)
    return value if isinstance(value, int) and value >= 0 else 0


def _first_column(result: dict[str, Any], column_type: str) -> str | None:
    for column in _columns(result):
        name = column.get("name")
        if column.get("type") == column_type and isinstance(name, str):
            return name
    return None


def _first_metric(result: dict[str, Any]) -> str | None:
    return _first_column(result, "number")


def compatible_chart_types(result: dict[str, Any] | None) -> list[str]:
    """Return views whose structural requirements are satisfied, in stable order."""
    if not result:
        return ["table"]
    row_count = _row_count(result)
    metric = _first_metric(result)
    temporal = _first_column(result, "temporal")
    category = next(
        (
            column.get("name")
            for column in _columns(result)
            if column.get("type") in {"string", "boolean"} and isinstance(column.get("name"), str)
        ),
        None,
    )
    compatible = ["table"]
    if row_count == 1 and metric:
        compatible.append("kpi")
    if category and metric and 1 <= row_count <= 50:
        compatible.append("bar")
    if temporal and metric and row_count >= 2:
        compatible.extend(("line", "area"))
    if category and metric and 2 <= row_count <= 5:
        compatible.append("pie")
    return compatible


def select_visualization(result: dict[str, Any] | None) -> str:
    compatible = compatible_chart_types(result)
    for preferred in ("kpi", "line", "bar", "table"):
        if preferred in compatible:
            return preferred
    return "table"


def build_chart_config(result: dict[str, Any], chart_type: str) -> dict[str, Any]:
    if chart_type not in compatible_chart_types(result):
        raise ValueError("Chart type is not compatible with this result")
    if chart_type == "table":
        return {}
    metric = _first_metric(result)
    if chart_type == "kpi":
        return {"value_key": metric}
    if chart_type in {"line", "area"}:
        dimension = _first_column(result, "temporal")
    else:
        dimension = next(
            (
                column.get("name")
                for column in _columns(result)
                if column.get("type") in {"string", "boolean"}
            ),
            None,
        )
    return {"dimension_key": dimension, "metric_key": metric}
