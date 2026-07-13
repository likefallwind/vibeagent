from __future__ import annotations

import io
import json
import subprocess
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import patch

from tests.test_v1_dogfood import (
    DogfoodClient,
    claude_compat_dogfood_responses,
    init_broken_calculator_repo,
    interrupted_dogfood_responses,
    resumed_dogfood_responses,
    v1_dogfood_responses,
)
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

    def test_v1_cli_json_can_resume_interrupted_run_and_commit(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-v1-cli-resume-smoke-") as base:
            root = Path(base)
            init_broken_calculator_repo(root)
            interrupted_client = DogfoodClient(interrupted_dogfood_responses())
            interrupted_stdout = io.StringIO()

            with (
                patch("vibeagent.cli.create_chat_client", return_value=interrupted_client),
                redirect_stdout(interrupted_stdout),
            ):
                interrupted_exit_code = main(
                    [
                        "--output-format",
                        "json",
                        "--approval",
                        "allow",
                        "--cwd",
                        str(root),
                        "--max-iterations",
                        "3",
                        "Fix the calculator test failure and commit the verified fix.",
                    ]
                )

            interrupted_payload = json.loads(interrupted_stdout.getvalue())
            resumed_client = DogfoodClient(resumed_dogfood_responses())
            resumed_stdout = io.StringIO()
            with (
                patch("vibeagent.cli.create_chat_client", return_value=resumed_client),
                redirect_stdout(resumed_stdout),
            ):
                resumed_exit_code = main(
                    [
                        "--output-format",
                        "json",
                        "--approval",
                        "allow",
                        "--cwd",
                        str(root),
                        "--resume",
                        interrupted_payload["runId"],
                        "--max-iterations",
                        "12",
                        "Continue from the previous VibeAgent session and commit the verified fix.",
                    ]
                )

            resumed_payload = json.loads(resumed_stdout.getvalue())
            initial_resumed_prompt = "\n".join(str(message.content) for message in resumed_client.messages[0])
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

        self.assertEqual(interrupted_exit_code, 1)
        self.assertEqual(interrupted_payload["kind"], "code")
        self.assertFalse(interrupted_payload["success"])
        self.assertEqual(interrupted_payload["status"], "failed")
        self.assertTrue(interrupted_payload["runId"])
        self.assertEqual(resumed_exit_code, 0)
        self.assertEqual(resumed_payload["kind"], "code")
        self.assertEqual(resumed_payload["status"], "completed")
        self.assertEqual(resumed_payload["stopReason"], "completed")
        self.assertTrue(resumed_payload["success"])
        self.assertTrue(resumed_payload["completionReady"])
        self.assertEqual(resumed_payload["completionBlockers"], [])
        self.assertEqual(resumed_payload["pendingVerificationChecks"], [])
        self.assertEqual(resumed_payload["failedVerificationChecks"], [])
        self.assertEqual(resumed_payload["priorContext"], {
            "loaded": True,
            "source": "resume",
            "runId": interrupted_payload["runId"],
        })
        self.assertIn("Previous session context:", initial_resumed_prompt)
        self.assertIn("python -B -m unittest discover -s tests", initial_resumed_prompt)
        self.assertEqual(git_status, "")
        self.assertEqual(head_message, "Fix calculator add after resume")
        self.assertIn("return left + right", calc_text)

    def test_v1_cli_stream_json_can_repair_with_allowed_tools_and_report_events(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-v1-cli-stream-smoke-") as base:
            root = Path(base)
            init_broken_calculator_repo(root)
            client = DogfoodClient(claude_compat_dogfood_responses())
            stdout = io.StringIO()

            with (
                patch("vibeagent.cli.create_chat_client", return_value=client),
                redirect_stdout(stdout),
            ):
                exit_code = main(
                    [
                        "--output-format",
                        "stream-json",
                        "--allowed-tools",
                        "Read",
                        "--allowed-tools",
                        "Bash(*)",
                        "--allowed-tools",
                        "Edit",
                        "--allowed-tools",
                        "TodoRead",
                        "--allowed-tools",
                        "TodoWrite",
                        "--allowed-tools",
                        "git_stage",
                        "--allowed-tools",
                        "git_commit",
                        "--allowed-tools",
                        "run_session_verification",
                        "--cwd",
                        str(root),
                        "--max-iterations",
                        "14",
                        "Fix the calculator test failure using Claude-style tools and commit the verified fix.",
                    ]
                )

            records = [json.loads(line) for line in stdout.getvalue().splitlines()]
            event_records = [record for record in records if record["type"] == "event"]
            event_types = [record["event"]["type"] for record in event_records]
            tool_names = [
                record["event"]["name"]
                for record in event_records
                if record["event"]["type"] == "tool_call"
            ]
            permissions = next(record["event"] for record in event_records if record["event"]["type"] == "permissions_loaded")
            final = records[-1]
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
        self.assertEqual([record["sequence"] for record in records], list(range(1, len(records) + 1)))
        self.assertEqual(records[-1]["type"], "result")
        self.assertEqual(final["kind"], "code")
        self.assertEqual(final["status"], "completed")
        self.assertEqual(final["stopReason"], "completed")
        self.assertTrue(final["success"])
        self.assertTrue(final["completionReady"])
        self.assertEqual(final["completionBlockers"], [])
        self.assertEqual(final["pendingVerificationChecks"], [])
        self.assertEqual(final["failedVerificationChecks"], [])
        self.assertIn("permissions_loaded", event_types)
        self.assertIn("permission_rule_evaluated", event_types)
        self.assertNotIn("approval_requested", event_types)
        self.assertNotIn("approval_decision", event_types)
        self.assertIn("<cli --allowed-tools>", permissions["sources"])
        self.assertIn("<cli --allowed-tools>", permissions["trusted_allow_sources"])
        self.assertIn("Bash", tool_names)
        self.assertIn("Edit", tool_names)
        self.assertIn("git_stage", tool_names)
        self.assertIn("git_commit", tool_names)
        self.assertTrue(all(record["runId"] == final["runId"] for record in event_records))
        self.assertEqual(git_status, "")
        self.assertEqual(head_message, "Fix calculator add via Claude aliases")
        self.assertIn("return left + right", calc_text)

    def test_v1_cli_dangerously_skip_permissions_can_repair_with_claude_aliases(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-v1-cli-skip-perms-smoke-") as base:
            root = Path(base)
            init_broken_calculator_repo(root)
            client = DogfoodClient(claude_compat_dogfood_responses())
            stdout = io.StringIO()

            with (
                patch("vibeagent.cli.create_chat_client", return_value=client),
                redirect_stdout(stdout),
            ):
                exit_code = main(
                    [
                        "--output-format",
                        "json",
                        "--dangerously-skip-permissions",
                        "--cwd",
                        str(root),
                        "--max-iterations",
                        "14",
                        "Fix the calculator test failure using Claude-style tools and commit the verified fix.",
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
            events_path = root / ".vibeagent" / "sessions" / payload["runId"] / "events.jsonl"
            events = [json.loads(line) for line in events_path.read_text(encoding="utf-8").splitlines()]
            events_text = "\n".join(json.dumps(event, sort_keys=True) for event in events)
            approval_decisions = [event["decision"] for event in events if event["type"] == "approval_decision"]

        self.assertEqual(exit_code, 0)
        self.assertEqual(payload["kind"], "code")
        self.assertEqual(payload["status"], "completed")
        self.assertEqual(payload["stopReason"], "completed")
        self.assertTrue(payload["success"])
        self.assertTrue(payload["completionReady"])
        self.assertEqual(payload["completionBlockers"], [])
        self.assertEqual(payload["pendingVerificationChecks"], [])
        self.assertEqual(payload["failedVerificationChecks"], [])
        self.assertEqual(git_status, "")
        self.assertEqual(head_message, "Fix calculator add via Claude aliases")
        self.assertIn("return left + right", calc_text)
        self.assertIn('"name": "Bash"', events_text)
        self.assertIn('"name": "Edit"', events_text)
        self.assertIn('"name": "git_commit"', events_text)
        self.assertEqual(events[0]["approval_policy"], "allow")
        self.assertGreaterEqual(len(approval_decisions), 1)
        self.assertTrue(all(decision["approved"] for decision in approval_decisions))
        self.assertTrue(all("Approved by policy" in decision["message"] for decision in approval_decisions))


if __name__ == "__main__":
    unittest.main()
