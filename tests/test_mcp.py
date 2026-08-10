import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from vibeagent.actions import execute_action, parse_tool_action
from vibeagent.agent import run_agent
from vibeagent.agent_approval import build_approval_request
from vibeagent.agent_delegate import execute_delegate_task_action
from vibeagent.mcp_config import read_mcp_server_configs
from vibeagent.mcp_protocol import McpToolsClient
from vibeagent.mcp_resource_runtime import (
    mcp_uri_matches_template,
    normalize_mcp_resource_template,
)
from vibeagent.redaction import redact_jsonable_payload
from vibeagent.types import (
    ApprovalDecision,
    AssistantResponse,
    ChatMessage,
    ContentBlock,
    McpCallAction,
    McpReadResourceAction,
    McpResourcesAction,
    McpToolsAction,
)
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
            "capabilities": {"tools": {}, "resources": {}},
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
    elif method == "resources/list":
        result = {
            "resources": [
                {
                    "uri": "docs://guide",
                    "name": "guide",
                    "title": "Project Guide",
                    "description": "Repository integration guide",
                    "mimeType": "text/markdown",
                    "size": 120,
                },
                {
                    "uri": "asset://logo",
                    "name": "logo",
                    "mimeType": "image/png",
                },
            ]
        }
    elif method == "resources/templates/list":
        if os.environ.get("MCP_TEST_NO_TEMPLATES") == "1":
            print(json.dumps({"jsonrpc": "2.0", "id": message["id"], "error": {"code": -32601, "message": "Method not found"}}), flush=True)
            continue
        result = {
            "resourceTemplates": [
                {
                    "uriTemplate": "docs://topics/{topic}",
                    "name": "topic",
                    "title": "Topic Guide",
                    "description": "Guide for one repository topic",
                    "mimeType": "text/markdown",
                }
            ]
        }
    elif method == "resources/read":
        uri = message.get("params", {}).get("uri")
        if uri == "docs://guide":
            contents = [{"uri": uri, "mimeType": "text/markdown", "text": "Use the documented API."}]
        elif uri.startswith("docs://topics/"):
            contents = [{"uri": uri, "mimeType": "text/markdown", "text": "Generated topic guide."}]
        else:
            contents = [{"uri": uri, "mimeType": "image/png", "blob": "aGVsbG8="}]
        result = {"contents": contents}
    else:
        continue
    print(json.dumps({"jsonrpc": "2.0", "id": message["id"], "result": result}), flush=True)
