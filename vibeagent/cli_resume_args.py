from __future__ import annotations

import argparse


def normalize_resume_arguments(args: argparse.Namespace) -> argparse.Namespace:
    args.resume_from_continue = False
    if args.continue_latest and args.resume is None:
        args.resume = ""
        args.resume_from_continue = True
    return args


def validate_resume_arguments(args: argparse.Namespace, *, local_selected: bool) -> str | None:
    if (args.resume is not None or args.compact is not None or args.continue_latest) and local_selected:
        return "--resume, --compact, and --continue cannot be combined with local command flags."
    if args.no_auto_compact and (args.resume is not None or args.compact is not None or args.continue_latest):
        return "--no-auto-compact cannot be combined with --resume, --compact, or --continue."
    resume_context_selected = args.resume is not None or args.session_id is not None
    if resume_context_selected and args.compact is not None:
        return "--resume/--session-id and --compact cannot be used together."
    resume_limit_error = _validate_limit_options(
        {
            "--resume-max-failures": args.resume_max_failures,
            "--resume-max-files": args.resume_max_files,
            "--resume-max-commands": args.resume_max_commands,
            "--resume-max-checks": args.resume_max_checks,
            "--resume-max-output-chars": args.resume_max_output_chars,
            "--resume-max-text": args.resume_max_text,
        },
        selected=resume_context_selected,
        required="--resume or --session-id",
    )
    if resume_limit_error is not None:
        return resume_limit_error
    return _validate_limit_options(
        {
            "--compact-max-failures": args.compact_max_failures,
            "--compact-max-files": args.compact_max_files,
            "--compact-max-commands": args.compact_max_commands,
            "--compact-max-checks": args.compact_max_checks,
            "--compact-max-output-chars": args.compact_max_output_chars,
            "--compact-max-text": args.compact_max_text,
        },
        selected=args.compact is not None,
        required="--compact",
    )


def _validate_limit_options(
    options: dict[str, int | None],
    *,
    selected: bool,
    required: str,
) -> str | None:
    for option, value in options.items():
        if value is not None and not selected:
            return f"{option} can only be used with {required}."
    return None
