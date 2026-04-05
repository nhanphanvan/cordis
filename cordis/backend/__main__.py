import uvicorn

from cordis.backend.app import create_app
from cordis.backend.config import build_config
from cordis.backend.settings import setup


def main() -> None:
    setup()
    config = build_config()
    uvicorn.run(create_app(), host=config.app.host, port=config.app.port)


if __name__ == "__main__":
    main()
