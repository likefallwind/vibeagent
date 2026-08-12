import json
import tempfile
import unittest
from dataclasses import replace
from pathlib import Path
from unittest.mock import patch

from vibeagent.actions import parse_tool_action
from vibeagent.agent import run_agent
from vibeagent.agent_delegate import execute_delegate_task_action
from vibeagent.agent_hooks import run_tool_hooks
from vibeagent.agent_hook_results import HookRunResult
from vibeagent.agent_post_tool_hook_output import (
    MAX_UPDATED_TOOL_OUTPUT_BYTES,
    PostToolHookOutputError,
    parse_post_tool_hook_output,
)
from vibeagent.agent_multimodal import build_updated_tool_result_block
from vibeagent.types import ApprovalDecision, AssistantResponse, ChatMessage, ContentBlock
from vibeagent.workspace import create_run_workspace
from vibeagent.workspace_hooks import ProjectHook, ProjectHooks, read_project_hooks
from vibeagent.workspace_permissions import ProjectPermissions


class OutputHookClient:
    def __init__(self, responses: list[list[ContentBlock]]) -> None:
        self.responses = responses
        self.messages: list[list[ChatMessage]] = []

    def complete(self, messages, tools=None, max_tokens=4096, temperature=0.2, timeout_ms=120_000):
        self.messages.append(list(messages))
        content = self.responses[len(self.messages) - 1]
        return AssistantResponse(content=content, raw={"content": content})


def _result(stdout: str) -> HookRunResult:
    return HookRunResult(
        event="PostToolUse",
        command="hook",
        source="test",
        status="passed",
        ok=True,
        exit_code=0,
        timed_out=False,
        stdout=stdout,
        stderr="",
        message="passed",
    )


def _write_hook(root: Path, commands: list[str], matcher: str = "read_file") -> None:
    path = root / ".vibeagent" / "hooks.json"
    path.parent.mkdir(parents=True)
    path.write_text(
        json.dumps(
            {
                "PostToolUse": [
                    {
                        "matcher": matcher,
                        "hooks": [
                            {"type": "command", "command": command}
                            for command in commands
                        ],
                    }
                ]
            }
        ),
        encoding="utf-8",
    )


def _approve(_request) -> ApprovalDecision:
    return ApprovalDecision(approved=True, message="approved")


