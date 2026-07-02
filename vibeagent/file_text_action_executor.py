from __future__ import annotations

from .types import (
    AppendFileAction,
    AppendFileObservation,
    CheckAppendFileAction,
    CheckAppendFileObservation,
    CheckEditFileAction,
    CheckEditFileObservation,
    CheckInsertLinesAction,
    CheckInsertLinesObservation,
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
    CheckWriteFileAction,
    CheckWriteFileObservation,
    CheckWriteFileResult,
    CheckWriteFilesAction,
    CheckWriteFilesObservation,
    EditFileAction,
    EditFileObservation,
    InsertLinesAction,
    InsertLinesObservation,
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
    edit_project_file,
    insert_project_file_lines,
    multi_edit_project_file,
    patch_project_file,
    patch_project_files,
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


def execute_text_file_action(workspace: RunWorkspace, action: object) -> Observation | None:
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

    return None
