from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from vibeagent.agent_hooks import HookRunResult
from vibeagent.agent_tool_results import (
    ToolObservationContext,
    record_subagent_tool_observation,
    record_subagent_tool_result_event,
    record_tool_observation,
    record_tool_result_event,
    record_tool_result_observation,
)
from vibeagent.session import read_session_events
from vibeagent.types import CommandResult, RunCommandObservation, WriteFileObservation
from vibeagent.workspace import create_run_workspace


class AgentToolResultsTests(unittest.TestCase):
    def test_record_tool_result_event_redacts_hooks_and_preserves_auto_flag(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-tool-results-") as base:
            workspace = create_run_workspace(Path(base), "run-1")
            observation = WriteFileObservation(
                kind="write_file",
                path="src/app.py",
                ok=True,
                message="Wrote src/app.py with OPENAI_API_KEY=plain-secret",
            )
            hook = HookRunResult(
                event="PostToolUse",
                command="python3 hook.py",
                source=".vibeagent/hooks.json",
                status="passed",
                ok=True,
                exit_code=0,
                timed_out=False,
                stdout="TOKEN=hook-secret",
                stderr="",
                message="Hook passed.",
            )

            payload = record_tool_result_event(
                workspace,
                tool_id="auto-final-review",
                tool_name="final_review",
                observation=observation,
                iteration=3,
                hook_results=(hook,),
                auto=True,
                event_extra={"before_action_type": "write_file"},
            )

            events = read_session_events(workspace.root, workspace.run_id)

        self.assertEqual(payload["message"], "Wrote src/app.py with OPENAI_API_KEY=[REDACTED]")
        self.assertEqual(payload["hooks"][0]["stdout"], "TOKEN=[REDACTED]")
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0].type, "tool_result")
        self.assertEqual(events[0].payload["id"], "auto-final-review")
        self.assertEqual(events[0].payload["name"], "final_review")
        self.assertEqual(events[0].payload["iteration"], 3)
        self.assertTrue(events[0].payload["auto"])
        self.assertEqual(events[0].payload["before_action_type"], "write_file")
        self.assertEqual(events[0].payload["result"], payload)
        self.assertNotIn("before_action_type", payload)

    def test_record_tool_result_observation_returns_tool_block_and_records_event(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-tool-results-") as base:
            workspace = create_run_workspace(Path(base), "run-1")
            observation = WriteFileObservation(
                kind="write_file",
                path="src/app.py",
                ok=True,
                message="Wrote src/app.py with OPENAI_API_KEY=plain-secret",
            )

            block = record_tool_result_observation(
                workspace,
                tool_id="write-1",
                tool_name="write_file",
                observation=observation,
                iteration=3,
            )
            events = read_session_events(workspace.root, workspace.run_id)

        self.assertEqual(block["type"], "tool_result")
        self.assertEqual(block["tool_call_id"], "write-1")
        self.assertEqual(json.loads(block["content"])["message"], "Wrote src/app.py with OPENAI_API_KEY=[REDACTED]")
        self.assertEqual(events[0].type, "tool_result")
        self.assertEqual(events[0].payload["id"], "write-1")
        self.assertEqual(events[0].payload["iteration"], 3)
        self.assertEqual(events[0].payload["result"]["message"], "Wrote src/app.py with OPENAI_API_KEY=[REDACTED]")

    def test_record_subagent_tool_result_event_redacts_payload_and_preserves_context(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-tool-results-") as base:
            workspace = create_run_workspace(Path(base), "run-1")
            observation = WriteFileObservation(
                kind="write_file",
                path="src/app.py",
                ok=False,
                message="Failed with TOKEN=subagent-secret",
            )
            hook = HookRunResult(
                event="PostToolUseFailure",
                command="python3 hook.py",
                source=".vibeagent/hooks.json",
                status="failed",
                ok=False,
                exit_code=1,
                timed_out=False,
                stdout="",
                stderr="PASSWORD=hook-secret",
                message="Hook failed.",
            )

            payload = record_subagent_tool_result_event(
                workspace,
                subagent_id="delegate-1-1",
                parent_iteration=4,
                iteration=2,
                tool_id="write-1",
                tool_name="write_file",
                observation=observation,
                failed=True,
                hook_results=(hook,),
            )
            events = read_session_events(workspace.root, workspace.run_id)

        self.assertEqual(payload["message"], "Failed with TOKEN=[REDACTED]")
        self.assertEqual(payload["hooks"][0]["stderr"], "PASSWORD=[REDACTED]")
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0].type, "subagent_tool_result")
        self.assertEqual(events[0].payload["subagent_id"], "delegate-1-1")
        self.assertEqual(events[0].payload["parent_iteration"], 4)
        self.assertEqual(events[0].payload["iteration"], 2)
        self.assertEqual(events[0].payload["id"], "write-1")
        self.assertEqual(events[0].payload["name"], "write_file")
        self.assertTrue(events[0].payload["failed"])
        self.assertEqual(events[0].payload["result"], payload)

    def test_record_subagent_tool_observation_returns_tool_block_and_records_failure(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-tool-results-") as base:
            workspace = create_run_workspace(Path(base), "run-1")
            observation = WriteFileObservation(
                kind="write_file",
                path="src/app.py",
                ok=False,
                message="Failed with API_KEY=subagent-secret",
            )

            block = record_subagent_tool_observation(
                workspace,
                subagent_id="delegate-1-1",
                parent_iteration=1,
                iteration=2,
                tool_id="write-1",
                tool_name="write_file",
                observation=observation,
            )
            events = read_session_events(workspace.root, workspace.run_id)

        self.assertEqual(block["type"], "tool_result")
        self.assertEqual(block["tool_call_id"], "write-1")
        self.assertEqual(json.loads(block["content"])["message"], "Failed with API_KEY=[REDACTED]")
        self.assertEqual(events[0].type, "subagent_tool_result")
        self.assertTrue(events[0].payload["failed"])
        self.assertEqual(events[0].payload["result"]["message"], "Failed with API_KEY=[REDACTED]")

    def test_record_tool_observation_appends_state_logs_command_and_returns_tool_block(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-tool-results-") as base:
            workspace = create_run_workspace(Path(base), "run-1")
            observation = RunCommandObservation(
                kind="run_command",
                result=CommandResult(
                    command="python3 -m unittest",
                    exit_code=1,
                    stdout="failure",
                    stderr="",
                    timed_out=False,
                    signal=None,
                    cwd=".",
                ),
            )
            additional = WriteFileObservation(kind="write_file", path="notes.txt", ok=True, message="Wrote notes.txt")
            observations = []
            logs = []

            block = record_tool_observation(
                workspace,
                tool_id="cmd-1",
                tool_name="run_command",
                observation=observation,
                additional_observations=(additional,),
                hook_results=(),
                context=ToolObservationContext(
                    observations=observations,
                    active_tool_names=set(),
                    iteration=2,
                    approval_policy="ask",
                    logger=lambda event, message: logs.append((event, message)),
                ),
            )
            events = read_session_events(workspace.root, workspace.run_id)

        self.assertEqual(observations, [observation, additional])
        self.assertEqual(block["type"], "tool_result")
        self.assertEqual(block["tool_call_id"], "cmd-1")
        self.assertEqual(json.loads(block["content"])["result"]["exit_code"], 1)
        self.assertEqual(events[0].type, "tool_result")
        self.assertEqual(events[0].payload["id"], "cmd-1")
        self.assertEqual(events[0].payload["result"]["result"]["stdout"], "failure")
        self.assertEqual(logs[0][0], "observed failure")
        self.assertIn("exit=1", logs[0][1])


if __name__ == "__main__":
    unittest.main()
