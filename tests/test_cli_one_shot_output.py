from __future__ import annotations

from contextlib import redirect_stderr
from dataclasses import replace
from decimal import Decimal
import io
import unittest
from pathlib import Path
from unittest.mock import patch

from vibeagent.agent_result import AgentResult
from vibeagent.cli_context import OneShotPriorContext
from vibeagent.cli_one_shot_output import (
    apply_model_budget_result,
    apply_structured_output_result,
    build_one_shot_chat_payload,
    build_one_shot_code_payload,
    build_one_shot_error_payload,
    emit_one_shot_error,
    emit_one_shot_chat_payload,
    emit_one_shot_code_payload,
    one_shot_code_exit_code,
)
from vibeagent.config import CostRates
from vibeagent.model_budget import ModelCostBudget
from vibeagent.structured_output import StructuredOutputResult


def _result(root: Path, run_id: str = "run-1") -> AgentResult:
    return AgentResult(
        success=True,
        message="done",
        run_dir=root,
        run_id=run_id,
        iterations=2,
        observations=[],
        steps=[],
    )


class CliOneShotOutputTests(unittest.TestCase):
    def test_error_payload_adds_duration_and_exit_code_for_machine_output(self) -> None:
        payload = build_one_shot_error_payload(
            "Invalid input.",
            machine_output=True,
            elapsed_ms=42,
            exit_code=2,
        )

        self.assertEqual(payload["kind"], "error")
        self.assertEqual(payload["error"], "Invalid input.")
        self.assertEqual(payload["exitCode"], 2)
        self.assertEqual(payload["exit_code"], 2)
        self.assertEqual(payload["durationMs"], 42)
        self.assertEqual(payload["duration_ms"], 42)

    def test_error_payload_omits_machine_only_fields_for_text_output(self) -> None:
        payload = build_one_shot_error_payload(
            "No task provided.",
            machine_output=False,
            elapsed_ms=42,
        )

        self.assertNotIn("exitCode", payload)
        self.assertNotIn("exit_code", payload)
        self.assertNotIn("durationMs", payload)
        self.assertNotIn("duration_ms", payload)

    def test_emit_error_uses_stream_when_available(self) -> None:
        emitted: list[dict[str, object]] = []

        class Stream:
            def result(self, value):
                emitted.append(value)

        exit_code = emit_one_shot_error(
            "Interrupted.",
            stream=Stream(),
            output_json=False,
            machine_output=True,
            elapsed_ms=99,
            kind="interrupted",
            status="interrupted",
            exit_code=130,
            print_output_func=lambda value, output_json: self.fail("printed instead of streamed"),
            print_error_result_func=lambda *args, **kwargs: self.fail("printed error instead of streamed"),
        )

        self.assertEqual(exit_code, 130)
        self.assertEqual(emitted[0]["kind"], "interrupted")
        self.assertEqual(emitted[0]["status"], "interrupted")
        self.assertEqual(emitted[0]["exitCode"], 130)
        self.assertEqual(emitted[0]["durationMs"], 99)

    def test_emit_error_prints_json_payload(self) -> None:
        calls: list[tuple[dict[str, object], bool]] = []

        exit_code = emit_one_shot_error(
            "Invalid input.",
            stream=None,
            output_json=True,
            machine_output=True,
            elapsed_ms=42,
            exit_code=2,
            print_output_func=lambda value, output_json: calls.append((value, output_json)),
            print_error_result_func=lambda *args, **kwargs: self.fail("printed text error instead of json"),
        )

        self.assertEqual(exit_code, 2)
        self.assertEqual(calls[0][1], True)
        self.assertEqual(calls[0][0]["error"], "Invalid input.")
        self.assertEqual(calls[0][0]["exitCode"], 2)

    def test_emit_error_prints_text_error_without_machine_fields(self) -> None:
        calls: list[tuple[tuple[object, ...], dict[str, object]]] = []

        exit_code = emit_one_shot_error(
            "No task provided.",
            stream=None,
            output_json=False,
            machine_output=False,
            elapsed_ms=42,
            print_output_func=lambda value, output_json: self.fail("printed payload instead of text error"),
            print_error_result_func=lambda *args, **kwargs: calls.append((args, kwargs)) or 1,
        )

        self.assertEqual(exit_code, 1)
        self.assertEqual(calls, [(("No task provided.", False), {"exit_code": 1})])

    def test_chat_payload_adds_turn_count_and_duration_for_machine_output(self) -> None:
        payload = build_one_shot_chat_payload("hello", machine_output=True, elapsed_ms=7)

        self.assertEqual(payload["kind"], "chat")
        self.assertEqual(payload["message"], "hello")
        self.assertEqual(payload["numTurns"], 1)
        self.assertEqual(payload["num_turns"], 1)
        self.assertEqual(payload["durationMs"], 7)
        self.assertEqual(payload["duration_ms"], 7)

    def test_chat_payload_keeps_base_result_for_text_output(self) -> None:
        payload = build_one_shot_chat_payload("hello", machine_output=False, elapsed_ms=7)

        self.assertEqual(payload["kind"], "chat")
        self.assertEqual(payload["message"], "hello")
        self.assertNotIn("numTurns", payload)
        self.assertNotIn("durationMs", payload)

    def test_emit_chat_payload_uses_stream_when_available(self) -> None:
        payload = {"kind": "chat", "message": "hello"}
        emitted: list[dict[str, object]] = []

        class Stream:
            def result(self, value):
                emitted.append(value)

        emit_one_shot_chat_payload(
            payload,
            stream=Stream(),
            output_json=False,
            print_output_func=lambda value, output_json: self.fail("printed instead of streamed"),
        )

        self.assertEqual(emitted, [payload])

    def test_emit_chat_payload_prints_without_stream(self) -> None:
        calls: list[tuple[dict[str, object], bool]] = []
        payload = {"kind": "chat", "message": "hello"}

        emit_one_shot_chat_payload(
            payload,
            stream=None,
            output_json=True,
            print_output_func=lambda value, output_json: calls.append((value, output_json)),
        )

        self.assertEqual(calls, [(payload, True)])

    def test_code_payload_adds_duration_usage_and_cost_for_machine_output(self) -> None:
        root = Path("/tmp/vibeagent-one-shot-output")
        usage = {"exists": True, "usage": {"sessions": 1}}
        cost = {"estimate": {"available": True, "estimatedCostUsd": "0.000001"}}

        with (
            patch("vibeagent.cli_one_shot_output.build_run_usage_report", return_value=usage) as build_usage,
            patch("vibeagent.cli_one_shot_output.resolve_cost_rates", return_value=({"input": 1.0}, [])) as resolve_rates,
            patch("vibeagent.cli_one_shot_output.build_run_cost_report", return_value=cost) as build_cost,
        ):
            payload = build_one_shot_code_payload(
                _result(root),
                OneShotPriorContext(source="none"),
                machine_output=True,
                elapsed_ms=123,
                project_root=root,
                provider_env={"VIBEAGENT_PROVIDER": "minimax"},
            )

        self.assertEqual(payload["kind"], "code")
        self.assertEqual(payload["message"], "done")
        self.assertEqual(payload["durationMs"], 123)
        self.assertEqual(payload["duration_ms"], 123)
        self.assertIs(payload["usage"], usage)
        self.assertIs(payload["cost"], cost)
        build_usage.assert_called_once_with(root, "run-1")
        resolve_rates.assert_called_once_with({"VIBEAGENT_PROVIDER": "minimax"})
        build_cost.assert_called_once_with(root, "run-1", {"input": 1.0}, [])

    def test_code_payload_omits_usage_and_cost_for_text_output(self) -> None:
        root = Path("/tmp/vibeagent-one-shot-output")

        with (
            patch("vibeagent.cli_one_shot_output.build_run_usage_report") as build_usage,
            patch("vibeagent.cli_one_shot_output.resolve_cost_rates") as resolve_rates,
            patch("vibeagent.cli_one_shot_output.build_run_cost_report") as build_cost,
        ):
            payload = build_one_shot_code_payload(
                _result(root),
                OneShotPriorContext(source="none"),
                machine_output=False,
                elapsed_ms=123,
                project_root=root,
                provider_env={},
            )

        self.assertEqual(payload["kind"], "code")
        self.assertEqual(payload["message"], "done")
        self.assertNotIn("durationMs", payload)
        self.assertNotIn("usage", payload)
        self.assertNotIn("cost", payload)
        build_usage.assert_not_called()
        resolve_rates.assert_not_called()
        build_cost.assert_not_called()

    def test_emit_code_payload_uses_stream_when_available(self) -> None:
        root = Path("/tmp/vibeagent-one-shot-output")
        result = _result(root)
        payload = {"kind": "code", "message": "done"}
        emitted: list[dict[str, object]] = []

        class Stream:
            def result(self, value):
                emitted.append(value)

        emit_one_shot_code_payload(
            result,
            payload,
            stream=Stream(),
            output_json=False,
            print_mode=False,
            print_output_func=lambda value, output_json: self.fail("printed instead of streamed"),
            print_agent_result_func=lambda value: self.fail("printed agent result instead of streamed"),
        )

        self.assertEqual(emitted, [payload])

    def test_emit_code_payload_prints_json_payload(self) -> None:
        root = Path("/tmp/vibeagent-one-shot-output")
        result = _result(root)
        payload = {"kind": "code", "message": "done"}
        calls: list[tuple[dict[str, object], bool]] = []

        emit_one_shot_code_payload(
            result,
            payload,
            stream=None,
            output_json=True,
            print_mode=False,
            print_output_func=lambda value, output_json: calls.append((value, output_json)),
            print_agent_result_func=lambda value: self.fail("printed text result instead of json"),
        )

        self.assertEqual(calls, [(payload, True)])

    def test_emit_code_payload_print_mode_uses_message_only(self) -> None:
        root = Path("/tmp/vibeagent-one-shot-output")
        result = replace(
            _result(root),
            hook_system_messages=["Background lint finished."],
            display_message="displayed done",
        )
        payload = {"kind": "code", "message": "done", "extra": True}
        calls: list[tuple[dict[str, object], bool]] = []
        stderr = io.StringIO()

        with redirect_stderr(stderr):
            emit_one_shot_code_payload(
                result,
                payload,
                stream=None,
                output_json=False,
                print_mode=True,
                print_output_func=lambda value, output_json: calls.append((value, output_json)),
                print_agent_result_func=lambda value: self.fail("printed full agent result in print mode"),
            )

        self.assertEqual(calls, [({"message": "displayed done"}, False)])
        self.assertEqual(stderr.getvalue(), "Hook message: Background lint finished.\n")

    def test_structured_output_success_adds_aliases_and_prints_json_value(self) -> None:
        root = Path("/tmp/vibeagent-one-shot-output")
        result = _result(root)
        payload = {"kind": "code", "message": "done", "success": True}
        calls: list[tuple[dict[str, object], bool]] = []
        apply_structured_output_result(
            payload,
            StructuredOutputResult(value={"count": 2}, error=None, attempts=2),
        )

        emit_one_shot_code_payload(
            result,
            payload,
            stream=None,
            output_json=False,
            print_mode=True,
            print_output_func=lambda value, output_json: calls.append((value, output_json)),
        )

        self.assertEqual(payload["structuredOutput"], {"count": 2})
        self.assertEqual(payload["structured_output"], {"count": 2})
        self.assertEqual(payload["structuredOutputAttempts"], 2)
        self.assertEqual(payload["subtype"], "success")
        self.assertEqual(calls, [({"message": '{"count": 2}'}, False)])

    def test_structured_output_failure_overrides_machine_status_and_exit_code(self) -> None:
        root = Path("/tmp/vibeagent-one-shot-output")
        result = _result(root)
        payload = {"kind": "code", "message": "done", "success": True}
        structured = StructuredOutputResult(value=None, error="schema mismatch", attempts=3)

        apply_structured_output_result(payload, structured)

        self.assertFalse(payload["success"])
        self.assertEqual(payload["status"], "failed")
        self.assertEqual(payload["stopReason"], "error_max_structured_output_retries")
        self.assertEqual(payload["subtype"], "error_max_structured_output_retries")
        self.assertEqual(payload["structured_output_error"], "schema mismatch")
        self.assertEqual(one_shot_code_exit_code(result, structured), 1)

    def test_healthy_budget_does_not_mark_an_unrelated_agent_failure_successful(self) -> None:
        payload = {"kind": "code", "message": "provider failed", "success": False}
        budget = ModelCostBudget(
            Decimal("1"),
            CostRates(
                input_usd_per_million=Decimal("1"),
                output_usd_per_million=Decimal("2"),
            ),
        )

        apply_model_budget_result(payload, budget)

        self.assertFalse(payload["success"])
        self.assertNotIn("subtype", payload)

    def test_emit_code_payload_prints_agent_result_for_text_output(self) -> None:
        root = Path("/tmp/vibeagent-one-shot-output")
        result = _result(root)
        payload = {"kind": "code", "message": "done"}
        calls: list[AgentResult] = []

        emit_one_shot_code_payload(
            result,
            payload,
            stream=None,
            output_json=False,
            print_mode=False,
            print_output_func=lambda value, output_json: self.fail("printed payload instead of agent result"),
            print_agent_result_func=lambda value: calls.append(value),
        )

        self.assertEqual(calls, [result])

    def test_one_shot_code_exit_code_requires_success_and_completion_ready(self) -> None:
        root = Path("/tmp/vibeagent-one-shot-output")
        self.assertEqual(one_shot_code_exit_code(_result(root)), 0)
        self.assertEqual(one_shot_code_exit_code(AgentResult(False, "failed", root, "run-1", 1, [], [])), 1)
        self.assertEqual(
            one_shot_code_exit_code(
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


if __name__ == "__main__":
    unittest.main()
