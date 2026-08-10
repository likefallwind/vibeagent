from __future__ import annotations

import json
from pathlib import Path
import tempfile
import unittest

from vibeagent.actions import parse_tool_action
from vibeagent.agent import run_agent
from vibeagent.agent_delegate import execute_delegate_task_action
from vibeagent.agent_hook_prompt import (
    expand_prompt_hook_arguments,
    parse_prompt_hook_decision,
)
from vibeagent.agent_runtime_utils import append_session_event
from vibeagent.session import summarize_session
from vibeagent.types import ApprovalDecision, AssistantResponse, ChatMessage, ContentBlock
from vibeagent.workspace import create_run_workspace
from vibeagent.workspace_hooks import read_project_hooks


class PromptHookClient:
    def __init__(
        self,
        responses: list[list[ContentBlock] | BaseException],
        *,
        model: str = "main-model",
        configured_models: list[str] | None = None,
        messages: list[list[ChatMessage]] | None = None,
        timeouts: list[int] | None = None,
    ) -> None:
        self.responses = responses
        self.messages = messages if messages is not None else []
        self.timeouts = timeouts if timeouts is not None else []
        self.model = model
        self.configured_models = configured_models if configured_models is not None else []

    def complete(
        self,
        messages,
        tools=None,
        max_tokens=4096,
        temperature=0.2,
        timeout_ms=120_000,
    ):
        self.messages.append(list(messages))
        self.timeouts.append(timeout_ms)
        response = self.responses.pop(0)
        if isinstance(response, BaseException):
            raise response
        return AssistantResponse(content=response, raw={"content": response})

    def with_agent_profile(self, *, model: str | None, effort: str | None):
        assert effort is None
        selected = model or self.model
        self.configured_models.append(selected)
        return PromptHookClient(
            self.responses,
            model=selected,
            configured_models=self.configured_models,
            messages=self.messages,
            timeouts=self.timeouts,
        )


def _write_prompt_hook(
    root: Path,
    *,
    event: str = "PreToolUse",
    matcher: str = "write_file",
    prompt: str = "Evaluate this operation: $ARGUMENTS",
    model: str | None = None,
    timeout: float | None = None,
    continue_on_block: bool = False,
) -> None:
    handler: dict[str, object] = {
        "type": "prompt",
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
            {
                event: [
                    {
                        "matcher": matcher,
                        "hooks": [handler],
                    }
                ]
            }
        ),
        encoding="utf-8",
    )


def _approve(_request) -> ApprovalDecision:
    return ApprovalDecision(approved=True, message="approved")


