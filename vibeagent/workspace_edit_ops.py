from __future__ import annotations

import stat as stat_module
from pathlib import Path

from .workspace_core import RunWorkspace
from .workspace_file_path_ops import (
    build_delete_file,
    build_delete_files,
    copy_project_file,
    copy_project_files,
    delete_project_file,
    delete_project_files,
    move_project_file,
    move_project_files,
    prepare_project_file_copies,
    prepare_project_file_transfer,
    prepare_project_file_transfers,
    preview_copy_project_file,
    preview_copy_project_files,
    preview_delete_project_file,
    preview_delete_project_files,
    preview_move_project_file,
    preview_move_project_files,
)
from .workspace_json_edit_ops import (
    add_json_pointer_value,
    apply_json_patch_operation,
    build_json_patch,
    build_json_remove,
    build_json_set,
    format_json_document,
    json_patch_project_file,
    json_remove_project_file,
    json_set_project_file,
    parse_json_array_index,
    parse_json_pointer,
    preview_json_patch_project_file,
    preview_json_remove_project_file,
    preview_json_set_project_file,
    remove_json_pointer_value,
    set_json_pointer_value,
)
from .workspace_directory_ops import (
    copy_project_directories,
    copy_project_directory,
    create_project_directories,
    create_project_directory,
    delete_project_empty_directories,
    delete_project_empty_directory,
    move_project_directories,
    move_project_directory,
    prepare_project_directory_copy,
    prepare_project_directory_move,
    preview_copy_project_directories,
    preview_copy_project_directory,
    preview_create_project_directories,
    preview_create_project_directory,
    preview_delete_project_empty_directories,
    preview_delete_project_empty_directory,
    preview_move_project_directories,
    preview_move_project_directory,
    validate_project_directory_transfer_batch,
)
from .workspace_text_edit_ops import (
    append_project_file,
    build_append_file,
    build_edit_file,
    build_insert_lines,
    build_multi_edit,
    build_regex_replacement,
    build_replace_lines,
    build_write_file,
    edit_project_file,
    insert_project_file_lines,
    multi_edit_project_file,
    prepare_write_run_files,
    preview_append_project_file,
    preview_edit_project_file,
    preview_insert_project_file_lines,
    preview_multi_edit_project_file,
    preview_regex_replace_project_file,
    preview_replace_project_file_lines,
    preview_write_run_file,
    preview_write_run_files,
    regex_replace_project_file,
    replace_project_file_lines,
    write_run_file,
    write_run_files,
)
from .workspace_patch_ops import (
    apply_unified_patch,
    check_project_patch,
    check_project_patches,
    is_file_header_at,
    parse_unified_diff_path,
    parse_unified_patch_hunks,
    patch_project_file,
    patch_project_files,
    split_unified_patch_by_file,
)
from .workspace_resolve import resolve_mutation_path


def set_project_file_executable(workspace: RunWorkspace, relative_path: str, executable: bool = True) -> tuple[Path, int, int]:
    target, before, after = preview_set_project_file_executable(workspace, relative_path, executable=executable)
    if after != before:
        target.chmod(after)
    return target, before, after


def preview_set_project_file_executable(workspace: RunWorkspace, relative_path: str, executable: bool = True) -> tuple[Path, int, int]:
    target = resolve_mutation_path(workspace.root, relative_path)
    if not target.is_file():
        raise ValueError(f"File does not exist: {relative_path}")
    before = stat_module.S_IMODE(target.stat().st_mode)
    if executable:
        after = before | stat_module.S_IXUSR | stat_module.S_IXGRP | stat_module.S_IXOTH
    else:
        after = before & ~(stat_module.S_IXUSR | stat_module.S_IXGRP | stat_module.S_IXOTH)
    return target, before, after
