from __future__ import annotations

import unittest
from types import SimpleNamespace

from vibeagent import prompt_next_action_project, prompt_next_action_project_tests


class PromptNextActionProjectTestsModuleTests(unittest.TestCase):
    def test_project_module_reexports_test_instruction_helpers(self) -> None:
        self.assertIs(
            prompt_next_action_project._related_tests_next_action_instruction,
            prompt_next_action_project_tests._related_tests_next_action_instruction,
        )
        self.assertIs(
            prompt_next_action_project._focused_test_commands_next_action_instruction,
            prompt_next_action_project_tests._focused_test_commands_next_action_instruction,
        )
        self.assertIs(
            prompt_next_action_project._check_focused_test_commands_next_action_instruction,
            prompt_next_action_project_tests._check_focused_test_commands_next_action_instruction,
        )

    def test_project_next_action_routes_test_observations(self) -> None:
        base = "Next:"
        related = prompt_next_action_project.project_next_action_instruction(
            base,
            SimpleNamespace(kind="related_tests", ok=True, total=2),
        )
        focused = prompt_next_action_project.project_next_action_instruction(
            base,
            SimpleNamespace(
                kind="focused_test_commands",
                ok=True,
                total=1,
                commands=[SimpleNamespace(command="python -m unittest", cwd=".")],
            ),
        )
        dry_run = prompt_next_action_project.project_next_action_instruction(
            base,
            SimpleNamespace(
                kind="check_focused_test_commands",
                ok=True,
                focused_commands=[SimpleNamespace(command="python -m unittest", cwd=".")],
            ),
        )

        self.assertIn("focused_test_commands", related)
        self.assertIn("run_focused_test_commands", focused)
        self.assertIn("run_focused_test_commands", dry_run)


if __name__ == "__main__":
    unittest.main()
