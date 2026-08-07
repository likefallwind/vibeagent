import unittest

from vibeagent import agent_hook_results, agent_hooks


class AgentHookResultsTests(unittest.TestCase):
    def test_agent_hooks_reexports_result_helpers(self) -> None:
        self.assertIs(agent_hooks.HookRunResult, agent_hook_results.HookRunResult)
        self.assertIs(agent_hooks.HookBatchResult, agent_hook_results.HookBatchResult)
        self.assertIs(agent_hooks.HookWrappedToolResult, agent_hook_results.HookWrappedToolResult)
        self.assertIs(agent_hooks._hook_command_with_context, agent_hook_results.hook_command_with_context)
        self.assertIs(agent_hooks._hook_result_from_observation, agent_hook_results.hook_result_from_observation)
        self.assertIs(agent_hooks._hook_failure_observation, agent_hook_results.hook_failure_observation)


if __name__ == "__main__":
    unittest.main()
