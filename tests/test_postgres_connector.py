import os

import pytest

from connectors.base import (
    ConnectionConfig,
    ConnectorError,
    ProfilingPolicy,
    QueryLimits,
    ValidatedNativeQuery,
)
from connectors.postgres import PostgresConnector


def demo_connector() -> PostgresConnector:
    return PostgresConnector(
        ConnectionConfig(
            host="demo-postgres",
            port=5432,
            database="insightmesh_demo",
            username="demo_reader",
            password=os.environ["DEMO_READER_PASSWORD"],
            ssl_mode="disable",
            allowed_schemas=("public",),
        )
    )


def test_connection_and_introspection() -> None:
    connector = demo_connector()

    connection = connector.test_connection()
    metadata = connector.introspect()

    assert connection.database == "insightmesh_demo"
    assert connection.read_only_transaction is True
    assert {entity.name for entity in metadata.entities} >= {
        "customers",
        "orders",
        "order_items",
        "products",
    }
    assert len(metadata.relationships) >= 4


def test_local_profiling_is_bounded_and_excludes_possible_pii() -> None:
    connector = demo_connector()
    metadata = connector.introspect()
    result = connector.profile(
        metadata,
        ProfilingPolicy(
            max_rows_per_entity=3,
            timeout_ms=2_000,
            enum_max_distinct=5,
            excluded_fields=frozenset({("public", "customers", "customer_name")}),
        ),
    )
    profiles = {
        (item.schema_name, item.entity_name, item.field_name): item for item in result.fields
    }

    customer_name = profiles[("public", "customers", "customer_name")]
    assert customer_name.sample_size == 0
    assert customer_name.statistics == {
        "excluded": True,
        "exclusion_reason": "possible_pii",
    }
    order_status = profiles[("public", "orders", "status")]
    assert order_status.sample_size <= 3
    assert set(order_status.statistics["candidate_values"]) <= {
        "completed",
        "cancelled",
        "pending",
        "refunded",
    }


def test_query_boundaries_enforce_row_limit_schema_timeout_and_read_only() -> None:
    connector = demo_connector()
    result = connector.execute_readonly(
        ValidatedNativeQuery(
            text="SELECT value FROM generate_series(1, 5) AS value",
            dialect="postgresql",
            referenced_schemas=frozenset({"public"}),
        ),
        QueryLimits(timeout_ms=1_000, max_rows=3),
    )
    assert result.columns == ("value",)
    assert len(result.rows) == 3
    assert result.truncated is True

    with pytest.raises(ConnectorError, match="outside the allowlist") as schema_error:
        connector.execute_readonly(
            ValidatedNativeQuery(
                text="SELECT * FROM pg_catalog.pg_class",
                dialect="postgresql",
                referenced_schemas=frozenset({"pg_catalog"}),
            ),
            QueryLimits(timeout_ms=1_000, max_rows=10),
        )
    assert schema_error.value.code == "schema_blocked"

    with pytest.raises(ConnectorError) as write_error:
        connector.execute_readonly(
            ValidatedNativeQuery(
                text="UPDATE public.foundation_probe SET label = label RETURNING id",
                dialect="postgresql",
                referenced_schemas=frozenset({"public"}),
            ),
            QueryLimits(timeout_ms=1_000, max_rows=10),
        )
    assert write_error.value.code == "query_blocked"

    with pytest.raises(ConnectorError) as timeout_error:
        connector.execute_readonly(
            ValidatedNativeQuery(
                text="SELECT pg_sleep(0.2)",
                dialect="postgresql",
                referenced_schemas=frozenset({"public"}),
            ),
            QueryLimits(timeout_ms=20, max_rows=1),
        )
    assert timeout_error.value.code == "query_timeout"
