from __future__ import annotations

import asyncio
import json
import logging
import sys
from typing import Any

import structlog

from smart_search_sidecar.config import parse_args
from smart_search_sidecar.errors import SidecarError
from smart_search_sidecar.service import DocumentMiningService


def _configure_logging() -> None:
    structlog.configure(
        wrapper_class=structlog.make_filtering_bound_logger(logging.WARNING),
        logger_factory=structlog.PrintLoggerFactory(file=sys.stderr),
    )


def _write_response(response: dict[str, Any]) -> None:
    sys.stdout.write(
        json.dumps(response, ensure_ascii=False, separators=(",", ":")) + "\n"
    )
    sys.stdout.flush()


async def run(service: DocumentMiningService) -> None:
    for raw_line in sys.stdin:
        request_id: Any = None
        try:
            request = json.loads(raw_line)
            if not isinstance(request, dict):
                raise SidecarError(
                    "INVALID_REQUEST", "Each protocol line must be a JSON object."
                )
            request_id = request.get("id")
            if request_id is None:
                raise SidecarError("INVALID_REQUEST", "Request id is required.")
            if not isinstance(request.get("op"), str):
                raise SidecarError("INVALID_REQUEST", "Request op is required.")
            result = await service.dispatch(request)
            _write_response({"id": request_id, "ok": True, "result": result})
        except json.JSONDecodeError:
            _write_response(
                {
                    "id": request_id,
                    "ok": False,
                    "error": {
                        "code": "INVALID_JSON",
                        "message": "Protocol input is not valid JSON.",
                    },
                }
            )
        except SidecarError as exc:
            error: dict[str, Any] = {"code": exc.code, "message": exc.message}
            if exc.details:
                error["details"] = exc.details
            _write_response({"id": request_id, "ok": False, "error": error})
        except Exception as exc:  # noqa: BLE001 - keep protocol alive without leaking request/config details
            _write_response(
                {
                    "id": request_id,
                    "ok": False,
                    "error": {
                        "code": "INTERNAL_ERROR",
                        "message": "Sidecar operation failed.",
                        "details": {"exception_type": type(exc).__name__},
                    },
                }
            )


def main(argv: list[str] | None = None) -> None:
    _configure_logging()
    config = parse_args(argv)
    service = DocumentMiningService(config)
    try:
        asyncio.run(run(service))
    finally:
        service.close()


if __name__ == "__main__":
    main()
