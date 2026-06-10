import json
import os
import tempfile
import unittest
from decimal import Decimal
from pathlib import Path

from vibeagent.config import CostRates
from vibeagent.session import (
    build_session_resume_context,
    format_cost,
    format_session_summary,
    format_sessions,
    format_usage,
    list_sessions,
    read_session_events,
    summarize_session,
    summarize_usage,
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
                        "usage": {
                            "input_tokens": 20,
                            "output_tokens": 5,
                            "total_tokens": 25,
                            "cache_creation_tokens": 2,
                            "cache_read_tokens": 3,
                        },
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
                        "name": "update_plan",
                        "result": {
                            "kind": "update_plan",
                            "plan": [
                                {"step": "Inspect failing test", "status": "completed"},
                                {"step": "Run focused check", "status": "in_progress"},
                            ],
                            "message": "Plan updated.",
                        },
                    },
                    {
                        "type": "tool_result",
                        "iteration": 3,
                        "id": "3",
                        "name": "finish",
                        "result": {"kind": "finish", "message": "Done."},
                    },
                ],
            )

            summary = summarize_session(root, "run-1")
            text = format_session_summary(summary)

        self.assertTrue(summary.completed)
        self.assertFalse(summary.failed)
        self.assertEqual(summary.iterations, 3)
        self.assertEqual(summary.task, "Fix the failing test.")
        self.assertEqual(summary.tool_calls, ["write_file"])
        self.assertEqual(summary.approvals_requested, 1)
        self.assertEqual(summary.approvals_approved, 1)
        self.assertEqual(summary.input_tokens, 20)
        self.assertEqual(summary.output_tokens, 5)
        self.assertEqual(summary.total_tokens, 25)
        self.assertEqual(summary.cache_creation_tokens, 2)
        self.assertEqual(summary.cache_read_tokens, 3)
        self.assertEqual(summary.final_message, "Done.")
        self.assertEqual([item.step for item in summary.latest_plan], ["Inspect failing test", "Run focused check"])
        self.assertEqual([item.status for item in summary.latest_plan], ["completed", "in_progress"])
        self.assertIn("write_file", text)
        self.assertIn("task: Fix the failing test.", text)
        self.assertIn("plan:", text)
        self.assertIn("tokens: 20 input, 5 output, 25 total", text)
        self.assertIn("cacheTokens: 2 created, 3 read", text)
        self.assertIn("completed: Inspect failing test", text)
        self.assertIn("in_progress: Run focused check", text)
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
                        "iteration": 1,
                        "id": "plan-1",
                        "name": "update_plan",
                        "result": {
                            "kind": "update_plan",
                            "plan": [
                                {"step": "Inspect auth files", "status": "completed"},
                                {"step": "Update login flow", "status": "in_progress"},
                            ],
                        },
                    },
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
        self.assertIn("plan:", context)
        self.assertIn("- completed: Inspect auth files", context)
        self.assertIn("- in_progress: Update login flow", context)
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

    def test_format_usage_summarizes_recorded_session_events_without_fake_cost(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-session-") as base:
            root = Path(base)
            self.assertEqual(format_usage(root), "No sessions found.")
            write_events(
                root,
                "run-1",
                [
                    {"type": "task", "task": "Fix bug."},
                    {
                        "type": "model",
                        "iteration": 2,
                        "usage": {"input_tokens": 12, "output_tokens": 4},
                        "content": [{"type": "text", "text": "Done."}],
                    },
                    {"type": "tool_call", "iteration": 1, "name": "read_file", "input": {"path": "SECRET_PATH"}},
                    {"type": "approval_requested", "iteration": 1, "request": {"target": "note.txt"}},
                    {"type": "approval_decision", "iteration": 1, "decision": {"approved": False}},
                ],
                mtime=200,
            )
            write_events(
                root,
                "run-2",
                [
                    {"type": "model", "iteration": 1, "content": []},
                    "{bad json",
                ],
                mtime=100,
            )

            usage = summarize_usage(root)
            text = format_usage(root)

        self.assertEqual(usage.sessions, 2)
        self.assertEqual(usage.events, 6)
        self.assertEqual(usage.malformed_rows, 1)
        self.assertEqual(usage.iterations, 3)
        self.assertEqual(usage.tool_calls, 1)
        self.assertEqual(usage.approvals_requested, 1)
        self.assertEqual(usage.approvals_denied, 1)
        self.assertEqual(usage.input_tokens, 12)
        self.assertEqual(usage.output_tokens, 4)
        self.assertEqual(usage.total_tokens, 16)
        self.assertEqual(usage.completed, 1)
        self.assertEqual(usage.failed, 1)
        self.assertIn("Usage:", text)
        self.assertIn("sessions: 2", text)
        self.assertIn("toolCalls: 1", text)
        self.assertIn("inputTokens: 12", text)
        self.assertIn("outputTokens: 4", text)
        self.assertIn("totalTokens: 16", text)
        self.assertIn("cost: unavailable; provider pricing is not configured.", text)
        self.assertNotIn("SECRET_PATH", text)

    def test_format_cost_requires_configured_rates_for_recorded_tokens(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-session-") as base:
            root = Path(base)
            write_events(
                root,
                "run-1",
                [
                    {
                        "type": "model",
                        "iteration": 1,
                        "usage": {"input_tokens": 100, "output_tokens": 50},
                        "content": [{"type": "text", "text": "Done."}],
                    }
                ],
            )

            text = format_cost(root, CostRates())

        self.assertIn("Cost:", text)
        self.assertIn("inputTokens: 100", text)
        self.assertIn("outputTokens: 50", text)
        self.assertIn("estimate: unavailable", text)
        self.assertIn("VIBEAGENT_INPUT_USD_PER_MILLION", text)
        self.assertIn("VIBEAGENT_OUTPUT_USD_PER_MILLION", text)

    def test_format_cost_estimates_from_configured_rates(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-session-") as base:
            root = Path(base)
            write_events(
                root,
                "run-1",
                [
                    {
                        "type": "model",
                        "iteration": 1,
                        "usage": {
                            "input_tokens": 100,
                            "output_tokens": 50,
                            "cache_creation_tokens": 20,
                            "cache_read_tokens": 10,
                        },
                        "content": [{"type": "text", "text": "Done."}],
                    }
                ],
            )

            text = format_cost(
                root,
                CostRates(
                    input_usd_per_million=Decimal("1"),
                    output_usd_per_million=Decimal("2"),
                    cache_creation_usd_per_million=Decimal("0.5"),
                    cache_read_usd_per_million=Decimal("0.1"),
                ),
            )

        self.assertIn("inputCostUsd: $0.000100", text)
        self.assertIn("outputCostUsd: $0.000100", text)
        self.assertIn("cacheCostUsd: $0.000011", text)
        self.assertIn("estimatedCostUsd: $0.000211", text)

    def test_format_cost_reports_invalid_rate_errors(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-session-") as base:
            root = Path(base)
            write_events(
                root,
                "run-1",
                [
                    {
                        "type": "model",
                        "iteration": 1,
                        "usage": {"input_tokens": 100},
                        "content": [{"type": "text", "text": "Done."}],
                    }
                ],
            )

            text = format_cost(root, CostRates(), ["VIBEAGENT_INPUT_USD_PER_MILLION must be a non-negative decimal."])

        self.assertIn("error: VIBEAGENT_INPUT_USD_PER_MILLION must be a non-negative decimal.", text)

    def test_summarize_session_marks_failed_check_write_file_result(self) -> None:
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
                        "name": "check_write_file",
                        "input": {"path": "SECRET_PATH", "content": "SECRET_CONTENT"},
                    },
                    {
                        "type": "tool_result",
                        "iteration": 1,
                        "id": "1",
                        "name": "check_write_file",
                        "result": {"kind": "check_write_file", "path": "app.py", "ok": False},
                    },
                ],
            )

            summary = summarize_session(root, "run-1")
            text = format_session_summary(summary)

        self.assertFalse(summary.completed)
        self.assertTrue(summary.failed)
        self.assertIn("check_write_file", text)
        self.assertNotIn("SECRET_PATH", text)
        self.assertNotIn("SECRET_CONTENT", text)

    def test_summarize_session_marks_failed_check_write_files_result(self) -> None:
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
                        "name": "check_write_files",
                        "input": {"files": [{"path": "SECRET_PATH", "content": "SECRET_CONTENT"}]},
                    },
                    {
                        "type": "tool_result",
                        "iteration": 1,
                        "id": "1",
                        "name": "check_write_files",
                        "result": {"kind": "check_write_files", "ok": False, "message": "write failed"},
                    },
                ],
            )

            summary = summarize_session(root, "run-1")
            text = format_session_summary(summary)

        self.assertFalse(summary.completed)
        self.assertTrue(summary.failed)
        self.assertIn("check_write_files", text)
        self.assertNotIn("SECRET_PATH", text)
        self.assertNotIn("SECRET_CONTENT", text)

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

    def test_summarize_session_marks_failed_check_edit_file_result(self) -> None:
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
                        "name": "check_edit_file",
                        "input": {"path": "app.py", "old": "SECRET_OLD", "new": "SECRET_NEW"},
                    },
                    {
                        "type": "tool_result",
                        "iteration": 1,
                        "id": "1",
                        "name": "check_edit_file",
                        "result": {"kind": "check_edit_file", "path": "app.py", "ok": False},
                    },
                ],
            )

            summary = summarize_session(root, "run-1")
            text = format_session_summary(summary)

        self.assertFalse(summary.completed)
        self.assertTrue(summary.failed)
        self.assertIn("check_edit_file", text)
        self.assertNotIn("SECRET_OLD", text)

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

    def test_summarize_session_marks_failed_check_multi_edit_result(self) -> None:
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
                        "name": "check_multi_edit_file",
                        "input": {"path": "app.py", "edits": [{"old": "SECRET_OLD", "new": "SECRET_NEW"}]},
                    },
                    {
                        "type": "tool_result",
                        "iteration": 1,
                        "id": "1",
                        "name": "check_multi_edit_file",
                        "result": {"kind": "check_multi_edit_file", "path": "app.py", "ok": False},
                    },
                ],
            )

            summary = summarize_session(root, "run-1")
            text = format_session_summary(summary)

        self.assertFalse(summary.completed)
        self.assertTrue(summary.failed)
        self.assertIn("check_multi_edit_file", text)
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

    def test_summarize_session_marks_failed_check_replace_lines_result(self) -> None:
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
                        "name": "check_replace_lines",
                        "input": {"path": "app.py", "start_line": 1, "end_line": 1, "content": "SECRET_CONTENT"},
                    },
                    {
                        "type": "tool_result",
                        "iteration": 1,
                        "id": "1",
                        "name": "check_replace_lines",
                        "result": {"kind": "check_replace_lines", "path": "app.py", "ok": False},
                    },
                ],
            )

            summary = summarize_session(root, "run-1")
            text = format_session_summary(summary)

        self.assertFalse(summary.completed)
        self.assertTrue(summary.failed)
        self.assertIn("check_replace_lines", text)
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
                    {
                        "type": "tool_call",
                        "iteration": 2,
                        "id": "2",
                        "name": "check_replace_python_definition",
                        "input": {"symbol": "run_agent", "content": "SECRET_CONTENT"},
                    },
                    {
                        "type": "tool_result",
                        "iteration": 2,
                        "id": "2",
                        "name": "check_replace_python_definition",
                        "result": {"kind": "check_replace_python_definition", "symbol": "run_agent", "ok": False},
                    },
                ],
            )

            summary = summarize_session(root, "run-1")
            text = format_session_summary(summary)

        self.assertFalse(summary.completed)
        self.assertTrue(summary.failed)
        self.assertIn("check_replace_python_definition", text)
        self.assertIn("replace_python_definition", text)
        self.assertNotIn("SECRET_CONTENT", text)

    def test_summarize_session_marks_failed_check_insert_lines_result(self) -> None:
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
                        "name": "check_insert_lines",
                        "input": {"path": "app.py", "line": 2, "content": "SECRET_CONTENT"},
                    },
                    {
                        "type": "tool_result",
                        "iteration": 1,
                        "id": "1",
                        "name": "check_insert_lines",
                        "result": {"kind": "check_insert_lines", "path": "app.py", "ok": False},
                    },
                ],
            )

            summary = summarize_session(root, "run-1")
            text = format_session_summary(summary)

        self.assertFalse(summary.completed)
        self.assertTrue(summary.failed)
        self.assertIn("check_insert_lines", text)
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

    def test_summarize_session_marks_failed_check_append_file_result(self) -> None:
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
                        "name": "check_append_file",
                        "input": {"path": "app.py", "content": "SECRET_CONTENT"},
                    },
                    {
                        "type": "tool_result",
                        "iteration": 1,
                        "id": "1",
                        "name": "check_append_file",
                        "result": {"kind": "check_append_file", "path": "app.py", "ok": False},
                    },
                ],
            )

            summary = summarize_session(root, "run-1")
            text = format_session_summary(summary)

        self.assertFalse(summary.completed)
        self.assertTrue(summary.failed)
        self.assertIn("check_append_file", text)
        self.assertNotIn("SECRET_CONTENT", text)

    def test_summarize_session_marks_failed_append_file_result(self) -> None:
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
                        "name": "append_file",
                        "input": {"path": "app.py", "content": "SECRET_CONTENT"},
                    },
                    {
                        "type": "tool_result",
                        "iteration": 1,
                        "id": "1",
                        "name": "append_file",
                        "result": {"kind": "append_file", "path": "app.py", "ok": False},
                    },
                ],
            )

            summary = summarize_session(root, "run-1")
            text = format_session_summary(summary)

        self.assertFalse(summary.completed)
        self.assertTrue(summary.failed)
        self.assertIn("append_file", text)
        self.assertNotIn("SECRET_CONTENT", text)

    def test_summarize_session_marks_failed_regex_replace_result(self) -> None:
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
                        "name": "regex_replace",
                        "input": {"path": "app.py", "pattern": "SECRET_PATTERN", "replacement": "SECRET_REPLACEMENT"},
                    },
                    {
                        "type": "tool_result",
                        "iteration": 1,
                        "id": "1",
                        "name": "regex_replace",
                        "result": {"kind": "regex_replace", "path": "app.py", "ok": False},
                    },
                ],
            )

            summary = summarize_session(root, "run-1")
            text = format_session_summary(summary)

        self.assertFalse(summary.completed)
        self.assertTrue(summary.failed)
        self.assertIn("regex_replace", text)
        self.assertNotIn("SECRET_PATTERN", text)
        self.assertNotIn("SECRET_REPLACEMENT", text)

    def test_summarize_session_marks_failed_check_regex_replace_result(self) -> None:
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
                        "name": "check_regex_replace",
                        "input": {"path": "app.py", "pattern": "SECRET_PATTERN", "replacement": "SECRET_REPLACEMENT"},
                    },
                    {
                        "type": "tool_result",
                        "iteration": 1,
                        "id": "1",
                        "name": "check_regex_replace",
                        "result": {"kind": "check_regex_replace", "path": "app.py", "ok": False},
                    },
                ],
            )

            summary = summarize_session(root, "run-1")
            text = format_session_summary(summary)

        self.assertFalse(summary.completed)
        self.assertTrue(summary.failed)
        self.assertIn("check_regex_replace", text)
        self.assertNotIn("SECRET_PATTERN", text)
        self.assertNotIn("SECRET_REPLACEMENT", text)

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
                        "iteration": 1,
                        "id": "1b",
                        "name": "check_delete_file",
                        "input": {"path": "SECRET_PATH"},
                    },
                    {
                        "type": "tool_result",
                        "iteration": 1,
                        "id": "1b",
                        "name": "check_delete_file",
                        "result": {"kind": "check_delete_file", "path": "old.py", "ok": False},
                    },
                    {
                        "type": "tool_call",
                        "iteration": 1,
                        "id": "1c",
                        "name": "delete_files",
                        "input": {"paths": ["SECRET_PATH", "SECRET_OTHER_PATH"]},
                    },
                    {
                        "type": "tool_result",
                        "iteration": 1,
                        "id": "1c",
                        "name": "delete_files",
                        "result": {"kind": "delete_files", "paths": ["old.py", "other.py"], "ok": False},
                    },
                    {
                        "type": "tool_call",
                        "iteration": 1,
                        "id": "1d",
                        "name": "check_delete_files",
                        "input": {"paths": ["SECRET_PATH", "SECRET_OTHER_PATH"]},
                    },
                    {
                        "type": "tool_result",
                        "iteration": 1,
                        "id": "1d",
                        "name": "check_delete_files",
                        "result": {"kind": "check_delete_files", "paths": ["old.py", "other.py"], "ok": False},
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
                    {
                        "type": "tool_call",
                        "iteration": 2,
                        "id": "2b",
                        "name": "check_move_file",
                        "input": {"source": "SECRET_PATH", "destination": "SECRET_DEST"},
                    },
                    {
                        "type": "tool_result",
                        "iteration": 2,
                        "id": "2b",
                        "name": "check_move_file",
                        "result": {"kind": "check_move_file", "source": "old.py", "destination": "new.py", "ok": False},
                    },
                    {
                        "type": "tool_call",
                        "iteration": 2,
                        "id": "2c",
                        "name": "move_files",
                        "input": {"transfers": [{"source": "SECRET_PATH", "destination": "SECRET_DEST"}]},
                    },
                    {
                        "type": "tool_result",
                        "iteration": 2,
                        "id": "2c",
                        "name": "move_files",
                        "result": {
                            "kind": "move_files",
                            "transfers": [{"source": "old.py", "destination": "new.py"}],
                            "ok": False,
                        },
                    },
                    {
                        "type": "tool_call",
                        "iteration": 2,
                        "id": "2d",
                        "name": "check_move_files",
                        "input": {"transfers": [{"source": "SECRET_PATH", "destination": "SECRET_DEST"}]},
                    },
                    {
                        "type": "tool_result",
                        "iteration": 2,
                        "id": "2d",
                        "name": "check_move_files",
                        "result": {
                            "kind": "check_move_files",
                            "transfers": [{"source": "old.py", "destination": "new.py"}],
                            "ok": False,
                        },
                    },
                    {
                        "type": "tool_call",
                        "iteration": 3,
                        "id": "3",
                        "name": "set_executable",
                        "input": {"path": "SECRET_PATH", "executable": True},
                    },
                    {
                        "type": "tool_result",
                        "iteration": 3,
                        "id": "3",
                        "name": "set_executable",
                        "result": {"kind": "set_executable", "path": "tool.sh", "ok": False},
                    },
                    {
                        "type": "tool_call",
                        "iteration": 3,
                        "id": "3b",
                        "name": "check_set_executable",
                        "input": {"path": "SECRET_PATH", "executable": True},
                    },
                    {
                        "type": "tool_result",
                        "iteration": 3,
                        "id": "3b",
                        "name": "check_set_executable",
                        "result": {"kind": "check_set_executable", "path": "tool.sh", "ok": False},
                    },
                    {
                        "type": "tool_call",
                        "iteration": 4,
                        "id": "4",
                        "name": "copy_file",
                        "input": {"source": "SECRET_PATH", "destination": "SECRET_DEST"},
                    },
                    {
                        "type": "tool_result",
                        "iteration": 4,
                        "id": "4",
                        "name": "copy_file",
                        "result": {"kind": "copy_file", "source": "old.py", "destination": "copy.py", "ok": False},
                    },
                    {
                        "type": "tool_call",
                        "iteration": 4,
                        "id": "4b",
                        "name": "check_copy_file",
                        "input": {"source": "SECRET_PATH", "destination": "SECRET_DEST"},
                    },
                    {
                        "type": "tool_result",
                        "iteration": 4,
                        "id": "4b",
                        "name": "check_copy_file",
                        "result": {"kind": "check_copy_file", "source": "old.py", "destination": "copy.py", "ok": False},
                    },
                    {
                        "type": "tool_call",
                        "iteration": 4,
                        "id": "4c",
                        "name": "copy_files",
                        "input": {"transfers": [{"source": "SECRET_PATH", "destination": "SECRET_DEST"}]},
                    },
                    {
                        "type": "tool_result",
                        "iteration": 4,
                        "id": "4c",
                        "name": "copy_files",
                        "result": {
                            "kind": "copy_files",
                            "transfers": [{"source": "old.py", "destination": "copy.py"}],
                            "ok": False,
                        },
                    },
                    {
                        "type": "tool_call",
                        "iteration": 4,
                        "id": "4d",
                        "name": "check_copy_files",
                        "input": {"transfers": [{"source": "SECRET_PATH", "destination": "SECRET_DEST"}]},
                    },
                    {
                        "type": "tool_result",
                        "iteration": 4,
                        "id": "4d",
                        "name": "check_copy_files",
                        "result": {
                            "kind": "check_copy_files",
                            "transfers": [{"source": "old.py", "destination": "copy.py"}],
                            "ok": False,
                        },
                    },
                    {
                        "type": "tool_call",
                        "iteration": 5,
                        "id": "5",
                        "name": "move_dir",
                        "input": {"source": "SECRET_PATH", "destination": "SECRET_DEST"},
                    },
                    {
                        "type": "tool_result",
                        "iteration": 5,
                        "id": "5",
                        "name": "move_dir",
                        "result": {"kind": "move_dir", "source": "old-dir", "destination": "new-dir", "ok": False},
                    },
                    {
                        "type": "tool_call",
                        "iteration": 5,
                        "id": "5b",
                        "name": "check_move_dir",
                        "input": {"source": "SECRET_PATH", "destination": "SECRET_DEST"},
                    },
                    {
                        "type": "tool_result",
                        "iteration": 5,
                        "id": "5b",
                        "name": "check_move_dir",
                        "result": {"kind": "check_move_dir", "source": "old-dir", "destination": "new-dir", "ok": False},
                    },
                    {
                        "type": "tool_call",
                        "iteration": 5,
                        "id": "5c",
                        "name": "move_dirs",
                        "input": {"transfers": [{"source": "SECRET_PATH", "destination": "SECRET_DEST"}]},
                    },
                    {
                        "type": "tool_result",
                        "iteration": 5,
                        "id": "5c",
                        "name": "move_dirs",
                        "result": {
                            "kind": "move_dirs",
                            "transfers": [{"source": "old-dir", "destination": "new-dir"}],
                            "ok": False,
                        },
                    },
                    {
                        "type": "tool_call",
                        "iteration": 5,
                        "id": "5d",
                        "name": "check_move_dirs",
                        "input": {"transfers": [{"source": "SECRET_PATH", "destination": "SECRET_DEST"}]},
                    },
                    {
                        "type": "tool_result",
                        "iteration": 5,
                        "id": "5d",
                        "name": "check_move_dirs",
                        "result": {
                            "kind": "check_move_dirs",
                            "transfers": [{"source": "old-dir", "destination": "new-dir"}],
                            "ok": False,
                        },
                    },
                    {
                        "type": "tool_call",
                        "iteration": 6,
                        "id": "6",
                        "name": "copy_dir",
                        "input": {"source": "SECRET_PATH", "destination": "SECRET_DEST"},
                    },
                    {
                        "type": "tool_result",
                        "iteration": 6,
                        "id": "6",
                        "name": "copy_dir",
                        "result": {"kind": "copy_dir", "source": "template", "destination": "copy-dir", "ok": False},
                    },
                    {
                        "type": "tool_call",
                        "iteration": 6,
                        "id": "6b",
                        "name": "check_copy_dir",
                        "input": {"source": "SECRET_PATH", "destination": "SECRET_DEST"},
                    },
                    {
                        "type": "tool_result",
                        "iteration": 6,
                        "id": "6b",
                        "name": "check_copy_dir",
                        "result": {"kind": "check_copy_dir", "source": "template", "destination": "copy-dir", "ok": False},
                    },
                    {
                        "type": "tool_call",
                        "iteration": 6,
                        "id": "6c",
                        "name": "copy_dirs",
                        "input": {"transfers": [{"source": "SECRET_PATH", "destination": "SECRET_DEST"}]},
                    },
                    {
                        "type": "tool_result",
                        "iteration": 6,
                        "id": "6c",
                        "name": "copy_dirs",
                        "result": {
                            "kind": "copy_dirs",
                            "transfers": [{"source": "template", "destination": "copy-dir"}],
                            "ok": False,
                        },
                    },
                    {
                        "type": "tool_call",
                        "iteration": 6,
                        "id": "6d",
                        "name": "check_copy_dirs",
                        "input": {"transfers": [{"source": "SECRET_PATH", "destination": "SECRET_DEST"}]},
                    },
                    {
                        "type": "tool_result",
                        "iteration": 6,
                        "id": "6d",
                        "name": "check_copy_dirs",
                        "result": {
                            "kind": "check_copy_dirs",
                            "transfers": [{"source": "template", "destination": "copy-dir"}],
                            "ok": False,
                        },
                    },
                    {
                        "type": "tool_call",
                        "iteration": 7,
                        "id": "7",
                        "name": "create_dir",
                        "input": {"path": "SECRET_PATH"},
                    },
                    {
                        "type": "tool_result",
                        "iteration": 7,
                        "id": "7",
                        "name": "create_dir",
                        "result": {"kind": "create_dir", "path": "new-dir", "ok": False},
                    },
                    {
                        "type": "tool_call",
                        "iteration": 7,
                        "id": "7b",
                        "name": "check_create_dir",
                        "input": {"path": "SECRET_PATH"},
                    },
                    {
                        "type": "tool_result",
                        "iteration": 7,
                        "id": "7b",
                        "name": "check_create_dir",
                        "result": {"kind": "check_create_dir", "path": "new-dir", "ok": False},
                    },
                    {
                        "type": "tool_call",
                        "iteration": 7,
                        "id": "7c",
                        "name": "create_dirs",
                        "input": {"paths": ["SECRET_PATH", "other-dir"]},
                    },
                    {
                        "type": "tool_result",
                        "iteration": 7,
                        "id": "7c",
                        "name": "create_dirs",
                        "result": {"kind": "create_dirs", "paths": ["new-dir", "other-dir"], "ok": False},
                    },
                    {
                        "type": "tool_call",
                        "iteration": 7,
                        "id": "7d",
                        "name": "check_create_dirs",
                        "input": {"paths": ["SECRET_PATH", "other-dir"]},
                    },
                    {
                        "type": "tool_result",
                        "iteration": 7,
                        "id": "7d",
                        "name": "check_create_dirs",
                        "result": {"kind": "check_create_dirs", "paths": ["new-dir", "other-dir"], "ok": False},
                    },
                    {
                        "type": "tool_call",
                        "iteration": 8,
                        "id": "8",
                        "name": "delete_empty_dir",
                        "input": {"path": "SECRET_PATH"},
                    },
                    {
                        "type": "tool_result",
                        "iteration": 8,
                        "id": "8",
                        "name": "delete_empty_dir",
                        "result": {"kind": "delete_empty_dir", "path": "old-dir", "ok": False},
                    },
                    {
                        "type": "tool_call",
                        "iteration": 8,
                        "id": "8b",
                        "name": "check_delete_empty_dir",
                        "input": {"path": "SECRET_PATH"},
                    },
                    {
                        "type": "tool_result",
                        "iteration": 8,
                        "id": "8b",
                        "name": "check_delete_empty_dir",
                        "result": {"kind": "check_delete_empty_dir", "path": "old-dir", "ok": False},
                    },
                    {
                        "type": "tool_call",
                        "iteration": 8,
                        "id": "8c",
                        "name": "delete_empty_dirs",
                        "input": {"paths": ["SECRET_PATH", "old-other"]},
                    },
                    {
                        "type": "tool_result",
                        "iteration": 8,
                        "id": "8c",
                        "name": "delete_empty_dirs",
                        "result": {"kind": "delete_empty_dirs", "paths": ["old-dir", "old-other"], "ok": False},
                    },
                    {
                        "type": "tool_call",
                        "iteration": 8,
                        "id": "8d",
                        "name": "check_delete_empty_dirs",
                        "input": {"paths": ["SECRET_PATH", "old-other"]},
                    },
                    {
                        "type": "tool_result",
                        "iteration": 8,
                        "id": "8d",
                        "name": "check_delete_empty_dirs",
                        "result": {"kind": "check_delete_empty_dirs", "paths": ["old-dir", "old-other"], "ok": False},
                    },
                ],
            )

            summary = summarize_session(root, "run-1")
            text = format_session_summary(summary)

        self.assertFalse(summary.completed)
        self.assertTrue(summary.failed)
        self.assertIn("check_delete_file", text)
        self.assertIn("delete_file", text)
        self.assertIn("check_delete_files", text)
        self.assertIn("delete_files", text)
        self.assertIn("check_move_file", text)
        self.assertIn("move_file", text)
        self.assertIn("check_move_files", text)
        self.assertIn("move_files", text)
        self.assertIn("check_copy_file", text)
        self.assertIn("copy_file", text)
        self.assertIn("check_copy_files", text)
        self.assertIn("copy_files", text)
        self.assertIn("check_move_dir", text)
        self.assertIn("move_dir", text)
        self.assertIn("check_move_dirs", text)
        self.assertIn("move_dirs", text)
        self.assertIn("check_copy_dir", text)
        self.assertIn("copy_dir", text)
        self.assertIn("check_copy_dirs", text)
        self.assertIn("copy_dirs", text)
        self.assertIn("check_create_dir", text)
        self.assertIn("create_dir", text)
        self.assertIn("check_create_dirs", text)
        self.assertIn("create_dirs", text)
        self.assertIn("check_delete_empty_dir", text)
        self.assertIn("delete_empty_dir", text)
        self.assertIn("check_delete_empty_dirs", text)
        self.assertIn("delete_empty_dirs", text)
        self.assertIn("check_set_executable", text)
        self.assertIn("set_executable", text)
        self.assertNotIn("SECRET_PATH", text)
        self.assertNotIn("SECRET_OTHER_PATH", text)
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
                        "name": "git_info",
                        "input": {},
                    },
                    {
                        "type": "tool_result",
                        "iteration": 2,
                        "id": "2",
                        "name": "git_info",
                        "result": {"kind": "git_info", "ok": False, "is_git_repo": False, "message": "not a git repo"},
                    },
                    {
                        "type": "tool_call",
                        "iteration": 3,
                        "id": "3",
                        "name": "git_changes",
                        "input": {},
                    },
                    {
                        "type": "tool_result",
                        "iteration": 3,
                        "id": "3",
                        "name": "git_changes",
                        "result": {"kind": "git_changes", "ok": False, "files": [], "status": "", "message": "not a git repo"},
                    },
                    {
                        "type": "tool_call",
                        "iteration": 3,
                        "id": "branches",
                        "name": "git_branches",
                        "input": {"max_branches": 100},
                    },
                    {
                        "type": "tool_result",
                        "iteration": 3,
                        "id": "branches",
                        "name": "git_branches",
                        "result": {"kind": "git_branches", "ok": False, "branches": [], "status": "", "message": "not a git repo"},
                    },
                    {
                        "type": "tool_call",
                        "iteration": 3,
                        "id": "check-fetch",
                        "name": "check_git_fetch",
                        "input": {"remote": "SECRET_REMOTE"},
                    },
                    {
                        "type": "tool_result",
                        "iteration": 3,
                        "id": "check-fetch",
                        "name": "check_git_fetch",
                        "result": {"kind": "check_git_fetch", "ok": False, "remote": "origin", "message": "not a git repo"},
                    },
                    {
                        "type": "tool_call",
                        "iteration": 3,
                        "id": "fetch",
                        "name": "git_fetch",
                        "input": {"remote": "SECRET_REMOTE"},
                    },
                    {
                        "type": "tool_result",
                        "iteration": 3,
                        "id": "fetch",
                        "name": "git_fetch",
                        "result": {"kind": "git_fetch", "ok": False, "remote": "origin", "message": "not a git repo"},
                    },
                    {
                        "type": "tool_call",
                        "iteration": 3,
                        "id": "check-pull",
                        "name": "check_git_pull",
                        "input": {"remote": "SECRET_PULL_REMOTE"},
                    },
                    {
                        "type": "tool_result",
                        "iteration": 3,
                        "id": "check-pull",
                        "name": "check_git_pull",
                        "result": {"kind": "check_git_pull", "ok": False, "remote": "origin", "message": "not a git repo"},
                    },
                    {
                        "type": "tool_call",
                        "iteration": 3,
                        "id": "pull",
                        "name": "git_pull",
                        "input": {"remote": "SECRET_PULL_REMOTE"},
                    },
                    {
                        "type": "tool_result",
                        "iteration": 3,
                        "id": "pull",
                        "name": "git_pull",
                        "result": {"kind": "git_pull", "ok": False, "remote": "origin", "message": "not a git repo"},
                    },
                    {
                        "type": "tool_call",
                        "iteration": 3,
                        "id": "check-push",
                        "name": "check_git_push",
                        "input": {"remote": "SECRET_PUSH_REMOTE"},
                    },
                    {
                        "type": "tool_result",
                        "iteration": 3,
                        "id": "check-push",
                        "name": "check_git_push",
                        "result": {"kind": "check_git_push", "ok": False, "remote": "origin", "message": "not a git repo"},
                    },
                    {
                        "type": "tool_call",
                        "iteration": 3,
                        "id": "push",
                        "name": "git_push",
                        "input": {"remote": "SECRET_PUSH_REMOTE"},
                    },
                    {
                        "type": "tool_result",
                        "iteration": 3,
                        "id": "push",
                        "name": "git_push",
                        "result": {"kind": "git_push", "ok": False, "remote": "origin", "message": "not a git repo"},
                    },
                    {
                        "type": "tool_call",
                        "iteration": 3,
                        "id": "check-restore",
                        "name": "check_git_restore",
                        "input": {"paths": ["SECRET_RESTORE_PATH"]},
                    },
                    {
                        "type": "tool_result",
                        "iteration": 3,
                        "id": "check-restore",
                        "name": "check_git_restore",
                        "result": {"kind": "check_git_restore", "ok": False, "paths": ["app.py"], "message": "no changes"},
                    },
                    {
                        "type": "tool_call",
                        "iteration": 3,
                        "id": "restore",
                        "name": "git_restore",
                        "input": {"paths": ["SECRET_RESTORE_PATH"]},
                    },
                    {
                        "type": "tool_result",
                        "iteration": 3,
                        "id": "restore",
                        "name": "git_restore",
                        "result": {"kind": "git_restore", "ok": False, "paths": ["app.py"], "message": "no changes"},
                    },
                    {
                        "type": "tool_call",
                        "iteration": 3,
                        "id": "stashes",
                        "name": "git_stashes",
                        "input": {"max_entries": 3},
                    },
                    {
                        "type": "tool_result",
                        "iteration": 3,
                        "id": "stashes",
                        "name": "git_stashes",
                        "result": {"kind": "git_stashes", "ok": False, "entries": [], "message": "not a git repo"},
                    },
                    {
                        "type": "tool_call",
                        "iteration": 3,
                        "id": "check-stash",
                        "name": "check_git_stash",
                        "input": {"message": "SECRET_STASH_MESSAGE"},
                    },
                    {
                        "type": "tool_result",
                        "iteration": 3,
                        "id": "check-stash",
                        "name": "check_git_stash",
                        "result": {"kind": "check_git_stash", "ok": False, "message_text": "safe message", "message": "not a git repo"},
                    },
                    {
                        "type": "tool_call",
                        "iteration": 3,
                        "id": "stash",
                        "name": "git_stash",
                        "input": {"message": "SECRET_STASH_MESSAGE"},
                    },
                    {
                        "type": "tool_result",
                        "iteration": 3,
                        "id": "stash",
                        "name": "git_stash",
                        "result": {"kind": "git_stash", "ok": False, "message_text": "safe message", "message": "not a git repo"},
                    },
                    {
                        "type": "tool_call",
                        "iteration": 3,
                        "id": "check-stash-apply",
                        "name": "check_git_stash_apply",
                        "input": {"stash_ref": "SECRET_STASH_REF"},
                    },
                    {
                        "type": "tool_result",
                        "iteration": 3,
                        "id": "check-stash-apply",
                        "name": "check_git_stash_apply",
                        "result": {"kind": "check_git_stash_apply", "ok": False, "stash_ref": "stash@{0}", "message": "not a git repo"},
                    },
                    {
                        "type": "tool_call",
                        "iteration": 3,
                        "id": "stash-apply",
                        "name": "git_stash_apply",
                        "input": {"stash_ref": "SECRET_STASH_REF"},
                    },
                    {
                        "type": "tool_result",
                        "iteration": 3,
                        "id": "stash-apply",
                        "name": "git_stash_apply",
                        "result": {"kind": "git_stash_apply", "ok": False, "stash_ref": "stash@{0}", "message": "not a git repo"},
                    },
                    {
                        "type": "tool_call",
                        "iteration": 3,
                        "id": "check-stash-drop",
                        "name": "check_git_stash_drop",
                        "input": {"stash_ref": "SECRET_STASH_DROP_REF"},
                    },
                    {
                        "type": "tool_result",
                        "iteration": 3,
                        "id": "check-stash-drop",
                        "name": "check_git_stash_drop",
                        "result": {"kind": "check_git_stash_drop", "ok": False, "stash_ref": "stash@{0}", "message": "not a git repo"},
                    },
                    {
                        "type": "tool_call",
                        "iteration": 3,
                        "id": "stash-drop",
                        "name": "git_stash_drop",
                        "input": {"stash_ref": "SECRET_STASH_DROP_REF"},
                    },
                    {
                        "type": "tool_result",
                        "iteration": 3,
                        "id": "stash-drop",
                        "name": "git_stash_drop",
                        "result": {"kind": "git_stash_drop", "ok": False, "stash_ref": "stash@{0}", "message": "not a git repo"},
                    },
                    {
                        "type": "tool_call",
                        "iteration": 3,
                        "id": "check-switch",
                        "name": "check_git_switch",
                        "input": {"branch": "SECRET_BRANCH"},
                    },
                    {
                        "type": "tool_result",
                        "iteration": 3,
                        "id": "check-switch",
                        "name": "check_git_switch",
                        "result": {"kind": "check_git_switch", "ok": False, "branch": "main", "status": "", "message": "not a git repo"},
                    },
                    {
                        "type": "tool_call",
                        "iteration": 3,
                        "id": "switch",
                        "name": "git_switch",
                        "input": {"branch": "SECRET_BRANCH"},
                    },
                    {
                        "type": "tool_result",
                        "iteration": 3,
                        "id": "switch",
                        "name": "git_switch",
                        "result": {"kind": "git_switch", "ok": False, "branch": "main", "status": "", "message": "not a git repo"},
                    },
                    {
                        "type": "tool_call",
                        "iteration": 4,
                        "id": "4",
                        "name": "git_stage",
                        "input": {"paths": ["SECRET_PATH"]},
                    },
                    {
                        "type": "tool_result",
                        "iteration": 4,
                        "id": "4",
                        "name": "git_stage",
                        "result": {"kind": "git_stage", "ok": False, "paths": ["app.py"], "status": "", "message": "not a git repo"},
                    },
                    {
                        "type": "tool_call",
                        "iteration": 4,
                        "id": "4b",
                        "name": "check_git_stage",
                        "input": {"paths": ["SECRET_PATH"]},
                    },
                    {
                        "type": "tool_result",
                        "iteration": 4,
                        "id": "4b",
                        "name": "check_git_stage",
                        "result": {"kind": "check_git_stage", "ok": False, "paths": ["app.py"], "status": "", "message": "not a git repo"},
                    },
                    {
                        "type": "tool_call",
                        "iteration": 5,
                        "id": "5",
                        "name": "git_unstage",
                        "input": {"paths": ["SECRET_PATH"]},
                    },
                    {
                        "type": "tool_result",
                        "iteration": 5,
                        "id": "5",
                        "name": "git_unstage",
                        "result": {"kind": "git_unstage", "ok": False, "paths": ["app.py"], "status": "", "message": "not a git repo"},
                    },
                    {
                        "type": "tool_call",
                        "iteration": 5,
                        "id": "5b",
                        "name": "check_git_unstage",
                        "input": {"paths": ["SECRET_PATH"]},
                    },
                    {
                        "type": "tool_result",
                        "iteration": 5,
                        "id": "5b",
                        "name": "check_git_unstage",
                        "result": {"kind": "check_git_unstage", "ok": False, "paths": ["app.py"], "status": "", "message": "not a git repo"},
                    },
                    {
                        "type": "tool_call",
                        "iteration": 6,
                        "id": "6",
                        "name": "git_commit",
                        "input": {"message": "SECRET_MESSAGE"},
                    },
                    {
                        "type": "tool_result",
                        "iteration": 6,
                        "id": "6",
                        "name": "git_commit",
                        "result": {"kind": "git_commit", "ok": False, "head_before": "", "head_after": "", "status": "", "message": "not a git repo"},
                    },
                    {
                        "type": "tool_call",
                        "iteration": 6,
                        "id": "6b",
                        "name": "check_git_commit",
                        "input": {"message": "SECRET_MESSAGE"},
                    },
                    {
                        "type": "tool_result",
                        "iteration": 6,
                        "id": "6b",
                        "name": "check_git_commit",
                        "result": {"kind": "check_git_commit", "ok": False, "head_before": "", "head_after": "", "status": "", "message": "not a git repo"},
                    },
                    {
                        "type": "tool_call",
                        "iteration": 7,
                        "id": "7",
                        "name": "git_diff",
                        "input": {"path": "SECRET_PATH"},
                    },
                    {
                        "type": "tool_result",
                        "iteration": 7,
                        "id": "7",
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
                        "iteration": 8,
                        "id": "8",
                        "name": "git_diff_hunks",
                        "input": {"path": "SECRET_PATH"},
                    },
                    {
                        "type": "tool_result",
                        "iteration": 8,
                        "id": "8",
                        "name": "git_diff_hunks",
                        "result": {
                            "kind": "git_diff_hunks",
                            "ok": False,
                            "hunks": [],
                            "path": "app.py",
                            "staged": False,
                            "truncated": False,
                            "total_hunks": 0,
                        },
                    },
                    {
                        "type": "tool_call",
                        "iteration": 9,
                        "id": "9",
                        "name": "git_log",
                        "input": {"path": "SECRET_PATH"},
                    },
                    {
                        "type": "tool_result",
                        "iteration": 9,
                        "id": "9",
                        "name": "git_log",
                        "result": {"kind": "git_log", "ok": False, "log": "", "path": "app.py", "max_count": 5},
                    },
                    {
                        "type": "tool_call",
                        "iteration": 10,
                        "id": "10",
                        "name": "git_show",
                        "input": {"rev": "SECRET_REV", "path": "SECRET_PATH"},
                    },
                    {
                        "type": "tool_result",
                        "iteration": 10,
                        "id": "10",
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
                        "iteration": 11,
                        "id": "11",
                        "name": "git_blame",
                        "input": {"path": "SECRET_PATH"},
                    },
                    {
                        "type": "tool_result",
                        "iteration": 11,
                        "id": "11",
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
        self.assertIn("git_info", text)
        self.assertIn("git_changes", text)
        self.assertIn("git_branches", text)
        self.assertIn("check_git_fetch", text)
        self.assertIn("git_fetch", text)
        self.assertIn("check_git_pull", text)
        self.assertIn("git_pull", text)
        self.assertIn("check_git_push", text)
        self.assertIn("git_push", text)
        self.assertIn("check_git_restore", text)
        self.assertIn("git_restore", text)
        self.assertIn("git_stashes", text)
        self.assertIn("check_git_stash", text)
        self.assertIn("git_stash", text)
        self.assertIn("check_git_stash_apply", text)
        self.assertIn("git_stash_apply", text)
        self.assertIn("check_git_stash_drop", text)
        self.assertIn("git_stash_drop", text)
        self.assertIn("check_git_switch", text)
        self.assertIn("git_switch", text)
        self.assertIn("check_git_stage", text)
        self.assertIn("git_stage", text)
        self.assertIn("check_git_unstage", text)
        self.assertIn("git_unstage", text)
        self.assertIn("check_git_commit", text)
        self.assertIn("git_commit", text)
        self.assertIn("git_diff", text)
        self.assertIn("git_diff_hunks", text)
        self.assertIn("git_log", text)
        self.assertIn("git_show", text)
        self.assertIn("git_blame", text)
        self.assertNotIn("SECRET_PATH", text)
        self.assertNotIn("SECRET_BRANCH", text)
        self.assertNotIn("SECRET_REMOTE", text)
        self.assertNotIn("SECRET_PULL_REMOTE", text)
        self.assertNotIn("SECRET_PUSH_REMOTE", text)
        self.assertNotIn("SECRET_RESTORE_PATH", text)
        self.assertNotIn("SECRET_STASH_MESSAGE", text)
        self.assertNotIn("SECRET_STASH_REF", text)
        self.assertNotIn("SECRET_STASH_DROP_REF", text)
        self.assertNotIn("SECRET_REV", text)
        self.assertNotIn("SECRET_MESSAGE", text)

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

    def test_summarize_session_marks_failed_search_result(self) -> None:
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
                        "name": "search",
                        "input": {"query": "SECRET_QUERY"},
                    },
                    {
                        "type": "tool_result",
                        "iteration": 1,
                        "id": "1",
                        "name": "search",
                        "result": {"kind": "search", "ok": False, "message": "invalid regex"},
                    },
                ],
            )

            summary = summarize_session(root, "run-1")
            text = format_session_summary(summary)

        self.assertFalse(summary.completed)
        self.assertTrue(summary.failed)
        self.assertIn("search", text)
        self.assertNotIn("SECRET_QUERY", text)

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

    def test_summarize_session_marks_failed_code_outline_result(self) -> None:
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
                        "name": "code_outline",
                        "input": {"paths": ["SECRET_PATH"]},
                    },
                    {
                        "type": "tool_result",
                        "iteration": 1,
                        "id": "1",
                        "name": "code_outline",
                        "result": {
                            "kind": "code_outline",
                            "files": [{"path": "missing.ts", "ok": False, "message": "missing"}],
                        },
                    },
                ],
            )

            summary = summarize_session(root, "run-1")
            text = format_session_summary(summary)

        self.assertFalse(summary.completed)
        self.assertTrue(summary.failed)
        self.assertIn("code_outline", text)
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

    def test_summarize_session_marks_failed_config_check_result(self) -> None:
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
                        "name": "config_check",
                        "input": {"path": "SECRET_PATH"},
                    },
                    {
                        "type": "tool_result",
                        "iteration": 1,
                        "id": "1",
                        "name": "config_check",
                        "result": {"kind": "config_check", "path": ".", "ok": False},
                    },
                ],
            )

            summary = summarize_session(root, "run-1")
            text = format_session_summary(summary)

        self.assertFalse(summary.completed)
        self.assertTrue(summary.failed)
        self.assertIn("config_check", text)
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

    def test_summarize_session_marks_failed_code_dependencies_result(self) -> None:
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
                        "name": "code_dependencies",
                        "input": {"path": "SECRET_PATH"},
                    },
                    {
                        "type": "tool_result",
                        "iteration": 1,
                        "id": "1",
                        "name": "code_dependencies",
                        "result": {"kind": "code_dependencies", "path": "src", "ok": False},
                    },
                ],
            )

            summary = summarize_session(root, "run-1")
            text = format_session_summary(summary)

        self.assertFalse(summary.completed)
        self.assertTrue(summary.failed)
        self.assertIn("code_dependencies", text)
        self.assertNotIn("SECRET_PATH", text)

    def test_summarize_session_marks_failed_code_references_result(self) -> None:
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
                        "name": "code_references",
                        "input": {"symbol": "SECRET_SYMBOL", "path": "SECRET_PATH"},
                    },
                    {
                        "type": "tool_result",
                        "iteration": 1,
                        "id": "1",
                        "name": "code_references",
                        "result": {"kind": "code_references", "symbol": "bad", "ok": False},
                    },
                ],
            )

            summary = summarize_session(root, "run-1")
            text = format_session_summary(summary)

        self.assertFalse(summary.completed)
        self.assertTrue(summary.failed)
        self.assertIn("code_references", text)
        self.assertNotIn("SECRET_SYMBOL", text)
        self.assertNotIn("SECRET_PATH", text)

    def test_summarize_session_marks_failed_code_definitions_result(self) -> None:
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
                        "name": "code_definitions",
                        "input": {"symbol": "SECRET_SYMBOL", "path": "SECRET_PATH"},
                    },
                    {
                        "type": "tool_result",
                        "iteration": 1,
                        "id": "1",
                        "name": "code_definitions",
                        "result": {"kind": "code_definitions", "symbol": "bad", "ok": False},
                    },
                ],
            )

            summary = summarize_session(root, "run-1")
            text = format_session_summary(summary)

        self.assertFalse(summary.completed)
        self.assertTrue(summary.failed)
        self.assertIn("code_definitions", text)
        self.assertNotIn("SECRET_SYMBOL", text)
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

    def test_summarize_session_marks_failed_python_rename_preview_result(self) -> None:
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
                        "name": "python_rename_preview",
                        "input": {"symbol": "SECRET_SYMBOL", "new_name": "execute_agent"},
                    },
                    {
                        "type": "tool_result",
                        "iteration": 1,
                        "id": "1",
                        "name": "python_rename_preview",
                        "result": {"kind": "python_rename_preview", "symbol": "bad-name", "ok": False},
                    },
                ],
            )

            summary = summarize_session(root, "run-1")
            text = format_session_summary(summary)

        self.assertFalse(summary.completed)
        self.assertTrue(summary.failed)
        self.assertIn("python_rename_preview", text)
        self.assertNotIn("SECRET_SYMBOL", text)

    def test_summarize_session_marks_failed_python_rename_result(self) -> None:
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
                        "name": "python_rename",
                        "input": {"symbol": "SECRET_SYMBOL", "new_name": "execute_agent"},
                    },
                    {
                        "type": "tool_result",
                        "iteration": 1,
                        "id": "1",
                        "name": "python_rename",
                        "result": {"kind": "python_rename", "symbol": "bad-name", "ok": False},
                    },
                ],
            )

            summary = summarize_session(root, "run-1")
            text = format_session_summary(summary)

        self.assertFalse(summary.completed)
        self.assertTrue(summary.failed)
        self.assertIn("python_rename", text)
        self.assertNotIn("SECRET_SYMBOL", text)

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

    def test_summarize_session_marks_failed_project_commands_result(self) -> None:
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
                        "name": "project_commands",
                        "input": {"max_files": 201, "path": "SECRET_PATH"},
                    },
                    {
                        "type": "tool_result",
                        "iteration": 1,
                        "id": "1",
                        "name": "project_commands",
                        "result": {"kind": "project_commands", "ok": False, "message": "invalid max_files"},
                    },
                ],
            )

            summary = summarize_session(root, "run-1")
            text = format_session_summary(summary)

        self.assertFalse(summary.completed)
        self.assertTrue(summary.failed)
        self.assertIn("project_commands", text)
        self.assertNotIn("SECRET_PATH", text)

    def test_summarize_session_marks_failed_project_manifests_result(self) -> None:
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
                        "name": "project_manifests",
                        "input": {"max_items": 2001, "path": "SECRET_PATH"},
                    },
                    {
                        "type": "tool_result",
                        "iteration": 1,
                        "id": "1",
                        "name": "project_manifests",
                        "result": {"kind": "project_manifests", "ok": False, "message": "invalid max_items"},
                    },
                ],
            )

            summary = summarize_session(root, "run-1")
            text = format_session_summary(summary)

        self.assertFalse(summary.completed)
        self.assertTrue(summary.failed)
        self.assertIn("project_manifests", text)
        self.assertNotIn("SECRET_PATH", text)

    def test_summarize_session_marks_failed_project_overview_result(self) -> None:
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
                        "name": "project_overview",
                        "input": {"max_files": 0, "path": "SECRET_PATH"},
                    },
                    {
                        "type": "tool_result",
                        "iteration": 1,
                        "id": "1",
                        "name": "project_overview",
                        "result": {"kind": "project_overview", "ok": False, "message": "invalid overview"},
                    },
                ],
            )

            summary = summarize_session(root, "run-1")
            text = format_session_summary(summary)

        self.assertFalse(summary.completed)
        self.assertTrue(summary.failed)
        self.assertIn("project_overview", text)
        self.assertNotIn("SECRET_PATH", text)

    def test_summarize_session_marks_failed_final_review_result(self) -> None:
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
                        "name": "final_review",
                        "input": {"max_checks": 0, "path": "SECRET_PATH"},
                    },
                    {
                        "type": "tool_result",
                        "iteration": 1,
                        "id": "1",
                        "name": "final_review",
                        "result": {"kind": "final_review", "ok": False, "message": "invalid final review"},
                    },
                ],
            )

            summary = summarize_session(root, "run-1")
            text = format_session_summary(summary)

        self.assertFalse(summary.completed)
        self.assertTrue(summary.failed)
        self.assertIn("final_review", text)
        self.assertNotIn("SECRET_PATH", text)

    def test_summarize_session_marks_failed_environment_info_result(self) -> None:
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
                        "name": "environment_info",
                        "input": {"path": "SECRET_PATH"},
                    },
                    {
                        "type": "tool_result",
                        "iteration": 1,
                        "id": "1",
                        "name": "environment_info",
                        "result": {"kind": "environment_info", "ok": False, "message": "environment read failed"},
                    },
                ],
            )

            summary = summarize_session(root, "run-1")
            text = format_session_summary(summary)

        self.assertFalse(summary.completed)
        self.assertTrue(summary.failed)
        self.assertIn("environment_info", text)
        self.assertNotIn("SECRET_PATH", text)

    def test_summarize_session_marks_failed_command_check_result(self) -> None:
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
                        "name": "command_check",
                        "input": {"command": "SECRET_COMMAND", "cwd": "SECRET_PATH"},
                    },
                    {
                        "type": "tool_result",
                        "iteration": 1,
                        "id": "1",
                        "name": "command_check",
                        "result": {"kind": "command_check", "ok": False, "message": "command blocked"},
                    },
                    {
                        "type": "tool_call",
                        "iteration": 2,
                        "id": "2",
                        "name": "check_start_command",
                        "input": {"command": "SECRET_START_COMMAND", "cwd": "SECRET_START_PATH"},
                    },
                    {
                        "type": "tool_result",
                        "iteration": 2,
                        "id": "2",
                        "name": "check_start_command",
                        "result": {"kind": "check_start_command", "ok": False, "message": "start command blocked"},
                    },
                    {
                        "type": "tool_call",
                        "iteration": 3,
                        "id": "port",
                        "name": "port_check",
                        "input": {"host": "SECRET_HOST", "port": 1234},
                    },
                    {
                        "type": "tool_result",
                        "iteration": 3,
                        "id": "port",
                        "name": "port_check",
                        "result": {"kind": "port_check", "ok": False, "message": "port check failed"},
                    },
                    {
                        "type": "tool_call",
                        "iteration": 3,
                        "id": "http",
                        "name": "http_check",
                        "input": {"url": "http://SECRET_HOST/SECRET_PATH"},
                    },
                    {
                        "type": "tool_result",
                        "iteration": 3,
                        "id": "http",
                        "name": "http_check",
                        "result": {"kind": "http_check", "ok": False, "message": "http check failed"},
                    },
                    {
                        "type": "tool_call",
                        "iteration": 3,
                        "id": "3",
                        "name": "check_stop_process",
                        "input": {"process_id": "SECRET_PROCESS_ID"},
                    },
                    {
                        "type": "tool_result",
                        "iteration": 3,
                        "id": "3",
                        "name": "check_stop_process",
                        "result": {"kind": "check_stop_process", "ok": False, "message": "unknown process"},
                    },
                    {
                        "type": "tool_call",
                        "iteration": 4,
                        "id": "4",
                        "name": "wait_process",
                        "input": {"process_id": "SECRET_WAIT_PROCESS_ID"},
                    },
                    {
                        "type": "tool_result",
                        "iteration": 4,
                        "id": "4",
                        "name": "wait_process",
                        "result": {"kind": "wait_process", "ok": False, "message": "unknown process"},
                    },
                    {
                        "type": "tool_call",
                        "iteration": 4,
                        "id": "write-check",
                        "name": "check_write_process",
                        "input": {"process_id": "SECRET_WRITE_PROCESS_ID", "content": "SECRET_STDIN"},
                    },
                    {
                        "type": "tool_result",
                        "iteration": 4,
                        "id": "write-check",
                        "name": "check_write_process",
                        "result": {"kind": "check_write_process", "ok": False, "message": "cannot write"},
                    },
                    {
                        "type": "tool_call",
                        "iteration": 4,
                        "id": "write",
                        "name": "write_process",
                        "input": {"process_id": "SECRET_WRITE_PROCESS_ID", "content": "SECRET_STDIN"},
                    },
                    {
                        "type": "tool_result",
                        "iteration": 4,
                        "id": "write",
                        "name": "write_process",
                        "result": {"kind": "write_process", "ok": False, "message": "write failed"},
                    },
                    {
                        "type": "tool_call",
                        "iteration": 5,
                        "id": "5",
                        "name": "check_stop_all_processes",
                        "input": {"ignored": "SECRET_STOP_ALL_INPUT"},
                    },
                    {
                        "type": "tool_result",
                        "iteration": 5,
                        "id": "5",
                        "name": "check_stop_all_processes",
                        "result": {"kind": "check_stop_all_processes", "ok": False, "message": "check all failed"},
                    },
                    {
                        "type": "tool_call",
                        "iteration": 6,
                        "id": "6",
                        "name": "stop_all_processes",
                        "input": {"ignored": "SECRET_STOP_ALL_ACTION"},
                    },
                    {
                        "type": "tool_result",
                        "iteration": 6,
                        "id": "6",
                        "name": "stop_all_processes",
                        "result": {"kind": "stop_all_processes", "ok": False, "message": "stop all failed"},
                    },
                ],
            )

            summary = summarize_session(root, "run-1")
            text = format_session_summary(summary)

        self.assertFalse(summary.completed)
        self.assertTrue(summary.failed)
        self.assertIn("command_check", text)
        self.assertIn("check_start_command", text)
        self.assertIn("port_check", text)
        self.assertIn("http_check", text)
        self.assertIn("check_stop_process", text)
        self.assertIn("wait_process", text)
        self.assertIn("check_write_process", text)
        self.assertIn("write_process", text)
        self.assertIn("check_stop_all_processes", text)
        self.assertIn("stop_all_processes", text)
        self.assertNotIn("SECRET_COMMAND", text)
        self.assertNotIn("SECRET_PATH", text)
        self.assertNotIn("SECRET_START_COMMAND", text)
        self.assertNotIn("SECRET_START_PATH", text)
        self.assertNotIn("SECRET_HOST", text)
        self.assertNotIn("SECRET_PATH", text)
        self.assertNotIn("SECRET_PROCESS_ID", text)
        self.assertNotIn("SECRET_WAIT_PROCESS_ID", text)
        self.assertNotIn("SECRET_WRITE_PROCESS_ID", text)
        self.assertNotIn("SECRET_STDIN", text)
        self.assertNotIn("SECRET_STOP_ALL_INPUT", text)
        self.assertNotIn("SECRET_STOP_ALL_ACTION", text)

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
