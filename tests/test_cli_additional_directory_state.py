from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from vibeagent.cli_additional_directory_state import update_additional_directory_state


class CliAdditionalDirectoryStateTests(unittest.TestCase):
    def test_add_list_remove_and_clear_directories(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-add-dir-state-") as base:
            root = Path(base) / "project"
            shared = Path(base) / "shared files"
            other = Path(base) / "other"
            root.mkdir()
            shared.mkdir()
            other.mkdir()

            added = update_additional_directory_state((), '"../shared files"', project_root=root)
            listed = update_additional_directory_state(added.directories, None, project_root=root)
            second = update_additional_directory_state(added.directories, "add ../other", project_root=root)
            removed = update_additional_directory_state(second.directories, 'remove "../shared files"', project_root=root)
            cleared = update_additional_directory_state(removed.directories, "clear", project_root=root)

        self.assertTrue(added.changed)
        self.assertEqual(added.directories, (shared.resolve(),))
        self.assertIn(str(shared.resolve()), listed.text)
        self.assertEqual(second.directories, (shared.resolve(), other.resolve()))
        self.assertEqual(removed.directories, (other.resolve(),))
        self.assertTrue(cleared.changed)
        self.assertEqual(cleared.directories, ())

    def test_duplicate_primary_and_invalid_paths_do_not_change_state(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-add-dir-state-") as base:
            root = Path(base) / "project"
            shared = Path(base) / "shared"
            root.mkdir()
            shared.mkdir()
            initial = (shared.resolve(),)

            duplicate = update_additional_directory_state(initial, "../shared", project_root=root)
            primary = update_additional_directory_state(initial, ".", project_root=root)
            missing = update_additional_directory_state(initial, "../missing", project_root=root)
            bad_remove = update_additional_directory_state(initial, "remove ../other", project_root=root)

        for update in (duplicate, primary, missing, bad_remove):
            self.assertFalse(update.changed)
            self.assertEqual(update.directories, initial)

    def test_rejects_ambiguous_arguments(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-add-dir-state-") as base:
            root = Path(base)
            result = update_additional_directory_state((), "one two", project_root=root)

        self.assertFalse(result.changed)
        self.assertEqual(result.text, "Usage: /add-dir <path>")


if __name__ == "__main__":
    unittest.main()
