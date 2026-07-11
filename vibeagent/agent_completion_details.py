from __future__ import annotations

from .agent_approval_targets import (
    command_batch_target,
    command_target,
    focused_test_commands_target,
    session_verification_target,
    suggested_checks_target,
)
from .agent_completion_kinds import PROJECT_CHANGE_OBSERVATION_KINDS
from .agent_observation_utils import observation_failed
from .types import Observation


def final_review_running_process_count(final_review: Observation | None) -> int:
    if final_review is None:
        return 0
    running_processes = getattr(final_review, "running_processes", [])
    return sum(1 for process in running_processes if getattr(process, "running", False))


def build_active_background_process_details(observations: list[Observation]) -> list[str]:
    final_review = latest_final_review(observations)
    if final_review is None:
        return []
    running_processes = getattr(final_review, "running_processes", [])
    details: list[str] = []
    for process in running_processes:
        if not getattr(process, "running", False):
            continue
        process_id = str(getattr(process, "process_id", "unknown") or "unknown")
        pid = getattr(process, "pid", None)
        cwd = str(getattr(process, "cwd", ".") or ".")
        command = str(getattr(process, "command", "") or "")
        details.append(f"{process_id}: pid={pid if pid is not None else 'unknown'}, cwd={cwd}, command={command}")
    return details


def build_final_review_blocking_issue_details(observations: list[Observation]) -> list[str]:
    final_review = latest_final_review(observations)
    if final_review is None:
        return []
    issues = getattr(final_review, "blocking_issues", [])
    if not isinstance(issues, list):
        return []
    return [str(issue) for issue in issues if str(issue).strip()]


def build_final_review_changed_file_details(observations: list[Observation]) -> list[str]:
    final_review = latest_final_review(observations)
    if final_review is None:
        return []
    files = getattr(final_review, "files", [])
    if not isinstance(files, list):
        return []
    details: list[str] = []
    for file in files:
        path = str(getattr(file, "path", "") or "").strip()
        if not path:
            continue
        status = str(getattr(file, "status", "") or "?").strip() or "?"
        details.append(f"{status} {path}")
    return details


def build_tool_error_details(observations: list[Observation]) -> list[str]:
    details: list[str] = []
    for observation in observations:
        if observation.kind != "tool_error":
            continue
        tool = str(getattr(observation, "tool", "unknown") or "unknown")
        message = str(getattr(observation, "message", "") or "tool execution failed")
        details.append(f"{tool}: {message}")
    return details


def build_checkpoint_failure_details(observations: list[Observation]) -> list[str]:
    details: list[str] = []
    for observation in observations:
        if observation.kind != "checkpoint_create" or not observation_failed(observation):
            continue
        message = str(getattr(observation, "message", "") or "checkpoint creation failed")
        details.append(f"checkpoint_create: {message}")
    return details


def build_denied_approval_details(observations: list[Observation]) -> list[str]:
    details: list[str] = []
    for index, observation in enumerate(observations):
        if observation.kind != "approval_denied":
            continue
        if denied_approval_resolved(observation, observations[index + 1 :]):
            continue
        details.append(denied_approval_detail(observation))
    return details


def denied_approval_resolved(denied: Observation, later_observations: list[Observation]) -> bool:
    action_type = str(getattr(denied, "action_type", "") or "")
    if not action_type:
        return False
    denied_target = str(getattr(denied, "target", "") or "")
    for observation in later_observations:
        if observation_failed(observation):
            continue
        if action_type not in PROJECT_CHANGE_OBSERVATION_KINDS:
            if observation.kind != action_type:
                continue
            if not denied_target or denied_approval_target_matches_observation(denied_target, observation):
                return True
            continue
        if observation.kind not in PROJECT_CHANGE_OBSERVATION_KINDS:
            continue
        if denied_approval_target_matches_observation(denied_target, observation):
            return True
    return False


def denied_approval_target_matches_observation(denied_target: str, observation: Observation) -> bool:
    denied_targets = normalized_approval_target_tokens(denied_target)
    if not denied_targets:
        return False
    observation_targets = observation_target_tokens(observation)
    return bool(denied_targets & observation_targets)


