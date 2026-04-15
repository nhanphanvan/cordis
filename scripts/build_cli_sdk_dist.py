from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
STAGED_PATHS = (
    Path("pyproject.toml"),
    Path("README.md"),
    Path("cordis/__init__.py"),
    Path("cordis/constants.py"),
    Path("cordis/cli"),
    Path("cordis/sdk"),
)


def iter_manifest() -> list[str]:
    return [path.as_posix() for path in STAGED_PATHS]


def stage_distribution(stage_root: Path) -> None:
    for relative_path in STAGED_PATHS:
        source = PROJECT_ROOT / relative_path
        destination = stage_root / relative_path
        destination.parent.mkdir(parents=True, exist_ok=True)
        if source.is_dir():
            shutil.copytree(source, destination)
        else:
            shutil.copy2(source, destination)


def build_distribution(output_dir: Path) -> None:
    build_distribution_with_format(output_dir=output_dir, build_format="all")


def build_distribution_with_format(output_dir: Path, build_format: str) -> None:
    with tempfile.TemporaryDirectory(prefix="cordis-cli-sdk-build-") as temp_dir:
        stage_root = Path(temp_dir)
        stage_distribution(stage_root)
        output_dir.mkdir(parents=True, exist_ok=True)
        command = [sys.executable, "-m", "poetry", "build", "--output", str(output_dir)]
        if build_format != "all":
            command.extend(["--format", build_format])
        subprocess.run(command, cwd=stage_root, check=True)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build a CLI/SDK-only Cordis distribution.")
    parser.add_argument(
        "--print-manifest",
        action="store_true",
        help="Print the staged files and directories without building.",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=PROJECT_ROOT / "dist",
        help="Directory that receives built artifacts.",
    )
    parser.add_argument(
        "--format",
        choices=("all", "sdist", "wheel"),
        default="all",
        help="Which artifact format to build.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.print_manifest:
        print("\n".join(iter_manifest()))
        return 0
    build_distribution_with_format(output_dir=args.output_dir.resolve(), build_format=args.format)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
