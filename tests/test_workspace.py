import tempfile
import unittest
from pathlib import Path

from vibeagent.workspace import (
    create_run_workspace,
    edit_project_file,
    list_project_files,
    read_project_file,
    resolve_inside_run,
    search_project,
    write_run_file,
)


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

            self.assertEqual(workspace.root, Path(base).resolve())
            self.assertEqual(workspace.session_dir, Path(base).resolve() / ".vibeagent" / "sessions" / "test-run")
            self.assertEqual(target, workspace.root / "nested" / "hello.txt")
            self.assertEqual(Path(target).read_text(encoding="utf-8"), "hello")

    def test_project_helpers_read_search_and_edit_inside_project(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-workspace-") as base:
            workspace = create_run_workspace(base, "test-run")
            write_run_file(workspace, "app.py", "name = 'old'\nprint(name)\n")

            files, total = list_project_files(workspace)
            self.assertEqual(files, ["app.py"])
            self.assertEqual(total, 1)
            self.assertIn("name = 'old'", read_project_file(workspace, "app.py"))
            self.assertEqual(search_project(workspace, "print"), ["app.py:2: print(name)"])

            _, diff = edit_project_file(workspace, "app.py", "old", "new")

            self.assertIn("-name = 'old'", diff)
            self.assertIn("+name = 'new'", diff)
            self.assertIn("name = 'new'", read_project_file(workspace, "app.py"))

    def test_project_paths_protect_vibeagent_and_git_metadata(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-workspace-") as base:
            workspace = create_run_workspace(base, "test-run")

            with self.assertRaisesRegex(ValueError, "protected"):
                resolve_inside_run(workspace.root, ".vibeagent/sessions/test-run/events.jsonl")
            with self.assertRaisesRegex(ValueError, "protected"):
                resolve_inside_run(workspace.root, ".git/config")


if __name__ == "__main__":
    unittest.main()
