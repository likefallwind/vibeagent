import unittest

from vibeagent import agent_status_types, types


class AgentStatusTypesTests(unittest.TestCase):
    def test_types_reexports_agent_status_contract(self) -> None:
        self.assertIs(types.AgentStatus, agent_status_types.AgentStatus)
        self.assertIs(types.AgentLogger, agent_status_types.AgentLogger)


if __name__ == "__main__":
    unittest.main()
