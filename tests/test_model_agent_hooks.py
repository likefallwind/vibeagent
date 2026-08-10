from __future__ import annotations

import json
from pathlib import Path
import tempfile
import unittest

from vibeagent.agent import run_agent
from vibeagent.agent_runtime_utils import append_session_event
from vibeagent.session import summarize_session
from vibeagent.types import ApprovalDecision, AssistantResponse, ChatMessage, ContentBlock
from vibeagent.workspace import create_run_workspace
from vibeagent.workspace_hooks import read_project_hooks


class AgentHookClient:
    def __init__(
        self,
        responses: list[list[ContentBlock] | BaseException],
        *,
        model: str = "main-model",
        messages: list[list[ChatMessage]] | None = None,
        tools: list[object] | None = None,
        timeouts: list[int] | None = None,
        configured_models: list[str] | None = None,
    ) -> None:
        self.responses = responses
        self.model = model
        self.messages = messages if messages is not None else []
        self.tools = tools if tools is not None else []
        self.timeouts = timeouts if timeouts is not None else []
        self.configured_models = (
            configured_models if configured_models is not None else []
        )

    def complete(
        self,
        messages,
        tools=None,
        max_tokens=4096,
        temperature=0.2,
        timeout_ms=120_000,
    ):
        self.messages.append(list(messages))
        self.tools.append(tools)
        self.timeouts.append(timeout_ms)
        response = self.responses.pop(0)
        if isinstance(response, BaseException):
            raise response
        return AssistantResponse(content=response, raw={"content": response})

    def with_agent_profile(self, *, model: str | None, effort: str | None):
        assert effort is None
        selected = model or self.model
        self.configured_models.append(selected)
        return AgentHookClient(
            self.responses,
            model=selected,
            messages=self.messages,
            tools=self.tools,
            timeouts=self.timeouts,
            configured_models=self.configured_models,
        )


def _write_agent_hook(
    root: Path,
    *,
    event: str = "PreToolUse",
    matcher: str = "write_file",
    prompt: str = "Inspect the repository before deciding: $ARGUMENTS",
    model: str | None = None,
    timeout: float | None = None,
    continue_on_block: bool = False,
) -> None:
    handler: dict[str, object] = {
        "type": "agent",
        "prompt": prompt,
        "continueOnBlock": continue_on_block,
    }
    if model is not None:
        handler["model"] = model
    if timeout is not None:
        handler["timeout"] = timeout
    path = root / ".vibeagent/hooks.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(
            {event: [{"matcher": matcher, "hooks": [handler]}]}
        ),
        encoding="utf-8",
    )


def _approve(_request) -> ApprovalDecision:
    return ApprovalDecision(approved=True, message="approved")


