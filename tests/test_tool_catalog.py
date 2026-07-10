from __future__ import annotations

import unittest

from vibeagent import tool_catalog, tool_catalog_core, tool_catalog_search
from vibeagent.tool_catalog import (
    format_tool_search_report_text,
    get_tool_search_report,
    valid_tool_categories,
)
from vibeagent.tool_definitions import AGENT_TOOL_DEFINITIONS


class ToolCatalogTests(unittest.TestCase):
    def test_tool_catalog_reexports_split_helpers(self) -> None:
        self.assertIs(tool_catalog.APPROVAL_REQUIRED_TOOL_NAMES, tool_catalog_core.APPROVAL_REQUIRED_TOOL_NAMES)
        self.assertIs(tool_catalog.TOOL_CATEGORIES, tool_catalog_core.TOOL_CATEGORIES)
        self.assertIs(tool_catalog.categorize_tools, tool_catalog_core.categorize_tools)
        self.assertIs(tool_catalog.suggest_tool_names, tool_catalog_core.suggest_tool_names)
        self.assertIs(tool_catalog.tool_category, tool_catalog_core.tool_category)
        self.assertIs(tool_catalog.tool_requires_approval, tool_catalog_core.tool_requires_approval)
        self.assertIs(tool_catalog.get_tool_search_report, tool_catalog_search.get_tool_search_report)
        self.assertIs(tool_catalog.get_tool_search_text, tool_catalog_search.get_tool_search_text)
        self.assertIs(tool_catalog.format_tool_search_report_text, tool_catalog_search.format_tool_search_report_text)

    def test_tool_search_matches_names_descriptions_and_properties(self) -> None:
        report = get_tool_search_report("verification", max_matches=10)
        names = [str(match["name"]) for match in report["matches"]]

        self.assertTrue(report["ok"])
        self.assertIn("session_verification", names)
        self.assertIn("run_session_verification", names)
        self.assertGreaterEqual(report["total"], len(names))
        self.assertFalse(report["truncated"])

    def test_tool_search_filters_category_and_approval(self) -> None:
        report = get_tool_search_report(
            "verification",
            max_matches=10,
            category="session",
            approval_required=False,
        )

        self.assertTrue(report["ok"])
        self.assertGreater(report["total"], 0)
        self.assertTrue(all(match["category"] == "session" for match in report["matches"]))
        self.assertTrue(all(not match["approvalRequired"] for match in report["matches"]))

    def test_tool_search_formats_usage_for_missing_query(self) -> None:
        report = get_tool_search_report("")

        self.assertFalse(report["ok"])
        self.assertEqual(format_tool_search_report_text(report), "Usage: /tool-search <query>")

    def test_tool_search_schema_category_enum_uses_shared_categories(self) -> None:
        tool = next(item for item in AGENT_TOOL_DEFINITIONS if item["name"] == "tool_search")
        schema = tool["input_schema"]
        properties = schema["properties"]
        category_schema = properties["category"]

        self.assertEqual(category_schema["enum"], list(valid_tool_categories()))

    def test_ask_user_is_a_read_only_session_control(self) -> None:
        report = get_tool_search_report("ask_user", max_matches=1)

        self.assertEqual(report["matches"][0]["category"], "session")
        self.assertFalse(report["matches"][0]["approvalRequired"])


if __name__ == "__main__":
    unittest.main()
