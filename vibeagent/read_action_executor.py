from __future__ import annotations

from .output_conversion import output_context_results_from_dicts, output_diagnostics_from_dicts
from .read_action_file_observations import execute_read_file_action
from .types import (
    AgentAction,
    CodeOutlineResult,
    ListFilesAction,
    ListFilesObservation,
    ListTreeAction,
    ListTreeObservation,
    Observation,
    OutputContextsAction,
    OutputContextsObservation,
    OutputDiagnosticsAction,
    OutputDiagnosticsObservation,
    PythonSymbol,
    RepoMapAction,
    RepoMapObservation,
    RepoMapPythonFile,
)
from .workspace import (
    build_repo_map,
    list_project_files,
    list_project_tree,
    read_output_contexts_result,
    read_output_diagnostics_result,
)


def execute_read_action(workspace, action: AgentAction) -> Observation | None:
    file_observation = execute_read_file_action(workspace, action)
    if file_observation is not None:
        return file_observation

    if isinstance(action, ListFilesAction):
        try:
            files, total = list_project_files(workspace, action.path)
            truncated = len(files) < total
            message = f"Found {total} file(s)."
            if truncated:
                message += f" Showing first {len(files)}."
        except ValueError as error:
            files = []
            total = 0
            truncated = False
            message = str(error)
        return ListFilesObservation(
            kind="list_files",
            path=action.path or ".",
            files=files,
            total=total,
            truncated=truncated,
            message=message,
        )

    if isinstance(action, ListTreeAction):
        try:
            entries, total = list_project_tree(
                workspace,
                action.path,
                max_depth=action.max_depth,
                max_entries=action.max_entries,
            )
            truncated = len(entries) < total
            entry_word = "entry" if total == 1 else "entries"
            message = f"Found {total} {entry_word}."
            if truncated:
                message += f" Showing first {len(entries)}."
            ok = True
        except ValueError as error:
            entries = []
            total = 0
            truncated = False
            message = str(error)
            ok = False
        return ListTreeObservation(
            kind="list_tree",
            path=action.path or ".",
            entries=entries,
            total=total,
            truncated=truncated,
            max_depth=action.max_depth,
            ok=ok,
            message=message,
        )

    if isinstance(action, RepoMapAction):
        try:
            repo_map = build_repo_map(
                workspace,
                action.path,
                max_depth=action.max_depth,
                max_files=action.max_files,
                max_symbols=action.max_symbols,
            )
            python_files = [
                RepoMapPythonFile(
                    path=str(item["path"]),
                    ok=bool(item["ok"]),
                    imports=list(item["imports"]),
                    symbols=[PythonSymbol(**symbol) for symbol in item["symbols"]],
                    message=str(item["message"]),
                )
                for item in repo_map["python_files"]
            ]
            code_files = [
                CodeOutlineResult(
                    path=str(item["path"]),
                    ok=bool(item["ok"]),
                    language=str(item["language"]) if item.get("language") is not None else None,
                    imports=list(item["imports"]),
                    symbols=[PythonSymbol(**symbol) for symbol in item["symbols"]],
                    message=str(item["message"]),
                )
                for item in repo_map["code_files"]
            ]
            return RepoMapObservation(
                kind="repo_map",
                path=str(repo_map["path"]),
                tree=list(repo_map["tree"]),
                files=list(repo_map["files"]),
                python_files=python_files,
                code_files=code_files,
                total_tree_entries=int(repo_map["total_tree_entries"]),
                total_files=int(repo_map["total_files"]),
                truncated=bool(repo_map["truncated"]),
                ok=True,
                message=str(repo_map["message"]),
            )
        except ValueError as error:
            return RepoMapObservation(
                kind="repo_map",
                path=action.path or ".",
                tree=[],
                files=[],
                python_files=[],
                code_files=[],
                total_tree_entries=0,
                total_files=0,
                truncated=False,
                ok=False,
                message=str(error),
            )

    if isinstance(action, OutputContextsAction):
        result = read_output_contexts_result(
            workspace,
            action.text,
            context_lines=action.context_lines,
            max_contexts=action.max_contexts,
            max_bytes_per_context=action.max_bytes_per_context,
        )
        contexts = output_context_results_from_dicts(result["contexts"])
        return OutputContextsObservation(
            kind="output_contexts",
            contexts=contexts,
            total_refs=int(result["total_refs"]),
            truncated=bool(result["truncated"]),
            message=str(result["message"]),
        )

    if isinstance(action, OutputDiagnosticsAction):
        result = read_output_diagnostics_result(
            workspace,
            action.text,
            context_lines=action.context_lines,
            max_diagnostics=action.max_diagnostics,
            max_contexts=action.max_contexts,
            max_bytes_per_context=action.max_bytes_per_context,
        )
        return OutputDiagnosticsObservation(
            kind="output_diagnostics",
            diagnostics=output_diagnostics_from_dicts(result["diagnostics"]),
            contexts=output_context_results_from_dicts(result["contexts"]),
            total_diagnostics=int(result["total_diagnostics"]),
            total_refs=int(result["total_refs"]),
            diagnostics_truncated=bool(result["diagnostics_truncated"]),
            contexts_truncated=bool(result["contexts_truncated"]),
            message=str(result["message"]),
        )

    return None
