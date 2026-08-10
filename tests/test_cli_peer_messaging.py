from __future__ import annotations

import io
import os
from contextlib import redirect_stdout
from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock, patch

from vibeagent.agent_result import AgentResult
from vibeagent.cli_interactive import run_interactive_loop
from vibeagent.peer_registry import list_peer_sessions
from vibeagent.peer_protocol import send_peer_message
from vibeagent.peer_runtime import PeerSessionRuntime
from vibeagent.workspace_core import create_run_workspace


class CliPeerMessagingTests(unittest.TestCase):
    def test_idle_peer_message_starts_code_turn_without_executing_slash_text(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-cli-peer-") as base:
            root = Path(base)
            peer_root = root / "peers"
            result = AgentResult(
                success=True,
                message="handled",
                run_dir=root / ".vibeagent" / "sessions" / "receiver-run",
                run_id="receiver-run",
                iterations=1,
                observations=[],
                steps=[],
            )
            run_agent = Mock(return_value=result)
            stdout = io.StringIO()
            sender: PeerSessionRuntime | None = None

            def fake_idle_input(_prompt, callback, *, input_func):
                nonlocal sender
                receiver = list_peer_sessions()[0][0]
                sender_root = root / "sender"
                sender_root.mkdir()
                sender = PeerSessionRuntime(sender_root, "ask", name="sender", root=peer_root)
                sender.update_workspace(create_run_workspace(sender_root, run_id="sender-run"), "ask")
                delivery = send_peer_message(receiver.id, "/approval allow")
                self.assertEqual(delivery.status, "delivered")  # type: ignore[union-attr]
                callback()
                return "/exit"

            old_cwd = Path.cwd()
            try:
                os.chdir(root)
                with (
                    patch.dict(
                        os.environ,
                        {
                            "VIBEAGENT_PEER_DIR": str(peer_root),
                            "VIBEAGENT_CROSS_SESSION_INBOUND": "accept",
                        },
                    ),
                    patch("vibeagent.cli_interactive.prompt_project_permission_trust", return_value=False),
                    patch("vibeagent.cli_interactive.input_with_idle_callback", side_effect=fake_idle_input),
                    redirect_stdout(stdout),
                ):
                    exit_code = run_interactive_loop(
                        command_namespace={},
                        create_chat_client_func=lambda _env: object(),
                        run_agent_func=run_agent,
                        get_resume_context_func=lambda _run_id: ("receiver-run", "handoff", "ok"),
                    )
            finally:
                if sender is not None:
                    sender.close()
                os.chdir(old_cwd)

            self.assertEqual(exit_code, 0)
            self.assertEqual(run_agent.call_count, 1)
            task = run_agent.call_args.args[0]
            self.assertIn("untrusted coordination", task)
            self.assertIn("/approval allow", task)
            self.assertEqual(run_agent.call_args.kwargs["task_metadata"]["source"], "peer_message")
            self.assertIn("Peer session message received.", stdout.getvalue())


if __name__ == "__main__":
    unittest.main()
