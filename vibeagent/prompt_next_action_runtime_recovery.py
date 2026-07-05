from __future__ import annotations

from .prompt_next_action_runtime_formatting import context_labels, failed_command_labels
from .types import Observation


RECOVERY_SIGNAL_KINDS = {
    "output_diagnostics",
    "output_contexts",
    "process_output_diagnostics",
    "process_output_contexts",
}

PROCESS_RECOVERY_SIGNAL_KINDS = {
    "process_output_diagnostics",
    "process_output_contexts",
}

SESSION_RECOVERY_SIGNAL_KINDS = {
    "session_output_diagnostics",
    "session_output_contexts",
}

SOURCE_CONTEXT_KINDS = {
    "read_file_context",
    "read_file_contexts",
}


def source_context_labels(observation: Observation) -> list[str]:
    if observation.kind == "read_file_context":
        path = str(getattr(observation, "path", "") or "").strip()
        line = getattr(observation, "line", None)
        if path and isinstance(line, int):
            label = f"{path}:{line}"
        else:
            label = path
        if label and not getattr(observation, "ok", True):
            return [f"{label} (context unavailable)"]
        return [label] if label else []
    if observation.kind == "read_file_contexts":
        return context_labels(getattr(observation, "contexts", []))
    return []


def process_exited_with_failure(observation: Observation) -> bool:
    if not getattr(observation, "ok", False) or getattr(observation, "running", False):
        return False
    exit_code = getattr(observation, "exit_code", 0)
    signal = getattr(observation, "signal", None)
    return bool(signal) or (exit_code is not None and exit_code != 0)


def _session_recovery_rerun_target(observations: list[Observation]) -> str:
    for observation in reversed(observations):
        if observation.kind == "run_session_verification":
            if failed_command_labels(getattr(observation, "results", [])):
                return "run_session_verification"
            return "session_verification"
        if observation.kind == "session_verification":
            return "run_session_verification"
        if observation.kind in {"session_handoff", "session_audit"}:
            return "session_audit"
    return "relevant check"


def _command_recovery_rerun_target(observations: list[Observation], batch_command_kinds: set[str]) -> str:
    for observation in reversed(observations):
        if observation.kind in batch_command_kinds:
            if failed_command_labels(getattr(observation, "results", [])):
                return str(observation.kind)
        if observation.kind == "run_command":
            result = observation.result
            if result.exit_code != 0 or result.timed_out:
                return "failed command"
    return "failed command"


def _process_recovery_rerun_target() -> str:
    return "background command or relevant check"


def recovery_rerun_target(observations: list[Observation], batch_command_kinds: set[str]) -> str | None:
    for index in range(len(observations) - 1, -1, -1):
        observation = observations[index]
        if observation.kind in SESSION_RECOVERY_SIGNAL_KINDS:
            return _session_recovery_rerun_target(observations[:index])
        if observation.kind in PROCESS_RECOVERY_SIGNAL_KINDS:
            return _process_recovery_rerun_target()
        if observation.kind in RECOVERY_SIGNAL_KINDS:
            return _command_recovery_rerun_target(observations[:index], batch_command_kinds)
        if observation.kind in {"read_process", "wait_process"} and process_exited_with_failure(observation):
            return _process_recovery_rerun_target()
        if observation.kind == "run_session_verification":
            if failed_command_labels(getattr(observation, "results", [])):
                return "run_session_verification"
        if observation.kind in batch_command_kinds:
            if failed_command_labels(getattr(observation, "results", [])):
                return str(observation.kind)
        if observation.kind == "run_command":
            result = observation.result
            if result.exit_code != 0 or result.timed_out:
                return "failed command"
    return None
