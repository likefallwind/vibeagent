from __future__ import annotations

from pathlib import Path

from .workspace_core import RunWorkspace
from .workspace_project_info import (
    list_files,
    read_makefile_targets,
    read_package_json_scripts,
)
from .workspace_review_tests import (
    add_check_suggestion,
    check_suggestion_sort_key,
    find_python_package_dirs,
    find_python_test_dirs,
    is_check_script_name,
)


def suggest_project_checks(workspace: RunWorkspace, max_commands: int = 20) -> dict[str, object]:
    if max_commands < 1:
        raise ValueError("max_commands must be at least 1.")
    if max_commands > 100:
        raise ValueError("max_commands must be at most 100.")

    files = list_files(workspace.root)
    from .workspace_review_ops import read_git_changes

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
