from uuid import uuid4

from api.schemas.retrieval import RetrievedEntity, RetrievedField
from query.sql_validator import validate_mysql_sql, validate_postgres_sql


def _orders() -> RetrievedEntity:
    return RetrievedEntity(
        id=uuid4(),
        schema_name="public",
        name="orders",
        description=None,
        selection_source="semantic",
        similarity=1.0,
        business_terms=[],
        fields=[
            RetrievedField(
                id=uuid4(),
                name="id",
                native_type="bigint",
                normalized_type="integer",
                description=None,
                primary_key=True,
                unique=True,
                profile=None,
            ),
            RetrievedField(
                id=uuid4(),
                name="status",
                native_type="text",
                normalized_type="string",
                description=None,
                primary_key=False,
                unique=False,
                profile=None,
            ),
        ],
        metrics=[],
    )


def test_sql_validator_allows_one_known_select() -> None:
    result = validate_postgres_sql(
        "SELECT status, COUNT(*) AS order_count FROM public.orders GROUP BY status",
        [_orders()],
        {"public"},
    )
    assert result.valid is True
    assert result.query is not None


def test_sql_validator_blocks_writes_multiple_statements_and_unsafe_functions() -> None:
    for sql in (
        "DELETE FROM public.orders",
        "SELECT status FROM public.orders; SELECT status FROM public.orders",
        "SELECT pg_sleep(1) FROM public.orders",
        "SELECT nextval('order_sequence') FROM public.orders",
        "SELECT status INTO temporary_orders FROM public.orders",
        "SELECT status FROM secret.orders",
    ):
        result = validate_postgres_sql(sql, [_orders()], {"public"})
        assert result.valid is False
        assert result.unsafe is True


def test_sql_validator_marks_unknown_columns_as_repairable() -> None:
    result = validate_postgres_sql(
        "SELECT order_state FROM public.orders",
        [_orders()],
        {"public"},
    )
    assert result.valid is False
    assert result.unsafe is False


def test_sql_validator_accepts_cte_output_aliases_in_outer_query_and_window_order() -> (
    None
):
    result = validate_postgres_sql(
        """
        WITH customer_revenue AS (
            SELECT id AS customer_id, COUNT(*) AS total_revenue
            FROM public.orders
            GROUP BY id
        )
        SELECT customer_id,
               total_revenue,
               RANK() OVER (ORDER BY total_revenue DESC) AS revenue_rank
        FROM customer_revenue
        ORDER BY revenue_rank
        """,
        [_orders()],
        {"public"},
    )

    assert result.valid is True
    assert result.query is not None
    assert result.error_code is None


def test_mysql_validator_uses_mysql_dialect_and_blocks_server_side_functions() -> None:
    orders = _orders().model_copy(update={"schema_name": "insightmesh_demo"})
    valid = validate_mysql_sql(
        "SELECT status, COUNT(*) AS order_count "
        "FROM insightmesh_demo.orders GROUP BY status",
        [orders],
        {"insightmesh_demo"},
    )
    assert valid.valid is True
    assert valid.query is not None
    assert valid.query.dialect == "mysql"

    for sql in (
        "SELECT SLEEP(1) FROM insightmesh_demo.orders",
        "SELECT LOAD_FILE('/etc/passwd') FROM insightmesh_demo.orders",
        "SELECT GET_LOCK('insightmesh', 1) FROM insightmesh_demo.orders",
        "UPDATE insightmesh_demo.orders SET status = 'cancelled'",
    ):
        blocked = validate_mysql_sql(sql, [orders], {"insightmesh_demo"})
        assert blocked.valid is False
        assert blocked.unsafe is True
