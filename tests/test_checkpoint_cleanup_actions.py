import unittest

from vibeagent import checkpoint_actions
from vibeagent import checkpoint_cleanup_actions


class CheckpointCleanupActionsTests(unittest.TestCase):
    def test_checkpoint_actions_reexports_cleanup_helpers(self) -> None:
        self.assertIs(
            checkpoint_actions.check_checkpoint_delete_observation,
            checkpoint_cleanup_actions.check_checkpoint_delete_observation,
        )
        self.assertIs(
            checkpoint_actions.checkpoint_delete_observation,
            checkpoint_cleanup_actions.checkpoint_delete_observation,
        )
        self.assertIs(
            checkpoint_actions.check_checkpoint_prune_observation,
            checkpoint_cleanup_actions.check_checkpoint_prune_observation,
        )
        self.assertIs(
            checkpoint_actions.checkpoint_prune_observation,
            checkpoint_cleanup_actions.checkpoint_prune_observation,
        )


if __name__ == "__main__":
    unittest.main()
