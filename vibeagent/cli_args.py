from __future__ import annotations

import argparse
from collections.abc import Sequence

from .cli_parse_core import nonnegative_int, positive_int, timeout_ms
from .cli_compat_args import add_compat_arguments, normalize_compat_arguments
from .cli_git_args import (
    add_git_diff_option_arguments,
    add_git_history_option_arguments,
    add_git_local_arguments,
)
from .cli_local_flag_detection import (
    LOCAL_FLAG_ARG_NAMES,
    has_local_flag as _has_local_flag,
)
from .cli_output_args import add_output_arguments, normalize_output_arguments
from .cli_one_shot_args import add_one_shot_arguments
from .cli_process_args import add_process_local_arguments, add_process_option_arguments
from .cli_project_args import (
    add_project_check_local_arguments,
    add_project_check_option_arguments,
    add_project_discovery_local_arguments,
    add_project_discovery_option_arguments,
)
from .cli_read_args import add_read_local_arguments, add_read_option_arguments
from .cli_runtime_args import (
    add_runtime_connection_option_arguments,
    add_runtime_local_arguments,
    add_runtime_network_local_arguments,
    add_runtime_run_option_arguments,
)
from .cli_session_args import add_session_limit_arguments, add_session_local_arguments
from .tool_categories import valid_tool_categories
from .tool_search_options import tool_search_approval_choices


