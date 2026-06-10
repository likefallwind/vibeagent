import tempfile
import unittest
import subprocess
from pathlib import Path
from unittest.mock import patch

from vibeagent.workspace import (
    append_project_file,
    build_repo_map,
    check_config_syntax,
    check_python_syntax,
    check_project_patch,
    check_project_patches,
    commit_staged_changes,
    copy_project_directory,
    copy_project_directories,
    copy_project_file,
    create_project_directory,
    create_run_workspace,
    delete_project_empty_directory,
    delete_project_empty_directories,
    delete_project_file,
    edit_project_file,
    inspect_python_call_graph,
    find_python_calls,
    find_python_definitions,
    find_python_references,
    glob_project_files,
    inspect_code_dependencies,
    find_code_definitions,
    find_code_references,
    inspect_python_dependencies,
    insert_project_file_lines,
    list_project_files,
    list_project_tree,
    move_project_directory,
    move_project_directories,
    move_project_file,
    multi_edit_project_file,
    patch_project_file,
    patch_project_files,
    apply_python_rename,
    preview_python_rename,
    preview_create_project_directory,
    preview_copy_project_file,
    preview_delete_project_empty_directory,
    preview_delete_project_empty_directories,
    preview_edit_project_file,
    preview_move_project_file,
    preview_multi_edit_project_file,
    preview_append_project_file,
    preview_copy_project_directory,
    preview_copy_project_directories,
    preview_insert_project_file_lines,
    preview_move_project_directory,
    preview_move_project_directories,
    preview_replace_project_file_lines,
    parse_git_diff_hunks,
    parse_git_remotes,
    read_environment_info,
    read_project_command_hints,
    read_git_changes,
    read_git_blame,
    read_git_diff,
    read_git_diff_hunks,
    read_git_info,
    read_git_log,
    read_git_show,
    read_git_status,
    read_project_file_info,
    read_project_instructions,
    read_project_file,
    read_project_file_result,
    read_project_commands,
    read_project_manifests,
    read_code_outline,
    read_python_symbol_outline,
    preview_set_project_file_executable,
    preview_regex_replace_project_file,
    preview_replace_python_definition,
    regex_replace_project_file,
    replace_python_definition,
    replace_project_file_lines,
    review_project_changes,
    resolve_inside_run,
    resolve_command_cwd,
    search_project,
    search_project_result,
    set_project_file_executable,
    stage_git_paths,
    suggest_project_checks,
    unstage_git_paths,
    preview_delete_project_file,
    preview_write_run_file,
    preview_write_run_files,
    write_run_file,
    write_run_files,
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
            preview_target, preview_diff = preview_write_run_file(workspace, "nested/hello.txt", "hello")
            preview_exists = preview_target.exists()
            target = write_run_file(workspace, "nested/hello.txt", "hello")

            self.assertEqual(workspace.root, Path(base).resolve())
            self.assertEqual(workspace.session_dir, Path(base).resolve() / ".vibeagent" / "sessions" / "test-run")
            self.assertEqual(preview_target, workspace.root / "nested" / "hello.txt")
            self.assertFalse(preview_exists)
            self.assertIn("+hello", preview_diff)
            self.assertEqual(target, workspace.root / "nested" / "hello.txt")
            self.assertEqual(Path(target).read_text(encoding="utf-8"), "hello")

    def test_parse_git_remotes_redacts_url_credentials(self) -> None:
        remotes = parse_git_remotes(
            "\n".join(
                [
                    "origin https://user:SECRET_TOKEN@example.com/org/repo.git (fetch)",
                    "origin https://user:SECRET_TOKEN@example.com/org/repo.git (push)",
                    "backup git@example.com:org/repo.git (fetch)",
                ]
            )
        )

        urls = [remote["url"] for remote in remotes]
        self.assertIn("https://***@example.com/org/repo.git", urls)
        self.assertIn("git@example.com:org/repo.git", urls)
        self.assertNotIn("SECRET_TOKEN", "\n".join(urls))

    def test_write_run_files_writes_multiple_files_atomically(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-workspace-") as base:
            workspace = create_run_workspace(base, "test-run")
            write_run_file(workspace, "existing.txt", "old\n")

            previews = preview_write_run_files(
                workspace,
                [
                    ("existing.txt", "new\n"),
                    ("pkg/app.py", "print('ok')\n"),
                ],
            )
            preview_content = (workspace.root / "existing.txt").read_text(encoding="utf-8")
            written = write_run_files(
                workspace,
                [
                    ("existing.txt", "new\n"),
                    ("pkg/app.py", "print('ok')\n"),
                ],
            )

            with self.assertRaisesRegex(ValueError, "Path is protected"):
                write_run_files(
                    workspace,
                    [
                        ("existing.txt", "bad\n"),
                        (".vibeagent/secret.txt", "no\n"),
                    ],
                )

            with self.assertRaisesRegex(ValueError, "Duplicate file path"):
                write_run_files(workspace, [("dup.txt", "one\n"), ("dup.txt", "two\n")])

            self.assertEqual([item[0] for item in previews], ["existing.txt", "pkg/app.py"])
            self.assertEqual(preview_content, "old\n")
            self.assertIn("+new", previews[0][2])
            self.assertIn("+print('ok')", previews[1][2])
            self.assertEqual([path.relative_to(workspace.root).as_posix() for path in written], ["existing.txt", "pkg/app.py"])
            self.assertEqual((workspace.root / "existing.txt").read_text(encoding="utf-8"), "new\n")
            self.assertEqual((workspace.root / "pkg/app.py").read_text(encoding="utf-8"), "print('ok')\n")
            self.assertFalse((workspace.root / ".vibeagent" / "secret.txt").exists())

    def test_create_and_delete_project_empty_directory(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-workspace-") as base:
            workspace = create_run_workspace(base, "test-run")
            preview_created = preview_create_project_directory(workspace, "pkg/empty")
            preview_created_exists = (workspace.root / "pkg" / "empty").exists()
            created = create_project_directory(workspace, "pkg/empty")
            existing = create_project_directory(workspace, "pkg/empty")
            write_run_file(workspace, "pkg/nonempty/file.txt", "x\n")

            with self.assertRaisesRegex(ValueError, "not empty"):
                preview_delete_project_empty_directory(workspace, "pkg/nonempty")
            with self.assertRaisesRegex(ValueError, "not empty"):
                delete_project_empty_directory(workspace, "pkg/nonempty")
            preview_deleted = preview_delete_project_empty_directory(workspace, "pkg/empty")
            preview_deleted_exists = (workspace.root / "pkg" / "empty").is_dir()
            deleted = delete_project_empty_directory(workspace, "pkg/empty")
            with self.assertRaisesRegex(ValueError, "Directory does not exist"):
                delete_project_empty_directory(workspace, "missing")
            write_run_file(workspace, "file.txt", "x\n")
            with self.assertRaisesRegex(ValueError, "not a directory"):
                create_project_directory(workspace, "file.txt")

            created_path = created.relative_to(workspace.root).as_posix()
            existing_path = existing.relative_to(workspace.root).as_posix()
            deleted_path = deleted.relative_to(workspace.root).as_posix()
            empty_exists = (workspace.root / "pkg" / "empty").exists()
            nonempty_exists = (workspace.root / "pkg" / "nonempty").is_dir()

        self.assertEqual(preview_created, workspace.root / "pkg" / "empty")
        self.assertFalse(preview_created_exists)
        self.assertEqual(created_path, "pkg/empty")
        self.assertEqual(existing_path, "pkg/empty")
        self.assertEqual(preview_deleted, workspace.root / "pkg" / "empty")
        self.assertTrue(preview_deleted_exists)
        self.assertEqual(deleted_path, "pkg/empty")
        self.assertFalse(empty_exists)
        self.assertTrue(nonempty_exists)

    def test_delete_project_empty_directories_validates_before_deleting(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-workspace-") as base:
            workspace = create_run_workspace(base, "test-run")
            create_project_directory(workspace, "pkg/parent/child")
            create_project_directory(workspace, "standalone")
            previewed = preview_delete_project_empty_directories(
                workspace,
                ["pkg/parent/child", "pkg/parent", "standalone"],
            )
            previewed_exists = [
                (workspace.root / "pkg" / "parent" / "child").is_dir(),
                (workspace.root / "pkg" / "parent").is_dir(),
                (workspace.root / "standalone").is_dir(),
            ]
            deleted = delete_project_empty_directories(
                workspace,
                ["pkg/parent/child", "pkg/parent", "standalone"],
            )
            deleted_exists = [
                (workspace.root / "pkg" / "parent" / "child").exists(),
                (workspace.root / "pkg" / "parent").exists(),
                (workspace.root / "standalone").exists(),
            ]
            create_project_directory(workspace, "keep")
            write_run_file(workspace, "nonempty/file.txt", "x\n")
            with self.assertRaisesRegex(ValueError, "not empty"):
                delete_project_empty_directories(workspace, ["keep", "nonempty"])
            keep_exists_after_failed_batch = (workspace.root / "keep").is_dir()
            with self.assertRaisesRegex(ValueError, "duplicates"):
                preview_delete_project_empty_directories(workspace, ["keep", "pkg/../keep"])

            previewed_paths = [path.relative_to(workspace.root).as_posix() for path in previewed]
            deleted_paths = [path.relative_to(workspace.root).as_posix() for path in deleted]

        self.assertEqual(previewed_paths, ["pkg/parent/child", "pkg/parent", "standalone"])
        self.assertEqual(previewed_exists, [True, True, True])
        self.assertEqual(deleted_paths, ["pkg/parent/child", "pkg/parent", "standalone"])
        self.assertEqual(deleted_exists, [False, False, False])
        self.assertTrue(keep_exists_after_failed_batch)

    def test_move_project_directory_moves_without_overwriting_or_self_nesting(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-workspace-") as base:
            workspace = create_run_workspace(base, "test-run")
            write_run_file(workspace, "old_pkg/module.py", "VALUE = 1\n")
            write_run_file(workspace, "existing/file.py", "EXISTING = True\n")

            preview_source, preview_destination = preview_move_project_directory(workspace, "old_pkg", "packages/new_pkg")
            preview_source_exists = (workspace.root / "old_pkg").is_dir()
            preview_destination_exists = (workspace.root / "packages" / "new_pkg").exists()
            source, destination = move_project_directory(workspace, "old_pkg", "packages/new_pkg")

            with self.assertRaisesRegex(ValueError, "Directory does not exist"):
                move_project_directory(workspace, "missing", "packages/missing")
            with self.assertRaisesRegex(ValueError, "Destination already exists"):
                move_project_directory(workspace, "packages/new_pkg", "existing")
            with self.assertRaisesRegex(ValueError, "inside itself"):
                move_project_directory(workspace, "packages/new_pkg", "packages/new_pkg/nested")
            with self.assertRaisesRegex(ValueError, "project root"):
                move_project_directory(workspace, ".", "root-copy")

            source_path = source.relative_to(workspace.root).as_posix()
            destination_path = destination.relative_to(workspace.root).as_posix()
            source_exists = (workspace.root / "old_pkg").exists()
            moved_content = (workspace.root / "packages" / "new_pkg" / "module.py").read_text(encoding="utf-8")

        self.assertEqual(preview_source, workspace.root / "old_pkg")
        self.assertEqual(preview_destination, workspace.root / "packages" / "new_pkg")
        self.assertTrue(preview_source_exists)
        self.assertFalse(preview_destination_exists)
        self.assertEqual(source_path, "old_pkg")
        self.assertEqual(destination_path, "packages/new_pkg")
        self.assertFalse(source_exists)
        self.assertEqual(moved_content, "VALUE = 1\n")

    def test_move_project_directories_validates_before_moving(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-workspace-") as base:
            workspace = create_run_workspace(base, "test-run")
            write_run_file(workspace, "old_a/module.py", "A = 1\n")
            write_run_file(workspace, "old_b/module.py", "B = 1\n")
            previewed = preview_move_project_directories(
                workspace,
                [("old_a", "packages/new_a"), ("old_b", "packages/new_b")],
            )
            preview_sources_exist = [(workspace.root / "old_a").is_dir(), (workspace.root / "old_b").is_dir()]
            preview_destinations_exist = [
                (workspace.root / "packages" / "new_a").exists(),
                (workspace.root / "packages" / "new_b").exists(),
            ]
            moved = move_project_directories(workspace, [("old_a", "packages/new_a"), ("old_b", "packages/new_b")])
            moved_sources_exist = [(workspace.root / "old_a").exists(), (workspace.root / "old_b").exists()]
            moved_destinations_exist = [
                (workspace.root / "packages" / "new_a" / "module.py").is_file(),
                (workspace.root / "packages" / "new_b" / "module.py").is_file(),
            ]
            write_run_file(workspace, "keep_a/module.py", "A = 1\n")
            write_run_file(workspace, "keep_b/module.py", "B = 1\n")
            with self.assertRaisesRegex(ValueError, "Directory does not exist"):
                move_project_directories(workspace, [("keep_a", "moved_a"), ("missing", "moved_missing")])
            failed_sources_exist = [(workspace.root / "keep_a").is_dir(), (workspace.root / "keep_b").is_dir()]
            failed_destination_exists = (workspace.root / "moved_a").exists()
            create_project_directory(workspace, "keep_a/subdir")
            with self.assertRaisesRegex(ValueError, "must not overlap"):
                preview_move_project_directories(workspace, [("keep_a", "nested_a"), ("keep_a/subdir", "nested_child")])
            with self.assertRaisesRegex(ValueError, "destination must not overlap a source"):
                preview_move_project_directories(workspace, [("keep_a", "keep_b/inside"), ("keep_b", "moved_b")])

            previewed_pairs = [
                (source.relative_to(workspace.root).as_posix(), destination.relative_to(workspace.root).as_posix())
                for source, destination in previewed
            ]
            moved_pairs = [
                (source.relative_to(workspace.root).as_posix(), destination.relative_to(workspace.root).as_posix())
                for source, destination in moved
            ]

        self.assertEqual(previewed_pairs, [("old_a", "packages/new_a"), ("old_b", "packages/new_b")])
        self.assertEqual(preview_sources_exist, [True, True])
        self.assertEqual(preview_destinations_exist, [False, False])
        self.assertEqual(moved_pairs, [("old_a", "packages/new_a"), ("old_b", "packages/new_b")])
        self.assertEqual(moved_sources_exist, [False, False])
        self.assertEqual(moved_destinations_exist, [True, True])
        self.assertEqual(failed_sources_exist, [True, True])
        self.assertFalse(failed_destination_exists)

    def test_copy_project_directory_copies_without_overwriting_or_self_nesting(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-workspace-") as base:
            workspace = create_run_workspace(base, "test-run")
            write_run_file(workspace, "template/module.py", "VALUE = 1\n")
            write_run_file(workspace, "template/nested/config.txt", "ok\n")
            write_run_file(workspace, "existing/file.py", "EXISTING = True\n")

            preview_source, preview_destination = preview_copy_project_directory(workspace, "template", "packages/copied")
            preview_source_content = (workspace.root / "template" / "module.py").read_text(encoding="utf-8")
            preview_destination_exists = (workspace.root / "packages" / "copied").exists()
            source, destination = copy_project_directory(workspace, "template", "packages/copied")

            with self.assertRaisesRegex(ValueError, "Directory does not exist"):
                copy_project_directory(workspace, "missing", "packages/missing")
            with self.assertRaisesRegex(ValueError, "Destination already exists"):
                copy_project_directory(workspace, "template", "existing")
            with self.assertRaisesRegex(ValueError, "inside itself"):
                copy_project_directory(workspace, "template", "template/nested/copy")
            with self.assertRaisesRegex(ValueError, "project root"):
                copy_project_directory(workspace, ".", "root-copy")

            source_path = source.relative_to(workspace.root).as_posix()
            destination_path = destination.relative_to(workspace.root).as_posix()
            source_content = (workspace.root / "template" / "module.py").read_text(encoding="utf-8")
            copied_content = (workspace.root / "packages" / "copied" / "nested" / "config.txt").read_text(encoding="utf-8")

        self.assertEqual(preview_source, workspace.root / "template")
        self.assertEqual(preview_destination, workspace.root / "packages" / "copied")
        self.assertEqual(preview_source_content, "VALUE = 1\n")
        self.assertFalse(preview_destination_exists)
        self.assertEqual(source_path, "template")
        self.assertEqual(destination_path, "packages/copied")
        self.assertEqual(source_content, "VALUE = 1\n")
        self.assertEqual(copied_content, "ok\n")

    def test_copy_project_directories_validates_before_copying(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-workspace-") as base:
            workspace = create_run_workspace(base, "test-run")
            write_run_file(workspace, "template_a/module.py", "A = 1\n")
            write_run_file(workspace, "template_b/module.py", "B = 1\n")
            previewed = preview_copy_project_directories(
                workspace,
                [("template_a", "copies/a"), ("template_b", "copies/b")],
            )
            preview_sources_exist = [
                (workspace.root / "template_a").is_dir(),
                (workspace.root / "template_b").is_dir(),
            ]
            preview_destinations_exist = [
                (workspace.root / "copies" / "a").exists(),
                (workspace.root / "copies" / "b").exists(),
            ]
            copied = copy_project_directories(workspace, [("template_a", "copies/a"), ("template_b", "copies/b")])
            copied_sources_exist = [
                (workspace.root / "template_a").is_dir(),
                (workspace.root / "template_b").is_dir(),
            ]
            copied_destinations_exist = [
                (workspace.root / "copies" / "a" / "module.py").is_file(),
                (workspace.root / "copies" / "b" / "module.py").is_file(),
            ]
            with self.assertRaisesRegex(ValueError, "Directory does not exist"):
                copy_project_directories(workspace, [("template_a", "copies/c"), ("missing", "copies/missing")])
            failed_destination_exists = (workspace.root / "copies" / "c").exists()
            with self.assertRaisesRegex(ValueError, "destinations must not overlap"):
                preview_copy_project_directories(workspace, [("template_a", "copies/parent"), ("template_b", "copies/parent/child")])
            with self.assertRaisesRegex(ValueError, "destination must not overlap a source"):
                preview_copy_project_directories(workspace, [("template_a", "template_b/inside"), ("template_b", "copies/b2")])

            previewed_pairs = [
                (source.relative_to(workspace.root).as_posix(), destination.relative_to(workspace.root).as_posix())
                for source, destination in previewed
            ]
            copied_pairs = [
                (source.relative_to(workspace.root).as_posix(), destination.relative_to(workspace.root).as_posix())
                for source, destination in copied
            ]

        self.assertEqual(previewed_pairs, [("template_a", "copies/a"), ("template_b", "copies/b")])
        self.assertEqual(preview_sources_exist, [True, True])
        self.assertEqual(preview_destinations_exist, [False, False])
        self.assertEqual(copied_pairs, [("template_a", "copies/a"), ("template_b", "copies/b")])
        self.assertEqual(copied_sources_exist, [True, True])
        self.assertEqual(copied_destinations_exist, [True, True])
        self.assertFalse(failed_destination_exists)

    def test_copy_project_directory_rejects_symlinks_and_large_trees(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-workspace-") as base:
            workspace = create_run_workspace(base, "test-run")
            write_run_file(workspace, "template/file.txt", "ok\n")
            (Path(base) / "template" / "link.txt").symlink_to(Path(base) / "template" / "file.txt")
            write_run_file(workspace, "large/file.txt", "12345\n")

            with self.assertRaisesRegex(ValueError, "symbolic link"):
                copy_project_directory(workspace, "template", "copied")
            with self.assertRaisesRegex(ValueError, "more than 0 entries"):
                copy_project_directory(workspace, "large", "large-copy", max_entries=0)
            with self.assertRaisesRegex(ValueError, "exceeds 2 bytes"):
                copy_project_directory(workspace, "large", "large-copy", max_bytes=2)

    def test_project_helpers_read_search_and_edit_inside_project(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-workspace-") as base:
            workspace = create_run_workspace(base, "test-run")
            write_run_file(workspace, "app.py", "name = 'old'\nprint(name)\n")

            files, total = list_project_files(workspace)
            self.assertEqual(files, ["app.py"])
            self.assertEqual(total, 1)
            self.assertIn("name = 'old'", read_project_file(workspace, "app.py"))
            self.assertEqual(read_project_file(workspace, "app.py", start_line=2, line_count=1), "2: print(name)")
            preview = read_project_file_result(workspace, "app.py", max_bytes=10)
            self.assertEqual(search_project(workspace, "print"), ["app.py:2: print(name)"])
            Path(base, "asset.bin").write_bytes(b"\x00\x01")

            with self.assertRaisesRegex(ValueError, "binary or non-UTF-8"):
                read_project_file(workspace, "asset.bin")

            preview_target, preview_diff = preview_edit_project_file(workspace, "app.py", "old", "new")
            preview_path = preview_target.relative_to(workspace.root).as_posix()
            preview_content = read_project_file(workspace, "app.py")
            _, diff = edit_project_file(workspace, "app.py", "old", "new")
            updated = read_project_file(workspace, "app.py")

        self.assertEqual(preview_path, "app.py")
        self.assertEqual(preview_content, "name = 'old'\nprint(name)\n")
        self.assertIn("+name = 'new'", preview_diff)
        self.assertIn("-name = 'old'", diff)
        self.assertIn("+name = 'new'", diff)
        self.assertIn("name = 'new'", updated)
        self.assertTrue(preview["truncated"])
        self.assertEqual(preview["max_bytes"], 10)
        self.assertIn("[file truncated]", preview["content"])

    def test_multi_edit_project_file_applies_replacements_atomically(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-workspace-") as base:
            workspace = create_run_workspace(base, "test-run")
            write_run_file(workspace, "app.py", "name = 'old'\nprint(name)\n")

            preview_target, preview_diff = preview_multi_edit_project_file(
                workspace,
                "app.py",
                [("old", "new"), ("print(name)", "print(name.upper())")],
            )
            preview_path = preview_target.relative_to(workspace.root).as_posix()
            preview_content = read_project_file(workspace, "app.py")
            _, diff = multi_edit_project_file(
                workspace,
                "app.py",
                [("old", "new"), ("print(name)", "print(name.upper())")],
            )

            with self.assertRaisesRegex(ValueError, "Edit 2 old text was not found"):
                multi_edit_project_file(workspace, "app.py", [("new", "changed"), ("missing", "value")])

            content = read_project_file(workspace, "app.py")

        self.assertEqual(preview_path, "app.py")
        self.assertEqual(preview_content, "name = 'old'\nprint(name)\n")
        self.assertIn("+print(name.upper())", preview_diff)
        self.assertEqual(content, "name = 'new'\nprint(name.upper())\n")
        self.assertIn("+print(name.upper())", diff)

    def test_replace_project_file_lines_replaces_inclusive_range(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-workspace-") as base:
            workspace = create_run_workspace(base, "test-run")
            write_run_file(workspace, "app.py", "one\ntwo\nthree\nfour\n")

            preview_target, preview_diff = preview_replace_project_file_lines(workspace, "app.py", 2, 3, "TWO\nTHREE")
            preview_path = preview_target.relative_to(workspace.root).as_posix()
            preview_content = read_project_file(workspace, "app.py")
            _, diff = replace_project_file_lines(workspace, "app.py", 2, 3, "TWO\nTHREE")

            with self.assertRaisesRegex(ValueError, "end_line must be greater"):
                replace_project_file_lines(workspace, "app.py", 3, 2, "bad\n")
            with self.assertRaisesRegex(ValueError, "exceeds file line count"):
                replace_project_file_lines(workspace, "app.py", 4, 5, "bad\n")
            with self.assertRaisesRegex(ValueError, "made no changes"):
                replace_project_file_lines(workspace, "app.py", 2, 3, "TWO\nTHREE\n")

            _, delete_diff = replace_project_file_lines(workspace, "app.py", 2, 2, "")
            content = read_project_file(workspace, "app.py")

        self.assertEqual(preview_path, "app.py")
        self.assertEqual(preview_content, "one\ntwo\nthree\nfour\n")
        self.assertIn("+TWO", preview_diff)
        self.assertIn("-two", diff)
        self.assertIn("+TWO", diff)
        self.assertEqual(content, "one\nTHREE\nfour\n")
        self.assertIn("-TWO", delete_diff)

    def test_insert_project_file_lines_inserts_before_line_or_appends(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-workspace-") as base:
            workspace = create_run_workspace(base, "test-run")
            write_run_file(workspace, "app.py", "one\nthree\n")

            preview_target, preview_diff = preview_insert_project_file_lines(workspace, "app.py", 2, "two")
            preview_path = preview_target.relative_to(workspace.root).as_posix()
            preview_content = read_project_file(workspace, "app.py")
            _, diff = insert_project_file_lines(workspace, "app.py", 2, "two")
            _, append_diff = insert_project_file_lines(workspace, "app.py", 4, "four\n")

            with self.assertRaisesRegex(ValueError, "content must not be empty"):
                insert_project_file_lines(workspace, "app.py", 1, "")
            with self.assertRaisesRegex(ValueError, "exceeds append position"):
                insert_project_file_lines(workspace, "app.py", 6, "bad\n")

            content = read_project_file(workspace, "app.py")

        self.assertEqual(preview_path, "app.py")
        self.assertEqual(preview_content, "one\nthree\n")
        self.assertIn("+two", preview_diff)
        self.assertEqual(content, "one\ntwo\nthree\nfour\n")
        self.assertIn("+two", diff)
        self.assertIn("+four", append_diff)

    def test_append_project_file_appends_exact_text_to_existing_utf8_file(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-workspace-") as base:
            workspace = create_run_workspace(base, "test-run")
            write_run_file(workspace, "notes.md", "one\n")
            Path(base, "asset.bin").write_bytes(b"\x00\x01")

            preview_target, preview_diff = preview_append_project_file(workspace, "notes.md", "two")
            preview_path = preview_target.relative_to(workspace.root).as_posix()
            preview_content = (workspace.root / "notes.md").read_text(encoding="utf-8")
            target, diff = append_project_file(workspace, "notes.md", "two")

            with self.assertRaisesRegex(ValueError, "content must not be empty"):
                append_project_file(workspace, "notes.md", "")
            with self.assertRaisesRegex(ValueError, "File does not exist"):
                append_project_file(workspace, "missing.md", "x\n")
            with self.assertRaisesRegex(ValueError, "binary or non-UTF-8"):
                append_project_file(workspace, "asset.bin", "x\n")

            target_path = target.relative_to(workspace.root).as_posix()
            content = (workspace.root / "notes.md").read_text(encoding="utf-8")

        self.assertEqual(preview_path, "notes.md")
        self.assertEqual(preview_content, "one\n")
        self.assertIn("+two", preview_diff)
        self.assertEqual(target_path, "notes.md")
        self.assertEqual(content, "one\ntwo")
        self.assertIn("+two", diff)

    def test_regex_replace_project_file_applies_bounded_pattern_replacements(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-workspace-") as base:
            workspace = create_run_workspace(base, "test-run")
            write_run_file(workspace, "app.py", "Name = 'Ada'\nname = 'Bob'\n")

            target, replacements, diff = regex_replace_project_file(
                workspace,
                "app.py",
                r"^name\s*=\s*'([^']+)'",
                r"user = '\1'",
                case_sensitive=False,
                multiline=True,
                max_replacements=2,
            )

            with self.assertRaisesRegex(ValueError, "above max_replacements"):
                regex_replace_project_file(workspace, "app.py", r"user", "name", max_replacements=1)
            with self.assertRaisesRegex(ValueError, "Pattern was not found"):
                regex_replace_project_file(workspace, "app.py", r"missing", "x")
            with self.assertRaisesRegex(ValueError, "Invalid regex pattern"):
                regex_replace_project_file(workspace, "app.py", "(", "x")

            target_path = target.relative_to(workspace.root).as_posix()
            content = (workspace.root / "app.py").read_text(encoding="utf-8")

        self.assertEqual(target_path, "app.py")
        self.assertEqual(replacements, 2)
        self.assertEqual(content, "user = 'Ada'\nuser = 'Bob'\n")
        self.assertIn("+user = 'Ada'", diff)

    def test_preview_regex_replace_project_file_returns_diff_without_writing(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-workspace-") as base:
            workspace = create_run_workspace(base, "test-run")
            write_run_file(workspace, "app.py", "value = 'old'\n")

            target, replacements, diff = preview_regex_replace_project_file(workspace, "app.py", "old", "new")
            content = (workspace.root / "app.py").read_text(encoding="utf-8")

        self.assertEqual(target.relative_to(workspace.root).as_posix(), "app.py")
        self.assertEqual(replacements, 1)
        self.assertIn("+value = 'new'", diff)
        self.assertEqual(content, "value = 'old'\n")

    def test_read_project_file_info_reports_text_binary_directory_and_missing_paths(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-workspace-") as base:
            workspace = create_run_workspace(base, "test-run")
            write_run_file(workspace, "app.py", "one\ntwo\n")
            Path(base, "asset.bin").write_bytes(b"\x00\x01")
            Path(base, "pkg").mkdir()

            text = read_project_file_info(workspace, "app.py")
            binary = read_project_file_info(workspace, "asset.bin")
            directory = read_project_file_info(workspace, "pkg")
            missing = read_project_file_info(workspace, "missing.py")

            with self.assertRaisesRegex(ValueError, "protected"):
                read_project_file_info(workspace, ".vibeagent")

        self.assertTrue(text["ok"])
        self.assertEqual(text["size_bytes"], 8)
        self.assertEqual(text["line_count"], 2)
        self.assertFalse(text["is_binary"])
        self.assertTrue(binary["is_binary"])
        self.assertTrue(directory["is_dir"])
        self.assertFalse(missing["ok"])
        self.assertFalse(missing["exists"])

    def test_read_python_symbol_outline_reports_imports_and_nested_definitions(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-workspace-") as base:
            workspace = create_run_workspace(base, "test-run")
            write_run_file(
                workspace,
                "app.py",
                (
                    "import os\n"
                    "from pathlib import Path\n\n"
                    "class App:\n"
                    "    def run(self):\n"
                    "        def inner():\n"
                    "            return Path.cwd()\n"
                    "        return inner()\n\n"
                    "async def main():\n"
                    "    return App().run()\n"
                ),
            )
            write_run_file(workspace, "bad.py", "def broken(:\n")
            write_run_file(workspace, "note.txt", "plain\n")

            outline = read_python_symbol_outline(workspace, "app.py")

            with self.assertRaisesRegex(ValueError, "not a Python source file"):
                read_python_symbol_outline(workspace, "note.txt")
            with self.assertRaisesRegex(ValueError, "Python syntax error"):
                read_python_symbol_outline(workspace, "bad.py")

        self.assertIn("1: import os", outline["imports"])
        self.assertIn("2: from pathlib import Path", outline["imports"])
        self.assertEqual(
            [(item["kind"], item["name"], item["line"], item["parent"]) for item in outline["symbols"]],
            [
                ("class", "App", 4, None),
                ("function", "run", 5, "App"),
                ("function", "inner", 6, "App.run"),
                ("async_function", "main", 10, None),
            ],
        )

    def test_read_code_outline_reports_non_python_symbols(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-workspace-") as base:
            workspace = create_run_workspace(base, "test-run")
            write_run_file(
                workspace,
                "src/app.ts",
                (
                    "import { readFile } from 'fs';\n"
                    "export class App {}\n"
                    "export function runApp() {}\n"
                    "export const loadData = async () => readFile('x');\n"
                    "export type Options = { debug: boolean };\n"
                ),
            )
            write_run_file(
                workspace,
                "src/main.go",
                "package main\n\nimport \"fmt\"\n\ntype Server struct{}\nfunc Run() {}\nfunc (s Server) Stop() {}\n",
            )

            ts = read_code_outline(workspace, "src/app.ts")
            go = read_code_outline(workspace, "src/main.go")
            limited = read_code_outline(workspace, "src/app.ts", max_symbols=2)

            with self.assertRaisesRegex(ValueError, "max_symbols must be at most 1000"):
                read_code_outline(workspace, "src/app.ts", max_symbols=1001)

        self.assertEqual(ts["language"], "typescript")
        self.assertEqual(ts["imports"], ["1: import { readFile } from 'fs';"])
        self.assertEqual(
            [(item["kind"], item["name"], item["line"]) for item in ts["symbols"]],
            [("class", "App", 2), ("function", "runApp", 3), ("function", "loadData", 4), ("type", "Options", 5)],
        )
        self.assertEqual(go["language"], "go")
        self.assertEqual([(item["kind"], item["name"]) for item in go["symbols"]], [("type", "Server"), ("function", "Run"), ("function", "Stop")])
        self.assertEqual(len(limited["symbols"]), 2)

    def test_read_environment_info_reports_runtime_and_common_tools(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-workspace-") as base:
            workspace = create_run_workspace(base, "test-run")

            info = read_environment_info(workspace)

        self.assertEqual(info["project_root"], Path(base).resolve().as_posix())
        self.assertTrue(info["python_version"])
        self.assertTrue(info["python_executable"])
        self.assertFalse(info["is_git_repo"])
        tools = info["tools"]
        self.assertIsInstance(tools, list)
        tool_names = [tool["name"] for tool in tools]
        self.assertIn("python", tool_names)
        python_tool = next(tool for tool in tools if tool["name"] == "python")
        self.assertTrue(python_tool["available"])
        self.assertTrue(python_tool["path"])
        self.assertIn("Python", python_tool["version"])

    def test_check_python_syntax_reports_errors_and_scope(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-workspace-") as base:
            workspace = create_run_workspace(base, "test-run")
            write_run_file(workspace, "src/app.py", "def ok():\n    return 1\n")
            write_run_file(workspace, "src/bad.py", "def broken(:\n")
            write_run_file(workspace, "tests/test_app.py", "def test_ok():\n    assert True\n")
            write_run_file(workspace, "note.txt", "def ignored(:\n")

            results, total = check_python_syntax(workspace)
            scoped, scoped_total = check_python_syntax(workspace, "tests")
            limited, limited_total = check_python_syntax(workspace, max_files=1)

            with self.assertRaisesRegex(ValueError, "max_files must be at most 500"):
                check_python_syntax(workspace, max_files=501)
            with self.assertRaisesRegex(ValueError, "escapes"):
                check_python_syntax(workspace, "../outside")

        self.assertEqual(total, 3)
        self.assertEqual([(item["path"], item["ok"]) for item in results], [("src/app.py", True), ("src/bad.py", False), ("tests/test_app.py", True)])
        self.assertEqual(results[1]["line"], 1)
        self.assertIn("Python syntax error", results[1]["message"])
        self.assertEqual(scoped_total, 1)
        self.assertEqual(scoped[0]["path"], "tests/test_app.py")
        self.assertEqual(limited_total, 3)
        self.assertEqual(len(limited), 1)

    def test_check_config_syntax_reports_json_and_toml_errors(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-workspace-") as base:
            workspace = create_run_workspace(base, "test-run")
            write_run_file(workspace, "package.json", '{"scripts": {"test": "pytest"}}\n')
            write_run_file(workspace, "bad.json", '{"scripts": }\n')
            write_run_file(workspace, "pyproject.toml", "[project]\nname = 'demo'\n")
            write_run_file(workspace, "bad.toml", "[project\nname = 'demo'\n")
            write_run_file(workspace, "app.py", "print('ignored')\n")

            results, total = check_config_syntax(workspace, max_files=10)
            scoped_results, scoped_total = check_config_syntax(workspace, "package.json")

            with self.assertRaisesRegex(ValueError, "max_files must be at most 500"):
                check_config_syntax(workspace, max_files=501)
            with self.assertRaisesRegex(ValueError, "escapes"):
                check_config_syntax(workspace, "../outside")

        self.assertEqual(total, 4)
        self.assertEqual([item["path"] for item in results], ["bad.json", "bad.toml", "package.json", "pyproject.toml"])
        self.assertEqual([item["format"] for item in results], ["json", "toml", "json", "toml"])
        self.assertFalse(results[0]["ok"])
        self.assertEqual(results[0]["line"], 1)
        self.assertIn("JSON syntax error", results[0]["message"])
        self.assertFalse(results[1]["ok"])
        self.assertIn("TOML syntax error", results[1]["message"])
        self.assertTrue(results[2]["ok"])
        self.assertTrue(results[3]["ok"])
        self.assertEqual(scoped_total, 1)
        self.assertEqual(scoped_results[0]["path"], "package.json")

    def test_inspect_python_dependencies_classifies_local_and_external_imports(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-workspace-") as base:
            workspace = create_run_workspace(base, "test-run")
            write_run_file(workspace, "pkg/__init__.py", "")
            write_run_file(workspace, "pkg/util.py", "VALUE = 1\n")
            write_run_file(
                workspace,
                "pkg/app.py",
                (
                    "import os\n"
                    "import pkg.util as util\n"
                    "from .util import VALUE\n"
                    "from pathlib import Path\n"
                ),
            )
            write_run_file(workspace, "pkg/bad.py", "def broken(:\n")

            results, total = inspect_python_dependencies(workspace, "pkg")
            limited, limited_total = inspect_python_dependencies(workspace, "pkg", max_files=1)

            with self.assertRaisesRegex(ValueError, "max_imports must be at most 2000"):
                inspect_python_dependencies(workspace, max_imports=2001)
            with self.assertRaisesRegex(ValueError, "escapes"):
                inspect_python_dependencies(workspace, "../outside")

        self.assertEqual(total, 4)
        files = {item["path"]: item for item in results}
        self.assertTrue(files["pkg/app.py"]["ok"])
        self.assertEqual(files["pkg/app.py"]["module"], "pkg.app")
        self.assertIn("pkg.util", files["pkg/app.py"]["local_modules"])
        self.assertIn("os", files["pkg/app.py"]["external_modules"])
        self.assertIn("pathlib", files["pkg/app.py"]["external_modules"])
        self.assertEqual([(item["target"], item["local"]) for item in files["pkg/app.py"]["imports"]], [("os", False), ("pkg.util", True), ("pkg.util", True), ("pathlib", False)])
        self.assertFalse(files["pkg/bad.py"]["ok"])
        self.assertIn("Python syntax error", files["pkg/bad.py"]["message"])
        self.assertEqual(limited_total, 4)
        self.assertEqual(len(limited), 1)

    def test_inspect_code_dependencies_reports_common_language_imports(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-workspace-") as base:
            workspace = create_run_workspace(base, "test-run")
            write_run_file(
                workspace,
                "web/app.ts",
                "import React from 'react';\nexport { helper } from './helper';\n",
            )
            write_run_file(workspace, "cmd/main.go", 'package main\nimport (\n    "fmt"\n    alias "example.com/pkg"\n)\n')
            write_run_file(workspace, "native/app.c", "#include <stdio.h>\n#include \"app.h\"\n")
            write_run_file(workspace, "src/lib.rs", "use std::fs;\npub use crate::model::User;\n")
            write_run_file(workspace, "pkg/app.py", "import os\n")

            results, total = inspect_code_dependencies(workspace)
            scoped, scoped_total = inspect_code_dependencies(workspace, "web")
            limited, limited_total = inspect_code_dependencies(workspace, max_imports=1)

            with self.assertRaisesRegex(ValueError, "max_imports must be at most 2000"):
                inspect_code_dependencies(workspace, max_imports=2001)
            with self.assertRaisesRegex(ValueError, "escapes"):
                inspect_code_dependencies(workspace, "../outside")

        self.assertEqual(total, 4)
        files = {item["path"]: item for item in results}
        self.assertNotIn("pkg/app.py", files)
        self.assertEqual(files["web/app.ts"]["language"], "typescript")
        self.assertEqual(files["web/app.ts"]["dependencies"], ["./helper", "react"])
        self.assertEqual([(item["kind"], item["source"]) for item in files["web/app.ts"]["imports"]], [("import", "react"), ("export", "./helper")])
        self.assertEqual(files["cmd/main.go"]["dependencies"], ["example.com/pkg", "fmt"])
        self.assertEqual(files["native/app.c"]["dependencies"], ['"app.h"', "<stdio.h>"])
        self.assertEqual(files["src/lib.rs"]["dependencies"], ["crate::model::User", "std::fs"])
        self.assertEqual(scoped_total, 1)
        self.assertEqual(scoped[0]["path"], "web/app.ts")
        self.assertEqual(limited_total, 4)
        self.assertEqual(limited[0]["imports"][0]["source"], "fmt")
        self.assertFalse(limited[1]["ok"])
        self.assertIn("limit reached", limited[1]["message"])

    def test_find_code_references_reports_non_python_identifier_matches(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-workspace-") as base:
            workspace = create_run_workspace(base, "test-run")
            write_run_file(workspace, "web/app.ts", "const runAgent = 1;\nrunAgent();\nrunAgentExtra();\n")
            write_run_file(workspace, "src/lib.rs", "fn runAgent() {}\nlet value = runAgent();\n")
            write_run_file(workspace, "pkg/app.py", "runAgent()\n")

            matches, total = find_code_references(workspace, "runAgent", max_matches=2)
            scoped, scoped_total = find_code_references(workspace, "runAgent", relative_path="web")
            literal, literal_total = find_code_references(workspace, "./helper")

            with self.assertRaisesRegex(ValueError, "single-line"):
                find_code_references(workspace, "run\nAgent")
            with self.assertRaisesRegex(ValueError, "max_matches must be at most 500"):
                find_code_references(workspace, "runAgent", max_matches=501)
            with self.assertRaisesRegex(ValueError, "escapes"):
                find_code_references(workspace, "runAgent", relative_path="../outside")

        self.assertEqual(total, 4)
        self.assertEqual(len(matches), 2)
        self.assertEqual([(item["path"], item["line"], item["column"]) for item in matches], [("src/lib.rs", 1, 4), ("src/lib.rs", 2, 13)])
        self.assertEqual(scoped_total, 2)
        self.assertEqual([item["line"] for item in scoped], [1, 2])
        self.assertEqual(literal_total, 0)
        self.assertNotIn("pkg/app.py", {item["path"] for item in matches})

    def test_find_code_definitions_returns_generic_source_excerpts(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-workspace-") as base:
            workspace = create_run_workspace(base, "test-run")
            write_run_file(workspace, "web/app.ts", "export function runAgent() {\n  return 1;\n}\n")
            write_run_file(workspace, "cmd/main.go", "package main\nfunc runAgent() int {\n    return 1\n}\n")
            write_run_file(workspace, "src/lib.rs", "pub fn runAgent() -> i32 {\n    1\n}\n")
            write_run_file(workspace, "pkg/app.py", "def runAgent():\n    return 1\n")

            definitions, total, errors = find_code_definitions(workspace, "runAgent", max_matches=2, max_lines=2)
            scoped, scoped_total, scoped_errors = find_code_definitions(workspace, "runAgent", relative_path="web")

            with self.assertRaisesRegex(ValueError, "single-line"):
                find_code_definitions(workspace, "run\nAgent")
            with self.assertRaisesRegex(ValueError, "max_matches must be at most 200"):
                find_code_definitions(workspace, "runAgent", max_matches=201)
            with self.assertRaisesRegex(ValueError, "escapes"):
                find_code_definitions(workspace, "runAgent", relative_path="../outside")

        self.assertEqual(total, 3)
        self.assertEqual(len(definitions), 2)
        self.assertEqual(errors, [])
        self.assertEqual([(item["path"], item["language"], item["kind"], item["line"]) for item in definitions], [("cmd/main.go", "go", "function", 2), ("src/lib.rs", "rust", "function", 1)])
        self.assertIn("func runAgent", definitions[0]["content"])
        self.assertTrue(definitions[0]["truncated"])
        self.assertEqual(scoped_total, 1)
        self.assertEqual(scoped_errors, [])
        self.assertEqual(scoped[0]["path"], "web/app.ts")
        self.assertNotIn("pkg/app.py", {item["path"] for item in definitions})

    def test_find_python_definitions_returns_focused_source_excerpts(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-workspace-") as base:
            workspace = create_run_workspace(base, "test-run")
            write_run_file(
                workspace,
                "src/app.py",
                (
                    "class Runner:\n"
                    "    def run(self):\n"
                    "        value = 1\n"
                    "        return value\n\n"
                    "def run(task):\n"
                    "    return task\n"
                ),
            )
            write_run_file(workspace, "src/bad.py", "def broken(:\n")

            definitions, total, errors = find_python_definitions(workspace, "Runner.run", "src", max_lines=2)
            unqualified, unqualified_total, _ = find_python_definitions(workspace, "run", "src/app.py")

            with self.assertRaisesRegex(ValueError, "valid identifier"):
                find_python_definitions(workspace, "bad-name")
            with self.assertRaisesRegex(ValueError, "max_matches must be at most 200"):
                find_python_definitions(workspace, "run", max_matches=201)

        self.assertEqual(total, 1)
        self.assertEqual(definitions[0]["qualified_name"], "Runner.run")
        self.assertEqual(definitions[0]["line"], 2)
        self.assertEqual(definitions[0]["end_line"], 4)
        self.assertTrue(definitions[0]["truncated"])
        self.assertIn("2:     def run", definitions[0]["content"])
        self.assertIn("Python syntax error in src/bad.py", errors[0])
        self.assertEqual(unqualified_total, 2)
        self.assertEqual([item["qualified_name"] for item in unqualified], ["Runner.run", "run"])

    def test_replace_python_definition_replaces_unique_symbol_and_validates_syntax(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-workspace-") as base:
            workspace = create_run_workspace(base, "test-run")
            write_run_file(
                workspace,
                "src/app.py",
                (
                    "class Runner:\n"
                    "    def run(self):\n"
                    "        return 'old'\n\n"
                    "def run(task):\n"
                    "    return task\n"
                ),
            )

            preview_target, preview_after, preview_diff, preview_definition = preview_replace_python_definition(
                workspace,
                "Runner.run",
                "    def run(self):\n        return 'new'\n",
                "src/app.py",
            )
            preview_content = read_project_file(workspace, "src/app.py")
            target, diff, definition = replace_python_definition(
                workspace,
                "Runner.run",
                "    def run(self):\n        return 'new'\n",
                "src/app.py",
            )

            with self.assertRaisesRegex(ValueError, "ambiguous"):
                replace_python_definition(workspace, "run", "def run(task):\n    return task\n", "src/app.py")
            with self.assertRaisesRegex(ValueError, "syntax error"):
                replace_python_definition(workspace, "Runner.run", "    def run(self):\n        return (\n", "src/app.py")

            content = read_project_file(workspace, "src/app.py")

        self.assertEqual(preview_target, workspace.root / "src" / "app.py")
        self.assertEqual(preview_definition["qualified_name"], "Runner.run")
        self.assertIn("return 'new'", preview_after)
        self.assertIn("+        return 'new'", preview_diff)
        self.assertIn("return 'old'", preview_content)
        self.assertEqual(target, workspace.root / "src" / "app.py")
        self.assertEqual(definition["qualified_name"], "Runner.run")
        self.assertIn("-        return 'old'", diff)
        self.assertIn("+        return 'new'", diff)
        self.assertIn("return 'new'", content)

    def test_find_python_calls_reports_call_sites_and_callers(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-workspace-") as base:
            workspace = create_run_workspace(base, "test-run")
            write_run_file(
                workspace,
                "src/app.py",
                (
                    "def run_agent(task):\n"
                    "    return task\n\n"
                    "class Runner:\n"
                    "    def call(self):\n"
                    "        return run_agent('x')\n\n"
                    "    def other(self):\n"
                    "        return self.call()\n\n"
                    "value = Runner().call()\n"
                ),
            )
            write_run_file(workspace, "src/bad.py", "def broken(:\n")

            calls, total, errors = find_python_calls(workspace, "call", "src")
            run_calls, run_total, _ = find_python_calls(workspace, "run_agent", "src/app.py")

            with self.assertRaisesRegex(ValueError, "valid identifier"):
                find_python_calls(workspace, "bad-name")
            with self.assertRaisesRegex(ValueError, "max_matches must be at most 500"):
                find_python_calls(workspace, "run_agent", max_matches=501)

        self.assertEqual(total, 2)
        self.assertEqual(
            [(item["path"], item["line"], item["callee"], item["caller"], item["context"]) for item in calls],
            [
                ("src/app.py", 9, "self.call", "Runner.other", "return self.call()"),
                ("src/app.py", 11, "Runner.call", None, "value = Runner().call()"),
            ],
        )
        self.assertEqual(run_total, 1)
        self.assertEqual(run_calls[0]["callee"], "run_agent")
        self.assertEqual(run_calls[0]["caller"], "Runner.call")
        self.assertIn("Python syntax error in src/bad.py", errors[0])

    def test_inspect_python_call_graph_reports_edges_and_file_limits(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-workspace-") as base:
            workspace = create_run_workspace(base, "test-run")
            write_run_file(
                workspace,
                "src/app.py",
                (
                    "def helper():\n"
                    "    return 1\n\n"
                    "async def fetch(client):\n"
                    "    return client.get('/x')\n\n"
                    "class Runner:\n"
                    "    def run(self):\n"
                    "        return helper()\n\n"
                    "    def build(self):\n"
                    "        return Runner().run()\n\n"
                    "value = Runner().build()\n"
                ),
            )
            write_run_file(workspace, "src/bad.py", "def broken(:\n")

            edges, total, total_files, errors = inspect_python_call_graph(workspace, "src", max_edges=4)
            limited, limited_total, limited_files, _ = inspect_python_call_graph(workspace, "src", max_files=1)

            with self.assertRaisesRegex(ValueError, "max_files must be at most 500"):
                inspect_python_call_graph(workspace, max_files=501)
            with self.assertRaisesRegex(ValueError, "max_edges must be at most 2000"):
                inspect_python_call_graph(workspace, max_edges=2001)

        self.assertEqual(total_files, 2)
        self.assertEqual(total, 6)
        self.assertEqual(len(edges), 4)
        self.assertEqual(
            {(item["callee"], item["caller"]) for item in edges},
            {("client.get", "fetch"), ("helper", "Runner.run"), ("Runner", "Runner.build"), ("Runner.run", "Runner.build")},
        )
        self.assertIn("Python syntax error in src/bad.py", errors[0])
        self.assertEqual(limited_files, 2)
        self.assertEqual(limited_total, 6)
        self.assertEqual(len(limited), 6)

    def test_preview_python_rename_reports_ast_guided_diffs_without_writing(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-workspace-") as base:
            workspace = create_run_workspace(base, "test-run")
            write_run_file(
                workspace,
                "src/app.py",
                (
                    "def run_agent(task):\n"
                    "    task = task.strip()\n"
                    "    return task\n\n"
                    "class Runner:\n"
                    "    def call(self, task):\n"
                    "        return run_agent(task)\n\n"
                    "value = runner.run_agent(task)\n"
                ),
            )
            write_run_file(workspace, "src/bad.py", "def broken(:\n")

            preview = preview_python_rename(workspace, "run_agent", "execute_agent", "src", max_replacements=2)
            invalid_same = None
            with self.assertRaisesRegex(ValueError, "different"):
                preview_python_rename(workspace, "run_agent", "run_agent", "src")
            with self.assertRaisesRegex(ValueError, "simple identifier"):
                preview_python_rename(workspace, "Runner.run", "execute", "src")
            content = read_project_file(workspace, "src/app.py")

        self.assertIsNone(invalid_same)
        self.assertEqual(preview["total_replacements"], 3)
        self.assertTrue(preview["truncated"])
        self.assertEqual(preview["total_files"], 2)
        self.assertEqual(len(preview["files"]), 1)
        replacements = preview["files"][0]["replacements"]
        self.assertEqual([(item["line"], item["kind"]) for item in replacements], [(1, "function"), (7, "name")])
        self.assertIn("-def run_agent(task):", preview["files"][0]["diff"])
        self.assertIn("+def execute_agent(task):", preview["files"][0]["diff"])
        self.assertIn("Python syntax error in src/bad.py", preview["errors"][0])
        self.assertIn("def run_agent(task):", content)

    def test_apply_python_rename_writes_valid_rename_and_rejects_errors(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-workspace-") as base:
            workspace = create_run_workspace(base, "test-run")
            write_run_file(
                workspace,
                "src/app.py",
                "def run_agent(task):\n    return run_agent(task.strip())\n",
            )

            result = apply_python_rename(workspace, "run_agent", "execute_agent", "src")
            content = read_project_file(workspace, "src/app.py")

            write_run_file(workspace, "src/bad.py", "def broken(:\n")
            with self.assertRaisesRegex(ValueError, "skipped"):
                apply_python_rename(workspace, "execute_agent", "run_agent", "src")
            with self.assertRaisesRegex(ValueError, "no replacements"):
                apply_python_rename(workspace, "missing_name", "new_name", "src/app.py")

        self.assertEqual(result["total_replacements"], 2)
        self.assertIn("+def execute_agent(task):", result["diff"])
        self.assertEqual(content, "def execute_agent(task):\n    return execute_agent(task.strip())\n")

    def test_find_python_references_reports_ast_matches_and_scope(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-workspace-") as base:
            workspace = create_run_workspace(base, "test-run")
            write_run_file(
                workspace,
                "src/app.py",
                (
                    "from helpers import run_agent\n\n"
                    "def run_agent(task):\n"
                    "    return task\n\n"
                    "class Runner:\n"
                    "    def call(self):\n"
                    "        return self.run_agent('x')\n\n"
                    "result = run_agent('task')\n"
                ),
            )
            write_run_file(workspace, "tests/test_app.py", "from src.app import run_agent\nvalue = run_agent('t')\n")
            write_run_file(workspace, "src/bad.py", "def broken(:\n")
            write_run_file(workspace, "note.txt", "run_agent in text\n")

            matches, total, errors = find_python_references(workspace, "run_agent", max_matches=4)
            scoped, scoped_total, scoped_errors = find_python_references(workspace, "run_agent", relative_path="tests")

            with self.assertRaisesRegex(ValueError, "valid identifier"):
                find_python_references(workspace, "not-valid")
            with self.assertRaisesRegex(ValueError, "max_matches must be at most 500"):
                find_python_references(workspace, "run_agent", max_matches=501)

        self.assertEqual(
            [(item["path"], item["line"], item["kind"], item["context"]) for item in matches],
            [
                ("src/app.py", 1, "import", "from helpers import run_agent"),
                ("src/app.py", 3, "definition", "def run_agent(task):"),
                ("src/app.py", 8, "reference", "return self.run_agent('x')"),
                ("src/app.py", 10, "reference", "result = run_agent('task')"),
            ],
        )
        self.assertEqual(total, 6)
        self.assertEqual(len(errors), 1)
        self.assertIn("Python syntax error in src/bad.py", errors[0])
        self.assertEqual(scoped_total, 2)
        self.assertFalse(scoped_errors)
        self.assertEqual([item["path"] for item in scoped], ["tests/test_app.py", "tests/test_app.py"])

    def test_read_project_instructions_reads_scoped_agents_md_with_bounds(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-workspace-") as base:
            workspace = create_run_workspace(base, "test-run")
            self.assertIsNone(read_project_instructions(workspace))

            write_run_file(workspace, "AGENTS.md", "Use Python.\n")
            write_run_file(workspace, "pkg/AGENTS.md", "Use unittest in this package.\n")
            write_run_file(workspace, "empty/AGENTS.md", "\n")
            short = read_project_instructions(workspace)
            bounded = read_project_instructions(workspace, max_bytes=40)

        self.assertIn("File: AGENTS.md", short or "")
        self.assertIn("Scope: .", short or "")
        self.assertIn("Use Python.", short or "")
        self.assertIn("File: pkg/AGENTS.md", short or "")
        self.assertIn("Scope: pkg", short or "")
        self.assertIn("Use unittest in this package.", short or "")
        self.assertNotIn("empty/AGENTS.md", short or "")
        self.assertTrue((bounded or "").endswith("[AGENTS.md instructions truncated]"))

    def test_read_project_command_hints_reads_common_project_metadata(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-workspace-") as base:
            workspace = create_run_workspace(base, "test-run")
            self.assertIsNone(read_project_command_hints(workspace))

            write_run_file(
                workspace,
                "package.json",
                '{"scripts":{"test":"python3 -m unittest discover -s tests","build":"python3 -m compileall -q vibeagent"}}',
            )
            write_run_file(
                workspace,
                "apps/web/package.json",
                '{"scripts":{"test":"vitest","dev":"vite --host 0.0.0.0"}}',
            )
            write_run_file(
                workspace,
                "pyproject.toml",
                '[project]\n[project.scripts]\nvibeagent = "vibeagent.cli:main"\n',
            )
            write_run_file(workspace, "apps/api/Makefile", "test:\n\tpytest\n")
            write_run_file(workspace, "node_modules/pkg/package.json", '{"scripts":{"test":"ignored"}}')
            write_run_file(workspace, "Makefile", "test:\n\tpython3 -m unittest\n.PHONY: test\nbuild:\n\tpython3 -m compileall\n")
            hints = read_project_command_hints(workspace)
            bounded = read_project_command_hints(workspace, max_bytes=50)

        self.assertIn("File: package.json", hints or "")
        self.assertIn("Cwd: .", hints or "")
        self.assertIn("package.json scripts:", hints or "")
        self.assertIn("- npm run test [available=", hints or "")
        self.assertIn("missingTool=", hints or "")
        self.assertIn(": python3 -m unittest discover -s tests", hints or "")
        self.assertIn("File: apps/web/package.json", hints or "")
        self.assertIn("Cwd: apps/web", hints or "")
        self.assertIn("- npm run dev [available=", hints or "")
        self.assertIn(": vite --host 0.0.0.0", hints or "")
        self.assertIn("pyproject.toml console scripts:", hints or "")
        self.assertIn("- vibeagent [available=", hints or "")
        self.assertIn(": vibeagent.cli:main", hints or "")
        self.assertIn("Makefile targets:", hints or "")
        self.assertIn("- make build [available=", hints or "")
        self.assertIn("File: apps/api/Makefile", hints or "")
        self.assertIn("Cwd: apps/api", hints or "")
        self.assertNotIn("ignored", hints or "")
        self.assertTrue((bounded or "").endswith("[project command hints truncated]"))

    def test_read_project_command_hints_marks_missing_command_tools(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-workspace-") as base:
            workspace = create_run_workspace(base, "test-run")
            write_run_file(workspace, "package.json", '{"scripts":{"test":"node test.js"}}')

            with patch("vibeagent.workspace.shutil.which", side_effect=lambda name: None if name == "npm" else f"/bin/{name}"):
                hints = read_project_command_hints(workspace)

        self.assertIn("- npm run test [available=false missingTool=npm]: node test.js", hints or "")

    def test_read_project_command_hints_marks_missing_pyproject_scripts(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-workspace-") as base:
            workspace = create_run_workspace(base, "test-run")
            write_run_file(
                workspace,
                "pyproject.toml",
                '[project]\n[project.scripts]\nmissing-cli = "pkg.cli:main"\n',
            )

            with patch("vibeagent.workspace.shutil.which", return_value=None):
                hints = read_project_command_hints(workspace)

        self.assertIn("- missing-cli [available=false missingTool=missing-cli]: pkg.cli:main", hints or "")

    def test_read_project_commands_reports_structured_metadata(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-workspace-") as base:
            workspace = create_run_workspace(base, "test-run")
            write_run_file(workspace, "package.json", '{"scripts":{"test":"node test.js"}}')
            write_run_file(
                workspace,
                "aaa/pyproject.toml",
                '[project]\n[project.scripts]\nmissing-cli = "pkg.cli:main"\n',
            )
            write_run_file(workspace, "apps/api/Makefile", "test:\n\tpytest\n")

            with patch("vibeagent.workspace.shutil.which", side_effect=lambda name: None if name == "missing-cli" else f"/bin/{name}"):
                metadata = read_project_commands(workspace, max_files=2)

        self.assertTrue(metadata["ok"])
        self.assertEqual(metadata["total"], 2)
        self.assertTrue(metadata["truncated"])
        self.assertEqual(metadata["total_files"], 3)
        self.assertEqual(metadata["scanned_files"], 2)
        commands = metadata["commands"]
        self.assertEqual(len(commands), 2)
        missing = commands[0]
        self.assertEqual(missing["file"], "aaa/pyproject.toml")
        self.assertFalse(missing["available"])
        self.assertEqual(missing["missing_tool"], "missing-cli")
        self.assertEqual(commands[1]["file"], "apps/api/Makefile")
        self.assertEqual(commands[1]["cwd"], "apps/api")
        self.assertEqual(commands[1]["source"], "makefile_target")
        self.assertEqual(commands[1]["command"], "make test")
        self.assertEqual(commands[1]["detail"], "test")

    def test_read_project_manifests_reports_dependencies_and_scripts(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-workspace-") as base:
            workspace = create_run_workspace(base, "test-run")
            write_run_file(
                workspace,
                "package.json",
                '{"name":"web","version":"1.2.3","scripts":{"test":"vitest"},"dependencies":{"react":"^19.0.0"},"devDependencies":{"vite":"^7.0.0"}}',
            )
            write_run_file(
                workspace,
                "pyproject.toml",
                "[project]\nname='pkg'\nversion='0.1.0'\ndependencies=['requests>=2']\n[project.scripts]\nvibe='pkg.cli:main'\n",
            )
            write_run_file(workspace, "bad/package.json", '{"name": }\n')

            metadata = read_project_manifests(workspace, max_items=4)
            with self.assertRaisesRegex(ValueError, "max_items must be at most 2000"):
                read_project_manifests(workspace, max_items=2001)

        self.assertFalse(metadata["ok"])
        self.assertEqual(metadata["total_files"], 3)
        self.assertEqual(metadata["scanned_files"], 3)
        self.assertTrue(metadata["truncated"])
        manifests = {item["path"]: item for item in metadata["manifests"]}
        package = manifests["package.json"]
        self.assertTrue(package["ok"])
        self.assertEqual(package["kind"], "package_json")
        self.assertEqual(package["name"], "web")
        self.assertEqual(package["version"], "1.2.3")
        self.assertEqual([(item["group"], item["name"], item["value"]) for item in package["items"]], [("scripts", "test", "vitest"), ("dependencies", "react", "^19.0.0"), ("devDependencies", "vite", "^7.0.0")])
        pyproject = manifests["pyproject.toml"]
        self.assertEqual(pyproject["name"], "pkg")
        self.assertEqual(pyproject["items"][0]["group"], "dependencies")
        self.assertEqual(pyproject["items"][0]["name"], "requests>=2")
        self.assertFalse(manifests["bad/package.json"]["ok"])

    def test_suggest_project_checks_uses_metadata_tests_and_changes(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-workspace-") as base:
            root = Path(base)
            subprocess.run(["git", "init"], cwd=root, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            workspace = create_run_workspace(root, "test-run")
            write_run_file(
                workspace,
                "package.json",
                '{"scripts":{"test":"node test.js","build":"vite build","dev":"vite"}}',
            )
            write_run_file(workspace, "pkg/__init__.py", "")
            write_run_file(workspace, "tests/test_app.py", "def test_ok():\n    assert True\n")
            write_run_file(workspace, "Makefile", "lint:\n\tpython -m compileall pkg\nserve:\n\tpython -m http.server\n")
            subprocess.run(["git", "add", "."], cwd=root, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            subprocess.run(
                ["git", "-c", "user.name=Test", "-c", "user.email=test@example.com", "commit", "-m", "initial"],
                cwd=root,
                check=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
            write_run_file(workspace, "pkg/app.py", "value = 1\n")

            suggestions = suggest_project_checks(workspace, max_commands=3)
            all_suggestions = suggest_project_checks(workspace)

            with self.assertRaisesRegex(ValueError, "max_commands must be at most 100"):
                suggest_project_checks(workspace, max_commands=101)

        self.assertTrue(suggestions["ok"])
        self.assertTrue(suggestions["truncated"])
        self.assertEqual(len(suggestions["checks"]), 3)
        commands = {(item["cwd"], item["command"]) for item in all_suggestions["checks"]}
        self.assertIn((".", "npm run test"), commands)
        self.assertIn((".", "npm run build"), commands)
        self.assertIn((".", "make lint"), commands)
        self.assertIn((".", "python -m unittest discover -s tests"), commands)
        self.assertIn((".", "python -m compileall -q pkg"), commands)
        self.assertNotIn((".", "npm run dev"), commands)
        self.assertNotIn((".", "make serve"), commands)
        self.assertIn("pkg/app.py", all_suggestions["changed_files"])
        npm_check = next(item for item in all_suggestions["checks"] if item["command"] == "npm run test")
        self.assertIn("available", npm_check)
        self.assertIn("missing_tool", npm_check)

    def test_suggest_project_checks_marks_missing_command_tools(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-workspace-") as base:
            workspace = create_run_workspace(base, "test-run")
            write_run_file(workspace, "package.json", '{"scripts":{"test":"node test.js"}}\n')

            with patch("vibeagent.workspace.shutil.which", side_effect=lambda name: None if name == "npm" else f"/bin/{name}"):
                suggestions = suggest_project_checks(workspace)

        npm_check = next(item for item in suggestions["checks"] if item["command"] == "npm run test")
        self.assertFalse(npm_check["available"])
        self.assertEqual(npm_check["missing_tool"], "npm")

    def test_resolve_command_cwd_allows_only_project_directories(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-workspace-") as base:
            workspace = create_run_workspace(base, "test-run")
            write_run_file(workspace, "pkg/app.py", "print('ok')\n")

            cwd = resolve_command_cwd(workspace, "pkg")

            self.assertEqual(cwd, workspace.root / "pkg")
            with self.assertRaisesRegex(ValueError, "not a directory"):
                resolve_command_cwd(workspace, "pkg/app.py")
            with self.assertRaisesRegex(ValueError, "escapes"):
                resolve_command_cwd(workspace, "../outside")
            with self.assertRaisesRegex(ValueError, "protected"):
                resolve_command_cwd(workspace, ".vibeagent")

    def test_search_project_supports_scope_regex_and_case_options(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-workspace-") as base:
            workspace = create_run_workspace(base, "test-run")
            write_run_file(workspace, "src/app.py", "def HandleEvent():\n    return 1\n")
            write_run_file(workspace, "tests/test_app.py", "def test_handle_event():\n    return 2\n")
            Path(base, "src", "asset.bin").write_bytes(b"\x00def\xff")

            scoped = search_project(workspace, "def", relative_path="src")
            insensitive = search_project(workspace, "handleevent", case_sensitive=False)
            regex = search_project(workspace, r"def\s+\w+Event", regex=True, relative_path="src/app.py")
            contextual = search_project(workspace, "return 1", relative_path="src/app.py", context_lines=1)
            limited = search_project_result(workspace, "def", max_matches=1)

            with self.assertRaisesRegex(ValueError, "Invalid regex"):
                search_project(workspace, "(", regex=True)
            with self.assertRaisesRegex(ValueError, "context_lines must be at most 5"):
                search_project(workspace, "def", context_lines=6)

        self.assertEqual(scoped, ["src/app.py:1: def HandleEvent():"])
        self.assertEqual(insensitive, ["src/app.py:1: def HandleEvent():"])
        self.assertEqual(regex, ["src/app.py:1: def HandleEvent():"])
        self.assertEqual(contextual, ["src/app.py:1:  def HandleEvent():\nsrc/app.py:2:>     return 1"])
        self.assertEqual(limited["matches"], ["src/app.py:1: def HandleEvent():"])
        self.assertEqual(limited["total"], 2)
        self.assertTrue(limited["truncated"])

    def test_glob_project_files_matches_relative_patterns_and_ignores_generated_dirs(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-workspace-") as base:
            workspace = create_run_workspace(base, "test-run")
            write_run_file(workspace, "src/app.py", "print('app')\n")
            write_run_file(workspace, "tests/test_app.py", "def test_app(): pass\n")
            write_run_file(workspace, "node_modules/pkg/index.py", "ignored\n")
            (Path(base) / ".vibeagent" / "local.py").write_text("ignored\n", encoding="utf-8")

            matches, total = glob_project_files(workspace, "**/*.py", max_matches=1)

        self.assertEqual(matches, ["src/app.py"])
        self.assertEqual(total, 2)

    def test_project_scans_respect_root_gitignore_patterns(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-workspace-") as base:
            workspace = create_run_workspace(base, "test-run")
            write_run_file(workspace, ".gitignore", "ignored.log\ncoverage/\n*.tmp\nsrc/generated.py\n")
            write_run_file(workspace, "src/app.py", "print('visible')\n")
            write_run_file(workspace, "src/generated.py", "print('hidden_marker generated')\n")
            write_run_file(workspace, "ignored.log", "hidden_marker log\n")
            write_run_file(workspace, "coverage/report.txt", "hidden_marker coverage\n")
            write_run_file(workspace, "nested/cache.tmp", "hidden_marker tmp\n")

            files, total = list_project_files(workspace)
            matches = search_project(workspace, "hidden_marker")
            python_matches, python_total = glob_project_files(workspace, "**/*.py")
            repo_map = build_repo_map(workspace, max_depth=3, max_files=20, max_symbols=20)

        self.assertEqual(files, [".gitignore", "src/app.py"])
        self.assertEqual(total, 2)
        self.assertEqual(matches, [])
        self.assertEqual(python_matches, ["src/app.py"])
        self.assertEqual(python_total, 1)
        self.assertEqual(repo_map["files"], [".gitignore", "src/app.py"])

    def test_project_scans_respect_nested_gitignore_patterns(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-workspace-") as base:
            workspace = create_run_workspace(base, "test-run")
            write_run_file(workspace, "src/.gitignore", "generated.py\nlocal_build/\n*.snap\n")
            write_run_file(workspace, "src/app.py", "print('visible')\n")
            write_run_file(workspace, "src/generated.py", "hidden_marker generated\n")
            write_run_file(workspace, "src/local_build/output.py", "hidden_marker build\n")
            write_run_file(workspace, "src/snapshot.snap", "hidden_marker snap\n")
            write_run_file(workspace, "other/generated.py", "print('visible elsewhere')\n")

            files, total = list_project_files(workspace)
            matches = search_project(workspace, "hidden_marker")
            python_matches, python_total = glob_project_files(workspace, "**/*.py")

        self.assertEqual(files, ["other/generated.py", "src/.gitignore", "src/app.py"])
        self.assertEqual(total, 3)
        self.assertEqual(matches, [])
        self.assertEqual(python_matches, ["other/generated.py", "src/app.py"])
        self.assertEqual(python_total, 2)

    def test_glob_project_files_rejects_unsafe_patterns(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-workspace-") as base:
            workspace = create_run_workspace(base, "test-run")

            with self.assertRaisesRegex(ValueError, "Absolute paths"):
                glob_project_files(workspace, "/tmp/*.py")
            with self.assertRaisesRegex(ValueError, "escapes"):
                glob_project_files(workspace, "../*.py")
            with self.assertRaisesRegex(ValueError, "protected"):
                glob_project_files(workspace, ".git/*")

    def test_list_project_tree_reports_hierarchy_and_ignores_generated_dirs(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-workspace-") as base:
            workspace = create_run_workspace(base, "test-run")
            write_run_file(workspace, "src/app.py", "print('app')\n")
            write_run_file(workspace, "src/pkg/mod.py", "value = 1\n")
            write_run_file(workspace, "tests/test_app.py", "def test_app(): pass\n")
            write_run_file(workspace, "node_modules/pkg/index.py", "ignored\n")
            (Path(base) / ".vibeagent" / "local.py").write_text("ignored\n", encoding="utf-8")

            shallow, shallow_total = list_project_tree(workspace, max_depth=1)
            deeper, deeper_total = list_project_tree(workspace, max_depth=3, max_entries=3)
            src_tree, src_total = list_project_tree(workspace, "src", max_depth=2)
            file_tree, file_total = list_project_tree(workspace, "src/app.py")

        self.assertEqual(shallow, ["src/", "tests/"])
        self.assertEqual(shallow_total, 2)
        self.assertEqual(deeper, ["src/", "src/app.py", "src/pkg/"])
        self.assertEqual(deeper_total, 6)
        self.assertEqual(src_tree, ["src/app.py", "src/pkg/", "src/pkg/mod.py"])
        self.assertEqual(src_total, 3)
        self.assertEqual(file_tree, ["src/app.py"])
        self.assertEqual(file_total, 1)

    def test_list_project_tree_rejects_invalid_bounds_and_unsafe_paths(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-workspace-") as base:
            workspace = create_run_workspace(base, "test-run")

            with self.assertRaisesRegex(ValueError, "max_depth must be at least 1"):
                list_project_tree(workspace, max_depth=0)
            with self.assertRaisesRegex(ValueError, "max_depth must be at most 10"):
                list_project_tree(workspace, max_depth=11)
            with self.assertRaisesRegex(ValueError, "max_entries must be at least 1"):
                list_project_tree(workspace, max_entries=0)
            with self.assertRaisesRegex(ValueError, "max_entries must be at most 1000"):
                list_project_tree(workspace, max_entries=1001)
            with self.assertRaisesRegex(ValueError, "escapes"):
                list_project_tree(workspace, "../outside")
            with self.assertRaisesRegex(ValueError, "protected"):
                list_project_tree(workspace, ".vibeagent")

    def test_build_repo_map_reports_tree_files_and_python_symbols(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-workspace-") as base:
            workspace = create_run_workspace(base, "test-run")
            write_run_file(workspace, "README.md", "# Demo\n")
            write_run_file(workspace, "src/app.py", "import os\n\nclass App:\n    def run(self):\n        return os.getcwd()\n")
            write_run_file(workspace, "src/app.ts", "import x from 'x';\nexport function render() {}\n")
            write_run_file(workspace, "src/util.py", "def helper():\n    return 1\n")
            write_run_file(workspace, "src/main.go", 'package main\n\nimport "fmt"\n\nfunc Run() { fmt.Println("ok") }\n')
            write_run_file(workspace, "src/bad.py", "def broken(:\n")
            write_run_file(workspace, "node_modules/pkg/index.py", "ignored\n")

            repo_map = build_repo_map(workspace, max_depth=2, max_files=10, max_symbols=20)
            scoped = build_repo_map(workspace, "src", max_depth=1, max_files=2, max_symbols=10)

            with self.assertRaisesRegex(ValueError, "max_files must be at most 500"):
                build_repo_map(workspace, max_files=501)
            with self.assertRaisesRegex(ValueError, "protected"):
                build_repo_map(workspace, ".vibeagent")

        self.assertEqual(repo_map["path"], ".")
        self.assertEqual(repo_map["tree"], ["README.md", "src/", "src/app.py", "src/app.ts", "src/bad.py", "src/main.go", "src/util.py"])
        self.assertEqual(repo_map["files"], ["README.md", "src/app.py", "src/app.ts", "src/bad.py", "src/main.go", "src/util.py"])
        python_files = repo_map["python_files"]
        self.assertEqual([item["path"] for item in python_files], ["src/app.py", "src/bad.py", "src/util.py"])
        self.assertTrue(python_files[0]["ok"])
        self.assertEqual([(item["kind"], item["name"]) for item in python_files[0]["symbols"]], [("class", "App"), ("function", "run")])
        self.assertFalse(python_files[1]["ok"])
        self.assertIn("Python syntax error", python_files[1]["message"])
        code_files = repo_map["code_files"]
        self.assertEqual([item["path"] for item in code_files], ["src/app.py", "src/app.ts", "src/bad.py", "src/main.go", "src/util.py"])
        self.assertEqual([item["language"] for item in code_files], ["python", "typescript", "python", "go", "python"])
        self.assertEqual([(item["kind"], item["name"]) for item in code_files[1]["symbols"]], [("function", "render")])
        self.assertEqual([(item["kind"], item["name"]) for item in code_files[3]["symbols"]], [("function", "Run")])
        self.assertFalse(code_files[2]["ok"])
        self.assertEqual(scoped["path"], "src")
        self.assertEqual(scoped["files"], ["src/app.py", "src/app.ts"])
        self.assertEqual(scoped["total_files"], 5)
        self.assertTrue(scoped["truncated"])

    def test_patch_project_file_applies_unified_diff_hunks(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-workspace-") as base:
            workspace = create_run_workspace(base, "test-run")
            write_run_file(workspace, "app.py", "name = 'old'\nprint(name)\n")

            _, diff = patch_project_file(
                workspace,
                "app.py",
                "@@ -1,2 +1,3 @@\n"
                "-name = 'old'\n"
                "+name = 'new'\n"
                "+count = 1\n"
                " print(name)\n",
            )

            content = read_project_file(workspace, "app.py")
        self.assertEqual(content, "name = 'new'\ncount = 1\nprint(name)\n")
        self.assertIn("+count = 1", diff)

    def test_patch_project_file_rejects_mismatched_context(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-workspace-") as base:
            workspace = create_run_workspace(base, "test-run")
            write_run_file(workspace, "app.py", "name = 'actual'\nprint(name)\n")

            with self.assertRaisesRegex(ValueError, "context did not match"):
                patch_project_file(
                    workspace,
                    "app.py",
                    "@@ -1,2 +1,2 @@\n"
                    "-name = 'old'\n"
                    "+name = 'new'\n"
                    " print(name)\n",
                )

            self.assertEqual(read_project_file(workspace, "app.py"), "name = 'actual'\nprint(name)\n")

    def test_check_project_patch_validates_without_writing(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-workspace-") as base:
            workspace = create_run_workspace(base, "test-run")
            write_run_file(workspace, "app.py", "name = 'old'\nprint(name)\n")

            path, diff = check_project_patch(
                workspace,
                "app.py",
                "@@ -1,2 +1,2 @@\n"
                "-name = 'old'\n"
                "+name = 'new'\n"
                " print(name)\n",
            )
            content = read_project_file(workspace, "app.py")

            with self.assertRaisesRegex(ValueError, "context did not match"):
                check_project_patch(
                    workspace,
                    "app.py",
                    "@@ -1,2 +1,2 @@\n"
                    "-name = 'missing'\n"
                    "+name = 'new'\n"
                    " print(name)\n",
                )

        self.assertEqual(path.name, "app.py")
        self.assertIn("+name = 'new'", diff)
        self.assertEqual(content, "name = 'old'\nprint(name)\n")

    def test_patch_project_files_applies_multi_file_patch_atomically(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-workspace-") as base:
            workspace = create_run_workspace(base, "test-run")
            write_run_file(workspace, "app.py", "name = 'old'\nprint(name)\n")
            write_run_file(workspace, "config.py", "debug = False\n")

            paths, diff = patch_project_files(
                workspace,
                "--- a/app.py\n"
                "+++ b/app.py\n"
                "@@ -1,2 +1,2 @@\n"
                "-name = 'old'\n"
                "+name = 'new'\n"
                " print(name)\n"
                "--- a/config.py\n"
                "+++ b/config.py\n"
                "@@ -1 +1 @@\n"
                "-debug = False\n"
                "+debug = True\n",
            )

            app = read_project_file(workspace, "app.py")
            config = read_project_file(workspace, "config.py")
        self.assertEqual([path.name for path in paths], ["app.py", "config.py"])
        self.assertEqual(app, "name = 'new'\nprint(name)\n")
        self.assertEqual(config, "debug = True\n")
        self.assertIn("a/app.py", diff)
        self.assertIn("a/config.py", diff)

    def test_patch_project_files_can_create_new_files(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-workspace-") as base:
            workspace = create_run_workspace(base, "test-run")
            write_run_file(workspace, "app.py", "name = 'old'\n")
            write_run_file(workspace, "old.py", "print('remove')\n")

            paths, diff = patch_project_files(
                workspace,
                "--- a/app.py\n"
                "+++ b/app.py\n"
                "@@ -1 +1 @@\n"
                "-name = 'old'\n"
                "+name = 'new'\n"
                "--- /dev/null\n"
                "+++ b/pkg/new.py\n"
                "@@ -0,0 +1,2 @@\n"
                "+def created():\n"
                "+    return 'ok'\n"
                "--- a/old.py\n"
                "+++ /dev/null\n"
                "@@ -1 +0,0 @@\n"
                "-print('remove')\n",
            )

            app = read_project_file(workspace, "app.py")
            created = read_project_file(workspace, "pkg/new.py")
            old_exists = (workspace.root / "old.py").exists()
        self.assertEqual([path.relative_to(workspace.root).as_posix() for path in paths], ["app.py", "pkg/new.py", "old.py"])
        self.assertEqual(app, "name = 'new'\n")
        self.assertEqual(created, "def created():\n    return 'ok'\n")
        self.assertFalse(old_exists)
        self.assertIn("b/pkg/new.py", diff)
        self.assertIn("-print('remove')", diff)

    def test_check_project_patches_validates_multiple_files_without_writing(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-workspace-") as base:
            workspace = create_run_workspace(base, "test-run")
            write_run_file(workspace, "app.py", "name = 'old'\n")
            write_run_file(workspace, "config.py", "debug = False\n")

            paths, diff = check_project_patches(
                workspace,
                "--- a/app.py\n"
                "+++ b/app.py\n"
                "@@ -1 +1 @@\n"
                "-name = 'old'\n"
                "+name = 'new'\n"
                "--- a/config.py\n"
                "+++ b/config.py\n"
                "@@ -1 +1 @@\n"
                "-debug = False\n"
                "+debug = True\n",
            )
            app = read_project_file(workspace, "app.py")
            config = read_project_file(workspace, "config.py")

            with self.assertRaisesRegex(ValueError, "duplicate file section"):
                check_project_patches(
                    workspace,
                    "--- a/app.py\n"
                    "+++ b/app.py\n"
                    "@@ -1 +1 @@\n"
                    "-name = 'old'\n"
                    "+name = 'new'\n"
                    "--- a/app.py\n"
                    "+++ b/app.py\n"
                    "@@ -1 +1 @@\n"
                    "-name = 'old'\n"
                    "+name = 'new'\n",
                )

            create_paths, create_diff = check_project_patches(
                workspace,
                "--- /dev/null\n"
                "+++ b/new.py\n"
                "@@ -0,0 +1 @@\n"
                "+print('new')\n",
            )

            with self.assertRaisesRegex(ValueError, "File already exists"):
                check_project_patches(
                    workspace,
                    "--- /dev/null\n"
                    "+++ b/app.py\n"
                    "@@ -0,0 +1 @@\n"
                    "+print('new')\n",
                )

            delete_paths, delete_diff = check_project_patches(
                workspace,
                "--- a/config.py\n"
                "+++ /dev/null\n"
                "@@ -1 +0,0 @@\n"
                "-debug = False\n",
            )

            with self.assertRaisesRegex(ValueError, "must remove all content"):
                check_project_patches(
                    workspace,
                    "--- a/config.py\n"
                    "+++ /dev/null\n"
                    "@@ -1 +1 @@\n"
                    "-debug = False\n"
                    "+debug = True\n",
                )
            dry_created_exists = (workspace.root / "new.py").exists()
            dry_deleted_exists = (workspace.root / "config.py").exists()

        self.assertEqual([path.name for path in paths], ["app.py", "config.py"])
        self.assertIn("+debug = True", diff)
        self.assertEqual(app, "name = 'old'\n")
        self.assertEqual(config, "debug = False\n")
        self.assertEqual([path.name for path in create_paths], ["new.py"])
        self.assertIn("+print('new')", create_diff)
        self.assertEqual([path.name for path in delete_paths], ["config.py"])
        self.assertIn("-debug = False", delete_diff)
        self.assertFalse(dry_created_exists)
        self.assertTrue(dry_deleted_exists)

    def test_patch_project_files_rejects_second_file_without_partial_write(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-workspace-") as base:
            workspace = create_run_workspace(base, "test-run")
            write_run_file(workspace, "app.py", "name = 'old'\nprint(name)\n")
            write_run_file(workspace, "config.py", "debug = False\n")

            with self.assertRaisesRegex(ValueError, "context did not match"):
                patch_project_files(
                    workspace,
                    "--- a/app.py\n"
                    "+++ b/app.py\n"
                    "@@ -1,2 +1,2 @@\n"
                    "-name = 'old'\n"
                    "+name = 'new'\n"
                    " print(name)\n"
                    "--- a/config.py\n"
                    "+++ b/config.py\n"
                    "@@ -1 +1 @@\n"
                    "-debug = wrong\n"
                    "+debug = True\n",
                )

            app = read_project_file(workspace, "app.py")
            config = read_project_file(workspace, "config.py")
        self.assertEqual(app, "name = 'old'\nprint(name)\n")
        self.assertEqual(config, "debug = False\n")

    def test_delete_project_file_removes_file_and_returns_diff(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-workspace-") as base:
            workspace = create_run_workspace(base, "test-run")
            write_run_file(workspace, "obsolete.py", "print('remove')\n")

            preview_deleted, preview_diff = preview_delete_project_file(workspace, "obsolete.py")
            preview_exists = (workspace.root / "obsolete.py").exists()
            deleted, diff = delete_project_file(workspace, "obsolete.py")

            self.assertEqual(preview_deleted, workspace.root / "obsolete.py")
            self.assertTrue(preview_exists)
            self.assertIn("-print('remove')", preview_diff)
            self.assertEqual(deleted, workspace.root / "obsolete.py")
            self.assertFalse((workspace.root / "obsolete.py").exists())
            self.assertIn("-print('remove')", diff)

    def test_text_mutation_helpers_reject_binary_files_without_changes(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-workspace-") as base:
            workspace = create_run_workspace(base, "test-run")
            binary = Path(base, "asset.bin")
            binary.write_bytes(b"\x00old")

            with self.assertRaisesRegex(ValueError, "binary or non-UTF-8"):
                edit_project_file(workspace, "asset.bin", "old", "new")
            with self.assertRaisesRegex(ValueError, "binary or non-UTF-8"):
                multi_edit_project_file(workspace, "asset.bin", [("old", "new")])
            with self.assertRaisesRegex(ValueError, "binary or non-UTF-8"):
                patch_project_file(workspace, "asset.bin", "@@ -1 +1 @@\n-old\n+new\n")
            with self.assertRaisesRegex(ValueError, "binary or non-UTF-8"):
                patch_project_files(workspace, "--- a/asset.bin\n+++ b/asset.bin\n@@ -1 +1 @@\n-old\n+new\n")
            with self.assertRaisesRegex(ValueError, "binary or non-UTF-8"):
                delete_project_file(workspace, "asset.bin")

            self.assertEqual(binary.read_bytes(), b"\x00old")

    def test_move_project_file_moves_file_without_overwriting(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-workspace-") as base:
            workspace = create_run_workspace(base, "test-run")
            write_run_file(workspace, "old.py", "print('move')\n")

            preview_source, preview_destination = preview_move_project_file(workspace, "old.py", "pkg/new.py")
            preview_source_exists = (workspace.root / "old.py").exists()
            preview_destination_exists = (workspace.root / "pkg" / "new.py").exists()
            source, destination = move_project_file(workspace, "old.py", "pkg/new.py")

            self.assertEqual(preview_source, workspace.root / "old.py")
            self.assertEqual(preview_destination, workspace.root / "pkg" / "new.py")
            self.assertTrue(preview_source_exists)
            self.assertFalse(preview_destination_exists)
            self.assertEqual(source, workspace.root / "old.py")
            self.assertEqual(destination, workspace.root / "pkg" / "new.py")
            self.assertFalse((workspace.root / "old.py").exists())
            self.assertEqual((workspace.root / "pkg" / "new.py").read_text(encoding="utf-8"), "print('move')\n")

            write_run_file(workspace, "other.py", "print('other')\n")
            with self.assertRaisesRegex(ValueError, "Destination already exists"):
                move_project_file(workspace, "other.py", "pkg/new.py")
            self.assertTrue((workspace.root / "other.py").exists())

    def test_copy_project_file_copies_file_without_overwriting(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-workspace-") as base:
            workspace = create_run_workspace(base, "test-run")
            write_run_file(workspace, "template.py", "print('copy')\n")

            preview_source, preview_destination = preview_copy_project_file(workspace, "template.py", "pkg/copied.py")
            preview_source_content = (workspace.root / "template.py").read_text(encoding="utf-8")
            preview_destination_exists = (workspace.root / "pkg" / "copied.py").exists()
            source, destination = copy_project_file(workspace, "template.py", "pkg/copied.py")

            self.assertEqual(preview_source, workspace.root / "template.py")
            self.assertEqual(preview_destination, workspace.root / "pkg" / "copied.py")
            self.assertEqual(preview_source_content, "print('copy')\n")
            self.assertFalse(preview_destination_exists)
            self.assertEqual(source, workspace.root / "template.py")
            self.assertEqual(destination, workspace.root / "pkg" / "copied.py")
            self.assertEqual((workspace.root / "template.py").read_text(encoding="utf-8"), "print('copy')\n")
            self.assertEqual((workspace.root / "pkg" / "copied.py").read_text(encoding="utf-8"), "print('copy')\n")

            write_run_file(workspace, "other.py", "print('other')\n")
            with self.assertRaisesRegex(ValueError, "Destination already exists"):
                copy_project_file(workspace, "other.py", "pkg/copied.py")
            self.assertEqual((workspace.root / "other.py").read_text(encoding="utf-8"), "print('other')\n")

    def test_set_project_file_executable_updates_mode_bits(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-workspace-") as base:
            workspace = create_run_workspace(base, "test-run")
            write_run_file(workspace, "script.sh", "#!/bin/sh\n")
            script = workspace.root / "script.sh"
            script.chmod(0o644)

            preview_target, preview_before, preview_after = preview_set_project_file_executable(workspace, "script.sh", executable=True)
            preview_mode = script.stat().st_mode & 0o777
            target, before, after = set_project_file_executable(workspace, "script.sh", executable=True)
            _target, second_before, cleared = set_project_file_executable(workspace, "script.sh", executable=False)

            with self.assertRaisesRegex(ValueError, "File does not exist"):
                set_project_file_executable(workspace, "missing.sh")

        self.assertEqual(preview_target, script)
        self.assertEqual(preview_before, 0o644)
        self.assertEqual(preview_after, 0o755)
        self.assertEqual(preview_mode, 0o644)
        self.assertEqual(target, script)
        self.assertEqual(before, 0o644)
        self.assertEqual(after, 0o755)
        self.assertEqual(second_before, 0o755)
        self.assertEqual(cleared, 0o644)

    def test_read_git_status_and_diff_are_read_only(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-workspace-") as base:
            root = Path(base)
            subprocess.run(["git", "init"], cwd=root, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            workspace = create_run_workspace(root, "test-run")
            write_run_file(workspace, "app.py", "print('old')\n")
            write_run_file(workspace, "blame.py", "print('blame')\n")
            subprocess.run(["git", "add", "app.py", "blame.py"], cwd=root, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            subprocess.run(
                ["git", "-c", "user.name=Test", "-c", "user.email=test@example.com", "commit", "-m", "initial"],
                cwd=root,
                check=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
            write_run_file(workspace, "app.py", "print('new')\n")
            write_run_file(workspace, "staged.py", "print('staged')\n")
            subprocess.run(["git", "add", "staged.py"], cwd=root, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            write_run_file(workspace, "new.py", "print('untracked')\n")

            status = read_git_status(workspace)
            info = read_git_info(workspace)
            expected_head = subprocess.run(
                ["git", "rev-parse", "--short", "HEAD"],
                cwd=root,
                check=True,
                stdout=subprocess.PIPE,
                text=True,
            ).stdout.strip()
            changes = read_git_changes(workspace)
            diff = read_git_diff(workspace, "app.py")
            log = read_git_log(workspace, max_count=1, relative_path="app.py")
            show = read_git_show(workspace, "HEAD", "app.py")
            blame = read_git_blame(workspace, "blame.py", start_line=1, line_count=1)
            with self.assertRaisesRegex(ValueError, "escapes"):
                read_git_log(workspace, relative_path="../outside.py")
            with self.assertRaisesRegex(ValueError, "escapes"):
                read_git_show(workspace, relative_path="../outside.py")
            with self.assertRaisesRegex(ValueError, "must not start"):
                read_git_show(workspace, rev="--stat")

        self.assertTrue(status.ok)
        self.assertIn("M app.py", status.stdout)
        self.assertTrue(info["ok"])
        self.assertTrue(info["is_git_repo"])
        self.assertEqual(info["head"], expected_head)
        self.assertEqual(info["ahead"], 0)
        self.assertEqual(info["behind"], 0)
        self.assertIn("app.py", info["status"])
        self.assertTrue(changes["ok"])
        files = {str(item["path"]): item for item in changes["files"]}
        self.assertTrue(files["app.py"]["unstaged"])
        self.assertEqual(files["app.py"]["unstaged_insertions"], 1)
        self.assertEqual(files["app.py"]["unstaged_deletions"], 1)
        self.assertTrue(files["staged.py"]["staged"])
        self.assertEqual(files["staged.py"]["staged_insertions"], 1)
        self.assertTrue(files["new.py"]["untracked"])
        self.assertTrue(diff.ok)
        self.assertIn("-print('old')", diff.stdout)
        self.assertIn("+print('new')", diff.stdout)
        self.assertTrue(log.ok)
        self.assertIn("initial", log.stdout)
        self.assertTrue(show.ok)
        self.assertIn("initial", show.stdout)
        self.assertIn("app.py", show.stdout)
        self.assertIn("+print('old')", show.stdout)
        self.assertTrue(blame.ok)
        self.assertIn("print('blame')", blame.stdout)
        self.assertIn("Test", blame.stdout)

    def test_stage_and_unstage_git_paths_update_index(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-workspace-") as base:
            root = Path(base)
            subprocess.run(["git", "init"], cwd=root, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            workspace = create_run_workspace(root, "test-run")
            write_run_file(workspace, "app.py", "print('old')\n")
            subprocess.run(["git", "add", "app.py"], cwd=root, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            subprocess.run(
                ["git", "-c", "user.name=Test", "-c", "user.email=test@example.com", "commit", "-m", "initial"],
                cwd=root,
                check=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
            write_run_file(workspace, "app.py", "print('new')\n")

            staged = stage_git_paths(workspace, ["app.py"])
            unstaged = unstage_git_paths(workspace, ["app.py"])

            with self.assertRaisesRegex(ValueError, "protected"):
                stage_git_paths(workspace, [".git/config"])

        self.assertTrue(staged["ok"])
        self.assertEqual(staged["paths"], ["app.py"])
        self.assertIn("M  app.py", staged["status"])
        self.assertTrue(unstaged["ok"])
        self.assertIn(" M app.py", unstaged["status"])

    def test_commit_staged_changes_creates_local_commit(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-workspace-") as base:
            root = Path(base)
            subprocess.run(["git", "init"], cwd=root, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            subprocess.run(["git", "config", "user.name", "Test"], cwd=root, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=root, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            workspace = create_run_workspace(root, "test-run")
            write_run_file(workspace, "app.py", "print('initial')\n")
            stage_git_paths(workspace, ["app.py"])
            initial = commit_staged_changes(workspace, "initial")
            write_run_file(workspace, "app.py", "print('changed')\n")
            no_staged = commit_staged_changes(workspace, "should not commit")
            stage_git_paths(workspace, ["app.py"])
            committed = commit_staged_changes(workspace, "update app")
            log = subprocess.run(["git", "log", "--oneline", "--max-count=1"], cwd=root, check=True, stdout=subprocess.PIPE, text=True).stdout

            with self.assertRaisesRegex(ValueError, "message must be a non-empty"):
                commit_staged_changes(workspace, " ")

        self.assertTrue(initial["ok"])
        self.assertTrue(committed["ok"])
        self.assertNotEqual(committed["head_before"], committed["head_after"])
        self.assertEqual(committed["status"], "")
        self.assertFalse(no_staged["ok"])
        self.assertIn("No staged changes", no_staged["message"])
        self.assertIn("update app", log)

    def test_read_git_blame_rejects_invalid_scope(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-workspace-") as base:
            workspace = create_run_workspace(base, "test-run")
            write_run_file(workspace, "app.py", "print('ok')\n")

            with self.assertRaisesRegex(ValueError, "escapes"):
                read_git_blame(workspace, "../outside.py")
            with self.assertRaisesRegex(ValueError, "not a file"):
                read_git_blame(workspace, ".")
            with self.assertRaisesRegex(ValueError, "line_count must be at most 1000"):
                read_git_blame(workspace, "app.py", start_line=1, line_count=1001)

    def test_review_project_changes_checks_diff_and_changed_python(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-workspace-") as base:
            root = Path(base)
            subprocess.run(["git", "init"], cwd=root, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            workspace = create_run_workspace(root, "test-run")
            write_run_file(workspace, "app.py", "print('old')\n")
            write_run_file(workspace, "package.json", '{"scripts": {"test": "python3 -m unittest"}}\n')
            subprocess.run(["git", "add", "app.py"], cwd=root, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            subprocess.run(
                ["git", "-c", "user.name=Test", "-c", "user.email=test@example.com", "commit", "-m", "initial"],
                cwd=root,
                check=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
            write_run_file(workspace, "app.py", "def broken(: \n")
            write_run_file(workspace, "package.json", '{"scripts": }\n')
            write_run_file(workspace, "note.txt", "trailing whitespace \n")
            subprocess.run(["git", "add", "note.txt"], cwd=root, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            Path(root, ".vibeagent").mkdir(exist_ok=True)
            Path(root, ".vibeagent", "local.py").write_text("def ignored(:\n", encoding="utf-8")

            review = review_project_changes(workspace)

        self.assertFalse(review["ok"])
        self.assertTrue(review["changes_ok"])
        self.assertFalse(review["diff_check_ok"])
        self.assertFalse(review["staged_diff_check_ok"])
        self.assertFalse(review["python_ok"])
        self.assertFalse(review["config_ok"])
        self.assertIn("unstaged diff check failed", review["message"])
        self.assertIn("staged diff check failed", review["message"])
        self.assertIn("config file(s) failed syntax check", review["message"])
        files = {str(item["path"]): item for item in review["files"]}
        self.assertEqual(sorted(files), ["app.py", "note.txt", "package.json"])
        self.assertEqual(review["total_files"], 3)
        self.assertEqual([(item["path"], item["ok"]) for item in review["python"]], [("app.py", False)])
        self.assertEqual(review["python_total"], 1)
        self.assertIn("Python syntax error", review["python"][0]["message"])
        self.assertEqual([(item["path"], item["ok"], item["format"]) for item in review["config"]], [("package.json", False, "json")])
        self.assertEqual(review["config_total"], 1)
        self.assertIn("JSON syntax error", review["config"][0]["message"])
        suggested_commands = {(item["cwd"], item["command"]) for item in review["suggested_checks"]}
        self.assertIn((".", "python -m unittest discover -s tests"), suggested_commands)
        self.assertIn((".", "npm test"), suggested_commands)
        self.assertEqual(review["suggested_checks_total"], len(review["suggested_checks"]))
        self.assertFalse(review["suggested_checks_truncated"])
        self.assertEqual(review["diff_hunks_total"], 1)
        self.assertFalse(review["diff_hunks_truncated"])
        self.assertEqual(review["diff_hunks"][0]["file"], "app.py")
        self.assertEqual(review["diff_hunks"][0]["added"], 1)
        self.assertEqual(review["diff_hunks"][0]["deleted"], 1)
        self.assertEqual(review["staged_diff_hunks_total"], 1)
        self.assertFalse(review["staged_diff_hunks_truncated"])
        self.assertEqual(review["staged_diff_hunks"][0]["file"], "note.txt")
        self.assertEqual(review["untracked_previews_total"], 1)
        self.assertFalse(review["untracked_previews_truncated"])
        self.assertEqual(review["untracked_previews"][0]["path"], "package.json")
        self.assertIn('"scripts"', review["untracked_previews"][0]["content"])
        self.assertIn("note.txt", review["staged_diff_check"])

    def test_read_git_diff_rejects_path_escape(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-workspace-") as base:
            workspace = create_run_workspace(base, "test-run")

            with self.assertRaisesRegex(ValueError, "escapes"):
                read_git_diff(workspace, "../outside.py")

    def test_parse_git_diff_hunks_reports_ranges_and_counts(self) -> None:
        diff = (
            "diff --git a/app.py b/app.py\n"
            "index 111..222 100644\n"
            "--- a/app.py\n"
            "+++ b/app.py\n"
            "@@ -1,2 +1,3 @@\n"
            " line1\n"
            "-old\n"
            "+new\n"
            "+extra\n"
        )

        parsed = parse_git_diff_hunks(diff, max_hunks=1, max_lines_per_hunk=2)

        self.assertEqual(parsed["total_hunks"], 1)
        self.assertTrue(parsed["truncated"])
        hunk = parsed["hunks"][0]
        self.assertEqual(hunk["file"], "app.py")
        self.assertEqual((hunk["old_start"], hunk["old_count"]), (1, 2))
        self.assertEqual((hunk["new_start"], hunk["new_count"]), (1, 3))
        self.assertEqual((hunk["added"], hunk["deleted"], hunk["context"]), (2, 1, 1))
        self.assertEqual(hunk["lines"], [" line1", "-old"])
        self.assertTrue(hunk["lines_truncated"])

    def test_read_git_diff_hunks_returns_structured_project_diff(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-workspace-") as base:
            root = Path(base)
            subprocess.run(["git", "init"], cwd=root, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            workspace = create_run_workspace(root, "test-run")
            write_run_file(workspace, "app.py", "print('old')\n")
            subprocess.run(["git", "add", "app.py"], cwd=root, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            subprocess.run(
                ["git", "-c", "user.name=Test", "-c", "user.email=test@example.com", "commit", "-m", "initial"],
                cwd=root,
                check=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
            write_run_file(workspace, "app.py", "print('new')\nprint('extra')\n")

            summary = read_git_diff_hunks(workspace, "app.py", max_hunks=1, max_lines_per_hunk=10)
            with self.assertRaisesRegex(ValueError, "escapes"):
                read_git_diff_hunks(workspace, "../outside.py")

        self.assertTrue(summary["ok"])
        self.assertEqual(summary["total_hunks"], 1)
        self.assertEqual(summary["hunks"][0]["file"], "app.py")
        self.assertEqual(summary["hunks"][0]["added"], 2)
        self.assertEqual(summary["hunks"][0]["deleted"], 1)

    def test_project_paths_protect_vibeagent_and_git_metadata(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-workspace-") as base:
            workspace = create_run_workspace(base, "test-run")

            with self.assertRaisesRegex(ValueError, "protected"):
                resolve_inside_run(workspace.root, ".vibeagent/sessions/test-run/events.jsonl")
            with self.assertRaisesRegex(ValueError, "protected"):
                resolve_inside_run(workspace.root, ".git/config")


if __name__ == "__main__":
    unittest.main()
