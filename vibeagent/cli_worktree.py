from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
from uuid import uuid4

from .config import SECRET_PROJECT_CONFIG_KEYS, project_config_path, read_project_config
from .workspace_core import RunWorkspace
from .workspace_git_utils import run_readonly_git
from .workspace_git_worktree_ops import enter_git_worktree
from .worktree_cleanup import remove_created_worktree
from .worktree_include import copy_worktree_includes
from .worktree_hooks import WorktreeHookContext, run_worktree_create_hook


@dataclass(frozen=True)
class CliWorktree:
    source_root: Path
    root: Path
    branch: str
    name: str


def create_cli_worktree(
    project_root: str | Path,
    name: str | None = None,
    *,
    hook_context: WorktreeHookContext | None = None,
) -> CliWorktree:
    source_root = Path(project_root).expanduser().resolve()
    if not source_root.is_dir():
        raise ValueError(f"Project directory not found: {project_root}")
    safe_config = _read_safe_project_config(source_root)
    workspace = RunWorkspace(
        root=source_root,
        run_id="cli-worktree",
        session_dir=source_root / ".vibeagent" / "sessions" / "cli-worktree",
    )
    selected_name = name or f"agent-{uuid4().hex[:10]}"
    hooked = run_worktree_create_hook(workspace, selected_name, hook_context)
    if hooked.configured:
        if hooked.error is not None or hooked.path is None:
            raise ValueError(hooked.error or "WorktreeCreate hook failed.")
        result = {
            "ok": True,
            "path": str(hooked.path),
            "branch": f"hook/{selected_name}",
        }
    else:
        result = enter_git_worktree(workspace, name=selected_name)
    if not result["ok"]:
        raise ValueError(str(result["message"]))
    root = Path(str(result["path"])).resolve()
    try:
        if not hooked.configured:
            copy_worktree_includes(source_root, root)
        _write_safe_project_config(root, safe_config)
    except (OSError, ValueError) as error:
        if not hooked.configured and bool(result.get("created")):
            _remove_failed_cli_worktree(source_root, root, str(result["branch"]))
        raise ValueError(
            f"Created worktree {root}, but could not finish its setup: {error}"
        ) from error
    resolved_name = str(result["branch"]).split("/", 1)[-1]
    return CliWorktree(
        source_root=source_root,
        root=root,
        branch=str(result["branch"]),
        name=resolved_name,
    )


def _read_safe_project_config(source_root: Path) -> dict[str, object]:
    source = project_config_path(source_root)
    if not source.is_file():
        return {}
    try:
        return {
            key: value
            for key, value in read_project_config(source_root).items()
            if key not in SECRET_PROJECT_CONFIG_KEYS
        }
    except OSError as error:
        raise ValueError(f"Could not read .vibeagent/config.json: {error}") from error


def _write_safe_project_config(target_root: Path, config: dict[str, object]) -> None:
    if not config:
        return
    target = project_config_path(target_root)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(config, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _remove_failed_cli_worktree(
    source_root: Path,
    target_root: Path,
    branch: str,
) -> None:
    top = run_readonly_git(target_root, ["rev-parse", "--show-toplevel"])
    if not top.ok or not top.stdout.strip():
        return
    remove_created_worktree(source_root, Path(top.stdout.strip()), branch)
