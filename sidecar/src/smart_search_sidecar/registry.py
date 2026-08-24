from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any
from urllib.parse import urlparse

from mistralai.search.toolkit.ingestion import File

from smart_search_sidecar.errors import SidecarError

ARTIFACT_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$")
ALLOWED_CONTENT_TYPES = {"text/markdown", "text/plain"}


@dataclass(frozen=True, slots=True)
class RegisteredArtifact:
    artifact_id: str
    content: str
    content_type: str
    source_url: str
    snapshot_identity: dict[str, Any]
    retrieved_at: str | None
    parser: dict[str, str]


def validate_artifact_id(artifact_id: Any) -> str:
    if not isinstance(artifact_id, str) or not ARTIFACT_ID_RE.fullmatch(artifact_id):
        raise SidecarError(
            "INVALID_ARTIFACT_ID",
            "artifact_id must be an opaque run-local identifier, not a path or URL.",
        )
    lowered = artifact_id.lower()
    if (
        lowered.startswith(("file:", "http:", "https:"))
        or "/" in artifact_id
        or "\\" in artifact_id
    ):
        raise SidecarError(
            "INVALID_ARTIFACT_ID",
            "artifact_id must be an opaque run-local identifier, not a path or URL.",
        )
    return artifact_id


def parse_registered_artifact(
    payload: Any, *, max_artifact_bytes: int
) -> RegisteredArtifact:
    if not isinstance(payload, dict):
        raise SidecarError("INVALID_ARTIFACT", "registered_artifact must be an object.")
    allowed = {
        "artifact_id",
        "content",
        "content_type",
        "source_url",
        "snapshot_identity",
        "retrieved_at",
        "parser",
    }
    unexpected = sorted(set(payload) - allowed)
    if unexpected:
        raise SidecarError(
            "UNCONTROLLED_INPUT",
            "registered_artifact contains unsupported input fields.",
            details={"fields": unexpected},
        )
    artifact_id = validate_artifact_id(payload.get("artifact_id"))
    content = payload.get("content")
    if not isinstance(content, str) or not content:
        raise SidecarError(
            "INVALID_ARTIFACT", "registered_artifact.content must be non-empty text."
        )
    if len(content.encode("utf-8")) > max_artifact_bytes:
        raise SidecarError(
            "ARTIFACT_TOO_LARGE",
            "registered artifact exceeds the configured byte limit.",
        )
    content_type = payload.get("content_type")
    if content_type not in ALLOWED_CONTENT_TYPES:
        raise SidecarError(
            "UNSUPPORTED_CONTENT_TYPE",
            "Only already-fetched Markdown and plain text artifacts are accepted.",
        )
    source_url = payload.get("source_url")
    if not isinstance(source_url, str):
        raise SidecarError(
            "INVALID_ARTIFACT", "source_url must be canonical HTTP(S) metadata."
        )
    parsed_url = urlparse(source_url)
    if parsed_url.scheme not in {"http", "https"} or not parsed_url.netloc:
        raise SidecarError(
            "INVALID_ARTIFACT", "source_url must be canonical HTTP(S) metadata."
        )
    snapshot_identity = payload.get("snapshot_identity")
    if not isinstance(snapshot_identity, dict) or not snapshot_identity:
        raise SidecarError(
            "INVALID_ARTIFACT", "snapshot_identity must be a non-empty object."
        )
    parser = payload.get("parser")
    if (
        not isinstance(parser, dict)
        or not isinstance(parser.get("name"), str)
        or not isinstance(parser.get("version"), str)
    ):
        raise SidecarError(
            "INVALID_ARTIFACT", "parser must include string name and version fields."
        )
    retrieved_at = payload.get("retrieved_at")
    if retrieved_at is not None and not isinstance(retrieved_at, str):
        raise SidecarError(
            "INVALID_ARTIFACT", "retrieved_at must be a string when present."
        )
    return RegisteredArtifact(
        artifact_id=artifact_id,
        content=content,
        content_type=content_type,
        source_url=source_url,
        snapshot_identity=snapshot_identity,
        retrieved_at=retrieved_at,
        parser={"name": parser["name"], "version": parser["version"]},
    )


class ArtifactRegistry:
    def __init__(self) -> None:
        self._artifacts: dict[str, RegisteredArtifact] = {}
        self._read_chunk_ids: dict[str, set[str]] = {}

    def register(self, artifact: RegisteredArtifact) -> None:
        existing = self._artifacts.get(artifact.artifact_id)
        if (
            existing is not None
            and existing.snapshot_identity != artifact.snapshot_identity
        ):
            raise SidecarError(
                "ARTIFACT_ID_COLLISION",
                "artifact_id is already registered to a different snapshot in this run.",
            )
        self._artifacts[artifact.artifact_id] = artifact
        self._read_chunk_ids.setdefault(artifact.artifact_id, set())

    def require(self, artifact_id: Any) -> RegisteredArtifact:
        normalized = validate_artifact_id(artifact_id)
        try:
            return self._artifacts[normalized]
        except KeyError as exc:
            raise SidecarError(
                "ARTIFACT_NOT_REGISTERED",
                "artifact_id is not registered in the current sidecar run.",
            ) from exc

    def mark_read(self, artifact_id: str, chunk_ids: set[str]) -> None:
        self.require(artifact_id)
        self._read_chunk_ids[artifact_id].update(chunk_ids)

    def read_chunk_ids(self, artifact_id: str) -> set[str]:
        self.require(artifact_id)
        return set(self._read_chunk_ids[artifact_id])


class RegisteredArtifactLoader:
    """Resolve only artifacts previously registered in this process."""

    def __init__(self, registry: ArtifactRegistry) -> None:
        self._registry = registry

    def load(self, artifact_id: Any, *, content_override: str | None = None) -> File:
        artifact = self._registry.require(artifact_id)
        content = content_override if content_override is not None else artifact.content
        return File(
            path=artifact.artifact_id,
            name=f"{artifact.artifact_id}.md"
            if artifact.content_type == "text/markdown"
            else f"{artifact.artifact_id}.txt",
            raw=content.encode("utf-8"),
            source_id=artifact.artifact_id,
            metadata={
                "mimetype": artifact.content_type,
                "source_url": artifact.source_url,
                "snapshot_identity": artifact.snapshot_identity,
                "retrieved_at": artifact.retrieved_at,
                "parser": artifact.parser,
            },
        )
