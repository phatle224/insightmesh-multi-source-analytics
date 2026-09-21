from typing import Any
from uuid import uuid4

from sqlalchemy import delete

from persistence.database import SessionLocal
from persistence.models import (
    Datasource,
    Embedding,
    Entity,
    Field,
    MetricCandidate,
    QueryRun,
    Relationship,
    SemanticTerm,
)
from semantic.provider import StructuredGenerationRequest
from services.retrieval import retrieve_context


class QueryEmbeddingProvider:
    def generate_structured(self, request: StructuredGenerationRequest) -> dict[str, Any]:
        raise AssertionError("Retrieval must not generate text")

    def embed(self, inputs: list[str]) -> list[list[float]]:
        assert inputs == ["revenue by product"]
        return [[1.0, 0.0, 0.0]]

    def close(self) -> None:
        return None


class StaticEmbeddingProvider:
    def generate_structured(self, request: StructuredGenerationRequest) -> dict[str, Any]:
        raise AssertionError("Retrieval must not generate text")

    def embed(self, inputs: list[str]) -> list[list[float]]:
        assert len(inputs) == 1
        return [[1.0, 0.0, 0.0]]

    def close(self) -> None:
        return None


def test_retrieval_is_datasource_scoped_expands_join_path_and_records_context() -> None:
    datasource_id = None
    with SessionLocal() as session:
        datasource = Datasource(
            name=f"retrieval-{uuid4()}",
            source_type="postgresql",
            database_name="analytics",
            safe_host="db",
            port=5432,
            semantic_status="ready",
        )
        session.add(datasource)
        session.flush()
        datasource_id = datasource.id

        other_datasource = Datasource(
            name=f"retrieval-other-{uuid4()}",
            source_type="postgresql",
            database_name="other_analytics",
            safe_host="other-db",
            port=5432,
            semantic_status="ready",
        )
        session.add(other_datasource)
        session.flush()
        other_entity = Entity(
            datasource_id=other_datasource.id,
            schema_name="public",
            name="private_ledger",
            entity_type="table",
            description="A closer vector from another datasource",
            metadata_json={},
        )
        session.add(other_entity)
        session.flush()
        session.add(
            Embedding(
                datasource_id=other_datasource.id,
                object_type="entity",
                object_id=other_entity.id,
                content="revenue by product",
                embedding=[1.0, 0.0, 0.0],
                metadata_json={},
            )
        )

        orders = Entity(
            datasource_id=datasource.id,
            schema_name="public",
            name="orders",
            entity_type="table",
            description="Customer orders",
            metadata_json={},
        )
        order_items = Entity(
            datasource_id=datasource.id,
            schema_name="public",
            name="order_items",
            entity_type="table",
            description="Order line items",
            metadata_json={},
        )
        products = Entity(
            datasource_id=datasource.id,
            schema_name="public",
            name="products",
            entity_type="table",
            description="Products sold",
            metadata_json={},
        )
        session.add_all([orders, order_items, products])
        session.flush()

        orders_id = Field(
            entity_id=orders.id,
            name="id",
            native_type="integer",
            normalized_type="number",
            nullable=False,
            ordinal=1,
            metadata_json={"primary_key": True, "unique": True},
        )
        item_order_id = Field(
            entity_id=order_items.id,
            name="order_id",
            native_type="integer",
            normalized_type="number",
            nullable=False,
            ordinal=1,
            metadata_json={"primary_key": True, "unique": False},
        )
        item_product_id = Field(
            entity_id=order_items.id,
            name="product_id",
            native_type="integer",
            normalized_type="number",
            nullable=False,
            ordinal=2,
            metadata_json={"primary_key": True, "unique": False},
        )
        products_id = Field(
            entity_id=products.id,
            name="id",
            native_type="integer",
            normalized_type="number",
            nullable=False,
            ordinal=1,
            metadata_json={"primary_key": True, "unique": True},
        )
        session.add_all([orders_id, item_order_id, item_product_id, products_id])
        session.flush()
        session.add_all(
            [
                Relationship(
                    datasource_id=datasource.id,
                    source_entity_id=order_items.id,
                    target_entity_id=orders.id,
                    source_field_id=item_order_id.id,
                    target_field_id=orders_id.id,
                    relationship_type="foreign_key",
                    confidence=1,
                    source="introspection",
                ),
                Relationship(
                    datasource_id=datasource.id,
                    source_entity_id=order_items.id,
                    target_entity_id=products.id,
                    source_field_id=item_product_id.id,
                    target_field_id=products_id.id,
                    relationship_type="foreign_key",
                    confidence=1,
                    source="introspection",
                ),
            ]
        )
        session.add_all(
            [
                Embedding(
                    datasource_id=datasource.id,
                    object_type="entity",
                    object_id=orders.id,
                    content="orders revenue",
                    embedding=[1.0, 0.0, 0.0],
                    metadata_json={},
                ),
                Embedding(
                    datasource_id=datasource.id,
                    object_type="entity",
                    object_id=products.id,
                    content="products",
                    embedding=[0.8, 0.2, 0.0],
                    metadata_json={},
                ),
                Embedding(
                    datasource_id=datasource.id,
                    object_type="entity",
                    object_id=order_items.id,
                    content="line items",
                    embedding=[0.0, 1.0, 0.0],
                    metadata_json={},
                ),
                SemanticTerm(
                    datasource_id=datasource.id,
                    entity_id=orders.id,
                    term="revenue",
                    description="Order revenue",
                    confidence=0.9,
                    source="llm_inferred",
                ),
                MetricCandidate(
                    datasource_id=datasource.id,
                    entity_id=order_items.id,
                    name="revenue",
                    expression="SUM(quantity * unit_price)",
                    description="Candidate revenue",
                    confidence=0.8,
                    source="llm_inferred",
                    metadata_json={"verified": False},
                ),
            ]
        )
        session.commit()

        result = retrieve_context(
            session,
            datasource.id,
            "revenue by product",
            top_k=2,
            provider=QueryEmbeddingProvider(),
        )

        assert [item.name for item in result.entities[:2]] == ["orders", "products"]
        assert all(item.name != "private_ledger" for item in result.entities)
        expanded = next(item for item in result.entities if item.name == "order_items")
        assert expanded.selection_source == "relationship_expansion"
        assert len(result.relationships) == 2
        assert all(item.source_field and item.target_field for item in result.relationships)
        assert any(item.startswith("relationship:") for item in result.context_ids)
        stored_run = session.get(QueryRun, result.run_id)
        assert stored_run is not None
        assert stored_run.status == "retrieve_context"
        assert stored_run.retrieved_context_ids == result.context_ids

        vector = retrieve_context(
            session,
            datasource.id,
            "products",
            top_k=1,
            provider=StaticEmbeddingProvider(),
            strategy="vector",
        )
        hybrid = retrieve_context(
            session,
            datasource.id,
            "products",
            top_k=1,
            provider=StaticEmbeddingProvider(),
            strategy="hybrid",
        )
        assert vector.entities[0].name == "orders"
        assert vector.entities[0].selection_source == "semantic"
        assert hybrid.entities[0].name == "products"
        assert hybrid.entities[0].selection_source == "hybrid"
        assert hybrid.entities[0].lexical_score is not None
        assert hybrid.entities[0].lexical_score > 0
        assert hybrid.entities[0].fused_score is not None
        assert hybrid.strategy == "hybrid"
        assert hybrid.config_version

        session.execute(delete(Datasource).where(Datasource.id == datasource.id))
        session.execute(delete(Datasource).where(Datasource.id == other_datasource.id))
        session.commit()

    assert datasource_id is not None
