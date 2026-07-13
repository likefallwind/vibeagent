from __future__ import annotations

from typing import Any

from .action_parsing_helpers import (
    ActionParseError,
    parse_directory_transfers,
    parse_edit_operations,
    parse_move_file_transfers,
    parse_optional_nonnegative_int,
    parse_optional_positive_int,
    parse_path_list,
    parse_write_file_items,
)
from .types import (
    AppendFileAction,
    CheckAppendFileAction,
    CheckCopyFileAction,
    CheckCopyFilesAction,
    CheckCopyDirectoryAction,
    CheckCopyDirectoriesAction,
    CheckCreateDirectoryAction,
    CheckCreateDirectoriesAction,
    CheckDeleteFileAction,
    CheckDeleteFilesAction,
    CheckDeleteEmptyDirectoryAction,
    CheckDeleteEmptyDirectoriesAction,
    CheckEditFileAction,
    CheckInsertLinesAction,
    CheckMoveFileAction,
    CheckMoveFilesAction,
    CheckMoveDirectoryAction,
    CheckMoveDirectoriesAction,
    CheckMultiEditAction,
    CheckPatchAction,
    CheckPatchesAction,
    CheckRegexReplaceAction,
    CheckReplaceLinesAction,
    CheckSetExecutableAction,
    CheckWriteFileAction,
    CheckWriteFilesAction,
    CopyFileAction,
    CopyFilesAction,
    CopyDirectoryAction,
    CopyDirectoriesAction,
    CreateDirectoryAction,
    CreateDirectoriesAction,
    DeleteFileAction,
    DeleteFilesAction,
    DeleteEmptyDirectoryAction,
    DeleteEmptyDirectoriesAction,
    EditFileAction,
    InsertLinesAction,
    MoveFileAction,
    MoveFilesAction,
    MoveDirectoryAction,
    MoveDirectoriesAction,
    MultiEditAction,
    NotebookEditAction,
    PatchFileAction,
    PatchFilesAction,
    RegexReplaceAction,
    ReplaceLinesAction,
    SetExecutableAction,
    WriteFileAction,
    WriteFilesAction,
)


FILE_EDIT_ACTION_TYPES = {
    "check_edit_file",
    "edit_file",
    "notebook_edit",
    "check_multi_edit_file",
    "multi_edit_file",
    "check_replace_lines",
    "replace_lines",
    "check_insert_lines",
    "insert_lines",
    "check_append_file",
    "append_file",
    "check_regex_replace",
    "regex_replace",
    "check_patch",
    "check_patches",
    "patch_file",
    "patch_files",
    "check_write_file",
    "write_file",
    "check_write_files",
    "write_files",
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
}


def _parse_string_field(value: Any, raw: str, message: str) -> str:
    if not isinstance(value, str):
        raise ActionParseError(message, raw)
    return value


def _parse_line_range(value: dict[str, Any], raw: str, action_type: str) -> tuple[str, int, int, str]:
    path = _parse_string_field(value.get("path"), raw, f"{action_type} action requires a string path.")
    start_line = parse_optional_positive_int(value.get("start_line"), "start_line", raw, maximum=None)
    end_line = parse_optional_positive_int(value.get("end_line"), "end_line", raw, maximum=None)
    if start_line is None:
        raise ActionParseError(f"{action_type} action requires start_line.", raw)
    if end_line is None:
        raise ActionParseError(f"{action_type} action requires end_line.", raw)
    if end_line < start_line:
        raise ActionParseError("end_line must be greater than or equal to start_line.", raw)
    content = _parse_string_field(value.get("content"), raw, f"{action_type} action requires string content.")
    return path, start_line, end_line, content


def _parse_insert(value: dict[str, Any], raw: str, action_type: str) -> tuple[str, int, str]:
    path = _parse_string_field(value.get("path"), raw, f"{action_type} action requires a string path.")
    line = parse_optional_positive_int(value.get("line"), "line", raw, maximum=None)
    if line is None:
        raise ActionParseError(f"{action_type} action requires line.", raw)
    content = value.get("content")
    if not isinstance(content, str) or content == "":
        raise ActionParseError(f"{action_type} action requires non-empty string content.", raw)
    return path, line, content


