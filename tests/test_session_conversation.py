from __future__ import annotations

import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from vibeagent.session_conversation import (
    SessionConversationError,
    checkpoint_session_conversation,
    load_session_conversation,
    read_session_conversation,
)
from vibeagent.types import ChatMessage
from vibeagent.workspace_core import create_run_workspace


class SessionConversationTests(unittest.TestCase):
    def test_checkpoint_is_private_bounded_and_redacted(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-conversation-") as base:
            workspace = create_run_workspace(base, run_id="run-1")
            messages = [
                ChatMessage(role="system", content="system must stay fresh"),
                ChatMessage(
                    role="user",
                    content=[
                        {
                            "type": "text",
                            "text": "User task:\nfix app\n\nProject directory:\n/tmp/project",
                        },
                        {
                            "type": "image",
                            "source": {"type": "base64", "data": "private-image-data"},
                        },
                    ],
                ),
                ChatMessage(
                    role="assistant",
                    content=[
                        {"type": "text", "text": "I will update app.py."},
                        {
                            "type": "tool_call",
                            "id": "write-1",
                            "name": "write_file",
                            "input": {"path": "app.py", "content": "API_KEY=secret-value"},
                        },
                    ],
                ),
                ChatMessage(
                    role="user",
                    content=[
                        {
                            "type": "tool_result",
                            "tool_call_id": "write-1",
                            "content": json.dumps(
                                {
                                    "kind": "write_file",
                                    "path": "app.py",
                                    "content": "private-file-body",
                                    "message": "Wrote app.py",
                                }
                            ),
                        }
                    ],
                ),
            ]

            checkpoint_session_conversation(workspace, messages, "fix app")
            path = workspace.session_dir / "conversation.json"
            stored = path.read_text(encoding="utf-8")
            restored = read_session_conversation(base, "run-1")

            self.assertEqual(os.stat(path).st_mode & 0o777, 0o600)
            self.assertNotIn("system must stay fresh", stored)
            self.assertNotIn("private-image-data", stored)
            self.assertNotIn("private-file-body", stored)
            self.assertNotIn("secret-value", stored)
            self.assertEqual(restored[0], ChatMessage(role="user", content="User task:\nfix app"))
            self.assertIn("app.py", stored)
            self.assertIn("Wrote app.py", stored)

    def test_load_missing_is_empty_and_corrupt_falls_back_with_warning(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-conversation-") as base:
            workspace = create_run_workspace(base, run_id="run-1")
            self.assertEqual(load_session_conversation(base, "run-1").messages, ())
            (workspace.session_dir / "conversation.json").write_text("{broken", encoding="utf-8")

            loaded = load_session_conversation(base, "run-1")

            self.assertEqual(loaded.messages, ())
            self.assertIn("using bounded session context instead", loaded.warning or "")

    def test_read_rejects_symlink_and_session_mismatch(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-conversation-") as base:
            root = Path(base)
            workspace = create_run_workspace(root, run_id="run-1")
            target = root / "outside.json"
            target.write_text("{}", encoding="utf-8")
            (workspace.session_dir / "conversation.json").symlink_to(target)
            with self.assertRaises(SessionConversationError):
                read_session_conversation(root, "run-1")

            (workspace.session_dir / "conversation.json").unlink()
            (workspace.session_dir / "conversation.json").write_text(
                json.dumps({"version": 1, "run_id": "other", "messages": []}),
                encoding="utf-8",
            )
            with self.assertRaises(SessionConversationError):
                read_session_conversation(root, "run-1")

    def test_message_limit_keeps_a_complete_user_turn_boundary(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-conversation-") as base:
            workspace = create_run_workspace(base, run_id="run-1")
            messages = [
                ChatMessage(role="user", content="User task:\nfirst"),
                ChatMessage(role="assistant", content="first answer"),
                ChatMessage(role="user", content="User task:\nsecond"),
                ChatMessage(role="assistant", content="second answer"),
            ]

            with patch("vibeagent.session_conversation.MAX_CONVERSATION_MESSAGES", 3):
                checkpoint_session_conversation(workspace, messages, "second")
                restored = read_session_conversation(base, "run-1")

        self.assertEqual(
            restored,
            [
                ChatMessage(role="user", content="User task:\nsecond"),
                ChatMessage(role="assistant", content="second answer"),
            ],
        )


if __name__ == "__main__":
    unittest.main()
