from __future__ import annotations

from typing import Any

from .tool_definition_git_review import GIT_REVIEW_TOOL_DEFINITIONS
from .tool_definition_git_stash import GIT_STASH_TOOL_DEFINITIONS
from .tool_definition_git_status import GIT_STATUS_TOOL_DEFINITIONS
from .tool_definition_git_sync import GIT_SYNC_TOOL_DEFINITIONS
from .tool_definition_git_worktree import GIT_WORKTREE_TOOL_DEFINITIONS


GIT_TOOL_DEFINITIONS: list[dict[str, Any]] = (
    GIT_STATUS_TOOL_DEFINITIONS
    + GIT_SYNC_TOOL_DEFINITIONS
    + GIT_WORKTREE_TOOL_DEFINITIONS
    + GIT_STASH_TOOL_DEFINITIONS
    + GIT_REVIEW_TOOL_DEFINITIONS
)
