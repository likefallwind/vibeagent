from __future__ import annotations

from .prompt_next_action_runtime_formatting import (
    context_labels,
    diagnostic_labels,
    format_next_action_items,
    not_run_selected_command_labels,
)
from .prompt_next_action_runtime_recovery import process_exited_with_failure, recovery_rerun_target
from .types import Observation


BATCH_COMMAND_RESULT_KINDS = {
    "run_commands",
    "run_suggested_checks",
    "run_focused_test_commands",
    "run_session_verification",
}


def diagnostics_next_action_instruction(
    base: str,
    latest: Observation,
    *,
    label: str,
    output_source: str,
    rerun_target: str,
    recovery_detail: str = "",
) -> str:
    diagnostics = diagnostic_labels(getattr(latest, "diagnostics", []))
    if diagnostics:
        return (
            f"{base} {label} diagnostics found concrete issues. "
            f"Inspect or edit the referenced source for: {format_next_action_items(diagnostics)}. "
            f"Then rerun the {rerun_target} before finishing.{recovery_detail}"
        )
    return (
        f"{base} {label} diagnostics did not find concrete file references. "
        f"Use the {output_source} and any available contexts to inspect the likely source, fix the issue, "
        f"and rerun the {rerun_target} before finishing.{recovery_detail}"
    )


def contexts_next_action_instruction(
    base: str,
    latest: Observation,
    *,
    label: str,
    fallback_tool: str,
    output_source: str,
    rerun_target: str,
    recovery_detail: str = "",
) -> str:
    contexts = context_labels(getattr(latest, "contexts", []))
    if contexts:
        return (
            f"{base} {label} contexts located source references. "
            f"Inspect or edit the relevant code for: {format_next_action_items(contexts)}. "
            f"Then rerun the {rerun_target} before finishing.{recovery_detail}"
        )
    return (
        f"{base} {label} contexts did not find source references. "
        f"Use {fallback_tool} or the {output_source} to identify the failure, "
        f"then fix it and rerun the {rerun_target} before finishing.{recovery_detail}"
    )


def command_output_rerun_target(observations: list[Observation]) -> str:
    return recovery_rerun_target(observations, BATCH_COMMAND_RESULT_KINDS) or "failed command"


def session_output_rerun_target(observations: list[Observation]) -> str:
    return recovery_rerun_target(observations, BATCH_COMMAND_RESULT_KINDS) or "relevant check"


def process_output_rerun_target(observations: list[Observation]) -> str:
    for observation in reversed(observations):
        if observation.kind in {"read_process", "wait_process"} and process_exited_with_failure(observation):
            return "background command or relevant check"
    return "relevant check"


def not_run_batch_command_labels(latest: Observation, ran_count: int) -> list[str]:
    if latest.kind == "run_suggested_checks":
        values = getattr(latest, "suggested_checks", [])
    elif latest.kind == "run_focused_test_commands":
        values = getattr(latest, "focused_commands", [])
    else:
        return []
    if not isinstance(values, list):
        return []

    labels: list[str] = []
    for index, value in enumerate(values):
        if index < ran_count:
            continue
        command = str(getattr(value, "command", "") or "").strip()
        cwd = str(getattr(value, "cwd", ".") or ".").strip() or "."
        if command:
            labels.append(not_run_batch_command_label(value, command=command, cwd=cwd))
    return labels


def not_run_batch_command_label(value: object, *, command: str, cwd: str) -> str:
    source = str(getattr(value, "source", "") or "").strip() or "."
    reason = str(getattr(value, "reason", "") or "").strip() or "."
    available = str(bool(getattr(value, "available", True))).lower()
    missing_tool = str(getattr(value, "missing_tool", "") or "none").strip() or "none"
    return (
        f"{command} (cwd={cwd}, source={source}, available={available}, "
        f"missingTool={missing_tool}, reason={reason})"
    )


def not_run_session_verification_labels(observation: Observation) -> list[str]:
    return not_run_selected_command_labels(
        getattr(observation, "selected_commands", []),
        len(getattr(observation, "results", []) or []),
    )


def not_run_detail(labels: list[str]) -> str:
    return (
        f" Not-yet-run selected check(s): {format_next_action_items(labels)}."
        if labels
        else ""
    )


def recovery_not_run_detail(observations: list[Observation]) -> str:
    for observation in reversed(observations):
        if observation.kind == "run_session_verification":
            if not getattr(observation, "stopped_early", False):
                return ""
            return not_run_detail(not_run_session_verification_labels(observation))
        if observation.kind in {"run_suggested_checks", "run_focused_test_commands"}:
            if not getattr(observation, "stopped_early", False):
                return ""
            return not_run_detail(
                not_run_batch_command_labels(
                    observation,
                    len(getattr(observation, "results", []) or []),
                )
            )
    return ""