def parse_args(argv: Sequence[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="vibeagent",
        description="Run VibeAgent interactively or execute one task.",
        allow_abbrev=False,
    )
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--chat", action="store_true", help="Run the one-shot task in daily conversation mode.")
    mode.add_argument("--code", action="store_true", help="Run the one-shot task in coding mode. This is the default.")
    local = parser.add_mutually_exclusive_group()
    parser.add_argument(
        "--model",
        nargs="?",
        const=True,
        metavar="MODEL",
        help="Show model provider configuration and exit, or set the model for a one-shot task when MODEL is provided.",
    )
    local.add_argument("--version", action="store_true", help="Show VibeAgent version and exit.")
    local.add_argument("--config", action="store_true", help="Show resolved provider and execution configuration and exit.")
    local.add_argument("--tools", action="store_true", help="Show model tool names by category and exit.")
    local.add_argument("--tool", metavar="NAME", help="Show one model tool's description and input schema and exit.")
    local.add_argument("--tool-search", metavar="QUERY", help="Search model tools by name, description, category, or input fields and exit.")
    parser.add_argument("--tool-search-max", type=positive_int, default=20, metavar="N", help="Maximum matching tools to show with --tool-search.")
    parser.add_argument(
        "--tool-search-category",
        choices=valid_tool_categories(),
        help="Optional category filter for --tool-search.",
    )
    parser.add_argument(
        "--tool-search-approval",
        choices=tool_search_approval_choices(),
        default="any",
        help="Optional approval filter for --tool-search.",
    )
    local.add_argument("--permissions", action="store_true", help="Show approval-gated tools and hard command blocks and exit.")
    local.add_argument("--sandbox-status", action="store_true", help="Show command sandbox configuration and availability and exit.")
    local.add_argument("--trust-status", action="store_true", help="Show persistent permission trust for the active project and exit.")
    local.add_argument("--trust-project", action="store_true", help="Persist trust in permission allow rules for the active project and exit.")
    local.add_argument("--untrust-project", action="store_true", help="Remove persistent permission trust for the active project and exit.")
    add_project_check_local_arguments(local)
    add_project_check_option_arguments(parser, positive_int=positive_int)
    add_runtime_local_arguments(local)
    add_runtime_network_local_arguments(local, positive_int=positive_int)
    add_project_discovery_local_arguments(local)
    add_read_local_arguments(local)
    local.add_argument("--python-check", nargs="?", const="", metavar="PATH", help="Check Python syntax and exit.")
    local.add_argument("--python-deps", nargs="?", const="", metavar="PATH", help="Inspect Python imports and dependencies and exit.")
    local.add_argument("--python-defs", metavar="SYMBOL", help="Find Python class/function definitions and exit.")
    local.add_argument("--python-refs", metavar="SYMBOL", help="Find Python definitions, imports, and references and exit.")
    local.add_argument("--python-ref-contexts", metavar="SYMBOL", help="Find Python references with surrounding context and exit.")
    local.add_argument("--python-calls", metavar="SYMBOL", help="Find Python call sites for a symbol and exit.")
    local.add_argument("--python-call-graph", nargs="?", const="", metavar="PATH", help="Inspect Python caller-to-callee edges and exit.")
    local.add_argument("--python-rename-preview", nargs=2, metavar=("SYMBOL", "NEW_NAME"), help="Preview a Python symbol rename and exit.")
    local.add_argument("--python-rename", nargs=2, metavar=("SYMBOL", "NEW_NAME"), help="Rename a Python symbol and exit.")
    local.add_argument("--check-replace-python-def", nargs=2, metavar=("SYMBOL", "CONTENT"), help="Preview replacing one Python class/function definition and exit.")
    local.add_argument("--replace-python-def", nargs=2, metavar=("SYMBOL", "CONTENT"), help="Replace one Python class/function definition and exit.")
    local.add_argument("--config-check", nargs="?", const="", metavar="PATH", help="Check JSON/YAML/TOML config syntax and exit.")
    local.add_argument("--check-json-set", nargs=3, metavar=("PATH", "POINTER", "JSON_VALUE"), help="Preview updating one JSON value and exit.")
    local.add_argument("--json-set", nargs=3, metavar=("PATH", "POINTER", "JSON_VALUE"), help="Update one JSON value and exit.")
    parser.add_argument("--json-create-missing", action="store_true", help="Create missing JSON object parents with --check-json-set or --json-set.")
    local.add_argument("--check-json-remove", nargs=2, metavar=("PATH", "POINTER"), help="Preview removing one JSON value and exit.")
    local.add_argument("--json-remove", nargs=2, metavar=("PATH", "POINTER"), help="Remove one JSON value and exit.")
    local.add_argument("--check-json-patch", nargs=2, metavar=("PATH", "JSON_OPS"), help="Preview JSON Patch operations and exit.")
    local.add_argument("--json-patch", nargs=2, metavar=("PATH", "JSON_OPS"), help="Apply JSON Patch operations and exit.")
    local.add_argument("--check-replace-lines", nargs=4, metavar=("PATH", "START", "END", "TEXT"), help="Preview replacing an inclusive line range and exit.")
    local.add_argument("--replace-lines", nargs=4, metavar=("PATH", "START", "END", "TEXT"), help="Replace an inclusive line range and exit.")
    local.add_argument("--check-insert-lines", nargs=3, metavar=("PATH", "LINE", "TEXT"), help="Preview inserting text before a line and exit.")
    local.add_argument("--insert-lines", nargs=3, metavar=("PATH", "LINE", "TEXT"), help="Insert text before a line and exit.")
    local.add_argument("--check-append", nargs=2, metavar=("PATH", "TEXT"), help="Preview appending text to one file and exit.")
    local.add_argument("--append", nargs=2, metavar=("PATH", "TEXT"), help="Append text to one file and exit.")
    local.add_argument("--check-write", nargs=2, metavar=("PATH", "TEXT"), help="Preview writing one file and exit.")
    local.add_argument("--write", nargs=2, metavar=("PATH", "TEXT"), help="Write one file and exit.")
    local.add_argument("--check-write-files", nargs="+", metavar="ARG", help="Preview writing multiple files and exit. Usage: --check-write-files PATH TEXT [PATH TEXT ...].")
    local.add_argument("--write-files", nargs="+", metavar="ARG", help="Write multiple files and exit. Usage: --write-files PATH TEXT [PATH TEXT ...].")
    local.add_argument("--check-edit", nargs=3, metavar=("PATH", "OLD", "NEW"), help="Preview replacing exact text in one file and exit.")
    local.add_argument("--edit", nargs=3, metavar=("PATH", "OLD", "NEW"), help="Replace exact text in one file and exit.")
    local.add_argument("--check-multi-edit", nargs="+", metavar="ARG", help="Preview multiple exact replacements in one file and exit. Usage: --check-multi-edit PATH OLD NEW [OLD NEW ...].")
    local.add_argument("--multi-edit", nargs="+", metavar="ARG", help="Apply multiple exact replacements in one file and exit. Usage: --multi-edit PATH OLD NEW [OLD NEW ...].")
    local.add_argument("--check-delete", metavar="PATH", help="Preview deleting one file and exit.")
    local.add_argument("--delete", metavar="PATH", help="Delete one file and exit.")
    local.add_argument("--check-delete-files", nargs="+", metavar="PATH", help="Preview deleting multiple files and exit.")
    local.add_argument("--delete-files", nargs="+", metavar="PATH", help="Delete multiple files and exit.")
    local.add_argument("--check-move", nargs=2, metavar=("SOURCE", "DESTINATION"), help="Preview moving one file and exit.")
    local.add_argument("--move", nargs=2, metavar=("SOURCE", "DESTINATION"), help="Move one file and exit.")
    local.add_argument("--check-move-files", nargs="+", metavar="ARG", help="Preview moving multiple files and exit. Usage: --check-move-files SOURCE DESTINATION [SOURCE DESTINATION ...].")
    local.add_argument("--move-files", nargs="+", metavar="ARG", help="Move multiple files and exit. Usage: --move-files SOURCE DESTINATION [SOURCE DESTINATION ...].")
    local.add_argument("--check-copy", nargs=2, metavar=("SOURCE", "DESTINATION"), help="Preview copying one file and exit.")
    local.add_argument("--copy", nargs=2, metavar=("SOURCE", "DESTINATION"), help="Copy one file and exit.")
    local.add_argument("--check-copy-files", nargs="+", metavar="ARG", help="Preview copying multiple files and exit. Usage: --check-copy-files SOURCE DESTINATION [SOURCE DESTINATION ...].")
    local.add_argument("--copy-files", nargs="+", metavar="ARG", help="Copy multiple files and exit. Usage: --copy-files SOURCE DESTINATION [SOURCE DESTINATION ...].")
    local.add_argument("--check-move-dir", nargs=2, metavar=("SOURCE", "DESTINATION"), help="Preview moving one directory and exit.")
    local.add_argument("--move-dir", nargs=2, metavar=("SOURCE", "DESTINATION"), help="Move one directory and exit.")
    local.add_argument("--check-move-dirs", nargs="+", metavar="ARG", help="Preview moving multiple directories and exit. Usage: --check-move-dirs SOURCE DESTINATION [SOURCE DESTINATION ...].")
    local.add_argument("--move-dirs", nargs="+", metavar="ARG", help="Move multiple directories and exit. Usage: --move-dirs SOURCE DESTINATION [SOURCE DESTINATION ...].")
    local.add_argument("--check-copy-dir", nargs=2, metavar=("SOURCE", "DESTINATION"), help="Preview copying one directory and exit.")
    local.add_argument("--copy-dir", nargs=2, metavar=("SOURCE", "DESTINATION"), help="Copy one directory and exit.")
    local.add_argument("--check-copy-dirs", nargs="+", metavar="ARG", help="Preview copying multiple directories and exit. Usage: --check-copy-dirs SOURCE DESTINATION [SOURCE DESTINATION ...].")
    local.add_argument("--copy-dirs", nargs="+", metavar="ARG", help="Copy multiple directories and exit. Usage: --copy-dirs SOURCE DESTINATION [SOURCE DESTINATION ...].")
    local.add_argument("--check-mkdir", metavar="PATH", help="Preview creating one directory and exit.")
    local.add_argument("--mkdir", metavar="PATH", help="Create one directory and exit.")
    local.add_argument("--check-mkdirs", nargs="+", metavar="PATH", help="Preview creating multiple directories and exit.")
    local.add_argument("--mkdirs", nargs="+", metavar="PATH", help="Create multiple directories and exit.")
    local.add_argument("--check-rmdir", metavar="PATH", help="Preview deleting one empty directory and exit.")
    local.add_argument("--rmdir", metavar="PATH", help="Delete one empty directory and exit.")
    local.add_argument("--check-rmdirs", nargs="+", metavar="PATH", help="Preview deleting multiple empty directories and exit.")
    local.add_argument("--rmdirs", nargs="+", metavar="PATH", help="Delete multiple empty directories and exit.")
    local.add_argument("--check-executable", nargs="+", metavar="ARG", help="Preview changing one file's executable bit and exit. Usage: --check-executable PATH [true|false].")
    local.add_argument("--set-executable", nargs="+", metavar="ARG", help="Change one file's executable bit and exit. Usage: --set-executable PATH [true|false].")
    local.add_argument("--check-patch", nargs=2, metavar=("PATH", "PATCH"), help="Preview applying one unified diff hunk to a file and exit. Use PATCH=- to read stdin.")
    local.add_argument("--patch", nargs=2, metavar=("PATH", "PATCH"), help="Apply one unified diff hunk to a file and exit. Use PATCH=- to read stdin.")
    local.add_argument("--check-patches", metavar="PATCH", help="Preview applying one unified diff across files and exit. Use PATCH=- to read stdin.")
    local.add_argument("--patches", metavar="PATCH", help="Apply one unified diff across files and exit. Use PATCH=- to read stdin.")
    local.add_argument("--check-regex-replace", nargs=3, metavar=("PATH", "PATTERN", "REPLACEMENT"), help="Preview a regex replacement and exit.")
    local.add_argument("--regex-replace", nargs=3, metavar=("PATH", "PATTERN", "REPLACEMENT"), help="Apply a regex replacement and exit.")
    local.add_argument("--code-deps", nargs="?", const="", metavar="PATH", help="Inspect non-Python source imports and dependencies and exit.")
    local.add_argument("--code-refs", metavar="SYMBOL", help="Find non-Python source references for a symbol and exit.")
    local.add_argument("--code-ref-contexts", metavar="SYMBOL", help="Find non-Python source references with surrounding context and exit.")
    local.add_argument("--code-defs", metavar="SYMBOL", help="Find non-Python source definitions for a symbol and exit.")
    local.add_argument("--code-rename-preview", nargs=2, metavar=("SYMBOL", "NEW_NAME"), help="Preview a non-Python source symbol or literal rename and exit.")
    local.add_argument("--code-rename", nargs=2, metavar=("SYMBOL", "NEW_NAME"), help="Rename a non-Python source symbol or literal and exit.")
    add_git_local_arguments(local)
    add_process_local_arguments(local)
    local.add_argument("--status", action="store_true", help="Show default non-interactive status and exit.")
    local.add_argument("--context", action="store_true", help="Show project context sources and exit.")
    local.add_argument("--init", nargs="?", const="AGENTS.md", metavar="FILE", help="Create a starter AGENTS.md or CLAUDE.md and exit.")
    local.add_argument("--doctor", action="store_true", help="Show local diagnostics and exit.")
    local.add_argument("--review", action="store_true", help="Review current git changes, syntax checks, and suggested commands and exit.")
    parser.add_argument("--review-max-files", type=positive_int, default=200, metavar="N", help="Maximum changed files to show with --review.")
    parser.add_argument("--review-max-checks", type=positive_int, default=5, metavar="N", help="Maximum suggested checks to show with --review.")
    local.add_argument("--handoff", action="store_true", help="Show final handoff review, checks, changed files, and latest plan and exit.")
    parser.add_argument("--handoff-max-files", type=positive_int, default=200, metavar="N", help="Maximum changed files to show with --handoff.")
    parser.add_argument("--handoff-max-checks", type=positive_int, default=10, metavar="N", help="Maximum suggested checks to show with --handoff.")
    parser.add_argument("--handoff-max-status-chars", type=positive_int, default=4_000, metavar="N", help="Maximum git status characters to show with --handoff.")
    parser.add_argument("--handoff-max-plan-chars", type=positive_int, default=4_000, metavar="N", help="Maximum latest-plan characters to show with --handoff.")
    local.add_argument("--changes", action="store_true", help="Show a structured changed-file summary and exit.")
    parser.add_argument("--changes-max-files", type=positive_int, default=200, metavar="N", help="Maximum changed files to show with --changes.")
    local.add_argument("--diff", nargs="?", const="", metavar="ARGS", help="Show current git diff. Optional ARGS: '--staged [path]' or '[path]'.")
    local.add_argument("--diff-hunks", nargs="?", const="", metavar="ARGS", help="Show structured git diff hunks. Optional ARGS: '--staged [path]' or '[path]'.")
    local.add_argument("--diff-contexts", nargs="?", const="", metavar="ARGS", help="Show source context around git diff hunks. Optional ARGS: '--staged [path]' or '[path]'.")
    add_git_diff_option_arguments(
        parser,
        positive_int=positive_int,
        nonnegative_int=nonnegative_int,
    )
    add_runtime_connection_option_arguments(
        parser,
        positive_int=positive_int,
        timeout_ms=timeout_ms,
    )
    add_project_discovery_option_arguments(
        parser,
        positive_int=positive_int,
        nonnegative_int=nonnegative_int,
    )
    parser.add_argument(
        "--python-path",
        metavar="PATH",
        help="Project-relative source scope for --python-defs, --python-refs, --python-ref-contexts, --python-calls, --python-rename, or --replace-python-def.",
    )
    parser.add_argument("--python-max-matches", type=positive_int, metavar="N", help="Maximum matches for --python-defs, --python-refs, --python-ref-contexts, or --python-calls.")
    parser.add_argument("--python-def-max-lines", type=positive_int, metavar="N", help="Maximum definition lines to show with --python-defs.")
    parser.add_argument("--python-context-lines", type=nonnegative_int, metavar="N", help="Surrounding source lines for --python-ref-contexts.")
    parser.add_argument("--python-context-max-bytes", type=positive_int, metavar="N", help="Maximum bytes per context with --python-ref-contexts.")
    parser.add_argument("--python-deps-max-files", type=positive_int, metavar="N", help="Maximum Python files to inspect with --python-deps.")
    parser.add_argument("--python-deps-max-imports", type=positive_int, metavar="N", help="Maximum imports to show with --python-deps.")
    parser.add_argument("--python-call-graph-max-files", type=positive_int, metavar="N", help="Maximum Python files to inspect with --python-call-graph.")
    parser.add_argument("--python-call-graph-max-edges", type=positive_int, metavar="N", help="Maximum call graph edges to show with --python-call-graph.")
    parser.add_argument("--code-path", metavar="PATH", help="Project-relative source scope for --code-refs, --code-ref-contexts, --code-defs, or --code-rename.")
    parser.add_argument("--code-max-matches", type=positive_int, metavar="N", help="Maximum matches for --code-refs, --code-ref-contexts, or --code-defs.")
    parser.add_argument("--code-def-max-lines", type=positive_int, metavar="N", help="Maximum definition lines to show with --code-defs.")
    parser.add_argument("--code-context-lines", type=nonnegative_int, metavar="N", help="Surrounding source lines for --code-ref-contexts.")
    parser.add_argument("--code-context-max-bytes", type=positive_int, metavar="N", help="Maximum bytes per context with --code-ref-contexts.")
    add_read_option_arguments(
        parser,
        positive_int=positive_int,
        nonnegative_int=nonnegative_int,
    )
    add_session_limit_arguments(
        parser,
        positive_int=positive_int,
        nonnegative_int=nonnegative_int,
    )
    add_git_history_option_arguments(parser, positive_int=positive_int)
    add_process_option_arguments(
        parser,
        positive_int=positive_int,
        nonnegative_int=nonnegative_int,
        timeout_ms=timeout_ms,
    )
    parser.add_argument("--regex-count", type=nonnegative_int, default=0, metavar="N", help="Maximum replacements for --check-regex-replace or --regex-replace. Use 0 for all.")
    parser.add_argument("--regex-max-replacements", type=positive_int, default=100, metavar="N", help="Safety cap for --check-regex-replace or --regex-replace.")
    parser.add_argument("--regex-ignore-case", action="store_true", help="Use case-insensitive matching with --check-regex-replace or --regex-replace.")
    parser.add_argument("--regex-multiline", action="store_true", help="Let ^ and $ match line boundaries with --check-regex-replace or --regex-replace.")
    add_runtime_run_option_arguments(
        parser,
        positive_int=positive_int,
        nonnegative_int=nonnegative_int,
        timeout_ms=timeout_ms,
    )
    add_session_local_arguments(parser, local)
    local.add_argument("--checkpoint", nargs="?", const="", metavar="LABEL", help="Save current git status, diffs, and ordinary untracked files as a local checkpoint and exit.")
    local.add_argument("--checkpoints", action="store_true", help="List saved local checkpoints and exit.")
    local.add_argument("--checkpoint-show", metavar="ID", help="Show one saved local checkpoint and exit.")
    local.add_argument("--checkpoint-diff", metavar="ID", help="Show saved staged and unstaged checkpoint patches and exit.")
    local.add_argument("--checkpoint-status", metavar="ID", help="Compare current git status and diffs with a saved checkpoint and exit.")
    local.add_argument("--check-checkpoint-restore", metavar="ID", help="Preview restoring tracked staged/unstaged changes and saved untracked files from a checkpoint and exit.")
    local.add_argument("--checkpoint-restore", metavar="ID", help="Restore tracked staged/unstaged changes and saved untracked files from a checkpoint and exit.")
    local.add_argument("--check-checkpoint-delete", metavar="ID", help="Preview deleting one saved local checkpoint and exit.")
    local.add_argument("--checkpoint-delete", metavar="ID", help="Delete one saved local checkpoint and exit.")
    local.add_argument("--check-checkpoint-prune", metavar="N", help="Preview deleting older checkpoints while keeping the newest N and exit.")
    local.add_argument("--checkpoint-prune", metavar="N", help="Delete older checkpoints while keeping the newest N and exit.")
    local.add_argument("--usage", action="store_true", help="Show local session usage and exit.")
    local.add_argument("--cost", action="store_true", help="Show configured cost estimate and exit.")
    local.add_argument("--save-config", action="store_true", help="Save non-secret provider defaults to .vibeagent/config.json and exit.")
    add_one_shot_arguments(
        parser,
        positive_int=positive_int,
        nonnegative_int=nonnegative_int,
        timeout_ms=timeout_ms,
    )
    add_output_arguments(parser)
    add_compat_arguments(parser, positive_int=positive_int)
    parser.add_argument("task", nargs="*", help="One-shot task text. Omit it to start the interactive prompt.")
    return normalize_output_arguments(normalize_compat_arguments(parser.parse_args(list(argv))))


def has_local_flag(args: argparse.Namespace) -> bool:
    return _has_local_flag(args)
