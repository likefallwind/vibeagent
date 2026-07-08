import unittest

from vibeagent import checkpoint_actions
from vibeagent import checkpoint_query_actions


class CheckpointQueryActionsTests(unittest.TestCase):
    def test_checkpoint_actions_reexports_query_helpers(self) -> None:
        self.assertIs(
            checkpoint_actions.list_checkpoints_observation,
            checkpoint_query_actions.list_checkpoints_observation,
        )
        self.assertIs(
            checkpoint_actions.checkpoint_show_observation,
            checkpoint_query_actions.checkpoint_show_observation,
        )
        self.assertIs(
            checkpoint_actions.checkpoint_diff_observation,
            checkpoint_query_actions.checkpoint_diff_observation,
        )
        self.assertIs(
            checkpoint_actions.checkpoint_status_observation,
            checkpoint_query_actions.checkpoint_status_observation,
        )
        self.assertIs(
            checkpoint_actions.empty_checkpoint_status,
            checkpoint_query_actions.empty_checkpoint_status,
        )


if __name__ == "__main__":
    unittest.main()
