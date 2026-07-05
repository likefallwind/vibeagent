from __future__ import annotations

import unittest

from vibeagent.tool_definition_checkpoints import CHECKPOINT_TOOL_DEFINITIONS
from vibeagent.tool_definition_session_reports import SESSION_REPORT_TOOL_DEFINITIONS
from vibeagent.tool_definition_session_verification import SESSION_VERIFICATION_TOOL_DEFINITIONS
from vibeagent.tool_definition_sessions import SESSION_TOOL_DEFINITIONS


class SessionToolDefinitionTests(unittest.TestCase):
    def test_session_definitions_are_split_in_order(self) -> None:
        self.assertEqual(
            SESSION_TOOL_DEFINITIONS,
            SESSION_REPORT_TOOL_DEFINITIONS + SESSION_VERIFICATION_TOOL_DEFINITIONS + CHECKPOINT_TOOL_DEFINITIONS,
        )

    def test_session_definition_boundaries_remain_stable(self) -> None:
        self.assertEqual(SESSION_REPORT_TOOL_DEFINITIONS[0]["name"], "session_summary")
        self.assertEqual(SESSION_REPORT_TOOL_DEFINITIONS[-1]["name"], "session_failures")
        self.assertEqual(SESSION_VERIFICATION_TOOL_DEFINITIONS[0]["name"], "session_verification")
        self.assertEqual(SESSION_VERIFICATION_TOOL_DEFINITIONS[-1]["name"], "session_handoff")
        self.assertEqual(CHECKPOINT_TOOL_DEFINITIONS[0]["name"], "checkpoint_create")
        self.assertEqual(CHECKPOINT_TOOL_DEFINITIONS[-1]["name"], "checkpoint_prune")


if __name__ == "__main__":
    unittest.main()
