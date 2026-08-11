from __future__ import annotations

import stat
from pathlib import Path
import tempfile
import threading
import time
import unittest
from unittest.mock import patch

from vibeagent.background_agent_approval import (
    BackgroundApprovalPrompt,
    decide_background_approval,
    read_background_approval,
)
from vibeagent.background_agent_config import create_background_agent_config
from vibeagent.background_agent_store import background_agent_view
from vibeagent.background_agent_types import BackgroundAgentRecord
from vibeagent.session_approval import SessionApprovalHandler
from vibeagent.types import ApprovalRequest


class BackgroundAgentApprovalTests(unittest.TestCase):
    def test_prompt_blocks_until_exact_agent_view_decision(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-background-approval-") as base:
            root = Path(base).resolve()
            config = create_background_agent_config(
                root,
                "aaaaaaaaaaaa",
                session_root=root,
                resume_reference="background-aaaaaaaaaaaa",
                base_argv=["--print", "task"],
            )
            handler = BackgroundApprovalPrompt(config, poll_interval=0.005)
            decisions = []
            thread = threading.Thread(
                target=lambda: decisions.append(
                    handler(
                        ApprovalRequest(
                            action_type="write_file",
                            target="result.txt",
                            risk="writes workspace content",
                            preview="hello",
                        )
                    )
                )
            )
            thread.start()
            approval = self._wait_for_approval(root, config.agent_id)

            self.assertTrue(thread.is_alive())
            self.assertEqual(approval.action_type, "write_file")
            self.assertEqual(approval.target, "result.txt")
            request_path = root / ".vibeagent/background-agents/approvals/aaaaaaaaaaaa.request.json"
            self.assertEqual(stat.S_IMODE(request_path.stat().st_mode), 0o600)
            with self.assertRaisesRegex(ValueError, "stale"):
                decide_background_approval(
                    root,
                    config.agent_id,
                    approved=True,
                    request_id="f" * 32,
                )
            self.assertTrue(thread.is_alive())
            decide_background_approval(
                root,
                config.agent_id,
                approved=True,
                scope="once",
                request_id=approval.request_id,
            )
            thread.join(timeout=2)

            self.assertFalse(thread.is_alive())
            self.assertTrue(decisions[0].approved)
            self.assertIsNone(read_background_approval(root, config.agent_id))

    def test_session_decision_skips_matching_second_prompt(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-background-approval-") as base:
            root = Path(base).resolve()
            config = create_background_agent_config(
                root,
                "bbbbbbbbbbbb",
                session_root=root,
                resume_reference="background-bbbbbbbbbbbb",
                base_argv=["--print", "task"],
            )
            handler = SessionApprovalHandler(BackgroundApprovalPrompt(config, poll_interval=0.005))
            request = ApprovalRequest(
                action_type="run_command",
                target="npm test",
                risk="runs a command",
            )
            decisions = []
            thread = threading.Thread(target=lambda: decisions.append(handler(request)))
            thread.start()
            self._wait_for_approval(root, config.agent_id)
            decide_background_approval(root, config.agent_id, approved=True, scope="session")
            thread.join(timeout=2)

            remembered = handler(request)

            self.assertTrue(decisions[0].approved)
            self.assertTrue(remembered.approved)
            self.assertTrue(remembered.remembered)
            self.assertIsNone(read_background_approval(root, config.agent_id))

    def test_live_record_reports_needs_input_while_prompt_waits(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-background-approval-") as base:
            root = Path(base).resolve()
            agent_id = "cccccccccccc"
            config = create_background_agent_config(
                root,
                agent_id,
                session_root=root,
                resume_reference=f"background-{agent_id}",
                base_argv=["--print", "task"],
            )
            handler = BackgroundApprovalPrompt(config, poll_interval=0.005)
            request = ApprovalRequest(
                action_type="edit_file",
                target="main.py",
                risk="edits workspace content",
            )
            thread = threading.Thread(target=lambda: handler(request))
            thread.start()
            self._wait_for_approval(root, agent_id)
            logs = root / ".vibeagent/background-agents/logs"
            record = BackgroundAgentRecord(
                id=agent_id,
                project_root=root,
                invocation_root=root,
                pid=1234,
                start_ticks=77,
                started_at="2026-08-11T00:00:00+00:00",
                task_summary="edit main",
                session_name=f"background-{agent_id}",
                stdout_path=logs / f"{agent_id}.stdout.log",
                stderr_path=logs / f"{agent_id}.stderr.log",
                exit_code_path=logs / f"{agent_id}.exitcode",
                stopped_path=logs / f"{agent_id}.stopped",
            )

            with patch(
                "vibeagent.background_agent_store.persistent_process_running",
                return_value=True,
            ):
                view = background_agent_view(record)
            decide_background_approval(root, agent_id, approved=False)
            thread.join(timeout=2)

            self.assertEqual(view.status, "needs-input")
            self.assertFalse(thread.is_alive())

    def _wait_for_approval(self, root: Path, agent_id: str):
        deadline = time.monotonic() + 2
        while time.monotonic() < deadline:
            approval = read_background_approval(root, agent_id)
            if approval is not None:
                return approval
            time.sleep(0.005)
        self.fail("background approval was not published")


if __name__ == "__main__":
    unittest.main()
