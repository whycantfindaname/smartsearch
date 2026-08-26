"""Offline policy self-test entrypoint used by the task quality gate."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
if __name__ == "__main__":
    environment = {**os.environ, "PYTHONDONTWRITEBYTECODE": "1"}
    raise SystemExit(
        subprocess.call(
            [sys.executable, "-m", "pytest", "-q", str(HERE / "tests")],
            env=environment,
        )
    )
