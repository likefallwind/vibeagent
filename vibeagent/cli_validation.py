from __future__ import annotations

import argparse

from .cli_local_flag_detection import has_local_flag, has_non_model_local_flag
from .cli_local_option_validation import validate_local_option_dependencies
from .cli_permission_overrides import has_permission_overrides, permission_override_validation_error
from .cli_resume_args import validate_resume_arguments


def validate_cli_args(args: argparse.Namespace) -> str | None:
    compat_error = getattr(args, "compat_error", None)
    if compat_error is not None:
        return compat_error
    if args.print_mode and (not args.task or has_local_flag(args)):
        return "--print requires a one-shot task."
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
    if (args.system_prompt is not None or args.append_system_prompt is not None) and (not args.task or has_local_flag(args)):
        return "--system-prompt and --append-system-prompt require a one-shot task."
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
