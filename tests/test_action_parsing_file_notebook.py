import unittest

from vibeagent.action_parsing_file_notebook import parse_file_notebook_action
from vibeagent.action_parsing_helpers import ActionParseError
from vibeagent.types import CheckNotebookEditAction, NotebookEditAction


class ActionParsingFileNotebookTests(unittest.TestCase):
    def test_parse_file_notebook_action_parses_cell_id_action(self) -> None:
        checked = parse_file_notebook_action(
            "check_notebook_edit",
            {"path": "analysis.ipynb", "new_source": "print('ok')", "cell_id": "abc", "cell_type": "code"},
            "{}",
        )

        self.assertEqual(
            checked,
            CheckNotebookEditAction(
                type="check_notebook_edit",
                path="analysis.ipynb",
                new_source="print('ok')",
                cell_id="abc",
                cell_number=None,
                cell_type="code",
            ),
        )

    def test_parse_file_notebook_action_parses_cell_number_action(self) -> None:
        edited = parse_file_notebook_action(
            "notebook_edit",
            {"path": "analysis.ipynb", "new_source": "print('ok')", "cell_number": "2"},
            "{}",
        )

        self.assertEqual(
            edited,
            NotebookEditAction(
                type="notebook_edit",
                path="analysis.ipynb",
                new_source="print('ok')",
                cell_id=None,
                cell_number=2,
                cell_type=None,
            ),
        )

    def test_parse_file_notebook_action_returns_none_for_other_actions(self) -> None:
        self.assertIsNone(parse_file_notebook_action("write_file", {"path": "app.py"}, "{}"))

    def test_parse_file_notebook_action_preserves_validation_errors(self) -> None:
        with self.assertRaisesRegex(ActionParseError, "check_notebook_edit action requires cell_id or cell_number"):
            parse_file_notebook_action("check_notebook_edit", {"path": "analysis.ipynb", "new_source": "x"}, "{}")

        with self.assertRaisesRegex(ActionParseError, "notebook_edit action cell_id must be a string"):
            parse_file_notebook_action("notebook_edit", {"path": "analysis.ipynb", "new_source": "x", "cell_id": 1}, "{}")


if __name__ == "__main__":
    unittest.main()
