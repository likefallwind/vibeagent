from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from vibeagent import workspace_project_info, workspace_project_todos, workspace_search_files
from vibeagent.workspace_core import RunWorkspace


class WorkspaceProjectTodosTests(unittest.TestCase):
    def make_workspace(self, root: Path) -> RunWorkspace:
        session_dir = root / ".vibeagent" / "sessions" / "run-1"
        session_dir.mkdir(parents=True)
        return RunWorkspace(root=root, run_id="run-1", session_dir=session_dir)

    def test_project_info_keeps_todos_and_file_listing_reexports(self) -> None:
        self.assertIs(workspace_project_info.read_project_todos, workspace_project_todos.read_project_todos)
        self.assertIs(workspace_project_info.list_files, workspace_search_files.list_files)
        self.assertIs(workspace_project_info.list_search_files, workspace_search_files.list_search_files)

    def test_read_project_todos_finds_markers_with_limits(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-project-todos-") as tmp:
            root = Path(tmp)
            (root / "src").mkdir()
            (root / "src" / "app.py").write_text("# TODO: repair parser\n# FIXME later\n", encoding="utf-8")
            (root / "notes.txt").write_text("plain text\n", encoding="utf-8")
            workspace = self.make_workspace(root)

            report = workspace_project_todos.read_project_todos(workspace, "src", max_items=1)

        self.assertTrue(report["ok"])
        self.assertEqual(report["total"], 2)
        self.assertTrue(report["truncated"])
        self.assertEqual(report["path"], "src")
        self.assertEqual(report["todos"], [{"path": "src/app.py", "line": 1, "marker": "TODO", "text": "# TODO: repair parser"}])


if __name__ == "__main__":
    unittest.main()
