from __future__ import annotations

import json
import os
import tempfile
import threading
import unittest
import urllib.error
from contextlib import contextmanager
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Iterator
from unittest.mock import patch

from tests.test_agent_hooks import HookClient
from vibeagent.agent import run_agent
from vibeagent.agent_hook_http import run_project_http_hook
from vibeagent.session_timeline_reports import format_session_event_timeline_item
from vibeagent.session_types import SessionEvent
from vibeagent.types import ApprovalDecision
from vibeagent.workspace import create_run_workspace
from vibeagent.workspace_hooks import read_project_hooks
from vibeagent.workspace_permissions import ProjectPermissions


def _approve(_request) -> ApprovalDecision:
    return ApprovalDecision(approved=True, message="approved")


def _write_http_hook(
    root: Path,
    url: str,
    *,
    event: str = "PreToolUse",
    matcher: str = "write_file",
    headers: dict[str, str] | None = None,
    allowed_env_vars: list[str] | None = None,
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
                                "type": "http",
                                "url": url,
                                "headers": headers or {},
                                "allowedEnvVars": allowed_env_vars or [],
                                "timeout": 2,
                            }
                        ],
                    }
                ]
            }
        ),
        encoding="utf-8",
    )


@contextmanager
def _hook_server(
    *,
    status: int = 200,
    response: str = "",
) -> Iterator[tuple[str, list[dict[str, object]]]]:
    requests: list[dict[str, object]] = []

    class Handler(BaseHTTPRequestHandler):
        def do_POST(self) -> None:  # noqa: N802
            body = self.rfile.read(int(self.headers.get("Content-Length", "0")))
            requests.append(
                {
                    "path": self.path,
                    "headers": {name.lower(): value for name, value in self.headers.items()},
                    "body": json.loads(body.decode("utf-8")),
                }
            )
            encoded = response.encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(encoded)))
            self.end_headers()
            self.wfile.write(encoded)

        def log_message(self, _format: str, *args: object) -> None:
            return

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        host, port = server.server_address
        yield f"http://{host}:{port}/hook", requests
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)


