from __future__ import annotations

from pathlib import Path
import stat
import tempfile
import threading
import time
import unittest
from unittest.mock import patch

from vibeagent.agent import run_agent
from vibeagent.background_agent_config import create_background_agent_config
from vibeagent.background_agent_input import (
    BackgroundUserInputPrompt,
    answer_background_user_input,
    read_background_user_input,
)
from vibeagent.background_agent_store import background_agent_view
from vibeagent.background_agent_types import BackgroundAgentRecord
from vibeagent.types import AssistantResponse, UserInputRequest


class _QuestionClient:
    def __init__(self) -> None:
        self.calls = 0

    def complete(self, messages, tools=None, max_tokens=4096, temperature=0.2, timeout_ms=120_000):
        self.calls += 1
        if self.calls == 1:
            content = [
                {
                    "type": "tool_call",
                    "id": "ask-1",
                    "name": "AskUserQuestion",
                    "input": {
                        "questions": [
                            {
                                "question": "Which database should back the service?",
                                "header": "Database",
                                "options": [
                                    {"label": "SQLite", "description": "Local storage"},
                                    {"label": "PostgreSQL", "description": "Shared storage"},
                                ],
                                "multiSelect": False,
                            }
                        ]
                    },
                }
            ]
        else:
            content = [{"type": "text", "text": "Using PostgreSQL."}]
        return AssistantResponse(content=content, raw={"content": content})


class BackgroundAgentInputTests(unittest.TestCase):
    def test_agent_turn_resumes_after_dashboard_answer(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-background-input-") as base:
            root = Path(base).resolve()
            config = self._config(root, "aaaaaaaaaaaa")
            results = []
            thread = threading.Thread(
                target=lambda: results.append(
                    run_agent(
                        "Configure storage",
                        base_dir=root,
                        client=_QuestionClient(),
                        max_iterations=2,
                        user_input_handler=BackgroundUserInputPrompt(
                            config,
                            poll_interval=0.005,
                        ),
                    )
                )
            )
            thread.start()
            interaction = self._wait_for_input(root, config.agent_id)

            self.assertTrue(thread.is_alive())
            self.assertEqual(interaction.request.header, "Database")
            self.assertEqual(interaction.request.options, ["SQLite", "PostgreSQL"])
            request_path = (
                root
                / ".vibeagent/background-agents/user-input/aaaaaaaaaaaa.request.json"
            )
            self.assertEqual(stat.S_IMODE(request_path.stat().st_mode), 0o600)
            with patch(
                "vibeagent.background_agent_store.persistent_process_running",
                return_value=True,
            ):
                self.assertEqual(
                    background_agent_view(self._record(root, config.agent_id)).status,
                    "needs-input",
                )
            answer_background_user_input(root, config.agent_id, "2")
            thread.join(timeout=3)

            self.assertFalse(thread.is_alive())
            self.assertEqual(results[0].message, "Using PostgreSQL.")
            self.assertEqual(results[0].observations[0].answer, "PostgreSQL")
            self.assertIsNone(read_background_user_input(root, config.agent_id))

    def test_invalid_closed_answer_does_not_release_waiter(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-background-input-") as base:
            root = Path(base).resolve()
            config = self._config(root, "bbbbbbbbbbbb")
            answers = []
            handler = BackgroundUserInputPrompt(config, poll_interval=0.2)
            request = UserInputRequest(
                question="Choose capabilities",
                options=["Audit", "Metrics"],
                allow_free_text=False,
                multi_select=True,
            )
            thread = threading.Thread(target=lambda: answers.append(handler(request)))
            thread.start()
            self._wait_for_input(root, config.agent_id)

            with self.assertRaisesRegex(ValueError, "allowed options"):
                answer_background_user_input(root, config.agent_id, "Tracing")
            self.assertTrue(thread.is_alive())
            answer_background_user_input(root, config.agent_id, "1, 2")
            with self.assertRaisesRegex(ValueError, "already answered"):
                answer_background_user_input(root, config.agent_id, "1")
            thread.join(timeout=2)

            self.assertFalse(thread.is_alive())
            self.assertEqual(answers, [["Audit", "Metrics"]])

    def _config(self, root: Path, agent_id: str):
        return create_background_agent_config(
            root,
            agent_id,
            session_root=root,
            resume_reference=f"background-{agent_id}",
            base_argv=["--print", "task"],
        )

    def _record(self, root: Path, agent_id: str) -> BackgroundAgentRecord:
        logs = root / ".vibeagent/background-agents/logs"
        return BackgroundAgentRecord(
            id=agent_id,
            project_root=root,
            invocation_root=root,
            pid=1234,
            start_ticks=77,
            started_at="2026-08-11T00:00:00+00:00",
            task_summary="configure storage",
            session_name=f"background-{agent_id}",
            stdout_path=logs / f"{agent_id}.stdout.log",
            stderr_path=logs / f"{agent_id}.stderr.log",
            exit_code_path=logs / f"{agent_id}.exitcode",
            stopped_path=logs / f"{agent_id}.stopped",
        )

    def _wait_for_input(self, root: Path, agent_id: str):
        deadline = time.monotonic() + 2
        while time.monotonic() < deadline:
            interaction = read_background_user_input(root, agent_id)
            if interaction is not None:
                return interaction
            time.sleep(0.005)
        self.fail("background user input was not published")


if __name__ == "__main__":
    unittest.main()
