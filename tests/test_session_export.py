from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from vibeagent.agent_runtime_utils import append_session_event
from vibeagent.session_export import export_session
from vibeagent.session_names import name_session
from vibeagent.workspace_core import create_run_workspace


class SessionExportTests(unittest.TestCase):
    def test_prints_or_atomically_writes_safe_named_session_transcript(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-session-export-") as base:
            root = Path(base)
            workspace = create_run_workspace(root, "run-1")
            append_session_event(
                workspace.session_dir,
                "task",
                {"task": "inspect token sk-secret-value and finish"},
            )
            name_session(root, workspace.run_id, "audit")
            (root / "reports").mkdir()

            printed = export_session(root, "audit")
            written = export_session(root, "audit", "reports/session.txt")

            self.assertEqual(printed.run_id, workspace.run_id)
            self.assertIn("Transcript:", printed.text)
            self.assertNotIn("sk-secret-value", printed.text)
            self.assertEqual(written.path, root / "reports" / "session.txt")
            self.assertEqual(written.path.read_text(encoding="utf-8"), printed.text + "\n")
            self.assertEqual(list((root / "reports").glob("*.tmp")), [])

    def test_rejects_escape_protected_and_symlink_export_paths(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-session-export-") as base:
            root = Path(base) / "project"
            outside = Path(base) / "outside"
            root.mkdir()
            outside.mkdir()
            workspace = create_run_workspace(root, "run-1")
            append_session_event(workspace.session_dir, "task", {"task": "safe task"})
            (root / "linked").symlink_to(outside, target_is_directory=True)

            with self.assertRaisesRegex(ValueError, "escapes"):
                export_session(root, workspace.run_id, "../outside/export.txt")
            with self.assertRaisesRegex(ValueError, "protected"):
                export_session(root, workspace.run_id, ".vibeagent/export.txt")
            with self.assertRaisesRegex(ValueError, "escapes|symbolic link"):
                export_session(root, workspace.run_id, "linked/export.txt")


if __name__ == "__main__":
    unittest.main()
