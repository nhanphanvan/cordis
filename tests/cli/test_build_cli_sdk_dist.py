from __future__ import annotations

import subprocess
import sys
from pathlib import Path


def test_build_cli_sdk_manifest_excludes_backend() -> None:
    script = Path("scripts/build_cli_sdk_dist.py")

    result = subprocess.run(
        [sys.executable, str(script), "--print-manifest"],
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0
    manifest = result.stdout.splitlines()
    assert "cordis/__init__.py" in manifest
    assert "cordis/constants.py" in manifest
    assert "cordis/cli" in manifest
    assert "cordis/sdk" in manifest
    assert all(not item.startswith("cordis/backend") for item in manifest)
