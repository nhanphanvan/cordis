import importlib
from pathlib import Path

import pytest

from cordis.backend.config import AppConfig, DatabaseConfig, build_config
from cordis.backend.db.base import ModelBase
from cordis.backend.versioning import get_version_payload


def test_shared_version_payload_exposes_name_and_version() -> None:
    assert get_version_payload() == {"name": "cordis", "version": "0.1.0"}


def test_shared_package_is_not_importable() -> None:
    with pytest.raises(ModuleNotFoundError):
        importlib.import_module("cordis.shared")


def test_database_config_derives_async_and_sync_database_urls() -> None:
    database = DatabaseConfig(
        db_url="postgresql+asyncpg://user:password@localhost:5432/cordis",
    )

    assert database.db_url == "postgresql+asyncpg://user:password@localhost:5432/cordis"
    assert database.sync_db_url == "postgresql://user:password@localhost:5432/cordis"


def test_database_config_exposes_full_engine_args_for_postgresql_urls() -> None:
    database = DatabaseConfig(
        db_url="postgresql+asyncpg://user:password@localhost:5432/cordis",
        db_pool_size=30,
        db_max_overflow=40,
        db_pool_timeout=180,
        db_pool_recycle=3600,
    )

    assert database.database_engine_args == {
        "pool_size": 30,
        "max_overflow": 40,
        "pool_timeout": 180,
        "pool_recycle": 3600,
        "pool_pre_ping": True,
    }


def test_database_config_uses_sqlite_safe_engine_args_for_sqlite_urls() -> None:
    database = DatabaseConfig(
        db_url="sqlite+aiosqlite:///./.cordis/cordis.db",
        db_pool_size=30,
        db_max_overflow=40,
        db_pool_timeout=180,
        db_pool_recycle=3600,
    )

    assert database.database_engine_args == {"pool_pre_ping": True}


def test_build_config_groups_app_database_and_storage_defaults() -> None:
    build_config.cache_clear()
    config = build_config()

    assert config.app.app_name == "cordis-backend"
    assert config.app.api_v1_prefix == "/api/v1"
    assert config.database.db_url == "sqlite+aiosqlite:///./.cordis/cordis.db"
    assert config.storage.bucket == "cordis-artifacts"


def test_app_config_loads_from_env_files(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.chdir(tmp_path)
    (tmp_path / ".env").write_text("CORDIS_APP_NAME=env-app\n", encoding="utf-8")
    (tmp_path / ".env.local").write_text("CORDIS_PORT=9001\n", encoding="utf-8")

    config = AppConfig()

    assert config.app_name == "env-app"
    assert config.port == 9001


def test_model_metadata_registers_phase_3_baseline_tables() -> None:
    table_names = set(ModelBase.metadata.tables)

    assert {"users", "roles", "repositories", "repository_members"} <= table_names
