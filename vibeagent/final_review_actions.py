from __future__ import annotations

import json
import os
import re
from pathlib import Path
from typing import Any

from .session import read_session_events
from .types import FocusedTestCommand, SuggestedCheck
from .verification_command_utils import verification_commands_from_objects
from .workspace_core import RunWorkspace
from .workspace_git_utils import parse_git_short_status, run_readonly_git, should_ignore_git_path
from .workspace import (
    is_protected_project_path,
    read_git_status,
    should_ignore_path,
)


PROJECT_CHANGE_RESULT_KINDS = {
    "write_file",
    "write_files",
    "edit_file",
    "multi_edit_file",
    "replace_python_definition",
    "code_rename",
    "python_rename",
    "replace_lines",
    "insert_lines",
    "append_file",
    "regex_replace",
    "json_set",
    "json_remove",
    "json_patch",
    "patch_file",
    "patch_files",
    "delete_file",
    "delete_files",
    "move_file",
    "move_files",
    "copy_file",
    "copy_files",
    "move_dir",
    "move_dirs",
    "copy_dir",
    "copy_dirs",
    "create_dir",
    "create_dirs",
    "delete_empty_dir",
    "delete_empty_dirs",
    "set_executable",
    "git_stage",
    "git_unstage",
    "git_commit",
    "git_restore",
    "checkpoint_restore",
}


FINAL_REVIEW_LARGE_FILE_BYTES = 100 * 1024 * 1024
FINAL_REVIEW_SECRET_SCAN_BYTES = 1024 * 1024
SECRET_LIKE_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("private key block", re.compile(r"-----BEGIN [A-Z0-9 ]*PRIVATE KEY-----")),
    (
        "credential assignment",
        re.compile(
            r"\b(?P<name>[A-Z0-9_]*(?:API[_-]?KEY|TOKEN|SECRET|PASSWORD|ACCESS[_-]?KEY)[A-Z0-9_]*)"
            r"\s*[:=]\s*[\"']?(?P<value>[A-Za-z0-9_./+=:-]{24,})",
            re.IGNORECASE,
        ),
    ),
    ("OpenAI API key", re.compile(r"\bsk-[A-Za-z0-9_-]{24,}\b")),
    ("GitHub token", re.compile(r"\b(?:ghp|gho|ghu|ghs|ghr)_[A-Za-z0-9_]{30,}\b")),
    ("AWS access key", re.compile(r"\b(?:AKIA|ASIA)[A-Z0-9]{16}\b")),
)

def final_review_session_verification_issues(
    workspace: RunWorkspace,
    suggested_checks: list[SuggestedCheck],
    focused_test_commands: list[FocusedTestCommand] | None = None,
) -> tuple[list[str], list[str]]:
    verification_commands = verification_commands_from_objects(suggested_checks, focused_test_commands or [])
    if not verification_commands:
        return [], []

    events = read_session_events(workspace.root, workspace.run_id)
    last_change_index = latest_successful_project_change_event_index(events)
    if last_change_index is None:
        return [], []

    statuses: dict[tuple[str, str], bool] = {}
    for event in events[last_change_index + 1 :]:
        result = event.payload.get("result") if not event.malformed and event.type == "tool_result" else None
        if not isinstance(result, dict):
            continue
        for command_result in iter_command_results(result):
            key = command_result_key(command_result)
            if key not in verification_commands:
                continue
            statuses[key] = command_result_succeeded(command_result)

    verified_commands = {key for key, passed in statuses.items() if passed}
    failed_commands = {key for key, passed in statuses.items() if not passed}
    failed_labels = [suggested_check_label(command, cwd) for command, cwd in sorted(failed_commands)]
    pending_labels = [
        suggested_check_label(command, cwd)
        for command, cwd in sorted(verification_commands - verified_commands - failed_commands)
    ]
    blockers: list[str] = []
    warnings: list[str] = []
    if failed_labels:
        blockers.append("Suggested verification checks failed after the latest project change.")
        warnings.append("Failed suggested check(s): " + ", ".join(failed_labels[:5]) + ".")
    if pending_labels:
        blockers.append("Suggested verification checks are still pending after the latest project change.")
        warnings.append("Pending suggested check(s): " + ", ".join(pending_labels[:5]) + ".")
    return blockers, warnings


