import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from vibeagent.agent_runtime_utils import append_session_event
from vibeagent.checkpoint_session import checkpoint_session_metadata
from vibeagent.cli_interactive_rewind import run_interactive_rewind_command
from vibeagent.command_types import LocalCommand
from vibeagent.session_rewind import list_session_rewind_points, rewind_session
from vibeagent.session_store import read_session_events
from vibeagent.workspace_core import create_run_workspace


class SessionRewindTests(unittest.TestCase):
    def test_checkpoint_session_metadata_records_physical_event_boundary(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-rewind-") as base:
            root = Path(base)
            workspace = create_run_workspace(root)
            append_session_event(workspace.session_dir, "task", {"task": "first"})
            with (workspace.session_dir / "events.jsonl").open("a", encoding="utf-8") as handle:
                handle.write("malformed\n")

            self.assertEqual(
                checkpoint_session_metadata(root, workspace.run_id),
                {"session_run_id": workspace.run_id, "session_event_line": 2},
            )
            self.assertEqual(checkpoint_session_metadata(root, None), {})

    def test_conversation_rewind_copies_only_prefix_and_preserves_source(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-rewind-") as base:
            root = Path(base)
            source = create_run_workspace(root)
            append_session_event(source.session_dir, "task", {"task": "before"})
            append_session_event(source.session_dir, "tool_result", {"value": "checkpoint state"})
            checkpoint_id = self._write_checkpoint(root, source.run_id, 2)
            append_session_event(source.session_dir, "task", {"task": "after"})
            source_path = source.session_dir / "events.jsonl"
            original = source_path.read_bytes()

            def context(run_id: str):
                return run_id, "bounded rewind context", "loaded"

            result = rewind_session(
                root,
                source.run_id,
                checkpoint_id,
                "conversation",
                get_resume_context=context,
            )

            self.assertIsNone(result.error)
            self.assertIsNotNone(result.workspace)
            self.assertEqual(source_path.read_bytes(), original)
            events = read_session_events(root, result.workspace.run_id)  # type: ignore[union-attr]
            self.assertEqual([event.type for event in events], ["task", "tool_result", "session_rewound"])
            self.assertNotIn("after", json.dumps([event.raw for event in events]))
            self.assertEqual(result.context, "bounded rewind context")

    def test_rewind_points_are_scoped_to_active_session(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-rewind-") as base:
            root = Path(base)
            first = create_run_workspace(root)
            second = create_run_workspace(root)
            append_session_event(first.session_dir, "task", {"task": "first"})
            append_session_event(second.session_dir, "task", {"task": "second"})
            first_checkpoint = self._write_checkpoint(root, first.run_id, 1)
            self._write_checkpoint(root, second.run_id, 1)

            points = list_session_rewind_points(root, first.run_id)

            self.assertEqual([point.checkpoint_id for point in points], [first_checkpoint])

    def test_code_rewind_restores_without_creating_session(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-rewind-") as base:
            root = Path(base)
            source = create_run_workspace(root)
            append_session_event(source.session_dir, "task", {"task": "first"})
            checkpoint_id = self._write_checkpoint(root, source.run_id, 1)
            before = {path.name for path in (root / ".vibeagent" / "sessions").iterdir()}

            with (
                patch(
                    "vibeagent.session_rewind.get_check_checkpoint_restore_report",
                    return_value={"ok": True, "canRestore": True},
                ),
                patch(
                    "vibeagent.session_rewind.get_checkpoint_restore_report",
                    return_value={"ok": True, "restored": True},
                ),
            ):
                result = rewind_session(
                    root,
                    source.run_id,
                    checkpoint_id,
                    "code",
                    get_resume_context=lambda *_: (None, None, "unused"),
                )

            after = {path.name for path in (root / ".vibeagent" / "sessions").iterdir()}
            self.assertTrue(result.changed)
            self.assertIsNone(result.workspace)
            self.assertEqual(after, before)

    def test_both_mode_validates_conversation_before_restoring_code(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-rewind-") as base:
            root = Path(base)
            source = create_run_workspace(root)
            append_session_event(source.session_dir, "task", {"task": "first"})
            checkpoint_id = self._write_checkpoint(root, source.run_id, 2)

            with patch("vibeagent.session_rewind.get_checkpoint_restore_report") as restore:
                result = rewind_session(
                    root,
                    source.run_id,
                    checkpoint_id,
                    "both",
                    get_resume_context=lambda *_: (None, None, "unused"),
                )

            self.assertIn("points beyond", result.text)
            restore.assert_not_called()

    def test_interactive_parser_rejects_unknown_mode(self) -> None:
        result = run_interactive_rewind_command(
            LocalCommand(type="rewind", argument="latest everything"),
            project_root=Path.cwd(),
            run_id="run-1",
            get_resume_context=lambda *_: (None, None, "unused"),
        )
        self.assertIsNotNone(result)
        self.assertIn("Usage: /rewind", result.text)  # type: ignore[union-attr]

    @staticmethod
    def _write_checkpoint(root: Path, run_id: str, event_line: int) -> str:
        checkpoint_id = f"2026-08-10T00-00-00-000Z-{run_id[-8:]}"
        checkpoint_dir = root / ".vibeagent" / "checkpoints" / checkpoint_id
        checkpoint_dir.mkdir(parents=True)
        metadata = {
            "id": checkpoint_id,
            "label": "before change",
            "created_at": "2026-08-10T00:00:00Z",
            "head": "abc123",
            "session_run_id": run_id,
            "session_event_line": event_line,
        }
        (checkpoint_dir / "metadata.json").write_text(json.dumps(metadata), encoding="utf-8")
        return checkpoint_id


if __name__ == "__main__":
    unittest.main()
