from __future__ import annotations

from contextlib import contextmanager
from functools import lru_cache
import os
from pathlib import Path
import re
import sys
from typing import Any, Iterator

from .help_commands import get_help_text
from .workspace_paths import should_ignore_path


MAX_COMPLETION_PATHS = 5_000
MAX_COMPLETION_SCAN_ENTRIES = 20_000
MAX_COMPLETION_MATCHES = 100
SAFE_UNQUOTED_PATH = re.compile(r"[A-Za-z0-9_./+~-]+")
SLASH_COMMAND_PATTERN = re.compile(r"(?<!\S)(/[a-z][a-z0-9-]*)")


class InteractivePromptCompleter:
    def __init__(self, project_root: Path) -> None:
        self.project_root = project_root.resolve()
        self._paths: tuple[str, ...] | None = None
        self._last_text: str | None = None
        self._last_matches: tuple[str, ...] = ()

    def __call__(self, text: str, state: int) -> str | None:
        if state == 0 or text != self._last_text:
            self._last_text = text
            self._last_matches = self.matches(text)
        if state < 0 or state >= len(self._last_matches):
            return None
        return self._last_matches[state]

    def matches(self, text: str) -> tuple[str, ...]:
        if text.startswith("@"):
            return self._path_matches(text)
        if text.startswith("/"):
            return tuple(
                command
                for command in _slash_command_names()
                if command.startswith(text)
            )[:MAX_COMPLETION_MATCHES]
        return ()

    def _path_matches(self, text: str) -> tuple[str, ...]:
        quote = text[1:2] if text[1:2] in {"'", '"'} else ""
        typed_path = text[2:] if quote else text[1:]
        normalized = typed_path.replace("\\", "/")
        while normalized.startswith("./"):
            normalized = normalized[2:]
        needle = normalized.casefold()

        ranked: list[tuple[int, int, str]] = []
        for candidate in self.paths:
            folded = candidate.casefold()
            basename = candidate.rstrip("/").rsplit("/", 1)[-1].casefold()
            if folded.startswith(needle):
                rank = 0
            elif basename.startswith(needle):
                rank = 1
            elif needle and needle in folded:
                rank = 2
            else:
                continue
            ranked.append((rank, len(candidate), candidate))

        rendered = [
            _render_path_mention(candidate, preferred_quote=quote)
            for _, _, candidate in sorted(ranked)
        ]
        return tuple(candidate for candidate in rendered if candidate is not None)[
            :MAX_COMPLETION_MATCHES
        ]

    @property
    def paths(self) -> tuple[str, ...]:
        if self._paths is None:
            self._paths = list_safe_completion_paths(self.project_root)
        return self._paths


def list_safe_completion_paths(
    project_root: Path,
    *,
    max_paths: int = MAX_COMPLETION_PATHS,
    max_scan_entries: int = MAX_COMPLETION_SCAN_ENTRIES,
) -> tuple[str, ...]:
    if max_paths < 1 or max_scan_entries < 1:
        return ()
    root = project_root.resolve()
    if not root.is_dir():
        return ()

    candidates: set[str] = set()
    scanned = 0
    try:
        walker = os.walk(root, topdown=True, followlinks=False)
        for directory, directory_names, file_names in walker:
            current = Path(directory)
            retained_directories: list[str] = []
            for name in sorted(directory_names):
                scanned += 1
                path = current / name
                if scanned > max_scan_entries or len(candidates) >= max_paths:
                    break
                if path.is_symlink() or _ignored_path(root, path):
                    continue
                retained_directories.append(name)
                candidates.add(f"{path.relative_to(root).as_posix()}/")
            directory_names[:] = retained_directories
            if scanned > max_scan_entries or len(candidates) >= max_paths:
                break

            for name in sorted(file_names):
                scanned += 1
                path = current / name
                if scanned > max_scan_entries or len(candidates) >= max_paths:
                    break
                if path.is_symlink() or not path.is_file() or _ignored_path(root, path):
                    continue
                candidates.add(path.relative_to(root).as_posix())
            if scanned > max_scan_entries or len(candidates) >= max_paths:
                break
    except OSError:
        return tuple(sorted(candidates))
    return tuple(sorted(candidates))


@contextmanager
def interactive_prompt_completion(project_root: Path) -> Iterator[None]:
    readline = _terminal_readline()
    if readline is None:
        yield
        return

    previous_completer = readline.get_completer()
    previous_delimiters = readline.get_completer_delims()
    completer = InteractivePromptCompleter(project_root)
    try:
        readline.set_completer(completer)
        readline.set_completer_delims(" \t\n")
        binding = "bind ^I rl_complete" if "libedit" in str(readline.__doc__).lower() else "tab: complete"
        readline.parse_and_bind(binding)
        yield
    finally:
        readline.set_completer(previous_completer)
        readline.set_completer_delims(previous_delimiters)


def _ignored_path(root: Path, path: Path) -> bool:
    try:
        return should_ignore_path(root, path)
    except (OSError, ValueError):
        return True


def _render_path_mention(path: str, *, preferred_quote: str = "") -> str | None:
    suffix = "/" if path.endswith("/") else ""
    value = path.rstrip("/")
    if preferred_quote and preferred_quote not in value:
        return f"@{preferred_quote}{value}{suffix}{preferred_quote}"
    if SAFE_UNQUOTED_PATH.fullmatch(path):
        return f"@{path}"
    if '"' not in value:
        return f'@"{value}{suffix}"'
    if "'" not in value:
        return f"@'{value}{suffix}'"
    return None


@lru_cache(maxsize=1)
def _slash_command_names() -> tuple[str, ...]:
    return tuple(sorted(set(SLASH_COMMAND_PATTERN.findall(get_help_text()))))


def _terminal_readline() -> Any | None:
    try:
        if not sys.stdin.isatty():
            return None
        import readline
    except (ImportError, OSError):
        return None
    return readline


__all__ = [
    "InteractivePromptCompleter",
    "interactive_prompt_completion",
    "list_safe_completion_paths",
]