def latest_successful_project_change_event_index(events: list[Any]) -> int | None:
    for index in range(len(events) - 1, -1, -1):
        event = events[index]
        if event.malformed or event.type != "tool_result":
            continue
        result = event.payload.get("result")
        if not isinstance(result, dict):
            continue
        if result.get("kind") in PROJECT_CHANGE_RESULT_KINDS and result.get("ok") is not False:
            return index
    return None


def iter_command_results(result: dict[str, Any]) -> list[dict[str, Any]]:
    kind = result.get("kind")
    if kind == "run_command":
        command_result = result.get("result")
        return [command_result] if isinstance(command_result, dict) else []
    if kind in {"run_commands", "run_suggested_checks", "run_focused_test_commands"}:
        command_results = result.get("results")
        if isinstance(command_results, list):
            return [item for item in command_results if isinstance(item, dict)]
    return []


def command_result_key(result: dict[str, Any]) -> tuple[str, str]:
    command = result.get("command")
    cwd = result.get("cwd")
    return (command if isinstance(command, str) else "", cwd if isinstance(cwd, str) and cwd else ".")


def command_result_succeeded(result: dict[str, Any]) -> bool:
    return result.get("exit_code") == 0 and result.get("timed_out") is not True


def suggested_check_label(command: str, cwd: str) -> str:
    return command if cwd in {"", "."} else f"{command} (cwd={cwd})"


def find_large_changed_files(
    workspace: RunWorkspace,
    files: list[dict[str, object]],
    max_bytes: int | None = None,
    max_files: int = 10,
) -> tuple[list[dict[str, object]], int]:
    size_limit = FINAL_REVIEW_LARGE_FILE_BYTES if max_bytes is None else max_bytes
    root = workspace.root.resolve()
    large_files: list[dict[str, object]] = []
    total = 0
    for item in files:
        raw_path = item.get("path") if isinstance(item, dict) else None
        if not isinstance(raw_path, str) or not raw_path:
            continue
        try:
            path = (root / raw_path).resolve()
            if path != root and root not in path.parents:
                continue
            if not path.is_file():
                continue
            size_bytes = path.stat().st_size
        except OSError:
            continue
        if size_bytes <= size_limit:
            continue
        total += 1
        if len(large_files) < max_files:
            large_files.append({"path": raw_path, "size_bytes": size_bytes})
    return large_files, total


def final_review_scan_file_items(workspace: RunWorkspace, files: list[dict[str, object]]) -> list[dict[str, object]]:
    by_path: dict[str, dict[str, object]] = {}
    for item in files:
        raw_path = item.get("path") if isinstance(item, dict) else None
        if isinstance(raw_path, str) and raw_path:
            by_path.setdefault(raw_path, item)
    for path in session_project_change_paths(workspace):
        by_path.setdefault(path, {"path": path, "status": "session"})
    return list(by_path.values())


def session_project_change_paths(workspace: RunWorkspace) -> list[str]:
    events_path = workspace.session_dir / "events.jsonl"
    try:
        lines = events_path.read_text(encoding="utf-8").splitlines()
    except OSError:
        return []

    paths: set[str] = set()
    for line in lines:
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            continue
        if not isinstance(event, dict) or event.get("type") != "tool_result":
            continue
        result = event.get("result")
        if not isinstance(result, dict):
            continue
        if result.get("kind") not in PROJECT_CHANGE_RESULT_KINDS or result.get("ok") is not True:
            continue
        paths.update(extract_project_change_result_paths(result))
    return sorted(paths)


def extract_project_change_result_paths(value: Any) -> set[str]:
    paths: set[str] = set()
    if not isinstance(value, dict):
        return paths
    for key in ("path", "source", "destination"):
        item = value.get(key)
        if isinstance(item, str):
            add_project_change_result_path(paths, item)
    for key in ("paths", "files", "transfers"):
        item = value.get(key)
        if isinstance(item, list):
            for child in item:
                if isinstance(child, str):
                    add_project_change_result_path(paths, child)
                elif isinstance(child, dict):
                    paths.update(extract_project_change_result_paths(child))
        elif isinstance(item, dict):
            paths.update(extract_project_change_result_paths(item))
    return paths