def _parse_regex_replace(value: dict[str, Any], raw: str, action_type: str) -> tuple[str, str, str, int, bool, bool, int]:
    path = _parse_string_field(value.get("path"), raw, f"{action_type} action requires a string path.")
    pattern = value.get("pattern")
    replacement = value.get("replacement")
    if not isinstance(pattern, str) or pattern == "":
        raise ActionParseError(f"{action_type} action requires a non-empty string pattern.", raw)
    if not isinstance(replacement, str):
        raise ActionParseError(f"{action_type} action requires string replacement.", raw)
    count = parse_optional_nonnegative_int(value.get("count", 0), "count", raw, maximum=1000)
    max_replacements = parse_optional_positive_int(value.get("max_replacements", 100), "max_replacements", raw, maximum=1000)
    case_sensitive = value.get("case_sensitive", True)
    multiline = value.get("multiline", False)
    if type(case_sensitive) is not bool:
        raise ActionParseError(f"{action_type} action case_sensitive must be a boolean.", raw)
    if type(multiline) is not bool:
        raise ActionParseError(f"{action_type} action multiline must be a boolean.", raw)
    return (
        path,
        pattern,
        replacement,
        count if count is not None else 0,
        case_sensitive,
        multiline,
        max_replacements if max_replacements is not None else 100,
    )


def _parse_transfer(value: dict[str, Any], raw: str, action_type: str) -> tuple[str, str]:
    source = _parse_string_field(value.get("source"), raw, f"{action_type} action requires string source.")
    destination = _parse_string_field(value.get("destination"), raw, f"{action_type} action requires string destination.")
    return source, destination


