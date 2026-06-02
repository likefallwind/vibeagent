import tempfile
import unittest
from pathlib import Path

from vibeagent.actions import ActionParseError, execute_action, parse_tool_action, run_command
from vibeagent.types import EditFileAction, ListFilesAction, ReadFileAction, RunCommandAction, SearchAction
from vibeagent.workspace import create_run_workspace, write_run_file


class ActionTests(unittest.TestCase):
    def test_parse_tool_action_accepts_project_actions(self) -> None:
        cases = [
            ("list_files", {"path": "src"}, "list_files"),
            ("read_file", {"path": "src/app.py"}, "read_file"),
            ("search", {"query": "needle"}, "search"),
            ("edit_file", {"path": "src/app.py", "old": "a", "new": "b"}, "edit_file"),
        ]

        for name, tool_input, expected_type in cases:
            parsed = parse_tool_action(name, tool_input)
            self.assertEqual(parsed.type, expected_type)

    def test_parse_tool_action_rejects_unsupported_action(self) -> None:
        with self.assertRaisesRegex(ActionParseError, "Unsupported action type"):
            parse_tool_action("delete_everything", {})

    def test_parse_tool_action_validates_tool_inputs(self) -> None:
        action = parse_tool_action("write_file", {"path": "app.py", "content": "print('ok')\n"})

        self.assertEqual(action.type, "write_file")
        self.assertEqual(action.path, "app.py")

        with self.assertRaisesRegex(ActionParseError, "read_file action requires a string path"):
            parse_tool_action("read_file", {})

        with self.assertRaisesRegex(ActionParseError, "tool input must be an object"):
            parse_tool_action("read_file", "bad")

    def test_run_command_captures_stdout_stderr_exit_code_and_success(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-command-") as cwd:
            result = run_command(
                Path(cwd),
                "python3 -c \"import sys; print('out'); print('err', file=sys.stderr)\"",
            )

        self.assertEqual(result.exit_code, 0)
        self.assertEqual(result.stdout.strip(), "out")
        self.assertEqual(result.stderr.strip(), "err")
        self.assertFalse(result.timed_out)

    def test_run_command_reports_timeout(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-timeout-") as cwd:
            result = run_command(Path(cwd), "python3 -c \"import time; time.sleep(1)\"", 50)

        self.assertTrue(result.timed_out)
        self.assertIsNotNone(result.signal)

    def test_execute_project_actions_inside_workspace(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-actions-") as base:
            workspace = create_run_workspace(base, "test-run")
            write_run_file(workspace, "app.py", "value = 'old'\nprint(value)\n")

            listed = execute_action(workspace, ListFilesAction(type="list_files"))
            read = execute_action(workspace, ReadFileAction(type="read_file", path="app.py"))
            searched = execute_action(workspace, SearchAction(type="search", query="print"))
            edited = execute_action(workspace, EditFileAction(type="edit_file", path="app.py", old="old", new="new"))

            self.assertEqual(listed.kind, "list_files")
            self.assertEqual(read.kind, "read_file")
            self.assertEqual(searched.kind, "search")
            self.assertEqual(edited.kind, "edit_file")
            self.assertEqual(Path(base, "app.py").read_text(encoding="utf-8"), "value = 'new'\nprint(value)\n")

    def test_execute_project_action_errors_are_observations(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-actions-") as base:
            workspace = create_run_workspace(base, "test-run")

            read = execute_action(workspace, ReadFileAction(type="read_file", path="missing.py"))
            edit = execute_action(workspace, EditFileAction(type="edit_file", path="missing.py", old="a", new="b"))

            self.assertEqual(read.kind, "read_file")
            self.assertIn("File does not exist", read.message)
            self.assertEqual(edit.kind, "edit_file")
            self.assertFalse(edit.ok)
            self.assertIn("File does not exist", edit.message)

    def test_execute_action_blocks_high_risk_commands(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-actions-") as base:
            workspace = create_run_workspace(base, "test-run")

            observation = execute_action(workspace, RunCommandAction(type="run_command", command="sudo reboot"))

            self.assertEqual(observation.kind, "run_command")
            self.assertIsNone(observation.result.exit_code)
            self.assertIn("Command blocked", observation.result.stderr)


if __name__ == "__main__":
    unittest.main()
