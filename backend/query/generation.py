"""Structured SQL generation and repair using static dialect-specific assets."""

from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from api.schemas.retrieval import RetrievalResponse
from semantic.provider import LLMProvider, StructuredGenerationRequest
from skills.registry import get_skill


class GeneratedSQL(BaseModel):
    model_config = ConfigDict(extra="forbid")

    sql: str
    expected_columns: list[str] = Field(max_length=50)


def _context_payload(context: RetrievalResponse, dialect: str) -> dict[str, Any]:
    return {
        "datasource_type": dialect,
        "entities": [
            {
                "schema": entity.schema_name,
                "name": entity.name,
                "description": entity.description,
                "business_terms": entity.business_terms,
                "fields": [
                    {
                        "name": field.name,
                        "type": field.native_type,
                        "description": field.description,
                        "primary_key": field.primary_key,
                        "profile": field.profile,
                    }
                    for field in entity.fields
                ],
                "metrics": [metric.model_dump(mode="json") for metric in entity.metrics],
            }
            for entity in context.entities
        ],
        "relationships": [
            relationship.model_dump(mode="json") for relationship in context.relationships
        ],
    }


def generate_postgres_sql(
    provider: LLMProvider, question: str, context: RetrievalResponse
) -> GeneratedSQL:
    skill = get_skill("query-generation")
    response = provider.generate_structured(
        StructuredGenerationRequest(
            system_prompt=skill.instructions,
            user_payload={"question": question, "context": _context_payload(context, "postgresql")},
            schema_name="postgresql_query_generation",
            json_schema=GeneratedSQL.model_json_schema(),
        )
    )
    return GeneratedSQL.model_validate(response)


def repair_postgres_sql(
    provider: LLMProvider,
    question: str,
    context: RetrievalResponse,
    previous_sql: str,
    error_code: str,
    issues: list[str],
) -> GeneratedSQL:
    skill = get_skill("query-repair")
    response = provider.generate_structured(
        StructuredGenerationRequest(
            system_prompt=skill.instructions,
            user_payload={
                "question": question,
                "context": _context_payload(context, "postgresql"),
                "previous_sql": previous_sql,
                "error_code": error_code,
                "validation_issues": issues,
            },
            schema_name="postgresql_query_repair",
            json_schema=GeneratedSQL.model_json_schema(),
        )
    )
    return GeneratedSQL.model_validate(response)


def generate_mysql_sql(
    provider: LLMProvider, question: str, context: RetrievalResponse
) -> GeneratedSQL:
    skill = get_skill("mysql-query-generation")
    response = provider.generate_structured(
        StructuredGenerationRequest(
            system_prompt=skill.instructions,
            user_payload={"question": question, "context": _context_payload(context, "mysql")},
            schema_name="mysql_query_generation",
            json_schema=GeneratedSQL.model_json_schema(),
        )
    )
    return GeneratedSQL.model_validate(response)


def repair_mysql_sql(
    provider: LLMProvider,
    question: str,
    context: RetrievalResponse,
    previous_sql: str,
    error_code: str,
    issues: list[str],
) -> GeneratedSQL:
    skill = get_skill("mysql-query-repair")
    response = provider.generate_structured(
        StructuredGenerationRequest(
            system_prompt=skill.instructions,
            user_payload={
                "question": question,
                "context": _context_payload(context, "mysql"),
                "previous_sql": previous_sql,
                "error_code": error_code,
                "validation_issues": issues,
            },
            schema_name="mysql_query_repair",
            json_schema=GeneratedSQL.model_json_schema(),
        )
    )
    return GeneratedSQL.model_validate(response)
