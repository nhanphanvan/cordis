import importlib
from pathlib import Path
from uuid import UUID

import pytest

from cordis.backend.config import AppConfig, DatabaseConfig, build_config
from cordis.backend.versioning import get_version_payload


def test_shared_version_payload_exposes_name_and_version() -> None:
    assert get_version_payload() == {"name": "cordis", "version": "0.1.0"}


def test_shared_package_is_not_importable() -> None:
    with pytest.raises(ModuleNotFoundError):
        importlib.import_module("cordis.shared")


def test_backend_db_package_is_not_importable() -> None:
    with pytest.raises(ModuleNotFoundError):
        importlib.import_module("cordis.backend.db")


def test_legacy_backend_error_modules_are_not_importable() -> None:
    with pytest.raises(ModuleNotFoundError):
        importlib.import_module("cordis.backend.errors")
    with pytest.raises(ModuleNotFoundError):
        importlib.import_module("cordis.backend.api.errors")
    with pytest.raises(ModuleNotFoundError):
        importlib.import_module("cordis.backend.services.authorization")


def test_legacy_flat_schema_modules_are_not_importable() -> None:
    with pytest.raises(ModuleNotFoundError):
        importlib.import_module("cordis.backend.schemas.auth")
    with pytest.raises(ModuleNotFoundError):
        importlib.import_module("cordis.backend.schemas.repository")


def test_cordis_package_is_root_level_not_src_layout() -> None:
    package = importlib.import_module("cordis")
    package_path = Path(package.__file__).resolve()

    assert "src" not in package_path.parts


def test_public_sdk_package_exports_cordis_client() -> None:
    sdk = importlib.import_module("cordis.sdk")

    assert hasattr(sdk, "CordisClient")


def test_legacy_cli_sdk_package_is_not_importable() -> None:
    with pytest.raises(ModuleNotFoundError):
        importlib.import_module("cordis.cli.sdk")


def test_sdk_config_helper_module_is_not_importable() -> None:
    with pytest.raises(ModuleNotFoundError):
        importlib.import_module("cordis.sdk.config")


def test_database_config_derives_async_and_sync_database_urls() -> None:
    database = DatabaseConfig(
        db_url="postgresql+asyncpg://user:password@localhost:5432/cordis",
    )

    assert database.db_url == "postgresql+asyncpg://user:password@localhost:5432/cordis"
    assert database.sync_db_url == "postgresql://user:password@localhost:5432/cordis"


def test_public_sdk_client_does_not_require_cli_config_for_explicit_construction() -> None:
    client = importlib.import_module("cordis.sdk").CordisClient(base_url="http://127.0.0.1:8000")

    assert client.base_url == "http://127.0.0.1:8000"
    assert client.token is None


