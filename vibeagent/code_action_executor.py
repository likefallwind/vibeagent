from __future__ import annotations

from .action_results import build_code_rename_preview_files, build_reference_context_results
from .types import (
    AgentAction,
    CodeDependenciesAction,
    CodeDependenciesObservation,
    CodeDependenciesResult,
    CodeDefinition,
    CodeDefinitionsAction,
    CodeDefinitionsObservation,
    CodeImportRef,
    CodeReference,
    CodeReferenceContextsAction,
    CodeReferenceContextsObservation,
    CodeReferencesAction,
    CodeReferencesObservation,
    CodeRenameAction,
    CodeRenameObservation,
    CodeRenamePreviewAction,
    CodeRenamePreviewObservation,
    ConfigCheckAction,
    ConfigCheckObservation,
    ConfigCheckResult,
    Observation,
)
from .workspace import (
    apply_code_rename,
    check_config_syntax,
    find_code_definitions,
    find_code_references,
    inspect_code_dependencies,
    preview_code_rename,
)


def execute_code_action(workspace, action: AgentAction) -> Observation | None:
    if isinstance(action, ConfigCheckAction):
        try:
            raw_results, total = check_config_syntax(workspace, action.path, max_files=action.max_files)
            files = [ConfigCheckResult(**item) for item in raw_results]
            failed_count = sum(1 for file in files if not file.ok)
            truncated = len(files) < total
            message = f"Checked {len(files)}/{total} config file(s); {failed_count} failed."
            ok = failed_count == 0
        except ValueError as error:
            files = []
            total = 0
            truncated = False
            ok = False
            message = str(error)
        return ConfigCheckObservation(
            kind="config_check",
            path=action.path,
            files=files,
            total=total,
            truncated=truncated,
            ok=ok,
            message=message,
        )

    if isinstance(action, CodeDependenciesAction):
        try:
            raw_results, total = inspect_code_dependencies(
                workspace,
                action.path,
                max_files=action.max_files,
                max_imports=action.max_imports,
            )
            files = [
                CodeDependenciesResult(
                    path=str(item["path"]),
                    ok=bool(item["ok"]),
                    language=str(item["language"]),
                    imports=[CodeImportRef(**import_item) for import_item in item["imports"]],
                    dependencies=list(item["dependencies"]),
                    message=str(item["message"]),
                )
                for item in raw_results
            ]
            failed_count = sum(1 for file in files if not file.ok)
            truncated = len(files) < total
            ok = failed_count == 0
            message = f"Inspected dependencies for {len(files)}/{total} source file(s); {failed_count} failed."
        except ValueError as error:
            files = []
            total = 0
            truncated = False
            ok = False
            message = str(error)
        return CodeDependenciesObservation(
            kind="code_dependencies",
            path=action.path,
            files=files,
            total=total,
            truncated=truncated,
            ok=ok,
            message=message,
        )

    if isinstance(action, CodeReferencesAction):
        try:
            raw_references, total = find_code_references(
                workspace,
                action.symbol,
                relative_path=action.path,
                max_matches=action.max_matches,
            )
            references = [CodeReference(**item) for item in raw_references]
            truncated = len(references) < total
            ok = True
            message = f"Found {total} code reference(s) for {action.symbol}."
        except ValueError as error:
            references = []
            total = 0
            truncated = False
            ok = False
            message = str(error)
        return CodeReferencesObservation(
            kind="code_references",
            symbol=action.symbol,
            path=action.path,
            references=references,
            total=total,
            truncated=truncated,
            ok=ok,
            message=message,
        )

    if isinstance(action, CodeReferenceContextsAction):
        try:
            raw_references, total = find_code_references(
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
            ok = True
            message = f"Found {total} code reference context(s) for {action.symbol}."
            if truncated:
                message += f" Showing first {len(contexts)}."
        except ValueError as error:
            contexts = []
            total = 0
            truncated = False
            ok = False
            message = str(error)
        return CodeReferenceContextsObservation(
            kind="code_reference_contexts",
            symbol=action.symbol,
            path=action.path,
            contexts=contexts,
            total=total,
            truncated=truncated,
            ok=ok,
            message=message,
            context_lines=action.context_lines,
            max_bytes_per_context=action.max_bytes_per_context,
        )

    if isinstance(action, CodeDefinitionsAction):
        try:
            raw_definitions, total, errors = find_code_definitions(
                workspace,
                action.symbol,
                relative_path=action.path,
                max_matches=action.max_matches,
                max_lines=action.max_lines,
            )
            definitions = [CodeDefinition(**item) for item in raw_definitions]
            truncated = len(definitions) < total
            ok = not errors
            message = f"Found {total} code definition(s) for {action.symbol}."
        except ValueError as error:
            definitions = []
            total = 0
            errors = [str(error)]
            truncated = False
            ok = False
            message = str(error)
        return CodeDefinitionsObservation(
            kind="code_definitions",
            symbol=action.symbol,
            path=action.path,
            definitions=definitions,
            total=total,
            truncated=truncated,
            ok=ok,
            errors=errors,
            message=message,
        )

    if isinstance(action, CodeRenamePreviewAction):
        try:
            preview = preview_code_rename(
                workspace,
                action.symbol,
                action.new_name,
                relative_path=action.path,
                max_files=action.max_files,
                max_replacements=action.max_replacements,
            )
            files = build_code_rename_preview_files(preview)
            message = str(preview["message"])
            if bool(preview["truncated"]):
                message += f" Showing first {action.max_replacements} replacement(s)."
            errors = list(preview["errors"])
            if errors:
                message += f" Skipped {len(errors)} file(s)."
            return CodeRenamePreviewObservation(
                kind="code_rename_preview",
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
            return CodeRenamePreviewObservation(
                kind="code_rename_preview",
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

    if isinstance(action, CodeRenameAction):
        try:
            result = apply_code_rename(
                workspace,
                action.symbol,
                action.new_name,
                relative_path=action.path,
                max_files=action.max_files,
                max_replacements=action.max_replacements,
            )
            files = build_code_rename_preview_files(result)
            return CodeRenameObservation(
                kind="code_rename",
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
            return CodeRenameObservation(
                kind="code_rename",
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
