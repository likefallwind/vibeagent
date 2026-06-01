import json
import tempfile
import unittest
from pathlib import Path

from vibeagent.actions import ActionParseError, execute_action, parse_model_action, run_command
from vibeagent.types import EditFileAction, ListFilesAction, ReadFileAction, RunCommandAction, SearchAction
from vibeagent.workspace import create_run_workspace, write_run_file


class ActionTests(unittest.TestCase):
    def test_parse_model_action_accepts_valid_write_file_json(self) -> None:
        parsed = parse_model_action(
            json.dumps(
                {
                    "thought": "create file",
                    "action": {
                        "type": "write_file",
                        "path": "sum.py",
                        "content": "print(5050)",
                    },
                }
            )
        )

        self.assertEqual(parsed.action.type, "write_file")
        self.assertEqual(parsed.action.path, "sum.py")

    def test_parse_model_action_accepts_project_actions(self) -> None:
        cases = [
            ({"type": "list_files", "path": "src"}, "list_files"),
            ({"type": "read_file", "path": "src/app.py"}, "read_file"),
            ({"type": "search", "query": "needle"}, "search"),
            ({"type": "edit_file", "path": "src/app.py", "old": "a", "new": "b"}, "edit_file"),
        ]

        for action, expected_type in cases:
            parsed = parse_model_action(json.dumps({"thought": "inspect", "action": action}))
            self.assertEqual(parsed.action.type, expected_type)

    def test_parse_model_action_accepts_first_json_object_when_model_returns_extra_actions(self) -> None:
        parsed = parse_model_action(
            "\n".join(
                [
                    json.dumps(
                        {
                            "thought": "create file",
                            "action": {"type": "write_file", "path": "sum.py", "content": "print(55)"},
                        }
                    ),
                    json.dumps(
                        {
                            "thought": "run it",
                            "action": {"type": "run_command", "command": "python sum.py"},
                        }
                    ),
                ]
            )
        )

        self.assertEqual(parsed.action.type, "write_file")
        self.assertEqual(parsed.action.path, "sum.py")

    def test_parse_model_action_rejects_invalid_json(self) -> None:
        with self.assertRaises(ActionParseError):
            parse_model_action("not json")

    def test_parse_model_action_rejects_unsupported_action(self) -> None:
        with self.assertRaisesRegex(ActionParseError, "Unsupported action type"):
            parse_model_action(json.dumps({"thought": "bad", "action": {"type": "delete_everything"}}))

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
