from __future__ import annotations

import argparse
from pathlib import Path
import shlex
from typing import Any

from .cli_parse_tool_search import parse_interactive_tool_search_argument
from .cli_local_result import local_text_or_report
from .tool_search_options import tool_search_approval_filter


def build_check_suggested_kwargs(args: argparse.Namespace) -> dict[str, object]:
    return {
        "argument": args.check_suggested_checks or None,
        "max_checks": args.check_suggested_checks_max,
    }


def build_run_suggested_kwargs(args: argparse.Namespace) -> dict[str, object]:
    return {
        "argument": args.run_suggested_checks or None,
        "max_checks": args.run_suggested_checks_max,
        "timeout_ms": args.run_timeout_ms,
        "max_output_chars": args.run_max_chars,
        "stop_on_failure": not args.run_continue_on_failure,
        "extract_output_contexts": args.run_output_contexts,
        "extract_output_diagnostics": args.run_output_diagnostics,
        "context_lines": args.run_output_context_lines,
        "max_diagnostics": args.run_output_diagnostic_max,
        "max_contexts": args.run_output_context_max,
        "max_bytes_per_context": args.run_output_context_max_bytes,
    }


def kwargs_without_argument(kwargs: dict[str, object]) -> dict[str, object]:
    return {key: value for key, value in kwargs.items() if key != "argument"}


