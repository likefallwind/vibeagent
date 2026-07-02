from __future__ import annotations

import re
import shlex
import shutil
from pathlib import Path

from .workspace_git_utils import (
    combine_git_output,
    empty_git_change,
    parse_git_numstat,
    parse_git_remotes,
    parse_git_short_status,
    redact_git_text,
    redact_git_url,
    run_git_mutation,
    run_readonly_git,
    should_ignore_git_path,
)
from .workspace_core import (
    GIT_CONFLICT_MARKERS,
    GIT_UNMERGED_STATUS_CODES,
    JS_TEST_SUFFIXES,
    PROJECT_INSTRUCTION_CONTENT_LIMIT,
    PROJECT_INSTRUCTION_FILE_NAMES,
    PROJECT_TODO_MARKERS,
    PROJECT_TODO_PATTERN,
    TEST_FILE_SUFFIXES,
    GitCommandResult,
    RunWorkspace,
    create_run_workspace,
    make_run_id,
)
from .workspace_resolve import resolve_command_cwd, resolve_inside_run, resolve_mutation_path
from .workspace_search import (
    search_project,
    search_project_result,
    search_project_contexts_result,
    find_project_files_result,
    format_search_context,
    glob_project_files,
    validate_glob_pattern,
    list_project_files,
    list_project_tree,
    build_repo_map,
)
from .workspace_edit_ops import (
    write_run_file,
    preview_write_run_file,
    build_write_file,
    write_run_files,
    preview_write_run_files,
    prepare_write_run_files,
    edit_project_file,
    preview_edit_project_file,
    build_edit_file,
    multi_edit_project_file,
    preview_multi_edit_project_file,
    build_multi_edit,
    json_set_project_file,
    preview_json_set_project_file,
    json_remove_project_file,
    preview_json_remove_project_file,
    json_patch_project_file,
    preview_json_patch_project_file,
    build_json_set,
    build_json_remove,
    build_json_patch,
    apply_json_patch_operation,
    add_json_pointer_value,
    set_json_pointer_value,
    remove_json_pointer_value,
    parse_json_pointer,
    parse_json_array_index,
    format_json_document,
    replace_project_file_lines,
    preview_replace_project_file_lines,
    build_replace_lines,
    insert_project_file_lines,
    preview_insert_project_file_lines,
    build_insert_lines,
    append_project_file,
    preview_append_project_file,
    build_append_file,
    regex_replace_project_file,
    preview_regex_replace_project_file,
    build_regex_replacement,
    delete_project_file,
    preview_delete_project_file,
    delete_project_files,
    preview_delete_project_files,
    build_delete_files,
    build_delete_file,
    move_project_file,
    preview_move_project_file,
    move_project_files,
    preview_move_project_files,
    prepare_project_file_transfers,
    copy_project_file,
    preview_copy_project_file,
    copy_project_files,
    preview_copy_project_files,
    prepare_project_file_copies,
    prepare_project_file_transfer,
    move_project_directory,
    move_project_directories,
    preview_move_project_directory,
    preview_move_project_directories,
    prepare_project_directory_move,
    copy_project_directory,
    copy_project_directories,
    preview_copy_project_directory,
    preview_copy_project_directories,
    prepare_project_directory_copy,
    validate_project_directory_transfer_batch,
    create_project_directory,
    create_project_directories,
    preview_create_project_directory,
    preview_create_project_directories,
    delete_project_empty_directory,
    delete_project_empty_directories,
    preview_delete_project_empty_directory,
    preview_delete_project_empty_directories,
    set_project_file_executable,
    preview_set_project_file_executable,
    patch_project_file,
    check_project_patch,
    patch_project_files,
    check_project_patches,
    split_unified_patch_by_file,
    is_file_header_at,
    parse_unified_diff_path,
    apply_unified_patch,
    parse_unified_patch_hunks,
)
from .workspace_code_intel import (
    read_python_symbol_outline,
    read_code_outline,
    code_language_for_path,
    supports_code_outline_path,
    collect_generic_code_outline,
    inspect_code_dependencies,
    find_code_references,
    find_code_definitions,
    preview_code_rename,
    apply_code_rename,
    build_code_reference_pattern,
    collect_code_rename_replacements,
    apply_code_rename_replacements,
    collect_code_imports,
    parse_code_import_line,
    parse_go_import_line,
    is_generic_import_line,
    generic_symbol_matches,
    check_python_syntax,
    check_config_syntax,
    config_format_for_path,
    check_config_file_paths,
    check_python_file_paths,
    inspect_python_dependencies,
    build_python_module_index,
    module_name_for_python_path,
    collect_python_dependency_imports,
    resolve_import_from_module,
    resolve_import_target,
    is_local_python_module,
    python_import_sort_key,
    find_python_definitions,
    replace_python_definition,
    preview_replace_python_definition,
    collect_python_definition_matches,
    python_definition_start_line,
    find_python_calls,
    inspect_python_call_graph,
    collect_python_call_graph_edges,
    collect_python_call_matches,
    preview_python_rename,
    apply_python_rename,
    collect_python_rename_replacements,
    find_identifier_column,
    apply_python_rename_replacements,
    python_call_name,
    call_matches_symbol,
    find_python_references,
    collect_python_references,
    collect_python_imports,
    format_import_alias,
    import_line_number,
    collect_python_symbols,
    split_replacement_lines,
    build_simple_diff,
)
from .workspace_file_read import (
    add_output_line_reference,
    classify_output_diagnostic_line,
    count_file_lines,
    detect_binary_file,
    extract_output_line_references,
    format_line_excerpt,
    format_numbered_lines,
    is_url_reference_match,
    looks_like_project_source_reference,
    normalize_output_reference_path,
    parse_image_header,
    parse_jpeg_dimensions,
    parse_webp_dimensions,
    read_output_contexts_result,
    read_output_diagnostics_result,
    read_project_file,
    read_project_file_context_result,
    read_project_file_info,
    read_project_file_result,
    read_project_file_tail_result,
    read_project_image_info,
    read_utf8_text_file,
    truncate_utf8_text_bytes,
)
from .workspace_git_ops import (
    apply_git_stash,
    commit_staged_changes,
    drop_git_stash,
    fetch_git_remote,
    git_branch_exists,
    git_stash_candidate_paths,
    git_status_has_non_runtime_changes,
    normalize_git_index_paths,
    parse_git_diff_file_path,
    parse_git_diff_hunks,
    parse_git_stash_list,
    parse_git_unmerged_status,
    preview_apply_git_stash,
    preview_commit_staged_changes,
    preview_drop_git_stash,
    preview_fetch_git_remote,
    preview_pull_git_upstream,
    preview_push_git_upstream,
    preview_restore_git_paths,
    preview_stage_git_paths,
    preview_stash_git_changes,
    preview_switch_git_branch,
    preview_unstage_git_paths,
    pull_git_upstream,
    push_git_upstream,
    read_git_blame,
    read_git_branches,
    read_git_conflicts,
    read_git_current_branch,
    read_git_diff,
    read_git_diff_hunks,
    read_git_head,
    read_git_info,
    read_git_log,
    read_git_show,
    read_git_stashes,
    read_git_status,
    read_git_upstream_parts,
    restore_git_paths,
    select_git_fetch_remote,
    stage_git_paths,
    stash_git_changes,
    switch_git_branch,
    unstage_git_paths,
    validate_git_branch_name,
    validate_git_stash_ref,
    validate_git_tracked_paths,
)
from .workspace_project_info import (
    first_command_executable,
    format_command_hint,
    is_shell_assignment,
    list_files,
    list_search_files,
    missing_command_tool,
    read_environment_info,
    read_makefile_targets,
    read_package_json_scripts,
    read_project_command_hints,
    read_project_commands,
    read_project_instruction_sources,
    read_project_instructions,
    read_project_manifests,
    read_project_todos,
    read_pyproject_scripts,
    read_workspace_snapshot,
)
from .workspace_paths import (
    gitignore_pattern_matches,
    gitignore_rule_bases,
    gitignore_scoped_path,
    is_protected_project_path,
    is_sensitive_project_path,
    path_has_directory,
    path_matches_gitignore,
    read_gitignore_patterns,
    should_ignore_path,
)


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


