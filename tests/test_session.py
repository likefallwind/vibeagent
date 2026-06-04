import json
import os
import tempfile
import unittest
from pathlib import Path

from vibeagent.session import (
    format_session_summary,
    format_sessions,
    list_sessions,
    read_session_events,
    summarize_session,
)


def write_events(project_root: Path, run_id: str, rows: list[dict | str], mtime: int | None = None) -> Path:
    session_dir = project_root / ".vibeagent" / "sessions" / run_id
    session_dir.mkdir(parents=True, exist_ok=True)
    events_path = session_dir / "events.jsonl"
    lines = [row if isinstance(row, str) else json.dumps(row, ensure_ascii=False) for row in rows]
    events_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    if mtime is not None:
        os.utime(events_path, (mtime, mtime))
    return events_path


class SessionTests(unittest.TestCase):
    def test_list_sessions_returns_newest_first_with_counts(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-session-") as base:
            root = Path(base)
            write_events(root, "old-run", [{"type": "model", "iteration": 1, "content": []}], mtime=100)
            write_events(
                root,
                "new-run",
                [
                    {"type": "model", "iteration": 1, "content": []},
                    "{bad json",
                ],
                mtime=200,
            )

            sessions = list_sessions(root)

        self.assertEqual([session.run_id for session in sessions], ["new-run", "old-run"])
        self.assertEqual(sessions[0].event_count, 1)
        self.assertEqual(sessions[0].malformed_count, 1)

    def test_summarize_session_reads_model_tool_approval_and_final_events(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-session-") as base:
            root = Path(base)
            write_events(
                root,
                "run-1",
                [
                    {
                        "type": "model",
                        "iteration": 1,
                        "content": [
                            {
                                "type": "tool_call",
                                "id": "1",
                                "name": "write_file",
                                "input": {"path": "secret.txt", "content": "SECRET_CONTENT"},
                            }
                        ],
                    },
                    {
                        "type": "tool_call",
                        "iteration": 1,
                        "id": "1",
                        "name": "write_file",
                        "input": {"path": "secret.txt", "content": "SECRET_CONTENT"},
                    },
                    {
                        "type": "approval_requested",
                        "iteration": 1,
                        "request": {"action_type": "write_file", "target": "secret.txt"},
                    },
                    {"type": "approval_decision", "iteration": 1, "decision": {"approved": True}},
                    {
                        "type": "tool_result",
                        "iteration": 1,
                        "id": "1",
                        "name": "write_file",
                        "result": {"kind": "write_file", "path": "secret.txt", "ok": True},
                    },
                    {
                        "type": "tool_result",
                        "iteration": 2,
                        "id": "2",
                        "name": "finish",
                        "result": {"kind": "finish", "message": "Done."},
                    },
                ],
            )

            summary = summarize_session(root, "run-1")
            text = format_session_summary(summary)

        self.assertTrue(summary.completed)
        self.assertFalse(summary.failed)
        self.assertEqual(summary.iterations, 2)
        self.assertEqual(summary.tool_calls, ["write_file"])
        self.assertEqual(summary.approvals_requested, 1)
        self.assertEqual(summary.approvals_approved, 1)
        self.assertEqual(summary.final_message, "Done.")
        self.assertIn("write_file", text)
        self.assertIn("final: Done.", text)
        self.assertNotIn("SECRET_CONTENT", text)

    def test_missing_and_malformed_session_rows_do_not_crash(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-session-") as base:
            root = Path(base)
            write_events(root, "bad-run", ["not json", '["not", "object"]'])

            missing = summarize_session(root, "missing-run")
            events = read_session_events(root, "bad-run")
            bad_summary = summarize_session(root, "bad-run")

        self.assertFalse(missing.exists)
        self.assertEqual(missing.event_count, 0)
        self.assertEqual(len(events), 2)
        self.assertTrue(all(event.malformed for event in events))
        self.assertEqual(bad_summary.malformed_count, 2)
        self.assertEqual(bad_summary.event_count, 0)

    def test_format_sessions_omits_full_payloads_and_handles_empty_project(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-session-") as base:
            root = Path(base)
            self.assertEqual(format_sessions(root), "No sessions found.")
            write_events(
                root,
                "run-1",
                [
                    {
                        "type": "tool_call",
                        "iteration": 1,
                        "name": "write_file",
                        "input": {"path": "note.txt", "content": "SHOULD_NOT_PRINT"},
                    }
                ],
            )

            text = format_sessions(root)

        self.assertIn("run-1", text)
        self.assertIn("events=1", text)
        self.assertNotIn("SHOULD_NOT_PRINT", text)


if __name__ == "__main__":
    unittest.main()
