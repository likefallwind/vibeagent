from __future__ import annotations

import unittest
from types import SimpleNamespace

from vibeagent.prompt_next_action_project import (
    _available_command_labels,
    _blocked_check_labels,
    _command_labels,
    _project_overview_next_action_instruction,
)


class PromptNextActionProjectTests(unittest.TestCase):
    def test_command_labels_default_cwd_and_skip_empty_commands(self) -> None:
        labels = _command_labels(
            [
                SimpleNamespace(command=" npm test ", cwd=""),
                SimpleNamespace(command="", cwd="."),
                SimpleNamespace(command="python -m unittest", cwd=" tests "),
            ]
        )

        self.assertEqual(labels, ["npm test (cwd=.)", "python -m unittest (cwd=tests)"])

    def test_available_command_labels_skip_unavailable_commands(self) -> None:
        labels = _available_command_labels(
            [
                SimpleNamespace(command="npm test", cwd=".", available=True),
                SimpleNamespace(command="npm run build", cwd="web", available=False),
                SimpleNamespace(command="python -m unittest", cwd=None),
            ]
        )

        self.assertEqual(labels, ["npm test (cwd=.)", "python -m unittest (cwd=.)"])

    def test_blocked_check_labels_use_reason_priority_and_skip_ok_checks(self) -> None:
        labels = _blocked_check_labels(
            [
                SimpleNamespace(ok=True, command="npm test", block_reason="ignored", missing_tool="", message=""),
                SimpleNamespace(ok=False, command="code .", block_reason="GUI launch blocked", missing_tool="code", message="blocked"),
                SimpleNamespace(ok=False, command="pytest", block_reason="", missing_tool="pytest", message="Missing pytest"),
                SimpleNamespace(ok=False, command="", block_reason="", missing_tool="", message="command invalid"),
            ]
        )

        self.assertEqual(labels, ["code .: GUI launch blocked", "pytest: pytest", "command invalid"])

    def test_project_overview_instruction_guides_available_skills(self) -> None:
        instruction = _project_overview_next_action_instruction(
            "Next.",
            SimpleNamespace(
                ok=True,
                commands=[],
                suggested_checks=[],
                instruction_sources=[],
                todos=[],
                git_status="",
                skills=[
                    SimpleNamespace(name="release-checklist", available=True),
                    SimpleNamespace(name="draft-helper", available=False),
                ],
            ),
        )

        self.assertIn("Project skills are available", instruction)
        self.assertIn("release-checklist", instruction)
        self.assertIn("project_skills", instruction)
        self.assertIn("skill", instruction)
        self.assertNotIn("draft-helper", instruction)


if __name__ == "__main__":
    unittest.main()
