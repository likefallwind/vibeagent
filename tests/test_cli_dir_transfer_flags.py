import io
import json
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import patch

from vibeagent.cli import main


class CliDirTransferFlagTests(unittest.TestCase):
    def test_main_runs_move_and_copy_dir_local_flags_without_creating_client(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
            stdout = io.StringIO()

            with (
                patch("vibeagent.cli.create_chat_client") as create_chat_client,
                patch("vibeagent.cli.get_check_move_dir_text", return_value="Check move dir:\n  ok: yes") as get_check_move_dir_text,
                redirect_stdout(stdout),
            ):
                exit_code = main(["--cwd", base, "--check-move-dir", "old_pkg", "new_pkg"])

        self.assertEqual(exit_code, 0)
        self.assertIn("Check move dir:", stdout.getvalue())
        get_check_move_dir_text.assert_called_once_with(Path(base).resolve(), source="old_pkg", destination="new_pkg")
        create_chat_client.assert_not_called()

        with tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
            stdout = io.StringIO()
            with (
                patch("vibeagent.cli.create_chat_client") as create_chat_client,
                patch("vibeagent.cli.get_move_dir_text", return_value="Move dir:\n  ok: yes") as get_move_dir_text,
                redirect_stdout(stdout),
            ):
                exit_code = main(["--cwd", base, "--move-dir", "old_pkg", "new_pkg"])

        self.assertEqual(exit_code, 0)
        self.assertIn("Move dir:", stdout.getvalue())
        get_move_dir_text.assert_called_once_with(Path(base).resolve(), source="old_pkg", destination="new_pkg")
        create_chat_client.assert_not_called()

        with tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
            stdout = io.StringIO()
            with (
                patch("vibeagent.cli.create_chat_client") as create_chat_client,
                patch("vibeagent.cli.get_check_copy_dir_text", return_value="Check copy dir:\n  ok: yes") as get_check_copy_dir_text,
                redirect_stdout(stdout),
            ):
                exit_code = main(["--cwd", base, "--check-copy-dir", "template_pkg", "copy_pkg"])

        self.assertEqual(exit_code, 0)
        self.assertIn("Check copy dir:", stdout.getvalue())
        get_check_copy_dir_text.assert_called_once_with(Path(base).resolve(), source="template_pkg", destination="copy_pkg")
        create_chat_client.assert_not_called()

        with tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
            stdout = io.StringIO()
            with (
                patch("vibeagent.cli.create_chat_client") as create_chat_client,
                patch("vibeagent.cli.get_copy_dir_text", return_value="Copy dir:\n  ok: yes") as get_copy_dir_text,
                redirect_stdout(stdout),
            ):
                exit_code = main(["--cwd", base, "--copy-dir", "template_pkg", "copy_pkg"])

        self.assertEqual(exit_code, 0)
        self.assertIn("Copy dir:", stdout.getvalue())
        get_copy_dir_text.assert_called_once_with(Path(base).resolve(), source="template_pkg", destination="copy_pkg")
        create_chat_client.assert_not_called()

        cases = [
            (
                "--check-move-dir",
                "vibeagent.cli.get_check_move_dir_report",
                "Check move dir:",
                "checkMoveDir",
                ["old_pkg", "new_pkg"],
            ),
            (
                "--move-dir",
                "vibeagent.cli.get_move_dir_report",
                "Move dir:",
                "moveDir",
                ["old_pkg", "new_pkg"],
            ),
            (
                "--check-copy-dir",
                "vibeagent.cli.get_check_copy_dir_report",
                "Check copy dir:",
                "checkCopyDir",
                ["template_pkg", "copy_pkg"],
            ),
            (
                "--copy-dir",
                "vibeagent.cli.get_copy_dir_report",
                "Copy dir:",
                "copyDir",
                ["template_pkg", "copy_pkg"],
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

    def test_main_runs_move_and_copy_dirs_local_flags_without_creating_client(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
            stdout = io.StringIO()

            with (
                patch("vibeagent.cli.create_chat_client") as create_chat_client,
                patch("vibeagent.cli.get_check_move_dirs_text", return_value="Check move dirs:\n  ok: yes") as get_check_move_dirs_text,
                redirect_stdout(stdout),
            ):
                exit_code = main(["--cwd", base, "--check-move-dirs", "old_a", "new_a", "old_b", "new_b"])

        self.assertEqual(exit_code, 0)
        self.assertIn("Check move dirs:", stdout.getvalue())
        get_check_move_dirs_text.assert_called_once_with(Path(base).resolve(), transfers=["old_a", "new_a", "old_b", "new_b"])
        create_chat_client.assert_not_called()

        with tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
            stdout = io.StringIO()
            with (
                patch("vibeagent.cli.create_chat_client") as create_chat_client,
                patch("vibeagent.cli.get_move_dirs_text", return_value="Move dirs:\n  ok: yes") as get_move_dirs_text,
                redirect_stdout(stdout),
            ):
                exit_code = main(["--cwd", base, "--move-dirs", "old_a", "new_a", "old_b", "new_b"])

        self.assertEqual(exit_code, 0)
        self.assertIn("Move dirs:", stdout.getvalue())
        get_move_dirs_text.assert_called_once_with(Path(base).resolve(), transfers=["old_a", "new_a", "old_b", "new_b"])
        create_chat_client.assert_not_called()

        with tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
            stdout = io.StringIO()
            with (
                patch("vibeagent.cli.create_chat_client") as create_chat_client,
                patch("vibeagent.cli.get_check_copy_dirs_text", return_value="Check copy dirs:\n  ok: yes") as get_check_copy_dirs_text,
                redirect_stdout(stdout),
            ):
                exit_code = main(["--cwd", base, "--check-copy-dirs", "template_a", "copy_a", "template_b", "copy_b"])

        self.assertEqual(exit_code, 0)
        self.assertIn("Check copy dirs:", stdout.getvalue())
        get_check_copy_dirs_text.assert_called_once_with(Path(base).resolve(), transfers=["template_a", "copy_a", "template_b", "copy_b"])
        create_chat_client.assert_not_called()

        with tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
            stdout = io.StringIO()
            with (
                patch("vibeagent.cli.create_chat_client") as create_chat_client,
                patch("vibeagent.cli.get_copy_dirs_text", return_value="Copy dirs:\n  ok: yes") as get_copy_dirs_text,
                redirect_stdout(stdout),
            ):
                exit_code = main(["--cwd", base, "--copy-dirs", "template_a", "copy_a", "template_b", "copy_b"])

        self.assertEqual(exit_code, 0)
        self.assertIn("Copy dirs:", stdout.getvalue())
        get_copy_dirs_text.assert_called_once_with(Path(base).resolve(), transfers=["template_a", "copy_a", "template_b", "copy_b"])
        create_chat_client.assert_not_called()

        cases = [
            (
                "--check-move-dirs",
                "vibeagent.cli.get_check_move_dirs_report",
                "Check move dirs:",
                "checkMoveDirs",
                ["old_a", "new_a", "old_b", "new_b"],
            ),
            (
                "--move-dirs",
                "vibeagent.cli.get_move_dirs_report",
                "Move dirs:",
                "moveDirs",
                ["old_a", "new_a", "old_b", "new_b"],
            ),
            (
                "--check-copy-dirs",
                "vibeagent.cli.get_check_copy_dirs_report",
                "Check copy dirs:",
                "checkCopyDirs",
                ["template_a", "copy_a", "template_b", "copy_b"],
            ),
            (
                "--copy-dirs",
                "vibeagent.cli.get_copy_dirs_report",
                "Copy dirs:",
                "copyDirs",
                ["template_a", "copy_a", "template_b", "copy_b"],
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