def find_related_tests(
    workspace: RunWorkspace,
    paths: list[str] | None = None,
    max_paths: int = 100,
    max_candidates: int = 200,
) -> dict[str, object]:
    if max_paths < 1:
        raise ValueError("max_paths must be at least 1.")
    if max_paths > 500:
        raise ValueError("max_paths must be at most 500.")
    if max_candidates < 1:
        raise ValueError("max_candidates must be at least 1.")
    if max_candidates > 1000:
        raise ValueError("max_candidates must be at most 1000.")

    files = list_files(workspace.root)
    test_files = [path for path in files if is_project_test_file(path)]
    target_paths = normalize_related_test_targets(workspace, paths, max_paths=max_paths)
    candidates: list[dict[str, object]] = []
    seen: set[tuple[str, str]] = set()
    for target in target_paths:
        for candidate, reason, score in related_test_candidates_for_target(target, test_files):
            key = (target, candidate)
            if key in seen:
                continue
            seen.add(key)
            candidates.append(
                {
                    "source_path": target,
                    "test_path": candidate,
                    "score": score,
                    "reason": reason,
                }
            )

    candidates.sort(key=related_test_candidate_sort_key)
    total = len(candidates)
    return {
        "ok": True,
        "target_paths": target_paths,
        "candidates": candidates[:max_candidates],
        "total": total,
        "truncated": total > max_candidates,
        "test_files_total": len(test_files),
        "message": f"Found {total} related test candidate(s) for {len(target_paths)} target file(s).",
    }


