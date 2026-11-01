"""The JavaScript tests of the frontend (tests/js, node --test), run with the Python ones."""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import pytest

JS_TESTS = sorted((Path(__file__).parent / "js").glob("*.test.mjs"))


@pytest.mark.skipif(shutil.which("node") is None, reason="Node.js is needed for the frontend tests")
@pytest.mark.parametrize("path", JS_TESTS, ids=lambda p: p.name)
def test_frontend(path: Path) -> None:
    result = subprocess.run(["node", "--test", str(path)], capture_output=True, text=True, timeout=60, check=False)
    assert result.returncode == 0, result.stdout + result.stderr
