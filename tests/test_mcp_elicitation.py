from __future__ import annotations

from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
import sys
import tempfile
from threading import Event, Thread
import unittest

from vibeagent.actions import execute_action
from vibeagent.agent import run_agent
from vibeagent.agent_execution_support import execute_action_safely
from vibeagent.mcp_elicitation import McpElicitationRuntime
from vibeagent.mcp_elicitation_context import mcp_elicitation_handler
from vibeagent.types import (
    ApprovalDecision,
    AssistantResponse,
    ChatMessage,
    ContentBlock,
    McpCallAction,
)
from vibeagent.workspace import create_run_workspace
from vibeagent.workspace_hooks import ProjectHooks, read_project_hooks
from vibeagent.workspace_permissions import ProjectPermissions


STDIO_SERVER = r'''
import json
import sys

capabilities = {}
for raw in sys.stdin:
    message = json.loads(raw)
    method = message.get("method")
    if method == "initialize":
        capabilities = message.get("params", {}).get("capabilities", {})
        result = {
            "protocolVersion": "2025-11-25",
            "capabilities": {"tools": {}},
            "serverInfo": {"name": "elicit-server", "version": "1"},
        }
    elif method == "tools/list":
        result = {"tools": [{"name": "collect", "inputSchema": {"type": "object"}}]}
    elif method == "tools/call":
        print(json.dumps({
            "jsonrpc": "2.0",
            "id": "elicit-1",
            "method": "elicitation/create",
            "params": {
                "mode": "form",
                "message": "Choose a project name",
                "requestedSchema": {
                    "type": "object",
                    "properties": {"project": {"type": "string", "title": "Project"}},
                    "required": ["project"],
                },
            },
        }), flush=True)
        response = json.loads(next(sys.stdin))
        result = {
            "content": [{"type": "text", "text": json.dumps({
                "elicitation": response.get("result"),
                "capabilities": capabilities,
            }, sort_keys=True)}],
            "isError": False,
        }
    else:
        continue
    print(json.dumps({"jsonrpc": "2.0", "id": message["id"], "result": result}), flush=True)
'''


class _Client:
    def __init__(self, responses: list[list[ContentBlock]]) -> None:
        self.responses = responses
        self.index = 0

    def complete(
        self,
        messages: list[ChatMessage],
        tools=None,
        max_tokens=4096,
        temperature=0.2,
        timeout_ms=120_000,
    ) -> AssistantResponse:
        content = self.responses[self.index]
        self.index += 1
        return AssistantResponse(content=content, raw={"content": content})


def _write_stdio_project(root: Path) -> None:
    (root / "server.py").write_text(STDIO_SERVER, encoding="utf-8")
    (root / ".mcp.json").write_text(
        json.dumps(
            {
                "mcpServers": {
                    "elicit": {
                        "command": sys.executable,
                        "args": ["server.py"],
                    }
                }
            }
        ),
        encoding="utf-8",
    )


def _approve(_request) -> ApprovalDecision:
    return ApprovalDecision(True, "approved")


