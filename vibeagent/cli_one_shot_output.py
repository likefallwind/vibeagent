from __future__ import annotations

from collections.abc import Callable
import json
from pathlib import Path

from .agent_result import AgentResult
from .cli_machine_output import add_duration_fields
from .cli_machine_output import machine_result_status_fields
from .cli_output import print_agent_result, print_error_result, print_output
from .cli_result_payloads import (
    build_chat_result_payload,
    build_code_result_payload,
    error_result_payload,
)
from .cli_stream_output import JsonEventStream
from .config import resolve_cost_rates
from .model_budget import ModelBudgetExceededError, ModelCostBudget
from .model_fallback import ModelFallbackState
from .session_usage import build_run_cost_report, build_run_usage_report
from .structured_output import StructuredOutputResult


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


def emit_one_shot_error(
    error: str,
    *,
    stream: JsonEventStream | None,
    output_json: bool,
    machine_output: bool,
    elapsed_ms: int,
    kind: str = "error",
    status: str = "failed",
    exit_code: int = 1,
    print_output_func: Callable[[dict[str, object], bool], None] = print_output,
    print_error_result_func: Callable[..., int] = print_error_result,
) -> int:
    payload = build_one_shot_error_payload(
        error,
        machine_output=machine_output,
        elapsed_ms=elapsed_ms,
        kind=kind,
        status=status,
        exit_code=exit_code,
    )
    if stream is not None:
        stream.result(payload)
        return exit_code
    if output_json:
        print_output_func(payload, True)
        return exit_code
    return print_error_result_func(error, output_json, exit_code=exit_code)


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


def emit_one_shot_chat_payload(
    payload: dict[str, object],
    *,
    stream: JsonEventStream | None,
    output_json: bool,
    print_output_func: Callable[[dict[str, object], bool], None] = print_output,
) -> None:
    if stream is not None:
        stream.result(payload)
    else:
        print_output_func(payload, output_json)


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


def emit_one_shot_code_payload(
    result: AgentResult,
    payload: dict[str, object],
    *,
    stream: JsonEventStream | None,
    output_json: bool,
    print_mode: bool,
    print_output_func: Callable[[dict[str, object], bool], None] = print_output,
    print_agent_result_func: Callable[[AgentResult], None] = print_agent_result,
) -> None:
    if stream is not None:
        stream.result(payload)
    elif output_json:
        print_output_func(payload, True)
    elif print_mode:
        if "structured_output" in payload:
            print_output_func(
                {"message": json.dumps(payload["structured_output"], ensure_ascii=False, sort_keys=True)},
                False,
            )
        elif "structured_output_error" in payload:
            print_output_func({"message": payload["structured_output_error"]}, False)
        else:
            print_output_func({"message": result.message}, False)
    else:
        print_agent_result_func(result)


def apply_structured_output_result(
    payload: dict[str, object],
    structured: StructuredOutputResult | None,
) -> None:
    if structured is None:
        return
    payload["structuredOutputAttempts"] = structured.attempts
    payload["structured_output_attempts"] = structured.attempts
    if structured.success:
        payload["structuredOutput"] = structured.value
        payload["structured_output"] = structured.value
        payload["subtype"] = "success"
        return
    payload["success"] = False
    payload.update(
        machine_result_status_fields(
            status="failed",
            stop_reason="error_max_structured_output_retries",
            exit_code=1,
        )
    )
    payload["subtype"] = "error_max_structured_output_retries"
    payload["structuredOutputError"] = structured.error
    payload["structured_output_error"] = structured.error


def apply_model_budget_result(
    payload: dict[str, object],
    budget: ModelCostBudget | None,
) -> None:
    if budget is None:
        return
    report = budget.report()
    payload["budget"] = report
    payload["totalCostUsd"] = report["estimatedCostUsd"]
    payload["total_cost_usd"] = report["estimatedCostUsd"]
    if budget.failure is None:
        if payload.get("success") is True:
            payload.setdefault("subtype", "success")
        return
    exceeded = isinstance(budget.failure, ModelBudgetExceededError)
    subtype = "error_max_budget_usd" if exceeded else "error_during_execution"
    stop_reason = "error_max_budget_usd" if exceeded else "failed"
    payload["success"] = False
    payload.pop("result", None)
    payload.update(
        machine_result_status_fields(
            status="failed",
            stop_reason=stop_reason,
            exit_code=1,
        )
    )
    payload["subtype"] = subtype
    payload["budgetError"] = str(budget.failure)
    payload["budget_error"] = str(budget.failure)


def apply_model_fallback_result(
    payload: dict[str, object],
    fallback: ModelFallbackState | None,
) -> None:
    if fallback is None:
        return
    report = fallback.report()
    payload["modelFallback"] = report
    payload["model_fallback"] = report
    if payload.get("success") is True:
        payload.setdefault("subtype", "success")


def one_shot_code_exit_code(
    result: AgentResult,
    structured: StructuredOutputResult | None = None,
    budget: ModelCostBudget | None = None,
) -> int:
    if budget is not None and budget.failure is not None:
        return 1
    if structured is not None and not structured.success:
        return 1
    return 0 if result.success and result.completion_ready else 1
