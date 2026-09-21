import json
import os
from typing import Any
from uuid import uuid4

import httpx
from fastapi.testclient import TestClient
from sqlalchemy import delete, func, select

from api.main import app
from persistence.database import SessionLocal
from persistence.models import (
    Datasource,
    Embedding,
    MetricCandidate,
    SemanticManifest,
    SemanticTerm,
)
from semantic.provider import (
    FallbackProvider,
    GeminiProvider,
    OpenRouterProvider,
    ProviderError,
    StructuredGenerationRequest,
)
from services import datasources as datasource_service


class FakeProvider:
    def __init__(self) -> None:
        self.requests: list[StructuredGenerationRequest] = []

    def generate_structured(self, request: StructuredGenerationRequest) -> dict[str, Any]:
        self.requests.append(request)
        fields = request.user_payload["fields"]
        return {
            "entity_description": f"Analytics entity {request.user_payload['entity']}",
            "business_terms": [request.user_payload["entity"]],
            "fields": [
                {
                    "name": field["name"],
                    "description": f"Field {field['name']}",
                    "business_terms": [],
                    "confidence": 0.8,
                }
                for field in fields
            ],
            "metrics": [
                {
                    "name": "row count",
                    "expression": "COUNT(*)",
                    "description": "Candidate row count",
                    "confidence": 0.7,
                }
            ],
            "confidence": 0.8,
        }

    def embed(self, inputs: list[str]) -> list[list[float]]:
        return [[0.1, 0.2, 0.3] for _ in inputs]

    def close(self) -> None:
        return None


def test_openrouter_uses_strict_structured_output_and_embedding_dimensions() -> None:
    requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        if request.url.path.endswith("/chat/completions"):
            return httpx.Response(
                200,
                json={"choices": [{"message": {"content": '{"ok": true}'}}]},
            )
        return httpx.Response(
            200,
            json={"data": [{"index": 0, "embedding": [0.1, 0.2, 0.3]}]},
        )

    provider = OpenRouterProvider(
        api_key="test-key",
        base_url="https://openrouter.test/api/v1",
        llm_model="test/chat",
        embedding_model="test/embed",
        embedding_dimensions=3,
        timeout_seconds=2,
    )
    provider._client.close()
    provider._client = httpx.Client(
        base_url="https://openrouter.test/api/v1",
        transport=httpx.MockTransport(handler),
    )
    generated = provider.generate_structured(
        StructuredGenerationRequest(
            system_prompt="Return JSON",
            user_payload={"safe": True, "entity": "test", "fields": []},
            schema_name="test_schema",
            json_schema={"type": "object", "properties": {"ok": {"type": "boolean"}}},
        )
    )
    vectors = provider.embed(["safe metadata"])
    provider.close()

    assert generated == {"ok": True}
    assert vectors == [[0.1, 0.2, 0.3]]
    chat_body = json.loads(requests[0].content)
    assert chat_body["response_format"]["type"] == "json_schema"
    assert chat_body["response_format"]["json_schema"]["strict"] is True
    assert chat_body["provider"]["require_parameters"] is True
    embedding_body = json.loads(requests[1].content)
    assert embedding_body["dimensions"] == 3


def test_gemini_uses_direct_generate_content_and_falls_back_on_rate_limit() -> None:
    primary = GeminiProvider(
        api_key="gemini-test",
        base_url="https://generativelanguage.test",
        model="gemini-2.5-flash",
        timeout_seconds=2,
    )
    fallback = FakeProvider()
    calls = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        return httpx.Response(429, json={"error": {"status": "RESOURCE_EXHAUSTED"}})

    primary._client.close()
    primary._client = httpx.Client(
        base_url="https://generativelanguage.test",
        transport=httpx.MockTransport(handler),
    )
    provider = FallbackProvider(primary, fallback)
    output = provider.generate_structured(
        StructuredGenerationRequest(
            system_prompt="Return JSON",
            user_payload={"safe": True, "entity": "test", "fields": []},
            schema_name="test_schema",
            json_schema={"type": "object", "properties": {"ok": {"type": "boolean"}}},
        )
    )
    provider.close()

    assert output["entity_description"].startswith("Analytics entity")
    assert calls == 2
    assert len(fallback.requests) == 1


def test_gemini_auth_failure_does_not_fallback() -> None:
    primary = GeminiProvider(
        api_key="gemini-test",
        base_url="https://generativelanguage.test",
        model="gemini-2.5-flash",
        timeout_seconds=2,
    )
    fallback = FakeProvider()
    primary._client.close()
    primary._client = httpx.Client(
        base_url="https://generativelanguage.test",
        transport=httpx.MockTransport(
            lambda request: httpx.Response(401, json={"error": {"status": "UNAUTHENTICATED"}})
        ),
    )
    provider = FallbackProvider(primary, fallback)
    try:
        provider.generate_structured(
            StructuredGenerationRequest(
                system_prompt="Return JSON",
                user_payload={"safe": True},
                schema_name="test_schema",
                json_schema={"type": "object"},
            )
        )
    except ProviderError as error:
        assert error.code == "provider_auth_failed"
    else:
        raise AssertionError("Expected Gemini authentication failure")
    finally:
        provider.close()
    assert not fallback.requests


