from __future__ import annotations

from pathlib import Path
from typing import Any

from .redaction import redact_sensitive_text


def is_local_session_id(run_id: str) -> bool:
    return run_id.startswith("local-")


def sessions_dir(project_root: str | Path) -> Path:
    return Path(project_root).resolve() / ".vibeagent" / "sessions"


def session_store_safety_error(project_root: str | Path) -> str | None:
    project = Path(project_root).resolve()
    runtime = project / ".vibeagent"
    sessions = runtime / "sessions"
    if runtime.is_symlink() or (runtime.exists() and not runtime.is_dir()):
        return "Session runtime path is not a regular directory: .vibeagent"
    if sessions.is_symlink() or (sessions.exists() and not sessions.is_dir()):
        return "Session root path is not a regular directory: .vibeagent/sessions"
    return None


def session_dir(project_root: str | Path, run_id: str) -> Path:
    if not run_id or Path(run_id).name != run_id:
        raise ValueError(f"Invalid session id: {run_id}")
    store_error = session_store_safety_error(project_root)
    if store_error:
        raise ValueError(store_error)
    path = sessions_dir(project_root) / run_id
    if path.is_symlink() or (path.exists() and not path.is_dir()):
        raise ValueError(f"Session path is not a regular directory: .vibeagent/sessions/{run_id}")
    return path


def events_path(project_root: str | Path, run_id: str) -> Path:
    path = session_dir(project_root, run_id) / "events.jsonl"
    event_error = session_events_safety_error(path)
    if event_error:
        raise ValueError(f"Session events path is not a regular file: .vibeagent/sessions/{run_id}/events.jsonl")
    return path


def session_events_safety_error(path: Path) -> str | None:
    if path.is_symlink() or (path.exists() and not path.is_file()):
        return "Session events path is not a regular file"
    return None


def as_int(value: Any) -> int | None:
    return value if isinstance(value, int) else None


def as_nonnegative_int(value: Any) -> int:
    return value if isinstance(value, int) and value >= 0 else 0


def parse_usage_payload(value: Any) -> dict[str, int]:
    if not isinstance(value, dict):
        return {
            "input_tokens": 0,
            "output_tokens": 0,
            "total_tokens": 0,
            "cache_creation_tokens": 0,
            "cache_read_tokens": 0,
        }
    input_tokens = as_nonnegative_int(value.get("input_tokens"))
    output_tokens = as_nonnegative_int(value.get("output_tokens"))
    total_tokens = as_nonnegative_int(value.get("total_tokens"))
    if total_tokens == 0 and (input_tokens or output_tokens):
        total_tokens = input_tokens + output_tokens
    return {
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "total_tokens": total_tokens,
        "cache_creation_tokens": as_nonnegative_int(value.get("cache_creation_tokens")),
        "cache_read_tokens": as_nonnegative_int(value.get("cache_read_tokens")),
    }


def model_text(content: Any) -> str:
    if isinstance(content, str):
        return content.strip()
    if not isinstance(content, list):
        return ""
    return "".join(
        block["text"]
        for block in content
        if isinstance(block, dict) and block.get("type") == "text" and isinstance(block.get("text"), str)
    ).strip()


def has_tool_call_content(content: Any) -> bool:
    return isinstance(content, list) and any(
        isinstance(block, dict) and block.get("type") == "tool_call" for block in content
    )


