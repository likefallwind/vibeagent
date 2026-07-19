from __future__ import annotations

import shlex
from pathlib import Path

from .workspace_core import JS_TEST_SUFFIXES, TEST_FILE_SUFFIXES, RunWorkspace
from .workspace_focused_test_commands import (
    add_focused_test_command,
    add_focused_test_commands_for_file,
    focused_npm_test_command,
    nearest_package_json,
    preferred_test_script_name,
    project_has_pytest_evidence,
)
from .workspace_paths import should_ignore_path
from .workspace_project_info import list_files, missing_command_tool
from .workspace_resolve import resolve_inside_run


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

    from .workspace_review_ops import read_git_changes

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
