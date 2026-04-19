import logging
from dataclasses import dataclass

from sqlalchemy import func, select

from cordis.backend.config import BootstrapConfig, build_config
from cordis.backend.database import get_session_factory
from cordis.backend.models import Role, User
from cordis.backend.security import get_password_hash

logger = logging.getLogger(__name__)

DEFAULT_ROLES: dict[str, str] = {
    "owner": "full repository control",
    "developer": "mutation access",
    "viewer": "read access",
}


class BootstrapConfigurationError(RuntimeError):
    pass


@dataclass(frozen=True)
class BootstrapAdmin:
    email: str
    password: str
    name: str


def _validate_bootstrap_admin(config: BootstrapConfig) -> BootstrapAdmin:
    email = (config.admin_email or "").strip()
    password = config.admin_password or ""
    name = (config.admin_name or "Admin").strip() or "Admin"

    if not email:
        raise BootstrapConfigurationError(
            "Empty database requires CORDIS_BOOTSTRAP_ADMIN_EMAIL to be set before backend startup."
        )
    if "@" not in email or email.startswith("@") or email.endswith("@"):
        raise BootstrapConfigurationError("CORDIS_BOOTSTRAP_ADMIN_EMAIL must be a valid email address.")
    if not password.strip():
        raise BootstrapConfigurationError(
            "Empty database requires CORDIS_BOOTSTRAP_ADMIN_PASSWORD to be set before backend startup."
        )

    return BootstrapAdmin(email=email, password=password, name=name)


async def bootstrap_runtime_state() -> None:
    config = build_config()
    session_factory = get_session_factory()

    async with session_factory() as session:
        created_roles: list[str] = []
        for name, description in DEFAULT_ROLES.items():
            existing_role = await session.scalar(select(Role).where(Role.name == name))
            if existing_role is None:
                session.add(Role(name=name, description=description))
                created_roles.append(name)

        if created_roles:
            logger.info("Seeded default repository roles: %s", ", ".join(sorted(created_roles)))
        else:
            logger.info("Default repository roles already present.")

        user_count = await session.scalar(select(func.count()).select_from(User))  # pylint: disable=not-callable
        if int(user_count or 0) > 0:
            logger.info("Bootstrap admin creation skipped because users already exist.")
            await session.commit()
            return

        bootstrap_admin = _validate_bootstrap_admin(config.bootstrap)
        session.add(
            User(
                email=bootstrap_admin.email,
                name=bootstrap_admin.name,
                password_hash=get_password_hash(bootstrap_admin.password),
                is_active=True,
                is_admin=True,
            )
        )
        await session.commit()
        logger.info("Created bootstrap admin user `%s`.", bootstrap_admin.email)
