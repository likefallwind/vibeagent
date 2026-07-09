from __future__ import annotations

import unittest

from vibeagent.tool_definition_git import GIT_TOOL_DEFINITIONS
from vibeagent.tool_definition_git_review import GIT_REVIEW_TOOL_DEFINITIONS
from vibeagent.tool_definition_git_stash import GIT_STASH_TOOL_DEFINITIONS
from vibeagent.tool_definition_git_status import GIT_STATUS_TOOL_DEFINITIONS
from vibeagent.tool_definition_git_sync import GIT_SYNC_TOOL_DEFINITIONS
from vibeagent.tool_definition_git_worktree import GIT_WORKTREE_TOOL_DEFINITIONS


class GitToolDefinitionTests(unittest.TestCase):
    def test_git_tool_definitions_are_grouped_in_original_order(self) -> None:
        self.assertEqual(
            GIT_TOOL_DEFINITIONS,
            GIT_STATUS_TOOL_DEFINITIONS
            + GIT_SYNC_TOOL_DEFINITIONS
            + GIT_WORKTREE_TOOL_DEFINITIONS
            + GIT_STASH_TOOL_DEFINITIONS
            + GIT_REVIEW_TOOL_DEFINITIONS,
        )

    def test_git_definition_boundaries_match_git_domains(self) -> None:
        self.assertEqual(
            [tool["name"] for tool in GIT_STATUS_TOOL_DEFINITIONS],
            ["git_status", "git_conflicts", "git_info", "git_changes", "git_branches"],
        )
        self.assertEqual(
            [tool["name"] for tool in GIT_SYNC_TOOL_DEFINITIONS],
            ["check_git_fetch", "git_fetch", "check_git_pull", "git_pull", "check_git_push", "git_push"],
        )
        self.assertEqual(
            [tool["name"] for tool in GIT_WORKTREE_TOOL_DEFINITIONS],
            [
                "check_git_switch",
                "git_switch",
                "check_git_stage",
                "git_stage",
                "check_git_unstage",
                "git_unstage",
                "check_git_restore",
                "git_restore",
            ],
        )
        self.assertEqual(
            [tool["name"] for tool in GIT_STASH_TOOL_DEFINITIONS],
            [
                "git_stashes",
                "check_git_stash",
                "git_stash",
                "check_git_stash_apply",
                "git_stash_apply",
                "check_git_stash_drop",
                "git_stash_drop",
            ],
        )
        self.assertEqual(
            [tool["name"] for tool in GIT_REVIEW_TOOL_DEFINITIONS],
            [
                "check_git_commit",
                "git_commit",
                "review_changes",
                "final_review",
                "suggest_checks",
                "check_suggested_checks",
                "run_suggested_checks",
            ],
        )


if __name__ == "__main__":
    unittest.main()
