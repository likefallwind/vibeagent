import unittest

from vibeagent import action_types, action_union_types


class ActionUnionTypesTests(unittest.TestCase):
    def test_action_types_reexports_agent_action_union(self) -> None:
        self.assertIs(action_types.AgentAction, action_union_types.AgentAction)


if __name__ == "__main__":
    unittest.main()
