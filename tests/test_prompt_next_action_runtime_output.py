import unittest
from types import SimpleNamespace

from vibeagent.prompt_next_action_runtime_output import (
    command_output_rerun_target,
    not_run_batch_command_labels,
    not_run_detail,
)


class PromptNextActionRuntimeOutputTests(unittest.TestCase):
    def test_command_output_rerun_target_prefers_previous_batch_kind(self) -> None:
        observations = [
            SimpleNamespace(
                kind="run_focused_test_commands",
                results=[
                    SimpleNamespace(
                        command="python -m unittest tests.test_one",
                        exit_code=1,
                        timed_out=False,
                        cwd=".",
                    )
                ],
            ),
            SimpleNamespace(kind="output_diagnostics"),
        ]

        self.assertEqual(command_output_rerun_target(observations[:-1]), "run_focused_test_commands")

    def test_not_run_batch_command_labels_include_available_metadata(self) -> None:
        observation = SimpleNamespace(
            kind="run_focused_test_commands",
            focused_commands=[
                SimpleNamespace(
                    command="python -m unittest tests.test_one",
                    cwd=".",
                    source="focused",
                    reason="related",
                    available=True,
                    missing_tool=None,
                ),
                SimpleNamespace(
                    command="npm test",
                    cwd="web",
                    source="package.json",
                    reason="script",
                    available=False,
                    missing_tool="npm",
                ),
            ],
        )

        labels = not_run_batch_command_labels(observation, ran_count=1)

        self.assertEqual(
            labels,
            ["npm test (cwd=web, source=package.json, available=false, missingTool=npm, reason=script)"],
        )
        self.assertIn("Not-yet-run selected check(s): npm test", not_run_detail(labels))


if __name__ == "__main__":
    unittest.main()
