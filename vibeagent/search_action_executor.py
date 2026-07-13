from __future__ import annotations

from .types import (
    FindFilesAction,
    FindFilesObservation,
    GlobAction,
    GlobObservation,
    Observation,
    SearchAction,
    SearchContextResult,
    SearchContextsAction,
    SearchContextsObservation,
    SearchObservation,
)
from .workspace import (
    RunWorkspace,
    find_project_files_result,
    glob_project_files,
    search_project_contexts_result,
    search_project_result,
)


def execute_search_action(workspace: RunWorkspace, action: object) -> Observation | None:
    if isinstance(action, SearchAction):
        return search_observation(workspace, action)
    if isinstance(action, SearchContextsAction):
        return search_contexts_observation(workspace, action)
    if isinstance(action, FindFilesAction):
        return find_files_observation(workspace, action)
    if isinstance(action, GlobAction):
        return glob_observation(workspace, action)
    return None


def search_observation(workspace: RunWorkspace, action: SearchAction) -> SearchObservation:
    try:
        result = search_project_result(
            workspace,
            action.query,
            max_matches=action.max_matches,
            relative_path=action.path,
            file_glob=action.file_glob,
            regex=action.regex,
            case_sensitive=action.case_sensitive,
            context_lines=action.context_lines,
        )
        matches = list(result["matches"])
        total = int(result["total"])
        truncated = bool(result["truncated"])
        message = f"Found {total} match(es)."
        if truncated:
            message += f" Showing {len(matches)}."
        ok = True
    except ValueError as error:
        matches = []
        total = 0
        truncated = False
        message = str(error)
        ok = False
    return SearchObservation(
        kind="search",
        ok=ok,
        query=action.query,
        matches=matches,
        total=total,
        truncated=truncated,
        message=message,
        path=action.path,
        file_glob=action.file_glob,
        regex=action.regex,
        case_sensitive=action.case_sensitive,
        context_lines=action.context_lines,
    )


def search_contexts_observation(workspace: RunWorkspace, action: SearchContextsAction) -> SearchContextsObservation:
    try:
        result = search_project_contexts_result(
            workspace,
            action.query,
            max_matches=action.max_matches,
            relative_path=action.path,
            file_glob=action.file_glob,
            regex=action.regex,
            case_sensitive=action.case_sensitive,
            context_lines=action.context_lines,
            max_bytes_per_context=action.max_bytes_per_context,
        )
        contexts = [SearchContextResult(**item) for item in result["contexts"]]
        total = int(result["total"])
        truncated = bool(result["truncated"])
        message = f"Found {total} match context(s)."
        if truncated:
            message += f" Showing {len(contexts)}."
        ok = True
    except ValueError as error:
        contexts = []
        total = 0
        truncated = False
        message = str(error)
        ok = False
    return SearchContextsObservation(
        kind="search_contexts",
        ok=ok,
        query=action.query,
        contexts=contexts,
        total=total,
        truncated=truncated,
        message=message,
        path=action.path,
        file_glob=action.file_glob,
        regex=action.regex,
        case_sensitive=action.case_sensitive,
        context_lines=action.context_lines,
        max_bytes_per_context=action.max_bytes_per_context,
    )


def find_files_observation(workspace: RunWorkspace, action: FindFilesAction) -> FindFilesObservation:
    try:
        result = find_project_files_result(
            workspace,
            action.query,
            max_matches=action.max_matches,
            relative_path=action.path,
            regex=action.regex,
            case_sensitive=action.case_sensitive,
            include_dirs=action.include_dirs,
        )
        matches = list(result["matches"])
        total = int(result["total"])
        truncated = bool(result["truncated"])
        message = f"Found {total} path match(es)."
        if truncated:
            message += f" Showing {len(matches)}."
        ok = True
    except ValueError as error:
        matches = []
        total = 0
        truncated = False
        message = str(error)
        ok = False
    return FindFilesObservation(
        kind="find_files",
        ok=ok,
        query=action.query,
        matches=matches,
        total=total,
        truncated=truncated,
        message=message,
        path=action.path,
        regex=action.regex,
        case_sensitive=action.case_sensitive,
        include_dirs=action.include_dirs,
    )


def glob_observation(workspace: RunWorkspace, action: GlobAction) -> GlobObservation:
    try:
        matches, total = glob_project_files(
            workspace,
            action.pattern,
            max_matches=action.max_matches,
            include_dirs=action.include_dirs,
        )
        truncated = len(matches) < total
        noun = "file(s) or directories" if action.include_dirs else "file(s)"
        message = f"Found {total} {noun}."
        if truncated:
            message += f" Showing first {len(matches)}."
        ok = True
    except ValueError as error:
        matches = []
        total = 0
        truncated = False
        message = str(error)
        ok = False
    return GlobObservation(
        kind="glob",
        pattern=action.pattern,
        matches=matches,
        total=total,
        truncated=truncated,
        ok=ok,
        message=message,
    )
