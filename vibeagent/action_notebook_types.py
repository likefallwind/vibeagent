from __future__ import annotations

from dataclasses import dataclass
from typing import Literal


@dataclass(frozen=True)
class NotebookReadAction:
    type: Literal["notebook_read"]
    path: str
    start_cell: int = 1
    cell_count: int = 50
    include_outputs: bool = False
    max_source_chars: int = 2_000


@dataclass(frozen=True)
class CheckNotebookEditAction:
    type: Literal["check_notebook_edit"]
    path: str
    new_source: str
    cell_id: str | None = None
    cell_number: int | None = None
    cell_type: str | None = None


@dataclass(frozen=True)
class NotebookEditAction:
    type: Literal["notebook_edit"]
    path: str
    new_source: str
    cell_id: str | None = None
    cell_number: int | None = None
    cell_type: str | None = None
