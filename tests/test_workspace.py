import tempfile
import unittest
from pathlib import Path

from vibeagent.workspace import create_run_workspace, resolve_inside_run, write_run_file


class WorkspaceTests(unittest.TestCase):
    def test_resolve_inside_run_rejects_absolute_paths(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-workspace-") as base:
            workspace = create_run_workspace(base, "test-run")

            with self.assertRaisesRegex(ValueError, "Absolute paths"):
                resolve_inside_run(workspace.root, "/tmp/file.py")

    def test_resolve_inside_run_rejects_parent_directory_escape(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-workspace-") as base:
            workspace = create_run_workspace(base, "test-run")

            with self.assertRaisesRegex(ValueError, "escapes"):
                resolve_inside_run(workspace.root, "../file.py")
            with self.assertRaisesRegex(ValueError, "escapes"):
                resolve_inside_run(workspace.root, "nested/../../file.py")

    def test_write_run_file_writes_inside_the_run_directory(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-workspace-") as base:
            workspace = create_run_workspace(base, "test-run")
            target = write_run_file(workspace, "nested/hello.txt", "hello")

            self.assertEqual(target, workspace.root / "nested" / "hello.txt")
            self.assertEqual(Path(target).read_text(encoding="utf-8"), "hello")


if __name__ == "__main__":
    unittest.main()
