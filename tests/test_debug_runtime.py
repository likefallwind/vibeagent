from __future__ import annotations

from contextlib import redirect_stderr
import io
import json
from pathlib import Path
import stat
import tempfile
import unittest
from unittest.mock import patch

from vibeagent import cli as cli_module
from vibeagent.agent_runtime_utils import append_session_event
from vibeagent.agent_result import AgentResult
from vibeagent.debug_runtime import (
    DebugOptions,
    DebugRuntime,
    combine_agent_loggers,
    parse_debug_filter,
    resolve_debug_options,
)
from vibeagent.workspace_core import create_run_workspace


class DebugRuntimeTests(unittest.TestCase):
    def test_equals_form_binds_filter_while_space_form_leaves_task_untouched(self) -> None:
        filtered = cli_module.parse_args(["--debug=api,!mcp", "inspect"])
        unfiltered = cli_module.parse_args(["--debug", "api,mcp", "inspect"])
        after_separator = cli_module.parse_args(["--", "--debug=api", "inspect"])

        self.assertTrue(filtered.debug)
        self.assertEqual(filtered._debug_filter, "api,!mcp")
        self.assertEqual(filtered.task, ["inspect"])
        self.assertTrue(unfiltered.debug)
        self.assertIsNone(unfiltered._debug_filter)
        self.assertEqual(unfiltered.task, ["api,mcp", "inspect"])
        self.assertFalse(after_separator.debug)
        self.assertEqual(after_separator.task, ["--debug=api", "inspect"])

    def test_filter_supports_includes_excludes_and_rejects_invalid_values(self) -> None:
        selected = parse_debug_filter("api,tools,!mcp")
        excluded = parse_debug_filter("!hooks")

        self.assertTrue(selected.allows("api"))
        self.assertFalse(selected.allows("mcp"))
        self.assertFalse(selected.allows("session"))
        self.assertTrue(excluded.allows("api"))
        self.assertFalse(excluded.allows("hooks"))
        for value in ("api,,mcp", "bad category", "api,!api", "!"):
            with self.subTest(value=value), self.assertRaises(ValueError):
                parse_debug_filter(value)

    def test_file_runtime_writes_private_filtered_redacted_jsonl(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-debug-") as base:
            path = Path(base) / "debug.jsonl"
            options = resolve_debug_options(
                False,
                "api,!mcp",
                str(path),
                invocation_root=Path(base),
            )
            runtime = DebugRuntime(options)

            runtime.emit("mcp", "ignored", {"value": "not written"})
            runtime.emit("api", "request", {"api_key": "secret", "attempt": 1})
            rows = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]
            mode = stat.S_IMODE(path.stat().st_mode)

        self.assertTrue(options.enabled)
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["category"], "api")
        self.assertNotIn("secret", json.dumps(rows[0]))
        self.assertEqual(mode, 0o600)

    def test_event_scope_and_status_logger_share_category_pipeline(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-debug-events-") as base:
            root = Path(base)
            path = root / "debug.jsonl"
            runtime = DebugRuntime(
                resolve_debug_options(True, None, str(path), invocation_root=root)
            )
            workspace = create_run_workspace(root, "run-1")

            with runtime.event_scope(workspace):
                append_session_event(
                    workspace.session_dir,
                    "mcp_call",
                    {"server": "docs", "token": "secret"},
                )
                assert runtime.logger is not None
                runtime.logger("thinking", "provider api_key=secret")
            rows = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]

        self.assertEqual([row["category"] for row in rows], ["mcp", "api"])
        self.assertEqual([row["event"] for row in rows], ["mcp_call", "status"])
        self.assertNotIn("secret", json.dumps(rows))

    def test_stderr_mode_does_not_write_stdout_and_combines_loggers(self) -> None:
        runtime = DebugRuntime(DebugOptions(enabled=True))
        calls: list[tuple[str, str | None]] = []
        combined = combine_agent_loggers(
            lambda status, detail: calls.append((status, detail)),
            runtime.logger,
        )
        stderr = io.StringIO()

        with redirect_stderr(stderr):
            assert combined is not None
            combined("reading file", "README.md")

        self.assertEqual(calls, [("reading file", "README.md")])
        self.assertIn("[debug:tools] status", stderr.getvalue())

    def test_oversized_records_are_replaced_with_bounded_metadata(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-debug-large-") as base:
            root = Path(base)
            path = root / "debug.jsonl"
            runtime = DebugRuntime(
                resolve_debug_options(True, None, str(path), invocation_root=root)
            )

            runtime.emit("session", "large", {"text": "x" * 110_000})
            row = json.loads(path.read_text(encoding="utf-8"))

        self.assertTrue(row["payload"]["truncated"])
        self.assertGreater(row["payload"]["originalChars"], 100_000)

    def test_file_write_failure_warns_once_without_interrupting_runtime(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-debug-failure-") as base:
            root = Path(base)
            path = root / "debug.jsonl"
            runtime = DebugRuntime(
                resolve_debug_options(True, None, str(path), invocation_root=root)
            )
            stderr = io.StringIO()

            with (
                patch(
                    "vibeagent.debug_runtime._append_private_line",
                    side_effect=OSError("disk unavailable"),
                ),
                redirect_stderr(stderr),
            ):
                runtime.emit("session", "first", {})
                runtime.emit("session", "second", {})

        self.assertEqual(stderr.getvalue().count("Debug log write failed"), 1)

    def test_debug_file_rejects_missing_parent_directory_and_symlink(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-debug-path-") as base:
            root = Path(base)
            with self.assertRaisesRegex(ValueError, "parent directory"):
                resolve_debug_options(
                    True,
                    None,
                    "missing/debug.log",
                    invocation_root=root,
                )
            target = root / "target.log"
            target.write_text("existing\n", encoding="utf-8")
            link = root / "debug.log"
            try:
                link.symlink_to(target)
            except OSError:
                return
            with self.assertRaisesRegex(ValueError, "non-symlink"):
                resolve_debug_options(True, None, str(link), invocation_root=root)

    def test_interactive_cli_records_agent_status_and_session_events(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-debug-cli-") as base:
            root = Path(base)
            path = root / "interactive-debug.jsonl"

            def run_agent(_task, **kwargs):
                workspace = kwargs["workspace"]
                kwargs["logger"]("thinking", "starting")
                append_session_event(workspace.session_dir, "mcp_tools", {"server": "docs"})
                return AgentResult(True, "done", root, workspace.run_id, 1, [], [])

            with (
                patch("builtins.input", side_effect=["inspect", "/exit"]),
                patch("vibeagent.cli.create_chat_client", return_value=object()),
                patch("vibeagent.cli.run_agent", side_effect=run_agent),
                redirect_stderr(io.StringIO()),
                patch("sys.stdout", new=io.StringIO()),
            ):
                exit_code = cli_module.main(
                    ["--cwd", str(root), "--debug-file", str(path)]
                )
            rows = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]

        self.assertEqual(exit_code, 0)
        self.assertIn("api", {row["category"] for row in rows})
        self.assertIn("mcp", {row["category"] for row in rows})

    def test_print_cli_applies_equals_filter_without_polluting_stdout(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-debug-print-") as base:
            root = Path(base)
            path = root / "print-debug.jsonl"

            def run_agent(_task, **kwargs):
                workspace = kwargs["workspace"]
                kwargs["logger"]("thinking", "starting")
                append_session_event(workspace.session_dir, "mcp_call", {"server": "docs"})
                append_session_event(workspace.session_dir, "tool_result", {"kind": "read_file"})
                return AgentResult(True, "done", root, workspace.run_id, 1, [], [])

            stdout = io.StringIO()
            with (
                patch("vibeagent.cli.create_chat_client", return_value=object()),
                patch("vibeagent.cli.run_agent", side_effect=run_agent),
                patch("sys.stdout", new=stdout),
            ):
                exit_code = cli_module.main(
                    [
                        "-p",
                        "--cwd",
                        str(root),
                        "--debug=api,mcp",
                        "--debug-file",
                        str(path),
                        "inspect",
                    ]
                )
            rows = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]

        self.assertEqual(exit_code, 0)
        self.assertNotIn("[debug:", stdout.getvalue())
        self.assertEqual({row["category"] for row in rows}, {"api", "mcp"})


if __name__ == "__main__":
    unittest.main()
