import unittest

from vibeagent.command_file_edit_parsing import parse_file_edit_local_command
from vibeagent.command_parsing import LocalCommand, parse_local_command


class CommandFileEditParsingTests(unittest.TestCase):
    def test_file_edit_parser_recognizes_file_edit_commands(self) -> None:
        cases = {
            "/check-replace-lines app.py 2 3 'new\\n'": LocalCommand(
                type="check_replace_lines",
                argument="app.py 2 3 'new\\n'",
            ),
            "/replace-lines app.py 2 2 'new\\n'": LocalCommand(type="replace_lines", argument="app.py 2 2 'new\\n'"),
            "/check-insert-lines app.py 2 'new\\n'": LocalCommand(
                type="check_insert_lines",
                argument="app.py 2 'new\\n'",
            ),
            "/insert-lines app.py 2 'new\\n'": LocalCommand(type="insert_lines", argument="app.py 2 'new\\n'"),
            "/check-append app.py 'new\\n'": LocalCommand(type="check_append_file", argument="app.py 'new\\n'"),
            "/append app.py 'new\\n'": LocalCommand(type="append_file", argument="app.py 'new\\n'"),
            "/check-write app.py 'new\\n'": LocalCommand(type="check_write_file", argument="app.py 'new\\n'"),
            "/write app.py 'new\\n'": LocalCommand(type="write_file", argument="app.py 'new\\n'"),
            "/check-write-files app.py 'a\\n' test.py 'b\\n'": LocalCommand(
                type="check_write_files",
                argument="app.py 'a\\n' test.py 'b\\n'",
            ),
            "/write-files app.py 'a\\n' test.py 'b\\n'": LocalCommand(
                type="write_files",
                argument="app.py 'a\\n' test.py 'b\\n'",
            ),
            "/check-edit app.py old new": LocalCommand(type="check_edit_file", argument="app.py old new"),
            "/edit app.py old new": LocalCommand(type="edit_file", argument="app.py old new"),
            "/check-multi-edit app.py old new print log": LocalCommand(
                type="check_multi_edit_file",
                argument="app.py old new print log",
            ),
            "/multi-edit app.py old new print log": LocalCommand(
                type="multi_edit_file",
                argument="app.py old new print log",
            ),
            "/check-delete old.py": LocalCommand(type="check_delete_file", argument="old.py"),
            "/delete old.py": LocalCommand(type="delete_file", argument="old.py"),
            "/check-delete-files old.py other.py": LocalCommand(
                type="check_delete_files",
                argument="old.py other.py",
            ),
            "/delete-files old.py other.py": LocalCommand(type="delete_files", argument="old.py other.py"),
            "/check-move old.py new.py": LocalCommand(type="check_move_file", argument="old.py new.py"),
            "/move old.py new.py": LocalCommand(type="move_file", argument="old.py new.py"),
            "/check-move-files old.py new.py other.py other-new.py": LocalCommand(
                type="check_move_files",
                argument="old.py new.py other.py other-new.py",
            ),
            "/move-files old.py new.py other.py other-new.py": LocalCommand(
                type="move_files",
                argument="old.py new.py other.py other-new.py",
            ),
            "/check-copy template.py new.py": LocalCommand(type="check_copy_file", argument="template.py new.py"),
            "/copy template.py new.py": LocalCommand(type="copy_file", argument="template.py new.py"),
            "/check-copy-files template.py new.py config.py config-copy.py": LocalCommand(
                type="check_copy_files",
                argument="template.py new.py config.py config-copy.py",
            ),
            "/copy-files template.py new.py config.py config-copy.py": LocalCommand(
                type="copy_files",
                argument="template.py new.py config.py config-copy.py",
            ),
            "/check-move-dir old_pkg new_pkg": LocalCommand(type="check_move_dir", argument="old_pkg new_pkg"),
            "/move-dir old_pkg new_pkg": LocalCommand(type="move_dir", argument="old_pkg new_pkg"),
            "/check-move-dirs old_a new_a old_b new_b": LocalCommand(
                type="check_move_dirs",
                argument="old_a new_a old_b new_b",
            ),
            "/move-dirs old_a new_a old_b new_b": LocalCommand(
                type="move_dirs",
                argument="old_a new_a old_b new_b",
            ),
            "/check-copy-dir template_pkg copy_pkg": LocalCommand(
                type="check_copy_dir",
                argument="template_pkg copy_pkg",
            ),
            "/copy-dir template_pkg copy_pkg": LocalCommand(type="copy_dir", argument="template_pkg copy_pkg"),
            "/check-copy-dirs template_a copy_a template_b copy_b": LocalCommand(
                type="check_copy_dirs",
                argument="template_a copy_a template_b copy_b",
            ),
            "/copy-dirs template_a copy_a template_b copy_b": LocalCommand(
                type="copy_dirs",
                argument="template_a copy_a template_b copy_b",
            ),
            "/check-mkdir pkg/generated": LocalCommand(type="check_create_dir", argument="pkg/generated"),
            "/mkdir pkg/generated": LocalCommand(type="create_dir", argument="pkg/generated"),
            "/check-mkdirs pkg/generated assets/icons": LocalCommand(
                type="check_create_dirs",
                argument="pkg/generated assets/icons",
            ),
            "/mkdirs pkg/generated assets/icons": LocalCommand(
                type="create_dirs",
                argument="pkg/generated assets/icons",
            ),
            "/check-rmdir pkg/generated": LocalCommand(type="check_delete_empty_dir", argument="pkg/generated"),
            "/rmdir pkg/generated": LocalCommand(type="delete_empty_dir", argument="pkg/generated"),
            "/check-rmdirs pkg/generated assets/icons": LocalCommand(
                type="check_delete_empty_dirs",
                argument="pkg/generated assets/icons",
            ),
            "/rmdirs pkg/generated assets/icons": LocalCommand(
                type="delete_empty_dirs",
                argument="pkg/generated assets/icons",
            ),
            "/check-executable scripts/tool.sh false": LocalCommand(
                type="check_set_executable",
                argument="scripts/tool.sh false",
            ),
            "/set-executable scripts/tool.sh true": LocalCommand(
                type="set_executable",
                argument="scripts/tool.sh true",
            ),
            "/check-patch app.py '@@ -1 +1 @@\\n-old\\n+new\\n'": LocalCommand(
                type="check_patch",
                argument="app.py '@@ -1 +1 @@\\n-old\\n+new\\n'",
            ),
            "/patch app.py '@@ -1 +1 @@\\n-old\\n+new\\n'": LocalCommand(
                type="patch_file",
                argument="app.py '@@ -1 +1 @@\\n-old\\n+new\\n'",
            ),
            "/check-patches '--- a/app.py\\n+++ b/app.py\\n@@ -1 +1 @@\\n-old\\n+new\\n'": LocalCommand(
                type="check_patches",
                argument="'--- a/app.py\\n+++ b/app.py\\n@@ -1 +1 @@\\n-old\\n+new\\n'",
            ),
            "/patches '--- a/app.py\\n+++ b/app.py\\n@@ -1 +1 @@\\n-old\\n+new\\n'": LocalCommand(
                type="patch_files",
                argument="'--- a/app.py\\n+++ b/app.py\\n@@ -1 +1 @@\\n-old\\n+new\\n'",
            ),
            "/check-regex-replace --ignore-case app.py old 'new\\n'": LocalCommand(
                type="check_regex_replace",
                argument="--ignore-case app.py old 'new\\n'",
            ),
            "/regex-replace --count 1 app.py old new": LocalCommand(
                type="regex_replace",
                argument="--count 1 app.py old new",
            ),
        }

        for raw, expected in cases.items():
            with self.subTest(raw=raw):
                self.assertEqual(parse_file_edit_local_command(raw), expected)
                self.assertEqual(parse_local_command(raw), expected)

    def test_file_edit_parser_handles_empty_arguments_and_ignores_other_commands(self) -> None:
        self.assertEqual(parse_file_edit_local_command("/write"), LocalCommand(type="write_file"))
        self.assertEqual(parse_file_edit_local_command("/check-patches"), LocalCommand(type="check_patches"))
        self.assertIsNone(parse_file_edit_local_command("/session run-1"))
        self.assertIsNone(parse_file_edit_local_command("write app.py data"))


if __name__ == "__main__":
    unittest.main()
