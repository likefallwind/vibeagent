from __future__ import annotations

import unittest
from pathlib import Path
from unittest.mock import patch

from vibeagent import process_commands, process_output_runtime, process_runtime
from vibeagent.process_output_commands import (
    format_process_output_contexts_report_text,
    format_process_output_diagnostics_report_text,
    get_process_output_contexts_report,
    get_process_output_contexts_text,
    get_process_output_diagnostics_report,
    get_process_output_diagnostics_text,
    parse_process_request,
)


class ProcessOutputCommandModuleTests(unittest.TestCase):
    def test_process_commands_reexports_output_helpers(self) -> None:
        self.assertIs(process_commands.get_process_output_contexts_report, get_process_output_contexts_report)
        self.assertIs(process_commands.get_process_output_contexts_text, get_process_output_contexts_text)
        self.assertIs(process_commands.format_process_output_contexts_report_text, format_process_output_contexts_report_text)
        self.assertIs(process_commands.get_process_output_diagnostics_report, get_process_output_diagnostics_report)
        self.assertIs(process_commands.get_process_output_diagnostics_text, get_process_output_diagnostics_text)
        self.assertIs(process_commands.format_process_output_diagnostics_report_text, format_process_output_diagnostics_report_text)
        self.assertIs(process_commands.parse_process_request, parse_process_request)

    def test_process_runtime_reexports_output_runtime_helpers(self) -> None:
        self.assertIs(
            process_runtime.read_background_process_output_contexts,
            process_output_runtime.read_background_process_output_contexts,
        )
        self.assertIs(
            process_runtime.read_background_process_output_diagnostics,
            process_output_runtime.read_background_process_output_diagnostics,
        )

    def test_text_helpers_resolve_compatibility_patch_targets(self) -> None:
        root = Path(".").resolve()
        contexts_report = {"ok": True, "message": "contexts"}
        diagnostics_report = {"ok": True, "message": "diagnostics"}
        with (
            patch("vibeagent.process_commands.get_process_output_contexts_report", return_value=contexts_report) as get_contexts,
            patch("vibeagent.process_commands.format_process_output_contexts_report_text", return_value="contexts rendered") as format_contexts,
            patch("vibeagent.process_commands.get_process_output_diagnostics_report", return_value=diagnostics_report) as get_diagnostics,
            patch("vibeagent.process_commands.format_process_output_diagnostics_report_text", return_value="diagnostics rendered") as format_diagnostics,
        ):
            self.assertEqual(
                get_process_output_contexts_text(root, "bg-1", max_output_chars=2_000),
                "contexts rendered",
            )
            self.assertEqual(
                get_process_output_contexts_text(root, "bg-2"),
                "contexts rendered",
            )
            self.assertEqual(
                get_process_output_diagnostics_text(root, "bg-1", max_output_chars=2_000),
                "diagnostics rendered",
            )
            self.assertEqual(
                get_process_output_diagnostics_text(root, "bg-2"),
                "diagnostics rendered",
            )

        self.assertEqual(
            get_contexts.call_args_list[0].args,
            (root, "bg-1", None, 2_000, 5, 20, 20_000),
        )
        self.assertEqual(
            get_contexts.call_args_list[1].args,
            (root, "bg-2", None, None, 5, 20, 20_000),
        )
        self.assertEqual(format_contexts.call_count, 2)
        self.assertEqual(
            get_diagnostics.call_args_list[0].args,
            (root, "bg-1", None, 2_000, 2, 50, 20, 20_000),
        )
        self.assertEqual(
            get_diagnostics.call_args_list[1].args,
            (root, "bg-2", None, None, 2, 50, 20, 20_000),
        )
        self.assertEqual(format_diagnostics.call_count, 2)

    def test_parse_process_request_preserves_unspecified_max_chars(self) -> None:
        self.assertEqual(parse_process_request("bg-1"), ("bg-1", None))
        self.assertEqual(parse_process_request("bg-1 2000"), ("bg-1", 2000))
        self.assertEqual(parse_process_request(process_id="bg-1", max_output_chars=3000), ("bg-1", 3000))


if __name__ == "__main__":
    unittest.main()
