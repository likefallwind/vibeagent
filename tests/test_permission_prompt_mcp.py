from __future__ import annotations

import json
from dataclasses import replace
from pathlib import Path
import sys
import tempfile
import unittest
from types import SimpleNamespace
from unittest.mock import Mock, patch

from vibeagent.mcp_action_executor import execute_mcp_action
from vibeagent.permission_prompt_mcp import (
    PermissionPromptTool,
    build_mcp_permission_prompt_handler,
    resolve_permission_prompt_tool,
)
from vibeagent.types import ApprovalRequest, McpCallAction
from vibeagent.workspace_core import RunWorkspace


class PermissionPromptMcpTests(unittest.TestCase):
    def test_real_stdio_permission_tool_resolves_and_authorizes(self) -> None:
        server_source = r'''
import json
import sys

for raw in sys.stdin:
    message = json.loads(raw)
    method = message.get("method")
    if method == "initialize":
        result = {
            "protocolVersion": "2025-11-25",
            "capabilities": {"tools": {}},
            "serverInfo": {"name": "policy", "version": "1"},
        }
    elif method == "tools/list":
        result = {
            "tools": [{"name": "authorize", "inputSchema": {"type": "object"}}]
        }
    elif method == "tools/call":
        prompt_input = message["params"]["arguments"]["input"]
        result = {
            "content": [{
                "type": "text",
                "text": json.dumps({"behavior": "allow", "updatedInput": prompt_input}),
            }]
        }
    else:
        continue
    print(json.dumps({"jsonrpc": "2.0", "id": message["id"], "result": result}), flush=True)
'''
        with tempfile.TemporaryDirectory(prefix="vibeagent-permission-mcp-") as base:
            root = Path(base)
            (root / "policy_server.py").write_text(server_source, encoding="utf-8")
            (root / ".mcp.json").write_text(
                json.dumps(
                    {
                        "mcpServers": {
                            "policy": {
                                "command": sys.executable,
                                "args": ["policy_server.py"],
                            }
                        }
                    }
                ),
                encoding="utf-8",
            )
            workspace = RunWorkspace(
                root=root,
                run_id="run-1",
                session_dir=root / ".vibeagent" / "sessions" / "run-1",
            )

            tool = resolve_permission_prompt_tool(workspace, "authorize")
            reserved_workspace = replace(
                workspace,
                permission_prompt_tool=tool.qualified_name,
            )
            decision = build_mcp_permission_prompt_handler(
                reserved_workspace,
                tool,
            )(
                ApprovalRequest("write_file", "src/app.py", "writes a file")
            )

        self.assertEqual(tool.qualified_name, "mcp__policy__authorize")
        self.assertTrue(decision.approved)

    def test_resolves_qualified_and_unique_bare_tool_names(self) -> None:
        workspace = _workspace()
        listed = Mock(return_value=frozenset({"authorize"}))

        qualified = resolve_permission_prompt_tool(
            workspace,
            "mcp__policy__authorize",
            list_tools_func=listed,
        )

        self.assertEqual(qualified.qualified_name, "mcp__policy__authorize")
        listed.assert_called_once_with(workspace, "policy", timeout_ms=10_000)

        listed.reset_mock()
        listed.side_effect = lambda _workspace, server, **_kwargs: (
            frozenset({"authorize"}) if server == "policy" else frozenset({"other"})
        )
        with patch(
            "vibeagent.permission_prompt_mcp.read_mcp_server_configs",
            return_value=[SimpleNamespace(name="docs"), SimpleNamespace(name="policy")],
        ):
            bare = resolve_permission_prompt_tool(
                workspace,
                "authorize",
                list_tools_func=listed,
            )

        self.assertEqual(bare.qualified_name, "mcp__policy__authorize")

    def test_rejects_missing_ambiguous_and_invalid_tool_references(self) -> None:
        workspace = _workspace()
        with self.assertRaisesRegex(ValueError, "not advertised"):
            resolve_permission_prompt_tool(
                workspace,
                "policy/missing",
                list_tools_func=Mock(return_value=frozenset()),
            )
        with patch(
            "vibeagent.permission_prompt_mcp.read_mcp_server_configs",
            return_value=[SimpleNamespace(name="one"), SimpleNamespace(name="two")],
        ), self.assertRaisesRegex(ValueError, "ambiguous"):
            resolve_permission_prompt_tool(
                workspace,
                "authorize",
                list_tools_func=Mock(return_value=frozenset({"authorize"})),
            )
        for value in ("", "mcp__missing", "bad server/tool", "server/"):
            with self.subTest(value=value), self.assertRaises(ValueError):
                resolve_permission_prompt_tool(
                    workspace,
                    value,
                    list_tools_func=Mock(return_value=frozenset()),
                )

    def test_handler_sends_bounded_request_and_accepts_allow_or_deny(self) -> None:
        workspace = _workspace(permission_prompt_tool="mcp__policy__authorize")
        tool = PermissionPromptTool("policy", "authorize")
        call = Mock(
            return_value={
                "content": [
                    {
                        "type": "text",
                        "text": json.dumps(
                            {
                                "behavior": "allow",
                                "updatedInput": {
                                    "target": "src/app.py",
                                    "risk": "writes a file",
                                    "preview": "diff",
                                },
                            }
                        ),
                    }
                ]
            }
        )
        handler = build_mcp_permission_prompt_handler(
            workspace,
            tool,
            timeout_ms=4321,
            call_tool_func=call,
        )
        request = ApprovalRequest(
            action_type="write_file",
            target="src/app.py",
            risk="writes a file",
            preview="diff",
        )

        allowed = handler(request)

        self.assertTrue(allowed.approved)
        call.assert_called_once_with(
            workspace,
            "policy",
            "authorize",
            {
                "tool_name": "write_file",
                "input": {
                    "target": "src/app.py",
                    "risk": "writes a file",
                    "preview": "diff",
                },
            },
            timeout_ms=4321,
        )

        call.return_value = {
            "structuredContent": {"behavior": "deny", "message": "policy blocked it"}
        }
        denied = handler(request)
        self.assertFalse(denied.approved)
        self.assertEqual(denied.message, "policy blocked it")

    def test_handler_fails_closed_on_errors_or_unsafe_decisions(self) -> None:
        workspace = _workspace(permission_prompt_tool="mcp__policy__authorize")
        tool = PermissionPromptTool("policy", "authorize")
        request = ApprovalRequest("run_command", "pytest", "runs a command")
        unsafe_results = (
            [],
            {"content": [{"type": "text", "text": "not-json"}]},
            {"structuredContent": {"behavior": "allow", "updatedInput": {"target": "rm"}}},
            {"structuredContent": {"behavior": "deny", "message": ""}},
            {"structuredContent": {"behavior": "maybe"}},
            {"isError": True, "content": []},
        )
        for result in unsafe_results:
            with self.subTest(result=result):
                handler = build_mcp_permission_prompt_handler(
                    workspace,
                    tool,
                    call_tool_func=Mock(return_value=result),
                )
                decision = handler(request)
                self.assertFalse(decision.approved)
                self.assertIn("failed closed", decision.message)

        handler = build_mcp_permission_prompt_handler(
            workspace,
            tool,
            call_tool_func=Mock(side_effect=TimeoutError("secret=token")),
        )
        decision = handler(request)
        self.assertFalse(decision.approved)
        self.assertNotIn("token", decision.message)

    def test_reserved_permission_tool_cannot_be_called_as_model_mcp_action(self) -> None:
        workspace = _workspace(permission_prompt_tool="mcp__policy__authorize")
        action = McpCallAction(
            type="mcp_call",
            server="policy",
            name="authorize",
            arguments={"behavior": "allow"},
        )

        observation = execute_mcp_action(workspace, action)

        self.assertIsNotNone(observation)
        self.assertFalse(observation.ok)
        self.assertIn("reserved", observation.error or "")


def _workspace(*, permission_prompt_tool: str | None = None) -> RunWorkspace:
    root = Path(tempfile.gettempdir()).resolve()
    return RunWorkspace(
        root=root,
        run_id="test-run",
        session_dir=root / "permission-prompt-test",
        permission_prompt_tool=permission_prompt_tool,
    )


if __name__ == "__main__":
    unittest.main()
