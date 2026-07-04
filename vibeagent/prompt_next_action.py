from __future__ import annotations

from .prompt_next_action_checkpoint import CHECKPOINT_NEXT_ACTION_KINDS, checkpoint_next_action_instruction
from .prompt_next_action_completion import COMPLETION_NEXT_ACTION_KINDS, completion_next_action_instruction
from .prompt_next_action_edit import EDIT_NEXT_ACTION_KINDS, edit_next_action_instruction
from .prompt_next_action_error import ERROR_NEXT_ACTION_KINDS, error_next_action_instruction
from .prompt_next_action_git import GIT_NEXT_ACTION_KINDS, git_next_action_instruction
from .prompt_next_action_project import PROJECT_NEXT_ACTION_KINDS, project_next_action_instruction
from .prompt_next_action_runtime import runtime_next_action_instruction
from .prompt_next_action_session import SESSION_NEXT_ACTION_KINDS, session_next_action_instruction
from .types import Observation


def get_next_action_instruction(task: str, observations: list[Observation]) -> str:
    base = "Choose the next response: call a tool if needed, or answer directly if the task is complete."
    if not observations:
        return base

    latest = observations[-1]
    runtime_instruction = runtime_next_action_instruction(base, observations)
    if runtime_instruction is not None:
        return runtime_instruction

    if latest.kind in ERROR_NEXT_ACTION_KINDS:
        return error_next_action_instruction(base, latest)

    if latest.kind in COMPLETION_NEXT_ACTION_KINDS:
        return completion_next_action_instruction(base, latest)

    if latest.kind in SESSION_NEXT_ACTION_KINDS:
        return session_next_action_instruction(base, latest)

    if latest.kind in CHECKPOINT_NEXT_ACTION_KINDS:
        return checkpoint_next_action_instruction(base, latest)

    if latest.kind in PROJECT_NEXT_ACTION_KINDS:
        return project_next_action_instruction(base, latest)

    if latest.kind in GIT_NEXT_ACTION_KINDS:
        return git_next_action_instruction(base, latest)

    if latest.kind in EDIT_NEXT_ACTION_KINDS:
        return edit_next_action_instruction(base, latest)

    if latest.kind in {
        "read_file",
        "read_file_context",
        "read_file_contexts",
        "python_traceback",
        "tail_file",
        "read_files",
        "read_file_ranges",
        "file_info",
        "image_info",
        "repo_map",
        "python_symbols",
        "code_outline",
        "python_dependencies",
        "code_dependencies",
        "code_references",
        "code_reference_contexts",
        "code_definitions",
        "code_rename_preview",
        "python_definitions",
        "python_calls",
        "python_call_graph",
        "python_references",
        "python_reference_contexts",
        "python_rename_preview",
        "project_commands",
        "related_tests",
        "focused_test_commands",
        "git_branches",
        "check_git_fetch",
        "check_git_pull",
        "check_git_push",
        "check_git_restore",
        "git_conflicts",
        "git_stashes",
        "check_git_stash_apply",
        "check_git_stash_drop",
        "check_git_switch",
        "port_check",
        "http_check",
        "http_fetch",
        "list_files",
        "search",
        "search_contexts",
        "list_tree",
        "glob",
    }:
        return (
            f"{base} Do not repeat inspection unless you need specific missing information. "
            "If you already created the requested files, run one appropriate check or answer directly if the task is complete."
        )

    if latest.kind in {
        "git_info",
        "git_conflicts",
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
        "port_check",
        "http_check",
        "http_fetch",
        "git_log",
        "git_show",
        "git_blame",
        "session_summary",
        "session_plan",
        "session_transcript",
        "session_search",
        "session_commands",
        "session_output_contexts",
        "session_files",
        "session_failures",
        "session_verification",
        "run_session_verification",
        "session_audit",
        "session_handoff",
    }:
        return f"{base} Use the repository or session information to decide whether to continue, run a check, or answer directly."

    if latest.kind in {"git_fetch", "git_pull", "git_push", "git_restore", "git_stash", "git_stash_apply", "git_stash_drop", "git_switch"}:
        return f"{base} Continue with the next required file, run one appropriate check, or answer directly if the task is complete."

    return f"{base} If the task is complete, answer directly or use finish."
