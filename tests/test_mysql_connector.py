import os

import pytest
from connectors.base import (
    ConnectionConfig,
    ConnectorError,
    ProfilingPolicy,
    QueryLimits,
    ValidatedNativeQuery,
)
from connectors.mysql import MySQLConnector


def demo_connector() -> MySQLConnector:
    return MySQLConnector(
        ConnectionConfig(
            host="demo-mysql",
            port=3306,
            database="insightmesh_demo",
            username="demo_reader",
            password=os.environ["DEMO_READER_PASSWORD"],
            ssl_mode="disable",
            allowed_schemas=("insightmesh_demo",),
        )
    )


def test_mysql_capabilities_connection_and_introspection() -> None:
    connector = demo_connector()

    assert connector.capabilities.dialect == "mysql"
    assert connector.capabilities.supports_explain is True
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


def test_mysql_local_profiling_is_bounded_and_privacy_aware() -> None:
    connector = demo_connector()
    metadata = connector.introspect()
    result = connector.profile(
        metadata,
        ProfilingPolicy(
            max_rows_per_entity=3,
            timeout_ms=2_000,
            enum_max_distinct=5,
            excluded_fields=frozenset(
                {("insightmesh_demo", "customers", "customer_name")}
            ),
        ),
    )
    profiles = {
        (item.schema_name, item.entity_name, item.field_name): item
        for item in result.fields
    }

    customer_name = profiles[("insightmesh_demo", "customers", "customer_name")]
    assert customer_name.sample_size == 0
    assert customer_name.statistics["excluded"] is True
    order_status = profiles[("insightmesh_demo", "orders", "status")]
    assert order_status.sample_size <= 3
    assert set(order_status.statistics["candidate_values"]) <= {
        "completed",
        "cancelled",
        "pending",
        "refunded",
    }


def test_mysql_query_boundaries_enforce_limit_database_timeout_and_read_only() -> None:
    connector = demo_connector()
    result = connector.execute_readonly(
        ValidatedNativeQuery(
            text=(
                "SELECT id FROM insightmesh_demo.orders "
                "UNION ALL SELECT id FROM insightmesh_demo.orders"
            ),
            dialect="mysql",
            referenced_schemas=frozenset({"insightmesh_demo"}),
        ),
        QueryLimits(timeout_ms=1_000, max_rows=3),
    )
    assert len(result.rows) == 3
    assert result.truncated is True

    with pytest.raises(ConnectorError, match="outside the allowlist") as schema_error:
        connector.execute_readonly(
            ValidatedNativeQuery(
                text="SELECT * FROM mysql.user",
                dialect="mysql",
                referenced_schemas=frozenset({"mysql"}),
            ),
            QueryLimits(timeout_ms=1_000, max_rows=10),
        )
    assert schema_error.value.code == "schema_blocked"

    with pytest.raises(ConnectorError) as write_error:
        connector.execute_readonly(
            ValidatedNativeQuery(
                text="UPDATE insightmesh_demo.foundation_probe SET label = label",
                dialect="mysql",
                referenced_schemas=frozenset({"insightmesh_demo"}),
            ),
            QueryLimits(timeout_ms=1_000, max_rows=10),
        )
    assert write_error.value.code == "query_blocked"

    with pytest.raises(ConnectorError) as timeout_error:
        connector.execute_readonly(
            ValidatedNativeQuery(
                text=(
                    "SELECT SUM(a.id*b.id*c.id*d.id*e.id*f.id*g.id*h.id*i.id*j.id) "
                    "FROM insightmesh_demo.orders a "
                    "CROSS JOIN insightmesh_demo.orders b "
                    "CROSS JOIN insightmesh_demo.orders c "
                    "CROSS JOIN insightmesh_demo.orders d "
                    "CROSS JOIN insightmesh_demo.orders e "
                    "CROSS JOIN insightmesh_demo.orders f "
                    "CROSS JOIN insightmesh_demo.orders g "
                    "CROSS JOIN insightmesh_demo.orders h "
                    "CROSS JOIN insightmesh_demo.orders i "
                    "CROSS JOIN insightmesh_demo.orders j"
                ),
                dialect="mysql",
                referenced_schemas=frozenset({"insightmesh_demo"}),
            ),
            QueryLimits(timeout_ms=20, max_rows=1),
        )
    assert timeout_error.value.code == "query_timeout"
