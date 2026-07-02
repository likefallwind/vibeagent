from __future__ import annotations

from .action_parsing import directory_transfer_pairs, format_file_mode
from .types import (
    AppendFileAction,
    AppendFileObservation,
    CheckAppendFileAction,
    CheckAppendFileObservation,
    CheckCreateDirectoryAction,
    CheckCreateDirectoryObservation,
    CheckCreateDirectoriesAction,
    CheckCreateDirectoriesObservation,
    CheckCopyDirectoryAction,
    CheckCopyDirectoryObservation,
    CheckCopyDirectoriesAction,
    CheckCopyDirectoriesObservation,
    CheckCopyFileAction,
    CheckCopyFileObservation,
    CheckCopyFilesAction,
    CheckCopyFilesObservation,
    CheckDeleteEmptyDirectoryAction,
    CheckDeleteEmptyDirectoryObservation,
    CheckDeleteEmptyDirectoriesAction,
    CheckDeleteEmptyDirectoriesObservation,
    CheckDeleteFileAction,
    CheckDeleteFileObservation,
    CheckDeleteFilesAction,
    CheckDeleteFilesObservation,
    CheckEditFileAction,
    CheckEditFileObservation,
    CheckInsertLinesAction,
    CheckInsertLinesObservation,
    CheckMoveDirectoryAction,
    CheckMoveDirectoryObservation,
    CheckMoveDirectoriesAction,
    CheckMoveDirectoriesObservation,
    CheckMoveFileAction,
    CheckMoveFileObservation,
    CheckMoveFilesAction,
    CheckMoveFilesObservation,
    CheckMultiEditAction,
    CheckMultiEditObservation,
    CheckPatchAction,
    CheckPatchObservation,
    CheckPatchesAction,
    CheckPatchesObservation,
    CheckRegexReplaceAction,
    CheckRegexReplaceObservation,
    CheckReplaceLinesAction,
    CheckReplaceLinesObservation,
    CheckSetExecutableAction,
    CheckSetExecutableObservation,
    CheckWriteFileAction,
    CheckWriteFileObservation,
    CheckWriteFileResult,
    CheckWriteFilesAction,
    CheckWriteFilesObservation,
    CopyDirectoryAction,
    CopyDirectoryObservation,
    CopyDirectoriesAction,
    CopyDirectoriesObservation,
    CopyFileAction,
    CopyFileObservation,
    CopyFilesAction,
    CopyFilesObservation,
    CreateDirectoryAction,
    CreateDirectoryObservation,
    CreateDirectoriesAction,
    CreateDirectoriesObservation,
    DeleteEmptyDirectoryAction,
    DeleteEmptyDirectoryObservation,
    DeleteEmptyDirectoriesAction,
    DeleteEmptyDirectoriesObservation,
    DeleteFileAction,
    DeleteFileObservation,
    DeleteFilesAction,
    DeleteFilesObservation,
    EditFileAction,
    EditFileObservation,
    InsertLinesAction,
    InsertLinesObservation,
    MoveDirectoryAction,
    MoveDirectoryObservation,
    MoveDirectoriesAction,
    MoveDirectoriesObservation,
    MoveFileAction,
    MoveFileObservation,
    MoveFilesAction,
    MoveFilesObservation,
    MultiEditAction,
    MultiEditObservation,
    Observation,
    PatchFileAction,
    PatchFileObservation,
    PatchFilesAction,
    PatchFilesObservation,
    RegexReplaceAction,
    RegexReplaceObservation,
    ReplaceLinesAction,
    ReplaceLinesObservation,
    SetExecutableAction,
    SetExecutableObservation,
    WriteFileAction,
    WriteFileObservation,
    WriteFileResult,
    WriteFilesAction,
    WriteFilesObservation,
)
from .workspace import (
    RunWorkspace,
    append_project_file,
    check_project_patch,
    check_project_patches,
    copy_project_directory,
    copy_project_directories,
    copy_project_file,
    copy_project_files,
    create_project_directories,
    create_project_directory,
    delete_project_empty_directories,
    delete_project_empty_directory,
    delete_project_file,
    delete_project_files,
    edit_project_file,
    insert_project_file_lines,
    move_project_directories,
    move_project_directory,
    move_project_file,
    move_project_files,
    multi_edit_project_file,
    patch_project_file,
    patch_project_files,
    preview_append_project_file,
    preview_copy_project_directories,
    preview_copy_project_directory,
    preview_copy_project_file,
    preview_copy_project_files,
    preview_create_project_directories,
    preview_create_project_directory,
    preview_delete_project_empty_directories,
    preview_delete_project_empty_directory,
    preview_delete_project_file,
    preview_delete_project_files,
    preview_edit_project_file,
    preview_insert_project_file_lines,
    preview_move_project_directories,
    preview_move_project_directory,
    preview_move_project_file,
    preview_move_project_files,
    preview_multi_edit_project_file,
    preview_regex_replace_project_file,
    preview_replace_project_file_lines,
    preview_set_project_file_executable,
    preview_write_run_file,
    preview_write_run_files,
    regex_replace_project_file,
    replace_project_file_lines,
    set_project_file_executable,
    write_run_file,
    write_run_files,
)


