from __future__ import annotations

import json
import shlex
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from vibeagent.agent import run_agent
from vibeagent.agent_hook_results import HookRunResult
from vibeagent.agent_pre_tool_hook_output import (
    PreToolHookOutputError,
    merge_pre_tool_decision,
    parse_pre_tool_hook_output,
)
from vibeagent.types import ApprovalDecision, AssistantResponse, ChatMessage, ContentBlock


class HookClient:
    def __init__(self, responses: list[list[ContentBlock]]) -> None:
        self.responses = responses
        self.messages: list[list[ChatMessage]] = []

    def complete(self, messages, tools=None, max_tokens=4096, temperature=0.2, timeout_ms=120_000):
        self.messages.append(list(messages))
        content = self.responses[len(self.messages) - 1]
        return AssistantResponse(content=content, raw={"content": content})


def _hook_output(payload: dict[str, object]) -> str:
    code = f"import json; print(json.dumps({payload!r}))"
    return f"python3 -c {shlex.quote(code)}"


def _write_hooks(root: Path, commands: list[str], matcher: str) -> None:
    path = root / ".vibeagent/hooks.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(
            {
                "PreToolUse": [
                    {
                        "matcher": matcher,
                        "hooks": [{"type": "command", "command": command}],
                    }
                    for command in commands
                ]
            }
        ),
        encoding="utf-8",
    )


def _decision_payload(
    decision: str,
    *,
    reason: str | None = None,
    updated_input: dict[str, object] | None = None,
    context: str | None = None,
) -> dict[str, object]:
    specific: dict[str, object] = {
        "hookEventName": "PreToolUse",
        "permissionDecision": decision,
    }
    if reason is not None:
        specific["permissionDecisionReason"] = reason
    if updated_input is not None:
        specific["updatedInput"] = updated_input
    if context is not None:
        specific["additionalContext"] = context
    return {"hookSpecificOutput": specific}


def _client(tool_name: str, tool_input: dict[str, object]) -> HookClient:
    return HookClient(
        [
            [{"type": "tool_call", "id": "tool-1", "name": tool_name, "input": tool_input}],
            [{"type": "text", "text": "Tool call handled."}],
        ]
    )


class PreToolHookOutputTests(unittest.TestCase):
    def _result(self, stdout: str) -> HookRunResult:
        return HookRunResult(
            event="PreToolUse",
            command="hook",
            source="test",
            status="passed",
            ok=True,
            exit_code=0,
            timed_out=False,
            stdout=stdout,
            stderr="",
            message="passed",
        )

    def test_parses_structured_and_legacy_decisions(self) -> None:
        structured = parse_pre_tool_hook_output(
            self._result(json.dumps(_decision_payload("ask", reason="review")))
        )
        legacy = parse_pre_tool_hook_output(
            self._result(json.dumps({"decision": "block", "reason": "legacy"}))
        )

        self.assertEqual(structured.permission_decision, "ask")
        self.assertEqual(structured.permission_reason, "review")
        self.assertEqual(legacy.permission_decision, "deny")
        self.assertEqual(legacy.permission_reason, "legacy")
        self.assertEqual(merge_pre_tool_decision("allow", "ask"), "ask")
        self.assertEqual(merge_pre_tool_decision("defer", "deny"), "deny")

    def test_rejects_malformed_structured_output(self) -> None:
        with self.assertRaises(PreToolHookOutputError):
            parse_pre_tool_hook_output(self._result('{"hookSpecificOutput":'))
        with self.assertRaises(PreToolHookOutputError):
            parse_pre_tool_hook_output(
                self._result(json.dumps(_decision_payload("allow", updated_input={}) | {"hookSpecificOutput": []}))
            )


