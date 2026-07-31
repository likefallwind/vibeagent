from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .types import (
    CheckNotebookEditAction,
    CheckNotebookEditObservation,
    NotebookCellSummary,
    NotebookEditAction,
    NotebookEditObservation,
    NotebookReadAction,
    NotebookReadObservation,
    Observation,
)
from .workspace import RunWorkspace
from .workspace_code_intel import build_simple_diff
from .workspace_file_read import read_utf8_text_file
from .workspace_resolve import resolve_inside_run, resolve_mutation_path


def execute_notebook_action(workspace: RunWorkspace, action: object) -> Observation | None:
    if isinstance(action, NotebookReadAction):
        return read_notebook(workspace, action)
    if isinstance(action, CheckNotebookEditAction):
        return preview_notebook_cell_edit(workspace, action)
    if isinstance(action, NotebookEditAction):
        return edit_notebook_cell(workspace, action)
    return None


def read_notebook(workspace: RunWorkspace, action: NotebookReadAction) -> NotebookReadObservation:
    try:
        _target, notebook = _load_notebook(workspace, action.path, mutate=False)
        cells = _notebook_cells(notebook)
        start = max(action.start_cell, 1)
        end = start + action.cell_count
        selected = cells[start - 1:end - 1]
        summaries = [
            _cell_summary(index, cell, max_source_chars=action.max_source_chars, include_outputs=action.include_outputs)
            for index, cell in enumerate(selected, start=start)
        ]
        truncated = end - 1 < len(cells)
        message = f"Read {len(summaries)}/{len(cells)} notebook cell(s) from {action.path}."
        if truncated:
            message += f" Showing cells {start}-{end - 2}."
        return NotebookReadObservation(
            kind="notebook_read",
            path=action.path,
            ok=True,
            cells=summaries,
            total_cells=len(cells),
            start_cell=start,
            cell_count=action.cell_count,
            truncated=truncated,
            include_outputs=action.include_outputs,
            message=message,
        )
    except ValueError as error:
        return NotebookReadObservation(
            kind="notebook_read",
            path=action.path,
            ok=False,
            cells=[],
            total_cells=0,
            start_cell=action.start_cell,
            cell_count=action.cell_count,
            truncated=False,
            include_outputs=action.include_outputs,
            message=str(error),
        )


def preview_notebook_cell_edit(workspace: RunWorkspace, action: CheckNotebookEditAction) -> CheckNotebookEditObservation:
    try:
        _target, cell_index, cell_id, diff, _after = _build_notebook_cell_edit(workspace, action, mutate=False)
        return CheckNotebookEditObservation(
            kind="check_notebook_edit",
            path=action.path,
            ok=True,
            cell_number=action.cell_number,
            cell_id=action.cell_id,
            message=f"Notebook edit can apply to cell {cell_index + 1} in {action.path}.",
            diff=diff,
            new_source=action.new_source,
            cell_type=action.cell_type,
        )
    except ValueError as error:
        return CheckNotebookEditObservation(
            kind="check_notebook_edit",
            path=action.path,
            ok=False,
            cell_number=action.cell_number,
            cell_id=action.cell_id,
            message=str(error),
            diff="",
            new_source=action.new_source,
            cell_type=action.cell_type,
        )


def edit_notebook_cell(workspace: RunWorkspace, action: NotebookEditAction) -> NotebookEditObservation:
    try:
        target, cell_index, cell_id, diff, after = _build_notebook_cell_edit(workspace, action, mutate=True)
        target.write_text(after, encoding="utf-8")
        return NotebookEditObservation(
            kind="notebook_edit",
            path=action.path,
            ok=True,
            cell_number=cell_index + 1,
            cell_id=cell_id,
            message=f"Edited notebook cell {cell_index + 1} in {action.path}.",
            diff=diff,
            new_source=action.new_source,
            cell_type=action.cell_type,
        )
    except ValueError as error:
        return NotebookEditObservation(
            kind="notebook_edit",
            path=action.path,
            ok=False,
            cell_number=action.cell_number,
            cell_id=action.cell_id,
            message=str(error),
            diff="",
            new_source=action.new_source,
            cell_type=action.cell_type,
        )


