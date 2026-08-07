from __future__ import annotations

from .workspace_append_edit_ops import append_project_file, build_append_file, preview_append_project_file
from .workspace_exact_edit_ops import (
    EditSpec,
    build_edit_file,
    build_multi_edit,
    edit_project_file,
    multi_edit_project_file,
    preview_edit_project_file,
    preview_multi_edit_project_file,
)
from .workspace_line_edit_ops import (
    build_insert_lines,
    build_replace_lines,
    insert_project_file_lines,
    preview_insert_project_file_lines,
    preview_replace_project_file_lines,
    replace_project_file_lines,
)
from .workspace_regex_edit_ops import (
    build_regex_replacement,
    preview_regex_replace_project_file,
    regex_replace_project_file,
)
from .workspace_resolve import resolve_mutation_path
from .workspace_write_edit_ops import (
    build_write_file,
    prepare_write_run_files,
    preview_write_run_file,
    preview_write_run_files,
    write_run_file,
    write_run_files,
)
