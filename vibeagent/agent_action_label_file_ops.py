from __future__ import annotations

from . import types as t


def build_file_operation_step_label(action: object) -> str | None:
    if isinstance(action, t.CheckWriteFileAction):
        return f"Check write {action.path}"
    if isinstance(action, t.WriteFileAction):
        return f"Write {action.path}"
    if isinstance(action, t.CheckWriteFilesAction):
        return f"Check write {len(action.files)} files"
    if isinstance(action, t.WriteFilesAction):
        return f"Write {len(action.files)} files"
    if isinstance(action, t.CheckEditFileAction):
        return f"Check edit {action.path}"
    if isinstance(action, t.EditFileAction):
        return f"Edit {action.path}"
    if isinstance(action, t.CheckMultiEditAction):
        return f"Check multi-edit {action.path}"
    if isinstance(action, t.MultiEditAction):
        return f"Multi-edit {action.path}"
    if isinstance(action, t.CheckReplaceLinesAction):
        return f"Check replace lines {action.start_line}-{action.end_line} in {action.path}"
    if isinstance(action, t.ReplaceLinesAction):
        return f"Replace lines {action.start_line}-{action.end_line} in {action.path}"
    if isinstance(action, t.CheckInsertLinesAction):
        return f"Check insert lines before {action.line} in {action.path}"
    if isinstance(action, t.InsertLinesAction):
        return f"Insert lines before {action.line} in {action.path}"
    if isinstance(action, t.CheckAppendFileAction):
        return f"Check append to {action.path}"
    if isinstance(action, t.AppendFileAction):
        return f"Append to {action.path}"
    if isinstance(action, t.RegexReplaceAction):
        return f"Regex replace in {action.path}"
    if isinstance(action, t.CheckRegexReplaceAction):
        return f"Check regex replace in {action.path}"
    if isinstance(action, t.CheckPatchAction):
        return f"Check patch {action.path}"
    if isinstance(action, t.CheckPatchesAction):
        return "Check patches"
    if isinstance(action, t.PatchFileAction):
        return f"Patch {action.path}"
    if isinstance(action, t.PatchFilesAction):
        return "Patch files"
    if isinstance(action, t.CheckDeleteFileAction):
        return f"Check delete {action.path}"
    if isinstance(action, t.DeleteFileAction):
        return f"Delete {action.path}"
    if isinstance(action, t.CheckDeleteFilesAction):
        return f"Check delete {len(action.paths)} file(s)"
    if isinstance(action, t.DeleteFilesAction):
        return f"Delete {len(action.paths)} file(s)"
    if isinstance(action, t.CheckMoveFileAction):
        return f"Check move {action.source}"
    if isinstance(action, t.MoveFileAction):
        return f"Move {action.source}"
    if isinstance(action, t.CheckMoveFilesAction):
        return f"Check move {len(action.transfers)} file(s)"
    if isinstance(action, t.MoveFilesAction):
        return f"Move {len(action.transfers)} file(s)"
    if isinstance(action, t.CheckCopyFileAction):
        return f"Check copy {action.source}"
    if isinstance(action, t.CopyFileAction):
        return f"Copy {action.source}"
    if isinstance(action, t.CheckCopyFilesAction):
        return f"Check copy {len(action.transfers)} file(s)"
    if isinstance(action, t.CopyFilesAction):
        return f"Copy {len(action.transfers)} file(s)"
    if isinstance(action, t.CheckMoveDirectoryAction):
        return f"Check move directory {action.source}"
    if isinstance(action, t.MoveDirectoryAction):
        return f"Move directory {action.source}"
    if isinstance(action, t.CheckMoveDirectoriesAction):
        return f"Check move {len(action.transfers)} directories"
    if isinstance(action, t.MoveDirectoriesAction):
        return f"Move {len(action.transfers)} directories"
    if isinstance(action, t.CheckCopyDirectoryAction):
        return f"Check copy directory {action.source}"
    if isinstance(action, t.CopyDirectoryAction):
        return f"Copy directory {action.source}"
    if isinstance(action, t.CheckCopyDirectoriesAction):
        return f"Check copy {len(action.transfers)} directories"
    if isinstance(action, t.CopyDirectoriesAction):
        return f"Copy {len(action.transfers)} directories"
    if isinstance(action, t.CheckCreateDirectoryAction):
        return f"Check create directory {action.path}"
    if isinstance(action, t.CreateDirectoryAction):
        return f"Create directory {action.path}"
    if isinstance(action, t.CheckCreateDirectoriesAction):
        return f"Check create {len(action.paths)} directories"
    if isinstance(action, t.CreateDirectoriesAction):
        return f"Create {len(action.paths)} directories"
    if isinstance(action, t.CheckDeleteEmptyDirectoryAction):
        return f"Check delete empty directory {action.path}"
    if isinstance(action, t.DeleteEmptyDirectoryAction):
        return f"Delete empty directory {action.path}"
    if isinstance(action, t.CheckDeleteEmptyDirectoriesAction):
        return f"Check delete {len(action.paths)} empty directories"
    if isinstance(action, t.DeleteEmptyDirectoriesAction):
        return f"Delete {len(action.paths)} empty directories"
    if isinstance(action, t.CheckSetExecutableAction):
        state = "executable" if action.executable else "not executable"
        return f"Check set {action.path} {state}"
    if isinstance(action, t.SetExecutableAction):
        state = "executable" if action.executable else "not executable"
        return f"Set {action.path} {state}"
    return None
