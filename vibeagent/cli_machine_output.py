from __future__ import annotations

from . import MACHINE_OUTPUT_SCHEMA_VERSION, __version__


def machine_runtime_fields() -> dict[str, object]:
    return {
        "schemaVersion": MACHINE_OUTPUT_SCHEMA_VERSION,
        "version": __version__,
    }


def machine_result_status_fields(
    *,
    status: str,
    stop_reason: str,
    exit_code: int | None = None,
) -> dict[str, object]:
    payload: dict[str, object] = {
        "status": status,
        "stopReason": stop_reason,
        "stop_reason": stop_reason,
    }
    if exit_code is not None:
        payload["exitCode"] = exit_code
        payload["exit_code"] = exit_code
    return payload
