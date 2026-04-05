from functools import lru_cache
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "cordis-backend"
    environment: Literal["development", "test", "production"] = "development"
    api_v1_prefix: str = "/api/v1"
    db_url: str = "sqlite+aiosqlite:///./.cordis/cordis.db"
    db_echo: bool = False
    host: str = "127.0.0.1"
    port: int = 8000
    storage_provider: Literal["s3"] = "s3"
    storage_bucket: str = "cordis-artifacts"
    storage_prefix: str = ""
    storage_endpoint: str | None = None
    storage_access_key: str | None = None
    storage_secret_key: str | None = None
    storage_region: str | None = None
    storage_secure: bool = True
    storage_presign_expiry_seconds: int = 3600

    model_config = SettingsConfigDict(env_prefix="CORDIS_", extra="ignore")

    @property
    def sync_db_url(self) -> str:
        if self.db_url.startswith("postgresql+asyncpg://"):
            return self.db_url.replace("postgresql+asyncpg://", "postgresql://", 1)
        if self.db_url.startswith("sqlite+aiosqlite:///"):
            return self.db_url.replace("sqlite+aiosqlite:///", "sqlite:///", 1)
        return self.db_url


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