class PostToolOutputHookTests(unittest.TestCase):
    def test_parser_accepts_any_bounded_json_value_and_context(self) -> None:
        parsed = parse_post_tool_hook_output(
            _result(
                json.dumps(
                    {
                        "hookSpecificOutput": {
                            "hookEventName": "PostToolUse",
                            "updatedToolOutput": ["sanitized", {"count": 2}],
                            "additionalContext": "Output was filtered.",
                        }
                    }
                )
            )
        )

        self.assertTrue(parsed.updated_tool_output_set)
        self.assertEqual(parsed.updated_tool_output, ["sanitized", {"count": 2}])
        self.assertEqual(parsed.additional_context, "Output was filtered.")

    def test_parser_rejects_wrong_event_non_finite_and_oversized_output(self) -> None:
        invalid = [
            {"hookSpecificOutput": {"hookEventName": "PreToolUse", "updatedToolOutput": {}}},
            {"hookSpecificOutput": {"updatedToolOutput": float("nan")}},
            {
                "hookSpecificOutput": {
                    "updatedToolOutput": "x" * (MAX_UPDATED_TOOL_OUTPUT_BYTES + 1)
                }
            },
        ]

        for payload in invalid:
            with self.subTest(payload=str(payload)[:80]), self.assertRaises(
                PostToolHookOutputError
            ):
                parse_post_tool_hook_output(_result(json.dumps(payload)))

    def test_all_synchronous_handler_types_share_replacement_semantics(self) -> None:
        response = json.dumps(
            {"hookSpecificOutput": {"updatedToolOutput": {"filtered": True}}}
        )
        with tempfile.TemporaryDirectory(prefix="vibeagent-output-hook-") as base:
            workspace = create_run_workspace(Path(base))
            action = parse_tool_action("read_file", {"path": "app.txt"})
            for handler_type in ("command", "http", "mcp_tool", "prompt", "agent"):
                with self.subTest(handler_type=handler_type):
                    hook = ProjectHook(
                        event="PostToolUse",
                        matcher="read_file",
                        command="hook",
                        timeout_ms=1_000,
                        source="test",
                        handler_type=handler_type,
                    )
                    mocked = replace(_result(response), handler_type=handler_type)
                    with patch(
                        "vibeagent.agent_hooks.run_tool_hook_handler",
                        return_value=mocked,
                    ):
                        batch = run_tool_hooks(
                            workspace,
                            ProjectHooks(hooks=(hook,)),
                            "PostToolUse",
                            "read_file",
                            action,
                            1,
                            1_000,
                            None,
                            _approve,
                            "ask",
                            lambda *_args: self.fail("hook wrapper must not execute target"),
                            ProjectPermissions(),
                            tool_response={"original": True},
                        )

                    self.assertTrue(batch.updated_tool_output_set)
                    self.assertEqual(batch.updated_tool_output, {"filtered": True})

    def test_async_handler_cannot_replace_immediate_tool_output(self) -> None:
        hook = ProjectHook(
            event="PostToolUse",
            matcher="read_file",
            command="hook",
            timeout_ms=1_000,
            source="test",
            async_=True,
        )
        response = json.dumps(
            {"hookSpecificOutput": {"updatedToolOutput": "too late"}}
        )
        with tempfile.TemporaryDirectory(prefix="vibeagent-output-hook-") as base:
            workspace = create_run_workspace(Path(base))
            action = parse_tool_action("read_file", {"path": "app.txt"})
            with patch(
                "vibeagent.agent_hooks.run_tool_hook_handler",
                return_value=replace(_result(response), async_started=True),
            ):
                batch = run_tool_hooks(
                    workspace,
                    ProjectHooks(hooks=(hook,)),
                    "PostToolUse",
                    "read_file",
                    action,
                    1,
                    1_000,
                    None,
                    _approve,
                    "ask",
                    lambda *_args: self.fail("hook wrapper must not execute target"),
                    ProjectPermissions(),
                    tool_response={"original": True},
                )

        self.assertFalse(batch.updated_tool_output_set)

    def test_failure_event_does_not_replace_failed_tool_output(self) -> None:
        hook = ProjectHook(
            event="PostToolUseFailure",
            matcher="read_file",
            command="hook",
            timeout_ms=1_000,
            source="test",
        )
        response = json.dumps(
            {"hookSpecificOutput": {"updatedToolOutput": "not supported"}}
        )
        with tempfile.TemporaryDirectory(prefix="vibeagent-output-hook-") as base:
            workspace = create_run_workspace(Path(base))
            action = parse_tool_action("read_file", {"path": "missing.txt"})
            with patch(
                "vibeagent.agent_hooks.run_tool_hook_handler",
                return_value=replace(_result(response), event="PostToolUseFailure"),
            ):
                batch = run_tool_hooks(
                    workspace,
                    ProjectHooks(hooks=(hook,)),
                    "PostToolUseFailure",
                    "read_file",
                    action,
                    1,
                    1_000,
                    None,
                    _approve,
                    "ask",
                    lambda *_args: self.fail("hook wrapper must not execute target"),
                    ProjectPermissions(),
                    tool_response={"error": "missing"},
                )

        self.assertFalse(batch.updated_tool_output_set)

    def test_replacement_is_redacted_before_entering_model_context(self) -> None:
        block = build_updated_tool_result_block(
            "tool-1",
            {"token": "sk-test-secret-value", "status": "ok"},
            additional_contexts=("Bearer context-secret-value",),
        )

        self.assertNotIn("sk-test-secret-value", json.dumps(block))
        self.assertNotIn("context-secret-value", json.dumps(block))
        self.assertIn("REDACTED", json.dumps(block))

    def test_replacement_changes_only_model_view_and_hook_receives_original(self) -> None:
        replacement = {
            "kind": "read_file",
            "path": "app.txt",
            "content": "SANITIZED",
            "message": "Filtered by project hook.",
        }
        hook = (
            "python3 -c \"import json,pathlib,sys; d=json.load(sys.stdin); "
            "pathlib.Path('hook-input.json').write_text(json.dumps(d['tool_response'])); "
            f"print(json.dumps({{'hookSpecificOutput':{{'hookEventName':'PostToolUse',"
            f"'updatedToolOutput':{replacement!r},'additionalContext':'Filtered output.'}}}}))\""
        )
        client = OutputHookClient(
            [
                [{"type": "tool_call", "id": "read-1", "name": "read_file", "input": {"path": "app.txt"}}],
                [{"type": "text", "text": "Used the filtered result."}],
            ]
        )
        with tempfile.TemporaryDirectory(prefix="vibeagent-output-hook-") as base:
            root = Path(base)
            root.joinpath("app.txt").write_text("ORIGINAL_RESULT\n", encoding="utf-8")
            _write_hook(root, [hook])
            result = run_agent(
                "Read app.txt",
                base_dir=root,
                client=client,
                max_iterations=2,
                approval_handler=_approve,
            )
            hook_input = json.loads(root.joinpath("hook-input.json").read_text(encoding="utf-8"))
            events = [
                json.loads(line)
                for line in (root / ".vibeagent" / "sessions" / result.run_id / "events.jsonl")
                .read_text(encoding="utf-8")
                .splitlines()
            ]

        model_result = client.messages[1][-1].content[0]
        self.assertTrue(result.success)
        self.assertEqual(result.observations[0].content, "ORIGINAL_RESULT\n")
        self.assertEqual(hook_input["content"], "ORIGINAL_RESULT\n")
        self.assertNotIn("ORIGINAL_RESULT", json.dumps(model_result))
        self.assertIn("SANITIZED", json.dumps(model_result))
        self.assertIn("Filtered output", json.dumps(model_result))
        tool_event = next(event for event in events if event["type"] == "tool_result")
        self.assertTrue(tool_event["result"]["content"]["redacted"])
        self.assertEqual(tool_event["result"]["content"]["chars"], len("ORIGINAL_RESULT\n"))
        hook_result = tool_event["result"]["hooks"][0]
        self.assertTrue(hook_result["updated_tool_output_applied"])
        self.assertEqual(hook_result["stdout"], "[PostToolUse updatedToolOutput applied]")

    def test_later_hook_receives_and_replaces_prior_hook_output(self) -> None:
        first = (
            "python3 -c \"import json; print(json.dumps({'hookSpecificOutput':"
            "{'updatedToolOutput':{'stage':1}}}))\""
        )
        second = (
            "python3 -c \"import json,sys; d=json.load(sys.stdin); "
            "assert d['tool_response']=={'stage':1}; "
            "print(json.dumps({'hookSpecificOutput':{'updatedToolOutput':{'stage':2}}}))\""
        )
        client = OutputHookClient(
            [
                [{"type": "tool_call", "id": "read-1", "name": "read_file", "input": {"path": "app.txt"}}],
                [{"type": "text", "text": "Done."}],
            ]
        )
        with tempfile.TemporaryDirectory(prefix="vibeagent-output-hook-") as base:
            root = Path(base)
            root.joinpath("app.txt").write_text("original", encoding="utf-8")
            _write_hook(root, [first, second])
            result = run_agent(
                "Read app.txt", base_dir=root, client=client, max_iterations=2,
                approval_handler=_approve,
            )

        self.assertTrue(result.success)
        self.assertEqual(
            json.loads(client.messages[1][-1].content[0]["content"]),
            {"stage": 2},
        )

    def test_subagent_receives_replaced_output_but_keeps_original_observation(self) -> None:
        hook = (
            "python3 -c \"import json; print(json.dumps({'hookSpecificOutput':"
            "{'updatedToolOutput':'SUBAGENT_FILTERED'}}))\""
        )
        client = OutputHookClient(
            [
                [{"type": "tool_call", "id": "read-1", "name": "read_file", "input": {"path": "app.txt"}}],
                [{"type": "text", "text": "Subagent used the filtered result."}],
            ]
        )
        with tempfile.TemporaryDirectory(prefix="vibeagent-output-hook-") as base:
            root = Path(base)
            root.joinpath("app.txt").write_text("SUBAGENT_ORIGINAL", encoding="utf-8")
            _write_hook(root, [hook])
            workspace = create_run_workspace(root)
            result = execute_delegate_task_action(
                workspace,
                parse_tool_action("delegate_task", {"task": "Read app.txt", "max_iterations": 2}),
                client,
                parent_iteration=1,
                subagent_id="reader",
                max_output_tokens=1024,
                model_retries=0,
                model_retry_delay_ms=0,
                model_timeout_ms=10_000,
                command_timeout_ms=10_000,
                logger=None,
                approval_handler=_approve,
                hooks=read_project_hooks(workspace),
            )

        self.assertTrue(result.ok)
        self.assertEqual(result.summary, "Subagent used the filtered result.")
        self.assertEqual(client.messages[1][-1].content[0]["content"], "SUBAGENT_FILTERED")

    def test_invalid_replacement_preserves_original_and_reports_hook_failure(self) -> None:
        hook = "python3 -c \"print('{')\""
        client = OutputHookClient(
            [
                [{"type": "tool_call", "id": "read-1", "name": "read_file", "input": {"path": "app.txt"}}],
                [{"type": "text", "text": "Observed the hook failure and original result."}],
            ]
        )
        with tempfile.TemporaryDirectory(prefix="vibeagent-output-hook-") as base:
            root = Path(base)
            root.joinpath("app.txt").write_text("ORIGINAL_AFTER_INVALID", encoding="utf-8")
            _write_hook(root, [hook])
            result = run_agent(
                "Read app.txt", base_dir=root, client=client, max_iterations=2,
                approval_handler=_approve,
            )

        model_result = json.dumps(client.messages[1][-1].content[0])
        self.assertTrue(result.success)
        self.assertIn("ORIGINAL_AFTER_INVALID", model_result)
        self.assertIn("PostToolUse hook output was rejected", model_result)
        self.assertEqual(result.observations[0].content, "ORIGINAL_AFTER_INVALID")
        self.assertEqual(result.observations[1].kind, "tool_error")

    def test_special_delegate_result_is_replaced_only_for_parent_model(self) -> None:
        hook = (
            "python3 -c \"import json; print(json.dumps({'hookSpecificOutput':"
            "{'updatedToolOutput':'DELEGATE_FILTERED'}}))\""
        )
        client = OutputHookClient(
            [
                [
                    {
                        "type": "tool_call",
                        "id": "delegate-1",
                        "name": "delegate_task",
                        "input": {"task": "Inspect app.txt", "max_iterations": 1},
                    }
                ],
                [{"type": "text", "text": "Original delegate report."}],
                [{"type": "text", "text": "Parent used filtered delegate output."}],
            ]
        )
        with tempfile.TemporaryDirectory(prefix="vibeagent-output-hook-") as base:
            root = Path(base)
            _write_hook(root, [hook], matcher="delegate_task")
            result = run_agent(
                "Delegate inspection", base_dir=root, client=client, max_iterations=2,
                approval_handler=_approve,
            )

        self.assertTrue(result.success)
        self.assertEqual(result.observations[0].summary, "Original delegate report.")
        self.assertEqual(client.messages[2][-1].content[0]["content"], "DELEGATE_FILTERED")


if __name__ == "__main__":
    unittest.main()
