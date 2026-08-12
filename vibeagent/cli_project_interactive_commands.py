from __future__ import annotations

from pathlib import Path
from typing import Any

from .cli_parse_tool_search import parse_interactive_tool_search_argument


def _option_limited_text(
    command: Any,
    commands: dict[str, Any],
    usage: str,
    option_map: dict[str, str],
    getter_name: str,
) -> str:
    kwargs, error, uses_named_options = commands["parse_interactive_option_limit_argument"](
        command.argument,
        usage,
        option_map,
    )
    if error:
        return error
    return commands[getter_name](**kwargs) if uses_named_options else commands[getter_name]()


def _test_paths_text(
    command: Any,
    commands: dict[str, Any],
    usage: str,
    getter_name: str,
    *,
    include_max_commands: bool = False,
) -> str:
    test_argument, kwargs, error, uses_named_options = commands["parse_interactive_test_paths_argument"](
        command.argument,
        usage,
        include_max_commands=include_max_commands,
    )
    if error:
        return error
    if uses_named_options:
        return commands[getter_name](argument=test_argument, **kwargs)
    return commands[getter_name](argument=command.argument)


def run_interactive_project_command(
    command: Any,
    commands: dict[str, Any],
    approval_policy: str,
    root: str | Path = ".",
    *,
    safe_mode: bool = False,
) -> str | None:
    if command.type == "help":
        return commands["get_help_text"]()
    if command.type == "config":
        return commands["get_config_text"]()
    if command.type == "custom_commands":
        return "Custom commands are disabled by safe mode." if safe_mode else commands["get_custom_commands_text"]()
    if command.type == "agents":
        if safe_mode:
            return "Custom agents are disabled by safe mode."
        return _option_limited_text(
            command,
            commands,
            "Usage: /agents [--max-agents N]",
            {"--max-agents": "max_agents"},
            "get_agents_text",
        )
    if command.type == "skills":
        if safe_mode:
            return "Custom skills are disabled by safe mode."
        return _option_limited_text(
            command,
            commands,
            "Usage: /skills [--max-skills N]",
            {"--max-skills": "max_skills"},
            "get_skills_text",
        )
    if command.type == "tools":
        return commands["get_tools_text"]()
    if command.type == "tool":
        return commands["get_tool_text"](command.argument)
    if command.type == "tool_search":
        query, kwargs, error = parse_interactive_tool_search_argument(command.argument)
        if error:
            return error
        return commands["get_tool_search_text"](query, **kwargs)
    if command.type == "permissions":
        return commands["get_permissions_text"](approval_policy, root)
    if command.type == "sandbox":
        return commands["get_sandbox_text"](root)
    if command.type == "checks":
        return _option_limited_text(
            command,
            commands,
            "Usage: /checks [--max-checks N]",
            {"--max-checks": "max_checks"},
            "get_checks_text",
        )
    if command.type == "check_suggested_checks":
        if command.argument and command.argument.strip().startswith("--"):
            return _option_limited_text(
                command,
                commands,
                "Usage: /check-suggested-checks [--max-checks N]",
                {"--max-checks": "max_checks"},
                "get_check_suggested_checks_text",
            )
        return commands["get_check_suggested_checks_text"](argument=command.argument)
    if command.type == "run_suggested_checks":
        suggested_argument, kwargs, error, uses_named_options = commands["parse_interactive_run_suggested_checks_argument"](
            command.argument
        )
        if error:
            return error
        if uses_named_options:
            return commands["get_run_suggested_checks_text"](argument=suggested_argument, **kwargs)
        return commands["get_run_suggested_checks_text"](argument=command.argument)
    if command.type == "commands":
        kwargs, error, uses_named_options = commands["parse_interactive_commands_argument"](command.argument)
        if error:
            return error
        return commands["get_commands_text"](**kwargs) if uses_named_options else commands["get_commands_text"]()
    if command.type == "related_tests":
        return _test_paths_text(
            command,
            commands,
            "Usage: /related-tests [--max-paths N] [--max-candidates N] -- [path...]",
            "get_related_tests_text",
        )
    if command.type == "focused_test_commands":
        return _test_paths_text(
            command,
            commands,
            "Usage: /focused-tests [--max-paths N] [--max-candidates N] [--max-commands N] -- [path...]",
            "get_focused_test_commands_text",
            include_max_commands=True,
        )
    if command.type == "check_focused_test_commands":
        return _test_paths_text(
            command,
            commands,
            "Usage: /check-focused-tests [--max-paths N] [--max-candidates N] [--max-commands N] -- [path...]",
            "get_check_focused_test_commands_text",
            include_max_commands=True,
        )
    if command.type == "run_focused_test_commands":
        focused_argument, kwargs, error, uses_named_options = commands["parse_interactive_run_focused_tests_argument"](
            command.argument
        )
        if error:
            return error
        if uses_named_options:
            return commands["get_run_focused_test_commands_text"](argument=focused_argument, **kwargs)
        return commands["get_run_focused_test_commands_text"](
            argument=command.argument,
            timeout_ms=30_000,
            max_output_chars=12_000,
        )
    if command.type == "manifests":
        kwargs, error, uses_named_options = commands["parse_interactive_manifests_argument"](command.argument)
        if error:
            return error
        return commands["get_manifests_text"](**kwargs) if uses_named_options else commands["get_manifests_text"]()
    if command.type == "instructions":
        if safe_mode:
            return "Project instructions are disabled by safe mode."
        kwargs, error, uses_named_options = commands["parse_interactive_instructions_argument"](command.argument)
        if error:
            return error
        return commands["get_instructions_text"](**kwargs) if uses_named_options else commands["get_instructions_text"]()
    if command.type == "hooks":
        return "Custom hooks are disabled by safe mode." if safe_mode else commands["get_hooks_text"]()
    if command.type == "todos":
        path, kwargs, error, uses_named_options = commands["parse_interactive_todos_argument"](command.argument)
        if error:
            return error
        return commands["get_todos_text"](path=path, **kwargs) if uses_named_options else commands["get_todos_text"](
            path=command.argument
        )
    return None


def run_interactive_project_state_command(
    command: Any,
    commands: dict[str, Any],
    *,
    mode: str,
    approval_policy: str,
    resume_run_id: str | None,
    resume_context: str | None,
    chat_turns: int,
    effort: str = "auto",
    autocompact: str = "auto",
    system_prompt_set: bool = False,
    append_system_prompt_set: bool = False,
) -> str | None:
    if command.type == "status":
        return commands["get_status_text"](
            mode,
            approval_policy,
            resume_run_id,
            chat_turns=chat_turns,
            effort=effort,
            autocompact=autocompact,
            system_prompt_set=system_prompt_set,
            append_system_prompt_set=append_system_prompt_set,
        )
    if command.type == "context":
        return commands["get_context_text"](resume_run_id=resume_run_id, resume_context=resume_context)
    if command.type == "init":
        return commands["init_project_instructions"](file_name=command.argument)
    if command.type == "doctor":
        return commands["get_doctor_text"]()
    return None
