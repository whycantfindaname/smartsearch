from __future__ import annotations

from typing import Any

import httpx
import numpy as np
from mistralai.search.toolkit.context import RetrievalContext
from mistralai.search.toolkit.embedders.base import Embedder, EmbeddingResult

from smart_search_sidecar.errors import SidecarError

_DEFAULT_RETRIEVAL_CONTEXT = RetrievalContext()


class OpenAICompatibleEmbedder(Embedder):
    def __init__(
        self,
        *,
        base_url: str,
        model_name: str,
        dimension: int,
        normalization: str,
        api_key: str | None,
        timeout_seconds: float,
    ) -> None:
        super().__init__(model_name=model_name)
        self.base_url = base_url.rstrip("/")
        self.dimension = dimension
        self.normalization = normalization
        self.api_key = api_key
        self.timeout_seconds = timeout_seconds

    @property
    def endpoint(self) -> str:
        if self.base_url.endswith("/embeddings"):
            return self.base_url
        return f"{self.base_url}/embeddings"

    async def embed(
        self,
        texts: list[str],
        context: RetrievalContext = _DEFAULT_RETRIEVAL_CONTEXT,
    ) -> EmbeddingResult:
        del context
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        payload: dict[str, Any] = {"model": self.model_name, "input": texts}
        try:
            async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
                response = await client.post(
                    self.endpoint, headers=headers, json=payload
                )
                response.raise_for_status()
                body = response.json()
        except Exception as exc:
            raise SidecarError(
                "EMBEDDING_FAILED", "OpenAI-compatible embedding request failed."
            ) from exc
        data = body.get("data") if isinstance(body, dict) else None
        if not isinstance(data, list) or len(data) != len(texts):
            raise SidecarError(
                "EMBEDDING_INVALID_RESPONSE",
                "Embedding response count does not match input count.",
            )
        ordered = sorted(data, key=lambda item: item.get("index", 0))
        embeddings: list[list[float]] = []
        for item in ordered:
            vector = item.get("embedding") if isinstance(item, dict) else None
            if not isinstance(vector, list) or len(vector) != self.dimension:
                raise SidecarError(
                    "EMBEDDING_DIMENSION_MISMATCH",
                    "Embedding response dimension differs from the configured index identity.",
                    details={"expected_dimension": self.dimension},
                )
            array = np.asarray(vector, dtype=np.float32)
            if not np.all(np.isfinite(array)):
                raise SidecarError(
                    "EMBEDDING_INVALID_RESPONSE",
                    "Embedding contains non-finite values.",
                )
            if self.normalization == "l2":
                norm = float(np.linalg.norm(array))
                if norm == 0:
                    raise SidecarError(
                        "EMBEDDING_INVALID_RESPONSE",
                        "Cannot L2-normalize a zero embedding.",
                    )
                array = array / norm
            embeddings.append(array.astype(float).tolist())
        usage = body.get("usage", {}) if isinstance(body, dict) else {}
        total_tokens = usage.get("total_tokens", 0) if isinstance(usage, dict) else 0
        return EmbeddingResult(
            embeddings=embeddings, total_tokens=int(total_tokens or 0)
        )
