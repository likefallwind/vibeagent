import io
import json
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import patch

from vibeagent.cli import main


class CliReadContextFlagTests(unittest.TestCase):
    def test_main_runs_read_local_flag_without_creating_client(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
            stdout = io.StringIO()

            with (
                patch("vibeagent.cli.create_chat_client") as create_chat_client,
                patch("vibeagent.cli.get_read_text", return_value="Read:\n  ok: yes") as get_read_text,
                redirect_stdout(stdout),
            ):
                exit_code = main(
                    [
                        "--cwd",
                        base,
                        "--read",
                        "src/app.py",
                        "--read-lines",
                        "2:4",
                        "--read-max-bytes",
                        "1000",
                        "--read-line-numbers",
                    ]
                )

        self.assertEqual(exit_code, 0)
        self.assertIn("Read:", stdout.getvalue())
        get_read_text.assert_called_once_with(
            Path(base).resolve(),
            "src/app.py",
            "2:4",
            max_bytes=1000,
            show_line_numbers=True,
        )
        create_chat_client.assert_not_called()

    def test_main_read_json_outputs_structured_payloads(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
            root = Path(base)
            (root / "src").mkdir()
            (root / "src" / "app.py").write_text("one\nTwo\nthree\nfour\n", encoding="utf-8")
            (root / "tests").mkdir()
            (root / "tests" / "test_app.py").write_text("alpha\nbeta\ngamma\n", encoding="utf-8")

            def run_json(*argv: str) -> tuple[int, dict[str, object]]:
                stdout = io.StringIO()
                with redirect_stdout(stdout):
                    exit_code = main(["--json", "--cwd", base, *argv])
                return exit_code, json.loads(stdout.getvalue())

            with patch("vibeagent.cli.create_chat_client") as create_chat_client:
                read_exit, read_payload = run_json("--read", "src/app.py", "--read-lines", "2:3")
                files_exit, files_payload = run_json("--read-files", "src/app.py", "tests/test_app.py")
                ranges_exit, ranges_payload = run_json("--read-ranges", "src/app.py:2:3", "tests/test_app.py:1")

        self.assertEqual(read_exit, 0)
        self.assertEqual(read_payload["read"]["path"], "src/app.py")
        self.assertEqual(read_payload["read"]["range"], "2:3")
        self.assertIn("2: Two", read_payload["read"]["read"]["content"])
        self.assertEqual(files_exit, 0)
        self.assertEqual(files_payload["readFiles"]["files"]["ok"], 2)
        self.assertIn("alpha", files_payload["readFiles"]["files"]["items"][1]["content"])
        self.assertEqual(ranges_exit, 0)
        self.assertEqual(ranges_payload["readRanges"]["ranges"]["ok"], 2)
        self.assertEqual(ranges_payload["readRanges"]["ranges"]["items"][0]["endLine"], 3)
        self.assertIn("1: alpha", ranges_payload["readRanges"]["ranges"]["items"][1]["content"])
        create_chat_client.assert_not_called()

    def test_main_runs_tail_local_flag_without_creating_client(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
            stdout = io.StringIO()

            with (
                patch("vibeagent.cli.create_chat_client") as create_chat_client,
                patch("vibeagent.cli.get_tail_text", return_value="Tail:\n  ok: yes") as get_tail_text,
                redirect_stdout(stdout),
            ):
                exit_code = main(["--cwd", base, "--tail", "logs/app.log", "--tail-lines", "3", "--tail-max-bytes", "1000"])

        self.assertEqual(exit_code, 0)
        self.assertIn("Tail:", stdout.getvalue())
        get_tail_text.assert_called_once_with(Path(base).resolve(), "logs/app.log", 3, max_bytes=1000)
        create_chat_client.assert_not_called()

    def test_main_runs_around_local_flag_without_creating_client(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
            stdout = io.StringIO()

            with (
                patch("vibeagent.cli.create_chat_client") as create_chat_client,
                patch("vibeagent.cli.get_around_text", return_value="Around:\n  ok: yes") as get_around_text,
                redirect_stdout(stdout),
            ):
                exit_code = main(["--cwd", base, "--around", "src/app.py", "42", "--around-lines", "8", "--around-max-bytes", "1200"])

        self.assertEqual(exit_code, 0)
        self.assertIn("Around:", stdout.getvalue())
        get_around_text.assert_called_once_with(Path(base).resolve(), "src/app.py 42", 8, max_bytes=1200)
        create_chat_client.assert_not_called()

    def test_main_runs_around_many_local_flag_without_creating_client(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
            stdout = io.StringIO()

            with (
                patch("vibeagent.cli.create_chat_client") as create_chat_client,
                patch("vibeagent.cli.get_around_many_text", return_value="Around many:\n  contexts: 2/2") as get_around_many_text,
                redirect_stdout(stdout),
            ):
                exit_code = main(["--cwd", base, "--around-many", "src/app.py:42:8", "tests/test_app.py:17", "--around-many-max-bytes", "1400"])

        self.assertEqual(exit_code, 0)
        self.assertIn("Around many:", stdout.getvalue())
        get_around_many_text.assert_called_once_with(Path(base).resolve(), ["src/app.py:42:8", "tests/test_app.py:17"], max_bytes_per_context=1400)
        create_chat_client.assert_not_called()

    def test_main_context_json_outputs_structured_payloads(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
            root = Path(base)
            (root / "src").mkdir()
            (root / "src" / "app.py").write_text("one\nTwo\nthree\nfour\n", encoding="utf-8")
            (root / "tests").mkdir()
            (root / "tests" / "test_app.py").write_text("alpha\nbeta\ngamma\n", encoding="utf-8")
            (root / "logs").mkdir()
            (root / "logs" / "app.log").write_text("one\ntwo\nthree\nfour\n", encoding="utf-8")

            def run_json(*argv: str) -> tuple[int, dict[str, object]]:
                stdout = io.StringIO()
                with redirect_stdout(stdout):
                    exit_code = main(["--json", "--cwd", base, *argv])
                return exit_code, json.loads(stdout.getvalue())

            with patch("vibeagent.cli.create_chat_client") as create_chat_client:
                tail_exit, tail_payload = run_json("--tail", "logs/app.log", "--tail-lines", "2")
                around_exit, around_payload = run_json("--around", "src/app.py", "3", "--around-lines", "1")
                many_exit, many_payload = run_json("--around-many", "src/app.py:3:1", "tests/test_app.py:2")

        self.assertEqual(tail_exit, 0)
        self.assertEqual(tail_payload["tail"]["path"], "logs/app.log")
        self.assertEqual(tail_payload["tail"]["tail"]["startLine"], 3)
        self.assertIn("3: three", tail_payload["tail"]["tail"]["content"])
        self.assertEqual(around_exit, 0)
        self.assertEqual(around_payload["around"]["path"], "src/app.py")
        self.assertEqual(around_payload["around"]["context"]["startLine"], 2)
        self.assertEqual(around_payload["around"]["context"]["endLine"], 4)
        self.assertIn("2: Two", around_payload["around"]["context"]["content"])
        self.assertEqual(many_exit, 0)
        self.assertEqual(many_payload["aroundMany"]["contexts"]["ok"], 2)
        self.assertEqual(many_payload["aroundMany"]["contexts"]["items"][1]["path"], "tests/test_app.py")
        self.assertIn("2: beta", many_payload["aroundMany"]["contexts"]["items"][1]["content"])
        create_chat_client.assert_not_called()

    def test_main_batch_read_local_flags_exit_nonzero_for_incomplete_results(self) -> None:
        cases = [
            (
                ["--around-many", "src/app.py:42:8", "missing.py:1"],
                "vibeagent.cli.get_around_many_text",
                "Around many:\n  contexts: 1/2",
                (Path, ["src/app.py:42:8", "missing.py:1"]),
            ),
            (
                ["--read-files", "src/app.py", "missing.py"],
                "vibeagent.cli.get_read_files_text",
                "Read files:\n  files: 1/2",
                (Path, ["src/app.py", "missing.py"]),
            ),
            (
                ["--read-ranges", "src/app.py:1:5", "missing.py:1:3"],
                "vibeagent.cli.get_read_ranges_text",
                "Read ranges:\n  ranges: 1/2",
                (Path, ["src/app.py:1:5", "missing.py:1:3"]),
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

    def test_main_batch_read_local_flag_reports_json_failure_status(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
            stdout = io.StringIO()
            report = {
                "projectRoot": str(Path(base).resolve()),
                "ok": False,
                "files": {"ok": 0, "total": 2, "items": []},
                "maxBytesPerFile": 20000,
                "message": "Read 0/2 file(s).",
            }

            with (
                patch("vibeagent.cli.create_chat_client") as create_chat_client,
                patch("vibeagent.cli.get_read_files_report", return_value=report) as get_read_files_report,
                patch(
                    "vibeagent.cli.format_read_files_report_text",
                    return_value="Read files:\n  files: 0/2",
                ) as format_read_files_report_text,
                redirect_stdout(stdout),
            ):
                exit_code = main(["--json", "--cwd", base, "--read-files", "missing-a.py", "missing-b.py"])

        self.assertEqual(exit_code, 1)
        payload = json.loads(stdout.getvalue())
        self.assertEqual(payload["kind"], "local")
        self.assertFalse(payload["success"])
        self.assertEqual(payload["status"], "failed")
        self.assertEqual(payload["text"], "Read files:\n  files: 0/2")
        self.assertEqual(payload["readFiles"], report)
        get_read_files_report.assert_called_once_with(Path(base).resolve(), ["missing-a.py", "missing-b.py"])
        format_read_files_report_text.assert_called_once_with(report)
        create_chat_client.assert_not_called()