def _build_notebook_cell_edit(
    workspace: RunWorkspace,
    action: CheckNotebookEditAction | NotebookEditAction,
    *,
    mutate: bool,
) -> tuple[Path, int, str | None, str, str]:
    target, notebook = _load_notebook(workspace, action.path, mutate=mutate)
    before = target.read_text(encoding="utf-8")
    cells = _notebook_cells(notebook)
    cell_index = _find_cell_index(cells, cell_id=action.cell_id, cell_number=action.cell_number)
    cell = cells[cell_index]
    if action.cell_type is not None:
        _validate_cell_type(action.cell_type)
        cell["cell_type"] = action.cell_type
    cell["source"] = _source_to_notebook_lines(action.new_source)
    after = json.dumps(notebook, ensure_ascii=False, indent=1) + "\n"
    if before == after:
        raise ValueError(f"Notebook edit made no changes to {action.path}")
    cell_id = cell.get("id") if isinstance(cell.get("id"), str) else None
    return target, cell_index, cell_id, build_simple_diff(action.path, before, after), after


def _load_notebook(workspace: RunWorkspace, path: str, *, mutate: bool) -> tuple[Path, dict[str, Any]]:
    target = resolve_mutation_path(workspace.root, path) if mutate else resolve_inside_run(workspace.root, path)
    if not target.is_file():
        raise ValueError(f"Notebook does not exist: {path}")
    try:
        data = json.loads(read_utf8_text_file(target, path))
    except json.JSONDecodeError as error:
        raise ValueError(f"Invalid notebook JSON in {path}: {error.msg}") from error
    if not isinstance(data, dict):
        raise ValueError(f"Notebook root must be an object: {path}")
    _notebook_cells(data)
    return target, data


def _notebook_cells(notebook: dict[str, Any]) -> list[dict[str, Any]]:
    cells = notebook.get("cells")
    if not isinstance(cells, list):
        raise ValueError("Notebook cells must be a list.")
    for index, cell in enumerate(cells, start=1):
        if not isinstance(cell, dict):
            raise ValueError(f"Notebook cell {index} must be an object.")
    return cells


def _cell_summary(index: int, cell: dict[str, Any], *, max_source_chars: int, include_outputs: bool) -> NotebookCellSummary:
    source = _source_to_text(cell.get("source"))
    truncated = len(source) > max_source_chars
    if truncated:
        source = source[:max_source_chars]
    output_count = len(cell.get("outputs")) if include_outputs and isinstance(cell.get("outputs"), list) else 0
    execution_count = cell.get("execution_count") if isinstance(cell.get("execution_count"), int) else None
    cell_id = cell.get("id") if isinstance(cell.get("id"), str) else None
    cell_type = cell.get("cell_type") if isinstance(cell.get("cell_type"), str) else "unknown"
    return NotebookCellSummary(
        cell_number=index,
        cell_id=cell_id,
        cell_type=cell_type,
        source=source,
        source_truncated=truncated,
        execution_count=execution_count,
        output_count=output_count,
    )


def _find_cell_index(cells: list[dict[str, Any]], *, cell_id: str | None, cell_number: int | None) -> int:
    if cell_id is None and cell_number is None:
        raise ValueError("Notebook edit requires cell_id or cell_number.")
    if cell_id is not None:
        for index, cell in enumerate(cells):
            if cell.get("id") == cell_id:
                return index
        raise ValueError(f"Notebook cell id was not found: {cell_id}")
    assert cell_number is not None
    if cell_number < 1 or cell_number > len(cells):
        raise ValueError(f"Notebook cell_number out of range: {cell_number}")
    return cell_number - 1


def _validate_cell_type(cell_type: str) -> None:
    if cell_type not in {"code", "markdown", "raw"}:
        raise ValueError("Notebook cell_type must be code, markdown, or raw.")


def _source_to_text(source: object) -> str:
    if isinstance(source, list):
        return "".join(str(item) for item in source)
    if isinstance(source, str):
        return source
    return ""


def _source_to_notebook_lines(source: str) -> list[str]:
    if source == "":
        return []
    lines = source.splitlines(keepends=True)
    if source and not source.endswith(("\n", "\r")):
        return lines
    return lines
