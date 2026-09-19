"""Strict semantic-enrichment contract and privacy-safe request construction."""

from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from semantic.provider import LLMProvider, StructuredGenerationRequest


class EnrichedField(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: str
    description: str
    business_terms: list[str] = Field(max_length=8)
    confidence: float = Field(ge=0, le=1)


class MetricSuggestion(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: str
    expression: str
    description: str
    confidence: float = Field(ge=0, le=1)


class EntityEnrichment(BaseModel):
    model_config = ConfigDict(extra="forbid")
    entity_description: str
    business_terms: list[str] = Field(max_length=8)
    fields: list[EnrichedField]
    metrics: list[MetricSuggestion] = Field(max_length=8)
    confidence: float = Field(ge=0, le=1)


SYSTEM_PROMPT = """You enrich database metadata for retrieval.
Use only supplied metadata and derived statistics. Do not infer personal data values.
Descriptions and metric candidates are suggestions, not verified business truth.
Return exactly the requested JSON schema. Keep expressions datasource-native and read-only."""


def enrich_entity(provider: LLMProvider, payload: dict[str, Any]) -> EntityEnrichment:
    response = provider.generate_structured(
        StructuredGenerationRequest(
            system_prompt=SYSTEM_PROMPT,
            user_payload=payload,
            schema_name="entity_semantic_enrichment",
            json_schema=EntityEnrichment.model_json_schema(),
        )
    )
    return EntityEnrichment.model_validate(response)
