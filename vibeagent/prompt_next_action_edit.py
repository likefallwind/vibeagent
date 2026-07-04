from __future__ import annotations

from .types import Observation


EDIT_CHECK_NEXT_ACTION_KINDS = {
    "check_patch",
    "check_patches",
    "check_regex_replace",
    "check_write_file",
    "check_write_files",
    "check_edit_file",
    "check_multi_edit_file",
    "check_replace_python_definition",
    "check_replace_lines",
    "check_insert_lines",
    "check_append_file",
    "check_json_set",
    "check_json_remove",
    "check_json_patch",
    "check_delete_file",
    "check_delete_files",
    "check_move_file",
    "check_move_files",
    "check_copy_file",
    "check_copy_files",
    "check_move_dir",
    "check_move_dirs",
    "check_copy_dir",
    "check_copy_dirs",
    "check_create_dir",
    "check_create_dirs",
    "check_delete_empty_dir",
    "check_delete_empty_dirs",
    "check_set_executable",
}

EDIT_APPLY_NEXT_ACTION_KINDS = {
    "write_file",
    "write_files",
    "edit_file",
    "multi_edit_file",
    "replace_python_definition",
    "code_rename",
    "python_rename",
    "regex_replace",
    "json_set",
    "json_remove",
    "json_patch",
    "replace_lines",
    "insert_lines",
    "append_file",
    "patch_file",
    "patch_files",
    "delete_file",
    "delete_files",
    "move_file",
    "move_files",
    "copy_file",
    "copy_files",
    "move_dir",
    "move_dirs",
    "copy_dir",
    "copy_dirs",
    "create_dir",
    "create_dirs",
    "delete_empty_dir",
    "delete_empty_dirs",
    "set_executable",
}

EDIT_NEXT_ACTION_KINDS = EDIT_CHECK_NEXT_ACTION_KINDS | EDIT_APPLY_NEXT_ACTION_KINDS


_CHECK_TO_APPLY_TOOL = {
    "check_patch": "patch_file",
    "check_patches": "patch_files",
    "check_write_file": "write_file",
    "check_write_files": "write_files",
    "check_edit_file": "edit_file",
    "check_multi_edit_file": "multi_edit_file",
    "check_replace_python_definition": "replace_python_definition",
    "check_replace_lines": "replace_lines",
    "check_insert_lines": "insert_lines",
    "check_append_file": "append_file",
    "check_regex_replace": "regex_replace",
    "check_json_set": "json_set",
    "check_json_remove": "json_remove",
    "check_json_patch": "json_patch",
    "check_delete_file": "delete_file",
    "check_delete_files": "delete_files",
    "check_move_file": "move_file",
    "check_move_files": "move_files",
    "check_copy_file": "copy_file",
    "check_copy_files": "copy_files",
    "check_move_dir": "move_dir",
    "check_move_dirs": "move_dirs",
    "check_copy_dir": "copy_dir",
    "check_copy_dirs": "copy_dirs",
    "check_create_dir": "create_dir",
    "check_create_dirs": "create_dirs",
    "check_delete_empty_dir": "delete_empty_dir",
    "check_delete_empty_dirs": "delete_empty_dirs",
    "check_set_executable": "set_executable",
}


def _format_next_action_items(items: list[str], max_items: int = 3) -> str:
    shown = items[:max_items]
    suffix = "" if len(items) <= max_items else f"; +{len(items) - max_items} more"
    return "; ".join(shown) + suffix


def _string_items(values: object) -> list[str]:
    if not isinstance(values, list):
        return []
    return [str(value).strip() for value in values if str(value).strip()]


def _result_path_items(values: object) -> list[str]:
    if not isinstance(values, list):
        return []
    items: list[str] = []
    for value in values:
        path = str(getattr(value, "path", "") or "").strip()
        ok = getattr(value, "ok", True)
        if path and not ok:
            items.append(f"{path} (failed)")
        elif path:
            items.append(path)
    return items


def _transfer_items(values: object) -> list[str]:
    if not isinstance(values, list):
        return []
    items: list[str] = []
    for value in values:
        source = str(getattr(value, "source", "") or "").strip()
        destination = str(getattr(value, "destination", "") or "").strip()
        if source and destination:
            items.append(f"{source} -> {destination}")
        elif source:
            items.append(source)
        elif destination:
            items.append(destination)
    return items


def _edit_target_label(latest: Observation) -> str:
    path = str(getattr(latest, "path", "") or "").strip()
    if path:
        return path

    definition_path = str(getattr(latest, "definition_path", "") or "").strip()
    if definition_path:
        return definition_path

    file_results = _result_path_items(getattr(latest, "files", []))
    if file_results:
        return _format_next_action_items(file_results)

    files = _string_items(getattr(latest, "files", []))
    if files:
        return _format_next_action_items(files)

    paths = _string_items(getattr(latest, "paths", []))
    if paths:
        return _format_next_action_items(paths)

    transfers = _transfer_items(getattr(latest, "transfers", []))
    if transfers:
        return _format_next_action_items(transfers)

    source = str(getattr(latest, "source", "") or "").strip()
    destination = str(getattr(latest, "destination", "") or "").strip()
    if source and destination:
        return f"{source} -> {destination}"
    if source:
        return source
    if destination:
        return destination

    return "the selected path(s)"


def _edit_check_next_action_instruction(base: str, latest: Observation) -> str:
    target = _edit_target_label(latest)
    apply_tool = _CHECK_TO_APPLY_TOOL.get(latest.kind, latest.kind.removeprefix("check_"))
    if getattr(latest, "ok", False):
        return (
            f"{base} File change dry-run succeeded for {target}. Review the preview diff or validation result; "
            f"apply {apply_tool} only if it matches the request, otherwise inspect the source context and adjust the edit."
        )
    return (
        f"{base} File change dry-run failed for {target}. Inspect its message, read targeted source context if needed, "
        "and fix the edit parameters before applying any file change."
    )


def _edit_apply_next_action_instruction(base: str, latest: Observation) -> str:
    target = _edit_target_label(latest)
    if not getattr(latest, "ok", False):
        return (
            f"{base} File change failed for {target}. Inspect its message and source context, "
            "then choose a corrected edit before continuing."
        )
    return (
        f"{base} File change applied for {target}. Inspect the resulting worktree with git_diff or review_changes, "
        "use related_tests or focused_test_commands for changed code paths, run relevant verification, "
        "then use final_review before finishing."
    )


def edit_next_action_instruction(base: str, latest: Observation) -> str:
    if latest.kind in EDIT_CHECK_NEXT_ACTION_KINDS:
        return _edit_check_next_action_instruction(base, latest)
    if latest.kind in EDIT_APPLY_NEXT_ACTION_KINDS:
        return _edit_apply_next_action_instruction(base, latest)

    raise ValueError(f"Unsupported edit next-action kind: {latest.kind}")
