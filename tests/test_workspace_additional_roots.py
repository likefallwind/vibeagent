import os
import tempfile
import unittest
from pathlib import Path

from vibeagent.workspace_core import RunWorkspace
from vibeagent.workspace_exact_edit_ops import edit_project_file
from vibeagent.workspace_file_read import read_project_file
from vibeagent.workspace_path_discovery import glob_project_files, list_project_tree
from vibeagent.workspace_python_definitions import find_python_definitions
from vibeagent.workspace_repo_map import build_repo_map
from vibeagent.workspace_resolve import resolve_command_cwd, resolve_inside_run
from vibeagent.workspace_search import search_project_result
from vibeagent.workspace_write_edit_ops import write_run_file


class WorkspaceAdditionalRootsTests(unittest.TestCase):
    def workspace(self, root: Path, additional: Path) -> RunWorkspace:
        return RunWorkspace(
            root=root,
            run_id="run-1",
            session_dir=root / ".vibeagent" / "sessions" / "run-1",
            additional_roots=(additional,),
        )

    def test_reads_edits_writes_searches_and_lists_an_additional_root(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-workspace-") as base:
            parent = Path(base)
            root = parent / "main"
            shared = parent / "shared"
            root.mkdir()
            shared.mkdir()
            source = shared / "src" / "shared.py"
            source.parent.mkdir()
            source.write_text("value = 'old'\n# shared needle\ndef shared_helper():\n    return value\n", encoding="utf-8")
            workspace = self.workspace(root, shared)

            self.assertIn("value = 'old'", read_project_file(workspace, str(source)))
            edit_project_file(workspace, "../shared/src/shared.py", "old", "new")
            write_run_file(workspace, str(shared / "generated.txt"), "generated\n")
            search = search_project_result(workspace, "shared needle", relative_path=str(shared))
            tree, _total = list_project_tree(workspace, str(shared), max_depth=3)
            globbed, _glob_total = glob_project_files(workspace, f"{shared}/**/*.py")
            definitions, definition_total, definition_errors = find_python_definitions(
                workspace,
                "shared_helper",
                str(shared),
            )
            repo_map = build_repo_map(workspace, str(shared), max_depth=3)

            self.assertIn("value = 'new'", source.read_text(encoding="utf-8"))
            self.assertEqual((shared / "generated.txt").read_text(encoding="utf-8"), "generated\n")
            self.assertEqual(search["matches"], [f"{source}:2: # shared needle"])
            self.assertIn(f"{shared / 'src'}/", tree)
            self.assertIn(str(source), tree)
            self.assertEqual(globbed, [str(source)])
            self.assertEqual(definition_total, 1)
            self.assertEqual(definition_errors, [])
            self.assertEqual(definitions[0]["path"], str(source))
            self.assertIn(str(source), repo_map["files"])

    def test_command_cwd_accepts_only_main_or_additional_roots(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-workspace-") as base:
            parent = Path(base)
            root = parent / "main"
            shared = parent / "shared"
            outside = parent / "outside"
            for path in (root, shared, outside):
                path.mkdir()
            workspace = self.workspace(root, shared)

            self.assertEqual(resolve_command_cwd(workspace, str(shared)), shared)
            self.assertEqual(resolve_command_cwd(workspace, "../shared"), shared)
            with self.assertRaisesRegex(ValueError, "escapes the project directory"):
                resolve_command_cwd(workspace, str(outside))

    def test_protects_runtime_and_git_paths_in_every_root(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-workspace-") as base:
            parent = Path(base)
            root = parent / "main"
            shared = parent / "shared"
            root.mkdir()
            shared.mkdir()
            workspace = self.workspace(root, shared)

            for path in (shared / ".git" / "config", shared / ".vibeagent" / "state.json"):
                with self.subTest(path=path), self.assertRaisesRegex(ValueError, "protected"):
                    resolve_inside_run(workspace, str(path))

            nested = shared / "nested"
            nested.mkdir()
            overlapping = RunWorkspace(
                root=root,
                run_id="run-2",
                session_dir=root / ".vibeagent" / "sessions" / "run-2",
                additional_roots=(shared, nested),
            )
            with self.assertRaisesRegex(ValueError, "protected"):
                resolve_inside_run(overlapping, str(nested / ".git" / "config"))

    def test_cannot_move_copy_or_delete_an_additional_root(self) -> None:
        from vibeagent.workspace_directory_ops import (
            prepare_project_directory_copy,
            prepare_project_directory_move,
            preview_delete_project_empty_directory,
        )

        with tempfile.TemporaryDirectory(prefix="vibeagent-workspace-") as base:
            parent = Path(base)
            root = parent / "main"
            shared = parent / "shared"
            root.mkdir()
            shared.mkdir()
            workspace = self.workspace(root, shared)

            for operation, args in (
                (prepare_project_directory_move, (workspace, str(shared), str(root / "moved"))),
                (prepare_project_directory_copy, (workspace, str(shared), str(root / "copied"))),
                (preview_delete_project_empty_directory, (workspace, str(shared))),
            ):
                with self.subTest(operation=operation.__name__), self.assertRaisesRegex(ValueError, "workspace root"):
                    operation(*args)

    @unittest.skipUnless(hasattr(os, "symlink"), "symbolic links are unavailable")
    def test_mutation_rejects_symlink_paths_inside_an_additional_root(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-workspace-") as base:
            parent = Path(base)
            root = parent / "main"
            shared = parent / "shared"
            outside = parent / "outside"
            root.mkdir()
            shared.mkdir()
            outside.mkdir()
            (outside / "target.txt").write_text("old", encoding="utf-8")
            (shared / "link.txt").symlink_to(outside / "target.txt")
            workspace = self.workspace(root, shared)

            with self.assertRaisesRegex(ValueError, "escapes the project directory|symbolic link"):
                edit_project_file(workspace, str(shared / "link.txt"), "old", "new")


if __name__ == "__main__":
    unittest.main()
