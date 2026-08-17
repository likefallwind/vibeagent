from __future__ import annotations

from contextlib import redirect_stdout
import io
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from vibeagent import cli as cli_module
from vibeagent.cli_runner import run_one_shot
from vibeagent.startup_file_resources import DownloadedFileResource


class StartupFileCliTests(unittest.TestCase):
    def test_one_shot_downloads_before_creating_model_client(self) -> None:
        events: list[object] = []

        def download(specs, project_root, provider_env):
            events.append(("download", specs, project_root, provider_env["VIBEAGENT_PROVIDER"]))
            return (DownloadedFileResource("file_alpha", "input.bin", 4),)

        def create_client(_provider_env):
            events.append("client")
            return object()

        def run_chat(_task, **_kwargs):
            events.append("chat")
            return "done"

        with tempfile.TemporaryDirectory() as base, patch.dict(
            os.environ,
            {
                "VIBEAGENT_PROVIDER": "anthropic",
                "ANTHROPIC_API_KEY": "test-secret",
            },
        ), redirect_stdout(io.StringIO()):
            exit_code = run_one_shot(
                "inspect input",
                request_mode="chat",
                approval_policy="ask",
                base_dir=base,
                file_resources=("file_alpha:input.bin",),
                create_chat_client_func=create_client,
                run_chat_func=run_chat,
                download_file_resources_func=download,
            )

        self.assertEqual(exit_code, 0)
        self.assertEqual(events[0][0], "download")
        self.assertEqual(events[0][1], ("file_alpha:input.bin",))
        self.assertEqual(events[0][2], Path(base))
        self.assertEqual(events[1:], ["client", "chat"])

    def test_interactive_downloads_before_loop_and_reports_paths(self) -> None:
        events: list[object] = []
        captured_contexts = []

        def download(specs, project_root, provider_env):
            events.append(("download", tuple(specs), project_root, provider_env["VIBEAGENT_PROVIDER"]))
            return (DownloadedFileResource("file_alpha", "fixtures/input.bin", 7),)

        def run_interactive(base_dir, startup_context):
            events.append("interactive")
            captured_contexts.append((base_dir, startup_context))
            return 7

        with tempfile.TemporaryDirectory() as base:
            args = cli_module.parse_args(
                [
                    "--cwd",
                    base,
                    "--provider",
                    "anthropic",
                    "--api-key",
                    "test-secret",
                    "--file",
                    "file_alpha:fixtures/input.bin",
                ]
            )
            with patch.object(cli_module, "download_startup_file_resources", side_effect=download), patch.object(
                cli_module, "run_interactive", side_effect=run_interactive
            ):
                exit_code = cli_module.run_interactive_with_args(args)

        self.assertEqual(exit_code, 7)
        self.assertEqual(events[0][0], "download")
        self.assertEqual(events[0][1], ("file_alpha:fixtures/input.bin",))
        self.assertEqual(events[0][2], Path(base))
        self.assertEqual(events[1], "interactive")
        self.assertEqual(captured_contexts[0][0], base)
        self.assertIn("fixtures/input.bin", captured_contexts[0][1].message or "")


if __name__ == "__main__":
    unittest.main()
