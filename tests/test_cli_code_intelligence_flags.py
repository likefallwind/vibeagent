import io
import json
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import patch

from vibeagent.cli import main


class CliCodeIntelligenceFlagTests(unittest.TestCase):
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
