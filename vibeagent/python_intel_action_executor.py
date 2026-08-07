from __future__ import annotations

from .action_results import build_reference_context_results
from .python_action_reports import python_call_graph_message, python_found_message
from .types import (
    AgentAction,
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
)
from .workspace import (
    check_python_syntax,
    find_python_calls,
    find_python_definitions,
    find_python_references,
    inspect_python_call_graph,
    inspect_python_dependencies,
)


def execute_python_intel_action(workspace, action: AgentAction) -> Observation | None:
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
            message = python_found_message(total, len(definitions), "definition", errors=errors)
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
            message = python_found_message(total, len(calls), "call", errors=errors)
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
            message = python_call_graph_message(
                total,
                len(edges),
                total_files,
                action.max_files,
                errors=errors,
            )
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
            message = python_found_message(total, len(references), "reference", errors=errors)
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
            message = python_found_message(total, len(contexts), "reference context", errors=errors)
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

    return None
