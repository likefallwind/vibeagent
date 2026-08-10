from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

from tests.test_agent_hooks import HookClient
from vibeagent.agent import run_agent
from vibeagent.agent_hook_mcp import expand_mcp_hook_input
from vibeagent.types import ApprovalDecision
from vibeagent.workspace import create_run_workspace
from vibeagent.workspace_hooks import read_project_hooks


MCP_HOOK_SERVER_SOURCE = r'''
import json
import sys

for raw in sys.stdin:
    message = json.loads(raw)
    method = message.get("method")
    if method == "initialize":
        result = {
            "protocolVersion": "2025-11-25",
            "capabilities": {"tools": {}},
            "serverInfo": {"name": "hook-server", "version": "1.0"},
        }
    elif method == "tools/list":
        result = {
            "tools": [
                {
                    "name": "policy",
                    "description": "Evaluate hook input",
                    "inputSchema": {"type": "object"},
                }
            ]
        }
    elif method == "tools/call":
        arguments = message.get("params", {}).get("arguments", {})
        mode = arguments.get("mode")
        if mode == "error":
            result = {
                "content": [{"type": "text", "text": "policy service unavailable"}],
                "isError": True,
            }
        elif mode == "plain":
            result = {
                "content": [
                    {
                        "type": "text",
                        "text": "MCP lifecycle context: " + str(arguments.get("source", "")),
                    }
                ],
                "isError": False,
            }
        else:
            output = {
                "hookSpecificOutput": {
                    "hookEventName": "PreToolUse",
                    "permissionDecision": "deny",
                    "permissionDecisionReason": "MCP policy denied " + str(arguments.get("path", "unknown")),
                    "additionalContext": "MCP policy evaluated the requested write.",
                }
            }
            result = {
                "content": [{"type": "text", "text": json.dumps(output)}],
                "structuredContent": {"audit": "must not alter hook stdout"},
                "isError": False,
            }
    else:
        continue
    print(json.dumps({"jsonrpc": "2.0", "id": message["id"], "result": result}), flush=True)
'''


def _approve(_request) -> ApprovalDecision:
    return ApprovalDecision(approved=True, message="approved")


def _write_mcp_server(root: Path) -> None:
    (root / "mcp_hook_server.py").write_text(
        MCP_HOOK_SERVER_SOURCE, encoding="utf-8"
    )
    (root / ".mcp.json").write_text(
        json.dumps(
            {
                "mcpServers": {
                    "hooks": {
                        "command": sys.executable,
                        "args": ["mcp_hook_server.py"],
                        "cwd": ".",
                    }
                }
            }
        ),
        encoding="utf-8",
    )


def _write_mcp_hook(
    root: Path,
    input_payload: dict[str, object],
    *,
    event: str = "PreToolUse",
    matcher: str = "write_file",
) -> None:
    path = root / ".vibeagent/hooks.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(
            {
                event: [
                    {
                        "matcher": matcher,
                        "hooks": [
                            {
                                "type": "mcp_tool",
                                "server": "hooks",
                                "tool": "policy",
                                "input": input_payload,
                                "timeout": 2,
                            }
                        ],
                    }
                ]
            }
        ),
        encoding="utf-8",
    )


