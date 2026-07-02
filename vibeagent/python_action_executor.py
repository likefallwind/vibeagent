from __future__ import annotations

from .action_results import build_python_rename_preview_files, build_reference_context_results
from .types import (
    AgentAction,
    CheckReplacePythonDefinitionAction,
    CheckReplacePythonDefinitionObservation,
    Observation,
    PythonCall,
    PythonCallGraphAction,
    PythonCallGraphObservation,
    PythonCallsAction,
    PythonCallsObservation,
    PythonCheckAction,
    PythonCheckObservation,
    PythonCheckResult,
    PythonDependenciesAction,
    PythonDependenciesObservation,
    PythonDependenciesResult,
    PythonDefinition,
    PythonDefinitionsAction,
    PythonDefinitionsObservation,
    PythonImportRef,
    PythonReference,
    PythonReferenceContextsAction,
    PythonReferenceContextsObservation,
    PythonReferencesAction,
    PythonReferencesObservation,
    PythonRenameAction,
    PythonRenameObservation,
    PythonRenamePreviewAction,
    PythonRenamePreviewObservation,
    ReplacePythonDefinitionAction,
    ReplacePythonDefinitionObservation,
)
from .workspace import (
    apply_python_rename,
    check_python_syntax,
    find_python_calls,
    find_python_definitions,
    find_python_references,
    inspect_python_call_graph,
    inspect_python_dependencies,
    preview_python_rename,
    preview_replace_python_definition,
    replace_python_definition,
)


