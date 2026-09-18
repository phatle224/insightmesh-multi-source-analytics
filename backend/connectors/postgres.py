"""PostgreSQL connector with read-only, schema, timeout, and row boundaries."""

import re
from collections.abc import Iterator
from contextlib import contextmanager
from typing import Any

import psycopg
from psycopg import sql
from psycopg.errors import InsufficientPrivilege, QueryCanceled, ReadOnlySqlTransaction

from connectors.base import (
    ConnectionConfig,
    ConnectionTestResult,
    ConnectorError,
    ExplainResult,
    QueryLimits,
    QueryResult,
    RawDataSourceMetadata,
    RawEntity,
    RawField,
    RawRelationship,
    ValidatedNativeQuery,
)

IDENTIFIER = re.compile(r"^[A-Za-z_][A-Za-z0-9_$]{0,62}$")
SSL_MODES = {"disable", "prefer", "require", "verify-ca", "verify-full"}


def _normalized_type(native_type: str) -> str:
    lowered = native_type.lower()
    if any(token in lowered for token in ("int", "numeric", "decimal", "real", "double")):
        return "number"
    if "bool" in lowered:
        return "boolean"
    if any(token in lowered for token in ("date", "time")):
        return "temporal"
    if any(token in lowered for token in ("json", "array")):
        return "structured"
    if any(token in lowered for token in ("char", "text", "uuid")):
        return "string"
    return "other"


