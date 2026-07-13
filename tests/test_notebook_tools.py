from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from vibeagent.action_parsing import parse_tool_action
from vibeagent.actions import execute_action
from vibeagent.agent_approval_preview import approval_preview_summary
from vibeagent.prompts import format_observations
from vibeagent.types import NotebookEditAction, NotebookReadAction
from vibeagent.workspace import create_run_workspace


def write_notebook(path: Path) -> None:
    path.write_text(
        json.dumps(
            {
                "cells": [
                    {
                        "cell_type": "markdown",
                        "id": "intro",
                        "metadata": {},
                        "source": ["# Title\n", "notes\n"],
                    },
                    {
                        "cell_type": "code",
                        "execution_count": 3,
                        "id": "calc",
                        "metadata": {},
                        "outputs": [{"output_type": "stream", "text": ["4\n"]}],
                        "source": ["value = 1 + 1\n", "value\n"],
                    },
                ],
                "metadata": {},
                "nbformat": 4,
                "nbformat_minor": 5,
            },
            indent=1,
        )
        + "\n",
        encoding="utf-8",
    )


class NotebookToolTests(unittest.TestCase):
    def test_notebook_read_returns_structured_cell_summaries(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-notebook-") as base:
            root = Path(base)
            write_notebook(root / "analysis.ipynb")
            action = parse_tool_action("NotebookRead", {"notebook_path": "analysis.ipynb", "offset": 0, "limit": 2})

            observation = execute_action(create_run_workspace(root), action)

        self.assertIsInstance(action, NotebookReadAction)
        self.assertEqual(observation.kind, "notebook_read")
        self.assertTrue(observation.ok)
        self.assertEqual(observation.total_cells, 2)
        self.assertEqual(observation.cells[0].cell_id, "intro")
        self.assertEqual(observation.cells[0].cell_type, "markdown")
        self.assertIn("# Title", observation.cells[0].source)
        self.assertEqual(observation.cells[1].execution_count, 3)
        self.assertIn("cell 2 id=calc type=code", format_observations([observation]))

    def test_notebook_edit_replaces_target_cell_source(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-notebook-") as base:
            root = Path(base)
            notebook_path = root / "analysis.ipynb"
            write_notebook(notebook_path)
            action = parse_tool_action(
                "NotebookEdit",
                {
                    "notebook_path": "analysis.ipynb",
                    "cell_id": "calc",
                    "new_source": "value = 2 + 3\nvalue\n",
                    "cell_type": "code",
                },
            )

            observation = execute_action(create_run_workspace(root), action)
            updated = json.loads(notebook_path.read_text(encoding="utf-8"))

        self.assertIsInstance(action, NotebookEditAction)
        self.assertEqual(observation.kind, "notebook_edit")
        self.assertTrue(observation.ok)
        self.assertEqual(observation.cell_number, 2)
        self.assertEqual(observation.cell_id, "calc")
        self.assertEqual(updated["cells"][1]["source"], ["value = 2 + 3\n", "value\n"])
        self.assertIn("+    \"value = 2 + 3\\n\"", observation.diff)

    def test_check_notebook_edit_previews_without_writing_and_matches_approval_preview(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-notebook-") as base:
            root = Path(base)
            notebook_path = root / "analysis.ipynb"
            write_notebook(notebook_path)
            before = notebook_path.read_text(encoding="utf-8")
            preview_action = parse_tool_action(
                "check_notebook_edit",
                {
                    "path": "analysis.ipynb",
                    "cell_number": 2,
                    "new_source": "value = 5\nvalue\n",
                },
            )
            edit_action = parse_tool_action(
                "NotebookEdit",
                {
                    "notebook_path": "analysis.ipynb",
                    "cell_number": 2,
                    "new_source": "value = 5\nvalue\n",
                },
            )

            preview = execute_action(create_run_workspace(root), preview_action)
            after_preview = notebook_path.read_text(encoding="utf-8")

        self.assertEqual(preview.kind, "check_notebook_edit")
        self.assertTrue(preview.ok)
        self.assertEqual(after_preview, before)
        self.assertIn("+    \"value = 5\\n\"", preview.diff)
        approval_preview = approval_preview_summary(edit_action, [preview])
        self.assertIsNotNone(approval_preview)
        assert approval_preview is not None
        self.assertIn("diffChars=", approval_preview)

    def test_notebook_edit_legacy_raw_text_mode_still_maps_to_text_edit(self) -> None:
        action = parse_tool_action(
            "NotebookEdit",
            {"notebook_path": "analysis.ipynb", "old_string": '"old"', "new_string": '"new"'},
        )

        self.assertEqual(action.type, "edit_file")
        self.assertEqual(action.path, "analysis.ipynb")


if __name__ == "__main__":
    unittest.main()
