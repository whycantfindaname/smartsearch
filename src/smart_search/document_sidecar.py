"""Bridge the Python 3.10 CLI to the Python 3.12 document-mining sidecar.

The bridge owns process launch and configuration translation only.  Semantic
document selection and EvidenceItem authoring remain Root/Evidence Miner work.
"""

from __future__ import annotations

import json
import os
import subprocess
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FutureTimeout
from pathlib import Path
from typing import Any, Mapping, Sequence

import httpx

from .config import Config
from .research_contracts import ArtifactRecord, ContractValidationError
from .research_kernel import ArtifactRegistry


SIDECAR_MAX_ARTIFACT_BYTES = 2 * 1024 * 1024


class SidecarBridgeError(RuntimeError):
    """Raised when the isolated sidecar cannot satisfy its public protocol."""

    def __init__(self, code: str, message: str, *, details: Mapping[str, Any] | None = None):
        super().__init__(message)
        self.code = code
        self.message = message
        self.details = dict(details or {})

    def to_dict(self) -> dict[str, Any]:
        value: dict[str, Any] = {"code": self.code, "message": self.message}
        if self.details:
            value["details"] = self.details
        return value


def _embedding_endpoint(api_url: str) -> str:
    value = api_url.rstrip("/")
    return value if value.endswith("/embeddings") else f"{value}/embeddings"


async def resolve_embedding_dimension(
    embedding: Mapping[str, Any],
    *,
    timeout_seconds: float,
) -> int:
    """Resolve auto dimensions once before index identity is fixed.

    A disabled or unconfigured embedder receives the stable lexical-only
    placeholder dimension 1.  It will degrade inside the sidecar without a
    credential.  No secret is returned from this function.
    """

    configured = bool(embedding.get("configured"))
    requested = int(embedding.get("dimensions") or 0)
    if requested > 0:
        return requested
    if not configured:
        return 1

    api_url = str(embedding.get("api_url") or "")
    api_key = str(embedding.get("api_key") or "")
    model = str(embedding.get("model") or "")
    if not api_url or not api_key or not model:
        return 1
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    try:
        async with httpx.AsyncClient(timeout=timeout_seconds) as client:
            response = await client.post(
                _embedding_endpoint(api_url),
                headers=headers,
                json={"model": model, "input": ["smart-search dimension probe"]},
            )
            response.raise_for_status()
            body = response.json()
    except Exception as exc:
        raise SidecarBridgeError(
            "EMBEDDING_DIMENSION_PROBE_FAILED",
            "Document embedding dimension could not be resolved; configure an explicit dimension or disable embeddings.",
            details={"exception_type": type(exc).__name__},
        ) from exc
    data = body.get("data") if isinstance(body, Mapping) else None
    first = data[0] if isinstance(data, list) and data else None
    vector = first.get("embedding") if isinstance(first, Mapping) else None
    if not isinstance(vector, list) or not vector:
        raise SidecarBridgeError(
            "EMBEDDING_DIMENSION_PROBE_FAILED",
            "Document embedding endpoint returned no usable vector.",
        )
    return len(vector)


