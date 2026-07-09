import unittest

from vibeagent.tool_definition_session_readiness import SESSION_READINESS_TOOL_DEFINITIONS
from vibeagent.tool_definition_session_verification import SESSION_VERIFICATION_TOOL_DEFINITIONS
from vibeagent.tool_definition_session_verification_checks import SESSION_VERIFICATION_CHECK_TOOL_DEFINITIONS


class SessionVerificationToolDefinitionTests(unittest.TestCase):
    def test_session_verification_definitions_are_split_in_order(self) -> None:
        self.assertEqual(
            SESSION_VERIFICATION_TOOL_DEFINITIONS,
            SESSION_VERIFICATION_CHECK_TOOL_DEFINITIONS
            + SESSION_READINESS_TOOL_DEFINITIONS,
        )

    def test_session_verification_definition_boundaries_remain_stable(self) -> None:
        self.assertEqual(SESSION_VERIFICATION_CHECK_TOOL_DEFINITIONS[0]["name"], "session_verification")
        self.assertEqual(SESSION_VERIFICATION_CHECK_TOOL_DEFINITIONS[-1]["name"], "run_session_verification")
        self.assertEqual(SESSION_READINESS_TOOL_DEFINITIONS[0]["name"], "session_audit")
        self.assertEqual(SESSION_READINESS_TOOL_DEFINITIONS[-1]["name"], "session_handoff")

    def test_session_verification_tool_names_remain_in_original_order(self) -> None:
        self.assertEqual(
            [tool["name"] for tool in SESSION_VERIFICATION_TOOL_DEFINITIONS],
            [
                "session_verification",
                "run_session_verification",
                "session_audit",
                "session_handoff",
            ],
        )


if __name__ == "__main__":
    unittest.main()