class HttpHookConfigTests(unittest.TestCase):
    def test_loads_http_handler_fields_and_timeout(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-http-hook-") as base:
            root = Path(base)
            _write_http_hook(
                root,
                "http://127.0.0.1:8123/check",
                headers={"Authorization": "Bearer $HOOK_TOKEN"},
                allowed_env_vars=["HOOK_TOKEN"],
            )
            config = read_project_hooks(create_run_workspace(root))

        self.assertIsNone(config.error)
        self.assertEqual(len(config.hooks), 1)
        hook = config.hooks[0]
        self.assertEqual(hook.handler_type, "http")
        self.assertEqual(hook.url, "http://127.0.0.1:8123/check")
        self.assertEqual(hook.headers, (("Authorization", "Bearer $HOOK_TOKEN"),))
        self.assertEqual(hook.allowed_env_vars, ("HOOK_TOKEN",))
        self.assertEqual(hook.timeout_ms, 2_000)

    def test_rejects_unsafe_or_malformed_http_handler_fields(self) -> None:
        invalid_handlers = [
            {"type": "http", "url": "ftp://example.com/hook"},
            {"type": "http", "url": "http://user:pass@example.com/hook"},
            {"type": "http", "url": "http://example.com", "headers": {"Host": "other"}},
            {"type": "http", "url": "http://example.com", "headers": {"Content-Type": "text/plain"}},
            {"type": "http", "url": "http://example.com", "headers": {"X-Test": "a\nb"}},
            {"type": "http", "url": "http://example.com", "allowedEnvVars": ["BAD-NAME"]},
            {"type": "http", "url": "http://example.com", "async": True},
        ]
        for index, handler in enumerate(invalid_handlers):
            with self.subTest(index=index), tempfile.TemporaryDirectory(
                prefix="vibeagent-http-hook-"
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


class HttpHookIntegrationTests(unittest.TestCase):
    def test_session_timeline_includes_http_handler_and_status(self) -> None:
        event = SessionEvent(
            line_number=1,
            type="hook_completed",
            payload={
                "event": "PreToolUse",
                "tool": "Write",
                "source": ".vibeagent/hooks.json",
                "handler_type": "http",
                "result": {
                    "status": "failed",
                    "http_status": 503,
                    "message": "non-blocking",
                },
            },
        )

        text = format_session_event_timeline_item(event)

        self.assertIn("handler=http", text)
        self.assertIn("httpStatus=503", text)

    def test_expanded_header_injection_is_rejected_without_connecting(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-http-hook-") as base:
            root = Path(base)
            _write_http_hook(
                root,
                "http://127.0.0.1:8123/hook",
                headers={"X-Value": "$HOOK_VALUE"},
                allowed_env_vars=["HOOK_VALUE"],
            )
            workspace = create_run_workspace(root)
            hook = read_project_hooks(workspace).hooks[0]
            with patch(
                "vibeagent.agent_hook_http.open_local_or_public_url"
            ) as open_url:
                result = run_project_http_hook(
                    workspace,
                    hook,
                    target="Write",
                    hook_input={"hook_event_name": "PreToolUse"},
                    environment={"HOOK_VALUE": "unsafe\r\nInjected: yes"},
                    iteration=1,
                    hook_index=1,
                    logger=None,
                    approval_handler=_approve,
                    approval_policy="ask",
                    permissions=ProjectPermissions(),
                )

        open_url.assert_not_called()
        self.assertFalse(result.ok)
        self.assertTrue(result.non_blocking_error)
        self.assertIn("invalid after environment expansion", result.message)

    def test_oversized_hook_input_is_rejected_without_connecting(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-http-hook-") as base:
            root = Path(base)
            _write_http_hook(root, "http://127.0.0.1:8123/hook")
            workspace = create_run_workspace(root)
            hook = read_project_hooks(workspace).hooks[0]
            with patch(
                "vibeagent.agent_hook_http.open_local_or_public_url"
            ) as open_url:
                result = run_project_http_hook(
                    workspace,
                    hook,
                    target="Write",
                    hook_input={"payload": "x" * 1_048_577},
                    environment=None,
                    iteration=1,
                    hook_index=1,
                    logger=None,
                    approval_handler=_approve,
                    approval_policy="ask",
                    permissions=ProjectPermissions(),
                )

        open_url.assert_not_called()
        self.assertFalse(result.ok)
        self.assertTrue(result.non_blocking_error)
        self.assertIn("input exceeds", result.message)

    def test_connection_failure_is_redacted_and_non_blocking(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-http-hook-") as base:
            root = Path(base)
            _write_http_hook(root, "http://127.0.0.1:8123/hook")
            workspace = create_run_workspace(root)
            hook = read_project_hooks(workspace).hooks[0]
            with patch(
                "vibeagent.agent_hook_http.open_local_or_public_url",
                side_effect=urllib.error.URLError(
                    "connection failed token=super-secret-token"
                ),
            ):
                result = run_project_http_hook(
                    workspace,
                    hook,
                    target="Write",
                    hook_input={"hook_event_name": "PreToolUse"},
                    environment=None,
                    iteration=1,
                    hook_index=1,
                    logger=None,
                    approval_handler=_approve,
                    approval_policy="ask",
                    permissions=ProjectPermissions(),
                )

        self.assertFalse(result.ok)
        self.assertTrue(result.non_blocking_error)
        self.assertNotIn("super-secret-token", result.message)
        self.assertIn("[REDACTED]", result.message)

    def test_pre_tool_http_hook_receives_input_and_denies_write(self) -> None:
        response = json.dumps(
            {
                "hookSpecificOutput": {
                    "hookEventName": "PreToolUse",
                    "permissionDecision": "deny",
                    "permissionDecisionReason": "Remote policy denied this write.",
                }
            }
        )
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
                [{"type": "text", "text": "The remote policy denied the write."}],
            ]
        )
        with _hook_server(response=response) as (url, requests), tempfile.TemporaryDirectory(
            prefix="vibeagent-http-hook-"
        ) as base:
            root = Path(base)
            _write_http_hook(
                root,
                url,
                headers={
                    "Authorization": "Bearer $HOOK_TOKEN",
                    "X-Unlisted": "$UNLISTED_TOKEN",
                },
                allowed_env_vars=["HOOK_TOKEN"],
            )
            original = os.environ.get("HOOK_TOKEN")
            os.environ["HOOK_TOKEN"] = "test-hook-token"
            try:
                result = run_agent(
                    "Write app.py",
                    base_dir=root,
                    client=client,
                    max_iterations=2,
                    approval_handler=_approve,
                )
            finally:
                if original is None:
                    os.environ.pop("HOOK_TOKEN", None)
                else:
                    os.environ["HOOK_TOKEN"] = original

            self.assertFalse((root / "app.py").exists())

        self.assertTrue(result.success)
        self.assertEqual(len(requests), 1)
        request = requests[0]
        self.assertEqual(request["path"], "/hook")
        self.assertEqual(request["headers"]["authorization"], "Bearer test-hook-token")  # type: ignore[index]
        self.assertEqual(request["headers"]["x-unlisted"], "")  # type: ignore[index]
        self.assertEqual(request["headers"]["content-type"], "application/json")  # type: ignore[index]
        self.assertEqual(request["body"]["hook_event_name"], "PreToolUse")  # type: ignore[index]
        self.assertEqual(request["body"]["tool_input"]["path"], "app.py")  # type: ignore[index]
        self.assertIn("Remote policy denied this write.", str(client.messages[1][-1].content))

    def test_non_success_http_status_is_non_blocking(self) -> None:
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
                [{"type": "text", "text": "Created app.py despite hook outage."}],
            ]
        )
        with _hook_server(status=503, response="unavailable") as (url, _), tempfile.TemporaryDirectory(
            prefix="vibeagent-http-hook-"
        ) as base:
            root = Path(base)
            _write_http_hook(root, url)
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
            and event["result"].get("handler_type") == "http"
        )
        self.assertEqual(completed["result"]["http_status"], 503)
        self.assertTrue(completed["result"]["non_blocking_error"])

    def test_lifecycle_http_plain_text_adds_model_context(self) -> None:
        client = HookClient(
            [[{"type": "text", "text": "Used remote startup context."}]]
        )
        with _hook_server(response="remote startup context") as (url, requests), tempfile.TemporaryDirectory(
            prefix="vibeagent-http-hook-"
        ) as base:
            root = Path(base)
            _write_http_hook(
                root,
                url,
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
        self.assertEqual(len(requests), 1)
        initial_user = client.messages[0][1].content
        self.assertIsInstance(initial_user, str)
        self.assertIn("SessionStart hook context:\nremote startup context", initial_user)


if __name__ == "__main__":
    unittest.main()