class DocumentSidecarSession:
    """One controlled stdio session for an EvidenceMiningTask."""

    def __init__(
        self,
        *,
        state_dir: Path,
        config: Config,
        embedding_dimension: int,
        embedding_enabled: bool = True,
        process_factory: Any = subprocess.Popen,
    ) -> None:
        embedding = config.document_embedding_config()
        normalization = "l2" if bool(embedding.get("normalize")) else "none"
        model = str(embedding.get("model") or "lexical-only") if embedding_enabled else "lexical-only"
        api_url = (
            str(embedding.get("api_url") or "http://127.0.0.1:1/v1")
            if embedding_enabled
            else "http://127.0.0.1:1/v1"
        )
        command = [
            config.sidecar_python,
            "-m",
            "smart_search_sidecar",
            "--state-dir",
            str(state_dir),
            "--embedding-base-url",
            api_url,
            "--embedding-model",
            model,
            "--embedding-dimension",
            str(embedding_dimension),
            "--embedding-enabled",
            "true" if embedding_enabled else "false",
            "--embedding-normalization",
            normalization,
            "--splitter",
            config.document_splitter,
            "--chunk-size",
            str(config.document_chunk_size),
            "--max-artifact-bytes",
            str(SIDECAR_MAX_ARTIFACT_BYTES),
            "--request-timeout-seconds",
            str(config.sidecar_timeout),
        ]
        environment = dict(os.environ)
        api_key = embedding.get("api_key") if embedding_enabled else None
        if api_key:
            environment["SMART_SEARCH_EMBEDDING_API_KEY"] = str(api_key)
        else:
            environment.pop("SMART_SEARCH_EMBEDDING_API_KEY", None)
        try:
            self.process = process_factory(
                command,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                bufsize=1,
                env=environment,
            )
        except (OSError, ValueError) as exc:
            raise SidecarBridgeError(
                "SIDECAR_UNAVAILABLE",
                "Python 3.12 document sidecar could not be launched.",
                details={"exception_type": type(exc).__name__},
            ) from exc
        self.timeout_seconds = config.sidecar_timeout
        self._next_id = 1

    def close(self) -> None:
        if self.process.stdin is not None and not self.process.stdin.closed:
            self.process.stdin.close()
        try:
            self.process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            self.process.terminate()
            try:
                self.process.wait(timeout=3)
            except subprocess.TimeoutExpired:
                self.process.kill()
                self.process.wait(timeout=3)

    def __enter__(self) -> "DocumentSidecarSession":
        return self

    def __exit__(self, exc_type: Any, exc: Any, traceback: Any) -> None:
        del exc_type, exc, traceback
        self.close()

    def request(self, operation: Mapping[str, Any]) -> dict[str, Any]:
        if self.process.stdin is None or self.process.stdout is None:
            raise SidecarBridgeError("SIDECAR_UNAVAILABLE", "Sidecar stdio is unavailable.")
        request = dict(operation)
        request.setdefault("id", f"bridge-{self._next_id}")
        self._next_id += 1
        try:
            self.process.stdin.write(json.dumps(request, ensure_ascii=False) + "\n")
            self.process.stdin.flush()
        except (BrokenPipeError, OSError) as exc:
            raise self._process_failure("Sidecar stopped before accepting a request.") from exc

        with ThreadPoolExecutor(max_workers=1) as executor:
            future = executor.submit(self.process.stdout.readline)
            try:
                line = future.result(timeout=self.timeout_seconds)
            except FutureTimeout as exc:
                self.process.terminate()
                raise SidecarBridgeError(
                    "SIDECAR_TIMEOUT",
                    "Document sidecar operation exceeded its configured timeout.",
                ) from exc
        if not line:
            raise self._process_failure("Sidecar exited without a protocol response.")
        try:
            response = json.loads(line)
        except json.JSONDecodeError as exc:
            raise SidecarBridgeError(
                "SIDECAR_PROTOCOL_ERROR",
                "Sidecar returned invalid JSON.",
            ) from exc
        if not isinstance(response, dict) or response.get("id") != request["id"]:
            raise SidecarBridgeError(
                "SIDECAR_PROTOCOL_ERROR",
                "Sidecar response id does not match the request.",
            )
        if not response.get("ok"):
            error = response.get("error") if isinstance(response.get("error"), dict) else {}
            raise SidecarBridgeError(
                str(error.get("code") or "SIDECAR_OPERATION_FAILED"),
                str(error.get("message") or "Document sidecar operation failed."),
                details=error.get("details") if isinstance(error.get("details"), dict) else None,
            )
        result = response.get("result")
        if not isinstance(result, dict):
            raise SidecarBridgeError(
                "SIDECAR_PROTOCOL_ERROR",
                "Sidecar success response is missing an object result.",
            )
        return result

    def _process_failure(self, message: str) -> SidecarBridgeError:
        stderr = ""
        if self.process.stderr is not None and self.process.poll() is not None:
            try:
                stderr = self.process.stderr.read(1000)
            except OSError:
                stderr = ""
        return SidecarBridgeError(
            "SIDECAR_UNAVAILABLE",
            message,
            details={
                "returncode": self.process.poll(),
                "stderr": " ".join(stderr.split())[:500],
            },
        )


