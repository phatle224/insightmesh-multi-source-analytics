from connectors.mysql import MySQLConnector
from connectors.postgres import PostgresConnector


def test_supported_connectors_publish_the_common_capability_contract() -> None:
    for connector_type, dialect in (
        (PostgresConnector, "postgresql"),
        (MySQLConnector, "mysql"),
    ):
        capabilities = connector_type.capabilities
        assert capabilities.dialect == dialect
        assert capabilities.supports_explain is True
        assert capabilities.supports_read_only_transactions is True
        assert capabilities.supports_local_profiling is True
