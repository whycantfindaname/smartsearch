"""Stop only the gateway process groups owned by one acceptance run."""

from __future__ import annotations

import argparse
import os
import signal
import time
from pathlib import Path

try:
    from .schema import load_json
except ImportError:
    from schema import load_json


def cleanup(runtime_root: Path) -> list[int]:
    manifest = load_json(runtime_root / "private" / "run-manifest.json")
    stopped: list[int] = []
    for case in manifest["cases"].values():
        pid = int(case["gateway_pid"])
        try:
            os.killpg(pid, signal.SIGTERM)
            stopped.append(pid)
        except ProcessLookupError:
            continue
    deadline = time.monotonic() + 3
    while time.monotonic() < deadline:
        alive = []
        for pid in stopped:
            try:
                os.kill(pid, 0)
                alive.append(pid)
            except ProcessLookupError:
                pass
        if not alive:
            break
        time.sleep(0.05)
    return stopped


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("runtime_root", type=Path)
    arguments = parser.parse_args()
    stopped = cleanup(arguments.runtime_root)
    print(" ".join(str(pid) for pid in stopped))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
