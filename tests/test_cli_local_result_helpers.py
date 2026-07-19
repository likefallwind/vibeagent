import argparse
import io
import json
import unittest
from unittest.mock import patch

from vibeagent import MACHINE_OUTPUT_SCHEMA_VERSION, __version__, cli as cli_module
from vibeagent.cli import format_error
from vibeagent.cli_exit_codes import has_incomplete_count_failure
from vibeagent.cli_local_flag_detection import LOCAL_FLAG_ARG_NAMES


class Http401Error(Exception):
    status = 401


class CliLocalResultHelpersTests(unittest.TestCase):
    def test_local_result_exit_code_covers_local_result_flags(self) -> None:
        self.assertEqual(LOCAL_FLAG_ARG_NAMES - cli_module.LOCAL_RESULT_ARG_NAMES, set())
        self.assertEqual(cli_module.LOCAL_RESULT_ARG_NAMES - LOCAL_FLAG_ARG_NAMES, set())

    def test_incomplete_count_failure_maps_selected_flags_to_count_fields(self) -> None:
        cases = [
            ("read_files", "Read files:\n  files: 1/2", True),
            ("output_contexts", "Output contexts:\n  contexts: 0/1", True),
            ("image_info", "Image info:\n  images: 2/2", False),
            ("symbols", "Symbols:\n  files: 3/4", True),
        ]

        for arg_name, text, expected in cases:
            with self.subTest(arg_name=arg_name):
                args = argparse.Namespace(**{arg_name: object()})
                self.assertIs(has_incomplete_count_failure(args, text), expected)

        self.assertFalse(
            has_incomplete_count_failure(
                argparse.Namespace(read_files=None),
                "Read files:\n  files: 1/2",
            )
        )

    def test_emit_local_result_sets_failed_status_for_local_errors(self) -> None:
        args = argparse.Namespace(json=True, tool="missing")

        with patch("sys.stdout", new_callable=io.StringIO) as stdout:
            exit_code = cli_module.emit_local_result(args, "Tool not found: missing", {"tool": {"ok": False}})

        payload = json.loads(stdout.getvalue())
        self.assertEqual(exit_code, 1)
        self.assertFalse(payload["success"])
        self.assertEqual(payload["schemaVersion"], MACHINE_OUTPUT_SCHEMA_VERSION)
        self.assertEqual(payload["version"], __version__)
        self.assertEqual(payload["exitCode"], 1)
        self.assertEqual(payload["exit_code"], 1)
        self.assertEqual(payload["status"], "failed")
        self.assertEqual(payload["stopReason"], "failed")
        self.assertEqual(payload["stop_reason"], "failed")
        self.assertEqual(payload["tool"], {"ok": False})

    def test_format_error_uses_provider_neutral_401_guidance(self) -> None:
        text = format_error(Http401Error("unauthorized"))

        self.assertIn("unauthorized", text)
        self.assertIn("configured model provider rejected the API key", text)
        self.assertIn("Check /model", text)
        self.assertNotIn("MiniMax rejected", text)
        self.assertNotIn("DEEPSEEK_API_KEY", text)

    def test_format_error_returns_plain_error_for_other_errors(self) -> None:
        self.assertEqual(format_error(ValueError("bad")), "bad")


if __name__ == "__main__":
    unittest.main()