def suggest_focused_test_commands(
    workspace: RunWorkspace,
    paths: list[str] | None = None,
    max_paths: int = 100,
    max_candidates: int = 200,
    max_commands: int = 50,
) -> dict[str, object]:
    if max_commands < 1:
        raise ValueError("max_commands must be at least 1.")
    if max_commands > 500:
        raise ValueError("max_commands must be at most 500.")

    related = find_related_tests(
        workspace,
        paths=paths,
        max_paths=max_paths,
        max_candidates=max_candidates,
    )
    files = list_files(workspace.root)
    pytest_evidence = project_has_pytest_evidence(workspace.root, files)
    commands: list[dict[str, object]] = []
    seen_tests: set[str] = set()
    for item in related["candidates"]:
        if not isinstance(item, dict):
            continue
        test_path = item.get("test_path")
        if not isinstance(test_path, str) or test_path in seen_tests:
            continue
        seen_tests.add(test_path)
        add_focused_test_commands_for_file(
            commands,
            workspace.root,
            files,
            test_path,
            source=str(item.get("source_path") or test_path),
            candidate_reason=str(item.get("reason") or "Related test candidate."),
            pytest_evidence=pytest_evidence,
        )

    total = len(commands)
    return {
        "ok": True,
        "target_paths": related["target_paths"],
        "commands": commands[:max_commands],
        "total": total,
        "truncated": total > max_commands,
        "related_tests_total": related["total"],
        "message": f"Suggested {total} focused test command(s) from {int(related['total'])} related test candidate(s).",
    }


