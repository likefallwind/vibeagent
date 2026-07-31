from __future__ import annotations

from .action_results import build_python_rename_preview_files
from .types import (
    Observation,
    PythonRenameAction,
    PythonRenameObservation,
    PythonRenamePreviewAction,
    PythonRenamePreviewObservation,
)
from .workspace import apply_python_rename, preview_python_rename


def execute_python_rename_action(workspace, action: PythonRenamePreviewAction | PythonRenameAction) -> Observation | None:
    if isinstance(action, PythonRenamePreviewAction):
        try:
            preview = preview_python_rename(
                workspace,
                action.symbol,
                action.new_name,
                relative_path=action.path,
                max_files=action.max_files,
                max_replacements=action.max_replacements,
            )
            files = build_python_rename_preview_files(preview)
            message = str(preview["message"])
            if bool(preview["truncated"]):
                message += f" Showing first {action.max_replacements} replacement(s)."
            errors = list(preview["errors"])
            if errors:
                message += f" Skipped {len(errors)} file(s)."
            return PythonRenamePreviewObservation(
                kind="python_rename_preview",
                symbol=action.symbol,
                new_name=action.new_name,
                path=action.path,
                files=files,
                total_replacements=int(preview["total_replacements"]),
                total_files=int(preview["total_files"]),
                truncated=bool(preview["truncated"]),
                ok=True,
                errors=errors,
                message=message,
            )
        except ValueError as error:
            return PythonRenamePreviewObservation(
                kind="python_rename_preview",
                symbol=action.symbol,
                new_name=action.new_name,
                path=action.path,
                files=[],
                total_replacements=0,
                total_files=0,
                truncated=False,
                ok=False,
                errors=[],
                message=str(error),
            )

    if isinstance(action, PythonRenameAction):
        try:
            result = apply_python_rename(
                workspace,
                action.symbol,
                action.new_name,
                relative_path=action.path,
                max_files=action.max_files,
                max_replacements=action.max_replacements,
            )
            files = build_python_rename_preview_files(result)
            return PythonRenameObservation(
                kind="python_rename",
                symbol=action.symbol,
                new_name=action.new_name,
                path=action.path,
                files=files,
                total_replacements=int(result["total_replacements"]),
                total_files=int(result["total_files"]),
                ok=True,
                errors=[],
                message=f"Renamed {action.symbol} to {action.new_name} in {len(files)} file(s).",
                diff=str(result["diff"]),
            )
        except ValueError as error:
            return PythonRenameObservation(
                kind="python_rename",
                symbol=action.symbol,
                new_name=action.new_name,
                path=action.path,
                files=[],
                total_replacements=0,
                total_files=0,
                ok=False,
                errors=[],
                message=str(error),
                diff="",
            )

    return None