class AgentHookConfigTests(unittest.TestCase):
    def test_loads_agent_fields_with_sixty_second_default_timeout(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-agent-hook-") as base:
            root = Path(base)
            _write_agent_hook(
                root,
                event="Stop",
                matcher=".*",
                model="fast-model",
                continue_on_block=True,
            )
            config = read_project_hooks(create_run_workspace(root))

        self.assertIsNone(config.error)
        hook = config.hooks[0]
        self.assertEqual(hook.handler_type, "agent")
        self.assertEqual(hook.timeout_ms, 60_000)
        self.assertEqual(hook.model, "fast-model")
        self.assertTrue(hook.continue_on_block)

    def test_rejects_agent_on_unsupported_event_and_async(self) -> None:
        invalid = [
            ("SessionStart", {"type": "agent", "prompt": "verify"}),
            (
                "PreToolUse",
                {"type": "agent", "prompt": "verify", "async": True},
            ),
        ]
        for event, handler in invalid:
            with self.subTest(event=event), tempfile.TemporaryDirectory(
                prefix="vibeagent-agent-hook-"
            ) as base:
                root = Path(base)
                path = root / ".vibeagent/hooks.json"
                path.parent.mkdir(parents=True)
                path.write_text(
                    json.dumps(
                        {event: [{"matcher": ".*", "hooks": [handler]}]}
                    ),
                    encoding="utf-8",
                )
                config = read_project_hooks(create_run_workspace(root))
            self.assertIsNotNone(config.error)

    def test_hook_agent_usage_is_included_in_session_totals(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-agent-hook-") as base:
            root = Path(base)
            workspace = create_run_workspace(root, run_id="agent-hook-usage")
            append_session_event(
                workspace.session_dir,
                "hook_agent_model",
                {
                    "usage": {
                        "input_tokens": 20,
                        "output_tokens": 5,
                        "total_tokens": 25,
                    }
                },
            )
            summary = summarize_session(root, "agent-hook-usage")

        self.assertEqual(summary.input_tokens, 20)
        self.assertEqual(summary.output_tokens, 5)
        self.assertEqual(summary.total_tokens, 25)


class AgentHookIntegrationTests(unittest.TestCase):
    def test_pre_tool_agent_reads_file_then_blocks_turn(self) -> None:
        client = AgentHookClient(
            [
                [
                    {
                        "type": "tool_call",
                        "id": "write-1",
                        "name": "write_file",
                        "input": {"path": "app.py", "content": "x = 1\n"},
                    }
                ],
                [
                    {
                        "type": "tool_call",
                        "id": "read-1",
                        "name": "read_file",
                        "input": {"path": "policy.txt"},
                    }
                ],
                [
                    {
                        "type": "text",
                        "text": '{"ok":false,"reason":"Policy file requires review."}',
                    }
                ],
            ]
        )
        with tempfile.TemporaryDirectory(prefix="vibeagent-agent-hook-") as base:
            root = Path(base)
            (root / "policy.txt").write_text("manual review\n", encoding="utf-8")
            _write_agent_hook(root)
            result = run_agent(
                "Write app.py",
                base_dir=root,
                client=client,
                max_iterations=2,
                model_retries=0,
                approval_handler=_approve,
            )
            events = [
                json.loads(line)
                for line in (
                    root / ".vibeagent/sessions" / result.run_id / "events.jsonl"
                ).read_text(encoding="utf-8").splitlines()
            ]

            self.assertFalse((root / "app.py").exists())

        self.assertFalse(result.success)
        self.assertEqual(result.stop_reason, "hook_blocked")
        self.assertEqual(result.message, "Policy file requires review.")
        agent_tool_names = {
            str(tool["name"])
            for tool in client.tools[1]
            if isinstance(tool, dict)
        }
        self.assertIn("read_file", agent_tool_names)
        self.assertIn("finish", agent_tool_names)
        self.assertNotIn("write_file", agent_tool_names)
        self.assertNotIn("run_command", agent_tool_names)
        self.assertNotIn("delegate_task", agent_tool_names)
        self.assertNotIn("http_fetch", agent_tool_names)
        self.assertNotIn("mcp_servers", agent_tool_names)
        self.assertNotIn("session_transcript", agent_tool_names)
        self.assertNotIn("tool_search", agent_tool_names)
        event_types = [event["type"] for event in events]
        self.assertIn("hook_agent_tool_call", event_types)
        self.assertIn("hook_agent_tool_result", event_types)
        self.assertNotIn("subagent_started", event_types)

    def test_continue_on_block_returns_reason_to_main_agent(self) -> None:
        client = AgentHookClient(
            [
                [
                    {
                        "type": "tool_call",
                        "id": "write-1",
                        "name": "write_file",
                        "input": {"path": "app.py", "content": "x = 1\n"},
                    }
                ],
                [
                    {
                        "type": "text",
                        "text": '{"ok":false,"reason":"Use another approach."}',
                    }
                ],
                [{"type": "text", "text": "Stopped after verifier feedback."}],
            ]
        )
        with tempfile.TemporaryDirectory(prefix="vibeagent-agent-hook-") as base:
            root = Path(base)
            _write_agent_hook(root, continue_on_block=True)
            result = run_agent(
                "Write app.py",
                base_dir=root,
                client=client,
                max_iterations=2,
                model_retries=0,
                approval_handler=_approve,
            )

            self.assertFalse((root / "app.py").exists())

        self.assertTrue(result.success)
        self.assertIn("Use another approach.", str(client.messages[2][-1].content))

    def test_stop_agent_hook_continues_then_allows(self) -> None:
        client = AgentHookClient(
            [
                [{"type": "text", "text": "Draft answer."}],
                [
                    {
                        "type": "text",
                        "text": '{"ok":false,"reason":"Inspect evidence first."}',
                    }
                ],
                [{"type": "text", "text": "Verified answer."}],
                [{"type": "text", "text": '{"ok":true}'}],
            ]
        )
        with tempfile.TemporaryDirectory(prefix="vibeagent-agent-hook-") as base:
            root = Path(base)
            _write_agent_hook(root, event="Stop", matcher=".*")
            result = run_agent(
                "Finish carefully",
                base_dir=root,
                client=client,
                max_iterations=2,
                model_retries=0,
                approval_handler=_approve,
            )

        self.assertTrue(result.success)
        self.assertEqual(result.message, "Verified answer.")
        self.assertIn(
            "Stop hook feedback:\nInspect evidence first.",
            str(client.messages[2][-1].content),
        )

    def test_agent_finish_tool_returns_strict_decision(self) -> None:
        client = AgentHookClient(
            [
                [
                    {
                        "type": "tool_call",
                        "id": "write-1",
                        "name": "write_file",
                        "input": {"path": "app.py", "content": "x = 1\n"},
                    }
                ],
                [
                    {
                        "type": "tool_call",
                        "id": "finish-1",
                        "name": "finish",
                        "input": {"message": '{"ok":true}'},
                    }
                ],
                [{"type": "text", "text": "Created app.py."}],
            ]
        )
        with tempfile.TemporaryDirectory(prefix="vibeagent-agent-hook-") as base:
            root = Path(base)
            _write_agent_hook(root)
            result = run_agent(
                "Write app.py",
                base_dir=root,
                client=client,
                max_iterations=2,
                model_retries=0,
                approval_handler=_approve,
            )
            written = (root / "app.py").read_text(encoding="utf-8")

        self.assertTrue(result.success)
        self.assertEqual(written, "x = 1\n")

    def test_invalid_response_and_model_failure_are_non_blocking(self) -> None:
        for hook_response, expected_event in (
            ([{"type": "text", "text": "not json"}], None),
            (RuntimeError("provider unavailable"), "hook_agent_model_error"),
        ):
            with self.subTest(expected_event=expected_event):
                client = AgentHookClient(
                    [
                        [
                            {
                                "type": "tool_call",
                                "id": "write-1",
                                "name": "write_file",
                                "input": {
                                    "path": "app.py",
                                    "content": "x = 1\n",
                                },
                            }
                        ],
                        hook_response,
                        [{"type": "text", "text": "Created app.py."}],
                    ]
                )
                with tempfile.TemporaryDirectory(
                    prefix="vibeagent-agent-hook-"
                ) as base:
                    root = Path(base)
                    _write_agent_hook(root)
                    result = run_agent(
                        "Write app.py",
                        base_dir=root,
                        client=client,
                        max_iterations=2,
                        model_retries=0,
                        approval_handler=_approve,
                    )
                    events = [
                        json.loads(line)
                        for line in (
                            root
                            / ".vibeagent/sessions"
                            / result.run_id
                            / "events.jsonl"
                        ).read_text(encoding="utf-8").splitlines()
                    ]
                    written = (root / "app.py").exists()

                self.assertTrue(result.success)
                self.assertTrue(written)
                if expected_event is not None:
                    self.assertIn(
                        expected_event, [event["type"] for event in events]
                    )
                completed = next(
                    event["result"]
                    for event in events
                    if event["type"] == "hook_completed"
                    and event["result"].get("handler_type") == "agent"
                )
                self.assertTrue(completed["non_blocking_error"])

    def test_agent_model_override_and_timeout_are_scoped(self) -> None:
        client = AgentHookClient(
            [
                [
                    {
                        "type": "tool_call",
                        "id": "write-1",
                        "name": "write_file",
                        "input": {"path": "app.py", "content": "x = 1\n"},
                    }
                ],
                [{"type": "text", "text": '{"ok":true}'}],
                [{"type": "text", "text": "Created app.py."}],
            ]
        )
        with tempfile.TemporaryDirectory(prefix="vibeagent-agent-hook-") as base:
            root = Path(base)
            _write_agent_hook(root, model="fast-model", timeout=1.5)
            result = run_agent(
                "Write app.py",
                base_dir=root,
                client=client,
                max_iterations=2,
                model_retries=0,
                approval_handler=_approve,
            )

        self.assertTrue(result.success)
        self.assertEqual(client.configured_models, ["fast-model"])
        self.assertEqual(client.timeouts[0], 120_000)
        self.assertGreaterEqual(client.timeouts[1], 1_400)
        self.assertLessEqual(client.timeouts[1], 1_500)
        self.assertEqual(client.timeouts[2], 120_000)


if __name__ == "__main__":
    unittest.main()
