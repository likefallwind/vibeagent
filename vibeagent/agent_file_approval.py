from __future__ import annotations

from . import types as t


def build_file_approval_request(action: object) -> t.ApprovalRequest | None:
    if isinstance(action, t.WriteFileAction):
        return t.ApprovalRequest(
            action_type="write_file",
            target=action.path,
            risk="This will create or replace a file in the active project.",
        )
    if isinstance(action, t.WriteFilesAction):
        return t.ApprovalRequest(
            action_type="write_files",
            target=", ".join(file.path for file in action.files),
            risk="This will create or replace multiple files in the active project.",
        )
    if isinstance(action, t.EditFileAction):
        return t.ApprovalRequest(
            action_type="edit_file",
            target=action.path,
            risk="This will modify an existing file in the active project.",
        )
    if isinstance(action, t.MultiEditAction):
        return t.ApprovalRequest(
            action_type="multi_edit_file",
            target=action.path,
            risk="This will apply multiple exact replacements to an existing file in the active project.",
        )
    if isinstance(action, t.NotebookEditAction):
        target = f"{action.path} cell {action.cell_id or action.cell_number}"
        return t.ApprovalRequest(
            action_type="notebook_edit",
            target=target,
            risk="This will modify a notebook cell in the active project.",
        )
    if isinstance(action, t.ReplacePythonDefinitionAction):
        return t.ApprovalRequest(
            action_type="replace_python_definition",
            target=f"{action.symbol} in {action.path or '.'}",
            risk="This will replace a full Python class/function definition in the active project.",
        )
    if isinstance(action, t.PythonRenameAction):
        return t.ApprovalRequest(
            action_type="python_rename",
            target=f"{action.symbol} -> {action.new_name} in {action.path or '.'}",
            risk="This will rename Python identifiers across matching project files.",
        )
    if isinstance(action, t.CodeRenameAction):
        return t.ApprovalRequest(
            action_type="code_rename",
            target=f"{action.symbol} -> {action.new_name} in {action.path or '.'}",
            risk="This will rename non-Python source symbols or literals across matching project files.",
        )
    if isinstance(action, t.ReplaceLinesAction):
        return t.ApprovalRequest(
            action_type="replace_lines",
            target=f"{action.path}:{action.start_line}-{action.end_line}",
            risk="This will replace a line range in an existing file in the active project.",
        )
    if isinstance(action, t.InsertLinesAction):
        return t.ApprovalRequest(
            action_type="insert_lines",
            target=f"{action.path}:{action.line}",
            risk="This will insert text into an existing file in the active project.",
        )
    if isinstance(action, t.AppendFileAction):
        return t.ApprovalRequest(
            action_type="append_file",
            target=action.path,
            risk="This will append text to an existing file in the active project.",
        )
    if isinstance(action, t.RegexReplaceAction):
        return t.ApprovalRequest(
            action_type="regex_replace",
            target=action.path,
            risk="This will apply a regular expression replacement to an existing file in the active project.",
        )
    if isinstance(action, t.JsonSetAction):
        return t.ApprovalRequest(
            action_type="json_set",
            target=f"{action.path} {action.pointer}",
            risk="This will update one value in an existing JSON file in the active project.",
        )
    if isinstance(action, t.JsonRemoveAction):
        return t.ApprovalRequest(
            action_type="json_remove",
            target=f"{action.path} {action.pointer}",
            risk="This will remove one value from an existing JSON file in the active project.",
        )
    if isinstance(action, t.JsonPatchAction):
        return t.ApprovalRequest(
            action_type="json_patch",
            target=f"{action.path} ({len(action.operations)} operations)",
            risk="This will apply multiple JSON changes to an existing JSON file in the active project.",
        )
    if isinstance(action, t.PatchFileAction):
        return t.ApprovalRequest(
            action_type="patch_file",
            target=action.path,
            risk="This will apply a unified diff patch to an existing file in the active project.",
        )
    if isinstance(action, t.PatchFilesAction):
        return t.ApprovalRequest(
            action_type="patch_files",
            target="multiple files",
            risk="This will apply a multi-file unified diff patch to files in the active project.",
        )
    if isinstance(action, t.DeleteFileAction):
        return t.ApprovalRequest(
            action_type="delete_file",
            target=action.path,
            risk="This will delete an existing file in the active project.",
        )
    if isinstance(action, t.DeleteFilesAction):
        return t.ApprovalRequest(
            action_type="delete_files",
            target=", ".join(action.paths),
            risk="This will delete explicit existing files in the active project.",
        )
    if isinstance(action, t.MoveFileAction):
        return t.ApprovalRequest(
            action_type="move_file",
            target=f"{action.source} -> {action.destination}",
            risk="This will move or rename an existing file in the active project.",
        )
    if isinstance(action, t.MoveFilesAction):
        return t.ApprovalRequest(
            action_type="move_files",
            target=", ".join(f"{transfer.source} -> {transfer.destination}" for transfer in action.transfers),
            risk="This will move or rename explicit existing files in the active project.",
        )
    if isinstance(action, t.CopyFileAction):
        return t.ApprovalRequest(
            action_type="copy_file",
            target=f"{action.source} -> {action.destination}",
            risk="This will copy an existing file to a new path in the active project.",
        )
    if isinstance(action, t.CopyFilesAction):
        return t.ApprovalRequest(
            action_type="copy_files",
            target=", ".join(f"{transfer.source} -> {transfer.destination}" for transfer in action.transfers),
            risk="This will copy explicit existing files to new paths in the active project.",
        )
    if isinstance(action, t.MoveDirectoryAction):
        return t.ApprovalRequest(
            action_type="move_dir",
            target=f"{action.source} -> {action.destination}",
            risk="This will move or rename an existing directory in the active project.",
        )
    if isinstance(action, t.MoveDirectoriesAction):
        return t.ApprovalRequest(
            action_type="move_dirs",
            target=", ".join(f"{transfer.source} -> {transfer.destination}" for transfer in action.transfers),
            risk="This will move or rename one or more existing directories in the active project.",
        )
    if isinstance(action, t.CopyDirectoryAction):
        return t.ApprovalRequest(
            action_type="copy_dir",
            target=f"{action.source} -> {action.destination}",
            risk="This will copy an existing directory tree in the active project.",
        )
    if isinstance(action, t.CopyDirectoriesAction):
        return t.ApprovalRequest(
            action_type="copy_dirs",
            target=", ".join(f"{transfer.source} -> {transfer.destination}" for transfer in action.transfers),
            risk="This will copy one or more existing directory trees in the active project.",
        )
    if isinstance(action, t.CreateDirectoryAction):
        return t.ApprovalRequest(
            action_type="create_dir",
            target=action.path,
            risk="This will create a directory in the active project.",
        )
    if isinstance(action, t.CreateDirectoriesAction):
        return t.ApprovalRequest(
            action_type="create_dirs",
            target=", ".join(action.paths),
            risk="This will create one or more directories in the active project.",
        )
    if isinstance(action, t.DeleteEmptyDirectoryAction):
        return t.ApprovalRequest(
            action_type="delete_empty_dir",
            target=action.path,
            risk="This will delete one empty directory in the active project.",
        )
    if isinstance(action, t.DeleteEmptyDirectoriesAction):
        return t.ApprovalRequest(
            action_type="delete_empty_dirs",
            target=", ".join(action.paths),
            risk="This will delete one or more empty directories in the active project.",
        )
    if isinstance(action, t.SetExecutableAction):
        state = "add executable bits to" if action.executable else "remove executable bits from"
        return t.ApprovalRequest(
            action_type="set_executable",
            target=action.path,
            risk=f"This will {state} one file in the active project.",
        )
    return None
