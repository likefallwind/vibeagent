from __future__ import annotations

from .agent_preview_paths import paths_overlap_or_nested
from .agent_approval_preview_stale import (
    FILE_MUTATION_OBSERVATION_KINDS,
    FILE_PREVIEW_KINDS,
    checkpoint_restore_preview_invalidated_by_workspace_mutation,
    command_preview_invalidated_by_workspace_mutation,
    file_preview_invalidated_by_broad_workspace_mutation,
    git_preview_invalidated_by_workspace_mutation,
    preview_invalidated_by_workspace_restore,
    process_preview_invalidated_by_process_state,
)


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
