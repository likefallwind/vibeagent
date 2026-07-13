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


def _run_cli(client: DogfoodClient, args: list[str]) -> tuple[int, str]:
    stdout = io.StringIO()
    with (
        patch("vibeagent.cli.create_chat_client", return_value=client),
        redirect_stdout(stdout),
    ):
        exit_code = main(args)

    return exit_code, stdout.getvalue()


def _run_json_cli(client: DogfoodClient, args: list[str]) -> tuple[int, dict[str, object]]:
    exit_code, output = _run_cli(client, args)
    return exit_code, json.loads(output)


def _run_stream_json_cli(client: DogfoodClient, args: list[str]) -> tuple[int, list[dict[str, object]]]:
    exit_code, output = _run_cli(client, args)
    return exit_code, [json.loads(line) for line in output.splitlines()]


def _git_status(root: Path) -> str:
    return subprocess.run(
        ["git", "status", "--short"],
        cwd=root,
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    ).stdout


def _git_head_subject(root: Path) -> str:
    return subprocess.run(
        ["git", "log", "-1", "--pretty=%s"],
        cwd=root,
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    ).stdout.strip()


def _calc_text(root: Path) -> str:
    return (root / "calc.py").read_text(encoding="utf-8")


def _calculator_commit_state(root: Path) -> tuple[str, str, str]:
    return _git_status(root), _git_head_subject(root), _calc_text(root)


def _session_events(root: Path, run_id: object) -> list[dict[str, object]]:
    events_path = root / ".vibeagent" / "sessions" / str(run_id) / "events.jsonl"
    return [json.loads(line) for line in events_path.read_text(encoding="utf-8").splitlines()]


def _initial_prompt(client: DogfoodClient) -> str:
    return "\n".join(str(message.content) for message in client.messages[0])


def _assert_completed_code_result(
    testcase: unittest.TestCase,
    result: dict[str, object],
    *,
    num_turns: int | None = None,
) -> None:
    testcase.assertEqual(result["kind"], "code")
    testcase.assertEqual(result["status"], "completed")
    testcase.assertEqual(result["stopReason"], "completed")
    testcase.assertTrue(result["success"])
    testcase.assertTrue(result["completionReady"])
    testcase.assertEqual(result["completionBlockers"], [])
    testcase.assertEqual(result["pendingVerificationChecks"], [])
    testcase.assertEqual(result["failedVerificationChecks"], [])
    if num_turns is not None:
        testcase.assertEqual(result["numTurns"], num_turns)


def _assert_clean_calculator_commit(
    testcase: unittest.TestCase,
    state: tuple[str, str, str],
    *,
    expected_subject: str,
) -> None:
    git_status, head_subject, calc_text = state
    testcase.assertEqual(git_status, "")
    testcase.assertEqual(head_subject, expected_subject)
    testcase.assertIn("return left + right", calc_text)


