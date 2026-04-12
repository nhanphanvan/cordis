from cordis.cli.config.files import ensure_global_config, get_global_config_path, read_config
from cordis.sdk import CordisClient


def get_client() -> CordisClient:
    ensure_global_config()
    config = read_config(get_global_config_path())
    base_url = str(config.get("endpoint") or "http://127.0.0.1:8000")
    token = config.get("token")
    return CordisClient(base_url=base_url, token=None if token is None else str(token))