def test_backend_migrations_helpers_expose_sync_url_and_metadata(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("CORDIS_DB_URL", "postgresql+asyncpg://user:password@localhost:5432/cordis")
    importlib.import_module("cordis.backend.config").build_config.cache_clear()

    migrations = importlib.import_module("cordis.backend.migrations")
    database_model = importlib.import_module("cordis.backend.models.base").DatabaseModel

    assert migrations.get_alembic_database_url() == "postgresql://user:password@localhost:5432/cordis"
    assert migrations.get_alembic_target_metadata() is database_model.metadata


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


def test_docker_assets_exist_for_backend_postgres_and_minio_stack() -> None:
    dockerfile = Path("Dockerfile")
    dockerignore = Path(".dockerignore")
    compose = Path("compose.yml")
    docker_env = Path(".env.docker.example")

    assert dockerfile.exists()
    assert dockerignore.exists()
    assert compose.exists()
    assert docker_env.exists()


def test_compose_stack_defines_backend_migrate_postgres_and_minio_services() -> None:
    compose_text = Path("compose.yml").read_text(encoding="utf-8")

    assert "backend:" in compose_text
    assert "migrate:" in compose_text
    assert "postgres:" in compose_text
    assert "minio:" in compose_text
    assert "/healthz" in compose_text
    assert "alembic upgrade head" in compose_text
    assert "postgresql+asyncpg://" in compose_text
    assert "CORDIS_STORAGE_PROVIDER:" in compose_text


def test_docker_env_example_uses_postgres_and_minio_defaults() -> None:
    env_text = Path(".env.docker.example").read_text(encoding="utf-8")

    assert "CORDIS_DB_URL=postgresql+asyncpg://" in env_text
    assert "CORDIS_STORAGE_PROVIDER=minio" in env_text
    assert "CORDIS_STORAGE_ENDPOINT=minio:9000" in env_text


def test_app_config_loads_from_env_files(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.chdir(tmp_path)
    (tmp_path / ".env").write_text("CORDIS_APP_NAME=env-app\n", encoding="utf-8")
    (tmp_path / ".env.local").write_text("CORDIS_PORT=9001\n", encoding="utf-8")

    config = AppConfig()

    assert config.app_name == "env-app"
    assert config.port == 9001


def test_model_metadata_registers_phase_3_baseline_tables() -> None:
    database_model = importlib.import_module("cordis.backend.models.base").DatabaseModel
    table_names = set(database_model.metadata.tables)

    assert {"users", "roles", "repositories", "repository_members"} <= table_names


def test_repository_member_uses_composite_primary_key_without_surrogate_id() -> None:
    repository_member = importlib.import_module("cordis.backend.models.repository_member").RepositoryMember
    primary_key_columns = [column.name for column in repository_member.__table__.primary_key.columns]

    assert primary_key_columns == ["repository_id", "user_id"]
    assert "id" not in repository_member.__table__.c


def test_models_base_exposes_database_model_not_legacy_split() -> None:
    models_base = importlib.import_module("cordis.backend.models.base")

    assert hasattr(models_base, "DatabaseModel")
    assert not hasattr(models_base, "TimestampedModel")
    assert not hasattr(models_base, "ModelBase")


def test_database_module_exposes_async_session_helpers() -> None:
    database = importlib.import_module("cordis.backend.database")

    assert callable(database.build_async_engine)
    assert callable(database.get_engine)
    assert callable(database.get_session_factory)
    assert callable(database.get_async_session)


def test_exceptions_package_exposes_app_status_and_handlers() -> None:
    exceptions = importlib.import_module("cordis.backend.exceptions")

    assert hasattr(exceptions, "AppStatus")
    assert callable(exceptions.configure_exception_handlers)


def test_policies_package_exposes_authorize_and_domain_policies() -> None:
    policies = importlib.import_module("cordis.backend.policies")

    assert callable(policies.authorize)
    assert hasattr(policies, "RepositoryPolicy")
    assert hasattr(policies, "UserPolicy")
    assert hasattr(policies, "RolePolicy")


def test_schema_packages_expose_request_and_response_modules() -> None:
    auth_requests = importlib.import_module("cordis.backend.schemas.requests.auth")
    auth_responses = importlib.import_module("cordis.backend.schemas.responses.auth")

    assert hasattr(auth_requests, "LoginRequest")
    assert hasattr(auth_responses, "TokenResponse")
    assert hasattr(auth_responses, "CurrentUserResponse")


def test_api_router_module_is_top_level_and_v1_router_module_is_not_importable() -> None:
    api_router = importlib.import_module("cordis.backend.api.router")

    assert hasattr(api_router, "router")

    with pytest.raises(ModuleNotFoundError):
        importlib.import_module("cordis.backend.api.v1.router")


def test_uuid_backed_model_columns_use_uuid_python_types() -> None:
    version = importlib.import_module("cordis.backend.models.version").Version
    version_tag = importlib.import_module("cordis.backend.models.version_tag").VersionTag
    artifact = importlib.import_module("cordis.backend.models.artifact").Artifact
    upload_session = importlib.import_module("cordis.backend.models.upload_session").UploadSession

    assert version.__table__.c.id.type.python_type is UUID
    assert version_tag.__table__.c.id.type.python_type is UUID
    assert version_tag.__table__.c.version_id.type.python_type is UUID
    assert artifact.__table__.c.id.type.python_type is UUID
    assert upload_session.__table__.c.id.type.python_type is UUID
    assert upload_session.__table__.c.version_id.type.python_type is UUID
    assert upload_session.__table__.c.artifact_id.type.python_type is UUID


def test_artifact_storage_version_id_is_non_nullable() -> None:
    artifact = importlib.import_module("cordis.backend.models.artifact").Artifact

    assert artifact.__table__.c.storage_version_id.nullable is False


def test_repository_member_relationships_use_explicit_bidirectional_ownership_style() -> None:
    repository = importlib.import_module("cordis.backend.models.repository").Repository
    repository_member = importlib.import_module("cordis.backend.models.repository_member").RepositoryMember
    user = importlib.import_module("cordis.backend.models.user").User
    role = importlib.import_module("cordis.backend.models.role").Role

    members = repository.__mapper__.relationships["members"]
    repository_ref = repository_member.__mapper__.relationships["repository"]
    user_memberships = user.__mapper__.relationships["repository_memberships"]
    role_memberships = role.__mapper__.relationships["repository_memberships"]

    assert members.back_populates == "repository"
    assert members.passive_deletes is True
    assert "delete-orphan" in str(members.cascade)
    assert repository_ref.back_populates == "members"
    assert repository_ref.passive_deletes is True
    assert user_memberships.back_populates == "user"
    assert user_memberships.passive_deletes is True
    assert role_memberships.back_populates == "role"
    assert role_memberships.passive_deletes is True


def test_upload_session_relationships_use_explicit_bidirectional_ownership_style() -> None:
    upload_session = importlib.import_module("cordis.backend.models.upload_session").UploadSession
    upload_session_part = importlib.import_module("cordis.backend.models.upload_session_part").UploadSessionPart

    assert "parts" in upload_session.__mapper__.relationships

    parts = upload_session.__mapper__.relationships["parts"]
    session = upload_session_part.__mapper__.relationships["session"]

    assert parts.back_populates == "session"
    assert parts.passive_deletes is True
    assert "delete-orphan" in str(parts.cascade)
    assert session.back_populates == "parts"
    assert session.passive_deletes is True


def test_backend_enums_and_constants_expose_canonical_domain_values() -> None:
    enums = importlib.import_module("cordis.backend.enums")
    constants = importlib.import_module("cordis.backend.constants")

    assert enums.UploadSessionStatus.CREATED.value == "created"
    assert enums.ResourceCheckStatus.EXISTS.value == "exists"
    assert enums.RepositoryAccessRole.OWNER.value == "owner"
    assert constants.BUILTIN_OWNER_ROLE == enums.RepositoryAccessRole.OWNER
    assert enums.UploadSessionStatus.COMPLETED in constants.UPLOAD_TERMINAL_STATUSES
    assert enums.UploadSessionStatus.CREATED in constants.UPLOAD_RESUMABLE_STATUSES
    assert "interrupted" not in {status.value for status in constants.UPLOAD_RESUMABLE_STATUSES}


def test_upload_session_status_column_uses_enum_python_type() -> None:
    upload_session = importlib.import_module("cordis.backend.models.upload_session").UploadSession
    enums = importlib.import_module("cordis.backend.enums")

    assert upload_session.__table__.c.status.type.python_type is enums.UploadSessionStatus
