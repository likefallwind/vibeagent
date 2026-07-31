from __future__ import annotations

from .types import (
    CheckEditFileAction,
    CheckEditFileObservation,
    CheckMultiEditAction,
    CheckMultiEditObservation,
    EditFileAction,
    EditFileObservation,
    MultiEditAction,
    MultiEditObservation,
    Observation,
)
from .workspace import RunWorkspace, edit_project_file, multi_edit_project_file, preview_edit_project_file, preview_multi_edit_project_file


def execute_exact_file_action(workspace: RunWorkspace, action: object) -> Observation | None:
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
            old=action.old,
            new=action.new,
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
            old=action.old,
            new=action.new,
        )

    if isinstance(action, CheckMultiEditAction):
        try:
            _, diff = preview_multi_edit_project_file(
                workspace,
                action.path,
                [(edit.old, edit.new, edit.replace_all) for edit in action.edits],
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
            edits=action.edits,
        )

    if isinstance(action, MultiEditAction):
        try:
            _, diff = multi_edit_project_file(
                workspace,
                action.path,
                [(edit.old, edit.new, edit.replace_all) for edit in action.edits],
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
            edits=action.edits,
        )

    return None
