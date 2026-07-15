from __future__ import annotations

import unittest
from types import SimpleNamespace

from vibeagent.prompt_observation_mcp import format_mcp_observation
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

    def test_format_mcp_call_includes_status_and_output(self) -> None:
        text = format_mcp_observation(
            3,
            SimpleNamespace(
                kind="mcp_call",
                server="docs",
                name="search",
                message="completed",
                ok=True,
                is_error=False,
                truncated=False,
                max_output_chars=4000,
                timeout_ms=2000,
                error="",
                output="result body",
            ),
        )

        self.assertEqual(
            text,
            (
                "3. mcp_call docs/search: completed\n"
                "ok: true isError=false truncated=false maxOutputChars=4000 timeoutMs=2000\n"
                "error: none\n"
                "output:\n"
                "result body"
            ),
        )


if __name__ == "__main__":
    unittest.main()
