from __future__ import annotations

import ast
import json
import platform
import re
import shlex
import shutil
import stat as stat_module
import subprocess
import sys
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
    target, _before, after, _diff = build_write_file(workspace, relative_path, content)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(after, encoding="utf-8")
    return target


def preview_write_run_file(workspace: RunWorkspace, relative_path: str, content: str) -> tuple[Path, str]:
    target, _before, _after, diff = build_write_file(workspace, relative_path, content)
    return target, diff


def build_write_file(workspace: RunWorkspace, relative_path: str, content: str) -> tuple[Path, str, str, str]:
    # Resolve and read existing UTF-8 content when replacing a file.
    target = resolve_inside_run(workspace.root, relative_path)
    if target.exists() and not target.is_file():
        raise ValueError(f"Path is not a file: {relative_path}")
    before = read_utf8_text_file(target, relative_path) if target.exists() else ""
    return target, before, content, build_simple_diff(relative_path, before, content)


def write_run_files(workspace: RunWorkspace, files: list[tuple[str, str]]) -> list[Path]:
    prepared = prepare_write_run_files(workspace, files)

    snapshots: list[tuple[Path, bool, str | None]] = []
    written: list[Path] = []
    try:
        for _relative_path, target, before, content, _diff in prepared:
            snapshots.append((target, target.exists(), before if target.exists() else None))
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


def preview_write_run_files(workspace: RunWorkspace, files: list[tuple[str, str]]) -> list[tuple[str, Path, str]]:
    prepared = prepare_write_run_files(workspace, files)
    return [(relative_path, target, diff) for relative_path, target, _before, _content, diff in prepared]


def prepare_write_run_files(workspace: RunWorkspace, files: list[tuple[str, str]]) -> list[tuple[str, Path, str, str, str]]:
    if not files:
        raise ValueError("At least one file is required.")
    if len(files) > 20:
        raise ValueError("write_files supports at most 20 files.")

    prepared: list[tuple[str, Path, str, str, str]] = []
    seen: set[Path] = set()
    for index, (relative_path, content) in enumerate(files, start=1):
        if not relative_path or not relative_path.strip():
            raise ValueError(f"File {index} path must not be empty.")
        target, before, after, diff = build_write_file(workspace, relative_path, content)
        if target in seen:
            raise ValueError(f"Duplicate file path: {relative_path}")
        seen.add(target)
        prepared.append((relative_path, target, before, after, diff))

    return prepared


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
    metadata = read_project_commands(workspace, max_commands=500, max_files=max_files)
    commands = metadata["commands"]
    if not commands:
        return None

    chunks: list[str] = []
    current_file = ""
    current_lines: list[str] = []
    for command in commands:
        relative_path = str(command["file"])
        if relative_path != current_file:
            if current_lines:
                chunks.append("\n".join(current_lines))
            current_file = relative_path
            current_lines = [f"File: {relative_path}", f"Cwd: {command['cwd']}"]
            source = str(command["source"])
            if source == "package_json_script":
                current_lines.append("package.json scripts:")
            elif source == "pyproject_console_script":
                current_lines.append("pyproject.toml console scripts:")
            elif source == "makefile_target":
                current_lines.append("Makefile targets:")
        current_lines.append(format_command_hint(str(command["command"]), str(command["detail"]) or None))
    if current_lines:
        chunks.append("\n".join(current_lines))

    omitted_files = int(metadata["total_files"]) - int(metadata["scanned_files"])
    if omitted_files > 0:
        chunks.append(f"[{omitted_files} additional command metadata file(s) omitted]")
    if bool(metadata["truncated"]):
        omitted_commands = int(metadata["total"]) - len(commands)
        if omitted_commands > 0:
            chunks.append(f"[{omitted_commands} additional command(s) omitted]")

    combined = "\n\n".join(chunks)
    if len(combined) <= max_bytes:
        return combined
    return f"{combined[:max_bytes]}\n[project command hints truncated]"


def read_project_commands(workspace: RunWorkspace, max_commands: int = 100, max_files: int = 30) -> dict[str, object]:
    if max_commands < 1:
        raise ValueError("max_commands must be at least 1.")
    if max_commands > 500:
        raise ValueError("max_commands must be at most 500.")
    if max_files < 1:
        raise ValueError("max_files must be at least 1.")
    if max_files > 200:
        raise ValueError("max_files must be at most 200.")

    command_files = [
        file
        for file in list_files(workspace.root)
        if Path(file).name in {"package.json", "pyproject.toml", "Makefile"}
    ]
    commands: list[dict[str, object]] = []
    total = 0
    for relative_path in command_files[:max_files]:
        path = workspace.root / relative_path
        cwd = Path(relative_path).parent.as_posix()
        if cwd == ".":
            cwd = "."

        file_commands: list[tuple[str, str, str]] = []
        if Path(relative_path).name == "package.json":
            file_commands = [
                ("package_json_script", f"npm run {name}", command)
                for name, command in read_package_json_scripts(path)
            ]
        elif Path(relative_path).name == "pyproject.toml":
            file_commands = [
                ("pyproject_console_script", name, target)
                for name, target in read_pyproject_scripts(path)
            ]
        elif Path(relative_path).name == "Makefile":
            file_commands = [
                ("makefile_target", f"make {target}", target)
                for target in read_makefile_targets(path)
            ]

        total += len(file_commands)
        for source, command, detail in file_commands:
            if len(commands) >= max_commands:
                continue
            missing_tool = missing_command_tool(command)
            commands.append(
                {
                    "file": relative_path,
                    "cwd": cwd,
                    "source": source,
                    "command": command,
                    "detail": detail,
                    "available": missing_tool is None,
                    "missing_tool": missing_tool,
                }
            )

    truncated = len(command_files) > max_files or total > len(commands)
    scanned_files = min(len(command_files), max_files)
    return {
        "ok": True,
        "commands": commands,
        "total": total,
        "truncated": truncated,
        "total_files": len(command_files),
        "scanned_files": scanned_files,
        "message": f"Found {total} project command(s) in {scanned_files}/{len(command_files)} metadata file(s).",
    }


def read_project_manifests(workspace: RunWorkspace, max_files: int = 30, max_items: int = 500) -> dict[str, object]:
    if max_files < 1:
        raise ValueError("max_files must be at least 1.")
    if max_files > 200:
        raise ValueError("max_files must be at most 200.")
    if max_items < 1:
        raise ValueError("max_items must be at least 1.")
    if max_items > 2000:
        raise ValueError("max_items must be at most 2000.")

    manifest_files = [
        file
        for file in list_files(workspace.root)
        if Path(file).name in {"package.json", "pyproject.toml"}
    ]
    manifests: list[dict[str, object]] = []
    remaining_items = max_items
    for relative_path in manifest_files[:max_files]:
        path = workspace.root / relative_path
        if Path(relative_path).name == "package.json":
            manifest = read_package_json_manifest(path, relative_path, remaining_items)
        else:
            manifest = read_pyproject_manifest(path, relative_path, remaining_items)
        manifests.append(manifest)
        remaining_items = max(0, remaining_items - int(manifest["item_count"]))

    total_items = sum(int(manifest["item_count"]) for manifest in manifests)
    truncated = len(manifest_files) > max_files or any(bool(manifest["truncated"]) for manifest in manifests)
    return {
        "ok": all(bool(manifest["ok"]) for manifest in manifests),
        "manifests": manifests,
        "total_files": len(manifest_files),
        "scanned_files": min(len(manifest_files), max_files),
        "total_items": total_items,
        "truncated": truncated,
        "message": f"Read {min(len(manifest_files), max_files)}/{len(manifest_files)} project manifest file(s).",
    }


def read_package_json_manifest(path: Path, relative_path: str, max_items: int) -> dict[str, object]:
    try:
        parsed = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        return empty_project_manifest(relative_path, "package_json", str(error))
    if not isinstance(parsed, dict):
        return empty_project_manifest(relative_path, "package_json", "package.json root is not an object.")

    groups = [
        ("scripts", parsed.get("scripts")),
        ("dependencies", parsed.get("dependencies")),
        ("devDependencies", parsed.get("devDependencies")),
        ("peerDependencies", parsed.get("peerDependencies")),
        ("optionalDependencies", parsed.get("optionalDependencies")),
    ]
    items, item_count, truncated = manifest_group_items(groups, max_items)
    return {
        "path": relative_path,
        "kind": "package_json",
        "ok": True,
        "name": str(parsed.get("name") or ""),
        "version": str(parsed.get("version") or ""),
        "items": items,
        "item_count": item_count,
        "truncated": truncated,
        "message": f"Read package.json manifest with {item_count} item(s).",
    }


def read_pyproject_manifest(path: Path, relative_path: str, max_items: int) -> dict[str, object]:
    try:
        parsed = tomllib.loads(path.read_text(encoding="utf-8"))
    except (OSError, tomllib.TOMLDecodeError) as error:
        return empty_project_manifest(relative_path, "pyproject_toml", str(error))
    if not isinstance(parsed, dict):
        return empty_project_manifest(relative_path, "pyproject_toml", "pyproject.toml root is not an object.")

    project = parsed.get("project") if isinstance(parsed.get("project"), dict) else {}
    tool = parsed.get("tool") if isinstance(parsed.get("tool"), dict) else {}
    poetry = tool.get("poetry") if isinstance(tool.get("poetry"), dict) else {}
    groups = [
        ("dependencies", project.get("dependencies")),
        ("optional-dependencies", project.get("optional-dependencies")),
        ("scripts", project.get("scripts")),
        ("gui-scripts", project.get("gui-scripts")),
        ("poetry.dependencies", poetry.get("dependencies")),
        ("poetry.dev-dependencies", poetry.get("dev-dependencies")),
    ]
    items, item_count, truncated = manifest_group_items(groups, max_items)
    return {
        "path": relative_path,
        "kind": "pyproject_toml",
        "ok": True,
        "name": str(project.get("name") or poetry.get("name") or ""),
        "version": str(project.get("version") or poetry.get("version") or ""),
        "items": items,
        "item_count": item_count,
        "truncated": truncated,
        "message": f"Read pyproject.toml manifest with {item_count} item(s).",
    }


def empty_project_manifest(relative_path: str, kind: str, message: str) -> dict[str, object]:
    return {
        "path": relative_path,
        "kind": kind,
        "ok": False,
        "name": "",
        "version": "",
        "items": [],
        "item_count": 0,
        "truncated": False,
        "message": message,
    }


def manifest_group_items(groups: list[tuple[str, object]], max_items: int) -> tuple[list[dict[str, str]], int, bool]:
    items: list[dict[str, str]] = []
    total = 0
    for group, value in groups:
        entries = normalize_manifest_group_items(group, value)
        total += len(entries)
        for item in entries:
            if len(items) < max_items:
                items.append(item)
    return items, total, total > len(items)


def normalize_manifest_group_items(group: str, value: object) -> list[dict[str, str]]:
    if isinstance(value, dict):
        return sorted(
            [
                {"group": group, "name": str(name), "value": stringify_manifest_value(raw_value)}
                for name, raw_value in value.items()
                if isinstance(name, str)
            ],
            key=lambda item: item["name"],
        )
    if isinstance(value, list):
        return [
            {"group": group, "name": str(item), "value": ""}
            for item in value
            if isinstance(item, str)
        ]
    return []


def stringify_manifest_value(value: object) -> str:
    if isinstance(value, str):
        return value
    if isinstance(value, (int, float, bool)):
        return str(value)
    if value is None:
        return ""
    try:
        return json.dumps(value, sort_keys=True)
    except TypeError:
        return str(value)


def format_command_hint(command: str, detail: str | None = None) -> str:
    missing_tool = missing_command_tool(command)
    availability = f"available={str(missing_tool is None).lower()} missingTool={missing_tool or '.'}"
    suffix = f": {detail}" if detail else ""
    return f"- {command} [{availability}]{suffix}"


def read_environment_info(workspace: RunWorkspace) -> dict[str, object]:
    tools = [read_runtime_tool_info(name, args) for name, args in runtime_tool_commands()]
    git_probe = run_readonly_git(workspace.root, ["rev-parse", "--is-inside-work-tree"])
    return {
        "project_root": workspace.root.as_posix(),
        "python_version": platform.python_version(),
        "python_executable": sys.executable,
        "platform": f"{platform.system()} {platform.release()} {platform.machine()}".strip(),
        "is_git_repo": git_probe.ok and git_probe.stdout.strip() == "true",
        "tools": tools,
        "message": f"Inspected runtime environment; {sum(1 for tool in tools if tool['available'])}/{len(tools)} tool(s) available.",
    }


def runtime_tool_commands() -> list[tuple[str, list[str]]]:
    return [
        ("python", [sys.executable, "--version"]),
        ("python3", ["python3", "--version"]),
        ("git", ["git", "--version"]),
        ("node", ["node", "--version"]),
        ("npm", ["npm", "--version"]),
        ("pnpm", ["pnpm", "--version"]),
        ("yarn", ["yarn", "--version"]),
        ("uv", ["uv", "--version"]),
        ("pytest", ["pytest", "--version"]),
    ]


def read_runtime_tool_info(name: str, command: list[str]) -> dict[str, object]:
    executable = command[0]
    path = sys.executable if executable == sys.executable else shutil.which(executable)
    if not path:
        return {"name": name, "available": False, "path": None, "version": None, "message": "Not found on PATH."}
    try:
        result = subprocess.run(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=2,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired) as error:
        return {"name": name, "available": True, "path": path, "version": None, "message": str(error)}
    version = (result.stdout or result.stderr).strip().splitlines()
    version_text = version[0] if version else ""
    return {
        "name": name,
        "available": result.returncode == 0,
        "path": path,
        "version": version_text or None,
        "message": version_text or f"Exited with {result.returncode}.",
    }


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


def read_git_info(workspace: RunWorkspace) -> dict[str, object]:
    git_probe = run_readonly_git(workspace.root, ["rev-parse", "--is-inside-work-tree"])
    if not git_probe.ok or git_probe.stdout.strip() != "true":
        return {
            "ok": False,
            "is_git_repo": False,
            "branch": "",
            "head": "",
            "upstream": "",
            "ahead": 0,
            "behind": 0,
            "remotes": [],
            "status": "",
            "message": git_probe.stderr or "Not a git repository.",
        }

    branch_result = run_readonly_git(workspace.root, ["branch", "--show-current"])
    head_result = run_readonly_git(workspace.root, ["rev-parse", "--short", "HEAD"])
    upstream_result = run_readonly_git(workspace.root, ["rev-parse", "--abbrev-ref", "--symbolic-full-name", "@{u}"])
    status_result = read_git_status(workspace)
    remotes_result = run_readonly_git(workspace.root, ["remote", "-v"])

    upstream = upstream_result.stdout.strip() if upstream_result.ok else ""
    ahead = 0
    behind = 0
    if upstream:
        counts = run_readonly_git(workspace.root, ["rev-list", "--left-right", "--count", f"HEAD...{upstream}"])
        if counts.ok:
            parts = counts.stdout.strip().split()
            if len(parts) >= 2 and parts[0].isdigit() and parts[1].isdigit():
                ahead = int(parts[0])
                behind = int(parts[1])

    remotes = parse_git_remotes(remotes_result.stdout if remotes_result.ok else "")
    branch = branch_result.stdout.strip() if branch_result.ok else ""
    head = head_result.stdout.strip() if head_result.ok else ""
    status = status_result.stdout if status_result.ok else ""
    message = f"Git repository on {branch or 'detached HEAD'} at {head or 'unknown'}."
    if upstream:
        message += f" Upstream {upstream}, ahead {ahead}, behind {behind}."
    else:
        message += " No upstream configured."

    return {
        "ok": True,
        "is_git_repo": True,
        "branch": branch,
        "head": head,
        "upstream": upstream,
        "ahead": ahead,
        "behind": behind,
        "remotes": remotes,
        "status": status,
        "message": message,
    }


