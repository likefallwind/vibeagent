from __future__ import annotations

import json

from .agent_approval_targets import (
    command_batch_target,
    command_target,
    focused_test_commands_target,
    session_verification_target,
    suggested_checks_target,
)
from .agent_completion_kinds import PROJECT_CHANGE_OBSERVATION_KINDS
from .agent_observation_utils import observation_failed, summarize
from .types import Observation

BASIC_TARGET_FIELDS = (
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
)

EXACT_MESSAGE_TARGET_ACTION_TYPES = {"git_commit", "git_stash"}


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
            if not denied_target or denied_approval_target_matches_observation(action_type, denied_target, observation):
                return True
            continue
        if observation.kind not in PROJECT_CHANGE_OBSERVATION_KINDS:
            continue
        if denied_approval_target_matches_observation(action_type, denied_target, observation):
            return True
    return False


def denied_approval_target_matches_observation(action_type: str, denied_target: str, observation: Observation) -> bool:
    if action_type in EXACT_MESSAGE_TARGET_ACTION_TYPES:
        return denied_target in exact_message_target_tokens(observation)
    denied_targets = normalized_approval_target_tokens(denied_target)
    if not denied_targets:
        return False
    observation_targets = observation_target_tokens(observation)
    return bool(denied_targets & observation_targets)


def exact_message_target_tokens(observation: Observation) -> set[str]:
    message_text = str(getattr(observation, "message_text", "") or "").strip()
    if not message_text:
        return set()
    return {message_text, summarize(message_text, 120)}


def observation_target_tokens(observation: Observation) -> set[str]:
    tokens: set[str] = set()
    add_basic_target_tokens(tokens, observation)
    tokens.update(transfer_target_tokens(observation))
    add_mcp_target_tokens(tokens, observation)
    path = str(getattr(observation, "path", "") or "").strip()
    add_json_pointer_target_tokens(tokens, observation, path)
    add_line_target_tokens(tokens, observation, path)
    tokens.update(observation_symbol_target_tokens(observation))
    summary_target = observation_summary_target_token(observation)
    if summary_target:
        tokens.add(summary_target)
    add_command_target_tokens(tokens, observation)
    add_path_list_target_tokens(tokens, getattr(observation, "paths", []))
    add_path_list_target_tokens(tokens, getattr(observation, "files", []))
    add_transfer_list_target_tokens(tokens, getattr(observation, "transfers", []))
    return tokens


def add_basic_target_tokens(tokens: set[str], observation: Observation) -> None:
    for name in BASIC_TARGET_FIELDS:
        tokens.update(normalized_approval_target_tokens(getattr(observation, name, "")))


def add_mcp_target_tokens(tokens: set[str], observation: Observation) -> None:
    server = str(getattr(observation, "server", "") or "").strip()
    name = str(getattr(observation, "name", "") or "").strip()
    if not server or not name:
        return
    tokens.add(f"{server}/{name}")
    mcp_target = mcp_call_target_token(observation, server, name)
    if mcp_target:
        tokens.add(mcp_target)


def add_json_pointer_target_tokens(tokens: set[str], observation: Observation, path: str) -> None:
    pointer = str(getattr(observation, "pointer", "") or "").strip()
    if path and pointer:
        tokens.add(f"{path} {pointer}")


def add_line_target_tokens(tokens: set[str], observation: Observation, path: str) -> None:
    line = getattr(observation, "line", None)
    if path and isinstance(line, int):
        tokens.add(f"{path}:{line}")
    start_line = getattr(observation, "start_line", None)
    end_line = getattr(observation, "end_line", None)
    if path and isinstance(start_line, int) and isinstance(end_line, int):
        tokens.add(f"{path}:{start_line}-{end_line}")


def add_command_target_tokens(tokens: set[str], observation: Observation) -> None:
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


def add_path_list_target_tokens(tokens: set[str], values: object) -> None:
    if not isinstance(values, list):
        return
    path_values = [path_target(value) for value in values]
    batch_target = batch_path_target(path_values)
    if batch_target:
        tokens.add(batch_target)
    for value in values:
        tokens.update(normalized_approval_target_tokens(path_target(value)))


def add_transfer_list_target_tokens(tokens: set[str], transfers: object) -> None:
    if not isinstance(transfers, list):
        return
    batch_target = batch_transfer_target(transfers)
    if batch_target:
        tokens.add(batch_target)
    for transfer in transfers:
        tokens.update(transfer_target_tokens(transfer))


def string_attr(value: object, name: str, default: str = "") -> str:
    return str(getattr(value, name, default) or default).strip()


def transfer_target_tokens(value: object) -> set[str]:
    source = string_attr(value, "source")
    destination = string_attr(value, "destination")
    if not source or not destination:
        return set()
    return {f"{source} -> {destination}"}


def path_target(value: object) -> str:
    if isinstance(value, str):
        return value.strip()
    return string_attr(value, "path")


def batch_path_target(paths: list[str]) -> str | None:
    clean_paths = [path for path in paths if path]
    if len(clean_paths) < 2:
        return None
    return ", ".join(clean_paths)


def batch_transfer_target(transfers: list[object]) -> str | None:
    targets: list[str] = []
    for transfer in transfers:
        source = string_attr(transfer, "source")
        destination = string_attr(transfer, "destination")
        if source and destination:
            targets.append(f"{source} -> {destination}")
    if len(targets) < 2:
        return None
    return ", ".join(targets)


def mcp_call_target_token(observation: Observation, server: str, name: str) -> str | None:
    if observation.kind != "mcp_call":
        return None
    arguments = getattr(observation, "arguments", None)
    if not isinstance(arguments, dict):
        return None
    serialized = summarize(json.dumps(arguments, ensure_ascii=False), 500)
    return f"{server}/{name} arguments={serialized}"


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
    if observation.kind == "git_switch":
        branch = str(getattr(observation, "branch", "") or "").strip()
        create = bool(getattr(observation, "create", False))
        if branch:
            return f"{branch}{' (create)' if create else ''}"
    if observation.kind == "git_fetch":
        return "default remote"
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
    if should_preserve_approval_target(text):
        return {text}
    tokens: set[str] = set()
    candidates = [text]
    candidates.extend(part.strip() for part in text.split(","))
    split_candidates = list(candidates)
    for candidate in split_candidates:
        if should_preserve_approval_target(candidate):
            continue
        if " -> " in candidate and "," not in candidate and not _looks_like_transfer_target(candidate):
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


def should_preserve_approval_target(text: str) -> bool:
    return (
        "(cwd:" in text
        or _looks_like_path_pointer_target(text)
        or _looks_like_path_line_target(text)
        or _looks_like_symbol_target(text)
        or _looks_like_operation_count_target(text)
        or _looks_like_char_count_target(text)
        or _looks_like_transfer_target(text)
        or _looks_like_mcp_arguments_target(text)
        or _looks_like_git_switch_create_target(text)
        or _looks_like_comma_list_target(text)
    )


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


def _looks_like_comma_list_target(text: str) -> bool:
    return "," in text and all(part.strip() for part in text.split(","))


def _looks_like_mcp_arguments_target(text: str) -> bool:
    tool, separator, arguments = text.partition(" arguments=")
    return bool(separator and "/" in tool and tool.strip() and arguments.strip())


def _looks_like_git_switch_create_target(text: str) -> bool:
    return text.endswith(" (create)") and bool(text.removesuffix(" (create)").strip())
