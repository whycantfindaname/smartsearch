from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any

import pytest


class DeterministicEmbeddingHandler(BaseHTTPRequestHandler):
    def do_POST(self) -> None:
        length = int(self.headers.get("Content-Length", "0"))
        payload = json.loads(self.rfile.read(length))
        if payload["model"] == "force-failure":
            self.send_response(503)
            self.end_headers()
            return
        texts = payload["input"]
        dimension = self.server.dimension  # type: ignore[attr-defined]
        data = []
        for index, text in enumerate(texts):
            digest = hashlib.sha256(text.encode("utf-8")).digest()
            vector = [float(digest[position] + 1) for position in range(dimension)]
            data.append({"index": index, "embedding": vector})
        body = json.dumps({"data": data, "usage": {"total_tokens": len(texts)}}).encode(
            "utf-8"
        )
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format: str, *args: object) -> None:
        del format, args


@pytest.fixture
def embedding_server() -> str:
    server = ThreadingHTTPServer(("127.0.0.1", 0), DeterministicEmbeddingHandler)
    server.dimension = 8  # type: ignore[attr-defined]
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        host, port = server.server_address
        yield f"http://{host}:{port}/v1"
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)


class SidecarClient:
    def __init__(
        self, state_dir: Path, embedding_url: str, *, model: str = "fake-embedding-v1"
    ) -> None:
        sidecar_src = Path(__file__).resolve().parents[1] / "src"
        process_env = os.environ.copy()
        existing_pythonpath = process_env.get("PYTHONPATH", "")
        process_env["PYTHONPATH"] = os.pathsep.join(
            item for item in (str(sidecar_src), existing_pythonpath) if item
        )
        self.process = subprocess.Popen(
            [
                sys.executable,
                "-m",
                "smart_search_sidecar",
                "--state-dir",
                str(state_dir),
                "--embedding-base-url",
                embedding_url,
                "--embedding-model",
                model,
                "--embedding-dimension",
                "8",
                "--embedding-normalization",
                "l2",
                "--chunk-size",
                "72",
            ],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1,
            env=process_env,
        )
        assert self.process.stdin is not None
        assert self.process.stdout is not None

    def request(self, payload: dict[str, Any]) -> dict[str, Any]:
        assert self.process.stdin is not None
        assert self.process.stdout is not None
        self.process.stdin.write(json.dumps(payload) + "\n")
        self.process.stdin.flush()
        line = self.process.stdout.readline()
        if not line:
            stderr = (
                self.process.stderr.read() if self.process.stderr is not None else ""
            )
            raise AssertionError(f"sidecar exited without a response: {stderr}")
        return json.loads(line)

    def close(self) -> None:
        if self.process.stdin is not None:
            self.process.stdin.close()
        try:
            self.process.wait(timeout=10)
        except subprocess.TimeoutExpired:
            self.process.terminate()
            self.process.wait(timeout=5)
        if self.process.returncode != 0:
            stderr = (
                self.process.stderr.read() if self.process.stderr is not None else ""
            )
            raise AssertionError(
                f"sidecar exited with {self.process.returncode}: {stderr}"
            )


def _artifact() -> dict[str, Any]:
    content = (
        "# Alpha evidence\n\n"
        "Alpha is the first controlled claim in this registered snapshot. "
        "Its sentence remains in a stable character range for citation.\n\n"
        "## Beta details\n\n"
        "Beta phrase appears in the middle of the document and supports grep. "
        "Additional words ensure that navigation has neighboring chunks.\n\n"
        "## Gamma conclusion\n\n"
        "Gamma closes the artifact with plain text that can be opened and read."
    )
    return {
        "artifact_id": "artifact-md-001",
        "content": content,
        "content_type": "text/markdown",
        "source_url": "https://example.test/research/source",
        "snapshot_identity": {
            "kind": "sha256",
            "value": hashlib.sha256(content.encode()).hexdigest(),
        },
        "retrieved_at": "2026-08-24T10:00:00+08:00",
        "parser": {"name": "smart-search-fetch", "version": "1"},
    }