def add_focused_test_commands_for_file(
    commands: list[dict[str, object]],
    root: Path,
    files: list[str],
    test_path: str,
    source: str,
    candidate_reason: str,
    pytest_evidence: bool,
) -> None:
    path = Path(test_path)
    suffix = path.suffix.lower()
    quoted_test_path = shlex.quote(test_path)
    if suffix == ".py":
        if pytest_evidence:
            add_focused_test_command(
                commands,
                command=f"python -m pytest {quoted_test_path}",
                cwd=".",
                test_path=test_path,
                source=source,
                reason=f"{candidate_reason} Pytest project evidence was found.",
            )
        test_dir = path.parent.as_posix()
        pattern = path.name
        if test_dir and test_dir != ".":
            command = f"python -m unittest discover -s {shlex.quote(test_dir)} -p {shlex.quote(pattern)}"
        else:
            command = f"python -m unittest {path.with_suffix('').as_posix().replace('/', '.')}"
        add_focused_test_command(
            commands,
            command=command,
            cwd=".",
            test_path=test_path,
            source=source,
            reason=f"{candidate_reason} Python test file can be run through unittest discovery.",
        )
        return

    if suffix in {".js", ".jsx", ".ts", ".tsx", ".mjs", ".cjs"}:
        package_command = focused_npm_test_command(root, files, test_path)
        if package_command is not None:
            command, cwd = package_command
            add_focused_test_command(
                commands,
                command=command,
                cwd=cwd,
                test_path=test_path,
                source=source,
                reason=f"{candidate_reason} package.json defines a test script near this test file.",
            )


def add_focused_test_command(
    commands: list[dict[str, object]],
    command: str,
    cwd: str,
    test_path: str,
    source: str,
    reason: str,
) -> None:
    if any(item["command"] == command and item["cwd"] == cwd for item in commands):
        return
    missing_tool = missing_command_tool(command)
    commands.append(
        {
            "command": command,
            "cwd": cwd,
            "test_path": test_path,
            "source": source,
            "reason": reason,
            "available": missing_tool is None,
            "missing_tool": missing_tool,
        }
    )


def focused_npm_test_command(root: Path, files: list[str], test_path: str) -> tuple[str, str] | None:
    package_path = nearest_package_json(files, test_path)
    if package_path is None:
        return ("npm test -- " + shlex.quote(test_path), ".")
    package_file = root / package_path
    script_name = preferred_test_script_name(package_file)
    if script_name is None:
        return None
    cwd = package_path.parent.as_posix()
    if cwd == ".":
        cwd = "."
    relative_test = Path(test_path)
    if cwd != ".":
        try:
            relative_test = Path(test_path).relative_to(cwd)
        except ValueError:
            relative_test = Path(test_path)
    test_arg = shlex.quote(relative_test.as_posix())
    if script_name == "test":
        return (f"npm test -- {test_arg}", cwd)
    return (f"npm run {shlex.quote(script_name)} -- {test_arg}", cwd)


def nearest_package_json(files: list[str], test_path: str) -> Path | None:
    file_set = set(files)
    current = Path(test_path).parent
    for parent in [current, *current.parents]:
        package_path = parent / "package.json"
        package_text = package_path.as_posix()
        if package_text in file_set:
            return package_path
        if parent == Path("."):
            break
    return Path("package.json") if "package.json" in file_set else None


def preferred_test_script_name(package_json_path: Path) -> str | None:
    scripts = read_package_json_scripts(package_json_path)
    if any(name == "test" for name, _script in scripts):
        return "test"
    for name, _script in scripts:
        if name.startswith("test:") or name in {"tests", "unit", "unit-test"}:
            return name
    return None


def project_has_pytest_evidence(root: Path, files: list[str]) -> bool:
    evidence_names = {"pytest.ini", ".pytest.ini"}
    if any(Path(path).name in evidence_names for path in files):
        return True
    for relative in files:
        name = Path(relative).name.lower()
        if name not in {"pyproject.toml", "setup.cfg", "tox.ini", "requirements.txt", "requirements-dev.txt"}:
            continue
        try:
            content = read_utf8_text_file(root / relative, relative)
        except ValueError:
            continue
        if re.search(r"(^|[^A-Za-z0-9_-])pytest([^A-Za-z0-9_-]|$)", content):
            return True
    return False


def normalize_related_test_targets(workspace: RunWorkspace, paths: list[str] | None, max_paths: int) -> list[str]:
    if paths:
        targets: list[str] = []
        for path in paths:
            if not isinstance(path, str) or not path.strip():
                raise ValueError("paths must contain non-empty project-relative paths.")
            resolved = resolve_inside_run(workspace.root, path.strip())
            if should_ignore_path(workspace.root, resolved):
                continue
            targets.append(resolved.relative_to(workspace.root).as_posix())
        return sorted(dict.fromkeys(targets))[:max_paths]

    changes = read_git_changes(workspace)
    if not changes.get("ok"):
        return []
    changed_paths = [
        str(item["path"])
        for item in changes.get("files", [])
        if isinstance(item, dict) and isinstance(item.get("path"), str)
    ]
    return sorted(dict.fromkeys(changed_paths))[:max_paths]


