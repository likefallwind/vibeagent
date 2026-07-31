from __future__ import annotations

from dataclasses import dataclass
from typing import Literal


@dataclass(frozen=True)
class NotebookCellSummary:
    cell_number: int
    cell_id: str | None
    cell_type: str
    source: str
    source_truncated: bool = False
    execution_count: int | None = None
    output_count: int = 0


@dataclass(frozen=True)
class NotebookReadObservation:
    kind: Literal["notebook_read"]
    path: str
    ok: bool
    cells: list[NotebookCellSummary]
    total_cells: int
    start_cell: int
    cell_count: int
    truncated: bool
    include_outputs: bool
    message: str


@dataclass(frozen=True)
class CheckNotebookEditObservation:
    kind: Literal["check_notebook_edit"]
    path: str
    ok: bool
    cell_number: int | None
    cell_id: str | None
    message: str
    diff: str = ""
    new_source: str = ""
    cell_type: str | None = None


@dataclass(frozen=True)
class NotebookEditObservation:
    kind: Literal["notebook_edit"]
    path: str
    ok: bool
    cell_number: int | None
    cell_id: str | None
    message: str
    diff: str = ""
    new_source: str = ""
    cell_type: str | None = None
