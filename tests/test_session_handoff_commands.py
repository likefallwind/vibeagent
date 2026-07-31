import unittest

from vibeagent import session, session_handoff_commands


class SessionHandoffCommandsTests(unittest.TestCase):
    def test_session_module_reexports_handoff_helpers(self) -> None:
        self.assertIs(session.format_session_handoff, session_handoff_commands.format_session_handoff)
        self.assertIs(session.build_session_audit_report, session_handoff_commands.build_session_audit_report)
        self.assertIs(session.build_session_handoff_report, session_handoff_commands.build_session_handoff_report)
        self.assertIs(session.format_session_audit, session_handoff_commands.format_session_audit)
        self.assertIs(session.format_session_verification, session_handoff_commands.format_session_verification)
        self.assertIs(
            session.build_session_verification_report,
            session_handoff_commands.build_session_verification_report,
        )
        self.assertIs(session.build_session_resume_context, session_handoff_commands.build_session_resume_context)


if __name__ == "__main__":
    unittest.main()
