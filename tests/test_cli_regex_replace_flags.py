import io
import json
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import patch

from vibeagent.cli import main


class CliRegexReplaceFlagTests(unittest.TestCase):
    def test_main_runs_regex_replace_local_flags_without_creating_client(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
            stdout = io.StringIO()

            with (
                patch("vibeagent.cli.create_chat_client") as create_chat_client,
                patch("vibeagent.cli.get_check_regex_replace_text", return_value="Check regex replace:\n  ok: yes") as get_check_regex_replace_text,
                redirect_stdout(stdout),
            ):
                exit_code = main(
                    [
                        "--cwd",
                        base,
                        "--check-regex-replace",
                        "app.py",
                        "old",
                        "new\\n",
                        "--regex-count",
                        "1",
                        "--regex-ignore-case",
                        "--regex-multiline",
                        "--regex-max-replacements",
                        "5",
                    ]
                )

        self.assertEqual(exit_code, 0)
        self.assertIn("Check regex replace:", stdout.getvalue())
        get_check_regex_replace_text.assert_called_once_with(
            Path(base).resolve(),
            path="app.py",
            pattern="old",
            replacement="new\\n",
            count=1,
            case_sensitive=False,
            multiline=True,
            max_replacements=5,
        )
        create_chat_client.assert_not_called()

        with tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
            stdout = io.StringIO()
            with (
                patch("vibeagent.cli.create_chat_client") as create_chat_client,
                patch("vibeagent.cli.get_regex_replace_text", return_value="Regex replace:\n  ok: yes") as get_regex_replace_text,
                redirect_stdout(stdout),
            ):
                exit_code = main(["--cwd", base, "--regex-replace", "app.py", "old", "new"])

        self.assertEqual(exit_code, 0)
        self.assertIn("Regex replace:", stdout.getvalue())
        get_regex_replace_text.assert_called_once_with(
            Path(base).resolve(),
            path="app.py",
            pattern="old",
            replacement="new",
            count=0,
            case_sensitive=True,
            multiline=False,
            max_replacements=100,
        )
        create_chat_client.assert_not_called()

        cases = [
            (
                [
                    "--check-regex-replace",
                    "app.py",
                    "old",
                    "new\\n",
                    "--regex-count",
                    "1",
                    "--regex-ignore-case",
                    "--regex-multiline",
                    "--regex-max-replacements",
                    "5",
                ],
                "vibeagent.cli.get_check_regex_replace_report",
                "Check regex replace:",
                "checkRegexReplace",
                {
                    "path": "app.py",
                    "pattern": "old",
                    "replacement": "new\\n",
                    "count": 1,
                    "case_sensitive": False,
                    "multiline": True,
                    "max_replacements": 5,
                },
            ),
            (
                ["--regex-replace", "app.py", "old", "new"],
                "vibeagent.cli.get_regex_replace_report",
                "Regex replace:",
                "regexReplace",
                {
                    "path": "app.py",
                    "pattern": "old",
                    "replacement": "new",
                    "count": 0,
                    "case_sensitive": True,
                    "multiline": False,
                    "max_replacements": 100,
                },
            ),
        ]
        for cli_args, getter_target, title, payload_key, expected_kwargs in cases:
            with self.subTest(payload_key=payload_key), tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
                stdout = io.StringIO()
                report = {
                    "projectRoot": str(Path(base).resolve()),
                    "kind": payload_key,
                    "ok": True,
                    "path": expected_kwargs["path"],
                    "pattern": expected_kwargs["pattern"],
                    "replacement": expected_kwargs["replacement"],
                    "count": expected_kwargs["count"],
                    "caseSensitive": expected_kwargs["case_sensitive"],
                    "multiline": expected_kwargs["multiline"],
                    "maxReplacements": expected_kwargs["max_replacements"],
                    "replacements": 1,
                    "message": "ok",
                    "diff": {"text": "+new\n", "lines": ["+new"], "lineCount": 1},
                }
                rendered = f"{title}\n  ok: yes"
                with (
                    patch("vibeagent.cli.create_chat_client") as create_chat_client,
                    patch(getter_target, return_value=report) as getter,
                    patch("vibeagent.cli.format_regex_replace_report_text", return_value=rendered) as formatter,
                    redirect_stdout(stdout),
                ):
                    exit_code = main(["--json", "--cwd", base, *cli_args])

                payload = json.loads(stdout.getvalue())
                self.assertEqual(exit_code, 0)
                self.assertTrue(payload["success"])
                self.assertEqual(payload[payload_key], report)
                self.assertEqual(payload["text"], rendered)
                getter.assert_called_once_with(Path(base).resolve(), **expected_kwargs)
                formatter.assert_called_once_with(title, report)
                create_chat_client.assert_not_called()