def add_project_change_result_path(paths: set[str], value: str) -> None:
    path = value.strip()
    if not path or "\n" in path:
        return
    if path.startswith("-") or "://" in path:
        return
    candidate = Path(path)
    if candidate.is_absolute() or ".." in candidate.parts:
        return
    paths.add(path)


def find_secret_like_changed_files(
    workspace: RunWorkspace,
    files: list[dict[str, object]],
    max_bytes: int | None = None,
    max_findings: int = 10,
) -> tuple[list[dict[str, object]], int, bool]:
    byte_limit = FINAL_REVIEW_SECRET_SCAN_BYTES if max_bytes is None else max_bytes
    root = workspace.root.resolve()
    findings: list[dict[str, object]] = []
    total = 0
    truncated = False
    for item in files:
        raw_path = item.get("path") if isinstance(item, dict) else None
        if not isinstance(raw_path, str) or not raw_path:
            continue
        try:
            path = (root / raw_path).resolve()
            if path != root and root not in path.parents:
                continue
            if not path.is_file():
                continue
            with path.open("rb") as handle:
                content = handle.read(byte_limit + 1)
        except OSError:
            continue
        if b"\x00" in content:
            continue
        if len(content) > byte_limit:
            truncated = True
            content = content[:byte_limit]
        text = content.decode("utf-8", errors="ignore")
        for line_number, line in enumerate(text.splitlines(), start=1):
            label = secret_like_line_label(line)
            if not label:
                continue
            total += 1
            if len(findings) < max_findings:
                findings.append({"path": raw_path, "line": line_number, "label": label})
    return findings, total, truncated


def find_secret_like_git_diff_additions(
    workspace: RunWorkspace,
    max_bytes: int | None = None,
    max_findings: int = 10,
) -> tuple[list[dict[str, object]], int, bool, list[str]]:
    byte_limit = FINAL_REVIEW_SECRET_SCAN_BYTES if max_bytes is None else max_bytes
    findings: list[dict[str, object]] = []
    total = 0
    truncated = False
    warnings: list[str] = []
    for diff_args, source in (
        (["diff", "--unified=0", "--no-ext-diff"], "worktree"),
        (["diff", "--cached", "--unified=0", "--no-ext-diff"], "index"),
    ):
        result = run_readonly_git(workspace.root, diff_args)
        if not result.ok:
            warnings.append(result.stderr.strip() or f"git {' '.join(diff_args)} failed")
            continue
        output = result.stdout
        output_bytes = output.encode("utf-8", errors="ignore")
        if len(output_bytes) > byte_limit:
            truncated = True
            output = output_bytes[:byte_limit].decode("utf-8", errors="ignore")
        diff_findings, diff_total = secret_like_git_diff_addition_findings(
            output,
            source,
            max_findings=max(0, max_findings - len(findings)),
        )
        total += diff_total
        findings.extend(diff_findings)
    return findings, total, truncated, warnings


def secret_like_git_diff_addition_findings(
    diff_text: str,
    source: str,
    max_findings: int = 10,
) -> tuple[list[dict[str, object]], int]:
    findings: list[dict[str, object]] = []
    total = 0
    current_file = ""
    new_line: int | None = None
    for line in diff_text.splitlines():
        if line.startswith("+++ "):
            current_file = normalize_diff_new_file_path(line[4:].strip())
            continue
        if line.startswith("@@ "):
            new_line = parse_diff_hunk_new_start(line)
            continue
        if line.startswith("+") and not line.startswith("+++"):
            label = secret_like_line_label(line[1:])
            if label:
                total += 1
                if len(findings) < max_findings:
                    findings.append(
                        {
                            "path": current_file or "<unknown>",
                            "line": new_line or 0,
                            "label": label,
                            "source": source,
                        }
                    )
            if new_line is not None:
                new_line += 1
            continue
        if line.startswith("-") and not line.startswith("---"):
            continue
        if new_line is not None:
            new_line += 1
    return findings, total


