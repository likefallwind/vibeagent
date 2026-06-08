from __future__ import annotations

import ast
import json
import re
import subprocess
import tomllib
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4


@dataclass(frozen=True)
class RunWorkspace:
    root: Path
    run_id: str
    session_dir: Path


@dataclass(frozen=True)
class GitCommandResult:
    ok: bool
    stdout: str
    stderr: str
    exit_code: int | None


def create_run_workspace(base_dir: str | Path | None = None, run_id: str | None = None) -> RunWorkspace:
    # Project mode: work in the caller's directory and store task logs under .vibeagent/sessions/.
    base = Path(base_dir) if base_dir is not None else Path.cwd()
    project_root = base.resolve()
    current_run_id = run_id or make_run_id()
    session_dir = (project_root / ".vibeagent" / "sessions" / current_run_id).resolve()
    session_dir.mkdir(parents=True, exist_ok=True)
    return RunWorkspace(root=project_root, run_id=current_run_id, session_dir=session_dir)


def resolve_inside_run(root: str | Path, relative_path: str) -> Path:
    # Enforce relative paths to prevent reads/writes outside the active project directory.
    if not relative_path or not relative_path.strip():
        raise ValueError("Path must not be empty.")

    candidate = Path(relative_path)
    if candidate.is_absolute():
        raise ValueError(f"Absolute paths are not allowed: {relative_path}")

    resolved_root = Path(root).resolve()
    resolved_path = (resolved_root / candidate).resolve()
    if resolved_path != resolved_root and resolved_root not in resolved_path.parents:
        raise ValueError(f"Path escapes the project directory: {relative_path}")
    if is_protected_project_path(resolved_root, resolved_path):
        raise ValueError(f"Path is protected: {relative_path}")

    return resolved_path


def resolve_command_cwd(workspace: RunWorkspace, relative_path: str | None) -> Path:
    target = resolve_inside_run(workspace.root, relative_path or ".")
    if not target.exists():
        raise ValueError(f"Command cwd does not exist: {relative_path or '.'}")
    if not target.is_dir():
        raise ValueError(f"Command cwd is not a directory: {relative_path or '.'}")
    return target


