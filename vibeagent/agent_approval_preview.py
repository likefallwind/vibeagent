from __future__ import annotations

import hashlib
import json
from dataclasses import replace
from typing import Any

from .agent_observation_utils import summarize
from .types import ApprovalRequest, Observation


PREVIEW_KIND_BY_ACTION_TYPE = {
    "write_file": "check_write_file",
    "write_files": "check_write_files",
    "edit_file": "check_edit_file",
    "notebook_edit": "check_notebook_edit",
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
        parts.append(f"diffSha256={preview_digest(diff)}")
    checks = getattr(observation, "checks", None)
    if isinstance(checks, list):
        parts.append(f"commands={len(checks)}")
        if checks:
            parts.append(f"commandsSha256={preview_digest(command_check_fingerprint_payload(checks))}")
    file_diffs = preview_file_diffs(getattr(observation, "files", None))
    if file_diffs:
        parts.append(f"fileDiffs={len(file_diffs)}")
        parts.append(f"fileDiffsSha256={preview_digest(file_diff_fingerprint_payload(file_diffs))}")
    return "; ".join(parts)


def preview_digest(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()[:12]


def command_check_fingerprint_payload(checks: list[object]) -> str:
    payload = [
        {
            "command": str(getattr(check, "command", "") or ""),
            "cwd": str(getattr(check, "cwd", ".") or "."),
            "ok": bool(getattr(check, "ok", False)),
            "blocked": bool(getattr(check, "blocked", False)),
            "missing_tool": getattr(check, "missing_tool", None),
        }
        for check in checks
    ]
    return json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def preview_file_diffs(files: object) -> list[object]:
    if not isinstance(files, list):
        return []
    return [file for file in files if isinstance(getattr(file, "diff", None), str) and getattr(file, "diff")]


def file_diff_fingerprint_payload(files: list[object]) -> str:
    payload = [
        {
            "path": str(getattr(file, "path", "") or ""),
            "diff": str(getattr(file, "diff", "") or ""),
            "truncated": bool(getattr(file, "truncated", False)),
        }
        for file in files
    ]
    return json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def approval_preview_key(value: object) -> tuple[Any, ...]:
    kind = str(getattr(value, "kind", getattr(value, "type", "")))
    edit_key = edit_preview_key(kind, value)
    if edit_key is not None:
        return edit_key
    file_key = file_preview_key(kind, value)
    if file_key is not None:
        return file_key
    structured_key = structured_edit_preview_key(kind, value)
    if structured_key is not None:
        return structured_key
    code_key = code_preview_key(kind, value)
    if code_key is not None:
        return code_key
    transfer_key = transfer_preview_key(kind, value)
    if transfer_key is not None:
        return transfer_key
    git_key = git_preview_key(kind, value)
    if git_key is not None:
        return git_key
    workflow_key = workflow_preview_key(kind, value)
    if workflow_key is not None:
        return workflow_key
    run_key = run_preview_key(kind, value)
    if run_key is not None:
        return run_key
    return (kind,)


def edit_preview_key(kind: str, value: object) -> tuple[Any, ...] | None:
    if kind in {"edit_file", "check_edit_file"}:
        return (kind.replace("check_", ""), getattr(value, "path", ""), getattr(value, "old", ""), getattr(value, "new", ""))
    if kind in {"multi_edit_file", "check_multi_edit_file"}:
        return (
            kind.replace("check_", ""),
            getattr(value, "path", ""),
            tuple(
                (getattr(edit, "old", ""), getattr(edit, "new", ""), getattr(edit, "replace_all", False))
                for edit in getattr(value, "edits", []) or []
            ),
        )
    if kind in {"replace_lines", "check_replace_lines"}:
        return (
            "replace_lines",
            getattr(value, "path", ""),
            getattr(value, "start_line", None),
            getattr(value, "end_line", None),
            getattr(value, "content", ""),
        )
    if kind in {"insert_lines", "check_insert_lines"}:
        return ("insert_lines", getattr(value, "path", ""), getattr(value, "line", None), getattr(value, "content", ""))
    if kind in {"append_file", "check_append_file"}:
        return ("append_file", getattr(value, "path", ""), getattr(value, "content", ""))
    if kind in {"patch_file", "check_patch"}:
        return ("patch_file", getattr(value, "path", ""), getattr(value, "patch", ""))
    if kind in {"patch_files", "check_patches"}:
        return ("patch_files", getattr(value, "patch", ""))
    return None


def file_preview_key(kind: str, value: object) -> tuple[Any, ...] | None:
    if kind in {"write_file", "check_write_file"}:
        return ("write_file", getattr(value, "path", ""), getattr(value, "content", ""))
    if kind in {"write_files", "check_write_files"}:
        input_files = getattr(value, "inputs", None) or getattr(value, "files", [])
        return (
            "write_files",
            tuple((getattr(item, "path", ""), getattr(item, "content", "")) for item in input_files),
        )
    if kind in {"delete_file", "check_delete_file", "create_dir", "check_create_dir", "delete_empty_dir", "check_delete_empty_dir", "set_executable", "check_set_executable"}:
        return (kind.replace("check_", ""), getattr(value, "path", ""), getattr(value, "executable", None))
    if kind in {"delete_files", "check_delete_files", "create_dirs", "check_create_dirs", "delete_empty_dirs", "check_delete_empty_dirs", "git_stage", "check_git_stage", "git_unstage", "check_git_unstage", "git_restore", "check_git_restore"}:
        return (kind.replace("check_", ""), tuple(getattr(value, "paths", [])))
    return None


def structured_edit_preview_key(kind: str, value: object) -> tuple[Any, ...] | None:
    if kind in {"regex_replace", "check_regex_replace"}:
        return (
            "regex_replace",
            getattr(value, "path", ""),
            getattr(value, "pattern", ""),
            getattr(value, "replacement", ""),
            getattr(value, "count", 0),
            getattr(value, "case_sensitive", True),
            getattr(value, "multiline", False),
            getattr(value, "max_replacements", 100),
        )
    if kind in {"notebook_edit", "check_notebook_edit"}:
        return (
            "notebook_edit",
            getattr(value, "path", ""),
            getattr(value, "cell_id", None),
            getattr(value, "cell_number", None),
            getattr(value, "new_source", ""),
            getattr(value, "cell_type", None),
        )
    if kind in {"json_set", "check_json_set"}:
        return (
            "json_set",
            getattr(value, "path", ""),
            getattr(value, "pointer", ""),
            json.dumps(getattr(value, "value", None), ensure_ascii=False, sort_keys=True, separators=(",", ":")),
            getattr(value, "create_missing", False),
        )
    if kind in {"json_remove", "check_json_remove"}:
        return (kind.replace("check_", ""), getattr(value, "path", ""), getattr(value, "pointer", ""))
    if kind in {"json_patch", "check_json_patch"}:
        operations = getattr(value, "operations", None) or []
        operation_payload = [
            {"op": getattr(operation, "op", ""), "path": getattr(operation, "path", ""), "value": getattr(operation, "value", None)}
            for operation in operations
        ]
        return (
            "json_patch",
            getattr(value, "path", ""),
            json.dumps(operation_payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")),
        )
    return None


def code_preview_key(kind: str, value: object) -> tuple[Any, ...] | None:
    if kind in {"replace_python_definition", "check_replace_python_definition"}:
        return ("replace_python_definition", getattr(value, "symbol", ""), getattr(value, "path", None))
    if kind in {"python_rename", "python_rename_preview"}:
        return ("python_rename", getattr(value, "symbol", ""), getattr(value, "new_name", ""), getattr(value, "path", None))
    if kind in {"code_rename", "code_rename_preview"}:
        return ("code_rename", getattr(value, "symbol", ""), getattr(value, "new_name", ""), getattr(value, "path", None))
    return None


def transfer_preview_key(kind: str, value: object) -> tuple[Any, ...] | None:
    if kind in {"move_file", "check_move_file", "copy_file", "check_copy_file", "move_dir", "check_move_dir", "copy_dir", "check_copy_dir"}:
        return (kind.replace("check_", ""), getattr(value, "source", ""), getattr(value, "destination", ""))
    if kind in {"move_files", "check_move_files", "copy_files", "check_copy_files", "move_dirs", "check_move_dirs", "copy_dirs", "check_copy_dirs"}:
        return (
            kind.replace("check_", ""),
            tuple((getattr(item, "source", ""), getattr(item, "destination", "")) for item in getattr(value, "transfers", [])),
        )
    return None


def workflow_preview_key(kind: str, value: object) -> tuple[Any, ...] | None:
    if kind in {"checkpoint_restore", "check_checkpoint_restore", "checkpoint_delete", "check_checkpoint_delete"}:
        return (kind.replace("check_", ""), getattr(value, "checkpoint_id", ""))
    if kind in {"checkpoint_prune", "check_checkpoint_prune"}:
        return ("checkpoint_prune", getattr(value, "keep_last", None))
    return None


def git_preview_key(kind: str, value: object) -> tuple[Any, ...] | None:
    if kind in {"git_fetch", "check_git_fetch"}:
        return ("git_fetch", getattr(value, "remote", None) or "default remote")
    if kind in {"git_pull", "check_git_pull", "git_push", "check_git_push"}:
        return (kind.replace("check_", ""),)
    if kind in {"git_commit", "check_git_commit"}:
        return ("git_commit", getattr(value, "message_text", getattr(value, "message", "")))
    if kind in {"git_switch", "check_git_switch"}:
        return ("git_switch", getattr(value, "branch", ""), getattr(value, "create", False))
    if kind in {"git_stash", "check_git_stash"}:
        return ("git_stash", git_stash_preview_message(value), getattr(value, "include_untracked", False))
    if kind in {"git_stash_apply", "check_git_stash_apply", "git_stash_drop", "check_git_stash_drop"}:
        return (kind.replace("check_", ""), getattr(value, "stash_ref", ""))
    return None


def run_preview_key(kind: str, value: object) -> tuple[Any, ...] | None:
    if kind in {"run_command", "command_check"}:
        return (
            "run_command",
            command_item_preview_key(value),
        )
    if kind in {"start_command", "check_start_command"}:
        return (
            "start_command",
            getattr(value, "command", ""),
            getattr(value, "cwd", None) or ".",
            getattr(value, "max_output_chars", None),
        )
    if kind in {"run_commands", "check_run_commands"}:
        commands = getattr(value, "commands", None)
        if commands is None:
            commands = getattr(value, "checks", [])
        return (
            "run_commands",
            tuple(command_item_preview_key(item) for item in commands),
            getattr(value, "stop_on_failure", True),
        )
    if kind in {"run_suggested_checks", "check_suggested_checks"}:
        return ("run_suggested_checks", getattr(value, "max_commands", None))
    if kind in {"run_focused_test_commands", "check_focused_test_commands"}:
        return (
            "run_focused_test_commands",
            focused_test_preview_paths(value),
            getattr(value, "max_paths", None),
            getattr(value, "max_candidates", None),
            getattr(value, "max_commands", None),
        )
    if kind in {"run_session_verification", "session_verification"}:
        return ("run_session_verification", getattr(value, "run_id", None))
    if kind in {"write_process", "check_write_process"}:
        content_sha256 = getattr(value, "content_sha256", "")
        content = getattr(value, "content", None)
        if not content_sha256 and isinstance(content, str):
            content_sha256 = hashlib.sha256(content.encode("utf-8")).hexdigest()
        return ("write_process", getattr(value, "process_id", ""), content_sha256)
    if kind in {"stop_process", "check_stop_process"}:
        return ("stop_process", getattr(value, "process_id", ""))
    if kind in {"stop_all_processes", "check_stop_all_processes"}:
        return ("stop_all_processes",)
    return None


def command_item_preview_key(value: object) -> tuple[Any, ...]:
    return (
        getattr(value, "command", ""),
        getattr(value, "cwd", None) or ".",
        getattr(value, "timeout_ms", None),
        getattr(value, "max_output_chars", None),
        getattr(value, "extract_output_contexts", False),
        getattr(value, "extract_output_diagnostics", False),
        getattr(value, "context_lines", 5),
        getattr(value, "max_diagnostics", 50),
        getattr(value, "max_contexts", 20),
        getattr(value, "max_bytes_per_context", 20_000),
    )


def git_stash_preview_message(value: object) -> str:
    message_text = getattr(value, "message_text", None)
    if isinstance(message_text, str) and message_text.strip():
        return message_text.strip()
    message = getattr(value, "message", None)
    if isinstance(message, str) and message.strip():
        return message.strip()
    return "vibeagent stash"


def focused_test_preview_paths(value: object) -> tuple[str, ...]:
    paths = getattr(value, "paths", None)
    if paths is not None:
        return tuple(paths)
    requested_paths = getattr(value, "requested_paths", None)
    if requested_paths is not None:
        return tuple(requested_paths)
    return tuple(getattr(value, "target_paths", None) or ())