def normalize_diff_new_file_path(path: str) -> str:
    if path == "/dev/null":
        return path
    if path.startswith("b/"):
        return path[2:]
    return path


def parse_diff_hunk_new_start(header: str) -> int | None:
    match = re.search(r"\+(\d+)(?:,\d+)?", header)
    if not match:
        return None
    return int(match.group(1))


def secret_like_line_label(line: str) -> str | None:
    for label, pattern in SECRET_LIKE_PATTERNS:
        match = pattern.search(line)
        if not match:
            continue
        if label == "credential assignment":
            name = match.groupdict().get("name")
            value = match.groupdict().get("value")
            if not secret_like_assignment_is_high_confidence(name, value):
                continue
            return name.upper() if isinstance(name, str) and name else label
        return label
    return None


def secret_like_assignment_is_high_confidence(name: object, value: object) -> bool:
    if not isinstance(name, str) or not isinstance(value, str):
        return True
    normalized_name = name.upper().replace("-", "_")
    normalized_value = value.lower()
    if normalized_name.endswith(("_PATH", "_TRUNCATED", "_WARNINGS", "_TOKENS")):
        return False
    if re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", value):
        return False
    if any(marker in normalized_value for marker in ("testsecret", "placeholder", "dummy", "example", "redacted")):
        return False
    if value.startswith(("src/", "tests/", "test/")) or value.endswith((".py", ".txt", ".json", ".md")):
        return False
    return True


