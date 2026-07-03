from __future__ import annotations

from pathlib import Path

from .workspace_code_intel import (
    check_config_file_paths,
    check_python_file_paths,
    config_format_for_path,
)
from .workspace_core import RunWorkspace
from .workspace_file_read import (
    detect_binary_file,
    read_utf8_text_file,
    truncate_utf8_text_bytes,
)
from .workspace_git_ops import read_git_diff_hunks, read_git_status
from .workspace_git_utils import (
    combine_git_output,
    empty_git_change,
    parse_git_numstat,
    parse_git_short_status,
    run_readonly_git,
    should_ignore_git_path,
)
from .workspace_project_info import (
    list_files,
    read_makefile_targets,
    read_package_json_scripts,
)
from .workspace_review_tests import (
    add_check_suggestion,
    add_focused_test_command,
    add_focused_test_commands_for_file,
    check_suggestion_sort_key,
    expected_test_names,
    expected_test_paths,
    find_python_package_dirs,
    find_python_test_dirs,
    find_related_tests,
    focused_npm_test_command,
    is_check_script_name,
    is_project_test_file,
    nearest_package_json,
    normalize_related_test_targets,
    normalized_test_stem,
    preferred_test_script_name,
    project_has_pytest_evidence,
    related_test_candidate_sort_key,
    related_test_candidates_for_target,
    source_module_stem,
    suggest_focused_test_commands,
)
from .workspace_resolve import resolve_inside_run


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
        candidate = Path(relative_path)
        if candidate.is_absolute() or ".." in candidate.parts:
            previews.append(
                {
                    "path": relative_path,
                    "size_bytes": 0,
                    "is_binary": False,
                    "content": "",
                    "truncated": False,
                    "message": f"Unsafe untracked path preview omitted: {relative_path}",
                }
            )
            continue
        lexical_target = workspace.root / candidate
        if lexical_target.is_symlink():
            try:
                size_bytes = lexical_target.lstat().st_size
            except OSError:
                size_bytes = 0
            previews.append(
                {
                    "path": relative_path,
                    "size_bytes": size_bytes,
                    "is_binary": False,
                    "content": "",
                    "truncated": False,
                    "message": "Untracked symlink preview omitted.",
                }
            )
            continue
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
