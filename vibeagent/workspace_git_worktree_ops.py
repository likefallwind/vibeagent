from __future__ import annotations

from pathlib import Path
import re
from uuid import uuid4

from .workspace_core import RunWorkspace
from .workspace_git_utils import combine_git_output, run_git_mutation, run_readonly_git
from .worktree_cleanup import remove_created_worktree
from .worktree_include import copy_worktree_includes


WORKTREE_NAME_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_-]{0,47}$")


def enter_git_worktree(
    workspace: RunWorkspace,
    *,
    name: str | None = None,
    path: str | None = None,
) -> dict[str, object]:
    context = _worktree_context(workspace.root)
    if not context["ok"]:
        return _enter_failure(workspace, str(context["message"]))

    current_top = Path(str(context["current_top"]))
    relative_root = Path(str(context["relative_root"]))
    entries = list(context["entries"])
    if path is not None:
        selected = _resolve_existing_worktree_path(workspace.root, path, entries)
        if selected is None:
            return _enter_failure(workspace, f"Path is not a registered worktree for this repository: {path}")
        if selected == current_top:
            return _enter_failure(workspace, f"The session is already using worktree: {selected}")
        project_root = (selected / relative_root).resolve()
        if not project_root.is_dir():
            return _enter_failure(workspace, f"Project subdirectory does not exist in worktree: {project_root}")
        branch = _entry_branch(entries, selected)
        return {
            "ok": True,
            "path": str(project_root),
            "branch": branch,
            "created": False,
            "previous_root": str(workspace.root),
            "message": f"Switched agent workspace to existing worktree {project_root}.",
        }

    safe_name = name or f"agent-{uuid4().hex[:10]}"
    if not WORKTREE_NAME_PATTERN.fullmatch(safe_name):
        return _enter_failure(
            workspace,
            "Worktree name must be 1-48 ASCII letters, digits, underscores, or hyphens and start with a letter or digit.",
        )
    if relative_root != Path("."):
        tracked_root = run_readonly_git(current_top, ["cat-file", "-e", f"HEAD:{relative_root.as_posix()}"])
        if not tracked_root.ok:
            return _enter_failure(
                workspace,
                f"Project subdirectory is not present in HEAD and cannot be opened in a new worktree: {relative_root}",
            )
    main_top = Path(str(context["main_top"]))
    runtime_root = main_top / ".vibeagent"
    worktrees_root = runtime_root / "worktrees"
    if runtime_root.is_symlink() or worktrees_root.is_symlink():
        return _enter_failure(workspace, f"Worktree storage path must not be a symlink: {worktrees_root}")
    if (runtime_root.exists() and not runtime_root.is_dir()) or (worktrees_root.exists() and not worktrees_root.is_dir()):
        return _enter_failure(workspace, f"Worktree storage path is not a directory: {worktrees_root}")
    try:
        worktrees_root.mkdir(parents=True, exist_ok=True)
    except OSError as error:
        return _enter_failure(workspace, f"Could not create worktree storage path {worktrees_root}: {error}")
    if worktrees_root.is_symlink() or not worktrees_root.is_dir():
        return _enter_failure(workspace, f"Worktree storage path is not a regular directory: {worktrees_root}")
    target = worktrees_root / safe_name
    if target.exists() or target.is_symlink():
        return _enter_failure(workspace, f"Worktree path already exists: {target}")

    branch = f"vibeagent/{safe_name}"
    result = run_git_mutation(current_top, ["worktree", "add", "--quiet", "-b", branch, str(target), "HEAD"])
    if not result.ok:
        return _enter_failure(workspace, combine_git_output(result) or "git worktree add failed.")
    project_root = (target / relative_root).resolve()
    if not project_root.is_dir():
        remove_created_worktree(main_top, target, branch)
        return _enter_failure(workspace, f"Created worktree is missing project subdirectory: {project_root}")
    try:
        copy_worktree_includes(workspace.root, project_root)
    except ValueError as error:
        remove_created_worktree(main_top, target, branch)
        return _enter_failure(
            workspace,
            f"Could not apply .worktreeinclude: {error}",
        )
    return {
        "ok": True,
        "path": str(project_root),
        "branch": branch,
        "created": True,
        "previous_root": str(workspace.root),
        "message": f"Created and entered isolated worktree {project_root} on branch {branch}.",
    }


