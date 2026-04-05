import uvicorn

from cordis.backend.app import create_app
from cordis.backend.config import build_config
from cordis.backend.utils.logging import setup_logging


def main() -> None:
    config = build_config()
    setup_logging(log_level=config.app.log_level)
    uvicorn.run(create_app(), host=config.app.host, port=config.app.port)


if __name__ == "__main__":
    main()
