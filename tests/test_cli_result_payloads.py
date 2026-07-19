from __future__ import annotations

import unittest
from pathlib import Path

from vibeagent import MACHINE_OUTPUT_SCHEMA_VERSION, __version__
from vibeagent.agent_result import AgentResult
from vibeagent.cli_context import OneShotPriorContext
from vibeagent.cli_result_payloads import (
    CODE_RESULT_SNAKE_CASE_ALIAS_KEYS,
    build_chat_result_payload,
    build_code_result_payload,
    code_result_exit_code,
    code_result_snake_case_aliases,
    code_result_stop_reason,
    error_result_payload,
)
from vibeagent.observation_common_types import UserInputObservation


def _result(root: Path, run_id: str = "stream-run") -> AgentResult:
    return AgentResult(
        success=True,
        message="done",
        run_dir=root,
        run_id=run_id,
        iterations=1,
        observations=[],
        steps=[],
    )


class CodeResultPayloadTests(unittest.TestCase):
    def test_error_result_payload_includes_stop_reason_aliases(self) -> None:
        failed = error_result_payload("No task provided.")
        interrupted = error_result_payload("Interrupted.", kind="interrupted", status="interrupted")

        self.assertEqual(failed["stopReason"], "failed")
        self.assertEqual(failed["stop_reason"], "failed")
        self.assertEqual(interrupted["stopReason"], "interrupted")
        self.assertEqual(interrupted["stop_reason"], "interrupted")

    def test_error_result_payload_includes_exit_code_aliases_when_known(self) -> None:
        payload = error_result_payload("Invalid arguments.", exit_code=2)

        self.assertEqual(payload["exitCode"], 2)
        self.assertEqual(payload["exit_code"], 2)

    def test_chat_result_payload_includes_runtime_version_and_result_alias(self) -> None:
        payload = build_chat_result_payload("hello")

        self.assertEqual(
            payload,
            {
                "kind": "chat",
                "schemaVersion": MACHINE_OUTPUT_SCHEMA_VERSION,
                "version": __version__,
                "success": True,
                "status": "completed",
                "exitCode": 0,
                "exit_code": 0,
                "stopReason": "completed",
                "stop_reason": "completed",
                "message": "hello",
                "result": "hello",
            },
        )

    def test_code_result_snake_case_aliases_cover_machine_readable_fields(self) -> None:
        payload = {
            key: f"value-{index}"
            for index, key in enumerate(CODE_RESULT_SNAKE_CASE_ALIAS_KEYS)
        }

        aliases = code_result_snake_case_aliases(payload)

        self.assertEqual(
            aliases,
            {
                alias: payload[key]
                for key, alias in CODE_RESULT_SNAKE_CASE_ALIAS_KEYS.items()
            },
        )

    def test_code_result_snake_case_aliases_do_not_overwrite_existing_aliases(self) -> None:
        aliases = code_result_snake_case_aliases(
            {
                "completionReady": True,
                "completion_ready": "existing",
            }
        )

        self.assertEqual(aliases, {})

    def test_result_payload_includes_empty_user_input_requests_by_default(self) -> None:
        root = Path("/tmp/vibeagent-result")
        payload = build_code_result_payload(_result(root), prior_context=OneShotPriorContext(source="none"))

        self.assertEqual(payload["schemaVersion"], MACHINE_OUTPUT_SCHEMA_VERSION)
        self.assertEqual(payload["version"], __version__)
        self.assertEqual(payload["exitCode"], 0)
        self.assertEqual(payload["exit_code"], 0)
        self.assertFalse(payload["pendingUserInput"])
        self.assertFalse(payload["pending_user_input"])
        self.assertEqual(payload["userInputRequests"], [])
        self.assertEqual(payload["user_input_requests"], [])

    def test_result_payload_marks_cancelled_user_input_as_pending(self) -> None:
        root = Path("/tmp/vibeagent-result")
        result = AgentResult(
            success=True,
            message="Which database should I use?",
            run_dir=root,
            run_id="run-1",
            iterations=1,
            observations=[
                UserInputObservation(
                    kind="ask_user",
                    question="Which database?",
                    options=["SQLite", "PostgreSQL"],
                    answer=None,
                    cancelled=True,
                    message="User input is unavailable in this run. Return the question to the user without guessing.",
                )
            ],
            steps=[],
        )

        payload = build_code_result_payload(result, prior_context=OneShotPriorContext(source="none"))

        self.assertTrue(payload["pendingUserInput"])
        self.assertTrue(payload["pending_user_input"])
        self.assertEqual(payload["stopReason"], "user_input")
        self.assertEqual(payload["stop_reason"], "user_input")
        self.assertEqual(payload["exitCode"], 0)
        self.assertEqual(payload["exit_code"], 0)
        self.assertEqual(
            payload["userInputRequests"],
            [
                {
                    "question": "Which database?",
                    "options": ["SQLite", "PostgreSQL"],
                    "answer": None,
                    "cancelled": True,
                    "message": "User input is unavailable in this run. Return the question to the user without guessing.",
                }
            ],
        )
        self.assertEqual(payload["user_input_requests"], payload["userInputRequests"])

    def test_result_payload_keeps_answered_user_input_without_pending_flag(self) -> None:
        root = Path("/tmp/vibeagent-result")
        result = AgentResult(
            success=True,
            message="Using PostgreSQL.",
            run_dir=root,
            run_id="run-1",
            iterations=1,
            observations=[
                UserInputObservation(
                    kind="ask_user",
                    question="Which database?",
                    options=["SQLite", "PostgreSQL"],
                    answer="PostgreSQL",
                    cancelled=False,
                    message="User answered: PostgreSQL",
                )
            ],
            steps=[],
        )

        payload = build_code_result_payload(result, prior_context=OneShotPriorContext(source="none"))

        self.assertFalse(payload["pendingUserInput"])
        self.assertEqual(payload["stopReason"], "completed")
        self.assertEqual(payload["userInputRequests"][0]["answer"], "PostgreSQL")
        self.assertFalse(payload["userInputRequests"][0]["cancelled"])

    def test_stop_reason_reflects_completion_state(self) -> None:
        root = Path("/tmp/vibeagent-result")

        self.assertEqual(code_result_stop_reason(_result(root)), "completed")
        self.assertEqual(
            code_result_stop_reason(
                AgentResult(
                    success=True,
                    message="Need input",
                    run_dir=root,
                    run_id="run-1",
                    iterations=1,
                    observations=[
                        UserInputObservation(
                            kind="ask_user",
                            question="Which database?",
                            options=[],
                            answer=None,
                            cancelled=True,
                            message="User input is unavailable.",
                        )
                    ],
                    steps=[],
                )
            ),
            "user_input",
        )
        self.assertEqual(
            code_result_stop_reason(
                AgentResult(
                    success=True,
                    message="blocked",
                    run_dir=root,
                    run_id="run-1",
                    iterations=1,
                    observations=[],
                    steps=[],
                    completion_ready=False,
                )
            ),
            "blocked",
        )
        self.assertEqual(
            code_result_stop_reason(
                AgentResult(
                    success=False,
                    message="failed",
                    run_dir=root,
                    run_id="run-1",
                    iterations=1,
                    observations=[],
                    steps=[],
                )
            ),
            "failed",
        )

    def test_code_result_exit_code_matches_cli_completion_rule(self) -> None:
        root = Path("/tmp/vibeagent-result")

        self.assertEqual(code_result_exit_code(_result(root)), 0)
        self.assertEqual(
            code_result_exit_code(
                AgentResult(
                    success=True,
                    message="blocked",
                    run_dir=root,
                    run_id="run-1",
                    iterations=1,
                    observations=[],
                    steps=[],
                    completion_ready=False,
                )
            ),
            1,
        )
        self.assertEqual(
            code_result_exit_code(
                AgentResult(
                    success=False,
                    message="failed",
                    run_dir=root,
                    run_id="run-1",
                    iterations=1,
                    observations=[],
                    steps=[],
                )
            ),
            1,
        )


if __name__ == "__main__":
    unittest.main()
