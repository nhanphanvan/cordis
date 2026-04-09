import base64
import hashlib
import shutil
from collections.abc import Iterator
from pathlib import Path
from urllib import request

from pathspec import PathSpec

from cordis.cli.config.files import get_cache_dir

IGNORE_FILE_NAME = ".cordisignore"
DEFAULT_IGNORE_PATTERNS = [IGNORE_FILE_NAME, ".cordis/"]


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


def read_file_base64(path: Path) -> str:
    return base64.b64encode(path.read_bytes()).decode("ascii")


def cache_file_path(repository_key: str, checksum: str) -> Path:
    raw = checksum.replace("sha256:", "")
    return get_cache_dir() / repository_key / raw[:2] / raw[2:]


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


def download_to_path(url: str, destination_path: Path) -> None:
    destination_path.parent.mkdir(parents=True, exist_ok=True)
    with request.urlopen(url) as response, destination_path.open("wb") as handle:
        shutil.copyfileobj(response, handle)
