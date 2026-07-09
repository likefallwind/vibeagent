import unittest

from vibeagent.tool_definition_session_activity_reports import SESSION_ACTIVITY_REPORT_TOOL_DEFINITIONS
from vibeagent.tool_definition_session_output_reports import SESSION_OUTPUT_REPORT_TOOL_DEFINITIONS
from vibeagent.tool_definition_session_reports import SESSION_REPORT_TOOL_DEFINITIONS
from vibeagent.tool_definition_session_timeline import SESSION_TIMELINE_TOOL_DEFINITIONS


class SessionReportToolDefinitionTests(unittest.TestCase):
    def test_session_report_definitions_are_split_in_order(self) -> None:
        self.assertEqual(
            SESSION_REPORT_TOOL_DEFINITIONS,
            SESSION_TIMELINE_TOOL_DEFINITIONS
            + SESSION_OUTPUT_REPORT_TOOL_DEFINITIONS
            + SESSION_ACTIVITY_REPORT_TOOL_DEFINITIONS,
        )

    def test_session_report_definition_boundaries_remain_stable(self) -> None:
        self.assertEqual(SESSION_TIMELINE_TOOL_DEFINITIONS[0]["name"], "session_summary")
        self.assertEqual(SESSION_TIMELINE_TOOL_DEFINITIONS[-1]["name"], "session_search")
        self.assertEqual(SESSION_OUTPUT_REPORT_TOOL_DEFINITIONS[0]["name"], "session_commands")
        self.assertEqual(SESSION_OUTPUT_REPORT_TOOL_DEFINITIONS[-1]["name"], "session_output_diagnostics")
        self.assertEqual(SESSION_ACTIVITY_REPORT_TOOL_DEFINITIONS[0]["name"], "session_files")
        self.assertEqual(SESSION_ACTIVITY_REPORT_TOOL_DEFINITIONS[-1]["name"], "session_failures")

    def test_session_report_tool_names_remain_in_original_order(self) -> None:
        self.assertEqual(
            [tool["name"] for tool in SESSION_REPORT_TOOL_DEFINITIONS],
            [
                "session_summary",
                "session_plan",
                "session_transcript",
                "session_search",
                "session_commands",
                "session_output_contexts",
                "session_output_diagnostics",
                "session_files",
                "session_failures",
            ],
        )


if __name__ == "__main__":
    unittest.main()
