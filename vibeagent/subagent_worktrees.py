from __future__ import annotations

from dataclasses import dataclass, replace
from pathlib import Path
from uuid import uuid4

from .subagent_transcripts import SubagentWorktreeRecord
from .workspace_core import RunWorkspace
from .workspace_git_utils import combine_git_output, run_git_mutation, run_readonly_git
from .workspace_git_worktree_ops import enter_git_worktree
from .worktree_hooks import WorktreeHookContext, run_worktree_create_hook, run_worktree_remove_hooks
from .worktree_cleanup import remove_created_worktree


class SubagentWorktreeError(ValueError):
    pass


@dataclass(frozen=True)
class SubagentWorktreeRuntime:
    workspace: RunWorkspace
    record: SubagentWorktreeRecord


@dataclass(frozen=True)
class SubagentWorktreeOutcome:
    path: str
    branch: str
    preserved: bool
    message: str


def prepare_subagent_worktree(
    workspace: RunWorkspace,
    subagent_id: str,
    prior: SubagentWorktreeRecord | None = None,
    hook_context: WorktreeHookContext | None = None,
) -> SubagentWorktreeRuntime:
    if prior is not None and prior.provider == "hook":
        project_path = Path(prior.project_path)
        if project_path.is_symlink() or not project_path.is_dir():
            raise SubagentWorktreeError("Stored hook-created worktree is missing or unsafe.")
        return SubagentWorktreeRuntime(replace(workspace, root=project_path.resolve()), prior)
    worktree_name = _worktree_name()
    if prior is None:
        hooked = run_worktree_create_hook(workspace, worktree_name, hook_context)
        if hooked.configured:
            if hooked.error is not None or hooked.path is None:
                raise SubagentWorktreeError(hooked.error or "WorktreeCreate hook failed.")
            record = SubagentWorktreeRecord(
                project_path=str(hooked.path), worktree_path=str(hooked.path),
                branch=f"hook/{worktree_name}", base_commit="hook", provider="hook",
            )
            return SubagentWorktreeRuntime(replace(workspace, root=hooked.path), record)
    main_top, storage_root = _storage_context(workspace)
    entered: dict[str, object]
    if prior is not None and Path(prior.worktree_path).is_dir():
        worktree_top = _validated_stored_worktree(prior, storage_root)
        entered = enter_git_worktree(workspace, path=str(worktree_top))
        if not entered["ok"]:
            raise SubagentWorktreeError(str(entered["message"]))
        if entered["branch"] != prior.branch:
            raise SubagentWorktreeError("Stored subagent worktree is checked out on a different branch.")
        if Path(str(entered["path"])).resolve() != Path(prior.project_path).resolve():
            raise SubagentWorktreeError("Stored subagent worktree project path no longer matches this checkout.")
        record = prior
        created = False
    else:
        base = run_readonly_git(workspace.root, ["rev-parse", "HEAD"])
        if not base.ok or not base.stdout.strip():
            raise SubagentWorktreeError(combine_git_output(base) or "Could not resolve the worktree base commit.")
        entered = enter_git_worktree(workspace, name=worktree_name)
        if not entered["ok"]:
            raise SubagentWorktreeError(str(entered["message"]))
        project_path = Path(str(entered["path"])).resolve()
        top = run_readonly_git(project_path, ["rev-parse", "--show-toplevel"])
        if not top.ok or not top.stdout.strip():
            _remove_created_worktree(main_top, storage_root / worktree_name, str(entered["branch"]))
            raise SubagentWorktreeError(combine_git_output(top) or "Could not resolve the created worktree path.")
        worktree_top = Path(top.stdout.strip()).resolve()
        if not worktree_top.is_relative_to(storage_root):
            _remove_created_worktree(main_top, worktree_top, str(entered["branch"]))
            raise SubagentWorktreeError("Created subagent worktree is outside managed worktree storage.")
        record = SubagentWorktreeRecord(
            project_path=str(project_path),
            worktree_path=str(worktree_top),
            branch=str(entered["branch"]),
            base_commit=base.stdout.strip(),
            preserved=True,
        )
        created = True

    lock = run_git_mutation(
        main_top,
        ["worktree", "lock", "--reason", f"vibeagent subagent {subagent_id}", record.worktree_path],
    )
    if not lock.ok:
        if created:
            _remove_created_worktree(main_top, Path(record.worktree_path), record.branch)
        raise SubagentWorktreeError(combine_git_output(lock) or "Could not lock the subagent worktree.")
    return SubagentWorktreeRuntime(
        workspace=replace(workspace, root=Path(record.project_path).resolve()),
        record=record,
    )