def read_git_branches(workspace: RunWorkspace, max_branches: int = 100) -> dict[str, object]:
    if max_branches < 1:
        raise ValueError("max_branches must be at least 1.")
    if max_branches > 500:
        raise ValueError("max_branches must be at most 500.")
    git_probe = run_readonly_git(workspace.root, ["rev-parse", "--is-inside-work-tree"])
    if not git_probe.ok or git_probe.stdout.strip() != "true":
        return {
            "ok": False,
            "current": "",
            "branches": [],
            "total": 0,
            "truncated": False,
            "status": "",
            "message": git_probe.stderr or "Not a git repository.",
        }

    current_result = run_readonly_git(workspace.root, ["branch", "--show-current"])
    branches_result = run_readonly_git(workspace.root, ["branch", "--list", "--format=%(refname:short)"])
    status = read_git_status(workspace)
    if not branches_result.ok:
        return {
            "ok": False,
            "current": current_result.stdout.strip() if current_result.ok else "",
            "branches": [],
            "total": 0,
            "truncated": False,
            "status": status.stdout if status.ok else "",
            "message": branches_result.stderr or "git branch failed.",
        }

    current = current_result.stdout.strip() if current_result.ok else ""
    names = [line.strip() for line in branches_result.stdout.splitlines() if line.strip()]
    total = len(names)
    shown = names[:max_branches]
    return {
        "ok": True,
        "current": current,
        "branches": [{"name": name, "current": name == current} for name in shown],
        "total": total,
        "truncated": len(shown) < total,
        "status": status.stdout if status.ok else "",
        "message": f"Found {total} local git branch(es).",
    }


def preview_fetch_git_remote(workspace: RunWorkspace, remote: str | None = None) -> dict[str, object]:
    selected = select_git_fetch_remote(workspace, remote)
    if not selected["ok"]:
        return {
            "ok": False,
            "remote": str(selected["remote"]),
            "remote_url": "",
            "branch": "",
            "upstream": "",
            "ahead": 0,
            "behind": 0,
            "message": str(selected["message"]),
        }

    info = read_git_info(workspace)
    return {
        "ok": True,
        "remote": str(selected["remote"]),
        "remote_url": str(selected["remote_url"]),
        "branch": str(info["branch"]),
        "upstream": str(info["upstream"]),
        "ahead": int(info["ahead"]),
        "behind": int(info["behind"]),
        "message": (
            f"git fetch --prune {selected['remote']} can run. "
            f"Current branch {info['branch'] or 'detached HEAD'} is ahead {info['ahead']} and behind {info['behind']}."
        ),
    }


def fetch_git_remote(workspace: RunWorkspace, remote: str | None = None) -> dict[str, object]:
    before = preview_fetch_git_remote(workspace, remote)
    if not before["ok"]:
        return {
            "ok": False,
            "remote": str(before["remote"]),
            "remote_url": "",
            "branch": "",
            "upstream": "",
            "ahead_before": 0,
            "behind_before": 0,
            "ahead_after": 0,
            "behind_after": 0,
            "message": str(before["message"]),
        }

    result = run_git_mutation(workspace.root, ["fetch", "--prune", str(before["remote"])])
    after = read_git_info(workspace)
    if not result.ok:
        return {
            "ok": False,
            "remote": str(before["remote"]),
            "remote_url": str(before["remote_url"]),
            "branch": str(after["branch"]),
            "upstream": str(after["upstream"]),
            "ahead_before": int(before["ahead"]),
            "behind_before": int(before["behind"]),
            "ahead_after": int(after["ahead"]),
            "behind_after": int(after["behind"]),
            "message": redact_git_text(result.stderr or result.stdout or "git fetch failed."),
        }

    return {
        "ok": True,
        "remote": str(before["remote"]),
        "remote_url": str(before["remote_url"]),
        "branch": str(after["branch"]),
        "upstream": str(after["upstream"]),
        "ahead_before": int(before["ahead"]),
        "behind_before": int(before["behind"]),
        "ahead_after": int(after["ahead"]),
        "behind_after": int(after["behind"]),
        "message": (
            f"Fetched {before['remote']} with --prune. "
            f"Ahead/behind changed from {before['ahead']}/{before['behind']} to {after['ahead']}/{after['behind']}."
        ),
    }


def preview_pull_git_upstream(workspace: RunWorkspace) -> dict[str, object]:
    info = read_git_info(workspace)
    status = read_git_status(workspace)
    current = str(info["branch"]) if info["ok"] else ""
    if not info["ok"]:
        return {
            "ok": False,
            "remote": "",
            "branch": "",
            "current": "",
            "upstream": "",
            "ahead": 0,
            "behind": 0,
            "worktree_clean": False,
            "status": "",
            "message": str(info["message"]),
        }
    if not current:
        return {
            "ok": False,
            "remote": "",
            "branch": "",
            "current": "",
            "upstream": "",
            "ahead": int(info["ahead"]),
            "behind": int(info["behind"]),
            "worktree_clean": False,
            "status": status.stdout if status.ok else "",
            "message": "Cannot pull while HEAD is detached.",
        }
    upstream = str(info["upstream"])
    upstream_parts = read_git_upstream_parts(workspace, current)
    clean = status.ok and not git_status_has_non_runtime_changes(status.stdout)
    if not upstream or not upstream_parts["ok"]:
        return {
            "ok": False,
            "remote": str(upstream_parts["remote"]),
            "branch": str(upstream_parts["branch"]),
            "current": current,
            "upstream": upstream,
            "ahead": int(info["ahead"]),
            "behind": int(info["behind"]),
            "worktree_clean": clean,
            "status": status.stdout if status.ok else "",
            "message": "Current branch has no upstream configured.",
        }
    if not clean:
        return {
            "ok": False,
            "remote": str(upstream_parts["remote"]),
            "branch": str(upstream_parts["branch"]),
            "current": current,
            "upstream": upstream,
            "ahead": int(info["ahead"]),
            "behind": int(info["behind"]),
            "worktree_clean": False,
            "status": status.stdout if status.ok else "",
            "message": "Working tree has uncommitted changes; commit or clean changes before pulling.",
        }

    ahead = int(info["ahead"])
    behind = int(info["behind"])
    if ahead > 0 and behind > 0:
        message = "Current branch has diverged from upstream; fast-forward pull is not safe."
        ok = False
    elif ahead > 0:
        message = "Current branch is ahead of upstream; nothing to fast-forward pull."
        ok = False
    elif behind == 0:
        message = "Current branch is already up to date with cached upstream state; git pull --ff-only can still check the remote."
        ok = True
    else:
        message = f"Can fast-forward pull {upstream} into {current}."
        ok = True

    return {
        "ok": ok,
        "remote": str(upstream_parts["remote"]),
        "branch": str(upstream_parts["branch"]),
        "current": current,
        "upstream": upstream,
        "ahead": ahead,
        "behind": behind,
        "worktree_clean": True,
        "status": status.stdout if status.ok else "",
        "message": message,
    }


def pull_git_upstream(workspace: RunWorkspace) -> dict[str, object]:
    before = preview_pull_git_upstream(workspace)
    if not before["ok"]:
        return {
            "ok": False,
            "remote": str(before["remote"]),
            "branch": str(before["branch"]),
            "current_before": str(before["current"]),
            "current_after": str(before["current"]),
            "upstream": str(before["upstream"]),
            "ahead_before": int(before["ahead"]),
            "behind_before": int(before["behind"]),
            "ahead_after": int(before["ahead"]),
            "behind_after": int(before["behind"]),
            "status": str(before["status"]),
            "message": str(before["message"]),
        }

    result = run_git_mutation(workspace.root, ["pull", "--ff-only", str(before["remote"]), str(before["branch"])])
    after = read_git_info(workspace)
    status = read_git_status(workspace)
    return {
        "ok": result.ok,
        "remote": str(before["remote"]),
        "branch": str(before["branch"]),
        "current_before": str(before["current"]),
        "current_after": str(after["branch"]),
        "upstream": str(after["upstream"]),
        "ahead_before": int(before["ahead"]),
        "behind_before": int(before["behind"]),
        "ahead_after": int(after["ahead"]),
        "behind_after": int(after["behind"]),
        "status": status.stdout if status.ok else "",
        "message": (
            f"Pulled {before['upstream']} with --ff-only. "
            f"Ahead/behind changed from {before['ahead']}/{before['behind']} to {after['ahead']}/{after['behind']}."
            if result.ok
            else redact_git_text(result.stderr or result.stdout or "git pull --ff-only failed.")
        ),
    }


def preview_push_git_upstream(workspace: RunWorkspace) -> dict[str, object]:
    info = read_git_info(workspace)
    status = read_git_status(workspace)
    current = str(info["branch"]) if info["ok"] else ""
    if not info["ok"]:
        return {
            "ok": False,
            "remote": "",
            "branch": "",
            "current": "",
            "upstream": "",
            "ahead": 0,
            "behind": 0,
            "worktree_clean": False,
            "status": "",
            "message": str(info["message"]),
        }
    if not current:
        return {
            "ok": False,
            "remote": "",
            "branch": "",
            "current": "",
            "upstream": "",
            "ahead": int(info["ahead"]),
            "behind": int(info["behind"]),
            "worktree_clean": False,
            "status": status.stdout if status.ok else "",
            "message": "Cannot push while HEAD is detached.",
        }

    upstream = str(info["upstream"])
    upstream_parts = read_git_upstream_parts(workspace, current)
    clean = status.ok and not git_status_has_non_runtime_changes(status.stdout)
    if not upstream or not upstream_parts["ok"]:
        return {
            "ok": False,
            "remote": str(upstream_parts["remote"]),
            "branch": str(upstream_parts["branch"]),
            "current": current,
            "upstream": upstream,
            "ahead": int(info["ahead"]),
            "behind": int(info["behind"]),
            "worktree_clean": clean,
            "status": status.stdout if status.ok else "",
            "message": "Current branch has no upstream configured.",
        }
    if not clean:
        return {
            "ok": False,
            "remote": str(upstream_parts["remote"]),
            "branch": str(upstream_parts["branch"]),
            "current": current,
            "upstream": upstream,
            "ahead": int(info["ahead"]),
            "behind": int(info["behind"]),
            "worktree_clean": False,
            "status": status.stdout if status.ok else "",
            "message": "Working tree has uncommitted changes; commit or clean changes before pushing.",
        }

    ahead = int(info["ahead"])
    behind = int(info["behind"])
    if behind > 0:
        message = "Current branch is behind upstream; fetch and fast-forward pull before pushing."
        ok = False
    elif ahead == 0:
        message = "Current branch has no commits to push."
        ok = False
    else:
        message = f"Can push {ahead} commit(s) from {current} to {upstream}."
        ok = True

    return {
        "ok": ok,
        "remote": str(upstream_parts["remote"]),
        "branch": str(upstream_parts["branch"]),
        "current": current,
        "upstream": upstream,
        "ahead": ahead,
        "behind": behind,
        "worktree_clean": True,
        "status": status.stdout if status.ok else "",
        "message": message,
    }


def push_git_upstream(workspace: RunWorkspace) -> dict[str, object]:
    before = preview_push_git_upstream(workspace)
    if not before["ok"]:
        return {
            "ok": False,
            "remote": str(before["remote"]),
            "branch": str(before["branch"]),
            "current": str(before["current"]),
            "upstream": str(before["upstream"]),
            "ahead_before": int(before["ahead"]),
            "behind_before": int(before["behind"]),
            "status": str(before["status"]),
            "message": str(before["message"]),
        }

    result = run_git_mutation(workspace.root, ["push", str(before["remote"]), f"HEAD:{before['branch']}"])
    status = read_git_status(workspace)
    return {
        "ok": result.ok,
        "remote": str(before["remote"]),
        "branch": str(before["branch"]),
        "current": str(before["current"]),
        "upstream": str(before["upstream"]),
        "ahead_before": int(before["ahead"]),
        "behind_before": int(before["behind"]),
        "status": status.stdout if status.ok else "",
        "message": (
            f"Pushed {before['current']} to {before['upstream']}."
            if result.ok
            else redact_git_text(result.stderr or result.stdout or "git push failed.")
        ),
    }


def read_git_upstream_parts(workspace: RunWorkspace, branch: str) -> dict[str, object]:
    remote_result = run_readonly_git(workspace.root, ["config", f"branch.{branch}.remote"])
    merge_result = run_readonly_git(workspace.root, ["config", f"branch.{branch}.merge"])
    remote = remote_result.stdout.strip() if remote_result.ok else ""
    merge = merge_result.stdout.strip() if merge_result.ok else ""
    prefix = "refs/heads/"
    upstream_branch = merge[len(prefix) :] if merge.startswith(prefix) else merge
    return {
        "ok": bool(remote and upstream_branch),
        "remote": remote,
        "branch": upstream_branch,
    }


def select_git_fetch_remote(workspace: RunWorkspace, remote: str | None) -> dict[str, object]:
    git_probe = run_readonly_git(workspace.root, ["rev-parse", "--is-inside-work-tree"])
    if not git_probe.ok or git_probe.stdout.strip() != "true":
        return {"ok": False, "remote": remote or "", "remote_url": "", "message": git_probe.stderr or "Not a git repository."}

    remotes_result = run_readonly_git(workspace.root, ["remote", "-v"])
    remotes = parse_git_remotes(remotes_result.stdout if remotes_result.ok else "")
    fetch_remotes = [item for item in remotes if item.get("kind") == "fetch"]
    names = sorted({item["name"] for item in fetch_remotes})
    requested = remote.strip() if isinstance(remote, str) else ""
    if remote is not None and not requested:
        return {"ok": False, "remote": "", "remote_url": "", "message": "git_fetch remote must be non-empty when provided."}
    if requested and requested not in names:
        return {
            "ok": False,
            "remote": requested,
            "remote_url": "",
            "message": f"Git remote not found: {requested}.",
        }
    if not requested:
        if not names:
            return {"ok": False, "remote": "", "remote_url": "", "message": "No git remotes are configured."}
        if len(names) > 1:
            return {
                "ok": False,
                "remote": "",
                "remote_url": "",
                "message": "Multiple git remotes are configured; specify one remote.",
            }
        requested = names[0]

    remote_url = next((item["url"] for item in fetch_remotes if item["name"] == requested), "")
    return {"ok": True, "remote": requested, "remote_url": remote_url, "message": "Git remote selected."}


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


def read_git_diff(workspace: RunWorkspace, relative_path: str | None = None, staged: bool = False) -> GitCommandResult:
    args = ["diff"]
    if staged:
        args.append("--cached")
    if relative_path:
        resolve_inside_run(workspace.root, relative_path)
        args.extend(["--", relative_path])
    return run_readonly_git(workspace.root, args)


def read_git_diff_hunks(
    workspace: RunWorkspace,
    relative_path: str | None = None,
    staged: bool = False,
    max_hunks: int = 80,
    max_lines_per_hunk: int = 80,
) -> dict[str, object]:
    if max_hunks < 1:
        raise ValueError("max_hunks must be at least 1.")
    if max_hunks > 500:
        raise ValueError("max_hunks must be at most 500.")
    if max_lines_per_hunk < 1:
        raise ValueError("max_lines_per_hunk must be at least 1.")
    if max_lines_per_hunk > 500:
        raise ValueError("max_lines_per_hunk must be at most 500.")

    result = read_git_diff(workspace, relative_path, staged)
    hunks = parse_git_diff_hunks(result.stdout, max_hunks=max_hunks, max_lines_per_hunk=max_lines_per_hunk)
    return {
        "ok": result.ok,
        "hunks": hunks["hunks"],
        "total_hunks": hunks["total_hunks"],
        "truncated": bool(hunks["truncated"]),
        "path": relative_path,
        "staged": staged,
        "message": "Read git diff hunks." if result.ok else result.stderr or "git diff failed.",
    }


