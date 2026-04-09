from pathlib import Path

from cordis.cli.transfer.files import iter_files


def test_iter_files_skips_paths_ignored_by_cordisignore(tmp_path: Path) -> None:
    root = tmp_path / "payloads"
    root.mkdir()
    (root / ".cordisignore").write_text("*.tmp\nbuild/\n", encoding="utf-8")
    (root / "keep.txt").write_text("keep", encoding="utf-8")
    (root / "ignore.tmp").write_text("ignore", encoding="utf-8")
    build_dir = root / "build"
    build_dir.mkdir()
    (build_dir / "artifact.bin").write_text("bin", encoding="utf-8")

    items = list(iter_files(root))

    assert items == [(root / "keep.txt", "keep.txt")]


def test_iter_files_supports_gitignore_style_negation(tmp_path: Path) -> None:
    root = tmp_path / "payloads"
    root.mkdir()
    (root / ".cordisignore").write_text("*.txt\n!important.txt\n", encoding="utf-8")
    (root / "drop.txt").write_text("drop", encoding="utf-8")
    (root / "important.txt").write_text("keep", encoding="utf-8")

    items = list(iter_files(root))

    assert items == [(root / "important.txt", "important.txt")]


def test_iter_files_skips_cordis_metadata_by_default(tmp_path: Path) -> None:
    root = tmp_path / "payloads"
    root.mkdir()
    (root / ".cordisignore").write_text("", encoding="utf-8")
    metadata_dir = root / ".cordis"
    metadata_dir.mkdir()
    (metadata_dir / "config.json").write_text("{}", encoding="utf-8")
    (root / "keep.txt").write_text("keep", encoding="utf-8")

    items = list(iter_files(root))

    assert items == [(root / "keep.txt", "keep.txt")]
