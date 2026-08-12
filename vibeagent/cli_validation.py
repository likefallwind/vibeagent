from __future__ import annotations

import argparse

from .cli_local_flag_detection import has_local_flag, has_non_model_local_flag
from .cli_local_option_validation import validate_local_option_dependencies
from .cli_permission_overrides import has_permission_overrides, permission_override_validation_error
from .cli_resume_args import validate_resume_arguments
from .cli_tool_restrictions import parse_cli_tool_names
from .model_fallback import normalize_fallback_models
from .session_names import normalize_session_name


def validate_cli_args(args: argparse.Namespace) -> str | None:
    remote_control = getattr(args, "remote_control", False)
    remote_host = getattr(args, "remote_control_host", "127.0.0.1")
    remote_port = getattr(args, "remote_control_port", 0)
    remote_cert = getattr(args, "remote_control_cert", None)
    remote_key = getattr(args, "remote_control_key", None)
    compat_error = getattr(args, "compat_error", None)
    if compat_error is not None:
        return compat_error
    if args.safe_mode and args.bare:
        return "--safe-mode and --bare cannot be combined."
    if args.bare and args.setting_sources is not None:
        return "--bare does not load settings files; pass explicit settings with --settings."
    if args.safe_mode and (args.agent is not None or args.agents is not None):
        return "--safe-mode cannot be combined with --agent or --agents."
    if args.safe_mode and (args.mcp_config or args.strict_mcp_config):
        return "--safe-mode cannot be combined with --mcp-config or --strict-mcp-config."
    if args.safe_mode and args.permission_prompt_tool is not None:
        return "--safe-mode cannot be combined with --permission-prompt-tool."
    if args.safe_mode and (args.plugin_dir or args.plugin_url):
        return "--safe-mode cannot be combined with --plugin-dir or --plugin-url."
    if (args.plugin_dir or args.plugin_url) and (has_local_flag(args) or args.chat):
        return "--plugin-dir and --plugin-url require an interactive or one-shot coding session."
    if args.safe_mode and (args.maintenance or args.setup_trigger == "init"):
        return "--safe-mode cannot run custom Setup hooks through --init or --maintenance."
    if args.background and (not args.task or has_local_flag(args) or args.chat):
        return "--background requires a one-shot coding task."
    if args.background and args.task == ["-"]:
        return "--background cannot read task input from stdin."
    if args.background and args.no_session_persistence:
        return "--background requires session persistence."
    if args.background and args.api_key is not None:
        return "--background does not persist --api-key; configure the provider key in the environment."
    if args.permission_prompt_tool is not None and (
        (not args.print_mode and not args.background)
        or not args.task
        or has_local_flag(args)
        or args.chat
    ):
        return "--permission-prompt-tool requires a non-interactive coding task with --print or --background."
    if args.permission_prompt_tool is not None and not args.permission_prompt_tool.strip():
        return "--permission-prompt-tool cannot be empty."
    if args.permission_prompt_tool is not None and args.approval not in {"ask", "auto"}:
        return "--permission-prompt-tool requires --approval ask or auto."
    if args.agent_view:
        if args.task:
            return "agents/--agent-view cannot be combined with a task."
        if args.json or args.output_format != "text":
            return "agents/--agent-view requires interactive text output."
    if remote_control:
        if args.task:
            return "remote-control/--remote-control cannot be combined with a task."
        if args.json or args.output_format != "text":
            return "remote-control/--remote-control requires text output."
    elif any(
        value is not None
        for value in (remote_cert, remote_key)
    ) or remote_host != "127.0.0.1" or remote_port != 0:
        return "Remote Control host, port, and TLS options require --remote-control."
    if not 0 <= remote_port <= 65_535:
        return "--remote-control-port must be between 0 and 65535."
    if (remote_cert is None) != (remote_key is None):
        return "--remote-control-cert and --remote-control-key must be provided together."
    if args.attach_background_agent is not None:
        if args.task:
            return "--attach-background-agent cannot be combined with a task."
        if any(
            value is not None
            for value in (args.resume, args.session_id, args.compact, args.worktree, args.name)
        ) or args.continue_latest or args.fork_session:
            return (
                "--attach-background-agent cannot be combined with session selection, "
                "naming, forking, or worktree options."
            )
    if args.background_agent_log_max_chars > 100_000:
        return "--background-agent-log-max-chars cannot exceed 100000."
    if args.json_schema is not None and (
        not args.print_mode or not args.task or has_local_flag(args) or args.chat
    ):
        return "--json-schema requires a one-shot coding task with --print."
    if args.brief and (args.chat or has_local_flag(args)):
        return "--brief is available for coding sessions only."
    if args.max_budget_usd is not None and (
        not args.print_mode or not args.task or has_local_flag(args) or args.chat
    ):
        return "--max-budget-usd requires a one-shot coding task with --print."
    if args.fallback_model is not None and (
        not args.print_mode or not args.task or has_local_flag(args) or args.chat
    ):
        return "--fallback-model requires a one-shot coding task with --print."
    if args.fallback_model is not None:
        try:
            normalize_fallback_models(args.fallback_model)
        except ValueError as error:
            return str(error)
    if args.include_partial_messages and (
        not args.print_mode or args.output_format != "stream-json" or not args.task or has_local_flag(args)
    ):
        return "--include-partial-messages requires --print with --output-format stream-json."
    if args.include_hook_events and (
        not args.print_mode
        or args.output_format != "stream-json"
        or not args.task
        or args.chat
        or has_local_flag(args)
    ):
        return "--include-hook-events requires a one-shot coding task with --print and --output-format stream-json."
    if args.replay_user_messages and (
        not args.print_mode
        or args.input_format != "stream-json"
        or args.output_format != "stream-json"
        or args.task != ["-"]
        or args.chat
        or has_local_flag(args)
    ):
        return (
            "--replay-user-messages requires --print with --input-format stream-json, "
            "--output-format stream-json, task '-', and coding mode."
        )
    if args.forward_subagent_text and (
        not args.print_mode
        or args.output_format != "stream-json"
        or not args.task
        or args.chat
        or has_local_flag(args)
    ):
        return "--forward-subagent-text requires a one-shot coding task with --print and --output-format stream-json."
    if args.append_subagent_system_prompt is not None and not args.append_subagent_system_prompt.strip():
        return "--append-subagent-system-prompt cannot be empty."
    if args.append_subagent_system_prompt is not None and (
        not args.print_mode or not args.task or has_local_flag(args) or args.chat
    ):
        return "--append-subagent-system-prompt requires a one-shot coding task with --print."
    if args.maintenance and (
        not args.print_mode or not args.task or has_local_flag(args) or args.chat
    ):
        return "--maintenance requires a one-shot coding task with --print."
    if args.setup_trigger == "init" and args.chat:
        return "--init with --print is available for coding tasks only."
    if isinstance(args.tools, str):
        if not args.task or args.chat:
            return "--tools NAMES requires a one-shot coding task."
        try:
            parse_cli_tool_names(args.tools)
        except ValueError as error:
            return str(error)
    if args.print_mode and (not args.task or has_local_flag(args)):
        return "--print requires a one-shot task."
    if args.no_session_persistence and (not args.print_mode or not args.task or has_local_flag(args)):
        return "--no-session-persistence requires a one-shot task with --print."
    if args.no_session_persistence and args.name is not None:
        return "--no-session-persistence cannot be combined with --name."
    if args.no_session_persistence and args.fork_session:
        return "--no-session-persistence cannot be combined with --fork-session."
    if args.no_session_persistence and args.worktree is not None:
        return "--no-session-persistence cannot be combined with --worktree."
    if args.model is True and has_non_model_local_flag(args):
        return "--model cannot be combined with other local command flags unless a MODEL value is provided."
    if isinstance(args.model, str) and not args.task and not args.save_config and not has_non_model_local_flag(args):
        return "--model MODEL requires a one-shot task or --save-config."
    if args.dangerously_skip_permissions and (not args.task or has_local_flag(args) or args.chat):
        return "--dangerously-skip-permissions requires a one-shot coding task."
    if args.no_auto_compact and (not args.task or has_local_flag(args) or args.chat):
        return "--no-auto-compact requires a one-shot coding task."
    if args.worktree is not None and (has_local_flag(args) or args.chat):
        return "--worktree requires an interactive or one-shot coding session."
    if args.fork_session and (has_local_flag(args) or args.chat):
        return "--fork-session requires an interactive or one-shot coding session."
    if args.add_dir and (has_local_flag(args) or args.chat):
        return "--add-dir requires an interactive or one-shot coding session."
    if args.effort is not None and has_local_flag(args):
        return "--effort requires an interactive or one-shot session."
    if args.autocompact is not None and has_local_flag(args):
        return "--autocompact requires an interactive or one-shot session."
    if any(not value.strip() for value in args.add_dir):
        return "--add-dir path cannot be empty."
    if args.add_dir and args.worktree is not None:
        return "--add-dir cannot be combined with --worktree."
    if args.agent is not None and (not args.agent.strip() or has_local_flag(args) or args.chat):
        return "--agent requires a non-empty interactive or one-shot coding profile."
    if args.name is not None and (not args.name.strip() or has_local_flag(args) or args.chat):
        return "--name requires a non-empty interactive or one-shot coding session name."
    if args.name is not None:
        try:
            normalize_session_name(args.name)
        except ValueError as error:
            return str(error)
    if args.worktree is not None and (
        args.resume is not None
        or args.session_id is not None
        or args.compact is not None
        or args.continue_latest
    ):
        return "--worktree cannot be combined with --resume, --session-id, --compact, or --continue."
    resume_error = validate_resume_arguments(args, local_selected=has_local_flag(args))
    if resume_error is not None:
        return resume_error
    if args.input_format in {"json", "stream-json"} and args.task != ["-"]:
        return f"--input-format {args.input_format} requires task '-' so input can be read from stdin."
    if args.mcp_config and (not args.task or has_local_flag(args)):
        return "--mcp-config requires a one-shot task."
    if args.strict_mcp_config and (not args.task or has_local_flag(args)):
        return "--strict-mcp-config requires a one-shot task."
    if args.system_prompt is not None and not args.system_prompt.strip():
        return "--system-prompt cannot be empty."
    if args.append_system_prompt is not None and not args.append_system_prompt.strip():
        return "--append-system-prompt cannot be empty."
    if args.system_prompt_file is not None and not args.system_prompt_file.strip():
        return "--system-prompt-file path cannot be empty."
    if args.append_system_prompt_file is not None and not args.append_system_prompt_file.strip():
        return "--append-system-prompt-file path cannot be empty."
    if args.system_prompt is not None and args.system_prompt_file is not None:
        return "--system-prompt cannot be combined with --system-prompt-file."
    prompt_inputs = (
        args.system_prompt,
        args.system_prompt_file,
        args.append_system_prompt,
        args.append_system_prompt_file,
    )
    if any(value is not None for value in prompt_inputs) and has_local_flag(args):
        return "System prompt options require an interactive or one-shot session."
    if args.output_format == "stream-json" and (not args.task or has_local_flag(args)):
        return "--output-format stream-json requires a one-shot task."
    override_error = permission_override_validation_error(args)
    if override_error is not None:
        return override_error
    if has_permission_overrides(args) and (not args.task or has_local_flag(args) or args.chat):
        return "permission overrides can only be used with one-shot coding tasks."
    dependency_error = validate_local_option_dependencies(args)
    if dependency_error is not None:
        return dependency_error
    return None
