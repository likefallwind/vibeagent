from __future__ import annotations

from typing import Any


def _symbol_text(
    command: Any,
    commands: dict[str, Any],
    command_name: str,
    getter_name: str,
    *,
    include_context: bool = False,
    include_max_lines: bool = False,
) -> str:
    symbol, path, kwargs, error, uses_named_options = commands["parse_interactive_python_symbol_argument"](
        command.argument,
        command_name=command_name,
        include_context=include_context,
        include_max_lines=include_max_lines,
    )
    if error:
        return error
    if uses_named_options:
        return commands[getter_name](symbol=symbol, path=path, **kwargs)
    return commands[getter_name](argument=command.argument)


SIMPLE_CODE_INTEL_COMMANDS: dict[str, str] = {
    "python_check": "get_python_check_text",
    "python_rename_preview": "get_python_rename_preview_text",
    "python_rename": "get_python_rename_text",
    "check_replace_python_definition": "get_check_replace_python_definition_text",
    "replace_python_definition": "get_replace_python_definition_text",
    "code_deps": "get_code_deps_text",
    "code_rename_preview": "get_code_rename_preview_text",
    "code_rename": "get_code_rename_text",
}


def run_interactive_code_intel_command(command: Any, commands: dict[str, Any]) -> str | None:
    simple_getter = SIMPLE_CODE_INTEL_COMMANDS.get(command.type)
    if simple_getter is not None:
        return commands[simple_getter](argument=command.argument)
    if command.type == "python_deps":
        path, kwargs, error, uses_named_options = commands["parse_interactive_python_deps_argument"](command.argument)
        if error:
            return error
        if uses_named_options:
            return commands["get_python_deps_text"](argument=path, **kwargs)
        return commands["get_python_deps_text"](argument=command.argument)
    if command.type == "python_call_graph":
        path, kwargs, error, uses_named_options = commands["parse_interactive_python_call_graph_argument"](command.argument)
        if error:
            return error
        if uses_named_options:
            return commands["get_python_call_graph_text"](argument=path, **kwargs)
        return commands["get_python_call_graph_text"](argument=command.argument)
    if command.type == "python_defs":
        return _symbol_text(
            command,
            commands,
            "python-defs",
            "get_python_defs_text",
            include_max_lines=True,
        )
    if command.type == "python_refs":
        return _symbol_text(command, commands, "python-refs", "get_python_refs_text")
    if command.type == "python_ref_contexts":
        return _symbol_text(
            command,
            commands,
            "python-ref-contexts",
            "get_python_ref_contexts_text",
            include_context=True,
        )
    if command.type == "python_calls":
        return _symbol_text(command, commands, "python-calls", "get_python_calls_text")
    if command.type == "code_refs":
        return _symbol_text(command, commands, "code-refs", "get_code_refs_text")
    if command.type == "code_ref_contexts":
        return _symbol_text(
            command,
            commands,
            "code-ref-contexts",
            "get_code_ref_contexts_text",
            include_context=True,
        )
    if command.type == "code_defs":
        return _symbol_text(
            command,
            commands,
            "code-defs",
            "get_code_defs_text",
            include_max_lines=True,
        )
    return None
