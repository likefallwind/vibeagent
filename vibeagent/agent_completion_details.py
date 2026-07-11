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
    tokens.update(transfer_target_tokens(observation))
    server = str(getattr(observation, "server", "") or "").strip()
    name = str(getattr(observation, "name", "") or "").strip()
    if server and name:
        tokens.add(f"{server}/{name}")
    path = str(getattr(observation, "path", "") or "").strip()
    pointer = str(getattr(observation, "pointer", "") or "").strip()
    if path and pointer:
        tokens.add(f"{path} {pointer}")
    line = getattr(observation, "line", None)
    if path and isinstance(line, int):
        tokens.add(f"{path}:{line}")
    start_line = getattr(observation, "start_line", None)
    end_line = getattr(observation, "end_line", None)
    if path and isinstance(start_line, int) and isinstance(end_line, int):
        tokens.add(f"{path}:{start_line}-{end_line}")
    tokens.update(observation_symbol_target_tokens(observation))
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
            source = string_attr(transfer, "source")
            destination = string_attr(transfer, "destination")
            tokens.update(normalized_approval_target_tokens(source))
            tokens.update(normalized_approval_target_tokens(destination))
            tokens.update(transfer_target_tokens(transfer))
    return tokens


def string_attr(value: object, name: str, default: str = "") -> str:
    return str(getattr(value, name, default) or default).strip()


def transfer_target_tokens(value: object) -> set[str]:
    source = string_attr(value, "source")
    destination = string_attr(value, "destination")
    if not source or not destination:
        return set()
    return {f"{source} -> {destination}"}


def observation_symbol_target_tokens(observation: Observation) -> set[str]:
    symbol = str(getattr(observation, "symbol", "") or "").strip()
    qualified_name = str(getattr(observation, "qualified_name", "") or "").strip()
    new_name = str(getattr(observation, "new_name", "") or "").strip()
    symbols = {value for value in (symbol, qualified_name) if value}
    if not symbols:
        return set()

    paths = [
        str(getattr(observation, attr, "") or "").strip()
        for attr in ("path", "definition_path")
    ]
    paths = [path for path in paths if path]
    if not paths:
        paths = ["."]

    tokens: set[str] = set()
    for current_symbol in symbols:
        for path in paths:
            tokens.add(f"{current_symbol} in {path}")
            if new_name:
                tokens.add(f"{current_symbol} -> {new_name} in {path}")
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
    if observation.kind == "json_patch":
        path = str(getattr(observation, "path", "") or "").strip()
        operation_count = getattr(observation, "operation_count", None)
        if path and isinstance(operation_count, int):
            return f"{path} ({operation_count} operations)"
    if observation.kind == "write_process":
        process_id = str(getattr(observation, "process_id", "") or "").strip()
        content_chars = getattr(observation, "content_chars", None)
        if process_id and isinstance(content_chars, int):
            return f"{process_id} ({content_chars} chars)"
    if observation.kind == "patch_files":
        return "multiple files"
    keep_last = getattr(observation, "keep_last", None)
    if observation.kind == "checkpoint_prune" and isinstance(keep_last, int):
        return f"keep_last={keep_last}"
    if observation.kind in {"git_pull", "git_push"}:
        return "current branch upstream"
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
    if (
        _looks_like_path_pointer_target(text)
        or _looks_like_path_line_target(text)
        or _looks_like_symbol_target(text)
        or _looks_like_operation_count_target(text)
        or _looks_like_char_count_target(text)
        or _looks_like_transfer_target(text)
    ):
        return {text}
    tokens: set[str] = set()
    candidates = [text]
    candidates.extend(part.strip() for part in text.split(","))
    split_candidates = list(candidates)
    for candidate in split_candidates:
        if " -> " in candidate and not _looks_like_transfer_target(candidate):
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


def _looks_like_path_line_target(text: str) -> bool:
    prefix, separator, suffix = text.rpartition(":")
    if not separator or not prefix or not suffix:
        return False
    if "-" in suffix:
        start, end = suffix.split("-", 1)
        return bool(start.isdigit() and end.isdigit())
    return suffix.isdigit()


def _looks_like_symbol_target(text: str) -> bool:
    if " in " not in text:
        return False
    symbol_part, _, path_part = text.rpartition(" in ")
    if not symbol_part.strip() or not path_part.strip():
        return False
    if " -> " in symbol_part:
        old_name, new_name = symbol_part.split(" -> ", 1)
        return bool(old_name.strip() and new_name.strip())
    return True


def _looks_like_operation_count_target(text: str) -> bool:
    return _looks_like_count_target(text, "operations")


def _looks_like_char_count_target(text: str) -> bool:
    return _looks_like_count_target(text, "chars")


def _looks_like_count_target(text: str, label: str) -> bool:
    prefix, separator, suffix = text.rpartition(" (")
    suffix_text = f" {label})"
    if not separator or not prefix.strip() or not suffix.endswith(suffix_text):
        return False
    count_text = suffix.removesuffix(suffix_text)
    return count_text.isdigit()


def _looks_like_transfer_target(text: str) -> bool:
    if "," in text:
        return False
    source, separator, destination = text.partition(" -> ")
    return bool(separator and source.strip() and destination.strip())


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
