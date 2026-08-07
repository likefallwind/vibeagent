import unittest

from vibeagent import project_focused_test_commands
from vibeagent import project_focused_test_validation as validation


class ProjectFocusedTestValidationTests(unittest.TestCase):
    def test_command_module_reexports_argument_parser_for_compatibility(self) -> None:
        self.assertIs(project_focused_test_commands.parse_related_tests_argument, validation.parse_related_tests_argument)

    def test_parse_related_tests_argument_handles_shell_quoting_and_rejects_options(self) -> None:
        self.assertIsNone(validation.parse_related_tests_argument(None))
        self.assertIsNone(validation.parse_related_tests_argument("  "))
        self.assertEqual(
            validation.parse_related_tests_argument("'src/app module.py' tests/test_app.py"),
            ["src/app module.py", "tests/test_app.py"],
        )
        with self.assertRaisesRegex(ValueError, "options are not supported"):
            validation.parse_related_tests_argument("--bad")

    def test_validate_run_focused_test_options_reports_limit_errors(self) -> None:
        usage = "Usage: /run-focused-tests [path...]"
        self.assertEqual(
            validation.validate_run_focused_test_options(
                usage=usage,
                timeout_ms=99,
                max_output_chars=12_000,
                context_lines=5,
                max_diagnostics=50,
                max_contexts=20,
                max_bytes_per_context=20_000,
            ),
            "Usage: /run-focused-tests [path...]\nError: timeout_ms must be at least 100.",
        )
        self.assertIsNone(
            validation.validate_run_focused_test_options(
                usage=usage,
                timeout_ms=30_000,
                max_output_chars=12_000,
                context_lines=5,
                max_diagnostics=50,
                max_contexts=20,
                max_bytes_per_context=20_000,
            )
        )


if __name__ == "__main__":
    unittest.main()