class McpHookConfigTests(unittest.TestCase):
    def test_loads_mcp_tool_handler_fields(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-mcp-hook-") as base:
            root = Path(base)
            _write_mcp_hook(
                root,
                {
                    "path": "${tool_input.path}",
                    "event": "${hook_event_name}",
                },
            )
            config = read_project_hooks(create_run_workspace(root))

        self.assertIsNone(config.error)
        hook = config.hooks[0]
        self.assertEqual(hook.handler_type, "mcp_tool")
        self.assertEqual(hook.mcp_server, "hooks")
        self.assertEqual(hook.mcp_tool, "policy")
        self.assertEqual(hook.mcp_input["path"], "${tool_input.path}")
        self.assertEqual(hook.timeout_ms, 2_000)

    def test_rejects_invalid_mcp_tool_handler_fields(self) -> None:
        invalid_handlers = [
            {"type": "mcp_tool", "server": "bad:name", "tool": "policy"},
            {"type": "mcp_tool", "server": "hooks", "tool": "bad:name"},
            {"type": "mcp_tool", "server": "hooks", "tool": "policy", "input": []},
            {"type": "mcp_tool", "server": "hooks", "tool": "policy", "async": True},
            {
                "type": "mcp_tool",
                "server": "hooks",
                "tool": "policy",
                "input": {"value": "x" * 50_001},
            },
        ]
        for index, handler in enumerate(invalid_handlers):
            with self.subTest(index=index), tempfile.TemporaryDirectory(
                prefix="vibeagent-mcp-hook-"
            ) as base:
                root = Path(base)
                path = root / ".vibeagent/hooks.json"
                path.parent.mkdir(parents=True)
                path.write_text(
                    json.dumps(
                        {
                            "PreToolUse": [
                                {"matcher": "Write", "hooks": [handler]}
                            ]
                        }
                    ),
                    encoding="utf-8",
                )
                config = read_project_hooks(create_run_workspace(root))

            self.assertIsNotNone(config.error)

    def test_expands_nested_paths_and_preserves_exact_json_values(self) -> None:
        expanded = expand_mcp_hook_input(
            {
                "path": "${tool_input.path}",
                "label": "event=${hook_event_name}",
                "complete": "${tool_input}",
                "first": "${items.0.name}",
            },
            {
                "hook_event_name": "PreToolUse",
                "tool_input": {"path": "src/app.py", "enabled": True},
                "items": [{"name": "one"}],
            },
        )

        self.assertEqual(expanded["path"], "src/app.py")
        self.assertEqual(expanded["label"], "event=PreToolUse")
        self.assertEqual(
            expanded["complete"], {"path": "src/app.py", "enabled": True}
        )
        self.assertEqual(expanded["first"], "one")

    def test_missing_or_oversized_expanded_values_are_rejected(self) -> None:
        with self.assertRaisesRegex(ValueError, "unavailable"):
            expand_mcp_hook_input(
                {"path": "${tool_input.missing}"}, {"tool_input": {}}
            )
        with self.assertRaisesRegex(ValueError, "expanded input exceeds"):
            expand_mcp_hook_input(
                {"value": "${tool_input.value}"},
                {"tool_input": {"value": "x" * 50_001}},
            )

        deeply_nested: object = "leaf"
        for _ in range(22):
            deeply_nested = {"next": deeply_nested}
        with self.assertRaisesRegex(ValueError, "exceeds depth"):
            expand_mcp_hook_input(
                {"value": "${tool_input.value}"},
                {"tool_input": {"value": deeply_nested}},
            )


class McpHookIntegrationTests(unittest.TestCase):
    def test_pre_tool_mcp_hook_denies_write_with_expanded_input(self) -> None:
        client = HookClient(
            [
                [
                    {
                        "type": "tool_call",
                        "id": "write-1",
                        "name": "write_file",
                        "input": {"path": "app.py", "content": "x = 1\n"},
                    }
                ],
                [{"type": "text", "text": "The MCP policy denied the write."}],
            ]
        )
        approvals: list[str] = []

        def approve(request):
            approvals.append(request.action_type)
            return ApprovalDecision(approved=True, message="approved")

        with tempfile.TemporaryDirectory(prefix="vibeagent-mcp-hook-") as base:
            root = Path(base)
            _write_mcp_server(root)
            _write_mcp_hook(
                root,
                {
                    "path": "${tool_input.path}",
                    "event": "${hook_event_name}",
                },
            )
            result = run_agent(
                "Write app.py",
                base_dir=root,
                client=client,
                max_iterations=2,
                approval_handler=approve,
            )

            self.assertFalse((root / "app.py").exists())

        self.assertTrue(result.success)
        self.assertEqual(approvals, ["mcp_call"])
        self.assertIn("MCP policy denied app.py", str(client.messages[1][-1].content))
        self.assertIn(
            "MCP policy evaluated the requested write.",
            str(client.messages[1][-1].content),
        )

    def test_mcp_hook_error_is_non_blocking(self) -> None:
        client = HookClient(
            [
                [
                    {
                        "type": "tool_call",
                        "id": "write-1",
                        "name": "write_file",
                        "input": {"path": "app.py", "content": "x = 1\n"},
                    }
                ],
                [{"type": "text", "text": "Created app.py despite policy outage."}],
            ]
        )
        with tempfile.TemporaryDirectory(prefix="vibeagent-mcp-hook-") as base:
            root = Path(base)
            _write_mcp_server(root)
            _write_mcp_hook(root, {"mode": "error"})
            result = run_agent(
                "Write app.py",
                base_dir=root,
                client=client,
                max_iterations=2,
                approval_handler=_approve,
            )
            content = (root / "app.py").read_text(encoding="utf-8")
            events = [
                json.loads(line)
                for line in (
                    root / ".vibeagent/sessions" / result.run_id / "events.jsonl"
                ).read_text(encoding="utf-8").splitlines()
            ]

        self.assertTrue(result.success)
        self.assertEqual(content, "x = 1\n")
        completed = next(
            event
            for event in events
            if event["type"] == "hook_completed"
            and event["result"].get("handler_type") == "mcp_tool"
        )
        self.assertTrue(completed["result"]["non_blocking_error"])

    def test_unconfigured_mcp_server_is_non_blocking(self) -> None:
        client = HookClient(
            [
                [
                    {
                        "type": "tool_call",
                        "id": "write-1",
                        "name": "write_file",
                        "input": {"path": "app.py", "content": "x = 1\n"},
                    }
                ],
                [{"type": "text", "text": "Created app.py without MCP server."}],
            ]
        )
        with tempfile.TemporaryDirectory(prefix="vibeagent-mcp-hook-") as base:
            root = Path(base)
            _write_mcp_hook(root, {"mode": "error"})
            result = run_agent(
                "Write app.py",
                base_dir=root,
                client=client,
                max_iterations=2,
                approval_handler=_approve,
            )
            content = (root / "app.py").read_text(encoding="utf-8")
            events = [
                json.loads(line)
                for line in (
                    root / ".vibeagent/sessions" / result.run_id / "events.jsonl"
                ).read_text(encoding="utf-8").splitlines()
            ]

        self.assertTrue(result.success)
        self.assertEqual(content, "x = 1\n")
        mcp_hook = next(
            event["result"]
            for event in events
            if event["type"] == "hook_completed"
            and event["result"].get("handler_type") == "mcp_tool"
        )
        self.assertFalse(mcp_hook["ok"])
        self.assertTrue(mcp_hook["non_blocking_error"])
        self.assertIn("not found", mcp_hook["message"])

    def test_lifecycle_mcp_plain_text_adds_model_context(self) -> None:
        client = HookClient(
            [[{"type": "text", "text": "Used MCP startup context."}]]
        )
        with tempfile.TemporaryDirectory(prefix="vibeagent-mcp-hook-") as base:
            root = Path(base)
            _write_mcp_server(root)
            _write_mcp_hook(
                root,
                {"mode": "plain", "source": "${source}"},
                event="SessionStart",
                matcher="startup",
            )
            result = run_agent(
                "Inspect project",
                base_dir=root,
                client=client,
                max_iterations=1,
                approval_handler=_approve,
            )

        self.assertTrue(result.success)
        initial_user = client.messages[0][1].content
        self.assertIsInstance(initial_user, str)
        self.assertIn(
            "SessionStart hook context:\nMCP lifecycle context: startup",
            initial_user,
        )


if __name__ == "__main__":
    unittest.main()
