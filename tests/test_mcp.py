import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from vibeagent.actions import execute_action, parse_tool_action
from vibeagent.agent import run_agent
from vibeagent.agent_approval import build_approval_request
from vibeagent.mcp_config import read_mcp_server_configs
from vibeagent.redaction import redact_jsonable_payload
from vibeagent.types import AssistantResponse, ChatMessage, ContentBlock, McpCallAction, McpToolsAction
from vibeagent.workspace import create_run_workspace


MCP_SERVER_SOURCE = r'''
import json
import os
import sys

for raw in sys.stdin:
    message = json.loads(raw)
    method = message.get("method")
    if method == "initialize":
        print(json.dumps({"jsonrpc": "2.0", "id": message["id"], "method": "sampling/createMessage", "params": {}}), flush=True)
        result = {
            "protocolVersion": "2025-11-25",
            "capabilities": {"tools": {}},
            "serverInfo": {"name": "test-server", "version": "1.0"},
        }
    elif method == "tools/list":
        result = {
            "tools": [
                {
                    "name": "echo",
                    "title": "Echo",
                    "description": "Echo JSON arguments",
                    "inputSchema": {"type": "object"},
                }
            ]
        }
    elif method == "tools/call":
        params = message.get("params", {})
        result = {
            "content": [{"type": "text", "text": json.dumps(params.get("arguments", {}), sort_keys=True)}],
            "structuredContent": {"env": os.environ.get("MCP_TEST_VALUE", "")},
            "isError": False,
        }
    else:
        continue
    print(json.dumps({"jsonrpc": "2.0", "id": message["id"], "result": result}), flush=True)
'''


class _Client:
    def __init__(self, responses: list[list[ContentBlock]]) -> None:
        self.responses = responses
        self.calls = 0

    def complete(self, messages: list[ChatMessage], tools=None, max_tokens=4096, temperature=0.2, timeout_ms=120_000):
        response = self.responses[self.calls]
        self.calls += 1
        return AssistantResponse(content=response, raw={"content": response})


def _write_mcp_project(root: Path, *, cwd: str = ".") -> None:
    (root / "mcp_server.py").write_text(MCP_SERVER_SOURCE, encoding="utf-8")
    (root / ".mcp.json").write_text(
        json.dumps(
            {
                "mcpServers": {
                    "test": {
                        "command": sys.executable,
                        "args": ["mcp_server.py"],
                        "cwd": cwd,
                        "env": {"MCP_TEST_VALUE": "${MCP_TEST_SOURCE}"},
                    }
                }
            }
        ),
        encoding="utf-8",
    )


def _write_mcp_config(path: Path, server_name: str, *, cwd: str = ".") -> None:
    path.write_text(
        json.dumps(
            {
                "mcpServers": {
                    server_name: {
                        "command": sys.executable,
                        "args": ["mcp_server.py"],
                        "cwd": cwd,
                    }
                }
            }
        ),
        encoding="utf-8",
    )


