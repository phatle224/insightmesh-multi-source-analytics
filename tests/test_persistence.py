from sqlalchemy import inspect, select

from api.settings import get_settings
from persistence.credentials import CredentialCipher
from persistence.database import SessionLocal, engine
from persistence.models import Datasource, DatasourceCredential

EXPECTED_TABLES = {
    "alembic_version",
    "dashboard_widgets",
    "dashboards",
    "datasource_credentials",
    "datasources",
    "embeddings",
    "entities",
    "fields",
    "metric_candidates",
    "profile_statistics",
    "query_examples",
    "query_runs",
    "relationships",
    "semantic_terms",
}


def test_all_phase_two_tables_are_migrated() -> None:
    assert set(inspect(engine).get_table_names()) >= EXPECTED_TABLES


def test_credentials_are_encrypted_at_persistence_boundary() -> None:
    plaintext_password = "test-password-never-store"
    cipher = CredentialCipher(get_settings().credential_encryption_key.get_secret_value())
    datasource = Datasource(
        name="phase-two-test-source",
        source_type="postgresql",
        database_name="analytics",
        safe_host="db.internal",
        port=5432,
    )

    with SessionLocal() as session:
        session.add(datasource)
        session.flush()
        credential = DatasourceCredential(
            datasource_id=datasource.id,
            encrypted_payload=cipher.encrypt(
                {"username": "reader", "password": plaintext_password}
            ),
        )
        session.add(credential)
        session.flush()

        stored = session.scalar(
            select(DatasourceCredential).where(DatasourceCredential.datasource_id == datasource.id)
        )
        assert stored is not None
        assert plaintext_password.encode() not in stored.encrypted_payload
        assert cipher.decrypt(stored.encrypted_payload) == {
            "password": plaintext_password,
            "username": "reader",
        }
        session.rollback()