def execute_file_action(workspace: RunWorkspace, action: object) -> Observation | None:
    if isinstance(action, CheckEditFileAction):
        try:
            _, diff = preview_edit_project_file(workspace, action.path, action.old, action.new)
            ok = True
            message = f"Edit can apply to {action.path}."
        except ValueError as error:
            diff = ""
            ok = False
            message = str(error)
        return CheckEditFileObservation(
            kind="check_edit_file",
            path=action.path,
            ok=ok,
            message=message,
            diff=diff,
        )

    if isinstance(action, EditFileAction):
        try:
            _, diff = edit_project_file(workspace, action.path, action.old, action.new)
            ok = True
            message = f"Edited {action.path}."
        except ValueError as error:
            diff = ""
            ok = False
            message = str(error)
        return EditFileObservation(
            kind="edit_file",
            path=action.path,
            ok=ok,
            message=message,
            diff=diff,
        )

    if isinstance(action, CheckMultiEditAction):
        try:
            _, diff = preview_multi_edit_project_file(
                workspace,
                action.path,
                [(edit.old, edit.new) for edit in action.edits],
            )
            ok = True
            message = f"Multi-edit can apply {len(action.edits)} edit(s) to {action.path}."
        except ValueError as error:
            diff = ""
            ok = False
            message = str(error)
        return CheckMultiEditObservation(
            kind="check_multi_edit_file",
            path=action.path,
            ok=ok,
            message=message,
            diff=diff,
        )

    if isinstance(action, MultiEditAction):
        try:
            _, diff = multi_edit_project_file(
                workspace,
                action.path,
                [(edit.old, edit.new) for edit in action.edits],
            )
            ok = True
            message = f"Applied {len(action.edits)} edit(s) to {action.path}."
        except ValueError as error:
            diff = ""
            ok = False
            message = str(error)
        return MultiEditObservation(
            kind="multi_edit_file",
            path=action.path,
            ok=ok,
            message=message,
            diff=diff,
        )

    if isinstance(action, CheckReplaceLinesAction):
        try:
            _, diff = preview_replace_project_file_lines(
                workspace,
                action.path,
                action.start_line,
                action.end_line,
                action.content,
            )
            ok = True
            message = f"Line replacement can apply to lines {action.start_line}-{action.end_line} in {action.path}."
        except ValueError as error:
            diff = ""
            ok = False
            message = str(error)
        return CheckReplaceLinesObservation(
            kind="check_replace_lines",
            path=action.path,
            start_line=action.start_line,
            end_line=action.end_line,
            ok=ok,
            message=message,
            diff=diff,
        )

    if isinstance(action, ReplaceLinesAction):
        try:
            _, diff = replace_project_file_lines(
                workspace,
                action.path,
                action.start_line,
                action.end_line,
                action.content,
            )
            ok = True
            message = f"Replaced lines {action.start_line}-{action.end_line} in {action.path}."
        except ValueError as error:
            diff = ""
            ok = False
            message = str(error)
        return ReplaceLinesObservation(
            kind="replace_lines",
            path=action.path,
            start_line=action.start_line,
            end_line=action.end_line,
            ok=ok,
            message=message,
            diff=diff,
        )

    if isinstance(action, CheckInsertLinesAction):
        try:
            _, diff = preview_insert_project_file_lines(workspace, action.path, action.line, action.content)
            ok = True
            message = f"Line insertion can apply before line {action.line} in {action.path}."
        except ValueError as error:
            diff = ""
            ok = False
            message = str(error)
        return CheckInsertLinesObservation(
            kind="check_insert_lines",
            path=action.path,
            line=action.line,
            ok=ok,
            message=message,
            diff=diff,
        )

    if isinstance(action, InsertLinesAction):
        try:
            _, diff = insert_project_file_lines(workspace, action.path, action.line, action.content)
            ok = True
            message = f"Inserted lines before line {action.line} in {action.path}."
        except ValueError as error:
            diff = ""
            ok = False
            message = str(error)
        return InsertLinesObservation(
            kind="insert_lines",
            path=action.path,
            line=action.line,
            ok=ok,
            message=message,
            diff=diff,
        )

    if isinstance(action, CheckAppendFileAction):
        try:
            _, diff = preview_append_project_file(workspace, action.path, action.content)
            ok = True
            message = f"Append can apply to {action.path}."
        except ValueError as error:
            diff = ""
            ok = False
            message = str(error)
        return CheckAppendFileObservation(
            kind="check_append_file",
            path=action.path,
            ok=ok,
            message=message,
            diff=diff,
        )

    if isinstance(action, AppendFileAction):
        try:
            _, diff = append_project_file(workspace, action.path, action.content)
            ok = True
            message = f"Appended to {action.path}."
        except ValueError as error:
            diff = ""
            ok = False
            message = str(error)
        return AppendFileObservation(
            kind="append_file",
            path=action.path,
            ok=ok,
            message=message,
            diff=diff,
        )

    if isinstance(action, CheckRegexReplaceAction):
        try:
            _, replacements, diff = preview_regex_replace_project_file(
                workspace,
                action.path,
                action.pattern,
                action.replacement,
                count=action.count,
                case_sensitive=action.case_sensitive,
                multiline=action.multiline,
                max_replacements=action.max_replacements,
            )
            ok = True
            message = f"Regex replacement can apply to {replacements} match(es) in {action.path}."
        except ValueError as error:
            replacements = 0
            diff = ""
            ok = False
            message = str(error)
        return CheckRegexReplaceObservation(
            kind="check_regex_replace",
            path=action.path,
            pattern=action.pattern,
            count=action.count,
            replacements=replacements,
            ok=ok,
            message=message,
            diff=diff,
        )

    if isinstance(action, RegexReplaceAction):
        try:
            _, replacements, diff = regex_replace_project_file(
                workspace,
                action.path,
                action.pattern,
                action.replacement,
                count=action.count,
                case_sensitive=action.case_sensitive,
                multiline=action.multiline,
                max_replacements=action.max_replacements,
            )
            ok = True
            message = f"Applied {replacements} regex replacement(s) in {action.path}."
        except ValueError as error:
            replacements = 0
            diff = ""
            ok = False
            message = str(error)
        return RegexReplaceObservation(
            kind="regex_replace",
            path=action.path,
            pattern=action.pattern,
            count=action.count,
            replacements=replacements,
            ok=ok,
            message=message,
            diff=diff,
        )

    if isinstance(action, CheckPatchAction):
        try:
            _, diff = check_project_patch(workspace, action.path, action.patch)
            ok = True
            message = f"Patch can apply to {action.path}."
        except ValueError as error:
            diff = ""
            ok = False
            message = str(error)
        return CheckPatchObservation(
            kind="check_patch",
            path=action.path,
            ok=ok,
            message=message,
            diff=diff,
        )

    if isinstance(action, CheckPatchesAction):
        try:
            paths, diff = check_project_patches(workspace, action.patch)
            files = [path.relative_to(workspace.root).as_posix() for path in paths]
            ok = True
            message = f"Patches can apply to {len(files)} file(s)."
        except ValueError as error:
            files = []
            diff = ""
            ok = False
            message = str(error)
        return CheckPatchesObservation(
            kind="check_patches",
            files=files,
            ok=ok,
            message=message,
            diff=diff,
        )

    if isinstance(action, PatchFileAction):
        try:
            _, diff = patch_project_file(workspace, action.path, action.patch)
            ok = True
            message = f"Patched {action.path}."
        except ValueError as error:
            diff = ""
            ok = False
            message = str(error)
        return PatchFileObservation(
            kind="patch_file",
            path=action.path,
            ok=ok,
            message=message,
            diff=diff,
        )

    if isinstance(action, PatchFilesAction):
        try:
            paths, diff = patch_project_files(workspace, action.patch)
            files = [path.relative_to(workspace.root).as_posix() for path in paths]
            ok = True
            message = f"Patched {len(files)} file(s)."
        except ValueError as error:
            files = []
            diff = ""
            ok = False
            message = str(error)
        return PatchFilesObservation(
            kind="patch_files",
            files=files,
            ok=ok,
            message=message,
            diff=diff,
        )

    if isinstance(action, CheckWriteFileAction):
        try:
            _, diff = preview_write_run_file(workspace, action.path, action.content)
            return CheckWriteFileObservation(
                kind="check_write_file",
                path=action.path,
                ok=True,
                message=f"Write can apply to {action.path}.",
                diff=diff,
            )
        except ValueError as error:
            return CheckWriteFileObservation(
                kind="check_write_file",
                path=action.path,
                ok=False,
                message=str(error),
                diff="",
            )

    if isinstance(action, WriteFileAction):
        try:
            write_run_file(workspace, action.path, action.content)
            return WriteFileObservation(kind="write_file", path=action.path, ok=True, message=f"Wrote {action.path}")
        except ValueError as error:
            return WriteFileObservation(kind="write_file", path=action.path, ok=False, message=str(error))

    if isinstance(action, CheckWriteFilesAction):
        try:
            previews = preview_write_run_files(workspace, [(file.path, file.content) for file in action.files])
            files = [
                CheckWriteFileResult(path=relative_path, ok=True, message=f"Write can apply to {relative_path}.", diff=diff)
                for relative_path, _target, diff in previews
            ]
            return CheckWriteFilesObservation(
                kind="check_write_files",
                files=files,
                ok=True,
                message=f"Write can apply to {len(files)} file(s).",
            )
        except ValueError as error:
            files = [
                CheckWriteFileResult(path=file.path, ok=False, message=str(error), diff="")
                for file in action.files
            ]
            return CheckWriteFilesObservation(
                kind="check_write_files",
                files=files,
                ok=False,
                message=str(error),
            )

    if isinstance(action, WriteFilesAction):
        try:
            write_run_files(workspace, [(file.path, file.content) for file in action.files])
            files = [WriteFileResult(path=file.path, ok=True, message=f"Wrote {file.path}") for file in action.files]
            return WriteFilesObservation(
                kind="write_files",
                files=files,
                ok=True,
                message=f"Wrote {len(files)} file(s).",
            )
        except ValueError as error:
            files = [WriteFileResult(path=file.path, ok=False, message=str(error)) for file in action.files]
            return WriteFilesObservation(
                kind="write_files",
                files=files,
                ok=False,
                message=str(error),
            )

    if isinstance(action, CheckDeleteFileAction):
        try:
            _, diff = preview_delete_project_file(workspace, action.path)
            ok = True
            message = f"Delete can apply to {action.path}."
        except ValueError as error:
            diff = ""
            ok = False
            message = str(error)
        return CheckDeleteFileObservation(
            kind="check_delete_file",
            path=action.path,
            ok=ok,
            message=message,
            diff=diff,
        )

    if isinstance(action, DeleteFileAction):
        try:
            _, diff = delete_project_file(workspace, action.path)
            ok = True
            message = f"Deleted {action.path}."
        except ValueError as error:
            diff = ""
            ok = False
            message = str(error)
        return DeleteFileObservation(
            kind="delete_file",
            path=action.path,
            ok=ok,
            message=message,
            diff=diff,
        )

    if isinstance(action, CheckDeleteFilesAction):
        try:
            _, diff = preview_delete_project_files(workspace, action.paths)
            ok = True
            message = f"Delete can apply to {len(action.paths)} file(s)."
        except ValueError as error:
            diff = ""
            ok = False
            message = str(error)
        return CheckDeleteFilesObservation(
            kind="check_delete_files",
            paths=action.paths,
            ok=ok,
            message=message,
            diff=diff,
        )

    if isinstance(action, DeleteFilesAction):
        try:
            _, diff = delete_project_files(workspace, action.paths)
            ok = True
            message = f"Deleted {len(action.paths)} file(s)."
        except ValueError as error:
            diff = ""
            ok = False
            message = str(error)
        return DeleteFilesObservation(
            kind="delete_files",
            paths=action.paths,
            ok=ok,
            message=message,
            diff=diff,
        )

    if isinstance(action, CheckMoveFileAction):
        try:
            preview_move_project_file(workspace, action.source, action.destination)
            ok = True
            message = f"Move can apply from {action.source} to {action.destination}."
        except ValueError as error:
            ok = False
            message = str(error)
        return CheckMoveFileObservation(
            kind="check_move_file",
            source=action.source,
            destination=action.destination,
            ok=ok,
            message=message,
        )

    if isinstance(action, MoveFileAction):
        try:
            move_project_file(workspace, action.source, action.destination)
            ok = True
            message = f"Moved {action.source} to {action.destination}."
        except ValueError as error:
            ok = False
            message = str(error)
        return MoveFileObservation(
            kind="move_file",
            source=action.source,
            destination=action.destination,
            ok=ok,
            message=message,
        )

    if isinstance(action, CheckMoveFilesAction):
        try:
            preview_move_project_files(workspace, [transfer.__dict__ for transfer in action.transfers])
            ok = True
            message = f"Move can apply to {len(action.transfers)} file(s)."
        except ValueError as error:
            ok = False
            message = str(error)
        return CheckMoveFilesObservation(
            kind="check_move_files",
            transfers=action.transfers,
            ok=ok,
            message=message,
        )

    if isinstance(action, MoveFilesAction):
        try:
            move_project_files(workspace, [transfer.__dict__ for transfer in action.transfers])
            ok = True
            message = f"Moved {len(action.transfers)} file(s)."
        except ValueError as error:
            ok = False
            message = str(error)
        return MoveFilesObservation(
            kind="move_files",
            transfers=action.transfers,
            ok=ok,
            message=message,
        )

    if isinstance(action, CheckCopyFileAction):
        try:
            preview_copy_project_file(workspace, action.source, action.destination)
            ok = True
            message = f"Copy can apply from {action.source} to {action.destination}."
        except ValueError as error:
            ok = False
            message = str(error)
        return CheckCopyFileObservation(
            kind="check_copy_file",
            source=action.source,
            destination=action.destination,
            ok=ok,
            message=message,
        )

    if isinstance(action, CopyFileAction):
        try:
            copy_project_file(workspace, action.source, action.destination)
            ok = True
            message = f"Copied {action.source} to {action.destination}."
        except ValueError as error:
            ok = False
            message = str(error)
        return CopyFileObservation(
            kind="copy_file",
            source=action.source,
            destination=action.destination,
            ok=ok,
            message=message,
        )

    if isinstance(action, CheckCopyFilesAction):
        try:
            preview_copy_project_files(workspace, [transfer.__dict__ for transfer in action.transfers])
            ok = True
            message = f"Copy can apply to {len(action.transfers)} file(s)."
        except ValueError as error:
            ok = False
            message = str(error)
        return CheckCopyFilesObservation(
            kind="check_copy_files",
            transfers=action.transfers,
            ok=ok,
            message=message,
        )

    if isinstance(action, CopyFilesAction):
        try:
            copy_project_files(workspace, [transfer.__dict__ for transfer in action.transfers])
            ok = True
            message = f"Copied {len(action.transfers)} file(s)."
        except ValueError as error:
            ok = False
            message = str(error)
        return CopyFilesObservation(
            kind="copy_files",
            transfers=action.transfers,
            ok=ok,
            message=message,
        )

    if isinstance(action, CheckMoveDirectoryAction):
        try:
            preview_move_project_directory(workspace, action.source, action.destination)
            ok = True
            message = f"Directory move can apply from {action.source} to {action.destination}."
        except ValueError as error:
            ok = False
            message = str(error)
        return CheckMoveDirectoryObservation(
            kind="check_move_dir",
            source=action.source,
            destination=action.destination,
            ok=ok,
            message=message,
        )

    if isinstance(action, MoveDirectoryAction):
        try:
            move_project_directory(workspace, action.source, action.destination)
            ok = True
            message = f"Moved directory {action.source} to {action.destination}."
        except ValueError as error:
            ok = False
            message = str(error)
        return MoveDirectoryObservation(
            kind="move_dir",
            source=action.source,
            destination=action.destination,
            ok=ok,
            message=message,
        )

    if isinstance(action, CheckMoveDirectoriesAction):
        try:
            preview_move_project_directories(workspace, directory_transfer_pairs(action.transfers))
            ok = True
            message = f"Directory move can apply to {len(action.transfers)} transfer(s)."
        except ValueError as error:
            ok = False
            message = str(error)
        return CheckMoveDirectoriesObservation(
            kind="check_move_dirs",
            transfers=action.transfers,
            ok=ok,
            message=message,
        )

    if isinstance(action, MoveDirectoriesAction):
        try:
            move_project_directories(workspace, directory_transfer_pairs(action.transfers))
            ok = True
            message = f"Moved {len(action.transfers)} directory transfer(s)."
        except ValueError as error:
            ok = False
            message = str(error)
        return MoveDirectoriesObservation(
            kind="move_dirs",
            transfers=action.transfers,
            ok=ok,
            message=message,
        )

    if isinstance(action, CheckCopyDirectoryAction):
        try:
            preview_copy_project_directory(workspace, action.source, action.destination)
            ok = True
            message = f"Directory copy can apply from {action.source} to {action.destination}."
        except ValueError as error:
            ok = False
            message = str(error)
        return CheckCopyDirectoryObservation(
            kind="check_copy_dir",
            source=action.source,
            destination=action.destination,
            ok=ok,
            message=message,
        )

    if isinstance(action, CheckCopyDirectoriesAction):
        try:
            preview_copy_project_directories(workspace, directory_transfer_pairs(action.transfers))
            ok = True
            message = f"Directory copy can apply to {len(action.transfers)} transfer(s)."
        except ValueError as error:
            ok = False
            message = str(error)
        return CheckCopyDirectoriesObservation(
            kind="check_copy_dirs",
            transfers=action.transfers,
            ok=ok,
            message=message,
        )

    if isinstance(action, CopyDirectoryAction):
        try:
            copy_project_directory(workspace, action.source, action.destination)
            ok = True
            message = f"Copied directory {action.source} to {action.destination}."
        except ValueError as error:
            ok = False
            message = str(error)
        return CopyDirectoryObservation(
            kind="copy_dir",
            source=action.source,
            destination=action.destination,
            ok=ok,
            message=message,
        )

    if isinstance(action, CopyDirectoriesAction):
        try:
            copy_project_directories(workspace, directory_transfer_pairs(action.transfers))
            ok = True
            message = f"Copied {len(action.transfers)} directory transfer(s)."
        except ValueError as error:
            ok = False
            message = str(error)
        return CopyDirectoriesObservation(
            kind="copy_dirs",
            transfers=action.transfers,
            ok=ok,
            message=message,
        )

    if isinstance(action, CheckCreateDirectoryAction):
        try:
            preview_create_project_directory(workspace, action.path)
            ok = True
            message = f"Directory creation can apply to {action.path}."
        except ValueError as error:
            ok = False
            message = str(error)
        return CheckCreateDirectoryObservation(
            kind="check_create_dir",
            path=action.path,
            ok=ok,
            message=message,
        )

    if isinstance(action, CheckCreateDirectoriesAction):
        try:
            preview_create_project_directories(workspace, action.paths)
            ok = True
            message = f"Directory creation can apply to {len(action.paths)} path(s)."
        except ValueError as error:
            ok = False
            message = str(error)
        return CheckCreateDirectoriesObservation(
            kind="check_create_dirs",
            paths=action.paths,
            ok=ok,
            message=message,
        )

    if isinstance(action, CreateDirectoryAction):
        try:
            create_project_directory(workspace, action.path)
            ok = True
            message = f"Created directory {action.path}."
        except ValueError as error:
            ok = False
            message = str(error)
        return CreateDirectoryObservation(
            kind="create_dir",
            path=action.path,
            ok=ok,
            message=message,
        )

    if isinstance(action, CreateDirectoriesAction):
        try:
            create_project_directories(workspace, action.paths)
            ok = True
            message = f"Created {len(action.paths)} directory path(s)."
        except ValueError as error:
            ok = False
            message = str(error)
        return CreateDirectoriesObservation(
            kind="create_dirs",
            paths=action.paths,
            ok=ok,
            message=message,
        )

    if isinstance(action, CheckDeleteEmptyDirectoryAction):
        try:
            preview_delete_project_empty_directory(workspace, action.path)
            ok = True
            message = f"Empty directory deletion can apply to {action.path}."
        except ValueError as error:
            ok = False
            message = str(error)
        return CheckDeleteEmptyDirectoryObservation(
            kind="check_delete_empty_dir",
            path=action.path,
            ok=ok,
            message=message,
        )

    if isinstance(action, CheckDeleteEmptyDirectoriesAction):
        try:
            preview_delete_project_empty_directories(workspace, action.paths)
            ok = True
            message = f"Empty directory deletion can apply to {len(action.paths)} path(s)."
        except ValueError as error:
            ok = False
            message = str(error)
        return CheckDeleteEmptyDirectoriesObservation(
            kind="check_delete_empty_dirs",
            paths=action.paths,
            ok=ok,
            message=message,
        )

    if isinstance(action, DeleteEmptyDirectoryAction):
        try:
            delete_project_empty_directory(workspace, action.path)
            ok = True
            message = f"Deleted empty directory {action.path}."
        except ValueError as error:
            ok = False
            message = str(error)
        return DeleteEmptyDirectoryObservation(
            kind="delete_empty_dir",
            path=action.path,
            ok=ok,
            message=message,
        )

    if isinstance(action, DeleteEmptyDirectoriesAction):
        try:
            delete_project_empty_directories(workspace, action.paths)
            ok = True
            message = f"Deleted {len(action.paths)} empty directory path(s)."
        except ValueError as error:
            ok = False
            message = str(error)
        return DeleteEmptyDirectoriesObservation(
            kind="delete_empty_dirs",
            paths=action.paths,
            ok=ok,
            message=message,
        )

    if isinstance(action, CheckSetExecutableAction):
        try:
            _path, before, after = preview_set_project_file_executable(workspace, action.path, executable=action.executable)
            ok = True
            state = "executable" if action.executable else "not executable"
            message = f"Executable bit change can apply to set {action.path} {state}."
        except ValueError as error:
            before = 0
            after = 0
            ok = False
            message = str(error)
        return CheckSetExecutableObservation(
            kind="check_set_executable",
            path=action.path,
            executable=action.executable,
            ok=ok,
            mode_before=format_file_mode(before),
            mode_after=format_file_mode(after),
            message=message,
        )

    if isinstance(action, SetExecutableAction):
        try:
            _path, before, after = set_project_file_executable(workspace, action.path, executable=action.executable)
            ok = True
            state = "executable" if action.executable else "not executable"
            message = f"Set {action.path} {state}."
        except ValueError as error:
            before = 0
            after = 0
            ok = False
            message = str(error)
        return SetExecutableObservation(
            kind="set_executable",
            path=action.path,
            executable=action.executable,
            ok=ok,
            mode_before=format_file_mode(before),
            mode_after=format_file_mode(after),
            message=message,
        )

    return None
