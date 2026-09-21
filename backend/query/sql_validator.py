"""Deterministic PostgreSQL AST policy backed by SQLGlot."""

from dataclasses import dataclass

from sqlglot import exp, parse
from sqlglot.errors import ParseError

from api.schemas.retrieval import RetrievedEntity
from connectors.base import ValidatedNativeQuery

UNSAFE_NODE_KEYS = {
    "alter",
    "analyze",
    "attach",
    "cache",
    "command",
    "copy",
    "create",
    "delete",
    "detach",
    "drop",
    "grant",
    "insert",
    "into",
    "load_data",
    "lock",
    "merge",
    "refresh",
    "revoke",
    "set",
    "transaction",
    "truncate",
    "uncache",
    "update",
    "use",
}
DISALLOWED_FUNCTIONS = {
    "dblink",
    "dblink_exec",
    "lo_export",
    "lo_import",
    "nextval",
    "pg_ls_dir",
    "pg_cancel_backend",
    "pg_read_binary_file",
    "pg_read_file",
    "pg_sleep",
    "pg_terminate_backend",
    "set_config",
    "setval",
}


@dataclass(frozen=True)
class SQLValidationResult:
    valid: bool
    unsafe: bool
    error_code: str | None
    issues: tuple[str, ...]
    query: ValidatedNativeQuery | None = None


def _invalid(code: str, issue: str, *, unsafe: bool = False) -> SQLValidationResult:
    return SQLValidationResult(False, unsafe, code, (issue,))


def validate_postgres_sql(
    sql: str,
    entities: list[RetrievedEntity],
    allowed_schemas: set[str],
) -> SQLValidationResult:
    try:
        statements = [item for item in parse(sql, read="postgres") if item is not None]
    except ParseError:
        return _invalid("sql_parse_failed", "SQL could not be parsed")
    if len(statements) != 1:
        return _invalid(
            "multiple_statements_blocked",
            "Exactly one SQL statement is allowed",
            unsafe=True,
        )
    statement = statements[0]
    if not isinstance(statement, exp.Query):
        return _invalid("non_select_blocked", "Only SELECT queries are allowed", unsafe=True)
    for node in statement.walk():
        if node.key.lower() in UNSAFE_NODE_KEYS:
            return _invalid(
                "unsafe_sql_blocked",
                f"SQL operation {node.key.upper()} is not allowed",
                unsafe=True,
            )
        if isinstance(node, exp.Func):
            function_name = (
                node.name if isinstance(node, exp.Anonymous) else node.key
            ).lower()
            if function_name in DISALLOWED_FUNCTIONS or function_name.startswith(
                ("dblink", "pg_advisory_")
            ):
                return _invalid(
                    "unsafe_function_blocked",
                    f"SQL function {function_name} is not allowed",
                    unsafe=True,
                )

    entity_by_qualified = {
        (entity.schema_name.lower(), entity.name.lower()): entity for entity in entities
    }
    entities_by_name: dict[str, list[RetrievedEntity]] = {}
    for entity in entities:
        entities_by_name.setdefault(entity.name.lower(), []).append(entity)
    cte_fields = {
        cte.alias_or_name.lower(): {
            item.alias_or_name.lower()
            for item in cte.this.selects
            if item.alias_or_name
        }
        for cte in statement.find_all(exp.CTE)
    }
    cte_names = set(cte_fields)
    real_tables: list[tuple[exp.Table, RetrievedEntity]] = []
    referenced_schemas: set[str] = set()
    aliases_for_ctes: set[str] = set()
    alias_fields_for_ctes: dict[str, set[str]] = {}
    for table in statement.find_all(exp.Table):
        table_name = table.name.lower()
        alias = table.alias_or_name.lower()
        if table_name in cte_names:
            aliases_for_ctes.add(alias)
            alias_fields_for_ctes[alias] = cte_fields[table_name]
            continue
        schema_name = table.db.lower() if table.db else ""
        if table.catalog:
            return _invalid(
                "cross_database_blocked",
                "Cross-database references are not allowed",
                unsafe=True,
            )
        if schema_name and schema_name not in allowed_schemas:
            return _invalid(
                "schema_blocked",
                "SQL references a schema outside the allowlist",
                unsafe=True,
            )
        candidates = (
            [entity_by_qualified[(schema_name, table_name)]]
            if schema_name and (schema_name, table_name) in entity_by_qualified
            else ([] if schema_name else entities_by_name.get(table_name, []))
        )
        if len(candidates) != 1:
            return _invalid(
                "unknown_table",
                f"SQL references an unavailable table: {table.name}",
            )
        entity = candidates[0]
        real_tables.append((table, entity))
        referenced_schemas.add(schema_name or entity.schema_name.lower())

    if not real_tables:
        return _invalid("missing_table", "SQL must reference at least one retrieved table")

    alias_fields = {
        table.alias_or_name.lower(): {field.name.lower() for field in entity.fields}
        for table, entity in real_tables
    }
    available_fields = set().union(*alias_fields.values(), *alias_fields_for_ctes.values())
    projection_aliases = {
        item.alias.lower()
        for item in statement.selects
        if item.alias
    }
    for column in statement.find_all(exp.Column):
        name = column.name.lower()
        if name == "*":
            continue
        qualifier = column.table.lower() if column.table else ""
        if qualifier in aliases_for_ctes or qualifier in cte_names:
            cte_available_fields = alias_fields_for_ctes.get(
                qualifier, cte_fields.get(qualifier, set())
            )
            if name not in cte_available_fields:
                return _invalid(
                    "unknown_column",
                    f"SQL references an unavailable CTE column: {column.sql(dialect='postgres')}",
                )
            continue
        if qualifier:
            qualified_fields = alias_fields.get(qualifier)
            if qualified_fields is None or name not in qualified_fields:
                return _invalid(
                    "unknown_column",
                    f"SQL references an unavailable column: {column.sql(dialect='postgres')}",
                )
        elif name not in available_fields and name not in projection_aliases:
            return _invalid(
                "unknown_column",
                f"SQL references an unavailable column: {column.name}",
            )

    return SQLValidationResult(
        valid=True,
        unsafe=False,
        error_code=None,
        issues=(),
        query=ValidatedNativeQuery(
            text=sql.strip(),
            dialect="postgresql",
            referenced_schemas=frozenset(referenced_schemas),
        ),
    )
