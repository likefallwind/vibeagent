import tempfile
import unittest
from pathlib import Path

from vibeagent.actions import execute_action
from vibeagent.search_action_executor import execute_search_action
from vibeagent.types import FindFilesAction, GlobAction, ReadFileAction, SearchAction, SearchContextsAction
from vibeagent.workspace_core import RunWorkspace


class SearchActionExecutorTests(unittest.TestCase):
    def make_workspace(self, root: Path) -> RunWorkspace:
        session_dir = root / ".vibeagent" / "sessions" / "run-1"
        session_dir.mkdir(parents=True)
        return RunWorkspace(root=root, run_id="run-1", session_dir=session_dir)

    def test_search_executor_matches_top_level_for_search_actions(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-search-actions-") as tmp:
            root = Path(tmp)
            (root / "src").mkdir()
            (root / "src" / "app.py").write_text("def run():\n    return 'needle'\n", encoding="utf-8")
            workspace = self.make_workspace(root)
            actions = [
                SearchAction(type="search", query="needle"),
                SearchContextsAction(type="search_contexts", query="needle", context_lines=1),
                FindFilesAction(type="find_files", query="app", path="src"),
                GlobAction(type="glob", pattern="**/*.py"),
            ]

            for action in actions:
                with self.subTest(action=action.type):
                    self.assertEqual(execute_search_action(workspace, action), execute_action(workspace, action))

    def test_search_executor_returns_none_for_non_search_action(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-search-actions-") as tmp:
            workspace = self.make_workspace(Path(tmp))
            action = ReadFileAction(type="read_file", path="app.py")

            self.assertIsNone(execute_search_action(workspace, action))


if __name__ == "__main__":
    unittest.main()
