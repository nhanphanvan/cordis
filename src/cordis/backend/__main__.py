import uvicorn

from cordis.backend.app import create_app
from cordis.backend.config import build_config


def main() -> None:
    config = build_config()
    uvicorn.run(create_app(), host=config.app.host, port=config.app.port)


if __name__ == "__main__":
    main()
