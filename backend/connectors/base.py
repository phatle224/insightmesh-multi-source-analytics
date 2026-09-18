from dataclasses import dataclass, field
from typing import Any, Protocol


class ConnectorError(RuntimeError):
    def __init__(self, code: str, safe_message: str, *, retryable: bool = False) -> None:
        super().__init__(safe_message)
        self.code = code
        self.safe_message = safe_message
        self.retryable = retryable


@dataclass(frozen=True)
class ConnectionConfig:
    host: str
    port: int
    database: str
    username: str
    password: str
    ssl_mode: str = "prefer"
    allowed_schemas: tuple[str, ...] = ("public",)


@dataclass(frozen=True)
class ConnectionTestResult:
    database: str
    server_version: str
    read_only_transaction: bool


@dataclass(frozen=True)
class RawField:
    name: str
    native_type: str
    normalized_type: str
    nullable: bool
    ordinal: int
    primary_key: bool = False
    unique: bool = False


@dataclass(frozen=True)
class RawEntity:
    schema_name: str
    name: str
    entity_type: str
    fields: tuple[RawField, ...]


@dataclass(frozen=True)
class RawRelationship:
    name: str
    source_schema: str
    source_entity: str
    source_field: str
    target_schema: str
    target_entity: str
    target_field: str


@dataclass(frozen=True)
class RawDataSourceMetadata:
    entities: tuple[RawEntity, ...]
    relationships: tuple[RawRelationship, ...]


@dataclass(frozen=True)
class QueryLimits:
    timeout_ms: int
    max_rows: int


@dataclass(frozen=True)
class ValidatedNativeQuery:
    text: str
    dialect: str
    referenced_schemas: frozenset[str] = field(default_factory=frozenset)


@dataclass(frozen=True)
class QueryResult:
    columns: tuple[str, ...]
    rows: tuple[tuple[Any, ...], ...]
    truncated: bool


@dataclass(frozen=True)
class ExplainResult:
    plan: tuple[str, ...]


class DataSourceConnector(Protocol):
    def test_connection(self) -> ConnectionTestResult: ...

    def introspect(self) -> RawDataSourceMetadata: ...

    def explain(self, query: ValidatedNativeQuery, limits: QueryLimits) -> ExplainResult: ...

    def execute_readonly(
        self, query: ValidatedNativeQuery, limits: QueryLimits
    ) -> QueryResult: ...

    def close(self) -> None: ...
