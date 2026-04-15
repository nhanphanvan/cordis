import hashlib
import json
import os
import shutil
from collections.abc import Iterator
from pathlib import Path
from typing import Any, cast

from pathspec import PathSpec

from cordis.constants import DEFAULT_TRANSFER_CHUNK_SIZE

IGNORE_FILE_NAME = ".cordisignore"
DEFAULT_IGNORE_PATTERNS = [IGNORE_FILE_NAME, ".cordis/"]


def get_cordis_home() -> Path:
    return Path(os.environ.get("CORDIS_HOME", Path.home() / ".cordis"))


def get_global_config_path() -> Path:
    return get_cordis_home() / "config.json"


def get_cache_dir() -> Path:
    return get_cordis_home() / "cache"


def cache_file_path(repository_key: str, checksum: str) -> Path:
    raw = checksum.replace("sha256:", "")
    return get_cache_dir() / repository_key / raw[:2] / raw[2:]


def get_project_config_dir() -> Path:
    return Path.cwd() / ".cordis"


def get_project_config_path() -> Path:
    return get_project_config_dir() / "config.json"


def ensure_global_config() -> Path:
    config_path = get_global_config_path()
    config_path.parent.mkdir(parents=True, exist_ok=True)
    get_cache_dir().mkdir(parents=True, exist_ok=True)
    if not config_path.exists():
        config_path.write_text("{}", encoding="utf-8")
    return config_path


def ensure_project_config() -> Path:
    config_path = get_project_config_path()
    config_path.parent.mkdir(parents=True, exist_ok=True)
    if not config_path.exists():
        config_path.write_text("{}", encoding="utf-8")
    return config_path


def read_config(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    return cast(dict[str, Any], json.loads(path.read_text(encoding="utf-8")))


def write_config(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=True, indent=2, sort_keys=True), encoding="utf-8")


def update_config_value(path: Path, field: str, value: Any) -> None:
    data = read_config(path)
    data[field] = value
    write_config(path, data)


def remove_config_value(path: Path, field: str) -> None:
    data = read_config(path)
    data.pop(field, None)
    write_config(path, data)


def clear_project_registration() -> None:
    config_path = get_project_config_path()
    if config_path.exists():
        config_path.unlink()
    config_dir = get_project_config_dir()
    if config_dir.exists() and not any(config_dir.iterdir()):
        config_dir.rmdir()


def clean_cache() -> None:
    cache_dir = get_cache_dir()
    if cache_dir.exists():
        shutil.rmtree(cache_dir)
    cache_dir.mkdir(parents=True, exist_ok=True)


def save_to_cache(repository_key: str, checksum: str, source_path: Path) -> None:
    destination = cache_file_path(repository_key, checksum)
    destination.parent.mkdir(parents=True, exist_ok=True)
    if not destination.exists():
        shutil.copy2(source_path, destination)


def copy_from_cache(repository_key: str, checksum: str, destination_path: Path) -> bool:
    cached = cache_file_path(repository_key, checksum)
    if not cached.exists():
        return False
    destination_path.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(cached, destination_path)
    return True


def _build_ignore_spec(root: Path) -> PathSpec:
    patterns = list(DEFAULT_IGNORE_PATTERNS)
    ignore_file = root / IGNORE_FILE_NAME
    if ignore_file.exists():
        lines = ignore_file.read_text(encoding="utf-8").splitlines()
        patterns.extend(line for line in lines if line.strip() and not line.lstrip().startswith("#"))
    return PathSpec.from_lines("gitignore", patterns)


def iter_files(root: Path) -> Iterator[tuple[Path, str]]:
    ignore_spec = _build_ignore_spec(root)
    for path in root.rglob("*"):
        if path.is_file():
            relative_path = path.relative_to(root).as_posix()
            if ignore_spec.match_file(relative_path):
                continue
            yield path, relative_path


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return f"sha256:{digest.hexdigest()}"


def iter_file_chunks(path: Path, chunk_size: int = DEFAULT_TRANSFER_CHUNK_SIZE) -> Iterator[tuple[int, bytes]]:
    with path.open("rb") as handle:
        part_number = 1
        while True:
            chunk = handle.read(chunk_size)
            if not chunk:
                break
            yield part_number, chunk
            part_number += 1
