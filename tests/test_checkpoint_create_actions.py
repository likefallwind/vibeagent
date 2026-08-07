import unittest

from vibeagent import checkpoint_actions
from vibeagent import checkpoint_create_actions


class CheckpointCreateActionsTests(unittest.TestCase):
    def test_checkpoint_actions_reexports_create_helper(self) -> None:
        self.assertIs(
            checkpoint_actions.create_checkpoint_observation,
            checkpoint_create_actions.create_checkpoint_observation,
        )


if __name__ == "__main__":
    unittest.main()
