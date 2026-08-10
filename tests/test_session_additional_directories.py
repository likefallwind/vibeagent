from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from vibeagent.agent_runtime_utils import append_session_event
from vibeagent.session_additional_directories import (
    merge_additional_directories,
    record_session_additional_directories,
    restore_session_additional_directories,
)
from vibeagent.session_store import read_session_events


class SessionAdditionalDirectoriesTests(unittest.TestCase):
    def test_latest_directory_event_overrides_task_state_and_clear_persists(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-session-dirs-") as base:
            root = Path(base) / "project"
            shared = Path(base) / "shared"
            root.mkdir()
            shared.mkdir()
            session_dir = root / ".vibeagent" / "sessions" / "run-1"
            append_session_event(
                session_dir,
                "task",
                {"task": "inspect", "additional_directories": [str(shared.resolve())]},
            )

            first = restore_session_additional_directories(root, "run-1")
            record_session_additional_directories(root, "run-1", ())
            cleared = restore_session_additional_directories(root, "run-1")

        self.assertEqual(first.directories, (shared.resolve(),))
        self.assertEqual(cleared.directories, ())
        self.assertEqual(cleared.warnings, ())

    def test_missing_and_malformed_stored_directories_are_not_restored(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-session-dirs-") as base:
            root = Path(base) / "project"
            root.mkdir()
            session_dir = root / ".vibeagent" / "sessions" / "run-1"
            append_session_event(
                session_dir,
                "additional_directories_updated",
                {"additional_directories": [str(Path(base) / "missing")]},
            )
            missing = restore_session_additional_directories(root, "run-1")
            append_session_event(
                session_dir,
                "additional_directories_updated",
                {"additional_directories": "not-a-list"},
            )
            malformed = restore_session_additional_directories(root, "run-1")

        self.assertEqual(missing.directories, ())
        self.assertTrue(missing.warnings)
        self.assertEqual(malformed.directories, ())
        self.assertIn("malformed", malformed.message or "")

    def test_record_writes_absolute_directory_event(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-session-dirs-") as base:
            root = Path(base) / "project"
            shared = Path(base) / "shared"
            root.mkdir()
            shared.mkdir()

            record_session_additional_directories(root, "run-1", (shared,))
            event = read_session_events(root, "run-1")[-1]

        self.assertEqual(event.type, "additional_directories_updated")
        self.assertEqual(event.payload["additional_directories"], [str(shared.resolve())])

    def test_merge_reports_a_directory_removed_after_initial_resolution(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-session-dirs-") as base:
            root = Path(base) / "project"
            removed = Path(base) / "removed"
            root.mkdir()
            removed.mkdir()
            removed.rmdir()

            with self.assertRaisesRegex(ValueError, "Cannot restore additional working directories"):
                merge_additional_directories(root, (removed,), ())


if __name__ == "__main__":
    unittest.main()
