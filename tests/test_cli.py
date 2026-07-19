import io
import json
import os
import subprocess
import tempfile
import unittest
from contextlib import ExitStack, redirect_stdout
from pathlib import Path
from unittest.mock import Mock, call, patch

from vibeagent import MACHINE_OUTPUT_SCHEMA_VERSION, __version__, cli as cli_module
from vibeagent.agent import AgentResult
from vibeagent.cli import main
from vibeagent.types import ApprovalRequest


class CliTests(unittest.TestCase):
    def test_main_rejects_invalid_permission_override_rule(self) -> None:
        stdout = io.StringIO()

        with (
            patch("vibeagent.cli.create_chat_client") as create_chat_client,
            redirect_stdout(stdout),
        ):
            exit_code = main(["--json", "--allowed-tools", "Read(", "inspect"])

        payload = json.loads(stdout.getvalue())
        self.assertEqual(exit_code, 2)
        self.assertEqual(payload["kind"], "error")
        self.assertEqual(payload["schemaVersion"], MACHINE_OUTPUT_SCHEMA_VERSION)
        self.assertEqual(payload["version"], __version__)
        self.assertIn("permission rule is invalid", payload["error"])
        self.assertEqual(payload["stopReason"], "failed")
        self.assertEqual(payload["stop_reason"], "failed")
        create_chat_client.assert_not_called()

    def test_main_rejects_permission_overrides_without_code_task(self) -> None:
        cases = [
            ["--json", "--allowed-tools", "Read"],
            ["--json", "--allowed-tools", "Read", "--chat", "hello"],
            ["--json", "--disallowed-tools", "Edit", "--permissions"],
            ["--json", "--permission-mode", "acceptEdits"],
        ]
        for argv in cases:
            with self.subTest(argv=argv):
                stdout = io.StringIO()
                with (
                    patch("vibeagent.cli.create_chat_client") as create_chat_client,
                    redirect_stdout(stdout),
                ):
                    exit_code = main(argv)

                payload = json.loads(stdout.getvalue())
                self.assertEqual(exit_code, 2)
                self.assertIn("can only be used with one-shot coding tasks", payload["error"])
                create_chat_client.assert_not_called()

    def test_main_reports_command_cwd_without_command_check_as_local_flag_error(self) -> None:
        stdout = io.StringIO()

        with (
            patch("vibeagent.cli.create_chat_client") as create_chat_client,
            redirect_stdout(stdout),
        ):
            exit_code = main(["--command-cwd", "src", "fix", "tests"])

        self.assertEqual(exit_code, 2)
        self.assertEqual(stdout.getvalue(), "--command-cwd can only be used with --command-check or --command.\n")
        create_chat_client.assert_not_called()

    def test_main_reports_start_cwd_without_start_command_as_local_flag_error(self) -> None:
        stdout = io.StringIO()

        with (
            patch("vibeagent.cli.create_chat_client") as create_chat_client,
            redirect_stdout(stdout),
        ):
            exit_code = main(["--start-cwd", "src", "fix", "tests"])

        self.assertEqual(exit_code, 2)
        self.assertEqual(stdout.getvalue(), "--start-cwd can only be used with --check-start-command, --start-command, or --start.\n")
        create_chat_client.assert_not_called()

    def test_main_reports_run_options_without_run_command_as_local_flag_error(self) -> None:
        cases = [
            (["--run-cwd", "src", "fix"], "--run-cwd can only be used with --run-command, --run, --run-commands, or --check-run-commands.\n"),
            (["--run-timeout-ms", "2000", "fix"], "--run-timeout-ms can only be used with --run-command, --run, --run-commands, --run-suggested-checks, --run-focused-tests, or --run-session-verification.\n"),
            (["--run-max-chars", "2000", "fix"], "--run-max-chars can only be used with --run-command, --run, --run-commands, --run-suggested-checks, --run-focused-tests, or --run-session-verification.\n"),
            (["--run-continue-on-failure", "fix"], "--run-continue-on-failure can only be used with --run-commands, --run-suggested-checks, --run-focused-tests, or --run-session-verification.\n"),
            (["--run-output-contexts", "fix"], "--run-output-contexts can only be used with --run-command, --run, --run-commands, --run-suggested-checks, --run-focused-tests, or --run-session-verification.\n"),
            (["--run-output-diagnostics", "fix"], "--run-output-diagnostics can only be used with --run-command, --run, --run-commands, --run-suggested-checks, --run-focused-tests, or --run-session-verification.\n"),
            (["--run-output-context-lines", "2", "fix"], "--run-output-context-lines can only be used with --run-command, --run, --run-commands, --run-suggested-checks, --run-focused-tests, or --run-session-verification.\n"),
            (["--run-output-context-max", "5", "fix"], "--run-output-context-max can only be used with --run-command, --run, --run-commands, --run-suggested-checks, --run-focused-tests, or --run-session-verification.\n"),
            (["--run-output-context-max-bytes", "1000", "fix"], "--run-output-context-max-bytes can only be used with --run-command, --run, --run-commands, --run-suggested-checks, --run-focused-tests, or --run-session-verification.\n"),
            (["--run-output-diagnostic-max", "5", "fix"], "--run-output-diagnostic-max can only be used with --run-command, --run, --run-commands, --run-suggested-checks, --run-focused-tests, or --run-session-verification.\n"),
        ]
        for argv, expected in cases:
            with self.subTest(argv=argv):
                stdout = io.StringIO()
                with (
                    patch("vibeagent.cli.create_chat_client") as create_chat_client,
                    redirect_stdout(stdout),
                ):
                    exit_code = main(argv)

                self.assertEqual(exit_code, 2)
                self.assertEqual(stdout.getvalue(), expected)
                create_chat_client.assert_not_called()

    def test_main_reports_port_and_http_options_without_matching_local_flag(self) -> None:
        cases = [
            (["--port-host", "0.0.0.0", "fix"], "--port-host can only be used with --port-check.\n"),
            (["--port-timeout-ms", "1500", "fix"], "--port-timeout-ms can only be used with --port-check.\n"),
            (["--http-timeout-ms", "1500", "fix"], "--http-timeout-ms can only be used with --http-check or --http-fetch.\n"),
            (["--http-max-body-chars", "1000", "fix"], "--http-max-body-chars can only be used with --http-check or --http-fetch.\n"),
            (["--http-contains", "ready", "fix"], "--http-contains can only be used with --http-check.\n"),
            (["--http-regex", "fix"], "--http-regex can only be used with --http-check.\n"),
        ]
        for argv, expected in cases:
            with self.subTest(argv=argv):
                stdout = io.StringIO()
                with (
                    patch("vibeagent.cli.create_chat_client") as create_chat_client,
                    redirect_stdout(stdout),
                ):
                    exit_code = main(argv)

                self.assertEqual(exit_code, 2)
                self.assertEqual(stdout.getvalue(), expected)
                create_chat_client.assert_not_called()

    def test_main_runs_code_deps_local_flag_without_creating_client(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
            stdout = io.StringIO()

            with (
                patch("vibeagent.cli.create_chat_client") as create_chat_client,
                patch("vibeagent.cli.get_code_deps_text", return_value="Code dependencies:\n  files: 1/1") as get_code_deps_text,
                redirect_stdout(stdout),
            ):
                exit_code = main(["--cwd", base, "--code-deps", "web"])

        self.assertEqual(exit_code, 0)
        self.assertIn("Code dependencies:", stdout.getvalue())
        get_code_deps_text.assert_called_once_with(Path(base).resolve(), "web")
        create_chat_client.assert_not_called()

    def test_main_runs_code_refs_local_flag_without_creating_client(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
            stdout = io.StringIO()

            with (
                patch("vibeagent.cli.create_chat_client") as create_chat_client,
                patch("vibeagent.cli.get_code_refs_text", return_value="Code references:\n  references: 1/1") as get_code_refs_text,
                redirect_stdout(stdout),
            ):
                exit_code = main(["--cwd", base, "--code-refs", "runAgent", "--code-path", "web"])

        self.assertEqual(exit_code, 0)
        self.assertIn("Code references:", stdout.getvalue())
        get_code_refs_text.assert_called_once_with(Path(base).resolve(), symbol="runAgent", path="web")
        create_chat_client.assert_not_called()

    def test_main_runs_code_ref_contexts_local_flag_without_creating_client(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
            stdout = io.StringIO()

            with (
                patch("vibeagent.cli.create_chat_client") as create_chat_client,
                patch("vibeagent.cli.get_code_ref_contexts_text", return_value="Code reference contexts:\n  contexts: 1/1") as get_code_ref_contexts_text,
                redirect_stdout(stdout),
            ):
                exit_code = main(["--cwd", base, "--code-ref-contexts", "runAgent", "--code-path", "web"])

        self.assertEqual(exit_code, 0)
        self.assertIn("Code reference contexts:", stdout.getvalue())
        get_code_ref_contexts_text.assert_called_once_with(Path(base).resolve(), symbol="runAgent", path="web")
        create_chat_client.assert_not_called()

    def test_main_runs_code_defs_local_flag_without_creating_client(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
            stdout = io.StringIO()

            with (
                patch("vibeagent.cli.create_chat_client") as create_chat_client,
                patch("vibeagent.cli.get_code_defs_text", return_value="Code definitions:\n  definitions: 1/1") as get_code_defs_text,
                redirect_stdout(stdout),
            ):
                exit_code = main(["--cwd", base, "--code-defs", "runAgent", "--code-path", "web"])

        self.assertEqual(exit_code, 0)
        self.assertIn("Code definitions:", stdout.getvalue())
        get_code_defs_text.assert_called_once_with(Path(base).resolve(), symbol="runAgent", path="web")
        create_chat_client.assert_not_called()

    def test_main_runs_code_intelligence_local_flags_as_json_without_creating_client(self) -> None:
        cases = [
            (
                ["--code-deps", "web"],
                "vibeagent.cli.get_code_deps_report",
                "vibeagent.cli.format_code_deps_report_text",
                "codeDependencies",
                (Path, "web"),
                {},
            ),
            (
                ["--code-refs", "runAgent", "--code-path", "web", "--code-max-matches", "4"],
                "vibeagent.cli.get_code_refs_report",
                "vibeagent.cli.format_code_refs_report_text",
                "codeReferences",
                (Path,),
                {"symbol": "runAgent", "path": "web", "max_matches": 4},
            ),
            (
                [
                    "--code-ref-contexts",
                    "runAgent",
                    "--code-path",
                    "web",
                    "--code-max-matches",
                    "5",
                    "--code-context-lines",
                    "1",
                    "--code-context-max-bytes",
                    "1000",
                ],
                "vibeagent.cli.get_code_ref_contexts_report",
                "vibeagent.cli.format_code_ref_contexts_report_text",
                "codeReferenceContexts",
                (Path,),
                {"symbol": "runAgent", "path": "web", "max_matches": 5, "context_lines": 1, "max_bytes_per_context": 1000},
            ),
            (
                ["--code-defs", "runAgent", "--code-path", "web", "--code-max-matches", "6", "--code-def-max-lines", "40"],
                "vibeagent.cli.get_code_defs_report",
                "vibeagent.cli.format_code_defs_report_text",
                "codeDefinitions",
                (Path,),
                {"symbol": "runAgent", "path": "web", "max_matches": 6, "max_lines": 40},
            ),
        ]

        for argv_tail, getter_target, formatter_target, payload_key, expected_args, expected_kwargs in cases:
            with self.subTest(payload_key=payload_key), tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
                stdout = io.StringIO()
                report = {"ok": True, "message": payload_key}
                rendered = f"{payload_key}: ok"

                with (
                    patch("vibeagent.cli.create_chat_client") as create_chat_client,
                    patch(getter_target, return_value=report) as getter,
                    patch(formatter_target, return_value=rendered) as formatter,
                    redirect_stdout(stdout),
                ):
                    exit_code = main(["--json", "--cwd", base, *argv_tail])

                payload = json.loads(stdout.getvalue())
                resolved_args = tuple(Path(base).resolve() if item is Path else item for item in expected_args)
                self.assertEqual(exit_code, 0)
                self.assertTrue(payload["success"])
                self.assertEqual(payload["status"], "completed")
                self.assertEqual(payload["text"], rendered)
                self.assertEqual(payload[payload_key], report)
                getter.assert_called_once_with(*resolved_args, **expected_kwargs)
                formatter.assert_called_once_with(report)
                create_chat_client.assert_not_called()

    def test_main_runs_code_symbol_local_flags_with_bounds(self) -> None:
        cases = [
            (
                ["--code-refs", "runAgent", "--code-path", "web", "--code-max-matches", "4"],
                "vibeagent.cli.get_code_refs_text",
                "Code references:\n  references: 1/1",
                {"symbol": "runAgent", "path": "web", "max_matches": 4},
            ),
            (
                [
                    "--code-ref-contexts",
                    "runAgent",
                    "--code-path",
                    "web",
                    "--code-max-matches",
                    "5",
                    "--code-context-lines",
                    "1",
                    "--code-context-max-bytes",
                    "1000",
                ],
                "vibeagent.cli.get_code_ref_contexts_text",
                "Code reference contexts:\n  contexts: 1/1",
                {"symbol": "runAgent", "path": "web", "max_matches": 5, "context_lines": 1, "max_bytes_per_context": 1000},
            ),
            (
                ["--code-defs", "runAgent", "--code-path", "web", "--code-max-matches", "6", "--code-def-max-lines", "40"],
                "vibeagent.cli.get_code_defs_text",
                "Code definitions:\n  definitions: 1/1",
                {"symbol": "runAgent", "path": "web", "max_matches": 6, "max_lines": 40},
            ),
        ]

        for argv_tail, patch_target, text, expected_kwargs in cases:
            with self.subTest(argv=argv_tail), tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
                stdout = io.StringIO()

                with (
                    patch("vibeagent.cli.create_chat_client") as create_chat_client,
                    patch(patch_target, return_value=text) as getter,
                    redirect_stdout(stdout),
                ):
                    exit_code = main(["--cwd", base, *argv_tail])

            self.assertEqual(exit_code, 0)
            self.assertEqual(stdout.getvalue(), f"{text}\n")
            getter.assert_called_once_with(Path(base).resolve(), **expected_kwargs)
            create_chat_client.assert_not_called()

    def test_main_rejects_code_symbol_bounds_without_matching_local_flag(self) -> None:
        cases = [
            (
                ["--code-max-matches", "3"],
                "--code-max-matches can only be used with --code-refs, --code-ref-contexts, or --code-defs.",
            ),
            (
                ["--code-def-max-lines", "40"],
                "--code-def-max-lines can only be used with --code-defs.",
            ),
            (
                ["--code-refs", "runAgent", "--code-def-max-lines", "40"],
                "--code-def-max-lines can only be used with --code-defs.",
            ),
            (
                ["--code-context-lines", "1"],
                "--code-context-lines can only be used with --code-ref-contexts.",
            ),
            (
                ["--code-refs", "runAgent", "--code-context-lines", "1"],
                "--code-context-lines can only be used with --code-ref-contexts.",
            ),
            (
                ["--code-context-max-bytes", "1000"],
                "--code-context-max-bytes can only be used with --code-ref-contexts.",
            ),
        ]

        for argv, expected in cases:
            with self.subTest(argv=argv):
                stdout = io.StringIO()

                with (
                    patch("vibeagent.cli.create_chat_client") as create_chat_client,
                    redirect_stdout(stdout),
                ):
                    exit_code = main(argv)

                self.assertEqual(exit_code, 2)
                self.assertEqual(stdout.getvalue(), f"{expected}\n")
                create_chat_client.assert_not_called()

    def test_main_runs_code_rename_preview_local_flag_without_creating_client(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
            stdout = io.StringIO()

            with (
                patch("vibeagent.cli.create_chat_client") as create_chat_client,
                patch("vibeagent.cli.get_code_rename_preview_text", return_value="Code rename preview:\n  replacements: 1") as get_code_rename_preview_text,
                redirect_stdout(stdout),
            ):
                exit_code = main(["--cwd", base, "--code-rename-preview", "runAgent", "executeAgent", "--code-path", "web"])

        self.assertEqual(exit_code, 0)
        self.assertIn("Code rename preview:", stdout.getvalue())
        get_code_rename_preview_text.assert_called_once_with(Path(base).resolve(), symbol="runAgent", new_name="executeAgent", path="web")
        create_chat_client.assert_not_called()

    def test_main_runs_code_rename_local_flag_without_creating_client(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
            stdout = io.StringIO()

            with (
                patch("vibeagent.cli.create_chat_client") as create_chat_client,
                patch("vibeagent.cli.get_code_rename_text", return_value="Code rename:\n  replacements: 1") as get_code_rename_text,
                redirect_stdout(stdout),
            ):
                exit_code = main(["--cwd", base, "--code-rename", "runAgent", "executeAgent", "--code-path", "web"])

        self.assertEqual(exit_code, 0)
        self.assertIn("Code rename:", stdout.getvalue())
        get_code_rename_text.assert_called_once_with(Path(base).resolve(), symbol="runAgent", new_name="executeAgent", path="web")
        create_chat_client.assert_not_called()

    def test_main_runs_code_rename_local_flags_as_json_without_creating_client(self) -> None:
        cases = [
            (
                ["--code-rename-preview", "runAgent", "executeAgent", "--code-path", "web"],
                "vibeagent.cli.get_code_rename_preview_report",
                "Code rename preview:",
                "codeRenamePreview",
            ),
            (
                ["--code-rename", "runAgent", "executeAgent", "--code-path", "web"],
                "vibeagent.cli.get_code_rename_report",
                "Code rename:",
                "codeRename",
            ),
        ]

        for argv_tail, getter_target, title, payload_key in cases:
            with self.subTest(payload_key=payload_key), tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
                stdout = io.StringIO()
                report = {"ok": True, "message": payload_key}
                rendered = f"{payload_key}: ok"

                with (
                    patch("vibeagent.cli.create_chat_client") as create_chat_client,
                    patch(getter_target, return_value=report) as getter,
                    patch("vibeagent.cli.format_code_rename_report_text", return_value=rendered) as formatter,
                    redirect_stdout(stdout),
                ):
                    exit_code = main(["--json", "--cwd", base, *argv_tail])

                payload = json.loads(stdout.getvalue())
                self.assertEqual(exit_code, 0)
                self.assertTrue(payload["success"])
                self.assertEqual(payload["status"], "completed")
                self.assertEqual(payload["text"], rendered)
                self.assertEqual(payload[payload_key], report)
                getter.assert_called_once_with(Path(base).resolve(), symbol="runAgent", new_name="executeAgent", path="web")
                formatter.assert_called_once_with(title, report)
                create_chat_client.assert_not_called()

    def test_main_runs_git_info_local_flag_without_creating_client(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
            stdout = io.StringIO()

            with (
                patch("vibeagent.cli.create_chat_client") as create_chat_client,
                patch("vibeagent.cli.get_git_status_text", return_value="Git status:\n  ok: yes") as get_git_status_text,
                redirect_stdout(stdout),
            ):
                exit_code = main(["--cwd", base, "--git-status"])

        self.assertEqual(exit_code, 0)
        self.assertIn("Git status:", stdout.getvalue())
        get_git_status_text.assert_called_once_with(Path(base).resolve())
        create_chat_client.assert_not_called()

        with tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
            stdout = io.StringIO()

            with (
                patch("vibeagent.cli.create_chat_client") as create_chat_client,
                patch("vibeagent.cli.get_git_conflicts_text", return_value="Git conflicts:\n  ok: yes") as get_git_conflicts_text,
                redirect_stdout(stdout),
            ):
                exit_code = main(["--cwd", base, "--conflicts", "src"])

        self.assertEqual(exit_code, 0)
        self.assertIn("Git conflicts:", stdout.getvalue())
        get_git_conflicts_text.assert_called_once_with(Path(base).resolve(), "src")
        create_chat_client.assert_not_called()

        with tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
            stdout = io.StringIO()
            report = {
                "projectRoot": str(Path(base).resolve()),
                "ok": True,
                "path": "src",
                "unmerged": {"shown": 1, "total": 1, "items": [{"status": "UU", "path": "src/app.py"}]},
                "markers": {"shown": 1, "total": 1, "items": [{"path": "src/app.py", "line": 1, "marker": "<<<<<<<", "text": "<<<<<<< HEAD"}]},
                "scannedFiles": 1,
                "totalFiles": 1,
                "truncated": False,
                "message": "Found conflicts.",
            }

            with (
                patch("vibeagent.cli.create_chat_client") as create_chat_client,
                patch("vibeagent.cli.get_git_conflicts_report", return_value=report) as get_git_conflicts_report,
                patch("vibeagent.cli.format_git_conflicts_report_text", return_value="Git conflicts:\n  ok: yes") as formatter,
                redirect_stdout(stdout),
            ):
                exit_code = main(["--json", "--cwd", base, "--conflicts", "src"])

        payload = json.loads(stdout.getvalue())
        self.assertEqual(exit_code, 0)
        self.assertTrue(payload["success"])
        self.assertEqual(payload["status"], "completed")
        self.assertEqual(payload["gitConflicts"], report)
        self.assertIn("Git conflicts:", payload["text"])
        get_git_conflicts_report.assert_called_once_with(Path(base).resolve(), "src")
        formatter.assert_called_once_with(report)
        create_chat_client.assert_not_called()

        with tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
            stdout = io.StringIO()

            with (
                patch("vibeagent.cli.create_chat_client") as create_chat_client,
                patch("vibeagent.cli.get_git_info_text", return_value="Git info:\n  branch: main") as get_git_info_text,
                redirect_stdout(stdout),
            ):
                exit_code = main(["--cwd", base, "--git-info"])

        self.assertEqual(exit_code, 0)
        self.assertIn("Git info:", stdout.getvalue())
        get_git_info_text.assert_called_once_with(Path(base).resolve())
        create_chat_client.assert_not_called()

    def test_main_runs_branches_local_flag_without_creating_client(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
            stdout = io.StringIO()

            with (
                patch("vibeagent.cli.create_chat_client") as create_chat_client,
                patch("vibeagent.cli.get_branches_text", return_value="Branches:\n  current: main") as get_branches_text,
                redirect_stdout(stdout),
            ):
                exit_code = main(["--cwd", base, "--branches"])

        self.assertEqual(exit_code, 0)
        self.assertIn("Branches:", stdout.getvalue())
        get_branches_text.assert_called_once_with(Path(base).resolve())
        create_chat_client.assert_not_called()

    def test_main_runs_log_local_flag_without_creating_client(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
            stdout = io.StringIO()

            with (
                patch("vibeagent.cli.create_chat_client") as create_chat_client,
                patch("vibeagent.cli.get_log_text", return_value="Log:\n  ok: yes") as get_log_text,
                redirect_stdout(stdout),
            ):
                exit_code = main(["--cwd", base, "--log", "app.py", "--log-count", "2"])

        self.assertEqual(exit_code, 0)
        self.assertIn("Log:", stdout.getvalue())
        get_log_text.assert_called_once_with(Path(base).resolve(), "app.py", 2)
        create_chat_client.assert_not_called()

    def test_main_runs_show_local_flag_without_creating_client(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
            stdout = io.StringIO()

            with (
                patch("vibeagent.cli.create_chat_client") as create_chat_client,
                patch("vibeagent.cli.get_show_text", return_value="Show:\n  ok: yes") as get_show_text,
                redirect_stdout(stdout),
            ):
                exit_code = main(["--cwd", base, "--show", "HEAD", "--show-path", "app.py", "--show-max-chars", "2000"])

        self.assertEqual(exit_code, 0)
        self.assertIn("Show:", stdout.getvalue())
        get_show_text.assert_called_once_with(Path(base).resolve(), rev="HEAD", path="app.py", max_output_chars=2000)
        create_chat_client.assert_not_called()

    def test_main_runs_blame_local_flag_without_creating_client(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
            stdout = io.StringIO()

            with (
                patch("vibeagent.cli.create_chat_client") as create_chat_client,
                patch("vibeagent.cli.get_blame_text", return_value="Blame:\n  ok: yes") as get_blame_text,
                redirect_stdout(stdout),
            ):
                exit_code = main(["--cwd", base, "--blame", "app.py", "--blame-lines", "2:4", "--blame-max-chars", "2000"])

        self.assertEqual(exit_code, 0)
        self.assertIn("Blame:", stdout.getvalue())
        get_blame_text.assert_called_once_with(Path(base).resolve(), "app.py", "2:4", 2000)
        create_chat_client.assert_not_called()

    def test_main_runs_stashes_local_flag_without_creating_client(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
            stdout = io.StringIO()

            with (
                patch("vibeagent.cli.create_chat_client") as create_chat_client,
                patch("vibeagent.cli.get_stashes_text", return_value="Stashes:\n  entries: 1/1") as get_stashes_text,
                redirect_stdout(stdout),
            ):
                exit_code = main(["--cwd", base, "--stashes", "--stash-count", "3"])

        self.assertEqual(exit_code, 0)
        self.assertIn("Stashes:", stdout.getvalue())
        get_stashes_text.assert_called_once_with(Path(base).resolve(), max_entries=3)
        create_chat_client.assert_not_called()

    def test_main_read_only_git_json_outputs_structured_payloads(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
            root = Path(base)
            subprocess.run(["git", "init", "--initial-branch", "main"], cwd=root, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            subprocess.run(["git", "config", "user.name", "Test"], cwd=root, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=root, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            (root / "app.py").write_text("alpha\nbeta\n", encoding="utf-8")
            subprocess.run(["git", "add", "app.py"], cwd=root, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            subprocess.run(["git", "commit", "-m", "initial app"], cwd=root, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            (root / "app.py").write_text("alpha\nbeta changed\n", encoding="utf-8")
            subprocess.run(["git", "add", "app.py"], cwd=root, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            subprocess.run(["git", "commit", "-m", "update beta"], cwd=root, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            subprocess.run(["git", "branch", "feature/work"], cwd=root, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            (root / "app.py").write_text("alpha\nbeta stashed\n", encoding="utf-8")
            subprocess.run(["git", "stash", "push", "-m", "save local app"], cwd=root, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            (root / "notes.txt").write_text("local note\n", encoding="utf-8")

            def run_json(*argv: str) -> tuple[int, dict[str, object]]:
                stdout = io.StringIO()
                with redirect_stdout(stdout):
                    exit_code = main(["--json", "--cwd", base, *argv])
                return exit_code, json.loads(stdout.getvalue())

            with patch("vibeagent.cli.create_chat_client") as create_chat_client:
                status_exit, status_payload = run_json("--git-status")
                info_exit, info_payload = run_json("--git-info")
                branches_exit, branches_payload = run_json("--branches")
                log_exit, log_payload = run_json("--log", "app.py", "--log-count", "2")
                show_exit, show_payload = run_json("--show", "HEAD", "--show-path", "app.py")
                blame_exit, blame_payload = run_json("--blame", "app.py", "--blame-lines", "2:2")
                stashes_exit, stashes_payload = run_json("--stashes", "--stash-count", "1")

        self.assertEqual(status_exit, 0)
        self.assertIn("gitStatus", status_payload)
        self.assertEqual(status_payload["gitStatus"]["status"]["count"], 1)
        self.assertIn("?? notes.txt", status_payload["gitStatus"]["status"]["lines"])
        self.assertEqual(info_exit, 0)
        self.assertEqual(info_payload["gitInfo"]["branch"], "main")
        self.assertEqual(info_payload["gitInfo"]["status"]["count"], 1)
        self.assertEqual(branches_exit, 0)
        self.assertEqual(branches_payload["branches"]["branches"]["shown"], 2)
        self.assertEqual(log_exit, 0)
        self.assertEqual(log_payload["log"]["commits"]["shown"], 2)
        self.assertIn("update beta", log_payload["log"]["commits"]["items"][0]["subject"])
        self.assertEqual(show_exit, 0)
        self.assertIn("+beta changed", show_payload["show"]["output"]["text"])
        self.assertEqual(blame_exit, 0)
        self.assertIn("beta changed", blame_payload["blame"]["output"]["text"])
        self.assertEqual(stashes_exit, 0)
        self.assertEqual(stashes_payload["stashes"]["entries"]["items"][0]["name"], "stash@{0}")
        create_chat_client.assert_not_called()

    def test_main_read_only_git_local_flags_exit_nonzero_for_failed_results(self) -> None:
        cases = [
            (["--git-status"], "vibeagent.cli.get_git_status_text", "Git status:\n  ok: no", (Path,), {}),
            (["--conflicts", "src"], "vibeagent.cli.get_git_conflicts_text", "Git conflicts:\n  ok: no", (Path, "src"), {}),
            (["--git-info"], "vibeagent.cli.get_git_info_text", "Git info:\n  ok: no", (Path,), {}),
            (["--branches"], "vibeagent.cli.get_branches_text", "Branches:\n  ok: no", (Path,), {}),
            (["--log", "app.py", "--log-count", "2"], "vibeagent.cli.get_log_text", "Log:\n  ok: no", (Path, "app.py", 2), {}),
            (
                ["--show", "badrev", "--show-path", "app.py", "--show-max-chars", "2000"],
                "vibeagent.cli.get_show_text",
                "Show:\n  ok: no",
                (Path,),
                {"rev": "badrev", "path": "app.py", "max_output_chars": 2000},
            ),
            (["--blame", "missing.py", "--blame-lines", "2:4", "--blame-max-chars", "2000"], "vibeagent.cli.get_blame_text", "Blame:\n  ok: no", (Path, "missing.py", "2:4", 2000), {}),
            (["--stashes", "--stash-count", "3"], "vibeagent.cli.get_stashes_text", "Stashes:\n  ok: no", (Path,), {"max_entries": 3}),
            (["--diff"], "vibeagent.cli.get_diff_text", "Diff:\n  error: git diff failed", (Path, None), {"max_chars": 12000}),
            (
                ["--diff-hunks"],
                "vibeagent.cli.get_diff_hunks_text",
                "Diff hunks:\n  ok: no",
                (Path, None),
                {"max_hunks": 80, "max_lines_per_hunk": 80},
            ),
            (
                ["--diff-contexts"],
                "vibeagent.cli.get_diff_contexts_text",
                "Diff contexts:\n  ok: no",
                (Path, None),
                {"context_lines": 5, "max_hunks": 80, "max_bytes_per_context": 20000},
            ),
        ]

        for argv_tail, patch_target, text, expected_args, expected_kwargs in cases:
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
            getter.assert_called_once_with(*resolved_args, **expected_kwargs)
            create_chat_client.assert_not_called()

    def test_main_changes_local_flag_exit_nonzero_for_failed_result(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
            stdout = io.StringIO()
            report = {
                "projectRoot": str(Path(base).resolve()),
                "ok": False,
                "changedFiles": {"shown": 0, "total": 0, "truncated": False, "files": []},
                "counts": {"staged": 0, "unstaged": 0, "untracked": 0, "binary": 0, "insertions": 0, "deletions": 0},
                "message": "git status failed",
            }

            with (
                patch("vibeagent.cli.create_chat_client") as create_chat_client,
                patch("vibeagent.cli.get_changes_report", return_value=report) as get_changes_report,
                patch("vibeagent.cli.format_changes_report_text", return_value="Changes:\n  ok: no") as format_changes_report_text,
                redirect_stdout(stdout),
            ):
                exit_code = main(["--cwd", base, "--changes"])

        self.assertEqual(exit_code, 1)
        self.assertEqual(stdout.getvalue(), "Changes:\n  ok: no\n")
        get_changes_report.assert_called_once_with(Path(base).resolve(), max_files=200)
        format_changes_report_text.assert_called_once_with(report)
        create_chat_client.assert_not_called()

    def test_main_read_only_git_local_flag_reports_json_failure_status(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
            stdout = io.StringIO()
            report = {
                "projectRoot": str(Path(base).resolve()),
                "ok": False,
                "rev": "badrev",
                "path": ".",
                "output": {"text": "", "chars": 0, "lines": 0, "truncated": False, "maxOutputChars": 12000},
                "message": "git show failed.",
            }

            with (
                patch("vibeagent.cli.create_chat_client") as create_chat_client,
                patch("vibeagent.cli.get_show_report", return_value=report) as get_show_report,
                patch("vibeagent.cli.format_show_report_text", return_value="Show:\n  ok: no") as format_show_report_text,
                redirect_stdout(stdout),
            ):
                exit_code = main(["--json", "--cwd", base, "--show", "badrev"])

        self.assertEqual(exit_code, 1)
        payload = json.loads(stdout.getvalue())
        self.assertEqual(payload["kind"], "local")
        self.assertFalse(payload["success"])
        self.assertEqual(payload["status"], "failed")
        self.assertEqual(payload["text"], "Show:\n  ok: no")
        self.assertEqual(payload["show"], report)
        get_show_report.assert_called_once_with(Path(base).resolve(), rev="badrev", path=None, max_output_chars=12000)
        format_show_report_text.assert_called_once_with(report)
        create_chat_client.assert_not_called()

    def test_main_runs_env_local_flag_without_creating_client(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
            stdout = io.StringIO()

            with (
                patch("vibeagent.cli.create_chat_client") as create_chat_client,
                patch("vibeagent.cli.get_env_text", return_value="Environment:\n  tools: 3/9") as get_env_text,
                redirect_stdout(stdout),
            ):
                exit_code = main(["--cwd", base, "--env"])

        self.assertEqual(exit_code, 0)
        self.assertIn("Environment:", stdout.getvalue())
        get_env_text.assert_called_once_with(Path(base).resolve())
        create_chat_client.assert_not_called()

    def test_main_runs_env_local_flag_as_json_without_creating_client(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
            stdout = io.StringIO()
            report = {
                "projectRoot": str(Path(base).resolve()),
                "ok": True,
                "platform": "linux",
                "pythonVersion": "3.11",
                "pythonExecutable": "/usr/bin/python3",
                "gitRepo": False,
                "tools": {"available": 2, "total": 2, "items": []},
                "message": "Environment inspected.",
            }
            rendered = "Environment:\n  tools: 2/2"

            with (
                patch("vibeagent.cli.create_chat_client") as create_chat_client,
                patch("vibeagent.cli.get_env_report", return_value=report) as get_env_report,
                patch("vibeagent.cli.format_env_report_text", return_value=rendered) as format_env_report_text,
                redirect_stdout(stdout),
            ):
                exit_code = main(["--json", "--cwd", base, "--env"])

        payload = json.loads(stdout.getvalue())
        self.assertEqual(exit_code, 0)
        self.assertTrue(payload["success"])
        self.assertEqual(payload["status"], "completed")
        self.assertEqual(payload["text"], rendered)
        self.assertEqual(payload["env"], report)
        get_env_report.assert_called_once_with(Path(base).resolve())
        format_env_report_text.assert_called_once_with(report)
        create_chat_client.assert_not_called()

    def test_main_runs_processes_local_flag_without_creating_client(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
            stdout = io.StringIO()

            with (
                patch("vibeagent.cli.create_chat_client") as create_chat_client,
                patch("vibeagent.cli.get_processes_text", return_value="Processes:\n  processes: 0") as get_processes_text,
                redirect_stdout(stdout),
            ):
                exit_code = main(["--cwd", base, "--processes"])

        self.assertEqual(exit_code, 0)
        self.assertIn("Processes:", stdout.getvalue())
        get_processes_text.assert_called_once_with(Path(base).resolve())
        create_chat_client.assert_not_called()

    def test_main_processes_local_flag_exits_nonzero_for_failed_process_state(self) -> None:
        cases = [
            ("Processes:\n  processes: 1\n  running: 0\n  items:\n    - bg-1: pid=123; status=exited(7); cwd=.; command=pytest", 1),
            ("Processes:\n  processes: 1\n  running: 0\n  items:\n    - bg-1: pid=123; status=signaled(SIGTERM); cwd=.; command=server", 1),
            ("Processes:\n  processes: 1\n  running: 0\n  items:\n    - bg-1: pid=123; status=exited(0); cwd=.; command=pytest", 0),
            ("Processes:\n  processes: 1\n  running: 1\n  items:\n    - bg-1: pid=123; status=running; cwd=.; command=server", 0),
        ]

        for text, expected_exit_code in cases:
            with self.subTest(text=text), tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
                stdout = io.StringIO()

                with (
                    patch("vibeagent.cli.create_chat_client") as create_chat_client,
                    patch("vibeagent.cli.get_processes_text", return_value=text),
                    redirect_stdout(stdout),
                ):
                    exit_code = main(["--cwd", base, "--processes"])

            self.assertEqual(exit_code, expected_exit_code)
            self.assertEqual(stdout.getvalue(), f"{text}\n")
            create_chat_client.assert_not_called()

    def test_main_processes_json_outputs_structured_payload(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
            stdout = io.StringIO()
            report = {
                "projectRoot": str(Path(base).resolve()),
                "processes": {
                    "total": 1,
                    "running": 1,
                    "items": [
                        {
                            "processId": "bg-1",
                            "pid": 1234,
                            "command": "npm run dev",
                            "cwd": ".",
                            "running": True,
                            "exitCode": None,
                            "signal": None,
                            "status": "running",
                        }
                    ],
                },
                "message": "Found 1 background process(es).",
            }

            with (
                patch("vibeagent.cli.create_chat_client") as create_chat_client,
                patch("vibeagent.cli.get_processes_report", return_value=report) as get_processes_report,
                patch("vibeagent.cli.format_processes_report_text", return_value="Processes:\n  processes: 1\n  running: 1") as format_processes_report,
                redirect_stdout(stdout),
            ):
                exit_code = main(["--json", "--cwd", base, "--processes"])

        payload = json.loads(stdout.getvalue())
        self.assertEqual(exit_code, 0)
        self.assertEqual(payload["kind"], "local")
        self.assertTrue(payload["success"])
        self.assertEqual(payload["processes"], report)
        get_processes_report.assert_called_once_with(Path(base).resolve())
        format_processes_report.assert_called_once_with(report)
        create_chat_client.assert_not_called()

    def test_main_runs_process_output_local_flag_without_creating_client(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
            stdout = io.StringIO()

            with (
                patch("vibeagent.cli.create_chat_client") as create_chat_client,
                patch("vibeagent.cli.get_process_text", return_value="Process:\n  ok: no") as get_process_text,
                redirect_stdout(stdout),
            ):
                exit_code = main(["--cwd", base, "--process-output", "bg-1", "--process-max-chars", "2000"])

        self.assertEqual(exit_code, 1)
        self.assertIn("Process:", stdout.getvalue())
        get_process_text.assert_called_once_with(Path(base).resolve(), process_id="bg-1", max_output_chars=2000)
        create_chat_client.assert_not_called()

    def test_main_process_output_local_flag_exits_nonzero_for_failed_process_state(self) -> None:
        cases = [
            ("Process:\n  ok: yes\n  status: exited(7)", 1),
            ("Process:\n  ok: yes\n  status: signaled(SIGTERM)", 1),
            ("Process:\n  ok: yes\n  status: exited(0)", 0),
            ("Process:\n  ok: yes\n  status: running", 0),
        ]

        for text, expected_exit_code in cases:
            with self.subTest(text=text), tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
                stdout = io.StringIO()

                with (
                    patch("vibeagent.cli.create_chat_client") as create_chat_client,
                    patch("vibeagent.cli.get_process_text", return_value=text),
                    redirect_stdout(stdout),
                ):
                    exit_code = main(["--cwd", base, "--process-output", "bg-1"])

            self.assertEqual(exit_code, expected_exit_code)
            self.assertEqual(stdout.getvalue(), f"{text}\n")
            create_chat_client.assert_not_called()

    def test_main_process_output_json_outputs_structured_payload(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
            stdout = io.StringIO()
            report = {
                "projectRoot": str(Path(base).resolve()),
                "ok": True,
                "processId": "bg-1",
                "pid": 1234,
                "status": "running",
                "running": True,
                "exitCode": None,
                "signal": None,
                "maxOutputChars": 2000,
                "stdout": "ready\n",
                "stderr": "",
                "analysis": {"diagnostics": {"shown": 0, "total": 0, "items": []}, "diagnosticsTruncated": False, "contexts": {"shown": 0, "totalRefs": 0, "items": []}, "contextsTruncated": False},
                "message": "Process bg-1 is running.",
            }

            with (
                patch("vibeagent.cli.create_chat_client") as create_chat_client,
                patch("vibeagent.cli.get_process_report", return_value=report) as get_process_report,
                patch("vibeagent.cli.format_process_report_text", return_value="Process:\n  ok: yes\n  status: running") as format_process_report,
                redirect_stdout(stdout),
            ):
                exit_code = main(["--json", "--cwd", base, "--process-output", "bg-1", "--process-max-chars", "2000"])

        payload = json.loads(stdout.getvalue())
        self.assertEqual(exit_code, 0)
        self.assertEqual(payload["process"], report)
        get_process_report.assert_called_once_with(Path(base).resolve(), process_id="bg-1", max_output_chars=2000)
        format_process_report.assert_called_once_with(report)
        create_chat_client.assert_not_called()

    def test_main_runs_process_output_contexts_local_flag_without_creating_client(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
            stdout = io.StringIO()

            with (
                patch("vibeagent.cli.create_chat_client") as create_chat_client,
                patch("vibeagent.cli.get_process_output_contexts_text", return_value="Process output contexts:\n  contexts: 1/1") as get_process_output_contexts_text,
                redirect_stdout(stdout),
            ):
                exit_code = main(
                    [
                        "--cwd",
                        base,
                        "--process-output-contexts",
                        "bg-1",
                        "--process-max-chars",
                        "2000",
                        "--process-output-context-lines",
                        "2",
                        "--process-output-context-max",
                        "5",
                        "--process-output-context-max-bytes",
                        "1000",
                    ]
                )

        self.assertEqual(exit_code, 0)
        self.assertIn("Process output contexts:", stdout.getvalue())
        get_process_output_contexts_text.assert_called_once_with(
            Path(base).resolve(),
            process_id="bg-1",
            max_output_chars=2000,
            context_lines=2,
            max_contexts=5,
            max_bytes_per_context=1000,
        )
        create_chat_client.assert_not_called()

    def test_main_runs_process_output_diagnostics_local_flag_without_creating_client(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
            stdout = io.StringIO()

            with (
                patch("vibeagent.cli.create_chat_client") as create_chat_client,
                patch("vibeagent.cli.get_process_output_diagnostics_text", return_value="Process output diagnostics:\n  diagnostics: 1/1") as get_process_output_diagnostics_text,
                redirect_stdout(stdout),
            ):
                exit_code = main(
                    [
                        "--cwd",
                        base,
                        "--process-output-diagnostics",
                        "bg-1",
                        "--process-max-chars",
                        "2000",
                        "--process-output-context-lines",
                        "2",
                        "--process-output-diagnostic-max",
                        "7",
                        "--process-output-context-max",
                        "5",
                        "--process-output-context-max-bytes",
                        "1000",
                    ]
                )

        self.assertEqual(exit_code, 0)
        self.assertIn("Process output diagnostics:", stdout.getvalue())
        get_process_output_diagnostics_text.assert_called_once_with(
            Path(base).resolve(),
            process_id="bg-1",
            max_output_chars=2000,
            context_lines=2,
            max_diagnostics=7,
            max_contexts=5,
            max_bytes_per_context=1000,
        )
        create_chat_client.assert_not_called()

    def test_main_process_output_analysis_local_flags_exit_nonzero_for_failed_results(self) -> None:
        cases = [
            (
                [
                    "--process-output-contexts",
                    "missing-proc",
                    "--process-max-chars",
                    "2000",
                    "--process-output-context-lines",
                    "2",
                    "--process-output-context-max",
                    "5",
                    "--process-output-context-max-bytes",
                    "1000",
                ],
                "vibeagent.cli.get_process_output_contexts_text",
                "Process output contexts:\n  ok: no\n  message: Unknown background process id.",
            ),
            (
                [
                    "--process-output-diagnostics",
                    "bg-1",
                    "--process-max-chars",
                    "2000",
                    "--process-output-context-lines",
                    "2",
                    "--process-output-context-max",
                    "5",
                    "--process-output-context-max-bytes",
                    "1000",
                ],
                "vibeagent.cli.get_process_output_diagnostics_text",
                "Process output diagnostics:\n  diagnostics: 1/1\n  contexts: 0/1",
            ),
        ]

        for argv_tail, patch_target, text in cases:
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
            expected_kwargs = {
                "process_id": argv_tail[1],
                "max_output_chars": 2000,
                "context_lines": 2,
                "max_contexts": 5,
                "max_bytes_per_context": 1000,
            }
            if "diagnostics" in patch_target:
                expected_kwargs["max_diagnostics"] = 50
            getter.assert_called_once_with(Path(base).resolve(), **expected_kwargs)
            create_chat_client.assert_not_called()

    def test_main_process_output_analysis_local_flags_exit_nonzero_for_failed_process_state(self) -> None:
        cases = [
            (
                [
                    "--process-output-contexts",
                    "bg-1",
                    "--process-max-chars",
                    "2000",
                    "--process-output-context-lines",
                    "2",
                    "--process-output-context-max",
                    "5",
                    "--process-output-context-max-bytes",
                    "1000",
                ],
                "vibeagent.cli.get_process_output_contexts_text",
                "Process output contexts:\n  ok: yes\n  status: exited(7)\n  contexts: 1/1",
                1,
            ),
            (
                [
                    "--process-output-diagnostics",
                    "bg-1",
                    "--process-max-chars",
                    "2000",
                    "--process-output-context-lines",
                    "2",
                    "--process-output-context-max",
                    "5",
                    "--process-output-context-max-bytes",
                    "1000",
                ],
                "vibeagent.cli.get_process_output_diagnostics_text",
                "Process output diagnostics:\n  ok: yes\n  status: signaled(SIGTERM)\n  diagnostics: 1/1\n  contexts: 1/1",
                1,
            ),
            (
                [
                    "--process-output-contexts",
                    "bg-1",
                    "--process-max-chars",
                    "2000",
                    "--process-output-context-lines",
                    "2",
                    "--process-output-context-max",
                    "5",
                    "--process-output-context-max-bytes",
                    "1000",
                ],
                "vibeagent.cli.get_process_output_contexts_text",
                "Process output contexts:\n  ok: yes\n  status: exited(0)\n  contexts: 1/1",
                0,
            ),
            (
                [
                    "--process-output-diagnostics",
                    "bg-1",
                    "--process-max-chars",
                    "2000",
                    "--process-output-context-lines",
                    "2",
                    "--process-output-context-max",
                    "5",
                    "--process-output-context-max-bytes",
                    "1000",
                ],
                "vibeagent.cli.get_process_output_diagnostics_text",
                "Process output diagnostics:\n  ok: yes\n  status: running\n  diagnostics: 1/1\n  contexts: 1/1",
                0,
            ),
        ]

        for argv_tail, patch_target, text, expected_exit_code in cases:
            with self.subTest(argv=argv_tail, text=text), tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
                stdout = io.StringIO()

                with (
                    patch("vibeagent.cli.create_chat_client") as create_chat_client,
                    patch(patch_target, return_value=text) as getter,
                    redirect_stdout(stdout),
                ):
                    exit_code = main(["--cwd", base, *argv_tail])

            self.assertEqual(exit_code, expected_exit_code)
            self.assertEqual(stdout.getvalue(), f"{text}\n")
            expected_kwargs = {
                "process_id": "bg-1",
                "max_output_chars": 2000,
                "context_lines": 2,
                "max_contexts": 5,
                "max_bytes_per_context": 1000,
            }
            if "diagnostics" in patch_target:
                expected_kwargs["max_diagnostics"] = 50
            getter.assert_called_once_with(Path(base).resolve(), **expected_kwargs)
            create_chat_client.assert_not_called()

    def test_main_process_output_analysis_json_outputs_structured_payloads(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
            contexts_report = {
                "projectRoot": str(Path(base).resolve()),
                "ok": True,
                "processId": "bg-1",
                "pid": 1234,
                "status": "running",
                "contexts": {"ok": 1, "total": 1, "items": [{"path": "src/app.py", "line": 2, "content": "2: print('ok')"}]},
                "totalRefs": 1,
                "maxOutputChars": 2000,
                "stdoutChars": 24,
                "stderrChars": 0,
                "truncated": False,
                "message": "Extracted 1/1 output context(s) from process bg-1.",
            }
            diagnostics_report = {
                "projectRoot": str(Path(base).resolve()),
                "ok": True,
                "processId": "bg-1",
                "pid": 1234,
                "status": "running",
                "diagnostics": {"shown": 1, "total": 1, "items": [{"severity": "error", "outputLine": 1, "path": "src/app.py"}]},
                "contexts": {"ok": 1, "total": 1, "items": [{"path": "src/app.py", "line": 2, "content": "2: print('ok')"}]},
                "totalRefs": 1,
                "maxOutputChars": 2000,
                "stdoutChars": 32,
                "stderrChars": 0,
                "contextLines": 2,
                "maxDiagnostics": 7,
                "maxContexts": 5,
                "maxBytesPerContext": 1000,
                "diagnosticsTruncated": False,
                "contextsTruncated": False,
                "message": "Extracted 1/1 diagnostic(s) and 1/1 source context(s) from process bg-1.",
            }
            stdout = io.StringIO()

            with (
                patch("vibeagent.cli.create_chat_client") as create_chat_client,
                patch("vibeagent.cli.get_process_output_contexts_report", return_value=contexts_report) as get_contexts_report,
                patch(
                    "vibeagent.cli.format_process_output_contexts_report_text",
                    return_value="Process output contexts:\n  contexts: 1/1",
                ) as format_contexts_report,
                redirect_stdout(stdout),
            ):
                contexts_exit = main(
                    [
                        "--json",
                        "--cwd",
                        base,
                        "--process-output-contexts",
                        "bg-1",
                        "--process-max-chars",
                        "2000",
                        "--process-output-context-lines",
                        "2",
                        "--process-output-context-max",
                        "5",
                        "--process-output-context-max-bytes",
                        "1000",
                    ]
                )
            contexts_payload = json.loads(stdout.getvalue())
            stdout = io.StringIO()
            with (
                patch("vibeagent.cli.create_chat_client") as create_chat_client_diagnostics,
                patch("vibeagent.cli.get_process_output_diagnostics_report", return_value=diagnostics_report) as get_diagnostics_report,
                patch(
                    "vibeagent.cli.format_process_output_diagnostics_report_text",
                    return_value="Process output diagnostics:\n  diagnostics: 1/1\n  contexts: 1/1",
                ) as format_diagnostics_report,
                redirect_stdout(stdout),
            ):
                diagnostics_exit = main(
                    [
                        "--json",
                        "--cwd",
                        base,
                        "--process-output-diagnostics",
                        "bg-1",
                        "--process-max-chars",
                        "2000",
                        "--process-output-context-lines",
                        "2",
                        "--process-output-diagnostic-max",
                        "7",
                        "--process-output-context-max",
                        "5",
                        "--process-output-context-max-bytes",
                        "1000",
                    ]
                )
            diagnostics_payload = json.loads(stdout.getvalue())

        self.assertEqual(contexts_exit, 0)
        self.assertEqual(contexts_payload["processOutputContexts"], contexts_report)
        get_contexts_report.assert_called_once_with(
            Path(base).resolve(),
            process_id="bg-1",
            max_output_chars=2000,
            context_lines=2,
            max_contexts=5,
            max_bytes_per_context=1000,
        )
        format_contexts_report.assert_called_once_with(contexts_report)
        create_chat_client.assert_not_called()
        self.assertEqual(diagnostics_exit, 0)
        self.assertEqual(diagnostics_payload["processOutputDiagnostics"], diagnostics_report)
        get_diagnostics_report.assert_called_once_with(
            Path(base).resolve(),
            process_id="bg-1",
            max_output_chars=2000,
            context_lines=2,
            max_diagnostics=7,
            max_contexts=5,
            max_bytes_per_context=1000,
        )
        format_diagnostics_report.assert_called_once_with(diagnostics_report)
        create_chat_client_diagnostics.assert_not_called()

    def test_main_process_output_analysis_local_flag_reports_json_failure_status(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
            stdout = io.StringIO()
            report = {
                "projectRoot": str(Path(base).resolve()),
                "ok": False,
                "processId": "missing-proc",
                "pid": None,
                "status": "unknown",
                "contexts": {"ok": 0, "total": 0, "items": []},
                "totalRefs": 0,
                "maxOutputChars": 4000,
                "stdoutChars": 0,
                "stderrChars": 0,
                "truncated": False,
                "message": "Unknown background process id.",
            }

            with (
                patch("vibeagent.cli.create_chat_client") as create_chat_client,
                patch("vibeagent.cli.get_process_output_contexts_report", return_value=report) as get_process_output_contexts_report,
                patch(
                    "vibeagent.cli.format_process_output_contexts_report_text",
                    return_value="Process output contexts:\n  ok: no",
                ) as format_process_output_contexts_report_text,
                redirect_stdout(stdout),
            ):
                exit_code = main(["--json", "--cwd", base, "--process-output-contexts", "missing-proc"])

        self.assertEqual(exit_code, 1)
        payload = json.loads(stdout.getvalue())
        self.assertEqual(payload["kind"], "local")
        self.assertFalse(payload["success"])
        self.assertEqual(payload["status"], "failed")
        self.assertEqual(payload["text"], "Process output contexts:\n  ok: no")
        self.assertEqual(payload["processOutputContexts"], report)
        get_process_output_contexts_report.assert_called_once_with(
            Path(base).resolve(),
            process_id="missing-proc",
            max_output_chars=None,
            context_lines=5,
            max_contexts=20,
            max_bytes_per_context=20000,
        )
        format_process_output_contexts_report_text.assert_called_once_with(report)
        create_chat_client.assert_not_called()

    def test_main_runs_wait_process_local_flag_without_creating_client(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
            stdout = io.StringIO()

            with (
                patch("vibeagent.cli.create_chat_client") as create_chat_client,
                patch("vibeagent.cli.get_wait_process_text", return_value="Wait process:\n  ok: no") as get_wait_process_text,
                redirect_stdout(stdout),
            ):
                exit_code = main(
                    [
                        "--cwd",
                        base,
                        "--wait-process",
                        "bg-1",
                        "--wait-timeout-ms",
                        "2000",
                        "--wait-max-chars",
                        "3000",
                        "--wait-stdout",
                        "ready",
                        "--wait-regex",
                    ]
                )

        self.assertEqual(exit_code, 1)
        self.assertIn("Wait process:", stdout.getvalue())
        get_wait_process_text.assert_called_once_with(
            Path(base).resolve(),
            process_id="bg-1",
            timeout_ms=2000,
            max_output_chars=3000,
            stdout_contains="ready",
            stderr_contains=None,
            regex=True,
        )
        create_chat_client.assert_not_called()

    def test_main_runs_wait_process_local_flag_inherits_process_output_limit(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
            stdout = io.StringIO()

            with (
                patch("vibeagent.cli.create_chat_client") as create_chat_client,
                patch("vibeagent.cli.get_wait_process_text", return_value="Wait process:\n  ok: no") as get_wait_process_text,
                redirect_stdout(stdout),
            ):
                exit_code = main(["--cwd", base, "--wait-process", "bg-1"])

        self.assertEqual(exit_code, 1)
        self.assertIn("Wait process:", stdout.getvalue())
        get_wait_process_text.assert_called_once_with(
            Path(base).resolve(),
            process_id="bg-1",
            timeout_ms=5000,
            max_output_chars=None,
            stdout_contains=None,
            stderr_contains=None,
            regex=False,
        )
        create_chat_client.assert_not_called()

    def test_main_wait_process_json_outputs_structured_payload(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
            stdout = io.StringIO()
            report = {
                "projectRoot": str(Path(base).resolve()),
                "ok": True,
                "processId": "bg-1",
                "pid": 1234,
                "status": "running",
                "running": True,
                "timedOut": False,
                "matched": True,
                "matchedStream": "stdout",
                "matchedPattern": "ready",
                "timeoutMs": 5000,
                "exitCode": None,
                "signal": None,
                "maxOutputChars": 2000,
                "stdout": "ready\n",
                "stderr": "",
                "analysis": {"diagnostics": {"shown": 0, "total": 0, "items": []}, "diagnosticsTruncated": False, "contexts": {"shown": 0, "totalRefs": 0, "items": []}, "contextsTruncated": False},
                "message": "Matched stdout pattern.",
            }

            with (
                patch("vibeagent.cli.create_chat_client") as create_chat_client,
                patch("vibeagent.cli.get_wait_process_report", return_value=report) as get_wait_process_report,
                patch("vibeagent.cli.format_wait_process_report_text", return_value="Wait process:\n  matched: yes") as format_wait_process_report,
                redirect_stdout(stdout),
            ):
                exit_code = main(
                    [
                        "--json",
                        "--cwd",
                        base,
                        "--wait-process",
                        "bg-1",
                        "--wait-timeout-ms",
                        "5000",
                        "--wait-max-chars",
                        "2000",
                        "--wait-stdout",
                        "ready",
                    ]
                )

        payload = json.loads(stdout.getvalue())
        self.assertEqual(exit_code, 0)
        self.assertEqual(payload["waitProcess"], report)
        get_wait_process_report.assert_called_once_with(
            Path(base).resolve(),
            process_id="bg-1",
            timeout_ms=5000,
            max_output_chars=2000,
            stdout_contains="ready",
            stderr_contains=None,
            regex=False,
        )
        format_wait_process_report.assert_called_once_with(report)
        create_chat_client.assert_not_called()

    def test_main_wait_process_local_flag_exits_nonzero_for_failed_process_state(self) -> None:
        cases = [
            ("Wait process:\n  ok: yes\n  status: exited(7)\n  timedOut: no", 1),
            ("Wait process:\n  ok: yes\n  status: running\n  timedOut: yes", 1),
            ("Wait process:\n  ok: yes\n  status: signaled(SIGTERM)\n  timedOut: no", 1),
            ("Wait process:\n  ok: yes\n  status: exited(0)\n  timedOut: no", 0),
        ]

        for text, expected_exit_code in cases:
            with self.subTest(text=text), tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
                stdout = io.StringIO()

                with (
                    patch("vibeagent.cli.create_chat_client") as create_chat_client,
                    patch("vibeagent.cli.get_wait_process_text", return_value=text),
                    redirect_stdout(stdout),
                ):
                    exit_code = main(["--cwd", base, "--wait-process", "bg-1"])

            self.assertEqual(exit_code, expected_exit_code)
            self.assertEqual(stdout.getvalue(), f"{text}\n")
            create_chat_client.assert_not_called()

    def test_main_runs_write_process_local_flag_without_creating_client(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
            stdout = io.StringIO()

            with (
                patch("vibeagent.cli.create_chat_client") as create_chat_client,
                patch("vibeagent.cli.get_write_process_text", return_value="Write process:\n  ok: no") as get_write_process_text,
                redirect_stdout(stdout),
            ):
                exit_code = main(["--cwd", base, "--write-process", "bg-1", "--write-stdin", "hello\\n"])

        self.assertEqual(exit_code, 1)
        self.assertIn("Write process:", stdout.getvalue())
        get_write_process_text.assert_called_once_with(Path(base).resolve(), process_id="bg-1", content="hello\\n")
        create_chat_client.assert_not_called()

    def test_main_runs_check_write_process_local_flag_without_creating_client(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
            stdout = io.StringIO()

            with (
                patch("vibeagent.cli.create_chat_client") as create_chat_client,
                patch("vibeagent.cli.get_check_write_process_text", return_value="Check write process:\n  ok: yes") as get_check_write_process_text,
                redirect_stdout(stdout),
            ):
                exit_code = main(["--cwd", base, "--check-write-process", "bg-1", "--write-stdin", "hello\\n"])

        self.assertEqual(exit_code, 0)
        self.assertIn("Check write process:", stdout.getvalue())
        get_check_write_process_text.assert_called_once_with(Path(base).resolve(), process_id="bg-1", content="hello\\n")
        create_chat_client.assert_not_called()

    def test_main_write_process_json_outputs_structured_payloads(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
            check_stdout = io.StringIO()
            check_report = {
                "projectRoot": str(Path(base).resolve()),
                "ok": True,
                "processId": "bg-1",
                "pid": 123,
                "running": True,
                "command": "python3 repl.py",
                "cwd": ".",
                "contentChars": 6,
                "message": "Can write 6 character(s) to process bg-1.",
            }

            with (
                patch("vibeagent.cli.create_chat_client") as create_chat_client,
                patch("vibeagent.cli.get_check_write_process_report", return_value=check_report) as get_check_write_process_report,
                patch("vibeagent.cli.format_check_write_process_report_text", return_value="Check write process:\n  ok: yes") as format_check_write_process_report,
                redirect_stdout(check_stdout),
            ):
                check_exit = main(["--json", "--cwd", base, "--check-write-process", "bg-1", "--write-stdin", "hello\\n"])

            write_stdout = io.StringIO()
            write_report = {
                "projectRoot": str(Path(base).resolve()),
                "ok": False,
                "processId": "missing",
                "pid": None,
                "running": False,
                "command": "",
                "cwd": "",
                "contentChars": 6,
                "message": "Unknown background process id.",
            }
            with (
                patch("vibeagent.cli.create_chat_client") as create_chat_client_write,
                patch("vibeagent.cli.get_write_process_report", return_value=write_report) as get_write_process_report,
                patch("vibeagent.cli.format_write_process_report_text", return_value="Write process:\n  ok: no") as format_write_process_report,
                redirect_stdout(write_stdout),
            ):
                write_exit = main(["--json", "--cwd", base, "--write-process", "missing", "--write-stdin", "hello\\n"])

        check_payload = json.loads(check_stdout.getvalue())
        write_payload = json.loads(write_stdout.getvalue())
        self.assertEqual(check_exit, 0)
        self.assertTrue(check_payload["success"])
        self.assertEqual(check_payload["checkWriteProcess"], check_report)
        get_check_write_process_report.assert_called_once_with(Path(base).resolve(), process_id="bg-1", content="hello\\n")
        format_check_write_process_report.assert_called_once_with(check_report)
        create_chat_client.assert_not_called()
        self.assertEqual(write_exit, 1)
        self.assertFalse(write_payload["success"])
        self.assertEqual(write_payload["status"], "failed")
        self.assertEqual(write_payload["writeProcess"], write_report)
        get_write_process_report.assert_called_once_with(Path(base).resolve(), process_id="missing", content="hello\\n")
        format_write_process_report.assert_called_once_with(write_report)
        create_chat_client_write.assert_not_called()

    def test_main_runs_stop_process_local_flag_without_creating_client(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
            stdout = io.StringIO()

            with (
                patch("vibeagent.cli.create_chat_client") as create_chat_client,
                patch("vibeagent.cli.get_check_stop_process_text", return_value="Check stop process:\n  ok: yes") as get_check_stop_process_text,
                redirect_stdout(stdout),
            ):
                exit_code = main(["--cwd", base, "--check-stop-process", "bg-1"])

        self.assertEqual(exit_code, 0)
        self.assertIn("Check stop process:", stdout.getvalue())
        get_check_stop_process_text.assert_called_once_with(Path(base).resolve(), "bg-1")
        create_chat_client.assert_not_called()

        with tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
            stdout = io.StringIO()

            with (
                patch("vibeagent.cli.create_chat_client") as create_chat_client,
                patch("vibeagent.cli.get_stop_process_text", return_value="Stop process:\n  ok: no") as get_stop_process_text,
                redirect_stdout(stdout),
            ):
                exit_code = main(["--cwd", base, "--stop-process", "bg-1"])

        self.assertEqual(exit_code, 1)
        self.assertIn("Stop process:", stdout.getvalue())
        get_stop_process_text.assert_called_once_with(Path(base).resolve(), "bg-1")
        create_chat_client.assert_not_called()

    def test_main_stop_process_json_outputs_structured_payloads(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
            check_stdout = io.StringIO()
            check_report = {
                "projectRoot": str(Path(base).resolve()),
                "ok": True,
                "processId": "bg-1",
                "pid": 123,
                "command": "npm run dev",
                "cwd": "web",
                "running": True,
                "exitCode": None,
                "signal": None,
                "status": "running",
                "message": "Process bg-1 is running and can be stopped.",
            }

            with (
                patch("vibeagent.cli.create_chat_client") as create_chat_client,
                patch("vibeagent.cli.get_check_stop_process_report", return_value=check_report) as get_check_stop_process_report,
                patch("vibeagent.cli.format_check_stop_process_report_text", return_value="Check stop process:\n  ok: yes") as format_check_stop_process_report,
                redirect_stdout(check_stdout),
            ):
                check_exit = main(["--json", "--cwd", base, "--check-stop-process", "bg-1"])

            stop_stdout = io.StringIO()
            stop_report = {
                "projectRoot": str(Path(base).resolve()),
                "ok": False,
                "processId": "missing",
                "pid": None,
                "exitCode": None,
                "signal": None,
                "result": "unknown",
                "message": "Unknown background process id.",
            }
            with (
                patch("vibeagent.cli.create_chat_client") as create_chat_client_stop,
                patch("vibeagent.cli.get_stop_process_report", return_value=stop_report) as get_stop_process_report,
                patch("vibeagent.cli.format_stop_process_report_text", return_value="Stop process:\n  ok: no") as format_stop_process_report,
                redirect_stdout(stop_stdout),
            ):
                stop_exit = main(["--json", "--cwd", base, "--stop-process", "missing"])

        check_payload = json.loads(check_stdout.getvalue())
        stop_payload = json.loads(stop_stdout.getvalue())
        self.assertEqual(check_exit, 0)
        self.assertTrue(check_payload["success"])
        self.assertEqual(check_payload["checkStopProcess"], check_report)
        get_check_stop_process_report.assert_called_once_with(Path(base).resolve(), "bg-1")
        format_check_stop_process_report.assert_called_once_with(check_report)
        create_chat_client.assert_not_called()
        self.assertEqual(stop_exit, 1)
        self.assertFalse(stop_payload["success"])
        self.assertEqual(stop_payload["status"], "failed")
        self.assertEqual(stop_payload["stopProcess"], stop_report)
        get_stop_process_report.assert_called_once_with(Path(base).resolve(), "missing")
        format_stop_process_report.assert_called_once_with(stop_report)
        create_chat_client_stop.assert_not_called()

    def test_main_runs_stop_all_processes_local_flag_without_creating_client(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
            stdout = io.StringIO()

            with (
                patch("vibeagent.cli.create_chat_client") as create_chat_client,
                patch("vibeagent.cli.get_check_stop_all_processes_text", return_value="Check stop processes:\n  processes: 1") as get_check_stop_all_processes_text,
                redirect_stdout(stdout),
            ):
                exit_code = main(["--cwd", base, "--check-stop-all-processes"])

        self.assertEqual(exit_code, 0)
        self.assertIn("Check stop processes:", stdout.getvalue())
        get_check_stop_all_processes_text.assert_called_once_with(Path(base).resolve())
        create_chat_client.assert_not_called()

        with tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
            stdout = io.StringIO()

            with (
                patch("vibeagent.cli.create_chat_client") as create_chat_client,
                patch("vibeagent.cli.get_stop_all_processes_text", return_value="Stop processes:\n  stopped: 1") as get_stop_all_processes_text,
                redirect_stdout(stdout),
            ):
                exit_code = main(["--cwd", base, "--stop-all-processes"])

        self.assertEqual(exit_code, 0)
        self.assertIn("Stop processes:", stdout.getvalue())
        get_stop_all_processes_text.assert_called_once_with(Path(base).resolve())
        create_chat_client.assert_not_called()

    def test_main_stop_all_processes_json_outputs_structured_payloads(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
            check_stdout = io.StringIO()
            check_report = {
                "projectRoot": str(Path(base).resolve()),
                "ok": True,
                "processes": {
                    "total": 1,
                    "running": 1,
                    "items": [
                        {
                            "processId": "bg-1",
                            "pid": 123,
                            "command": "npm run dev",
                            "cwd": "web",
                            "running": True,
                            "exitCode": None,
                            "signal": None,
                            "status": "running",
                        }
                    ],
                },
                "message": "stop_all_processes would stop 1 background process(es), 1 still running.",
            }

            with (
                patch("vibeagent.cli.create_chat_client") as create_chat_client,
                patch("vibeagent.cli.get_check_stop_all_processes_report", return_value=check_report) as get_check_stop_all_processes_report,
                patch("vibeagent.cli.format_check_stop_all_processes_report_text", return_value="Check stop processes:\n  processes: 1") as format_check_stop_all_processes_report,
                redirect_stdout(check_stdout),
            ):
                check_exit = main(["--json", "--cwd", base, "--check-stop-all-processes"])

            stop_stdout = io.StringIO()
            stop_report = {
                "projectRoot": str(Path(base).resolve()),
                "ok": True,
                "stopped": {
                    "total": 1,
                    "items": [
                        {
                            "processId": "bg-1",
                            "pid": 123,
                            "command": "npm run dev",
                            "cwd": "web",
                            "ok": True,
                            "exitCode": -15,
                            "signal": "SIGTERM",
                            "result": "signaled(SIGTERM)",
                            "message": "Stopped process bg-1.",
                        }
                    ],
                },
                "message": "Stopped 1 background process(es).",
            }
            with (
                patch("vibeagent.cli.create_chat_client") as create_chat_client_stop,
                patch("vibeagent.cli.get_stop_all_processes_report", return_value=stop_report) as get_stop_all_processes_report,
                patch("vibeagent.cli.format_stop_all_processes_report_text", return_value="Stop processes:\n  stopped: 1") as format_stop_all_processes_report,
                redirect_stdout(stop_stdout),
            ):
                stop_exit = main(["--json", "--cwd", base, "--stop-all-processes"])

        check_payload = json.loads(check_stdout.getvalue())
        stop_payload = json.loads(stop_stdout.getvalue())
        self.assertEqual(check_exit, 0)
        self.assertTrue(check_payload["success"])
        self.assertEqual(check_payload["checkStopAllProcesses"], check_report)
        get_check_stop_all_processes_report.assert_called_once_with(Path(base).resolve())
        format_check_stop_all_processes_report.assert_called_once_with(check_report)
        create_chat_client.assert_not_called()
        self.assertEqual(stop_exit, 0)
        self.assertTrue(stop_payload["success"])
        self.assertEqual(stop_payload["stopAllProcesses"], stop_report)
        get_stop_all_processes_report.assert_called_once_with(Path(base).resolve())
        format_stop_all_processes_report.assert_called_once_with(stop_report)
        create_chat_client_stop.assert_not_called()

    def test_main_runs_git_stage_local_flags_without_creating_client(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
            stdout = io.StringIO()

            with (
                patch("vibeagent.cli.create_chat_client") as create_chat_client,
                patch("vibeagent.cli.get_check_stage_text", return_value="Check stage:\n  ok: yes") as get_check_stage_text,
                redirect_stdout(stdout),
            ):
                exit_code = main(["--cwd", base, "--check-git-stage", "app.py", "tests/test_app.py"])

        self.assertEqual(exit_code, 0)
        self.assertIn("Check stage:", stdout.getvalue())
        get_check_stage_text.assert_called_once_with(Path(base).resolve(), ["app.py", "tests/test_app.py"])
        create_chat_client.assert_not_called()

        with tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
            stdout = io.StringIO()

            with (
                patch("vibeagent.cli.create_chat_client") as create_chat_client,
                patch("vibeagent.cli.get_stage_text", return_value="Stage:\n  ok: yes") as get_stage_text,
                redirect_stdout(stdout),
            ):
                exit_code = main(["--cwd", base, "--git-stage", "app.py"])

        self.assertEqual(exit_code, 0)
        self.assertIn("Stage:", stdout.getvalue())
        get_stage_text.assert_called_once_with(Path(base).resolve(), ["app.py"])
        create_chat_client.assert_not_called()

    def test_main_runs_git_unstage_local_flags_without_creating_client(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
            stdout = io.StringIO()

            with (
                patch("vibeagent.cli.create_chat_client") as create_chat_client,
                patch("vibeagent.cli.get_check_unstage_text", return_value="Check unstage:\n  ok: yes") as get_check_unstage_text,
                redirect_stdout(stdout),
            ):
                exit_code = main(["--cwd", base, "--check-git-unstage", "app.py", "tests/test_app.py"])

        self.assertEqual(exit_code, 0)
        self.assertIn("Check unstage:", stdout.getvalue())
        get_check_unstage_text.assert_called_once_with(Path(base).resolve(), ["app.py", "tests/test_app.py"])
        create_chat_client.assert_not_called()

        with tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
            stdout = io.StringIO()

            with (
                patch("vibeagent.cli.create_chat_client") as create_chat_client,
                patch("vibeagent.cli.get_unstage_text", return_value="Unstage:\n  ok: yes") as get_unstage_text,
                redirect_stdout(stdout),
            ):
                exit_code = main(["--cwd", base, "--git-unstage", "app.py"])

        self.assertEqual(exit_code, 0)
        self.assertIn("Unstage:", stdout.getvalue())
        get_unstage_text.assert_called_once_with(Path(base).resolve(), ["app.py"])
        create_chat_client.assert_not_called()

    def test_main_check_git_stage_local_flag_exits_nonzero_when_not_ok(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
            stdout = io.StringIO()

            with (
                patch("vibeagent.cli.create_chat_client") as create_chat_client,
                patch("vibeagent.cli.get_check_stage_text", return_value="Check stage:\n  ok: no\n  message: git status failed"),
                redirect_stdout(stdout),
            ):
                exit_code = main(["--cwd", base, "--check-git-stage", "app.py"])

        self.assertEqual(exit_code, 1)
        self.assertIn("Check stage:", stdout.getvalue())
        self.assertIn("ok: no", stdout.getvalue())
        create_chat_client.assert_not_called()

    def test_main_runs_git_commit_local_flags_without_creating_client(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
            stdout = io.StringIO()

            with (
                patch("vibeagent.cli.create_chat_client") as create_chat_client,
                patch("vibeagent.cli.get_check_commit_text", return_value="Check commit:\n  ok: yes") as get_check_commit_text,
                redirect_stdout(stdout),
            ):
                exit_code = main(["--cwd", base, "--check-git-commit", "update app"])

        self.assertEqual(exit_code, 0)
        self.assertIn("Check commit:", stdout.getvalue())
        get_check_commit_text.assert_called_once_with(Path(base).resolve(), "update app")
        create_chat_client.assert_not_called()

        with tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
            stdout = io.StringIO()

            with (
                patch("vibeagent.cli.create_chat_client") as create_chat_client,
                patch("vibeagent.cli.get_commit_text", return_value="Commit:\n  ok: yes") as get_commit_text,
                redirect_stdout(stdout),
            ):
                exit_code = main(["--cwd", base, "--git-commit", "update app"])

        self.assertEqual(exit_code, 0)
        self.assertIn("Commit:", stdout.getvalue())
        get_commit_text.assert_called_once_with(Path(base).resolve(), "update app")
        create_chat_client.assert_not_called()

    def test_main_runs_git_restore_local_flags_without_creating_client(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
            stdout = io.StringIO()

            with (
                patch("vibeagent.cli.create_chat_client") as create_chat_client,
                patch("vibeagent.cli.get_check_restore_text", return_value="Check restore:\n  ok: yes") as get_check_restore_text,
                redirect_stdout(stdout),
            ):
                exit_code = main(["--cwd", base, "--check-git-restore", "app.py", "tests/test_app.py"])

        self.assertEqual(exit_code, 0)
        self.assertIn("Check restore:", stdout.getvalue())
        get_check_restore_text.assert_called_once_with(Path(base).resolve(), ["app.py", "tests/test_app.py"])
        create_chat_client.assert_not_called()

        with tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
            stdout = io.StringIO()

            with (
                patch("vibeagent.cli.create_chat_client") as create_chat_client,
                patch("vibeagent.cli.get_restore_text", return_value="Restore:\n  ok: yes") as get_restore_text,
                redirect_stdout(stdout),
            ):
                exit_code = main(["--cwd", base, "--git-restore", "app.py"])

        self.assertEqual(exit_code, 0)
        self.assertIn("Restore:", stdout.getvalue())
        get_restore_text.assert_called_once_with(Path(base).resolve(), ["app.py"])
        create_chat_client.assert_not_called()

    def test_main_runs_git_index_commit_restore_local_flags_as_json_without_creating_client(self) -> None:
        cases = [
            (
                ["--check-git-stage", "app.py", "tests/test_app.py"],
                "vibeagent.cli.get_check_stage_report",
                "vibeagent.cli.format_git_index_report_text",
                "Check stage",
                "checkGitStage",
                (["app.py", "tests/test_app.py"],),
            ),
            (
                ["--git-stage", "app.py"],
                "vibeagent.cli.get_stage_report",
                "vibeagent.cli.format_git_index_report_text",
                "Stage",
                "gitStage",
                (["app.py"],),
            ),
            (
                ["--check-git-unstage", "app.py", "tests/test_app.py"],
                "vibeagent.cli.get_check_unstage_report",
                "vibeagent.cli.format_git_index_report_text",
                "Check unstage",
                "checkGitUnstage",
                (["app.py", "tests/test_app.py"],),
            ),
            (
                ["--git-unstage", "app.py"],
                "vibeagent.cli.get_unstage_report",
                "vibeagent.cli.format_git_index_report_text",
                "Unstage",
                "gitUnstage",
                (["app.py"],),
            ),
            (
                ["--check-git-commit", "update app"],
                "vibeagent.cli.get_check_commit_report",
                "vibeagent.cli.format_git_commit_report_text",
                "Check commit",
                "checkGitCommit",
                ("update app",),
            ),
            (
                ["--git-commit", "update app"],
                "vibeagent.cli.get_commit_report",
                "vibeagent.cli.format_git_commit_report_text",
                "Commit",
                "gitCommit",
                ("update app",),
            ),
            (
                ["--check-git-restore", "app.py", "tests/test_app.py"],
                "vibeagent.cli.get_check_restore_report",
                "vibeagent.cli.format_git_restore_report_text",
                "Check restore",
                "checkGitRestore",
                (["app.py", "tests/test_app.py"],),
            ),
            (
                ["--git-restore", "app.py"],
                "vibeagent.cli.get_restore_report",
                "vibeagent.cli.format_git_restore_report_text",
                "Restore",
                "gitRestore",
                (["app.py"],),
            ),
        ]

        for argv_tail, getter_target, formatter_target, title, payload_key, expected_args in cases:
            with self.subTest(payload_key=payload_key), tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
                stdout = io.StringIO()
                report = {"ok": True, "message": payload_key}
                rendered = f"{title}:\n  ok: yes"

                with (
                    patch("vibeagent.cli.create_chat_client") as create_chat_client,
                    patch(getter_target, return_value=report) as getter,
                    patch(formatter_target, return_value=rendered) as formatter,
                    redirect_stdout(stdout),
                ):
                    exit_code = main(["--json", "--cwd", base, *argv_tail])

                payload = json.loads(stdout.getvalue())
                self.assertEqual(exit_code, 0)
                self.assertTrue(payload["success"])
                self.assertEqual(payload["status"], "completed")
                self.assertEqual(payload["text"], rendered)
                self.assertEqual(payload[payload_key], report)
                getter.assert_called_once_with(Path(base).resolve(), *expected_args)
                formatter.assert_called_once_with(title, report)
                create_chat_client.assert_not_called()

    def test_main_runs_git_remote_sync_switch_local_flags_as_json_without_creating_client(self) -> None:
        cases = [
            (
                ["--check-git-fetch", "origin"],
                "vibeagent.cli.get_check_fetch_report",
                "vibeagent.cli.format_git_fetch_report_text",
                "Check fetch",
                "checkGitFetch",
                ("origin",),
            ),
            (
                ["--git-fetch", "origin"],
                "vibeagent.cli.get_fetch_report",
                "vibeagent.cli.format_git_fetch_report_text",
                "Fetch",
                "gitFetch",
                ("origin",),
            ),
            (
                ["--check-git-pull"],
                "vibeagent.cli.get_check_pull_report",
                "vibeagent.cli.format_git_sync_preview_report_text",
                "Check pull",
                "checkGitPull",
                (),
            ),
            (
                ["--git-pull"],
                "vibeagent.cli.get_pull_report",
                "vibeagent.cli.format_git_pull_report_text",
                "Pull",
                "gitPull",
                (),
            ),
            (
                ["--check-git-push"],
                "vibeagent.cli.get_check_push_report",
                "vibeagent.cli.format_git_sync_preview_report_text",
                "Check push",
                "checkGitPush",
                (),
            ),
            (
                ["--git-push"],
                "vibeagent.cli.get_push_report",
                "vibeagent.cli.format_git_push_report_text",
                "Push",
                "gitPush",
                (),
            ),
            (
                ["--check-git-switch", "feature/demo", "--git-switch-create"],
                "vibeagent.cli.get_check_switch_report",
                "vibeagent.cli.format_git_switch_report_text",
                "Check switch",
                "checkGitSwitch",
                ("--create feature/demo",),
            ),
            (
                ["--git-switch", "main"],
                "vibeagent.cli.get_switch_report",
                "vibeagent.cli.format_git_switch_report_text",
                "Switch",
                "gitSwitch",
                ("main",),
            ),
        ]

        for argv_tail, getter_target, formatter_target, title, payload_key, expected_args in cases:
            with self.subTest(payload_key=payload_key), tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
                stdout = io.StringIO()
                report = {"ok": True, "message": payload_key}
                rendered = f"{title}:\n  ok: yes"

                with (
                    patch("vibeagent.cli.create_chat_client") as create_chat_client,
                    patch(getter_target, return_value=report) as getter,
                    patch(formatter_target, return_value=rendered) as formatter,
                    redirect_stdout(stdout),
                ):
                    exit_code = main(["--json", "--cwd", base, *argv_tail])

                payload = json.loads(stdout.getvalue())
                self.assertEqual(exit_code, 0)
                self.assertTrue(payload["success"])
                self.assertEqual(payload["status"], "completed")
                self.assertEqual(payload["text"], rendered)
                self.assertEqual(payload[payload_key], report)
                getter.assert_called_once_with(Path(base).resolve(), *expected_args)
                formatter.assert_called_once_with(title, report)
                create_chat_client.assert_not_called()

    def test_main_runs_git_stash_local_flags_without_creating_client(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
            stdout = io.StringIO()

            with (
                patch("vibeagent.cli.create_chat_client") as create_chat_client,
                patch("vibeagent.cli.get_check_stash_text", return_value="Check stash:\n  ok: yes") as get_check_stash_text,
                redirect_stdout(stdout),
            ):
                exit_code = main(["--cwd", base, "--check-git-stash", "save work", "--stash-include-untracked"])

        self.assertEqual(exit_code, 0)
        self.assertIn("Check stash:", stdout.getvalue())
        get_check_stash_text.assert_called_once_with(Path(base).resolve(), "--include-untracked save work")
        create_chat_client.assert_not_called()

        with tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
            stdout = io.StringIO()

            with (
                patch("vibeagent.cli.create_chat_client") as create_chat_client,
                patch("vibeagent.cli.get_stash_text", return_value="Stash:\n  ok: yes") as get_stash_text,
                redirect_stdout(stdout),
            ):
                exit_code = main(["--cwd", base, "--git-stash"])

        self.assertEqual(exit_code, 0)
        self.assertIn("Stash:", stdout.getvalue())
        get_stash_text.assert_called_once_with(Path(base).resolve(), "")
        create_chat_client.assert_not_called()

    def test_main_runs_git_stash_local_flags_as_json_without_creating_client(self) -> None:
        cases = [
            (
                ["--check-git-stash", "save work", "--stash-include-untracked"],
                "vibeagent.cli.get_check_stash_report",
                "vibeagent.cli.format_git_stash_report_text",
                "Check stash",
                "checkGitStash",
                ("--include-untracked save work",),
            ),
            (
                ["--git-stash"],
                "vibeagent.cli.get_stash_report",
                "vibeagent.cli.format_git_stash_report_text",
                "Stash",
                "gitStash",
                ("",),
            ),
            (
                ["--check-git-stash-apply", "stash@{0}"],
                "vibeagent.cli.get_check_stash_apply_report",
                "vibeagent.cli.format_git_stash_apply_report_text",
                "Check stash apply",
                "checkGitStashApply",
                ("stash@{0}",),
            ),
            (
                ["--git-stash-apply", "stash@{0}"],
                "vibeagent.cli.get_stash_apply_report",
                "vibeagent.cli.format_git_stash_apply_report_text",
                "Stash apply",
                "gitStashApply",
                ("stash@{0}",),
            ),
            (
                ["--check-git-stash-drop", "stash@{0}"],
                "vibeagent.cli.get_check_stash_drop_report",
                "vibeagent.cli.format_git_stash_drop_report_text",
                "Check stash drop",
                "checkGitStashDrop",
                ("stash@{0}",),
            ),
            (
                ["--git-stash-drop", "stash@{0}"],
                "vibeagent.cli.get_stash_drop_report",
                "vibeagent.cli.format_git_stash_drop_report_text",
                "Stash drop",
                "gitStashDrop",
                ("stash@{0}",),
            ),
        ]

        for argv_tail, getter_target, formatter_target, title, payload_key, expected_args in cases:
            with self.subTest(payload_key=payload_key), tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
                stdout = io.StringIO()
                report = {"ok": True, "message": payload_key}
                rendered = f"{title}:\n  ok: yes"

                with (
                    patch("vibeagent.cli.create_chat_client") as create_chat_client,
                    patch(getter_target, return_value=report) as getter,
                    patch(formatter_target, return_value=rendered) as formatter,
                    redirect_stdout(stdout),
                ):
                    exit_code = main(["--json", "--cwd", base, *argv_tail])

                payload = json.loads(stdout.getvalue())
                self.assertEqual(exit_code, 0)
                self.assertTrue(payload["success"])
                self.assertEqual(payload["status"], "completed")
                self.assertEqual(payload["text"], rendered)
                self.assertEqual(payload[payload_key], report)
                getter.assert_called_once_with(Path(base).resolve(), *expected_args)
                formatter.assert_called_once_with(title, report)
                create_chat_client.assert_not_called()

    def test_main_runs_git_stash_apply_local_flags_without_creating_client(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
            stdout = io.StringIO()

            with (
                patch("vibeagent.cli.create_chat_client") as create_chat_client,
                patch("vibeagent.cli.get_check_stash_apply_text", return_value="Check stash apply:\n  ok: yes") as get_check_stash_apply_text,
                redirect_stdout(stdout),
            ):
                exit_code = main(["--cwd", base, "--check-git-stash-apply", "stash@{0}"])

        self.assertEqual(exit_code, 0)
        self.assertIn("Check stash apply:", stdout.getvalue())
        get_check_stash_apply_text.assert_called_once_with(Path(base).resolve(), "stash@{0}")
        create_chat_client.assert_not_called()

        with tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
            stdout = io.StringIO()

            with (
                patch("vibeagent.cli.create_chat_client") as create_chat_client,
                patch("vibeagent.cli.get_stash_apply_text", return_value="Stash apply:\n  ok: yes") as get_stash_apply_text,
                redirect_stdout(stdout),
            ):
                exit_code = main(["--cwd", base, "--git-stash-apply", "stash@{0}"])

        self.assertEqual(exit_code, 0)
        self.assertIn("Stash apply:", stdout.getvalue())
        get_stash_apply_text.assert_called_once_with(Path(base).resolve(), "stash@{0}")
        create_chat_client.assert_not_called()

    def test_main_runs_git_stash_drop_local_flags_without_creating_client(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
            stdout = io.StringIO()

            with (
                patch("vibeagent.cli.create_chat_client") as create_chat_client,
                patch("vibeagent.cli.get_check_stash_drop_text", return_value="Check stash drop:\n  ok: yes") as get_check_stash_drop_text,
                redirect_stdout(stdout),
            ):
                exit_code = main(["--cwd", base, "--check-git-stash-drop", "stash@{0}"])

        self.assertEqual(exit_code, 0)
        self.assertIn("Check stash drop:", stdout.getvalue())
        get_check_stash_drop_text.assert_called_once_with(Path(base).resolve(), "stash@{0}")
        create_chat_client.assert_not_called()

        with tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
            stdout = io.StringIO()

            with (
                patch("vibeagent.cli.create_chat_client") as create_chat_client,
                patch("vibeagent.cli.get_stash_drop_text", return_value="Stash drop:\n  ok: yes") as get_stash_drop_text,
                redirect_stdout(stdout),
            ):
                exit_code = main(["--cwd", base, "--git-stash-drop", "stash@{0}"])

        self.assertEqual(exit_code, 0)
        self.assertIn("Stash drop:", stdout.getvalue())
        get_stash_drop_text.assert_called_once_with(Path(base).resolve(), "stash@{0}")
        create_chat_client.assert_not_called()

    def test_main_runs_git_remote_sync_local_flags_without_creating_client(self) -> None:
        cases = [
            ("--check-git-fetch", "origin", "vibeagent.cli.get_check_fetch_text", "Check fetch:", [Path, "origin"]),
            ("--git-fetch", "origin", "vibeagent.cli.get_fetch_text", "Fetch:", [Path, "origin"]),
            ("--check-git-pull", None, "vibeagent.cli.get_check_pull_text", "Check pull:", [Path]),
            ("--git-pull", None, "vibeagent.cli.get_pull_text", "Pull:", [Path]),
            ("--check-git-push", None, "vibeagent.cli.get_check_push_text", "Check push:", [Path]),
            ("--git-push", None, "vibeagent.cli.get_push_text", "Push:", [Path]),
        ]
        for flag, value, patch_target, output_text, expected_args in cases:
            with self.subTest(flag=flag), tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
                stdout = io.StringIO()
                argv = ["--cwd", base, flag]
                if value is not None:
                    argv.append(value)

                with (
                    patch("vibeagent.cli.create_chat_client") as create_chat_client,
                    patch(patch_target, return_value=f"{output_text}\n  ok: yes") as getter,
                    redirect_stdout(stdout),
                ):
                    exit_code = main(argv)

            self.assertEqual(exit_code, 0)
            self.assertIn(output_text, stdout.getvalue())
            resolved_args = [Path(base).resolve() if item is Path else item for item in expected_args]
            getter.assert_called_once_with(*resolved_args)
            create_chat_client.assert_not_called()

    def test_main_reports_stash_include_untracked_without_stash_as_local_flag_error(self) -> None:
        stdout = io.StringIO()

        with (
            patch("vibeagent.cli.create_chat_client") as create_chat_client,
            redirect_stdout(stdout),
        ):
            exit_code = main(["--stash-include-untracked", "fix", "tests"])

        self.assertEqual(exit_code, 2)
        self.assertEqual(stdout.getvalue(), "--stash-include-untracked can only be used with --check-git-stash or --git-stash.\n")
        create_chat_client.assert_not_called()

    def test_main_runs_git_switch_local_flags_without_creating_client(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
            stdout = io.StringIO()

            with (
                patch("vibeagent.cli.create_chat_client") as create_chat_client,
                patch("vibeagent.cli.get_check_switch_text", return_value="Check switch:\n  ok: yes") as get_check_switch_text,
                redirect_stdout(stdout),
            ):
                exit_code = main(["--cwd", base, "--check-git-switch", "feature/demo", "--git-switch-create"])

        self.assertEqual(exit_code, 0)
        self.assertIn("Check switch:", stdout.getvalue())
        get_check_switch_text.assert_called_once_with(Path(base).resolve(), "--create feature/demo")
        create_chat_client.assert_not_called()

        with tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
            stdout = io.StringIO()

            with (
                patch("vibeagent.cli.create_chat_client") as create_chat_client,
                patch("vibeagent.cli.get_switch_text", return_value="Switch:\n  ok: yes") as get_switch_text,
                redirect_stdout(stdout),
            ):
                exit_code = main(["--cwd", base, "--git-switch", "main"])

        self.assertEqual(exit_code, 0)
        self.assertIn("Switch:", stdout.getvalue())
        get_switch_text.assert_called_once_with(Path(base).resolve(), "main")
        create_chat_client.assert_not_called()

    def test_main_reports_git_switch_create_without_switch_as_local_flag_error(self) -> None:
        stdout = io.StringIO()

        with (
            patch("vibeagent.cli.create_chat_client") as create_chat_client,
            redirect_stdout(stdout),
        ):
            exit_code = main(["--git-switch-create", "fix", "tests"])

        self.assertEqual(exit_code, 2)
        self.assertEqual(stdout.getvalue(), "--git-switch-create can only be used with --check-git-switch or --git-switch.\n")
        create_chat_client.assert_not_called()

    def test_main_reports_diff_max_chars_without_diff_as_local_flag_error(self) -> None:
        stdout = io.StringIO()

        with (
            patch("vibeagent.cli.create_chat_client") as create_chat_client,
            redirect_stdout(stdout),
        ):
            exit_code = main(["--diff-max-chars", "2000", "fix", "tests"])

        self.assertEqual(exit_code, 2)
        self.assertEqual(stdout.getvalue(), "--diff-max-chars can only be used with --diff.\n")
        create_chat_client.assert_not_called()

    def test_main_reports_changes_max_files_without_changes_as_local_flag_error(self) -> None:
        stdout = io.StringIO()

        with (
            patch("vibeagent.cli.create_chat_client") as create_chat_client,
            redirect_stdout(stdout),
        ):
            exit_code = main(["--changes-max-files", "1", "fix", "tests"])

        self.assertEqual(exit_code, 2)
        self.assertEqual(stdout.getvalue(), "--changes-max-files can only be used with --changes.\n")
        create_chat_client.assert_not_called()

    def test_main_reports_review_limits_without_review_as_local_flag_errors(self) -> None:
        cases = [
            (["--review-max-files", "1", "fix", "tests"], "--review-max-files can only be used with --review.\n"),
            (["--review-max-checks", "1", "fix", "tests"], "--review-max-checks can only be used with --review.\n"),
        ]
        for argv, expected in cases:
            with self.subTest(argv=argv):
                stdout = io.StringIO()

                with (
                    patch("vibeagent.cli.create_chat_client") as create_chat_client,
                    redirect_stdout(stdout),
                ):
                    exit_code = main(argv)

                self.assertEqual(exit_code, 2)
                self.assertEqual(stdout.getvalue(), expected)
                create_chat_client.assert_not_called()

    def test_main_reports_handoff_limits_without_handoff_as_local_flag_errors(self) -> None:
        cases = [
            (["--handoff-max-files", "1", "fix", "tests"], "--handoff-max-files can only be used with --handoff.\n"),
            (["--handoff-max-checks", "1", "fix", "tests"], "--handoff-max-checks can only be used with --handoff.\n"),
            (["--handoff-max-status-chars", "1000", "fix", "tests"], "--handoff-max-status-chars can only be used with --handoff.\n"),
            (["--handoff-max-plan-chars", "1000", "fix", "tests"], "--handoff-max-plan-chars can only be used with --handoff.\n"),
        ]
        for argv, expected in cases:
            with self.subTest(argv=argv):
                stdout = io.StringIO()

                with (
                    patch("vibeagent.cli.create_chat_client") as create_chat_client,
                    redirect_stdout(stdout),
                ):
                    exit_code = main(argv)

                self.assertEqual(exit_code, 2)
                self.assertEqual(stdout.getvalue(), expected)
                create_chat_client.assert_not_called()

    def test_main_reports_structured_diff_limits_without_matching_diff_flag_as_local_flag_errors(self) -> None:
        cases = [
            (["--diff-hunks-max-hunks", "2", "fix"], "--diff-hunks-max-hunks can only be used with --diff-hunks.\n"),
            (["--diff-hunks-max-lines", "2", "fix"], "--diff-hunks-max-lines can only be used with --diff-hunks.\n"),
            (["--diff-context-lines", "2", "fix"], "--diff-context-lines can only be used with --diff-contexts.\n"),
            (["--diff-contexts-max-hunks", "2", "fix"], "--diff-contexts-max-hunks can only be used with --diff-contexts.\n"),
            (["--diff-contexts-max-bytes", "1000", "fix"], "--diff-contexts-max-bytes can only be used with --diff-contexts.\n"),
        ]

        for argv, expected in cases:
            with self.subTest(argv=argv):
                stdout = io.StringIO()

                with (
                    patch("vibeagent.cli.create_chat_client") as create_chat_client,
                    redirect_stdout(stdout),
                ):
                    exit_code = main(argv)

                self.assertEqual(exit_code, 2)
                self.assertEqual(stdout.getvalue(), expected)
                create_chat_client.assert_not_called()

    def test_main_reports_process_max_chars_without_process_output_flag_as_local_flag_error(self) -> None:
        stdout = io.StringIO()

        with (
            patch("vibeagent.cli.create_chat_client") as create_chat_client,
            redirect_stdout(stdout),
        ):
            exit_code = main(["--process-max-chars", "2000", "fix", "tests"])

        self.assertEqual(exit_code, 2)
        self.assertEqual(stdout.getvalue(), "--process-max-chars can only be used with --process-output, --process-output-contexts, or --process-output-diagnostics.\n")
        create_chat_client.assert_not_called()

    def test_main_reports_process_output_context_options_without_context_flag_as_local_flag_error(self) -> None:
        cases = [
            (["--process-output-context-lines", "2", "fix"], "--process-output-context-lines can only be used with --process-output-contexts or --process-output-diagnostics.\n"),
            (["--process-output-context-max", "5", "fix"], "--process-output-context-max can only be used with --process-output-contexts or --process-output-diagnostics.\n"),
            (["--process-output-context-max-bytes", "1000", "fix"], "--process-output-context-max-bytes can only be used with --process-output-contexts or --process-output-diagnostics.\n"),
            (["--process-output-diagnostic-max", "5", "fix"], "--process-output-diagnostic-max can only be used with --process-output-diagnostics.\n"),
            (["--process-output-contexts", "bg-1", "--process-output-diagnostic-max", "5"], "--process-output-diagnostic-max can only be used with --process-output-diagnostics.\n"),
        ]

        for argv, message in cases:
            with self.subTest(argv=argv):
                stdout = io.StringIO()
                with (
                    patch("vibeagent.cli.create_chat_client") as create_chat_client,
                    redirect_stdout(stdout),
                ):
                    exit_code = main(argv)

                self.assertEqual(exit_code, 2)
                self.assertEqual(stdout.getvalue(), message)
                create_chat_client.assert_not_called()

    def test_main_reports_wait_options_without_wait_process_as_local_flag_error(self) -> None:
        cases = [
            (["--wait-timeout-ms", "2000", "fix"], "--wait-timeout-ms can only be used with --wait-process.\n"),
            (["--wait-max-chars", "2000", "fix"], "--wait-max-chars can only be used with --wait-process.\n"),
            (["--wait-stdout", "ready", "fix"], "--wait-stdout can only be used with --wait-process.\n"),
            (["--wait-stderr", "ready", "fix"], "--wait-stderr can only be used with --wait-process.\n"),
            (["--wait-regex", "fix"], "--wait-regex can only be used with --wait-process.\n"),
        ]
        for argv, expected in cases:
            with self.subTest(argv=argv):
                stdout = io.StringIO()
                with (
                    patch("vibeagent.cli.create_chat_client") as create_chat_client,
                    redirect_stdout(stdout),
                ):
                    exit_code = main(argv)

                self.assertEqual(exit_code, 2)
                self.assertEqual(stdout.getvalue(), expected)
                create_chat_client.assert_not_called()

    def test_main_reports_write_process_stdin_pairing_errors(self) -> None:
        cases = [
            (["--write-stdin", "hello", "fix"], "--write-stdin can only be used with --check-write-process or --write-process.\n"),
            (["--check-write-process", "bg-1"], "--check-write-process requires --write-stdin.\n"),
            (["--write-process", "bg-1"], "--write-process requires --write-stdin.\n"),
        ]
        for argv, expected in cases:
            with self.subTest(argv=argv):
                stdout = io.StringIO()
                with (
                    patch("vibeagent.cli.create_chat_client") as create_chat_client,
                    redirect_stdout(stdout),
                ):
                    exit_code = main(argv)

                self.assertEqual(exit_code, 2)
                self.assertEqual(stdout.getvalue(), expected)
                create_chat_client.assert_not_called()

    def test_main_reports_stash_count_without_stashes_as_local_flag_error(self) -> None:
        stdout = io.StringIO()

        with (
            patch("vibeagent.cli.create_chat_client") as create_chat_client,
            redirect_stdout(stdout),
        ):
            exit_code = main(["--stash-count", "3", "fix", "tests"])

        self.assertEqual(exit_code, 2)
        self.assertEqual(stdout.getvalue(), "--stash-count can only be used with --stashes.\n")
        create_chat_client.assert_not_called()

    def test_main_reports_blame_lines_without_blame_as_local_flag_error(self) -> None:
        stdout = io.StringIO()

        with (
            patch("vibeagent.cli.create_chat_client") as create_chat_client,
            redirect_stdout(stdout),
        ):
            exit_code = main(["--blame-lines", "2:4", "fix", "tests"])

        self.assertEqual(exit_code, 2)
        self.assertEqual(stdout.getvalue(), "--blame-lines can only be used with --blame.\n")
        create_chat_client.assert_not_called()

    def test_main_reports_show_options_without_show_as_local_flag_error(self) -> None:
        stdout = io.StringIO()

        with (
            patch("vibeagent.cli.create_chat_client") as create_chat_client,
            redirect_stdout(stdout),
        ):
            exit_code = main(["--show-path", "app.py", "fix", "tests"])

        self.assertEqual(exit_code, 2)
        self.assertEqual(stdout.getvalue(), "--show-path can only be used with --show.\n")
        create_chat_client.assert_not_called()

    def test_main_reports_log_count_without_log_as_local_flag_error(self) -> None:
        stdout = io.StringIO()

        with (
            patch("vibeagent.cli.create_chat_client") as create_chat_client,
            redirect_stdout(stdout),
        ):
            exit_code = main(["--log-count", "2", "fix", "tests"])

        self.assertEqual(exit_code, 2)
        self.assertEqual(stdout.getvalue(), "--log-count can only be used with --log.\n")
        create_chat_client.assert_not_called()

    def test_main_reports_read_lines_without_read_as_local_flag_error(self) -> None:
        stdout = io.StringIO()

        with (
            patch("vibeagent.cli.create_chat_client") as create_chat_client,
            redirect_stdout(stdout),
        ):
            exit_code = main(["--read-lines", "2:4", "fix", "tests"])

        self.assertEqual(exit_code, 2)
        self.assertEqual(stdout.getvalue(), "--read-lines can only be used with --read.\n")
        create_chat_client.assert_not_called()

    def test_main_reports_read_max_bytes_without_read_as_local_flag_error(self) -> None:
        stdout = io.StringIO()

        with (
            patch("vibeagent.cli.create_chat_client") as create_chat_client,
            redirect_stdout(stdout),
        ):
            exit_code = main(["--read-max-bytes", "1000", "fix", "tests"])

        self.assertEqual(exit_code, 2)
        self.assertEqual(stdout.getvalue(), "--read-max-bytes can only be used with --read.\n")
        create_chat_client.assert_not_called()

    def test_main_reports_read_line_numbers_without_read_as_local_flag_error(self) -> None:
        stdout = io.StringIO()

        with (
            patch("vibeagent.cli.create_chat_client") as create_chat_client,
            redirect_stdout(stdout),
        ):
            exit_code = main(["--read-line-numbers", "fix", "tests"])

        self.assertEqual(exit_code, 2)
        self.assertEqual(stdout.getvalue(), "--read-line-numbers can only be used with --read.\n")
        create_chat_client.assert_not_called()

    def test_main_reports_read_files_max_bytes_without_read_files_as_local_flag_error(self) -> None:
        stdout = io.StringIO()

        with (
            patch("vibeagent.cli.create_chat_client") as create_chat_client,
            redirect_stdout(stdout),
        ):
            exit_code = main(["--read-files-max-bytes", "1000", "fix", "tests"])

        self.assertEqual(exit_code, 2)
        self.assertEqual(stdout.getvalue(), "--read-files-max-bytes can only be used with --read-files.\n")
        create_chat_client.assert_not_called()

    def test_main_reports_read_files_line_numbers_without_read_files_as_local_flag_error(self) -> None:
        stdout = io.StringIO()

        with (
            patch("vibeagent.cli.create_chat_client") as create_chat_client,
            redirect_stdout(stdout),
        ):
            exit_code = main(["--read-files-line-numbers", "fix", "tests"])

        self.assertEqual(exit_code, 2)
        self.assertEqual(stdout.getvalue(), "--read-files-line-numbers can only be used with --read-files.\n")
        create_chat_client.assert_not_called()

    def test_main_reports_read_ranges_max_bytes_without_read_ranges_as_local_flag_error(self) -> None:
        stdout = io.StringIO()

        with (
            patch("vibeagent.cli.create_chat_client") as create_chat_client,
            redirect_stdout(stdout),
        ):
            exit_code = main(["--read-ranges-max-bytes", "1000", "fix", "tests"])

        self.assertEqual(exit_code, 2)
        self.assertEqual(stdout.getvalue(), "--read-ranges-max-bytes can only be used with --read-ranges.\n")
        create_chat_client.assert_not_called()

    def test_main_reports_around_lines_without_around_as_local_flag_error(self) -> None:
        stdout = io.StringIO()

        with (
            patch("vibeagent.cli.create_chat_client") as create_chat_client,
            redirect_stdout(stdout),
        ):
            exit_code = main(["--around-lines", "5", "fix", "tests"])

        self.assertEqual(exit_code, 2)
        self.assertEqual(stdout.getvalue(), "--around-lines can only be used with --around.\n")
        create_chat_client.assert_not_called()

    def test_main_reports_around_max_bytes_without_around_as_local_flag_error(self) -> None:
        stdout = io.StringIO()

        with (
            patch("vibeagent.cli.create_chat_client") as create_chat_client,
            redirect_stdout(stdout),
        ):
            exit_code = main(["--around-max-bytes", "1000", "fix", "tests"])

        self.assertEqual(exit_code, 2)
        self.assertEqual(stdout.getvalue(), "--around-max-bytes can only be used with --around.\n")
        create_chat_client.assert_not_called()

    def test_main_reports_around_many_max_bytes_without_around_many_as_local_flag_error(self) -> None:
        stdout = io.StringIO()

        with (
            patch("vibeagent.cli.create_chat_client") as create_chat_client,
            redirect_stdout(stdout),
        ):
            exit_code = main(["--around-many-max-bytes", "1000", "fix", "tests"])

        self.assertEqual(exit_code, 2)
        self.assertEqual(stdout.getvalue(), "--around-many-max-bytes can only be used with --around-many.\n")
        create_chat_client.assert_not_called()

    def test_main_reports_output_context_options_without_output_contexts_as_local_flag_error(self) -> None:
        stdout = io.StringIO()

        with (
            patch("vibeagent.cli.create_chat_client") as create_chat_client,
            redirect_stdout(stdout),
        ):
            exit_code = main(["--output-context-lines", "2", "fix", "tests"])

        self.assertEqual(exit_code, 2)
        self.assertEqual(stdout.getvalue(), "--output-context-lines can only be used with --output-contexts.\n")
        create_chat_client.assert_not_called()

        stdout = io.StringIO()
        with (
            patch("vibeagent.cli.create_chat_client") as create_chat_client,
            redirect_stdout(stdout),
        ):
            exit_code = main(["--output-context-max", "5", "fix", "tests"])

        self.assertEqual(exit_code, 2)
        self.assertEqual(stdout.getvalue(), "--output-context-max can only be used with --output-contexts.\n")
        create_chat_client.assert_not_called()

        stdout = io.StringIO()
        with (
            patch("vibeagent.cli.create_chat_client") as create_chat_client,
            redirect_stdout(stdout),
        ):
            exit_code = main(["--output-context-max-bytes", "1000", "fix", "tests"])

        self.assertEqual(exit_code, 2)
        self.assertEqual(stdout.getvalue(), "--output-context-max-bytes can only be used with --output-contexts.\n")
        create_chat_client.assert_not_called()

    def test_main_reports_output_diagnostic_options_without_output_diagnostics_as_local_flag_error(self) -> None:
        cases = [
            (["--output-diagnostic-lines", "3", "fix"], "--output-diagnostic-lines can only be used with --output-diagnostics or --python-traceback.\n"),
            (["--output-diagnostic-max", "5", "fix"], "--output-diagnostic-max can only be used with --output-diagnostics or --python-traceback.\n"),
            (["--output-diagnostic-context-max", "5", "fix"], "--output-diagnostic-context-max can only be used with --output-diagnostics or --python-traceback.\n"),
            (["--output-diagnostic-context-max-bytes", "1000", "fix"], "--output-diagnostic-context-max-bytes can only be used with --output-diagnostics or --python-traceback.\n"),
        ]

        for argv, message in cases:
            with self.subTest(argv=argv):
                stdout = io.StringIO()
                with (
                    patch("vibeagent.cli.create_chat_client") as create_chat_client,
                    redirect_stdout(stdout),
                ):
                    exit_code = main(argv)

                self.assertEqual(exit_code, 2)
                self.assertEqual(stdout.getvalue(), message)
                create_chat_client.assert_not_called()

    def test_main_reports_session_output_context_options_without_session_output_contexts_as_local_flag_error(self) -> None:
        cases = [
            (
                ["--session-output-command-max", "3", "fix", "tests"],
                "--session-output-command-max can only be used with --session-output-contexts or --session-output-diagnostics.\n",
            ),
            (
                ["--session-output-max-chars", "4000", "fix", "tests"],
                "--session-output-max-chars can only be used with --session-output-contexts or --session-output-diagnostics.\n",
            ),
            (
                ["--session-output-context-lines", "2", "fix", "tests"],
                "--session-output-context-lines can only be used with --session-output-contexts or --session-output-diagnostics.\n",
            ),
            (
                ["--session-output-context-max", "5", "fix", "tests"],
                "--session-output-context-max can only be used with --session-output-contexts or --session-output-diagnostics.\n",
            ),
            (
                ["--session-output-context-max-bytes", "1000", "fix", "tests"],
                "--session-output-context-max-bytes can only be used with --session-output-contexts or --session-output-diagnostics.\n",
            ),
            (
                ["--session-output-diagnostic-max", "4", "fix", "tests"],
                "--session-output-diagnostic-max can only be used with --session-output-diagnostics.\n",
            ),
            (
                ["--session-output-diagnostic-max", "4", "--session-output-contexts", "run-1"],
                "--session-output-diagnostic-max can only be used with --session-output-diagnostics.\n",
            ),
        ]

        for argv, message in cases:
            with self.subTest(argv=argv):
                stdout = io.StringIO()
                with (
                    patch("vibeagent.cli.create_chat_client") as create_chat_client,
                    redirect_stdout(stdout),
                ):
                    exit_code = main(argv)

                self.assertEqual(exit_code, 2)
                self.assertEqual(stdout.getvalue(), message)
                create_chat_client.assert_not_called()

    def test_main_reports_session_limit_options_without_matching_session_view_as_local_flag_error(self) -> None:
        cases = [
            (
                ["--session-transcript-event-max", "3", "fix", "tests"],
                "--session-transcript-event-max can only be used with --transcript.\n",
            ),
            (
                ["--session-search-match-max", "3", "fix", "tests"],
                "--session-search-match-max can only be used with --session-search.\n",
            ),
            (
                ["--session-search-case-sensitive", "fix", "tests"],
                "--session-search-case-sensitive can only be used with --session-search.\n",
            ),
            (
                ["--session-max-checks", "3", "fix", "tests"],
                "--session-max-checks can only be used with --session-verification, --run-session-verification, --session-audit, or --session-handoff.\n",
            ),
            (
                ["--session-max-commands", "3", "fix", "tests"],
                "--session-max-commands can only be used with --session-commands, --session-audit, or --session-handoff.\n",
            ),
            (
                ["--session-max-output-chars", "4000", "fix", "tests"],
                "--session-max-output-chars can only be used with --session-commands or --session-handoff.\n",
            ),
            (
                ["--session-max-output-chars", "4000", "--session-audit", "run-1"],
                "--session-max-output-chars can only be used with --session-commands or --session-handoff.\n",
            ),
            (
                ["--session-max-files", "7", "--session-commands", "run-1"],
                "--session-max-files can only be used with --session-files, --session-audit, or --session-handoff.\n",
            ),
            (
                ["--session-max-failures", "4", "--session-files", "run-1"],
                "--session-max-failures can only be used with --session-failures, --session-audit, or --session-handoff.\n",
            ),
            (
                ["--session-max-text", "120", "--session-commands", "run-1"],
                "--session-max-text can only be used with --transcript, --session-search, --session-failures, --session-audit, or --session-handoff.\n",
            ),
        ]

        for argv, message in cases:
            with self.subTest(argv=argv):
                stdout = io.StringIO()
                with (
                    patch("vibeagent.cli.create_chat_client") as create_chat_client,
                    redirect_stdout(stdout),
                ):
                    exit_code = main(argv)

                self.assertEqual(exit_code, 2)
                self.assertEqual(stdout.getvalue(), message)
                create_chat_client.assert_not_called()

    def test_main_reports_tail_lines_without_tail_as_local_flag_error(self) -> None:
        stdout = io.StringIO()

        with (
            patch("vibeagent.cli.create_chat_client") as create_chat_client,
            redirect_stdout(stdout),
        ):
            exit_code = main(["--tail-lines", "5", "fix", "tests"])

        self.assertEqual(exit_code, 2)
        self.assertEqual(stdout.getvalue(), "--tail-lines can only be used with --tail.\n")
        create_chat_client.assert_not_called()

    def test_main_reports_tail_max_bytes_without_tail_as_local_flag_error(self) -> None:
        stdout = io.StringIO()

        with (
            patch("vibeagent.cli.create_chat_client") as create_chat_client,
            redirect_stdout(stdout),
        ):
            exit_code = main(["--tail-max-bytes", "1000", "fix", "tests"])

        self.assertEqual(exit_code, 2)
        self.assertEqual(stdout.getvalue(), "--tail-max-bytes can only be used with --tail.\n")
        create_chat_client.assert_not_called()

    def test_main_reports_search_path_without_search_as_local_flag_error(self) -> None:
        stdout = io.StringIO()

        with (
            patch("vibeagent.cli.create_chat_client") as create_chat_client,
            redirect_stdout(stdout),
        ):
            exit_code = main(["--search-path", "src", "fix", "tests"])

        self.assertEqual(exit_code, 2)
        self.assertEqual(stdout.getvalue(), "--search-path can only be used with --search or --search-contexts.\n")
        create_chat_client.assert_not_called()

    def test_main_local_model_flag_uses_provider_overrides(self) -> None:
        stdout = io.StringIO()

        with (
            patch("vibeagent.cli.create_chat_client") as create_chat_client,
            patch("vibeagent.cli.get_model_text", return_value="Model provider: deepseek") as get_model_text,
            redirect_stdout(stdout),
        ):
            exit_code = main(
                [
                    "--model",
                    "--provider",
                    "deepseek",
                    "--model-name",
                    "deepseek-reasoner",
                    "--base-url",
                    "https://deepseek.example",
                    "--api-key",
                    "secret-key",
                ]
            )

        provider_env = get_model_text.call_args.args[0]
        self.assertEqual(exit_code, 0)
        self.assertIn("Model provider: deepseek", stdout.getvalue())
        self.assertEqual(provider_env["VIBEAGENT_PROVIDER"], "deepseek")
        self.assertEqual(provider_env["OPENAI_COMPAT_MODEL"], "deepseek-reasoner")
        self.assertEqual(provider_env["OPENAI_COMPAT_BASE_URL"], "https://deepseek.example")
        self.assertEqual(provider_env["OPENAI_COMPAT_API_KEY"], "secret-key")
        create_chat_client.assert_not_called()

    def test_main_local_model_flag_uses_project_provider_config(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
            config_dir = Path(base) / ".vibeagent"
            config_dir.mkdir()
            (config_dir / "config.json").write_text(
                json.dumps({"provider": "deepseek", "model": "deepseek-reasoner"}),
                encoding="utf-8",
            )
            stdout = io.StringIO()

            with (
                patch.dict("vibeagent.cli.os.environ", {}, clear=True),
                patch("vibeagent.cli.create_chat_client") as create_chat_client,
                patch("vibeagent.cli.get_model_text", return_value="Model provider: deepseek") as get_model_text,
                redirect_stdout(stdout),
            ):
                exit_code = main(["--cwd", base, "--model"])

        provider_env = get_model_text.call_args.args[0]
        self.assertEqual(exit_code, 0)
        self.assertIn("Model provider: deepseek", stdout.getvalue())
        self.assertEqual(provider_env["VIBEAGENT_PROVIDER"], "deepseek")
        self.assertEqual(provider_env["VIBEAGENT_MODEL"], "deepseek-reasoner")
        create_chat_client.assert_not_called()

    def test_main_local_model_flag_exits_nonzero_for_invalid_provider(self) -> None:
        stdout = io.StringIO()

        with (
            patch.dict("vibeagent.cli.os.environ", {"VIBEAGENT_PROVIDER": "unknown"}, clear=True),
            patch("vibeagent.cli.create_chat_client") as create_chat_client,
            redirect_stdout(stdout),
        ):
            exit_code = main(["--model"])

        self.assertEqual(exit_code, 1)
        self.assertIn("Unsupported VIBEAGENT_PROVIDER: unknown", stdout.getvalue())
        create_chat_client.assert_not_called()

    def test_main_local_config_flag_reports_resolved_config_without_creating_client(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
            stdout = io.StringIO()

            with (
                patch.dict("vibeagent.cli.os.environ", {}, clear=True),
                patch("vibeagent.cli.create_chat_client") as create_chat_client,
                patch("vibeagent.cli.get_config_text", return_value="Config:\n  provider: deepseek") as get_config_text,
                redirect_stdout(stdout),
            ):
                exit_code = main(
                    [
                        "--cwd",
                        base,
                        "--config",
                        "--provider",
                        "deepseek",
                        "--model-name",
                        "deepseek-reasoner",
                        "--max-iterations",
                        "9",
                        "--command-timeout-ms",
                        "120000",
                        "--max-output-tokens",
                        "8192",
                        "--model-retries",
                        "2",
                        "--model-retry-delay-ms",
                        "25",
                        "--model-timeout-ms",
                        "45000",
                    ]
                )

        provider_env = get_config_text.call_args.args[1]
        self.assertEqual(exit_code, 0)
        self.assertIn("Config:", stdout.getvalue())
        self.assertEqual(get_config_text.call_args.args[0], Path(base).resolve())
        self.assertEqual(provider_env["VIBEAGENT_PROVIDER"], "deepseek")
        self.assertEqual(provider_env["OPENAI_COMPAT_MODEL"], "deepseek-reasoner")
        self.assertEqual(get_config_text.call_args.kwargs["max_iterations"], 9)
        self.assertEqual(get_config_text.call_args.kwargs["command_timeout_ms"], 120000)
        self.assertEqual(get_config_text.call_args.kwargs["max_output_tokens"], 8192)
        self.assertEqual(get_config_text.call_args.kwargs["model_retries"], 2)
        self.assertEqual(get_config_text.call_args.kwargs["model_retry_delay_ms"], 25)
        self.assertEqual(get_config_text.call_args.kwargs["model_timeout_ms"], 45000)
        create_chat_client.assert_not_called()

    def test_main_save_config_writes_non_secret_project_defaults(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
            stdout = io.StringIO()

            with (
                patch("vibeagent.cli.create_chat_client") as create_chat_client,
                redirect_stdout(stdout),
            ):
                exit_code = main(
                    [
                        "--cwd",
                        base,
                        "--save-config",
                        "--provider",
                        "deepseek",
                        "--model-name",
                        "deepseek-reasoner",
                        "--base-url",
                        "https://deepseek.example",
                        "--max-iterations",
                        "15",
                        "--command-timeout-ms",
                        "60000",
                        "--max-output-tokens",
                        "8192",
                        "--model-retries",
                        "2",
                        "--model-retry-delay-ms",
                        "25",
                        "--model-timeout-ms",
                        "60000",
                    ]
                )
            data = json.loads((Path(base) / ".vibeagent" / "config.json").read_text(encoding="utf-8"))

        self.assertEqual(exit_code, 0)
        self.assertEqual(stdout.getvalue(), "Saved .vibeagent/config.json.\n")
        self.assertEqual(data["provider"], "deepseek")
        self.assertEqual(data["model"], "deepseek-reasoner")
        self.assertEqual(data["base_url"], "https://deepseek.example")
        self.assertEqual(data["max_iterations"], 15)
        self.assertEqual(data["command_timeout_ms"], 60000)
        self.assertEqual(data["max_output_tokens"], 8192)
        self.assertEqual(data["model_retries"], 2)
        self.assertEqual(data["model_retry_delay_ms"], 25)
        self.assertEqual(data["model_timeout_ms"], 60000)
        self.assertNotIn("api_key", data)
        create_chat_client.assert_not_called()

    def test_main_save_config_accepts_model_alias(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
            stdout = io.StringIO()

            with (
                patch("vibeagent.cli.create_chat_client") as create_chat_client,
                redirect_stdout(stdout),
            ):
                exit_code = main(["--cwd", base, "--save-config", "--provider", "minimax", "--model", "MiniMax-custom"])
            data = json.loads((Path(base) / ".vibeagent" / "config.json").read_text(encoding="utf-8"))

        self.assertEqual(exit_code, 0)
        self.assertEqual(data["provider"], "minimax")
        self.assertEqual(data["model"], "MiniMax-custom")
        create_chat_client.assert_not_called()

    def test_main_save_config_rejects_api_key_without_writing_secret(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
            stdout = io.StringIO()

            with (
                patch("vibeagent.cli.create_chat_client") as create_chat_client,
                redirect_stdout(stdout),
            ):
                exit_code = main(["--cwd", base, "--save-config", "--provider", "deepseek", "--api-key", "secret-key"])
            config_path = Path(base) / ".vibeagent" / "config.json"

        self.assertEqual(exit_code, 1)
        self.assertIn("--save-config does not write API keys", stdout.getvalue())
        self.assertFalse(config_path.exists())
        create_chat_client.assert_not_called()

    def test_main_save_config_with_json_output(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
            stdout = io.StringIO()

            with (
                patch("vibeagent.cli.create_chat_client") as create_chat_client,
                redirect_stdout(stdout),
            ):
                exit_code = main(
                    [
                        "--json",
                        "--cwd",
                        base,
                        "--save-config",
                        "--provider",
                        "minimax",
                        "--model-name",
                        "MiniMax-M2.7",
                        "--max-iterations",
                        "9",
                    ]
                )

        payload = json.loads(stdout.getvalue())
        self.assertEqual(exit_code, 0)
        self.assertEqual(payload["kind"], "local")
        self.assertTrue(payload["success"])
        self.assertEqual(payload["status"], "completed")
        self.assertEqual(payload["text"], "Saved .vibeagent/config.json.")
        report = payload["saveConfig"]
        self.assertTrue(report["ok"])
        self.assertTrue(report["created"])
        self.assertFalse(report["existedBefore"])
        self.assertTrue(report["exists"])
        self.assertEqual(report["projectRoot"], str(Path(base).resolve()))
        self.assertEqual(report["path"], str(Path(base).resolve() / ".vibeagent" / "config.json"))
        self.assertEqual(report["writtenKeys"], ["provider", "model", "max_iterations"])
        self.assertEqual(report["config"]["provider"], "minimax")
        self.assertEqual(report["config"]["model"], "MiniMax-M2.7")
        self.assertEqual(report["config"]["max_iterations"], 9)
        self.assertNotIn("api_key", json.dumps(report, ensure_ascii=False))
        create_chat_client.assert_not_called()

    def test_main_local_session_flag_uses_requested_run_id_and_cwd(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
            stdout = io.StringIO()

            with (
                patch("vibeagent.cli.create_chat_client") as create_chat_client,
                patch("vibeagent.cli.get_session_text", return_value="Session: run-1") as get_session_text,
                redirect_stdout(stdout),
            ):
                exit_code = main(["--cwd", base, "--session", " run-1 "])

        self.assertEqual(exit_code, 0)
        self.assertIn("Session: run-1", stdout.getvalue())
        get_session_text.assert_called_once_with("run-1", Path(base).resolve())
        create_chat_client.assert_not_called()

    def test_main_local_status_flag_uses_approval_setting(self) -> None:
        stdout = io.StringIO()

        with (
            patch("vibeagent.cli.create_chat_client") as create_chat_client,
            redirect_stdout(stdout),
        ):
            exit_code = main(["--approval", "deny", "--status"])

        self.assertEqual(exit_code, 0)
        self.assertIn("Status:", stdout.getvalue())
        self.assertIn(f"version: {__version__}", stdout.getvalue())
        self.assertIn("approval: deny", stdout.getvalue())
        create_chat_client.assert_not_called()

    def test_main_local_status_flag_reports_json_payload(self) -> None:
        stdout = io.StringIO()
        report = {
            "version": __version__,
            "mode": "code",
            "approval": "deny",
            "resume": "",
            "chatTurns": 0,
            "message": "Runtime status resolved.",
        }

        with (
            patch("vibeagent.cli.create_chat_client") as create_chat_client,
            patch("vibeagent.cli.get_status_report", return_value=report) as get_status_report,
            patch("vibeagent.cli.format_status_report_text", return_value="Status:\n  approval: deny"),
            redirect_stdout(stdout),
        ):
            exit_code = main(["--json", "--approval", "deny", "--status"])

        payload = json.loads(stdout.getvalue())
        self.assertEqual(exit_code, 0)
        self.assertTrue(payload["success"])
        self.assertEqual(payload["runtimeStatus"], report)
        self.assertEqual(payload["runtimeStatus"]["version"], __version__)
        self.assertIn("Status:", payload["text"])
        get_status_report.assert_called_once_with("code", "deny", None, chat_turns=0)
        create_chat_client.assert_not_called()

    def test_main_local_context_flag_reports_json_payload(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
            stdout = io.StringIO()
            report = {
                "projectRoot": str(Path(base).resolve()),
                "resume": "",
                "resumeChars": 0,
                "instructions": {"found": False, "text": "No AGENTS.md or CLAUDE.md instructions found."},
                "commandHints": {"found": False, "text": "No project command hints found."},
                "workspaceSnapshot": {"text": "."},
                "message": "Prompt context resolved.",
            }

            with (
                patch("vibeagent.cli.create_chat_client") as create_chat_client,
                patch("vibeagent.cli.get_context_report", return_value=report) as get_context_report,
                patch("vibeagent.cli.format_context_report_text", return_value="Context:\n  resume: none"),
                redirect_stdout(stdout),
            ):
                exit_code = main(["--json", "--cwd", base, "--context"])

        payload = json.loads(stdout.getvalue())
        self.assertEqual(exit_code, 0)
        self.assertTrue(payload["success"])
        self.assertEqual(payload["context"], report)
        self.assertIn("Context:", payload["text"])
        get_context_report.assert_called_once_with(Path(base).resolve())
        create_chat_client.assert_not_called()

    def test_main_local_context_flag_defaults_to_current_directory(self) -> None:
        stdout = io.StringIO()
        report = {
            "projectRoot": str(Path.cwd().resolve()),
            "resume": "",
            "resumeChars": 0,
            "instructions": {"found": False, "text": "No AGENTS.md or CLAUDE.md instructions found."},
            "commandHints": {"found": False, "text": "No project command hints found."},
            "workspaceSnapshot": {"text": "."},
            "message": "Prompt context resolved.",
        }

        with (
            patch("vibeagent.cli.create_chat_client") as create_chat_client,
            patch("vibeagent.cli.get_context_report", return_value=report) as get_context_report,
            patch("vibeagent.cli.format_context_report_text", return_value="Context:\n  resume: none"),
            redirect_stdout(stdout),
        ):
            exit_code = main(["--json", "--context"])

        payload = json.loads(stdout.getvalue())
        self.assertEqual(exit_code, 0)
        self.assertTrue(payload["success"])
        self.assertEqual(payload["context"], report)
        get_context_report.assert_called_once_with(".")
        create_chat_client.assert_not_called()

    def test_main_local_flag_rejects_task_text(self) -> None:
        stdout = io.StringIO()

        with (
            patch("vibeagent.cli.create_chat_client") as create_chat_client,
            redirect_stdout(stdout),
        ):
            exit_code = main(["--doctor", "fix", "tests"])

        self.assertEqual(exit_code, 2)
        self.assertEqual(stdout.getvalue(), "Local command flags cannot be combined with a task.\n")
        create_chat_client.assert_not_called()

    def test_main_local_flag_rejects_task_text_with_json_status(self) -> None:
        stdout = io.StringIO()

        with (
            patch("vibeagent.cli.create_chat_client") as create_chat_client,
            redirect_stdout(stdout),
        ):
            exit_code = main(["--json", "--doctor", "fix", "tests"])

        payload = json.loads(stdout.getvalue())
        self.assertEqual(exit_code, 2)
        self.assertEqual(payload["kind"], "error")
        self.assertEqual(payload["version"], __version__)
        self.assertFalse(payload["success"])
        self.assertEqual(payload["status"], "failed")
        self.assertEqual(payload["error"], "Local command flags cannot be combined with a task.")
        create_chat_client.assert_not_called()

    def test_main_interactive_uses_requested_cwd_and_restores_original_cwd(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
            stdout = io.StringIO()
            original_cwd = Path.cwd()
            seen_cwds: list[Path] = []

            def fake_git_status_text() -> str:
                seen_cwds.append(Path.cwd())
                return "Git status:\n  ok: yes"

            with (
                patch("builtins.input", side_effect=["/git-status", "/exit"]),
                patch("vibeagent.cli.create_chat_client") as create_chat_client,
                patch("vibeagent.cli.get_git_status_text", side_effect=fake_git_status_text),
                redirect_stdout(stdout),
            ):
                exit_code = main(["--cwd", base])

        self.assertEqual(exit_code, 0)
        self.assertIn("Git status:", stdout.getvalue())
        self.assertEqual(seen_cwds, [Path(base).resolve()])
        self.assertEqual(Path.cwd(), original_cwd)
        create_chat_client.assert_not_called()

    def test_main_interactive_tool_search_reports_invalid_option_without_creating_client(self) -> None:
        stdout = io.StringIO()

        with (
            patch("builtins.input", side_effect=["/tool-search --category missing verification", "/exit"]),
            patch("vibeagent.cli.create_chat_client") as create_chat_client,
            patch("vibeagent.cli.get_tool_search_text") as get_tool_search_text,
            redirect_stdout(stdout),
        ):
            exit_code = main([])

        output = stdout.getvalue()
        self.assertEqual(exit_code, 0)
        self.assertIn("Usage: /tool-search", output)
        self.assertIn("--category must be one of:", output)
        get_tool_search_text.assert_not_called()
        create_chat_client.assert_not_called()

    def test_main_handles_session_commands_without_creating_client(self) -> None:
        stdout = io.StringIO()

        with ExitStack() as stack:
            stack.enter_context(
                patch(
                    "builtins.input",
                    side_effect=[
                        "/sessions",
                        "/usage",
                        "/cost",
                        "/doctor",
                        "/config",
                        "/review",
                        "/handoff",
                        "/changes",
                        "/diff --staged app.py",
                        "/diff-hunks --staged app.py",
                        "/diff-contexts --staged app.py",
                        "/tools",
                        "/tool read_file",
                        "/tool-search --max 3 --category session --approval no verification",
                        "/permissions",
                        "/checks",
                        "/commands",
                        "/related-tests pkg/actions.py",
                        "/focused-tests pkg/actions.py",
                        "/check-focused-tests pkg/actions.py",
                        "/run-focused-tests pkg/actions.py",
                        "/manifests",
                        "/command python3 --version",
                        "/run python3 --version",
                        "/check-run-seq python3 --version ;; npm test",
                        "/run-seq python3 --version ;; npm test",
                        "/check-start npm run dev",
                        "/start npm run dev",
                        "/port 5173 127.0.0.1 1500",
                        "/http http://127.0.0.1:5173 ready",
                        "/http-fetch http://127.0.0.1:5173/app",
                        "/overview",
                        "/repo-map src",
                        "/search needle",
                        "/search-contexts needle",
                        "/glob **/*.py",
                        "/tree src",
                        "/symbols src/app.py web/app.ts",
                        "/file-info src/app.py asset.bin",
                        "/image-info assets/logo.png",
                        "/read src/app.py 2:4",
                        "/around src/app.py 42 8",
                        "/around-many src/app.py:42:8 tests/test_app.py:17",
                        "/output-contexts src/app.py:42:8",
                        "/output-diagnostics ERROR src/app.py:42:8 failed",
                        "/python-traceback ValueError: bad",
                        "/tail logs/app.log 3",
                        "/read-files src/app.py tests/test_app.py",
                        "/read-ranges src/app.py:2:4 tests/test_app.py:1",
                        "/python-check src",
                        "/python-deps src",
                        "/python-defs Runner.run src",
                        "/python-refs run_agent src",
                        "/python-ref-contexts run_agent src",
                        "/python-calls helper src",
                        "/python-call-graph src",
                        "/python-rename-preview run_agent execute_agent src",
                        "/python-rename run_agent execute_agent src",
                        "/check-replace-python-def Runner.run '    def run(self):\\n        return 2\\n' src",
                        "/replace-python-def Runner.run '    def run(self):\\n        return 2\\n' src",
                        "/config-check pyproject.toml",
                        "/check-json-set package.json /private true",
                        "/json-set package.json /scripts/test '\"npm test\"'",
                        "/check-json-remove package.json /scripts/dev",
                        "/json-remove package.json /keywords/0",
                        "/check-json-patch package.json '[{\"op\":\"replace\",\"path\":\"/private\",\"value\":true}]'",
                        "/json-patch package.json '[{\"op\":\"remove\",\"path\":\"/keywords/0\"}]'",
                        "/check-replace-lines app.py 2 3 'new\\n'",
                        "/replace-lines app.py 2 2 'new\\n'",
                        "/check-insert-lines app.py 2 'new\\n'",
                        "/insert-lines app.py 2 'new\\n'",
                        "/check-append app.py 'new\\n'",
                        "/append app.py 'new\\n'",
                        "/check-write app.py 'new\\n'",
                        "/write app.py 'new\\n'",
                        "/check-write-files app.py 'a\\n' test.py 'b\\n'",
                        "/write-files app.py 'a\\n' test.py 'b\\n'",
                        "/check-edit app.py old new",
                        "/edit app.py old new",
                        "/check-multi-edit app.py old new print log",
                        "/multi-edit app.py old new print log",
                        "/check-delete old.py",
                        "/delete old.py",
                        "/check-delete-files old.py other.py",
                        "/delete-files old.py other.py",
                        "/check-move old.py new.py",
                        "/move old.py new.py",
                        "/check-move-files old.py new.py other.py other-new.py",
                        "/move-files old.py new.py other.py other-new.py",
                        "/check-copy template.py new.py",
                        "/copy template.py new.py",
                        "/check-copy-files template.py new.py config.py config-copy.py",
                        "/copy-files template.py new.py config.py config-copy.py",
                        "/check-move-dir old_pkg new_pkg",
                        "/move-dir old_pkg new_pkg",
                        "/check-move-dirs old_a new_a old_b new_b",
                        "/move-dirs old_a new_a old_b new_b",
                        "/check-copy-dir template_pkg copy_pkg",
                        "/copy-dir template_pkg copy_pkg",
                        "/check-copy-dirs template_a copy_a template_b copy_b",
                        "/copy-dirs template_a copy_a template_b copy_b",
                        "/check-mkdir pkg/generated",
                        "/mkdir pkg/generated",
                        "/check-mkdirs pkg/generated assets/icons",
                        "/mkdirs pkg/generated assets/icons",
                        "/check-rmdir pkg/generated",
                        "/rmdir pkg/generated",
                        "/check-rmdirs pkg/generated assets/icons",
                        "/rmdirs pkg/generated assets/icons",
                        "/check-executable tool.sh false",
                        "/set-executable tool.sh true",
                        "/check-patch app.py '@@ -1 +1 @@\\n-old\\n+new\\n'",
                        "/patch app.py '@@ -1 +1 @@\\n-old\\n+new\\n'",
                        "/check-patches '--- a/app.py\\n+++ b/app.py\\n@@ -1 +1 @@\\n-old\\n+new\\n'",
                        "/patches '--- a/app.py\\n+++ b/app.py\\n@@ -1 +1 @@\\n-old\\n+new\\n'",
                        "/check-regex-replace --ignore-case app.py old new",
                        "/regex-replace --count 1 app.py old new",
                        "/code-deps web",
                        "/code-refs runAgent web",
                        "/code-ref-contexts runAgent web",
                        "/code-defs runAgent web",
                        "/code-rename-preview runAgent executeAgent web",
                        "/code-rename runAgent executeAgent web",
                        "/git-status",
                        "/conflicts src",
                        "/git-info",
                        "/branches",
                        "/log app.py 2",
                        "/show HEAD app.py",
                        "/blame app.py 2:2",
                        "/stashes 3",
                        "/check-fetch origin",
                        "/fetch origin",
                        "/check-pull",
                        "/pull",
                        "/check-push",
                        "/push",
                        "/check-stash --include-untracked save work",
                        "/stash save work",
                        "/check-stash-apply stash@{0}",
                        "/stash-apply stash@{0}",
                        "/check-stash-drop stash@{0}",
                        "/stash-drop stash@{0}",
                        "/check-stage app.py",
                        "/stage app.py",
                        "/check-unstage app.py",
                        "/unstage app.py",
                        "/check-commit update app",
                        "/commit update app",
                        "/check-restore app.py",
                        "/restore app.py",
                        "/check-switch --create feature/demo",
                        "/switch feature/demo",
                        "/env",
                        "/processes",
                        "/process bg-1 2000",
                        "/process-output-contexts bg-1 2000",
                        "/process-output-diagnostics bg-1 2000",
                        "/wait-process bg-1 5000 2000",
                        "/check-write-process bg-1 hello\\n",
                        "/write-process bg-1 hello\\n",
                        "/check-stop-process bg-1",
                        "/stop-process bg-1",
                        "/check-stop-processes",
                        "/stop-processes",
                        "/session run-1",
                        "/last",
                        "/plan run-1",
                        "/transcript run-1",
                        "/checkpoint before tests",
                        "/checkpoints",
                        "/checkpoint-show ckpt-1",
                        "/checkpoint-diff ckpt-1",
                        "/checkpoint-status ckpt-1",
                        "/check-checkpoint-restore ckpt-1",
                        "/checkpoint-restore ckpt-1",
                        "/check-checkpoint-delete ckpt-1",
                        "/checkpoint-delete ckpt-1",
                        "/check-checkpoint-prune 2",
                        "/checkpoint-prune 2",
                        "/resume run-1",
                        "/compact run-1",
                        "/context",
                        "/init",
                        "/clear",
                        "/exit",
                    ],
                )
            )
            create_chat_client = stack.enter_context(patch("vibeagent.cli.create_chat_client"))
            stack.enter_context(patch("vibeagent.cli.get_sessions_text", return_value="Recent sessions:\n  run-1"))
            stack.enter_context(patch("vibeagent.cli.get_usage_text", return_value="Usage:\n  sessions: 1"))
            stack.enter_context(patch("vibeagent.cli.get_cost_text", return_value="Cost:\n  estimatedCostUsd: $0.000001"))
            stack.enter_context(patch("vibeagent.cli.get_doctor_text", return_value="Doctor:\n  provider: minimax"))
            get_config_text = stack.enter_context(patch("vibeagent.cli.get_config_text", return_value="Config:\n  provider: minimax"))
            stack.enter_context(patch("vibeagent.cli.get_review_text", return_value="Review:\n  ready: yes"))
            get_handoff_text = stack.enter_context(patch("vibeagent.cli.get_handoff_text", return_value="Handoff:\n  ready: yes"))
            get_changes_text = stack.enter_context(patch("vibeagent.cli.get_changes_text", return_value="Changes:\n  changedFiles: 1"))
            get_diff_text = stack.enter_context(patch("vibeagent.cli.get_diff_text", return_value="Diff:\n  scope: staged"))
            get_diff_hunks_text = stack.enter_context(patch("vibeagent.cli.get_diff_hunks_text", return_value="Diff hunks:\n  hunks: 1/1"))
            get_diff_contexts_text = stack.enter_context(patch("vibeagent.cli.get_diff_contexts_text", return_value="Diff contexts:\n  contexts: 1/1"))
            stack.enter_context(patch("vibeagent.cli.get_tools_text", return_value="Tools:\n  total: 1"))
            stack.enter_context(patch("vibeagent.cli.get_tool_text", return_value="Tool: read_file"))
            get_tool_search_text = stack.enter_context(patch("vibeagent.cli.get_tool_search_text", return_value="Tool search:\n  matches: 1/1"))
            get_permissions_text = stack.enter_context(patch("vibeagent.cli.get_permissions_text", return_value="Permissions:\n  approvalPolicy: ask"))
            get_checks_text = stack.enter_context(patch("vibeagent.cli.get_checks_text", return_value="Checks:\n  suggestedChecks: 1/1"))
            get_commands_text = stack.enter_context(patch("vibeagent.cli.get_commands_text", return_value="Project commands:\n  commands: 1/1"))
            get_related_tests_text = stack.enter_context(patch("vibeagent.cli.get_related_tests_text", return_value="Related tests:\n  candidates: 1/1"))
            get_focused_test_commands_text = stack.enter_context(patch("vibeagent.cli.get_focused_test_commands_text", return_value="Focused test commands:\n  commands: 1/1"))
            get_check_focused_test_commands_text = stack.enter_context(patch("vibeagent.cli.get_check_focused_test_commands_text", return_value="Check focused test commands:\n  ok: yes"))
            get_run_focused_test_commands_text = stack.enter_context(patch("vibeagent.cli.get_run_focused_test_commands_text", return_value="Run focused test commands:\n  ok: yes"))
            get_manifests_text = stack.enter_context(patch("vibeagent.cli.get_manifests_text", return_value="Manifests:\n  files: 1/1"))
            get_command_check_text = stack.enter_context(patch("vibeagent.cli.get_command_check_text", return_value="Command check:\n  ok: yes"))
            get_run_text = stack.enter_context(patch("vibeagent.cli.get_run_text", return_value="Run:\n  ok: yes"))
            get_check_run_sequence_text = stack.enter_context(patch("vibeagent.cli.get_check_run_sequence_text", return_value="Check run sequence:\n  ok: yes"))
            get_run_sequence_text = stack.enter_context(patch("vibeagent.cli.get_run_sequence_text", return_value="Run sequence:\n  ok: yes"))
            get_check_start_text = stack.enter_context(patch("vibeagent.cli.get_check_start_text", return_value="Check start:\n  ok: yes"))
            get_start_text = stack.enter_context(patch("vibeagent.cli.get_start_text", return_value="Start:\n  ok: yes"))
            get_port_text = stack.enter_context(patch("vibeagent.cli.get_port_text", return_value="Port:\n  ok: yes"))
            get_http_text = stack.enter_context(patch("vibeagent.cli.get_http_text", return_value="HTTP:\n  ok: yes"))
            get_http_fetch_text = stack.enter_context(patch("vibeagent.cli.get_http_fetch_text", return_value="HTTP fetch:\n  ok: yes"))
            get_overview_text = stack.enter_context(patch("vibeagent.cli.get_overview_text", return_value="Overview:\n  files: 1/1"))
            get_repo_map_text = stack.enter_context(patch("vibeagent.cli.get_repo_map_text", return_value="Repo map:\n  files: 1/1"))
            get_search_text = stack.enter_context(patch("vibeagent.cli.get_search_text", return_value="Search:\n  matches: 1/1"))
            get_search_contexts_text = stack.enter_context(patch("vibeagent.cli.get_search_contexts_text", return_value="Search contexts:\n  contexts: 1/1"))
            get_glob_text = stack.enter_context(patch("vibeagent.cli.get_glob_text", return_value="Glob:\n  matches: 1/1"))
            get_tree_text = stack.enter_context(patch("vibeagent.cli.get_tree_text", return_value="Tree:\n  entries: 1/1"))
            get_symbols_text = stack.enter_context(patch("vibeagent.cli.get_symbols_text", return_value="Symbols:\n  files: 1/1"))
            get_file_info_text = stack.enter_context(patch("vibeagent.cli.get_file_info_text", return_value="File info:\n  paths: 1/1"))
            get_image_info_text = stack.enter_context(patch("vibeagent.cli.get_image_info_text", return_value="Image info:\n  images: 1/1"))
            get_read_text = stack.enter_context(patch("vibeagent.cli.get_read_text", return_value="Read:\n  ok: yes"))
            get_around_text = stack.enter_context(patch("vibeagent.cli.get_around_text", return_value="Around:\n  ok: yes"))
            get_around_many_text = stack.enter_context(patch("vibeagent.cli.get_around_many_text", return_value="Around many:\n  contexts: 2/2"))
            get_output_contexts_text = stack.enter_context(patch("vibeagent.cli.get_output_contexts_text", return_value="Output contexts:\n  contexts: 1/1"))
            get_output_diagnostics_text = stack.enter_context(patch("vibeagent.cli.get_output_diagnostics_text", return_value="Output diagnostics:\n  diagnostics: 1/1"))
            get_python_traceback_text = stack.enter_context(patch("vibeagent.cli.get_python_traceback_text", return_value="Python traceback:\n  diagnostics: 1/1"))
            get_tail_text = stack.enter_context(patch("vibeagent.cli.get_tail_text", return_value="Tail:\n  ok: yes"))
            get_read_files_text = stack.enter_context(patch("vibeagent.cli.get_read_files_text", return_value="Read files:\n  files: 2/2"))
            get_read_ranges_text = stack.enter_context(patch("vibeagent.cli.get_read_ranges_text", return_value="Read ranges:\n  ranges: 2/2"))
            get_python_check_text = stack.enter_context(patch("vibeagent.cli.get_python_check_text", return_value="Python check:\n  ok: yes"))
            get_python_deps_text = stack.enter_context(patch("vibeagent.cli.get_python_deps_text", return_value="Python dependencies:\n  files: 1/1"))
            get_python_defs_text = stack.enter_context(patch("vibeagent.cli.get_python_defs_text", return_value="Python definitions:\n  definitions: 1/1"))
            get_python_refs_text = stack.enter_context(patch("vibeagent.cli.get_python_refs_text", return_value="Python references:\n  references: 1/1"))
            get_python_ref_contexts_text = stack.enter_context(patch("vibeagent.cli.get_python_ref_contexts_text", return_value="Python reference contexts:\n  contexts: 1/1"))
            get_python_calls_text = stack.enter_context(patch("vibeagent.cli.get_python_calls_text", return_value="Python calls:\n  calls: 1/1"))
            get_python_call_graph_text = stack.enter_context(patch("vibeagent.cli.get_python_call_graph_text", return_value="Python call graph:\n  edges: 3/3"))
            get_python_rename_preview_text = stack.enter_context(patch("vibeagent.cli.get_python_rename_preview_text", return_value="Python rename preview:\n  replacements: 2"))
            get_python_rename_text = stack.enter_context(patch("vibeagent.cli.get_python_rename_text", return_value="Python rename:\n  replacements: 2"))
            get_check_replace_python_definition_text = stack.enter_context(patch("vibeagent.cli.get_check_replace_python_definition_text", return_value="Check replace Python definition:\n  ok: yes"))
            get_replace_python_definition_text = stack.enter_context(patch("vibeagent.cli.get_replace_python_definition_text", return_value="Replace Python definition:\n  ok: yes"))
            get_config_check_text = stack.enter_context(patch("vibeagent.cli.get_config_check_text", return_value="Config check:\n  ok: yes"))
            get_check_json_set_text = stack.enter_context(patch("vibeagent.cli.get_check_json_set_text", return_value="Check JSON set:\n  ok: yes"))
            get_json_set_text = stack.enter_context(patch("vibeagent.cli.get_json_set_text", return_value="JSON set:\n  ok: yes"))
            get_check_json_remove_text = stack.enter_context(patch("vibeagent.cli.get_check_json_remove_text", return_value="Check JSON remove:\n  ok: yes"))
            get_json_remove_text = stack.enter_context(patch("vibeagent.cli.get_json_remove_text", return_value="JSON remove:\n  ok: yes"))
            get_check_json_patch_text = stack.enter_context(patch("vibeagent.cli.get_check_json_patch_text", return_value="Check JSON patch:\n  ok: yes"))
            get_json_patch_text = stack.enter_context(patch("vibeagent.cli.get_json_patch_text", return_value="JSON patch:\n  ok: yes"))
            get_check_replace_lines_text = stack.enter_context(patch("vibeagent.cli.get_check_replace_lines_text", return_value="Check replace lines:\n  ok: yes"))
            get_replace_lines_text = stack.enter_context(patch("vibeagent.cli.get_replace_lines_text", return_value="Replace lines:\n  ok: yes"))
            get_check_insert_lines_text = stack.enter_context(patch("vibeagent.cli.get_check_insert_lines_text", return_value="Check insert lines:\n  ok: yes"))
            get_insert_lines_text = stack.enter_context(patch("vibeagent.cli.get_insert_lines_text", return_value="Insert lines:\n  ok: yes"))
            get_check_append_file_text = stack.enter_context(patch("vibeagent.cli.get_check_append_file_text", return_value="Check append:\n  ok: yes"))
            get_append_file_text = stack.enter_context(patch("vibeagent.cli.get_append_file_text", return_value="Append:\n  ok: yes"))
            get_check_write_file_text = stack.enter_context(patch("vibeagent.cli.get_check_write_file_text", return_value="Check write:\n  ok: yes"))
            get_write_file_text = stack.enter_context(patch("vibeagent.cli.get_write_file_text", return_value="Write:\n  ok: yes"))
            get_check_write_files_text = stack.enter_context(patch("vibeagent.cli.get_check_write_files_text", return_value="Check write files:\n  ok: yes"))
            get_write_files_text = stack.enter_context(patch("vibeagent.cli.get_write_files_text", return_value="Write files:\n  ok: yes"))
            get_check_edit_file_text = stack.enter_context(patch("vibeagent.cli.get_check_edit_file_text", return_value="Check edit:\n  ok: yes"))
            get_edit_file_text = stack.enter_context(patch("vibeagent.cli.get_edit_file_text", return_value="Edit:\n  ok: yes"))
            get_check_multi_edit_file_text = stack.enter_context(patch("vibeagent.cli.get_check_multi_edit_file_text", return_value="Check multi edit:\n  ok: yes"))
            get_multi_edit_file_text = stack.enter_context(patch("vibeagent.cli.get_multi_edit_file_text", return_value="Multi edit:\n  ok: yes"))
            get_check_delete_file_text = stack.enter_context(patch("vibeagent.cli.get_check_delete_file_text", return_value="Check delete:\n  ok: yes"))
            get_delete_file_text = stack.enter_context(patch("vibeagent.cli.get_delete_file_text", return_value="Delete:\n  ok: yes"))
            get_check_delete_files_text = stack.enter_context(patch("vibeagent.cli.get_check_delete_files_text", return_value="Check delete files:\n  ok: yes"))
            get_delete_files_text = stack.enter_context(patch("vibeagent.cli.get_delete_files_text", return_value="Delete files:\n  ok: yes"))
            get_check_move_file_text = stack.enter_context(patch("vibeagent.cli.get_check_move_file_text", return_value="Check move:\n  ok: yes"))
            get_move_file_text = stack.enter_context(patch("vibeagent.cli.get_move_file_text", return_value="Move:\n  ok: yes"))
            get_check_move_files_text = stack.enter_context(patch("vibeagent.cli.get_check_move_files_text", return_value="Check move files:\n  ok: yes"))
            get_move_files_text = stack.enter_context(patch("vibeagent.cli.get_move_files_text", return_value="Move files:\n  ok: yes"))
            get_check_copy_file_text = stack.enter_context(patch("vibeagent.cli.get_check_copy_file_text", return_value="Check copy:\n  ok: yes"))
            get_copy_file_text = stack.enter_context(patch("vibeagent.cli.get_copy_file_text", return_value="Copy:\n  ok: yes"))
            get_check_copy_files_text = stack.enter_context(patch("vibeagent.cli.get_check_copy_files_text", return_value="Check copy files:\n  ok: yes"))
            get_copy_files_text = stack.enter_context(patch("vibeagent.cli.get_copy_files_text", return_value="Copy files:\n  ok: yes"))
            get_check_move_dir_text = stack.enter_context(patch("vibeagent.cli.get_check_move_dir_text", return_value="Check move dir:\n  ok: yes"))
            get_move_dir_text = stack.enter_context(patch("vibeagent.cli.get_move_dir_text", return_value="Move dir:\n  ok: yes"))
            get_check_move_dirs_text = stack.enter_context(patch("vibeagent.cli.get_check_move_dirs_text", return_value="Check move dirs:\n  ok: yes"))
            get_move_dirs_text = stack.enter_context(patch("vibeagent.cli.get_move_dirs_text", return_value="Move dirs:\n  ok: yes"))
            get_check_copy_dir_text = stack.enter_context(patch("vibeagent.cli.get_check_copy_dir_text", return_value="Check copy dir:\n  ok: yes"))
            get_copy_dir_text = stack.enter_context(patch("vibeagent.cli.get_copy_dir_text", return_value="Copy dir:\n  ok: yes"))
            get_check_copy_dirs_text = stack.enter_context(patch("vibeagent.cli.get_check_copy_dirs_text", return_value="Check copy dirs:\n  ok: yes"))
            get_copy_dirs_text = stack.enter_context(patch("vibeagent.cli.get_copy_dirs_text", return_value="Copy dirs:\n  ok: yes"))
            get_check_create_dir_text = stack.enter_context(patch("vibeagent.cli.get_check_create_dir_text", return_value="Check mkdir:\n  ok: yes"))
            get_create_dir_text = stack.enter_context(patch("vibeagent.cli.get_create_dir_text", return_value="Mkdir:\n  ok: yes"))
            get_check_create_dirs_text = stack.enter_context(patch("vibeagent.cli.get_check_create_dirs_text", return_value="Check mkdirs:\n  ok: yes"))
            get_create_dirs_text = stack.enter_context(patch("vibeagent.cli.get_create_dirs_text", return_value="Mkdirs:\n  ok: yes"))
            get_check_delete_empty_dir_text = stack.enter_context(patch("vibeagent.cli.get_check_delete_empty_dir_text", return_value="Check rmdir:\n  ok: yes"))
            get_delete_empty_dir_text = stack.enter_context(patch("vibeagent.cli.get_delete_empty_dir_text", return_value="Rmdir:\n  ok: yes"))
            get_check_delete_empty_dirs_text = stack.enter_context(patch("vibeagent.cli.get_check_delete_empty_dirs_text", return_value="Check rmdirs:\n  ok: yes"))
            get_delete_empty_dirs_text = stack.enter_context(patch("vibeagent.cli.get_delete_empty_dirs_text", return_value="Rmdirs:\n  ok: yes"))
            get_check_set_executable_text = stack.enter_context(patch("vibeagent.cli.get_check_set_executable_text", return_value="Check executable:\n  ok: yes"))
            get_set_executable_text = stack.enter_context(patch("vibeagent.cli.get_set_executable_text", return_value="Set executable:\n  ok: yes"))
            get_check_patch_text = stack.enter_context(patch("vibeagent.cli.get_check_patch_text", return_value="Check patch:\n  ok: yes"))
            get_patch_text = stack.enter_context(patch("vibeagent.cli.get_patch_text", return_value="Patch:\n  ok: yes"))
            get_check_patches_text = stack.enter_context(patch("vibeagent.cli.get_check_patches_text", return_value="Check patches:\n  ok: yes"))
            get_patches_text = stack.enter_context(patch("vibeagent.cli.get_patches_text", return_value="Patches:\n  ok: yes"))
            get_check_regex_replace_text = stack.enter_context(patch("vibeagent.cli.get_check_regex_replace_text", return_value="Check regex replace:\n  ok: yes"))
            get_regex_replace_text = stack.enter_context(patch("vibeagent.cli.get_regex_replace_text", return_value="Regex replace:\n  ok: yes"))
            get_code_deps_text = stack.enter_context(patch("vibeagent.cli.get_code_deps_text", return_value="Code dependencies:\n  files: 1/1"))
            get_code_refs_text = stack.enter_context(patch("vibeagent.cli.get_code_refs_text", return_value="Code references:\n  references: 1/1"))
            get_code_ref_contexts_text = stack.enter_context(patch("vibeagent.cli.get_code_ref_contexts_text", return_value="Code reference contexts:\n  contexts: 1/1"))
            get_code_defs_text = stack.enter_context(patch("vibeagent.cli.get_code_defs_text", return_value="Code definitions:\n  definitions: 1/1"))
            get_code_rename_preview_text = stack.enter_context(patch("vibeagent.cli.get_code_rename_preview_text", return_value="Code rename preview:\n  replacements: 2"))
            get_code_rename_text = stack.enter_context(patch("vibeagent.cli.get_code_rename_text", return_value="Code rename:\n  replacements: 2"))
            get_git_status_text = stack.enter_context(patch("vibeagent.cli.get_git_status_text", return_value="Git status:\n  ok: yes"))
            get_git_conflicts_text = stack.enter_context(patch("vibeagent.cli.get_git_conflicts_text", return_value="Git conflicts:\n  ok: yes"))
            get_git_info_text = stack.enter_context(patch("vibeagent.cli.get_git_info_text", return_value="Git info:\n  branch: main"))
            get_branches_text = stack.enter_context(patch("vibeagent.cli.get_branches_text", return_value="Branches:\n  current: main"))
            get_log_text = stack.enter_context(patch("vibeagent.cli.get_log_text", return_value="Log:\n  ok: yes"))
            get_show_text = stack.enter_context(patch("vibeagent.cli.get_show_text", return_value="Show:\n  ok: yes"))
            get_blame_text = stack.enter_context(patch("vibeagent.cli.get_blame_text", return_value="Blame:\n  ok: yes"))
            get_stashes_text = stack.enter_context(patch("vibeagent.cli.get_stashes_text", return_value="Stashes:\n  entries: 1/1"))
            get_check_fetch_text = stack.enter_context(patch("vibeagent.cli.get_check_fetch_text", return_value="Check fetch:\n  ok: yes"))
            get_fetch_text = stack.enter_context(patch("vibeagent.cli.get_fetch_text", return_value="Fetch:\n  ok: yes"))
            get_check_pull_text = stack.enter_context(patch("vibeagent.cli.get_check_pull_text", return_value="Check pull:\n  ok: yes"))
            get_pull_text = stack.enter_context(patch("vibeagent.cli.get_pull_text", return_value="Pull:\n  ok: yes"))
            get_check_push_text = stack.enter_context(patch("vibeagent.cli.get_check_push_text", return_value="Check push:\n  ok: yes"))
            get_push_text = stack.enter_context(patch("vibeagent.cli.get_push_text", return_value="Push:\n  ok: yes"))
            get_check_stash_text = stack.enter_context(patch("vibeagent.cli.get_check_stash_text", return_value="Check stash:\n  ok: yes"))
            get_stash_text = stack.enter_context(patch("vibeagent.cli.get_stash_text", return_value="Stash:\n  ok: yes"))
            get_check_stash_apply_text = stack.enter_context(patch("vibeagent.cli.get_check_stash_apply_text", return_value="Check stash apply:\n  ok: yes"))
            get_stash_apply_text = stack.enter_context(patch("vibeagent.cli.get_stash_apply_text", return_value="Stash apply:\n  ok: yes"))
            get_check_stash_drop_text = stack.enter_context(patch("vibeagent.cli.get_check_stash_drop_text", return_value="Check stash drop:\n  ok: yes"))
            get_stash_drop_text = stack.enter_context(patch("vibeagent.cli.get_stash_drop_text", return_value="Stash drop:\n  ok: yes"))
            get_check_stage_text = stack.enter_context(patch("vibeagent.cli.get_check_stage_text", return_value="Check stage:\n  ok: yes"))
            get_stage_text = stack.enter_context(patch("vibeagent.cli.get_stage_text", return_value="Stage:\n  ok: yes"))
            get_check_unstage_text = stack.enter_context(patch("vibeagent.cli.get_check_unstage_text", return_value="Check unstage:\n  ok: yes"))
            get_unstage_text = stack.enter_context(patch("vibeagent.cli.get_unstage_text", return_value="Unstage:\n  ok: yes"))
            get_check_commit_text = stack.enter_context(patch("vibeagent.cli.get_check_commit_text", return_value="Check commit:\n  ok: yes"))
            get_commit_text = stack.enter_context(patch("vibeagent.cli.get_commit_text", return_value="Commit:\n  ok: yes"))
            get_check_restore_text = stack.enter_context(patch("vibeagent.cli.get_check_restore_text", return_value="Check restore:\n  ok: yes"))
            get_restore_text = stack.enter_context(patch("vibeagent.cli.get_restore_text", return_value="Restore:\n  ok: yes"))
            get_check_switch_text = stack.enter_context(patch("vibeagent.cli.get_check_switch_text", return_value="Check switch:\n  ok: yes"))
            get_switch_text = stack.enter_context(patch("vibeagent.cli.get_switch_text", return_value="Switch:\n  ok: yes"))
            get_env_text = stack.enter_context(patch("vibeagent.cli.get_env_text", return_value="Environment:\n  tools: 3/9"))
            get_processes_text = stack.enter_context(patch("vibeagent.cli.get_processes_text", return_value="Processes:\n  processes: 0"))
            get_process_text = stack.enter_context(patch("vibeagent.cli.get_process_text", return_value="Process:\n  ok: no"))
            get_process_output_contexts_text = stack.enter_context(patch("vibeagent.cli.get_process_output_contexts_text", return_value="Process output contexts:\n  contexts: 1/1"))
            get_process_output_diagnostics_text = stack.enter_context(patch("vibeagent.cli.get_process_output_diagnostics_text", return_value="Process output diagnostics:\n  diagnostics: 1/1"))
            get_wait_process_text = stack.enter_context(patch("vibeagent.cli.get_wait_process_text", return_value="Wait process:\n  ok: no"))
            get_check_write_process_text = stack.enter_context(patch("vibeagent.cli.get_check_write_process_text", return_value="Check write process:\n  ok: yes"))
            get_write_process_text = stack.enter_context(patch("vibeagent.cli.get_write_process_text", return_value="Write process:\n  ok: no"))
            get_check_stop_process_text = stack.enter_context(patch("vibeagent.cli.get_check_stop_process_text", return_value="Check stop process:\n  ok: yes"))
            get_stop_process_text = stack.enter_context(patch("vibeagent.cli.get_stop_process_text", return_value="Stop process:\n  ok: no"))
            get_check_stop_all_processes_text = stack.enter_context(patch("vibeagent.cli.get_check_stop_all_processes_text", return_value="Check stop processes:\n  processes: 1"))
            get_stop_all_processes_text = stack.enter_context(patch("vibeagent.cli.get_stop_all_processes_text", return_value="Stop processes:\n  stopped: 1"))
            get_session_text = stack.enter_context(patch("vibeagent.cli.get_session_text", return_value="Session: run-1"))
            stack.enter_context(patch("vibeagent.cli.get_last_session_text", return_value="Session: run-1"))
            get_plan_text = stack.enter_context(patch("vibeagent.cli.get_plan_text", return_value="Plan:\n  session: run-1"))
            get_transcript_text = stack.enter_context(patch("vibeagent.cli.get_transcript_text", return_value="Transcript:\n  session: run-1"))
            get_checkpoint_text = stack.enter_context(patch("vibeagent.cli.get_checkpoint_text", return_value="Checkpoint:\n  created: yes"))
            get_checkpoints_text = stack.enter_context(patch("vibeagent.cli.get_checkpoints_text", return_value="Checkpoints:\n  total: 1"))
            get_checkpoint_show_text = stack.enter_context(patch("vibeagent.cli.get_checkpoint_show_text", return_value="Checkpoint:\n  id: ckpt-1"))
            get_checkpoint_diff_text = stack.enter_context(patch("vibeagent.cli.get_checkpoint_diff_text", return_value="Checkpoint diff:\n  id: ckpt-1"))
            get_checkpoint_status_text = stack.enter_context(patch("vibeagent.cli.get_checkpoint_status_text", return_value="Checkpoint status:\n  matches: yes"))
            get_check_checkpoint_restore_text = stack.enter_context(patch("vibeagent.cli.get_check_checkpoint_restore_text", return_value="Check checkpoint restore:\n  ok: yes"))
            get_checkpoint_restore_text = stack.enter_context(patch("vibeagent.cli.get_checkpoint_restore_text", return_value="Checkpoint restore:\n  restored: yes"))
            get_check_checkpoint_delete_text = stack.enter_context(patch("vibeagent.cli.get_check_checkpoint_delete_text", return_value="Check checkpoint delete:\n  canDelete: yes"))
            get_checkpoint_delete_text = stack.enter_context(patch("vibeagent.cli.get_checkpoint_delete_text", return_value="Checkpoint delete:\n  deleted: yes"))
            get_check_checkpoint_prune_text = stack.enter_context(patch("vibeagent.cli.get_check_checkpoint_prune_text", return_value="Check checkpoint prune:\n  deleteCount: 2"))
            get_checkpoint_prune_text = stack.enter_context(patch("vibeagent.cli.get_checkpoint_prune_text", return_value="Checkpoint prune:\n  deleted: 2"))
            stack.enter_context(patch("vibeagent.cli.get_resume_context", return_value=("run-1", "context", "Resume context loaded from session run-1.")))
            stack.enter_context(patch("vibeagent.cli.get_compact_context", return_value=("run-1", "context", "Compacted context loaded from session run-1.")))
            stack.enter_context(patch("vibeagent.cli.get_context_text", return_value="Context:\n  resume: run-1"))
            stack.enter_context(patch("vibeagent.cli.init_project_instructions", return_value="Created AGENTS.md."))
            stack.enter_context(redirect_stdout(stdout))
            exit_code = main()

        output = stdout.getvalue()
        self.assertEqual(exit_code, 0)
        self.assertIn("Recent sessions:", output)
        self.assertIn("Usage:", output)
        self.assertIn("Cost:", output)
        self.assertIn("Doctor:", output)
        self.assertIn("Config:", output)
        self.assertIn("Review:", output)
        self.assertIn("Handoff:", output)
        self.assertIn("Changes:", output)
        self.assertIn("Diff:", output)
        self.assertIn("Diff hunks:", output)
        self.assertIn("Diff contexts:", output)
        self.assertIn("Tools:", output)
        self.assertIn("Tool: read_file", output)
        self.assertIn("Tool search:", output)
        self.assertIn("Permissions:", output)
        self.assertIn("Checks:", output)
        self.assertIn("Project commands:", output)
        self.assertIn("Related tests:", output)
        self.assertIn("Focused test commands:", output)
        self.assertIn("Check focused test commands:", output)
        self.assertIn("Run focused test commands:", output)
        self.assertIn("Manifests:", output)
        self.assertIn("Command check:", output)
        self.assertIn("Run:", output)
        self.assertIn("Check run sequence:", output)
        self.assertIn("Run sequence:", output)
        self.assertIn("Check start:", output)
        self.assertIn("Start:", output)
        self.assertIn("Port:", output)
        self.assertIn("HTTP:", output)
        self.assertIn("Overview:", output)
        self.assertIn("Repo map:", output)
        self.assertIn("Search:", output)
        self.assertIn("Search contexts:", output)
        self.assertIn("Glob:", output)
        self.assertIn("Tree:", output)
        self.assertIn("Symbols:", output)
        self.assertIn("File info:", output)
        self.assertIn("Read:", output)
        self.assertIn("Output contexts:", output)
        self.assertIn("Output diagnostics:", output)
        self.assertIn("Python traceback:", output)
        self.assertIn("Read files:", output)
        self.assertIn("Read ranges:", output)
        self.assertIn("Python check:", output)
        self.assertIn("Python dependencies:", output)
        self.assertIn("Python definitions:", output)
        self.assertIn("Python references:", output)
        self.assertIn("Python reference contexts:", output)
        self.assertIn("Python calls:", output)
        self.assertIn("Python call graph:", output)
        self.assertIn("Python rename preview:", output)
        self.assertIn("Python rename:", output)
        self.assertIn("Config check:", output)
        self.assertIn("Check JSON set:", output)
        self.assertIn("JSON set:", output)
        self.assertIn("Check JSON remove:", output)
        self.assertIn("JSON remove:", output)
        self.assertIn("Check write:", output)
        self.assertIn("Write:", output)
        self.assertIn("Check write files:", output)
        self.assertIn("Write files:", output)
        self.assertIn("Check edit:", output)
        self.assertIn("Edit:", output)
        self.assertIn("Check multi edit:", output)
        self.assertIn("Multi edit:", output)
        self.assertIn("Check delete:", output)
        self.assertIn("Delete:", output)
        self.assertIn("Check delete files:", output)
        self.assertIn("Delete files:", output)
        self.assertIn("Check move:", output)
        self.assertIn("Move:", output)
        self.assertIn("Check move files:", output)
        self.assertIn("Move files:", output)
        self.assertIn("Check copy:", output)
        self.assertIn("Copy:", output)
        self.assertIn("Check copy files:", output)
        self.assertIn("Copy files:", output)
        self.assertIn("Check move dir:", output)
        self.assertIn("Move dir:", output)
        self.assertIn("Check move dirs:", output)
        self.assertIn("Move dirs:", output)
        self.assertIn("Check copy dir:", output)
        self.assertIn("Copy dir:", output)
        self.assertIn("Check copy dirs:", output)
        self.assertIn("Copy dirs:", output)
        self.assertIn("Check mkdir:", output)
        self.assertIn("Mkdir:", output)
        self.assertIn("Check mkdirs:", output)
        self.assertIn("Mkdirs:", output)
        self.assertIn("Check rmdir:", output)
        self.assertIn("Rmdir:", output)
        self.assertIn("Check rmdirs:", output)
        self.assertIn("Rmdirs:", output)
        self.assertIn("Check executable:", output)
        self.assertIn("Set executable:", output)
        self.assertIn("Check patch:", output)
        self.assertIn("Patch:", output)
        self.assertIn("Check patches:", output)
        self.assertIn("Patches:", output)
        self.assertIn("Code dependencies:", output)
        self.assertIn("Code references:", output)
        self.assertIn("Code reference contexts:", output)
        self.assertIn("Code definitions:", output)
        self.assertIn("Code rename preview:", output)
        self.assertIn("Code rename:", output)
        self.assertIn("Git status:", output)
        self.assertIn("Git conflicts:", output)
        self.assertIn("Git info:", output)
        self.assertIn("Branches:", output)
        self.assertIn("Log:", output)
        self.assertIn("Show:", output)
        self.assertIn("Blame:", output)
        self.assertIn("Stashes:", output)
        self.assertIn("Check fetch:", output)
        self.assertIn("Fetch:", output)
        self.assertIn("Check pull:", output)
        self.assertIn("Pull:", output)
        self.assertIn("Check push:", output)
        self.assertIn("Push:", output)
        self.assertIn("Check stash:", output)
        self.assertIn("Stash:", output)
        self.assertIn("Check stash apply:", output)
        self.assertIn("Stash apply:", output)
        self.assertIn("Check stash drop:", output)
        self.assertIn("Stash drop:", output)
        self.assertIn("Check stage:", output)
        self.assertIn("Stage:", output)
        self.assertIn("Check unstage:", output)
        self.assertIn("Unstage:", output)
        self.assertIn("Check commit:", output)
        self.assertIn("Commit:", output)
        self.assertIn("Check restore:", output)
        self.assertIn("Restore:", output)
        self.assertIn("Check switch:", output)
        self.assertIn("Switch:", output)
        self.assertIn("Environment:", output)
        self.assertIn("Processes:", output)
        self.assertIn("Process:", output)
        self.assertIn("Process output contexts:", output)
        self.assertIn("Process output diagnostics:", output)
        self.assertIn("Wait process:", output)
        self.assertIn("Write process:", output)
        self.assertIn("Check stop process:", output)
        self.assertIn("Stop process:", output)
        self.assertIn("Check stop processes:", output)
        self.assertIn("Stop processes:", output)
        self.assertIn("Session: run-1", output)
        self.assertIn("Plan:", output)
        self.assertIn("Transcript:", output)
        self.assertIn("Checkpoint:", output)
        self.assertIn("Checkpoints:", output)
        self.assertIn("Checkpoint diff:", output)
        self.assertIn("Checkpoint status:", output)
        self.assertIn("Check checkpoint restore:", output)
        self.assertIn("Checkpoint restore:", output)
        self.assertIn("Check checkpoint delete:", output)
        self.assertIn("Checkpoint delete:", output)
        self.assertIn("Check checkpoint prune:", output)
        self.assertIn("Checkpoint prune:", output)
        self.assertIn("Resume context loaded", output)
        self.assertIn("Compacted context loaded", output)
        self.assertIn("Context:", output)
        self.assertIn("Created AGENTS.md.", output)
        self.assertIn("Cleared chat history and resume context.", output)
        get_session_text.assert_called_once_with("run-1")
        get_plan_text.assert_called_once_with(run_id="run-1")
        get_transcript_text.assert_called_once_with(run_id="run-1")
        get_checkpoint_text.assert_called_once_with(label="before tests")
        get_checkpoints_text.assert_called_once_with()
        get_checkpoint_show_text.assert_called_once_with("ckpt-1")
        get_checkpoint_diff_text.assert_called_once_with("ckpt-1")
        get_checkpoint_status_text.assert_called_once_with("ckpt-1")
        get_check_checkpoint_restore_text.assert_called_once_with("ckpt-1")
        get_checkpoint_restore_text.assert_called_once_with("ckpt-1")
        get_check_checkpoint_delete_text.assert_called_once_with("ckpt-1")
        get_checkpoint_delete_text.assert_called_once_with("ckpt-1")
        get_check_checkpoint_prune_text.assert_called_once_with("2")
        get_checkpoint_prune_text.assert_called_once_with("2")
        get_diff_text.assert_called_once_with(argument="--staged app.py", max_chars=12000)
        get_diff_hunks_text.assert_called_once_with(argument="--staged app.py")
        get_diff_contexts_text.assert_called_once_with(argument="--staged app.py")
        get_config_text.assert_called_once_with()
        get_handoff_text.assert_called_once_with()
        get_changes_text.assert_called_once_with()
        get_tool_search_text.assert_called_once_with("verification", max_matches=3, category="session", approval_required=False)
        get_permissions_text.assert_called_once_with("ask", Path.cwd())
        get_checks_text.assert_called_once_with()
        get_commands_text.assert_called_once_with()
        get_related_tests_text.assert_called_once_with(argument="pkg/actions.py")
        get_focused_test_commands_text.assert_called_once_with(argument="pkg/actions.py")
        get_check_focused_test_commands_text.assert_called_once_with(argument="pkg/actions.py")
        get_run_focused_test_commands_text.assert_called_once_with(argument="pkg/actions.py", timeout_ms=30000, max_output_chars=12000)
        get_manifests_text.assert_called_once_with()
        get_command_check_text.assert_called_once_with(command="python3 --version")
        get_run_text.assert_called_once_with(command="python3 --version")
        get_check_run_sequence_text.assert_called_once_with(argument="python3 --version ;; npm test")
        get_run_sequence_text.assert_called_once_with(argument="python3 --version ;; npm test")
        get_check_start_text.assert_called_once_with(command="npm run dev")
        get_start_text.assert_called_once_with(command="npm run dev")
        get_port_text.assert_called_once_with(argument="5173 127.0.0.1 1500")
        get_http_text.assert_called_once_with(argument="http://127.0.0.1:5173 ready")
        get_http_fetch_text.assert_called_once_with(argument="http://127.0.0.1:5173/app")
        get_overview_text.assert_called_once_with()
        get_repo_map_text.assert_called_once_with(path="src")
        get_search_text.assert_called_once_with(query="needle")
        get_search_contexts_text.assert_called_once_with(query="needle")
        get_glob_text.assert_called_once_with(pattern="**/*.py")
        get_tree_text.assert_called_once_with(path="src")
        get_symbols_text.assert_called_once_with(argument="src/app.py web/app.ts")
        get_file_info_text.assert_called_once_with(argument="src/app.py asset.bin")
        get_image_info_text.assert_called_once_with(argument="assets/logo.png")
        get_read_text.assert_called_once_with(argument="src/app.py 2:4")
        get_around_text.assert_called_once_with(argument="src/app.py 42 8")
        get_around_many_text.assert_called_once_with(argument="src/app.py:42:8 tests/test_app.py:17")
        get_output_contexts_text.assert_called_once_with(text="src/app.py:42:8")
        get_output_diagnostics_text.assert_called_once_with(text="ERROR src/app.py:42:8 failed")
        get_python_traceback_text.assert_called_once_with(text="ValueError: bad")
        get_tail_text.assert_called_once_with(argument="logs/app.log 3")
        get_read_files_text.assert_called_once_with(argument="src/app.py tests/test_app.py")
        get_read_ranges_text.assert_called_once_with(argument="src/app.py:2:4 tests/test_app.py:1")
        get_python_check_text.assert_called_once_with(argument="src")
        get_python_deps_text.assert_called_once_with(argument="src")
        get_python_defs_text.assert_called_once_with(argument="Runner.run src")
        get_python_refs_text.assert_called_once_with(argument="run_agent src")
        get_python_ref_contexts_text.assert_called_once_with(argument="run_agent src")
        get_python_calls_text.assert_called_once_with(argument="helper src")
        get_python_call_graph_text.assert_called_once_with(argument="src")
        get_python_rename_preview_text.assert_called_once_with(argument="run_agent execute_agent src")
        get_python_rename_text.assert_called_once_with(argument="run_agent execute_agent src")
        get_check_replace_python_definition_text.assert_called_once_with(argument="Runner.run '    def run(self):\\n        return 2\\n' src")
        get_replace_python_definition_text.assert_called_once_with(argument="Runner.run '    def run(self):\\n        return 2\\n' src")
        get_config_check_text.assert_called_once_with(argument="pyproject.toml")
        get_check_json_set_text.assert_called_once_with(argument="package.json /private true")
        get_json_set_text.assert_called_once_with(argument="package.json /scripts/test '\"npm test\"'")
        get_check_json_remove_text.assert_called_once_with(argument="package.json /scripts/dev")
        get_json_remove_text.assert_called_once_with(argument="package.json /keywords/0")
        get_check_json_patch_text.assert_called_once_with(argument="package.json '[{\"op\":\"replace\",\"path\":\"/private\",\"value\":true}]'")
        get_json_patch_text.assert_called_once_with(argument="package.json '[{\"op\":\"remove\",\"path\":\"/keywords/0\"}]'")
        get_check_replace_lines_text.assert_called_once_with(argument="app.py 2 3 'new\\n'")
        get_replace_lines_text.assert_called_once_with(argument="app.py 2 2 'new\\n'")
        get_check_insert_lines_text.assert_called_once_with(argument="app.py 2 'new\\n'")
        get_insert_lines_text.assert_called_once_with(argument="app.py 2 'new\\n'")
        get_check_append_file_text.assert_called_once_with(argument="app.py 'new\\n'")
        get_append_file_text.assert_called_once_with(argument="app.py 'new\\n'")
        get_check_write_file_text.assert_called_once_with(argument="app.py 'new\\n'")
        get_write_file_text.assert_called_once_with(argument="app.py 'new\\n'")
        get_check_write_files_text.assert_called_once_with(argument="app.py 'a\\n' test.py 'b\\n'")
        get_write_files_text.assert_called_once_with(argument="app.py 'a\\n' test.py 'b\\n'")
        get_check_edit_file_text.assert_called_once_with(argument="app.py old new")
        get_edit_file_text.assert_called_once_with(argument="app.py old new")
        get_check_multi_edit_file_text.assert_called_once_with(argument="app.py old new print log")
        get_multi_edit_file_text.assert_called_once_with(argument="app.py old new print log")
        get_check_delete_file_text.assert_called_once_with(argument="old.py")
        get_delete_file_text.assert_called_once_with(argument="old.py")
        get_check_delete_files_text.assert_called_once_with(argument="old.py other.py")
        get_delete_files_text.assert_called_once_with(argument="old.py other.py")
        get_check_move_file_text.assert_called_once_with(argument="old.py new.py")
        get_move_file_text.assert_called_once_with(argument="old.py new.py")
        get_check_move_files_text.assert_called_once_with(argument="old.py new.py other.py other-new.py")
        get_move_files_text.assert_called_once_with(argument="old.py new.py other.py other-new.py")
        get_check_copy_file_text.assert_called_once_with(argument="template.py new.py")
        get_copy_file_text.assert_called_once_with(argument="template.py new.py")
        get_check_copy_files_text.assert_called_once_with(argument="template.py new.py config.py config-copy.py")
        get_copy_files_text.assert_called_once_with(argument="template.py new.py config.py config-copy.py")
        get_check_move_dir_text.assert_called_once_with(argument="old_pkg new_pkg")
        get_move_dir_text.assert_called_once_with(argument="old_pkg new_pkg")
        get_check_move_dirs_text.assert_called_once_with(argument="old_a new_a old_b new_b")
        get_move_dirs_text.assert_called_once_with(argument="old_a new_a old_b new_b")
        get_check_copy_dir_text.assert_called_once_with(argument="template_pkg copy_pkg")
        get_copy_dir_text.assert_called_once_with(argument="template_pkg copy_pkg")
        get_check_copy_dirs_text.assert_called_once_with(argument="template_a copy_a template_b copy_b")
        get_copy_dirs_text.assert_called_once_with(argument="template_a copy_a template_b copy_b")
        get_check_create_dir_text.assert_called_once_with(argument="pkg/generated")
        get_create_dir_text.assert_called_once_with(argument="pkg/generated")
        get_check_create_dirs_text.assert_called_once_with(argument="pkg/generated assets/icons")
        get_create_dirs_text.assert_called_once_with(argument="pkg/generated assets/icons")
        get_check_delete_empty_dir_text.assert_called_once_with(argument="pkg/generated")
        get_delete_empty_dir_text.assert_called_once_with(argument="pkg/generated")
        get_check_delete_empty_dirs_text.assert_called_once_with(argument="pkg/generated assets/icons")
        get_delete_empty_dirs_text.assert_called_once_with(argument="pkg/generated assets/icons")
        get_check_set_executable_text.assert_called_once_with(argument="tool.sh false")
        get_set_executable_text.assert_called_once_with(argument="tool.sh true")
        get_check_patch_text.assert_called_once_with(argument="app.py '@@ -1 +1 @@\\n-old\\n+new\\n'")
        get_patch_text.assert_called_once_with(argument="app.py '@@ -1 +1 @@\\n-old\\n+new\\n'")
        get_check_patches_text.assert_called_once_with(argument="'--- a/app.py\\n+++ b/app.py\\n@@ -1 +1 @@\\n-old\\n+new\\n'")
        get_patches_text.assert_called_once_with(argument="'--- a/app.py\\n+++ b/app.py\\n@@ -1 +1 @@\\n-old\\n+new\\n'")
        get_check_regex_replace_text.assert_called_once_with(argument="--ignore-case app.py old new")
        get_regex_replace_text.assert_called_once_with(argument="--count 1 app.py old new")
        get_code_deps_text.assert_called_once_with(argument="web")
        get_code_refs_text.assert_called_once_with(argument="runAgent web")
        get_code_ref_contexts_text.assert_called_once_with(argument="runAgent web")
        get_code_defs_text.assert_called_once_with(argument="runAgent web")
        get_code_rename_preview_text.assert_called_once_with(argument="runAgent executeAgent web")
        get_code_rename_text.assert_called_once_with(argument="runAgent executeAgent web")
        get_git_status_text.assert_called_once_with()
        get_git_conflicts_text.assert_called_once_with(argument="src")
        get_git_info_text.assert_called_once_with()
        get_branches_text.assert_called_once_with()
        get_log_text.assert_called_once_with(argument="app.py 2")
        get_show_text.assert_called_once_with(argument="HEAD app.py")
        get_blame_text.assert_called_once_with(argument="app.py 2:2")
        get_stashes_text.assert_called_once_with(argument="3")
        get_check_fetch_text.assert_called_once_with(argument="origin")
        get_fetch_text.assert_called_once_with(argument="origin")
        get_check_pull_text.assert_called_once_with()
        get_pull_text.assert_called_once_with()
        get_check_push_text.assert_called_once_with()
        get_push_text.assert_called_once_with()
        get_check_stash_text.assert_called_once_with(argument="--include-untracked save work")
        get_stash_text.assert_called_once_with(argument="save work")
        get_check_stash_apply_text.assert_called_once_with(argument="stash@{0}")
        get_stash_apply_text.assert_called_once_with(argument="stash@{0}")
        get_check_stash_drop_text.assert_called_once_with(argument="stash@{0}")
        get_stash_drop_text.assert_called_once_with(argument="stash@{0}")
        get_check_stage_text.assert_called_once_with(argument="app.py")
        get_stage_text.assert_called_once_with(argument="app.py")
        get_check_unstage_text.assert_called_once_with(argument="app.py")
        get_unstage_text.assert_called_once_with(argument="app.py")
        get_check_commit_text.assert_called_once_with(argument="update app")
        get_commit_text.assert_called_once_with(argument="update app")
        get_check_restore_text.assert_called_once_with(argument="app.py")
        get_restore_text.assert_called_once_with(argument="app.py")
        get_check_switch_text.assert_called_once_with(argument="--create feature/demo")
        get_switch_text.assert_called_once_with(argument="feature/demo")
        get_env_text.assert_called_once_with()
        get_processes_text.assert_called_once_with()
        get_process_text.assert_called_once_with(argument="bg-1 2000")
        get_process_output_contexts_text.assert_called_once_with(process_id="bg-1", max_output_chars=2000)
        get_process_output_diagnostics_text.assert_called_once_with(process_id="bg-1", max_output_chars=2000)
        get_wait_process_text.assert_called_once_with(process_id="bg-1", timeout_ms=5000, max_output_chars=2000)
        get_check_write_process_text.assert_called_once_with(argument="bg-1 hello\\n")
        get_write_process_text.assert_called_once_with(argument="bg-1 hello\\n")
        get_check_stop_process_text.assert_called_once_with(process_id="bg-1")
        get_stop_process_text.assert_called_once_with(process_id="bg-1")
        get_check_stop_all_processes_text.assert_called_once_with()
        get_stop_all_processes_text.assert_called_once_with()
        create_chat_client.assert_not_called()

    def test_main_parses_interactive_checks_options(self) -> None:
        stdout = io.StringIO()

        with (
            patch(
                "builtins.input",
                side_effect=[
                    "/checks --max-checks 2",
                    "/checks --max-checks=3",
                    "/exit",
                ],
            ),
            patch("vibeagent.cli.create_chat_client") as create_chat_client,
            patch("vibeagent.cli.get_checks_text", return_value="Checks:\n  suggestedChecks: 1/2") as get_checks_text,
            redirect_stdout(stdout),
        ):
            exit_code = main()

        output = stdout.getvalue()
        self.assertEqual(exit_code, 0)
        self.assertIn("Checks:", output)
        get_checks_text.assert_has_calls(
            [
                call(max_checks=2),
                call(max_checks=3),
            ]
        )
        create_chat_client.assert_not_called()

    def test_main_reports_interactive_checks_option_errors(self) -> None:
        stdout = io.StringIO()

        with (
            patch(
                "builtins.input",
                side_effect=[
                    "/checks --max-checks 0",
                    "/checks --unknown 1",
                    "/checks package.json",
                    "/exit",
                ],
            ),
            patch("vibeagent.cli.create_chat_client") as create_chat_client,
            patch("vibeagent.cli.get_checks_text") as get_checks_text,
            redirect_stdout(stdout),
        ):
            exit_code = main()

        output = stdout.getvalue()
        self.assertEqual(exit_code, 0)
        self.assertIn("Usage: /checks [--max-checks N]", output)
        self.assertIn("--max-checks must be a positive integer.", output)
        self.assertIn("Unknown option: --unknown", output)
        get_checks_text.assert_not_called()
        create_chat_client.assert_not_called()

    def test_main_parses_interactive_commands_options(self) -> None:
        stdout = io.StringIO()

        with (
            patch(
                "builtins.input",
                side_effect=[
                    "/commands --max-commands 2 --max-files 3",
                    "/commands --max-commands=4 --max-files=5",
                    "/exit",
                ],
            ),
            patch("vibeagent.cli.create_chat_client") as create_chat_client,
            patch("vibeagent.cli.get_commands_text", return_value="Project commands:\n  commands: 1/2") as get_commands_text,
            redirect_stdout(stdout),
        ):
            exit_code = main()

        output = stdout.getvalue()
        self.assertEqual(exit_code, 0)
        self.assertIn("Project commands:", output)
        get_commands_text.assert_has_calls(
            [
                call(max_commands=2, max_files=3),
                call(max_commands=4, max_files=5),
            ]
        )
        create_chat_client.assert_not_called()

    def test_main_reports_interactive_commands_option_errors(self) -> None:
        stdout = io.StringIO()

        with (
            patch(
                "builtins.input",
                side_effect=[
                    "/commands --max-commands 0",
                    "/commands --max-files 0",
                    "/commands --unknown 1",
                    "/commands package.json",
                    "/exit",
                ],
            ),
            patch("vibeagent.cli.create_chat_client") as create_chat_client,
            patch("vibeagent.cli.get_commands_text") as get_commands_text,
            redirect_stdout(stdout),
        ):
            exit_code = main()

        output = stdout.getvalue()
        self.assertEqual(exit_code, 0)
        self.assertIn("Usage: /commands [--max-commands N] [--max-files N]", output)
        self.assertIn("--max-commands must be a positive integer.", output)
        self.assertIn("--max-files must be a positive integer.", output)
        self.assertIn("Unknown option: --unknown", output)
        get_commands_text.assert_not_called()
        create_chat_client.assert_not_called()

    def test_main_parses_interactive_agents_and_skills_options(self) -> None:
        stdout = io.StringIO()

        with (
            patch(
                "builtins.input",
                side_effect=[
                    "/agents --max-agents 2",
                    "/skills --max-skills=3",
                    "/exit",
                ],
            ),
            patch("vibeagent.cli.create_chat_client") as create_chat_client,
            patch("vibeagent.cli.get_agents_text", return_value="Available project agent profiles:\n- reviewer") as get_agents_text,
            patch("vibeagent.cli.get_skills_text", return_value="Available project skills:\n- testing") as get_skills_text,
            redirect_stdout(stdout),
        ):
            exit_code = main()

        output = stdout.getvalue()
        self.assertEqual(exit_code, 0)
        self.assertIn("Available project agent profiles:", output)
        self.assertIn("Available project skills:", output)
        get_agents_text.assert_called_once_with(max_agents=2)
        get_skills_text.assert_called_once_with(max_skills=3)
        create_chat_client.assert_not_called()

    def test_main_reports_interactive_agents_and_skills_option_errors(self) -> None:
        stdout = io.StringIO()

        with (
            patch(
                "builtins.input",
                side_effect=[
                    "/agents --max-agents 0",
                    "/skills --unknown 1",
                    "/exit",
                ],
            ),
            patch("vibeagent.cli.create_chat_client") as create_chat_client,
            patch("vibeagent.cli.get_agents_text") as get_agents_text,
            patch("vibeagent.cli.get_skills_text") as get_skills_text,
            redirect_stdout(stdout),
        ):
            exit_code = main()

        output = stdout.getvalue()
        self.assertEqual(exit_code, 0)
        self.assertIn("Usage: /agents [--max-agents N]", output)
        self.assertIn("--max-agents must be a positive integer.", output)
        self.assertIn("Usage: /skills [--max-skills N]", output)
        self.assertIn("Unknown option: --unknown", output)
        get_agents_text.assert_not_called()
        get_skills_text.assert_not_called()
        create_chat_client.assert_not_called()

    def test_main_parses_interactive_manifests_options(self) -> None:
        stdout = io.StringIO()

        with (
            patch(
                "builtins.input",
                side_effect=[
                    "/manifests --max-files 2 --max-items 10",
                    "/manifests --max-files=3 --max-items=20",
                    "/exit",
                ],
            ),
            patch("vibeagent.cli.create_chat_client") as create_chat_client,
            patch("vibeagent.cli.get_manifests_text", return_value="Manifests:\n  files: 1/2") as get_manifests_text,
            redirect_stdout(stdout),
        ):
            exit_code = main()

        output = stdout.getvalue()
        self.assertEqual(exit_code, 0)
        self.assertIn("Manifests:", output)
        get_manifests_text.assert_has_calls(
            [
                call(max_files=2, max_items=10),
                call(max_files=3, max_items=20),
            ]
        )
        create_chat_client.assert_not_called()

    def test_main_reports_interactive_manifests_option_errors(self) -> None:
        stdout = io.StringIO()

        with (
            patch(
                "builtins.input",
                side_effect=[
                    "/manifests --max-files 0",
                    "/manifests --max-items 0",
                    "/manifests --unknown 1",
                    "/manifests package.json",
                    "/exit",
                ],
            ),
            patch("vibeagent.cli.create_chat_client") as create_chat_client,
            patch("vibeagent.cli.get_manifests_text") as get_manifests_text,
            redirect_stdout(stdout),
        ):
            exit_code = main()

        output = stdout.getvalue()
        self.assertEqual(exit_code, 0)
        self.assertIn("Usage: /manifests [--max-files N] [--max-items N]", output)
        self.assertIn("--max-files must be a positive integer.", output)
        self.assertIn("--max-items must be a positive integer.", output)
        self.assertIn("Unknown option: --unknown", output)
        get_manifests_text.assert_not_called()
        create_chat_client.assert_not_called()

    def test_main_parses_interactive_todos_options(self) -> None:
        stdout = io.StringIO()

        with (
            patch(
                "builtins.input",
                side_effect=[
                    "/todos src --max-items 3 --max-files 20",
                    "/todos --max-items=4 --max-files=30 -- src",
                    "/exit",
                ],
            ),
            patch("vibeagent.cli.create_chat_client") as create_chat_client,
            patch("vibeagent.cli.get_todos_text", return_value="Project TODOs:\n  todos: 1/3") as get_todos_text,
            redirect_stdout(stdout),
        ):
            exit_code = main()

        output = stdout.getvalue()
        self.assertEqual(exit_code, 0)
        self.assertIn("Project TODOs:", output)
        get_todos_text.assert_has_calls(
            [
                call(path="src", max_items=3, max_files=20),
                call(path="src", max_items=4, max_files=30),
            ]
        )
        create_chat_client.assert_not_called()

    def test_main_parses_interactive_instructions_options(self) -> None:
        stdout = io.StringIO()

        with (
            patch(
                "builtins.input",
                side_effect=[
                    "/instructions --max-files 2 --max-bytes 1000",
                    "/instructions --max-files=3 --max-bytes=1200",
                    "/exit",
                ],
            ),
            patch("vibeagent.cli.create_chat_client") as create_chat_client,
            patch("vibeagent.cli.get_instructions_text", return_value="Project instructions:\n  files: 1/2") as get_instructions_text,
            redirect_stdout(stdout),
        ):
            exit_code = main()

        output = stdout.getvalue()
        self.assertEqual(exit_code, 0)
        self.assertIn("Project instructions:", output)
        get_instructions_text.assert_has_calls(
            [
                call(max_files=2, max_bytes=1000),
                call(max_files=3, max_bytes=1200),
            ]
        )
        create_chat_client.assert_not_called()

    def test_main_reports_interactive_instructions_option_errors(self) -> None:
        stdout = io.StringIO()

        with (
            patch(
                "builtins.input",
                side_effect=[
                    "/instructions --max-files 0",
                    "/instructions --max-bytes 0",
                    "/instructions --unknown 1",
                    "/instructions AGENTS.md",
                    "/exit",
                ],
            ),
            patch("vibeagent.cli.create_chat_client") as create_chat_client,
            patch("vibeagent.cli.get_instructions_text") as get_instructions_text,
            redirect_stdout(stdout),
        ):
            exit_code = main()

        output = stdout.getvalue()
        self.assertEqual(exit_code, 0)
        self.assertIn("Usage: /instructions [--max-files N] [--max-bytes N]", output)
        self.assertIn("--max-files must be a positive integer.", output)
        self.assertIn("--max-bytes must be a positive integer.", output)
        self.assertIn("Unknown option: --unknown", output)
        get_instructions_text.assert_not_called()
        create_chat_client.assert_not_called()

    def test_main_reports_interactive_todos_option_errors(self) -> None:
        stdout = io.StringIO()

        with (
            patch(
                "builtins.input",
                side_effect=[
                    "/todos --max-items 0 -- src",
                    "/todos --max-files 0 -- src",
                    "/todos --unknown 1 -- src",
                    "/todos src docs --max-items 2",
                    "/exit",
                ],
            ),
            patch("vibeagent.cli.create_chat_client") as create_chat_client,
            patch("vibeagent.cli.get_todos_text") as get_todos_text,
            redirect_stdout(stdout),
        ):
            exit_code = main()

        output = stdout.getvalue()
        self.assertEqual(exit_code, 0)
        self.assertIn("Usage: /todos [--max-items N] [--max-files N] -- [path]", output)
        self.assertIn("error: --max-items must be a positive integer.", output)
        self.assertIn("error: --max-files must be a positive integer.", output)
        self.assertIn("error: Unknown option: --unknown", output)
        get_todos_text.assert_not_called()
        create_chat_client.assert_not_called()

    def test_main_parses_interactive_python_symbol_options(self) -> None:
        stdout = io.StringIO()

        with (
            patch(
                "builtins.input",
                side_effect=[
                    "/python-defs --path src --max-matches 3 --max-lines 40 -- Runner.run",
                    "/python-refs run_agent --path src --max-matches 4",
                    "/python-ref-contexts --path src --max-matches 5 --context-lines 1 --max-bytes 1000 -- run_agent",
                    "/python-calls helper src --max-matches 6",
                    "/exit",
                ],
            ),
            patch("vibeagent.cli.create_chat_client") as create_chat_client,
            patch("vibeagent.cli.get_python_defs_text", return_value="Python definitions:\n  definitions: 1/1") as get_python_defs_text,
            patch("vibeagent.cli.get_python_refs_text", return_value="Python references:\n  references: 1/1") as get_python_refs_text,
            patch("vibeagent.cli.get_python_ref_contexts_text", return_value="Python reference contexts:\n  contexts: 1/1") as get_python_ref_contexts_text,
            patch("vibeagent.cli.get_python_calls_text", return_value="Python calls:\n  calls: 1/1") as get_python_calls_text,
            redirect_stdout(stdout),
        ):
            exit_code = main()

        output = stdout.getvalue()
        self.assertEqual(exit_code, 0)
        self.assertIn("Python definitions:", output)
        self.assertIn("Python references:", output)
        self.assertIn("Python reference contexts:", output)
        self.assertIn("Python calls:", output)
        get_python_defs_text.assert_called_once_with(symbol="Runner.run", path="src", max_matches=3, max_lines=40)
        get_python_refs_text.assert_called_once_with(symbol="run_agent", path="src", max_matches=4)
        get_python_ref_contexts_text.assert_called_once_with(
            symbol="run_agent",
            path="src",
            max_matches=5,
            context_lines=1,
            max_bytes_per_context=1000,
        )
        get_python_calls_text.assert_called_once_with(symbol="helper", path="src", max_matches=6)
        create_chat_client.assert_not_called()

    def test_main_parses_interactive_python_deps_options(self) -> None:
        stdout = io.StringIO()

        with (
            patch(
                "builtins.input",
                side_effect=[
                    "/python-deps --max-files 2 --max-imports=7 -- src",
                    "/exit",
                ],
            ),
            patch("vibeagent.cli.create_chat_client") as create_chat_client,
            patch(
                "vibeagent.cli.get_python_deps_text",
                return_value="Python dependencies:\n  files: 1/1",
            ) as get_python_deps_text,
            redirect_stdout(stdout),
        ):
            exit_code = main()

        output = stdout.getvalue()
        self.assertEqual(exit_code, 0)
        self.assertIn("Python dependencies:", output)
        get_python_deps_text.assert_called_once_with(argument="src", max_files=2, max_imports=7)
        create_chat_client.assert_not_called()

    def test_main_parses_interactive_python_call_graph_options(self) -> None:
        stdout = io.StringIO()

        with (
            patch(
                "builtins.input",
                side_effect=[
                    "/python-call-graph --max-files 2 --max-edges=7 -- src",
                    "/exit",
                ],
            ),
            patch("vibeagent.cli.create_chat_client") as create_chat_client,
            patch("vibeagent.cli.get_python_call_graph_text", return_value="Python call graph:\n  edges: 3/3") as get_python_call_graph_text,
            redirect_stdout(stdout),
        ):
            exit_code = main()

        output = stdout.getvalue()
        self.assertEqual(exit_code, 0)
        self.assertIn("Python call graph:", output)
        get_python_call_graph_text.assert_called_once_with(argument="src", max_files=2, max_edges=7)
        create_chat_client.assert_not_called()

    def test_main_reports_interactive_python_symbol_option_errors(self) -> None:
        stdout = io.StringIO()

        with (
            patch(
                "builtins.input",
                side_effect=[
                    "/python-defs --max-matches 0 -- Runner.run",
                    "/python-defs --max-lines 0 -- Runner.run",
                    "/python-defs --path src Runner.run src",
                    "/python-refs --max-matches 0 -- run_agent",
                    "/python-ref-contexts --context-lines -1 -- run_agent",
                    "/python-ref-contexts --max-bytes 0 -- run_agent",
                    "/python-ref-contexts --unknown 1 -- run_agent",
                    "/python-calls --max-matches 0 -- helper",
                    "/exit",
                ],
            ),
            patch("vibeagent.cli.create_chat_client") as create_chat_client,
            patch("vibeagent.cli.get_python_defs_text") as get_python_defs_text,
            patch("vibeagent.cli.get_python_refs_text") as get_python_refs_text,
            patch("vibeagent.cli.get_python_ref_contexts_text") as get_python_ref_contexts_text,
            patch("vibeagent.cli.get_python_calls_text") as get_python_calls_text,
            redirect_stdout(stdout),
        ):
            exit_code = main()

        output = stdout.getvalue()
        self.assertEqual(exit_code, 0)
        self.assertIn("Usage: /python-defs [--path PATH] [--max-matches N] [--max-lines N] -- <symbol> [path]", output)
        self.assertIn("Usage: /python-refs [--path PATH] [--max-matches N] -- <symbol> [path]", output)
        self.assertIn(
            "Usage: /python-ref-contexts [--path PATH] [--max-matches N] [--context-lines N] [--max-bytes N] -- <symbol> [path]",
            output,
        )
        self.assertIn("Usage: /python-calls [--path PATH] [--max-matches N] -- <symbol> [path]", output)
        self.assertIn("error: --max-matches must be a positive integer.", output)
        self.assertIn("error: --max-lines must be a positive integer.", output)
        self.assertIn("error: path can only be provided once.", output)
        self.assertIn("error: --context-lines must be a non-negative integer.", output)
        self.assertIn("error: --max-bytes must be a positive integer.", output)
        self.assertIn("error: Unknown option: --unknown", output)
        get_python_defs_text.assert_not_called()
        get_python_refs_text.assert_not_called()
        get_python_ref_contexts_text.assert_not_called()
        get_python_calls_text.assert_not_called()
        create_chat_client.assert_not_called()

    def test_main_reports_interactive_python_deps_option_errors(self) -> None:
        stdout = io.StringIO()

        with (
            patch(
                "builtins.input",
                side_effect=[
                    "/python-deps --max-files 0 -- src",
                    "/python-deps --max-imports 0 -- src",
                    "/python-deps --unknown 1 -- src",
                    "/python-deps src tests --max-files 2",
                    "/exit",
                ],
            ),
            patch("vibeagent.cli.create_chat_client") as create_chat_client,
            patch("vibeagent.cli.get_python_deps_text") as get_python_deps_text,
            redirect_stdout(stdout),
        ):
            exit_code = main()

        output = stdout.getvalue()
        self.assertEqual(exit_code, 0)
        self.assertIn("Usage: /python-deps [--max-files N] [--max-imports N] -- [path]", output)
        self.assertIn("error: --max-files must be a positive integer.", output)
        self.assertIn("error: --max-imports must be a positive integer.", output)
        self.assertIn("error: Unknown option: --unknown", output)
        get_python_deps_text.assert_not_called()
        create_chat_client.assert_not_called()

    def test_main_reports_interactive_python_call_graph_option_errors(self) -> None:
        stdout = io.StringIO()

        with (
            patch(
                "builtins.input",
                side_effect=[
                    "/python-call-graph --max-files 0 -- src",
                    "/python-call-graph --max-edges 0 -- src",
                    "/python-call-graph --unknown 1 -- src",
                    "/python-call-graph src tests --max-files 2",
                    "/exit",
                ],
            ),
            patch("vibeagent.cli.create_chat_client") as create_chat_client,
            patch("vibeagent.cli.get_python_call_graph_text") as get_python_call_graph_text,
            redirect_stdout(stdout),
        ):
            exit_code = main()

        output = stdout.getvalue()
        self.assertEqual(exit_code, 0)
        self.assertIn("Usage: /python-call-graph [--max-files N] [--max-edges N] -- [path]", output)
        self.assertIn("error: --max-files must be a positive integer.", output)
        self.assertIn("error: --max-edges must be a positive integer.", output)
        self.assertIn("error: Unknown option: --unknown", output)
        get_python_call_graph_text.assert_not_called()
        create_chat_client.assert_not_called()

    def test_main_parses_interactive_code_symbol_options(self) -> None:
        stdout = io.StringIO()

        with (
            patch(
                "builtins.input",
                side_effect=[
                    "/code-refs runAgent --path web --max-matches 4",
                    "/code-ref-contexts --path web --max-matches 5 --context-lines 1 --max-bytes 1000 -- runAgent",
                    "/code-defs --path web --max-matches 6 --max-lines 40 -- runAgent",
                    "/exit",
                ],
            ),
            patch("vibeagent.cli.create_chat_client") as create_chat_client,
            patch("vibeagent.cli.get_code_refs_text", return_value="Code references:\n  references: 1/1") as get_code_refs_text,
            patch("vibeagent.cli.get_code_ref_contexts_text", return_value="Code reference contexts:\n  contexts: 1/1") as get_code_ref_contexts_text,
            patch("vibeagent.cli.get_code_defs_text", return_value="Code definitions:\n  definitions: 1/1") as get_code_defs_text,
            redirect_stdout(stdout),
        ):
            exit_code = main()

        output = stdout.getvalue()
        self.assertEqual(exit_code, 0)
        self.assertIn("Code references:", output)
        self.assertIn("Code reference contexts:", output)
        self.assertIn("Code definitions:", output)
        get_code_refs_text.assert_called_once_with(symbol="runAgent", path="web", max_matches=4)
        get_code_ref_contexts_text.assert_called_once_with(
            symbol="runAgent",
            path="web",
            max_matches=5,
            context_lines=1,
            max_bytes_per_context=1000,
        )
        get_code_defs_text.assert_called_once_with(symbol="runAgent", path="web", max_matches=6, max_lines=40)
        create_chat_client.assert_not_called()

    def test_main_reports_interactive_code_symbol_option_errors(self) -> None:
        stdout = io.StringIO()

        with (
            patch(
                "builtins.input",
                side_effect=[
                    "/code-refs --max-matches 0 -- runAgent",
                    "/code-ref-contexts --context-lines -1 -- runAgent",
                    "/code-ref-contexts --max-bytes 0 -- runAgent",
                    "/code-ref-contexts --unknown 1 -- runAgent",
                    "/code-defs --max-lines 0 -- runAgent",
                    "/code-defs --path web runAgent web",
                    "/exit",
                ],
            ),
            patch("vibeagent.cli.create_chat_client") as create_chat_client,
            patch("vibeagent.cli.get_code_refs_text") as get_code_refs_text,
            patch("vibeagent.cli.get_code_ref_contexts_text") as get_code_ref_contexts_text,
            patch("vibeagent.cli.get_code_defs_text") as get_code_defs_text,
            redirect_stdout(stdout),
        ):
            exit_code = main()

        output = stdout.getvalue()
        self.assertEqual(exit_code, 0)
        self.assertIn("Usage: /code-refs [--path PATH] [--max-matches N] -- <symbol> [path]", output)
        self.assertIn(
            "Usage: /code-ref-contexts [--path PATH] [--max-matches N] [--context-lines N] [--max-bytes N] -- <symbol> [path]",
            output,
        )
        self.assertIn("Usage: /code-defs [--path PATH] [--max-matches N] [--max-lines N] -- <symbol> [path]", output)
        self.assertIn("error: --max-matches must be a positive integer.", output)
        self.assertIn("error: --context-lines must be a non-negative integer.", output)
        self.assertIn("error: --max-bytes must be a positive integer.", output)
        self.assertIn("error: Unknown option: --unknown", output)
        self.assertIn("error: --max-lines must be a positive integer.", output)
        self.assertIn("error: path can only be provided once.", output)
        get_code_refs_text.assert_not_called()
        get_code_ref_contexts_text.assert_not_called()
        get_code_defs_text.assert_not_called()
        create_chat_client.assert_not_called()

    def test_main_parses_interactive_session_timeline_limit_options(self) -> None:
        stdout = io.StringIO()

        with (
            patch(
                "builtins.input",
                side_effect=[
                    "/transcript run-1 --max-events 3 --max-text 120",
                    '/session-search --run run-1 --max-matches 4 --case-sensitive --max-text 140 "Missing config"',
                    "/exit",
                ],
            ),
            patch("vibeagent.cli.create_chat_client") as create_chat_client,
            patch("vibeagent.cli.get_transcript_text", return_value="Transcript:\n  session: run-1") as get_transcript_text,
            patch("vibeagent.cli.get_session_search_text", return_value="Session search:\n  session: run-1") as get_session_search_text,
            redirect_stdout(stdout),
        ):
            exit_code = main()

        output = stdout.getvalue()
        self.assertEqual(exit_code, 0)
        self.assertIn("Transcript:", output)
        self.assertIn("Session search:", output)
        get_transcript_text.assert_called_once_with(run_id="run-1", max_events=3, max_text=120)
        get_session_search_text.assert_called_once_with(
            argument="Missing config",
            run_id="run-1",
            max_matches=4,
            case_sensitive=True,
            max_text=140,
        )
        create_chat_client.assert_not_called()

    def test_main_reports_interactive_session_timeline_limit_errors(self) -> None:
        stdout = io.StringIO()

        with (
            patch(
                "builtins.input",
                side_effect=[
                    "/transcript --max-events nope",
                    "/session-search --max-matches 0 needle",
                    "/session-search --unknown needle",
                    "/exit",
                ],
            ),
            patch("vibeagent.cli.create_chat_client") as create_chat_client,
            patch("vibeagent.cli.get_transcript_text") as get_transcript_text,
            patch("vibeagent.cli.get_session_search_text") as get_session_search_text,
            redirect_stdout(stdout),
        ):
            exit_code = main()

        output = stdout.getvalue()
        self.assertEqual(exit_code, 0)
        self.assertIn("Usage: /transcript [run-id] [--max-events N] [--max-text N]", output)
        self.assertIn("--max-events must be a positive integer.", output)
        self.assertIn("Usage: /session-search [--run run-id] [--max-matches N] [--case-sensitive] [--max-text N] <query>", output)
        self.assertIn("--max-matches must be a positive integer.", output)
        self.assertIn("Unknown option: --unknown", output)
        get_transcript_text.assert_not_called()
        get_session_search_text.assert_not_called()
        create_chat_client.assert_not_called()

    def test_main_parses_interactive_session_output_limit_options(self) -> None:
        stdout = io.StringIO()

        with (
            patch(
                "builtins.input",
                side_effect=[
                    "/session-output-contexts run-1 --max-commands 2 --max-output-chars 120 --context-lines 0 --max-contexts 3 --max-bytes 1000",
                    "/session-output-diagnostics run-1 --max-commands 4 --max-output-chars 140 --context-lines 1 --max-diagnostics 5 --max-contexts 6 --max-bytes 1200",
                    "/exit",
                ],
            ),
            patch("vibeagent.cli.create_chat_client") as create_chat_client,
            patch("vibeagent.cli.get_session_output_contexts_text", return_value="Session output contexts:\n  session: run-1") as get_session_output_contexts_text,
            patch("vibeagent.cli.get_session_output_diagnostics_text", return_value="Session output diagnostics:\n  session: run-1") as get_session_output_diagnostics_text,
            redirect_stdout(stdout),
        ):
            exit_code = main()

        output = stdout.getvalue()
        self.assertEqual(exit_code, 0)
        self.assertIn("Session output contexts:", output)
        self.assertIn("Session output diagnostics:", output)
        get_session_output_contexts_text.assert_called_once_with(
            run_id="run-1",
            max_commands=2,
            max_output_chars=120,
            context_lines=0,
            max_contexts=3,
            max_bytes_per_context=1000,
        )
        get_session_output_diagnostics_text.assert_called_once_with(
            run_id="run-1",
            max_commands=4,
            max_output_chars=140,
            context_lines=1,
            max_diagnostics=5,
            max_contexts=6,
            max_bytes_per_context=1200,
        )
        create_chat_client.assert_not_called()

    def test_main_reports_interactive_session_output_limit_errors(self) -> None:
        stdout = io.StringIO()

        with (
            patch(
                "builtins.input",
                side_effect=[
                    "/session-output-contexts --context-lines -1",
                    "/session-output-diagnostics --max-diagnostics 0",
                    "/session-output-contexts --max-diagnostics 2",
                    "/exit",
                ],
            ),
            patch("vibeagent.cli.create_chat_client") as create_chat_client,
            patch("vibeagent.cli.get_session_output_contexts_text") as get_session_output_contexts_text,
            patch("vibeagent.cli.get_session_output_diagnostics_text") as get_session_output_diagnostics_text,
            redirect_stdout(stdout),
        ):
            exit_code = main()

        output = stdout.getvalue()
        self.assertEqual(exit_code, 0)
        self.assertIn("Usage: /session-output-contexts [run-id]", output)
        self.assertIn("--context-lines must be a non-negative integer.", output)
        self.assertIn("Usage: /session-output-diagnostics [run-id]", output)
        self.assertIn("--max-diagnostics must be a positive integer.", output)
        self.assertIn("Unknown option: --max-diagnostics", output)
        get_session_output_contexts_text.assert_not_called()
        get_session_output_diagnostics_text.assert_not_called()
        create_chat_client.assert_not_called()

    def test_main_parses_interactive_process_output_limit_options(self) -> None:
        stdout = io.StringIO()

        with (
            patch(
                "builtins.input",
                side_effect=[
                    "/process-output-contexts bg-1 --max-chars 1200 --context-lines 0 --max-contexts 3 --max-bytes 1000",
                    "/process-output-diagnostics bg-1 1400 --context-lines 1 --max-diagnostics 4 --max-contexts 5 --max-bytes 1200",
                    "/exit",
                ],
            ),
            patch("vibeagent.cli.create_chat_client") as create_chat_client,
            patch("vibeagent.cli.get_process_output_contexts_text", return_value="Process output contexts:\n  contexts: 1/1") as get_process_output_contexts_text,
            patch("vibeagent.cli.get_process_output_diagnostics_text", return_value="Process output diagnostics:\n  diagnostics: 1/1") as get_process_output_diagnostics_text,
            redirect_stdout(stdout),
        ):
            exit_code = main()

        output = stdout.getvalue()
        self.assertEqual(exit_code, 0)
        self.assertIn("Process output contexts:", output)
        self.assertIn("Process output diagnostics:", output)
        get_process_output_contexts_text.assert_called_once_with(
            process_id="bg-1",
            max_output_chars=1200,
            context_lines=0,
            max_contexts=3,
            max_bytes_per_context=1000,
        )
        get_process_output_diagnostics_text.assert_called_once_with(
            process_id="bg-1",
            max_output_chars=1400,
            context_lines=1,
            max_diagnostics=4,
            max_contexts=5,
            max_bytes_per_context=1200,
        )
        create_chat_client.assert_not_called()

    def test_main_reports_interactive_process_output_limit_errors(self) -> None:
        stdout = io.StringIO()

        with (
            patch(
                "builtins.input",
                side_effect=[
                    "/process-output-contexts --context-lines -1 bg-1",
                    "/process-output-diagnostics bg-1 --max-diagnostics 0",
                    "/process-output-contexts bg-1 --max-diagnostics 2",
                    "/process-output-contexts bg-1 --max-chars 999",
                    "/process-output-diagnostics bg-1 999",
                    "/exit",
                ],
            ),
            patch("vibeagent.cli.create_chat_client") as create_chat_client,
            patch("vibeagent.cli.get_process_output_contexts_text") as get_process_output_contexts_text,
            patch("vibeagent.cli.get_process_output_diagnostics_text") as get_process_output_diagnostics_text,
            redirect_stdout(stdout),
        ):
            exit_code = main()

        output = stdout.getvalue()
        self.assertEqual(exit_code, 0)
        self.assertIn("Usage: /process-output-contexts <id> [chars]", output)
        self.assertIn("--context-lines must be a non-negative integer.", output)
        self.assertIn("Usage: /process-output-diagnostics <id> [chars]", output)
        self.assertIn("--max-diagnostics must be a positive integer.", output)
        self.assertIn("Unknown option: --max-diagnostics", output)
        self.assertIn("max chars must be at least 1000.", output)
        self.assertIn("invalid max chars: 999", output)
        get_process_output_contexts_text.assert_not_called()
        get_process_output_diagnostics_text.assert_not_called()
        create_chat_client.assert_not_called()

    def test_main_parses_interactive_port_options(self) -> None:
        stdout = io.StringIO()

        with (
            patch(
                "builtins.input",
                side_effect=[
                    "/port 5173 --host 0.0.0.0 --timeout-ms 1500",
                    "/exit",
                ],
            ),
            patch("vibeagent.cli.create_chat_client") as create_chat_client,
            patch("vibeagent.cli.get_port_text", return_value="Port:\n  reachable: yes") as get_port_text,
            redirect_stdout(stdout),
        ):
            exit_code = main()

        output = stdout.getvalue()
        self.assertEqual(exit_code, 0)
        self.assertIn("Port:", output)
        get_port_text.assert_called_once_with(port=5173, host="0.0.0.0", timeout_ms=1500)
        create_chat_client.assert_not_called()

    def test_main_reports_interactive_port_option_errors(self) -> None:
        stdout = io.StringIO()

        with (
            patch(
                "builtins.input",
                side_effect=[
                    "/port --host 127.0.0.1",
                    "/port 5173 --timeout-ms 99",
                    "/port 5173 --host",
                    "/port 5173 --unknown 1",
                    "/port 5173 extra --host 127.0.0.1",
                    "/exit",
                ],
            ),
            patch("vibeagent.cli.create_chat_client") as create_chat_client,
            patch("vibeagent.cli.get_port_text") as get_port_text,
            redirect_stdout(stdout),
        ):
            exit_code = main()

        output = stdout.getvalue()
        self.assertEqual(exit_code, 0)
        self.assertIn("Usage: /port <port> [host] [timeout-ms]", output)
        self.assertIn("port is required.", output)
        self.assertIn("--timeout-ms must be at least 100.", output)
        self.assertIn("--host requires a value.", output)
        self.assertIn("Unknown option: --unknown", output)
        get_port_text.assert_not_called()
        create_chat_client.assert_not_called()

    def test_main_parses_interactive_http_options(self) -> None:
        stdout = io.StringIO()

        with (
            patch(
                "builtins.input",
                side_effect=[
                    "/http http://127.0.0.1:5173 ready --timeout-ms 1500 --max-body-chars 1000 --regex",
                    "/http-fetch --timeout-ms 2500 --max-body-chars 4000 -- http://127.0.0.1:5173/app",
                    "/exit",
                ],
            ),
            patch("vibeagent.cli.create_chat_client") as create_chat_client,
            patch("vibeagent.cli.get_http_text", return_value="HTTP:\n  matched: yes") as get_http_text,
            patch("vibeagent.cli.get_http_fetch_text", return_value="HTTP fetch:\n  ok: yes") as get_http_fetch_text,
            redirect_stdout(stdout),
        ):
            exit_code = main()

        output = stdout.getvalue()
        self.assertEqual(exit_code, 0)
        self.assertIn("HTTP:", output)
        self.assertIn("HTTP fetch:", output)
        get_http_text.assert_called_once_with(
            url="http://127.0.0.1:5173",
            contains="ready",
            timeout_ms=1500,
            max_body_chars=1000,
            regex=True,
        )
        get_http_fetch_text.assert_called_once_with(
            url="http://127.0.0.1:5173/app",
            timeout_ms=2500,
            max_body_chars=4000,
        )
        create_chat_client.assert_not_called()

    def test_main_reports_interactive_http_option_errors(self) -> None:
        stdout = io.StringIO()

        with (
            patch(
                "builtins.input",
                side_effect=[
                    "/http --timeout-ms 99 -- http://127.0.0.1:5173",
                    "/http http://127.0.0.1:5173 --contains",
                    "/http --contains ready",
                    "/http http://127.0.0.1:5173 --unknown 1",
                    "/http-fetch --max-body-chars 0 -- http://127.0.0.1:5173/app",
                    "/http-fetch http://127.0.0.1:5173/app extra --timeout-ms 1000",
                    "/exit",
                ],
            ),
            patch("vibeagent.cli.create_chat_client") as create_chat_client,
            patch("vibeagent.cli.get_http_text") as get_http_text,
            patch("vibeagent.cli.get_http_fetch_text") as get_http_fetch_text,
            redirect_stdout(stdout),
        ):
            exit_code = main()

        output = stdout.getvalue()
        self.assertEqual(exit_code, 0)
        self.assertIn("Usage: /http <url> [contains]", output)
        self.assertIn("--timeout-ms must be at least 100.", output)
        self.assertIn("--contains requires a value.", output)
        self.assertIn("url is required.", output)
        self.assertIn("Unknown option: --unknown", output)
        self.assertIn("Usage: /http-fetch <url>", output)
        self.assertIn("--max-body-chars must be a positive integer.", output)
        get_http_text.assert_not_called()
        get_http_fetch_text.assert_not_called()
        create_chat_client.assert_not_called()

    def test_main_parses_interactive_search_options(self) -> None:
        stdout = io.StringIO()

        with (
            patch(
                "builtins.input",
                side_effect=[
                    "/search --path src --max-matches 5 --regex --ignore-case --context-lines 1 -- needle.+",
                    "/search-contexts needle --path tests --max-matches 3 --context-lines 2 --max-bytes 1000 --case-sensitive",
                    "/exit",
                ],
            ),
            patch("vibeagent.cli.create_chat_client") as create_chat_client,
            patch("vibeagent.cli.get_search_text", return_value="Search:\n  matches: 1/1") as get_search_text,
            patch("vibeagent.cli.get_search_contexts_text", return_value="Search contexts:\n  contexts: 1/1") as get_search_contexts_text,
            redirect_stdout(stdout),
        ):
            exit_code = main()

        output = stdout.getvalue()
        self.assertEqual(exit_code, 0)
        self.assertIn("Search:", output)
        self.assertIn("Search contexts:", output)
        get_search_text.assert_called_once_with(
            query="needle.+",
            path="src",
            max_matches=5,
            regex=True,
            case_sensitive=False,
            context_lines=1,
        )
        get_search_contexts_text.assert_called_once_with(
            query="needle",
            path="tests",
            max_matches=3,
            context_lines=2,
            max_bytes_per_context=1000,
            case_sensitive=True,
        )
        create_chat_client.assert_not_called()

    def test_main_parses_interactive_find_files_options(self) -> None:
        stdout = io.StringIO()

        with (
            patch(
                "builtins.input",
                side_effect=[
                    "/find-files --path src --max-matches 5 --regex --case-sensitive --include-dirs -- app.+",
                    "/exit",
                ],
            ),
            patch("vibeagent.cli.create_chat_client") as create_chat_client,
            patch("vibeagent.cli.get_find_files_text", return_value="Find Files:\n  matches: 1/1") as get_find_files_text,
            redirect_stdout(stdout),
        ):
            exit_code = main()

        output = stdout.getvalue()
        self.assertEqual(exit_code, 0)
        self.assertIn("Find Files:", output)
        get_find_files_text.assert_called_once_with(
            query="app.+",
            path="src",
            max_matches=5,
            regex=True,
            case_sensitive=True,
            include_dirs=True,
        )
        create_chat_client.assert_not_called()

    def test_main_reports_interactive_search_option_errors(self) -> None:
        stdout = io.StringIO()

        with (
            patch(
                "builtins.input",
                side_effect=[
                    "/search --path src",
                    "/search needle --max-matches 0",
                    "/search needle --regex=true",
                    "/search needle --max-bytes 1000",
                    "/search-contexts needle --context-lines -1",
                    "/search-contexts needle --max-bytes 0",
                    "/exit",
                ],
            ),
            patch("vibeagent.cli.create_chat_client") as create_chat_client,
            patch("vibeagent.cli.get_search_text") as get_search_text,
            patch("vibeagent.cli.get_search_contexts_text") as get_search_contexts_text,
            redirect_stdout(stdout),
        ):
            exit_code = main()

        output = stdout.getvalue()
        self.assertEqual(exit_code, 0)
        self.assertIn("Usage: /search [--path PATH]", output)
        self.assertIn("query is required.", output)
        self.assertIn("--max-matches must be a positive integer.", output)
        self.assertIn("--regex does not take a value.", output)
        self.assertIn("Unknown option: --max-bytes", output)
        self.assertIn("Usage: /search-contexts [--path PATH]", output)
        self.assertIn("--context-lines must be a non-negative integer.", output)
        self.assertIn("--max-bytes must be a positive integer.", output)
        get_search_text.assert_not_called()
        get_search_contexts_text.assert_not_called()
        create_chat_client.assert_not_called()

    def test_main_reports_interactive_find_files_option_errors(self) -> None:
        stdout = io.StringIO()

        with (
            patch(
                "builtins.input",
                side_effect=[
                    "/find-files --path src",
                    "/find-files app --max-matches 0",
                    "/find-files app --regex=true",
                    "/find-files app --unknown",
                    "/exit",
                ],
            ),
            patch("vibeagent.cli.create_chat_client") as create_chat_client,
            patch("vibeagent.cli.get_find_files_text") as get_find_files_text,
            redirect_stdout(stdout),
        ):
            exit_code = main()

        output = stdout.getvalue()
        self.assertEqual(exit_code, 0)
        self.assertIn("Usage: /find-files [--path PATH]", output)
        self.assertIn("query is required.", output)
        self.assertIn("--max-matches must be a positive integer.", output)
        self.assertIn("--regex does not take a value.", output)
        self.assertIn("Unknown option: --unknown", output)
        get_find_files_text.assert_not_called()
        create_chat_client.assert_not_called()

    def test_main_parses_interactive_overview_repo_map_options(self) -> None:
        stdout = io.StringIO()

        with (
            patch(
                "builtins.input",
                side_effect=[
                    "/overview --max-files 7 --max-commands 3 --max-checks 2",
                    "/repo-map src --max-depth 2 --max-files 8 --max-symbols 9",
                    "/repo-map --max-depth=0 --max-files=4 --max-symbols=5",
                    "/exit",
                ],
            ),
            patch("vibeagent.cli.create_chat_client") as create_chat_client,
            patch("vibeagent.cli.get_overview_text", return_value="Overview:\n  files: 1/1") as get_overview_text,
            patch("vibeagent.cli.get_repo_map_text", return_value="Repo map:\n  files: 1/1") as get_repo_map_text,
            redirect_stdout(stdout),
        ):
            exit_code = main()

        output = stdout.getvalue()
        self.assertEqual(exit_code, 0)
        self.assertIn("Overview:", output)
        self.assertIn("Repo map:", output)
        get_overview_text.assert_called_once_with(max_files=7, max_commands=3, max_checks=2)
        self.assertEqual(
            get_repo_map_text.call_args_list,
            [
                call(path="src", max_depth=2, max_files=8, max_symbols=9),
                call(path=None, max_depth=0, max_files=4, max_symbols=5),
            ],
        )
        create_chat_client.assert_not_called()

    def test_main_reports_interactive_overview_repo_map_option_errors(self) -> None:
        stdout = io.StringIO()

        with (
            patch(
                "builtins.input",
                side_effect=[
                    "/overview --max-files 0",
                    "/overview --unknown 1",
                    "/overview unexpected --max-files 1",
                    "/repo-map src --max-depth -1",
                    "/repo-map src --max-files 0",
                    "/repo-map src --max-symbols 0",
                    "/repo-map src other --max-depth 1",
                    "/exit",
                ],
            ),
            patch("vibeagent.cli.create_chat_client") as create_chat_client,
            patch("vibeagent.cli.get_overview_text") as get_overview_text,
            patch("vibeagent.cli.get_repo_map_text") as get_repo_map_text,
            redirect_stdout(stdout),
        ):
            exit_code = main()

        output = stdout.getvalue()
        self.assertEqual(exit_code, 0)
        self.assertIn("Usage: /overview [--max-files N]", output)
        self.assertIn("--max-files must be a positive integer.", output)
        self.assertIn("Unknown option: --unknown", output)
        self.assertIn("Usage: /repo-map [path] [--max-depth N]", output)
        self.assertIn("--max-depth must be a non-negative integer.", output)
        self.assertIn("--max-files must be a positive integer.", output)
        self.assertIn("--max-symbols must be a positive integer.", output)
        get_overview_text.assert_not_called()
        get_repo_map_text.assert_not_called()
        create_chat_client.assert_not_called()

    def test_main_parses_interactive_glob_tree_options(self) -> None:
        stdout = io.StringIO()

        with (
            patch(
                "builtins.input",
                side_effect=[
                    "/glob --max-matches 7 --include-dirs -- **/*.py",
                    "/tree src --max-depth 2 --max-entries 30",
                    "/tree --max-depth=0 --max-entries=5",
                    "/exit",
                ],
            ),
            patch("vibeagent.cli.create_chat_client") as create_chat_client,
            patch("vibeagent.cli.get_glob_text", return_value="Glob:\n  matches: 1/1") as get_glob_text,
            patch("vibeagent.cli.get_tree_text", return_value="Tree:\n  entries: 1/1") as get_tree_text,
            redirect_stdout(stdout),
        ):
            exit_code = main()

        output = stdout.getvalue()
        self.assertEqual(exit_code, 0)
        self.assertIn("Glob:", output)
        self.assertIn("Tree:", output)
        get_glob_text.assert_called_once_with(pattern="**/*.py", max_matches=7, include_dirs=True)
        self.assertEqual(
            get_tree_text.call_args_list,
            [
                call(path="src", max_depth=2, max_entries=30),
                call(path=None, max_depth=0, max_entries=5),
            ],
        )
        create_chat_client.assert_not_called()

    def test_main_reports_interactive_glob_tree_option_errors(self) -> None:
        stdout = io.StringIO()

        with (
            patch(
                "builtins.input",
                side_effect=[
                    "/glob --max-matches 0 -- **/*.py",
                    "/glob --max-matches 5",
                    "/glob --include-dirs=maybe -- **/*.py",
                    "/glob --unknown 1 -- **/*.py",
                    "/tree --max-depth -1",
                    "/tree src --max-entries 0",
                    "/tree src other --max-depth 1",
                    "/exit",
                ],
            ),
            patch("vibeagent.cli.create_chat_client") as create_chat_client,
            patch("vibeagent.cli.get_glob_text") as get_glob_text,
            patch("vibeagent.cli.get_tree_text") as get_tree_text,
            redirect_stdout(stdout),
        ):
            exit_code = main()

        output = stdout.getvalue()
        self.assertEqual(exit_code, 0)
        self.assertIn("Usage: /glob [--max-matches N] [--include-dirs] -- <pattern>", output)
        self.assertIn("--max-matches must be a positive integer.", output)
        self.assertIn("pattern is required.", output)
        self.assertIn("--include-dirs must be a boolean.", output)
        self.assertIn("Unknown option: --unknown", output)
        self.assertIn("Usage: /tree [path] [--max-depth N] [--max-entries N]", output)
        self.assertIn("--max-depth must be a non-negative integer.", output)
        self.assertIn("--max-entries must be a positive integer.", output)
        get_glob_text.assert_not_called()
        get_tree_text.assert_not_called()
        create_chat_client.assert_not_called()

    def test_main_parses_interactive_symbols_options(self) -> None:
        stdout = io.StringIO()

        with (
            patch(
                "builtins.input",
                side_effect=[
                    "/symbols --max-symbols 12 -- src/app.py web/app.ts",
                    "/exit",
                ],
            ),
            patch("vibeagent.cli.create_chat_client") as create_chat_client,
            patch("vibeagent.cli.get_symbols_text", return_value="Symbols:\n  files: 1/1") as get_symbols_text,
            redirect_stdout(stdout),
        ):
            exit_code = main()

        output = stdout.getvalue()
        self.assertEqual(exit_code, 0)
        self.assertIn("Symbols:", output)
        get_symbols_text.assert_called_once_with(argument=["src/app.py", "web/app.ts"], max_symbols=12)
        create_chat_client.assert_not_called()

    def test_main_reports_interactive_symbols_option_errors(self) -> None:
        stdout = io.StringIO()

        with (
            patch(
                "builtins.input",
                side_effect=[
                    "/symbols --max-symbols 0 -- src/app.py",
                    "/symbols --max-symbols 12",
                    "/symbols --unknown 1 -- src/app.py",
                    "/exit",
                ],
            ),
            patch("vibeagent.cli.create_chat_client") as create_chat_client,
            patch("vibeagent.cli.get_symbols_text") as get_symbols_text,
            redirect_stdout(stdout),
        ):
            exit_code = main()

        output = stdout.getvalue()
        self.assertEqual(exit_code, 0)
        self.assertIn("Usage: /symbols [--max-symbols N] -- <path...>", output)
        self.assertIn("--max-symbols must be a positive integer.", output)
        self.assertIn("at least one path is required.", output)
        self.assertIn("Unknown option: --unknown", output)
        get_symbols_text.assert_not_called()
        create_chat_client.assert_not_called()

    def test_main_parses_interactive_read_files_limit_options(self) -> None:
        stdout = io.StringIO()

        with (
            patch(
                "builtins.input",
                side_effect=[
                    "/read-files --max-bytes 1000 --line-numbers -- src/app.py tests/test_app.py",
                    "/read-files --max-bytes=1200 --line-numbers=false -- README.md",
                    "/exit",
                ],
            ),
            patch("vibeagent.cli.create_chat_client") as create_chat_client,
            patch("vibeagent.cli.get_read_files_text", return_value="Read files:\n  files: 1/1") as get_read_files_text,
            redirect_stdout(stdout),
        ):
            exit_code = main()

        output = stdout.getvalue()
        self.assertEqual(exit_code, 0)
        self.assertIn("Read files:", output)
        self.assertEqual(
            get_read_files_text.call_args_list,
            [
                call(argument=["src/app.py", "tests/test_app.py"], max_bytes_per_file=1000, show_line_numbers=True),
                call(argument=["README.md"], max_bytes_per_file=1200, show_line_numbers=False),
            ],
        )
        create_chat_client.assert_not_called()

    def test_main_parses_interactive_read_limit_options(self) -> None:
        stdout = io.StringIO()

        with (
            patch(
                "builtins.input",
                side_effect=[
                    "/read --max-bytes 1000 --line-numbers -- src/app.py 2:4",
                    "/read --max-bytes=1200 --line-numbers=false -- README.md",
                    "/exit",
                ],
            ),
            patch("vibeagent.cli.create_chat_client") as create_chat_client,
            patch("vibeagent.cli.get_read_text", return_value="Read:\n  ok: yes") as get_read_text,
            redirect_stdout(stdout),
        ):
            exit_code = main()

        output = stdout.getvalue()
        self.assertEqual(exit_code, 0)
        self.assertIn("Read:", output)
        self.assertEqual(
            get_read_text.call_args_list,
            [
                call(argument="src/app.py 2:4", max_bytes=1000, show_line_numbers=True),
                call(argument="README.md", max_bytes=1200, show_line_numbers=False),
            ],
        )
        create_chat_client.assert_not_called()

    def test_main_reports_interactive_read_limit_errors(self) -> None:
        stdout = io.StringIO()

        with (
            patch(
                "builtins.input",
                side_effect=[
                    "/read --max-bytes 0 -- src/app.py",
                    "/read --line-numbers=maybe -- src/app.py",
                    "/read --unknown 1 -- src/app.py",
                    "/read --max-bytes 1000",
                    "/exit",
                ],
            ),
            patch("vibeagent.cli.create_chat_client") as create_chat_client,
            patch("vibeagent.cli.get_read_text") as get_read_text,
            redirect_stdout(stdout),
        ):
            exit_code = main()

        output = stdout.getvalue()
        self.assertEqual(exit_code, 0)
        self.assertIn("Usage: /read [--max-bytes N] [--line-numbers] -- <path> [start[:end]]", output)
        self.assertIn("--max-bytes must be a positive integer.", output)
        self.assertIn("--line-numbers must be a boolean.", output)
        self.assertIn("Unknown option: --unknown", output)
        self.assertIn("path is required.", output)
        get_read_text.assert_not_called()
        create_chat_client.assert_not_called()

    def test_main_parses_interactive_context_read_limit_options(self) -> None:
        stdout = io.StringIO()

        with (
            patch(
                "builtins.input",
                side_effect=[
                    "/tail --max-bytes 1000 -- logs/app.log 3",
                    "/around --max-bytes=1200 -- src/app.py 42 8",
                    "/around-many --max-bytes 1400 -- src/app.py:42:8 tests/test_app.py:17",
                    "/exit",
                ],
            ),
            patch("vibeagent.cli.create_chat_client") as create_chat_client,
            patch("vibeagent.cli.get_tail_text", return_value="Tail:\n  ok: yes") as get_tail_text,
            patch("vibeagent.cli.get_around_text", return_value="Around:\n  ok: yes") as get_around_text,
            patch("vibeagent.cli.get_around_many_text", return_value="Around many:\n  contexts: 2/2") as get_around_many_text,
            redirect_stdout(stdout),
        ):
            exit_code = main()

        output = stdout.getvalue()
        self.assertEqual(exit_code, 0)
        self.assertIn("Tail:", output)
        self.assertIn("Around:", output)
        self.assertIn("Around many:", output)
        get_tail_text.assert_called_once_with(argument="logs/app.log 3", max_bytes=1000)
        get_around_text.assert_called_once_with(argument="src/app.py 42 8", max_bytes=1200)
        get_around_many_text.assert_called_once_with(argument="src/app.py:42:8 tests/test_app.py:17", max_bytes_per_context=1400)
        create_chat_client.assert_not_called()

    def test_main_parses_interactive_diff_max_chars(self) -> None:
        stdout = io.StringIO()

        with (
            patch(
                "builtins.input",
                side_effect=[
                    "/diff --max-chars 1000 --staged app.py",
                    "/exit",
                ],
            ),
            patch("vibeagent.cli.create_chat_client") as create_chat_client,
            patch("vibeagent.cli.get_diff_text", return_value="Diff:\n  truncated: yes") as get_diff_text,
            redirect_stdout(stdout),
        ):
            exit_code = main()

        self.assertEqual(exit_code, 0)
        self.assertIn("Diff:", stdout.getvalue())
        get_diff_text.assert_called_once_with(argument="--staged app.py", max_chars=1000)
        create_chat_client.assert_not_called()

    def test_main_parses_interactive_changes_max_files(self) -> None:
        stdout = io.StringIO()

        with (
            patch(
                "builtins.input",
                side_effect=[
                    "/changes --max-files 1",
                    "/exit",
                ],
            ),
            patch("vibeagent.cli.create_chat_client") as create_chat_client,
            patch("vibeagent.cli.get_changes_text", return_value="Changes:\n  shownFiles: 1/3") as get_changes_text,
            redirect_stdout(stdout),
        ):
            exit_code = main()

        self.assertEqual(exit_code, 0)
        self.assertIn("Changes:", stdout.getvalue())
        get_changes_text.assert_called_once_with(max_files=1)
        create_chat_client.assert_not_called()

    def test_main_parses_interactive_review_limits(self) -> None:
        stdout = io.StringIO()

        with (
            patch(
                "builtins.input",
                side_effect=[
                    "/review --max-files 1 --max-checks 2",
                    "/exit",
                ],
            ),
            patch("vibeagent.cli.create_chat_client") as create_chat_client,
            patch("vibeagent.cli.get_review_text", return_value="Review:\n  ready: yes") as get_review_text,
            redirect_stdout(stdout),
        ):
            exit_code = main()

        self.assertEqual(exit_code, 0)
        self.assertIn("Review:", stdout.getvalue())
        get_review_text.assert_called_once_with(max_files=1, max_checks=2)
        create_chat_client.assert_not_called()

    def test_main_parses_interactive_handoff_limits(self) -> None:
        stdout = io.StringIO()

        with (
            patch(
                "builtins.input",
                side_effect=[
                    "/handoff --max-files 1 --max-checks 2 --max-status-chars 3000 --max-plan-chars 4000",
                    "/exit",
                ],
            ),
            patch("vibeagent.cli.create_chat_client") as create_chat_client,
            patch("vibeagent.cli.get_handoff_text", return_value="Handoff:\n  ready: yes") as get_handoff_text,
            redirect_stdout(stdout),
        ):
            exit_code = main()

        self.assertEqual(exit_code, 0)
        self.assertIn("Handoff:", stdout.getvalue())
        get_handoff_text.assert_called_once_with(max_files=1, max_checks=2, max_status_chars=3000, max_plan_chars=4000)
        create_chat_client.assert_not_called()

    def test_main_reports_interactive_changes_max_files_errors(self) -> None:
        stdout = io.StringIO()

        with (
            patch(
                "builtins.input",
                side_effect=[
                    "/changes --max-files 0",
                    "/changes --unknown 1",
                    "/exit",
                ],
            ),
            patch("vibeagent.cli.create_chat_client") as create_chat_client,
            patch("vibeagent.cli.get_changes_text") as get_changes_text,
            redirect_stdout(stdout),
        ):
            exit_code = main()

        output = stdout.getvalue()
        self.assertEqual(exit_code, 0)
        self.assertIn("Usage: /changes [--max-files N]", output)
        self.assertIn("--max-files must be a positive integer.", output)
        self.assertIn("Unknown option: --unknown", output)
        get_changes_text.assert_not_called()
        create_chat_client.assert_not_called()

    def test_main_reports_interactive_review_limit_errors(self) -> None:
        stdout = io.StringIO()

        with (
            patch(
                "builtins.input",
                side_effect=[
                    "/review --max-files 0",
                    "/review --unknown 1",
                    "/exit",
                ],
            ),
            patch("vibeagent.cli.create_chat_client") as create_chat_client,
            patch("vibeagent.cli.get_review_text") as get_review_text,
            redirect_stdout(stdout),
        ):
            exit_code = main()

        output = stdout.getvalue()
        self.assertEqual(exit_code, 0)
        self.assertIn("Usage: /review [--max-files N] [--max-checks N]", output)
        self.assertIn("--max-files must be a positive integer.", output)
        self.assertIn("Unknown option: --unknown", output)
        get_review_text.assert_not_called()
        create_chat_client.assert_not_called()

    def test_main_reports_interactive_handoff_limit_errors(self) -> None:
        stdout = io.StringIO()

        with (
            patch(
                "builtins.input",
                side_effect=[
                    "/handoff --max-files 0",
                    "/handoff --unknown 1",
                    "/exit",
                ],
            ),
            patch("vibeagent.cli.create_chat_client") as create_chat_client,
            patch("vibeagent.cli.get_handoff_text") as get_handoff_text,
            redirect_stdout(stdout),
        ):
            exit_code = main()

        output = stdout.getvalue()
        self.assertEqual(exit_code, 0)
        self.assertIn("Usage: /handoff [--max-files N] [--max-checks N] [--max-status-chars N] [--max-plan-chars N]", output)
        self.assertIn("--max-files must be a positive integer.", output)
        self.assertIn("Unknown option: --unknown", output)
        get_handoff_text.assert_not_called()
        create_chat_client.assert_not_called()

    def test_main_reports_interactive_diff_max_chars_errors(self) -> None:
        stdout = io.StringIO()

        with (
            patch(
                "builtins.input",
                side_effect=[
                    "/diff --max-chars 0 app.py",
                    "/diff --max-chars 99 app.py",
                    "/exit",
                ],
            ),
            patch("vibeagent.cli.create_chat_client") as create_chat_client,
            patch("vibeagent.cli.get_diff_text", side_effect=ValueError("max_chars must be at least 100.")) as get_diff_text,
            redirect_stdout(stdout),
        ):
            exit_code = main()

        output = stdout.getvalue()
        self.assertEqual(exit_code, 0)
        self.assertIn("Usage: /diff [--staged|--cached] [--max-chars N] [path]", output)
        self.assertIn("--max-chars must be a positive integer.", output)
        self.assertIn("max_chars must be at least 100.", output)
        get_diff_text.assert_called_once_with(argument="app.py", max_chars=99)
        create_chat_client.assert_not_called()

    def test_main_parses_interactive_structured_diff_limit_options(self) -> None:
        stdout = io.StringIO()

        with (
            patch(
                "builtins.input",
                side_effect=[
                    "/diff-hunks --max-hunks 3 --max-lines 4 --staged app.py",
                    "/diff-contexts --context-lines 2 --max-hunks 5 --max-bytes 1000 app.py",
                    "/exit",
                ],
            ),
            patch("vibeagent.cli.create_chat_client") as create_chat_client,
            patch("vibeagent.cli.get_diff_hunks_text", return_value="Diff hunks:\n  hunks: 1/1") as get_diff_hunks_text,
            patch("vibeagent.cli.get_diff_contexts_text", return_value="Diff contexts:\n  contexts: 1/1") as get_diff_contexts_text,
            redirect_stdout(stdout),
        ):
            exit_code = main()

        output = stdout.getvalue()
        self.assertEqual(exit_code, 0)
        self.assertIn("Diff hunks:", output)
        self.assertIn("Diff contexts:", output)
        get_diff_hunks_text.assert_called_once_with(argument="--staged app.py", max_hunks=3, max_lines_per_hunk=4)
        get_diff_contexts_text.assert_called_once_with(
            argument="app.py",
            context_lines=2,
            max_hunks=5,
            max_bytes_per_context=1000,
        )
        create_chat_client.assert_not_called()

    def test_main_reports_interactive_structured_diff_limit_errors(self) -> None:
        stdout = io.StringIO()

        with (
            patch(
                "builtins.input",
                side_effect=[
                    "/diff-hunks --max-hunks 0 app.py",
                    "/diff-contexts --context-lines -1 app.py",
                    "/diff-contexts --unknown app.py",
                    "/exit",
                ],
            ),
            patch("vibeagent.cli.create_chat_client") as create_chat_client,
            patch("vibeagent.cli.get_diff_hunks_text") as get_diff_hunks_text,
            patch("vibeagent.cli.get_diff_contexts_text") as get_diff_contexts_text,
            redirect_stdout(stdout),
        ):
            exit_code = main()

        output = stdout.getvalue()
        self.assertEqual(exit_code, 0)
        self.assertIn("Usage: /diff-hunks [--staged|--cached] [--max-hunks N] [--max-lines N] [path]", output)
        self.assertIn("--max-hunks must be a positive integer.", output)
        self.assertIn("Usage: /diff-contexts [--staged|--cached] [--context-lines N] [--max-hunks N] [--max-bytes N] [path]", output)
        self.assertIn("--context-lines must be a non-negative integer.", output)
        self.assertIn("Unknown option: --unknown", output)
        get_diff_hunks_text.assert_not_called()
        get_diff_contexts_text.assert_not_called()
        create_chat_client.assert_not_called()

    def test_main_reports_interactive_context_read_limit_errors(self) -> None:
        stdout = io.StringIO()

        with (
            patch(
                "builtins.input",
                side_effect=[
                    "/tail --max-bytes 0 -- logs/app.log",
                    "/around --unknown 1 -- src/app.py 42",
                    "/around-many --max-bytes 1000",
                    "/exit",
                ],
            ),
            patch("vibeagent.cli.create_chat_client") as create_chat_client,
            patch("vibeagent.cli.get_tail_text") as get_tail_text,
            patch("vibeagent.cli.get_around_text") as get_around_text,
            patch("vibeagent.cli.get_around_many_text") as get_around_many_text,
            redirect_stdout(stdout),
        ):
            exit_code = main()

        output = stdout.getvalue()
        self.assertEqual(exit_code, 0)
        self.assertIn("Usage: /tail [--max-bytes N] -- <path> [lines]", output)
        self.assertIn("Usage: /around [--max-bytes N] -- <path> <line> [context-lines]", output)
        self.assertIn("Usage: /around-many [--max-bytes N] -- <path:line[:context-lines]...>", output)
        self.assertIn("--max-bytes must be a positive integer.", output)
        self.assertIn("Unknown option: --unknown", output)
        self.assertIn("at least one context is required.", output)
        get_tail_text.assert_not_called()
        get_around_text.assert_not_called()
        get_around_many_text.assert_not_called()
        create_chat_client.assert_not_called()

    def test_main_parses_interactive_read_ranges_limit_options(self) -> None:
        stdout = io.StringIO()

        with (
            patch(
                "builtins.input",
                side_effect=[
                    "/read-ranges --max-bytes 1000 -- src/app.py:2:4 tests/test_app.py:1",
                    "/exit",
                ],
            ),
            patch("vibeagent.cli.create_chat_client") as create_chat_client,
            patch("vibeagent.cli.get_read_ranges_text", return_value="Read ranges:\n  ranges: 2/2") as get_read_ranges_text,
            redirect_stdout(stdout),
        ):
            exit_code = main()

        output = stdout.getvalue()
        self.assertEqual(exit_code, 0)
        self.assertIn("Read ranges:", output)
        get_read_ranges_text.assert_called_once_with(argument="src/app.py:2:4 tests/test_app.py:1", max_bytes_per_range=1000)
        create_chat_client.assert_not_called()

    def test_main_reports_interactive_read_ranges_limit_errors(self) -> None:
        stdout = io.StringIO()

        with (
            patch(
                "builtins.input",
                side_effect=[
                    "/read-ranges --max-bytes 0 -- src/app.py:2:4",
                    "/read-ranges --max-bytes 1000",
                    "/exit",
                ],
            ),
            patch("vibeagent.cli.create_chat_client") as create_chat_client,
            patch("vibeagent.cli.get_read_ranges_text") as get_read_ranges_text,
            redirect_stdout(stdout),
        ):
            exit_code = main()

        output = stdout.getvalue()
        self.assertEqual(exit_code, 0)
        self.assertIn("Usage: /read-ranges [--max-bytes N] -- <path:start[:end]...>", output)
        self.assertIn("--max-bytes must be a positive integer.", output)
        self.assertIn("at least one range is required.", output)
        get_read_ranges_text.assert_not_called()
        create_chat_client.assert_not_called()

    def test_main_reports_interactive_read_files_limit_errors(self) -> None:
        stdout = io.StringIO()

        with (
            patch(
                "builtins.input",
                side_effect=[
                    "/read-files --max-bytes 0 -- src/app.py",
                    "/read-files --line-numbers=maybe -- src/app.py",
                    "/read-files --unknown 1 -- src/app.py",
                    "/read-files --max-bytes 1000",
                    "/exit",
                ],
            ),
            patch("vibeagent.cli.create_chat_client") as create_chat_client,
            patch("vibeagent.cli.get_read_files_text") as get_read_files_text,
            redirect_stdout(stdout),
        ):
            exit_code = main()

        output = stdout.getvalue()
        self.assertEqual(exit_code, 0)
        self.assertIn("Usage: /read-files [--max-bytes N] [--line-numbers] -- <path...>", output)
        self.assertIn("--max-bytes must be a positive integer.", output)
        self.assertIn("--line-numbers must be a boolean.", output)
        self.assertIn("Unknown option: --unknown", output)
        self.assertIn("at least one path is required.", output)
        get_read_files_text.assert_not_called()
        create_chat_client.assert_not_called()

    def test_main_parses_interactive_output_analysis_options(self) -> None:
        stdout = io.StringIO()

        with (
            patch(
                "builtins.input",
                side_effect=[
                    "/output-contexts --context-lines 3 --max-contexts 4 --max-bytes 1000 -- src/app.py:42:8",
                    "/output-diagnostics --context-lines 2 --max-diagnostics 5 --max-contexts 6 --max-bytes 1200 -- ERROR src/app.py:42 failed",
                    "/python-traceback --context-lines=1 --max-diagnostics=7 --max-contexts=8 --max-bytes=1400 -- ValueError: bad",
                    "/exit",
                ],
            ),
            patch("vibeagent.cli.create_chat_client") as create_chat_client,
            patch("vibeagent.cli.get_output_contexts_text", return_value="Output contexts:\n  contexts: 1/1") as get_output_contexts_text,
            patch("vibeagent.cli.get_output_diagnostics_text", return_value="Output diagnostics:\n  diagnostics: 1/1") as get_output_diagnostics_text,
            patch("vibeagent.cli.get_python_traceback_text", return_value="Python traceback:\n  diagnostics: 1/1") as get_python_traceback_text,
            redirect_stdout(stdout),
        ):
            exit_code = main()

        output = stdout.getvalue()
        self.assertEqual(exit_code, 0)
        self.assertIn("Output contexts:", output)
        self.assertIn("Output diagnostics:", output)
        self.assertIn("Python traceback:", output)
        get_output_contexts_text.assert_called_once_with(
            text="src/app.py:42:8",
            context_lines=3,
            max_contexts=4,
            max_bytes_per_context=1000,
        )
        get_output_diagnostics_text.assert_called_once_with(
            text="ERROR src/app.py:42 failed",
            context_lines=2,
            max_diagnostics=5,
            max_contexts=6,
            max_bytes_per_context=1200,
        )
        get_python_traceback_text.assert_called_once_with(
            text="ValueError: bad",
            context_lines=1,
            max_diagnostics=7,
            max_contexts=8,
            max_bytes_per_context=1400,
        )
        create_chat_client.assert_not_called()

    def test_main_reports_interactive_output_analysis_option_errors(self) -> None:
        stdout = io.StringIO()

        with (
            patch(
                "builtins.input",
                side_effect=[
                    "/output-contexts --context-lines -1 -- src/app.py:42",
                    "/output-contexts --max-contexts 0 -- src/app.py:42",
                    "/output-diagnostics --max-diagnostics 0 -- ERROR src/app.py:42 failed",
                    "/python-traceback --max-bytes 0 -- ValueError: bad",
                    "/python-traceback --unknown 1 -- ValueError: bad",
                    "/output-diagnostics --context-lines 2",
                    "/exit",
                ],
            ),
            patch("vibeagent.cli.create_chat_client") as create_chat_client,
            patch("vibeagent.cli.get_output_contexts_text") as get_output_contexts_text,
            patch("vibeagent.cli.get_output_diagnostics_text") as get_output_diagnostics_text,
            patch("vibeagent.cli.get_python_traceback_text") as get_python_traceback_text,
            redirect_stdout(stdout),
        ):
            exit_code = main()

        output = stdout.getvalue()
        self.assertEqual(exit_code, 0)
        self.assertIn("Usage: /output-contexts [--context-lines N]", output)
        self.assertIn("--context-lines must be a non-negative integer.", output)
        self.assertIn("--max-contexts must be a positive integer.", output)
        self.assertIn("Usage: /output-diagnostics [--context-lines N]", output)
        self.assertIn("--max-diagnostics must be a positive integer.", output)
        self.assertIn("Usage: /python-traceback [--context-lines N]", output)
        self.assertIn("--max-bytes must be a positive integer.", output)
        self.assertIn("Unknown option: --unknown", output)
        self.assertIn("text is required.", output)
        get_output_contexts_text.assert_not_called()
        get_output_diagnostics_text.assert_not_called()
        get_python_traceback_text.assert_not_called()
        create_chat_client.assert_not_called()

    def test_main_parses_interactive_wait_process_match_options(self) -> None:
        stdout = io.StringIO()

        with (
            patch(
                "builtins.input",
                side_effect=[
                    "/wait-process bg-1 --timeout-ms 6000 --max-chars 5000 --stdout ready --stderr error --regex",
                    "/exit",
                ],
            ),
            patch("vibeagent.cli.create_chat_client") as create_chat_client,
            patch("vibeagent.cli.get_wait_process_text", return_value="Wait process:\n  matched: yes") as get_wait_process_text,
            redirect_stdout(stdout),
        ):
            exit_code = main()

        output = stdout.getvalue()
        self.assertEqual(exit_code, 0)
        self.assertIn("Wait process:", output)
        get_wait_process_text.assert_called_once_with(
            process_id="bg-1",
            timeout_ms=6000,
            max_output_chars=5000,
            stdout_contains="ready",
            stderr_contains="error",
            regex=True,
        )
        create_chat_client.assert_not_called()

    def test_main_reports_interactive_wait_process_option_errors(self) -> None:
        stdout = io.StringIO()

        with (
            patch(
                "builtins.input",
                side_effect=[
                    "/wait-process --timeout-ms 99 -- bg-1",
                    "/wait-process bg-1 --stdout",
                    "/wait-process --stdout ready",
                    "/wait-process bg-1 --unknown 1",
                    "/wait-process bg-1 --max-chars 999",
                    "/wait-process bg-1 5000 999",
                    "/exit",
                ],
            ),
            patch("vibeagent.cli.create_chat_client") as create_chat_client,
            patch("vibeagent.cli.get_wait_process_text") as get_wait_process_text,
            redirect_stdout(stdout),
        ):
            exit_code = main()

        output = stdout.getvalue()
        self.assertEqual(exit_code, 0)
        self.assertIn("Usage: /wait-process <id> [timeout-ms] [chars]", output)
        self.assertIn("--timeout-ms must be at least 100.", output)
        self.assertIn("--stdout requires a value.", output)
        self.assertIn("process id is required.", output)
        self.assertIn("Unknown option: --unknown", output)
        self.assertIn("max chars must be at least 1000.", output)
        self.assertIn("invalid max chars: 999", output)
        get_wait_process_text.assert_not_called()
        create_chat_client.assert_not_called()

    def test_main_parses_interactive_run_limit_options(self) -> None:
        stdout = io.StringIO()

        with (
            patch(
                "builtins.input",
                side_effect=[
                    "/run --cwd src --timeout-ms 2000 --max-chars 3000 --output-contexts --output-diagnostics --context-lines 2 --max-diagnostics 7 --max-contexts 5 --max-bytes 1000 -- python3 --version",
                    "/exit",
                ],
            ),
            patch("vibeagent.cli.create_chat_client") as create_chat_client,
            patch("vibeagent.cli.get_run_text", return_value="Run:\n  ok: yes") as get_run_text,
            redirect_stdout(stdout),
        ):
            exit_code = main()

        output = stdout.getvalue()
        self.assertEqual(exit_code, 0)
        self.assertIn("Run:", output)
        get_run_text.assert_called_once_with(
            command="python3 --version",
            cwd="src",
            timeout_ms=2000,
            max_output_chars=3000,
            extract_output_contexts=True,
            extract_output_diagnostics=True,
            context_lines=2,
            max_diagnostics=7,
            max_contexts=5,
            max_bytes_per_context=1000,
        )
        create_chat_client.assert_not_called()

    def test_main_reports_interactive_run_limit_errors(self) -> None:
        stdout = io.StringIO()

        with (
            patch(
                "builtins.input",
                side_effect=[
                    "/run --timeout-ms 99 -- python3 --version",
                    "/run --max-diagnostics 0 -- python3 --version",
                    "/run --output-diagnostics",
                    "/exit",
                ],
            ),
            patch("vibeagent.cli.create_chat_client") as create_chat_client,
            patch("vibeagent.cli.get_run_text") as get_run_text,
            redirect_stdout(stdout),
        ):
            exit_code = main()

        output = stdout.getvalue()
        self.assertEqual(exit_code, 0)
        self.assertIn("Usage: /run [--timeout-ms N]", output)
        self.assertIn("--timeout-ms must be at least 100.", output)
        self.assertIn("--max-diagnostics must be a positive integer.", output)
        self.assertIn("command is required.", output)
        get_run_text.assert_not_called()
        create_chat_client.assert_not_called()

    def test_main_parses_interactive_run_sequence_limit_options(self) -> None:
        stdout = io.StringIO()

        with (
            patch(
                "builtins.input",
                side_effect=[
                    "/run-seq --cwd src --timeout-ms 2000 --max-chars 3000 --continue-on-failure --output-contexts --output-diagnostics --context-lines 2 --max-diagnostics 7 --max-contexts 5 --max-bytes 1000 -- python3 --version ;; npm test",
                    "/exit",
                ],
            ),
            patch("vibeagent.cli.create_chat_client") as create_chat_client,
            patch("vibeagent.cli.get_run_sequence_text", return_value="Run sequence:\n  ok: yes") as get_run_sequence_text,
            redirect_stdout(stdout),
        ):
            exit_code = main()

        output = stdout.getvalue()
        self.assertEqual(exit_code, 0)
        self.assertIn("Run sequence:", output)
        get_run_sequence_text.assert_called_once_with(
            commands=["python3 --version", "npm test"],
            cwd="src",
            timeout_ms=2000,
            max_output_chars=3000,
            stop_on_failure=False,
            extract_output_contexts=True,
            extract_output_diagnostics=True,
            context_lines=2,
            max_diagnostics=7,
            max_contexts=5,
            max_bytes_per_context=1000,
        )
        create_chat_client.assert_not_called()

    def test_main_reports_interactive_run_sequence_limit_errors(self) -> None:
        stdout = io.StringIO()

        with (
            patch(
                "builtins.input",
                side_effect=[
                    "/run-seq --timeout-ms 99 -- python3 --version",
                    "/run-seq --max-contexts 0 -- python3 --version",
                    "/run-seq --output-diagnostics",
                    "/exit",
                ],
            ),
            patch("vibeagent.cli.create_chat_client") as create_chat_client,
            patch("vibeagent.cli.get_run_sequence_text") as get_run_sequence_text,
            redirect_stdout(stdout),
        ):
            exit_code = main()

        output = stdout.getvalue()
        self.assertEqual(exit_code, 0)
        self.assertIn("Usage: /run-seq [--timeout-ms N]", output)
        self.assertIn("--timeout-ms must be at least 100.", output)
        self.assertIn("--max-contexts must be a positive integer.", output)
        self.assertIn("at least one command is required.", output)
        get_run_sequence_text.assert_not_called()
        create_chat_client.assert_not_called()

    def test_main_parses_interactive_run_focused_test_limit_options(self) -> None:
        stdout = io.StringIO()

        with (
            patch(
                "builtins.input",
                side_effect=[
                    "/run-focused-tests --max-paths 3 --max-candidates 4 --max-commands 5 --timeout-ms 2000 --max-chars 3000 --continue-on-failure --output-contexts --output-diagnostics --context-lines 2 --max-diagnostics 7 --max-contexts 5 --max-bytes 1000 -- pkg/actions.py tests/test_actions.py",
                    "/exit",
                ],
            ),
            patch("vibeagent.cli.create_chat_client") as create_chat_client,
            patch("vibeagent.cli.get_run_focused_test_commands_text", return_value="Run focused test commands:\n  ok: yes") as get_run_focused_test_commands_text,
            redirect_stdout(stdout),
        ):
            exit_code = main()

        output = stdout.getvalue()
        self.assertEqual(exit_code, 0)
        self.assertIn("Run focused test commands:", output)
        get_run_focused_test_commands_text.assert_called_once_with(
            argument="pkg/actions.py tests/test_actions.py",
            max_paths=3,
            max_candidates=4,
            max_commands=5,
            timeout_ms=2000,
            max_output_chars=3000,
            stop_on_failure=False,
            extract_output_contexts=True,
            extract_output_diagnostics=True,
            context_lines=2,
            max_diagnostics=7,
            max_contexts=5,
            max_bytes_per_context=1000,
        )
        create_chat_client.assert_not_called()

    def test_main_parses_interactive_related_and_focused_test_limit_options(self) -> None:
        stdout = io.StringIO()

        with (
            patch(
                "builtins.input",
                side_effect=[
                    "/related-tests --max-paths 3 --max-candidates 4 -- pkg/actions.py",
                    "/focused-tests --max-paths 5 --max-candidates 6 --max-commands 7 -- pkg/actions.py",
                    "/check-focused-tests --max-paths 8 --max-candidates 9 --max-commands 10 -- pkg/actions.py",
                    "/exit",
                ],
            ),
            patch("vibeagent.cli.create_chat_client") as create_chat_client,
            patch("vibeagent.cli.get_related_tests_text", return_value="Related tests:\n  candidates: 1/1") as get_related_tests_text,
            patch("vibeagent.cli.get_focused_test_commands_text", return_value="Focused test commands:\n  commands: 1/1") as get_focused_test_commands_text,
            patch("vibeagent.cli.get_check_focused_test_commands_text", return_value="Check focused test commands:\n  ok: yes") as get_check_focused_test_commands_text,
            redirect_stdout(stdout),
        ):
            exit_code = main()

        output = stdout.getvalue()
        self.assertEqual(exit_code, 0)
        self.assertIn("Related tests:", output)
        self.assertIn("Focused test commands:", output)
        self.assertIn("Check focused test commands:", output)
        get_related_tests_text.assert_called_once_with(argument="pkg/actions.py", max_paths=3, max_candidates=4)
        get_focused_test_commands_text.assert_called_once_with(argument="pkg/actions.py", max_paths=5, max_candidates=6, max_commands=7)
        get_check_focused_test_commands_text.assert_called_once_with(argument="pkg/actions.py", max_paths=8, max_candidates=9, max_commands=10)
        create_chat_client.assert_not_called()

    def test_main_reports_interactive_test_limit_option_errors(self) -> None:
        stdout = io.StringIO()

        with (
            patch(
                "builtins.input",
                side_effect=[
                    "/related-tests --max-paths 0 -- pkg/actions.py",
                    "/focused-tests --max-commands 0 -- pkg/actions.py",
                    "/check-focused-tests --unknown 1 -- pkg/actions.py",
                    "/exit",
                ],
            ),
            patch("vibeagent.cli.create_chat_client") as create_chat_client,
            patch("vibeagent.cli.get_related_tests_text") as get_related_tests_text,
            patch("vibeagent.cli.get_focused_test_commands_text") as get_focused_test_commands_text,
            patch("vibeagent.cli.get_check_focused_test_commands_text") as get_check_focused_test_commands_text,
            redirect_stdout(stdout),
        ):
            exit_code = main()

        output = stdout.getvalue()
        self.assertEqual(exit_code, 0)
        self.assertIn("Usage: /related-tests [--max-paths N]", output)
        self.assertIn("--max-paths must be a positive integer.", output)
        self.assertIn("Usage: /focused-tests [--max-paths N]", output)
        self.assertIn("--max-commands must be a positive integer.", output)
        self.assertIn("Usage: /check-focused-tests [--max-paths N]", output)
        self.assertIn("Unknown option: --unknown", output)
        get_related_tests_text.assert_not_called()
        get_focused_test_commands_text.assert_not_called()
        get_check_focused_test_commands_text.assert_not_called()
        create_chat_client.assert_not_called()

    def test_main_reports_interactive_run_focused_test_limit_errors(self) -> None:
        stdout = io.StringIO()

        with (
            patch(
                "builtins.input",
                side_effect=[
                    "/run-focused-tests --timeout-ms 99 -- pkg/actions.py",
                    "/run-focused-tests --max-bytes 0 -- pkg/actions.py",
                    "/run-focused-tests --output-contexts=true -- pkg/actions.py",
                    "/exit",
                ],
            ),
            patch("vibeagent.cli.create_chat_client") as create_chat_client,
            patch("vibeagent.cli.get_run_focused_test_commands_text") as get_run_focused_test_commands_text,
            redirect_stdout(stdout),
        ):
            exit_code = main()

        output = stdout.getvalue()
        self.assertEqual(exit_code, 0)
        self.assertIn("Usage: /run-focused-tests [--max-paths N]", output)
        self.assertIn("--timeout-ms must be at least 100.", output)
        self.assertIn("--max-bytes must be a positive integer.", output)
        self.assertIn("--output-contexts does not take a value.", output)
        get_run_focused_test_commands_text.assert_not_called()
        create_chat_client.assert_not_called()

    def test_main_parses_interactive_run_suggested_check_limit_options(self) -> None:
        stdout = io.StringIO()

        with (
            patch(
                "builtins.input",
                side_effect=[
                    "/run-suggested-checks --timeout-ms 2000 --max-chars 3000 --continue-on-failure --output-contexts --output-diagnostics --context-lines 2 --max-diagnostics 7 --max-contexts 5 --max-bytes 1000 -- 2",
                    "/exit",
                ],
            ),
            patch("vibeagent.cli.create_chat_client") as create_chat_client,
            patch("vibeagent.cli.get_run_suggested_checks_text", return_value="Run suggested checks:\n  ok: yes") as get_run_suggested_checks_text,
            redirect_stdout(stdout),
        ):
            exit_code = main()

        output = stdout.getvalue()
        self.assertEqual(exit_code, 0)
        self.assertIn("Run suggested checks:", output)
        get_run_suggested_checks_text.assert_called_once_with(
            argument="2",
            timeout_ms=2000,
            max_output_chars=3000,
            stop_on_failure=False,
            extract_output_contexts=True,
            extract_output_diagnostics=True,
            context_lines=2,
            max_diagnostics=7,
            max_contexts=5,
            max_bytes_per_context=1000,
        )
        create_chat_client.assert_not_called()

    def test_main_parses_interactive_run_suggested_check_named_max_option(self) -> None:
        stdout = io.StringIO()

        with (
            patch(
                "builtins.input",
                side_effect=[
                    "/run-suggested-checks --max-checks 2 --timeout-ms 2000",
                    "/exit",
                ],
            ),
            patch("vibeagent.cli.create_chat_client") as create_chat_client,
            patch("vibeagent.cli.get_run_suggested_checks_text", return_value="Run suggested checks:\n  ok: yes") as get_run_suggested_checks_text,
            redirect_stdout(stdout),
        ):
            exit_code = main()

        output = stdout.getvalue()
        self.assertEqual(exit_code, 0)
        self.assertIn("Run suggested checks:", output)
        get_run_suggested_checks_text.assert_called_once_with(
            argument=None,
            max_checks=2,
            timeout_ms=2000,
        )
        create_chat_client.assert_not_called()

    def test_main_parses_interactive_check_suggested_check_limit_options(self) -> None:
        stdout = io.StringIO()

        with (
            patch(
                "builtins.input",
                side_effect=[
                    "/check-suggested-checks --max-checks 2",
                    "/exit",
                ],
            ),
            patch("vibeagent.cli.create_chat_client") as create_chat_client,
            patch("vibeagent.cli.get_check_suggested_checks_text", return_value="Check suggested checks:\n  ok: yes") as get_check_suggested_checks_text,
            redirect_stdout(stdout),
        ):
            exit_code = main()

        output = stdout.getvalue()
        self.assertEqual(exit_code, 0)
        self.assertIn("Check suggested checks:", output)
        get_check_suggested_checks_text.assert_called_once_with(max_checks=2)
        create_chat_client.assert_not_called()

    def test_main_reports_interactive_check_suggested_check_limit_errors(self) -> None:
        stdout = io.StringIO()

        with (
            patch(
                "builtins.input",
                side_effect=[
                    "/check-suggested-checks --max-checks 0",
                    "/check-suggested-checks --bad",
                    "/exit",
                ],
            ),
            patch("vibeagent.cli.create_chat_client") as create_chat_client,
            patch("vibeagent.cli.get_check_suggested_checks_text") as get_check_suggested_checks_text,
            redirect_stdout(stdout),
        ):
            exit_code = main()

        output = stdout.getvalue()
        self.assertEqual(exit_code, 0)
        self.assertIn("Usage: /check-suggested-checks [--max-checks N]", output)
        self.assertIn("--max-checks must be a positive integer.", output)
        self.assertIn("Unknown option: --bad", output)
        get_check_suggested_checks_text.assert_not_called()
        create_chat_client.assert_not_called()

    def test_main_reports_interactive_run_suggested_check_limit_errors(self) -> None:
        stdout = io.StringIO()

        with (
            patch(
                "builtins.input",
                side_effect=[
                    "/run-suggested-checks --timeout-ms 99 -- 2",
                    "/run-suggested-checks --context-lines -1 -- 2",
                    "/run-suggested-checks --output-diagnostics=true -- 2",
                    "/run-suggested-checks --output-contexts -- 1 2",
                    "/run-suggested-checks --max-checks 1 -- 2",
                    "/exit",
                ],
            ),
            patch("vibeagent.cli.create_chat_client") as create_chat_client,
            patch("vibeagent.cli.get_run_suggested_checks_text") as get_run_suggested_checks_text,
            redirect_stdout(stdout),
        ):
            exit_code = main()

        output = stdout.getvalue()
        self.assertEqual(exit_code, 0)
        self.assertIn("Usage: /run-suggested-checks [--max-checks N]", output)
        self.assertIn("--timeout-ms must be at least 100.", output)
        self.assertIn("--context-lines must be a non-negative integer.", output)
        self.assertIn("--output-diagnostics does not take a value.", output)
        self.assertIn("expected at most one max value.", output)
        self.assertIn("provide either --max-checks or trailing max, not both.", output)
        get_run_suggested_checks_text.assert_not_called()
        create_chat_client.assert_not_called()

    def test_main_parses_interactive_run_session_verification_limit_options(self) -> None:
        stdout = io.StringIO()

        with (
            patch(
                "builtins.input",
                side_effect=[
                    "/run-session-verification run-1 --max-checks 2 --timeout-ms 2000 --max-output-chars 3000 --no-failed --continue-on-failure --output-contexts --output-diagnostics --context-lines 2 --max-diagnostics 7 --max-contexts 5 --max-bytes 1000",
                    "/exit",
                ],
            ),
            patch("vibeagent.cli.create_chat_client") as create_chat_client,
            patch("vibeagent.cli.get_run_session_verification_text", return_value="Run session verification:\n  ok: yes") as get_run_session_verification_text,
            redirect_stdout(stdout),
        ):
            exit_code = main()

        output = stdout.getvalue()
        self.assertEqual(exit_code, 0)
        self.assertIn("Run session verification:", output)
        get_run_session_verification_text.assert_called_once_with(
            run_id="run-1",
            max_checks=2,
            timeout_ms=2000,
            max_output_chars=3000,
            include_failed=False,
            stop_on_failure=False,
            extract_output_contexts=True,
            extract_output_diagnostics=True,
            context_lines=2,
            max_diagnostics=7,
            max_contexts=5,
            max_bytes_per_context=1000,
        )
        create_chat_client.assert_not_called()

    def test_main_reports_interactive_run_session_verification_limit_errors(self) -> None:
        stdout = io.StringIO()

        with (
            patch(
                "builtins.input",
                side_effect=[
                    "/run-session-verification --timeout-ms 99",
                    "/run-session-verification --context-lines -1",
                    "/run-session-verification --output-contexts=true",
                    "/exit",
                ],
            ),
            patch("vibeagent.cli.create_chat_client") as create_chat_client,
            patch("vibeagent.cli.get_run_session_verification_text") as get_run_session_verification_text,
            redirect_stdout(stdout),
        ):
            exit_code = main()

        output = stdout.getvalue()
        self.assertEqual(exit_code, 0)
        self.assertIn("Usage: /run-session-verification [run-id]", output)
        self.assertIn("--timeout-ms must be at least 100.", output)
        self.assertIn("--context-lines must be a non-negative integer.", output)
        self.assertIn("--output-contexts does not take a value.", output)
        get_run_session_verification_text.assert_not_called()
        create_chat_client.assert_not_called()

    def test_main_parses_interactive_preflight_cwd_options(self) -> None:
        stdout = io.StringIO()

        with (
            patch(
                "builtins.input",
                side_effect=[
                    "/command --cwd src -- python3 --version",
                    "/check-run-seq --cwd src -- python3 --version ;; npm test",
                    "/check-start --cwd web -- npm run dev",
                    "/start --cwd web -- npm run dev",
                    "/exit",
                ],
            ),
            patch("vibeagent.cli.create_chat_client") as create_chat_client,
            patch("vibeagent.cli.get_command_check_text", return_value="Command check:\n  ok: yes") as get_command_check_text,
            patch("vibeagent.cli.get_check_run_sequence_text", return_value="Check run sequence:\n  ok: yes") as get_check_run_sequence_text,
            patch("vibeagent.cli.get_check_start_text", return_value="Check start:\n  ok: yes") as get_check_start_text,
            patch("vibeagent.cli.get_start_text", return_value="Start:\n  ok: yes") as get_start_text,
            redirect_stdout(stdout),
        ):
            exit_code = main()

        output = stdout.getvalue()
        self.assertEqual(exit_code, 0)
        self.assertIn("Command check:", output)
        self.assertIn("Check run sequence:", output)
        self.assertIn("Check start:", output)
        self.assertIn("Start:", output)
        get_command_check_text.assert_called_once_with(command="python3 --version", cwd="src")
        get_check_run_sequence_text.assert_called_once_with(commands=["python3 --version", "npm test"], cwd="src")
        get_check_start_text.assert_called_once_with(command="npm run dev", cwd="web")
        get_start_text.assert_called_once_with(command="npm run dev", cwd="web")
        create_chat_client.assert_not_called()

    def test_main_reports_interactive_preflight_cwd_errors(self) -> None:
        stdout = io.StringIO()

        with (
            patch(
                "builtins.input",
                side_effect=[
                    "/command --cwd",
                    "/command --cwd src",
                    "/check-run-seq --cwd src",
                    "/check-start --cwd app --cwd web -- npm run dev",
                    "/start --cwd app --cwd web -- npm run dev",
                    "/exit",
                ],
            ),
            patch("vibeagent.cli.create_chat_client") as create_chat_client,
            patch("vibeagent.cli.get_command_check_text") as get_command_check_text,
            patch("vibeagent.cli.get_check_run_sequence_text") as get_check_run_sequence_text,
            patch("vibeagent.cli.get_check_start_text") as get_check_start_text,
            patch("vibeagent.cli.get_start_text") as get_start_text,
            redirect_stdout(stdout),
        ):
            exit_code = main()

        output = stdout.getvalue()
        self.assertEqual(exit_code, 0)
        self.assertIn("Usage: /command [--cwd PATH] -- <cmd>", output)
        self.assertIn("--cwd requires a value.", output)
        self.assertIn("command is required.", output)
        self.assertIn("Usage: /check-run-seq [--cwd PATH] -- <cmd> ;; <cmd>", output)
        self.assertIn("at least one command is required.", output)
        self.assertIn("Usage: /check-start [--cwd PATH] -- <cmd>", output)
        self.assertIn("Usage: /start [--cwd PATH] -- <cmd>", output)
        self.assertIn("--cwd can only be provided once.", output)
        get_command_check_text.assert_not_called()
        get_check_run_sequence_text.assert_not_called()
        get_check_start_text.assert_not_called()
        get_start_text.assert_not_called()
        create_chat_client.assert_not_called()

    def test_main_parses_interactive_session_detail_limit_options(self) -> None:
        stdout = io.StringIO()

        with (
            patch(
                "builtins.input",
                side_effect=[
                    "/session-verification run-1 --max-checks 2",
                    "/session-commands run-1 --max-commands 2 --max-output-chars 0",
                    "/session-files run-1 --max-files 3",
                    "/session-failures run-1 --max-failures 4 --max-text 80",
                    "/session-audit run-1 --max-failures 5 --max-files 6 --max-commands 7 --max-checks 8 --max-text 90",
                    "/session-handoff run-1 --max-failures 8 --max-files 9 --max-commands 10 --max-checks 11 --max-output-chars 0 --max-text 100",
                    "/exit",
                ],
            ),
            patch("vibeagent.cli.create_chat_client") as create_chat_client,
            patch("vibeagent.cli.get_session_verification_text", return_value="Session verification:\n  session: run-1") as get_session_verification_text,
            patch("vibeagent.cli.get_session_commands_text", return_value="Command results:\n  session: run-1") as get_session_commands_text,
            patch("vibeagent.cli.get_session_files_text", return_value="Session files:\n  session: run-1") as get_session_files_text,
            patch("vibeagent.cli.get_session_failures_text", return_value="Session failures:\n  session: run-1") as get_session_failures_text,
            patch("vibeagent.cli.get_session_audit_text", return_value="Session audit:\n  session: run-1") as get_session_audit_text,
            patch("vibeagent.cli.get_session_handoff_text", return_value="Session handoff:\n  session: run-1") as get_session_handoff_text,
            redirect_stdout(stdout),
        ):
            exit_code = main()

        output = stdout.getvalue()
        self.assertEqual(exit_code, 0)
        self.assertIn("Session verification:", output)
        self.assertIn("Command results:", output)
        self.assertIn("Session files:", output)
        self.assertIn("Session failures:", output)
        self.assertIn("Session audit:", output)
        self.assertIn("Session handoff:", output)
        get_session_verification_text.assert_called_once_with(run_id="run-1", max_checks=2)
        get_session_commands_text.assert_called_once_with(run_id="run-1", max_commands=2, max_output_chars=0)
        get_session_files_text.assert_called_once_with(run_id="run-1", max_files=3)
        get_session_failures_text.assert_called_once_with(run_id="run-1", max_failures=4, max_text=80)
        get_session_audit_text.assert_called_once_with(
            run_id="run-1",
            max_failures=5,
            max_files=6,
            max_commands=7,
            max_checks=8,
            max_text=90,
        )
        get_session_handoff_text.assert_called_once_with(
            run_id="run-1",
            max_failures=8,
            max_files=9,
            max_commands=10,
            max_checks=11,
            max_output_chars=0,
            max_text=100,
        )
        create_chat_client.assert_not_called()

    def test_main_reports_interactive_session_detail_limit_errors(self) -> None:
        stdout = io.StringIO()

        with (
            patch(
                "builtins.input",
                side_effect=[
                    "/session-verification --max-checks 0",
                    "/session-commands --max-output-chars -1",
                    "/session-files --max-files 0",
                    "/session-audit --max-checks 0",
                    "/session-handoff --max-checks 0",
                    "/session-handoff --unknown run-1",
                    "/resume --max-checks 0",
                    "/resume --max-output-chars -1",
                    "/compact --max-checks 0",
                    "/compact --max-output-chars -1",
                    "/exit",
                ],
            ),
            patch("vibeagent.cli.create_chat_client") as create_chat_client,
            patch("vibeagent.cli.get_session_verification_text") as get_session_verification_text,
            patch("vibeagent.cli.get_session_commands_text") as get_session_commands_text,
            patch("vibeagent.cli.get_session_files_text") as get_session_files_text,
            patch("vibeagent.cli.get_session_handoff_text") as get_session_handoff_text,
            patch("vibeagent.cli.get_resume_context") as get_resume_context,
            patch("vibeagent.cli.get_compact_context") as get_compact_context,
            redirect_stdout(stdout),
        ):
            exit_code = main()

        output = stdout.getvalue()
        self.assertEqual(exit_code, 0)
        self.assertIn("Usage: /session-verification [run-id] [--max-checks N]", output)
        self.assertIn("--max-checks must be a positive integer.", output)
        self.assertIn("Usage: /session-commands [run-id] [--max-commands N] [--max-output-chars N]", output)
        self.assertIn("--max-output-chars must be a non-negative integer.", output)
        self.assertIn("Usage: /session-files [run-id] [--max-files N]", output)
        self.assertIn("--max-files must be a positive integer.", output)
        self.assertIn("Usage: /session-audit [run-id]", output)
        self.assertIn("Usage: /session-handoff [run-id]", output)
        self.assertIn("Usage: /resume [run-id|off] [--max-failures N]", output)
        self.assertIn("Usage: /compact [run-id] [--max-failures N]", output)
        self.assertIn("Unknown option: --unknown", output)
        get_session_verification_text.assert_not_called()
        get_session_commands_text.assert_not_called()
        get_session_files_text.assert_not_called()
        get_session_handoff_text.assert_not_called()
        get_resume_context.assert_not_called()
        get_compact_context.assert_not_called()
        create_chat_client.assert_not_called()

    def test_main_status_command_reports_local_state_without_creating_client(self) -> None:
        stdout = io.StringIO()

        with (
            patch(
                "builtins.input",
                side_effect=[
                    "/status",
                    "/chat",
                    "/approval allow",
                    "/resume run-1",
                    "/status",
                    "/exit",
                ],
            ),
            patch("vibeagent.cli.create_chat_client") as create_chat_client,
            patch("vibeagent.cli.get_resume_context", return_value=("run-1", "context", "Resume context loaded from session run-1.")),
            redirect_stdout(stdout),
        ):
            exit_code = main()

        output = stdout.getvalue()
        self.assertEqual(exit_code, 0)
        self.assertIn("mode: code", output)
        self.assertIn("approval: ask", output)
        self.assertIn("resume: none", output)
        self.assertIn("mode: chat", output)
        self.assertIn("approval: allow", output)
        self.assertIn("resume: run-1", output)
        create_chat_client.assert_not_called()

    def test_main_passes_resume_context_to_agent(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
            result = AgentResult(
                success=True,
                message="done",
                run_dir=Path(base),
                run_id="new-run",
                iterations=1,
                observations=[],
                steps=[],
            )
            stdout = io.StringIO()
            run_agent = Mock(return_value=result)

            with (
                patch(
                    "builtins.input",
                    side_effect=[
                        "/resume run-1 --max-failures 3 --max-files 4 --max-commands 5 --max-checks 2 --max-output-chars 0 --max-text 90",
                        "continue task",
                        "/exit",
                    ],
                ),
                patch("vibeagent.cli.create_chat_client", return_value=object()),
                patch("vibeagent.cli.get_resume_context", side_effect=[
                    ("run-1", "previous context", "Resume context loaded from session run-1."),
                    ("new-run", "new context", "Resume context loaded from session new-run."),
                ]) as get_resume_context,
                patch("vibeagent.cli.run_agent", run_agent),
                redirect_stdout(stdout),
            ):
                exit_code = main()

        self.assertEqual(exit_code, 0)
        self.assertEqual(
            get_resume_context.call_args_list[0].kwargs,
            {
                "max_failures": 3,
                "max_files": 4,
                "max_commands": 5,
                "max_checks": 2,
                "max_output_chars": 0,
                "max_text": 90,
            },
        )
        self.assertEqual(run_agent.call_args.kwargs["prior_context"], "previous context")

    def test_main_starts_interactive_with_resume_context_from_cli_args(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
            result = AgentResult(
                success=True,
                message="done",
                run_dir=Path(base),
                run_id="new-run",
                iterations=1,
                observations=[],
                steps=[],
            )
            stdout = io.StringIO()
            run_agent = Mock(return_value=result)

            with (
                patch("builtins.input", side_effect=["continue task", "/exit"]),
                patch("vibeagent.cli.create_chat_client", return_value=object()),
                patch("vibeagent.cli.get_resume_context", side_effect=[
                    ("run-1", "startup context", "Resume context loaded from session run-1."),
                    ("new-run", "new context", "Resume context loaded from session new-run."),
                ]) as get_resume_context,
                patch("vibeagent.cli.run_agent", run_agent),
                redirect_stdout(stdout),
            ):
                exit_code = main(["--cwd", base, "--resume", "run-1", "--resume-max-files", "4"])

        self.assertEqual(exit_code, 0)
        get_resume_context.assert_any_call("run-1", Path(base).resolve(), max_files=4)
        self.assertEqual(run_agent.call_args.kwargs["prior_context"], "startup context")
        self.assertIn("Resume context loaded from session run-1.", stdout.getvalue())

    def test_main_continue_without_task_starts_interactive_with_latest_resume_context(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
            result = AgentResult(
                success=True,
                message="done",
                run_dir=Path(base),
                run_id="new-run",
                iterations=1,
                observations=[],
                steps=[],
            )
            run_agent = Mock(return_value=result)

            with (
                patch("builtins.input", side_effect=["continue task", "/exit"]),
                patch("vibeagent.cli.create_chat_client", return_value=object()),
                patch("vibeagent.cli.get_resume_context", side_effect=[
                    ("latest-run", "latest context", "Resume context loaded from session latest-run."),
                    ("new-run", "new context", "Resume context loaded from session new-run."),
                ]) as get_resume_context,
                patch("vibeagent.cli.run_agent", run_agent),
                redirect_stdout(io.StringIO()),
            ):
                exit_code = main(["--cwd", base, "-c"])

        self.assertEqual(exit_code, 0)
        get_resume_context.assert_any_call(None, Path(base).resolve())
        self.assertEqual(run_agent.call_args.kwargs["prior_context"], "latest context")

    def test_main_startup_resume_missing_context_does_not_create_client(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
            stdout = io.StringIO()
            with (
                patch("vibeagent.cli.create_chat_client") as create_chat_client,
                patch("vibeagent.cli.get_resume_context", return_value=(None, None, "Session not found: missing")),
                redirect_stdout(stdout),
            ):
                exit_code = main(["--cwd", base, "--resume", "missing"])

        self.assertEqual(exit_code, 2)
        self.assertIn("Session not found: missing", stdout.getvalue())
        create_chat_client.assert_not_called()

    def test_main_starts_interactive_with_compact_context_from_cli_args(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
            result = AgentResult(
                success=True,
                message="done",
                run_dir=Path(base),
                run_id="new-run",
                iterations=1,
                observations=[],
                steps=[],
            )
            run_agent = Mock(return_value=result)

            with (
                patch("builtins.input", side_effect=["continue task", "/exit"]),
                patch("vibeagent.cli.create_chat_client", return_value=object()),
                patch(
                    "vibeagent.cli.get_compact_context",
                    return_value=("run-1", "startup compact context", "Compacted context loaded from session run-1."),
                ) as get_compact_context,
                patch("vibeagent.cli.get_resume_context", return_value=("new-run", "new context", "Resume context loaded from session new-run.")),
                patch("vibeagent.cli.run_agent", run_agent),
                redirect_stdout(io.StringIO()),
            ):
                exit_code = main(["--cwd", base, "--compact", "run-1", "--compact-max-checks", "2"])

        self.assertEqual(exit_code, 0)
        get_compact_context.assert_called_once_with("run-1", Path(base).resolve(), max_checks=2)
        self.assertEqual(run_agent.call_args.kwargs["prior_context"], "startup compact context")

    def test_main_starts_interactive_with_session_id_resume_context(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
            result = AgentResult(
                success=True,
                message="done",
                run_dir=Path(base),
                run_id="new-run",
                iterations=1,
                observations=[],
                steps=[],
            )
            run_agent = Mock(return_value=result)

            with (
                patch("builtins.input", side_effect=["continue task", "/exit"]),
                patch("vibeagent.cli.create_chat_client", return_value=object()),
                patch(
                    "vibeagent.cli.get_resume_context",
                    side_effect=[
                        ("run-1", "startup resume context", "Resume context loaded from session run-1."),
                        ("new-run", "new context", "Resume context loaded from session new-run."),
                    ],
                ) as get_resume_context,
                patch("vibeagent.cli.run_agent", run_agent),
                redirect_stdout(io.StringIO()),
            ):
                exit_code = main(["--cwd", base, "--session-id", "run-1", "--resume-max-checks", "2"])

        self.assertEqual(exit_code, 0)
        self.assertEqual(get_resume_context.call_args_list[0].args, ("run-1", Path(base).resolve()))
        self.assertEqual(get_resume_context.call_args_list[0].kwargs, {"max_checks": 2})
        self.assertEqual(run_agent.call_args.kwargs["prior_context"], "startup resume context")

    def test_main_starts_interactive_with_session_id_latest_resume_context(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
            result = AgentResult(
                success=True,
                message="done",
                run_dir=Path(base),
                run_id="new-run",
                iterations=1,
                observations=[],
                steps=[],
            )
            run_agent = Mock(return_value=result)

            with (
                patch("builtins.input", side_effect=["continue task", "/exit"]),
                patch("vibeagent.cli.create_chat_client", return_value=object()),
                patch(
                    "vibeagent.cli.get_resume_context",
                    side_effect=[
                        ("latest-run", "startup latest context", "Resume context loaded from session latest-run."),
                        ("new-run", "new context", "Resume context loaded from session new-run."),
                    ],
                ) as get_resume_context,
                patch("vibeagent.cli.run_agent", run_agent),
                redirect_stdout(io.StringIO()),
            ):
                exit_code = main(["--cwd", base, "--session-id", "latest"])

        self.assertEqual(exit_code, 0)
        self.assertEqual(get_resume_context.call_args_list[0].args, (None, Path(base).resolve()))
        self.assertEqual(run_agent.call_args.kwargs["prior_context"], "startup latest context")

    def test_main_resume_off_clears_context_before_next_agent_run(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
            result = AgentResult(
                success=True,
                message="done",
                run_dir=Path(base),
                run_id="new-run",
                iterations=1,
                observations=[],
                steps=[],
            )
            stdout = io.StringIO()
            run_agent = Mock(return_value=result)

            with (
                patch("builtins.input", side_effect=["/resume run-1", "/resume off", "fresh task", "/exit"]),
                patch("vibeagent.cli.create_chat_client", return_value=object()),
                patch(
                    "vibeagent.cli.get_resume_context",
                    side_effect=[
                        ("run-1", "previous context", "Resume context loaded from session run-1."),
                        (None, None, "Resume context cleared."),
                        ("new-run", "new context", "Resume context loaded from session new-run."),
                    ],
                ),
                patch("vibeagent.cli.run_agent", run_agent),
                redirect_stdout(stdout),
            ):
                exit_code = main()

        self.assertEqual(exit_code, 0)
        self.assertIsNone(run_agent.call_args.kwargs["prior_context"])
        self.assertIn("Resume context cleared.", stdout.getvalue())

    def test_main_clear_clears_context_before_next_agent_run(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
            result = AgentResult(
                success=True,
                message="done",
                run_dir=Path(base),
                run_id="new-run",
                iterations=1,
                observations=[],
                steps=[],
            )
            stdout = io.StringIO()
            run_agent = Mock(return_value=result)

            with (
                patch("builtins.input", side_effect=["/resume run-1", "/clear", "fresh task", "/exit"]),
                patch("vibeagent.cli.create_chat_client", return_value=object()),
                patch(
                    "vibeagent.cli.get_resume_context",
                    side_effect=[
                        ("run-1", "previous context", "Resume context loaded from session run-1."),
                        ("new-run", "new context", "Resume context loaded from session new-run."),
                    ],
                ),
                patch("vibeagent.cli.run_agent", run_agent),
                redirect_stdout(stdout),
            ):
                exit_code = main()

        self.assertEqual(exit_code, 0)
        self.assertIsNone(run_agent.call_args.kwargs["prior_context"])
        self.assertIn("Cleared chat history and resume context.", stdout.getvalue())

    def test_main_compact_passes_compacted_context_to_agent(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
            result = AgentResult(
                success=True,
                message="done",
                run_dir=Path(base),
                run_id="new-run",
                iterations=1,
                observations=[],
                steps=[],
            )
            stdout = io.StringIO()
            run_agent = Mock(return_value=result)

            with (
                patch(
                    "builtins.input",
                    side_effect=[
                        "/compact run-1 --max-failures 3 --max-files 4 --max-commands 5 --max-checks 2 --max-output-chars 0 --max-text 90",
                        "continue task",
                        "/exit",
                    ],
                ),
                patch("vibeagent.cli.create_chat_client", return_value=object()),
                patch("vibeagent.cli.get_compact_context", return_value=("run-1", "compacted context", "Compacted context loaded from session run-1.")) as get_compact_context,
                patch("vibeagent.cli.get_resume_context", return_value=("new-run", "new context", "Resume context loaded from session new-run.")),
                patch("vibeagent.cli.run_agent", run_agent),
                redirect_stdout(stdout),
            ):
                exit_code = main()

        output = stdout.getvalue()
        self.assertEqual(exit_code, 0)
        self.assertIn("Compacted context loaded", output)
        get_compact_context.assert_called_once_with(
            "run-1",
            max_failures=3,
            max_files=4,
            max_commands=5,
            max_checks=2,
            max_output_chars=0,
            max_text=90,
        )
        self.assertEqual(run_agent.call_args.kwargs["prior_context"], "compacted context")

    def test_main_updates_approval_policy_and_passes_handler_to_agent(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
            result = AgentResult(
                success=True,
                message="done",
                run_dir=Path(base),
                run_id="test-run",
                iterations=1,
                observations=[],
                steps=[],
            )
            stdout = io.StringIO()
            run_agent = Mock(return_value=result)

            with (
                patch("builtins.input", side_effect=["/approval allow", "write file", "/approval deny", "run command", "/exit"]),
                patch("vibeagent.cli.create_chat_client", return_value=object()),
                patch("vibeagent.cli.run_agent", run_agent),
                redirect_stdout(stdout),
            ):
                exit_code = main()

        self.assertEqual(exit_code, 0)
        output = stdout.getvalue()
        self.assertIn("Approval policy: allow", output)
        self.assertIn("Approval policy: deny", output)
        first_handler = run_agent.call_args_list[0].kwargs["approval_handler"]
        second_handler = run_agent.call_args_list[1].kwargs["approval_handler"]
        self.assertEqual(run_agent.call_args_list[0].kwargs["approval_policy"], "allow")
        self.assertEqual(run_agent.call_args_list[1].kwargs["approval_policy"], "deny")
        request = ApprovalRequest(action_type="write_file", target="note.txt", risk="write")
        self.assertTrue(first_handler(request).approved)
        self.assertFalse(second_handler(request).approved)

    def test_main_interactive_system_prompt_commands_affect_code_and_chat_turns(self) -> None:
        result = AgentResult(
            success=True,
            message="done",
            run_dir=Path(tempfile.gettempdir()),
            run_id="test-run",
            iterations=1,
            observations=[],
            steps=[],
        )
        stdout = io.StringIO()
        run_agent = Mock(return_value=result)
        run_chat = Mock(return_value="chat response")

        with (
            patch(
                "builtins.input",
                side_effect=[
                    "/system-prompt You are a release engineer.",
                    "/append-system-prompt Prefer focused tests.",
                    "inspect code",
                    "/chat explain",
                    "/exit",
                ],
            ),
            patch("vibeagent.cli.create_chat_client", return_value=object()),
            patch("vibeagent.cli.run_agent", run_agent),
            patch("vibeagent.cli.run_chat", run_chat),
            redirect_stdout(stdout),
        ):
            exit_code = main()

        self.assertEqual(exit_code, 0)
        self.assertEqual(run_agent.call_args.kwargs["system_prompt"], "You are a release engineer.")
        self.assertEqual(run_agent.call_args.kwargs["append_system_prompt"], "Prefer focused tests.")
        self.assertEqual(run_chat.call_args.kwargs["system_prompt"], "You are a release engineer.")
        self.assertEqual(run_chat.call_args.kwargs["append_system_prompt"], "Prefer focused tests.")
        output = stdout.getvalue()
        self.assertIn("System prompt set", output)
        self.assertIn("Appended system prompt set", output)

    def test_main_interactive_system_prompt_status_and_clear(self) -> None:
        result = AgentResult(
            success=True,
            message="done",
            run_dir=Path(tempfile.gettempdir()),
            run_id="test-run",
            iterations=1,
            observations=[],
            steps=[],
        )
        stdout = io.StringIO()
        run_agent = Mock(return_value=result)

        with (
            patch(
                "builtins.input",
                side_effect=[
                    "/system-prompt You are terse.",
                    "/append-system-prompt Prefer focused tests.",
                    "/status",
                    "/system-prompt off",
                    "/append-system-prompt off",
                    "inspect code",
                    "/exit",
                ],
            ),
            patch("vibeagent.cli.create_chat_client", return_value=object()),
            patch("vibeagent.cli.run_agent", run_agent),
            redirect_stdout(stdout),
        ):
            exit_code = main()

        output = stdout.getvalue()
        self.assertEqual(exit_code, 0)
        self.assertIn("systemPrompt: custom", output)
        self.assertIn("appendSystemPrompt: set", output)
        self.assertIn("System prompt cleared.", output)
        self.assertIn("Appended system prompt cleared.", output)
        self.assertIsNone(run_agent.call_args.kwargs["system_prompt"])
        self.assertIsNone(run_agent.call_args.kwargs["append_system_prompt"])

    def test_main_interactive_task_keyboard_interrupt_returns_to_prompt(self) -> None:
        stdout = io.StringIO()

        with (
            patch("builtins.input", side_effect=["write file", "/exit"]),
            patch("vibeagent.cli.create_chat_client", return_value=object()),
            patch("vibeagent.cli.run_agent", side_effect=KeyboardInterrupt) as run_agent,
            redirect_stdout(stdout),
        ):
            exit_code = main()

        self.assertEqual(exit_code, 0)
        output = stdout.getvalue()
        self.assertIn("Interrupted.", output)
        self.assertNotIn("Error:", output)
        self.assertEqual(run_agent.call_count, 1)


if __name__ == "__main__":
    unittest.main()
