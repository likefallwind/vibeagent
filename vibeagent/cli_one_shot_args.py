from __future__ import annotations

import argparse

from .cli_permission_overrides import add_permission_override_arguments


def add_one_shot_arguments(
    parser: argparse.ArgumentParser,
    *,
    positive_int,
    nonnegative_int,
    timeout_ms,
) -> None:
    parser.add_argument(
        "--approval",
        choices=("ask", "allow", "deny", "plan"),
        help="Approval policy for one-shot coding tasks; plan exposes read-only tools only.",
    )
    parser.add_argument(
        "--trust-project-permissions",
        action="store_true",
        help="Allow project permission allow rules to skip side-effect prompts for this one-shot run.",
    )
    add_permission_override_arguments(parser)
    parser.add_argument(
        "--resume",
        "-r",
        nargs="?",
        const="",
        metavar="RUN_ID",
        help="Load a previous session summary before a one-shot coding task. Omit RUN_ID to use the newest session.",
    )
    parser.add_argument("--resume-max-failures", type=positive_int, metavar="N", help="Maximum failure entries in --resume context.")
    parser.add_argument("--resume-max-files", type=positive_int, metavar="N", help="Maximum file references in --resume context.")
    parser.add_argument("--resume-max-commands", type=positive_int, metavar="N", help="Maximum command results in --resume context.")
    parser.add_argument("--resume-max-checks", type=positive_int, metavar="N", help="Maximum check rows per group in --resume context.")
    parser.add_argument("--resume-max-output-chars", type=nonnegative_int, metavar="N", help="Maximum stdout/stderr tail characters per command in --resume context.")
    parser.add_argument("--resume-max-text", type=positive_int, metavar="N", help="Maximum text characters per timeline, failure, or readiness entry in --resume context.")
    parser.add_argument(
        "--compact",
        nargs="?",
        const="",
        metavar="RUN_ID",
        help="Load a compact previous session handoff before a one-shot coding task. Omit RUN_ID to use the newest session.",
    )
    parser.add_argument("--compact-max-failures", type=positive_int, metavar="N", help="Maximum failure entries in --compact context.")
    parser.add_argument("--compact-max-files", type=positive_int, metavar="N", help="Maximum file references in --compact context.")
    parser.add_argument("--compact-max-commands", type=positive_int, metavar="N", help="Maximum command results in --compact context.")
    parser.add_argument("--compact-max-checks", type=positive_int, metavar="N", help="Maximum check rows per group in --compact context.")
    parser.add_argument("--compact-max-output-chars", type=nonnegative_int, metavar="N", help="Maximum stdout/stderr tail characters per command in --compact context.")
    parser.add_argument("--compact-max-text", type=positive_int, metavar="N", help="Maximum text characters per timeline, failure, or readiness entry in --compact context.")
    parser.add_argument("--cwd", help="Project directory for one-shot coding tasks.")
    parser.add_argument(
        "--provider",
        choices=("minimax", "deepseek", "openai-compatible"),
        help="Temporarily override the model provider for this command.",
    )
    parser.add_argument(
        "--model-name",
        help="Temporarily override the model name for this command. --model MODEL is also accepted.",
    )
    parser.add_argument("--base-url", help="Temporarily override the provider base URL for this command.")
    parser.add_argument("--api-key", help="Temporarily override the provider API key for this command.")
    parser.add_argument(
        "--mcp-config",
        action="append",
        default=[],
        metavar="PATH",
        help="Load an additional MCP configuration file for this one-shot command.",
    )
    parser.add_argument("--system-prompt", help="Override the default one-shot system prompt for this command.")
    parser.add_argument(
        "--append-system-prompt",
        help="Append extra instructions to the default or overridden one-shot system prompt.",
    )
    parser.add_argument(
        "--max-iterations",
        type=positive_int,
        help="Maximum model/tool iterations for one-shot coding tasks. Defaults to project config or 20.",
    )
    parser.add_argument(
        "--command-timeout-ms",
        type=timeout_ms,
        help="Default command timeout in milliseconds for one-shot coding tasks. Defaults to project config or 30000.",
    )
    parser.add_argument(
        "--max-output-tokens",
        type=positive_int,
        help="Maximum model output tokens per response. Defaults to project config or 4096.",
    )
    parser.add_argument(
        "--model-retries",
        type=nonnegative_int,
        help="Retry attempts after a provider request failure. Defaults to project config or 1.",
    )
    parser.add_argument(
        "--model-retry-delay-ms",
        type=nonnegative_int,
        help="Milliseconds to wait between provider retry attempts. Defaults to project config or 250.",
    )
    parser.add_argument(
        "--model-timeout-ms",
        type=timeout_ms,
        help="Provider request timeout in milliseconds. Defaults to project config or 120000.",
    )


__all__ = ["add_one_shot_arguments"]
