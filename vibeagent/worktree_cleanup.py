from __future__ import annotations

from pathlib import Path

from .workspace_git_utils import run_git_mutation


def remove_created_worktree(
    main_top: str | Path,
    worktree_top: str | Path,
    branch: str,
) -> None:
    run_git_mutation(main_top, ["worktree", "unlock", str(worktree_top)])
    run_git_mutation(
        main_top,
        ["worktree", "remove", "--force", str(worktree_top)],
    )
    if branch:
        run_git_mutation(main_top, ["branch", "-D", branch])


__all__ = ["remove_created_worktree"]
