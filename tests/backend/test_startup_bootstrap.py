import asyncio
from pathlib import Path

import pytest
from sqlalchemy import select

from cordis.backend.config import build_config
from cordis.backend.database import get_engine, get_session_factory
from cordis.backend.models import Role, User
from cordis.backend.models.base import DatabaseModel


async def _reset_database() -> None:
    engine = get_engine()
    async with engine.begin() as connection:
        await connection.run_sync(DatabaseModel.metadata.drop_all)
        await connection.run_sync(DatabaseModel.metadata.create_all)


async def _list_role_names() -> list[str]:
    session_factory = get_session_factory()
    async with session_factory() as session:
        result = await session.execute(select(Role.name).order_by(Role.name))
        return list(result.scalars())


async def _list_users() -> list[User]:
    session_factory = get_session_factory()
    async with session_factory() as session:
        result = await session.execute(select(User).order_by(User.id))
        return list(result.scalars())


def _clear_cached_state() -> None:
    build_config.cache_clear()
    get_engine.cache_clear()
    get_session_factory.cache_clear()


def test_bootstrap_runtime_creates_roles_and_first_admin_for_empty_database(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    db_path = tmp_path / "cordis-bootstrap.db"
    monkeypatch.setenv("CORDIS_DB_URL", f"sqlite+aiosqlite:///{db_path}")
    monkeypatch.setenv("CORDIS_BOOTSTRAP_ADMIN_EMAIL", "admin@example.com")
    monkeypatch.setenv("CORDIS_BOOTSTRAP_ADMIN_PASSWORD", "password123")
    monkeypatch.delenv("CORDIS_BOOTSTRAP_ADMIN_NAME", raising=False)
    _clear_cached_state()
    asyncio.run(_reset_database())

    from cordis.backend.bootstrap import bootstrap_runtime_state

    asyncio.run(bootstrap_runtime_state())

    assert asyncio.run(_list_role_names()) == ["developer", "owner", "viewer"]
    users = asyncio.run(_list_users())
    assert len(users) == 1
    assert users[0].email == "admin@example.com"
    assert users[0].name == "Admin"
    assert users[0].is_active is True
    assert users[0].is_admin is True
    assert users[0].password_hash != "password123"


def test_bootstrap_runtime_fails_for_empty_database_without_required_admin_env(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    db_path = tmp_path / "cordis-bootstrap-missing-env.db"
    monkeypatch.setenv("CORDIS_DB_URL", f"sqlite+aiosqlite:///{db_path}")
    monkeypatch.setenv("CORDIS_BOOTSTRAP_ADMIN_EMAIL", "")
    monkeypatch.setenv("CORDIS_BOOTSTRAP_ADMIN_PASSWORD", "")
    monkeypatch.setenv("CORDIS_BOOTSTRAP_ADMIN_NAME", "")
    _clear_cached_state()
    asyncio.run(_reset_database())

    from cordis.backend.bootstrap import BootstrapConfigurationError, bootstrap_runtime_state

    with pytest.raises(BootstrapConfigurationError):
        asyncio.run(bootstrap_runtime_state())


def test_bootstrap_runtime_leaves_existing_users_unchanged_but_restores_missing_roles(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    db_path = tmp_path / "cordis-bootstrap-existing-user.db"
    monkeypatch.setenv("CORDIS_DB_URL", f"sqlite+aiosqlite:///{db_path}")
    monkeypatch.setenv("CORDIS_BOOTSTRAP_ADMIN_EMAIL", "bootstrap@example.com")
    monkeypatch.setenv("CORDIS_BOOTSTRAP_ADMIN_PASSWORD", "password123")
    monkeypatch.setenv("CORDIS_BOOTSTRAP_ADMIN_NAME", "Bootstrap Admin")
    _clear_cached_state()
    asyncio.run(_reset_database())

    from cordis.backend.bootstrap import bootstrap_runtime_state
    from cordis.backend.security import get_password_hash

    async def _seed_existing_user_and_partial_roles() -> None:
        session_factory = get_session_factory()
        async with session_factory() as session:
            session.add(Role(name="owner", description="full repository control"))
            session.add(
                User(
                    email="existing@example.com",
                    name="Existing User",
                    password_hash=get_password_hash("existing-password"),
                    is_active=True,
                    is_admin=False,
                )
            )
            await session.commit()

    asyncio.run(_seed_existing_user_and_partial_roles())

    asyncio.run(bootstrap_runtime_state())

    assert asyncio.run(_list_role_names()) == ["developer", "owner", "viewer"]
    users = asyncio.run(_list_users())
    assert len(users) == 1
    assert users[0].email == "existing@example.com"
    assert users[0].name == "Existing User"
    assert users[0].is_admin is False


def test_bootstrap_runtime_rejects_weak_default_password_in_production(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    db_path = tmp_path / "cordis-bootstrap-production.db"
    monkeypatch.setenv("CORDIS_ENVIRONMENT", "production")
    monkeypatch.setenv("CORDIS_DB_URL", f"sqlite+aiosqlite:///{db_path}")
    monkeypatch.setenv("CORDIS_BOOTSTRAP_ADMIN_EMAIL", "admin@example.com")
    monkeypatch.setenv("CORDIS_BOOTSTRAP_ADMIN_PASSWORD", "password123")
    monkeypatch.setenv("CORDIS_BOOTSTRAP_ADMIN_NAME", "Admin")
    _clear_cached_state()
    asyncio.run(_reset_database())

    from cordis.backend.bootstrap import BootstrapConfigurationError, bootstrap_runtime_state

    with pytest.raises(BootstrapConfigurationError):
        asyncio.run(bootstrap_runtime_state())
