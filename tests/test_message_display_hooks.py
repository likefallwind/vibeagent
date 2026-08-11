from __future__ import annotations

from contextlib import redirect_stdout
import io
import json
from pathlib import Path
import tempfile
import unittest
from uuid import UUID

from vibeagent.agent import run_agent
from vibeagent.agent_hook_results import HookRunResult
from vibeagent.agent_lifecycle_output import parse_lifecycle_hook_output
from vibeagent.cli_context import OneShotPriorContext
from vibeagent.cli_output import print_agent_result
from vibeagent.cli_result_payloads import build_code_result_payload
from vibeagent.types import ApprovalDecision, AssistantResponse, ChatMessage, ContentBlock
from vibeagent.workspace import create_run_workspace
from vibeagent.workspace_hooks import read_project_hooks


class MessageClient:
    def __init__(self, content: list[ContentBlock]) -> None:
        self.content = content
        self.messages: list[list[ChatMessage]] = []

    def complete(self, messages, tools=None, max_tokens=4096, temperature=0.2, timeout_ms=120_000):
        self.messages.append(list(messages))
        return AssistantResponse(content=self.content, raw={"content": self.content})


def _approve(_request) -> ApprovalDecision:
    return ApprovalDecision(approved=True, message="approved")


def _write_hooks(root: Path, payload: dict[str, object]) -> None:
    path = root / ".vibeagent" / "hooks.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload), encoding="utf-8")


def _hook_result(stdout: str, *, ok: bool = True) -> HookRunResult:
    return HookRunResult(
        event="MessageDisplay",
        command="hook",
        source="test",
        status="passed" if ok else "failed",
        ok=ok,
        exit_code=0 if ok else 1,
        timed_out=False,
        stdout=stdout,
        stderr="",
        message="hook result",
    )


class MessageDisplayConfigTests(unittest.TestCase):
    def test_matcher_is_ignored_and_default_timeout_is_ten_seconds(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-message-display-") as base:
            root = Path(base)
            _write_hooks(
                root,
                {
                    "MessageDisplay": [
                        {
                            "matcher": "ignored",
                            "hooks": [{"type": "command", "command": "true"}],
                        }
                    ],
                    "UserPromptSubmit": [
                        {"hooks": [{"type": "command", "command": "true"}]}
                    ],
                },
            )

            config = read_project_hooks(create_run_workspace(root))

        self.assertIsNone(config.error)
        hooks = {hook.event: hook for hook in config.hooks}
        self.assertEqual(hooks["MessageDisplay"].matcher, ".*")
        self.assertEqual(hooks["MessageDisplay"].timeout_ms, 10_000)
        self.assertEqual(hooks["UserPromptSubmit"].timeout_ms, 30_000)
        self.assertFalse(config.requires_sequential_tools)

    def test_rejects_model_handlers(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-message-display-") as base:
            root = Path(base)
            _write_hooks(
                root,
                {
                    "MessageDisplay": [
                        {"hooks": [{"type": "prompt", "prompt": "rewrite"}]}
                    ]
                },
            )

            config = read_project_hooks(create_run_workspace(root))

        self.assertIn("do not support prompt handlers", config.error or "")


class MessageDisplayOutputTests(unittest.TestCase):
    def test_parser_preserves_empty_replacement_and_ignores_failed_output(self) -> None:
        hidden = parse_lifecycle_hook_output(
            _hook_result(
                json.dumps(
                    {
                        "hookSpecificOutput": {
                            "hookEventName": "MessageDisplay",
                            "displayContent": "",
                        }
                    }
                )
            )
        )
        failed = parse_lifecycle_hook_output(
            _hook_result(json.dumps({"displayContent": "unsafe"}), ok=False)
        )

        self.assertEqual(hidden.display_content, "")
        self.assertIsNone(failed.display_content)

    def test_agent_keeps_original_semantics_and_exposes_display_only_text(self) -> None:
        script = """from __future__ import annotations
import json
from pathlib import Path
import sys

payload = json.load(sys.stdin)
Path("message-display-input.json").write_text(json.dumps(payload), encoding="utf-8")
print(json.dumps({
    "systemMessage": "display transformed",
    "hookSpecificOutput": {
        "hookEventName": "MessageDisplay",
        "displayContent": payload["delta"].replace("SECRET", "[redacted]"),
    },
}))
"""
        client = MessageClient([{"type": "text", "text": "Visible SECRET"}])
        with tempfile.TemporaryDirectory(prefix="vibeagent-message-display-") as base:
            root = Path(base)
            (root / "display_hook.py").write_text(script, encoding="utf-8")
            _write_hooks(
                root,
                {
                    "MessageDisplay": [
                        {
                            "hooks": [
                                {
                                    "type": "command",
                                    "command": "python3 display_hook.py",
                                }
                            ]
                        }
                    ]
                },
            )

            result = run_agent(
                "show a message",
                base_dir=root,
                client=client,
                max_iterations=1,
                approval_handler=_approve,
            )
            hook_input = json.loads(
                (root / "message-display-input.json").read_text(encoding="utf-8")
            )
            payload = build_code_result_payload(
                result,
                OneShotPriorContext(source="none"),
            )
            stdout = io.StringIO()
            with redirect_stdout(stdout):
                print_agent_result(result)

        self.assertTrue(result.success)
        self.assertEqual(result.message, "Visible SECRET")
        self.assertEqual(result.display_message, "Visible [redacted]")
        self.assertEqual(result.hook_system_messages, ["display transformed"])
        self.assertIn("Visible SECRET", str(result.conversation))
        self.assertNotIn("[redacted]", str(result.conversation))
        self.assertEqual(payload["message"], "Visible SECRET")
        self.assertEqual(payload["result"], "Visible SECRET")
        self.assertEqual(payload["displayMessage"], "Visible [redacted]")
        self.assertEqual(payload["display_message"], "Visible [redacted]")
        self.assertIn("Visible [redacted]", stdout.getvalue())
        self.assertNotIn("Visible SECRET", stdout.getvalue())
        self.assertEqual(hook_input["hook_event_name"], "MessageDisplay")
        self.assertEqual(hook_input["index"], 0)
        self.assertTrue(hook_input["final"])
        self.assertEqual(hook_input["delta"], "Visible SECRET")
        UUID(hook_input["turn_id"])
        UUID(hook_input["message_id"])

    def test_failed_hook_falls_back_to_original_display(self) -> None:
        client = MessageClient([{"type": "text", "text": "original"}])
        with tempfile.TemporaryDirectory(prefix="vibeagent-message-display-") as base:
            root = Path(base)
            _write_hooks(
                root,
                {
                    "MessageDisplay": [
                        {
                            "hooks": [
                                {
                                    "type": "command",
                                    "command": "python3 -c 'import sys; sys.exit(1)'",
                                }
                            ]
                        }
                    ]
                },
            )

            result = run_agent(
                "show a message",
                base_dir=root,
                client=client,
                max_iterations=1,
                approval_handler=_approve,
            )

        self.assertEqual(result.message, "original")
        self.assertIsNone(result.display_message)
        self.assertEqual(result.displayed_message, "original")


if __name__ == "__main__":
    unittest.main()