def run_project_local_flag(
    args: argparse.Namespace,
    project_root: Path | None,
    config_root: Path,
    provider_env: dict[str, str],
    commands: dict[str, Any],
) -> tuple[str, dict[str, object]] | None:
    root = project_root or "."
    if args.model is True:
        return local_text_or_report(
            args,
            "model",
            lambda: commands["get_model_report"](provider_env),
            commands["format_model_report_text"],
            lambda: commands["get_model_text"](provider_env),
        )
    if args.config:
        config_kwargs = {
            "max_iterations": args.max_iterations,
            "command_timeout_ms": args.command_timeout_ms,
            "max_output_tokens": args.max_output_tokens,
            "model_retries": args.model_retries,
            "model_retry_delay_ms": args.model_retry_delay_ms,
            "model_timeout_ms": args.model_timeout_ms,
        }
        return local_text_or_report(
            args,
            "config",
            lambda: commands["get_config_report"](config_root, provider_env, **config_kwargs),
            commands["format_config_report_text"],
            lambda: commands["get_config_text"](config_root, provider_env, **config_kwargs),
        )
    if args.tools:
        return local_text_or_report(
            args,
            "tools",
            commands["get_tools_report"],
            commands["format_tools_report_text"],
            commands["get_tools_text"],
        )
    if args.tool is not None:
        return local_text_or_report(
            args,
            "tool",
            lambda: commands["get_tool_report"](args.tool),
            commands["format_tool_report_text"],
            lambda: commands["get_tool_text"](args.tool),
        )
    if args.tool_search is not None:
        approval_required = tool_search_approval_filter(args.tool_search_approval)
        return local_text_or_report(
            args,
            "toolSearch",
            lambda: commands["get_tool_search_report"](
                args.tool_search,
                max_matches=args.tool_search_max,
                category=args.tool_search_category,
                approval_required=approval_required,
            ),
            commands["format_tool_search_report_text"],
            lambda: commands["get_tool_search_text"](
                args.tool_search,
                max_matches=args.tool_search_max,
                category=args.tool_search_category,
                approval_required=approval_required,
            ),
        )
    if args.permissions:
        return local_text_or_report(
            args,
            "permissions",
            lambda: commands["get_permissions_report"](args.approval, root),
            commands["format_permissions_report_text"],
            lambda: commands["get_permissions_text"](args.approval, root),
        )
    if args.sandbox_status:
        return local_text_or_report(
            args,
            "sandbox",
            lambda: commands["get_sandbox_report"](root),
            commands["format_sandbox_report_text"],
            lambda: commands["get_sandbox_text"](root),
        )
    if args.trust_status:
        return local_text_or_report(
            args,
            "projectTrust",
            lambda: commands["get_project_trust_report"](root),
            commands["format_project_trust_report_text"],
            lambda: commands["get_project_trust_text"](root),
        )
    if args.trust_project:
        return local_text_or_report(
            args,
            "projectTrust",
            lambda: commands["get_trust_project_report"](root),
            commands["format_project_trust_report_text"],
            lambda: commands["get_trust_project_text"](root),
        )
    if args.untrust_project:
        return local_text_or_report(
            args,
            "projectTrust",
            lambda: commands["get_untrust_project_report"](root),
            commands["format_project_trust_report_text"],
            lambda: commands["get_untrust_project_text"](root),
        )
    if args.checks:
        return local_text_or_report(
            args,
            "checks",
            lambda: commands["get_checks_report"](root, max_checks=args.checks_max),
            commands["format_checks_report_text"],
            lambda: commands["get_checks_text"](root, max_checks=args.checks_max),
        )
    if args.check_suggested_checks is not None:
        check_suggested_kwargs = build_check_suggested_kwargs(args)
        return local_text_or_report(
            args,
            "checkSuggestedChecks",
            lambda: commands["get_check_suggested_checks_report"](root, **check_suggested_kwargs),
            commands["format_check_suggested_checks_report_text"],
            lambda: commands["get_check_suggested_checks_text"](
                root,
                check_suggested_kwargs["argument"],
                **kwargs_without_argument(check_suggested_kwargs),
            ),
        )
    if args.run_suggested_checks is not None:
        run_suggested_kwargs = build_run_suggested_kwargs(args)
        return local_text_or_report(
            args,
            "runSuggestedChecks",
            lambda: commands["get_run_suggested_checks_report"](root, **run_suggested_kwargs),
            commands["format_run_suggested_checks_report_text"],
            lambda: commands["get_run_suggested_checks_text"](
                root,
                run_suggested_kwargs["argument"],
                **kwargs_without_argument(run_suggested_kwargs),
            ),
        )
    if args.commands:
        commands_kwargs = {}
        if args.commands_max_commands is not None:
            commands_kwargs["max_commands"] = args.commands_max_commands
        if args.commands_max_files is not None:
            commands_kwargs["max_files"] = args.commands_max_files
        return local_text_or_report(
            args,
            "projectCommands",
            lambda: commands["get_commands_report"](root, **commands_kwargs),
            commands["format_commands_report_text"],
            lambda: commands["get_commands_text"](root, **commands_kwargs),
        )
    if args.related_tests is not None:
        related_kwargs = {}
        if args.related_tests_max_paths is not None:
            related_kwargs["max_paths"] = args.related_tests_max_paths
        if args.related_tests_max_candidates is not None:
            related_kwargs["max_candidates"] = args.related_tests_max_candidates
        related_argument = shlex.join(args.related_tests) if args.related_tests else None
        return local_text_or_report(
            args,
            "relatedTests",
            lambda: commands["get_related_tests_report"](root, argument=related_argument, **related_kwargs),
            commands["format_related_tests_report_text"],
            lambda: commands["get_related_tests_text"](root, related_argument, **related_kwargs),
        )
    if args.focused_tests is not None:
        focused_kwargs = commands["build_focused_tests_kwargs"](args)
        focused_kwargs["argument"] = shlex.join(args.focused_tests) if args.focused_tests else None
        return local_text_or_report(
            args,
            "focusedTests",
            lambda: commands["get_focused_test_commands_report"](root, **focused_kwargs),
            commands["format_focused_test_commands_report_text"],
            lambda: commands["get_focused_test_commands_text"](
                root,
                focused_kwargs["argument"],
                **kwargs_without_argument(focused_kwargs),
            ),
        )
    if args.check_focused_tests is not None:
        focused_kwargs = commands["build_focused_tests_kwargs"](args)
        focused_kwargs["argument"] = shlex.join(args.check_focused_tests) if args.check_focused_tests else None
        return local_text_or_report(
            args,
            "checkFocusedTests",
            lambda: commands["get_check_focused_test_commands_report"](root, **focused_kwargs),
            commands["format_check_focused_test_commands_report_text"],
            lambda: commands["get_check_focused_test_commands_text"](
                root,
                focused_kwargs["argument"],
                **kwargs_without_argument(focused_kwargs),
            ),
        )
    if args.run_focused_tests is not None:
        focused_kwargs = commands["build_focused_tests_kwargs"](args)
        focused_kwargs.update(
            {
                "argument": shlex.join(args.run_focused_tests) if args.run_focused_tests else None,
                "timeout_ms": args.run_timeout_ms,
                "max_output_chars": args.run_max_chars,
                "stop_on_failure": not args.run_continue_on_failure,
                "extract_output_contexts": args.run_output_contexts,
                "extract_output_diagnostics": args.run_output_diagnostics,
                "context_lines": args.run_output_context_lines,
                "max_diagnostics": args.run_output_diagnostic_max,
                "max_contexts": args.run_output_context_max,
                "max_bytes_per_context": args.run_output_context_max_bytes,
            }
        )
        return local_text_or_report(
            args,
            "runFocusedTests",
            lambda: commands["get_run_focused_test_commands_report"](root, **focused_kwargs),
            commands["format_run_focused_test_commands_report_text"],
            lambda: commands["get_run_focused_test_commands_text"](
                root,
                focused_kwargs["argument"],
                **kwargs_without_argument(focused_kwargs),
            ),
        )
    if args.manifests:
        manifests_kwargs = {}
        if args.manifests_max_files is not None:
            manifests_kwargs["max_files"] = args.manifests_max_files
        if args.manifests_max_items is not None:
            manifests_kwargs["max_items"] = args.manifests_max_items
        return local_text_or_report(
            args,
            "manifests",
            lambda: commands["get_manifests_report"](root, **manifests_kwargs),
            commands["format_manifests_report_text"],
            lambda: commands["get_manifests_text"](root, **manifests_kwargs),
        )
    if args.instructions:
        instructions_kwargs = {}
        if args.instructions_max_files is not None:
            instructions_kwargs["max_files"] = args.instructions_max_files
        if args.instructions_max_bytes is not None:
            instructions_kwargs["max_bytes"] = args.instructions_max_bytes
        return local_text_or_report(
            args,
            "instructions",
            lambda: commands["get_instructions_report"](root, **instructions_kwargs),
            commands["format_instructions_report_text"],
            lambda: commands["get_instructions_text"](root, **instructions_kwargs),
        )
    if args.todos is not None:
        todos_kwargs = {}
        if args.todos_max_items is not None:
            todos_kwargs["max_items"] = args.todos_max_items
        if args.todos_max_files is not None:
            todos_kwargs["max_files"] = args.todos_max_files
        todos_argument = args.todos or None
        return local_text_or_report(
            args,
            "todos",
            lambda: commands["get_todos_report"](root, path=todos_argument, **todos_kwargs),
            commands["format_todos_report_text"],
            lambda: commands["get_todos_text"](root, todos_argument, **todos_kwargs),
        )
    return None


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
) -> str | None:
    if command.type == "help":
        return commands["get_help_text"]()
    if command.type == "model":
        return commands["get_model_text"]()
    if command.type == "config":
        return commands["get_config_text"]()
    if command.type == "custom_commands":
        return commands["get_custom_commands_text"]()
    if command.type == "agents":
        return _option_limited_text(
            command,
            commands,
            "Usage: /agents [--max-agents N]",
            {"--max-agents": "max_agents"},
            "get_agents_text",
        )
    if command.type == "skills":
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
        kwargs, error, uses_named_options = commands["parse_interactive_instructions_argument"](command.argument)
        if error:
            return error
        return commands["get_instructions_text"](**kwargs) if uses_named_options else commands["get_instructions_text"]()
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
    system_prompt_set: bool = False,
    append_system_prompt_set: bool = False,
) -> str | None:
    if command.type == "status":
        return commands["get_status_text"](
            mode,
            approval_policy,
            resume_run_id,
            chat_turns=chat_turns,
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
