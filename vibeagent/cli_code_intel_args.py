from __future__ import annotations

import argparse
from typing import Callable


IntParser = Callable[[str], int]


def add_code_intel_local_arguments(local: argparse._MutuallyExclusiveGroup) -> None:
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
    local.add_argument("--code-deps", nargs="?", const="", metavar="PATH", help="Inspect non-Python source imports and dependencies and exit.")
    local.add_argument("--code-refs", metavar="SYMBOL", help="Find non-Python source references for a symbol and exit.")
    local.add_argument("--code-ref-contexts", metavar="SYMBOL", help="Find non-Python source references with surrounding context and exit.")
    local.add_argument("--code-defs", metavar="SYMBOL", help="Find non-Python source definitions for a symbol and exit.")
    local.add_argument("--code-rename-preview", nargs=2, metavar=("SYMBOL", "NEW_NAME"), help="Preview a non-Python source symbol or literal rename and exit.")
    local.add_argument("--code-rename", nargs=2, metavar=("SYMBOL", "NEW_NAME"), help="Rename a non-Python source symbol or literal and exit.")


def add_code_intel_option_arguments(
    parser: argparse.ArgumentParser,
    *,
    positive_int: IntParser,
    nonnegative_int: IntParser,
) -> None:
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
