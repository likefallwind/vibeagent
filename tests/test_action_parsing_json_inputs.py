from __future__ import annotations

import unittest

from vibeagent import action_parsing_helpers
from vibeagent.action_parsing_json_inputs import (
    parse_json_patch_input,
    parse_json_pointer_action_input,
    parse_json_set_input,
)
from vibeagent.action_parsing_scalars import ActionParseError
from vibeagent.types import JsonPatchOperation


class ActionParsingJsonInputsTests(unittest.TestCase):
    def test_helpers_reexport_json_input_parsers(self) -> None:
        self.assertIs(action_parsing_helpers.parse_json_set_input, parse_json_set_input)
        self.assertIs(action_parsing_helpers.parse_json_pointer_action_input, parse_json_pointer_action_input)
        self.assertIs(action_parsing_helpers.parse_json_patch_input, parse_json_patch_input)

    def test_parse_json_set_input_returns_value_and_create_missing(self) -> None:
        self.assertEqual(
            parse_json_set_input(
                {
                    "path": " package.json ",
                    "pointer": " /scripts/test ",
                    "value": "pytest",
                    "create_missing": True,
                },
                "raw",
                "json_set",
            ),
            ("package.json", "/scripts/test", "pytest", True),
        )

    def test_parse_json_patch_input_parses_supported_operations(self) -> None:
        self.assertEqual(
            parse_json_patch_input(
                {
                    "path": "package.json",
                    "operations": [
                        {"op": "add", "path": " /scripts/dev ", "value": "vite"},
                        {"op": "remove", "path": "/private"},
                    ],
                },
                "raw",
                "json_patch",
            ),
            (
                "package.json",
                [
                    JsonPatchOperation(op="add", path="/scripts/dev", value="vite"),
                    JsonPatchOperation(op="remove", path="/private", value=None),
                ],
            ),
        )

    def test_parse_json_inputs_reject_invalid_values(self) -> None:
        with self.assertRaisesRegex(ActionParseError, "requires value"):
            parse_json_set_input({"path": "package.json", "pointer": "/private"}, "raw", "json_set")
        with self.assertRaisesRegex(ActionParseError, "unsupported op"):
            parse_json_patch_input(
                {"path": "package.json", "operations": [{"op": "move", "path": "/x"}]},
                "raw",
                "json_patch",
            )
        with self.assertRaisesRegex(ActionParseError, "requires value"):
            parse_json_patch_input(
                {"path": "package.json", "operations": [{"op": "replace", "path": "/x"}]},
                "raw",
                "json_patch",
            )


if __name__ == "__main__":
    unittest.main()
