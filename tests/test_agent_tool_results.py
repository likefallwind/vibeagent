from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from vibeagent.agent_hooks import HookRunResult
from vibeagent.agent_tool_results import record_tool_observation, record_tool_result_event
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
        self.assertEqual(events[0].payload["result"], payload)

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
                observations=observations,
                active_tool_names=set(),
                iteration=2,
                approval_policy="ask",
                logger=lambda event, message: logs.append((event, message)),
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
