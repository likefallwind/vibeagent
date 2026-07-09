import tempfile
import unittest
from pathlib import Path

from vibeagent import project_context_commands, project_focused_test_commands


class ProjectFocusedTestCommandsTests(unittest.TestCase):
    def test_project_context_commands_reexports_focused_test_helpers(self) -> None:
        self.assertIs(project_context_commands.get_related_tests_text, project_focused_test_commands.get_related_tests_text)
        self.assertIs(project_context_commands.get_related_tests_report, project_focused_test_commands.get_related_tests_report)
        self.assertIs(project_context_commands.get_focused_test_commands_text, project_focused_test_commands.get_focused_test_commands_text)
        self.assertIs(project_context_commands.get_focused_test_commands_report, project_focused_test_commands.get_focused_test_commands_report)
        self.assertIs(project_context_commands.get_check_focused_test_commands_text, project_focused_test_commands.get_check_focused_test_commands_text)
        self.assertIs(project_context_commands.get_check_focused_test_commands_report, project_focused_test_commands.get_check_focused_test_commands_report)
        self.assertIs(project_context_commands.get_run_focused_test_commands_text, project_focused_test_commands.get_run_focused_test_commands_text)
        self.assertIs(project_context_commands.get_run_focused_test_commands_report, project_focused_test_commands.get_run_focused_test_commands_report)
        self.assertIs(project_context_commands.parse_related_tests_argument, project_focused_test_commands.parse_related_tests_argument)

    def test_parse_related_tests_argument_rejects_options(self) -> None:
        self.assertIsNone(project_focused_test_commands.parse_related_tests_argument(None))
        self.assertIsNone(project_focused_test_commands.parse_related_tests_argument(""))
        self.assertEqual(
            project_focused_test_commands.parse_related_tests_argument("pkg/actions.py tests/test_actions.py"),
            ["pkg/actions.py", "tests/test_actions.py"],
        )
        with self.assertRaisesRegex(ValueError, "options are not supported"):
            project_focused_test_commands.parse_related_tests_argument("--bad")

    def test_related_and_focused_reports_find_candidate_test(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-project-focused-tests-") as tmp:
            root = Path(tmp)
            (root / "pkg").mkdir()
            (root / "tests").mkdir()
            (root / "pkg" / "actions.py").write_text("def run():\n    return 1\n", encoding="utf-8")
            (root / "tests" / "test_actions.py").write_text("def test_run():\n    assert True\n", encoding="utf-8")

            related = project_focused_test_commands.get_related_tests_report(root, "pkg/actions.py")
            focused = project_focused_test_commands.get_focused_test_commands_report(root, "pkg/actions.py")

        self.assertTrue(related["ok"])
        self.assertEqual(related["targetPaths"], ["pkg/actions.py"])
        self.assertEqual(related["candidates"]["items"][0]["test"], "tests/test_actions.py")
        self.assertTrue(focused["ok"])
        self.assertEqual(focused["targetPaths"], ["pkg/actions.py"])
        self.assertEqual(focused["commands"]["items"][0]["test"], "tests/test_actions.py")


if __name__ == "__main__":
    unittest.main()
