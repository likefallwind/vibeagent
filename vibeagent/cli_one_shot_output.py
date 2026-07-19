from __future__ import annotations

from pathlib import Path

from .agent_result import AgentResult
from .cli_machine_output import add_duration_fields
from .cli_result_payloads import (
    build_chat_result_payload,
    build_code_result_payload,
    error_result_payload,
)
from .config import resolve_cost_rates
from .session_usage import build_run_cost_report, build_run_usage_report


def build_one_shot_error_payload(
    error: str,
    *,
    machine_output: bool,
    elapsed_ms: int,
    kind: str = "error",
    status: str = "failed",
    exit_code: int = 1,
) -> dict[str, object]:
    payload_exit_code = exit_code if machine_output else None
    payload = error_result_payload(error, kind=kind, status=status, exit_code=payload_exit_code)
    if machine_output:
        add_duration_fields(payload, elapsed_ms)
    return payload


def build_one_shot_chat_payload(
    message: str,
    *,
    machine_output: bool,
    elapsed_ms: int,
) -> dict[str, object]:
    payload = build_chat_result_payload(message)
    if machine_output:
        add_duration_fields(payload, elapsed_ms)
        payload["numTurns"] = 1
        payload["num_turns"] = 1
    return payload


def build_one_shot_code_payload(
    result: AgentResult,
    prior_context: object,
    *,
    machine_output: bool,
    elapsed_ms: int,
    project_root: Path,
    provider_env: dict[str, str],
) -> dict[str, object]:
    payload = build_code_result_payload(result, prior_context)
    if machine_output:
        add_duration_fields(payload, elapsed_ms)
        payload["usage"] = build_run_usage_report(project_root, result.run_id)
        cost_rates, cost_errors = resolve_cost_rates(provider_env)
        payload["cost"] = build_run_cost_report(project_root, result.run_id, cost_rates, cost_errors)
    return payload