def write_run_file(workspace: RunWorkspace, relative_path: str, content: str) -> Path:
    # Resolve, mkdir for parent directories, then write UTF-8 text into the project folder.
    target = resolve_inside_run(workspace.root, relative_path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(content, encoding="utf-8")
    return target


def write_run_files(workspace: RunWorkspace, files: list[tuple[str, str]]) -> list[Path]:
    if not files:
        raise ValueError("At least one file is required.")
    if len(files) > 20:
        raise ValueError("write_files supports at most 20 files.")

    prepared: list[tuple[str, Path, str]] = []
    seen: set[Path] = set()
    for index, (relative_path, content) in enumerate(files, start=1):
        if not relative_path or not relative_path.strip():
            raise ValueError(f"File {index} path must not be empty.")
        target = resolve_inside_run(workspace.root, relative_path)
        if target in seen:
            raise ValueError(f"Duplicate file path: {relative_path}")
        if target.exists() and not target.is_file():
            raise ValueError(f"Path is not a file: {relative_path}")
        seen.add(target)
        prepared.append((relative_path, target, content))

    snapshots: list[tuple[Path, bool, str | None]] = []
    written: list[Path] = []
    try:
        for relative_path, target, content in prepared:
            try:
                previous = target.read_text(encoding="utf-8") if target.exists() else None
            except UnicodeDecodeError as error:
                raise ValueError(f"File is not valid UTF-8 text: {relative_path}") from error
            snapshots.append((target, target.exists(), previous))
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(content, encoding="utf-8")
            written.append(target)
    except OSError as error:
        for target, existed, previous in reversed(snapshots):
            try:
                if existed and previous is not None:
                    target.write_text(previous, encoding="utf-8")
                elif target.exists():
                    target.unlink()
            except OSError:
                pass
        raise ValueError(f"Failed to write files: {error}") from error

    return written


def read_workspace_snapshot(workspace: RunWorkspace, max_bytes: int = 12_000) -> str:
    # Build a bounded project file listing so prompts remain informative but not oversized.
    files = list_files(workspace.root)
    if not files:
        return "No project files found."

    used = 0
    chunks: list[str] = []
    for file in files[:120]:
        content = file
        remaining = max_bytes - used
        if remaining <= 0:
            chunks.append("\n[workspace snapshot truncated]")
            break

        shown = content[:remaining]
        used += len(shown)
        chunks.append(shown)

    return "\n\n".join(chunks)


def read_project_instructions(workspace: RunWorkspace, max_bytes: int = 12_000, max_files: int = 20) -> str | None:
    instruction_files = [file for file in list_files(workspace.root) if Path(file).name == "AGENTS.md"]
    if not instruction_files:
        return None

    chunks: list[str] = []
    for relative_path in instruction_files[:max_files]:
        instructions_path = workspace.root / relative_path
        content = instructions_path.read_text(encoding="utf-8")
        if not content.strip():
            continue
        scope = Path(relative_path).parent.as_posix()
        if scope == ".":
            scope = "."
        chunks.append(
            "\n".join(
                [
                    f"File: {relative_path}",
                    f"Scope: {scope}",
                    "Instructions:",
                    content,
                ]
            )
        )

    if not chunks:
        return None
    if len(instruction_files) > max_files:
        chunks.append(f"[{len(instruction_files) - max_files} additional AGENTS.md file(s) omitted]")

    combined = "\n\n".join(chunks)
    if len(combined) <= max_bytes:
        return combined
    return f"{combined[:max_bytes]}\n[AGENTS.md instructions truncated]"


def read_project_command_hints(workspace: RunWorkspace, max_bytes: int = 8_000, max_files: int = 30) -> str | None:
    command_files = [
        file
        for file in list_files(workspace.root)
        if Path(file).name in {"package.json", "pyproject.toml", "Makefile"}
    ]
    if not command_files:
        return None

    chunks: list[str] = []
    for relative_path in command_files[:max_files]:
        path = workspace.root / relative_path
        cwd = Path(relative_path).parent.as_posix()
        if cwd == ".":
            cwd = "."

        lines = [f"File: {relative_path}", f"Cwd: {cwd}"]
        if Path(relative_path).name == "package.json":
            scripts = read_package_json_scripts(path)
            if scripts:
                lines.extend(["package.json scripts:", *[f"- npm run {name}: {command}" for name, command in scripts]])
        elif Path(relative_path).name == "pyproject.toml":
            scripts = read_pyproject_scripts(path)
            if scripts:
                lines.extend(["pyproject.toml console scripts:", *[f"- {name}: {target}" for name, target in scripts]])
        elif Path(relative_path).name == "Makefile":
            targets = read_makefile_targets(path)
            if targets:
                lines.extend(["Makefile targets:", *[f"- make {target}" for target in targets]])
        if len(lines) > 2:
            chunks.append("\n".join(lines))

    if not chunks:
        return None
    if len(command_files) > max_files:
        chunks.append(f"[{len(command_files) - max_files} additional command metadata file(s) omitted]")

    combined = "\n\n".join(chunks)
    if len(combined) <= max_bytes:
        return combined
    return f"{combined[:max_bytes]}\n[project command hints truncated]"


def read_package_json_scripts(path: Path, max_scripts: int = 30) -> list[tuple[str, str]]:
    try:
        parsed = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return []
    scripts = parsed.get("scripts") if isinstance(parsed, dict) else None
    if not isinstance(scripts, dict):
        return []
    return sorted(
        (str(name), command)
        for name, command in scripts.items()
        if isinstance(name, str) and isinstance(command, str)
    )[:max_scripts]


def read_pyproject_scripts(path: Path, max_scripts: int = 30) -> list[tuple[str, str]]:
    try:
        parsed = tomllib.loads(path.read_text(encoding="utf-8"))
    except (OSError, tomllib.TOMLDecodeError):
        return []
    project = parsed.get("project") if isinstance(parsed, dict) else None
    scripts = project.get("scripts") if isinstance(project, dict) else None
    if not isinstance(scripts, dict):
        return []
    return sorted(
        (str(name), target)
        for name, target in scripts.items()
        if isinstance(name, str) and isinstance(target, str)
    )[:max_scripts]


def read_makefile_targets(path: Path, max_targets: int = 40) -> list[str]:
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError:
        return []
    targets: list[str] = []
    seen: set[str] = set()
    for line in lines:
        if line.startswith(("\t", " ", "#")):
            continue
        match = re.match(r"^([A-Za-z0-9][A-Za-z0-9_.-]*):(?:\s|$)", line)
        if not match:
            continue
        target = match.group(1)
        if "%" in target or target in seen:
            continue
        seen.add(target)
        targets.append(target)
        if len(targets) >= max_targets:
            break
    return targets


def list_files(root: str | Path) -> list[str]:
    # Enumerate all files in deterministic order so prompt diffs stay stable.
    root_path = Path(root).resolve()
    files = [
        path.relative_to(root_path).as_posix()
        for path in root_path.rglob("*")
        if path.is_file() and not should_ignore_path(root_path, path)
    ]
    return sorted(files)


def read_git_status(workspace: RunWorkspace) -> GitCommandResult:
    return run_readonly_git(workspace.root, ["status", "--short"])


def read_git_diff(workspace: RunWorkspace, relative_path: str | None = None, staged: bool = False) -> GitCommandResult:
    args = ["diff"]
    if staged:
        args.append("--cached")
    if relative_path:
        resolve_inside_run(workspace.root, relative_path)
        args.extend(["--", relative_path])
    return run_readonly_git(workspace.root, args)


def read_git_log(workspace: RunWorkspace, max_count: int = 5, relative_path: str | None = None) -> GitCommandResult:
    if max_count < 1:
        raise ValueError("max_count must be at least 1.")
    if max_count > 50:
        raise ValueError("max_count must be at most 50.")
    args = ["log", "--oneline", "--decorate", f"--max-count={max_count}"]
    if relative_path:
        resolve_inside_run(workspace.root, relative_path)
        args.extend(["--", relative_path])
    return run_readonly_git(workspace.root, args)


def read_git_show(workspace: RunWorkspace, rev: str = "HEAD", relative_path: str | None = None) -> GitCommandResult:
    rev = rev.strip()
    if not rev:
        raise ValueError("rev must be a non-empty string.")
    if rev.startswith("-"):
        raise ValueError("rev must not start with '-'.")
    args = ["show", "--stat", "--patch", "--format=fuller", "--no-ext-diff", rev]
    if relative_path:
        resolve_inside_run(workspace.root, relative_path)
        args.extend(["--", relative_path])
    return run_readonly_git(workspace.root, args)


def read_git_blame(
    workspace: RunWorkspace,
    relative_path: str,
    start_line: int | None = None,
    line_count: int | None = None,
) -> GitCommandResult:
    if not relative_path or not relative_path.strip():
        raise ValueError("path must be a non-empty string.")
    target = resolve_inside_run(workspace.root, relative_path)
    if not target.is_file():
        raise ValueError(f"Path is not a file: {relative_path}")
    if start_line is not None and start_line < 1:
        raise ValueError("start_line must be at least 1.")
    if line_count is not None and line_count < 1:
        raise ValueError("line_count must be at least 1.")
    if line_count is not None and line_count > 1000:
        raise ValueError("line_count must be at most 1000.")

    args = ["blame", "--date=short"]
    if start_line is not None:
        args.extend(["-L", f"{start_line},+{line_count or 120}"])
    args.extend(["--", relative_path])
    return run_readonly_git(workspace.root, args)


def read_git_changes(workspace: RunWorkspace) -> dict[str, object]:
    status = read_git_status(workspace)
    if not status.ok:
        return {
            "ok": False,
            "files": [],
            "status": status.stdout,
            "message": status.stderr or "git status failed.",
        }

    unstaged = run_readonly_git(workspace.root, ["diff", "--numstat"])
    staged = run_readonly_git(workspace.root, ["diff", "--cached", "--numstat"])
    if not unstaged.ok:
        return {"ok": False, "files": [], "status": status.stdout, "message": unstaged.stderr or "git diff failed."}
    if not staged.ok:
        return {"ok": False, "files": [], "status": status.stdout, "message": staged.stderr or "git diff --cached failed."}

    entries: dict[str, dict[str, object]] = {}
    for path, short_status in parse_git_short_status(status.stdout):
        if should_ignore_git_path(workspace.root, path):
            continue
        entry = entries.setdefault(path, empty_git_change(path))
        entry["status"] = short_status
        entry["staged"] = short_status[:1] not in {" ", "?"}
        entry["unstaged"] = short_status[1:2] not in {" ", ""}
        if short_status == "??":
            entry["untracked"] = True

    for path, insertions, deletions, binary in parse_git_numstat(staged.stdout):
        if should_ignore_git_path(workspace.root, path):
            continue
        entry = entries.setdefault(path, empty_git_change(path))
        entry["staged"] = True
        entry["staged_insertions"] = insertions
        entry["staged_deletions"] = deletions
        entry["binary"] = bool(entry["binary"]) or binary

    for path, insertions, deletions, binary in parse_git_numstat(unstaged.stdout):
        if should_ignore_git_path(workspace.root, path):
            continue
        entry = entries.setdefault(path, empty_git_change(path))
        entry["unstaged"] = True
        entry["unstaged_insertions"] = insertions
        entry["unstaged_deletions"] = deletions
        entry["binary"] = bool(entry["binary"]) or binary

    files = sorted(entries.values(), key=lambda item: str(item["path"]))
    message = f"Found {len(files)} changed file(s)."
    return {"ok": True, "files": files, "status": status.stdout, "message": message}


def review_project_changes(workspace: RunWorkspace, max_files: int = 200) -> dict[str, object]:
    if max_files < 1:
        raise ValueError("max_files must be at least 1.")
    if max_files > 500:
        raise ValueError("max_files must be at most 500.")

    changes = read_git_changes(workspace)
    if not changes["ok"]:
        return {
            "ok": False,
            "changes_ok": False,
            "diff_check_ok": False,
            "staged_diff_check_ok": False,
            "python_ok": False,
            "files": [],
            "total_files": 0,
            "python": [],
            "python_total": 0,
            "python_truncated": False,
            "diff_check": "",
            "staged_diff_check": "",
            "status": str(changes["status"]),
            "message": str(changes["message"]),
        }

    files = [item for item in changes["files"] if isinstance(item, dict)]
    diff_check = run_readonly_git(workspace.root, ["diff", "--check"])
    staged_diff_check = run_readonly_git(workspace.root, ["diff", "--cached", "--check"])
    diff_check_output = combine_git_output(diff_check)
    staged_diff_check_output = combine_git_output(staged_diff_check)

    python_paths = [
        str(item["path"])
        for item in files
        if isinstance(item.get("path"), str) and str(item["path"]).endswith(".py")
    ]
    python_results, python_total = check_python_file_paths(workspace, python_paths, max_files=max_files)
    python_failed = sum(1 for item in python_results if not item["ok"])
    python_truncated = len(python_results) < python_total

    diff_check_ok = diff_check.exit_code == 0
    staged_diff_check_ok = staged_diff_check.exit_code == 0
    python_ok = python_failed == 0
    ok = diff_check_ok and staged_diff_check_ok and python_ok

    issues: list[str] = []
    if not diff_check_ok:
        issues.append("unstaged diff check failed")
    if not staged_diff_check_ok:
        issues.append("staged diff check failed")
    if not python_ok:
        issues.append(f"{python_failed} Python file(s) failed syntax check")
    if python_truncated:
        issues.append(f"Python syntax check truncated at {len(python_results)}/{python_total} file(s)")
    if len(files) > max_files:
        issues.append(f"changed file list truncated at {max_files}/{len(files)} file(s)")
    if issues:
        message = "Review found issue(s): " + "; ".join(issues) + "."
    else:
        message = f"Review passed for {len(files)} changed file(s) and {python_total} Python file(s)."

    return {
        "ok": ok,
        "changes_ok": True,
        "diff_check_ok": diff_check_ok,
        "staged_diff_check_ok": staged_diff_check_ok,
        "python_ok": python_ok,
        "files": files[:max_files],
        "total_files": len(files),
        "python": python_results,
        "python_total": python_total,
        "python_truncated": python_truncated,
        "diff_check": diff_check_output,
        "staged_diff_check": staged_diff_check_output,
        "status": str(changes["status"]),
        "message": message,
    }


def suggest_project_checks(workspace: RunWorkspace, max_commands: int = 20) -> dict[str, object]:
    if max_commands < 1:
        raise ValueError("max_commands must be at least 1.")
    if max_commands > 100:
        raise ValueError("max_commands must be at most 100.")

    files = list_files(workspace.root)
    changes = read_git_changes(workspace)
    changed_paths = [
        str(item["path"])
        for item in changes.get("files", [])
        if isinstance(item, dict) and isinstance(item.get("path"), str)
    ]

    suggestions: list[dict[str, str]] = []
    for relative_path in files:
        name = Path(relative_path).name
        cwd = Path(relative_path).parent.as_posix()
        if cwd == ".":
            cwd = "."
        source = relative_path
        path = workspace.root / relative_path
        if name == "package.json":
            for script_name, _script in read_package_json_scripts(path):
                if is_check_script_name(script_name):
                    add_check_suggestion(
                        suggestions,
                        command=f"npm run {script_name}",
                        cwd=cwd,
                        source=source,
                        reason=f"package.json defines a {script_name} script.",
                    )
        elif name == "Makefile":
            for target in read_makefile_targets(path):
                if is_check_script_name(target):
                    add_check_suggestion(
                        suggestions,
                        command=f"make {target}",
                        cwd=cwd,
                        source=source,
                        reason=f"Makefile defines a {target} target.",
                    )

    test_dirs = find_python_test_dirs(workspace.root, files)
    for test_dir in test_dirs:
        add_check_suggestion(
            suggestions,
            command=f"python -m unittest discover -s {test_dir}",
            cwd=".",
            source=test_dir,
            reason="Python unittest-style tests were found.",
        )

    package_dirs = find_python_package_dirs(files)
    if package_dirs:
        add_check_suggestion(
            suggestions,
            command="python -m compileall -q " + " ".join(package_dirs),
            cwd=".",
            source="python packages",
            reason="Python package directories were found.",
        )

    if any(path.endswith(".py") for path in changed_paths):
        add_check_suggestion(
            suggestions,
            command="python -m unittest discover -s tests",
            cwd=".",
            source="git changes",
            reason="Changed Python files usually need the Python test suite.",
        )
    if any(Path(path).name == "package.json" for path in changed_paths):
        add_check_suggestion(
            suggestions,
            command="npm test",
            cwd=".",
            source="git changes",
            reason="package.json changed, so the npm test entry point may be relevant.",
        )

    ordered = sorted(suggestions, key=check_suggestion_sort_key)
    return {
        "ok": True,
        "checks": ordered[:max_commands],
        "total": len(ordered),
        "truncated": len(ordered) > max_commands,
        "changed_files": changed_paths,
        "message": f"Suggested {len(ordered)} check command(s).",
    }


def is_check_script_name(name: str) -> bool:
    normalized = name.lower()
    exact = {"test", "tests", "build", "lint", "check", "typecheck", "type-check", "compile"}
    prefixes = ("test:", "build:", "lint:", "check:", "typecheck:", "type-check:")
    return normalized in exact or normalized.startswith(prefixes)


def add_check_suggestion(
    suggestions: list[dict[str, str]],
    command: str,
    cwd: str,
    source: str,
    reason: str,
) -> None:
    if any(item["command"] == command and item["cwd"] == cwd for item in suggestions):
        return
    suggestions.append({"command": command, "cwd": cwd, "source": source, "reason": reason})


def check_suggestion_sort_key(item: dict[str, str]) -> tuple[int, str, str]:
    command = item["command"]
    base = command.split()[0] if command else ""
    priority = 50
    if "test" in command:
        priority = 0
    elif "unittest" in command or "pytest" in command:
        priority = 1
    elif "compileall" in command or "build" in command:
        priority = 10
    elif "lint" in command or "check" in command or "typecheck" in command:
        priority = 20
    return (priority, item["cwd"], base + command)


def find_python_test_dirs(root: Path, files: list[str]) -> list[str]:
    dirs: set[str] = set()
    for relative in files:
        path = Path(relative)
        if path.suffix != ".py" or not path.name.startswith("test"):
            continue
        if path.parent.name == "__pycache__":
            continue
        if path.parent == Path("."):
            continue
        if path.parent.name == "tests" or "tests" in path.parts:
            dirs.add(path.parent.as_posix())
    return sorted(dirs)


def find_python_package_dirs(files: list[str]) -> list[str]:
    packages: set[str] = set()
    for relative in files:
        path = Path(relative)
        if path.name != "__init__.py" or len(path.parts) < 2:
            continue
        if path.parts[0] in {".venv", "node_modules", "build", "dist"}:
            continue
        packages.add(path.parent.as_posix())
    return sorted(packages)


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
    try:
        return should_ignore_path(root.resolve(), (root / normalized).resolve())
    except ValueError:
        return True


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


def read_project_file(
    workspace: RunWorkspace,
    relative_path: str,
    max_bytes: int = 20_000,
    start_line: int | None = None,
    line_count: int | None = None,
) -> str:
    target = resolve_inside_run(workspace.root, relative_path)
    if not target.is_file():
        raise ValueError(f"File does not exist: {relative_path}")
    content = read_utf8_text_file(target, relative_path)
    if start_line is not None:
        return format_line_excerpt(content, start_line, line_count or 200)
    if len(content) <= max_bytes:
        return content
    return f"{content[:max_bytes]}\n[file truncated]"


def read_utf8_text_file(path: Path, relative_path: str) -> str:
    if detect_binary_file(path):
        raise ValueError(f"File appears to be binary or non-UTF-8 text: {relative_path}")
    try:
        return path.read_text(encoding="utf-8")
    except UnicodeDecodeError as error:
        raise ValueError(f"File is not valid UTF-8 text: {relative_path}") from error


def read_project_file_info(workspace: RunWorkspace, relative_path: str) -> dict[str, object]:
    target = resolve_inside_run(workspace.root, relative_path)
    if not target.exists():
        return {
            "path": relative_path,
            "ok": False,
            "exists": False,
            "is_file": False,
            "is_dir": False,
            "size_bytes": None,
            "line_count": None,
            "is_binary": None,
            "message": f"Path does not exist: {relative_path}",
        }

    is_file = target.is_file()
    is_dir = target.is_dir()
    size_bytes = target.stat().st_size if is_file else None
    is_binary = detect_binary_file(target) if is_file else None
    line_count = count_file_lines(target) if is_file and is_binary is False else None
    kind = "file" if is_file else "directory" if is_dir else "path"
    return {
        "path": relative_path,
        "ok": True,
        "exists": True,
        "is_file": is_file,
        "is_dir": is_dir,
        "size_bytes": size_bytes,
        "line_count": line_count,
        "is_binary": is_binary,
        "message": f"Inspected {kind}: {relative_path}",
    }


def detect_binary_file(path: Path, sample_bytes: int = 4096) -> bool:
    with path.open("rb") as handle:
        sample = handle.read(sample_bytes)
    if b"\0" in sample:
        return True
    try:
        sample.decode("utf-8")
    except UnicodeDecodeError:
        return True
    return False


def count_file_lines(path: Path) -> int:
    count = 0
    has_bytes = False
    ends_with_newline = False
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            if chunk:
                has_bytes = True
                count += chunk.count(b"\n")
                ends_with_newline = chunk.endswith(b"\n")
    if has_bytes and not ends_with_newline:
        count += 1
    return count


def read_python_symbol_outline(workspace: RunWorkspace, relative_path: str, max_symbols: int = 200) -> dict[str, object]:
    target = resolve_inside_run(workspace.root, relative_path)
    if not target.is_file():
        raise ValueError(f"File does not exist: {relative_path}")
    if target.suffix != ".py":
        raise ValueError(f"File is not a Python source file: {relative_path}")
    content = read_utf8_text_file(target, relative_path)
    try:
        tree = ast.parse(content, filename=relative_path)
    except SyntaxError as error:
        line = error.lineno or "unknown"
        raise ValueError(f"Python syntax error in {relative_path} at line {line}: {error.msg}") from error

    imports = collect_python_imports(tree)
    symbols = collect_python_symbols(tree, max_symbols=max_symbols)
    return {
        "path": relative_path,
        "ok": True,
        "symbols": symbols,
        "imports": imports,
        "message": f"Found {len(symbols)} symbol(s) and {len(imports)} import(s).",
    }


def check_python_syntax(
    workspace: RunWorkspace,
    relative_path: str | None = None,
    max_files: int = 200,
) -> tuple[list[dict[str, object]], int]:
    if max_files < 1:
        raise ValueError("max_files must be at least 1.")
    if max_files > 500:
        raise ValueError("max_files must be at most 500.")

    files = [path for path in list_search_files(workspace, relative_path) if path.endswith(".py")]
    results: list[dict[str, object]] = []
    for relative in files[:max_files]:
        target = resolve_inside_run(workspace.root, relative)
        try:
            content = read_utf8_text_file(target, relative)
            ast.parse(content, filename=relative)
            results.append(
                {
                    "path": relative,
                    "ok": True,
                    "line": None,
                    "column": None,
                    "message": "Syntax OK.",
                }
            )
        except SyntaxError as error:
            results.append(
                {
                    "path": relative,
                    "ok": False,
                    "line": error.lineno,
                    "column": error.offset,
                    "message": f"Python syntax error: {error.msg}",
                }
            )
        except ValueError as error:
            results.append(
                {
                    "path": relative,
                    "ok": False,
                    "line": None,
                    "column": None,
                    "message": str(error),
                }
            )
    return results, len(files)


def check_python_file_paths(
    workspace: RunWorkspace,
    relative_paths: list[str],
    max_files: int = 200,
) -> tuple[list[dict[str, object]], int]:
    if max_files < 1:
        raise ValueError("max_files must be at least 1.")
    if max_files > 500:
        raise ValueError("max_files must be at most 500.")

    files: list[str] = []
    seen: set[str] = set()
    for relative in relative_paths:
        if relative in seen or not relative.endswith(".py"):
            continue
        try:
            target = resolve_inside_run(workspace.root, relative)
        except ValueError:
            continue
        if not target.is_file():
            continue
        seen.add(relative)
        files.append(relative)

    results: list[dict[str, object]] = []
    for relative in files[:max_files]:
        target = resolve_inside_run(workspace.root, relative)
        try:
            content = read_utf8_text_file(target, relative)
            ast.parse(content, filename=relative)
            results.append(
                {
                    "path": relative,
                    "ok": True,
                    "line": None,
                    "column": None,
                    "message": "Syntax OK.",
                }
            )
        except SyntaxError as error:
            results.append(
                {
                    "path": relative,
                    "ok": False,
                    "line": error.lineno,
                    "column": error.offset,
                    "message": f"Python syntax error: {error.msg}",
                }
            )
        except ValueError as error:
            results.append(
                {
                    "path": relative,
                    "ok": False,
                    "line": None,
                    "column": None,
                    "message": str(error),
                }
            )
    return results, len(files)


def inspect_python_dependencies(
    workspace: RunWorkspace,
    relative_path: str | None = None,
    max_files: int = 100,
    max_imports: int = 500,
) -> tuple[list[dict[str, object]], int]:
    if max_files < 1:
        raise ValueError("max_files must be at least 1.")
    if max_files > 500:
        raise ValueError("max_files must be at most 500.")
    if max_imports < 1:
        raise ValueError("max_imports must be at least 1.")
    if max_imports > 2000:
        raise ValueError("max_imports must be at most 2000.")

    all_python_files = [path for path in list_files(workspace.root) if path.endswith(".py")]
    local_modules = build_python_module_index(all_python_files)
    files = [path for path in list_search_files(workspace, relative_path) if path.endswith(".py")]
    results: list[dict[str, object]] = []
    remaining_imports = max_imports
    for relative in files[:max_files]:
        if remaining_imports <= 0:
            results.append(
                {
                    "path": relative,
                    "ok": False,
                    "module": module_name_for_python_path(relative),
                    "imports": [],
                    "local_modules": [],
                    "external_modules": [],
                    "message": "Import result limit reached.",
                }
            )
            continue
        target = resolve_inside_run(workspace.root, relative)
        try:
            content = read_utf8_text_file(target, relative)
            tree = ast.parse(content, filename=relative)
        except SyntaxError as error:
            results.append(
                {
                    "path": relative,
                    "ok": False,
                    "module": module_name_for_python_path(relative),
                    "imports": [],
                    "local_modules": [],
                    "external_modules": [],
                    "message": f"Python syntax error: {error.msg}",
                }
            )
            continue
        except ValueError as error:
            results.append(
                {
                    "path": relative,
                    "ok": False,
                    "module": module_name_for_python_path(relative),
                    "imports": [],
                    "local_modules": [],
                    "external_modules": [],
                    "message": str(error),
                }
            )
            continue

        imports = collect_python_dependency_imports(
            tree,
            current_module=module_name_for_python_path(relative),
            local_modules=local_modules,
            max_imports=remaining_imports,
        )
        remaining_imports -= len(imports)
        local_targets = sorted({str(item["target"]) for item in imports if item["local"]})
        external_targets = sorted({str(item["target"]) for item in imports if not item["local"]})
        results.append(
            {
                "path": relative,
                "ok": True,
                "module": module_name_for_python_path(relative),
                "imports": imports,
                "local_modules": local_targets,
                "external_modules": external_targets,
                "message": f"Found {len(imports)} import(s).",
            }
        )
    return results, len(files)


def build_python_module_index(files: list[str]) -> set[str]:
    modules: set[str] = set()
    for relative in files:
        module = module_name_for_python_path(relative)
        if module:
            modules.add(module)
            parts = module.split(".")
            for index in range(1, len(parts)):
                modules.add(".".join(parts[:index]))
    return modules


def module_name_for_python_path(relative_path: str) -> str:
    path = Path(relative_path)
    if path.suffix != ".py":
        return ""
    parts = list(path.with_suffix("").parts)
    if parts and parts[-1] == "__init__":
        parts = parts[:-1]
    return ".".join(parts)


def collect_python_dependency_imports(
    tree: ast.AST,
    current_module: str,
    local_modules: set[str],
    max_imports: int,
) -> list[dict[str, object]]:
    imports: list[dict[str, object]] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                target = alias.name
                imports.append(
                    {
                        "line": node.lineno,
                        "kind": "import",
                        "module": alias.name,
                        "name": None,
                        "alias": alias.asname,
                        "target": target,
                        "local": is_local_python_module(target, local_modules),
                    }
                )
                if len(imports) >= max_imports:
                    return sorted(imports, key=python_import_sort_key)
        elif isinstance(node, ast.ImportFrom):
            module = resolve_import_from_module(current_module, node.level, node.module)
            for alias in node.names:
                target = resolve_import_target(module, alias.name, local_modules)
                imports.append(
                    {
                        "line": node.lineno,
                        "kind": "from_import",
                        "module": module,
                        "name": alias.name,
                        "alias": alias.asname,
                        "target": target,
                        "local": is_local_python_module(target, local_modules),
                    }
                )
                if len(imports) >= max_imports:
                    return sorted(imports, key=python_import_sort_key)
    return sorted(imports, key=python_import_sort_key)


def resolve_import_from_module(current_module: str, level: int, module: str | None) -> str:
    if level <= 0:
        return module or ""
    package_parts = current_module.split(".")[:-1]
    keep = max(0, len(package_parts) - level + 1)
    base = ".".join(package_parts[:keep])
    if module:
        return f"{base}.{module}" if base else module
    return base


def resolve_import_target(module: str, name: str, local_modules: set[str]) -> str:
    candidate = f"{module}.{name}" if module else name
    if candidate in local_modules:
        return candidate
    if module in local_modules:
        return module
    return module or name


def is_local_python_module(module: str, local_modules: set[str]) -> bool:
    return bool(module) and (module in local_modules or any(module.startswith(f"{local}.") for local in local_modules))


def python_import_sort_key(item: dict[str, object]) -> tuple[int, str, str]:
    return (int(item["line"]), str(item["module"]), str(item["name"] or ""))


def find_python_definitions(
    workspace: RunWorkspace,
    symbol: str,
    relative_path: str | None = None,
    max_matches: int = 50,
    max_lines: int = 120,
) -> tuple[list[dict[str, object]], int, list[str]]:
    symbol = symbol.strip()
    if not re.match(r"^[A-Za-z_][A-Za-z0-9_]*(?:\.[A-Za-z_][A-Za-z0-9_]*)*$", symbol):
        raise ValueError("Python symbol must be a valid identifier or dotted identifier.")
    if max_matches < 1:
        raise ValueError("max_matches must be at least 1.")
    if max_matches > 200:
        raise ValueError("max_matches must be at most 200.")
    if max_lines < 1:
        raise ValueError("max_lines must be at least 1.")
    if max_lines > 1000:
        raise ValueError("max_lines must be at most 1000.")

    definitions: list[dict[str, object]] = []
    errors: list[str] = []
    for relative in list_search_files(workspace, relative_path):
        if Path(relative).suffix != ".py":
            continue
        target = resolve_inside_run(workspace.root, relative)
        try:
            content = read_utf8_text_file(target, relative)
            tree = ast.parse(content, filename=relative)
        except ValueError as error:
            errors.append(str(error))
            continue
        except SyntaxError as error:
            line = error.lineno or "unknown"
            errors.append(f"Python syntax error in {relative} at line {line}: {error.msg}")
            continue

        definitions.extend(collect_python_definition_matches(tree, symbol, relative, content, max_lines=max_lines))

    definitions.sort(key=lambda item: (str(item["path"]), int(item["line"]), str(item["qualified_name"])))
    return definitions[:max_matches], len(definitions), errors


def replace_python_definition(
    workspace: RunWorkspace,
    symbol: str,
    new_content: str,
    relative_path: str | None = None,
) -> tuple[Path, str, dict[str, object]]:
    if not new_content.strip():
        raise ValueError("Replacement content must not be empty.")

    definitions, total, _ = find_python_definitions(
        workspace,
        symbol,
        relative_path=relative_path,
        max_matches=2,
        max_lines=1,
    )
    if total == 0:
        raise ValueError(f"Python definition not found: {symbol}")
    if total > 1:
        raise ValueError(f"Python definition is ambiguous: found {total} matches for {symbol}")

    definition = definitions[0]
    path = str(definition["path"])
    start_line = int(definition["line"])
    end_line = int(definition["end_line"])
    target = resolve_inside_run(workspace.root, path)
    before = read_utf8_text_file(target, path)
    lines = before.splitlines(keepends=True)

    replacement = split_replacement_lines(new_content)
    after = "".join(lines[: start_line - 1] + replacement + lines[end_line:])
    if after == before:
        raise ValueError(f"Python definition replacement made no changes to {path}")

    try:
        ast.parse(after, filename=path)
    except SyntaxError as error:
        line = error.lineno or "unknown"
        raise ValueError(f"Replacement would create Python syntax error in {path} at line {line}: {error.msg}") from error

    target.write_text(after, encoding="utf-8")
    return target, build_simple_diff(path, before, after), definition


def collect_python_definition_matches(
    tree: ast.AST,
    symbol: str,
    relative_path: str,
    content: str,
    max_lines: int,
) -> list[dict[str, object]]:
    matches: list[dict[str, object]] = []
    wanted_name = symbol.rsplit(".", 1)[-1]

    def visit_body(nodes: list[ast.stmt], parent: str | None = None) -> None:
        for node in nodes:
            kind: str | None = None
            if isinstance(node, ast.ClassDef):
                kind = "class"
            elif isinstance(node, ast.AsyncFunctionDef):
                kind = "async_function"
            elif isinstance(node, ast.FunctionDef):
                kind = "function"

            if kind is not None:
                qualified_name = node.name if parent is None else f"{parent}.{node.name}"
                if node.name == wanted_name and (symbol == wanted_name or symbol == qualified_name):
                    end_line = getattr(node, "end_lineno", None) or node.lineno
                    start_line = python_definition_start_line(node)
                    line_count = min(max_lines, end_line - start_line + 1)
                    matches.append(
                        {
                            "path": relative_path,
                            "name": node.name,
                            "qualified_name": qualified_name,
                            "kind": kind,
                            "line": start_line,
                            "end_line": end_line,
                            "parent": parent,
                            "content": format_line_excerpt(content, start_line, line_count),
                            "truncated": line_count < end_line - start_line + 1,
                            "message": f"Found {kind} {qualified_name}.",
                        }
                    )
                visit_body(node.body, qualified_name)
            else:
                child_body = getattr(node, "body", None)
                if isinstance(child_body, list):
                    visit_body(child_body, parent)

    visit_body(getattr(tree, "body", []))
    return matches


def python_definition_start_line(node: ast.ClassDef | ast.FunctionDef | ast.AsyncFunctionDef) -> int:
    decorator_lines = [decorator.lineno for decorator in node.decorator_list if hasattr(decorator, "lineno")]
    return min([node.lineno, *decorator_lines])


def find_python_calls(
    workspace: RunWorkspace,
    symbol: str,
    relative_path: str | None = None,
    max_matches: int = 200,
) -> tuple[list[dict[str, object]], int, list[str]]:
    symbol = symbol.strip()
    if not re.match(r"^[A-Za-z_][A-Za-z0-9_]*(?:\.[A-Za-z_][A-Za-z0-9_]*)*$", symbol):
        raise ValueError("Python symbol must be a valid identifier or dotted identifier.")
    if max_matches < 1:
        raise ValueError("max_matches must be at least 1.")
    if max_matches > 500:
        raise ValueError("max_matches must be at most 500.")

    calls: list[dict[str, object]] = []
    errors: list[str] = []
    for relative in list_search_files(workspace, relative_path):
        if Path(relative).suffix != ".py":
            continue
        target = resolve_inside_run(workspace.root, relative)
        try:
            content = read_utf8_text_file(target, relative)
            tree = ast.parse(content, filename=relative)
        except ValueError as error:
            errors.append(str(error))
            continue
        except SyntaxError as error:
            line = error.lineno or "unknown"
            errors.append(f"Python syntax error in {relative} at line {line}: {error.msg}")
            continue

        calls.extend(collect_python_call_matches(tree, symbol, relative, content.splitlines()))

    calls.sort(key=lambda item: (str(item["path"]), int(item["line"]), int(item["column"]), str(item["callee"])))
    return calls[:max_matches], len(calls), errors


def inspect_python_call_graph(
    workspace: RunWorkspace,
    relative_path: str | None = None,
    max_files: int = 100,
    max_edges: int = 500,
) -> tuple[list[dict[str, object]], int, int, list[str]]:
    if max_files < 1:
        raise ValueError("max_files must be at least 1.")
    if max_files > 500:
        raise ValueError("max_files must be at most 500.")
    if max_edges < 1:
        raise ValueError("max_edges must be at least 1.")
    if max_edges > 2000:
        raise ValueError("max_edges must be at most 2000.")

    files = [path for path in list_search_files(workspace, relative_path) if path.endswith(".py")]
    edges: list[dict[str, object]] = []
    errors: list[str] = []
    for relative in files[:max_files]:
        target = resolve_inside_run(workspace.root, relative)
        try:
            content = read_utf8_text_file(target, relative)
            tree = ast.parse(content, filename=relative)
        except ValueError as error:
            errors.append(str(error))
            continue
        except SyntaxError as error:
            line = error.lineno or "unknown"
            errors.append(f"Python syntax error in {relative} at line {line}: {error.msg}")
            continue

        edges.extend(collect_python_call_graph_edges(tree, relative, content.splitlines()))

    edges.sort(key=lambda item: (str(item["path"]), int(item["line"]), int(item["column"]), str(item["callee"])))
    return edges[:max_edges], len(edges), len(files), errors


def collect_python_call_graph_edges(
    tree: ast.AST,
    relative_path: str,
    lines: list[str],
) -> list[dict[str, object]]:
    edges: list[dict[str, object]] = []
    scope_stack: list[str] = []

    class Visitor(ast.NodeVisitor):
        def visit_ClassDef(self, node: ast.ClassDef) -> None:
            scope_stack.append(node.name if not scope_stack else f"{scope_stack[-1]}.{node.name}")
            self.generic_visit(node)
            scope_stack.pop()

        def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
            self.visit_function_scope(node)

        def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
            self.visit_function_scope(node)

        def visit_function_scope(self, node: ast.FunctionDef | ast.AsyncFunctionDef) -> None:
            scope_stack.append(node.name if not scope_stack else f"{scope_stack[-1]}.{node.name}")
            self.generic_visit(node)
            scope_stack.pop()

        def visit_Call(self, node: ast.Call) -> None:
            callee = python_call_name(node.func)
            if callee:
                line = getattr(node, "lineno", 0)
                column = getattr(node, "col_offset", 0)
                edges.append(
                    {
                        "path": relative_path,
                        "line": int(line),
                        "column": int(column),
                        "callee": callee,
                        "caller": scope_stack[-1] if scope_stack else None,
                        "context": lines[line - 1].strip() if 1 <= line <= len(lines) else "",
                    }
                )
            self.generic_visit(node)

    Visitor().visit(tree)
    return edges


def collect_python_call_matches(
    tree: ast.AST,
    symbol: str,
    relative_path: str,
    lines: list[str],
) -> list[dict[str, object]]:
    calls: list[dict[str, object]] = []
    wanted_tail = symbol.rsplit(".", 1)[-1]
    scope_stack: list[str] = []

    class Visitor(ast.NodeVisitor):
        def visit_ClassDef(self, node: ast.ClassDef) -> None:
            scope_stack.append(node.name if not scope_stack else f"{scope_stack[-1]}.{node.name}")
            self.generic_visit(node)
            scope_stack.pop()

        def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
            self.visit_function_scope(node)

        def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
            self.visit_function_scope(node)

        def visit_function_scope(self, node: ast.FunctionDef | ast.AsyncFunctionDef) -> None:
            scope_stack.append(node.name if not scope_stack else f"{scope_stack[-1]}.{node.name}")
            self.generic_visit(node)
            scope_stack.pop()

        def visit_Call(self, node: ast.Call) -> None:
            callee = python_call_name(node.func)
            if call_matches_symbol(callee, symbol, wanted_tail):
                line = getattr(node, "lineno", 0)
                column = getattr(node, "col_offset", 0)
                calls.append(
                    {
                        "path": relative_path,
                        "line": int(line),
                        "column": int(column),
                        "callee": callee,
                        "caller": scope_stack[-1] if scope_stack else None,
                        "context": lines[line - 1].strip() if 1 <= line <= len(lines) else "",
                    }
                )
            self.generic_visit(node)

    Visitor().visit(tree)
    return calls


def python_call_name(node: ast.AST) -> str:
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        base = python_call_name(node.value)
        return f"{base}.{node.attr}" if base else node.attr
    if isinstance(node, ast.Call):
        return python_call_name(node.func)
    if isinstance(node, ast.Subscript):
        return python_call_name(node.value)
    return ""


def call_matches_symbol(callee: str, symbol: str, wanted_tail: str) -> bool:
    if not callee:
        return False
    if "." in symbol:
        return callee == symbol or callee.endswith(f".{symbol}")
    return callee == symbol or callee.rsplit(".", 1)[-1] == wanted_tail


def find_python_references(
    workspace: RunWorkspace,
    symbol: str,
    relative_path: str | None = None,
    max_matches: int = 200,
) -> tuple[list[dict[str, object]], int, list[str]]:
    symbol = symbol.strip()
    if not re.match(r"^[A-Za-z_][A-Za-z0-9_]*$", symbol):
        raise ValueError("Python symbol must be a valid identifier.")
    if max_matches < 1:
        raise ValueError("max_matches must be at least 1.")
    if max_matches > 500:
        raise ValueError("max_matches must be at most 500.")

    references: list[dict[str, object]] = []
    errors: list[str] = []
    for relative in list_search_files(workspace, relative_path):
        if Path(relative).suffix != ".py":
            continue
        target = resolve_inside_run(workspace.root, relative)
        try:
            content = read_utf8_text_file(target, relative)
            tree = ast.parse(content, filename=relative)
        except ValueError as error:
            errors.append(str(error))
            continue
        except SyntaxError as error:
            line = error.lineno or "unknown"
            errors.append(f"Python syntax error in {relative} at line {line}: {error.msg}")
            continue

        lines = content.splitlines()
        references.extend(collect_python_references(tree, symbol, relative, lines))

    references.sort(key=lambda item: (str(item["path"]), int(item["line"]), int(item["column"]), str(item["kind"])))
    return references[:max_matches], len(references), errors


def collect_python_references(
    tree: ast.AST,
    symbol: str,
    relative_path: str,
    lines: list[str],
) -> list[dict[str, object]]:
    references: list[dict[str, object]] = []
    seen: set[tuple[int, int, str]] = set()

    def add(node: ast.AST, kind: str, column: int | None = None) -> None:
        line = getattr(node, "lineno", None)
        if not isinstance(line, int):
            return
        col = column if column is not None else getattr(node, "col_offset", 0)
        key = (line, int(col), kind)
        if key in seen:
            return
        seen.add(key)
        context = lines[line - 1].strip() if 1 <= line <= len(lines) else ""
        references.append(
            {
                "path": relative_path,
                "line": line,
                "column": int(col),
                "kind": kind,
                "context": context,
            }
        )

    for node in ast.walk(tree):
        if isinstance(node, (ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == symbol:
            add(node, "definition")
        elif isinstance(node, ast.Name) and node.id == symbol:
            add(node, "reference")
        elif isinstance(node, ast.Attribute) and node.attr == symbol:
            attr_column = getattr(node, "end_col_offset", None)
            if isinstance(attr_column, int):
                attr_column -= len(symbol)
            add(node, "reference", column=attr_column)
        elif isinstance(node, ast.Import):
            for alias in node.names:
                if alias.asname == symbol or alias.name.split(".", 1)[0] == symbol:
                    add(node, "import")
                    break
        elif isinstance(node, ast.ImportFrom):
            for alias in node.names:
                imported_name = alias.asname or alias.name
                if imported_name == symbol:
                    add(node, "import")
                    break

    return references


def collect_python_imports(tree: ast.AST, max_imports: int = 100) -> list[str]:
    imports: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            names = ", ".join(format_import_alias(alias) for alias in node.names)
            imports.append(f"{node.lineno}: import {names}")
        elif isinstance(node, ast.ImportFrom):
            module = "." * node.level + (node.module or "")
            names = ", ".join(format_import_alias(alias) for alias in node.names)
            imports.append(f"{node.lineno}: from {module} import {names}")
        if len(imports) >= max_imports:
            break
    return sorted(imports, key=import_line_number)


def format_import_alias(alias: ast.alias) -> str:
    return f"{alias.name} as {alias.asname}" if alias.asname else alias.name


def import_line_number(value: str) -> int:
    try:
        return int(value.split(":", 1)[0])
    except ValueError:
        return 0


def collect_python_symbols(tree: ast.AST, max_symbols: int = 200) -> list[dict[str, object]]:
    symbols: list[dict[str, object]] = []

    def visit_body(nodes: list[ast.stmt], parent: str | None = None) -> None:
        for node in nodes:
            if len(symbols) >= max_symbols:
                return
            kind: str | None = None
            if isinstance(node, ast.ClassDef):
                kind = "class"
            elif isinstance(node, ast.AsyncFunctionDef):
                kind = "async_function"
            elif isinstance(node, ast.FunctionDef):
                kind = "function"

            if kind is not None:
                symbols.append(
                    {
                        "name": node.name,
                        "kind": kind,
                        "line": node.lineno,
                        "end_line": getattr(node, "end_lineno", None),
                        "parent": parent,
                    }
                )
                visit_body(node.body, node.name if parent is None else f"{parent}.{node.name}")
            else:
                child_body = getattr(node, "body", None)
                if isinstance(child_body, list):
                    visit_body(child_body, parent)

    visit_body(getattr(tree, "body", []))
    return symbols


def format_line_excerpt(content: str, start_line: int, line_count: int) -> str:
    if start_line < 1:
        raise ValueError("start_line must be at least 1.")
    if line_count < 1:
        raise ValueError("line_count must be at least 1.")
    if line_count > 1000:
        raise ValueError("line_count must be at most 1000.")

    lines = content.splitlines()
    start_index = start_line - 1
    end_index = min(start_index + line_count, len(lines))
    if start_index >= len(lines):
        return ""
    return "\n".join(
        f"{line_number}: {line}"
        for line_number, line in enumerate(lines[start_index:end_index], start=start_line)
    )


def edit_project_file(workspace: RunWorkspace, relative_path: str, old: str, new: str) -> tuple[Path, str]:
    target = resolve_inside_run(workspace.root, relative_path)
    if not target.is_file():
        raise ValueError(f"File does not exist: {relative_path}")
    content = read_utf8_text_file(target, relative_path)
    if old not in content:
        raise ValueError(f"Old text was not found in {relative_path}")
    updated = content.replace(old, new, 1)
    target.write_text(updated, encoding="utf-8")
    return target, build_simple_diff(relative_path, content, updated)


def multi_edit_project_file(workspace: RunWorkspace, relative_path: str, edits: list[tuple[str, str]]) -> tuple[Path, str]:
    target = resolve_inside_run(workspace.root, relative_path)
    if not target.is_file():
        raise ValueError(f"File does not exist: {relative_path}")
    if not edits:
        raise ValueError("At least one edit is required.")

    content = read_utf8_text_file(target, relative_path)
    updated = content
    for index, (old, new) in enumerate(edits, start=1):
        if old == "":
            raise ValueError(f"Edit {index} old text must not be empty.")
        if old not in updated:
            raise ValueError(f"Edit {index} old text was not found in {relative_path}")
        updated = updated.replace(old, new, 1)

    if updated == content:
        raise ValueError(f"Edits made no changes to {relative_path}")
    target.write_text(updated, encoding="utf-8")
    return target, build_simple_diff(relative_path, content, updated)


def replace_project_file_lines(
    workspace: RunWorkspace,
    relative_path: str,
    start_line: int,
    end_line: int,
    new_content: str,
) -> tuple[Path, str]:
    if start_line < 1:
        raise ValueError("start_line must be at least 1.")
    if end_line < start_line:
        raise ValueError("end_line must be greater than or equal to start_line.")

    target = resolve_inside_run(workspace.root, relative_path)
    if not target.is_file():
        raise ValueError(f"File does not exist: {relative_path}")
    before = read_utf8_text_file(target, relative_path)
    lines = before.splitlines(keepends=True)
    if end_line > len(lines):
        raise ValueError(f"end_line exceeds file line count: {len(lines)}")

    replacement = split_replacement_lines(new_content)
    updated_lines = lines[: start_line - 1] + replacement + lines[end_line:]
    after = "".join(updated_lines)
    if after == before:
        raise ValueError(f"Line replacement made no changes to {relative_path}")
    target.write_text(after, encoding="utf-8")
    return target, build_simple_diff(relative_path, before, after)


def insert_project_file_lines(
    workspace: RunWorkspace,
    relative_path: str,
    line: int,
    content: str,
) -> tuple[Path, str]:
    if line < 1:
        raise ValueError("line must be at least 1.")
    if content == "":
        raise ValueError("content must not be empty.")

    target = resolve_inside_run(workspace.root, relative_path)
    if not target.is_file():
        raise ValueError(f"File does not exist: {relative_path}")
    before = read_utf8_text_file(target, relative_path)
    lines = before.splitlines(keepends=True)
    if line > len(lines) + 1:
        raise ValueError(f"line exceeds append position: {len(lines) + 1}")

    insertion = split_replacement_lines(content)
    updated_lines = lines[: line - 1] + insertion + lines[line - 1 :]
    after = "".join(updated_lines)
    if after == before:
        raise ValueError(f"Line insertion made no changes to {relative_path}")
    target.write_text(after, encoding="utf-8")
    return target, build_simple_diff(relative_path, before, after)


def split_replacement_lines(content: str) -> list[str]:
    if content == "":
        return []
    lines = content.splitlines(keepends=True)
    if not content.endswith(("\n", "\r")):
        lines[-1] += "\n"
    return lines


def delete_project_file(workspace: RunWorkspace, relative_path: str) -> tuple[Path, str]:
    target = resolve_inside_run(workspace.root, relative_path)
    if not target.is_file():
        raise ValueError(f"File does not exist: {relative_path}")
    before = read_utf8_text_file(target, relative_path)
    target.unlink()
    return target, build_simple_diff(relative_path, before, "")


def move_project_file(workspace: RunWorkspace, source_path: str, destination_path: str) -> tuple[Path, Path]:
    source = resolve_inside_run(workspace.root, source_path)
    destination = resolve_inside_run(workspace.root, destination_path)
    if source == destination:
        raise ValueError("Source and destination must be different.")
    if not source.is_file():
        raise ValueError(f"File does not exist: {source_path}")
    if destination.exists():
        raise ValueError(f"Destination already exists: {destination_path}")
    destination.parent.mkdir(parents=True, exist_ok=True)
    source.rename(destination)
    return source, destination


def patch_project_file(workspace: RunWorkspace, relative_path: str, patch: str) -> tuple[Path, str]:
    target = resolve_inside_run(workspace.root, relative_path)
    if not target.is_file():
        raise ValueError(f"File does not exist: {relative_path}")
    if not patch.strip():
        raise ValueError("Patch must not be empty.")

    before = read_utf8_text_file(target, relative_path)
    after = apply_unified_patch(before, patch)
    if after == before:
        raise ValueError(f"Patch made no changes to {relative_path}")
    target.write_text(after, encoding="utf-8")
    return target, build_simple_diff(relative_path, before, after)


def check_project_patch(workspace: RunWorkspace, relative_path: str, patch: str) -> tuple[Path, str]:
    target = resolve_inside_run(workspace.root, relative_path)
    if not target.is_file():
        raise ValueError(f"File does not exist: {relative_path}")
    if not patch.strip():
        raise ValueError("Patch must not be empty.")

    before = read_utf8_text_file(target, relative_path)
    after = apply_unified_patch(before, patch)
    if after == before:
        raise ValueError(f"Patch made no changes to {relative_path}")
    return target, build_simple_diff(relative_path, before, after)


def patch_project_files(workspace: RunWorkspace, patch: str) -> tuple[list[Path], str]:
    if not patch.strip():
        raise ValueError("Patch must not be empty.")

    file_patches = split_unified_patch_by_file(patch)
    if not file_patches:
        raise ValueError("Patch must include file headers for at least one existing file.")

    prepared: list[tuple[Path, str, str, str]] = []
    seen: set[str] = set()
    for relative_path, file_patch in file_patches:
        if relative_path in seen:
            raise ValueError(f"Patch contains duplicate file section: {relative_path}")
        seen.add(relative_path)

        target = resolve_inside_run(workspace.root, relative_path)
        if not target.is_file():
            raise ValueError(f"File does not exist: {relative_path}")
        before = read_utf8_text_file(target, relative_path)
        after = apply_unified_patch(before, file_patch)
        if after == before:
            raise ValueError(f"Patch made no changes to {relative_path}")
        prepared.append((target, relative_path, before, after))

    for target, _relative_path, _before, after in prepared:
        target.write_text(after, encoding="utf-8")

    diff = "".join(build_simple_diff(relative_path, before, after) for _target, relative_path, before, after in prepared)
    return [target for target, _relative_path, _before, _after in prepared], diff


def check_project_patches(workspace: RunWorkspace, patch: str) -> tuple[list[Path], str]:
    if not patch.strip():
        raise ValueError("Patch must not be empty.")

    file_patches = split_unified_patch_by_file(patch)
    if not file_patches:
        raise ValueError("Patch must include file headers for at least one existing file.")

    prepared: list[tuple[Path, str, str, str]] = []
    seen: set[str] = set()
    for relative_path, file_patch in file_patches:
        if relative_path in seen:
            raise ValueError(f"Patch contains duplicate file section: {relative_path}")
        seen.add(relative_path)

        target = resolve_inside_run(workspace.root, relative_path)
        if not target.is_file():
            raise ValueError(f"File does not exist: {relative_path}")
        before = read_utf8_text_file(target, relative_path)
        after = apply_unified_patch(before, file_patch)
        if after == before:
            raise ValueError(f"Patch made no changes to {relative_path}")
        prepared.append((target, relative_path, before, after))

    diff = "".join(build_simple_diff(relative_path, before, after) for _target, relative_path, before, after in prepared)
    return [target for target, _relative_path, _before, _after in prepared], diff


def split_unified_patch_by_file(patch: str) -> list[tuple[str, str]]:
    patch_lines = patch.splitlines(keepends=True)
    sections: list[tuple[str, str]] = []
    index = 0
    while index < len(patch_lines):
        if not is_file_header_at(patch_lines, index):
            index += 1
            continue

        old_path = parse_unified_diff_path(patch_lines[index][4:])
        new_path = parse_unified_diff_path(patch_lines[index + 1][4:])
        if old_path is None or new_path is None:
            raise ValueError("Patch create/delete file sections are not supported.")
        if old_path != new_path:
            raise ValueError(f"Patch rename sections are not supported: {old_path} -> {new_path}")

        start = index
        index += 2
        while index < len(patch_lines) and not is_file_header_at(patch_lines, index):
            index += 1
        sections.append((old_path, "".join(patch_lines[start:index])))

    return sections


def is_file_header_at(lines: list[str], index: int) -> bool:
    return index + 1 < len(lines) and lines[index].startswith("--- ") and lines[index + 1].startswith("+++ ")


def parse_unified_diff_path(value: str) -> str | None:
    token = value.strip().split("\t", 1)[0].strip()
    if token == "/dev/null":
        return None
    if token.startswith("a/") or token.startswith("b/"):
        token = token[2:]
    return token


def apply_unified_patch(content: str, patch: str) -> str:
    lines = content.splitlines(keepends=True)
    patch_lines = patch.splitlines(keepends=True)
    hunks = parse_unified_patch_hunks(patch_lines)
    if not hunks:
        raise ValueError("Patch must contain at least one unified diff hunk.")

    offset = 0
    updated = list(lines)
    for hunk in hunks:
        old_start, old_count, old_chunk, new_chunk = hunk
        if old_count == 0:
            position = old_start + offset
        else:
            position = old_start - 1 + offset
        if position < 0 or position > len(updated):
            raise ValueError("Patch hunk target is outside the file.")
        if updated[position : position + len(old_chunk)] != old_chunk:
            raise ValueError("Patch context did not match file content.")
        updated[position : position + len(old_chunk)] = new_chunk
        offset += len(new_chunk) - len(old_chunk)

    return "".join(updated)


def parse_unified_patch_hunks(patch_lines: list[str]) -> list[tuple[int, int, list[str], list[str]]]:
    hunks: list[tuple[int, int, list[str], list[str]]] = []
    index = 0
    while index < len(patch_lines):
        line = patch_lines[index]
        if not line.startswith("@@ "):
            index += 1
            continue

        match = re.match(r"@@ -(\d+)(?:,(\d+))? \+(\d+)(?:,(\d+))? @@", line)
        if not match:
            raise ValueError(f"Invalid patch hunk header: {line.strip()}")
        old_start = int(match.group(1))
        old_count = int(match.group(2) or "1")
        new_count = int(match.group(4) or "1")
        index += 1
        old_chunk: list[str] = []
        new_chunk: list[str] = []

        while index < len(patch_lines) and not patch_lines[index].startswith("@@ "):
            raw = patch_lines[index]
            marker = raw[:1]
            text = raw[1:]
            if marker == " ":
                old_chunk.append(text)
                new_chunk.append(text)
            elif marker == "-":
                old_chunk.append(text)
            elif marker == "+":
                new_chunk.append(text)
            elif marker == "\\":
                pass
            elif raw.startswith(("--- ", "+++ ", "diff ", "index ")):
                pass
            else:
                raise ValueError(f"Invalid patch hunk line: {raw.strip()}")
            index += 1

        if len(old_chunk) != old_count:
            raise ValueError("Patch hunk old line count does not match header.")
        if len(new_chunk) != new_count:
            raise ValueError("Patch hunk new line count does not match header.")
        hunks.append((old_start, old_count, old_chunk, new_chunk))

    return hunks


def search_project(
    workspace: RunWorkspace,
    query: str,
    max_matches: int = 80,
    relative_path: str | None = None,
    regex: bool = False,
    case_sensitive: bool = True,
    context_lines: int = 0,
) -> list[str]:
    if not query.strip():
        raise ValueError("Search query must not be empty.")
    if max_matches < 1:
        raise ValueError("max_matches must be at least 1.")
    if max_matches > 500:
        raise ValueError("max_matches must be at most 500.")
    if context_lines < 0:
        raise ValueError("context_lines must be at least 0.")
    if context_lines > 5:
        raise ValueError("context_lines must be at most 5.")

    pattern = None
    needle = query if case_sensitive else query.lower()
    if regex:
        flags = 0 if case_sensitive else re.IGNORECASE
        try:
            pattern = re.compile(query, flags)
        except re.error as error:
            raise ValueError(f"Invalid regex query: {error}") from error

    matches: list[str] = []
    for relative in list_search_files(workspace, relative_path):
        path = resolve_inside_run(workspace.root, relative)
        try:
            lines = path.read_text(encoding="utf-8").splitlines()
        except UnicodeDecodeError:
            continue
        for line_number, line in enumerate(lines, start=1):
            haystack = line if case_sensitive else line.lower()
            found = bool(pattern.search(line)) if pattern else needle in haystack
            if found:
                if context_lines:
                    matches.append(format_search_context(relative, lines, line_number, context_lines))
                else:
                    matches.append(f"{relative}:{line_number}: {line.strip()}")
                if len(matches) >= max_matches:
                    return matches
    return matches


def format_search_context(relative_path: str, lines: list[str], line_number: int, context_lines: int) -> str:
    start = max(1, line_number - context_lines)
    end = min(len(lines), line_number + context_lines)
    parts = []
    for current in range(start, end + 1):
        marker = ">" if current == line_number else " "
        parts.append(f"{relative_path}:{current}:{marker} {lines[current - 1]}")
    return "\n".join(parts)


def glob_project_files(workspace: RunWorkspace, pattern: str, max_matches: int = 200) -> tuple[list[str], int]:
    if max_matches < 1:
        raise ValueError("max_matches must be at least 1.")
    if max_matches > 500:
        raise ValueError("max_matches must be at most 500.")

    normalized = validate_glob_pattern(pattern)
    root = workspace.root.resolve()
    matches: list[str] = []
    for path in sorted(root.glob(normalized)):
        if not path.is_file():
            continue
        try:
            resolved = path.resolve()
        except OSError:
            continue
        if resolved != root and root not in resolved.parents:
            continue
        if should_ignore_path(root, resolved):
            continue
        matches.append(path.relative_to(root).as_posix())

    return matches[:max_matches], len(matches)


def validate_glob_pattern(pattern: str) -> str:
    normalized = pattern.strip().replace("\\", "/")
    if not normalized:
        raise ValueError("Glob pattern must not be empty.")
    if Path(normalized).is_absolute():
        raise ValueError(f"Absolute paths are not allowed: {pattern}")

    parts = [part for part in normalized.split("/") if part]
    if any(part == ".." for part in parts):
        raise ValueError(f"Path escapes the project directory: {pattern}")
    if parts and parts[0] in {".git", ".vibeagent"}:
        raise ValueError(f"Path is protected: {pattern}")
    return normalized


def list_search_files(workspace: RunWorkspace, relative_path: str | None) -> list[str]:
    if not relative_path:
        return list_files(workspace.root)

    base = resolve_inside_run(workspace.root, relative_path)
    if not base.exists():
        raise ValueError(f"Path does not exist: {relative_path}")
    if base.is_file():
        return [base.relative_to(workspace.root).as_posix()]
    return [
        path.relative_to(workspace.root).as_posix()
        for path in sorted(base.rglob("*"))
        if path.is_file() and not should_ignore_path(workspace.root, path)
    ]


def list_project_files(workspace: RunWorkspace, relative_path: str | None = None, max_files: int = 200) -> tuple[list[str], int]:
    base = resolve_inside_run(workspace.root, relative_path or ".")
    if not base.exists():
        raise ValueError(f"Path does not exist: {relative_path or '.'}")
    if base.is_file():
        return [base.relative_to(workspace.root).as_posix()], 1
    files = [
        path.relative_to(workspace.root).as_posix()
        for path in sorted(base.rglob("*"))
        if path.is_file() and not should_ignore_path(workspace.root, path)
    ]
    return files[:max_files], len(files)


def list_project_tree(
    workspace: RunWorkspace,
    relative_path: str | None = None,
    max_depth: int = 3,
    max_entries: int = 200,
) -> tuple[list[str], int]:
    if max_depth < 1:
        raise ValueError("max_depth must be at least 1.")
    if max_depth > 10:
        raise ValueError("max_depth must be at most 10.")
    if max_entries < 1:
        raise ValueError("max_entries must be at least 1.")
    if max_entries > 1000:
        raise ValueError("max_entries must be at most 1000.")

    root = workspace.root.resolve()
    base = resolve_inside_run(root, relative_path or ".")
    if not base.exists():
        raise ValueError(f"Path does not exist: {relative_path or '.'}")
    if base != root and should_ignore_path(root, base):
        raise ValueError(f"Path is ignored: {relative_path or '.'}")
    if base.is_file():
        return [base.relative_to(root).as_posix()], 1

    entries: list[str] = []

    def walk(directory: Path, depth: int) -> None:
        if depth > max_depth:
            return
        try:
            children = sorted(directory.iterdir(), key=lambda path: path.name)
        except OSError:
            return
        for child in children:
            try:
                resolved = child.resolve()
            except OSError:
                continue
            if resolved != root and root not in resolved.parents:
                continue
            if should_ignore_path(root, resolved):
                continue
            suffix = "/" if resolved.is_dir() else ""
            entries.append(f"{resolved.relative_to(root).as_posix()}{suffix}")
            if resolved.is_dir():
                walk(resolved, depth + 1)

    walk(base, 1)
    return entries[:max_entries], len(entries)


def build_repo_map(
    workspace: RunWorkspace,
    relative_path: str | None = None,
    max_depth: int = 3,
    max_files: int = 80,
    max_symbols: int = 120,
) -> dict[str, object]:
    if max_depth < 1:
        raise ValueError("max_depth must be at least 1.")
    if max_depth > 10:
        raise ValueError("max_depth must be at most 10.")
    if max_files < 1:
        raise ValueError("max_files must be at least 1.")
    if max_files > 500:
        raise ValueError("max_files must be at most 500.")
    if max_symbols < 1:
        raise ValueError("max_symbols must be at least 1.")
    if max_symbols > 500:
        raise ValueError("max_symbols must be at most 500.")

    path_label = relative_path or "."
    tree_entries, total_tree_entries = list_project_tree(
        workspace,
        relative_path,
        max_depth=max_depth,
        max_entries=max_files,
    )
    files, total_files = list_project_files(workspace, relative_path, max_files=max_files)

    python_files: list[dict[str, object]] = []
    used_symbols = 0
    symbols_truncated = False
    for file in files:
        if not file.endswith(".py"):
            continue
        remaining = max_symbols - used_symbols
        if remaining <= 0:
            symbols_truncated = True
            break
        try:
            outline = read_python_symbol_outline(workspace, file, max_symbols=remaining)
            symbols = list(outline["symbols"])
            used_symbols += len(symbols)
            python_files.append(
                {
                    "path": file,
                    "ok": True,
                    "imports": list(outline["imports"]),
                    "symbols": symbols,
                    "message": str(outline["message"]),
                }
            )
            if used_symbols >= max_symbols and len(symbols) == remaining:
                symbols_truncated = True
        except ValueError as error:
            python_files.append(
                {
                    "path": file,
                    "ok": False,
                    "imports": [],
                    "symbols": [],
                    "message": str(error),
                }
            )

    truncated = len(tree_entries) < total_tree_entries or len(files) < total_files or symbols_truncated
    return {
        "path": path_label,
        "tree": tree_entries,
        "files": files,
        "python_files": python_files,
        "total_tree_entries": total_tree_entries,
        "total_files": total_files,
        "truncated": truncated,
        "message": f"Mapped {len(files)}/{total_files} file(s) and {len(python_files)} Python file(s).",
    }


def should_ignore_path(root: Path, path: Path) -> bool:
    relative_parts = path.resolve().relative_to(root).parts
    ignored = {".git", ".vibeagent", ".venv", "__pycache__", "node_modules", "dist", "build"}
    return any(part in ignored for part in relative_parts)


def is_protected_project_path(root: Path, path: Path) -> bool:
    try:
        parts = path.relative_to(root).parts
    except ValueError:
        return True
    return bool(parts and parts[0] in {".git", ".vibeagent"})


def build_simple_diff(path: str, before: str, after: str) -> str:
    import difflib

    return "".join(
        difflib.unified_diff(
            before.splitlines(keepends=True),
            after.splitlines(keepends=True),
            fromfile=f"a/{path}",
            tofile=f"b/{path}",
        )
    )


def make_run_id() -> str:
    # Timestamp+uuid-based ID keeps IDs unique without shared state.
    timestamp = datetime.now(UTC).isoformat(timespec="milliseconds").replace("+00:00", "Z")
    safe_timestamp = timestamp.replace(":", "-").replace(".", "-")
    return f"{safe_timestamp}-{uuid4().hex[:8]}"
