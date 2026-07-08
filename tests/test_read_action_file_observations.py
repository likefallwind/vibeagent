import tempfile
import unittest
from pathlib import Path

from vibeagent.read_action_executor import execute_read_action
from vibeagent.read_action_file_observations import execute_read_file_action
from vibeagent.types import OutputContextsAction, PythonSymbolsAction, ReadFileAction, ReadFilesAction
from vibeagent.workspace_core import RunWorkspace


class ReadActionFileObservationsTests(unittest.TestCase):
    def make_workspace(self, root: Path) -> RunWorkspace:
        session_dir = root / ".vibeagent" / "sessions" / "run-1"
        session_dir.mkdir(parents=True)
        return RunWorkspace(root=root, run_id="run-1", session_dir=session_dir)

    def test_file_helper_matches_read_executor_for_single_file(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-read-files-") as tmp:
            root = Path(tmp)
            (root / "app.py").write_text("print('hello')\n", encoding="utf-8")
            workspace = self.make_workspace(root)
            action = ReadFileAction(type="read_file", path="app.py")

            self.assertEqual(execute_read_file_action(workspace, action), execute_read_action(workspace, action))

    def test_file_helper_matches_read_executor_for_batch_and_symbols(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-read-files-") as tmp:
            root = Path(tmp)
            (root / "app.py").write_text("def run():\n    return 1\n", encoding="utf-8")
            workspace = self.make_workspace(root)
            batch = ReadFilesAction(type="read_files", paths=["app.py", "missing.py"])
            symbols = PythonSymbolsAction(type="python_symbols", paths=["app.py"])

            self.assertEqual(execute_read_file_action(workspace, batch), execute_read_action(workspace, batch))
            self.assertEqual(execute_read_file_action(workspace, symbols), execute_read_action(workspace, symbols))

    def test_file_helper_leaves_output_context_actions_to_read_executor(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-read-files-") as tmp:
            workspace = self.make_workspace(Path(tmp))
            action = OutputContextsAction(type="output_contexts", text="app.py:1")

            self.assertIsNone(execute_read_file_action(workspace, action))


if __name__ == "__main__":
    unittest.main()
