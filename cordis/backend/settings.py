from cordis.backend.config import build_config
from cordis.backend.security import setup_security
from cordis.backend.utils.logging import setup_logging


def setup() -> None:
    config = build_config()
    setup_logging(log_level=config.app.log_level)
    setup_security(
        secret_key=config.security.secret_key,
        jwt_algorithm=config.security.jwt_algorithm,
        access_token_expire_minutes=config.security.access_token_expire_minutes,
    )
