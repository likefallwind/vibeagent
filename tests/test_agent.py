import json
import tempfile
import unittest
from pathlib import Path

from vibeagent.agent import run_agent
from vibeagent.types import ChatMessage


class MockClient:
    def __init__(self, responses: list[str]) -> None:
        self.responses = responses
        self.index = 0

    def complete(self, _messages: list[ChatMessage]) -> str:
        response = self.responses[self.index]
        self.index += 1
        return response


class AgentTests(unittest.TestCase):
    def test_run_agent_repairs_a_failing_script_and_finishes(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-agent-") as base:
            client = MockClient(
                [
                    json.dumps(
                        {
                            "thought": "write an initial script",
                            "action": {
                                "type": "write_file",
                                "path": "sum.py",
                                "content": "print(total)",
                            },
                        }
                    ),
                    json.dumps(
                        {
                            "thought": "run it",
                            "action": {
                                "type": "run_command",
                                "command": "python3 sum.py",
                            },
                        }
                    ),
                    json.dumps(
                        {
                            "thought": "fix missing variable",
                            "action": {
                                "type": "write_file",
                                "path": "sum.py",
                                "content": "total = sum(range(1, 101))\nprint(total)\n",
                            },
                        }
                    ),
                    json.dumps(
                        {
                            "thought": "run fixed script",
                            "action": {
                                "type": "run_command",
                                "command": "python3 sum.py",
                            },
                        }
                    ),
                    json.dumps(
                        {
                            "thought": "done",
                            "action": {
                                "type": "finish",
                                "message": "Generated and ran sum.py successfully.",
                            },
                        }
                    ),
                ]
            )

            result = run_agent("sum 1 to 100", base_dir=Path(base), client=client, max_iterations=5)

        self.assertTrue(result.success)
        self.assertIn(".vibeagent/runs/", result.run_dir.as_posix())
        command_observations = [item for item in result.observations if item.kind == "run_command"]
        self.assertEqual(len(command_observations), 2)
        self.assertNotEqual(command_observations[0].result.exit_code, 0)
        self.assertEqual(command_observations[1].result.exit_code, 0)
        self.assertEqual(command_observations[1].result.stdout.strip(), "5050")


if __name__ == "__main__":
    unittest.main()
