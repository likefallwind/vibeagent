from __future__ import annotations

from contextlib import redirect_stdout
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from vibeagent.agent_runtime_utils import append_session_event
from vibeagent.cli import main
from vibeagent.session_rewind import check_session_rewind
from vibeagent.session_rewind_commands import (
    get_check_session_rewind_report,
    get_session_rewind_points_report,
    get_session_rewind_report,
)
from vibeagent.workspace_core import create_run_workspace


class SessionRewindCommandTests(unittest.TestCase):
    def test_reports_scoped_points_and_conversation_preflight(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-rewind-command-") as base:
            root = Path(base)
            run_id, checkpoint_id = self._session_with_checkpoint(root)
            other = create_run_workspace(root)
            append_session_event(other.session_dir, "task", {"task": "other"})
            self._write_checkpoint(root, other.run_id, 1, suffix="other001")

            points = get_session_rewind_points_report(root, run_id)
            preview = get_check_session_rewind_report(root, run_id, checkpoint_id, "conversation")
            wrong_mode = get_check_session_rewind_report(root, run_id, checkpoint_id, "everything")

        self.assertTrue(points["ok"])
        self.assertEqual(points["total"], 1)
        self.assertEqual(points["points"][0]["checkpointId"], checkpoint_id)  # type: ignore[index]
        self.assertTrue(preview["canRewind"])
        self.assertFalse(preview["codeWillChange"])
        self.assertTrue(preview["conversationWillBranch"])
        self.assertFalse(wrong_mode["canRewind"])
        self.assertIn("Mode must be", str(wrong_mode["message"]))

    def test_shared_code_preflight_uses_checkpoint_restore_preview(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-rewind-command-") as base:
            root = Path(base)
            run_id, checkpoint_id = self._session_with_checkpoint(root)
            with patch(
                "vibeagent.session_rewind.get_check_checkpoint_restore_report",
                return_value={"ok": True, "canRestore": True, "message": "safe"},
            ) as restore_preview:
                check = check_session_rewind(root, run_id, checkpoint_id, "both")

        self.assertTrue(check.can_rewind)
        self.assertTrue(check.code_will_change)
        self.assertTrue(check.conversation_will_branch)
        self.assertEqual(check.restore_preview["message"], "safe")  # type: ignore[index]
        restore_preview.assert_called_once_with(checkpoint_id, root)

    def test_points_report_bounds_long_session_history(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-rewind-command-") as base:
            root = Path(base)
            workspace = create_run_workspace(root)
            append_session_event(workspace.session_dir, "task", {"task": "before"})
            for index in range(105):
                self._write_checkpoint(
                    root,
                    workspace.run_id,
                    1,
                    suffix=f"point{index:03d}",
                )
            report = get_session_rewind_points_report(root, workspace.run_id)

        self.assertEqual(report["total"], 105)
        self.assertTrue(report["truncated"])
        self.assertEqual(len(report["points"]), 100)  # type: ignore[arg-type]

    def test_conversation_rewind_report_creates_a_new_session(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-rewind-command-") as base:
            root = Path(base)
            run_id, checkpoint_id = self._session_with_checkpoint(root)

            def context(target: str, project_root: Path):
                self.assertEqual(project_root, root)
                return target, "bounded context", "loaded"

            report = get_session_rewind_report(
                root,
                run_id,
                "latest",
                "conversation",
                get_resume_context_fn=context,
            )

        self.assertTrue(report["rewound"])
        self.assertEqual(report["checkpointId"], checkpoint_id)
        self.assertTrue(report["conversationBranched"])
        self.assertFalse(report["codeRestored"])
        self.assertNotEqual(report["newSession"], run_id)

    def test_cli_json_lists_previews_and_executes_conversation_rewind(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-rewind-command-") as base:
            root = Path(base)
            run_id, checkpoint_id = self._session_with_checkpoint(root)

            listed_exit, listed = self._run_json(
                ["--cwd", base, "--session-rewind-points", run_id]
            )
            preview_exit, preview = self._run_json(
                ["--cwd", base, "--check-session-rewind", run_id, checkpoint_id, "conversation"]
            )
            rewind_exit, rewound = self._run_json(
                ["--cwd", base, "--session-rewind", run_id, checkpoint_id, "conversation"]
            )

        self.assertEqual(listed_exit, 0)
        self.assertEqual(listed["sessionRewindPoints"]["total"], 1)
        self.assertEqual(preview_exit, 0)
        self.assertTrue(preview["checkSessionRewind"]["canRewind"])
        self.assertEqual(rewind_exit, 0)
        self.assertTrue(rewound["sessionRewind"]["rewound"])
        self.assertNotEqual(rewound["sessionRewind"]["newSession"], run_id)

    def test_invalid_or_missing_session_reports_fail_without_mutation(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-rewind-command-") as base:
            root = Path(base)
            invalid = get_session_rewind_points_report(root, "../escape")
            missing = get_session_rewind_points_report(root, "missing")
            exit_code, payload = self._run_json(
                ["--cwd", base, "--session-rewind-points", "missing"]
            )

        self.assertFalse(invalid["ok"])
        self.assertIn("Invalid session id", str(invalid["message"]))
        self.assertFalse(missing["ok"])
        self.assertEqual(exit_code, 1)
        self.assertFalse(payload["success"])

    @staticmethod
    def _run_json(arguments: list[str]) -> tuple[int, dict[str, object]]:
        stdout = io.StringIO()
        with redirect_stdout(stdout):
            exit_code = main(["--json", *arguments])
        return exit_code, json.loads(stdout.getvalue())

    @classmethod
    def _session_with_checkpoint(cls, root: Path) -> tuple[str, str]:
        workspace = create_run_workspace(root)
        append_session_event(workspace.session_dir, "task", {"task": "before"})
        append_session_event(workspace.session_dir, "tool_result", {"value": "checkpoint"})
        checkpoint_id = cls._write_checkpoint(root, workspace.run_id, 2)
        append_session_event(workspace.session_dir, "task", {"task": "after"})
        return workspace.run_id, checkpoint_id

    @staticmethod
    def _write_checkpoint(
        root: Path,
        run_id: str,
        event_line: int,
        *,
        suffix: str = "rewind01",
    ) -> str:
        checkpoint_id = f"2026-08-11T00-00-00-000Z-{suffix}"
        directory = root / ".vibeagent" / "checkpoints" / checkpoint_id
        directory.mkdir(parents=True)
        directory.joinpath("metadata.json").write_text(
            json.dumps(
                {
                    "id": checkpoint_id,
                    "label": "before change",
                    "created_at": "2026-08-11T00:00:00Z",
                    "head": "abc123",
                    "session_run_id": run_id,
                    "session_event_line": event_line,
                }
            ),
            encoding="utf-8",
        )
        return checkpoint_id


if __name__ == "__main__":
    unittest.main()
