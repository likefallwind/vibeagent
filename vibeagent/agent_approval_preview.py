from __future__ import annotations

from dataclasses import replace

from .agent_preview_paths import (
    paths_overlap_or_nested,
)
from .agent_approval_preview_keys import approval_preview_key
from .agent_approval_preview_stale import (
    CHECKPOINT_RESTORE_MUTATION_OBSERVATION_KINDS,
    CHECKPOINT_RESTORE_PREVIEW_KINDS,
    COMMAND_MUTATION_OBSERVATION_KINDS,
    COMMAND_PREVIEW_KINDS,
    FILE_MUTATION_OBSERVATION_KINDS,
    FILE_PREVIEW_KINDS,
    GIT_MUTATION_OBSERVATION_KINDS,
    GIT_PREVIEW_KINDS,
    PROCESS_PREVIEW_KINDS,
    PROCESS_STATE_OBSERVATION_KINDS,
    WORKSPACE_MUTATION_OBSERVATION_KINDS,
    WORKSPACE_PREVIEW_KINDS,
    checkpoint_restore_preview_invalidated_by_workspace_mutation,
    command_preview_invalidated_by_workspace_mutation,
    file_preview_invalidated_by_broad_workspace_mutation,
    git_preview_invalidated_by_workspace_mutation,
    preview_invalidated_by_workspace_restore,
    process_preview_invalidated_by_process_state,
)
from .agent_approval_preview_summary import (
    command_check_fingerprint_payload,
    file_diff_fingerprint_payload,
    preview_digest,
    preview_file_diffs,
    summarize_preview_observation,
)
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
    expected_paths = approval_preview_paths(action)
    for observation in reversed(observations):
        observation_kind = getattr(observation, "kind", None)
        if observation_kind == expected_kind:
            if getattr(observation, "ok", True) is not True:
                continue
            if approval_preview_key(observation) != expected_key:
                continue
            return summarize_preview_observation(observation)
        if preview_search_invalidated(expected_kind, observation_kind, expected_paths, observation):
            return None
        if observation_kind != expected_kind:
            continue
    return None


def preview_search_invalidated(
    expected_kind: str,
    observation_kind: object,
    expected_paths: frozenset[str] | None,
    observation: object,
) -> bool:
    if preview_invalidated_by_workspace_restore(expected_kind, observation_kind):
        return True
    if checkpoint_restore_preview_invalidated_by_workspace_mutation(expected_kind, observation_kind):
        return True
    if command_preview_invalidated_by_workspace_mutation(expected_kind, observation_kind):
        return True
    if process_preview_invalidated_by_process_state(expected_kind, observation_kind):
        return True
    if git_preview_invalidated_by_workspace_mutation(expected_kind, observation_kind):
        return True
    if file_preview_invalidated_by_broad_workspace_mutation(expected_kind, observation_kind):
        return True
    return file_preview_invalidated_by_file_mutation(expected_kind, observation_kind, expected_paths, observation)


def file_preview_invalidated_by_file_mutation(
    expected_kind: str,
    observation_kind: object,
    expected_paths: frozenset[str] | None,
    observation: object,
) -> bool:
    if expected_kind not in FILE_PREVIEW_KINDS or observation_kind not in FILE_MUTATION_OBSERVATION_KINDS:
        return False
    if expected_paths is None:
        return True
    changed_paths = observation_paths(observation)
    return paths_overlap_or_nested(changed_paths, expected_paths)


def approval_preview_paths(value: object) -> frozenset[str] | None:
    kind = str(getattr(value, "kind", getattr(value, "type", "")))
    if kind in {"patch_files", "check_patches"}:
        return None
    paths = observation_paths(value)
    return paths if paths else None


def observation_paths(value: object) -> frozenset[str]:
    paths: set[str] = set()
    path = getattr(value, "path", None)
    if isinstance(path, str) and path:
        paths.add(path)
    definition_path = getattr(value, "definition_path", None)
    if isinstance(definition_path, str) and definition_path:
        paths.add(definition_path)
    for attr in ("paths", "files"):
        for item in getattr(value, attr, []) or []:
            if isinstance(item, str) and item:
                paths.add(item)
            else:
                item_path = getattr(item, "path", None)
                if isinstance(item_path, str) and item_path:
                    paths.add(item_path)
    for attr in ("inputs",):
        for item in getattr(value, attr, []) or []:
            item_path = getattr(item, "path", None)
            if isinstance(item_path, str) and item_path:
                paths.add(item_path)
    for attr in ("source", "destination"):
        value_path = getattr(value, attr, None)
        if isinstance(value_path, str) and value_path:
            paths.add(value_path)
    for transfer in getattr(value, "transfers", []) or []:
        for attr in ("source", "destination"):
            transfer_path = getattr(transfer, attr, None)
            if isinstance(transfer_path, str) and transfer_path:
                paths.add(transfer_path)
    return frozenset(paths)
