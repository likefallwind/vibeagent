from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from vibeagent import project_commands, project_symbol_commands


class ProjectSymbolCommandsTests(unittest.TestCase):
    def test_project_commands_keeps_symbol_command_exports(self) -> None:
        self.assertIs(project_commands.get_symbols_text, project_symbol_commands.get_symbols_text)
        self.assertIs(project_commands.get_symbols_report, project_symbol_commands.get_symbols_report)
        self.assertIs(project_commands.format_symbols_report_text, project_symbol_commands.format_symbols_report_text)
        self.assertIs(project_commands.format_serialized_symbol_file, project_symbol_commands.format_serialized_symbol_file)
        self.assertIs(project_commands.parse_symbols_paths, project_symbol_commands.parse_symbols_paths)
        self.assertIs(project_commands.serialize_symbol, project_symbol_commands.serialize_symbol)
        self.assertIs(project_commands.serialize_symbol_file, project_symbol_commands.serialize_symbol_file)

    def test_parse_symbols_paths_handles_strings_lists_and_invalid_paths(self) -> None:
        self.assertEqual(project_symbol_commands.parse_symbols_paths("src/app.py web/app.ts"), ["src/app.py", "web/app.ts"])
        self.assertEqual(project_symbol_commands.parse_symbols_paths(["src/app.py", "web/app.ts"]), ["src/app.py", "web/app.ts"])
        self.assertEqual(project_symbol_commands.parse_symbols_paths(None), [])
        with self.assertRaises(ValueError):
            project_symbol_commands.parse_symbols_paths([f"{index}.py" for index in range(21)])

    def test_symbols_report_serializes_python_typescript_and_missing_paths(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            (root / "src").mkdir()
            (root / "web").mkdir()
            (root / "src" / "app.py").write_text(
                "import os\n\nclass App:\n    def run(self):\n        return os.getcwd()\n",
                encoding="utf-8",
            )
            (root / "web" / "app.ts").write_text(
                "import React from 'react';\nexport function render() { return React.createElement('div'); }\n",
                encoding="utf-8",
            )

            report = project_symbol_commands.get_symbols_report(root, "src/app.py web/app.ts missing.py", max_symbols=20)
            text = project_symbol_commands.get_symbols_text(root, "src/app.py", max_symbols=20)
            usage = project_symbol_commands.get_symbols_report(root)

        self.assertFalse(report["ok"])
        self.assertEqual(report["files"]["ok"], 2)
        self.assertEqual(report["files"]["total"], 3)
        self.assertEqual(report["counts"], {"symbols": 3, "imports": 2})
        self.assertEqual(report["files"]["items"][0]["path"], "src/app.py")
        self.assertEqual(report["files"]["items"][0]["language"], "python")
        self.assertEqual(report["files"]["items"][0]["symbols"][0]["name"], "App")
        self.assertEqual(report["files"]["items"][1]["language"], "typescript")
        self.assertEqual(report["files"]["items"][1]["symbols"][0]["name"], "render")
        self.assertFalse(report["files"]["items"][2]["ok"])
        self.assertIn("Symbols:", text)
        self.assertFalse(usage["ok"])
        self.assertIn("Usage: /symbols", usage["message"])


if __name__ == "__main__":
    unittest.main()
