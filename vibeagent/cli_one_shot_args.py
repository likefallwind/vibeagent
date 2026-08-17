from __future__ import annotations

import argparse

from .cli_permission_overrides import add_permission_override_arguments


def add_one_shot_arguments(
    parser: argparse.ArgumentParser,
    *,
    positive_int,
    nonnegative_int,
    timeout_ms,
    autocompact_tokens,
) -> None:
    parser.add_argument(
        "--approval",
        choices=("ask", "allow", "auto", "deny", "dontAsk", "plan"),
        help="Approval policy for one-shot coding tasks; auto classifies side effects, dontAsk never prompts, and plan exposes read-only tools only.",
    )
    parser.add_argument(
        "--agent",
        metavar="PROFILE",
        help="Run coding turns with an exact project or plugin main agent profile.",
    )
    parser.add_argument(
        "--agents",
        metavar="JSON",
        help="Define invocation-scoped subagent profiles as a JSON object keyed by agent name.",
    )
    parser.add_argument(
        "--name",
        "-n",
        metavar="NAME",
        help="Name the coding session so it can be resumed by name.",
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
    parser.add_argument(
        "--session-id",
        metavar="UUID",
        help="Use a specific UUID for a new coding session.",
    )
    parser.add_argument(
        "--from-pr",
        metavar="PR",
        help="Resume the newest local session linked to a PR number or GitHub, GitLab, or Bitbucket PR URL.",
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
    parser.add_argument(
        "--no-auto-compact",
        action="store_true",
        help="Disable automatic latest-session compact context when neither --resume nor --compact is provided.",
    )
    parser.add_argument("--compact-max-failures", type=positive_int, metavar="N", help="Maximum failure entries in --compact context.")
    parser.add_argument("--compact-max-files", type=positive_int, metavar="N", help="Maximum file references in --compact context.")
    parser.add_argument("--compact-max-commands", type=positive_int, metavar="N", help="Maximum command results in --compact context.")
    parser.add_argument("--compact-max-checks", type=positive_int, metavar="N", help="Maximum check rows per group in --compact context.")
    parser.add_argument("--compact-max-output-chars", type=nonnegative_int, metavar="N", help="Maximum stdout/stderr tail characters per command in --compact context.")
    parser.add_argument("--compact-max-text", type=positive_int, metavar="N", help="Maximum text characters per timeline, failure, or readiness entry in --compact context.")
    parser.add_argument("--cwd", help="Project directory for one-shot coding tasks.")
    parser.add_argument(
        "--file",
        action="extend",
        nargs="+",
        default=[],
        metavar="FILE_ID:PATH",
        help="Download Anthropic file resources into project-relative paths before startup.",
    )
    parser.add_argument(
        "--add-dir",
        action="append",
        default=[],
        metavar="PATH",
        help="Grant this coding session access to an additional directory; repeat for multiple directories.",
    )
    parser.add_argument(
        "--worktree",
        "-w",
        nargs="?",
        const="",
        metavar="NAME",
        help="Create an isolated git worktree, run this session there, and preserve it after exit.",
    )
    parser.add_argument(
        "--tmux",
        nargs="?",
        const="auto",
        choices=("auto", "classic"),
        metavar="MODE",
        help="Run the worktree session in tmux; use --tmux=classic to disable terminal-native control mode.",
    )
    parser.add_argument(
        "--ide",
        action="store_true",
        help="Connect to the unique active VibeAgent VS Code workspace matching --cwd.",
    )
    parser.add_argument(
        "--teammate-mode",
        choices=("in-process", "auto", "tmux", "iterm2"),
        help="Set agent-team teammate display mode for this session.",
    )
    parser.add_argument(
        "--provider",
        choices=("minimax", "anthropic", "deepseek", "openai-compatible"),
        help="Temporarily override the model provider for this command.",
    )
    parser.add_argument(
        "--model-name",
        help="Temporarily override the model name for this command. --model MODEL is also accepted.",
    )
    parser.add_argument(
        "--effort",
        choices=("auto", "low", "medium", "high", "xhigh", "max"),
        help="Set model effort for interactive or one-shot sessions; CLAUDE_CODE_EFFORT_LEVEL takes precedence.",
    )
    parser.add_argument(
        "--autocompact",
        type=autocompact_tokens,
        metavar="AUTO|TOKENS",
        help="Set automatic context compaction to auto or a 100k-1M token threshold.",
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
    parser.add_argument(
        "--strict-mcp-config",
        action="store_true",
        help="Use only --mcp-config files for this one-shot command, ignoring project .mcp.json.",
    )
    parser.add_argument("--system-prompt", help="Override the default system prompt for this session.")
    parser.add_argument(
        "--system-prompt-file",
        metavar="PATH",
        help="Read the replacement system prompt from a UTF-8 file.",
    )
    parser.add_argument(
        "--append-system-prompt",
        help="Append extra instructions to the default or overridden system prompt.",
    )
    parser.add_argument(
        "--append-system-prompt-file",
        metavar="PATH",
        help="Read additional system prompt instructions from a UTF-8 file.",
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
