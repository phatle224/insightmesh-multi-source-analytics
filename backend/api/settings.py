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
