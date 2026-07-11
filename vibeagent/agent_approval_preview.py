from __future__ import annotations

from dataclasses import replace
from typing import Any

from .agent_observation_utils import summarize
from .types import ApprovalRequest, Observation


PREVIEW_KIND_BY_ACTION_TYPE = {
    "write_file": "check_write_file",
    "write_files": "check_write_files",
    "edit_file": "check_edit_file",
    "multi_edit_file": "check_multi_edit_file",
    "replace_python_definition": "check_replace_python_definition",
    "code_rename": "code_rename_preview",
    "python_rename": "python_rename_preview",
    "replace_lines": "check_replace_lines",
    "insert_lines": "check_insert_lines",
    "append_file": "check_append_file",
    "regex_replace": "check_regex_replace",
    "json_set": "check_json_set",
    "json_remove": "check_json_remove",
    "json_patch": "check_json_patch",
    "patch_file": "check_patch",
    "patch_files": "check_patches",
    "delete_file": "check_delete_file",
    "delete_files": "check_delete_files",
    "move_file": "check_move_file",
    "move_files": "check_move_files",
    "copy_file": "check_copy_file",
    "copy_files": "check_copy_files",
    "move_dir": "check_move_dir",
    "move_dirs": "check_move_dirs",
    "copy_dir": "check_copy_dir",
    "copy_dirs": "check_copy_dirs",
    "create_dir": "check_create_dir",
    "create_dirs": "check_create_dirs",
    "delete_empty_dir": "check_delete_empty_dir",
    "delete_empty_dirs": "check_delete_empty_dirs",
    "set_executable": "check_set_executable",
    "git_stage": "check_git_stage",
    "git_unstage": "check_git_unstage",
    "git_commit": "check_git_commit",
    "git_fetch": "check_git_fetch",
    "git_pull": "check_git_pull",
    "git_push": "check_git_push",
    "git_restore": "check_git_restore",
    "git_switch": "check_git_switch",
    "git_stash": "check_git_stash",
    "git_stash_apply": "check_git_stash_apply",
    "git_stash_drop": "check_git_stash_drop",
    "checkpoint_restore": "check_checkpoint_restore",
    "checkpoint_delete": "check_checkpoint_delete",
    "checkpoint_prune": "check_checkpoint_prune",
    "run_command": "command_check",
    "run_commands": "check_run_commands",
    "run_suggested_checks": "check_suggested_checks",
    "run_focused_test_commands": "check_focused_test_commands",
    "run_session_verification": "session_verification",
    "start_command": "check_start_command",
    "write_process": "check_write_process",
    "stop_process": "check_stop_process",
    "stop_all_processes": "check_stop_all_processes",
}

# External requests cannot be meaningfully previewed without performing the
# disclosure that approval is intended to guard.
APPROVAL_WITHOUT_PREVIEW_ACTION_TYPES = {"mcp_call", "mcp_tools", "web_fetch"}


def attach_approval_preview(
    request: ApprovalRequest,
    action: object,
    observations: list[Observation],
) -> ApprovalRequest:
    preview = approval_preview_summary(action, observations)
    if not preview:
        return request
    return replace(request, preview=preview)


def approval_preview_summary(action: object, observations: list[Observation]) -> str | None:
    expected_kind = PREVIEW_KIND_BY_ACTION_TYPE.get(str(getattr(action, "type", "")))
    if not expected_kind:
        return None
    expected_key = approval_preview_key(action)
    for observation in reversed(observations):
        if getattr(observation, "kind", None) != expected_kind:
            continue
        if getattr(observation, "ok", True) is not True:
            continue
        if approval_preview_key(observation) != expected_key:
            continue
        return summarize_preview_observation(observation)
    return None


def summarize_preview_observation(observation: object) -> str:
    message = getattr(observation, "message", "")
    parts = [summarize(message, 160) if isinstance(message, str) and message.strip() else "Matching preview completed."]
    diff = getattr(observation, "diff", None)
    if isinstance(diff, str) and diff:
        parts.append(f"diffChars={len(diff)}")
    checks = getattr(observation, "checks", None)
    if isinstance(checks, list):
        parts.append(f"commands={len(checks)}")
    return "; ".join(parts)


