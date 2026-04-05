from cordis.backend.db.base import ModelBase
from cordis.shared.settings import Settings
from cordis.shared.version import get_version_payload


def test_shared_version_payload_exposes_name_and_version() -> None:
    assert get_version_payload() == {"name": "cordis", "version": "0.1.0"}


def test_settings_derive_async_and_sync_database_urls() -> None:
    settings = Settings(
        app_name="cordis-backend",
        db_url="postgresql+asyncpg://user:password@localhost:5432/cordis",
    )

    assert settings.db_url == "postgresql+asyncpg://user:password@localhost:5432/cordis"
    assert settings.sync_db_url == "postgresql://user:password@localhost:5432/cordis"


def test_model_metadata_registers_phase_3_baseline_tables() -> None:
    table_names = set(ModelBase.metadata.tables)

    assert {"users", "roles", "repositories", "repository_members"} <= table_names
