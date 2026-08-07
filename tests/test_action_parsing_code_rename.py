import unittest

from vibeagent.action_parsing_code_intel import parse_code_intel_action
from vibeagent.action_parsing_code_rename import (
    parse_code_rename_action,
    parse_python_rename_action,
    parse_replace_python_definition_action,
)
from vibeagent.types import CodeRenameAction, PythonRenamePreviewAction, ReplacePythonDefinitionAction


class ActionParsingCodeRenameTests(unittest.TestCase):
    def test_code_rename_helper_matches_code_intel_entrypoint(self) -> None:
        payload = {
            "symbol": "runAgent",
            "new_name": "executeAgent",
            "path": "src",
            "max_files": 3,
            "max_replacements": 4,
        }

        helper = parse_code_rename_action("code_rename", payload, "raw")
        entrypoint = parse_code_intel_action("code_rename", payload, "raw")

        self.assertEqual(helper, entrypoint)
        self.assertIsInstance(entrypoint, CodeRenameAction)

    def test_python_rename_helper_matches_code_intel_entrypoint(self) -> None:
        payload = {"symbol": "run_agent", "new_name": "execute_agent", "max_replacements": 7}

        helper = parse_python_rename_action("python_rename_preview", payload, "raw")
        entrypoint = parse_code_intel_action("python_rename_preview", payload, "raw")

        self.assertEqual(helper, entrypoint)
        self.assertIsInstance(entrypoint, PythonRenamePreviewAction)

    def test_replace_definition_helper_matches_code_intel_entrypoint(self) -> None:
        payload = {"symbol": "Runner.run", "content": "def run(self):\n    return 1\n", "path": "app.py"}

        helper = parse_replace_python_definition_action("replace_python_definition", payload, "raw")
        entrypoint = parse_code_intel_action("replace_python_definition", payload, "raw")

        self.assertEqual(helper, entrypoint)
        self.assertIsInstance(entrypoint, ReplacePythonDefinitionAction)


if __name__ == "__main__":
    unittest.main()