'''


class _Client:
    def __init__(self, responses: list[list[ContentBlock]]) -> None:
        self.responses = responses
        self.calls = 0
        self.tools: list[list[dict]] = []

    def complete(self, messages: list[ChatMessage], tools=None, max_tokens=4096, temperature=0.2, timeout_ms=120_000):
        self.tools.append(list(tools or []))
        response = self.responses[self.calls]
        self.calls += 1
        return AssistantResponse(content=response, raw={"content": response})


class _PagedResourceClient(McpToolsClient):
    def request(self, method, params):
        if method == "resources/list":
            if params.get("cursor") == "next":
                return {"resources": [{"uri": "docs://two"}]}
            return {"resources": [{"uri": "docs://one"}], "nextCursor": "next"}
        if method == "resources/templates/list":
            if params.get("cursor") == "template-next":
                return {"resourceTemplates": [{"uriTemplate": "docs://topic/{name}"}]}
            return {
                "resourceTemplates": [{"uriTemplate": "docs://issue/{id}"}],
                "nextCursor": "template-next",
            }
        raise AssertionError(method)


class _ConcreteOnlyResourceClient(McpToolsClient):
    def request(self, method, params):
        if method == "resources/list":
            return {"resources": [{"uri": "docs://one"}]}
        if method == "resources/templates/list":
            from vibeagent.mcp_protocol import McpProtocolError

            raise McpProtocolError("method not found", code=-32601)
        raise AssertionError(method)


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
                        "env": {"MCP_TEST_VALUE": "${MCP_TEST_SOURCE:-}"},
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


def _write_agent(root: Path, name: str, tools: str) -> None:
    path = root / ".claude" / "agents" / f"{name}.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        (
            f"---\nname: {name}\ndescription: Uses MCP tools\n"
            f"mode: code\ntools: {tools}\n---\n\nUse only the scoped MCP tool.\n"
        ),
        encoding="utf-8",
    )


class McpRuntimeTests(unittest.TestCase):
    def test_protocol_resource_listing_follows_cursor_and_applies_limit(self) -> None:
        resources, total, truncated = _PagedResourceClient().list_resources(1)
        templates, template_total, templates_truncated = (
            _PagedResourceClient().list_resource_templates(1)
        )

        self.assertEqual(resources, [{"uri": "docs://one"}])
        self.assertEqual(total, 2)
        self.assertTrue(truncated)
        self.assertEqual(templates, [{"uriTemplate": "docs://issue/{id}"}])
        self.assertEqual(template_total, 2)
        self.assertTrue(templates_truncated)

    def test_resource_template_listing_tolerates_method_not_found(self) -> None:
        templates, total, truncated = (
            _ConcreteOnlyResourceClient().list_resource_templates()
        )

        self.assertEqual(templates, [])
        self.assertEqual(total, 0)
        self.assertFalse(truncated)

    def test_resource_template_matching_validates_structure_and_expressions(self) -> None:
        template = normalize_mcp_resource_template(
            {
                "uriTemplate": "repo://issues/{id}{?view,locale}",
                "name": "issue",
            }
        )

        self.assertEqual(template.uri_template, "repo://issues/{id}{?view,locale}")
        self.assertTrue(
            mcp_uri_matches_template(
                "repo://issues/42?view=full&locale=en",
                template.uri_template,
            )
        )
        self.assertFalse(
            mcp_uri_matches_template(
                "repo://users/42?view=full",
                template.uri_template,
            )
        )
        self.assertFalse(
            mcp_uri_matches_template(
                "repo://issues/42?other=value",
                template.uri_template,
            )
        )
        with self.assertRaisesRegex(ValueError, "RFC 6570"):
            normalize_mcp_resource_template({"uriTemplate": "repo://issues/{bad!}"})

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
        self.assertEqual(called.arguments, {"message": "hello"})
        self.assertIn('"message": "hello"', called.output)
        self.assertIn('"env": "expanded"', called.output)
        self.assertEqual(called.text_output, '{"message": "hello"}')

    def test_lists_and_reads_resources_over_real_stdio_protocol(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-mcp-") as base:
            root = Path(base)
            _write_mcp_project(root)
            workspace = create_run_workspace(root, "run-1")
            listed = execute_action(
                workspace,
                McpResourcesAction(
                    type="mcp_resources",
                    server="test",
                    timeout_ms=2_000,
                ),
            )
            text = execute_action(
                workspace,
                McpReadResourceAction(
                    type="mcp_read_resource",
                    server="test",
                    uri="docs://guide",
                    timeout_ms=2_000,
                ),
            )
            binary = execute_action(
                workspace,
                McpReadResourceAction(
                    type="mcp_read_resource",
                    server="test",
                    uri="asset://logo",
                    timeout_ms=2_000,
                ),
            )
            templated = execute_action(
                workspace,
                McpReadResourceAction(
                    type="mcp_read_resource",
                    server="test",
                    uri="docs://topics/testing",
                    timeout_ms=2_000,
                ),
            )

        self.assertTrue(listed.ok, listed.error)
        self.assertEqual([item.uri for item in listed.resources], ["docs://guide", "asset://logo"])
        self.assertEqual(
            [item.uri_template for item in listed.templates],
            ["docs://topics/{topic}"],
        )
        self.assertEqual(listed.resource_total, 2)
        self.assertEqual(listed.template_total, 1)
        self.assertEqual(listed.resources[0].mime_type, "text/markdown")
        self.assertTrue(text.ok, text.error)
        self.assertIn("Use the documented API.", text.output)
        self.assertEqual(text.mime_types, ["text/markdown"])
        self.assertTrue(binary.ok, binary.error)
        self.assertIn("binary content omitted", binary.output)
        self.assertNotIn("aGVsbG8=", binary.output)
        self.assertTrue(templated.ok, templated.error)
        self.assertEqual(templated.template_uri, "docs://topics/{topic}")
        self.assertIn("Generated topic guide.", templated.output)

    def test_stdio_concrete_resources_survive_unsupported_templates_method(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-mcp-") as base:
            root = Path(base)
            _write_mcp_project(root)
            workspace = create_run_workspace(root, "run-1")
            with patch.dict("os.environ", {"MCP_TEST_NO_TEMPLATES": "1"}):
                listed = execute_action(
                    workspace,
                    McpResourcesAction(type="mcp_resources", server="test"),
                )

        self.assertTrue(listed.ok, listed.error)
        self.assertEqual([item.uri for item in listed.resources], ["docs://guide", "asset://logo"])
        self.assertEqual(listed.templates, [])
        self.assertEqual(listed.template_total, 0)

    def test_read_resource_rejects_uri_not_advertised_by_server(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-mcp-") as base:
            root = Path(base)
            _write_mcp_project(root)
            workspace = create_run_workspace(root, "run-1")
            observation = execute_action(
                workspace,
                McpReadResourceAction(
                    type="mcp_read_resource",
                    server="test",
                    uri="docs://missing",
                    timeout_ms=2_000,
                ),
            )

        self.assertFalse(observation.ok)
        self.assertIn("was not advertised", observation.error or "")

    def test_claude_resource_aliases_parse_and_require_approval(self) -> None:
        listed = parse_tool_action(
            "ListMcpResourcesTool",
            {"server": "test", "max_resources": 2, "max_templates": 3},
        )
        read = parse_tool_action(
            "ReadMcpResourceTool",
            {"server": "test", "uri": "docs://guide"},
        )

        self.assertIsInstance(listed, McpResourcesAction)
        self.assertEqual(listed.max_templates, 3)
        self.assertIsInstance(read, McpReadResourceAction)
        self.assertEqual(build_approval_request(listed).action_type, "mcp_resources")
        self.assertEqual(build_approval_request(read).action_type, "mcp_read_resource")

    def test_agent_discovers_lists_and_reads_mcp_resource(self) -> None:
        client = _Client(
            [
                [
                    {
                        "type": "tool_call",
                        "id": "search-1",
                        "name": "ToolSearch",
                        "input": {"query": "MCP resource", "max_results": 10},
                    }
                ],
                [
                    {
                        "type": "tool_call",
                        "id": "list-1",
                        "name": "ListMcpResourcesTool",
                        "input": {"server": "test"},
                    }
                ],
                [
                    {
                        "type": "tool_call",
                        "id": "read-1",
                        "name": "ReadMcpResourceTool",
                        "input": {"server": "test", "uri": "docs://topics/testing"},
                    }
                ],
                [{"type": "text", "text": "Used the MCP project guide."}],
            ]
        )
        approvals = []
        with tempfile.TemporaryDirectory(prefix="vibeagent-mcp-") as base:
            root = Path(base)
            _write_mcp_project(root)
            result = run_agent(
                "Read the MCP guide",
                base_dir=root,
                client=client,
                max_iterations=4,
                approval_policy="allow",
                approval_handler=lambda request: approvals.append(request.action_type)
                or ApprovalDecision(True, "approved"),
            )

        self.assertTrue(result.success, result.message)
        self.assertEqual(
            [item.kind for item in result.observations],
            ["tool_search", "mcp_resources", "mcp_read_resource"],
        )
        self.assertIn("ListMcpResourcesTool", {tool["name"] for tool in client.tools[1]})
        self.assertIn("ReadMcpResourceTool", {tool["name"] for tool in client.tools[2]})
        self.assertEqual(approvals, ["mcp_resources", "mcp_read_resource"])
        self.assertEqual(
            result.observations[-1].template_uri,
            "docs://topics/{topic}",
        )

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

    def test_agent_exposes_listed_mcp_tools_as_claude_style_dynamic_tools(self) -> None:
        client = _Client(
            [
                [
                    {
                        "type": "tool_call",
                        "id": "tools-1",
                        "name": "mcp_tools",
                        "input": {"server": "test", "timeout_ms": 2000},
                    }
                ],
                [
                    {
                        "type": "tool_call",
                        "id": "call-1",
                        "name": "mcp__test__echo",
                        "input": {"message": "hello"},
                    }
                ],
                [{"type": "text", "text": "MCP tool completed."}],
            ]
        )
        with tempfile.TemporaryDirectory(prefix="vibeagent-mcp-") as base:
            root = Path(base)
            _write_mcp_project(root)
            with patch.dict("os.environ", {"MCP_TEST_SOURCE": "expanded"}):
                result = run_agent(
                    "List then call MCP",
                    base_dir=root,
                    client=client,
                    max_iterations=3,
                    approval_handler=lambda request: ApprovalDecision(approved=True, message="approved"),
                )

        second_turn_names = {str(tool["name"]) for tool in client.tools[1]}
        self.assertIn("mcp__test__echo", second_turn_names)
        self.assertEqual([observation.kind for observation in result.observations], ["mcp_tools", "mcp_call"])
        self.assertTrue(result.observations[1].ok)
        self.assertEqual(result.observations[1].server, "test")
        self.assertEqual(result.observations[1].name, "echo")
        self.assertIn('"message": "hello"', result.observations[1].output)

    def test_claude_mcp_hook_matcher_runs_for_generic_mcp_call(self) -> None:
        hook_command = "python3 -c \"from pathlib import Path; Path('mcp-hook').write_text('ran')\""
        client = _Client(
            [
                [
                    {
                        "type": "tool_call",
                        "id": "call-1",
                        "name": "mcp_call",
                        "input": {"server": "test", "name": "echo", "arguments": {"message": "hooked"}, "timeout_ms": 2000},
                    }
                ],
                [{"type": "text", "text": "MCP call completed."}],
            ]
        )
        with tempfile.TemporaryDirectory(prefix="vibeagent-mcp-") as base:
            root = Path(base)
            _write_mcp_project(root)
            root.joinpath(".vibeagent").mkdir(exist_ok=True)
            root.joinpath(".vibeagent/hooks.json").write_text(
                json.dumps(
                    {
                        "PreToolUse": [
                            {
                                "matcher": "mcp__test__echo",
                                "hooks": [{"type": "command", "command": hook_command, "timeout_ms": 10_000}],
                            }
                        ]
                    }
                ),
                encoding="utf-8",
            )
            with patch.dict("os.environ", {"MCP_TEST_SOURCE": "expanded"}):
                result = run_agent(
                    "Call MCP through generic action",
                    base_dir=root,
                    client=client,
                    max_iterations=2,
                    approval_handler=lambda request: ApprovalDecision(approved=True, message="approved"),
                )

            hook_marker = root.joinpath("mcp-hook").read_text(encoding="utf-8")

        self.assertTrue(result.success)
        self.assertEqual(hook_marker, "ran")
        self.assertEqual([observation.kind for observation in result.observations], ["mcp_call"])

    def test_code_subagent_exposes_listed_mcp_tools_as_dynamic_tools(self) -> None:
        client = _Client(
            [
                [
                    {
                        "type": "tool_call",
                        "id": "tools-1",
                        "name": "mcp_tools",
                        "input": {"server": "test", "timeout_ms": 2000},
                    }
                ],
                [
                    {
                        "type": "tool_call",
                        "id": "call-1",
                        "name": "mcp__test__echo",
                        "input": {"message": "from subagent"},
                    }
                ],
                [{"type": "text", "text": "Subagent MCP call completed."}],
            ]
        )
        with tempfile.TemporaryDirectory(prefix="vibeagent-mcp-") as base:
            root = Path(base)
            _write_mcp_project(root)
            workspace = create_run_workspace(root, "run-1")
            action = parse_tool_action(
                "delegate_task",
                {"task": "List and call MCP", "mode": "code", "max_iterations": 3},
            )
            with patch.dict("os.environ", {"MCP_TEST_SOURCE": "expanded"}):
                observation = execute_delegate_task_action(
                    workspace,
                    action,
                    client,
                    parent_iteration=1,
                    subagent_id="delegate-1-1",
                    max_output_tokens=2048,
                    model_retries=0,
                    model_retry_delay_ms=0,
                    model_timeout_ms=10_000,
                    command_timeout_ms=10_000,
                    logger=None,
                    approval_handler=lambda request: ApprovalDecision(approved=True, message="approved"),
                )

        second_turn_names = {str(tool["name"]) for tool in client.tools[1]}
        self.assertIn("mcp__test__echo", second_turn_names)
        self.assertTrue(observation.ok)
        self.assertEqual(observation.tool_calls, ["mcp_tools", "mcp__test__echo"])

    def test_code_profile_can_scope_subagent_to_specific_mcp_alias(self) -> None:
        client = _Client(
            [
                [
                    {
                        "type": "tool_call",
                        "id": "tools-1",
                        "name": "mcp_tools",
                        "input": {"server": "test", "timeout_ms": 2000},
                    }
                ],
                [
                    {
                        "type": "tool_call",
                        "id": "call-1",
                        "name": "mcp__test__echo",
                        "input": {"message": "profile scoped"},
                    }
                ],
                [{"type": "text", "text": "Profile-scoped MCP call completed."}],
            ]
        )
        with tempfile.TemporaryDirectory(prefix="vibeagent-mcp-") as base:
            root = Path(base)
            _write_mcp_project(root)
            _write_agent(root, "mcp-runner", "mcp__test__echo")
            workspace = create_run_workspace(root, "run-1")
            action = parse_tool_action(
                "delegate_task",
                {"task": "Use scoped MCP", "agent": "mcp-runner", "max_iterations": 3},
            )
            with patch.dict("os.environ", {"MCP_TEST_SOURCE": "expanded"}):
                observation = execute_delegate_task_action(
                    workspace,
                    action,
                    client,
                    parent_iteration=1,
                    subagent_id="delegate-1-1",
                    max_output_tokens=2048,
                    model_retries=0,
                    model_retry_delay_ms=0,
                    model_timeout_ms=10_000,
                    command_timeout_ms=10_000,
                    logger=None,
                    approval_handler=lambda request: ApprovalDecision(approved=True, message="approved"),
                )

        first_turn_names = {str(tool["name"]) for tool in client.tools[0]}
        self.assertEqual(first_turn_names, {"finish", "mcp_tools"})
        self.assertIn("mcp__test__echo", {str(tool["name"]) for tool in client.tools[1]})
        self.assertTrue(observation.ok)
        self.assertEqual(observation.tool_calls, ["mcp_tools", "mcp__test__echo"])


class McpParsingTests(unittest.TestCase):
    def test_parses_bounded_actions(self) -> None:
        tools = parse_tool_action("mcp_tools", {"server": "docs", "max_tools": 5, "timeout_ms": 500})
        call = parse_tool_action("mcp_call", {"server": "docs", "name": "search", "arguments": {"q": "api"}})
        alias_call = parse_tool_action("mcp__docs__search", {"q": "api"})

        self.assertEqual(tools.server, "docs")
        self.assertEqual(tools.max_tools, 5)
        self.assertEqual(call.arguments, {"q": "api"})
        self.assertEqual(alias_call.type, "mcp_call")
        self.assertEqual(alias_call.server, "docs")
        self.assertEqual(alias_call.name, "search")
        self.assertEqual(alias_call.arguments, {"q": "api"})

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