def observation_target_tokens(observation: Observation) -> set[str]:
    tokens: set[str] = set()
    for name in (
        "path",
        "definition_path",
        "source",
        "destination",
        "process_id",
        "url",
        "final_url",
        "server",
        "remote",
        "branch",
        "upstream",
        "stash_ref",
        "message_text",
        "checkpoint_id",
    ):
        tokens.update(normalized_approval_target_tokens(getattr(observation, name, "")))
    server = str(getattr(observation, "server", "") or "").strip()
    name = str(getattr(observation, "name", "") or "").strip()
    if server and name:
        tokens.add(f"{server}/{name}")
    path = str(getattr(observation, "path", "") or "").strip()
    pointer = str(getattr(observation, "pointer", "") or "").strip()
    if path and pointer:
        tokens.add(f"{path} {pointer}")
    summary_target = observation_summary_target_token(observation)
    if summary_target:
        tokens.add(summary_target)
    command = str(getattr(observation, "command", "") or "").strip()
    if command:
        cwd = str(getattr(observation, "cwd", ".") or ".")
        tokens.add(command_target(command, cwd))
    result = getattr(observation, "result", None)
    if result is not None:
        command = str(getattr(result, "command", "") or "").strip()
        if command:
            cwd = str(getattr(result, "cwd", ".") or ".")
            tokens.add(command_target(command, cwd))
    result_tokens = command_result_target_tokens(getattr(observation, "results", []))
    tokens.update(result_tokens)
    if result_tokens:
        tokens.add(command_batch_target(getattr(observation, "results", [])))
    for name in ("paths", "files"):
        values = getattr(observation, name, [])
        if not isinstance(values, list):
            continue
        for value in values:
            if isinstance(value, str):
                tokens.update(normalized_approval_target_tokens(value))
            else:
                tokens.update(normalized_approval_target_tokens(getattr(value, "path", "")))
    transfers = getattr(observation, "transfers", [])
    if isinstance(transfers, list):
        for transfer in transfers:
            tokens.update(normalized_approval_target_tokens(getattr(transfer, "source", "")))
            tokens.update(normalized_approval_target_tokens(getattr(transfer, "destination", "")))
    return tokens


def observation_summary_target_token(observation: Observation) -> str | None:
    max_commands = getattr(observation, "max_commands", None)
    if observation.kind == "run_suggested_checks" and isinstance(max_commands, int):
        return suggested_checks_target(max_commands)
    if observation.kind == "run_focused_test_commands" and isinstance(max_commands, int):
        return focused_test_commands_target(max_commands)
    if observation.kind == "run_session_verification":
        include_failed = int(getattr(observation, "failed_count", 0) or 0) > 0
        include_pending = int(getattr(observation, "pending_count", 0) or 0) > 0
        run_id = str(getattr(observation, "run_id", "") or "current session")
        return session_verification_target(run_id, include_failed, include_pending)
    keep_last = getattr(observation, "keep_last", None)
    if observation.kind == "checkpoint_prune" and isinstance(keep_last, int):
        return f"keep_last={keep_last}"
    if observation.kind == "stop_all_processes":
        return "background processes"
    return None


def command_result_target_tokens(results: object) -> list[str]:
    if not isinstance(results, list):
        return []
    tokens: list[str] = []
    for result in results:
        command = str(getattr(result, "command", "") or "").strip()
        if not command:
            continue
        cwd = str(getattr(result, "cwd", ".") or ".")
        tokens.append(command_target(command, cwd))
    return tokens


def normalized_approval_target_tokens(value: object) -> set[str]:
    text = str(value or "").strip()
    if not text:
        return set()
    if "(cwd:" in text:
        return {text}
    if _looks_like_path_pointer_target(text):
        return {text}
    tokens: set[str] = set()
    candidates = [text]
    candidates.extend(part.strip() for part in text.split(","))
    split_candidates = list(candidates)
    for candidate in split_candidates:
        if " -> " in candidate:
            candidates.extend(part.strip() for part in candidate.split(" -> "))
        if " " in candidate:
            candidates.append(candidate.split(" ", 1)[0].strip())
        if ":" in candidate and "://" not in candidate:
            candidates.append(candidate.split(":", 1)[0].strip())
    for candidate in candidates:
        normalized = candidate.strip()
        if normalized:
            tokens.add(normalized)
    return tokens


def _looks_like_path_pointer_target(text: str) -> bool:
    parts = text.split(" ", 1)
    return len(parts) == 2 and parts[1].startswith("/")


def denied_approval_detail(observation: Observation) -> str:
    action_type = str(getattr(observation, "action_type", "unknown") or "unknown")
    target = str(getattr(observation, "target", "") or "")
    message = str(getattr(observation, "message", "") or "")
    detail = action_type
    if target:
        detail += f" {target}"
    if message:
        detail += f": {message}"
    return detail


def latest_final_review(observations: list[Observation]) -> Observation | None:
    return next((observation for observation in reversed(observations) if observation.kind == "final_review"), None)
