import unittest
from types import SimpleNamespace

from vibeagent import prompt_observation_session
from vibeagent import prompt_observation_session_helpers as helpers


class PromptObservationSessionHelpersTests(unittest.TestCase):
    def test_session_module_reexports_helper_names_for_compatibility(self) -> None:
        names = [
            "format_completion_recovery_lines",
            "format_file_reference_lines",
            "format_selected_session_verification_command_lines",
            "format_subagent_failure_lines",
            "format_verification_command_lines",
        ]
        for name in names:
            with self.subTest(name=name):
                self.assertIs(getattr(prompt_observation_session, name), getattr(helpers, name))

    def test_format_file_reference_lines_filters_blank_paths_and_includes_uses(self) -> None:
        lines = helpers.format_file_reference_lines(
            [
                {"path": "app.py", "uses": ["read", "", "edit"]},
                {"path": "   ", "uses": ["ignored"]},
            ],
            file_count=2,
            shown_file_count=1,
            files_truncated=True,
        )

        self.assertEqual(
            lines,
            [
                "files: 1/2 truncated=true",
                "file: app.py uses=read,edit",
            ],
        )

    def test_format_completion_recovery_lines_includes_detail_fields(self) -> None:
        observation = SimpleNamespace(
            completion_ready=False,
            completion_blockers=["tests missing"],
            latest_completion_blockers=["working tree dirty"],
            latest_completion_failed_verification_checks=["npm test"],
        )

        lines = helpers.format_completion_recovery_lines(observation)

        self.assertIn("completionReady: false", lines)
        self.assertIn("completionBlocker: tests missing", lines)
        self.assertIn("latestCompletionBlocker: working tree dirty", lines)
        self.assertIn("latestCompletionFailedCheck: npm test", lines)


if __name__ == "__main__":
    unittest.main()