class PreToolHookIntegrationTests(unittest.TestCase):
    def test_updated_input_is_reparsed_before_approval_and_execution(self) -> None:
        client = _client("write_file", {"path": "original.py", "content": "old = True\n"})
        approvals: list[tuple[str, str]] = []

        def approve(request):
            approvals.append((request.action_type, request.target))
            return ApprovalDecision(approved=True, message="approved")

        output = _decision_payload(
            "ask",
            updated_input={"path": "updated.py", "content": "new = True\n"},
        )
        with tempfile.TemporaryDirectory(prefix="vibeagent-pre-hook-") as base:
            root = Path(base)
            _write_hooks(root, [_hook_output(output)], "write_file")
            run_agent(
                "Write a file",
                base_dir=root,
                client=client,
                max_iterations=2,
                approval_handler=approve,
            )

            self.assertFalse((root / "original.py").exists())
            self.assertEqual((root / "updated.py").read_text(encoding="utf-8"), "new = True\n")

        self.assertEqual(approvals[-1], ("write_file", "updated.py"))
        payload = json.loads(client.messages[1][-1].content[0]["content"])
        self.assertTrue(payload["hooks"][0]["updated_input_applied"])

    def test_allow_skips_target_approval_and_exposes_additional_context(self) -> None:
        client = _client("write_file", {"path": "allowed.py", "content": "ok = True\n"})
        approvals: list[str] = []

        def approve(request):
            approvals.append(request.action_type)
            return ApprovalDecision(approved=True, message="approved")

        with tempfile.TemporaryDirectory(prefix="vibeagent-pre-hook-") as base:
            root = Path(base)
            _write_hooks(
                root,
                [_hook_output(_decision_payload("allow", context="validated by policy service"))],
                "write_file",
            )
            run_agent(
                "Write allowed.py",
                base_dir=root,
                client=client,
                max_iterations=2,
                approval_handler=approve,
            )
            self.assertTrue((root / "allowed.py").exists())

        self.assertEqual(approvals, ["run_command"])
        payload = json.loads(client.messages[1][-1].content[0]["content"])
        self.assertEqual(payload["hooks"][0]["additional_context"], "validated by policy service")

    def test_ask_forces_approval_for_read_only_tool(self) -> None:
        client = _client("read_file", {"path": "app.py"})
        approvals: list[str] = []

        def approve(request):
            approvals.append(request.action_type)
            return ApprovalDecision(approved=True, message="approved")

        with tempfile.TemporaryDirectory(prefix="vibeagent-pre-hook-") as base:
            root = Path(base)
            (root / "app.py").write_text("x = 1\n", encoding="utf-8")
            _write_hooks(root, [_hook_output(_decision_payload("ask", reason="review read"))], "read_file")
            run_agent(
                "Read app.py",
                base_dir=root,
                client=client,
                max_iterations=2,
                approval_handler=approve,
            )

        self.assertEqual(approvals, ["run_command", "read_file"])

    def test_ask_is_not_replaced_by_sandbox_auto_approval(self) -> None:
        client = _client("write_file", {"path": "reviewed.py", "content": "x = 1\n"})
        approvals: list[str] = []

        def approve(request):
            approvals.append(request.action_type)
            return ApprovalDecision(approved=True, message="approved")

        with tempfile.TemporaryDirectory(prefix="vibeagent-pre-hook-") as base:
            root = Path(base)
            _write_hooks(root, [_hook_output(_decision_payload("ask"))], "write_file")
            with patch(
                "vibeagent.agent_permissions.sandbox_auto_approval_reason",
                return_value="sandboxed",
            ):
                run_agent(
                    "Write reviewed.py",
                    base_dir=root,
                    client=client,
                    max_iterations=2,
                    approval_handler=approve,
                )

        self.assertEqual(approvals, ["write_file"])

    def test_deny_wins_over_allow_without_target_approval(self) -> None:
        client = _client("write_file", {"path": "denied.py", "content": "bad = True\n"})
        approvals: list[str] = []

        def approve(request):
            approvals.append(request.action_type)
            return ApprovalDecision(approved=True, message="approved")

        commands = [
            _hook_output(_decision_payload("allow")),
            _hook_output(_decision_payload("deny", reason="blocked by second hook")),
        ]
        with tempfile.TemporaryDirectory(prefix="vibeagent-pre-hook-") as base:
            root = Path(base)
            _write_hooks(root, commands, "write_file")
            result = run_agent(
                "Write denied.py",
                base_dir=root,
                client=client,
                max_iterations=2,
                approval_handler=approve,
            )
            self.assertFalse((root / "denied.py").exists())

        self.assertEqual(approvals, ["run_command", "run_command"])
        self.assertEqual(result.observations[0].kind, "approval_denied")
        self.assertEqual(result.observations[0].message, "blocked by second hook")

    def test_updated_command_is_still_hard_blocked(self) -> None:
        client = _client("Bash", {"command": "printf safe"})
        approvals: list[str] = []

        def approve(request):
            approvals.append(request.action_type)
            return ApprovalDecision(approved=True, message="approved")

        output = _decision_payload("allow", updated_input={"command": "sudo reboot"})
        with tempfile.TemporaryDirectory(prefix="vibeagent-pre-hook-") as base:
            root = Path(base)
            _write_hooks(root, [_hook_output(output)], "Bash")
            result = run_agent(
                "Run command",
                base_dir=root,
                client=client,
                max_iterations=2,
                approval_handler=approve,
            )

        self.assertEqual(approvals, ["run_command"])
        self.assertEqual(result.observations[0].kind, "run_command")
        self.assertIsNone(result.observations[0].result.exit_code)
        self.assertIn("Command blocked", result.observations[0].result.stderr)

    def test_permission_deny_applies_to_updated_input_despite_hook_allow(self) -> None:
        client = _client("write_file", {"path": "safe.py", "content": "x = 1\n"})
        approvals: list[str] = []

        def approve(request):
            approvals.append(request.action_type)
            return ApprovalDecision(approved=True, message="approved")

        output = _decision_payload(
            "allow",
            updated_input={"path": "blocked.py", "content": "x = 1\n"},
        )
        with tempfile.TemporaryDirectory(prefix="vibeagent-pre-hook-") as base:
            root = Path(base)
            _write_hooks(root, [_hook_output(output)], "write_file")
            permissions_path = root / ".vibeagent/permissions.json"
            permissions_path.write_text(
                json.dumps({"deny": ["Write(blocked.py)"]}), encoding="utf-8"
            )
            result = run_agent(
                "Write a file",
                base_dir=root,
                client=client,
                max_iterations=2,
                approval_handler=approve,
            )
            self.assertFalse((root / "blocked.py").exists())

        self.assertEqual(approvals, ["run_command"])
        self.assertEqual(result.observations[0].kind, "approval_denied")
        self.assertIn("permission rule", result.observations[0].message)

    def test_updated_input_reaches_special_ask_user_execution(self) -> None:
        client = _client(
            "ask_user",
            {"question": "Original?", "options": ["yes", "no"], "allow_free_text": False},
        )
        asked: list[str] = []

        def answer(request):
            asked.append(request.question)
            return "later"

        output = _decision_payload(
            "allow",
            updated_input={
                "question": "Updated?",
                "options": ["now", "later"],
                "allow_free_text": False,
            },
        )
        with tempfile.TemporaryDirectory(prefix="vibeagent-pre-hook-") as base:
            root = Path(base)
            _write_hooks(root, [_hook_output(output)], "ask_user")
            result = run_agent(
                "Ask before continuing",
                base_dir=root,
                client=client,
                max_iterations=2,
                approval_handler=lambda _request: ApprovalDecision(True, "approved"),
                user_input_handler=answer,
            )

        self.assertEqual(asked, ["Updated?"])
        self.assertEqual(result.observations[0].question, "Updated?")
        self.assertEqual(result.observations[0].answer, "later")

    def test_defer_stops_execution_with_explicit_result(self) -> None:
        client = _client("write_file", {"path": "later.py", "content": "x = 1\n"})
        with tempfile.TemporaryDirectory(prefix="vibeagent-pre-hook-") as base:
            root = Path(base)
            _write_hooks(root, [_hook_output(_decision_payload("defer"))], "write_file")
            result = run_agent(
                "Write later.py",
                base_dir=root,
                client=client,
                max_iterations=2,
                approval_handler=lambda _request: ApprovalDecision(True, "approved"),
            )
            self.assertFalse((root / "later.py").exists())

        self.assertEqual(result.observations[0].kind, "tool_error")
        self.assertIn("deferred", result.observations[0].message)


if __name__ == "__main__":
    unittest.main()