def is_failed_tool_result(result: dict[str, Any]) -> bool:
    kind = result.get("kind")
    if kind in {"tool_error", "approval_denied"}:
        return True
    if kind in {
        "check_write_file",
        "write_file",
        "check_write_files",
        "write_files",
        "check_edit_file",
        "edit_file",
        "check_multi_edit_file",
        "multi_edit_file",
        "check_replace_python_definition",
        "replace_python_definition",
        "python_rename",
        "check_replace_lines",
        "replace_lines",
        "check_insert_lines",
        "insert_lines",
        "check_append_file",
        "append_file",
        "regex_replace",
        "check_regex_replace",
        "check_json_set",
        "json_set",
        "check_json_remove",
        "json_remove",
        "check_json_patch",
        "json_patch",
        "check_patch",
        "check_patches",
        "patch_file",
        "patch_files",
        "check_delete_file",
        "delete_file",
        "check_delete_files",
        "delete_files",
        "check_move_file",
        "move_file",
        "check_move_files",
        "move_files",
        "check_copy_file",
        "copy_file",
        "check_copy_files",
        "copy_files",
        "check_move_dir",
        "move_dir",
        "check_move_dirs",
        "move_dirs",
        "check_copy_dir",
        "copy_dir",
        "check_copy_dirs",
        "copy_dirs",
        "check_create_dir",
        "create_dir",
        "check_create_dirs",
        "create_dirs",
        "check_delete_empty_dir",
        "delete_empty_dir",
        "check_delete_empty_dirs",
        "delete_empty_dirs",
        "check_set_executable",
        "set_executable",
        "check_git_stage",
        "git_stage",
        "check_git_unstage",
        "git_unstage",
        "check_git_commit",
        "git_commit",
    }:
        return result.get("ok") is False
    if kind == "read_files":
        files = result.get("files")
        return isinstance(files, list) and any(isinstance(file, dict) and file.get("ok") is False for file in files)
    if kind == "read_file_context":
        return result.get("ok") is False
    if kind == "read_file_contexts":
        contexts = result.get("contexts")
        return isinstance(contexts, list) and any(isinstance(item, dict) and item.get("ok") is False for item in contexts)
    if kind == "output_contexts":
        contexts = result.get("contexts")
        return isinstance(contexts, list) and any(isinstance(item, dict) and item.get("ok") is False for item in contexts)
    if kind == "read_file_ranges":
        ranges = result.get("ranges")
        return isinstance(ranges, list) and any(isinstance(item, dict) and item.get("ok") is False for item in ranges)
    if kind == "file_info":
        files = result.get("files")
        return isinstance(files, list) and any(isinstance(file, dict) and file.get("ok") is False for file in files)
    if kind == "image_info":
        images = result.get("images")
        return isinstance(images, list) and any(isinstance(image, dict) and image.get("ok") is False for image in images)
    if kind == "view_image":
        return result.get("ok") is False
    if kind == "repo_map":
        return result.get("ok") is False
    if kind == "python_symbols":
        files = result.get("files")
        return isinstance(files, list) and any(isinstance(file, dict) and file.get("ok") is False for file in files)
    if kind == "code_outline":
        files = result.get("files")
        return isinstance(files, list) and any(isinstance(file, dict) and file.get("ok") is False for file in files)
    if kind == "python_check":
        return result.get("ok") is False
    if kind == "config_check":
        return result.get("ok") is False
    if kind == "python_dependencies":
        return result.get("ok") is False
    if kind == "code_dependencies":
        return result.get("ok") is False
    if kind == "code_references":
        return result.get("ok") is False
    if kind == "code_reference_contexts":
        return result.get("ok") is False
    if kind == "code_definitions":
        return result.get("ok") is False
    if kind == "code_rename_preview":
        return result.get("ok") is False
    if kind == "code_rename":
        return result.get("ok") is False
    if kind == "python_definitions":
        return result.get("ok") is False
    if kind == "python_calls":
        return result.get("ok") is False
    if kind == "python_call_graph":
        return result.get("ok") is False
    if kind == "python_references":
        return result.get("ok") is False
    if kind == "python_reference_contexts":
        return result.get("ok") is False
    if kind == "python_rename_preview":
        return result.get("ok") is False
    if kind in {
        "git_info",
        "git_status",
        "git_conflicts",
        "git_changes",
        "git_branches",
        "check_git_fetch",
        "git_fetch",
        "check_git_pull",
        "git_pull",
        "check_git_push",
        "git_push",
        "check_git_restore",
        "git_restore",
        "git_stashes",
        "check_git_stash",
        "git_stash",
        "check_git_stash_apply",
        "git_stash_apply",
        "check_git_stash_drop",
        "git_stash_drop",
        "check_git_switch",
        "git_switch",
        "review_changes",
        "final_review",
        "suggest_checks",
        "project_commands",
        "related_tests",
        "focused_test_commands",
        "check_focused_test_commands",
        "run_focused_test_commands",
        "project_manifests",
        "project_skills",
        "skill",
        "mcp_servers",
        "mcp_tools",
        "mcp_call",
        "project_overview",
        "command_check",
        "check_run_commands",
        "check_start_command",
        "port_check",
        "http_check",
        "http_fetch",
        "web_fetch",
        "check_write_process",
        "write_process",
        "check_stop_all_processes",
        "check_stop_process",
        "environment_info",
        "git_diff",
        "git_diff_hunks",
        "git_diff_contexts",
        "git_log",
        "git_show",
        "git_blame",
    }:
        return result.get("ok") is False
    if kind in {
        "session_summary",
        "session_plan",
        "session_transcript",
        "session_search",
        "session_commands",
        "session_output_contexts",
        "session_output_diagnostics",
        "session_files",
        "session_failures",
        "session_handoff",
    }:
        return result.get("ok") is False
    if kind in {
        "checkpoint_create",
        "checkpoint_list",
        "checkpoint_show",
        "checkpoint_diff",
        "checkpoint_status",
        "check_checkpoint_restore",
        "checkpoint_restore",
        "check_checkpoint_delete",
        "checkpoint_delete",
        "check_checkpoint_prune",
        "checkpoint_prune",
    }:
        return result.get("ok") is False
    if kind == "search":
        return result.get("ok") is False
    if kind == "glob":
        return result.get("ok") is False
    if kind == "list_tree":
        return result.get("ok") is False
    if kind in {
        "start_command",
        "read_process",
        "wait_process",
        "check_stop_all_processes",
        "check_stop_process",
        "stop_all_processes",
        "stop_process",
    }:
        return result.get("ok") is False
    if kind == "run_command":
        command_result = result.get("result")
        if not isinstance(command_result, dict):
            return True
        return command_result.get("exit_code") != 0 or command_result.get("timed_out") is True
    if kind in {"run_commands", "run_suggested_checks"}:
        return result.get("ok") is False
    return False


def count_names(values: list[str]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for value in values:
        counts[value] = counts.get(value, 0) + 1
    return counts


def compact(value: str, max_length: int) -> str:
    collapsed = " ".join(redact_sensitive_text(value).split())
    if len(collapsed) <= max_length:
        return collapsed
    return f"{collapsed[:max_length]}..."
