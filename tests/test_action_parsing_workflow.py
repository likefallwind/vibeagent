from __future__ import annotations

import unittest

from vibeagent.action_parsing import parse_tool_action
from vibeagent.types import UpdatePlanAction


class WorkflowActionParsingTests(unittest.TestCase):
    def test_update_plan_normalizes_status_aliases(self) -> None:
        action = parse_tool_action(
            "update_plan",
            {
                "plan": [
                    {"step": "Inspect", "status": "todo"},
                    {"step": "Implement", "status": "in-progress"},
                    {"step": "Verify", "status": "done"},
                ]
            },
        )

        self.assertIsInstance(action, UpdatePlanAction)
        self.assertEqual([item.status for item in action.plan], ["pending", "in_progress", "completed"])

    def test_todo_write_normalizes_status_aliases(self) -> None:
        action = parse_tool_action(
            "todo_write",
            {
                "todos": [
                    {"content": "Inspect", "status": "pending"},
                    {"content": "Implement", "status": "in-progress", "activeForm": "Implementing"},
                    {"content": "Verify", "status": "complete"},
                ]
            },
        )

        self.assertIsInstance(action, UpdatePlanAction)
        self.assertEqual([item.step for item in action.plan], ["Inspect", "Implement", "Verify"])
        self.assertEqual([item.status for item in action.plan], ["pending", "in_progress", "completed"])


if __name__ == "__main__":
    unittest.main()