class PostgresConnector:
    def __init__(
        self,
        config: ConnectionConfig,
        *,
        connect_timeout_seconds: int = 5,
        statement_timeout_ms: int = 5_000,
    ) -> None:
        if config.ssl_mode not in SSL_MODES:
            raise ConnectorError("unsupported_configuration", "Unsupported PostgreSQL SSL mode")
        if not config.allowed_schemas or any(
            not IDENTIFIER.fullmatch(name) for name in config.allowed_schemas
        ):
            raise ConnectorError("unsupported_configuration", "Allowed schema names are invalid")
        self.config = config
        self.connect_timeout_seconds = connect_timeout_seconds
        self.statement_timeout_ms = statement_timeout_ms

    @contextmanager
    def _connection(self) -> Iterator[psycopg.Connection[Any]]:
        try:
            with psycopg.connect(
                host=self.config.host,
                port=self.config.port,
                dbname=self.config.database,
                user=self.config.username,
                password=self.config.password,
                sslmode=self.config.ssl_mode,
                connect_timeout=self.connect_timeout_seconds,
                application_name="insightmesh",
            ) as connection:
                yield connection
        except ConnectorError:
            raise
        except psycopg.OperationalError as exc:
            message = str(exc).lower()
            if "password authentication failed" in message or "authentication failed" in message:
                raise ConnectorError(
                    "authentication_failed", "PostgreSQL authentication failed"
                ) from None
            if "timeout" in message:
                raise ConnectorError(
                    "connection_timeout", "PostgreSQL connection timed out", retryable=True
                ) from None
            raise ConnectorError(
                "connection_failed", "PostgreSQL connection could not be established", retryable=True
            ) from None

    def _prepare_transaction(self, connection: psycopg.Connection[Any], timeout_ms: int) -> None:
        connection.execute("SET TRANSACTION READ ONLY")
        connection.execute("SELECT set_config('statement_timeout', %s, true)", (str(timeout_ms),))
        identifiers = sql.SQL(", ").join(sql.Identifier(name) for name in self.config.allowed_schemas)
        connection.execute(sql.SQL("SET LOCAL search_path TO {}").format(identifiers))

    def _check_query_boundary(self, query: ValidatedNativeQuery) -> None:
        if query.dialect != "postgresql":
            raise ConnectorError("dialect_mismatch", "Query dialect does not match PostgreSQL")
        if not query.referenced_schemas.issubset(set(self.config.allowed_schemas)):
            raise ConnectorError("schema_blocked", "Query references a schema outside the allowlist")

    def test_connection(self) -> ConnectionTestResult:
        with self._connection() as connection:
            with connection.transaction():
                self._prepare_transaction(connection, self.statement_timeout_ms)
                row = connection.execute(
                    "SELECT current_database(), current_setting('server_version'), "
                    "current_setting('transaction_read_only')"
                ).fetchone()
                if row is None:
                    raise ConnectorError("connection_failed", "PostgreSQL returned no test result")
                return ConnectionTestResult(
                    database=str(row[0]),
                    server_version=str(row[1]),
                    read_only_transaction=str(row[2]) == "on",
                )

    def introspect(self) -> RawDataSourceMetadata:
        with self._connection() as connection:
            with connection.transaction():
                self._prepare_transaction(connection, self.statement_timeout_ms)
                schema_filter = list(self.config.allowed_schemas)
                table_rows = connection.execute(
                    """
                    SELECT table_schema, table_name, table_type
                    FROM information_schema.tables
                    WHERE table_schema = ANY(%s)
                      AND table_type IN ('BASE TABLE', 'VIEW')
                    ORDER BY table_schema, table_name
                    """,
                    (schema_filter,),
                ).fetchall()
                column_rows = connection.execute(
                    """
                    SELECT table_schema, table_name, column_name, data_type,
                           is_nullable, ordinal_position
                    FROM information_schema.columns
                    WHERE table_schema = ANY(%s)
                    ORDER BY table_schema, table_name, ordinal_position
                    """,
                    (schema_filter,),
                ).fetchall()
                constraint_rows = connection.execute(
                    """
                    SELECT tc.table_schema, tc.table_name, kcu.column_name, tc.constraint_type
                    FROM information_schema.table_constraints tc
                    JOIN information_schema.key_column_usage kcu
                      ON tc.constraint_name = kcu.constraint_name
                     AND tc.constraint_schema = kcu.constraint_schema
                    WHERE tc.table_schema = ANY(%s)
                      AND tc.constraint_type IN ('PRIMARY KEY', 'UNIQUE')
                    """,
                    (schema_filter,),
                ).fetchall()
                relationship_rows = connection.execute(
                    """
                    SELECT tc.constraint_name,
                           kcu.table_schema, kcu.table_name, kcu.column_name,
                           ccu.table_schema, ccu.table_name, ccu.column_name
                    FROM information_schema.table_constraints tc
                    JOIN information_schema.key_column_usage kcu
                      ON tc.constraint_name = kcu.constraint_name
                     AND tc.constraint_schema = kcu.constraint_schema
                    JOIN information_schema.constraint_column_usage ccu
                      ON ccu.constraint_name = tc.constraint_name
                     AND ccu.constraint_schema = tc.constraint_schema
                    WHERE tc.constraint_type = 'FOREIGN KEY'
                      AND tc.table_schema = ANY(%s)
                      AND ccu.table_schema = ANY(%s)
                    ORDER BY tc.constraint_name, kcu.ordinal_position
                    """,
                    (schema_filter, schema_filter),
                ).fetchall()

        flags = {
            (str(row[0]), str(row[1]), str(row[2]), str(row[3])) for row in constraint_rows
        }
        fields_by_entity: dict[tuple[str, str], list[RawField]] = {}
        for row in column_rows:
            schema_name, table_name, column_name, native_type = map(str, row[:4])
            fields_by_entity.setdefault((schema_name, table_name), []).append(
                RawField(
                    name=column_name,
                    native_type=native_type,
                    normalized_type=_normalized_type(native_type),
                    nullable=str(row[4]) == "YES",
                    ordinal=int(row[5]),
                    primary_key=(schema_name, table_name, column_name, "PRIMARY KEY") in flags,
                    unique=(schema_name, table_name, column_name, "UNIQUE") in flags,
                )
            )
        entities = tuple(
            RawEntity(
                schema_name=str(row[0]),
                name=str(row[1]),
                entity_type="table" if str(row[2]) == "BASE TABLE" else "view",
                fields=tuple(fields_by_entity.get((str(row[0]), str(row[1])), [])),
            )
            for row in table_rows
        )
        relationships = tuple(
            RawRelationship(
                name=str(row[0]),
                source_schema=str(row[1]),
                source_entity=str(row[2]),
                source_field=str(row[3]),
                target_schema=str(row[4]),
                target_entity=str(row[5]),
                target_field=str(row[6]),
            )
            for row in relationship_rows
        )
        return RawDataSourceMetadata(entities=entities, relationships=relationships)

    def explain(self, query: ValidatedNativeQuery, limits: QueryLimits) -> ExplainResult:
        self._check_query_boundary(query)
        try:
            with self._connection() as connection, connection.transaction():
                self._prepare_transaction(connection, limits.timeout_ms)
                rows = connection.execute(f"EXPLAIN {query.text}").fetchall()
                return ExplainResult(plan=tuple(str(row[0]) for row in rows))
        except QueryCanceled:
            raise ConnectorError("query_timeout", "PostgreSQL query timed out", retryable=True) from None
        except (InsufficientPrivilege, ReadOnlySqlTransaction):
            raise ConnectorError("query_blocked", "PostgreSQL rejected a non-read-only query") from None
        except psycopg.Error:
            raise ConnectorError("query_invalid", "PostgreSQL could not explain the query") from None

    def execute_readonly(
        self, query: ValidatedNativeQuery, limits: QueryLimits
    ) -> QueryResult:
        self._check_query_boundary(query)
        try:
            with self._connection() as connection, connection.transaction():
                self._prepare_transaction(connection, limits.timeout_ms)
                cursor = connection.execute(query.text)
                if cursor.description is None:
                    raise ConnectorError("query_blocked", "Query did not produce a read-only result")
                rows = cursor.fetchmany(limits.max_rows + 1)
                columns = tuple(column.name for column in cursor.description)
                return QueryResult(
                    columns=columns,
                    rows=tuple(tuple(value for value in row) for row in rows[: limits.max_rows]),
                    truncated=len(rows) > limits.max_rows,
                )
        except ConnectorError:
            raise
        except QueryCanceled:
            raise ConnectorError("query_timeout", "PostgreSQL query timed out", retryable=True) from None
        except (InsufficientPrivilege, ReadOnlySqlTransaction):
            raise ConnectorError("query_blocked", "PostgreSQL rejected a non-read-only query") from None
        except psycopg.Error:
            raise ConnectorError("query_invalid", "PostgreSQL could not execute the query") from None

    def close(self) -> None:
        return None
