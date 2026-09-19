import os
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import delete, func, select, update

from api.main import app
from persistence.database import SessionLocal
from persistence.models import Datasource, DatasourceCredential


def demo_payload(name: str) -> dict[str, object]:
    return {
        "name": name,
        "source_type": "postgresql",
        "host": "demo-postgres",
        "port": 5432,
        "database": "insightmesh_demo",
        "username": "demo_reader",
        "password": os.environ["DEMO_READER_PASSWORD"],
        "ssl_mode": "disable",
        "allowed_schemas": ["public"],
    }


def test_datasource_onboarding_lifecycle_and_secret_boundary(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr("services.datasources.build_semantic_provider", lambda settings: None)
    client = TestClient(app)
    name = f"phase-four-{uuid4()}"
    payload = demo_payload(name)

    with SessionLocal() as session:
        count_before = session.scalar(select(func.count()).select_from(Datasource))
        active_before = session.scalars(
            select(Datasource.id).where(Datasource.is_active.is_(True))
        ).all()

    test_response = client.post("/api/v1/datasources/test", json=payload)
    assert test_response.status_code == 200
    assert test_response.json()["read_only_transaction"] is True
    with SessionLocal() as session:
        assert session.scalar(select(func.count()).select_from(Datasource)) == count_before

    create_response = client.post("/api/v1/datasources", json=payload)
    assert create_response.status_code == 201, create_response.text
    created = create_response.json()
    datasource_id = created["id"]
    assert created["status"] == "ready"
    assert created["entity_count"] >= 6
    assert created["relationship_count"] >= 4
    assert created["profile_count"] > 0
    assert created["pii_excluded_count"] >= 1
    assert created["semantic_status"] == "configuration_required"
    assert created["semantic_error_code"] == "gemini_api_key_missing"
    assert "password" not in create_response.text
    assert "username" not in create_response.text
    assert str(payload["password"]) not in create_response.text

    list_response = client.get("/api/v1/datasources")
    assert list_response.status_code == 200
    assert any(item["id"] == datasource_id for item in list_response.json())

    detail_response = client.get(f"/api/v1/datasources/{datasource_id}")
    assert detail_response.status_code == 200
    assert any(entity["name"] == "orders" for entity in detail_response.json()["entities"])

    status_response = client.get(
        f"/api/v1/datasources/{datasource_id}/onboarding-status"
    )
    assert status_response.status_code == 200
    assert status_response.json()["status"] == "ready"

    activate_response = client.post(f"/api/v1/datasources/{datasource_id}/activate")
    assert activate_response.status_code == 200
    assert activate_response.json()["is_active"] is True

    refresh_response = client.post(f"/api/v1/datasources/{datasource_id}/refresh")
    assert refresh_response.status_code == 200
    assert refresh_response.json()["status"] == "ready"

    persisted_id = UUID(datasource_id)
    with SessionLocal() as session:
        credential = session.get(DatasourceCredential, persisted_id)
        assert credential is not None
        assert str(payload["password"]).encode() not in credential.encrypted_payload
        session.execute(delete(Datasource).where(Datasource.id == persisted_id))
        if active_before:
            session.execute(
                update(Datasource)
                .where(Datasource.id.in_(active_before))
                .values(is_active=True)
            )
        session.commit()
