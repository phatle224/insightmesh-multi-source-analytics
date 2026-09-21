from uuid import uuid4

from sqlalchemy import delete

from api.schemas.dashboards import DashboardCreate, DashboardWidgetCreate
from api.settings import get_settings
from connectors.base import ConnectorError, ExplainResult, QueryResult
from persistence.database import SessionLocal
from persistence.models import Dashboard, Datasource, Entity, Field, QueryRun
from services.dashboards import add_widget, create_dashboard, refresh_widget
from visualization.selection import compatible_chart_types, select_visualization


def result_payload(
    columns: list[tuple[str, str]], rows: list[list[object]]
) -> dict[str, object]:
    return {
        "columns": [
            {
                "name": name,
                "type": type_name,
                "semantic_type": "metric" if type_name == "number" else "dimension",
            }
            for name, type_name in columns
        ],
        "rows": rows,
        "row_count": len(rows),
        "truncated": False,
        "duration_ms": 10,
        "warnings": [],
    }


def test_visualization_selection_is_deterministic_for_supported_shapes() -> None:
    kpi = result_payload([("revenue", "number")], [[120]])
    categories = result_payload(
        [("status", "string"), ("orders", "number")], [["paid", 8], ["new", 3]]
    )
    temporal = result_payload(
        [("month", "temporal"), ("revenue", "number")],
        [["2026-01-01", 10], ["2026-02-01", 12]],
    )

    assert compatible_chart_types(kpi) == ["table", "kpi"]
    assert select_visualization(kpi) == "kpi"
    assert compatible_chart_types(categories) == ["table", "bar", "pie"]
    assert select_visualization(categories) == "bar"
    assert compatible_chart_types(temporal) == ["table", "line", "area"]
    assert select_visualization(temporal) == "line"


class RefreshConnector:
    def __init__(self, *, fail: bool = False) -> None:
        self.fail = fail
        self.closed = False
        self.execution_calls = 0

    def explain(self, query, limits):  # type: ignore[no-untyped-def]
        if self.fail:
            raise ConnectorError(
                "query_timeout", "The stored query timed out", retryable=True
            )
        return ExplainResult(plan=("safe",))

    def execute_readonly(self, query, limits):  # type: ignore[no-untyped-def]
        self.execution_calls += 1
        return QueryResult(
            columns=("status", "orders"),
            rows=(("paid", 11), ("new", 4)),
            truncated=False,
        )

    def close(self) -> None:
        self.closed = True


def test_dashboard_refresh_reuses_stored_query_and_preserves_last_good_result() -> None:
    with SessionLocal() as session:
        datasource = Datasource(
            name=f"dashboard-source-{uuid4()}",
            source_type="postgresql",
            database_name="analytics",
            safe_host="database.internal",
            port=5432,
            allowed_schemas=["public"],
            status="ready",
            semantic_status="ready",
        )
        session.add(datasource)
        session.flush()
        entity = Entity(
            datasource_id=datasource.id,
            schema_name="public",
            name="orders",
            entity_type="table",
            metadata_json={},
        )
        session.add(entity)
        session.flush()
        session.add_all(
            [
                Field(
                    entity_id=entity.id,
                    name="status",
                    native_type="text",
                    normalized_type="string",
                    nullable=False,
                    ordinal=1,
                    metadata_json={},
                ),
                Field(
                    entity_id=entity.id,
                    name="id",
                    native_type="integer",
                    normalized_type="number",
                    nullable=False,
                    ordinal=2,
                    metadata_json={},
                ),
            ]
        )
        initial = result_payload(
            [("status", "string"), ("orders", "number")], [["paid", 8], ["new", 3]]
        )
        run = QueryRun(
            datasource_id=datasource.id,
            question="Orders by status",
            retrieved_context_ids=[],
            generated_query={
                "sql": "SELECT status, COUNT(id) AS orders FROM public.orders GROUP BY status",
                "expected_columns": ["status", "orders"],
            },
            query_type="sql",
            validation_result={"valid": True},
            status="completed",
            row_count=2,
            duration_ms=10,
            repair_count=0,
            visualization_type="bar",
            result_json=initial,
            trace_json=[],
            warnings=[],
        )
        session.add(run)
        session.commit()
        dashboard = create_dashboard(session, DashboardCreate(name="Operations"))
        widget = add_widget(
            session,
            dashboard.id,
            DashboardWidgetCreate(query_run_id=run.id, title="Orders", chart_type="bar"),
        )

        successful_connector = RefreshConnector()
        refreshed = refresh_widget(
            session,
            widget.id,
            settings=get_settings(),
            connector_factory=lambda *_: successful_connector,
        )
        assert refreshed.status == "ready"
        assert refreshed.result_json is not None
        assert refreshed.result_json["rows"] == [["paid", 11], ["new", 4]]
        assert successful_connector.execution_calls == 1
        assert successful_connector.closed

        last_good_result = refreshed.result_json
        failed_connector = RefreshConnector(fail=True)
        stale = refresh_widget(
            session,
            widget.id,
            settings=get_settings(),
            connector_factory=lambda *_: failed_connector,
        )
        assert stale.status == "stale"
        assert stale.last_error_code == "query_timeout"
        assert stale.result_json == last_good_result
        assert failed_connector.execution_calls == 0
        assert failed_connector.closed

        session.execute(delete(Dashboard).where(Dashboard.id == dashboard.id))
        session.execute(delete(Datasource).where(Datasource.id == datasource.id))
        session.commit()
