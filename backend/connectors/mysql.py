"""MySQL connector with read-only, schema, timeout, and row boundaries."""

import re
from collections.abc import Iterator
from contextlib import contextmanager, suppress
from datetime import date, datetime
from decimal import Decimal
from math import ceil
from typing import Any

import pymysql
from pymysql.connections import Connection

from connectors.base import (
    ConnectionConfig,
    ConnectionTestResult,
    ConnectorCapabilities,
    ConnectorError,
    ExplainResult,
    FieldProfile,
    ProfileResult,
    ProfilingPolicy,
    QueryLimits,
    QueryResult,
    RawDataSourceMetadata,
    RawEntity,
    RawField,
    RawRelationship,
    ValidatedNativeQuery,
)

IDENTIFIER = re.compile(r"^[A-Za-z_][A-Za-z0-9_$]{0,63}$")
SSL_MODES = {"disable", "prefer", "require"}


def _identifier(value: str) -> str:
    if not IDENTIFIER.fullmatch(value):
        raise ConnectorError("unsupported_configuration", "MySQL identifier is invalid")
    return f"`{value}`"


def _json_value(value: Any) -> Any:
    if isinstance(value, (date, datetime, Decimal)):
        return str(value)
    if isinstance(value, bytes):
        return value.decode("utf-8", errors="replace")
    return value


def _result_value(value: Any) -> Any:
    """Keep native scalar types until result verification infers their semantics."""
    if isinstance(value, bytes):
        return value.decode("utf-8", errors="replace")
    return value


def _normalized_type(native_type: str) -> str:
    lowered = native_type.lower()
    if lowered.startswith("tinyint(1)") or lowered == "boolean":
        return "boolean"
    if any(token in lowered for token in ("int", "numeric", "decimal", "float", "double")):
        return "number"
    if any(token in lowered for token in ("date", "time", "year")):
        return "temporal"
    if any(token in lowered for token in ("json", "blob", "binary", "geometry")):
        return "structured"
    if any(token in lowered for token in ("char", "text", "enum", "set")):
        return "string"
    return "other"


