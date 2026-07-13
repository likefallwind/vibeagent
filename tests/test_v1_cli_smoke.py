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
    claude_mcp_dogfood_responses,
    claude_notebook_dogfood_responses,
    init_broken_calculator_repo,
    init_mcp_calculator_repo,
    init_broken_notebook_repo,
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


def _run_cli_with_stdin(client: DogfoodClient, args: list[str], stdin_text: str) -> tuple[int, str]:
    stdout = io.StringIO()
    with (
        patch("sys.stdin", io.StringIO(stdin_text)),
        patch("vibeagent.cli.create_chat_client", return_value=client),
        redirect_stdout(stdout),
    ):
        exit_code = main(args)

    return exit_code, stdout.getvalue()


def _run_json_cli(client: DogfoodClient, args: list[str]) -> tuple[int, dict[str, object]]:
    exit_code, output = _run_cli(client, args)
    return exit_code, json.loads(output)


def _run_json_cli_with_stdin(client: DogfoodClient, args: list[str], stdin_text: str) -> tuple[int, dict[str, object]]:
    exit_code, output = _run_cli_with_stdin(client, args, stdin_text)
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


def _notebook_cell_source(root: Path) -> list[str]:
    notebook = json.loads((root / "analysis.ipynb").read_text(encoding="utf-8"))
    return notebook["cells"][1]["source"]


def _notebook_commit_state(root: Path) -> tuple[str, str, list[str]]:
    return _git_status(root), _git_head_subject(root), _notebook_cell_source(root)


def _session_events(root: Path, run_id: object) -> list[dict[str, object]]:
    events_path = root / ".vibeagent" / "sessions" / str(run_id) / "events.jsonl"
    return [json.loads(line) for line in events_path.read_text(encoding="utf-8").splitlines()]


def _initial_prompt(client: DogfoodClient) -> str:
    return "\n".join(str(message.content) for message in client.messages[0])


def pending_user_input_responses() -> list[list[dict[str, object]]]:
    return [
        [
            {
                "type": "tool_call",
                "id": "ask-1",
                "name": "AskUserQuestion",
                "input": {
                    "question": "Should calc.add use addition or subtraction?",
                    "options": ["addition", "subtraction"],
                    "allow_free_text": False,
                },
            }
        ],
        [{"type": "text", "text": "Should calc.add use addition or subtraction?"}],
    ]


def disallowed_edit_responses() -> list[list[dict[str, object]]]:
    return [
        [
            {
                "type": "tool_call",
                "id": "edit-1",
                "name": "Edit",
                "input": {
                    "file_path": "calc.py",
                    "old_string": "return left - right",
                    "new_string": "return left + right",
                },
            }
        ],
        [{"type": "text", "text": "The CLI deny rule blocked the edit."}],
    ]


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


