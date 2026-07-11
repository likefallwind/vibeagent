from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, Mock, patch

from vibeagent.cli_interactive import run_interactive_loop
from vibeagent.cli_output import build_approval_handler
from vibeagent.runtime_types import ApprovalDecision, ApprovalRequest
from vibeagent.session_timeline_reports import format_session_event_timeline_item
from vibeagent.session_types import SessionEvent
from vibeagent.session_approval import SessionApprovalHandler, approval_cache_key


def _request(action_type: str = "write_file", target: str = "app.py", preview: str | None = None) -> ApprovalRequest:
    return ApprovalRequest(action_type=action_type, target=target, risk="test risk", preview=preview)


class SessionApprovalHandlerTests(unittest.TestCase):
    def test_session_decision_is_reused_for_exact_action_and_target(self) -> None:
        prompt = Mock(
            side_effect=[
                ApprovalDecision(approved=True, message="always", scope="session"),
                ApprovalDecision(approved=True, message="other", scope="once"),
            ]
        )
        handler = SessionApprovalHandler(prompt)

        first = handler(_request())
        remembered = handler(_request())
        different = handler(_request(target="other.py"))

        self.assertTrue(first.approved)
        self.assertFalse(first.remembered)
        self.assertTrue(remembered.approved)
        self.assertTrue(remembered.remembered)
        self.assertEqual(remembered.scope, "session")
        self.assertEqual(different.message, "other")
        self.assertEqual(prompt.call_count, 2)
        self.assertEqual(handler.remembered_count, 1)

    def test_session_decision_includes_preview_in_cache_key(self) -> None:
        prompt = Mock(
            side_effect=[
                ApprovalDecision(approved=True, message="always first", scope="session"),
                ApprovalDecision(approved=True, message="always second", scope="session"),
            ]
        )
        handler = SessionApprovalHandler(prompt)

        first = handler(_request(preview="diff: add app"))
        remembered = handler(_request(preview="diff: add app"))
        different = handler(_request(preview="diff: add docs"))

        self.assertTrue(first.approved)
        self.assertTrue(remembered.remembered)
        self.assertEqual(different.message, "always second")
        self.assertEqual(prompt.call_count, 2)
        self.assertEqual(handler.remembered_count, 2)

    def test_session_decision_without_preview_keeps_existing_cache_key_shape(self) -> None:
        prompt = Mock(return_value=ApprovalDecision(approved=True, message="always", scope="session"))
        handler = SessionApprovalHandler(prompt)

        first = handler(_request())
        remembered = handler(_request())

        self.assertTrue(first.approved)
        self.assertTrue(remembered.remembered)
        self.assertEqual(prompt.call_count, 1)

    def test_denials_are_not_cached_and_clear_removes_approvals(self) -> None:
        prompt = Mock(
            side_effect=[
                ApprovalDecision(approved=False, message="no"),
                ApprovalDecision(approved=True, message="always", scope="session"),
                ApprovalDecision(approved=True, message="after clear"),
            ]
        )
        handler = SessionApprovalHandler(prompt)

        denied = handler(_request())
        approved = handler(_request())
        handler.clear()
        after_clear = handler(_request())

        self.assertFalse(denied.approved)
        self.assertTrue(approved.approved)
        self.assertEqual(handler.remembered_count, 0)
        self.assertEqual(after_clear.message, "after clear")
        self.assertEqual(prompt.call_count, 3)

    def test_mcp_actions_always_require_separate_approval(self) -> None:
        prompt = Mock(return_value=ApprovalDecision(approved=True, message="always", scope="session"))
        handler = SessionApprovalHandler(prompt)
        request = _request("mcp_call", "docs/search")

        first = handler(request)
        second = handler(request)

        self.assertEqual(prompt.call_count, 2)
        self.assertEqual(first.scope, "once")
        self.assertEqual(second.scope, "once")
        self.assertIn("always requires separate approval", first.message)
        self.assertIsNone(approval_cache_key(request))

    def test_terminal_handler_remembers_always_answer_without_reprompting(self) -> None:
        handler = build_approval_handler("ask")

        with patch("builtins.input", return_value="always") as input_mock, patch("sys.stdout"):
            first = handler(_request("run_command", "npm test"))
            second = handler(_request("run_command", "npm test"))

        self.assertEqual(input_mock.call_count, 1)
        self.assertEqual(first.scope, "session")
        self.assertTrue(second.remembered)

    def test_timeline_distinguishes_remembered_session_decisions(self) -> None:
        event = SessionEvent(
            line_number=4,
            type="approval_decision",
            payload={
                "decision": {
                    "approved": True,
                    "message": "Approved by remembered session decision.",
                    "scope": "session",
                    "remembered": True,
                }
            },
        )

        summary = format_session_event_timeline_item(event)

        self.assertIn("approved=yes", summary)
        self.assertIn("scope=session", summary)
        self.assertIn("remembered=yes", summary)


class InteractiveApprovalLifecycleTests(unittest.TestCase):
    def test_repl_reuses_handler_until_approval_policy_changes(self) -> None:
        result = MagicMock()
        result.message = "done"
        result.run_id = "run-1"
        run_agent = Mock(return_value=result)
        inputs = iter(
            [
                "task one",
                "task two",
                "/approval allow",
                "task three",
                "/approval ask",
                "task four",
                "/exit",
            ]
        )
        with tempfile.TemporaryDirectory(prefix="vibeagent-approval-") as base:
            with (
                patch("builtins.input", side_effect=lambda _prompt="": next(inputs)),
                patch("vibeagent.cli_interactive.prompt_project_permission_trust", return_value=False),
                patch("vibeagent.cli_interactive.print_agent_result"),
                patch("vibeagent.cli_interactive.resolve_execution_config") as config,
                patch("vibeagent.cli_interactive.build_provider_env", return_value={}),
                patch("pathlib.Path.cwd", return_value=Path(base)),
                patch("sys.stdout"),
            ):
                config.return_value = MagicMock(
                    max_iterations=2,
                    command_timeout_ms=10_000,
                    max_output_tokens=100,
                    model_retries=0,
                    model_retry_delay_ms=0,
                    model_timeout_ms=10_000,
                )
                code = run_interactive_loop(
                    command_namespace={},
                    create_chat_client_func=lambda _env: object(),
                    run_agent_func=run_agent,
                    get_resume_context_func=lambda _run_id: (None, None, ""),
                )

        handlers = [call.kwargs["approval_handler"] for call in run_agent.call_args_list]
        policies = [call.kwargs["approval_policy"] for call in run_agent.call_args_list]
        self.assertEqual(code, 0)
        self.assertIs(handlers[0], handlers[1])
        self.assertIsNot(handlers[1], handlers[2])
        self.assertIsNot(handlers[2], handlers[3])
        self.assertEqual(policies, ["ask", "ask", "allow", "ask"])


if __name__ == "__main__":
    unittest.main()