class MySQLConnector:
    capabilities = ConnectorCapabilities(
        dialect="mysql",
        supports_schemas=True,
        supports_explain=True,
        supports_read_only_transactions=True,
        supports_local_profiling=True,
    )

    def __init__(
        self,
        config: ConnectionConfig,
        *,
        connect_timeout_seconds: int = 5,
        statement_timeout_ms: int = 5_000,
    ) -> None:
        if config.ssl_mode not in SSL_MODES:
            raise ConnectorError("unsupported_configuration", "Unsupported MySQL SSL mode")
        if not config.allowed_schemas or any(
            not IDENTIFIER.fullmatch(name) for name in config.allowed_schemas
        ):
            raise ConnectorError("unsupported_configuration", "Allowed database names are invalid")
        self.config = config
        self.connect_timeout_seconds = connect_timeout_seconds
        self.statement_timeout_ms = statement_timeout_ms

    @contextmanager
    def _connection(self, timeout_ms: int | None = None) -> Iterator[Connection]:
        ssl: dict[str, str] | None = None if self.config.ssl_mode in {"disable", "prefer"} else {}
        try:
            connection = pymysql.connect(
                host=self.config.host,
                port=self.config.port,
                database=self.config.database,
                user=self.config.username,
                password=self.config.password,
                connect_timeout=self.connect_timeout_seconds,
                read_timeout=max(1, ceil((timeout_ms or self.statement_timeout_ms) / 1000)),
                write_timeout=self.connect_timeout_seconds,
                charset="utf8mb4",
                autocommit=False,
                ssl=ssl,
            )
        except pymysql.err.OperationalError as exc:
            code = int(exc.args[0]) if exc.args and isinstance(exc.args[0], int) else 0
            if code == 1045:
                raise ConnectorError(
                    "authentication_failed", "MySQL authentication failed"
                ) from None
            if code in {2002, 2003, 2013}:
                raise ConnectorError(
                    "connection_timeout", "MySQL connection timed out", retryable=True
                ) from None
            raise ConnectorError(
                "connection_failed",
                "MySQL connection could not be established",
                retryable=True,
            ) from None
        try:
            yield connection
        finally:
            with suppress(pymysql.MySQLError):
                connection.rollback()
            connection.close()

    def _prepare_transaction(self, connection: Connection, timeout_ms: int) -> None:
        with connection.cursor() as cursor:
            cursor.execute("SET SESSION MAX_EXECUTION_TIME = %s", (timeout_ms,))
            cursor.execute("START TRANSACTION READ ONLY")

    def _check_query_boundary(self, query: ValidatedNativeQuery) -> None:
        if query.dialect != "mysql":
            raise ConnectorError("dialect_mismatch", "Query dialect does not match MySQL")
        if not query.referenced_schemas.issubset(set(self.config.allowed_schemas)):
            raise ConnectorError(
                "schema_blocked", "Query references a database outside the allowlist"
            )

    def test_connection(self) -> ConnectionTestResult:
        with self._connection() as connection:
            self._prepare_transaction(connection, self.statement_timeout_ms)
            with connection.cursor() as cursor:
                cursor.execute("SELECT DATABASE(), VERSION()")
                row = cursor.fetchone()
            if row is None:
                raise ConnectorError("connection_failed", "MySQL returned no test result")
            return ConnectionTestResult(
                database=str(row[0]),
                server_version=str(row[1]),
                read_only_transaction=True,
            )

    def introspect(self) -> RawDataSourceMetadata:
        schemas = tuple(self.config.allowed_schemas)
        placeholders = ", ".join(["%s"] * len(schemas))
        with self._connection() as connection:
            self._prepare_transaction(connection, self.statement_timeout_ms)
            with connection.cursor() as cursor:
                cursor.execute(
                    f"""
                    SELECT TABLE_SCHEMA, TABLE_NAME, TABLE_TYPE
                    FROM information_schema.TABLES
                    WHERE TABLE_SCHEMA IN ({placeholders})
                      AND TABLE_TYPE IN ('BASE TABLE', 'VIEW')
                    ORDER BY TABLE_SCHEMA, TABLE_NAME
                    """,
                    schemas,
                )
                table_rows = cursor.fetchall()
                cursor.execute(
                    f"""
                    SELECT TABLE_SCHEMA, TABLE_NAME, COLUMN_NAME, COLUMN_TYPE,
                           IS_NULLABLE, ORDINAL_POSITION
                    FROM information_schema.COLUMNS
                    WHERE TABLE_SCHEMA IN ({placeholders})
                    ORDER BY TABLE_SCHEMA, TABLE_NAME, ORDINAL_POSITION
                    """,
                    schemas,
                )
                column_rows = cursor.fetchall()
                cursor.execute(
                    f"""
                    SELECT k.TABLE_SCHEMA, k.TABLE_NAME, k.COLUMN_NAME, c.CONSTRAINT_TYPE
                    FROM information_schema.KEY_COLUMN_USAGE k
                    JOIN information_schema.TABLE_CONSTRAINTS c
                      ON c.CONSTRAINT_SCHEMA = k.CONSTRAINT_SCHEMA
                     AND c.TABLE_NAME = k.TABLE_NAME
                     AND c.CONSTRAINT_NAME = k.CONSTRAINT_NAME
                    WHERE k.TABLE_SCHEMA IN ({placeholders})
                      AND c.CONSTRAINT_TYPE IN ('PRIMARY KEY', 'UNIQUE')
                    """,
                    schemas,
                )
                constraint_rows = cursor.fetchall()
                cursor.execute(
                    f"""
                    SELECT CONSTRAINT_NAME, TABLE_SCHEMA, TABLE_NAME, COLUMN_NAME,
                           REFERENCED_TABLE_SCHEMA, REFERENCED_TABLE_NAME,
                           REFERENCED_COLUMN_NAME
                    FROM information_schema.KEY_COLUMN_USAGE
                    WHERE TABLE_SCHEMA IN ({placeholders})
                      AND REFERENCED_TABLE_SCHEMA IN ({placeholders})
                      AND REFERENCED_TABLE_NAME IS NOT NULL
                    ORDER BY CONSTRAINT_NAME, ORDINAL_POSITION
                    """,
                    (*schemas, *schemas),
                )
                relationship_rows = cursor.fetchall()

        flags = {(str(row[0]), str(row[1]), str(row[2]), str(row[3])) for row in constraint_rows}
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

    def profile(self, metadata: RawDataSourceMetadata, policy: ProfilingPolicy) -> ProfileResult:
        profiles: list[FieldProfile] = []
        try:
            with self._connection(policy.timeout_ms) as connection:
                self._prepare_transaction(connection, policy.timeout_ms)
                with connection.cursor() as cursor:
                    for entity in metadata.entities:
                        for field in entity.fields:
                            key = (entity.schema_name, entity.name, field.name)
                            if key in policy.excluded_fields:
                                profiles.append(
                                    FieldProfile(
                                        schema_name=entity.schema_name,
                                        entity_name=entity.name,
                                        field_name=field.name,
                                        sample_size=0,
                                        statistics={
                                            "excluded": True,
                                            "exclusion_reason": "possible_pii",
                                        },
                                    )
                                )
                                continue
                            column = _identifier(field.name)
                            table = f"{_identifier(entity.schema_name)}.{_identifier(entity.name)}"
                            sampled = f"SELECT {column} AS value FROM {table} LIMIT %s"
                            aggregate_parts = [
                                "COUNT(*) AS sample_size",
                                "SUM(value IS NULL) AS null_count",
                            ]
                            supports_distinct = field.normalized_type in {
                                "number",
                                "temporal",
                                "string",
                                "boolean",
                            }
                            aggregate_parts.append(
                                "COUNT(DISTINCT value) AS distinct_count"
                                if supports_distinct
                                else "NULL AS distinct_count"
                            )
                            if field.normalized_type in {"number", "temporal"}:
                                aggregate_parts.extend(
                                    ["MIN(value) AS minimum", "MAX(value) AS maximum"]
                                )
                            cursor.execute(
                                f"SELECT {', '.join(aggregate_parts)} FROM ({sampled}) AS bounded",
                                (policy.max_rows_per_entity,),
                            )
                            row = cursor.fetchone()
                            if row is None:
                                continue
                            sample_size = int(row[0])
                            null_count = int(row[1])
                            distinct_count = int(row[2]) if row[2] is not None else None
                            statistics: dict[str, Any] = {
                                "null_ratio": round(null_count / sample_size, 6)
                                if sample_size
                                else 0.0,
                            }
                            if distinct_count is not None:
                                statistics["distinct_count"] = distinct_count
                            if field.normalized_type in {"number", "temporal"}:
                                statistics["minimum"] = _json_value(row[3])
                                statistics["maximum"] = _json_value(row[4])
                            elif (
                                field.normalized_type in {"string", "boolean"}
                                and distinct_count is not None
                                and 0 < distinct_count <= policy.enum_max_distinct
                            ):
                                cursor.execute(
                                    f"SELECT DISTINCT value FROM ({sampled}) AS bounded "
                                    "WHERE value IS NOT NULL ORDER BY value LIMIT %s",
                                    (
                                        policy.max_rows_per_entity,
                                        policy.enum_max_distinct,
                                    ),
                                )
                                statistics["candidate_values"] = [
                                    _json_value(item[0]) for item in cursor.fetchall()
                                ]
                            profiles.append(
                                FieldProfile(
                                    schema_name=entity.schema_name,
                                    entity_name=entity.name,
                                    field_name=field.name,
                                    sample_size=sample_size,
                                    statistics=statistics,
                                )
                            )
        except pymysql.err.OperationalError as exc:
            code = int(exc.args[0]) if exc.args and isinstance(exc.args[0], int) else 0
            if code in {3024, 2013}:
                raise ConnectorError(
                    "profile_timeout", "MySQL profiling timed out", retryable=True
                ) from None
            raise ConnectorError(
                "profile_failed", "MySQL profiling could not be completed", retryable=True
            ) from None
        return ProfileResult(fields=tuple(profiles))

    def explain(self, query: ValidatedNativeQuery, limits: QueryLimits) -> ExplainResult:
        self._check_query_boundary(query)
        try:
            with self._connection(limits.timeout_ms) as connection:
                self._prepare_transaction(connection, limits.timeout_ms)
                with connection.cursor() as cursor:
                    cursor.execute(f"EXPLAIN FORMAT=JSON {query.text}")
                    rows = cursor.fetchall()
            return ExplainResult(plan=tuple(str(row[0]) for row in rows))
        except pymysql.err.OperationalError as exc:
            code = int(exc.args[0]) if exc.args and isinstance(exc.args[0], int) else 0
            if code in {3024, 2013}:
                raise ConnectorError(
                    "query_timeout", "MySQL query timed out", retryable=True
                ) from None
            if code in {1142, 1290, 1792}:
                raise ConnectorError(
                    "query_blocked", "MySQL rejected a non-read-only query"
                ) from None
            raise ConnectorError("query_invalid", "MySQL could not explain the query") from None
        except pymysql.MySQLError:
            raise ConnectorError("query_invalid", "MySQL could not explain the query") from None

    def execute_readonly(self, query: ValidatedNativeQuery, limits: QueryLimits) -> QueryResult:
        self._check_query_boundary(query)
        try:
            with self._connection(limits.timeout_ms) as connection:
                self._prepare_transaction(connection, limits.timeout_ms)
                with connection.cursor() as cursor:
                    cursor.execute(query.text)
                    if cursor.description is None:
                        raise ConnectorError(
                            "query_blocked", "Query did not produce a read-only result"
                        )
                    rows = cursor.fetchmany(limits.max_rows + 1)
                    columns = tuple(str(column[0]) for column in cursor.description)
            return QueryResult(
                columns=columns,
                rows=tuple(
                    tuple(_result_value(value) for value in row)
                    for row in rows[: limits.max_rows]
                ),
                truncated=len(rows) > limits.max_rows,
            )
        except ConnectorError:
            raise
        except pymysql.err.OperationalError as exc:
            code = int(exc.args[0]) if exc.args and isinstance(exc.args[0], int) else 0
            if code in {3024, 2013}:
                raise ConnectorError(
                    "query_timeout", "MySQL query timed out", retryable=True
                ) from None
            if code in {1142, 1290, 1792}:
                raise ConnectorError(
                    "query_blocked", "MySQL rejected a non-read-only query"
                ) from None
            raise ConnectorError("query_invalid", "MySQL could not execute the query") from None
        except pymysql.MySQLError:
            raise ConnectorError("query_invalid", "MySQL could not execute the query") from None

    def close(self) -> None:
        return None
