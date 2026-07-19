import argparse
import unittest

from vibeagent import cli as cli_module


class CliSessionKwargsTests(unittest.TestCase):
    def test_session_kwargs_helpers_keep_cli_option_mapping(self) -> None:
        args = argparse.Namespace(
            session_transcript_event_max=12,
            session_max_text=500,
            session_search_match_max=7,
            session_search_case_sensitive=True,
            session_max_commands=3,
            session_max_output_chars=1000,
            session_output_command_max=4,
            session_output_max_chars=1200,
            session_output_context_lines=2,
            session_output_context_max=5,
            session_output_context_max_bytes=800,
            session_output_diagnostic_max=6,
            session_max_files=9,
            session_max_failures=10,
            session_max_checks=11,
            run_timeout_ms=1500,
            run_max_chars=2000,
            run_session_no_failed=True,
            run_session_no_pending=False,
            run_continue_on_failure=True,
            run_output_contexts=True,
            run_output_diagnostics=True,
            run_output_context_lines=2,
            run_output_diagnostic_max=6,
            run_output_context_max=5,
            run_output_context_max_bytes=800,
        )

        self.assertEqual(cli_module.session_transcript_kwargs(args), {"max_events": 12, "max_text": 500})
        self.assertEqual(
            cli_module.session_search_kwargs(args),
            {"max_matches": 7, "max_text": 500, "case_sensitive": True},
        )
        self.assertEqual(cli_module.session_commands_kwargs(args), {"max_commands": 3, "max_output_chars": 1000})
        self.assertEqual(
            cli_module.session_output_contexts_kwargs(args),
            {
                "max_commands": 4,
                "max_output_chars": 1200,
                "context_lines": 2,
                "max_contexts": 5,
                "max_bytes_per_context": 800,
            },
        )
        self.assertEqual(
            cli_module.session_output_diagnostics_kwargs(args),
            {
                "max_commands": 4,
                "max_output_chars": 1200,
                "context_lines": 2,
                "max_contexts": 5,
                "max_bytes_per_context": 800,
                "max_diagnostics": 6,
            },
        )
        self.assertEqual(cli_module.session_files_kwargs(args), {"max_files": 9})
        self.assertEqual(cli_module.session_failures_kwargs(args), {"max_failures": 10, "max_text": 500})
        self.assertEqual(cli_module.session_verification_kwargs(args), {"max_checks": 11})
        self.assertEqual(
            cli_module.run_session_verification_kwargs(args),
            {
                "max_checks": 11,
                "timeout_ms": 1500,
                "max_output_chars": 2000,
                "extract_output_contexts": True,
                "extract_output_diagnostics": True,
                "context_lines": 2,
                "max_diagnostics": 6,
                "max_contexts": 5,
                "max_bytes_per_context": 800,
                "include_failed": False,
                "stop_on_failure": False,
            },
        )
        self.assertEqual(
            cli_module.session_audit_kwargs(args),
            {
                "max_failures": 10,
                "max_files": 9,
                "max_commands": 3,
                "max_checks": 11,
                "max_text": 500,
            },
        )
        self.assertEqual(
            cli_module.session_handoff_kwargs(args),
            {
                "max_failures": 10,
                "max_files": 9,
                "max_commands": 3,
                "max_checks": 11,
                "max_output_chars": 1000,
                "max_text": 500,
            },
        )

    def test_session_kwargs_helpers_omit_unset_optional_values(self) -> None:
        args = argparse.Namespace(
            session_transcript_event_max=None,
            session_max_text=None,
            session_search_match_max=None,
            session_search_case_sensitive=False,
            session_max_commands=None,
            session_max_output_chars=None,
            session_output_command_max=20,
            session_output_max_chars=4000,
            session_output_context_lines=2,
            session_output_context_max=10,
            session_output_context_max_bytes=12000,
            session_output_diagnostic_max=10,
            session_max_files=None,
            session_max_failures=None,
            session_max_checks=None,
            run_timeout_ms=30000,
            run_max_chars=12000,
            run_session_no_failed=False,
            run_session_no_pending=False,
            run_continue_on_failure=False,
            run_output_contexts=False,
            run_output_diagnostics=False,
            run_output_context_lines=5,
            run_output_diagnostic_max=50,
            run_output_context_max=20,
            run_output_context_max_bytes=20000,
        )

        self.assertEqual(cli_module.session_transcript_kwargs(args), {})
        self.assertEqual(cli_module.session_search_kwargs(args), {})
        self.assertEqual(cli_module.session_commands_kwargs(args), {})
        self.assertEqual(cli_module.session_files_kwargs(args), {})
        self.assertEqual(cli_module.session_failures_kwargs(args), {})
        self.assertEqual(cli_module.session_verification_kwargs(args), {})
        self.assertEqual(
            cli_module.run_session_verification_kwargs(args),
            {
                "timeout_ms": 30000,
                "max_output_chars": 12000,
                "extract_output_contexts": False,
                "extract_output_diagnostics": False,
                "context_lines": 5,
                "max_diagnostics": 50,
                "max_contexts": 20,
                "max_bytes_per_context": 20000,
            },
        )
        self.assertEqual(cli_module.session_audit_kwargs(args), {})
        self.assertEqual(cli_module.session_handoff_kwargs(args), {})
        self.assertEqual(
            cli_module.session_output_contexts_kwargs(args),
            {
                "max_commands": 20,
                "max_output_chars": 4000,
                "context_lines": 2,
                "max_contexts": 10,
                "max_bytes_per_context": 12000,
            },
        )


if __name__ == "__main__":
    unittest.main()