def parse_file_edit_action(action_type: object, value: dict[str, Any], raw: str) -> object | None:
    if action_type not in FILE_EDIT_ACTION_TYPES:
        return None

    if action_type == "check_edit_file":
        path = _parse_string_field(value.get("path"), raw, "check_edit_file action requires a string path.")
        old = _parse_string_field(value.get("old"), raw, "check_edit_file action requires string old.")
        new = _parse_string_field(value.get("new"), raw, "check_edit_file action requires string new.")
        return CheckEditFileAction(type="check_edit_file", path=path, old=old, new=new)

    if action_type == "edit_file":
        path = _parse_string_field(value.get("path"), raw, "edit_file action requires a string path.")
        old = _parse_string_field(value.get("old"), raw, "edit_file action requires string old.")
        new = _parse_string_field(value.get("new"), raw, "edit_file action requires string new.")
        return EditFileAction(type="edit_file", path=path, old=old, new=new)

    if action_type == "notebook_edit":
        path = _parse_string_field(value.get("path"), raw, "notebook_edit action requires a string path.")
        new_source = _parse_string_field(value.get("new_source"), raw, "notebook_edit action requires string new_source.")
        cell_id = value.get("cell_id")
        cell_number = value.get("cell_number")
        cell_type = value.get("cell_type")
        if cell_id is not None and not isinstance(cell_id, str):
            raise ActionParseError("notebook_edit action cell_id must be a string when provided.", raw)
        parsed_cell_number = parse_optional_positive_int(cell_number, "cell_number", raw, maximum=1_000_000)
        if cell_id is None and parsed_cell_number is None:
            raise ActionParseError("notebook_edit action requires cell_id or cell_number.", raw)
        if cell_type is not None and not isinstance(cell_type, str):
            raise ActionParseError("notebook_edit action cell_type must be a string when provided.", raw)
        return NotebookEditAction(
            type="notebook_edit",
            path=path,
            new_source=new_source,
            cell_id=cell_id,
            cell_number=parsed_cell_number,
            cell_type=cell_type,
        )

    if action_type == "check_multi_edit_file":
        path = _parse_string_field(value.get("path"), raw, "check_multi_edit_file action requires a string path.")
        return CheckMultiEditAction(
            type="check_multi_edit_file",
            path=path,
            edits=parse_edit_operations(value.get("edits"), raw, action_type="check_multi_edit_file"),
        )

    if action_type == "multi_edit_file":
        path = _parse_string_field(value.get("path"), raw, "multi_edit_file action requires a string path.")
        return MultiEditAction(type="multi_edit_file", path=path, edits=parse_edit_operations(value.get("edits"), raw))

    if action_type == "check_replace_lines":
        path, start_line, end_line, content = _parse_line_range(value, raw, "check_replace_lines")
        return CheckReplaceLinesAction(
            type="check_replace_lines",
            path=path,
            start_line=start_line,
            end_line=end_line,
            content=content,
        )

    if action_type == "replace_lines":
        path, start_line, end_line, content = _parse_line_range(value, raw, "replace_lines")
        return ReplaceLinesAction(
            type="replace_lines",
            path=path,
            start_line=start_line,
            end_line=end_line,
            content=content,
        )

    if action_type == "check_insert_lines":
        path, line, content = _parse_insert(value, raw, "check_insert_lines")
        return CheckInsertLinesAction(type="check_insert_lines", path=path, line=line, content=content)

    if action_type == "insert_lines":
        path, line, content = _parse_insert(value, raw, "insert_lines")
        return InsertLinesAction(type="insert_lines", path=path, line=line, content=content)

    if action_type == "check_append_file":
        path = _parse_string_field(value.get("path"), raw, "check_append_file action requires a string path.")
        content = value.get("content")
        if not isinstance(content, str) or content == "":
            raise ActionParseError("check_append_file action requires non-empty string content.", raw)
        return CheckAppendFileAction(type="check_append_file", path=path, content=content)

    if action_type == "append_file":
        path = _parse_string_field(value.get("path"), raw, "append_file action requires a string path.")
        content = value.get("content")
        if not isinstance(content, str) or content == "":
            raise ActionParseError("append_file action requires non-empty string content.", raw)
        return AppendFileAction(type="append_file", path=path, content=content)

    if action_type == "check_regex_replace":
        path, pattern, replacement, count, case_sensitive, multiline, max_replacements = _parse_regex_replace(
            value,
            raw,
            "check_regex_replace",
        )
        return CheckRegexReplaceAction(
            type="check_regex_replace",
            path=path,
            pattern=pattern,
            replacement=replacement,
            count=count,
            case_sensitive=case_sensitive,
            multiline=multiline,
            max_replacements=max_replacements,
        )

    if action_type == "regex_replace":
        path, pattern, replacement, count, case_sensitive, multiline, max_replacements = _parse_regex_replace(
            value,
            raw,
            "regex_replace",
        )
        return RegexReplaceAction(
            type="regex_replace",
            path=path,
            pattern=pattern,
            replacement=replacement,
            count=count,
            case_sensitive=case_sensitive,
            multiline=multiline,
            max_replacements=max_replacements,
        )

    if action_type == "check_patch":
        path = _parse_string_field(value.get("path"), raw, "check_patch action requires a string path.")
        patch = _parse_string_field(value.get("patch"), raw, "check_patch action requires string patch.")
        return CheckPatchAction(type="check_patch", path=path, patch=patch)

    if action_type == "check_patches":
        patch = _parse_string_field(value.get("patch"), raw, "check_patches action requires string patch.")
        return CheckPatchesAction(type="check_patches", patch=patch)

    if action_type == "patch_file":
        path = _parse_string_field(value.get("path"), raw, "patch_file action requires a string path.")
        patch = _parse_string_field(value.get("patch"), raw, "patch_file action requires string patch.")
        return PatchFileAction(type="patch_file", path=path, patch=patch)

    if action_type == "patch_files":
        patch = _parse_string_field(value.get("patch"), raw, "patch_files action requires string patch.")
        return PatchFilesAction(type="patch_files", patch=patch)

    if action_type == "check_write_file":
        path = _parse_string_field(value.get("path"), raw, "check_write_file action requires a string path.")
        content = _parse_string_field(value.get("content"), raw, "check_write_file action requires string content.")
        return CheckWriteFileAction(type="check_write_file", path=path, content=content)

    if action_type == "write_file":
        path = _parse_string_field(value.get("path"), raw, "write_file action requires a string path.")
        content = _parse_string_field(value.get("content"), raw, "write_file action requires string content.")
        return WriteFileAction(type="write_file", path=path, content=content)

    if action_type == "check_write_files":
        return CheckWriteFilesAction(
            type="check_write_files",
            files=parse_write_file_items(value.get("files"), raw, action_type="check_write_files"),
        )

    if action_type == "write_files":
        return WriteFilesAction(type="write_files", files=parse_write_file_items(value.get("files"), raw))

    if action_type == "check_delete_file":
        path = _parse_string_field(value.get("path"), raw, "check_delete_file action requires a string path.")
        return CheckDeleteFileAction(type="check_delete_file", path=path)

    if action_type == "delete_file":
        path = _parse_string_field(value.get("path"), raw, "delete_file action requires a string path.")
        return DeleteFileAction(type="delete_file", path=path)

    if action_type == "check_delete_files":
        return CheckDeleteFilesAction(
            type="check_delete_files",
            paths=parse_path_list(value.get("paths"), raw, "check_delete_files", maximum=100),
        )

    if action_type == "delete_files":
        return DeleteFilesAction(
            type="delete_files",
            paths=parse_path_list(value.get("paths"), raw, "delete_files", maximum=100),
        )

    if action_type == "check_move_file":
        source, destination = _parse_transfer(value, raw, "check_move_file")
        return CheckMoveFileAction(type="check_move_file", source=source, destination=destination)

    if action_type == "move_file":
        source, destination = _parse_transfer(value, raw, "move_file")
        return MoveFileAction(type="move_file", source=source, destination=destination)

    if action_type == "check_move_files":
        return CheckMoveFilesAction(
            type="check_move_files",
            transfers=parse_move_file_transfers(value.get("transfers"), raw, "check_move_files"),
        )

    if action_type == "move_files":
        return MoveFilesAction(
            type="move_files",
            transfers=parse_move_file_transfers(value.get("transfers"), raw, "move_files"),
        )

    if action_type == "check_copy_file":
        source, destination = _parse_transfer(value, raw, "check_copy_file")
        return CheckCopyFileAction(type="check_copy_file", source=source, destination=destination)

    if action_type == "copy_file":
        source, destination = _parse_transfer(value, raw, "copy_file")
        return CopyFileAction(type="copy_file", source=source, destination=destination)

    if action_type == "check_copy_files":
        return CheckCopyFilesAction(
            type="check_copy_files",
            transfers=parse_move_file_transfers(value.get("transfers"), raw, "check_copy_files"),
        )

    if action_type == "copy_files":
        return CopyFilesAction(
            type="copy_files",
            transfers=parse_move_file_transfers(value.get("transfers"), raw, "copy_files"),
        )

    if action_type == "check_move_dir":
        source, destination = _parse_transfer(value, raw, "check_move_dir")
        return CheckMoveDirectoryAction(type="check_move_dir", source=source, destination=destination)

    if action_type == "move_dir":
        source, destination = _parse_transfer(value, raw, "move_dir")
        return MoveDirectoryAction(type="move_dir", source=source, destination=destination)

    if action_type == "check_move_dirs":
        return CheckMoveDirectoriesAction(
            type="check_move_dirs",
            transfers=parse_directory_transfers(value.get("transfers"), raw, "check_move_dirs"),
        )

    if action_type == "move_dirs":
        return MoveDirectoriesAction(
            type="move_dirs",
            transfers=parse_directory_transfers(value.get("transfers"), raw, "move_dirs"),
        )

    if action_type == "check_copy_dir":
        source, destination = _parse_transfer(value, raw, "check_copy_dir")
        return CheckCopyDirectoryAction(type="check_copy_dir", source=source, destination=destination)

    if action_type == "copy_dir":
        source, destination = _parse_transfer(value, raw, "copy_dir")
        return CopyDirectoryAction(type="copy_dir", source=source, destination=destination)

    if action_type == "check_copy_dirs":
        return CheckCopyDirectoriesAction(
            type="check_copy_dirs",
            transfers=parse_directory_transfers(value.get("transfers"), raw, "check_copy_dirs"),
        )

    if action_type == "copy_dirs":
        return CopyDirectoriesAction(
            type="copy_dirs",
            transfers=parse_directory_transfers(value.get("transfers"), raw, "copy_dirs"),
        )

    if action_type == "check_create_dir":
        path = _parse_string_field(value.get("path"), raw, "check_create_dir action requires a string path.")
        return CheckCreateDirectoryAction(type="check_create_dir", path=path)

    if action_type == "create_dir":
        path = _parse_string_field(value.get("path"), raw, "create_dir action requires a string path.")
        return CreateDirectoryAction(type="create_dir", path=path)

    if action_type == "check_create_dirs":
        return CheckCreateDirectoriesAction(
            type="check_create_dirs",
            paths=parse_path_list(value.get("paths"), raw, "check_create_dirs", maximum=100),
        )

    if action_type == "create_dirs":
        return CreateDirectoriesAction(
            type="create_dirs",
            paths=parse_path_list(value.get("paths"), raw, "create_dirs", maximum=100),
        )

    if action_type == "check_delete_empty_dir":
        path = _parse_string_field(value.get("path"), raw, "check_delete_empty_dir action requires a string path.")
        return CheckDeleteEmptyDirectoryAction(type="check_delete_empty_dir", path=path)

    if action_type == "delete_empty_dir":
        path = _parse_string_field(value.get("path"), raw, "delete_empty_dir action requires a string path.")
        return DeleteEmptyDirectoryAction(type="delete_empty_dir", path=path)

    if action_type == "check_delete_empty_dirs":
        return CheckDeleteEmptyDirectoriesAction(
            type="check_delete_empty_dirs",
            paths=parse_path_list(value.get("paths"), raw, "check_delete_empty_dirs", maximum=100),
        )

    if action_type == "delete_empty_dirs":
        return DeleteEmptyDirectoriesAction(
            type="delete_empty_dirs",
            paths=parse_path_list(value.get("paths"), raw, "delete_empty_dirs", maximum=100),
        )

    if action_type == "check_set_executable":
        path = _parse_string_field(value.get("path"), raw, "check_set_executable action requires a string path.")
        executable = value.get("executable", True)
        if not isinstance(executable, bool):
            raise ActionParseError("check_set_executable action executable must be a boolean.", raw)
        return CheckSetExecutableAction(type="check_set_executable", path=path, executable=executable)

    if action_type == "set_executable":
        path = _parse_string_field(value.get("path"), raw, "set_executable action requires a string path.")
        executable = value.get("executable", True)
        if not isinstance(executable, bool):
            raise ActionParseError("set_executable action executable must be a boolean.", raw)
        return SetExecutableAction(type="set_executable", path=path, executable=executable)

    raise AssertionError(f"Unhandled file edit action type: {action_type!r}")
    CheckSetExecutableAction,
    SetExecutableAction,
