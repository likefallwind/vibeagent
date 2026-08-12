from __future__ import annotations

import unittest

from vibeagent.action_parsing import parse_tool_action
from vibeagent.action_parsing_helpers import ActionParseError
from vibeagent.types import SendUserMessageAction, UpdatePlanAction


class WorkflowActionParsingTests(unittest.TestCase):
    def test_send_user_message_is_strict_bounded_and_control_safe(self) -> None:
        action = parse_tool_action(
            "SendUserMessage",
            {"message": "  Focused tests passed; running the full suite.  "},
        )

        self.assertEqual(
            action,
            SendUserMessageAction(
                type="send_user_message",
                message="Focused tests passed; running the full suite.",
            ),
        )
        invalid = (
            {},
            {"message": ""},
            {"message": "unsafe\x1b[2J"},
            {"message": "x" * 2_001},
            {"message": "ok", "extra": True},
        )
        for tool_input in invalid:
            with self.subTest(tool_input=tool_input), self.assertRaises(ActionParseError):
                parse_tool_action("SendUserMessage", tool_input)

    def test_update_plan_normalizes_status_aliases(self) -> None:
        action = parse_tool_action(
            "update_plan",
            {
                "plan": [
                    {"step": "Inspect", "status": "todo"},
                    {"step": "Implement", "status": "in-progress", "activeForm": "Implementing"},
                    {"step": "Verify", "status": "done", "active_form": "Verifying"},
                ]
            },
        )

        self.assertIsInstance(action, UpdatePlanAction)
        self.assertEqual([item.status for item in action.plan], ["pending", "in_progress", "completed"])
        self.assertEqual([item.active_form for item in action.plan], [None, "Implementing", "Verifying"])

    def test_todo_write_normalizes_status_aliases(self) -> None:
        action = parse_tool_action(
            "todo_write",
            {
                "explanation": "Reflect current progress",
                "todos": [
                    {"content": "Inspect", "status": "pending"},
                    {"content": "Implement", "status": "in-progress", "activeForm": "Implementing"},
                    {"content": "Verify", "status": "complete", "active_form": "Verifying"},
                ]
            },
        )

        self.assertIsInstance(action, UpdatePlanAction)
        self.assertEqual(action.explanation, "Reflect current progress")
        self.assertEqual([item.step for item in action.plan], ["Inspect", "Implement", "Verify"])
        self.assertEqual([item.status for item in action.plan], ["pending", "in_progress", "completed"])
        self.assertEqual([item.active_form for item in action.plan], [None, "Implementing", "Verifying"])


if __name__ == "__main__":
    unittest.main()
