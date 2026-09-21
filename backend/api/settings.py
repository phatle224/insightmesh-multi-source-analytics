"""Validated process configuration with secret-safe representations."""

from functools import lru_cache

from cryptography.fernet import Fernet
from pydantic import Field, SecretStr, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy import URL

LOCAL_ENCRYPTION_KEY = "MDEyMzQ1Njc4OTAxMjM0NTY3ODkwMTIzNDU2Nzg5MDE="


class Settings(BaseSettings):
    model_config = SettingsConfigDict(case_sensitive=False, extra="ignore")

    app_env: str = "development"
    pg_host: str = Field("metadata-db", alias="PGHOST")
    pg_port: int = Field(5432, alias="PGPORT", ge=1, le=65535)
    pg_database: str = Field("insightmesh", alias="PGDATABASE", min_length=1)
    pg_user: str = Field("insightmesh", alias="PGUSER", min_length=1)
    pg_password: SecretStr = Field(alias="PGPASSWORD")
    credential_encryption_key: SecretStr
    datasource_connect_timeout_seconds: int = Field(5, ge=1, le=30)
    datasource_statement_timeout_ms: int = Field(5_000, ge=100, le=120_000)
    datasource_max_rows: int = Field(1_000, ge=1, le=10_000)
    datasource_profile_max_rows: int = Field(1_000, ge=1, le=100_000)
    datasource_profile_timeout_ms: int = Field(10_000, ge=100, le=120_000)
    datasource_profile_enum_max_distinct: int = Field(20, ge=1, le=100)
    openrouter_base_url: str = "https://openrouter.ai/api/v1"
    openrouter_api_key: SecretStr | None = None
    gemini_base_url: str = "https://generativelanguage.googleapis.com"
    gemini_api_key: SecretStr | None = None
    gemini_model: str = "gemini-2.5-flash"
    llm_provider: str = "gemini"
    llm_model: str = "gemini-2.5-flash"
    llm_fallback_provider: str = "openrouter"
    llm_fallback_model: str = "openai/gpt-4o-mini"
    embedding_model: str = "openai/text-embedding-3-large"
    embedding_dimensions: int = Field(1536, ge=1, le=4096)
    model_config_version: str = "v1"
    provider_timeout_seconds: int = Field(30, ge=1, le=120)
    retrieval_top_k: int = Field(4, ge=1, le=10)
    retrieval_min_similarity: float = Field(0.2, ge=-1, le=1)
    retrieval_strategy: str = Field("hybrid", pattern="^(vector|hybrid)$")
    retrieval_semantic_weight: float = Field(0.65, ge=0, le=1)
    retrieval_lexical_weight: float = Field(0.35, ge=0, le=1)
    retrieval_hybrid_relative_threshold: float = Field(0.64, ge=0, le=1)
    retrieval_config_version: str = "v2-hybrid"
    retrieval_max_entities: int = Field(8, ge=1, le=20)
    retrieval_max_fields_per_entity: int = Field(24, ge=1, le=100)
    retrieval_max_relationship_hops: int = Field(3, ge=1, le=6)
    query_max_repair_attempts: int = Field(2, ge=0, le=2)

    @field_validator("credential_encryption_key")
    @classmethod
    def validate_fernet_key(cls, value: SecretStr) -> SecretStr:
        Fernet(value.get_secret_value().encode("ascii"))
        return value

    @model_validator(mode="after")
    def reject_local_key_outside_development(self) -> "Settings":
        if (
            self.app_env.lower() not in {"development", "test"}
            and self.credential_encryption_key.get_secret_value() == LOCAL_ENCRYPTION_KEY
        ):
            raise ValueError("The local credential encryption key is forbidden in this environment")
        if self.retrieval_semantic_weight + self.retrieval_lexical_weight <= 0:
            raise ValueError("At least one retrieval fusion weight must be positive")
        return self

    @property
    def database_url(self) -> URL:
        return URL.create(
            "postgresql+psycopg",
            username=self.pg_user,
            password=self.pg_password.get_secret_value(),
            host=self.pg_host,
            port=self.pg_port,
            database=self.pg_database,
        )


@lru_cache
def get_settings() -> Settings:
    return Settings()
