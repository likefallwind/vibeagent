from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from types import SimpleNamespace
import unittest

from vibeagent.smart_code_common import format_rename_report_text, plain_data, rename_observation_report


@dataclass
class NestedValue:
    name: str


class SmartCodeCommonTests(unittest.TestCase):
    def test_plain_data_serializes_nested_dataclasses(self) -> None:
        value = SimpleNamespace(name="not-dataclass")
        self.assertIs(plain_data(value), value)
        self.assertEqual(plain_data({"item": NestedValue(name="demo")}), {"item": {"name": "demo"}})

    def test_rename_observation_report_serializes_files_and_formatter(self) -> None:
        observation = SimpleNamespace(
            ok=True,
            symbol="runAgent",
            new_name="executeAgent",
            path="web",
            files=[
                {
                    "path": "web/app.ts",
                    "language": "typescript",
                    "truncated": False,
                    "replacements": [
                        {
                            "line": 1,
                            "column": 7,
                            "end_column": 15,
                            "old": "runAgent",
                            "new": "executeAgent",
                            "context": "const runAgent = () => null",
                            "language": "typescript",
                        }
                    ],
                }
            ],
            total_files=1,
            total_replacements=1,
            truncated=False,
            errors=[],
            diff="diff --git a/web/app.ts b/web/app.ts",
            message="Preview ready.",
        )
        report = rename_observation_report(Path("/repo"), observation, max_files=10, max_replacements=20)
        text = format_rename_report_text("Code rename preview:", report, include_language=True)

        self.assertEqual(report["totalReplacements"], 1)
        self.assertIn("Code rename preview:", text)
        self.assertIn("runAgent -> executeAgent", text)
        self.assertIn("typescript: runAgent -> executeAgent", text)


if __name__ == "__main__":
    unittest.main()
