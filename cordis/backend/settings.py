from cordis.backend.config import build_config
from cordis.backend.security import setup_security
from cordis.backend.utils.logging import setup_logging

DEFAULT_DEVELOPMENT_SECRET_KEYS = frozenset({"cordis-dev-secret-key", "cordis-dev-secret-key-change-me"})


class ProductionConfigurationError(RuntimeError):
    pass


def _validate_production_config() -> None:
    config = build_config()
    if config.app.environment != "production":
        return
    if config.security.secret_key.strip() in DEFAULT_DEVELOPMENT_SECRET_KEYS:
        raise ProductionConfigurationError("CORDIS_SECRET_KEY must be overridden before starting in production.")
    if str(config.database.db_url).startswith("sqlite+aiosqlite:///"):
        raise ProductionConfigurationError("CORDIS_DB_URL must use PostgreSQL before starting in production.")


def setup() -> None:
    _validate_production_config()
    config = build_config()
    setup_logging(log_level=config.app.log_level)
    setup_security(
        secret_key=config.security.secret_key,
        jwt_algorithm=config.security.jwt_algorithm,
        access_token_expire_minutes=config.security.access_token_expire_minutes,
    )
