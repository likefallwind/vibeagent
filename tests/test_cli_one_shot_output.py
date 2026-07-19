from __future__ import annotations

import unittest
from pathlib import Path
from unittest.mock import patch

from vibeagent.agent_result import AgentResult
from vibeagent.cli_context import OneShotPriorContext
from vibeagent.cli_one_shot_output import (
    build_one_shot_chat_payload,
    build_one_shot_code_payload,
    build_one_shot_error_payload,
)


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


if __name__ == "__main__":
    unittest.main()