def test_refresh_builds_semantic_index_without_pii_values(monkeypatch: Any) -> None:
    provider = FakeProvider()
    monkeypatch.setattr(datasource_service, "build_semantic_provider", lambda settings: provider)
    client = TestClient(app)
    name = f"phase-five-{uuid4()}"
    response = client.post(
        "/api/v1/datasources",
        json={
            "name": name,
            "source_type": "postgresql",
            "host": "demo-postgres",
            "port": 5432,
            "database": "insightmesh_demo",
            "username": "demo_reader",
            "password": os.environ["DEMO_READER_PASSWORD"],
            "ssl_mode": "disable",
            "allowed_schemas": ["public"],
        },
    )
    assert response.status_code == 201, response.text
    detail = response.json()
    assert detail["semantic_status"] == "ready"
    assert detail["embedding_count"] == detail["entity_count"]
    assert detail["semantic_term_count"] > 0
    assert detail["metric_count"] > 0
    assert detail["relationships"]
    assert all(
        relationship["provenance"] == "declared"
        and relationship["confidence"] == 1.0
        and relationship["generation_eligible"] is True
        and relationship["source_field"]
        and relationship["target_field"]
        for relationship in detail["relationships"]
    )
    customer_payload = next(
        request.user_payload
        for request in provider.requests
        if request.user_payload["entity"] == "customers"
    )
    customer_name = next(
        field for field in customer_payload["fields"] if field["name"] == "customer_name"
    )
    assert customer_name["profile"] == {
        "excluded": True,
        "exclusion_reason": "possible_pii",
    }
    assert "Acme Retail" not in str(customer_payload)
    first_request_count = len(provider.requests)
    refresh_response = client.post(f"/api/v1/datasources/{detail['id']}/refresh")
    assert refresh_response.status_code == 200, refresh_response.text
    assert len(provider.requests) == first_request_count

    manifest_response = client.get(f"/api/v1/datasources/{detail['id']}/semantic-manifest")
    assert manifest_response.status_code == 200, manifest_response.text
    manifest = manifest_response.json()
    assert manifest["version"] == 1
    assert manifest["configuration"]["generation_provider"] == "gemini"
    assert manifest["configuration"]["generation_model"] == "gemini-2.5-flash"
    assert manifest["configuration"]["skill_versions"] == {
        "query-generation": "v1",
        "query-repair": "v1",
    }
    assert len(manifest["metadata_hash"]) == 64
    assert len(manifest["profile_hash"]) == 64
    customer_manifest = next(
        entity for entity in manifest["entities"] if entity["name"] == "customers"
    )
    customer_name_manifest = next(
        field for field in customer_manifest["fields"] if field["name"] == "customer_name"
    )
    assert customer_name_manifest["profile"] == {
        "excluded": True,
        "exclusion_reason": "possible_pii",
    }
    assert customer_manifest["embedding_artifact_id"]
    serialized_manifest = json.dumps(manifest)
    assert "Acme Retail" not in serialized_manifest
    manifest_keys: set[str] = set()

    def collect_keys(value: object) -> None:
        if isinstance(value, dict):
            for key, item in value.items():
                manifest_keys.add(str(key))
                collect_keys(item)
        elif isinstance(value, list):
            for item in value:
                collect_keys(item)

    collect_keys(manifest)
    assert {"embedding", "content", "encrypted_payload"}.isdisjoint(manifest_keys)
    assert all(
        relationship["provenance"] == "declared"
        and relationship["generation_eligible"] is True
        for relationship in manifest["relationships"]
    )

    with SessionLocal() as session:
        datasource = session.scalar(select(Datasource).where(Datasource.name == name))
        assert datasource is not None
        assert session.scalar(
            select(func.count()).select_from(Embedding).where(
                Embedding.datasource_id == datasource.id
            )
        ) == detail["entity_count"]
        assert session.scalar(
            select(func.count()).select_from(SemanticTerm).where(
                SemanticTerm.datasource_id == datasource.id
            )
        )
        assert session.scalar(
            select(func.count()).select_from(MetricCandidate).where(
                MetricCandidate.datasource_id == datasource.id
            )
        )
        assert session.scalar(
            select(func.count()).select_from(SemanticManifest).where(
                SemanticManifest.datasource_id == datasource.id
            )
        ) == 1
        term = session.scalar(
            select(SemanticTerm).where(SemanticTerm.datasource_id == datasource.id).limit(1)
        )
        assert term is not None
        term.description = f"{term.description} (reviewed)"
        second_manifest = datasource_service.create_semantic_manifest_snapshot(
            session, datasource
        )
        session.commit()
        assert second_manifest.version == 2
        manifests = session.scalars(
            select(SemanticManifest)
            .where(SemanticManifest.datasource_id == datasource.id)
            .order_by(SemanticManifest.version)
        ).all()
        assert [item.version for item in manifests] == [1, 2]
        assert manifests[0].manifest_hash != manifests[1].manifest_hash
        session.execute(delete(Datasource).where(Datasource.id == datasource.id))
        session.commit()