def finalize_subagent_worktree(
    parent_workspace: RunWorkspace,
    runtime: SubagentWorktreeRuntime,
    hook_context: WorktreeHookContext | None = None,
) -> SubagentWorktreeOutcome:
    record = runtime.record
    if record.provider == "hook":
        results = run_worktree_remove_hooks(
            parent_workspace, record.worktree_path, hook_context
        )
        failed = [result.message for result in results if not result.ok]
        if failed:
            return _preserved(record, f"WorktreeRemove hook failed: {'; '.join(failed)}")
        return SubagentWorktreeOutcome(
            record.project_path, record.branch, Path(record.worktree_path).exists(),
            "WorktreeRemove hooks completed.",
        )
    try:
        main_top, storage_root = _storage_context(parent_workspace)
    except SubagentWorktreeError as error:
        return _preserved(record, f"{error} The subagent worktree was preserved.")
    worktree_top = Path(record.worktree_path).resolve()
    unlock = run_git_mutation(main_top, ["worktree", "unlock", str(worktree_top)])
    if not unlock.ok:
        return _preserved(record, combine_git_output(unlock) or "Could not unlock the subagent worktree.")
    if not worktree_top.is_relative_to(storage_root):
        return _preserved(record, "Subagent worktree moved outside managed storage; it was preserved.")
    status = run_readonly_git(worktree_top, ["status", "--porcelain", "--untracked-files=all"])
    head = run_readonly_git(worktree_top, ["rev-parse", "HEAD"])
    if not status.ok or not head.ok:
        detail = combine_git_output(status) or combine_git_output(head) or "Could not inspect the subagent worktree."
        return _preserved(record, f"{detail} The worktree was preserved.")
    if status.stdout.strip() or head.stdout.strip() != record.base_commit:
        return _preserved(record, "Subagent worktree contains changes or commits and was preserved.")
    removed = run_git_mutation(main_top, ["worktree", "remove", "--force", str(worktree_top)])
    if not removed.ok:
        return _preserved(record, f"{combine_git_output(removed) or 'Could not remove the clean worktree.'} It was preserved.")
    branch = run_git_mutation(main_top, ["branch", "-D", record.branch])
    detail = "" if branch.ok else f" Branch cleanup warning: {combine_git_output(branch)}"
    return SubagentWorktreeOutcome(
        path=record.project_path,
        branch=record.branch,
        preserved=False,
        message=f"Clean subagent worktree was removed.{detail}".strip(),
    )


def _storage_context(workspace: RunWorkspace) -> tuple[Path, Path]:
    common = run_readonly_git(workspace.root, ["rev-parse", "--path-format=absolute", "--git-common-dir"])
    if not common.ok or not common.stdout.strip():
        detail = combine_git_output(common)
        suffix = f" {detail}" if detail else ""
        raise SubagentWorktreeError(f"Subagent worktree isolation requires a git repository.{suffix}")
    common_dir = Path(common.stdout.strip()).resolve()
    if common_dir.name != ".git":
        raise SubagentWorktreeError(f"Unsupported git common directory: {common_dir}")
    main_top = common_dir.parent
    runtime_root = main_top / ".vibeagent"
    raw_storage_root = runtime_root / "worktrees"
    if runtime_root.is_symlink() or raw_storage_root.is_symlink():
        raise SubagentWorktreeError(f"Subagent worktree storage must not be a symbolic link: {raw_storage_root}")
    storage_root = raw_storage_root.resolve()
    return main_top, storage_root


def _validated_stored_worktree(record: SubagentWorktreeRecord, storage_root: Path) -> Path:
    worktree_top = Path(record.worktree_path)
    project_path = Path(record.project_path)
    if worktree_top.is_symlink() or project_path.is_symlink():
        raise SubagentWorktreeError("Stored subagent worktree paths must not be symbolic links.")
    resolved = worktree_top.resolve()
    if resolved.parent != storage_root:
        raise SubagentWorktreeError("Stored subagent worktree is outside managed worktree storage.")
    if record.branch != f"vibeagent/{resolved.name}" or not resolved.name.startswith("subagent-"):
        raise SubagentWorktreeError("Stored subagent worktree branch does not match its managed path.")
    if not project_path.resolve().is_relative_to(resolved):
        raise SubagentWorktreeError("Stored subagent project path is outside its worktree.")
    return resolved


def _worktree_name() -> str:
    return f"subagent-{uuid4().hex[:20]}"


def _remove_created_worktree(main_top: Path, path: Path, branch: str) -> None:
    remove_created_worktree(main_top, path, branch)


def _preserved(record: SubagentWorktreeRecord, message: str) -> SubagentWorktreeOutcome:
    return SubagentWorktreeOutcome(record.project_path, record.branch, True, message)


__all__ = [
    "SubagentWorktreeError",
    "SubagentWorktreeOutcome",
    "SubagentWorktreeRuntime",
    "finalize_subagent_worktree",
    "prepare_subagent_worktree",
]
