from __future__ import annotations

from .workspace_code_intel import (
    check_config_file_paths,
    check_python_file_paths,
    config_format_for_path,
)
from .workspace_core import RunWorkspace
from .workspace_git_changes import read_git_changes
from .workspace_git_ops import read_git_diff_hunks
from .workspace_git_utils import (
    combine_git_output,
    run_readonly_git,
)
from .workspace_review_checks import suggest_project_checks
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
from .workspace_untracked_previews import read_untracked_file_previews


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