class V1CliSmokeTests(unittest.TestCase):
    def test_v1_cli_json_can_repair_verify_commit_and_report_ready(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-v1-cli-smoke-") as base:
            root = Path(base)
            init_broken_calculator_repo(root)
            client = DogfoodClient(v1_dogfood_responses())
            exit_code, payload = _run_json_cli(
                client,
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
                ],
            )
            commit_state = _calculator_commit_state(root)

        self.assertEqual(exit_code, 0)
        _assert_completed_code_result(self, payload, num_turns=13)
        self.assertTrue(payload["runId"])
        _assert_clean_calculator_commit(self, commit_state, expected_subject="Fix calculator add")

    def test_v1_cli_json_can_resume_interrupted_run_and_commit(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-v1-cli-resume-smoke-") as base:
            root = Path(base)
            init_broken_calculator_repo(root)
            interrupted_client = DogfoodClient(interrupted_dogfood_responses())
            interrupted_exit_code, interrupted_payload = _run_json_cli(
                interrupted_client,
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
                ],
            )
            resumed_client = DogfoodClient(resumed_dogfood_responses())
            resumed_exit_code, resumed_payload = _run_json_cli(
                resumed_client,
                [
                    "--output-format",
                    "json",
                    "--approval",
                    "allow",
                    "--cwd",
                    str(root),
                    "--resume",
                    str(interrupted_payload["runId"]),
                    "--max-iterations",
                    "12",
                    "Continue from the previous VibeAgent session and commit the verified fix.",
                ],
            )
            initial_resumed_prompt = _initial_prompt(resumed_client)
            commit_state = _calculator_commit_state(root)

        self.assertEqual(interrupted_exit_code, 1)
        self.assertEqual(interrupted_payload["kind"], "code")
        self.assertFalse(interrupted_payload["success"])
        self.assertEqual(interrupted_payload["status"], "failed")
        self.assertTrue(interrupted_payload["runId"])
        self.assertEqual(resumed_exit_code, 0)
        _assert_completed_code_result(self, resumed_payload)
        self.assertEqual(resumed_payload["priorContext"], {
            "loaded": True,
            "source": "resume",
            "runId": interrupted_payload["runId"],
        })
        self.assertIn("Previous session context:", initial_resumed_prompt)
        self.assertIn("python -B -m unittest discover -s tests", initial_resumed_prompt)
        _assert_clean_calculator_commit(self, commit_state, expected_subject="Fix calculator add after resume")

    def test_v1_cli_json_can_compact_interrupted_run_and_commit(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-v1-cli-compact-smoke-") as base:
            root = Path(base)
            init_broken_calculator_repo(root)
            interrupted_client = DogfoodClient(interrupted_dogfood_responses())
            interrupted_exit_code, interrupted_payload = _run_json_cli(
                interrupted_client,
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
                ],
            )
            resumed_client = DogfoodClient(resumed_dogfood_responses())
            resumed_exit_code, resumed_payload = _run_json_cli(
                resumed_client,
                [
                    "--output-format",
                    "json",
                    "--approval",
                    "allow",
                    "--cwd",
                    str(root),
                    "--compact",
                    str(interrupted_payload["runId"]),
                    "--max-iterations",
                    "12",
                    "Continue from the compacted VibeAgent session and commit the verified fix.",
                ],
            )
            initial_resumed_prompt = _initial_prompt(resumed_client)
            commit_state = _calculator_commit_state(root)

        self.assertEqual(interrupted_exit_code, 1)
        self.assertFalse(interrupted_payload["success"])
        self.assertTrue(interrupted_payload["runId"])
        self.assertEqual(resumed_exit_code, 0)
        _assert_completed_code_result(self, resumed_payload)
        self.assertEqual(resumed_payload["priorContext"], {
            "loaded": True,
            "source": "compact",
            "runId": interrupted_payload["runId"],
        })
        self.assertIn("Previous session context:", initial_resumed_prompt)
        self.assertIn("python -B -m unittest discover -s tests", initial_resumed_prompt)
        _assert_clean_calculator_commit(self, commit_state, expected_subject="Fix calculator add after resume")

    def test_v1_cli_stream_json_can_repair_with_allowed_tools_and_report_events(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-v1-cli-stream-smoke-") as base:
            root = Path(base)
            init_broken_calculator_repo(root)
            client = DogfoodClient(claude_compat_dogfood_responses())
            exit_code, records = _run_stream_json_cli(
                client,
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
                ],
            )
            event_records = [record for record in records if record["type"] == "event"]
            event_types = [record["event"]["type"] for record in event_records]
            tool_names = [
                record["event"]["name"]
                for record in event_records
                if record["event"]["type"] == "tool_call"
            ]
            permissions = next(record["event"] for record in event_records if record["event"]["type"] == "permissions_loaded")
            final = records[-1]
            commit_state = _calculator_commit_state(root)

        self.assertEqual(exit_code, 0)
        self.assertEqual([record["sequence"] for record in records], list(range(1, len(records) + 1)))
        self.assertEqual(records[-1]["type"], "result")
        _assert_completed_code_result(self, final)
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
        _assert_clean_calculator_commit(self, commit_state, expected_subject="Fix calculator add via Claude aliases")

    def test_v1_cli_dangerously_skip_permissions_can_repair_with_claude_aliases(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-v1-cli-skip-perms-smoke-") as base:
            root = Path(base)
            init_broken_calculator_repo(root)
            client = DogfoodClient(claude_compat_dogfood_responses())
            exit_code, payload = _run_json_cli(
                client,
                [
                    "--output-format",
                    "json",
                    "--dangerously-skip-permissions",
                    "--cwd",
                    str(root),
                    "--max-iterations",
                    "14",
                    "Fix the calculator test failure using Claude-style tools and commit the verified fix.",
                ],
            )
            events = _session_events(root, payload["runId"])
            events_text = "\n".join(json.dumps(event, sort_keys=True) for event in events)
            approval_decisions = [event["decision"] for event in events if event["type"] == "approval_decision"]
            commit_state = _calculator_commit_state(root)

        self.assertEqual(exit_code, 0)
        _assert_completed_code_result(self, payload)
        _assert_clean_calculator_commit(self, commit_state, expected_subject="Fix calculator add via Claude aliases")
        self.assertIn('"name": "Bash"', events_text)
        self.assertIn('"name": "Edit"', events_text)
        self.assertIn('"name": "git_commit"', events_text)
        self.assertEqual(events[0]["approval_policy"], "allow")
        self.assertGreaterEqual(len(approval_decisions), 1)
        self.assertTrue(all(decision["approved"] for decision in approval_decisions))
        self.assertTrue(all("Approved by policy" in decision["message"] for decision in approval_decisions))


if __name__ == "__main__":
    unittest.main()
