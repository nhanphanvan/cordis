from functools import lru_cache
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class AppConfig(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=(".env", ".env.local"),
        env_file_encoding="utf-8",
        extra="ignore",
        populate_by_name=True,
    )

    app_name: str = Field("cordis-backend", validation_alias="CORDIS_APP_NAME")
    environment: Literal["development", "test", "production"] = Field(
        "development",
        validation_alias="CORDIS_ENVIRONMENT",
    )
    api_v1_prefix: str = Field("/api/v1", validation_alias="CORDIS_API_V1_PREFIX")
    host: str = Field("127.0.0.1", validation_alias="CORDIS_HOST")
    port: int = Field(8000, validation_alias="CORDIS_PORT")
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = Field(
        "INFO",
        validation_alias="CORDIS_LOG_LEVEL",
    )


class DatabaseConfig(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=(".env", ".env.local"),
        env_file_encoding="utf-8",
        extra="ignore",
        populate_by_name=True,
    )

    db_url: str = Field("sqlite+aiosqlite:///./.cordis/cordis.db", validation_alias="CORDIS_DB_URL")
    db_echo: bool = Field(False, validation_alias="CORDIS_DB_ECHO")
    db_pool_size: int = Field(30, validation_alias="CORDIS_DB_POOL_SIZE")
    db_max_overflow: int = Field(40, validation_alias="CORDIS_DB_MAX_OVERFLOW")
    db_pool_timeout: int = Field(180, validation_alias="CORDIS_DB_POOL_TIMEOUT")
    db_pool_recycle: int = Field(3600, validation_alias="CORDIS_DB_POOL_RECYCLE")

    @property
    def sync_db_url(self) -> str:
        db_url = str(self.db_url)
        if db_url.startswith("postgresql+asyncpg://"):
            return db_url.replace("postgresql+asyncpg://", "postgresql://", 1)
        if db_url.startswith("sqlite+aiosqlite:///"):
            return db_url.replace("sqlite+aiosqlite:///", "sqlite:///", 1)
        return db_url

    @property
    def database_engine_args(self) -> dict[str, Any]:
        db_url = str(self.db_url)
        if db_url.startswith("sqlite+aiosqlite:///"):
            return {"pool_pre_ping": True}
        return {
            "pool_size": self.db_pool_size,
            "max_overflow": self.db_max_overflow,
            "pool_timeout": self.db_pool_timeout,
            "pool_recycle": self.db_pool_recycle,
            "pool_pre_ping": True,
        }


class StorageConfig(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=(".env", ".env.local"),
        env_file_encoding="utf-8",
        extra="ignore",
        populate_by_name=True,
    )

    provider: Literal["s3"] = Field("s3", validation_alias="CORDIS_STORAGE_PROVIDER")
    bucket: str = Field("cordis-artifacts", validation_alias="CORDIS_STORAGE_BUCKET")
    prefix: str = Field("", validation_alias="CORDIS_STORAGE_PREFIX")
    endpoint: str | None = Field(None, validation_alias="CORDIS_STORAGE_ENDPOINT")
    access_key: str | None = Field(None, validation_alias="CORDIS_STORAGE_ACCESS_KEY")
    secret_key: str | None = Field(None, validation_alias="CORDIS_STORAGE_SECRET_KEY")
    region: str | None = Field(None, validation_alias="CORDIS_STORAGE_REGION")
    secure: bool = Field(True, validation_alias="CORDIS_STORAGE_SECURE")
    presign_expiry_seconds: int = Field(3600, validation_alias="CORDIS_STORAGE_PRESIGN_EXPIRY_SECONDS")


class Config(BaseModel):
    model_config = ConfigDict(extra="ignore")

    app: AppConfig
    database: DatabaseConfig
    storage: StorageConfig


@lru_cache(maxsize=1)
def build_config() -> Config:
    return Config(
        app=AppConfig(),
        database=DatabaseConfig(),
        storage=StorageConfig(),
    )