def approval_preview_key(value: object) -> tuple[Any, ...]:
    kind = str(getattr(value, "kind", getattr(value, "type", "")))
    if kind in {"write_file", "check_write_file", "edit_file", "check_edit_file", "multi_edit_file", "check_multi_edit_file", "append_file", "check_append_file", "regex_replace", "check_regex_replace", "patch_file", "check_patch", "delete_file", "check_delete_file", "create_dir", "check_create_dir", "delete_empty_dir", "check_delete_empty_dir", "set_executable", "check_set_executable"}:
        return (kind.replace("check_", ""), getattr(value, "path", ""), getattr(value, "executable", None))
    if kind in {"json_set", "check_json_set", "json_remove", "check_json_remove"}:
        return (kind.replace("check_", ""), getattr(value, "path", ""), getattr(value, "pointer", ""))
    if kind in {"json_patch", "check_json_patch"}:
        return ("json_patch", getattr(value, "path", ""), getattr(value, "operation_count", len(getattr(value, "operations", []))))
    if kind in {"replace_lines", "check_replace_lines"}:
        return ("replace_lines", getattr(value, "path", ""), getattr(value, "start_line", None), getattr(value, "end_line", None))
    if kind in {"insert_lines", "check_insert_lines"}:
        return ("insert_lines", getattr(value, "path", ""), getattr(value, "line", None))
    if kind in {"replace_python_definition", "check_replace_python_definition"}:
        return ("replace_python_definition", getattr(value, "symbol", ""), getattr(value, "path", None))
    if kind in {"python_rename", "python_rename_preview"}:
        return ("python_rename", getattr(value, "symbol", ""), getattr(value, "new_name", ""), getattr(value, "path", None))
    if kind in {"code_rename", "code_rename_preview"}:
        return ("code_rename", getattr(value, "symbol", ""), getattr(value, "new_name", ""), getattr(value, "path", None))
    if kind in {"write_files", "check_write_files"}:
        return ("write_files", tuple(getattr(item, "path", "") for item in getattr(value, "files", [])))
    if kind in {"delete_files", "check_delete_files", "create_dirs", "check_create_dirs", "delete_empty_dirs", "check_delete_empty_dirs", "git_stage", "check_git_stage", "git_unstage", "check_git_unstage", "git_restore", "check_git_restore"}:
        return (kind.replace("check_", ""), tuple(getattr(value, "paths", [])))
    if kind in {"move_file", "check_move_file", "copy_file", "check_copy_file", "move_dir", "check_move_dir", "copy_dir", "check_copy_dir"}:
        return (kind.replace("check_", ""), getattr(value, "source", ""), getattr(value, "destination", ""))
    if kind in {"move_files", "check_move_files", "copy_files", "check_copy_files", "move_dirs", "check_move_dirs", "copy_dirs", "check_copy_dirs"}:
        return (
            kind.replace("check_", ""),
            tuple((getattr(item, "source", ""), getattr(item, "destination", "")) for item in getattr(value, "transfers", [])),
        )
    if kind in {"patch_files", "check_patches"}:
        return ("patch_files",)
    if kind in {"git_fetch", "check_git_fetch"}:
        return ("git_fetch", getattr(value, "remote", None) or "default remote")
    if kind in {"git_pull", "check_git_pull", "git_push", "check_git_push"}:
        return (kind.replace("check_", ""),)
    if kind in {"git_commit", "check_git_commit"}:
        return ("git_commit", getattr(value, "message_text", getattr(value, "message", "")))
    if kind in {"git_switch", "check_git_switch"}:
        return ("git_switch", getattr(value, "branch", ""), getattr(value, "create", False))
    if kind in {"git_stash", "check_git_stash"}:
        return ("git_stash", getattr(value, "message_text", getattr(value, "message", None)), getattr(value, "include_untracked", False))
    if kind in {"git_stash_apply", "check_git_stash_apply", "git_stash_drop", "check_git_stash_drop"}:
        return (kind.replace("check_", ""), getattr(value, "stash_ref", ""))
    if kind in {"checkpoint_restore", "check_checkpoint_restore", "checkpoint_delete", "check_checkpoint_delete"}:
        return (kind.replace("check_", ""), getattr(value, "checkpoint_id", ""))
    if kind in {"checkpoint_prune", "check_checkpoint_prune"}:
        return ("checkpoint_prune", getattr(value, "keep_last", None))
    if kind in {"run_command", "command_check", "start_command", "check_start_command"}:
        normalized = "run_command" if kind == "command_check" else kind.replace("check_", "")
        return (normalized, getattr(value, "command", ""), getattr(value, "cwd", None) or ".")
    if kind in {"run_commands", "check_run_commands"}:
        commands = getattr(value, "commands", None)
        if commands is None:
            commands = getattr(value, "checks", [])
        return ("run_commands", tuple((getattr(item, "command", ""), getattr(item, "cwd", None) or ".") for item in commands))
    if kind in {"run_suggested_checks", "check_suggested_checks"}:
        return ("run_suggested_checks", getattr(value, "max_commands", None))
    if kind in {"run_focused_test_commands", "check_focused_test_commands"}:
        paths = tuple(getattr(value, "paths", None) or ())
        return ("run_focused_test_commands", paths, getattr(value, "max_commands", None))
    if kind in {"run_session_verification", "session_verification"}:
        return ("run_session_verification", getattr(value, "run_id", None))
    if kind in {"write_process", "check_write_process"}:
        return ("write_process", getattr(value, "process_id", ""), getattr(value, "content_chars", len(getattr(value, "content", ""))))
    if kind in {"stop_process", "check_stop_process"}:
        return ("stop_process", getattr(value, "process_id", ""))
    if kind in {"stop_all_processes", "check_stop_all_processes"}:
        return ("stop_all_processes",)
    return (kind,)
