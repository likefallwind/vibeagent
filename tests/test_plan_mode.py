import json
import tempfile
import unittest
from pathlib import Path

from vibeagent.agent import run_agent
from vibeagent.agent_runtime_utils import compact_agent_message_history
from vibeagent.prompts import build_messages
from vibeagent.tool_catalog import get_permissions_report, get_permissions_text
from vibeagent.tool_catalog_core import APPROVAL_REQUIRED_TOOL_NAMES
from vibeagent.types import ApprovalDecision, AssistantResponse, ChatMessage, ContentBlock
from vibeagent.workspace import create_run_workspace


class RecordingClient:
    def __init__(self, responses: list[list[ContentBlock]]) -> None:
        self.responses = responses
        self.messages: list[list[ChatMessage]] = []
        self.tools: list[list[dict]] = []

    def complete(self, messages, tools=None, max_tokens=4096, temperature=0.2, timeout_ms=120_000):
        self.messages.append(list(messages))
        self.tools.append(list(tools or []))
        content = self.responses[len(self.messages) - 1]
        return AssistantResponse(content=content, raw={"content": content})


class PlanModeTests(unittest.TestCase):
    def test_plan_mode_prompt_and_tool_catalog_are_read_only(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-plan-") as base:
            workspace = create_run_workspace(Path(base))
            messages = build_messages("Plan a refactor", workspace, approval_policy="plan")

        prompt = str(messages[1].content)
        self.assertIn("Plan mode is active", prompt)
        self.assertIn("Do not claim that you changed the workspace", prompt)

    def test_plan_mode_instruction_survives_context_compaction(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-plan-") as base:
            workspace = create_run_workspace(Path(base))
            messages = [ChatMessage(role="user", content=str(index)) for index in range(20)]
            compacted = compact_agent_message_history(
                "Plan a refactor",
                workspace,
                messages,
                [],
                [],
                None,
                10,
                approval_policy="plan",
            )

        self.assertIn("Plan mode is active", str(compacted[1].content))

    def test_custom_system_prompt_survives_context_compaction(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-plan-") as base:
            workspace = create_run_workspace(Path(base))
            messages = [ChatMessage(role="user", content=str(index)) for index in range(20)]
            compacted = compact_agent_message_history(
                "Plan a refactor",
                workspace,
                messages,
                [],
                [],
                None,
                10,
                append_system_prompt="Keep the final answer terse.",
            )

        self.assertIn("Keep the final answer terse.", str(compacted[0].content))

    def test_plan_mode_denies_hidden_write_even_with_approving_handler(self) -> None:
        approvals: list[str] = []

        def approve(request):
            approvals.append(request.action_type)
            return ApprovalDecision(approved=True, message="approved")

        client = RecordingClient(
            [[{"type": "tool_call", "id": "write-1", "name": "write_file", "input": {"path": "note.txt", "content": "changed"}}]]
        )
        with tempfile.TemporaryDirectory(prefix="vibeagent-plan-") as base:
            root = Path(base)
            result = run_agent(
                "Plan a file change",
                base_dir=root,
                client=client,
                max_iterations=1,
                approval_policy="plan",
                approval_handler=approve,
            )

            self.assertFalse((root / "note.txt").exists())

        exposed_names = {str(tool["name"]) for tool in client.tools[0]}
        self.assertEqual(exposed_names & APPROVAL_REQUIRED_TOOL_NAMES, {"ExitPlanMode"})
        self.assertEqual(approvals, [])
        self.assertEqual(result.observations[0].kind, "approval_denied")
        self.assertIn("Plan mode is read-only", result.observations[0].message)

    def test_plan_mode_tool_search_returns_read_only_matches(self) -> None:
        client = RecordingClient(
            [
                [
                    {"type": "tool_call", "id": "search-1", "name": "tool_search", "input": {"query": "file"}},
                    {"type": "tool_call", "id": "list-1", "name": "list_files", "input": {}},
                ]
            ]
        )
        with tempfile.TemporaryDirectory(prefix="vibeagent-plan-") as base:
            result = run_agent(
                "Find file tools",
                base_dir=Path(base),
                client=client,
                max_iterations=1,
                approval_policy="plan",
            )

        search = next(observation for observation in result.observations if observation.kind == "tool_search")
        self.assertFalse(search.approval_required)
        self.assertTrue(all(not match["approvalRequired"] for match in search.matches))

    def test_plan_mode_exit_requires_approval_and_restores_previous_policy(self) -> None:
        approvals: list[str] = []

        def approve(request):
            approvals.append(request.action_type)
            return ApprovalDecision(approved=True, message="approved")

        client = RecordingClient(
            [
                [
                    {
                        "type": "tool_call",
                        "id": "exit-plan-1",
                        "name": "ExitPlanMode",
                        "input": {"plan": "Change calc.py, then run python -m unittest discover -s tests."},
                    }
                ],
                [
                    {
                        "type": "tool_call",
                        "id": "write-1",
                        "name": "write_file",
                        "input": {"path": "note.txt", "content": "changed"},
                    }
                ],
                [{"type": "text", "text": "Plan approved and implemented."}],
            ]
        )
        with tempfile.TemporaryDirectory(prefix="vibeagent-plan-") as base:
            root = Path(base)
            result = run_agent(
                "Plan a file change",
                base_dir=root,
                client=client,
                max_iterations=3,
                approval_policy="plan",
                approval_handler=approve,
            )

            self.assertEqual((root / "note.txt").read_text(encoding="utf-8"), "changed")

        exposed_names = {str(tool["name"]) for tools in client.tools for tool in tools}
        observation_kinds = [observation.kind for observation in result.observations]

        self.assertTrue(result.success)
        self.assertIn("ExitPlanMode", exposed_names)
        self.assertEqual(observation_kinds[:2], ["exit_plan_mode", "write_file"])
        self.assertEqual(approvals, ["exit_plan_mode", "write_file"])
        self.assertEqual(result.approval_policy, "ask")
        self.assertEqual(len(result.plan), 1)
        self.assertEqual(result.plan[0].status, "completed")
        self.assertIn("Change calc.py", result.plan[0].step)

    def test_enter_plan_mode_changes_the_next_turn_to_read_only(self) -> None:
        approvals: list[str] = []

        def approve(request):
            approvals.append(request.action_type)
            return ApprovalDecision(approved=True, message="approved")

        client = RecordingClient(
            [
                [{"type": "tool_call", "id": "enter-1", "name": "EnterPlanMode", "input": {}}],
                [
                    {
                        "type": "tool_call",
                        "id": "write-1",
                        "name": "write_file",
                        "input": {"path": "blocked.txt", "content": "no"},
                    }
                ],
            ]
        )
        with tempfile.TemporaryDirectory(prefix="vibeagent-plan-") as base:
            root = Path(base)
            result = run_agent(
                "Inspect before editing",
                base_dir=root,
                client=client,
                max_iterations=2,
                approval_policy="ask",
                approval_handler=approve,
            )
            self.assertFalse((root / "blocked.txt").exists())
            events = [
                json.loads(line)
                for line in (
                    root / ".vibeagent" / "sessions" / result.run_id / "events.jsonl"
                ).read_text(encoding="utf-8").splitlines()
            ]

        first_names = {str(tool["name"]) for tool in client.tools[0]}
        second_names = {str(tool["name"]) for tool in client.tools[1]}
        self.assertIn("EnterPlanMode", first_names)
        self.assertNotIn("ExitPlanMode", first_names)
        self.assertNotIn("EnterPlanMode", second_names)
        self.assertIn("ExitPlanMode", second_names)
        self.assertEqual([item.kind for item in result.observations], ["enter_plan_mode", "approval_denied"])
        self.assertEqual(approvals, [])
        transition = next(event for event in events if event["type"] == "permission_mode_changed")
        self.assertEqual((transition["previous"], transition["current"]), ("ask", "plan"))

    def test_plan_feedback_keeps_read_only_mode_without_completion_blocker(self) -> None:
        def keep_planning(request):
            return ApprovalDecision(
                approved=False,
                message="Add a rollback step before implementation.",
                permission_mode="plan",
            )

        client = RecordingClient(
            [
                [
                    {
                        "type": "tool_call",
                        "id": "exit-1",
                        "name": "ExitPlanMode",
                        "input": {"plan": "Inspect, patch, and test."},
                    }
                ],
                [{"type": "tool_call", "id": "read-1", "name": "list_files", "input": {}}],
                [{"type": "text", "text": "Revised plan includes rollback."}],
            ]
        )
        with tempfile.TemporaryDirectory(prefix="vibeagent-plan-") as base:
            result = run_agent(
                "Plan safely",
                base_dir=Path(base),
                client=client,
                max_iterations=3,
                approval_policy="plan",
                approval_handler=keep_planning,
            )

        second_names = {str(tool["name"]) for tool in client.tools[1]}
        self.assertEqual(result.approval_policy, "plan")
        self.assertEqual(result.observations[0].kind, "plan_mode_feedback")
        self.assertIn("rollback", result.observations[0].message)
        self.assertIn("ExitPlanMode", second_names)
        self.assertNotIn("write_file", second_names)
        self.assertEqual(result.latest_completion_denied_approvals, [])

    def test_approved_plan_can_switch_to_allow_mode(self) -> None:
        approvals: list[str] = []

        def approve_plan(request):
            approvals.append(request.action_type)
            return ApprovalDecision(
                approved=True,
                message="approved",
                permission_mode="allow",
            )

        client = RecordingClient(
            [
                [
                    {
                        "type": "tool_call",
                        "id": "exit-1",
                        "name": "ExitPlanMode",
                        "input": {"plan": "Write approved.txt."},
                    }
                ],
                [
                    {
                        "type": "tool_call",
                        "id": "write-1",
                        "name": "write_file",
                        "input": {"path": "approved.txt", "content": "ok"},
                    }
                ],
                [{"type": "text", "text": "Implemented."}],
            ]
        )
        with tempfile.TemporaryDirectory(prefix="vibeagent-plan-") as base:
            root = Path(base)
            result = run_agent(
                "Plan then implement",
                base_dir=root,
                client=client,
                max_iterations=3,
                approval_policy="plan",
                approval_handler=approve_plan,
            )
            self.assertEqual((root / "approved.txt").read_text(encoding="utf-8"), "ok")

        self.assertEqual(approvals, ["exit_plan_mode"])
        self.assertEqual(result.approval_policy, "allow")

    def test_permissions_report_describes_plan_mode(self) -> None:
        report = get_permissions_report("plan")

        self.assertTrue(report["planMode"])
        self.assertIn("planMode: read-only tools only", get_permissions_text("plan"))


if __name__ == "__main__":
    unittest.main()
