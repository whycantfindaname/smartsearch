"""SessionStart must finish when a Windows hook runner leaves stdin open."""
import json
import os
import runpy
import subprocess
import sys
import tempfile
from pathlib import Path
from unittest import mock

import pytest

ROOT = Path(__file__).resolve().parents[1]
HOOK = ROOT / ".codex/hooks/session-start.py"


@pytest.mark.parametrize("payload", [b'{"probe":"open-stdin"}', b"", b"invalid-json"])
@pytest.mark.parametrize("reader_only", [True, False])
def test_session_start_exits_with_open_stdin(payload, reader_only):
    command = [sys.executable, str(HOOK)]
    if reader_only:
        code = 'import runpy,json,sys; m=runpy.run_path(sys.argv[1]); print(json.dumps(m["_load_hook_input"]()))'
        command = [sys.executable, "-c", code, str(HOOK)]
    env = dict(os.environ, PYTHONDONTWRITEBYTECODE="1", PYTHONUTF8="1",
               TRELLIS_CONTEXT_ID="session-start-open-stdin-test")
    with tempfile.TemporaryFile() as output, tempfile.TemporaryFile() as errors:
        child = subprocess.Popen(command, cwd=ROOT, env=env, stdin=subprocess.PIPE,
                                 stdout=output, stderr=errors)
        try:
            if payload:
                child.stdin.write(payload)
                child.stdin.flush()
            child.wait(timeout=5)
            errors.seek(0)
            assert child.returncode == 0, errors.read().decode("utf-8")
            output.seek(0)
            data = json.loads(output.read().decode("utf-8"))
            if reader_only:
                assert data == (json.loads(payload) if payload.startswith(b"{") else {})
            else:
                assert data["hookSpecificOutput"]["hookEventName"] == "SessionStart"
                assert data["hookSpecificOutput"]["additionalContext"]
        finally:
            if child.poll() is None:
                child.kill()
                child.wait()
            child.stdin.close()


def test_trellis_git_does_not_inherit_hook_stdin():
    module = runpy.run_path(str(ROOT / ".trellis/scripts/common/git.py"))
    with mock.patch.object(module["subprocess"], "run", return_value=subprocess.CompletedProcess([], 0, "main", "")) as run:
        assert module["run_git"](["branch", "--show-current"], cwd=ROOT) == (0, "main", "")
    assert run.call_args.kwargs["stdin"] == subprocess.DEVNULL
