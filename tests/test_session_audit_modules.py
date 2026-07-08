import unittest

from vibeagent import session_audit_readiness
from vibeagent import session_audit_reports
from vibeagent import session_audit_text


class SessionAuditModuleTests(unittest.TestCase):
    def test_session_audit_reports_reexports_readiness_helpers(self) -> None:
        self.assertIs(
            session_audit_reports.session_pending_plan_items,
            session_audit_readiness.session_pending_plan_items,
        )
        self.assertIs(
            session_audit_reports.session_audit_blockers,
            session_audit_readiness.session_audit_blockers,
        )
        self.assertIs(
            session_audit_reports.session_audit_denied_approval_blocker_count,
            session_audit_readiness.session_audit_denied_approval_blocker_count,
        )

    def test_session_audit_reports_reexports_text_helpers(self) -> None:
        self.assertIs(
            session_audit_reports.format_session_handoff_sections,
            session_audit_text.format_session_handoff_sections,
        )
        self.assertIs(
            session_audit_reports.format_session_handoff_readiness,
            session_audit_text.format_session_handoff_readiness,
        )
        self.assertIs(
            session_audit_reports.format_session_audit_from_parts,
            session_audit_text.format_session_audit_from_parts,
        )


if __name__ == "__main__":
    unittest.main()
