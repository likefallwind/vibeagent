import unittest

from vibeagent.tool_definition_python_calls import PYTHON_CALL_TOOL_DEFINITIONS
from vibeagent.tool_definition_python_code import PYTHON_CODE_TOOL_DEFINITIONS
from vibeagent.tool_definition_python_definitions import PYTHON_DEFINITION_TOOL_DEFINITIONS
from vibeagent.tool_definition_python_references import PYTHON_REFERENCE_TOOL_DEFINITIONS
from vibeagent.tool_definition_python_rename import PYTHON_RENAME_TOOL_DEFINITIONS


class PythonCodeToolDefinitionTests(unittest.TestCase):
    def test_python_code_definitions_are_split_in_order(self) -> None:
        self.assertEqual(
            PYTHON_CODE_TOOL_DEFINITIONS,
            PYTHON_DEFINITION_TOOL_DEFINITIONS
            + PYTHON_CALL_TOOL_DEFINITIONS
            + PYTHON_REFERENCE_TOOL_DEFINITIONS
            + PYTHON_RENAME_TOOL_DEFINITIONS,
        )

    def test_python_code_definition_boundaries_remain_stable(self) -> None:
        self.assertEqual(PYTHON_DEFINITION_TOOL_DEFINITIONS[0]["name"], "python_definitions")
        self.assertEqual(PYTHON_DEFINITION_TOOL_DEFINITIONS[-1]["name"], "replace_python_definition")
        self.assertEqual(PYTHON_CALL_TOOL_DEFINITIONS[0]["name"], "python_calls")
        self.assertEqual(PYTHON_CALL_TOOL_DEFINITIONS[-1]["name"], "python_call_graph")
        self.assertEqual(PYTHON_REFERENCE_TOOL_DEFINITIONS[0]["name"], "python_references")
        self.assertEqual(PYTHON_REFERENCE_TOOL_DEFINITIONS[-1]["name"], "python_reference_contexts")
        self.assertEqual(PYTHON_RENAME_TOOL_DEFINITIONS[0]["name"], "python_rename_preview")
        self.assertEqual(PYTHON_RENAME_TOOL_DEFINITIONS[-1]["name"], "python_rename")

    def test_python_code_tool_names_remain_in_original_order(self) -> None:
        self.assertEqual(
            [tool["name"] for tool in PYTHON_CODE_TOOL_DEFINITIONS],
            [
                "python_definitions",
                "check_replace_python_definition",
                "replace_python_definition",
                "python_calls",
                "python_call_graph",
                "python_references",
                "python_reference_contexts",
                "python_rename_preview",
                "python_rename",
            ],
        )


if __name__ == "__main__":
    unittest.main()
