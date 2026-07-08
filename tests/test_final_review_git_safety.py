import tempfile
import unittest
from pathlib import Path

from vibeagent import final_review_actions
from vibeagent import final_review_git_safety


class FinalReviewGitSafetyTests(unittest.TestCase):
    def test_final_review_actions_reexports_git_safety_helpers(self) -> None:
        self.assertIs(final_review_actions.find_nested_git_repositories, final_review_git_safety.find_nested_git_repositories)
        self.assertIs(final_review_actions.find_changed_gitlinks, final_review_git_safety.find_changed_gitlinks)
        self.assertIs(final_review_actions.find_hidden_tracked_git_changes, final_review_git_safety.find_hidden_tracked_git_changes)
        self.assertIs(final_review_actions.find_unsafe_changed_symlinks, final_review_git_safety.find_unsafe_changed_symlinks)
        self.assertIs(final_review_actions.read_git_operation_state, final_review_git_safety.read_git_operation_state)

    def test_raw_diff_parsers_identify_gitlinks_and_symlinks(self) -> None:
        self.assertEqual(
            final_review_git_safety.gitlink_path_from_raw_diff_line(":100644 160000 abc def A\tvendor/lib"),
            "vendor/lib",
        )
        self.assertEqual(
            final_review_git_safety.symlink_path_from_raw_diff_line(":000000 120000 000 abc A\tleak.txt"),
            "leak.txt",
        )
        self.assertIsNone(final_review_git_safety.gitlink_path_from_raw_diff_line(":100644 100644 abc def M\tapp.py"))
        self.assertIsNone(final_review_git_safety.symlink_path_from_raw_diff_line(":100644 100644 abc def M\tapp.py"))

    def test_changed_symlink_target_risk_classifies_unsafe_targets(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-review-") as base:
            root = Path(base)
            (root / ".git").mkdir()
            (root / ".codex").mkdir()
            link_path = root / "link.txt"

            self.assertEqual(
                final_review_git_safety.changed_symlink_target_risk(root, link_path, "../outside.txt"),
                "points outside project",
            )
            self.assertEqual(
                final_review_git_safety.changed_symlink_target_risk(root, link_path, ".git/config"),
                "points into protected project path",
            )
            self.assertEqual(
                final_review_git_safety.changed_symlink_target_risk(root, link_path, ".codex/private.txt"),
                "points into ignored project path",
            )
            self.assertIsNone(final_review_git_safety.changed_symlink_target_risk(root, link_path, "src/app.py"))


if __name__ == "__main__":
    unittest.main()