class McpRuntimeTests(unittest.TestCase):
    def test_lists_config_without_exposing_environment_values(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-mcp-") as base:
            root = Path(base)
            _write_mcp_project(root)
            workspace = create_run_workspace(root, "run-1")

            observation = execute_action(workspace, parse_tool_action("mcp_servers", {}))

        self.assertTrue(observation.ok)
        self.assertEqual(observation.servers[0].name, "test")
        self.assertEqual(observation.servers[0].arg_count, 1)
        self.assertEqual(observation.servers[0].env_keys, ["MCP_TEST_VALUE"])
        self.assertFalse(hasattr(observation.servers[0], "env"))
        self.assertFalse(hasattr(observation.servers[0], "args"))

    def test_workspace_can_merge_extra_mcp_config_paths(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-mcp-") as base:
            root = Path(base)
            _write_mcp_project(root)
            extra = root / "extra.mcp.json"
            _write_mcp_config(extra, "extra")
            workspace = create_run_workspace(root, "run-1", mcp_config_paths=(extra,))

            configs = read_mcp_server_configs(workspace)
            observation = execute_action(workspace, parse_tool_action("mcp_servers", {}))

        self.assertEqual([config.name for config in configs], ["extra", "test"])
        self.assertEqual([server.name for server in observation.servers], ["extra", "test"])
        self.assertIn(".mcp.json", observation.config_path)
        self.assertIn("extra.mcp.json", observation.config_path)

    def test_strict_workspace_uses_only_explicit_mcp_config_paths(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-mcp-") as base:
            root = Path(base)
            _write_mcp_project(root)
            extra = root / "extra.mcp.json"
            _write_mcp_config(extra, "extra")
            workspace = create_run_workspace(root, "run-1", mcp_config_paths=(extra,), strict_mcp_config=True)

            configs = read_mcp_server_configs(workspace)
            observation = execute_action(workspace, parse_tool_action("mcp_servers", {}))

        self.assertEqual([config.name for config in configs], ["extra"])
        self.assertEqual([server.name for server in observation.servers], ["extra"])
        self.assertEqual(observation.config_path, "extra.mcp.json")

    def test_strict_workspace_without_explicit_mcp_configs_reports_none(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-mcp-") as base:
            root = Path(base)
            _write_mcp_project(root)
            workspace = create_run_workspace(root, "run-1", strict_mcp_config=True)

            configs = read_mcp_server_configs(workspace)
            observation = execute_action(workspace, parse_tool_action("mcp_servers", {}))

        self.assertEqual(configs, [])
        self.assertEqual(observation.servers, [])
        self.assertEqual(observation.config_path, "none")

    def test_duplicate_extra_mcp_server_names_are_rejected(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-mcp-") as base:
            root = Path(base)
            (root / "mcp_server.py").write_text(MCP_SERVER_SOURCE, encoding="utf-8")
            _write_mcp_config(root / ".mcp.json", "test")
            extra = root / "extra.mcp.json"
            _write_mcp_config(extra, "test")
            workspace = create_run_workspace(root, "run-1", mcp_config_paths=(extra,))

            with self.assertRaisesRegex(ValueError, "defined in both"):
                read_mcp_server_configs(workspace)

    def test_explicit_project_mcp_config_path_is_deduplicated(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-mcp-") as base:
            root = Path(base)
            _write_mcp_project(root)
            workspace = create_run_workspace(root, "run-1", mcp_config_paths=(root / ".mcp.json",))

            configs = read_mcp_server_configs(workspace)

        self.assertEqual([config.name for config in configs], ["test"])

    def test_lists_and_calls_tools_over_real_stdio_protocol(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-mcp-") as base:
            root = Path(base)
            _write_mcp_project(root)
            workspace = create_run_workspace(root, "run-1")
            with patch.dict("os.environ", {"MCP_TEST_SOURCE": "expanded"}):
                listed = execute_action(
                    workspace,
                    McpToolsAction(type="mcp_tools", server="test", timeout_ms=2_000),
                )
                called = execute_action(
                    workspace,
                    McpCallAction(
                        type="mcp_call",
                        server="test",
                        name="echo",
                        arguments={"message": "hello"},
                        timeout_ms=2_000,
                        max_output_chars=1_000,
                    ),
                )

        self.assertTrue(listed.ok, listed.error)
        self.assertEqual(listed.tools[0].name, "echo")
        self.assertEqual(listed.tools[0].input_schema, {"type": "object"})
        self.assertTrue(called.ok, called.error)
        self.assertIn('"message": "hello"', called.output)
        self.assertIn('"env": "expanded"', called.output)

    def test_call_rejects_unadvertised_tool(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-mcp-") as base:
            root = Path(base)
            _write_mcp_project(root)
            workspace = create_run_workspace(root, "run-1")

            observation = execute_action(
                workspace,
                McpCallAction(type="mcp_call", server="test", name="missing", arguments={}, timeout_ms=2_000),
            )

        self.assertFalse(observation.ok)
        self.assertIn("was not advertised", observation.error or "")

    def test_request_timeout_stops_server_and_returns_bounded_failure(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-mcp-") as base:
            root = Path(base)
            (root / "hang.py").write_text("import time\ntime.sleep(10)\n", encoding="utf-8")
            (root / ".mcp.json").write_text(
                json.dumps({"mcpServers": {"hang": {"command": sys.executable, "args": ["hang.py"]}}}),
                encoding="utf-8",
            )
            workspace = create_run_workspace(root, "run-1")

            observation = execute_action(
                workspace,
                McpToolsAction(type="mcp_tools", server="hang", timeout_ms=100),
            )

        self.assertFalse(observation.ok)
        self.assertIn("timed out after 100 ms", observation.error or "")

    def test_config_rejects_escape_and_symlink(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-mcp-") as base:
            root = Path(base)
            _write_mcp_project(root, cwd="../outside")
            workspace = create_run_workspace(root, "run-1")
            with self.assertRaisesRegex(ValueError, "escapes the project directory"):
                read_mcp_server_configs(workspace)

        with tempfile.TemporaryDirectory(prefix="vibeagent-mcp-") as base:
            root = Path(base)
            target = root / "config.json"
            target.write_text('{"mcpServers": {}}', encoding="utf-8")
            (root / ".mcp.json").symlink_to(target)
            workspace = create_run_workspace(root, "run-1")
            with self.assertRaisesRegex(ValueError, "non-symlink"):
                read_mcp_server_configs(workspace)

    def test_mcp_process_actions_require_approval(self) -> None:
        tools_request = build_approval_request(McpToolsAction(type="mcp_tools", server="test"))
        call_request = build_approval_request(
            McpCallAction(type="mcp_call", server="test", name="echo", arguments={"secret": "value"})
        )

        self.assertEqual(tools_request.action_type, "mcp_tools")
        self.assertEqual(call_request.action_type, "mcp_call")
        self.assertIn("secret", call_request.target)
        self.assertNotIn("value", call_request.target)

    def test_agent_default_policy_denies_mcp_call_before_starting_server(self) -> None:
        client = _Client(
            [
                [{"type": "tool_call", "id": "mcp-1", "name": "mcp_call", "input": {"server": "test", "name": "echo", "arguments": {}}}],
                [{"type": "text", "text": "MCP call was denied."}],
            ]
        )
        with tempfile.TemporaryDirectory(prefix="vibeagent-mcp-") as base:
            root = Path(base)
            _write_mcp_project(root)
            result = run_agent("Call MCP", base_dir=root, client=client, max_iterations=2)

        self.assertEqual(result.observations[0].kind, "approval_denied")
        self.assertEqual(result.observations[0].action_type, "mcp_call")


class McpParsingTests(unittest.TestCase):
    def test_parses_bounded_actions(self) -> None:
        tools = parse_tool_action("mcp_tools", {"server": "docs", "max_tools": 5, "timeout_ms": 500})
        call = parse_tool_action("mcp_call", {"server": "docs", "name": "search", "arguments": {"q": "api"}})

        self.assertEqual(tools.server, "docs")
        self.assertEqual(tools.max_tools, 5)
        self.assertEqual(call.arguments, {"q": "api"})

    def test_key_redaction_hides_credentials_without_redacting_usage_counts(self) -> None:
        payload = redact_jsonable_payload(
            {
                "api_key": "private",
                "nested": {"access_token": "token-value", "accessToken": "camel-value"},
                "input_tokens": 12,
            }
        )

        self.assertEqual(payload["api_key"], "[REDACTED]")
        self.assertEqual(payload["nested"]["access_token"], "[REDACTED]")
        self.assertEqual(payload["nested"]["accessToken"], "[REDACTED]")
        self.assertEqual(payload["input_tokens"], 12)


if __name__ == "__main__":
    unittest.main()
