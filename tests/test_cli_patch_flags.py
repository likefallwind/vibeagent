import io
import json
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import patch

from vibeagent.cli import main


class CliPatchFlagTests(unittest.TestCase):
    def test_main_runs_patch_local_flags_without_creating_client(self) -> None:
        patch_text = "@@ -1 +1 @@\n-old\n+new\n"
        with tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
            stdout = io.StringIO()

            with (
                patch("vibeagent.cli.create_chat_client") as create_chat_client,
                patch("vibeagent.cli.get_check_patch_text", return_value="Check patch:\n  ok: yes") as get_check_patch_text,
                redirect_stdout(stdout),
            ):
                exit_code = main(["--cwd", base, "--check-patch", "app.py", patch_text])

        self.assertEqual(exit_code, 0)
        self.assertIn("Check patch:", stdout.getvalue())
        get_check_patch_text.assert_called_once_with(Path(base).resolve(), path="app.py", patch=patch_text)
        create_chat_client.assert_not_called()

        with tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
            stdout = io.StringIO()
            with (
                patch("vibeagent.cli.create_chat_client") as create_chat_client,
                patch("vibeagent.cli.get_patch_text", return_value="Patch:\n  ok: yes") as get_patch_text,
                redirect_stdout(stdout),
            ):
                exit_code = main(["--cwd", base, "--patch", "app.py", "-"])

        self.assertEqual(exit_code, 0)
        self.assertIn("Patch:", stdout.getvalue())
        get_patch_text.assert_called_once_with(Path(base).resolve(), path="app.py", patch="-")
        create_chat_client.assert_not_called()

        cases = [
            (
                "--check-patch",
                "vibeagent.cli.get_check_patch_report",
                "Check patch:",
                "checkPatch",
                patch_text,
            ),
            (
                "--patch",
                "vibeagent.cli.get_patch_report",
                "Patch:",
                "patch",
                "-",
            ),
        ]
        for flag, getter_target, title, payload_key, cli_patch in cases:
            with self.subTest(payload_key=payload_key), tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
                stdout = io.StringIO()
                report = {
                    "projectRoot": str(Path(base).resolve()),
                    "kind": payload_key,
                    "ok": True,
                    "path": "app.py",
                    "message": "ok",
                    "diff": {"text": "+new\n", "lines": ["+new"], "lineCount": 1},
                }
                rendered = f"{title}\n  ok: yes"
                with (
                    patch("vibeagent.cli.create_chat_client") as create_chat_client,
                    patch(getter_target, return_value=report) as getter,
                    patch("vibeagent.cli.format_patch_report_text", return_value=rendered) as formatter,
                    redirect_stdout(stdout),
                ):
                    exit_code = main(["--json", "--cwd", base, flag, "app.py", cli_patch])

                payload = json.loads(stdout.getvalue())
                self.assertEqual(exit_code, 0)
                self.assertTrue(payload["success"])
                self.assertEqual(payload[payload_key], report)
                self.assertEqual(payload["text"], rendered)
                getter.assert_called_once_with(Path(base).resolve(), path="app.py", patch=cli_patch)
                formatter.assert_called_once_with(title, report)
                create_chat_client.assert_not_called()

    def test_main_runs_patches_local_flags_without_creating_client(self) -> None:
        patch_text = "--- a/app.py\n+++ b/app.py\n@@ -1 +1 @@\n-old\n+new\n"
        with tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
            stdout = io.StringIO()

            with (
                patch("vibeagent.cli.create_chat_client") as create_chat_client,
                patch("vibeagent.cli.get_check_patches_text", return_value="Check patches:\n  ok: yes") as get_check_patches_text,
                redirect_stdout(stdout),
            ):
                exit_code = main(["--cwd", base, "--check-patches", patch_text])

        self.assertEqual(exit_code, 0)
        self.assertIn("Check patches:", stdout.getvalue())
        get_check_patches_text.assert_called_once_with(Path(base).resolve(), patch=patch_text)
        create_chat_client.assert_not_called()

        with tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
            stdout = io.StringIO()
            with (
                patch("vibeagent.cli.create_chat_client") as create_chat_client,
                patch("vibeagent.cli.get_patches_text", return_value="Patches:\n  ok: yes") as get_patches_text,
                redirect_stdout(stdout),
            ):
                exit_code = main(["--cwd", base, "--patches", "-"])

        self.assertEqual(exit_code, 0)
        self.assertIn("Patches:", stdout.getvalue())
        get_patches_text.assert_called_once_with(Path(base).resolve(), patch="-")
        create_chat_client.assert_not_called()

        cases = [
            (
                "--check-patches",
                "vibeagent.cli.get_check_patches_report",
                "Check patches:",
                "checkPatches",
                patch_text,
            ),
            (
                "--patches",
                "vibeagent.cli.get_patches_report",
                "Patches:",
                "patches",
                "-",
            ),
        ]
        for flag, getter_target, title, payload_key, cli_patch in cases:
            with self.subTest(payload_key=payload_key), tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
                stdout = io.StringIO()
                report = {
                    "projectRoot": str(Path(base).resolve()),
                    "kind": payload_key,
                    "ok": True,
                    "files": {"total": 2, "items": ["app.py", "config.py"]},
                    "message": "ok",
                    "diff": {"text": "+new\n", "lines": ["+new"], "lineCount": 1},
                }
                rendered = f"{title}\n  ok: yes"
                with (
                    patch("vibeagent.cli.create_chat_client") as create_chat_client,
                    patch(getter_target, return_value=report) as getter,
                    patch("vibeagent.cli.format_patches_report_text", return_value=rendered) as formatter,
                    redirect_stdout(stdout),
                ):
                    exit_code = main(["--json", "--cwd", base, flag, cli_patch])

                payload = json.loads(stdout.getvalue())
                self.assertEqual(exit_code, 0)
                self.assertTrue(payload["success"])
                self.assertEqual(payload[payload_key], report)
                self.assertEqual(payload["text"], rendered)
                getter.assert_called_once_with(Path(base).resolve(), patch=cli_patch)
                formatter.assert_called_once_with(title, report)
                create_chat_client.assert_not_called()
