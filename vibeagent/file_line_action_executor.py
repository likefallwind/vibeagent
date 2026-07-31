from __future__ import annotations

from .types import (
    AppendFileAction,
    AppendFileObservation,
    CheckAppendFileAction,
    CheckAppendFileObservation,
    CheckInsertLinesAction,
    CheckInsertLinesObservation,
    CheckReplaceLinesAction,
    CheckReplaceLinesObservation,
    InsertLinesAction,
    InsertLinesObservation,
    Observation,
    ReplaceLinesAction,
    ReplaceLinesObservation,
)
from .workspace import (
    RunWorkspace,
    append_project_file,
    insert_project_file_lines,
    preview_append_project_file,
    preview_insert_project_file_lines,
    preview_replace_project_file_lines,
    replace_project_file_lines,
)


def execute_line_file_action(workspace: RunWorkspace, action: object) -> Observation | None:
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
            content=action.content,
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
            content=action.content,
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
            content=action.content,
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
            content=action.content,
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
            content=action.content,
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
            content=action.content,
        )

    return None
