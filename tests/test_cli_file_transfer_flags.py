import io
import json
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import patch

from vibeagent.cli import main


class CliFileTransferFlagTests(unittest.TestCase):
    def test_main_runs_move_and_copy_file_local_flags_without_creating_client(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
            stdout = io.StringIO()

            with (
                patch("vibeagent.cli.create_chat_client") as create_chat_client,
                patch("vibeagent.cli.get_check_move_file_text", return_value="Check move:\n  ok: yes") as get_check_move_file_text,
                redirect_stdout(stdout),
            ):
                exit_code = main(["--cwd", base, "--check-move", "old.py", "new.py"])

        self.assertEqual(exit_code, 0)
        self.assertIn("Check move:", stdout.getvalue())
        get_check_move_file_text.assert_called_once_with(Path(base).resolve(), source="old.py", destination="new.py")
        create_chat_client.assert_not_called()

        with tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
            stdout = io.StringIO()
            with (
                patch("vibeagent.cli.create_chat_client") as create_chat_client,
                patch("vibeagent.cli.get_move_file_text", return_value="Move:\n  ok: yes") as get_move_file_text,
                redirect_stdout(stdout),
            ):
                exit_code = main(["--cwd", base, "--move", "old.py", "new.py"])

        self.assertEqual(exit_code, 0)
        self.assertIn("Move:", stdout.getvalue())
        get_move_file_text.assert_called_once_with(Path(base).resolve(), source="old.py", destination="new.py")
        create_chat_client.assert_not_called()

        with tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
            stdout = io.StringIO()
            with (
                patch("vibeagent.cli.create_chat_client") as create_chat_client,
                patch("vibeagent.cli.get_check_copy_file_text", return_value="Check copy:\n  ok: yes") as get_check_copy_file_text,
                redirect_stdout(stdout),
            ):
                exit_code = main(["--cwd", base, "--check-copy", "template.py", "new.py"])

        self.assertEqual(exit_code, 0)
        self.assertIn("Check copy:", stdout.getvalue())
        get_check_copy_file_text.assert_called_once_with(Path(base).resolve(), source="template.py", destination="new.py")
        create_chat_client.assert_not_called()

        with tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
            stdout = io.StringIO()
            with (
                patch("vibeagent.cli.create_chat_client") as create_chat_client,
                patch("vibeagent.cli.get_copy_file_text", return_value="Copy:\n  ok: yes") as get_copy_file_text,
                redirect_stdout(stdout),
            ):
                exit_code = main(["--cwd", base, "--copy", "template.py", "new.py"])

        self.assertEqual(exit_code, 0)
        self.assertIn("Copy:", stdout.getvalue())
        get_copy_file_text.assert_called_once_with(Path(base).resolve(), source="template.py", destination="new.py")
        create_chat_client.assert_not_called()

        cases = [
            (
                "--check-move",
                "vibeagent.cli.get_check_move_file_report",
                "Check move:",
                "checkMove",
                ["old.py", "new.py"],
            ),
            (
                "--move",
                "vibeagent.cli.get_move_file_report",
                "Move:",
                "move",
                ["old.py", "new.py"],
            ),
            (
                "--check-copy",
                "vibeagent.cli.get_check_copy_file_report",
                "Check copy:",
                "checkCopy",
                ["template.py", "new.py"],
            ),
            (
                "--copy",
                "vibeagent.cli.get_copy_file_report",
                "Copy:",
                "copy",
                ["template.py", "new.py"],
            ),
        ]
        for flag, getter_target, title, payload_key, cli_args in cases:
            with self.subTest(payload_key=payload_key), tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
                stdout = io.StringIO()
                report = {
                    "projectRoot": str(Path(base).resolve()),
                    "kind": payload_key,
                    "ok": True,
                    "source": cli_args[0],
                    "destination": cli_args[1],
                    "message": "ok",
                }
                rendered = f"{title}\n  ok: yes"
                with (
                    patch("vibeagent.cli.create_chat_client") as create_chat_client,
                    patch(getter_target, return_value=report) as getter,
                    patch("vibeagent.cli.format_file_transfer_report_text", return_value=rendered) as formatter,
                    redirect_stdout(stdout),
                ):
                    exit_code = main(["--json", "--cwd", base, flag, *cli_args])

                payload = json.loads(stdout.getvalue())
                self.assertEqual(exit_code, 0)
                self.assertTrue(payload["success"])
                self.assertEqual(payload[payload_key], report)
                self.assertEqual(payload["text"], rendered)
                getter.assert_called_once_with(Path(base).resolve(), source=cli_args[0], destination=cli_args[1])
                formatter.assert_called_once_with(title, report)
                create_chat_client.assert_not_called()

    def test_main_runs_move_and_copy_files_local_flags_without_creating_client(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
            stdout = io.StringIO()

            with (
                patch("vibeagent.cli.create_chat_client") as create_chat_client,
                patch("vibeagent.cli.get_check_move_files_text", return_value="Check move files:\n  ok: yes") as get_check_move_files_text,
                redirect_stdout(stdout),
            ):
                exit_code = main(["--cwd", base, "--check-move-files", "old.py", "new.py", "other.py", "other-new.py"])

        self.assertEqual(exit_code, 0)
        self.assertIn("Check move files:", stdout.getvalue())
        get_check_move_files_text.assert_called_once_with(Path(base).resolve(), transfers=["old.py", "new.py", "other.py", "other-new.py"])
        create_chat_client.assert_not_called()

        with tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
            stdout = io.StringIO()
            with (
                patch("vibeagent.cli.create_chat_client") as create_chat_client,
                patch("vibeagent.cli.get_move_files_text", return_value="Move files:\n  ok: yes") as get_move_files_text,
                redirect_stdout(stdout),
            ):
                exit_code = main(["--cwd", base, "--move-files", "old.py", "new.py", "other.py", "other-new.py"])

        self.assertEqual(exit_code, 0)
        self.assertIn("Move files:", stdout.getvalue())
        get_move_files_text.assert_called_once_with(Path(base).resolve(), transfers=["old.py", "new.py", "other.py", "other-new.py"])
        create_chat_client.assert_not_called()

        with tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
            stdout = io.StringIO()
            with (
                patch("vibeagent.cli.create_chat_client") as create_chat_client,
                patch("vibeagent.cli.get_check_copy_files_text", return_value="Check copy files:\n  ok: yes") as get_check_copy_files_text,
                redirect_stdout(stdout),
            ):
                exit_code = main(["--cwd", base, "--check-copy-files", "template.py", "new.py", "config.py", "config-copy.py"])

        self.assertEqual(exit_code, 0)
        self.assertIn("Check copy files:", stdout.getvalue())
        get_check_copy_files_text.assert_called_once_with(Path(base).resolve(), transfers=["template.py", "new.py", "config.py", "config-copy.py"])
        create_chat_client.assert_not_called()

        with tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
            stdout = io.StringIO()
            with (
                patch("vibeagent.cli.create_chat_client") as create_chat_client,
                patch("vibeagent.cli.get_copy_files_text", return_value="Copy files:\n  ok: yes") as get_copy_files_text,
                redirect_stdout(stdout),
            ):
                exit_code = main(["--cwd", base, "--copy-files", "template.py", "new.py", "config.py", "config-copy.py"])

        self.assertEqual(exit_code, 0)
        self.assertIn("Copy files:", stdout.getvalue())
        get_copy_files_text.assert_called_once_with(Path(base).resolve(), transfers=["template.py", "new.py", "config.py", "config-copy.py"])
        create_chat_client.assert_not_called()

        cases = [
            (
                "--check-move-files",
                "vibeagent.cli.get_check_move_files_report",
                "Check move files:",
                "checkMoveFiles",
                ["old.py", "new.py", "other.py", "other-new.py"],
            ),
            (
                "--move-files",
                "vibeagent.cli.get_move_files_report",
                "Move files:",
                "moveFiles",
                ["old.py", "new.py", "other.py", "other-new.py"],
            ),
            (
                "--check-copy-files",
                "vibeagent.cli.get_check_copy_files_report",
                "Check copy files:",
                "checkCopyFiles",
                ["template.py", "new.py", "config.py", "config-copy.py"],
            ),
            (
                "--copy-files",
                "vibeagent.cli.get_copy_files_report",
                "Copy files:",
                "copyFiles",
                ["template.py", "new.py", "config.py", "config-copy.py"],
            ),
        ]
        for flag, getter_target, title, payload_key, cli_args in cases:
            with self.subTest(payload_key=payload_key), tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
                stdout = io.StringIO()
                report = {
                    "projectRoot": str(Path(base).resolve()),
                    "kind": payload_key,
                    "ok": True,
                    "transfers": {
                        "total": 2,
                        "items": [
                            {"source": cli_args[0], "destination": cli_args[1]},
                            {"source": cli_args[2], "destination": cli_args[3]},
                        ],
                    },
                    "message": "ok",
                }
                rendered = f"{title}\n  ok: yes"
                with (
                    patch("vibeagent.cli.create_chat_client") as create_chat_client,
                    patch(getter_target, return_value=report) as getter,
                    patch("vibeagent.cli.format_file_transfer_list_report_text", return_value=rendered) as formatter,
                    redirect_stdout(stdout),
                ):
                    exit_code = main(["--json", "--cwd", base, flag, *cli_args])

                payload = json.loads(stdout.getvalue())
                self.assertEqual(exit_code, 0)
                self.assertTrue(payload["success"])
                self.assertEqual(payload[payload_key], report)
                self.assertEqual(payload["text"], rendered)
                getter.assert_called_once_with(Path(base).resolve(), transfers=cli_args)
                formatter.assert_called_once_with(title, report)
                create_chat_client.assert_not_called()
