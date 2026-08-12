from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any

from .invocation_settings import parse_invocation_settings, parse_setting_sources
from .cli_local_result import local_text_or_report
from .cli_project_interactive_commands import (
    run_interactive_project_command,
    run_interactive_project_state_command,
)
from .cli_project_kwargs import (
    build_check_suggested_kwargs,
    build_config_kwargs,
    build_focused_tests_local_kwargs,
    build_instructions_kwargs,
    build_manifests_kwargs,
    build_project_commands_kwargs,
    build_related_tests_local_kwargs,
    build_run_focused_tests_kwargs,
    build_run_suggested_kwargs,
    build_todos_kwargs,
    build_tool_search_kwargs,
    kwargs_without_argument,
    kwargs_without_keys,
)


def run_project_local_flag(
    args: argparse.Namespace,
    project_root: Path | None,
    config_root: Path,
    provider_env: dict[str, str],
    commands: dict[str, Any],
) -> tuple[str, dict[str, object]] | None:
    root = project_root or "."
    if args.auto_mode_defaults:
        return local_text_or_report(
            args,
            "autoModeDefaults",
            lambda: commands["get_auto_mode_defaults_report"](
                label=args.auto_mode_label
            ),
            commands["format_auto_mode_report_text"],
            lambda: commands["format_auto_mode_report_text"](
                commands["get_auto_mode_defaults_report"](
                    label=args.auto_mode_label
                )
            ),
        )
    if args.auto_mode_config:
        config_kwargs = {
            "setting_sources": (
                () if args.bare else parse_setting_sources(args.setting_sources)
            ),
            "settings_override_json": parse_invocation_settings(
                args.settings, invocation_root=Path.cwd()
            ),
            "bare_mode": args.bare,
            "label": args.auto_mode_label,
        }
        return local_text_or_report(
            args,
            "autoModeConfig",
            lambda: commands["get_auto_mode_config_report"](
                root, **config_kwargs
            ),
            commands["format_auto_mode_report_text"],
            lambda: commands["format_auto_mode_report_text"](
                commands["get_auto_mode_config_report"](
                    root, **config_kwargs
                )
            ),
        )
    if args.auto_mode_critique:
        critique_kwargs = {
            "setting_sources": (
                () if args.bare else parse_setting_sources(args.setting_sources)
            ),
            "settings_override_json": parse_invocation_settings(
                args.settings, invocation_root=Path.cwd()
            ),
            "bare_mode": args.bare,
        }
        return local_text_or_report(
            args,
            "autoModeCritique",
            lambda: commands["get_auto_mode_critique_report"](
                root, provider_env, **critique_kwargs
            ),
            commands["format_auto_mode_critique_text"],
            lambda: commands["format_auto_mode_critique_text"](
                commands["get_auto_mode_critique_report"](
                    root, provider_env, **critique_kwargs
                )
            ),
        )
    if args.auto_mode_reset:
        report = commands["get_auto_mode_reset_report"](yes=args.auto_mode_yes)
        return (
            commands["format_auto_mode_reset_text"](report),
            {"autoModeReset": report} if args.json else {},
        )
    if args.model is True:
        return local_text_or_report(
            args,
            "model",
            lambda: commands["get_model_report"](provider_env),
            commands["format_model_report_text"],
            lambda: commands["get_model_text"](provider_env),
        )
    if args.config:
        config_kwargs = build_config_kwargs(args)
        return local_text_or_report(
            args,
            "config",
            lambda: commands["get_config_report"](config_root, provider_env, **config_kwargs),
            commands["format_config_report_text"],
            lambda: commands["get_config_text"](config_root, provider_env, **config_kwargs),
        )
    if args.tools is True:
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
        tool_search_kwargs = build_tool_search_kwargs(args)
        return local_text_or_report(
            args,
            "toolSearch",
            lambda: commands["get_tool_search_report"](
                args.tool_search,
                **tool_search_kwargs,
            ),
            commands["format_tool_search_report_text"],
            lambda: commands["get_tool_search_text"](
                args.tool_search,
                **tool_search_kwargs,
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
        commands_kwargs = build_project_commands_kwargs(args)
        return local_text_or_report(
            args,
            "projectCommands",
            lambda: commands["get_commands_report"](root, **commands_kwargs),
            commands["format_commands_report_text"],
            lambda: commands["get_commands_text"](root, **commands_kwargs),
        )
    if args.related_tests is not None:
        related_kwargs = build_related_tests_local_kwargs(args)
        return local_text_or_report(
            args,
            "relatedTests",
            lambda: commands["get_related_tests_report"](root, **related_kwargs),
            commands["format_related_tests_report_text"],
            lambda: commands["get_related_tests_text"](
                root,
                related_kwargs["argument"],
                **kwargs_without_argument(related_kwargs),
            ),
        )
    if args.focused_tests is not None:
        focused_kwargs = build_focused_tests_local_kwargs(args, args.focused_tests)
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
        focused_kwargs = build_focused_tests_local_kwargs(args, args.check_focused_tests)
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
        focused_kwargs = build_run_focused_tests_kwargs(args)
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
        manifests_kwargs = build_manifests_kwargs(args)
        return local_text_or_report(
            args,
            "manifests",
            lambda: commands["get_manifests_report"](root, **manifests_kwargs),
            commands["format_manifests_report_text"],
            lambda: commands["get_manifests_text"](root, **manifests_kwargs),
        )
    if args.instructions:
        instructions_kwargs = build_instructions_kwargs(args)
        return local_text_or_report(
            args,
            "instructions",
            lambda: commands["get_instructions_report"](root, **instructions_kwargs),
            commands["format_instructions_report_text"],
            lambda: commands["get_instructions_text"](root, **instructions_kwargs),
        )
    if args.hooks:
        return local_text_or_report(
            args,
            "hooks",
            lambda: commands["get_hooks_report"](root),
            commands["format_hooks_report_text"],
            lambda: commands["get_hooks_text"](root),
        )
    if args.todos is not None:
        todos_kwargs = build_todos_kwargs(args)
        return local_text_or_report(
            args,
            "todos",
            lambda: commands["get_todos_report"](root, **todos_kwargs),
            commands["format_todos_report_text"],
            lambda: commands["get_todos_text"](
                root,
                todos_kwargs["path"],
                **kwargs_without_keys(todos_kwargs, "path"),
            ),
        )
    return None