def _assert_clean_notebook_commit(
    testcase: unittest.TestCase,
    state: tuple[str, str, list[str]],
    *,
    expected_subject: str,
) -> None:
    git_status, head_subject, cell_source = state
    testcase.assertEqual(git_status, "")
    testcase.assertEqual(head_subject, expected_subject)
    testcase.assertEqual(cell_source, ["value = 2 + 3\n", "value\n"])


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

    def test_v1_cli_json_input_format_can_repair_verify_commit_and_report_ready(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-v1-cli-input-json-smoke-") as base:
            root = Path(base)
            init_broken_calculator_repo(root)
            client = DogfoodClient(v1_dogfood_responses())
            stdin_payload = json.dumps(
                {
                    "messages": [
                        {"role": "system", "content": "Prefer focused checks before broad suites."},
                        {"role": "assistant", "content": "Previous context: calculator tests are failing."},
                        {"role": "user", "content": "Fix the calculator test failure and commit the verified fix."},
                    ]
                }
            )
            exit_code, payload = _run_json_cli_with_stdin(
                client,
                [
                    "--output-format",
                    "json",
                    "--input-format",
                    "json",
                    "--approval",
                    "allow",
                    "--cwd",
                    str(root),
                    "--max-iterations",
                    "14",
                    "-",
                ],
                stdin_payload,
            )
            initial_prompt = _initial_prompt(client)
            commit_state = _calculator_commit_state(root)

        self.assertEqual(exit_code, 0)
        _assert_completed_code_result(self, payload, num_turns=13)
        self.assertIn("Prefer focused checks before broad suites.", initial_prompt)
        self.assertIn("Structured input assistant messages:", initial_prompt)
        self.assertIn("calculator tests are failing", initial_prompt)
        _assert_clean_calculator_commit(self, commit_state, expected_subject="Fix calculator add")

    def test_v1_cli_json_can_use_strict_mcp_config_before_repair_and_commit(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-v1-cli-mcp-smoke-") as base:
            root = Path(base)
            init_mcp_calculator_repo(root)
            explicit_config = root / "explicit.mcp.json"
            (root / ".mcp.json").replace(explicit_config)
            subprocess.run(["git", "add", "-A"], cwd=root, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            subprocess.run(
                ["git", "commit", "-m", "use explicit mcp config"],
                cwd=root,
                check=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
            client = DogfoodClient(claude_mcp_dogfood_responses())
            exit_code, payload = _run_json_cli(
                client,
                [
                    "--output-format",
                    "json",
                    "--approval",
                    "allow",
                    "--cwd",
                    str(root),
                    "--mcp-config",
                    "explicit.mcp.json",
                    "--strict-mcp-config",
                    "--max-iterations",
                    "17",
                    "Use the configured MCP server for calculator guidance, then fix and commit.",
                ],
            )
            events = _session_events(root, payload["runId"])
            events_text = "\n".join(json.dumps(event, sort_keys=True) for event in events)
            commit_state = _calculator_commit_state(root)

        self.assertEqual(exit_code, 0)
        _assert_completed_code_result(self, payload)
        self.assertIn('"name": "mcp_tools"', events_text)
        self.assertIn('"name": "mcp__test__echo"', events_text)
        self.assertIn("calculator add should sum both operands", events_text)
        _assert_clean_calculator_commit(self, commit_state, expected_subject="Fix calculator add with MCP evidence")

    def test_v1_cli_stream_json_input_format_can_repair_verify_commit_and_report_ready(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-v1-cli-input-stream-smoke-") as base:
            root = Path(base)
            init_broken_calculator_repo(root)
            client = DogfoodClient(v1_dogfood_responses())
            stdin_payload = "\n".join(
                [
                    json.dumps({"type": "system", "text": "Prefer focused checks before broad suites."}),
                    json.dumps({"type": "assistant", "text": "Previous context: calculator tests are failing."}),
                    json.dumps({"type": "user", "text": "Fix the calculator test failure and commit the verified fix."}),
                ]
            )
            exit_code, payload = _run_json_cli_with_stdin(
                client,
                [
                    "--output-format",
                    "json",
                    "--input-format",
                    "stream-json",
                    "--approval",
                    "allow",
                    "--cwd",
                    str(root),
                    "--max-iterations",
                    "14",
                    "-",
                ],
                stdin_payload,
            )
            initial_prompt = _initial_prompt(client)
            commit_state = _calculator_commit_state(root)

        self.assertEqual(exit_code, 0)
        _assert_completed_code_result(self, payload, num_turns=13)
        self.assertIn("Prefer focused checks before broad suites.", initial_prompt)
        self.assertIn("Structured input assistant messages:", initial_prompt)
        self.assertIn("calculator tests are failing", initial_prompt)
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

    def test_v1_cli_stream_json_accept_edits_auto_allows_claude_edit(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-v1-cli-accept-edits-smoke-") as base:
            root = Path(base)
            init_broken_calculator_repo(root)
            client = DogfoodClient(claude_compat_dogfood_responses())
            exit_code, records = _run_stream_json_cli(
                client,
                [
                    "--output-format",
                    "stream-json",
                    "--permission-mode",
                    "acceptEdits",
                    "--allowed-tools",
                    "Read",
                    "--allowed-tools",
                    "Bash(*)",
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
                    "Fix the calculator test failure using acceptEdits and commit the verified fix.",
                ],
            )
            event_records = [record for record in records if record["type"] == "event"]
            event_types = [record["event"]["type"] for record in event_records]
            permission_evaluations = [
                record["event"]
                for record in event_records
                if record["event"]["type"] == "permission_rule_evaluated"
            ]
            permissions = next(record["event"] for record in event_records if record["event"]["type"] == "permissions_loaded")
            final = records[-1]
            commit_state = _calculator_commit_state(root)

        self.assertEqual(exit_code, 0)
        _assert_completed_code_result(self, final)
        self.assertIn("permissions_loaded", event_types)
        self.assertIn("permission_rule_evaluated", event_types)
        self.assertNotIn("approval_requested", event_types)
        self.assertEqual(permissions["count"], 9)
        self.assertIn("<cli --allowed-tools>", permissions["sources"])
        self.assertIn("<cli --permission-mode acceptEdits>", permissions["sources"])
        self.assertIn("<cli --permission-mode acceptEdits>", permissions["trusted_allow_sources"])
        self.assertTrue(
            any(
                event["tool"] == "Edit"
                and event["effect"] == "allow"
                and event["rule"] == "Edit"
                and event["source"] == "<cli --permission-mode acceptEdits>"
                and event["subjects"] == ["calc.py"]
                for event in permission_evaluations
            )
        )
        _assert_clean_calculator_commit(self, commit_state, expected_subject="Fix calculator add via Claude aliases")

    def test_v1_cli_stream_json_accept_edits_auto_allows_claude_notebook_edit(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-v1-cli-accept-notebook-smoke-") as base:
            root = Path(base)
            init_broken_notebook_repo(root)
            client = DogfoodClient(claude_notebook_dogfood_responses())
            exit_code, records = _run_stream_json_cli(
                client,
                [
                    "--output-format",
                    "stream-json",
                    "--permission-mode",
                    "acceptEdits",
                    "--allowed-tools",
                    "Read",
                    "--allowed-tools",
                    "NotebookRead",
                    "--allowed-tools",
                    "Bash(*)",
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
                    "Fix the notebook test failure using acceptEdits and commit the verified fix.",
                ],
            )
            event_records = [record for record in records if record["type"] == "event"]
            event_types = [record["event"]["type"] for record in event_records]
            permission_evaluations = [
                record["event"]
                for record in event_records
                if record["event"]["type"] == "permission_rule_evaluated"
            ]
            permissions = next(record["event"] for record in event_records if record["event"]["type"] == "permissions_loaded")
            final = records[-1]
            commit_state = _notebook_commit_state(root)

        self.assertEqual(exit_code, 0)
        _assert_completed_code_result(self, final)
        self.assertIn("permissions_loaded", event_types)
        self.assertIn("permission_rule_evaluated", event_types)
        self.assertNotIn("approval_requested", event_types)
        self.assertEqual(permissions["count"], 9)
        self.assertIn("<cli --allowed-tools>", permissions["sources"])
        self.assertIn("<cli --permission-mode acceptEdits>", permissions["sources"])
        self.assertIn("<cli --permission-mode acceptEdits>", permissions["trusted_allow_sources"])
        self.assertTrue(
            any(
                event["tool"] == "NotebookEdit"
                and event["effect"] == "allow"
                and event["rule"] == "NotebookEdit"
                and event["source"] == "<cli --permission-mode acceptEdits>"
                and event["subjects"] == ["analysis.ipynb"]
                for event in permission_evaluations
            )
        )
        _assert_clean_notebook_commit(self, commit_state, expected_subject="Fix notebook analysis formula")

    def test_v1_cli_stream_json_disallowed_tools_override_accept_edits(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-v1-cli-deny-edit-smoke-") as base:
            root = Path(base)
            init_broken_calculator_repo(root)
            client = DogfoodClient(disallowed_edit_responses())
            exit_code, records = _run_stream_json_cli(
                client,
                [
                    "--output-format",
                    "stream-json",
                    "--permission-mode",
                    "acceptEdits",
                    "--disallowed-tools",
                    "Edit",
                    "--cwd",
                    str(root),
                    "--max-iterations",
                    "2",
                    "Try to edit calc.py even though this run denies edits.",
                ],
            )
            event_records = [record for record in records if record["type"] == "event"]
            event_types = [record["event"]["type"] for record in event_records]
            permission_evaluations = [
                record["event"]
                for record in event_records
                if record["event"]["type"] == "permission_rule_evaluated"
            ]
            permissions = next(record["event"] for record in event_records if record["event"]["type"] == "permissions_loaded")
            final = records[-1]
            state = _calculator_commit_state(root)

        self.assertEqual(exit_code, 1)
        self.assertEqual(final["type"], "result")
        self.assertEqual(final["kind"], "code")
        self.assertEqual(final["status"], "blocked")
        self.assertEqual(final["stopReason"], "blocked")
        self.assertTrue(final["success"])
        self.assertIn("1 approval request(s) were denied.", final["completionBlockers"])
        self.assertIn("Denied by project permission rule Edit", final["latestCompletionDeniedApprovals"][0])
        self.assertIn("permissions_loaded", event_types)
        self.assertIn("permission_rule_evaluated", event_types)
        self.assertNotIn("approval_requested", event_types)
        self.assertEqual(permissions["count"], 3)
        self.assertIn("<cli --permission-mode acceptEdits>", permissions["sources"])
        self.assertIn("<cli --disallowed-tools>", permissions["sources"])
        self.assertTrue(
            any(
                event["tool"] == "Edit"
                and event["effect"] == "deny"
                and event["rule"] == "Edit"
                and event["source"] == "<cli --disallowed-tools>"
                and event["subjects"] == ["calc.py"]
                for event in permission_evaluations
            )
        )
        self.assertEqual(state[0], "")
        self.assertEqual(state[1], "initial broken calculator")
        self.assertIn("return left - right", state[2])

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

    def test_v1_cli_json_reports_pending_user_input_for_machine_callers(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-v1-cli-user-input-smoke-") as base:
            root = Path(base)
            init_broken_calculator_repo(root)
            client = DogfoodClient(pending_user_input_responses())
            exit_code, payload = _run_json_cli(
                client,
                [
                    "--output-format",
                    "json",
                    "--cwd",
                    str(root),
                    "--max-iterations",
                    "2",
                    "Clarify the expected calculator behavior before changing files.",
                ],
            )
            events = _session_events(root, payload["runId"])
            event_types = [event["type"] for event in events]
            git_status = _git_status(root)
            head_subject = _git_head_subject(root)
            calc_text = _calc_text(root)

        self.assertEqual(exit_code, 0)
        self.assertEqual(payload["kind"], "code")
        self.assertEqual(payload["status"], "completed")
        self.assertEqual(payload["stopReason"], "user_input")
        self.assertEqual(payload["stop_reason"], "user_input")
        self.assertTrue(payload["success"])
        self.assertTrue(payload["pendingUserInput"])
        self.assertTrue(payload["pending_user_input"])
        self.assertEqual(
            payload["userInputRequests"],
            [
                {
                    "question": "Should calc.add use addition or subtraction?",
                    "options": ["addition", "subtraction"],
                    "answer": None,
                    "cancelled": True,
                    "message": "User input is unavailable in this run. Return the question to the user without guessing.",
                }
            ],
        )
        self.assertEqual(payload["user_input_requests"], payload["userInputRequests"])
        self.assertIn("user_input_requested", event_types)
        self.assertIn("user_input_answered", event_types)
        self.assertEqual(git_status, "")
        self.assertEqual(head_subject, "initial broken calculator")
        self.assertIn("return left - right", calc_text)


if __name__ == "__main__":
    unittest.main()
