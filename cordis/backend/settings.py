from cordis.backend.config import build_config
from cordis.backend.utils.logging import setup_logging


def setup() -> None:
    config = build_config()
    setup_logging(log_level=config.app.log_level)
