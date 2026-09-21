"""PostgreSQL connector with read-only, schema, timeout, and row boundaries."""

import re
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import date, datetime
from decimal import Decimal
from typing import Any

import psycopg
from psycopg import sql
from psycopg.errors import InsufficientPrivilege, QueryCanceled, ReadOnlySqlTransaction

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

IDENTIFIER = re.compile(r"^[A-Za-z_][A-Za-z0-9_$]{0,62}$")
SSL_MODES = {"disable", "prefer", "require", "verify-ca", "verify-full"}


def _json_value(value: Any) -> Any:
    if isinstance(value, (date, datetime, Decimal)):
        return str(value)
    return value


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
    capabilities = ConnectorCapabilities(
        dialect="postgresql",
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
            connection = psycopg.connect(
                host=self.config.host,
                port=self.config.port,
                dbname=self.config.database,
                user=self.config.username,
                password=self.config.password,
                sslmode=self.config.ssl_mode,
                connect_timeout=self.connect_timeout_seconds,
                application_name="insightmesh",
            )
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
                "connection_failed",
                "PostgreSQL connection could not be established",
                retryable=True,
            ) from None
        with connection:
            yield connection

    def _prepare_transaction(self, connection: psycopg.Connection[Any], timeout_ms: int) -> None:
        connection.execute("SET TRANSACTION READ ONLY")
        connection.execute("SELECT set_config('statement_timeout', %s, true)", (str(timeout_ms),))
        identifiers = sql.SQL(", ").join(
            sql.Identifier(name) for name in self.config.allowed_schemas
        )
        connection.execute(sql.SQL("SET LOCAL search_path TO {}").format(identifiers))

    def _check_query_boundary(self, query: ValidatedNativeQuery) -> None:
        if query.dialect != "postgresql":
            raise ConnectorError("dialect_mismatch", "Query dialect does not match PostgreSQL")
        if not query.referenced_schemas.issubset(set(self.config.allowed_schemas)):
            raise ConnectorError(
                "schema_blocked", "Query references a schema outside the allowlist"
            )

    def test_connection(self) -> ConnectionTestResult:
        with self._connection() as connection, connection.transaction():
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
        with self._connection() as connection, connection.transaction():
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
                    SELECT ns.nspname, cls.relname, att.attname,
                           CASE con.contype WHEN 'p' THEN 'PRIMARY KEY' ELSE 'UNIQUE' END
                    FROM pg_catalog.pg_constraint con
                    JOIN pg_catalog.pg_class cls ON cls.oid = con.conrelid
                    JOIN pg_catalog.pg_namespace ns ON ns.oid = cls.relnamespace
                    JOIN LATERAL unnest(con.conkey) AS key(attnum) ON true
                    JOIN pg_catalog.pg_attribute att
                      ON att.attrelid = cls.oid AND att.attnum = key.attnum
                    WHERE ns.nspname = ANY(%s)
                      AND con.contype IN ('p', 'u')
                    """,
                (schema_filter,),
            ).fetchall()
            relationship_rows = connection.execute(
                """
                    SELECT con.conname,
                           source_ns.nspname, source_table.relname, source_att.attname,
                           target_ns.nspname, target_table.relname, target_att.attname
                    FROM pg_catalog.pg_constraint con
                    JOIN pg_catalog.pg_class source_table ON source_table.oid = con.conrelid
                    JOIN pg_catalog.pg_namespace source_ns
                      ON source_ns.oid = source_table.relnamespace
                    JOIN pg_catalog.pg_class target_table ON target_table.oid = con.confrelid
                    JOIN pg_catalog.pg_namespace target_ns
                      ON target_ns.oid = target_table.relnamespace
                    JOIN LATERAL unnest(con.conkey) WITH ORDINALITY
                      AS source_key(attnum, position) ON true
                    JOIN LATERAL unnest(con.confkey) WITH ORDINALITY
                      AS target_key(attnum, position)
                      ON target_key.position = source_key.position
                    JOIN pg_catalog.pg_attribute source_att
                      ON source_att.attrelid = source_table.oid
                     AND source_att.attnum = source_key.attnum
                    JOIN pg_catalog.pg_attribute target_att
                      ON target_att.attrelid = target_table.oid
                     AND target_att.attnum = target_key.attnum
                    WHERE con.contype = 'f'
                      AND source_ns.nspname = ANY(%s)
                      AND target_ns.nspname = ANY(%s)
                    ORDER BY con.conname, source_key.position
                    """,
                (schema_filter, schema_filter),
            ).fetchall()

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
            with self._connection() as connection, connection.transaction():
                self._prepare_transaction(connection, policy.timeout_ms)
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

                        column = sql.Identifier(field.name)
                        sampled = sql.SQL(
                            "SELECT {column} AS value FROM {schema}.{table} LIMIT %s"
                        ).format(
                            column=column,
                            schema=sql.Identifier(entity.schema_name),
                            table=sql.Identifier(entity.name),
                        )
                        aggregate_parts = [
                            sql.SQL("COUNT(*)::bigint AS sample_size"),
                            sql.SQL("COUNT(*) FILTER (WHERE value IS NULL)::bigint AS null_count"),
                        ]
                        supports_distinct = field.normalized_type in {
                            "number",
                            "temporal",
                            "string",
                            "boolean",
                        }
                        aggregate_parts.append(
                            sql.SQL("COUNT(DISTINCT value)::bigint AS distinct_count")
                            if supports_distinct
                            else sql.SQL("NULL::bigint AS distinct_count")
                        )
                        if field.normalized_type in {"number", "temporal"}:
                            aggregate_parts.extend(
                                [sql.SQL("MIN(value) AS minimum"), sql.SQL("MAX(value) AS maximum")]
                            )
                        query = sql.SQL("SELECT {aggregates} FROM ({sampled}) AS bounded").format(
                            aggregates=sql.SQL(", ").join(aggregate_parts), sampled=sampled
                        )
                        row = connection.execute(query, (policy.max_rows_per_entity,)).fetchone()
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
                            values_query = sql.SQL(
                                "SELECT DISTINCT value FROM ({sampled}) AS bounded "
                                "WHERE value IS NOT NULL ORDER BY value LIMIT %s"
                            ).format(sampled=sampled)
                            values = connection.execute(
                                values_query,
                                (policy.max_rows_per_entity, policy.enum_max_distinct),
                            ).fetchall()
                            statistics["candidate_values"] = [
                                _json_value(item[0]) for item in values
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
        except QueryCanceled:
            raise ConnectorError(
                "profile_timeout", "PostgreSQL profiling timed out", retryable=True
            ) from None
        except psycopg.Error:
            raise ConnectorError(
                "profile_failed", "PostgreSQL profiling could not be completed", retryable=True
            ) from None
        return ProfileResult(fields=tuple(profiles))

    def explain(self, query: ValidatedNativeQuery, limits: QueryLimits) -> ExplainResult:
        self._check_query_boundary(query)
        try:
            with self._connection() as connection, connection.transaction():
                self._prepare_transaction(connection, limits.timeout_ms)
                rows = connection.execute(f"EXPLAIN {query.text}").fetchall()
                return ExplainResult(plan=tuple(str(row[0]) for row in rows))
        except QueryCanceled:
            raise ConnectorError(
                "query_timeout", "PostgreSQL query timed out", retryable=True
            ) from None
        except (InsufficientPrivilege, ReadOnlySqlTransaction):
            raise ConnectorError(
                "query_blocked", "PostgreSQL rejected a non-read-only query"
            ) from None
        except psycopg.Error:
            raise ConnectorError(
                "query_invalid", "PostgreSQL could not explain the query"
            ) from None

    def execute_readonly(self, query: ValidatedNativeQuery, limits: QueryLimits) -> QueryResult:
        self._check_query_boundary(query)
        try:
            with self._connection() as connection, connection.transaction():
                self._prepare_transaction(connection, limits.timeout_ms)
                cursor = connection.execute(query.text)
                if cursor.description is None:
                    raise ConnectorError(
                        "query_blocked", "Query did not produce a read-only result"
                    )
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
            raise ConnectorError(
                "query_timeout", "PostgreSQL query timed out", retryable=True
            ) from None
        except (InsufficientPrivilege, ReadOnlySqlTransaction):
            raise ConnectorError(
                "query_blocked", "PostgreSQL rejected a non-read-only query"
            ) from None
        except psycopg.Error:
            raise ConnectorError(
                "query_invalid", "PostgreSQL could not execute the query"
            ) from None

    def close(self) -> None:
        return None
