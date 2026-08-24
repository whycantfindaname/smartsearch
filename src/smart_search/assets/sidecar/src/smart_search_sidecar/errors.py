from __future__ import annotations

from typing import Any


class SidecarError(Exception):
    def __init__(
        self, code: str, message: str, *, details: dict[str, Any] | None = None
    ) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.details = details or {}


class IndexIdentityMismatch(SidecarError):
    def __init__(self, expected: dict[str, Any], actual: dict[str, Any]) -> None:
        super().__init__(
            "INDEX_IDENTITY_MISMATCH",
            "The existing index identity differs from the configured identity; rebuild is required.",
            details={"expected": expected, "actual": actual, "rebuild_required": True},
        )
