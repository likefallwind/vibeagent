from __future__ import annotations

from pathlib import Path
import re
import subprocess

from .workspace_core import GitCommandResult
from .workspace_paths import is_sensitive_project_path, path_matches_gitignore


def parse_git_remotes(output: str) -> list[dict[str, str]]:
    remotes: list[dict[str, str]] = []
    seen: set[tuple[str, str, str]] = set()
    for line in output.splitlines():
        parts = line.split()
        if len(parts) < 3:
            continue
        name = parts[0]
        url = redact_git_url(parts[1])
        kind = parts[2].strip("()")
        key = (name, url, kind)
        if key in seen:
            continue
        seen.add(key)
        remotes.append({"name": name, "url": url, "kind": kind})
    return remotes


def redact_git_url(url: str) -> str:
    return re.sub(r"(^[A-Za-z][A-Za-z0-9+.-]*://)([^/@\s]+@)", r"\1***@", url)


def redact_git_text(value: str) -> str:
    return "\n".join(redact_git_url(part) for part in value.splitlines())


def combine_git_output(result: GitCommandResult) -> str:
    output = "\n".join(part for part in [result.stdout.strip(), result.stderr.strip()] if part)
    return output


def empty_git_change(path: str) -> dict[str, object]:
    return {
        "path": path,
        "status": "",
        "staged": False,
        "unstaged": False,
        "untracked": False,
        "staged_insertions": 0,
        "staged_deletions": 0,
        "unstaged_insertions": 0,
        "unstaged_deletions": 0,
        "binary": False,
    }


def should_ignore_git_path(root: Path, path: str) -> bool:
    normalized = path.rstrip("/") or path
    candidate = Path(normalized)
    if candidate.is_absolute() or ".." in candidate.parts:
        return True
    relative_parts = candidate.parts
    hard_ignored = {
        ".agents",
        ".codex",
        ".git",
        ".pytest_cache",
        ".venv",
        ".vibeagent",
        "__pycache__",
        "build",
        "dist",
        "node_modules",
    }
    if any(part in hard_ignored or part.endswith(".egg-info") for part in relative_parts):
        return True
    root_path = root.resolve()
    lexical_path = root_path / candidate
    if is_sensitive_project_path(candidate, lexical_path.is_dir()):
        return True
    return path_matches_gitignore(root_path, candidate, lexical_path.is_dir())


def parse_git_short_status(output: str) -> list[tuple[str, str]]:
    entries: list[tuple[str, str]] = []
    for line in output.splitlines():
        if not line:
            continue
        status = line[:2]
        path = line[3:].strip() if len(line) > 3 else ""
        if " -> " in path:
            path = path.rsplit(" -> ", 1)[1]
        if path:
            entries.append((path, status))
    return entries


def parse_git_numstat(output: str) -> list[tuple[str, int, int, bool]]:
    entries: list[tuple[str, int, int, bool]] = []
    for line in output.splitlines():
        parts = line.split("\t")
        if len(parts) < 3:
            continue
        raw_insertions, raw_deletions, path = parts[0], parts[1], parts[-1]
        binary = raw_insertions == "-" or raw_deletions == "-"
        insertions = 0 if binary else int(raw_insertions)
        deletions = 0 if binary else int(raw_deletions)
        if " => " in path:
            path = path.rsplit(" => ", 1)[1].rstrip("}")
        entries.append((path, insertions, deletions, binary))
    return entries


def run_readonly_git(root: str | Path, args: list[str]) -> GitCommandResult:
    try:
        result = subprocess.run(
            ["git", *args],
            cwd=Path(root),
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=10,
            check=False,
        )
    except FileNotFoundError:
        return GitCommandResult(ok=False, stdout="", stderr="git executable was not found.", exit_code=None)
    except subprocess.TimeoutExpired:
        return GitCommandResult(ok=False, stdout="", stderr="git command timed out.", exit_code=None)

    return GitCommandResult(
        ok=result.returncode == 0,
        stdout=result.stdout or "",
        stderr=result.stderr or "",
        exit_code=result.returncode,
    )


def run_git_mutation(root: str | Path, args: list[str]) -> GitCommandResult:
    try:
        result = subprocess.run(
            ["git", *args],
            cwd=Path(root),
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=30,
            check=False,
        )
    except FileNotFoundError:
        return GitCommandResult(ok=False, stdout="", stderr="git executable was not found.", exit_code=None)
    except subprocess.TimeoutExpired:
        return GitCommandResult(ok=False, stdout="", stderr="git command timed out.", exit_code=None)

    return GitCommandResult(
        ok=result.returncode == 0,
        stdout=result.stdout or "",
        stderr=result.stderr or "",
        exit_code=result.returncode,
    )
