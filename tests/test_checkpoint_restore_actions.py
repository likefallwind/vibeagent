import unittest

from vibeagent import checkpoint_actions
from vibeagent import checkpoint_restore_actions
from vibeagent import checkpoint_storage


class CheckpointRestoreActionsTests(unittest.TestCase):
    def test_checkpoint_actions_reexports_restore_helpers(self) -> None:
        self.assertIs(
            checkpoint_actions.check_checkpoint_restore_observation,
            checkpoint_restore_actions.check_checkpoint_restore_observation,
        )
        self.assertIs(
            checkpoint_actions.checkpoint_restore_observation,
            checkpoint_restore_actions.checkpoint_restore_observation,
        )
        self.assertIs(
            checkpoint_actions.empty_check_checkpoint_restore,
            checkpoint_restore_actions.empty_check_checkpoint_restore,
        )

    def test_checkpoint_actions_reexports_untracked_restore_helpers(self) -> None:
        self.assertIs(
            checkpoint_actions.checkpoint_untracked_files_match,
            checkpoint_storage.checkpoint_untracked_files_match,
        )
        self.assertIs(
            checkpoint_actions.read_checkpoint_git_head,
            checkpoint_storage.read_checkpoint_git_head,
        )
        self.assertIs(
            checkpoint_actions.restore_checkpoint_untracked_files,
            checkpoint_storage.restore_checkpoint_untracked_files,
        )
        self.assertIs(
            checkpoint_actions.save_checkpoint_untracked_files,
            checkpoint_storage.save_checkpoint_untracked_files,
        )


if __name__ == "__main__":
    unittest.main()