def registered_artifact_payload(registry: ArtifactRegistry, artifact: ArtifactRecord) -> dict[str, Any]:
    """Translate one immutable run artifact without exposing a caller path."""

    if artifact.artifact_kind not in {"snapshot", "fetched_snapshot", "document_snapshot"}:
        raise ContractValidationError("only registered document snapshots can enter the sidecar")
    content_path = registry.run_dir / artifact.raw_ref
    content = content_path.read_text(encoding="utf-8")
    media_type = artifact.media_type.split(";", 1)[0].strip().lower()
    if media_type not in {"text/markdown", "text/plain"}:
        raise ContractValidationError("sidecar input must be fetched Markdown or plain text")
    parser = artifact.metadata.get("parser") if isinstance(artifact.metadata, dict) else None
    if not isinstance(parser, Mapping):
        parser = {"name": "smart-search-fetch", "version": "1"}
    return {
        "artifact_id": artifact.artifact_id,
        "content": content,
        "content_type": media_type,
        "source_url": artifact.canonical_url,
        "snapshot_identity": {"snapshot_id": artifact.snapshot_id},
        "retrieved_at": artifact.created_at,
        "parser": {
            "name": str(parser.get("name") or "smart-search-fetch"),
            "version": str(parser.get("version") or "1"),
        },
    }


async def run_document_operations(
    *,
    registry: ArtifactRegistry,
    artifact_ids: Sequence[str],
    operations: Sequence[Mapping[str, Any]],
    config: Config,
    mineru_results: Mapping[str, Mapping[str, Any]] | None = None,
) -> dict[str, Any]:
    """Run an Agent-authored tool sequence inside one controlled sidecar session."""

    artifacts = registry.resolve_inputs(list(artifact_ids))
    allowed_ids = {artifact.artifact_id for artifact in artifacts}
    for operation in operations:
        if not isinstance(operation, Mapping):
            raise ContractValidationError("document operations must be objects")
        if operation.get("op") not in {"search", "open", "navigate", "read", "grep"}:
            raise ContractValidationError("document operations may only use search/open/navigate/read/grep")
        if operation.get("artifact_id") not in allowed_ids:
            raise ContractValidationError("document operation references an artifact outside the task")

    embedding = config.document_embedding_config()
    preflight_attempts: list[dict[str, Any]] = []
    embedding_enabled = bool(embedding.get("configured"))
    if not embedding_enabled:
        dimension = 1
    else:
        try:
            dimension = await resolve_embedding_dimension(
                embedding, timeout_seconds=config.sidecar_timeout
            )
        except SidecarBridgeError as exc:
            # Dimension discovery is an optional vector preflight. A failed
            # probe must not prevent SQLite FTS5 from mining the document.
            dimension = 1
            embedding_enabled = False
            preflight_attempts.append(
                {
                    "component": "openai_compatible_embedding",
                    "status": "degraded",
                    "kind": "embedding_preflight",
                    "reason": exc.message,
                    "error_code": exc.code,
                }
            )
    results: list[dict[str, Any]] = []
    attempts: list[dict[str, Any]] = []
    state_dir = registry.run_dir / "document-index"
    with DocumentSidecarSession(
        state_dir=state_dir,
        config=config,
        embedding_dimension=dimension,
        embedding_enabled=embedding_enabled,
    ) as session:
        health = session.request({"op": "health"})
        for artifact in artifacts:
            ingest_request: dict[str, Any] = {
                "op": "ingest",
                "artifact_id": artifact.artifact_id,
                "registered_artifact": registered_artifact_payload(registry, artifact),
            }
            mineru = (mineru_results or {}).get(artifact.artifact_id)
            if mineru is not None:
                ingest_request["mineru_delegate_result"] = dict(mineru)
            ingest_result = session.request(ingest_request)
            attempts.extend(ingest_result.get("component_attempts") or [])
        for operation in operations:
            result = session.request(operation)
            attempts.extend(result.get("component_attempts") or [])
            results.append({"request": dict(operation), "result": result})
    return {
        "ok": True,
        "health": health,
        "results": results,
        "component_attempts": preflight_attempts + attempts,
        "artifact_ids": sorted(allowed_ids),
    }
