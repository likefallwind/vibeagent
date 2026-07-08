import unittest

from vibeagent import session_audit_reports
from vibeagent import session_audit_serialization


class SessionAuditSerializationTests(unittest.TestCase):
    def test_session_audit_reports_reexports_serialization_helpers(self) -> None:
        self.assertIs(
            session_audit_reports.validate_session_audit_limits,
            session_audit_serialization.validate_session_audit_limits,
        )
        self.assertIs(
            session_audit_reports.validate_session_handoff_limits,
            session_audit_serialization.validate_session_handoff_limits,
        )
        self.assertIs(
            session_audit_reports.serialize_session_failure,
            session_audit_serialization.serialize_session_failure,
        )
        self.assertIs(
            session_audit_reports.serialize_session_command_entry,
            session_audit_serialization.serialize_session_command_entry,
        )
        self.assertIs(
            session_audit_reports.failed_checkpoint_create_count,
            session_audit_serialization.failed_checkpoint_create_count,
        )


if __name__ == "__main__":
    unittest.main()
