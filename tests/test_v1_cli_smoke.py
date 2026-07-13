from __future__ import annotations

import io
import json
import subprocess
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import patch

from tests.test_v1_dogfood import DogfoodClient, init_broken_calculator_repo, v1_dogfood_responses
from vibeagent.cli import main


class V1CliSmokeTests(unittest.TestCase):
    def test_v1_cli_json_can_repair_verify_commit_and_report_ready(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-v1-cli-smoke-") as base:
            root = Path(base)
            init_broken_calculator_repo(root)
            client = DogfoodClient(v1_dogfood_responses())
            stdout = io.StringIO()

            with (
                patch("vibeagent.cli.create_chat_client", return_value=client),
                redirect_stdout(stdout),
            ):
                exit_code = main(
                    [
                        "--output-format",
                        "json",
                        "--approval",
                        "allow",
                        "--cwd",
                        str(root),
                        "--max-iterations",
                        "14",
                        "Fix the calculator test failure and commit the verified fix.",
                    ]
                )

            payload = json.loads(stdout.getvalue())
            git_status = subprocess.run(
                ["git", "status", "--short"],
                cwd=root,
                check=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            ).stdout
            head_message = subprocess.run(
                ["git", "log", "-1", "--pretty=%s"],
                cwd=root,
                check=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            ).stdout.strip()
            calc_text = (root / "calc.py").read_text(encoding="utf-8")

        self.assertEqual(exit_code, 0)
        self.assertEqual(payload["kind"], "code")
        self.assertEqual(payload["status"], "completed")
        self.assertEqual(payload["stopReason"], "completed")
        self.assertTrue(payload["success"])
        self.assertTrue(payload["completionReady"])
        self.assertEqual(payload["completionBlockers"], [])
        self.assertEqual(payload["pendingVerificationChecks"], [])
        self.assertEqual(payload["failedVerificationChecks"], [])
        self.assertEqual(payload["numTurns"], 13)
        self.assertTrue(payload["runId"])
        self.assertEqual(git_status, "")
        self.assertEqual(head_message, "Fix calculator add")
        self.assertIn("return left + right", calc_text)


if __name__ == "__main__":
    unittest.main()