def parse_git_diff_hunks(diff: str, max_hunks: int = 80, max_lines_per_hunk: int = 80) -> dict[str, object]:
    hunks: list[dict[str, object]] = []
    total_hunks = 0
    current_file = ""
    current_hunk: dict[str, object] | None = None
    current_lines: list[str] = []
    lines_truncated = False

    def finish_hunk() -> None:
        nonlocal current_hunk, current_lines, lines_truncated
        if current_hunk is None:
            return
        current_hunk["lines"] = current_lines
        current_hunk["lines_truncated"] = lines_truncated
        if len(hunks) < max_hunks:
            hunks.append(current_hunk)
        current_hunk = None
        current_lines = []
        lines_truncated = False

    for line in diff.splitlines():
        if line.startswith("diff --git "):
            finish_hunk()
            current_file = parse_git_diff_file_path(line)
            continue
        hunk_match = re.match(r"^@@ -(\d+)(?:,(\d+))? \+(\d+)(?:,(\d+))? @@", line)
        if hunk_match:
            finish_hunk()
            total_hunks += 1
            old_start = int(hunk_match.group(1))
            old_count = int(hunk_match.group(2) or "1")
            new_start = int(hunk_match.group(3))
            new_count = int(hunk_match.group(4) or "1")
            current_hunk = {
                "file": current_file,
                "old_start": old_start,
                "old_count": old_count,
                "new_start": new_start,
                "new_count": new_count,
                "added": 0,
                "deleted": 0,
                "context": 0,
                "header": line,
            }
            current_lines = []
            lines_truncated = False
            continue
        if current_hunk is None:
            continue
        if line.startswith("+") and not line.startswith("+++"):
            current_hunk["added"] = int(current_hunk["added"]) + 1
        elif line.startswith("-") and not line.startswith("---"):
            current_hunk["deleted"] = int(current_hunk["deleted"]) + 1
        elif line.startswith(" "):
            current_hunk["context"] = int(current_hunk["context"]) + 1
        if len(current_lines) < max_lines_per_hunk:
            current_lines.append(line)
        else:
            lines_truncated = True

    finish_hunk()
    return {
        "hunks": hunks,
        "total_hunks": total_hunks,
        "truncated": total_hunks > len(hunks) or any(bool(hunk["lines_truncated"]) for hunk in hunks),
    }


def parse_git_diff_file_path(line: str) -> str:
    match = re.match(r"^diff --git a/(.*?) b/(.*)$", line)
    if not match:
        return ""
    return match.group(2)


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
            "config_ok": False,
            "files": [],
            "total_files": 0,
            "python": [],
            "python_total": 0,
            "python_truncated": False,
            "config": [],
            "config_total": 0,
            "config_truncated": False,
            "suggested_checks": [],
            "suggested_checks_total": 0,
            "suggested_checks_truncated": False,
            "diff_hunks": [],
            "diff_hunks_total": 0,
            "diff_hunks_truncated": False,
            "staged_diff_hunks": [],
            "staged_diff_hunks_total": 0,
            "staged_diff_hunks_truncated": False,
            "untracked_previews": [],
            "untracked_previews_total": 0,
            "untracked_previews_truncated": False,
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

    config_paths = [
        str(item["path"])
        for item in files
        if isinstance(item.get("path"), str) and config_format_for_path(str(item["path"])) is not None
    ]
    config_results, config_total = check_config_file_paths(workspace, config_paths, max_files=max_files)
    config_failed = sum(1 for item in config_results if not item["ok"])
    config_truncated = len(config_results) < config_total
    suggestions = suggest_project_checks(workspace, max_commands=min(max_files, 100))
    diff_hunks = read_git_diff_hunks(workspace, max_hunks=min(max_files, 100), max_lines_per_hunk=40)
    staged_diff_hunks = read_git_diff_hunks(workspace, staged=True, max_hunks=min(max_files, 100), max_lines_per_hunk=40)
    untracked_previews = read_untracked_file_previews(workspace, files, max_files=max_files, max_bytes=4000)

    diff_check_ok = diff_check.exit_code == 0
    staged_diff_check_ok = staged_diff_check.exit_code == 0
    python_ok = python_failed == 0
    config_ok = config_failed == 0
    ok = diff_check_ok and staged_diff_check_ok and python_ok and config_ok

    issues: list[str] = []
    if not diff_check_ok:
        issues.append("unstaged diff check failed")
    if not staged_diff_check_ok:
        issues.append("staged diff check failed")
    if not python_ok:
        issues.append(f"{python_failed} Python file(s) failed syntax check")
    if python_truncated:
        issues.append(f"Python syntax check truncated at {len(python_results)}/{python_total} file(s)")
    if not config_ok:
        issues.append(f"{config_failed} config file(s) failed syntax check")
    if config_truncated:
        issues.append(f"config syntax check truncated at {len(config_results)}/{config_total} file(s)")
    if len(files) > max_files:
        issues.append(f"changed file list truncated at {max_files}/{len(files)} file(s)")
    if issues:
        message = "Review found issue(s): " + "; ".join(issues) + "."
    else:
        message = (
            f"Review passed for {len(files)} changed file(s), "
            f"{python_total} Python file(s), and {config_total} config file(s)."
        )

    return {
        "ok": ok,
        "changes_ok": True,
        "diff_check_ok": diff_check_ok,
        "staged_diff_check_ok": staged_diff_check_ok,
        "python_ok": python_ok,
        "config_ok": config_ok,
        "files": files[:max_files],
        "total_files": len(files),
        "python": python_results,
        "python_total": python_total,
        "python_truncated": python_truncated,
        "config": config_results,
        "config_total": config_total,
        "config_truncated": config_truncated,
        "suggested_checks": suggestions["checks"],
        "suggested_checks_total": suggestions["total"],
        "suggested_checks_truncated": suggestions["truncated"],
        "diff_hunks": diff_hunks["hunks"],
        "diff_hunks_total": diff_hunks["total_hunks"],
        "diff_hunks_truncated": diff_hunks["truncated"],
        "staged_diff_hunks": staged_diff_hunks["hunks"],
        "staged_diff_hunks_total": staged_diff_hunks["total_hunks"],
        "staged_diff_hunks_truncated": staged_diff_hunks["truncated"],
        "untracked_previews": untracked_previews["previews"],
        "untracked_previews_total": untracked_previews["total"],
        "untracked_previews_truncated": untracked_previews["truncated"],
        "diff_check": diff_check_output,
        "staged_diff_check": staged_diff_check_output,
        "status": str(changes["status"]),
        "message": message,
    }


def read_untracked_file_previews(
    workspace: RunWorkspace,
    files: list[dict[str, object]],
    max_files: int = 200,
    max_bytes: int = 4000,
) -> dict[str, object]:
    paths = [
        str(item["path"])
        for item in files
        if bool(item.get("untracked")) and isinstance(item.get("path"), str)
    ]
    previews: list[dict[str, object]] = []
    for relative_path in paths[:max_files]:
        target = resolve_inside_run(workspace.root, relative_path)
        if not target.is_file():
            previews.append(
                {
                    "path": relative_path,
                    "size_bytes": 0,
                    "is_binary": False,
                    "content": "",
                    "truncated": False,
                    "message": f"Untracked path is not a file: {relative_path}",
                }
            )
            continue
        size_bytes = target.stat().st_size
        if detect_binary_file(target):
            previews.append(
                {
                    "path": relative_path,
                    "size_bytes": size_bytes,
                    "is_binary": True,
                    "content": "",
                    "truncated": False,
                    "message": "Binary untracked file preview omitted.",
                }
            )
            continue
        content = read_utf8_text_file(target, relative_path)
        content_bytes = len(content.encode("utf-8"))
        truncated = content_bytes > max_bytes
        if truncated:
            content = f"{truncate_utf8_text_bytes(content, max_bytes)}\n[file truncated]"
        previews.append(
            {
                "path": relative_path,
                "size_bytes": size_bytes,
                "is_binary": False,
                "content": content,
                "truncated": truncated,
                "message": "Read untracked file preview.",
            }
        )

    return {
        "previews": previews,
        "total": len(paths),
        "truncated": len(paths) > len(previews) or any(bool(item["truncated"]) for item in previews),
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

    suggestions: list[dict[str, object]] = []
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
    suggestions: list[dict[str, object]],
    command: str,
    cwd: str,
    source: str,
    reason: str,
) -> None:
    if any(item["command"] == command and item["cwd"] == cwd for item in suggestions):
        return
    missing_tool = missing_command_tool(command)
    suggestions.append(
        {
            "command": command,
            "cwd": cwd,
            "source": source,
            "reason": reason,
            "available": missing_tool is None,
            "missing_tool": missing_tool,
        }
    )


def missing_command_tool(command: str) -> str | None:
    try:
        parts = shlex.split(command)
    except ValueError:
        return None
    if not parts:
        return None

    executable = first_command_executable(parts)
    if not executable:
        return None
    if executable.startswith(("./", "../")):
        return None
    if executable in SHELL_BUILTINS:
        return None
    if shutil.which(executable):
        return None
    return executable


SHELL_BUILTINS = {
    "alias",
    "bg",
    "cd",
    "command",
    "echo",
    "eval",
    "exec",
    "exit",
    "export",
    "fg",
    "hash",
    "jobs",
    "printf",
    "pwd",
    "read",
    "set",
    "shift",
    "test",
    "type",
    "ulimit",
    "umask",
    "unalias",
    "unset",
}


def first_command_executable(parts: list[str]) -> str | None:
    for part in parts:
        if is_shell_assignment(part):
            continue
        return part
    return None


def is_shell_assignment(value: str) -> bool:
    name, separator, _rest = value.partition("=")
    return bool(separator) and bool(re.match(r"^[A-Za-z_][A-Za-z0-9_]*$", name))


def check_suggestion_sort_key(item: dict[str, object]) -> tuple[int, str, str]:
    command = str(item["command"])
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
    return (priority, str(item["cwd"]), base + command)


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


def stage_git_paths(workspace: RunWorkspace, paths: list[str]) -> dict[str, object]:
    normalized = normalize_git_index_paths(workspace, paths)
    result = run_git_mutation(workspace.root, ["add", "--", *normalized])
    status = read_git_status(workspace)
    return {
        "ok": result.ok,
        "paths": normalized,
        "status": status.stdout if status.ok else "",
        "message": f"Staged {len(normalized)} path(s)." if result.ok else result.stderr or "git add failed.",
    }


def preview_stage_git_paths(workspace: RunWorkspace, paths: list[str]) -> dict[str, object]:
    normalized = normalize_git_index_paths(workspace, paths)
    status = read_git_status(workspace)
    return {
        "ok": status.ok,
        "paths": normalized,
        "status": status.stdout if status.ok else "",
        "message": f"Can stage {len(normalized)} path(s)." if status.ok else status.stderr or "git status failed.",
    }


def unstage_git_paths(workspace: RunWorkspace, paths: list[str]) -> dict[str, object]:
    normalized = normalize_git_index_paths(workspace, paths)
    result = run_git_mutation(workspace.root, ["restore", "--staged", "--", *normalized])
    status = read_git_status(workspace)
    return {
        "ok": result.ok,
        "paths": normalized,
        "status": status.stdout if status.ok else "",
        "message": f"Unstaged {len(normalized)} path(s)." if result.ok else result.stderr or "git restore --staged failed.",
    }


def preview_unstage_git_paths(workspace: RunWorkspace, paths: list[str]) -> dict[str, object]:
    normalized = normalize_git_index_paths(workspace, paths)
    status = read_git_status(workspace)
    return {
        "ok": status.ok,
        "paths": normalized,
        "status": status.stdout if status.ok else "",
        "message": f"Can unstage {len(normalized)} path(s)." if status.ok else status.stderr or "git status failed.",
    }


def preview_restore_git_paths(workspace: RunWorkspace, paths: list[str]) -> dict[str, object]:
    normalized = normalize_git_index_paths(workspace, paths)
    tracked = validate_git_tracked_paths(workspace, normalized)
    status = read_git_status(workspace)
    if not tracked.ok:
        return {
            "ok": False,
            "paths": normalized,
            "diff": "",
            "status": status.stdout if status.ok else "",
            "message": tracked.stderr or "One or more paths are not tracked by git.",
        }

    diff = run_readonly_git(workspace.root, ["diff", "--", *normalized])
    if not diff.ok:
        return {
            "ok": False,
            "paths": normalized,
            "diff": "",
            "status": status.stdout if status.ok else "",
            "message": diff.stderr or "git diff failed.",
        }
    if not diff.stdout:
        return {
            "ok": False,
            "paths": normalized,
            "diff": "",
            "status": status.stdout if status.ok else "",
            "message": "No unstaged tracked changes to restore for the requested path(s).",
        }
    return {
        "ok": True,
        "paths": normalized,
        "diff": diff.stdout,
        "status": status.stdout if status.ok else "",
        "message": f"Can restore unstaged changes for {len(normalized)} tracked path(s).",
    }


def restore_git_paths(workspace: RunWorkspace, paths: list[str]) -> dict[str, object]:
    preview = preview_restore_git_paths(workspace, paths)
    if not preview["ok"]:
        return preview
    result = run_git_mutation(workspace.root, ["restore", "--", *list(preview["paths"])])
    status = read_git_status(workspace)
    return {
        "ok": result.ok,
        "paths": list(preview["paths"]),
        "diff": str(preview["diff"]),
        "status": status.stdout if status.ok else "",
        "message": f"Restored unstaged changes for {len(preview['paths'])} tracked path(s)." if result.ok else result.stderr or "git restore failed.",
    }


def validate_git_tracked_paths(workspace: RunWorkspace, paths: list[str]) -> GitCommandResult:
    return run_readonly_git(workspace.root, ["ls-files", "--error-unmatch", "--", *paths])


def read_git_stashes(workspace: RunWorkspace, max_entries: int = 20) -> dict[str, object]:
    if max_entries < 1:
        raise ValueError("max_entries must be at least 1.")
    if max_entries > 100:
        raise ValueError("max_entries must be at most 100.")

    result = run_readonly_git(workspace.root, ["stash", "list", "--format=%gd%x09%gs"])
    if not result.ok:
        return {"ok": False, "entries": [], "total": 0, "truncated": False, "message": result.stderr or "git stash list failed."}

    entries = parse_git_stash_list(result.stdout)
    shown = entries[:max_entries]
    return {
        "ok": True,
        "entries": shown,
        "total": len(entries),
        "truncated": len(shown) < len(entries),
        "message": f"Found {len(entries)} git stash entr{'y' if len(entries) == 1 else 'ies'}.",
    }


def preview_stash_git_changes(workspace: RunWorkspace, message: str | None = None, include_untracked: bool = False) -> dict[str, object]:
    stash_message = normalize_git_stash_message(message)
    status = read_git_status(workspace)
    if not status.ok:
        return {
            "ok": False,
            "message_text": stash_message,
            "include_untracked": include_untracked,
            "paths": [],
            "status": "",
            "diff": "",
            "message": status.stderr or "git status failed.",
        }

    tracked_paths, untracked_paths = git_stash_candidate_paths(status.stdout)
    paths = tracked_paths + (untracked_paths if include_untracked else [])
    if not paths:
        return {
            "ok": False,
            "message_text": stash_message,
            "include_untracked": include_untracked,
            "paths": [],
            "status": status.stdout,
            "diff": "",
            "message": "No stashable non-runtime changes found.",
        }

    diff = run_readonly_git(workspace.root, ["diff", "HEAD", "--", *tracked_paths]) if tracked_paths else GitCommandResult(True, "", "", 0)
    if not diff.ok:
        return {
            "ok": False,
            "message_text": stash_message,
            "include_untracked": include_untracked,
            "paths": paths,
            "status": status.stdout,
            "diff": "",
            "message": diff.stderr or "git diff failed.",
        }

    return {
        "ok": True,
        "message_text": stash_message,
        "include_untracked": include_untracked,
        "paths": paths,
        "status": status.stdout,
        "diff": diff.stdout,
        "message": f"Can stash {len(paths)} path(s).",
    }


