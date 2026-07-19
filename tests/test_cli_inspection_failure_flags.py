import io
import json
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import patch

from vibeagent.cli import main


class CliInspectionFailureFlagTests(unittest.TestCase):
    def test_main_local_inspection_flags_exit_nonzero_for_failed_results(self) -> None:
        cases = [
            (
                ["--todos", "../bad"],
                "vibeagent.cli.get_todos_text",
                "Path escapes the project directory: ../bad",
                (Path, "../bad"),
            ),
            (
                ["--repo-map", "../bad"],
                "vibeagent.cli.get_repo_map_text",
                "Repo map:\n  ok: no\n  message: Path escapes the project directory: ../bad",
                (Path, "../bad"),
            ),
            (
                ["--search", "needle", "--search-path", "../bad"],
                "vibeagent.cli.get_search_text",
                "Search:\n  ok: no\n  message: Path escapes the project directory: ../bad",
                (Path, "needle", "../bad"),
            ),
            (
                ["--glob", "../*"],
                "vibeagent.cli.get_glob_text",
                "Glob:\n  ok: no\n  message: Path escapes the project directory: ../*",
                (Path, "../*"),
            ),
            (
                ["--file-info", "../bad"],
                "vibeagent.cli.get_file_info_text",
                "File info:\n  paths: 0/1\n  message: Inspected 0/1 path(s).",
                (Path, ["../bad"]),
            ),
        ]

        for argv_tail, patch_target, text, expected_args in cases:
            with self.subTest(argv=argv_tail), tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
                stdout = io.StringIO()

                with (
                    patch("vibeagent.cli.create_chat_client") as create_chat_client,
                    patch(patch_target, return_value=text) as getter,
                    redirect_stdout(stdout),
                ):
                    exit_code = main(["--cwd", base, *argv_tail])

            self.assertEqual(exit_code, 1)
            self.assertEqual(stdout.getvalue(), f"{text}\n")
            resolved_args = tuple(Path(base).resolve() if item is Path else item for item in expected_args)
            getter.assert_called_once_with(*resolved_args)
            create_chat_client.assert_not_called()

    def test_main_local_inspection_flag_reports_json_failure_status(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
            stdout = io.StringIO()
            report = {
                "projectRoot": str(Path(base).resolve()),
                "ok": False,
                "pattern": "../*",
                "matches": {"shown": 0, "total": 0, "truncated": False, "files": []},
                "maxMatches": 200,
                "message": "bad pattern",
            }

            with (
                patch("vibeagent.cli.create_chat_client") as create_chat_client,
                patch("vibeagent.cli.get_glob_report", return_value=report) as get_glob_report,
                patch("vibeagent.cli.format_glob_report_text", return_value="Glob:\n  ok: no\n  message: bad pattern") as format_glob_report_text,
                redirect_stdout(stdout),
            ):
                exit_code = main(["--json", "--cwd", base, "--glob", "../*"])

        payload = json.loads(stdout.getvalue())
        self.assertEqual(exit_code, 1)
        self.assertEqual(payload["kind"], "local")
        self.assertFalse(payload["success"])
        self.assertEqual(payload["status"], "failed")
        self.assertEqual(payload["text"], "Glob:\n  ok: no\n  message: bad pattern")
        self.assertEqual(payload["glob"], report)
        get_glob_report.assert_called_once_with(Path(base).resolve(), "../*")
        format_glob_report_text.assert_called_once_with(report)
        create_chat_client.assert_not_called()


if __name__ == "__main__":
    unittest.main()