def find_nested_git_repositories(workspace: RunWorkspace, max_repos: int = 10) -> tuple[list[str], int]:
    root = workspace.root.resolve()
    ignored_dirs = {
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
    repos: list[str] = []
    total = 0
    for current, dirs, files in os.walk(root):
        current_path = Path(current)
        if current_path == root:
            if ".git" in dirs:
                dirs.remove(".git")
        elif ".git" in dirs or ".git" in files:
            total += 1
            if len(repos) < max_repos:
                repos.append(current_path.relative_to(root).as_posix())
            if ".git" in dirs:
                dirs.remove(".git")
        dirs[:] = [
            name
            for name in dirs
            if name not in ignored_dirs and not name.endswith(".egg-info")
        ]
    return repos, total


def find_changed_gitlinks(workspace: RunWorkspace, max_links: int = 10) -> tuple[list[str], int, list[str]]:
    links: list[str] = []
    total = 0
    warnings: list[str] = []
    seen: set[str] = set()
    for diff_args in (
        ["diff", "--raw", "--no-renames"],
        ["diff", "--cached", "--raw", "--no-renames"],
    ):
        result = run_readonly_git(workspace.root, diff_args)
        if not result.ok:
            warnings.append(result.stderr.strip() or f"git {' '.join(diff_args)} failed")
            continue
        for line in result.stdout.splitlines():
            path = gitlink_path_from_raw_diff_line(line)
            if path is None or path in seen:
                continue
            seen.add(path)
            total += 1
            if len(links) < max_links:
                links.append(path)
    return links, total, warnings


def gitlink_path_from_raw_diff_line(line: str) -> str | None:
    metadata, separator, path = line.partition("\t")
    if not separator:
        return None
    fields = metadata.split()
    if len(fields) < 2:
        return None
    old_mode = fields[0].removeprefix(":")
    new_mode = fields[1]
    if old_mode != "160000" and new_mode != "160000":
        return None
    return path.strip() or None


def find_hidden_tracked_git_changes(workspace: RunWorkspace, max_files: int = 10) -> tuple[list[dict[str, str]], int, list[str]]:
    status = read_git_status(workspace)
    if not status.ok:
        return [], 0, [status.stderr.strip() or "git status failed"]
    findings: list[dict[str, str]] = []
    total = 0
    for path, short_status in parse_git_short_status(status.stdout):
        if short_status == "??":
            continue
        if not should_ignore_git_path(workspace.root, path):
            continue
        total += 1
        if len(findings) < max_files:
            findings.append({"path": path, "status": short_status})
    return findings, total, []


def find_unsafe_changed_symlinks(
    workspace: RunWorkspace,
    files: list[dict[str, object]],
    max_links: int = 10,
) -> tuple[list[dict[str, str]], int, list[str], set[str]]:
    root = workspace.root.resolve()
    candidates: dict[str, str] = {}
    warnings: list[str] = []

    for item in files:
        raw_path = item.get("path") if isinstance(item, dict) else None
        if not isinstance(raw_path, str) or not raw_path:
            continue
        link_path = root / raw_path
        try:
            if link_path.is_symlink():
                candidates.setdefault(raw_path, "worktree")
        except OSError:
            continue

    for diff_args, source in (
        (["diff", "--raw", "--no-renames"], "worktree"),
        (["diff", "--cached", "--raw", "--no-renames"], "index"),
    ):
        result = run_readonly_git(workspace.root, diff_args)
        if not result.ok:
            warnings.append(result.stderr.strip() or f"git {' '.join(diff_args)} failed")
            continue
        for line in result.stdout.splitlines():
            path = symlink_path_from_raw_diff_line(line)
            if path is not None:
                candidates.setdefault(path, source)

    findings: list[dict[str, str]] = []
    reasons: set[str] = set()
    total = 0
    for relative_path, source in sorted(candidates.items()):
        target = read_changed_symlink_target(workspace, relative_path, source)
        if target is None:
            continue
        risk = changed_symlink_target_risk(root, root / relative_path, target)
        if risk is None:
            continue
        reasons.add(risk)
        total += 1
        if len(findings) < max_links:
            findings.append({"path": relative_path, "target": target, "reason": risk})
    return findings, total, warnings, reasons


def symlink_path_from_raw_diff_line(line: str) -> str | None:
    metadata, separator, path = line.partition("\t")
    if not separator:
        return None
    fields = metadata.split()
    if len(fields) < 2:
        return None
    new_mode = fields[1]
    if new_mode != "120000":
        return None
    return path.strip() or None


def read_changed_symlink_target(workspace: RunWorkspace, relative_path: str, source: str) -> str | None:
    link_path = workspace.root / relative_path
    if source == "worktree" or link_path.is_symlink():
        try:
            return os.readlink(link_path)
        except OSError:
            if source == "worktree":
                return None
    result = run_readonly_git(workspace.root, ["show", f":{relative_path}"])
    if not result.ok:
        return None
    target = result.stdout.strip()
    return target or None


def changed_symlink_target_risk(root: Path, link_path: Path, target: str) -> str | None:
    target_path = Path(target)
    if target_path.is_absolute():
        resolved = target_path.resolve(strict=False)
    else:
        resolved = (link_path.parent / target_path).resolve(strict=False)
    if resolved != root and root not in resolved.parents:
        return "points outside project"
    if is_protected_project_path(root, resolved):
        return "points into protected project path"
    if should_ignore_path(root, resolved):
        return "points into ignored project path"
    return None


def read_git_operation_state(workspace: RunWorkspace) -> dict[str, object]:
    git_dir_result = run_readonly_git(workspace.root, ["rev-parse", "--git-dir"])
    if not git_dir_result.ok:
        return {"ok": False, "operations": [], "message": git_dir_result.stderr or "Not a git repository."}
    raw_git_dir = git_dir_result.stdout.strip().splitlines()[0] if git_dir_result.stdout.strip() else ""
    if not raw_git_dir:
        return {"ok": False, "operations": [], "message": "Could not determine git dir."}
    git_dir = Path(raw_git_dir)
    if not git_dir.is_absolute():
        git_dir = (workspace.root / git_dir).resolve()
    operation_paths = (
        ("merge", "MERGE_HEAD"),
        ("cherry-pick", "CHERRY_PICK_HEAD"),
        ("revert", "REVERT_HEAD"),
        ("rebase", "rebase-merge"),
        ("rebase", "rebase-apply"),
        ("bisect", "BISECT_LOG"),
    )
    operations: list[dict[str, str]] = []
    seen: set[str] = set()
    for name, relative in operation_paths:
        if name in seen:
            continue
        if (git_dir / relative).exists():
            operations.append({"operation": name, "path": relative})
            seen.add(name)
    message = "No git operation in progress." if not operations else "Git operation in progress."
    return {"ok": True, "operations": operations, "message": message}
