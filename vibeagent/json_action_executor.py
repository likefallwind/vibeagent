from __future__ import annotations

from .types import (
    AgentAction,
    CheckJsonRemoveAction,
    CheckJsonRemoveObservation,
    CheckJsonPatchAction,
    CheckJsonPatchObservation,
    CheckJsonSetAction,
    CheckJsonSetObservation,
    JsonRemoveAction,
    JsonRemoveObservation,
    JsonPatchAction,
    JsonPatchObservation,
    JsonSetAction,
    JsonSetObservation,
    Observation,
)
from .workspace import (
    json_patch_project_file,
    json_remove_project_file,
    json_set_project_file,
    preview_json_patch_project_file,
    preview_json_remove_project_file,
    preview_json_set_project_file,
)


def execute_json_action(workspace, action: AgentAction) -> Observation | None:
    if isinstance(action, CheckJsonSetAction):
        try:
            _target, diff = preview_json_set_project_file(
                workspace,
                action.path,
                action.pointer,
                action.value,
                create_missing=action.create_missing,
            )
            ok = True
            message = f"JSON set can apply to {action.path} at {action.pointer}."
        except ValueError as error:
            ok = False
            diff = ""
            message = str(error)
        return CheckJsonSetObservation(
            kind="check_json_set",
            path=action.path,
            pointer=action.pointer,
            ok=ok,
            message=message,
            diff=diff,
            value=action.value,
            create_missing=action.create_missing,
        )

    if isinstance(action, JsonSetAction):
        try:
            _target, diff = json_set_project_file(
                workspace,
                action.path,
                action.pointer,
                action.value,
                create_missing=action.create_missing,
            )
            ok = True
            message = f"Set JSON value in {action.path} at {action.pointer}."
        except ValueError as error:
            ok = False
            diff = ""
            message = str(error)
        return JsonSetObservation(
            kind="json_set",
            path=action.path,
            pointer=action.pointer,
            ok=ok,
            message=message,
            diff=diff,
            value=action.value,
            create_missing=action.create_missing,
        )

    if isinstance(action, CheckJsonRemoveAction):
        try:
            _target, diff = preview_json_remove_project_file(workspace, action.path, action.pointer)
            ok = True
            message = f"JSON remove can apply to {action.path} at {action.pointer}."
        except ValueError as error:
            ok = False
            diff = ""
            message = str(error)
        return CheckJsonRemoveObservation(
            kind="check_json_remove",
            path=action.path,
            pointer=action.pointer,
            ok=ok,
            message=message,
            diff=diff,
        )

    if isinstance(action, JsonRemoveAction):
        try:
            _target, diff = json_remove_project_file(workspace, action.path, action.pointer)
            ok = True
            message = f"Removed JSON value in {action.path} at {action.pointer}."
        except ValueError as error:
            ok = False
            diff = ""
            message = str(error)
        return JsonRemoveObservation(
            kind="json_remove",
            path=action.path,
            pointer=action.pointer,
            ok=ok,
            message=message,
            diff=diff,
        )

    if isinstance(action, CheckJsonPatchAction):
        operations = [operation.__dict__ for operation in action.operations]
        try:
            _target, diff = preview_json_patch_project_file(workspace, action.path, operations)
            ok = True
            message = f"JSON patch can apply {len(action.operations)} operation(s) to {action.path}."
        except ValueError as error:
            ok = False
            diff = ""
            message = str(error)
        return CheckJsonPatchObservation(
            kind="check_json_patch",
            path=action.path,
            operation_count=len(action.operations),
            ok=ok,
            message=message,
            diff=diff,
            operations=action.operations,
        )

    if isinstance(action, JsonPatchAction):
        operations = [operation.__dict__ for operation in action.operations]
        try:
            _target, diff = json_patch_project_file(workspace, action.path, operations)
            ok = True
            message = f"Applied {len(action.operations)} JSON patch operation(s) to {action.path}."
        except ValueError as error:
            ok = False
            diff = ""
            message = str(error)
        return JsonPatchObservation(
            kind="json_patch",
            path=action.path,
            operation_count=len(action.operations),
            ok=ok,
            message=message,
            diff=diff,
            operations=action.operations,
        )

    return None
