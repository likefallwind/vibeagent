from __future__ import annotations

import io
import json
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import patch
from uuid import UUID

from vibeagent.cli_stream_output import JsonEventStream
from vibeagent.cli_stream_protocol import StreamSessionObserver


class CliStreamProtocolTests(unittest.TestCase):
    def setUp(self) -> None:
        self.output = io.StringIO()
        self.stream = JsonEventStream(self.output)
        self.session_dir = Path("/project/.vibeagent/sessions/run-1")
        self.workspace = SimpleNamespace(root=Path("/project"))

    def records(self) -> list[dict[str, object]]:
        return [json.loads(line) for line in self.output.getvalue().splitlines()]

    def test_emits_one_bounded_init_before_forwarding_the_tool_catalog_event(self) -> None:
        observer = StreamSessionObserver(
            self.stream,
            self.workspace,
            {
                "VIBEAGENT_PROVIDER": "minimax",
                "VIBEAGENT_MODEL": "m" * 300,
                "MINIMAX_API_KEY": "api-key-must-not-leak",
            },
        )
        event = {
            "type": "tool_catalog_initialized",
            "tools": ["Read", "Write", *[f"Tool-{index}" for index in range(100)]],
            "approval_policy": "ask",
        }

        with (
            patch("vibeagent.cli_stream_protocol.read_mcp_server_configs", return_value=[]),
            patch("vibeagent.cli_stream_protocol.enabled_plugin_manifests", return_value=[]),
        ):
            observer(self.session_dir, event)
            observer(self.session_dir, event)

        records = self.records()
        self.assertEqual([record["type"] for record in records], ["system", "event", "event"])
        init = records[0]
        self.assertEqual(init["subtype"], "init")
        self.assertEqual(init["provider"], "minimax")
        self.assertEqual(init["model"], "m" * 200)
        self.assertEqual(init["tools"][:2], ["Read", "Write"])
        self.assertEqual(len(init["tools"]), 100)
        self.assertTrue(init["tools_truncated"])
        self.assertEqual(init["permissionMode"], "ask")
        self.assertIn("system_init_v1", init["capabilities"])
        self.assertNotIn("api-key-must-not-leak", self.output.getvalue())

    def test_emits_api_retry_before_preserving_the_raw_model_error(self) -> None:
        observer = StreamSessionObserver(self.stream, self.workspace, {})

        observer(
            self.session_dir,
            {
                "type": "model_error",
                "attempt": 2,
                "attempts": 3,
                "will_retry": True,
                "retry_delay_ms": 250,
                "retry_reason": "transient_error",
                "error": "rate_limit",
                "status_code": 429,
            },
        )

        records = self.records()
        self.assertEqual([record["type"] for record in records], ["system", "event"])
        retry = records[0]
        self.assertEqual(retry["subtype"], "api_retry")
        self.assertEqual(retry["attempt"], 2)
        self.assertEqual(retry["max_retries"], 2)
        self.assertEqual(retry["retry_delay_ms"], 250)
        self.assertEqual(retry["error"], "rate_limit")
        self.assertEqual(retry["error_status"], 429)
        self.assertEqual(retry["retry_reason"], "transient_error")
        self.assertTrue(retry["uuid"])

    def test_metadata_failures_are_redacted_and_do_not_block_source_events(self) -> None:
        observer = StreamSessionObserver(
            self.stream,
            self.workspace,
            {"VIBEAGENT_PROVIDER": "unsupported", "VIBEAGENT_MODEL": "fallback-model"},
        )
        event = {"type": "tool_catalog_initialized", "tools": [], "approval_policy": "deny"}

        with (
            patch(
                "vibeagent.cli_stream_protocol.read_mcp_server_configs",
                side_effect=ValueError("api_key=server-secret"),
            ),
            patch(
                "vibeagent.cli_stream_protocol.enabled_plugin_manifests",
                side_effect=RuntimeError("token=plugin-secret"),
            ),
        ):
            observer(self.session_dir, event)

        records = self.records()
        self.assertEqual([record["type"] for record in records], ["system", "event"])
        init = records[0]
        self.assertEqual(init["provider"], "unsupported")
        self.assertEqual(init["model"], "fallback-model")
        self.assertEqual(init["mcp_servers"], [])
        self.assertEqual(init["plugins"], [])
        self.assertIn("[REDACTED]", self.output.getvalue())
        self.assertNotIn("server-secret", self.output.getvalue())
        self.assertNotIn("plugin-secret", self.output.getvalue())

    def test_explicit_hook_events_emit_sdk_lifecycle_before_raw_events(self) -> None:
        observer = StreamSessionObserver(
            self.stream,
            self.workspace,
            {},
            include_hook_events=True,
        )
        events = (
            {
                "type": "hook_started",
                "hook_id": "hook-1",
                "hook_name": "command:settings.json#1",
                "event": "PreToolUse",
            },
            {
                "type": "hook_progress",
                "hook_id": "hook-1",
                "hook_name": "command:settings.json#1",
                "event": "PreToolUse",
                "stdout": "working\n",
                "stderr": "",
                "output": "working\n",
            },
            {
                "type": "hook_response",
                "hook_id": "hook-1",
                "hook_name": "command:settings.json#1",
                "event": "PreToolUse",
                "stdout": "done\n",
                "stderr": "",
                "output": "done\n",
                "exit_code": 0,
                "outcome": "success",
            },
        )

        for event in events:
            observer(self.session_dir, event)

        records = self.records()
        system = records[::2]
        self.assertEqual(
            [record["subtype"] for record in system],
            ["hook_started", "hook_progress", "hook_response"],
        )
        self.assertTrue(all(record["hook_id"] == "hook-1" for record in system))
        self.assertTrue(all(record["hook_event"] == "PreToolUse" for record in system))
        self.assertEqual(system[-1]["outcome"], "success")
        self.assertEqual(system[-1]["exit_code"], 0)
        for record in system:
            UUID(record["uuid"])
        self.assertEqual([record["type"] for record in records[1::2]], ["event"] * 3)

    def test_setup_and_session_start_hook_events_are_visible_without_opt_in(self) -> None:
        observer = StreamSessionObserver(self.stream, self.workspace, {})

        for hook_event in ("PreToolUse", "Setup", "SessionStart"):
            observer(
                self.session_dir,
                {
                    "type": "hook_started",
                    "hook_id": f"hook-{hook_event}",
                    "hook_name": "command:settings.json#1",
                    "event": hook_event,
                },
            )

        records = self.records()
        visible = [record for record in records if record["type"] == "system"]
        self.assertEqual([record["hook_event"] for record in visible], ["Setup", "SessionStart"])


if __name__ == "__main__":
    unittest.main()