def stash_git_changes(workspace: RunWorkspace, message: str | None = None, include_untracked: bool = False) -> dict[str, object]:
    preview = preview_stash_git_changes(workspace, message, include_untracked=include_untracked)
    if not preview["ok"]:
        return {
            "ok": False,
            "message_text": str(preview["message_text"]),
            "include_untracked": include_untracked,
            "stash_ref": "",
            "status": str(preview["status"]),
            "diff": str(preview["diff"]),
            "message": str(preview["message"]),
        }

    before = read_git_stashes(workspace, max_entries=1)
    before_ref = str(before["entries"][0]["name"]) if before["ok"] and before["entries"] else ""
    args = ["stash", "push", "-m", str(preview["message_text"])]
    if include_untracked:
        args.append("--include-untracked")
    args.extend(["--", *list(preview["paths"])])
    result = run_git_mutation(workspace.root, args)
    after = read_git_stashes(workspace, max_entries=1)
    after_ref = str(after["entries"][0]["name"]) if after["ok"] and after["entries"] else ""
    status = read_git_status(workspace)
    created_ref = after_ref if result.ok and after_ref != before_ref else after_ref
    return {
        "ok": result.ok,
        "message_text": str(preview["message_text"]),
        "include_untracked": include_untracked,
        "stash_ref": created_ref,
        "status": status.stdout if status.ok else "",
        "diff": str(preview["diff"]),
        "message": f"Stashed changes as {created_ref or 'a new stash'}." if result.ok else result.stderr or "git stash push failed.",
    }


def preview_apply_git_stash(workspace: RunWorkspace, stash_ref: str) -> dict[str, object]:
    normalized = validate_git_stash_ref(stash_ref)
    status = read_git_status(workspace)
    if not status.ok:
        return {
            "ok": False,
            "stash_ref": normalized,
            "worktree_clean": False,
            "patch": "",
            "status": "",
            "message": status.stderr or "git status failed.",
        }
    clean = not git_status_has_non_runtime_changes(status.stdout)
    patch = run_readonly_git(workspace.root, ["stash", "show", "--patch", normalized])
    if not patch.ok:
        return {
            "ok": False,
            "stash_ref": normalized,
            "worktree_clean": clean,
            "patch": "",
            "status": status.stdout,
            "message": patch.stderr or f"Git stash not found: {normalized}.",
        }
    if not clean:
        return {
            "ok": False,
            "stash_ref": normalized,
            "worktree_clean": False,
            "patch": patch.stdout,
            "status": status.stdout,
            "message": "Working tree has uncommitted changes; commit, stash, or restore changes before applying a stash.",
        }
    return {
        "ok": True,
        "stash_ref": normalized,
        "worktree_clean": True,
        "patch": patch.stdout,
        "status": status.stdout,
        "message": f"Can apply {normalized}.",
    }


def apply_git_stash(workspace: RunWorkspace, stash_ref: str) -> dict[str, object]:
    preview = preview_apply_git_stash(workspace, stash_ref)
    if not preview["ok"]:
        return {
            "ok": False,
            "stash_ref": str(preview["stash_ref"]),
            "patch": str(preview["patch"]),
            "status": str(preview["status"]),
            "message": str(preview["message"]),
        }
    result = run_git_mutation(workspace.root, ["stash", "apply", str(preview["stash_ref"])])
    status = read_git_status(workspace)
    return {
        "ok": result.ok,
        "stash_ref": str(preview["stash_ref"]),
        "patch": str(preview["patch"]),
        "status": status.stdout if status.ok else "",
        "message": f"Applied {preview['stash_ref']}." if result.ok else result.stderr or "git stash apply failed.",
    }


def preview_drop_git_stash(workspace: RunWorkspace, stash_ref: str) -> dict[str, object]:
    normalized = validate_git_stash_ref(stash_ref)
    stashes = read_git_stashes(workspace, max_entries=100)
    if not stashes["ok"]:
        return {
            "ok": False,
            "stash_ref": normalized,
            "patch": "",
            "summary": "",
            "message": str(stashes["message"]),
        }
    summary = ""
    for entry in list(stashes["entries"]):
        if str(entry["name"]) == normalized:
            summary = str(entry["summary"])
            break
    if not summary:
        return {
            "ok": False,
            "stash_ref": normalized,
            "patch": "",
            "summary": "",
            "message": f"Git stash not found: {normalized}.",
        }

    patch = run_readonly_git(workspace.root, ["stash", "show", "--patch", normalized])
    if not patch.ok:
        return {
            "ok": False,
            "stash_ref": normalized,
            "patch": "",
            "summary": summary,
            "message": patch.stderr or f"Git stash not found: {normalized}.",
        }
    return {
        "ok": True,
        "stash_ref": normalized,
        "patch": patch.stdout,
        "summary": summary,
        "message": f"Can drop {normalized}.",
    }


def drop_git_stash(workspace: RunWorkspace, stash_ref: str) -> dict[str, object]:
    preview = preview_drop_git_stash(workspace, stash_ref)
    if not preview["ok"]:
        return {
            "ok": False,
            "stash_ref": str(preview["stash_ref"]),
            "patch": str(preview["patch"]),
            "summary": str(preview["summary"]),
            "remaining_total": int(read_git_stashes(workspace, max_entries=100).get("total", 0)),
            "message": str(preview["message"]),
        }
    result = run_git_mutation(workspace.root, ["stash", "drop", str(preview["stash_ref"])])
    remaining = read_git_stashes(workspace, max_entries=100)
    return {
        "ok": result.ok,
        "stash_ref": str(preview["stash_ref"]),
        "patch": str(preview["patch"]),
        "summary": str(preview["summary"]),
        "remaining_total": int(remaining["total"]) if remaining["ok"] else 0,
        "message": f"Dropped {preview['stash_ref']}." if result.ok else result.stderr or "git stash drop failed.",
    }


def parse_git_stash_list(output: str) -> list[dict[str, str]]:
    entries: list[dict[str, str]] = []
    for line in output.splitlines():
        if not line.strip():
            continue
        name, _separator, summary = line.partition("\t")
        entries.append({"name": name.strip(), "summary": summary.strip()})
    return entries


def validate_git_stash_ref(stash_ref: str) -> str:
    normalized = stash_ref.strip() if isinstance(stash_ref, str) else ""
    if not normalized:
        raise ValueError("stash_ref must be a non-empty string.")
    if not re.fullmatch(r"stash@\{\d+\}", normalized):
        raise ValueError("stash_ref must look like stash@{0}.")
    return normalized


def normalize_git_stash_message(message: str | None) -> str:
    if message is None:
        return "vibeagent stash"
    normalized = message.strip()
    if not normalized:
        raise ValueError("message must be non-empty when provided.")
    if len(normalized) > 200:
        raise ValueError("message must be at most 200 characters.")
    return normalized


def git_stash_candidate_paths(status: str) -> tuple[list[str], list[str]]:
    tracked: list[str] = []
    untracked: list[str] = []
    for line in status.splitlines():
        if len(line) < 4:
            continue
        raw_path = line[3:]
        if " -> " in raw_path:
            raw_path = raw_path.rsplit(" -> ", 1)[1]
        if raw_path == ".vibeagent" or raw_path.startswith(".vibeagent/"):
            continue
        if line.startswith("?? "):
            untracked.append(raw_path)
        else:
            tracked.append(raw_path)
    return dedupe_paths(tracked), dedupe_paths(untracked)


