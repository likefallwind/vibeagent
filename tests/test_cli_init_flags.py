import io
import json
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import patch

from vibeagent.cli import main


class CliInitFlagTests(unittest.TestCase):
    def test_main_keeps_default_instruction_init_behavior(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
            stdout = io.StringIO()

            with (
                patch("vibeagent.cli.create_chat_client") as create_chat_client,
                patch(
                    "vibeagent.cli.init_project_instructions",
                    return_value="Created AGENTS.md.",
                ) as init_project_instructions,
                redirect_stdout(stdout),
            ):
                exit_code = main(["--cwd", base, "--init"])

        self.assertEqual(exit_code, 0)
        self.assertEqual(stdout.getvalue(), "Created AGENTS.md.\n")
        init_project_instructions.assert_called_once_with(
            Path(base).resolve(), "AGENTS.md"
        )
        create_chat_client.assert_not_called()

    def test_main_runs_init_local_flag_with_selected_instruction_file(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
            stdout = io.StringIO()

            with (
                patch("vibeagent.cli.create_chat_client") as create_chat_client,
                patch("vibeagent.cli.init_project_instructions", return_value="Created CLAUDE.md.") as init_project_instructions,
                redirect_stdout(stdout),
            ):
                exit_code = main(["--cwd", base, "--init", "CLAUDE.md"])

        self.assertEqual(exit_code, 0)
        self.assertEqual(stdout.getvalue(), "Created CLAUDE.md.\n")
        init_project_instructions.assert_called_once_with(Path(base).resolve(), "CLAUDE.md")
        create_chat_client.assert_not_called()

    def test_main_runs_init_local_flag_with_json_payload(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
            stdout = io.StringIO()
            report = {
                "projectRoot": str(Path(base).resolve()),
                "requestedFile": "CLAUDE.md",
                "fileName": "CLAUDE.md",
                "path": str(Path(base).resolve() / "CLAUDE.md"),
                "ok": True,
                "created": True,
                "exists": True,
                "error": "",
                "message": "Created CLAUDE.md.",
            }

            with (
                patch("vibeagent.cli.create_chat_client") as create_chat_client,
                patch("vibeagent.cli.get_init_report", return_value=report) as get_init_report,
                patch("vibeagent.cli.format_init_report_text", return_value="Created CLAUDE.md."),
                redirect_stdout(stdout),
            ):
                exit_code = main(["--json", "--cwd", base, "--init", "CLAUDE.md"])

        payload = json.loads(stdout.getvalue())
        self.assertEqual(exit_code, 0)
        self.assertTrue(payload["success"])
        self.assertEqual(payload["init"], report)
        self.assertEqual(payload["text"], "Created CLAUDE.md.")
        get_init_report.assert_called_once_with(Path(base).resolve(), "CLAUDE.md")
        create_chat_client.assert_not_called()


if __name__ == "__main__":
    unittest.main()
