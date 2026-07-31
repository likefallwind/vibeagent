from __future__ import annotations

from .types import (
    CheckPatchAction,
    CheckPatchObservation,
    CheckPatchesAction,
    CheckPatchesObservation,
    CheckRegexReplaceAction,
    CheckRegexReplaceObservation,
    Observation,
    PatchFileAction,
    PatchFileObservation,
    PatchFilesAction,
    PatchFilesObservation,
    RegexReplaceAction,
    RegexReplaceObservation,
)
from .workspace import (
    RunWorkspace,
    check_project_patch,
    check_project_patches,
    patch_project_file,
    patch_project_files,
    preview_regex_replace_project_file,
    regex_replace_project_file,
)


def execute_patch_file_action(workspace: RunWorkspace, action: object) -> Observation | None:
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
            replacement=action.replacement,
            case_sensitive=action.case_sensitive,
            multiline=action.multiline,
            max_replacements=action.max_replacements,
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
            replacement=action.replacement,
            case_sensitive=action.case_sensitive,
            multiline=action.multiline,
            max_replacements=action.max_replacements,
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

    return None
