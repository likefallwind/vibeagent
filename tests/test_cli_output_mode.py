from __future__ import annotations

import unittest

from vibeagent.cli_output_mode import CliOutputMode, resolve_cli_output_mode


class CliOutputModeTests(unittest.TestCase):
    def test_json_flag_selects_machine_json_output(self) -> None:
        self.assertEqual(
            resolve_cli_output_mode(output_json=True, output_format=None),
            CliOutputMode(format="json", machine=True, stream_json=False),
        )

    def test_explicit_output_format_overrides_json_flag(self) -> None:
        self.assertEqual(
            resolve_cli_output_mode(output_json=True, output_format="stream-json"),
            CliOutputMode(format="stream-json", machine=True, stream_json=True),
        )
        self.assertEqual(
            resolve_cli_output_mode(output_json=True, output_format="text"),
            CliOutputMode(format="text", machine=False, stream_json=False),
        )

    def test_default_text_output_is_not_machine_output(self) -> None:
        self.assertEqual(
            resolve_cli_output_mode(output_json=False, output_format=None),
            CliOutputMode(format="text", machine=False, stream_json=False),
        )


if __name__ == "__main__":
    unittest.main()
