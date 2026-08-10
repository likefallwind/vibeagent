from __future__ import annotations

import io
import json
import os
import subprocess
import tempfile
import unittest
import uuid
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import patch

from tests.test_v1_dogfood import (
    DogfoodClient,
    background_process_dogfood_responses,
    checkpoint_safety_dogfood_responses,
    claude_compat_dogfood_responses,
    claude_hook_dogfood_responses,
    claude_mcp_dogfood_responses,
    claude_notebook_dogfood_responses,
    code_delegated_dogfood_responses,
    delegated_dogfood_responses,
    init_broken_calculator_repo,
    init_hooked_calculator_repo,
    init_mcp_calculator_repo,
    init_broken_notebook_repo,
    interrupted_dogfood_responses,
    plan_mode_dogfood_responses,
    profiled_delegated_dogfood_responses,
    resumed_dogfood_responses,
    session_handoff_dogfood_responses,
    skill_dogfood_responses,
    v1_dogfood_responses,
    web_fetch_dogfood_responses,
)
from vibeagent.cli import main
from vibeagent.session_commands import get_session_handoff_report
from vibeagent.session_handoff_details import extract_session_handoff_details
from vibeagent.types import ModelUsage, WebFetchObservation


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
    def test_v1_cli_dont_ask_completes_preapproved_repair_without_prompting(self) -> None:
        allowed_tools = [
            "project_overview",
            "read_file",
            "run_command",
            "update_plan",
            "write_file",
            "git_stage",
            "git_commit",
            "run_suggested_checks",
            "run_session_verification",
        ]
        with tempfile.TemporaryDirectory(prefix="vibeagent-v1-dont-ask-smoke-") as base:
            root = Path(base)
            init_broken_calculator_repo(root)
            client = DogfoodClient(v1_dogfood_responses())
            args = [
                "-p",
                "--output-format",
                "json",
                "--permission-mode",
                "dontAsk",
            ]
            for tool in allowed_tools:
                args.extend(["--allowed-tools", tool])
            args.extend(
                [
                    "--cwd",
                    str(root),
                    "--max-iterations",
                    "14",
                    "Fix the calculator test failure and commit the verified fix.",
                ]
            )
            exit_code, payload = _run_json_cli(client, args)
            events = _session_events(root, payload["runId"])
            event_types = {str(event["type"]) for event in events}
            permissions = next(event for event in events if event["type"] == "permissions_loaded")
            commit_state = _calculator_commit_state(root)

        self.assertEqual(exit_code, 0)
        _assert_completed_code_result(self, payload, num_turns=11)
        self.assertIn("dontAsk permission mode is active", _initial_prompt(client))
        self.assertNotIn("approval_requested", event_types)
        self.assertIn("permission_rule_evaluated", event_types)
        self.assertIn("<cli --allowed-tools>", permissions["trusted_allow_sources"])
        _assert_clean_calculator_commit(self, commit_state, expected_subject="Fix calculator add")

    def test_v1_cli_tools_restriction_completes_repair_without_extra_tools(self) -> None:
        requested_tools = {
            "project_overview",
            "read_file",
            "run_command",
            "update_plan",
            "write_file",
            "git_stage",
            "git_commit",
            "run_suggested_checks",
            "run_session_verification",
        }
        with tempfile.TemporaryDirectory(prefix="vibeagent-v1-tools-smoke-") as base:
            root = Path(base)
            init_broken_calculator_repo(root)
            client = DogfoodClient(v1_dogfood_responses())
            exit_code, payload = _run_json_cli(
                client,
                [
                    "-p",
                    "--output-format",
                    "json",
                    "--tools",
                    ",".join(sorted(requested_tools)),
                    "--approval",
                    "allow",
                    "--cwd",
                    str(root),
                    "--max-iterations",
                    "14",
                    "Fix the calculator test failure and commit the verified fix.",
                ],
            )
            events = _session_events(root, payload["runId"])
            restriction = next(
                event for event in events if event["type"] == "tool_restrictions_loaded"
            )
            commit_state = _calculator_commit_state(root)

        self.assertEqual(exit_code, 0)
        _assert_completed_code_result(self, payload, num_turns=11)
        for tools in client.tools:
            self.assertTrue({str(tool["name"]) for tool in tools} <= requested_tools)
        self.assertEqual(set(restriction["tools"]), requested_tools)
        _assert_clean_calculator_commit(self, commit_state, expected_subject="Fix calculator add")

    def test_v1_cli_fallback_model_completes_repair_after_primary_overload(self) -> None:
        fallback = DogfoodClient(v1_dogfood_responses())

        class PrimaryOverloadedClient:
            model = "primary"

            def __init__(self) -> None:
                self.calls = 0

            def complete(self, *args, **kwargs):
                self.calls += 1
                error = RuntimeError("primary overloaded")
                error.status = 529
                raise error

            def with_agent_profile(self, *, model, effort):
                self.assert_model = model
                if model != "backup" or effort is not None:
                    raise AssertionError("unexpected fallback configuration")
                return fallback

        primary = PrimaryOverloadedClient()
        with tempfile.TemporaryDirectory(prefix="vibeagent-v1-fallback-smoke-") as base:
            root = Path(base)
            init_broken_calculator_repo(root)
            exit_code, payload = _run_json_cli(
                primary,
                [
                    "-p",
                    "--output-format",
                    "json",
                    "--fallback-model",
                    "backup",
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
        _assert_completed_code_result(self, payload, num_turns=11)
        self.assertEqual(primary.calls, 1)
        self.assertEqual(len(fallback.messages), 11)
        self.assertEqual(payload["subtype"], "success")
        self.assertTrue(payload["modelFallback"]["activated"])
        self.assertEqual(payload["modelFallback"]["uses"], 11)
        _assert_clean_calculator_commit(self, commit_state, expected_subject="Fix calculator add")

    def test_v1_cli_budgeted_repair_verify_commit_and_report_cost(self) -> None:
        responses = v1_dogfood_responses()
        client = DogfoodClient(
            responses,
            usages=[ModelUsage(input_tokens=10, output_tokens=5, total_tokens=15)] * len(responses),
        )
        with tempfile.TemporaryDirectory(prefix="vibeagent-v1-budget-smoke-") as base:
            root = Path(base)
            init_broken_calculator_repo(root)
            with patch.dict(
                os.environ,
                {
                    "VIBEAGENT_INPUT_USD_PER_MILLION": "1",
                    "VIBEAGENT_OUTPUT_USD_PER_MILLION": "2",
                },
                clear=False,
            ):
                exit_code, payload = _run_json_cli(
                    client,
                    [
                        "-p",
                        "--output-format",
                        "json",
                        "--max-budget-usd",
                        "0.001",
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
        _assert_completed_code_result(self, payload, num_turns=11)
        self.assertEqual(payload["subtype"], "success")
        self.assertEqual(payload["totalCostUsd"], "0.000220")
        self.assertEqual(payload["budget"]["maximumUsd"], "0.001000")
        _assert_clean_calculator_commit(self, commit_state, expected_subject="Fix calculator add")

    def test_v1_cli_json_schema_repairs_then_returns_validated_output(self) -> None:
        responses = v1_dogfood_responses()[:11]
        responses.extend(
            [
                [{"type": "text", "text": '{"summary":"fixed","verified":"yes"}'}],
                [{"type": "text", "text": '{"summary":"fixed and committed","verified":true}'}],
            ]
        )
        schema = json.dumps(
            {
                "type": "object",
                "properties": {
                    "summary": {"type": "string"},
                    "verified": {"type": "boolean"},
                },
                "required": ["summary", "verified"],
                "additionalProperties": False,
            }
        )
        with tempfile.TemporaryDirectory(prefix="vibeagent-v1-structured-smoke-") as base:
            root = Path(base)
            init_broken_calculator_repo(root)
            client = DogfoodClient(responses)
            exit_code, payload = _run_json_cli(
                client,
                [
                    "-p",
                    "--output-format",
                    "json",
                    "--json-schema",
                    schema,
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
        _assert_completed_code_result(self, payload, num_turns=11)
        self.assertEqual(
            payload["structured_output"],
            {"summary": "fixed and committed", "verified": True},
        )
        self.assertEqual(payload["structured_output_attempts"], 2)
        _assert_clean_calculator_commit(self, commit_state, expected_subject="Fix calculator add")

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
        _assert_completed_code_result(self, payload, num_turns=11)
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
        _assert_completed_code_result(self, payload, num_turns=11)
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

    def test_v1_cli_json_can_use_web_fetch_before_repair_and_commit(self) -> None:
        fetched_contract = WebFetchObservation(
            kind="web_fetch",
            ok=True,
            url="https://docs.example.com/calculator-contract",
            final_url="https://docs.example.com/calculator-contract",
            status=200,
            content_type="text/html",
            title="Calculator Contract",
            text="The calc.add(left, right) function must return the arithmetic sum of both arguments.",
            text_truncated=False,
            max_text_chars=20_000,
            error=None,
            message="Fetched public document.",
        )
        with tempfile.TemporaryDirectory(prefix="vibeagent-v1-cli-webfetch-smoke-") as base:
            root = Path(base)
            init_broken_calculator_repo(root)
            client = DogfoodClient(web_fetch_dogfood_responses())
            with patch("vibeagent.runtime_action_executor.fetch_public_document", return_value=fetched_contract) as fetch_public_document:
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
                        "15",
                        "Fetch the external calculator contract, then fix and commit the verified implementation.",
                    ],
                )
            events = _session_events(root, payload["runId"])
            events_text = "\n".join(json.dumps(event, sort_keys=True) for event in events)
            next_turn_payload = str(client.messages[2][-1].content)
            commit_state = _calculator_commit_state(root)

        self.assertEqual(exit_code, 0)
        _assert_completed_code_result(self, payload)
        fetch_public_document.assert_called_once_with(
            "https://docs.example.com/calculator-contract",
            timeout_ms=10_000,
            max_text_chars=20_000,
        )
        self.assertIn('"name": "WebFetch"', events_text)
        self.assertIn("arithmetic sum", next_turn_payload)
        self.assertIn("Extract the expected behavior for calc.add.", next_turn_payload)
        _assert_clean_calculator_commit(self, commit_state, expected_subject="Fix calculator add using fetched contract")

    def test_v1_cli_json_can_load_project_skill_before_repair_and_commit(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-v1-cli-skill-smoke-") as base:
            root = Path(base)
            init_broken_calculator_repo(root)
            skill_dir = root / ".claude" / "skills" / "calculator-repair"
            skill_dir.mkdir(parents=True)
            (skill_dir / "SKILL.md").write_text(
                "---\n"
                "name: calculator-repair\n"
                "description: Repair calculator behavior safely\n"
                "---\n\n"
                "SKILL_CALCULATOR_REPAIR_INSTRUCTION: inspect calc.py and tests, make the smallest fix, run unittest, final-review before commit.\n",
                encoding="utf-8",
            )
            subprocess.run(["git", "add", ".claude/skills/calculator-repair/SKILL.md"], cwd=root, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            subprocess.run(["git", "commit", "-m", "add calculator repair skill"], cwd=root, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            client = DogfoodClient(skill_dogfood_responses())
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
                    "17",
                    "Use a relevant project skill to fix the calculator test failure and commit.",
                ],
            )
            events = _session_events(root, payload["runId"])
            events_text = "\n".join(json.dumps(event, sort_keys=True) for event in events)
            initial_prompt = _initial_prompt(client)
            after_skill_prompt = "\n".join(str(message.content) for message in client.messages[2])
            commit_state = _calculator_commit_state(root)

        self.assertEqual(exit_code, 0)
        _assert_completed_code_result(self, payload)
        self.assertIn('"name": "ToolSearch"', events_text)
        self.assertIn('"name": "Skill"', events_text)
        self.assertIn('"name": "skill"', events_text)
        self.assertIn('"name": "calculator-repair"', events_text)
        self.assertIn("Repair calculator behavior safely", events_text)
        self.assertNotIn("SKILL_CALCULATOR_REPAIR_INSTRUCTION", initial_prompt)
        self.assertIn("SKILL_CALCULATOR_REPAIR_INSTRUCTION", after_skill_prompt)
        _assert_clean_calculator_commit(self, commit_state, expected_subject="Fix calculator add with project skill")

    def test_v1_cli_json_runs_project_hooks_around_claude_edit_and_commits(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-v1-cli-hooks-smoke-") as base:
            root = Path(base)
            init_hooked_calculator_repo(root)
            client = DogfoodClient(claude_hook_dogfood_responses())
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
                    "17",
                    "Fix the calculator through the configured project hooks, verify it, and commit.",
                ],
            )
            events = _session_events(root, payload["runId"])
            events_text = "\n".join(json.dumps(event, sort_keys=True) for event in events)
            hook_log = (root / ".vibeagent" / "hook.log").read_text(encoding="utf-8")
            commit_state = _calculator_commit_state(root)

        self.assertEqual(exit_code, 0)
        _assert_completed_code_result(self, payload)
        self.assertEqual(hook_log.splitlines(), ["PreToolUse:Edit", "PostToolUse:Edit"])
        self.assertIn('"type": "hooks_loaded"', events_text)
        self.assertIn('"type": "hook_completed"', events_text)
        self.assertIn('"event": "PreToolUse"', events_text)
        self.assertIn('"event": "PostToolUse"', events_text)
        self.assertIn('"name": "Edit"', events_text)
        _assert_clean_calculator_commit(self, commit_state, expected_subject="Fix calculator add through hooks")

    def test_v1_cli_json_can_manage_background_process_before_repair_and_commit(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-v1-cli-background-smoke-") as base:
            root = Path(base)
            init_broken_calculator_repo(root)
            client = DogfoodClient(background_process_dogfood_responses())
            fixed_process_uuid = uuid.UUID("11111111-1111-2222-2222-222222222222")
            with patch("vibeagent.process_runtime.uuid.uuid4", return_value=fixed_process_uuid):
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
                        "18",
                        "Start a background readiness probe, inspect it, then fix the calculator test failure and commit.",
                    ],
                )
            events = _session_events(root, payload["runId"])
            events_text = "\n".join(json.dumps(event, sort_keys=True) for event in events)
            commit_state = _calculator_commit_state(root)

        self.assertEqual(exit_code, 0)
        _assert_completed_code_result(self, payload)
        self.assertIn('"name": "Bash"', events_text)
        self.assertIn('"name": "BashOutput"', events_text)
        self.assertIn('"name": "KillBash"', events_text)
        self.assertIn('"process_id": "111111111111"', events_text)
        self.assertIn("ready", events_text)
        _assert_clean_calculator_commit(self, commit_state, expected_subject="Fix calculator add after background probe")

    def test_v1_cli_json_can_delegate_read_only_investigation_before_repair_and_commit(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-v1-cli-delegate-smoke-") as base:
            root = Path(base)
            init_broken_calculator_repo(root)
            client = DogfoodClient(delegated_dogfood_responses())
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
                    "15",
                    "Delegate the initial investigation, then fix the calculator test failure and commit.",
                ],
            )
            events = _session_events(root, payload["runId"])
            events_text = "\n".join(json.dumps(event, sort_keys=True) for event in events)
            commit_state = _calculator_commit_state(root)

        self.assertEqual(exit_code, 0)
        _assert_completed_code_result(self, payload)
        self.assertIn('"name": "Task"', events_text)
        self.assertIn('"kind": "delegate_task"', events_text)
        self.assertIn('"type": "subagent_tool_call"', events_text)
        self.assertIn('"name": "Read"', events_text)
        self.assertIn("calc.py subtracts", events_text)
        _assert_clean_calculator_commit(self, commit_state, expected_subject="Fix calculator add after delegation")

    def test_v1_cli_json_can_delegate_with_project_agent_profile_before_repair_and_commit(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-v1-cli-profiled-delegate-smoke-") as base:
            root = Path(base)
            init_broken_calculator_repo(root)
            agent_dir = root / ".claude" / "agents"
            agent_dir.mkdir(parents=True)
            (agent_dir / "calc-reviewer.md").write_text(
                "---\n"
                "name: calc-reviewer\n"
                "description: Reviews calculator failures\n"
                "mode: explore\n"
                "tools: Read\n"
                "---\n\n"
                "PROFILED_CALC_REVIEWER_INSTRUCTION: inspect calculator code and test evidence only.\n",
                encoding="utf-8",
            )
            subprocess.run(["git", "add", ".claude/agents/calc-reviewer.md"], cwd=root, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            subprocess.run(["git", "commit", "-m", "add calc reviewer profile"], cwd=root, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            client = DogfoodClient(profiled_delegated_dogfood_responses())
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
                    "15",
                    "Delegate the initial investigation to the calc-reviewer profile, then fix and commit.",
                ],
            )
            events = _session_events(root, payload["runId"])
            events_text = "\n".join(json.dumps(event, sort_keys=True) for event in events)
            first_subagent_prompt = str(client.messages[1][0].content)
            commit_state = _calculator_commit_state(root)

        self.assertEqual(exit_code, 0)
        _assert_completed_code_result(self, payload)
        self.assertIn('"agent": "calc-reviewer"', events_text)
        self.assertIn('"name": "Task"', events_text)
        self.assertIn('"type": "subagent_tool_call"', events_text)
        self.assertIn('"name": "Read"', events_text)
        self.assertIn("Profiled review", events_text)
        self.assertIn("PROFILED_CALC_REVIEWER_INSTRUCTION", first_subagent_prompt)
        _assert_clean_calculator_commit(self, commit_state, expected_subject="Fix calculator add after profiled delegation")

    def test_v1_cli_json_can_delegate_with_dynamic_agent_before_repair_and_commit(self) -> None:
        dynamic_agents = json.dumps(
            {
                "calc-reviewer": {
                    "description": "Reviews calculator failures",
                    "prompt": "DYNAMIC_CALC_REVIEWER_INSTRUCTION: inspect calculator code and test evidence only.",
                    "mode": "explore",
                    "tools": ["Read"],
                    "maxTurns": 2,
                }
            }
        )
        with tempfile.TemporaryDirectory(prefix="vibeagent-v1-cli-dynamic-agent-smoke-") as base:
            root = Path(base)
            init_broken_calculator_repo(root)
            client = DogfoodClient(profiled_delegated_dogfood_responses())
            exit_code, payload = _run_json_cli(
                client,
                [
                    "--output-format",
                    "json",
                    "--approval",
                    "allow",
                    "--agents",
                    dynamic_agents,
                    "--cwd",
                    str(root),
                    "--max-iterations",
                    "15",
                    "Delegate the initial investigation to the dynamic calc-reviewer, then fix and commit.",
                ],
            )
            events = _session_events(root, payload["runId"])
            events_text = "\n".join(json.dumps(event, sort_keys=True) for event in events)
            first_subagent_prompt = str(client.messages[1][0].content)
            commit_state = _calculator_commit_state(root)
            agent_file_exists = root.joinpath(".claude", "agents", "calc-reviewer.md").exists()

        self.assertEqual(exit_code, 0)
        _assert_completed_code_result(self, payload)
        self.assertIn('"agent": "calc-reviewer"', events_text)
        self.assertIn('"type": "dynamic_agents_loaded"', events_text)
        self.assertIn('"names": ["calc-reviewer"]', events_text)
        self.assertNotIn("DYNAMIC_CALC_REVIEWER_INSTRUCTION", events_text)
        self.assertIn('"profile_skills": []', events_text)
        self.assertIn('"name": "Read"', events_text)
        self.assertIn("Profiled review", events_text)
        self.assertIn("DYNAMIC_CALC_REVIEWER_INSTRUCTION", first_subagent_prompt)
        self.assertFalse(agent_file_exists)
        _assert_clean_calculator_commit(self, commit_state, expected_subject="Fix calculator add after profiled delegation")

    def test_v1_cli_json_can_delegate_code_subagent_repair_and_commit(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-v1-cli-code-delegate-smoke-") as base:
            root = Path(base)
            init_broken_calculator_repo(root)
            client = DogfoodClient(code_delegated_dogfood_responses())
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
                    "9",
                    "Delegate a code subagent to fix the calculator test failure and commit.",
                ],
            )
            events = _session_events(root, payload["runId"])
            events_text = "\n".join(json.dumps(event, sort_keys=True) for event in events)
            commit_state = _calculator_commit_state(root)

        self.assertEqual(exit_code, 0)
        _assert_completed_code_result(self, payload)
        self.assertIn('"name": "Task"', events_text)
        self.assertIn('"mode": "code"', events_text)
        self.assertIn('"type": "subagent_tool_call"', events_text)
        self.assertIn('"name": "Edit"', events_text)
        self.assertIn('"name": "git_commit"', events_text)
        self.assertIn('"name": "run_suggested_checks"', events_text)
        self.assertIn('"name": "run_session_verification"', events_text)
        self.assertIn("Code subagent fixed calc.py", events_text)
        _assert_clean_calculator_commit(self, commit_state, expected_subject="Fix calculator add from code subagent")

    def test_v1_cli_json_can_create_and_check_checkpoint_before_commit(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-v1-cli-checkpoint-smoke-") as base:
            root = Path(base)
            init_broken_calculator_repo(root)
            client = DogfoodClient(checkpoint_safety_dogfood_responses())
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
                    "18",
                    "Create a rollback checkpoint, fix the calculator test failure, verify checkpoint safety, and commit.",
                ],
            )
            events = _session_events(root, payload["runId"])
            events_text = "\n".join(json.dumps(event, sort_keys=True) for event in events)
            commit_state = _calculator_commit_state(root)

        self.assertEqual(exit_code, 0)
        _assert_completed_code_result(self, payload)
        self.assertIn('"name": "checkpoint_create"', events_text)
        self.assertIn('"name": "checkpoint_list"', events_text)
        self.assertIn('"name": "checkpoint_status"', events_text)
        self.assertIn('"name": "check_checkpoint_restore"', events_text)
        self.assertIn("before calculator edit", events_text)
        self.assertIn('"can_restore": true', events_text)
        _assert_clean_calculator_commit(self, commit_state, expected_subject="Fix calculator add with checkpoint safety")

    def test_v1_cli_json_generates_ready_session_handoff_after_verified_commit(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-v1-cli-handoff-smoke-") as base:
            root = Path(base)
            init_broken_calculator_repo(root)
            client = DogfoodClient(session_handoff_dogfood_responses())
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
                    "18",
                    "Fix the calculator test failure, commit it, and generate a session handoff.",
                ],
            )
            events = _session_events(root, payload["runId"])
            events_text = "\n".join(json.dumps(event, sort_keys=True) for event in events)
            handoff_report = get_session_handoff_report(
                root,
                str(payload["runId"]),
                max_files=10,
                max_commands=10,
                max_checks=20,
                max_text=800,
            )
            handoff = extract_session_handoff_details(handoff_report)
            commit_state = _calculator_commit_state(root)

        self.assertEqual(exit_code, 0)
        _assert_completed_code_result(self, payload)
        self.assertIn('"name": "session_handoff"', events_text)
        self.assertIn("Session handoff:", events_text)
        self.assertIn("python -m unittest discover -s tests", events_text)
        self.assertTrue(handoff.ready)
        self.assertEqual(handoff.status, "ready")
        self.assertEqual(handoff.blockers, [])
        self.assertEqual(handoff.pending_count, 0)
        self.assertEqual(handoff.failed_count, 0)
        self.assertGreaterEqual(handoff.verified_count, 1)
        _assert_clean_calculator_commit(self, commit_state, expected_subject="Fix calculator add before handoff")

    def test_v1_cli_json_plan_mode_inspects_without_mutating(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-v1-cli-plan-smoke-") as base:
            root = Path(base)
            init_broken_calculator_repo(root)
            client = DogfoodClient(plan_mode_dogfood_responses())
            exit_code, payload = _run_json_cli(
                client,
                [
                    "--output-format",
                    "json",
                    "--approval",
                    "plan",
                    "--cwd",
                    str(root),
                    "--max-iterations",
                    "5",
                    "Plan the calculator repair without changing files or running commands.",
                ],
            )
            events = _session_events(root, payload["runId"])
            events_text = "\n".join(json.dumps(event, sort_keys=True) for event in events)
            initial_prompt = _initial_prompt(client)
            exposed_names = {str(tool["name"]) for tools in client.tools for tool in tools}
            commit_state = _calculator_commit_state(root)

        self.assertEqual(exit_code, 0)
        _assert_completed_code_result(self, payload)
        self.assertIn("Plan mode is active", initial_prompt)
        self.assertIn('"name": "project_overview"', events_text)
        self.assertIn('"name": "read_file"', events_text)
        self.assertIn('"name": "update_plan"', events_text)
        self.assertTrue({"write_file", "edit_file", "run_command", "git_commit"}.isdisjoint(exposed_names))
        self.assertIn("ExitPlanMode", exposed_names)
        self.assertIn("Plan recorded", str(payload["message"]))
        git_status, head_subject, calc_text = commit_state
        self.assertEqual(git_status, "")
        self.assertEqual(head_subject, "initial broken calculator")
        self.assertIn("return left - right", calc_text)

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
        _assert_completed_code_result(self, payload, num_turns=11)
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
        self.assertEqual(resumed_payload["runId"], interrupted_payload["runId"])
        self.assertEqual(resumed_payload["priorContext"], {
            "loaded": True,
            "source": "resume",
            "runId": interrupted_payload["runId"],
        })
        self.assertNotIn("Previous session context:", initial_resumed_prompt)
        self.assertIn("Fix the calculator test failure", initial_resumed_prompt)
        self.assertIn("python -B -m unittest discover -s tests", initial_resumed_prompt)
        self.assertIn("AssertionError: -1 != 5", initial_resumed_prompt)
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
        self.assertEqual(permissions["count"], 11)
        self.assertIn("<cli --allowed-tools>", permissions["sources"])
        self.assertIn("<cli --permission-mode acceptEdits>", permissions["sources"])
        self.assertIn("<cli --permission-mode acceptEdits>", permissions["trusted_allow_sources"])
        self.assertTrue(
            any(
                event["tool"] == "Edit"
                and event["effect"] == "allow"
                and event["rule"] in {"Write", "Edit"}
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
        self.assertEqual(permissions["count"], 11)
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
            restrictions = next(
                record["event"]
                for record in event_records
                if record["event"]["type"] == "tool_restrictions_loaded"
            )
            final = records[-1]
            state = _calculator_commit_state(root)

        self.assertEqual(exit_code, 1)
        self.assertEqual(final["type"], "result")
        self.assertEqual(final["kind"], "code")
        self.assertEqual(final["status"], "blocked")
        self.assertEqual(final["stopReason"], "blocked")
        self.assertTrue(final["success"])
        self.assertIn("1 tool error(s) occurred.", final["completionBlockers"])
        self.assertIn("active tool restrictions", final["latestCompletionToolErrors"][0])
        self.assertIn("permissions_loaded", event_types)
        self.assertIn("tool_restrictions_loaded", event_types)
        self.assertNotIn("approval_requested", event_types)
        self.assertEqual(permissions["count"], 5)
        self.assertIn("<cli --permission-mode acceptEdits>", permissions["sources"])
        self.assertIn("<cli --disallowed-tools>", permissions["sources"])
        self.assertFalse(any(event["tool"] == "Edit" for event in permission_evaluations))
        self.assertIn("Edit", restrictions["disallowed_tools"])
        self.assertIn("write_file", restrictions["disallowed_tools"])
        self.assertNotIn("Edit", {str(tool["name"]) for tool in client.tools[0]})
        self.assertNotIn("write_file", {str(tool["name"]) for tool in client.tools[0]})
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