class McpElicitationRuntimeTests(unittest.TestCase):
    def test_agent_collects_form_values_and_stdio_declares_capability(self) -> None:
        client = _Client(
            [
                [
                    {
                        "type": "tool_call",
                        "id": "call-1",
                        "name": "mcp_call",
                        "input": {
                            "server": "elicit",
                            "name": "collect",
                            "arguments": {},
                            "timeout_ms": 3000,
                        },
                    }
                ],
                [{"type": "text", "text": "done"}],
            ]
        )
        answers = iter(["Accept", "vibeagent"])
        with tempfile.TemporaryDirectory(prefix="vibeagent-elicit-") as base:
            root = Path(base)
            _write_stdio_project(root)
            result = run_agent(
                "collect project name",
                base_dir=root,
                client=client,
                max_iterations=2,
                approval_handler=_approve,
                user_input_handler=lambda _request: next(answers),
            )
            events = (root / ".vibeagent/sessions" / result.run_id / "events.jsonl").read_text(
                encoding="utf-8"
            )

        self.assertTrue(result.success, result.message)
        output = json.loads(result.observations[0].text_output)
        self.assertEqual(
            output["elicitation"],
            {"action": "accept", "content": {"project": "vibeagent"}},
        )
        self.assertEqual(
            output["capabilities"],
            {"elicitation": {"form": {}, "url": {}}},
        )
        event_rows = [json.loads(line) for line in events.splitlines()]
        elicitation_events = [
            row for row in event_rows if str(row.get("type", "")).startswith("mcp_elicitation_")
        ]
        self.assertEqual(
            [row["type"] for row in elicitation_events],
            ["mcp_elicitation_requested", "mcp_elicitation_response"],
        )
        self.assertNotIn("vibeagent", json.dumps(elicitation_events))
        self.assertNotIn("Choose a project name", json.dumps(elicitation_events))

    def test_hook_can_answer_and_result_hook_can_override(self) -> None:
        hook_script = """import json, sys
from pathlib import Path
d = json.load(sys.stdin)
with Path('hook-inputs.jsonl').open('a', encoding='utf-8') as handle:
    handle.write(json.dumps(d) + '\\n')
if d['hook_event_name'] == 'Elicitation':
    print(json.dumps({'hookSpecificOutput': {
        'hookEventName': 'Elicitation', 'action': 'accept', 'content': {'name': 'hook'}
    }}))
else:
    print(json.dumps({'hookSpecificOutput': {
        'hookEventName': 'ElicitationResult', 'action': 'decline', 'content': {}
    }}))
"""
        with tempfile.TemporaryDirectory(prefix="vibeagent-elicit-") as base:
            root = Path(base)
            (root / "hook.py").write_text(hook_script, encoding="utf-8")
            config = root / ".vibeagent/hooks.json"
            config.parent.mkdir()
            config.write_text(
                json.dumps(
                    {
                        event: [
                            {
                                "matcher": "server",
                                "hooks": [
                                    {"type": "command", "command": "python3 hook.py"}
                                ],
                            }
                        ]
                        for event in ("Elicitation", "ElicitationResult")
                    }
                ),
                encoding="utf-8",
            )
            workspace = create_run_workspace(root, "run-1")
            runtime = self._runtime(workspace, read_project_hooks(workspace), None)
            response = runtime.handle(
                "server",
                {
                    "message": "Name",
                    "requestedSchema": {
                        "type": "object",
                        "properties": {"name": {"type": "string"}},
                        "required": ["name"],
                    },
                },
            )
            inputs = [
                json.loads(line)
                for line in (root / "hook-inputs.jsonl").read_text(encoding="utf-8").splitlines()
            ]

        self.assertEqual(response, {"action": "decline"})
        self.assertEqual([item["hook_event_name"] for item in inputs], ["Elicitation", "ElicitationResult"])
        self.assertEqual(inputs[0]["mcp_server_name"], "server")
        self.assertEqual(inputs[0]["requested_schema"]["required"], ["name"])
        self.assertEqual(inputs[1]["action"], "accept")
        self.assertEqual(inputs[1]["content"], {"name": "hook"})

    def test_sensitive_form_and_unsafe_url_are_declined_without_prompt(self) -> None:
        requests = []
        with tempfile.TemporaryDirectory(prefix="vibeagent-elicit-") as base:
            workspace = create_run_workspace(Path(base), "run-1")
            runtime = self._runtime(
                workspace,
                ProjectHooks(),
                lambda request: requests.append(request) or "Accept",
            )
            sensitive = runtime.handle(
                "server",
                {
                    "message": "Token",
                    "requestedSchema": {
                        "type": "object",
                        "properties": {"api_key": {"type": "string"}},
                    },
                },
            )
            unsafe_url = runtime.handle(
                "server",
                {
                    "mode": "url",
                    "message": "Login",
                    "url": "http://user:pass@example.com",
                    "elicitationId": "id-1",
                },
            )

        self.assertEqual(sensitive, {"action": "decline"})
        self.assertEqual(unsafe_url, {"action": "decline"})
        self.assertEqual(requests, [])

    def test_result_hook_exit_two_declines_accepted_response(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-elicit-") as base:
            root = Path(base)
            config = root / ".vibeagent/hooks.json"
            config.parent.mkdir()
            config.write_text(
                json.dumps(
                    {
                        "ElicitationResult": [
                            {
                                "matcher": "server",
                                "hooks": [
                                    {
                                        "type": "command",
                                        "command": "python3 -c 'import sys; sys.exit(2)'",
                                    }
                                ],
                            }
                        ]
                    }
                ),
                encoding="utf-8",
            )
            workspace = create_run_workspace(root, "run-1")
            answers = iter(["Accept", "value"])
            runtime = self._runtime(
                workspace,
                read_project_hooks(workspace),
                lambda _request: next(answers),
            )
            response = runtime.handle(
                "server",
                {
                    "message": "Name",
                    "requestedSchema": {
                        "type": "object",
                        "properties": {"name": {"type": "string"}},
                        "required": ["name"],
                    },
                },
            )

        self.assertEqual(response, {"action": "decline"})

    def test_model_hook_handlers_are_rejected_for_elicitation_events(self) -> None:
        for event in ("Elicitation", "ElicitationResult"):
            for handler_type in ("prompt", "agent"):
                with self.subTest(event=event, handler_type=handler_type), tempfile.TemporaryDirectory(
                    prefix="vibeagent-elicit-"
                ) as base:
                    root = Path(base)
                    config = root / ".vibeagent/hooks.json"
                    config.parent.mkdir()
                    config.write_text(
                        json.dumps(
                            {
                                event: [
                                    {
                                        "matcher": ".*",
                                        "hooks": [
                                            {"type": handler_type, "prompt": "decide"}
                                        ],
                                    }
                                ]
                            }
                        ),
                        encoding="utf-8",
                    )
                    hooks = read_project_hooks(create_run_workspace(root))

                self.assertIsNotNone(hooks.error)

    @staticmethod
    def _runtime(workspace, hooks, user_input_handler):
        return McpElicitationRuntime(
            workspace=workspace,
            hooks=hooks,
            permissions=ProjectPermissions(),
            command_timeout_ms=10_000,
            logger=None,
            approval_handler=_approve,
            approval_policy="ask",
            user_input_handler=user_input_handler,
            execute_action_safely=execute_action_safely,
        )


class _ElicitationHttpServer:
    def __init__(self) -> None:
        self.response_event = Event()
        self.elicitation_response: dict[str, object] | None = None
        self.client_capabilities: dict[str, object] | None = None
        owner = self

        class Handler(BaseHTTPRequestHandler):
            def do_POST(self):
                length = int(self.headers.get("Content-Length", "0"))
                message = json.loads(self.rfile.read(length))
                if "method" not in message:
                    owner.elicitation_response = message.get("result")
                    owner.response_event.set()
                    self.send_response(202)
                    self.end_headers()
                    return
                method = message["method"]
                metadata = message.get("params", {}).get("_meta", {})
                owner.client_capabilities = metadata.get(
                    "io.modelcontextprotocol/clientCapabilities"
                )
                if method == "tools/list":
                    self._json(
                        {
                            "jsonrpc": "2.0",
                            "id": message["id"],
                            "result": {
                                "tools": [
                                    {"name": "collect", "inputSchema": {"type": "object"}}
                                ]
                            },
                        }
                    )
                    return
                if method == "tools/call":
                    self.send_response(200)
                    self.send_header("Content-Type", "text/event-stream")
                    self.end_headers()
                    request = {
                        "jsonrpc": "2.0",
                        "id": "http-elicit",
                        "method": "elicitation/create",
                        "params": {
                            "message": "Select branch",
                            "requestedSchema": {
                                "type": "object",
                                "properties": {"branch": {"type": "string"}},
                                "required": ["branch"],
                            },
                        },
                    }
                    self.wfile.write(f"data: {json.dumps(request)}\n\n".encode())
                    self.wfile.flush()
                    if not owner.response_event.wait(3):
                        return
                    result = {
                        "jsonrpc": "2.0",
                        "id": message["id"],
                        "result": {
                            "content": [
                                {
                                    "type": "text",
                                    "text": json.dumps(owner.elicitation_response),
                                }
                            ]
                        },
                    }
                    self.wfile.write(f"data: {json.dumps(result)}\n\n".encode())
                    self.wfile.flush()
                    return
                self.send_response(202)
                self.end_headers()

            def _json(self, payload):
                encoded = json.dumps(payload).encode()
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(encoded)))
                self.end_headers()
                self.wfile.write(encoded)

            def log_message(self, _format, *args):
                return

        self.server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        self.thread = Thread(target=self.server.serve_forever, daemon=True)

    @property
    def url(self) -> str:
        return f"http://127.0.0.1:{self.server.server_port}/mcp"

    def __enter__(self):
        self.thread.start()
        return self

    def __exit__(self, exc_type, exc, traceback):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=2)


