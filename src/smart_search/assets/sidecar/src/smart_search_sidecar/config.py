from __future__ import annotations

import argparse
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from smart_search_sidecar.errors import SidecarError

TOOLKIT_VERSION = "0.0.11"
SPLITTER_VERSION = "character-v1"


@dataclass(frozen=True, slots=True)
class SidecarConfig:
    state_dir: Path
    embedding_base_url: str
    embedding_model: str
    embedding_dimension: int
    embedding_enabled: bool
    embedding_normalization: str
    embedding_api_key: str | None
    splitter: str
    chunk_size: int
    request_timeout_seconds: float
    max_artifact_bytes: int

    @property
    def index_identity(self) -> dict[str, Any]:
        return {
            "embedding_model": self.embedding_model,
            "embedding_dimension": self.embedding_dimension,
            "embedding_enabled": self.embedding_enabled,
            "embedding_normalization": self.embedding_normalization,
            "splitter": self.splitter,
            "splitter_version": SPLITTER_VERSION,
            "splitter_chunk_size": self.chunk_size,
            "toolkit_version": TOOLKIT_VERSION,
        }


def _env(name: str, default: str) -> str:
    return os.environ.get(name, default)


def parse_args(argv: list[str] | None = None) -> SidecarConfig:
    parser = argparse.ArgumentParser(description="Smart Search document-mining sidecar")
    parser.add_argument(
        "--state-dir", default=_env("SMART_SEARCH_SIDECAR_STATE_DIR", ".sidecar-state")
    )
    parser.add_argument(
        "--embedding-base-url",
        default=_env("SMART_SEARCH_EMBEDDING_BASE_URL", "http://127.0.0.1:8000/v1"),
    )
    parser.add_argument(
        "--embedding-model",
        default=_env("SMART_SEARCH_EMBEDDING_MODEL", "text-embedding-3-small"),
    )
    parser.add_argument(
        "--embedding-dimension",
        type=int,
        default=int(_env("SMART_SEARCH_EMBEDDING_DIMENSION", "1536")),
    )
    parser.add_argument(
        "--embedding-enabled",
        choices=("true", "false"),
        default=_env("SMART_SEARCH_EMBEDDING_ENABLED", "true"),
    )
    parser.add_argument(
        "--embedding-normalization",
        choices=("l2", "none"),
        default=_env("SMART_SEARCH_EMBEDDING_NORMALIZATION", "l2"),
    )
    parser.add_argument(
        "--splitter",
        choices=("markdown", "character"),
        default=_env("SMART_SEARCH_DOCUMENT_SPLITTER", "character"),
    )
    parser.add_argument(
        "--chunk-size",
        type=int,
        default=int(_env("SMART_SEARCH_SIDECAR_CHUNK_SIZE", "1000")),
    )
    parser.add_argument(
        "--request-timeout-seconds",
        type=float,
        default=float(_env("SMART_SEARCH_EMBEDDING_TIMEOUT_SECONDS", "30")),
    )
    parser.add_argument(
        "--max-artifact-bytes",
        type=int,
        default=int(
            _env("SMART_SEARCH_SIDECAR_MAX_ARTIFACT_BYTES", str(2 * 1024 * 1024))
        ),
    )
    args = parser.parse_args(argv)
    if (
        args.embedding_dimension <= 0
        or args.chunk_size <= 0
        or args.max_artifact_bytes <= 0
    ):
        raise SidecarError(
            "INVALID_CONFIG",
            "Dimensions, chunk size, and artifact size limit must be positive.",
        )
    return SidecarConfig(
        state_dir=Path(args.state_dir).resolve(),
        embedding_base_url=args.embedding_base_url,
        embedding_model=args.embedding_model,
        embedding_dimension=args.embedding_dimension,
        embedding_enabled=args.embedding_enabled == "true",
        embedding_normalization=args.embedding_normalization,
        embedding_api_key=os.environ.get("SMART_SEARCH_EMBEDDING_API_KEY"),
        splitter=args.splitter,
        chunk_size=args.chunk_size,
        request_timeout_seconds=args.request_timeout_seconds,
        max_artifact_bytes=args.max_artifact_bytes,
    )
