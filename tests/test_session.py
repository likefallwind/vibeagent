import json
import os
import tempfile
import unittest
from pathlib import Path

from vibeagent.session import (
    build_session_resume_context,
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
                    {"type": "task", "task": "Fix the failing test."},
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
        self.assertEqual(summary.task, "Fix the failing test.")
        self.assertEqual(summary.tool_calls, ["write_file"])
        self.assertEqual(summary.approvals_requested, 1)
        self.assertEqual(summary.approvals_approved, 1)
        self.assertEqual(summary.final_message, "Done.")
        self.assertIn("write_file", text)
        self.assertIn("task: Fix the failing test.", text)
        self.assertIn("final: Done.", text)
        self.assertNotIn("SECRET_CONTENT", text)

    def test_build_session_resume_context_uses_summary_without_tool_payloads(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-session-") as base:
            root = Path(base)
            write_events(
                root,
                "run-1",
                [
                    {"type": "task", "task": "Refactor auth flow."},
                    {"type": "tool_call", "iteration": 1, "id": "1", "name": "read_file", "input": {"path": "SECRET_PATH"}},
                    {
                        "type": "tool_result",
                        "iteration": 2,
                        "id": "2",
                        "name": "finish",
                        "result": {"kind": "finish", "message": "Refactor complete."},
                    },
                ],
            )

            context = build_session_resume_context(root, "run-1")

        self.assertIn("session: run-1", context)
        self.assertIn("task: Refactor auth flow.", context)
        self.assertIn("tools: read_file", context)
        self.assertIn("final: Refactor complete.", context)
        self.assertNotIn("SECRET_PATH", context)

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

    def test_summarize_session_marks_failed_write_files_result(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-session-") as base:
            root = Path(base)
            write_events(
                root,
                "run-1",
                [
                    {
                        "type": "tool_call",
                        "iteration": 1,
                        "id": "1",
                        "name": "write_files",
                        "input": {"files": [{"path": "SECRET_PATH", "content": "SECRET_CONTENT"}]},
                    },
                    {
                        "type": "tool_result",
                        "iteration": 1,
                        "id": "1",
                        "name": "write_files",
                        "result": {"kind": "write_files", "ok": False, "message": "write failed"},
                    },
                ],
            )

            summary = summarize_session(root, "run-1")
            text = format_session_summary(summary)

        self.assertFalse(summary.completed)
        self.assertTrue(summary.failed)
        self.assertIn("write_files", text)
        self.assertNotIn("SECRET_PATH", text)
        self.assertNotIn("SECRET_CONTENT", text)

    def test_summarize_session_marks_failed_patch_file_result(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-session-") as base:
            root = Path(base)
            write_events(
                root,
                "run-1",
                [
                    {
                        "type": "tool_call",
                        "iteration": 1,
                        "id": "1",
                        "name": "patch_file",
                        "input": {"path": "app.py", "patch": "SECRET_PATCH"},
                    },
                    {
                        "type": "tool_result",
                        "iteration": 1,
                        "id": "1",
                        "name": "patch_file",
                        "result": {"kind": "patch_file", "path": "app.py", "ok": False},
                    },
                ],
            )

            summary = summarize_session(root, "run-1")
            text = format_session_summary(summary)

        self.assertFalse(summary.completed)
        self.assertTrue(summary.failed)
        self.assertIn("patch_file", text)
        self.assertNotIn("SECRET_PATCH", text)

    def test_summarize_session_marks_failed_multi_edit_result(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-session-") as base:
            root = Path(base)
            write_events(
                root,
                "run-1",
                [
                    {
                        "type": "tool_call",
                        "iteration": 1,
                        "id": "1",
                        "name": "multi_edit_file",
                        "input": {"path": "app.py", "edits": [{"old": "SECRET_OLD", "new": "SECRET_NEW"}]},
                    },
                    {
                        "type": "tool_result",
                        "iteration": 1,
                        "id": "1",
                        "name": "multi_edit_file",
                        "result": {"kind": "multi_edit_file", "path": "app.py", "ok": False},
                    },
                ],
            )

            summary = summarize_session(root, "run-1")
            text = format_session_summary(summary)

        self.assertFalse(summary.completed)
        self.assertTrue(summary.failed)
        self.assertIn("multi_edit_file", text)
        self.assertNotIn("SECRET_OLD", text)

    def test_summarize_session_marks_failed_replace_lines_result(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-session-") as base:
            root = Path(base)
            write_events(
                root,
                "run-1",
                [
                    {
                        "type": "tool_call",
                        "iteration": 1,
                        "id": "1",
                        "name": "replace_lines",
                        "input": {"path": "app.py", "start_line": 1, "end_line": 1, "content": "SECRET_CONTENT"},
                    },
                    {
                        "type": "tool_result",
                        "iteration": 1,
                        "id": "1",
                        "name": "replace_lines",
                        "result": {"kind": "replace_lines", "path": "app.py", "ok": False},
                    },
                ],
            )

            summary = summarize_session(root, "run-1")
            text = format_session_summary(summary)

        self.assertFalse(summary.completed)
        self.assertTrue(summary.failed)
        self.assertIn("replace_lines", text)
        self.assertNotIn("SECRET_CONTENT", text)

    def test_summarize_session_marks_failed_replace_python_definition_result(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-session-") as base:
            root = Path(base)
            write_events(
                root,
                "run-1",
                [
                    {
                        "type": "tool_call",
                        "iteration": 1,
                        "id": "1",
                        "name": "replace_python_definition",
                        "input": {"symbol": "run_agent", "content": "SECRET_CONTENT"},
                    },
                    {
                        "type": "tool_result",
                        "iteration": 1,
                        "id": "1",
                        "name": "replace_python_definition",
                        "result": {"kind": "replace_python_definition", "symbol": "run_agent", "ok": False},
                    },
                ],
            )

            summary = summarize_session(root, "run-1")
            text = format_session_summary(summary)

        self.assertFalse(summary.completed)
        self.assertTrue(summary.failed)
        self.assertIn("replace_python_definition", text)
        self.assertNotIn("SECRET_CONTENT", text)

    def test_summarize_session_marks_failed_insert_lines_result(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-session-") as base:
            root = Path(base)
            write_events(
                root,
                "run-1",
                [
                    {
                        "type": "tool_call",
                        "iteration": 1,
                        "id": "1",
                        "name": "insert_lines",
                        "input": {"path": "app.py", "line": 2, "content": "SECRET_CONTENT"},
                    },
                    {
                        "type": "tool_result",
                        "iteration": 1,
                        "id": "1",
                        "name": "insert_lines",
                        "result": {"kind": "insert_lines", "path": "app.py", "ok": False},
                    },
                ],
            )

            summary = summarize_session(root, "run-1")
            text = format_session_summary(summary)

        self.assertFalse(summary.completed)
        self.assertTrue(summary.failed)
        self.assertIn("insert_lines", text)
        self.assertNotIn("SECRET_CONTENT", text)

    def test_summarize_session_marks_failed_check_patch_result(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-session-") as base:
            root = Path(base)
            write_events(
                root,
                "run-1",
                [
                    {
                        "type": "tool_call",
                        "iteration": 1,
                        "id": "1",
                        "name": "check_patch",
                        "input": {"path": "app.py", "patch": "SECRET_PATCH"},
                    },
                    {
                        "type": "tool_result",
                        "iteration": 1,
                        "id": "1",
                        "name": "check_patch",
                        "result": {"kind": "check_patch", "path": "app.py", "ok": False},
                    },
                ],
            )

            summary = summarize_session(root, "run-1")
            text = format_session_summary(summary)

        self.assertFalse(summary.completed)
        self.assertTrue(summary.failed)
        self.assertIn("check_patch", text)
        self.assertNotIn("SECRET_PATCH", text)

    def test_summarize_session_marks_failed_patch_files_result(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-session-") as base:
            root = Path(base)
            write_events(
                root,
                "run-1",
                [
                    {
                        "type": "tool_call",
                        "iteration": 1,
                        "id": "1",
                        "name": "patch_files",
                        "input": {"patch": "SECRET_PATCH"},
                    },
                    {
                        "type": "tool_result",
                        "iteration": 1,
                        "id": "1",
                        "name": "patch_files",
                        "result": {"kind": "patch_files", "files": ["app.py"], "ok": False},
                    },
                ],
            )

            summary = summarize_session(root, "run-1")
            text = format_session_summary(summary)

        self.assertFalse(summary.completed)
        self.assertTrue(summary.failed)
        self.assertIn("patch_files", text)
        self.assertNotIn("SECRET_PATCH", text)

    def test_summarize_session_marks_failed_check_patches_result(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-session-") as base:
            root = Path(base)
            write_events(
                root,
                "run-1",
                [
                    {
                        "type": "tool_call",
                        "iteration": 1,
                        "id": "1",
                        "name": "check_patches",
                        "input": {"patch": "SECRET_PATCH"},
                    },
                    {
                        "type": "tool_result",
                        "iteration": 1,
                        "id": "1",
                        "name": "check_patches",
                        "result": {"kind": "check_patches", "files": ["app.py"], "ok": False},
                    },
                ],
            )

            summary = summarize_session(root, "run-1")
            text = format_session_summary(summary)

        self.assertFalse(summary.completed)
        self.assertTrue(summary.failed)
        self.assertIn("check_patches", text)
        self.assertNotIn("SECRET_PATCH", text)

    def test_summarize_session_marks_failed_lifecycle_results(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-session-") as base:
            root = Path(base)
            write_events(
                root,
                "run-1",
                [
                    {
                        "type": "tool_call",
                        "iteration": 1,
                        "id": "1",
                        "name": "delete_file",
                        "input": {"path": "SECRET_PATH"},
                    },
                    {
                        "type": "tool_result",
                        "iteration": 1,
                        "id": "1",
                        "name": "delete_file",
                        "result": {"kind": "delete_file", "path": "old.py", "ok": False},
                    },
                    {
                        "type": "tool_call",
                        "iteration": 2,
                        "id": "2",
                        "name": "move_file",
                        "input": {"source": "SECRET_PATH", "destination": "SECRET_DEST"},
                    },
                    {
                        "type": "tool_result",
                        "iteration": 2,
                        "id": "2",
                        "name": "move_file",
                        "result": {"kind": "move_file", "source": "old.py", "destination": "new.py", "ok": False},
                    },
                ],
            )

            summary = summarize_session(root, "run-1")
            text = format_session_summary(summary)

        self.assertFalse(summary.completed)
        self.assertTrue(summary.failed)
        self.assertIn("delete_file", text)
        self.assertIn("move_file", text)
        self.assertNotIn("SECRET_PATH", text)
        self.assertNotIn("SECRET_DEST", text)

    def test_summarize_session_marks_failed_git_read_results(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-session-") as base:
            root = Path(base)
            write_events(
                root,
                "run-1",
                [
                    {
                        "type": "tool_call",
                        "iteration": 1,
                        "id": "1",
                        "name": "git_status",
                        "input": {},
                    },
                    {
                        "type": "tool_result",
                        "iteration": 1,
                        "id": "1",
                        "name": "git_status",
                        "result": {"kind": "git_status", "ok": False, "status": "", "message": "not a git repo"},
                    },
                    {
                        "type": "tool_call",
                        "iteration": 2,
                        "id": "2",
                        "name": "git_changes",
                        "input": {},
                    },
                    {
                        "type": "tool_result",
                        "iteration": 2,
                        "id": "2",
                        "name": "git_changes",
                        "result": {"kind": "git_changes", "ok": False, "files": [], "status": "", "message": "not a git repo"},
                    },
                    {
                        "type": "tool_call",
                        "iteration": 3,
                        "id": "3",
                        "name": "git_diff",
                        "input": {"path": "SECRET_PATH"},
                    },
                    {
                        "type": "tool_result",
                        "iteration": 3,
                        "id": "3",
                        "name": "git_diff",
                        "result": {
                            "kind": "git_diff",
                            "ok": False,
                            "diff": "",
                            "path": "app.py",
                            "staged": False,
                            "truncated": False,
                            "max_output_chars": 12000,
                        },
                    },
                    {
                        "type": "tool_call",
                        "iteration": 4,
                        "id": "4",
                        "name": "git_log",
                        "input": {"path": "SECRET_PATH"},
                    },
                    {
                        "type": "tool_result",
                        "iteration": 4,
                        "id": "4",
                        "name": "git_log",
                        "result": {"kind": "git_log", "ok": False, "log": "", "path": "app.py", "max_count": 5},
                    },
                    {
                        "type": "tool_call",
                        "iteration": 5,
                        "id": "5",
                        "name": "git_show",
                        "input": {"rev": "SECRET_REV", "path": "SECRET_PATH"},
                    },
                    {
                        "type": "tool_result",
                        "iteration": 5,
                        "id": "5",
                        "name": "git_show",
                        "result": {
                            "kind": "git_show",
                            "ok": False,
                            "output": "",
                            "rev": "HEAD",
                            "path": "app.py",
                            "truncated": False,
                            "max_output_chars": 12000,
                        },
                    },
                    {
                        "type": "tool_call",
                        "iteration": 6,
                        "id": "6",
                        "name": "git_blame",
                        "input": {"path": "SECRET_PATH"},
                    },
                    {
                        "type": "tool_result",
                        "iteration": 6,
                        "id": "6",
                        "name": "git_blame",
                        "result": {
                            "kind": "git_blame",
                            "ok": False,
                            "blame": "",
                            "path": "../outside.py",
                            "start_line": None,
                            "line_count": None,
                            "truncated": False,
                            "max_output_chars": 12000,
                        },
                    },
                ],
            )

            summary = summarize_session(root, "run-1")
            text = format_session_summary(summary)

        self.assertFalse(summary.completed)
        self.assertTrue(summary.failed)
        self.assertIn("git_status", text)
        self.assertIn("git_changes", text)
        self.assertIn("git_diff", text)
        self.assertIn("git_log", text)
        self.assertIn("git_show", text)
        self.assertIn("git_blame", text)
        self.assertNotIn("SECRET_PATH", text)
        self.assertNotIn("SECRET_REV", text)

    def test_summarize_session_marks_failed_session_summary_result(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-session-") as base:
            root = Path(base)
            write_events(
                root,
                "run-1",
                [
                    {
                        "type": "tool_call",
                        "iteration": 1,
                        "id": "1",
                        "name": "session_summary",
                        "input": {"run_id": "SECRET_RUN"},
                    },
                    {
                        "type": "tool_result",
                        "iteration": 1,
                        "id": "1",
                        "name": "session_summary",
                        "result": {"kind": "session_summary", "run_id": "../bad", "ok": False},
                    },
                ],
            )

            summary = summarize_session(root, "run-1")
            text = format_session_summary(summary)

        self.assertFalse(summary.completed)
        self.assertTrue(summary.failed)
        self.assertIn("session_summary", text)
        self.assertNotIn("SECRET_RUN", text)

    def test_summarize_session_marks_failed_glob_result(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-session-") as base:
            root = Path(base)
            write_events(
                root,
                "run-1",
                [
                    {
                        "type": "tool_call",
                        "iteration": 1,
                        "id": "1",
                        "name": "glob",
                        "input": {"pattern": "SECRET_PATTERN"},
                    },
                    {
                        "type": "tool_result",
                        "iteration": 1,
                        "id": "1",
                        "name": "glob",
                        "result": {"kind": "glob", "pattern": "../*.py", "ok": False},
                    },
                ],
            )

            summary = summarize_session(root, "run-1")
            text = format_session_summary(summary)

        self.assertFalse(summary.completed)
        self.assertTrue(summary.failed)
        self.assertIn("glob", text)
        self.assertNotIn("SECRET_PATTERN", text)

    def test_summarize_session_marks_failed_list_tree_result(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-session-") as base:
            root = Path(base)
            write_events(
                root,
                "run-1",
                [
                    {
                        "type": "tool_call",
                        "iteration": 1,
                        "id": "1",
                        "name": "list_tree",
                        "input": {"path": "SECRET_PATH"},
                    },
                    {
                        "type": "tool_result",
                        "iteration": 1,
                        "id": "1",
                        "name": "list_tree",
                        "result": {"kind": "list_tree", "path": "../outside", "ok": False},
                    },
                ],
            )

            summary = summarize_session(root, "run-1")
            text = format_session_summary(summary)

        self.assertFalse(summary.completed)
        self.assertTrue(summary.failed)
        self.assertIn("list_tree", text)
        self.assertNotIn("SECRET_PATH", text)

    def test_summarize_session_marks_failed_repo_map_result(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-session-") as base:
            root = Path(base)
            write_events(
                root,
                "run-1",
                [
                    {
                        "type": "tool_call",
                        "iteration": 1,
                        "id": "1",
                        "name": "repo_map",
                        "input": {"path": "SECRET_PATH"},
                    },
                    {
                        "type": "tool_result",
                        "iteration": 1,
                        "id": "1",
                        "name": "repo_map",
                        "result": {"kind": "repo_map", "path": "../outside", "ok": False},
                    },
                ],
            )

            summary = summarize_session(root, "run-1")
            text = format_session_summary(summary)

        self.assertFalse(summary.completed)
        self.assertTrue(summary.failed)
        self.assertIn("repo_map", text)
        self.assertNotIn("SECRET_PATH", text)

    def test_summarize_session_marks_failed_read_files_result(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-session-") as base:
            root = Path(base)
            write_events(
                root,
                "run-1",
                [
                    {
                        "type": "tool_call",
                        "iteration": 1,
                        "id": "1",
                        "name": "read_files",
                        "input": {"paths": ["SECRET_PATH"]},
                    },
                    {
                        "type": "tool_result",
                        "iteration": 1,
                        "id": "1",
                        "name": "read_files",
                        "result": {
                            "kind": "read_files",
                            "files": [{"path": "missing.py", "ok": False, "message": "missing"}],
                        },
                    },
                ],
            )

            summary = summarize_session(root, "run-1")
            text = format_session_summary(summary)

        self.assertFalse(summary.completed)
        self.assertTrue(summary.failed)
        self.assertIn("read_files", text)
        self.assertNotIn("SECRET_PATH", text)

    def test_summarize_session_marks_failed_read_file_ranges_result(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-session-") as base:
            root = Path(base)
            write_events(
                root,
                "run-1",
                [
                    {
                        "type": "tool_call",
                        "iteration": 1,
                        "id": "1",
                        "name": "read_file_ranges",
                        "input": {"ranges": [{"path": "SECRET_PATH", "start_line": 1}]},
                    },
                    {
                        "type": "tool_result",
                        "iteration": 1,
                        "id": "1",
                        "name": "read_file_ranges",
                        "result": {
                            "kind": "read_file_ranges",
                            "ranges": [{"path": "missing.py", "start_line": 1, "line_count": 1, "ok": False}],
                        },
                    },
                ],
            )

            summary = summarize_session(root, "run-1")
            text = format_session_summary(summary)

        self.assertFalse(summary.completed)
        self.assertTrue(summary.failed)
        self.assertIn("read_file_ranges", text)
        self.assertNotIn("SECRET_PATH", text)

    def test_summarize_session_marks_failed_file_info_result(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-session-") as base:
            root = Path(base)
            write_events(
                root,
                "run-1",
                [
                    {
                        "type": "tool_call",
                        "iteration": 1,
                        "id": "1",
                        "name": "file_info",
                        "input": {"paths": ["SECRET_PATH"]},
                    },
                    {
                        "type": "tool_result",
                        "iteration": 1,
                        "id": "1",
                        "name": "file_info",
                        "result": {
                            "kind": "file_info",
                            "files": [{"path": "missing.py", "ok": False, "message": "missing"}],
                        },
                    },
                ],
            )

            summary = summarize_session(root, "run-1")
            text = format_session_summary(summary)

        self.assertFalse(summary.completed)
        self.assertTrue(summary.failed)
        self.assertIn("file_info", text)
        self.assertNotIn("SECRET_PATH", text)

    def test_summarize_session_marks_failed_python_symbols_result(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-session-") as base:
            root = Path(base)
            write_events(
                root,
                "run-1",
                [
                    {
                        "type": "tool_call",
                        "iteration": 1,
                        "id": "1",
                        "name": "python_symbols",
                        "input": {"paths": ["SECRET_PATH"]},
                    },
                    {
                        "type": "tool_result",
                        "iteration": 1,
                        "id": "1",
                        "name": "python_symbols",
                        "result": {
                            "kind": "python_symbols",
                            "files": [{"path": "missing.py", "ok": False, "message": "missing"}],
                        },
                    },
                ],
            )

            summary = summarize_session(root, "run-1")
            text = format_session_summary(summary)

        self.assertFalse(summary.completed)
        self.assertTrue(summary.failed)
        self.assertIn("python_symbols", text)
        self.assertNotIn("SECRET_PATH", text)

    def test_summarize_session_marks_failed_python_check_result(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-session-") as base:
            root = Path(base)
            write_events(
                root,
                "run-1",
                [
                    {
                        "type": "tool_call",
                        "iteration": 1,
                        "id": "1",
                        "name": "python_check",
                        "input": {"path": "SECRET_PATH"},
                    },
                    {
                        "type": "tool_result",
                        "iteration": 1,
                        "id": "1",
                        "name": "python_check",
                        "result": {"kind": "python_check", "path": "src", "ok": False},
                    },
                ],
            )

            summary = summarize_session(root, "run-1")
            text = format_session_summary(summary)

        self.assertFalse(summary.completed)
        self.assertTrue(summary.failed)
        self.assertIn("python_check", text)
        self.assertNotIn("SECRET_PATH", text)

    def test_summarize_session_marks_failed_python_dependencies_result(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-session-") as base:
            root = Path(base)
            write_events(
                root,
                "run-1",
                [
                    {
                        "type": "tool_call",
                        "iteration": 1,
                        "id": "1",
                        "name": "python_dependencies",
                        "input": {"path": "SECRET_PATH"},
                    },
                    {
                        "type": "tool_result",
                        "iteration": 1,
                        "id": "1",
                        "name": "python_dependencies",
                        "result": {"kind": "python_dependencies", "path": "src", "ok": False},
                    },
                ],
            )

            summary = summarize_session(root, "run-1")
            text = format_session_summary(summary)

        self.assertFalse(summary.completed)
        self.assertTrue(summary.failed)
        self.assertIn("python_dependencies", text)
        self.assertNotIn("SECRET_PATH", text)

    def test_summarize_session_marks_failed_python_definitions_result(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-session-") as base:
            root = Path(base)
            write_events(
                root,
                "run-1",
                [
                    {
                        "type": "tool_call",
                        "iteration": 1,
                        "id": "1",
                        "name": "python_definitions",
                        "input": {"symbol": "SECRET_SYMBOL"},
                    },
                    {
                        "type": "tool_result",
                        "iteration": 1,
                        "id": "1",
                        "name": "python_definitions",
                        "result": {"kind": "python_definitions", "symbol": "bad-name", "ok": False},
                    },
                ],
            )

            summary = summarize_session(root, "run-1")
            text = format_session_summary(summary)

        self.assertFalse(summary.completed)
        self.assertTrue(summary.failed)
        self.assertIn("python_definitions", text)
        self.assertNotIn("SECRET_SYMBOL", text)

    def test_summarize_session_marks_failed_python_calls_result(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-session-") as base:
            root = Path(base)
            write_events(
                root,
                "run-1",
                [
                    {
                        "type": "tool_call",
                        "iteration": 1,
                        "id": "1",
                        "name": "python_calls",
                        "input": {"symbol": "SECRET_SYMBOL"},
                    },
                    {
                        "type": "tool_result",
                        "iteration": 1,
                        "id": "1",
                        "name": "python_calls",
                        "result": {"kind": "python_calls", "symbol": "bad-name", "ok": False},
                    },
                ],
            )

            summary = summarize_session(root, "run-1")
            text = format_session_summary(summary)

        self.assertFalse(summary.completed)
        self.assertTrue(summary.failed)
        self.assertIn("python_calls", text)
        self.assertNotIn("SECRET_SYMBOL", text)

    def test_summarize_session_marks_failed_python_call_graph_result(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-session-") as base:
            root = Path(base)
            write_events(
                root,
                "run-1",
                [
                    {
                        "type": "tool_call",
                        "iteration": 1,
                        "id": "1",
                        "name": "python_call_graph",
                        "input": {"path": "SECRET_PATH"},
                    },
                    {
                        "type": "tool_result",
                        "iteration": 1,
                        "id": "1",
                        "name": "python_call_graph",
                        "result": {"kind": "python_call_graph", "path": "../outside", "ok": False},
                    },
                ],
            )

            summary = summarize_session(root, "run-1")
            text = format_session_summary(summary)

        self.assertFalse(summary.completed)
        self.assertTrue(summary.failed)
        self.assertIn("python_call_graph", text)
        self.assertNotIn("SECRET_PATH", text)

    def test_summarize_session_marks_failed_review_changes_result(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-session-") as base:
            root = Path(base)
            write_events(
                root,
                "run-1",
                [
                    {
                        "type": "tool_call",
                        "iteration": 1,
                        "id": "1",
                        "name": "review_changes",
                        "input": {"max_files": 200, "path": "SECRET_PATH"},
                    },
                    {
                        "type": "tool_result",
                        "iteration": 1,
                        "id": "1",
                        "name": "review_changes",
                        "result": {"kind": "review_changes", "ok": False, "message": "diff check failed"},
                    },
                ],
            )

            summary = summarize_session(root, "run-1")
            text = format_session_summary(summary)

        self.assertFalse(summary.completed)
        self.assertTrue(summary.failed)
        self.assertIn("review_changes", text)
        self.assertNotIn("SECRET_PATH", text)

    def test_summarize_session_marks_failed_suggest_checks_result(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-session-") as base:
            root = Path(base)
            write_events(
                root,
                "run-1",
                [
                    {
                        "type": "tool_call",
                        "iteration": 1,
                        "id": "1",
                        "name": "suggest_checks",
                        "input": {"max_commands": 101, "path": "SECRET_PATH"},
                    },
                    {
                        "type": "tool_result",
                        "iteration": 1,
                        "id": "1",
                        "name": "suggest_checks",
                        "result": {"kind": "suggest_checks", "ok": False, "message": "invalid max_commands"},
                    },
                ],
            )

            summary = summarize_session(root, "run-1")
            text = format_session_summary(summary)

        self.assertFalse(summary.completed)
        self.assertTrue(summary.failed)
        self.assertIn("suggest_checks", text)
        self.assertNotIn("SECRET_PATH", text)

    def test_summarize_session_marks_failed_python_references_result(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-session-") as base:
            root = Path(base)
            write_events(
                root,
                "run-1",
                [
                    {
                        "type": "tool_call",
                        "iteration": 1,
                        "id": "1",
                        "name": "python_references",
                        "input": {"symbol": "SECRET_SYMBOL"},
                    },
                    {
                        "type": "tool_result",
                        "iteration": 1,
                        "id": "1",
                        "name": "python_references",
                        "result": {
                            "kind": "python_references",
                            "symbol": "bad-name",
                            "ok": False,
                            "message": "invalid",
                        },
                    },
                ],
            )

            summary = summarize_session(root, "run-1")
            text = format_session_summary(summary)

        self.assertFalse(summary.completed)
        self.assertTrue(summary.failed)
        self.assertIn("python_references", text)
        self.assertNotIn("SECRET_SYMBOL", text)

    def test_summarize_session_marks_failed_background_process_results(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-session-") as base:
            root = Path(base)
            write_events(
                root,
                "run-1",
                [
                    {
                        "type": "tool_call",
                        "iteration": 1,
                        "id": "1",
                        "name": "read_process",
                        "input": {"process_id": "SECRET_PROCESS"},
                    },
                    {
                        "type": "tool_result",
                        "iteration": 1,
                        "id": "1",
                        "name": "read_process",
                        "result": {"kind": "read_process", "process_id": "missing", "ok": False},
                    },
                ],
            )

            summary = summarize_session(root, "run-1")
            text = format_session_summary(summary)

        self.assertFalse(summary.completed)
        self.assertTrue(summary.failed)
        self.assertIn("read_process", text)
        self.assertNotIn("SECRET_PROCESS", text)


if __name__ == "__main__":
    unittest.main()
