from __future__ import annotations

import unittest

from vibeagent import action_parsing_helpers
from vibeagent.action_parsing_plan import (
    PLAN_ITEM_SCHEMA_STATUS_VALUES,
    PLAN_ITEM_STATUS_VALUES,
    normalize_plan_item_status,
    parse_plan_items,
    summarize_plan_update,
)
from vibeagent.action_parsing_scalars import ActionParseError
from vibeagent.types import PlanItem, UpdatePlanAction


class ActionParsingPlanTests(unittest.TestCase):
    def test_helpers_reexport_plan_parsing_contract(self) -> None:
        self.assertIs(action_parsing_helpers.PLAN_ITEM_SCHEMA_STATUS_VALUES, PLAN_ITEM_SCHEMA_STATUS_VALUES)
        self.assertIs(action_parsing_helpers.PLAN_ITEM_STATUS_VALUES, PLAN_ITEM_STATUS_VALUES)
        self.assertIs(action_parsing_helpers.normalize_plan_item_status, normalize_plan_item_status)
        self.assertIs(action_parsing_helpers.parse_plan_items, parse_plan_items)
        self.assertIs(action_parsing_helpers.summarize_plan_update, summarize_plan_update)

    def test_normalize_plan_item_status_accepts_aliases(self) -> None:
        self.assertEqual(normalize_plan_item_status("done"), "completed")
        self.assertEqual(normalize_plan_item_status(" IN-PROGRESS "), "in_progress")
        self.assertEqual(normalize_plan_item_status("blocked"), "pending")
        self.assertIsNone(normalize_plan_item_status("unknown"))
        self.assertIsNone(normalize_plan_item_status(None))

    def test_parse_plan_items_trims_steps_and_normalizes_statuses(self) -> None:
        items = parse_plan_items(
            [
                {"step": " inspect ", "status": "done"},
                {"step": "edit", "status": "in-progress"},
                {"step": "verify", "status": "todo"},
            ],
            "raw",
        )

        self.assertEqual(
            items,
            [
                PlanItem(step="inspect", status="completed"),
                PlanItem(step="edit", status="in_progress"),
                PlanItem(step="verify", status="pending"),
            ],
        )

    def test_parse_plan_items_rejects_multiple_in_progress_items(self) -> None:
        with self.assertRaisesRegex(ActionParseError, "at most one in_progress"):
            parse_plan_items(
                [
                    {"step": "one", "status": "active"},
                    {"step": "two", "status": "started"},
                ],
                "raw",
            )

    def test_schema_statuses_are_model_facing_subset(self) -> None:
        self.assertEqual(
            PLAN_ITEM_SCHEMA_STATUS_VALUES,
            ("complete", "completed", "done", "in-progress", "in_progress", "pending", "todo"),
        )
        self.assertTrue(set(PLAN_ITEM_SCHEMA_STATUS_VALUES).issubset(PLAN_ITEM_STATUS_VALUES))

    def test_summarize_plan_update_prefers_current_item(self) -> None:
        action = UpdatePlanAction(
            type="update_plan",
            explanation="finished setup",
            plan=[
                PlanItem(step="inspect", status="completed"),
                PlanItem(step="edit", status="in_progress"),
            ],
        )

        self.assertEqual(summarize_plan_update(action), "Plan updated. Current: edit")

    def test_summarize_plan_update_falls_back_to_explanation(self) -> None:
        action = UpdatePlanAction(
            type="update_plan",
            explanation="finished setup",
            plan=[PlanItem(step="inspect", status="completed")],
        )

        self.assertEqual(summarize_plan_update(action), "Plan updated. finished setup")


if __name__ == "__main__":
    unittest.main()
