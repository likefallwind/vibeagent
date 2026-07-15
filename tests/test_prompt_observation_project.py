from __future__ import annotations

import unittest
from types import SimpleNamespace

from vibeagent.prompt_observation_project import _format_command_metadata


class PromptObservationProjectTests(unittest.TestCase):
    def test_format_command_metadata_keeps_common_field_order(self) -> None:
        command = SimpleNamespace(
            cwd=".",
            command="npm test",
            available=True,
            missing_tool=None,
            source="scripts.test",
            reason="unit tests",
        )

        self.assertEqual(
            _format_command_metadata("check", command, [("source", command.source), ("reason", command.reason)]),
            "check: cwd=. command=npm test available=true missingTool=. source=scripts.test reason=unit tests",
        )

    def test_format_command_metadata_preserves_pre_availability_fields(self) -> None:
        command = SimpleNamespace(
            cwd=".",
            command="python -m unittest tests.test_agent",
            available=False,
            missing_tool="python",
            test_path="tests/test_agent.py",
            source="vibeagent/agent.py",
            reason="related test",
        )

        self.assertEqual(
            _format_command_metadata(
                "command",
                command,
                [("source", command.source), ("reason", command.reason)],
                pre_availability_fields=[("test", command.test_path)],
            ),
            (
                "command: cwd=. command=python -m unittest tests.test_agent "
                "test=tests/test_agent.py available=false missingTool=python "
                "source=vibeagent/agent.py reason=related test"
            ),
        )


if __name__ == "__main__":
    unittest.main()
