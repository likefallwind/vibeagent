from __future__ import annotations

import unittest

from vibeagent import local_http_commands, local_http_parsing, local_http_reports, local_runtime_commands


class LocalHttpCommandModuleTests(unittest.TestCase):
    def test_local_runtime_keeps_http_and_port_exports(self) -> None:
        self.assertIs(local_runtime_commands.get_port_text, local_http_commands.get_port_text)
        self.assertIs(local_runtime_commands.get_port_report, local_http_commands.get_port_report)
        self.assertIs(local_runtime_commands.format_port_report_text, local_http_commands.format_port_report_text)
        self.assertIs(local_runtime_commands.parse_port_request, local_http_commands.parse_port_request)
        self.assertIs(local_runtime_commands.get_http_text, local_http_commands.get_http_text)
        self.assertIs(local_runtime_commands.get_http_report, local_http_commands.get_http_report)
        self.assertIs(local_runtime_commands.format_http_report_text, local_http_commands.format_http_report_text)
        self.assertIs(local_runtime_commands.serialize_http_report, local_http_commands.serialize_http_report)
        self.assertIs(local_runtime_commands.get_http_fetch_text, local_http_commands.get_http_fetch_text)
        self.assertIs(local_runtime_commands.get_http_fetch_report, local_http_commands.get_http_fetch_report)
        self.assertIs(local_runtime_commands.format_http_fetch_report_text, local_http_commands.format_http_fetch_report_text)
        self.assertIs(local_runtime_commands.parse_http_fetch_request, local_http_commands.parse_http_fetch_request)
        self.assertIs(local_runtime_commands.parse_http_request, local_http_commands.parse_http_request)
        self.assertIs(local_http_commands.parse_port_request, local_http_parsing.parse_port_request)
        self.assertIs(local_http_commands.parse_http_fetch_request, local_http_parsing.parse_http_fetch_request)
        self.assertIs(local_http_commands.parse_http_request, local_http_parsing.parse_http_request)

    def test_http_report_formatting_lives_in_report_module(self) -> None:
        self.assertIs(local_http_commands.format_port_report_text, local_http_reports.format_port_report_text)
        self.assertIs(local_http_commands.format_http_report_text, local_http_reports.format_http_report_text)
        self.assertIs(local_http_commands.serialize_http_report, local_http_reports.serialize_http_report)
        self.assertIs(local_http_commands.format_http_fetch_report_text, local_http_reports.format_http_fetch_report_text)

    def test_parsers_keep_validation_behavior(self) -> None:
        self.assertEqual(local_http_commands.parse_port_request("8080 127.0.0.1 200"), (8080, "127.0.0.1", 200))
        self.assertEqual(local_http_commands.parse_http_request("https://example.com ready"), ("https://example.com", "ready"))
        self.assertEqual(local_http_commands.parse_http_fetch_request("https://example.com"), "https://example.com")
        with self.assertRaisesRegex(ValueError, "port must be between 1 and 65535"):
            local_http_commands.parse_port_request("70000")
        with self.assertRaisesRegex(ValueError, "url must be an http or https URL"):
            local_http_commands.parse_http_request("ftp://example.com")


if __name__ == "__main__":
    unittest.main()