def is_project_test_file(path: str) -> bool:
    relative = Path(path)
    name = relative.name
    lower_name = name.lower()
    if relative.suffix.lower() not in TEST_FILE_SUFFIXES:
        return False
    if lower_name.startswith("test_") or lower_name.endswith("_test.py"):
        return True
    if any(part in {"tests", "test", "__tests__"} for part in relative.parts):
        return True
    stem = relative.with_suffix("").name.lower()
    return stem.endswith(JS_TEST_SUFFIXES)


def related_test_candidates_for_target(target: str, test_files: list[str]) -> list[tuple[str, str, int]]:
    if is_project_test_file(target):
        return [(target, "Target path is itself a test file.", 100)] if target in test_files else []

    target_path = Path(target)
    source_stem = source_module_stem(target_path)
    if not source_stem:
        return []

    candidates: list[tuple[str, str, int]] = []
    expected_names = expected_test_names(target_path, source_stem)
    expected_paths = expected_test_paths(target_path, source_stem)
    source_parts = set(target_path.with_suffix("").parts)
    for test_file in test_files:
        test_path = Path(test_file)
        test_name = test_path.name
        test_stem = normalized_test_stem(test_path)
        if test_file in expected_paths:
            candidates.append((test_file, "Test path mirrors the source path.", 95))
        elif test_name in expected_names:
            candidates.append((test_file, f"Test filename matches {target_path.name}.", 90))
        elif test_stem == source_stem:
            candidates.append((test_file, f"Test stem matches source stem {source_stem}.", 80))
        elif source_stem in test_stem.split("_"):
            candidates.append((test_file, f"Test stem contains source stem {source_stem}.", 65))
        elif source_stem and source_stem in test_stem:
            candidates.append((test_file, f"Test name contains source stem {source_stem}.", 55))
        elif source_parts and source_parts.intersection(test_path.with_suffix("").parts):
            candidates.append((test_file, "Test path shares a source path component.", 35))
    return candidates


def source_module_stem(path: Path) -> str:
    if path.stem == "__init__":
        return path.parent.name
    return path.stem


def normalized_test_stem(path: Path) -> str:
    stem = path.with_suffix("").name
    for suffix in JS_TEST_SUFFIXES:
        if stem.endswith(suffix):
            stem = stem[: -len(suffix)]
    if stem.startswith("test_"):
        stem = stem[5:]
    if stem.endswith("_test"):
        stem = stem[:-5]
    return stem


def expected_test_names(path: Path, source_stem: str) -> set[str]:
    suffix = path.suffix
    if suffix == ".py":
        return {f"test_{source_stem}.py", f"{source_stem}_test.py"}
    if suffix in {".js", ".jsx", ".ts", ".tsx", ".mjs", ".cjs"}:
        return {f"{source_stem}.test{suffix}", f"{source_stem}.spec{suffix}"}
    return {f"test_{source_stem}{suffix}", f"{source_stem}_test{suffix}"}


def expected_test_paths(path: Path, source_stem: str) -> set[str]:
    expected: set[str] = set()
    parent = path.parent
    for name in expected_test_names(path, source_stem):
        expected.add((parent / name).as_posix())
        expected.add((parent / "__tests__" / name).as_posix())
        expected.add((Path("tests") / name).as_posix())
        if len(path.parts) > 1:
            expected.add((Path("tests") / Path(*path.parts[1:]).parent / name).as_posix())
    return expected


def related_test_candidate_sort_key(item: dict[str, object]) -> tuple[str, int, str]:
    return (str(item["source_path"]), -int(item["score"]), str(item["test_path"]))


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