def dedupe_paths(paths: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for path in paths:
        if path not in seen:
            seen.add(path)
            result.append(path)
    return result


def commit_staged_changes(workspace: RunWorkspace, message: str) -> dict[str, object]:
    message = message.strip()
    if not message:
        raise ValueError("message must be a non-empty string.")
    if len(message) > 500:
        raise ValueError("message must be at most 500 characters.")

    staged_probe = run_readonly_git(workspace.root, ["diff", "--cached", "--quiet"])
    if staged_probe.exit_code == 0:
        return {
            "ok": False,
            "head_before": read_git_head(workspace),
            "head_after": read_git_head(workspace),
            "status": read_git_status(workspace).stdout,
            "message": "No staged changes to commit.",
        }

    head_before = read_git_head(workspace)
    result = run_git_mutation(workspace.root, ["commit", "--no-verify", "-m", message])
    head_after = read_git_head(workspace)
    status = read_git_status(workspace)
    return {
        "ok": result.ok,
        "head_before": head_before,
        "head_after": head_after,
        "status": status.stdout if status.ok else "",
        "message": f"Committed staged changes: {head_after}." if result.ok else result.stderr or "git commit failed.",
    }


def preview_commit_staged_changes(workspace: RunWorkspace, message: str) -> dict[str, object]:
    message = message.strip()
    if not message:
        raise ValueError("message must be a non-empty string.")
    if len(message) > 500:
        raise ValueError("message must be at most 500 characters.")

    head = read_git_head(workspace)
    status = read_git_status(workspace)
    staged_probe = run_readonly_git(workspace.root, ["diff", "--cached", "--quiet"])
    if staged_probe.exit_code == 0:
        return {
            "ok": False,
            "head_before": head,
            "head_after": head,
            "status": status.stdout if status.ok else "",
            "message": "No staged changes to commit.",
        }
    if staged_probe.exit_code == 1:
        return {
            "ok": True,
            "head_before": head,
            "head_after": head,
            "status": status.stdout if status.ok else "",
            "message": "Staged changes can be committed.",
        }
    return {
        "ok": False,
        "head_before": head,
        "head_after": head,
        "status": status.stdout if status.ok else "",
        "message": staged_probe.stderr or "git diff --cached failed.",
    }


def preview_switch_git_branch(workspace: RunWorkspace, branch: str, create: bool = False) -> dict[str, object]:
    normalized = validate_git_branch_name(workspace, branch)
    current = read_git_current_branch(workspace)
    status = read_git_status(workspace)
    if not status.ok:
        return {
            "ok": False,
            "branch": normalized,
            "create": create,
            "current_before": current,
            "branch_exists": False,
            "worktree_clean": False,
            "status": "",
            "message": status.stderr or "git status failed.",
        }

    clean = not git_status_has_non_runtime_changes(status.stdout)
    exists = git_branch_exists(workspace, normalized)
    ok = True
    if not clean:
        ok = False
        message = "Working tree has uncommitted changes; commit or clean changes before switching branches."
    elif create and exists:
        ok = False
        message = f"Branch already exists: {normalized}."
    elif not create and not exists:
        ok = False
        message = f"Branch does not exist: {normalized}."
    elif create:
        message = f"Can create and switch to branch {normalized}."
    else:
        message = f"Can switch to branch {normalized}."
    return {
        "ok": ok,
        "branch": normalized,
        "create": create,
        "current_before": current,
        "branch_exists": exists,
        "worktree_clean": clean,
        "status": status.stdout,
        "message": message,
    }


def switch_git_branch(workspace: RunWorkspace, branch: str, create: bool = False) -> dict[str, object]:
    preview = preview_switch_git_branch(workspace, branch, create=create)
    current_before = str(preview["current_before"])
    if not bool(preview["ok"]):
        return {
            "ok": False,
            "branch": str(preview["branch"]),
            "create": create,
            "current_before": current_before,
            "current_after": current_before,
            "status": str(preview["status"]),
            "message": str(preview["message"]),
        }

    args = ["switch"]
    if create:
        args.append("-c")
    args.append(str(preview["branch"]))
    result = run_git_mutation(workspace.root, args)
    current_after = read_git_current_branch(workspace)
    status = read_git_status(workspace)
    return {
        "ok": result.ok,
        "branch": str(preview["branch"]),
        "create": create,
        "current_before": current_before,
        "current_after": current_after,
        "status": status.stdout if status.ok else "",
        "message": (
            f"Switched to branch {current_after or preview['branch']}."
            if result.ok
            else result.stderr or "git switch failed."
        ),
    }


def validate_git_branch_name(workspace: RunWorkspace, branch: str) -> str:
    normalized = branch.strip()
    if not normalized:
        raise ValueError("branch must be a non-empty string.")
    if len(normalized) > 200:
        raise ValueError("branch must be at most 200 characters.")
    result = run_readonly_git(workspace.root, ["check-ref-format", "--branch", normalized])
    if not result.ok:
        raise ValueError(result.stderr.strip() or f"Invalid git branch name: {normalized}")
    return normalized


def git_branch_exists(workspace: RunWorkspace, branch: str) -> bool:
    result = run_readonly_git(workspace.root, ["show-ref", "--verify", "--quiet", f"refs/heads/{branch}"])
    return result.exit_code == 0


def read_git_current_branch(workspace: RunWorkspace) -> str:
    result = run_readonly_git(workspace.root, ["branch", "--show-current"])
    return result.stdout.strip() if result.ok else ""


def git_status_has_non_runtime_changes(status: str) -> bool:
    for line in status.splitlines():
        path = line[3:] if len(line) > 3 else line
        if path == ".vibeagent" or path.startswith(".vibeagent/"):
            continue
        return True
    return False


def read_git_head(workspace: RunWorkspace) -> str:
    result = run_readonly_git(workspace.root, ["rev-parse", "--short", "HEAD"])
    return result.stdout.strip() if result.ok else ""


def normalize_git_index_paths(workspace: RunWorkspace, paths: list[str]) -> list[str]:
    if not paths:
        raise ValueError("paths must contain at least one path.")
    if len(paths) > 100:
        raise ValueError("paths must contain at most 100 paths.")

    normalized: list[str] = []
    seen: set[str] = set()
    for path in paths:
        if not isinstance(path, str) or not path.strip():
            raise ValueError("paths must contain non-empty strings.")
        raw = path.strip()
        resolve_inside_run(workspace.root, raw)
        if raw not in seen:
            seen.add(raw)
            normalized.append(raw)
    return normalized


def read_project_file(
    workspace: RunWorkspace,
    relative_path: str,
    max_bytes: int = 20_000,
    start_line: int | None = None,
    line_count: int | None = None,
) -> str:
    return str(
        read_project_file_result(
            workspace,
            relative_path,
            max_bytes=max_bytes,
            start_line=start_line,
            line_count=line_count,
        )["content"]
    )


def read_project_file_result(
    workspace: RunWorkspace,
    relative_path: str,
    max_bytes: int = 20_000,
    start_line: int | None = None,
    line_count: int | None = None,
) -> dict[str, object]:
    if max_bytes < 1:
        raise ValueError("max_bytes must be at least 1.")
    if max_bytes > 200_000:
        raise ValueError("max_bytes must be at most 200000.")
    target = resolve_inside_run(workspace.root, relative_path)
    if not target.is_file():
        raise ValueError(f"File does not exist: {relative_path}")
    content = read_utf8_text_file(target, relative_path)
    total_bytes = len(content.encode("utf-8"))
    if start_line is not None:
        excerpt = format_line_excerpt(content, start_line, line_count or 200)
        return {
            "content": excerpt,
            "truncated": False,
            "total_bytes": total_bytes,
            "max_bytes": max_bytes,
        }
    if total_bytes <= max_bytes:
        return {
            "content": content,
            "truncated": False,
            "total_bytes": total_bytes,
            "max_bytes": max_bytes,
        }
    return {
        "content": f"{truncate_utf8_text_bytes(content, max_bytes)}\n[file truncated]",
        "truncated": True,
        "total_bytes": total_bytes,
        "max_bytes": max_bytes,
    }


def truncate_utf8_text_bytes(content: str, max_bytes: int) -> str:
    return content.encode("utf-8")[:max_bytes].decode("utf-8", errors="ignore")


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


def read_code_outline(workspace: RunWorkspace, relative_path: str, max_symbols: int = 200) -> dict[str, object]:
    if max_symbols < 1:
        raise ValueError("max_symbols must be at least 1.")
    if max_symbols > 1000:
        raise ValueError("max_symbols must be at most 1000.")

    target = resolve_inside_run(workspace.root, relative_path)
    if not target.is_file():
        raise ValueError(f"File does not exist: {relative_path}")
    suffix = target.suffix.lower()
    if suffix == ".py":
        outline = read_python_symbol_outline(workspace, relative_path, max_symbols=max_symbols)
        return {
            **outline,
            "language": "python",
        }

    content = read_utf8_text_file(target, relative_path)
    language = code_language_for_path(target)
    symbols, imports = collect_generic_code_outline(content, language, max_symbols=max_symbols)
    return {
        "path": relative_path,
        "ok": True,
        "language": language,
        "symbols": symbols,
        "imports": imports,
        "message": f"Found {len(symbols)} symbol(s) and {len(imports)} import(s).",
    }


def code_language_for_path(path: Path) -> str:
    suffix = path.suffix.lower()
    return {
        ".py": "python",
        ".js": "javascript",
        ".jsx": "javascript",
        ".mjs": "javascript",
        ".cjs": "javascript",
        ".ts": "typescript",
        ".tsx": "typescript",
        ".go": "go",
        ".rs": "rust",
        ".java": "java",
        ".kt": "kotlin",
        ".c": "c",
        ".h": "c",
        ".cc": "cpp",
        ".cpp": "cpp",
        ".cxx": "cpp",
        ".hpp": "cpp",
    }.get(suffix, "text")


def supports_code_outline_path(path: str | Path) -> bool:
    return code_language_for_path(Path(path)) != "text"


def collect_generic_code_outline(content: str, language: str, max_symbols: int = 200) -> tuple[list[dict[str, object]], list[str]]:
    symbols: list[dict[str, object]] = []
    imports: list[str] = []
    for line_number, raw_line in enumerate(content.splitlines(), start=1):
        line = raw_line.strip()
        if not line or line.startswith(("//", "#")):
            continue
        if is_generic_import_line(line, language):
            imports.append(f"{line_number}: {line}")
            continue
        for kind, name in generic_symbol_matches(line, language):
            symbols.append({"name": name, "kind": kind, "line": line_number, "end_line": None, "parent": None})
            if len(symbols) >= max_symbols:
                return symbols, imports
    return symbols, imports


def inspect_code_dependencies(
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

    files = [
        path
        for path in list_search_files(workspace, relative_path)
        if supports_code_outline_path(path) and code_language_for_path(Path(path)) != "python"
    ]
    results: list[dict[str, object]] = []
    remaining_imports = max_imports
    for relative in files[:max_files]:
        target = resolve_inside_run(workspace.root, relative)
        language = code_language_for_path(target)
        if remaining_imports <= 0:
            results.append(
                {
                    "path": relative,
                    "ok": False,
                    "language": language,
                    "imports": [],
                    "dependencies": [],
                    "message": "Import result limit reached.",
                }
            )
            continue
        try:
            content = read_utf8_text_file(target, relative)
            imports = collect_code_imports(content, language, max_imports=remaining_imports)
            remaining_imports -= len(imports)
            dependencies = sorted({str(item["source"]) for item in imports if str(item["source"])})
            results.append(
                {
                    "path": relative,
                    "ok": True,
                    "language": language,
                    "imports": imports,
                    "dependencies": dependencies,
                    "message": f"Found {len(imports)} import(s) and {len(dependencies)} dependency source(s).",
                }
            )
        except ValueError as error:
            results.append(
                {
                    "path": relative,
                    "ok": False,
                    "language": language,
                    "imports": [],
                    "dependencies": [],
                    "message": str(error),
                }
            )
    return results, len(files)


def find_code_references(
    workspace: RunWorkspace,
    symbol: str,
    relative_path: str | None = None,
    max_matches: int = 200,
) -> tuple[list[dict[str, object]], int]:
    symbol = symbol.strip()
    if not symbol:
        raise ValueError("Code reference symbol must not be empty.")
    if "\n" in symbol or "\r" in symbol:
        raise ValueError("Code reference symbol must be a single-line string.")
    if max_matches < 1:
        raise ValueError("max_matches must be at least 1.")
    if max_matches > 500:
        raise ValueError("max_matches must be at most 500.")

    pattern = build_code_reference_pattern(symbol)
    matches: list[dict[str, object]] = []
    total = 0
    for relative in list_search_files(workspace, relative_path):
        language = code_language_for_path(Path(relative))
        if language == "python" or language == "text":
            continue
        target = resolve_inside_run(workspace.root, relative)
        try:
            content = read_utf8_text_file(target, relative)
        except ValueError:
            continue
        for line_number, line in enumerate(content.splitlines(), start=1):
            for match in pattern.finditer(line):
                total += 1
                if len(matches) < max_matches:
                    matches.append(
                        {
                            "path": relative,
                            "language": language,
                            "line": line_number,
                            "column": match.start() + 1,
                            "symbol": symbol,
                            "context": line.strip(),
                        }
                    )
    return matches, total


def find_code_definitions(
    workspace: RunWorkspace,
    symbol: str,
    relative_path: str | None = None,
    max_matches: int = 50,
    max_lines: int = 80,
) -> tuple[list[dict[str, object]], int, list[str]]:
    symbol = symbol.strip()
    if not symbol:
        raise ValueError("Code definition symbol must not be empty.")
    if "\n" in symbol or "\r" in symbol:
        raise ValueError("Code definition symbol must be a single-line string.")
    if max_matches < 1:
        raise ValueError("max_matches must be at least 1.")
    if max_matches > 200:
        raise ValueError("max_matches must be at most 200.")
    if max_lines < 1:
        raise ValueError("max_lines must be at least 1.")
    if max_lines > 500:
        raise ValueError("max_lines must be at most 500.")

    definitions: list[dict[str, object]] = []
    total = 0
    errors: list[str] = []
    for relative in list_search_files(workspace, relative_path):
        language = code_language_for_path(Path(relative))
        if language == "python" or language == "text":
            continue
        try:
            outline = read_code_outline(workspace, relative, max_symbols=1000)
            symbols = list(outline["symbols"])
            target = resolve_inside_run(workspace.root, relative)
            content = read_utf8_text_file(target, relative)
        except ValueError as error:
            errors.append(str(error))
            continue
        lines = content.splitlines()
        for item in symbols:
            if str(item.get("name")) != symbol:
                continue
            total += 1
            if len(definitions) >= max_matches:
                continue
            line = int(item["line"])
            excerpt_lines = lines[line - 1 : line - 1 + max_lines]
            end_line = line + len(excerpt_lines) - 1
            definitions.append(
                {
                    "path": relative,
                    "language": language,
                    "name": symbol,
                    "kind": str(item["kind"]),
                    "line": line,
                    "end_line": end_line,
                    "content": "\n".join(excerpt_lines),
                    "truncated": len(lines) > end_line,
                    "message": f"Found {symbol} definition at line {line}.",
                }
            )
    return definitions, total, errors


def build_code_reference_pattern(symbol: str) -> re.Pattern[str]:
    escaped = re.escape(symbol)
    if re.match(r"^[A-Za-z_$][A-Za-z0-9_$]*$", symbol):
        return re.compile(rf"(?<![A-Za-z0-9_$]){escaped}(?![A-Za-z0-9_$])")
    return re.compile(escaped)


def collect_code_imports(content: str, language: str, max_imports: int = 500) -> list[dict[str, object]]:
    imports: list[dict[str, object]] = []
    in_go_import_block = False
    for line_number, raw_line in enumerate(content.splitlines(), start=1):
        line = raw_line.strip()
        if not line or line.startswith(("//", "#")) and not line.startswith("#include"):
            continue
        if language == "go":
            if line == "import (":
                in_go_import_block = True
                continue
            if in_go_import_block and line == ")":
                in_go_import_block = False
                continue
            parsed = parse_go_import_line(line, in_go_import_block)
        else:
            parsed = parse_code_import_line(line, language)
        if parsed is None:
            continue
        imports.append({"line": line_number, **parsed, "raw": line})
        if len(imports) >= max_imports:
            break
    return imports


def parse_code_import_line(line: str, language: str) -> dict[str, str] | None:
    if language in {"javascript", "typescript"}:
        side_effect = re.match(r"^import\s+['\"]([^'\"]+)['\"]", line)
        if side_effect:
            return {"kind": "import", "source": side_effect.group(1)}
        imported = re.match(r"^import\b.+?\bfrom\s+['\"]([^'\"]+)['\"]", line)
        if imported:
            return {"kind": "import", "source": imported.group(1)}
        exported = re.match(r"^export\b.+?\bfrom\s+['\"]([^'\"]+)['\"]", line)
        if exported:
            return {"kind": "export", "source": exported.group(1)}
    if language == "rust":
        match = re.match(r"^(?:pub\s+)?use\s+(.+?);?$", line)
        if match:
            return {"kind": "use", "source": match.group(1).rstrip(";")}
    if language in {"java", "kotlin"}:
        package = re.match(r"^package\s+([A-Za-z_][\w.]*)", line)
        if package:
            return {"kind": "package", "source": package.group(1)}
        imported = re.match(r"^import\s+(?:static\s+)?([A-Za-z_][\w.*]*)", line)
        if imported:
            return {"kind": "import", "source": imported.group(1)}
    if language in {"c", "cpp"}:
        include = re.match(r"^#include\s+([<\"].+[>\"])", line)
        if include:
            return {"kind": "include", "source": include.group(1)}
    return None


def parse_go_import_line(line: str, in_block: bool = False) -> dict[str, str] | None:
    if in_block:
        match = re.match(r"^(?:[._A-Za-z][\w.]*\s+)?\"([^\"]+)\"", line)
        if match:
            return {"kind": "import", "source": match.group(1)}
        return None
    imported = re.match(r"^import\s+(?:[._A-Za-z][\w.]*\s+)?\"([^\"]+)\"", line)
    if imported:
        return {"kind": "import", "source": imported.group(1)}
    return None


def is_generic_import_line(line: str, language: str) -> bool:
    if language in {"javascript", "typescript"}:
        return line.startswith("import ") or line.startswith("export ") and " from " in line
    if language == "go":
        return line.startswith("import ")
    if language == "rust":
        return line.startswith("use ")
    if language in {"java", "kotlin"}:
        return line.startswith("import ") or line.startswith("package ")
    if language in {"c", "cpp"}:
        return line.startswith("#include")
    return False


def generic_symbol_matches(line: str, language: str) -> list[tuple[str, str]]:
    matches: list[tuple[str, str]] = []
    if language in {"javascript", "typescript"}:
        patterns = [
            (r"^(?:export\s+)?(?:default\s+)?class\s+([A-Za-z_$][\w$]*)", "class"),
            (r"^(?:export\s+)?(?:async\s+)?function\s+([A-Za-z_$][\w$]*)", "function"),
            (r"^(?:export\s+)?(?:const|let|var)\s+([A-Za-z_$][\w$]*)\s*=\s*(?:async\s*)?(?:\([^)]*\)|[A-Za-z_$][\w$]*)\s*=>", "function"),
            (r"^(?:export\s+)?(?:interface|type)\s+([A-Za-z_$][\w$]*)", "type"),
        ]
    elif language == "go":
        patterns = [
            (r"^func\s+(?:\([^)]*\)\s*)?([A-Za-z_][A-Za-z0-9_]*)\s*\(", "function"),
            (r"^type\s+([A-Za-z_][A-Za-z0-9_]*)\s+(?:struct|interface)\b", "type"),
        ]
    elif language == "rust":
        patterns = [
            (r"^(?:pub\s+)?(?:async\s+)?fn\s+([A-Za-z_][A-Za-z0-9_]*)\s*\(", "function"),
            (r"^(?:pub\s+)?(?:struct|enum|trait)\s+([A-Za-z_][A-Za-z0-9_]*)", "type"),
            (r"^impl(?:<[^>]+>)?\s+([A-Za-z_][A-Za-z0-9_]*)", "impl"),
        ]
    elif language in {"java", "kotlin"}:
        patterns = [
            (r"^(?:public|private|protected|internal|open|final|abstract|\s)*\s*(?:class|interface|enum)\s+([A-Za-z_][A-Za-z0-9_]*)", "type"),
            (r"^(?:public|private|protected|static|final|synchronized|abstract|\s)+[\w<>\[\], ?]+\s+([A-Za-z_][A-Za-z0-9_]*)\s*\(", "function"),
            (r"^fun\s+([A-Za-z_][A-Za-z0-9_]*)\s*\(", "function"),
        ]
    elif language in {"c", "cpp"}:
        patterns = [
            (r"^(?:class|struct|enum)\s+([A-Za-z_][A-Za-z0-9_]*)", "type"),
            (r"^[A-Za-z_][\w:<>\*&\s]+\s+([A-Za-z_][A-Za-z0-9_]*)\s*\([^;]*\)\s*(?:\{|$)", "function"),
        ]
    else:
        patterns = []

    for pattern, kind in patterns:
        match = re.match(pattern, line)
        if match:
            matches.append((kind, match.group(1)))
    return matches


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


def check_config_syntax(
    workspace: RunWorkspace,
    relative_path: str | None = None,
    max_files: int = 200,
) -> tuple[list[dict[str, object]], int]:
    if max_files < 1:
        raise ValueError("max_files must be at least 1.")
    if max_files > 500:
        raise ValueError("max_files must be at most 500.")

    files = [path for path in list_search_files(workspace, relative_path) if config_format_for_path(path) is not None]
    results: list[dict[str, object]] = []
    for relative in files[:max_files]:
        target = resolve_inside_run(workspace.root, relative)
        config_format = config_format_for_path(relative) or "unknown"
        try:
            content = read_utf8_text_file(target, relative)
            if config_format == "json":
                json.loads(content)
            elif config_format == "toml":
                tomllib.loads(content)
            results.append(
                {
                    "path": relative,
                    "ok": True,
                    "format": config_format,
                    "line": None,
                    "column": None,
                    "message": "Syntax OK.",
                }
            )
        except json.JSONDecodeError as error:
            results.append(
                {
                    "path": relative,
                    "ok": False,
                    "format": config_format,
                    "line": error.lineno,
                    "column": error.colno,
                    "message": f"JSON syntax error: {error.msg}",
                }
            )
        except tomllib.TOMLDecodeError as error:
            results.append(
                {
                    "path": relative,
                    "ok": False,
                    "format": config_format,
                    "line": None,
                    "column": None,
                    "message": f"TOML syntax error: {error}",
                }
            )
        except ValueError as error:
            results.append(
                {
                    "path": relative,
                    "ok": False,
                    "format": config_format,
                    "line": None,
                    "column": None,
                    "message": str(error),
                }
            )
    return results, len(files)


def config_format_for_path(path: str | Path) -> str | None:
    suffix = Path(path).suffix.lower()
    if suffix == ".json":
        return "json"
    if suffix == ".toml":
        return "toml"
    return None


def check_config_file_paths(
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
        if relative in seen or config_format_for_path(relative) is None:
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
        scoped_results, _total = check_config_syntax(workspace, relative, max_files=1)
        results.extend(scoped_results)
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
    target, after, diff, definition = preview_replace_python_definition(
        workspace,
        symbol,
        new_content,
        relative_path=relative_path,
    )
    target.write_text(after, encoding="utf-8")
    return target, diff, definition


def preview_replace_python_definition(
    workspace: RunWorkspace,
    symbol: str,
    new_content: str,
    relative_path: str | None = None,
) -> tuple[Path, str, str, dict[str, object]]:
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

    return target, after, build_simple_diff(path, before, after), definition


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


def preview_python_rename(
    workspace: RunWorkspace,
    symbol: str,
    new_name: str,
    relative_path: str | None = None,
    max_files: int = 100,
    max_replacements: int = 500,
) -> dict[str, object]:
    symbol = symbol.strip()
    new_name = new_name.strip()
    identifier_pattern = r"^[A-Za-z_][A-Za-z0-9_]*$"
    if not re.match(identifier_pattern, symbol):
        raise ValueError("Python rename symbol must be a simple identifier.")
    if not re.match(identifier_pattern, new_name):
        raise ValueError("Python rename new_name must be a simple identifier.")
    if symbol == new_name:
        raise ValueError("Python rename new_name must be different from symbol.")
    if max_files < 1:
        raise ValueError("max_files must be at least 1.")
    if max_files > 500:
        raise ValueError("max_files must be at most 500.")
    if max_replacements < 1:
        raise ValueError("max_replacements must be at least 1.")
    if max_replacements > 2000:
        raise ValueError("max_replacements must be at most 2000.")

    files = [path for path in list_search_files(workspace, relative_path) if path.endswith(".py")]
    preview_files: list[dict[str, object]] = []
    total_replacements = 0
    errors: list[str] = []
    remaining = max_replacements
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

        lines = content.splitlines(keepends=True)
        replacements = collect_python_rename_replacements(tree, symbol, new_name, relative, lines)
        if not replacements:
            continue
        total_replacements += len(replacements)
        shown_replacements = replacements[:remaining]
        remaining = max(0, remaining - len(shown_replacements))
        if not shown_replacements:
            continue
        updated = apply_python_rename_replacements(content, shown_replacements)
        preview_files.append(
            {
                "path": relative,
                "replacements": shown_replacements,
                "diff": build_simple_diff(relative, content, updated),
                "truncated": len(shown_replacements) < len(replacements),
            }
        )

    return {
        "ok": True,
        "symbol": symbol,
        "new_name": new_name,
        "path": relative_path,
        "files": preview_files,
        "total_replacements": total_replacements,
        "total_files": len(files),
        "truncated": total_replacements > max_replacements,
        "errors": errors,
        "message": f"Found {total_replacements} Python rename replacement(s) across {len(files)} file(s).",
    }


def apply_python_rename(
    workspace: RunWorkspace,
    symbol: str,
    new_name: str,
    relative_path: str | None = None,
    max_files: int = 100,
    max_replacements: int = 2000,
) -> dict[str, object]:
    preview = preview_python_rename(
        workspace,
        symbol,
        new_name,
        relative_path=relative_path,
        max_files=max_files,
        max_replacements=max_replacements,
    )
    if preview["errors"]:
        raise ValueError(f"Python rename skipped {len(preview['errors'])} file(s); fix syntax/read errors first.")
    if int(preview["total_files"]) > max_files:
        raise ValueError(f"Python rename scope has {preview['total_files']} file(s); max_files is {max_files}.")
    if bool(preview["truncated"]):
        raise ValueError(f"Python rename has more than {max_replacements} replacement(s).")
    if int(preview["total_replacements"]) == 0:
        raise ValueError(f"Python rename found no replacements for {symbol}.")

    prepared: list[tuple[Path, str, str, str]] = []
    for file in list(preview["files"]):
        relative = str(file["path"])
        target = resolve_inside_run(workspace.root, relative)
        before = read_utf8_text_file(target, relative)
        after = apply_python_rename_replacements(before, list(file["replacements"]))
        try:
            ast.parse(after, filename=relative)
        except SyntaxError as error:
            line = error.lineno or "unknown"
            raise ValueError(f"Python rename would create syntax error in {relative} at line {line}: {error.msg}") from error
        prepared.append((target, relative, before, after))

    for target, _, _, after in prepared:
        target.write_text(after, encoding="utf-8")

    return {
        **preview,
        "diff": "".join(build_simple_diff(relative, before, after) for _, relative, before, after in prepared),
    }


def collect_python_rename_replacements(
    tree: ast.AST,
    symbol: str,
    new_name: str,
    relative_path: str,
    lines: list[str],
) -> list[dict[str, object]]:
    replacements: list[dict[str, object]] = []
    seen: set[tuple[int, int, int]] = set()

    def add_replacement(line: int, column: int, end_column: int, kind: str) -> None:
        if line < 1 or line > len(lines) or column < 0 or end_column <= column:
            return
        text = lines[line - 1]
        if text[column:end_column] != symbol:
            return
        key = (line, column, end_column)
        if key in seen:
            return
        seen.add(key)
        replacements.append(
            {
                "path": relative_path,
                "line": line,
                "column": column,
                "end_column": end_column,
                "kind": kind,
                "old": symbol,
                "new": new_name,
                "context": text.strip(),
            }
        )

    class Visitor(ast.NodeVisitor):
        def visit_Name(self, node: ast.Name) -> None:
            if node.id == symbol:
                add_replacement(node.lineno, node.col_offset, getattr(node, "end_col_offset", node.col_offset + len(symbol)), "name")

        def visit_Attribute(self, node: ast.Attribute) -> None:
            if node.attr == symbol:
                end_column = getattr(node, "end_col_offset", node.col_offset)
                add_replacement(node.lineno, end_column - len(symbol), end_column, "attribute")
            self.generic_visit(node)

        def visit_arg(self, node: ast.arg) -> None:
            if node.arg == symbol:
                add_replacement(node.lineno, node.col_offset, node.col_offset + len(symbol), "argument")

        def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
            self.visit_function(node, "function")

        def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
            self.visit_function(node, "async_function")

        def visit_function(self, node: ast.FunctionDef | ast.AsyncFunctionDef, kind: str) -> None:
            if node.name == symbol:
                column = find_identifier_column(lines[node.lineno - 1], symbol, node.col_offset)
                add_replacement(node.lineno, column, column + len(symbol), kind)
            self.generic_visit(node)

        def visit_ClassDef(self, node: ast.ClassDef) -> None:
            if node.name == symbol:
                column = find_identifier_column(lines[node.lineno - 1], symbol, node.col_offset)
                add_replacement(node.lineno, column, column + len(symbol), "class")
            self.generic_visit(node)

    Visitor().visit(tree)
    replacements.sort(key=lambda item: (str(item["path"]), int(item["line"]), int(item["column"])))
    return replacements


def find_identifier_column(line: str, symbol: str, start: int) -> int:
    column = line.find(symbol, max(0, start))
    return column if column >= 0 else start


def apply_python_rename_replacements(content: str, replacements: list[dict[str, object]]) -> str:
    lines = content.splitlines(keepends=True)
    by_line: dict[int, list[dict[str, object]]] = {}
    for replacement in replacements:
        by_line.setdefault(int(replacement["line"]), []).append(replacement)
    for line_number, line_replacements in by_line.items():
        line = lines[line_number - 1]
        for replacement in sorted(line_replacements, key=lambda item: int(item["column"]), reverse=True):
            column = int(replacement["column"])
            end_column = int(replacement["end_column"])
            line = f"{line[:column]}{replacement['new']}{line[end_column:]}"
        lines[line_number - 1] = line
    return "".join(lines)


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
    target, updated, diff = build_edit_file(workspace, relative_path, old, new)
    target.write_text(updated, encoding="utf-8")
    return target, diff


def preview_edit_project_file(workspace: RunWorkspace, relative_path: str, old: str, new: str) -> tuple[Path, str]:
    target, _updated, diff = build_edit_file(workspace, relative_path, old, new)
    return target, diff


def build_edit_file(workspace: RunWorkspace, relative_path: str, old: str, new: str) -> tuple[Path, str, str]:
    target = resolve_inside_run(workspace.root, relative_path)
    if not target.is_file():
        raise ValueError(f"File does not exist: {relative_path}")
    content = read_utf8_text_file(target, relative_path)
    if old not in content:
        raise ValueError(f"Old text was not found in {relative_path}")
    updated = content.replace(old, new, 1)
    if updated == content:
        raise ValueError(f"Edit made no changes to {relative_path}")
    return target, updated, build_simple_diff(relative_path, content, updated)


def multi_edit_project_file(workspace: RunWorkspace, relative_path: str, edits: list[tuple[str, str]]) -> tuple[Path, str]:
    target, updated, diff = build_multi_edit(workspace, relative_path, edits)
    target.write_text(updated, encoding="utf-8")
    return target, diff


def preview_multi_edit_project_file(workspace: RunWorkspace, relative_path: str, edits: list[tuple[str, str]]) -> tuple[Path, str]:
    target, _updated, diff = build_multi_edit(workspace, relative_path, edits)
    return target, diff


def build_multi_edit(workspace: RunWorkspace, relative_path: str, edits: list[tuple[str, str]]) -> tuple[Path, str, str]:
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
    return target, updated, build_simple_diff(relative_path, content, updated)


def json_set_project_file(
    workspace: RunWorkspace,
    relative_path: str,
    pointer: str,
    value: object,
    create_missing: bool = False,
) -> tuple[Path, str]:
    target, updated, diff = build_json_set(workspace, relative_path, pointer, value, create_missing=create_missing)
    target.write_text(updated, encoding="utf-8")
    return target, diff


def preview_json_set_project_file(
    workspace: RunWorkspace,
    relative_path: str,
    pointer: str,
    value: object,
    create_missing: bool = False,
) -> tuple[Path, str]:
    target, _updated, diff = build_json_set(workspace, relative_path, pointer, value, create_missing=create_missing)
    return target, diff


def json_remove_project_file(
    workspace: RunWorkspace,
    relative_path: str,
    pointer: str,
) -> tuple[Path, str]:
    target, updated, diff = build_json_remove(workspace, relative_path, pointer)
    target.write_text(updated, encoding="utf-8")
    return target, diff


def preview_json_remove_project_file(
    workspace: RunWorkspace,
    relative_path: str,
    pointer: str,
) -> tuple[Path, str]:
    target, _updated, diff = build_json_remove(workspace, relative_path, pointer)
    return target, diff


def json_patch_project_file(
    workspace: RunWorkspace,
    relative_path: str,
    operations: list[dict[str, object]],
) -> tuple[Path, str]:
    target, updated, diff = build_json_patch(workspace, relative_path, operations)
    target.write_text(updated, encoding="utf-8")
    return target, diff


def preview_json_patch_project_file(
    workspace: RunWorkspace,
    relative_path: str,
    operations: list[dict[str, object]],
) -> tuple[Path, str]:
    target, _updated, diff = build_json_patch(workspace, relative_path, operations)
    return target, diff


def build_json_set(
    workspace: RunWorkspace,
    relative_path: str,
    pointer: str,
    value: object,
    create_missing: bool = False,
) -> tuple[Path, str, str]:
    target = resolve_inside_run(workspace.root, relative_path)
    if not target.is_file():
        raise ValueError(f"File does not exist: {relative_path}")
    before = read_utf8_text_file(target, relative_path)
    try:
        document = json.loads(before)
    except json.JSONDecodeError as error:
        raise ValueError(f"Invalid JSON in {relative_path}: {error.msg} at line {error.lineno} column {error.colno}") from error

    set_json_pointer_value(document, pointer, value, create_missing=create_missing)
    after = format_json_document(document)
    if after == before:
        raise ValueError(f"JSON set made no changes to {relative_path}")
    return target, after, build_simple_diff(relative_path, before, after)


def build_json_remove(
    workspace: RunWorkspace,
    relative_path: str,
    pointer: str,
) -> tuple[Path, str, str]:
    target = resolve_inside_run(workspace.root, relative_path)
    if not target.is_file():
        raise ValueError(f"File does not exist: {relative_path}")
    before = read_utf8_text_file(target, relative_path)
    try:
        document = json.loads(before)
    except json.JSONDecodeError as error:
        raise ValueError(f"Invalid JSON in {relative_path}: {error.msg} at line {error.lineno} column {error.colno}") from error

    remove_json_pointer_value(document, pointer)
    after = format_json_document(document)
    if after == before:
        raise ValueError(f"JSON remove made no changes to {relative_path}")
    return target, after, build_simple_diff(relative_path, before, after)


def build_json_patch(
    workspace: RunWorkspace,
    relative_path: str,
    operations: list[dict[str, object]],
) -> tuple[Path, str, str]:
    if not operations:
        raise ValueError("At least one JSON patch operation is required.")
    if len(operations) > 50:
        raise ValueError("json_patch supports at most 50 operations.")

    target = resolve_inside_run(workspace.root, relative_path)
    if not target.is_file():
        raise ValueError(f"File does not exist: {relative_path}")
    before = read_utf8_text_file(target, relative_path)
    try:
        document = json.loads(before)
    except json.JSONDecodeError as error:
        raise ValueError(f"Invalid JSON in {relative_path}: {error.msg} at line {error.lineno} column {error.colno}") from error

    for index, operation in enumerate(operations, start=1):
        apply_json_patch_operation(document, operation, index)

    after = format_json_document(document)
    if after == before:
        raise ValueError(f"JSON patch made no changes to {relative_path}")
    return target, after, build_simple_diff(relative_path, before, after)


def apply_json_patch_operation(document: object, operation: dict[str, object], index: int) -> None:
    op = operation.get("op")
    pointer = operation.get("path")
    if not isinstance(op, str) or op not in {"add", "replace", "remove"}:
        raise ValueError(f"JSON patch operation {index} has unsupported op: {op}")
    if not isinstance(pointer, str) or not pointer.strip():
        raise ValueError(f"JSON patch operation {index} requires a non-empty path.")

    if op == "remove":
        remove_json_pointer_value(document, pointer)
        return
    if "value" not in operation:
        raise ValueError(f"JSON patch operation {index} requires value.")
    if op == "add":
        add_json_pointer_value(document, pointer, operation["value"])
        return
    set_json_pointer_value(document, pointer, operation["value"], create_missing=False)


def add_json_pointer_value(document: object, pointer: str, value: object) -> None:
    parts = parse_json_pointer(pointer)
    if not parts:
        raise ValueError("JSON pointer must target a key or array item, not the document root.")

    current = document
    for index, part in enumerate(parts[:-1]):
        if isinstance(current, dict):
            if part not in current:
                raise ValueError(f"JSON pointer parent does not exist: /{'/'.join(parts[: index + 1])}")
            current = current[part]
            continue
        if isinstance(current, list):
            item_index = parse_json_array_index(part, len(current), allow_append=False)
            current = current[item_index]
            continue
        raise ValueError(f"JSON pointer parent is not a container: /{'/'.join(parts[: index + 1])}")

    final = parts[-1]
    if isinstance(current, dict):
        current[final] = value
        return
    if isinstance(current, list):
        item_index = parse_json_array_index(final, len(current), allow_append=True)
        current.insert(item_index, value)
        return
    raise ValueError("JSON pointer target parent is not an object or array.")


def set_json_pointer_value(document: object, pointer: str, value: object, create_missing: bool = False) -> None:
    parts = parse_json_pointer(pointer)
    if not parts:
        raise ValueError("JSON pointer must target a key or array item, not the document root.")

    current = document
    for index, part in enumerate(parts[:-1]):
        next_part = parts[index + 1]
        if isinstance(current, dict):
            if part not in current:
                if not create_missing:
                    raise ValueError(f"JSON pointer parent does not exist: /{'/'.join(parts[: index + 1])}")
                if next_part.isdigit() or next_part == "-":
                    raise ValueError("create_missing can only create object parents, not array parents.")
                current[part] = {}
            current = current[part]
            continue
        if isinstance(current, list):
            item_index = parse_json_array_index(part, len(current), allow_append=False)
            current = current[item_index]
            continue
        raise ValueError(f"JSON pointer parent is not a container: /{'/'.join(parts[: index + 1])}")

    final = parts[-1]
    if isinstance(current, dict):
        if final not in current and not create_missing:
            raise ValueError(f"JSON object key does not exist: {final}")
        if final in current and current[final] == value:
            raise ValueError("JSON set made no changes.")
        current[final] = value
        return
    if isinstance(current, list):
        if final == "-":
            current.append(value)
            return
        item_index = parse_json_array_index(final, len(current), allow_append=False)
        if current[item_index] == value:
            raise ValueError("JSON set made no changes.")
        current[item_index] = value
        return
    raise ValueError("JSON pointer target parent is not an object or array.")


def remove_json_pointer_value(document: object, pointer: str) -> None:
    parts = parse_json_pointer(pointer)
    if not parts:
        raise ValueError("JSON pointer must target a key or array item, not the document root.")

    current = document
    for index, part in enumerate(parts[:-1]):
        if isinstance(current, dict):
            if part not in current:
                raise ValueError(f"JSON pointer parent does not exist: /{'/'.join(parts[: index + 1])}")
            current = current[part]
            continue
        if isinstance(current, list):
            item_index = parse_json_array_index(part, len(current), allow_append=False)
            current = current[item_index]
            continue
        raise ValueError(f"JSON pointer parent is not a container: /{'/'.join(parts[: index + 1])}")

    final = parts[-1]
    if isinstance(current, dict):
        if final not in current:
            raise ValueError(f"JSON object key does not exist: {final}")
        del current[final]
        return
    if isinstance(current, list):
        if final == "-":
            raise ValueError("JSON array removal requires an explicit index.")
        item_index = parse_json_array_index(final, len(current), allow_append=False)
        del current[item_index]
        return
    raise ValueError("JSON pointer target parent is not an object or array.")


def parse_json_pointer(pointer: str) -> list[str]:
    if pointer == "":
        return []
    if not pointer.startswith("/"):
        raise ValueError("JSON pointer must start with '/'.")
    parts = pointer.split("/")[1:]
    return [part.replace("~1", "/").replace("~0", "~") for part in parts]


def parse_json_array_index(raw: str, length: int, allow_append: bool) -> int:
    if raw == "-" and allow_append:
        return length
    if not raw.isdigit():
        raise ValueError(f"JSON array index must be a non-negative integer: {raw}")
    index = int(raw)
    if index >= length:
        raise ValueError(f"JSON array index out of range: {raw}")
    return index


def format_json_document(document: object) -> str:
    return json.dumps(document, indent=2, ensure_ascii=False) + "\n"


def replace_project_file_lines(
    workspace: RunWorkspace,
    relative_path: str,
    start_line: int,
    end_line: int,
    new_content: str,
) -> tuple[Path, str]:
    target, after, diff = build_replace_lines(workspace, relative_path, start_line, end_line, new_content)
    target.write_text(after, encoding="utf-8")
    return target, diff


def preview_replace_project_file_lines(
    workspace: RunWorkspace,
    relative_path: str,
    start_line: int,
    end_line: int,
    new_content: str,
) -> tuple[Path, str]:
    target, _after, diff = build_replace_lines(workspace, relative_path, start_line, end_line, new_content)
    return target, diff


def build_replace_lines(
    workspace: RunWorkspace,
    relative_path: str,
    start_line: int,
    end_line: int,
    new_content: str,
) -> tuple[Path, str, str]:
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
    return target, after, build_simple_diff(relative_path, before, after)


def insert_project_file_lines(
    workspace: RunWorkspace,
    relative_path: str,
    line: int,
    content: str,
) -> tuple[Path, str]:
    target, after, diff = build_insert_lines(workspace, relative_path, line, content)
    target.write_text(after, encoding="utf-8")
    return target, diff


def preview_insert_project_file_lines(
    workspace: RunWorkspace,
    relative_path: str,
    line: int,
    content: str,
) -> tuple[Path, str]:
    target, _after, diff = build_insert_lines(workspace, relative_path, line, content)
    return target, diff


def build_insert_lines(
    workspace: RunWorkspace,
    relative_path: str,
    line: int,
    content: str,
) -> tuple[Path, str, str]:
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
    return target, after, build_simple_diff(relative_path, before, after)


def append_project_file(workspace: RunWorkspace, relative_path: str, content: str) -> tuple[Path, str]:
    target, after, diff = build_append_file(workspace, relative_path, content)
    target.write_text(after, encoding="utf-8")
    return target, diff


def preview_append_project_file(workspace: RunWorkspace, relative_path: str, content: str) -> tuple[Path, str]:
    target, _after, diff = build_append_file(workspace, relative_path, content)
    return target, diff


def build_append_file(workspace: RunWorkspace, relative_path: str, content: str) -> tuple[Path, str, str]:
    if content == "":
        raise ValueError("content must not be empty.")
    target = resolve_inside_run(workspace.root, relative_path)
    if not target.is_file():
        raise ValueError(f"File does not exist: {relative_path}")
    before = read_utf8_text_file(target, relative_path)
    after = before + content
    if after == before:
        raise ValueError(f"Append made no changes to {relative_path}")
    return target, after, build_simple_diff(relative_path, before, after)


def regex_replace_project_file(
    workspace: RunWorkspace,
    relative_path: str,
    pattern: str,
    replacement: str,
    count: int = 0,
    case_sensitive: bool = True,
    multiline: bool = False,
    max_replacements: int = 100,
) -> tuple[Path, int, str]:
    target, after, replacements, diff = build_regex_replacement(
        workspace,
        relative_path,
        pattern,
        replacement,
        count=count,
        case_sensitive=case_sensitive,
        multiline=multiline,
        max_replacements=max_replacements,
    )
    target.write_text(after, encoding="utf-8")
    return target, replacements, diff


def preview_regex_replace_project_file(
    workspace: RunWorkspace,
    relative_path: str,
    pattern: str,
    replacement: str,
    count: int = 0,
    case_sensitive: bool = True,
    multiline: bool = False,
    max_replacements: int = 100,
) -> tuple[Path, int, str]:
    target, _after, replacements, diff = build_regex_replacement(
        workspace,
        relative_path,
        pattern,
        replacement,
        count=count,
        case_sensitive=case_sensitive,
        multiline=multiline,
        max_replacements=max_replacements,
    )
    return target, replacements, diff


def build_regex_replacement(
    workspace: RunWorkspace,
    relative_path: str,
    pattern: str,
    replacement: str,
    count: int = 0,
    case_sensitive: bool = True,
    multiline: bool = False,
    max_replacements: int = 100,
) -> tuple[Path, str, int, str]:
    if pattern == "":
        raise ValueError("pattern must not be empty.")
    if count < 0:
        raise ValueError("count must be non-negative.")
    if max_replacements < 1:
        raise ValueError("max_replacements must be at least 1.")

    target = resolve_inside_run(workspace.root, relative_path)
    if not target.is_file():
        raise ValueError(f"File does not exist: {relative_path}")
    before = read_utf8_text_file(target, relative_path)
    flags = 0
    if not case_sensitive:
        flags |= re.IGNORECASE
    if multiline:
        flags |= re.MULTILINE
    try:
        compiled = re.compile(pattern, flags)
    except re.error as error:
        raise ValueError(f"Invalid regex pattern: {error}") from error

    matches = list(compiled.finditer(before))
    if not matches:
        raise ValueError(f"Pattern was not found in {relative_path}")
    replacements_to_apply = len(matches) if count == 0 else min(count, len(matches))
    if replacements_to_apply > max_replacements:
        raise ValueError(f"Regex replacement would change {replacements_to_apply} matches, above max_replacements {max_replacements}.")
    try:
        after, replacements = compiled.subn(replacement, before, count=count)
    except re.error as error:
        raise ValueError(f"Invalid regex replacement: {error}") from error
    if replacements > max_replacements:
        raise ValueError(f"Regex replacement changed {replacements} matches, above max_replacements {max_replacements}.")
    if after == before:
        raise ValueError(f"Regex replacement made no changes to {relative_path}")
    return target, after, replacements, build_simple_diff(relative_path, before, after)


def split_replacement_lines(content: str) -> list[str]:
    if content == "":
        return []
    lines = content.splitlines(keepends=True)
    if not content.endswith(("\n", "\r")):
        lines[-1] += "\n"
    return lines


def delete_project_file(workspace: RunWorkspace, relative_path: str) -> tuple[Path, str]:
    target, diff = build_delete_file(workspace, relative_path)
    target.unlink()
    return target, diff


def preview_delete_project_file(workspace: RunWorkspace, relative_path: str) -> tuple[Path, str]:
    return build_delete_file(workspace, relative_path)


def delete_project_files(workspace: RunWorkspace, relative_paths: list[str]) -> tuple[list[Path], str]:
    targets, diff = build_delete_files(workspace, relative_paths)
    for target in targets:
        target.unlink()
    return targets, diff


def preview_delete_project_files(workspace: RunWorkspace, relative_paths: list[str]) -> tuple[list[Path], str]:
    return build_delete_files(workspace, relative_paths)


def build_delete_files(workspace: RunWorkspace, relative_paths: list[str]) -> tuple[list[Path], str]:
    if not relative_paths:
        raise ValueError("At least one file path is required.")
    if len(relative_paths) > 100:
        raise ValueError("At most 100 file paths can be deleted at once.")
    seen: set[str] = set()
    prepared: list[tuple[Path, str]] = []
    for relative_path in relative_paths:
        if relative_path in seen:
            raise ValueError(f"Duplicate file path: {relative_path}")
        seen.add(relative_path)
        prepared.append(build_delete_file(workspace, relative_path))
    diff = "".join(file_diff for _target, file_diff in prepared)
    return [target for target, _diff in prepared], diff


def build_delete_file(workspace: RunWorkspace, relative_path: str) -> tuple[Path, str]:
    target = resolve_inside_run(workspace.root, relative_path)
    if not target.is_file():
        raise ValueError(f"File does not exist: {relative_path}")
    before = read_utf8_text_file(target, relative_path)
    return target, build_simple_diff(relative_path, before, "")


def move_project_file(workspace: RunWorkspace, source_path: str, destination_path: str) -> tuple[Path, Path]:
    source, destination = prepare_project_file_transfer(workspace, source_path, destination_path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    source.rename(destination)
    return source, destination


def preview_move_project_file(workspace: RunWorkspace, source_path: str, destination_path: str) -> tuple[Path, Path]:
    return prepare_project_file_transfer(workspace, source_path, destination_path)


def move_project_files(workspace: RunWorkspace, transfers: list[dict[str, str]]) -> list[tuple[Path, Path]]:
    prepared = prepare_project_file_transfers(workspace, transfers)
    for source, destination in prepared:
        destination.parent.mkdir(parents=True, exist_ok=True)
        source.rename(destination)
    return prepared


def preview_move_project_files(workspace: RunWorkspace, transfers: list[dict[str, str]]) -> list[tuple[Path, Path]]:
    return prepare_project_file_transfers(workspace, transfers)


def prepare_project_file_transfers(workspace: RunWorkspace, transfers: list[dict[str, str]]) -> list[tuple[Path, Path]]:
    if not transfers:
        raise ValueError("At least one file transfer is required.")
    if len(transfers) > 100:
        raise ValueError("At most 100 files can be moved at once.")

    prepared: list[tuple[Path, Path]] = []
    seen_sources: set[Path] = set()
    seen_destinations: set[Path] = set()
    for transfer in transfers:
        source_label = transfer.get("source", "")
        destination_label = transfer.get("destination", "")
        source, destination = prepare_project_file_transfer(workspace, source_label, destination_label)
        if source in seen_sources:
            raise ValueError(f"Duplicate source file: {source_label}")
        if destination in seen_destinations:
            raise ValueError(f"Duplicate destination file: {destination_label}")
        seen_sources.add(source)
        seen_destinations.add(destination)
        prepared.append((source, destination))

    for source, destination in prepared:
        if destination in seen_sources:
            raise ValueError(f"Destination overlaps another source file: {destination.relative_to(workspace.root).as_posix()}")
        if source in seen_destinations:
            raise ValueError(f"Source overlaps another destination file: {source.relative_to(workspace.root).as_posix()}")
        for parent in destination.parents:
            if parent == workspace.root:
                break
            if parent in seen_destinations:
                raise ValueError(f"Destination parent overlaps another destination file: {destination.relative_to(workspace.root).as_posix()}")
            if parent in seen_sources:
                raise ValueError(f"Destination parent overlaps another source file: {destination.relative_to(workspace.root).as_posix()}")

    return prepared


def copy_project_file(workspace: RunWorkspace, source_path: str, destination_path: str) -> tuple[Path, Path]:
    source, destination = prepare_project_file_transfer(workspace, source_path, destination_path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, destination)
    return source, destination


def preview_copy_project_file(workspace: RunWorkspace, source_path: str, destination_path: str) -> tuple[Path, Path]:
    return prepare_project_file_transfer(workspace, source_path, destination_path)


def copy_project_files(workspace: RunWorkspace, transfers: list[dict[str, str]]) -> list[tuple[Path, Path]]:
    prepared = prepare_project_file_copies(workspace, transfers)
    for source, destination in prepared:
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, destination)
    return prepared


def preview_copy_project_files(workspace: RunWorkspace, transfers: list[dict[str, str]]) -> list[tuple[Path, Path]]:
    return prepare_project_file_copies(workspace, transfers)


def prepare_project_file_copies(workspace: RunWorkspace, transfers: list[dict[str, str]]) -> list[tuple[Path, Path]]:
    if not transfers:
        raise ValueError("At least one file transfer is required.")
    if len(transfers) > 100:
        raise ValueError("At most 100 files can be copied at once.")

    prepared: list[tuple[Path, Path]] = []
    seen_destinations: set[Path] = set()
    for transfer in transfers:
        source_label = transfer.get("source", "")
        destination_label = transfer.get("destination", "")
        source, destination = prepare_project_file_transfer(workspace, source_label, destination_label)
        if destination in seen_destinations:
            raise ValueError(f"Duplicate destination file: {destination_label}")
        seen_destinations.add(destination)
        prepared.append((source, destination))

    for _source, destination in prepared:
        for parent in destination.parents:
            if parent == workspace.root:
                break
            if parent in seen_destinations:
                raise ValueError(f"Destination parent overlaps another destination file: {destination.relative_to(workspace.root).as_posix()}")

    return prepared


def prepare_project_file_transfer(workspace: RunWorkspace, source_path: str, destination_path: str) -> tuple[Path, Path]:
    source = resolve_inside_run(workspace.root, source_path)
    destination = resolve_inside_run(workspace.root, destination_path)
    if source == destination:
        raise ValueError("Source and destination must be different.")
    if not source.is_file():
        raise ValueError(f"File does not exist: {source_path}")
    if destination.exists():
        raise ValueError(f"Destination already exists: {destination_path}")
    return source, destination


def move_project_directory(workspace: RunWorkspace, source_path: str, destination_path: str) -> tuple[Path, Path]:
    source, destination = prepare_project_directory_move(workspace, source_path, destination_path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    source.rename(destination)
    return source, destination


def move_project_directories(workspace: RunWorkspace, transfers: list[tuple[str, str]]) -> list[tuple[Path, Path]]:
    prepared = preview_move_project_directories(workspace, transfers)
    for source, destination in prepared:
        destination.parent.mkdir(parents=True, exist_ok=True)
        source.rename(destination)
    return prepared


def preview_move_project_directory(workspace: RunWorkspace, source_path: str, destination_path: str) -> tuple[Path, Path]:
    return prepare_project_directory_move(workspace, source_path, destination_path)


def preview_move_project_directories(workspace: RunWorkspace, transfers: list[tuple[str, str]]) -> list[tuple[Path, Path]]:
    prepared = [prepare_project_directory_move(workspace, source, destination) for source, destination in transfers]
    validate_project_directory_transfer_batch(prepared, operation="move")
    return prepared


def prepare_project_directory_move(workspace: RunWorkspace, source_path: str, destination_path: str) -> tuple[Path, Path]:
    source = resolve_inside_run(workspace.root, source_path)
    destination = resolve_inside_run(workspace.root, destination_path)
    if source == workspace.root:
        raise ValueError("Cannot move the project root directory.")
    if source == destination:
        raise ValueError("Source and destination must be different.")
    if not source.is_dir():
        raise ValueError(f"Directory does not exist: {source_path}")
    if destination.exists():
        raise ValueError(f"Destination already exists: {destination_path}")
    if source in destination.parents:
        raise ValueError("Cannot move a directory inside itself.")
    return source, destination


def copy_project_directory(
    workspace: RunWorkspace,
    source_path: str,
    destination_path: str,
    max_entries: int = 2000,
    max_bytes: int = 50 * 1024 * 1024,
) -> tuple[Path, Path]:
    source, destination = prepare_project_directory_copy(
        workspace,
        source_path,
        destination_path,
        max_entries=max_entries,
        max_bytes=max_bytes,
    )
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(source, destination)
    return source, destination


def copy_project_directories(
    workspace: RunWorkspace,
    transfers: list[tuple[str, str]],
    max_entries: int = 2000,
    max_bytes: int = 50 * 1024 * 1024,
) -> list[tuple[Path, Path]]:
    prepared = preview_copy_project_directories(
        workspace,
        transfers,
        max_entries=max_entries,
        max_bytes=max_bytes,
    )
    for source, destination in prepared:
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copytree(source, destination)
    return prepared


def preview_copy_project_directory(
    workspace: RunWorkspace,
    source_path: str,
    destination_path: str,
    max_entries: int = 2000,
    max_bytes: int = 50 * 1024 * 1024,
) -> tuple[Path, Path]:
    return prepare_project_directory_copy(
        workspace,
        source_path,
        destination_path,
        max_entries=max_entries,
        max_bytes=max_bytes,
    )


def preview_copy_project_directories(
    workspace: RunWorkspace,
    transfers: list[tuple[str, str]],
    max_entries: int = 2000,
    max_bytes: int = 50 * 1024 * 1024,
) -> list[tuple[Path, Path]]:
    prepared = [
        prepare_project_directory_copy(
            workspace,
            source,
            destination,
            max_entries=max_entries,
            max_bytes=max_bytes,
        )
        for source, destination in transfers
    ]
    validate_project_directory_transfer_batch(prepared, operation="copy")
    return prepared


def prepare_project_directory_copy(
    workspace: RunWorkspace,
    source_path: str,
    destination_path: str,
    max_entries: int = 2000,
    max_bytes: int = 50 * 1024 * 1024,
) -> tuple[Path, Path]:
    source = resolve_inside_run(workspace.root, source_path)
    destination = resolve_inside_run(workspace.root, destination_path)
    if source == workspace.root:
        raise ValueError("Cannot copy the project root directory.")
    if source == destination:
        raise ValueError("Source and destination must be different.")
    if not source.is_dir():
        raise ValueError(f"Directory does not exist: {source_path}")
    if destination.exists():
        raise ValueError(f"Destination already exists: {destination_path}")
    if source in destination.parents:
        raise ValueError("Cannot copy a directory inside itself.")

    entry_count = 0
    total_bytes = 0
    for path in source.rglob("*"):
        entry_count += 1
        if entry_count > max_entries:
            raise ValueError(f"Directory has more than {max_entries} entries: {source_path}")
        if path.is_symlink():
            raise ValueError(f"Directory contains a symbolic link: {path.relative_to(workspace.root).as_posix()}")
        if is_protected_project_path(workspace.root, path.resolve()):
            raise ValueError(f"Directory contains a protected path: {path.relative_to(workspace.root).as_posix()}")
        if path.is_file():
            total_bytes += path.stat().st_size
            if total_bytes > max_bytes:
                raise ValueError(f"Directory exceeds {max_bytes} bytes: {source_path}")

    return source, destination


def validate_project_directory_transfer_batch(prepared: list[tuple[Path, Path]], operation: str) -> None:
    if not prepared:
        raise ValueError(f"Directory {operation} requires at least one transfer.")
    if len(prepared) > 100:
        raise ValueError(f"Directory {operation} supports at most 100 transfers.")

    sources = [source.resolve() for source, _destination in prepared]
    destinations = [destination.resolve() for _source, destination in prepared]
    for index, source in enumerate(sources):
        for other in sources[index + 1:]:
            if source == other or source in other.parents or other in source.parents:
                raise ValueError("Directory transfer sources must not overlap.")
    for index, destination in enumerate(destinations):
        for other in destinations[index + 1:]:
            if destination == other or destination in other.parents or other in destination.parents:
                raise ValueError("Directory transfer destinations must not overlap.")
    for destination in destinations:
        for source in sources:
            if destination == source or source in destination.parents:
                raise ValueError("Directory transfer destination must not overlap a source.")


def create_project_directory(workspace: RunWorkspace, relative_path: str) -> Path:
    target = preview_create_project_directory(workspace, relative_path)
    target.mkdir(parents=True, exist_ok=True)
    return target


def create_project_directories(workspace: RunWorkspace, relative_paths: list[str]) -> list[Path]:
    targets = preview_create_project_directories(workspace, relative_paths)
    for target in targets:
        target.mkdir(parents=True, exist_ok=True)
    return targets


def preview_create_project_directory(workspace: RunWorkspace, relative_path: str) -> Path:
    target = resolve_inside_run(workspace.root, relative_path)
    if target.exists() and not target.is_dir():
        raise ValueError(f"Path already exists and is not a directory: {relative_path}")
    return target


def preview_create_project_directories(workspace: RunWorkspace, relative_paths: list[str]) -> list[Path]:
    if not relative_paths:
        raise ValueError("Directory creation requires at least one path.")
    if len(relative_paths) > 100:
        raise ValueError("Directory creation supports at most 100 paths.")

    targets: list[Path] = []
    seen: set[Path] = set()
    for index, relative_path in enumerate(relative_paths, start=1):
        target = preview_create_project_directory(workspace, relative_path)
        normalized = target.resolve()
        if normalized in seen:
            raise ValueError(f"Directory path {index} duplicates an earlier target: {relative_path}")
        seen.add(normalized)
        targets.append(target)
    return targets


def delete_project_empty_directory(workspace: RunWorkspace, relative_path: str) -> Path:
    target = preview_delete_project_empty_directory(workspace, relative_path)
    try:
        target.rmdir()
    except OSError as error:
        raise ValueError(f"Directory is not empty: {relative_path}") from error
    return target


def delete_project_empty_directories(workspace: RunWorkspace, relative_paths: list[str]) -> list[Path]:
    targets = preview_delete_project_empty_directories(workspace, relative_paths)
    for target in sorted(targets, key=lambda path: len(path.parts), reverse=True):
        try:
            target.rmdir()
        except OSError as error:
            relative_path = target.relative_to(workspace.root).as_posix()
            raise ValueError(f"Directory is not empty: {relative_path}") from error
    return targets


def preview_delete_project_empty_directory(workspace: RunWorkspace, relative_path: str) -> Path:
    target = resolve_inside_run(workspace.root, relative_path)
    if not target.is_dir():
        raise ValueError(f"Directory does not exist: {relative_path}")
    if any(target.iterdir()):
        raise ValueError(f"Directory is not empty: {relative_path}")
    return target


def preview_delete_project_empty_directories(workspace: RunWorkspace, relative_paths: list[str]) -> list[Path]:
    if not relative_paths:
        raise ValueError("Empty-directory deletion requires at least one path.")
    if len(relative_paths) > 100:
        raise ValueError("Empty-directory deletion supports at most 100 paths.")

    targets: list[Path] = []
    relative_by_target: dict[Path, str] = {}
    for index, relative_path in enumerate(relative_paths, start=1):
        target = resolve_inside_run(workspace.root, relative_path)
        normalized = target.resolve()
        if normalized in relative_by_target:
            raise ValueError(f"Directory path {index} duplicates an earlier target: {relative_path}")
        if not target.is_dir():
            raise ValueError(f"Directory does not exist: {relative_path}")
        relative_by_target[normalized] = relative_path
        targets.append(target)

    target_set = set(relative_by_target)
    for target in targets:
        for child in target.iterdir():
            child_path = child.resolve()
            if child_path in target_set and child.is_dir():
                continue
            relative_path = relative_by_target[target.resolve()]
            raise ValueError(f"Directory is not empty: {relative_path}")
    return targets


def set_project_file_executable(workspace: RunWorkspace, relative_path: str, executable: bool = True) -> tuple[Path, int, int]:
    target, before, after = preview_set_project_file_executable(workspace, relative_path, executable=executable)
    if after != before:
        target.chmod(after)
    return target, before, after


def preview_set_project_file_executable(workspace: RunWorkspace, relative_path: str, executable: bool = True) -> tuple[Path, int, int]:
    target = resolve_inside_run(workspace.root, relative_path)
    if not target.is_file():
        raise ValueError(f"File does not exist: {relative_path}")
    before = stat_module.S_IMODE(target.stat().st_mode)
    if executable:
        after = before | stat_module.S_IXUSR | stat_module.S_IXGRP | stat_module.S_IXOTH
    else:
        after = before & ~(stat_module.S_IXUSR | stat_module.S_IXGRP | stat_module.S_IXOTH)
    return target, before, after


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
        raise ValueError("Patch must include file headers for at least one file.")

    prepared: list[tuple[Path, str, str, str, str]] = []
    seen: set[str] = set()
    for relative_path, file_patch, operation in file_patches:
        if relative_path in seen:
            raise ValueError(f"Patch contains duplicate file section: {relative_path}")
        seen.add(relative_path)

        target = resolve_inside_run(workspace.root, relative_path)
        if operation == "create":
            if target.exists():
                raise ValueError(f"File already exists: {relative_path}")
            before = ""
        elif not target.is_file():
            raise ValueError(f"File does not exist: {relative_path}")
        else:
            before = read_utf8_text_file(target, relative_path)
        after = apply_unified_patch(before, file_patch)
        if after == before:
            raise ValueError(f"Patch made no changes to {relative_path}")
        if operation == "delete" and after:
            raise ValueError(f"Patch delete file section must remove all content: {relative_path}")
        prepared.append((target, relative_path, before, after, operation))

    for target, _relative_path, _before, after, operation in prepared:
        if operation == "create":
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(after, encoding="utf-8")
        elif operation == "delete":
            target.unlink()
        else:
            target.write_text(after, encoding="utf-8")

    diff = "".join(
        build_simple_diff(relative_path, before, after)
        for _target, relative_path, before, after, _operation in prepared
    )
    return [target for target, _relative_path, _before, _after, _operation in prepared], diff


def check_project_patches(workspace: RunWorkspace, patch: str) -> tuple[list[Path], str]:
    if not patch.strip():
        raise ValueError("Patch must not be empty.")

    file_patches = split_unified_patch_by_file(patch)
    if not file_patches:
        raise ValueError("Patch must include file headers for at least one file.")

    prepared: list[tuple[Path, str, str, str]] = []
    seen: set[str] = set()
    for relative_path, file_patch, operation in file_patches:
        if relative_path in seen:
            raise ValueError(f"Patch contains duplicate file section: {relative_path}")
        seen.add(relative_path)

        target = resolve_inside_run(workspace.root, relative_path)
        if operation == "create":
            if target.exists():
                raise ValueError(f"File already exists: {relative_path}")
            before = ""
        elif not target.is_file():
            raise ValueError(f"File does not exist: {relative_path}")
        else:
            before = read_utf8_text_file(target, relative_path)
        after = apply_unified_patch(before, file_patch)
        if after == before:
            raise ValueError(f"Patch made no changes to {relative_path}")
        if operation == "delete" and after:
            raise ValueError(f"Patch delete file section must remove all content: {relative_path}")
        prepared.append((target, relative_path, before, after))

    diff = "".join(build_simple_diff(relative_path, before, after) for _target, relative_path, before, after in prepared)
    return [target for target, _relative_path, _before, _after in prepared], diff


def split_unified_patch_by_file(patch: str) -> list[tuple[str, str, str]]:
    patch_lines = patch.splitlines(keepends=True)
    sections: list[tuple[str, str, str]] = []
    index = 0
    while index < len(patch_lines):
        if not is_file_header_at(patch_lines, index):
            index += 1
            continue

        old_path = parse_unified_diff_path(patch_lines[index][4:])
        new_path = parse_unified_diff_path(patch_lines[index + 1][4:])
        if old_path is None and new_path is None:
            raise ValueError("Patch file section must include a target path.")
        if old_path is not None and new_path is not None and old_path != new_path:
            raise ValueError(f"Patch rename sections are not supported: {old_path} -> {new_path}")
        relative_path = new_path or old_path
        if relative_path is None:
            raise ValueError("Patch file section must include a target path.")
        operation = "modify"
        if old_path is None:
            operation = "create"
        elif new_path is None:
            operation = "delete"

        start = index
        index += 2
        while index < len(patch_lines) and not is_file_header_at(patch_lines, index):
            index += 1
        sections.append((relative_path, "".join(patch_lines[start:index]), operation))

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
    return list(
        search_project_result(
            workspace,
            query,
            max_matches=max_matches,
            relative_path=relative_path,
            regex=regex,
            case_sensitive=case_sensitive,
            context_lines=context_lines,
        )["matches"]
    )


def search_project_result(
    workspace: RunWorkspace,
    query: str,
    max_matches: int = 80,
    relative_path: str | None = None,
    regex: bool = False,
    case_sensitive: bool = True,
    context_lines: int = 0,
) -> dict[str, object]:
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
    total = 0
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
                total += 1
                if len(matches) < max_matches:
                    if context_lines:
                        matches.append(format_search_context(relative, lines, line_number, context_lines))
                    else:
                        matches.append(f"{relative}:{line_number}: {line.strip()}")
    return {
        "matches": matches,
        "total": total,
        "truncated": total > len(matches),
    }


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

    code_files: list[dict[str, object]] = []
    used_code_symbols = 0
    code_symbols_truncated = False
    for file in files:
        if not supports_code_outline_path(file):
            continue
        remaining = max_symbols - used_code_symbols
        if remaining <= 0:
            code_symbols_truncated = True
            break
        try:
            outline = read_code_outline(workspace, file, max_symbols=remaining)
            symbols = list(outline["symbols"])
            used_code_symbols += len(symbols)
            code_files.append(
                {
                    "path": file,
                    "ok": True,
                    "language": str(outline["language"]),
                    "imports": list(outline["imports"]),
                    "symbols": symbols,
                    "message": str(outline["message"]),
                }
            )
            if used_code_symbols >= max_symbols and len(symbols) == remaining:
                code_symbols_truncated = True
        except ValueError as error:
            code_files.append(
                {
                    "path": file,
                    "ok": False,
                    "language": code_language_for_path(Path(file)),
                    "imports": [],
                    "symbols": [],
                    "message": str(error),
                }
            )

    truncated = len(tree_entries) < total_tree_entries or len(files) < total_files or symbols_truncated or code_symbols_truncated
    return {
        "path": path_label,
        "tree": tree_entries,
        "files": files,
        "python_files": python_files,
        "code_files": code_files,
        "total_tree_entries": total_tree_entries,
        "total_files": total_files,
        "truncated": truncated,
        "message": (
            f"Mapped {len(files)}/{total_files} file(s), "
            f"{len(python_files)} Python file(s), and {len(code_files)} source file(s)."
        ),
    }


def should_ignore_path(root: Path, path: Path) -> bool:
    relative_path = path.resolve().relative_to(root)
    relative_parts = relative_path.parts
    hard_ignored = {".git", ".vibeagent", ".venv", "__pycache__", "node_modules", "dist", "build"}
    if any(part in hard_ignored for part in relative_parts):
        return True
    return path_matches_gitignore(root, relative_path, path.is_dir())


def path_matches_gitignore(root: Path, relative_path: Path, is_dir: bool) -> bool:
    for base, pattern in read_gitignore_patterns(root, relative_path):
        scoped_path = gitignore_scoped_path(relative_path, base)
        if scoped_path is not None and gitignore_pattern_matches(pattern, scoped_path, is_dir):
            return True
    return False


def read_gitignore_patterns(root: Path, relative_path: Path) -> list[tuple[Path, str]]:
    rules: list[tuple[Path, str]] = []
    for base in gitignore_rule_bases(relative_path):
        path = root / base / ".gitignore"
        try:
            lines = path.read_text(encoding="utf-8").splitlines()
        except OSError:
            continue
        for line in lines:
            stripped = line.strip()
            if not stripped or stripped.startswith("#") or stripped.startswith("!"):
                continue
            rules.append((base, stripped))
    return rules


def gitignore_rule_bases(relative_path: Path) -> list[Path]:
    parent = relative_path.parent
    bases = [Path(".")]
    current = Path(".")
    for part in parent.parts:
        current = current / part
        bases.append(current)
    return bases


def gitignore_scoped_path(relative_path: Path, base: Path) -> Path | None:
    if base == Path("."):
        return relative_path
    try:
        return relative_path.relative_to(base)
    except ValueError:
        return None


def gitignore_pattern_matches(pattern: str, relative_path: Path, is_dir: bool) -> bool:
    normalized = pattern.replace("\\", "/").strip()
    if not normalized:
        return False
    normalized = normalized.lstrip("/")
    directory_only = normalized.endswith("/")
    normalized = normalized.rstrip("/")
    if not normalized:
        return False
    if directory_only and not path_has_directory(relative_path, normalized, is_dir):
        return False

    relative = relative_path.as_posix()
    if "/" in normalized:
        return relative == normalized or relative.startswith(f"{normalized}/") or relative_path.match(normalized)
    return any(part == normalized for part in relative_path.parts) or relative_path.match(normalized)


def path_has_directory(relative_path: Path, directory: str, is_dir: bool) -> bool:
    parts = relative_path.parts if is_dir else relative_path.parts[:-1]
    if "/" in directory:
        relative = "/".join(parts)
        return relative == directory or relative.startswith(f"{directory}/")
    return directory in parts


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