def execute_python_action(workspace, action: AgentAction) -> Observation | None:
    if isinstance(action, PythonCheckAction):
        try:
            raw_results, total = check_python_syntax(workspace, action.path, max_files=action.max_files)
            files = [PythonCheckResult(**item) for item in raw_results]
            failed_count = sum(1 for file in files if not file.ok)
            truncated = len(files) < total
            message = f"Checked {len(files)}/{total} Python file(s); {failed_count} failed."
            ok = failed_count == 0
        except ValueError as error:
            files = []
            total = 0
            truncated = False
            ok = False
            message = str(error)
        return PythonCheckObservation(
            kind="python_check",
            path=action.path,
            files=files,
            total=total,
            truncated=truncated,
            ok=ok,
            message=message,
        )

    if isinstance(action, PythonDependenciesAction):
        try:
            raw_results, total = inspect_python_dependencies(
                workspace,
                action.path,
                max_files=action.max_files,
                max_imports=action.max_imports,
            )
            files = [
                PythonDependenciesResult(
                    path=str(item["path"]),
                    ok=bool(item["ok"]),
                    module=str(item["module"]),
                    imports=[PythonImportRef(**import_item) for import_item in item["imports"]],
                    local_modules=list(item["local_modules"]),
                    external_modules=list(item["external_modules"]),
                    message=str(item["message"]),
                )
                for item in raw_results
            ]
            failed_count = sum(1 for file in files if not file.ok)
            truncated = len(files) < total
            ok = failed_count == 0
            message = f"Inspected dependencies for {len(files)}/{total} Python file(s); {failed_count} failed."
        except ValueError as error:
            files = []
            total = 0
            truncated = False
            ok = False
            message = str(error)
        return PythonDependenciesObservation(
            kind="python_dependencies",
            path=action.path,
            files=files,
            total=total,
            truncated=truncated,
            ok=ok,
            message=message,
        )

    if isinstance(action, PythonDefinitionsAction):
        try:
            raw_definitions, total, errors = find_python_definitions(
                workspace,
                action.symbol,
                relative_path=action.path,
                max_matches=action.max_matches,
                max_lines=action.max_lines,
            )
            definitions = [PythonDefinition(**item) for item in raw_definitions]
            truncated = len(definitions) < total
            message = f"Found {total} Python definition(s)."
            if truncated:
                message += f" Showing first {len(definitions)}."
            if errors:
                message += f" Skipped {len(errors)} file(s)."
            ok = True
        except ValueError as error:
            definitions = []
            total = 0
            truncated = False
            errors = []
            message = str(error)
            ok = False
        return PythonDefinitionsObservation(
            kind="python_definitions",
            symbol=action.symbol,
            path=action.path,
            definitions=definitions,
            total=total,
            truncated=truncated,
            ok=ok,
            errors=errors,
            message=message,
        )

    if isinstance(action, PythonCallsAction):
        try:
            raw_calls, total, errors = find_python_calls(
                workspace,
                action.symbol,
                relative_path=action.path,
                max_matches=action.max_matches,
            )
            calls = [PythonCall(**item) for item in raw_calls]
            truncated = len(calls) < total
            message = f"Found {total} Python call(s)."
            if truncated:
                message += f" Showing first {len(calls)}."
            if errors:
                message += f" Skipped {len(errors)} file(s)."
            ok = True
        except ValueError as error:
            calls = []
            total = 0
            truncated = False
            errors = []
            message = str(error)
            ok = False
        return PythonCallsObservation(
            kind="python_calls",
            symbol=action.symbol,
            path=action.path,
            calls=calls,
            total=total,
            truncated=truncated,
            ok=ok,
            errors=errors,
            message=message,
        )

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

    if isinstance(action, PythonCallGraphAction):
        try:
            raw_edges, total, total_files, errors = inspect_python_call_graph(
                workspace,
                relative_path=action.path,
                max_files=action.max_files,
                max_edges=action.max_edges,
            )
            edges = [PythonCall(**item) for item in raw_edges]
            truncated = len(edges) < total
            message = f"Found {total} Python call graph edge(s) across {total_files} file(s)."
            if truncated:
                message += f" Showing first {len(edges)}."
            if total_files > action.max_files:
                message += f" Inspected first {action.max_files} file(s)."
            if errors:
                message += f" Skipped {len(errors)} file(s)."
            ok = True
        except ValueError as error:
            edges = []
            total = 0
            truncated = False
            errors = []
            message = str(error)
            ok = False
        return PythonCallGraphObservation(
            kind="python_call_graph",
            path=action.path,
            edges=edges,
            total=total,
            truncated=truncated,
            ok=ok,
            errors=errors,
            message=message,
        )

    if isinstance(action, PythonReferencesAction):
        try:
            raw_references, total, errors = find_python_references(
                workspace,
                action.symbol,
                relative_path=action.path,
                max_matches=action.max_matches,
            )
            references = [PythonReference(**item) for item in raw_references]
            truncated = len(references) < total
            message = f"Found {total} Python reference(s)."
            if truncated:
                message += f" Showing first {len(references)}."
            if errors:
                message += f" Skipped {len(errors)} file(s)."
            ok = True
        except ValueError as error:
            references = []
            total = 0
            truncated = False
            errors = []
            message = str(error)
            ok = False
        return PythonReferencesObservation(
            kind="python_references",
            symbol=action.symbol,
            path=action.path,
            references=references,
            total=total,
            truncated=truncated,
            ok=ok,
            errors=errors,
            message=message,
        )

    if isinstance(action, PythonReferenceContextsAction):
        try:
            raw_references, total, errors = find_python_references(
                workspace,
                action.symbol,
                relative_path=action.path,
                max_matches=action.max_matches,
            )
            contexts = build_reference_context_results(
                workspace,
                raw_references,
                action.symbol,
                action.context_lines,
                action.max_bytes_per_context,
            )
            truncated = len(contexts) < total
            message = f"Found {total} Python reference context(s)."
            if truncated:
                message += f" Showing first {len(contexts)}."
            if errors:
                message += f" Skipped {len(errors)} file(s)."
            ok = True
        except ValueError as error:
            contexts = []
            total = 0
            truncated = False
            errors = []
            message = str(error)
            ok = False
        return PythonReferenceContextsObservation(
            kind="python_reference_contexts",
            symbol=action.symbol,
            path=action.path,
            contexts=contexts,
            total=total,
            truncated=truncated,
            ok=ok,
            errors=errors,
            message=message,
            context_lines=action.context_lines,
            max_bytes_per_context=action.max_bytes_per_context,
        )

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
