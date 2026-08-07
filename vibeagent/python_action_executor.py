from __future__ import annotations

from .python_intel_action_executor import execute_python_intel_action
from .python_rename_action_executor import execute_python_rename_action
from .types import (
    AgentAction,
    CheckReplacePythonDefinitionAction,
    CheckReplacePythonDefinitionObservation,
    Observation,
    PythonRenameAction,
    PythonRenamePreviewAction,
    ReplacePythonDefinitionAction,
    ReplacePythonDefinitionObservation,
)
from .workspace import (
    preview_replace_python_definition,
    replace_python_definition,
)


def execute_python_action(workspace, action: AgentAction) -> Observation | None:
    observation = execute_python_intel_action(workspace, action)
    if observation is not None:
        return observation

    if isinstance(action, CheckReplacePythonDefinitionAction):
        try:
            _, _after, diff, definition = preview_replace_python_definition(
                workspace,
                action.symbol,
                action.content,
                relative_path=action.path,
            )
            return CheckReplacePythonDefinitionObservation(
                kind="check_replace_python_definition",
                symbol=action.symbol,
                path=action.path,
                definition_path=str(definition["path"]),
                qualified_name=str(definition["qualified_name"]),
                start_line=int(definition["line"]),
                end_line=int(definition["end_line"]),
                ok=True,
                message=f"Python definition replacement can apply to {definition['qualified_name']} in {definition['path']}.",
                diff=diff,
            )
        except ValueError as error:
            return CheckReplacePythonDefinitionObservation(
                kind="check_replace_python_definition",
                symbol=action.symbol,
                path=action.path,
                definition_path=None,
                qualified_name=None,
                start_line=None,
                end_line=None,
                ok=False,
                message=str(error),
                diff="",
            )

    if isinstance(action, ReplacePythonDefinitionAction):
        try:
            _, diff, definition = replace_python_definition(
                workspace,
                action.symbol,
                action.content,
                relative_path=action.path,
            )
            return ReplacePythonDefinitionObservation(
                kind="replace_python_definition",
                symbol=action.symbol,
                path=action.path,
                definition_path=str(definition["path"]),
                qualified_name=str(definition["qualified_name"]),
                start_line=int(definition["line"]),
                end_line=int(definition["end_line"]),
                ok=True,
                message=f"Replaced Python definition {definition['qualified_name']} in {definition['path']}.",
                diff=diff,
            )
        except ValueError as error:
            return ReplacePythonDefinitionObservation(
                kind="replace_python_definition",
                symbol=action.symbol,
                path=action.path,
                definition_path=None,
                qualified_name=None,
                start_line=None,
                end_line=None,
                ok=False,
                message=str(error),
                diff="",
            )

    if isinstance(action, PythonRenamePreviewAction):
        return execute_python_rename_action(workspace, action)

    if isinstance(action, PythonRenameAction):
        return execute_python_rename_action(workspace, action)

    return None
