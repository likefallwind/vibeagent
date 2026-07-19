import io
import json
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import patch

from vibeagent.cli import main


class CliDirectoryFlagTests(unittest.TestCase):
    def test_main_runs_directory_local_flags_without_creating_client(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
            stdout = io.StringIO()

            with (
                patch("vibeagent.cli.create_chat_client") as create_chat_client,
                patch("vibeagent.cli.get_check_create_dir_text", return_value="Check mkdir:\n  ok: yes") as get_check_create_dir_text,
                redirect_stdout(stdout),
            ):
                exit_code = main(["--cwd", base, "--check-mkdir", "pkg/generated"])

        self.assertEqual(exit_code, 0)
        self.assertIn("Check mkdir:", stdout.getvalue())
        get_check_create_dir_text.assert_called_once_with(Path(base).resolve(), path="pkg/generated")
        create_chat_client.assert_not_called()

        with tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
            stdout = io.StringIO()
            with (
                patch("vibeagent.cli.create_chat_client") as create_chat_client,
                patch("vibeagent.cli.get_create_dir_text", return_value="Mkdir:\n  ok: yes") as get_create_dir_text,
                redirect_stdout(stdout),
            ):
                exit_code = main(["--cwd", base, "--mkdir", "pkg/generated"])

        self.assertEqual(exit_code, 0)
        self.assertIn("Mkdir:", stdout.getvalue())
        get_create_dir_text.assert_called_once_with(Path(base).resolve(), path="pkg/generated")
        create_chat_client.assert_not_called()

        with tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
            stdout = io.StringIO()
            with (
                patch("vibeagent.cli.create_chat_client") as create_chat_client,
                patch("vibeagent.cli.get_check_delete_empty_dir_text", return_value="Check rmdir:\n  ok: yes") as get_check_delete_empty_dir_text,
                redirect_stdout(stdout),
            ):
                exit_code = main(["--cwd", base, "--check-rmdir", "pkg/generated"])

        self.assertEqual(exit_code, 0)
        self.assertIn("Check rmdir:", stdout.getvalue())
        get_check_delete_empty_dir_text.assert_called_once_with(Path(base).resolve(), path="pkg/generated")
        create_chat_client.assert_not_called()

        with tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
            stdout = io.StringIO()
            with (
                patch("vibeagent.cli.create_chat_client") as create_chat_client,
                patch("vibeagent.cli.get_delete_empty_dir_text", return_value="Rmdir:\n  ok: yes") as get_delete_empty_dir_text,
                redirect_stdout(stdout),
            ):
                exit_code = main(["--cwd", base, "--rmdir", "pkg/generated"])

        self.assertEqual(exit_code, 0)
        self.assertIn("Rmdir:", stdout.getvalue())
        get_delete_empty_dir_text.assert_called_once_with(Path(base).resolve(), path="pkg/generated")
        create_chat_client.assert_not_called()

        cases = [
            (
                "--check-mkdir",
                "vibeagent.cli.get_check_create_dir_report",
                "Check mkdir:",
                "checkCreateDir",
                "pkg/generated",
            ),
            (
                "--mkdir",
                "vibeagent.cli.get_create_dir_report",
                "Mkdir:",
                "createDir",
                "pkg/generated",
            ),
            (
                "--check-rmdir",
                "vibeagent.cli.get_check_delete_empty_dir_report",
                "Check rmdir:",
                "checkDeleteEmptyDir",
                "pkg/generated",
            ),
            (
                "--rmdir",
                "vibeagent.cli.get_delete_empty_dir_report",
                "Rmdir:",
                "deleteEmptyDir",
                "pkg/generated",
            ),
        ]
        for flag, getter_target, title, payload_key, cli_path in cases:
            with self.subTest(payload_key=payload_key), tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
                stdout = io.StringIO()
                report = {
                    "projectRoot": str(Path(base).resolve()),
                    "kind": payload_key,
                    "ok": True,
                    "path": cli_path,
                    "message": "ok",
                }
                rendered = f"{title}\n  ok: yes"
                with (
                    patch("vibeagent.cli.create_chat_client") as create_chat_client,
                    patch(getter_target, return_value=report) as getter,
                    patch("vibeagent.cli.format_path_action_report_text", return_value=rendered) as formatter,
                    redirect_stdout(stdout),
                ):
                    exit_code = main(["--json", "--cwd", base, flag, cli_path])

                payload = json.loads(stdout.getvalue())
                self.assertEqual(exit_code, 0)
                self.assertTrue(payload["success"])
                self.assertEqual(payload[payload_key], report)
                self.assertEqual(payload["text"], rendered)
                getter.assert_called_once_with(Path(base).resolve(), path=cli_path)
                formatter.assert_called_once_with(title, report)
                create_chat_client.assert_not_called()

    def test_main_runs_batch_directory_local_flags_without_creating_client(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
            stdout = io.StringIO()

            with (
                patch("vibeagent.cli.create_chat_client") as create_chat_client,
                patch("vibeagent.cli.get_check_create_dirs_text", return_value="Check mkdirs:\n  ok: yes") as get_check_create_dirs_text,
                redirect_stdout(stdout),
            ):
                exit_code = main(["--cwd", base, "--check-mkdirs", "pkg/generated", "assets/icons"])

        self.assertEqual(exit_code, 0)
        self.assertIn("Check mkdirs:", stdout.getvalue())
        get_check_create_dirs_text.assert_called_once_with(Path(base).resolve(), paths=["pkg/generated", "assets/icons"])
        create_chat_client.assert_not_called()

        with tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
            stdout = io.StringIO()
            with (
                patch("vibeagent.cli.create_chat_client") as create_chat_client,
                patch("vibeagent.cli.get_create_dirs_text", return_value="Mkdirs:\n  ok: yes") as get_create_dirs_text,
                redirect_stdout(stdout),
            ):
                exit_code = main(["--cwd", base, "--mkdirs", "pkg/generated", "assets/icons"])

        self.assertEqual(exit_code, 0)
        self.assertIn("Mkdirs:", stdout.getvalue())
        get_create_dirs_text.assert_called_once_with(Path(base).resolve(), paths=["pkg/generated", "assets/icons"])
        create_chat_client.assert_not_called()

        with tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
            stdout = io.StringIO()
            with (
                patch("vibeagent.cli.create_chat_client") as create_chat_client,
                patch("vibeagent.cli.get_check_delete_empty_dirs_text", return_value="Check rmdirs:\n  ok: yes") as get_check_delete_empty_dirs_text,
                redirect_stdout(stdout),
            ):
                exit_code = main(["--cwd", base, "--check-rmdirs", "pkg/generated", "assets/icons"])

        self.assertEqual(exit_code, 0)
        self.assertIn("Check rmdirs:", stdout.getvalue())
        get_check_delete_empty_dirs_text.assert_called_once_with(Path(base).resolve(), paths=["pkg/generated", "assets/icons"])
        create_chat_client.assert_not_called()

        with tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
            stdout = io.StringIO()
            with (
                patch("vibeagent.cli.create_chat_client") as create_chat_client,
                patch("vibeagent.cli.get_delete_empty_dirs_text", return_value="Rmdirs:\n  ok: yes") as get_delete_empty_dirs_text,
                redirect_stdout(stdout),
            ):
                exit_code = main(["--cwd", base, "--rmdirs", "pkg/generated", "assets/icons"])

        self.assertEqual(exit_code, 0)
        self.assertIn("Rmdirs:", stdout.getvalue())
        get_delete_empty_dirs_text.assert_called_once_with(Path(base).resolve(), paths=["pkg/generated", "assets/icons"])
        create_chat_client.assert_not_called()

        cases = [
            (
                "--check-mkdirs",
                "vibeagent.cli.get_check_create_dirs_report",
                "Check mkdirs:",
                "checkCreateDirs",
            ),
            (
                "--mkdirs",
                "vibeagent.cli.get_create_dirs_report",
                "Mkdirs:",
                "createDirs",
            ),
            (
                "--check-rmdirs",
                "vibeagent.cli.get_check_delete_empty_dirs_report",
                "Check rmdirs:",
                "checkDeleteEmptyDirs",
            ),
            (
                "--rmdirs",
                "vibeagent.cli.get_delete_empty_dirs_report",
                "Rmdirs:",
                "deleteEmptyDirs",
            ),
        ]
        cli_paths = ["pkg/generated", "assets/icons"]
        for flag, getter_target, title, payload_key in cases:
            with self.subTest(payload_key=payload_key), tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
                stdout = io.StringIO()
                report = {
                    "projectRoot": str(Path(base).resolve()),
                    "kind": payload_key,
                    "ok": True,
                    "paths": {"total": 2, "items": cli_paths},
                    "message": "ok",
                }
                rendered = f"{title}\n  ok: yes"
                with (
                    patch("vibeagent.cli.create_chat_client") as create_chat_client,
                    patch(getter_target, return_value=report) as getter,
                    patch("vibeagent.cli.format_path_list_report_text", return_value=rendered) as formatter,
                    redirect_stdout(stdout),
                ):
                    exit_code = main(["--json", "--cwd", base, flag, *cli_paths])

                payload = json.loads(stdout.getvalue())
                self.assertEqual(exit_code, 0)
                self.assertTrue(payload["success"])
                self.assertEqual(payload[payload_key], report)
                self.assertEqual(payload["text"], rendered)
                getter.assert_called_once_with(Path(base).resolve(), paths=cli_paths)
                formatter.assert_called_once_with(title, report)
                create_chat_client.assert_not_called()
