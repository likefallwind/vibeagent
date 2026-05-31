import json
import tempfile
import unittest
from pathlib import Path

from vibeagent.actions import ActionParseError, parse_model_action, run_command


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


if __name__ == "__main__":
    unittest.main()