class PromptHookConfigTests(unittest.TestCase):
    def test_loads_prompt_fields_with_prompt_default_timeout(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-prompt-hook-") as base:
            root = Path(base)
            _write_prompt_hook(
                root,
                event="Stop",
                matcher=".*",
                model="fast-model",
                continue_on_block=True,
            )
            config = read_project_hooks(create_run_workspace(root))

        self.assertIsNone(config.error)
        hook = config.hooks[0]
        self.assertEqual(hook.handler_type, "prompt")
        self.assertEqual(hook.prompt, "Evaluate this operation: $ARGUMENTS")
        self.assertEqual(hook.model, "fast-model")
        self.assertTrue(hook.continue_on_block)
        self.assertEqual(hook.timeout_ms, 30_000)

    def test_rejects_prompt_handlers_on_unsupported_events_and_bad_fields(self) -> None:
        invalid = [
            ("SessionStart", {"type": "prompt", "prompt": "evaluate"}),
            ("CwdChanged", {"type": "prompt", "prompt": "evaluate"}),
            ("InstructionsLoaded", {"type": "prompt", "prompt": "evaluate"}),
            ("PreToolUse", {"type": "prompt", "prompt": ""}),
            ("PreToolUse", {"type": "prompt", "prompt": "bad\u0000prompt"}),
            ("PreToolUse", {"type": "prompt", "prompt": "evaluate", "model": ""}),
            (
                "PreToolUse",
                {"type": "prompt", "prompt": "evaluate", "continueOnBlock": "yes"},
            ),
            ("PreToolUse", {"type": "prompt", "prompt": "evaluate", "async": True}),
        ]
        for index, (event, handler) in enumerate(invalid):
            with self.subTest(index=index), tempfile.TemporaryDirectory(
                prefix="vibeagent-prompt-hook-"
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

    def test_expands_arguments_once_and_preserves_escaped_dollars(self) -> None:
        expanded = expand_prompt_hook_arguments(
            r"Cost is \$1.00. Inspect $ARGUMENTS and literal \$ARGUMENTS.",
            {"tool_input": {"path": "app.py"}},
        )
        appended = expand_prompt_hook_arguments("Inspect operation.", {"value": 2})

        self.assertIn("Cost is $1.00.", expanded)
        self.assertIn('{"tool_input":{"path":"app.py"}}', expanded)
        self.assertIn("literal $ARGUMENTS", expanded)
        self.assertEqual(appended, 'Inspect operation.\n\n{"value":2}')

    def test_decision_parser_is_strict(self) -> None:
        self.assertEqual(parse_prompt_hook_decision('{"ok":true}'), (True, ""))
        self.assertEqual(
            parse_prompt_hook_decision('{"ok":false,"reason":"Run tests."}'),
            (False, "Run tests."),
        )
        for invalid in (
            "```json\n{\"ok\":true}\n```",
            '{"ok":"true"}',
            '{"ok":false}',
            '{"ok":true,"reason":42}',
            '{"ok":false,"ok":true,"reason":"ambiguous"}',
            "[]",
        ):
            with self.subTest(invalid=invalid), self.assertRaises(ValueError):
                parse_prompt_hook_decision(invalid)

    def test_hook_model_usage_is_included_in_session_totals(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-prompt-hook-") as base:
            root = Path(base)
            workspace = create_run_workspace(root, run_id="prompt-usage")
            append_session_event(
                workspace.session_dir,
                "hook_model",
                {
                    "content": [{"type": "text", "text": '{"ok":true}'}],
                    "usage": {
                        "input_tokens": 12,
                        "output_tokens": 3,
                        "total_tokens": 15,
                    },
                },
            )
            summary = summarize_session(root, "prompt-usage")

        self.assertEqual(summary.input_tokens, 12)
        self.assertEqual(summary.output_tokens, 3)
        self.assertEqual(summary.total_tokens, 15)


class PromptHookIntegrationTests(unittest.TestCase):
    def test_pre_tool_prompt_hook_blocks_write_with_hook_input(self) -> None:
        client = PromptHookClient(
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
                        "text": '{"ok":false,"reason":"Policy rejected app.py."}',
                    }
                ],
                [{"type": "text", "text": "The policy rejected the write."}],
            ]
        )
        with tempfile.TemporaryDirectory(prefix="vibeagent-prompt-hook-") as base:
            root = Path(base)
            _write_prompt_hook(root, continue_on_block=True)
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
        prompt = client.messages[1][0].content
        self.assertIsInstance(prompt, str)
        self.assertIn('"tool_input":{"path":"app.py","content":"x = 1\\n"}', prompt)
        self.assertIn("Policy rejected app.py.", str(client.messages[2][-1].content))

    def test_pre_tool_prompt_hook_blocks_turn_by_default(self) -> None:
        client = PromptHookClient(
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
                        "text": '{"ok":false,"reason":"User review required."}',
                    }
                ],
            ]
        )
        with tempfile.TemporaryDirectory(prefix="vibeagent-prompt-hook-") as base:
            root = Path(base)
            _write_prompt_hook(root)
            result = run_agent(
                "Write app.py",
                base_dir=root,
                client=client,
                max_iterations=2,
                model_retries=0,
                approval_handler=_approve,
            )

            self.assertFalse((root / "app.py").exists())

        self.assertFalse(result.success)
        self.assertEqual(result.stop_reason, "hook_blocked")
        self.assertEqual(result.message, "User review required.")
        self.assertEqual(len(client.messages), 2)

    def test_invalid_prompt_response_is_non_blocking(self) -> None:
        client = PromptHookClient(
            [
                [
                    {
                        "type": "tool_call",
                        "id": "write-1",
                        "name": "write_file",
                        "input": {"path": "app.py", "content": "x = 1\n"},
                    }
                ],
                [{"type": "text", "text": "not json"}],
                [{"type": "text", "text": "Created app.py after hook error."}],
            ]
        )
        with tempfile.TemporaryDirectory(prefix="vibeagent-prompt-hook-") as base:
            root = Path(base)
            _write_prompt_hook(root)
            result = run_agent(
                "Write app.py",
                base_dir=root,
                client=client,
                max_iterations=2,
                model_retries=0,
                approval_handler=_approve,
            )
            content = (root / "app.py").read_text(encoding="utf-8")

        self.assertTrue(result.success)
        self.assertEqual(content, "x = 1\n")

    def test_prompt_model_failure_is_non_blocking(self) -> None:
        client = PromptHookClient(
            [
                [
                    {
                        "type": "tool_call",
                        "id": "write-1",
                        "name": "write_file",
                        "input": {"path": "app.py", "content": "x = 1\n"},
                    }
                ],
                RuntimeError("provider unavailable"),
                [{"type": "text", "text": "Created app.py after provider outage."}],
            ]
        )
        with tempfile.TemporaryDirectory(prefix="vibeagent-prompt-hook-") as base:
            root = Path(base)
            _write_prompt_hook(root)
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
            written = (root / "app.py").exists()

        self.assertTrue(result.success)
        self.assertTrue(written)
        self.assertIn("hook_model_error", [event["type"] for event in events])
        completed = next(
            event["result"]
            for event in events
            if event["type"] == "hook_completed"
            and event["result"].get("handler_type") == "prompt"
        )
        self.assertTrue(completed["non_blocking_error"])

    def test_post_tool_prompt_block_ends_turn_after_side_effect(self) -> None:
        client = PromptHookClient(
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
                        "text": '{"ok":false,"reason":"Review generated file."}',
                    }
                ],
            ]
        )
        with tempfile.TemporaryDirectory(prefix="vibeagent-prompt-hook-") as base:
            root = Path(base)
            _write_prompt_hook(root, event="PostToolUse")
            result = run_agent(
                "Write app.py",
                base_dir=root,
                client=client,
                max_iterations=2,
                model_retries=0,
                approval_handler=_approve,
            )
            content = (root / "app.py").read_text(encoding="utf-8")

        self.assertFalse(result.success)
        self.assertEqual(result.stop_reason, "hook_blocked")
        self.assertEqual(result.message, "Review generated file.")
        self.assertEqual(content, "x = 1\n")

    def test_stop_prompt_hook_continues_then_allows(self) -> None:
        client = PromptHookClient(
            [
                [{"type": "text", "text": "Draft answer."}],
                [
                    {
                        "type": "text",
                        "text": '{"ok":false,"reason":"Add verification evidence."}',
                    }
                ],
                [{"type": "text", "text": "Verified answer."}],
                [{"type": "text", "text": '{"ok":true}'}],
            ]
        )
        with tempfile.TemporaryDirectory(prefix="vibeagent-prompt-hook-") as base:
            root = Path(base)
            _write_prompt_hook(root, event="Stop", matcher=".*")
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
            "Stop hook feedback:\nAdd verification evidence.",
            str(client.messages[2][-1].content),
        )

    def test_prompt_model_override_and_timeout_are_scoped(self) -> None:
        client = PromptHookClient(
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
        with tempfile.TemporaryDirectory(prefix="vibeagent-prompt-hook-") as base:
            root = Path(base)
            _write_prompt_hook(root, model="fast-model", timeout=1.5)
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
        self.assertEqual(client.timeouts, [120_000, 1_500, 120_000])

    def test_subagent_stop_prompt_hook_continues_then_allows(self) -> None:
        client = PromptHookClient(
            [
                [{"type": "text", "text": "Draft subagent report."}],
                [
                    {
                        "type": "text",
                        "text": '{"ok":false,"reason":"Inspect tests first."}',
                    }
                ],
                [{"type": "text", "text": "Verified subagent report."}],
                [{"type": "text", "text": '{"ok":true}'}],
            ]
        )
        with tempfile.TemporaryDirectory(prefix="vibeagent-prompt-hook-") as base:
            root = Path(base)
            _write_prompt_hook(
                root,
                event="SubagentStop",
                matcher="Explore",
            )
            workspace = create_run_workspace(root, run_id="prompt-hook-subagent")
            action = parse_tool_action(
                "delegate_task",
                {"task": "Inspect carefully", "max_iterations": 2},
            )
            observation = execute_delegate_task_action(
                workspace,
                action,
                client,
                parent_iteration=1,
                subagent_id="delegate-1-1",
                max_output_tokens=2_048,
                model_retries=0,
                model_retry_delay_ms=0,
                model_timeout_ms=10_000,
                command_timeout_ms=10_000,
                logger=None,
                approval_handler=_approve,
                hooks=read_project_hooks(workspace),
            )

        self.assertTrue(observation.ok)
        self.assertEqual(observation.iterations, 2)
        self.assertEqual(observation.summary, "Verified subagent report.")
        self.assertIn(
            "SubagentStop hook feedback:\nInspect tests first.",
            str(client.messages[2][-1].content),
        )

    def test_subagent_pre_tool_prompt_block_halts_subagent_turn(self) -> None:
        client = PromptHookClient(
            [
                [
                    {
                        "type": "tool_call",
                        "id": "read-1",
                        "name": "Read",
                        "input": {"file_path": "app.py"},
                    }
                ],
                [
                    {
                        "type": "text",
                        "text": '{"ok":false,"reason":"Subagent read needs review."}',
                    }
                ],
            ]
        )
        with tempfile.TemporaryDirectory(prefix="vibeagent-prompt-hook-") as base:
            root = Path(base)
            (root / "app.py").write_text("x = 1\n", encoding="utf-8")
            _write_prompt_hook(root, matcher="Read")
            workspace = create_run_workspace(root, run_id="prompt-hook-subagent-tool")
            action = parse_tool_action(
                "delegate_task",
                {"task": "Inspect app.py", "max_iterations": 1},
            )
            observation = execute_delegate_task_action(
                workspace,
                action,
                client,
                parent_iteration=1,
                subagent_id="delegate-1-1",
                max_output_tokens=2_048,
                model_retries=0,
                model_retry_delay_ms=0,
                model_timeout_ms=10_000,
                command_timeout_ms=10_000,
                logger=None,
                approval_handler=_approve,
                hooks=read_project_hooks(workspace),
            )

        self.assertFalse(observation.ok)
        self.assertEqual(observation.iterations, 1)
        self.assertEqual(observation.message, "Subagent read needs review.")
        self.assertEqual(len(client.messages), 2)


if __name__ == "__main__":
    unittest.main()