def exit_git_worktree(workspace: RunWorkspace) -> dict[str, object]:
    context = _worktree_context(workspace.root)
    if not context["ok"]:
        return _exit_failure(workspace, str(context["message"]))
    current_top = Path(str(context["current_top"]))
    main_top = Path(str(context["main_top"]))
    if workspace.root_history:
        project_root = workspace.root_history[-1].resolve()
        if not project_root.is_dir():
            return _exit_failure(workspace, f"Previous project directory does not exist: {project_root}")
        previous_context = _worktree_context(project_root)
        if not previous_context["ok"] or Path(str(previous_context["main_top"])) != main_top:
            return _exit_failure(workspace, f"Previous project directory is not from the same git repository: {project_root}")
    elif current_top == main_top:
        return _exit_failure(workspace, "The session is already using the repository's main worktree.")
    else:
        project_root = (main_top / Path(str(context["relative_root"]))).resolve()
    if not project_root.is_dir():
        return _exit_failure(workspace, f"Main project directory does not exist: {project_root}")
    return {
        "ok": True,
        "path": str(project_root),
        "previous_root": str(workspace.root),
        "preserved_worktree": str(current_top),
        "message": f"Returned to main worktree {project_root}; preserved linked worktree {current_top}.",
    }


def _worktree_context(root: Path) -> dict[str, object]:
    top_result = run_readonly_git(root, ["rev-parse", "--show-toplevel"])
    if not top_result.ok:
        return {"ok": False, "message": combine_git_output(top_result) or "Active project is not a git repository."}
    current_top = Path(top_result.stdout.strip()).resolve()
    try:
        relative_root = root.resolve().relative_to(current_top)
    except ValueError:
        return {"ok": False, "message": f"Active project root is outside its git worktree: {root}"}

    common_result = run_readonly_git(root, ["rev-parse", "--path-format=absolute", "--git-common-dir"])
    if not common_result.ok:
        return {"ok": False, "message": combine_git_output(common_result) or "Could not resolve git common directory."}
    common_dir = Path(common_result.stdout.strip()).resolve()
    if common_dir.name != ".git":
        return {"ok": False, "message": f"Unsupported git common directory: {common_dir}"}
    main_top = common_dir.parent
    if not main_top.is_dir():
        return {"ok": False, "message": f"Git main worktree does not exist: {main_top}"}

    list_result = run_readonly_git(root, ["worktree", "list", "--porcelain"])
    if not list_result.ok:
        return {"ok": False, "message": combine_git_output(list_result) or "Could not list git worktrees."}
    return {
        "ok": True,
        "current_top": current_top,
        "main_top": main_top.resolve(),
        "relative_root": relative_root,
        "entries": _parse_worktree_entries(list_result.stdout),
        "message": "Read git worktree context.",
    }


def _parse_worktree_entries(output: str) -> list[dict[str, str]]:
    entries: list[dict[str, str]] = []
    current: dict[str, str] = {}
    for line in [*output.splitlines(), ""]:
        if not line:
            if current.get("path"):
                entries.append(current)
            current = {}
            continue
        key, _, value = line.partition(" ")
        if key == "worktree":
            current["path"] = str(Path(value).resolve())
        elif key == "branch":
            current["branch"] = value.removeprefix("refs/heads/")
        elif key == "HEAD":
            current["head"] = value
    return entries


def _resolve_existing_worktree_path(root: Path, value: str, entries: list[dict[str, str]]) -> Path | None:
    candidate = Path(value).expanduser()
    resolved = (root / candidate).resolve() if not candidate.is_absolute() else candidate.resolve()
    for entry in entries:
        entry_path = Path(entry["path"]).resolve()
        if resolved == entry_path:
            return entry_path
    return None


def _entry_branch(entries: list[dict[str, str]], path: Path) -> str:
    for entry in entries:
        if Path(entry["path"]).resolve() == path:
            return entry.get("branch", "")
    return ""


def _enter_failure(workspace: RunWorkspace, message: str) -> dict[str, object]:
    return {
        "ok": False,
        "path": "",
        "branch": "",
        "created": False,
        "previous_root": str(workspace.root),
        "message": message,
    }


def _exit_failure(workspace: RunWorkspace, message: str) -> dict[str, object]:
    return {
        "ok": False,
        "path": "",
        "previous_root": str(workspace.root),
        "preserved_worktree": "",
        "message": message,
    }