def test_stdio_navigation_boundaries_and_component_degradation(
    tmp_path: Path, embedding_server: str
) -> None:
    state_dir = tmp_path / "state"
    client = SidecarClient(state_dir, embedding_server)
    artifact = _artifact()
    try:
        health = client.request({"id": "health", "op": "health"})
        assert health["ok"] is True
        assert health["result"]["operations"] == [
            "health",
            "ingest",
            "search",
            "open",
            "navigate",
            "read",
            "grep",
        ]
        assert health["result"]["delete_exposed"] is False
        assert health["result"]["toolkit"]["version"] == "0.0.11"
        assert (
            "mistralai.search.toolkit.retrieval.QueryEngine"
            in health["result"]["toolkit"]["reused_imports"]
        )

        ingest = client.request(
            {
                "id": "ingest",
                "op": "ingest",
                "artifact_id": artifact["artifact_id"],
                "registered_artifact": artifact,
                "mineru_delegate_result": {
                    "status": "failed",
                    "error": "delegate unavailable in test",
                },
            }
        )
        assert ingest["ok"] is True
        result = ingest["result"]
        assert result["chunk_count"] >= 4
        assert result["vector_indexed"] is True
        assert result["source_url"] == artifact["source_url"]
        assert result["snapshot_identity"] == artifact["snapshot_identity"]
        assert all(
            locator["type"] == "character_range" for locator in result["locators"]
        )
        attempts = {
            (item["component"], item["status"]) for item in result["component_attempts"]
        }
        assert ("mineru", "failed") in attempts
        assert ("fetched_text_fallback", "success") in attempts
        assert ("search_toolkit_pipeline", "success") in attempts
        assert ("openai_compatible_embedding", "success") in attempts

        searched = client.request(
            {
                "id": "search",
                "op": "search",
                "artifact_id": artifact["artifact_id"],
                "query": "Alpha controlled claim",
                "top_k": 4,
            }
        )
        assert searched["ok"] is True
        assert searched["result"]["results"]
        hit = min(
            searched["result"]["results"], key=lambda item: item["locator"]["start"]
        )
        assert hit["source_url"] == artifact["source_url"]
        assert hit["snapshot_identity"] == artifact["snapshot_identity"]
        assert hit["locator"]["toolkit_locator"].startswith("char:")

        opened = client.request(
            {
                "id": "open",
                "op": "open",
                "artifact_id": artifact["artifact_id"],
                "chunk_id": hit["chunk_id"],
                "before": 1,
                "after": 1,
            }
        )
        assert opened["ok"] is True
        assert any(
            item["chunk_id"] == hit["chunk_id"] for item in opened["result"]["results"]
        )

        navigated = client.request(
            {
                "id": "navigate",
                "op": "navigate",
                "artifact_id": artifact["artifact_id"],
                "chunk_id": hit["chunk_id"],
                "direction": "next",
                "top_k": 2,
            }
        )
        assert navigated["ok"] is True
        assert navigated["result"]["results"]

        grepped = client.request(
            {
                "id": "grep",
                "op": "grep",
                "artifact_id": artifact["artifact_id"],
                "pattern": "Beta phrase",
                "mode": "phrase",
                "top_k": 5,
            }
        )
        assert grepped["ok"] is True
        assert any(
            "Beta phrase" in item["content"] for item in grepped["result"]["results"]
        )

        read = client.request(
            {
                "id": "read",
                "op": "read",
                "artifact_id": artifact["artifact_id"],
                "start": 0,
                "end": len(artifact["content"]),
                "top_k": 20,
            }
        )
        assert read["ok"] is True
        assert len(read["result"]["results"]) == result["chunk_count"]

        excluded = client.request(
            {
                "id": "search-after-read",
                "op": "search",
                "artifact_id": artifact["artifact_id"],
                "query": "Alpha",
                "top_k": 10,
            }
        )
        assert excluded["ok"] is True
        assert excluded["result"]["excluded_read_count"] == result["chunk_count"]
        assert excluded["result"]["results"] == []

        missing = client.request(
            {
                "id": "missing",
                "op": "search",
                "artifact_id": "artifact-missing",
                "query": "x",
            }
        )
        assert missing["ok"] is False
        assert missing["error"]["code"] == "ARTIFACT_NOT_REGISTERED"

        for invalid_id in (
            "/tmp/private.md",
            "file:///tmp/private.md",
            "https://example.test/private",
        ):
            rejected = client.request(
                {
                    "id": invalid_id,
                    "op": "search",
                    "artifact_id": invalid_id,
                    "query": "x",
                }
            )
            assert rejected["ok"] is False
            assert rejected["error"]["code"] == "INVALID_ARTIFACT_ID"

        arbitrary_url = client.request(
            {
                "id": "url-field",
                "op": "search",
                "artifact_id": artifact["artifact_id"],
                "query": "x",
                "url": "https://example.test/unregistered",
            }
        )
        assert arbitrary_url["ok"] is False
        assert arbitrary_url["error"]["code"] == "UNCONTROLLED_INPUT"

        delete = client.request(
            {"id": "delete", "op": "delete", "artifact_id": artifact["artifact_id"]}
        )
        assert delete["ok"] is False
        assert delete["error"]["code"] == "UNKNOWN_OPERATION"
    finally:
        client.close()

    mismatched = SidecarClient(state_dir, embedding_server, model="fake-embedding-v2")
    try:
        health = mismatched.request({"id": "health-mismatch", "op": "health"})
        assert health["ok"] is True
        assert health["result"]["status"] == "degraded"
        assert health["result"]["index_identity_mismatch"]["rebuild_required"] is True

        refused = mismatched.request(
            {
                "id": "refused",
                "op": "ingest",
                "artifact_id": artifact["artifact_id"],
                "registered_artifact": artifact,
            }
        )
        assert refused["ok"] is False
        assert refused["error"]["code"] == "INDEX_IDENTITY_MISMATCH"
        assert refused["error"]["details"]["rebuild_required"] is True
    finally:
        mismatched.close()


def test_embedding_failure_degrades_to_fts5(
    tmp_path: Path, embedding_server: str
) -> None:
    client = SidecarClient(
        tmp_path / "degraded-state", embedding_server, model="force-failure"
    )
    artifact = _artifact()
    try:
        ingest = client.request(
            {
                "id": "ingest-degraded",
                "op": "ingest",
                "artifact_id": artifact["artifact_id"],
                "registered_artifact": artifact,
            }
        )
        assert ingest["ok"] is True
        assert ingest["result"]["vector_indexed"] is False
        attempts = {
            (item["component"], item["status"])
            for item in ingest["result"]["component_attempts"]
        }
        assert ("openai_compatible_embedding", "degraded") in attempts
        assert ("sqlite_fts5", "success") in attempts

        searched = client.request(
            {
                "id": "search-degraded",
                "op": "search",
                "artifact_id": artifact["artifact_id"],
                "query": "Alpha controlled claim",
            }
        )
        assert searched["ok"] is True
        assert searched["result"]["results"]
        search_attempts = {
            (item["component"], item["status"])
            for item in searched["result"]["component_attempts"]
        }
        assert ("search_toolkit_query_engine", "degraded") in search_attempts
        assert ("sqlite_fts5", "success") in search_attempts
    finally:
        client.close()
