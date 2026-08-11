from __future__ import annotations

import json

from .agent_approval_targets import (
    command_batch_target,
    command_target,
    focused_test_commands_target,
    session_verification_target,
    suggested_checks_target,
)
from .agent_completion_target_normalization import normalized_approval_target_tokens, should_preserve_approval_target
from .agent_observation_utils import summarize
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
    "comment_target",
)


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
