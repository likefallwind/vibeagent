from __future__ import annotations

import argparse
from typing import Callable


IntParser = Callable[[str], int]


def add_edit_local_arguments(local: argparse._MutuallyExclusiveGroup) -> None:
    local.add_argument("--config-check", nargs="?", const="", metavar="PATH", help="Check JSON/YAML/TOML config syntax and exit.")
    local.add_argument("--check-json-set", nargs=3, metavar=("PATH", "POINTER", "JSON_VALUE"), help="Preview updating one JSON value and exit.")
    local.add_argument("--json-set", nargs=3, metavar=("PATH", "POINTER", "JSON_VALUE"), help="Update one JSON value and exit.")
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


def add_edit_option_arguments(
    parser: argparse.ArgumentParser,
    *,
    nonnegative_int: IntParser,
    positive_int: IntParser,
) -> None:
    parser.add_argument("--json-create-missing", action="store_true", help="Create missing JSON object parents with --check-json-set or --json-set.")
    parser.add_argument("--regex-count", type=nonnegative_int, default=0, metavar="N", help="Maximum replacements for --check-regex-replace or --regex-replace. Use 0 for all.")
    parser.add_argument("--regex-max-replacements", type=positive_int, default=100, metavar="N", help="Safety cap for --check-regex-replace or --regex-replace.")
    parser.add_argument("--regex-ignore-case", action="store_true", help="Use case-insensitive matching with --check-regex-replace or --regex-replace.")
    parser.add_argument("--regex-multiline", action="store_true", help="Let ^ and $ match line boundaries with --check-regex-replace or --regex-replace.")