class McpHttpElicitationTests(unittest.TestCase):
    def test_streamable_http_answers_server_request_before_final_response(self) -> None:
        with _ElicitationHttpServer() as server, tempfile.TemporaryDirectory(
            prefix="vibeagent-elicit-http-"
        ) as base:
            root = Path(base)
            (root / ".mcp.json").write_text(
                json.dumps(
                    {
                        "mcpServers": {
                            "remote": {
                                "type": "http",
                                "url": server.url,
                                "protocolVersion": "2026-07-28",
                            }
                        }
                    }
                ),
                encoding="utf-8",
            )
            workspace = create_run_workspace(root, "run-1")
            with mcp_elicitation_handler(
                lambda name, params: {
                    "action": "accept",
                    "content": {"branch": "main"},
                }
            ):
                observation = execute_action(
                    workspace,
                    McpCallAction(
                        type="mcp_call",
                        server="remote",
                        name="collect",
                        arguments={},
                        timeout_ms=5_000,
                    ),
                )

        self.assertTrue(observation.ok, observation.error)
        self.assertEqual(
            server.elicitation_response,
            {"action": "accept", "content": {"branch": "main"}},
        )
        self.assertEqual(
            server.client_capabilities,
            {"elicitation": {"form": {}, "url": {}}},
        )
        self.assertIn('"branch": "main"', observation.output)


if __name__ == "__main__":
    unittest.main()
