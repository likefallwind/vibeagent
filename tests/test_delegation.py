import json
import tempfile
import unittest
from pathlib import Path

from vibeagent.action_parsing import ActionParseError, parse_tool_action
from vibeagent.actions import AGENT_TOOL_DEFINITIONS, execute_action
from vibeagent.agent import run_agent
from vibeagent import agent_delegate, agent_delegate_completion, agent_delegate_context, agent_delegate_loop
from vibeagent.agent_delegate import (
    DELEGATE_TOOL_DEFINITIONS,
    code_delegate_initial_tool_names,
    delegate_tool_definitions,
    execute_delegate_task_action,
)
from vibeagent.session_timeline_reports import format_session_event_timeline_item
from vibeagent.session import read_session_events, summarize_session
from vibeagent.session_types import SessionEvent
from vibeagent.types import ApprovalDecision, AssistantResponse, ChatMessage, ContentBlock, ModelUsage
from vibeagent.workspace import create_run_workspace


class DelegationClient:
    def __init__(
        self,
        responses: list[list[ContentBlock]],
        usages: list[ModelUsage | None] | None = None,
    ) -> None:
        self.responses = responses
        self.usages = usages or []
        self.messages: list[list[ChatMessage]] = []
        self.tool_names: list[list[str]] = []

    def complete(self, messages, tools=None, max_tokens=4096, temperature=0.2, timeout_ms=120_000):
        self.messages.append(list(messages))
        self.tool_names.append([str(tool["name"]) for tool in tools or []])
        index = len(self.messages) - 1
        content = self.responses[index]
        usage = self.usages[index] if index < len(self.usages) else None
        return AssistantResponse(content=content, raw={"content": content}, usage=usage)


class ContextOverflowDelegationClient:
    def __init__(self) -> None:
        self.messages: list[list[ChatMessage]] = []

    def complete(self, messages, tools=None, max_tokens=4096, temperature=0.2, timeout_ms=120_000):
        self.messages.append(list(messages))
        call = len(self.messages)
        if call == 1:
            content = [
                {
                    "type": "tool_call",
                    "id": "read-1",
                    "name": "read_file",
                    "input": {"path": "app.py"},
                }
            ]
            return AssistantResponse(content=content, raw={"content": content})
        if call == 2:
            raise RuntimeError("context_length_exceeded")
        content = [{"type": "text", "text": "Recovered subagent evidence from app.py:1."}]
        return AssistantResponse(content=content, raw={"content": content})


class DelegationTests(unittest.TestCase):
    def test_delegate_context_helpers_live_in_context_module(self) -> None:
        self.assertIs(agent_delegate.DELEGATE_SYSTEM_PROMPT, agent_delegate_context.DELEGATE_SYSTEM_PROMPT)
        self.assertIs(agent_delegate.CODE_DELEGATE_SYSTEM_PROMPT, agent_delegate_context.CODE_DELEGATE_SYSTEM_PROMPT)
        self.assertIs(agent_delegate.build_delegate_messages, agent_delegate_context.build_delegate_messages)
        self.assertIs(
            agent_delegate.compact_delegate_message_history,
            agent_delegate_context.compact_delegate_message_history,
        )
        self.assertIs(
            agent_delegate.build_compacted_delegate_context,
            agent_delegate_context.build_compacted_delegate_context,
        )

    def test_delegate_completion_helpers_live_in_completion_module(self) -> None:
        self.assertIs(agent_delegate.clip_delegate_summary, agent_delegate_completion.clip_delegate_summary)
        self.assertIs(agent_delegate.delegate_completion_message, agent_delegate_completion.delegate_completion_message)
        self.assertIs(agent_delegate.finish_delegate_task, agent_delegate_completion.finish_delegate_task)

    def test_delegate_iteration_loop_lives_in_loop_module(self) -> None:
        self.assertIs(agent_delegate.run_delegate_iterations, agent_delegate_loop.run_delegate_iterations)

    def test_delegate_completion_helpers_format_messages(self) -> None:
        explore_action = parse_tool_action("delegate_task", {"task": "Inspect"})
        code_action = parse_tool_action("delegate_task", {"task": "Patch", "mode": "code"})

        self.assertEqual(agent_delegate_completion.delegate_completion_message(explore_action), "Subagent completed the investigation.")
        self.assertEqual(agent_delegate_completion.delegate_completion_message(code_action), "Subagent completed the coding task.")
        self.assertEqual(agent_delegate_completion.clip_delegate_summary("  short  "), "short")
        self.assertEqual(agent_delegate_completion.clip_delegate_summary("abcdef", max_chars=3), "abc\n[delegate summary truncated]")

    def test_parse_delegate_task_normalizes_limits_and_context(self) -> None:
        action = parse_tool_action(
            "delegate_task",
            {"task": "  Find the auth flow  ", "context": "  Focus on middleware  ", "max_iterations": 6},
        )

        self.assertEqual(action.task, "Find the auth flow")
        self.assertEqual(action.context, "Focus on middleware")
        self.assertEqual(action.max_iterations, 6)
        self.assertEqual(action.mode, "explore")

        code_action = parse_tool_action("delegate_task", {"task": "Implement auth", "mode": "code"})
        self.assertEqual(code_action.mode, "code")

        claude_code_action = parse_tool_action(
            "Task",
            {"prompt": "Implement auth", "description": "Use code mode", "mode": "code"},
        )
        self.assertEqual(claude_code_action.task, "Implement auth")
        self.assertEqual(claude_code_action.context, "Use code mode")
        self.assertEqual(claude_code_action.mode, "code")

    def test_parse_delegate_task_rejects_invalid_inputs(self) -> None:
        invalid_inputs = [
            {},
            {"task": ""},
            {"task": "inspect", "context": 1},
            {"task": "inspect", "max_iterations": True},
            {"task": "inspect", "max_iterations": 0},
            {"task": "inspect", "max_iterations": 9},
            {"task": "inspect", "mode": "write"},
            {"task": "inspect", "agent": "../unsafe"},
        ]

        for tool_input in invalid_inputs:
            with self.subTest(tool_input=tool_input), self.assertRaises(ActionParseError):
                parse_tool_action("delegate_task", tool_input)

    def test_claude_delegate_schemas_expose_mode(self) -> None:
        tools = {str(tool["name"]): tool for tool in AGENT_TOOL_DEFINITIONS}

        for name in ("Task", "Agent"):
            with self.subTest(name=name):
                schema = tools[name]["input_schema"]
                self.assertEqual(schema["properties"]["mode"]["enum"], ["explore", "code"])
                self.assertNotIn("mode", schema["required"])

    def test_delegate_tool_catalog_excludes_mutation_execution_and_recursion(self) -> None:
        names = {str(tool["name"]) for tool in DELEGATE_TOOL_DEFINITIONS}

        self.assertIn("read_file", names)
        self.assertIn("search", names)
        self.assertIn("Read", names)
        self.assertIn("Grep", names)
        self.assertIn("Glob", names)
        self.assertIn("LS", names)
        self.assertIn("finish", names)
        self.assertNotIn("delegate_task", names)
        self.assertNotIn("ask_user", names)
        self.assertNotIn("write_file", names)
        self.assertNotIn("Write", names)
        self.assertNotIn("run_command", names)
        self.assertNotIn("Bash", names)
        self.assertNotIn("git_commit", names)

    def test_code_delegate_tool_catalog_uses_shared_visibility_policy(self) -> None:
        active = code_delegate_initial_tool_names("plan")
        names = {str(tool["name"]) for tool in delegate_tool_definitions("code", active, "plan")}

        self.assertIn("read_file", names)
        self.assertIn("finish", names)
        self.assertNotIn("web_fetch", names)
        self.assertNotIn("write_file", names)
        self.assertNotIn("ask_user", names)
        self.assertNotIn("update_plan", names)
        self.assertNotIn("todo_write", names)
        self.assertNotIn("delegate_task", names)

    def test_direct_action_execution_requires_agent_model_client(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-delegate-") as base:
            workspace = create_run_workspace(Path(base))
            action = parse_tool_action("delegate_task", {"task": "Inspect auth"})

            observation = execute_action(workspace, action)

        self.assertFalse(observation.ok)
        self.assertEqual(observation.iterations, 0)
        self.assertIn("model client", observation.message)

    def test_read_only_subagent_reads_file_and_returns_evidence(self) -> None:
        client = DelegationClient(
            [
                [
                    {
                        "type": "tool_call",
                        "id": "read-1",
                        "name": "read_file",
                        "input": {"path": "app.py"},
                    }
                ],
                [{"type": "text", "text": "Authentication is implemented in `app.py:1`."}],
            ],
            usages=[
                ModelUsage(input_tokens=10, output_tokens=3, total_tokens=13),
                ModelUsage(input_tokens=20, output_tokens=5, total_tokens=25),
            ],
        )

        with tempfile.TemporaryDirectory(prefix="vibeagent-delegate-") as base:
            root = Path(base)
            root.joinpath("app.py").write_text("def authenticate():\n    return True\n", encoding="utf-8")
            workspace = create_run_workspace(root)
            action = parse_tool_action("delegate_task", {"task": "Find authentication", "max_iterations": 2})

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
            )
            summary = summarize_session(root, workspace.run_id)

        self.assertTrue(observation.ok)
        self.assertEqual(observation.iterations, 2)
        self.assertEqual(observation.tool_calls, ["read_file"])
        self.assertIn("app.py:1", observation.summary)
        self.assertEqual(summary.input_tokens, 30)
        self.assertEqual(summary.output_tokens, 8)
        self.assertEqual(summary.total_tokens, 38)
        read_result = json.loads(client.messages[1][-1].content[0]["content"])
        self.assertEqual(read_result["kind"], "read_file")

    def test_subagent_recovers_from_context_limit_with_forced_compaction(self) -> None:
        client = ContextOverflowDelegationClient()
        with tempfile.TemporaryDirectory(prefix="vibeagent-delegate-context-recovery-") as base:
            root = Path(base)
            root.joinpath("app.py").write_text("def authenticate():\n    return True\n", encoding="utf-8")
            workspace = create_run_workspace(root)
            action = parse_tool_action("delegate_task", {"task": "Find authentication", "max_iterations": 2})

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
            )
            events = read_session_events(root, workspace.run_id)

        model_errors = [event for event in events if event.type == "subagent_model_error"]
        compactions = [event for event in events if event.type == "subagent_context_compacted"]
        self.assertTrue(observation.ok)
        self.assertIn("app.py:1", observation.summary)
        self.assertEqual([len(messages) for messages in client.messages], [2, 4, 2])
        self.assertEqual(len(model_errors), 1)
        self.assertEqual(model_errors[0].payload["retry_reason"], "context_compaction")
        self.assertTrue(model_errors[0].payload["will_retry"])
        self.assertEqual(len(compactions), 1)
        self.assertEqual(compactions[0].payload["reason"], "context_limit_error")
        self.assertEqual(compactions[0].payload["previous_messages"], 4)
        self.assertEqual(compactions[0].payload["new_messages"], 2)

    def test_subagent_proactively_compacts_large_tool_output_by_character_count(self) -> None:
        client = DelegationClient(
            [
                [
                    {
                        "type": "tool_call",
                        "id": "read-large",
                        "name": "read_file",
                        "input": {"path": "large.txt", "max_bytes": 120_000},
                    }
                ],
                [{"type": "text", "text": "Large-file evidence collected."}],
            ]
        )
        with tempfile.TemporaryDirectory(prefix="vibeagent-delegate-context-size-") as base:
            root = Path(base)
            root.joinpath("large.txt").write_text("x" * 110_000 + "\n", encoding="utf-8")
            workspace = create_run_workspace(root)
            action = parse_tool_action("delegate_task", {"task": "Inspect large.txt", "max_iterations": 2})

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
            )
            events = read_session_events(root, workspace.run_id)

        compactions = [event for event in events if event.type == "subagent_context_compacted"]
        self.assertTrue(observation.ok)
        self.assertEqual([len(messages) for messages in client.messages], [2, 2])
        self.assertEqual(len(compactions), 1)
        self.assertEqual(compactions[0].payload["reason"], "char_threshold")
        self.assertEqual(compactions[0].payload["previous_messages"], 4)
        self.assertGreater(compactions[0].payload["previous_chars"], 96_000)
        self.assertLess(compactions[0].payload["new_chars"], compactions[0].payload["previous_chars"])

    def test_subagent_tool_results_use_shared_redaction_for_model_and_session_events(self) -> None:
        client = DelegationClient(
            [
                [
                    {
                        "type": "tool_call",
                        "id": "read-1",
                        "name": "read_file",
                        "input": {"path": "app.py"},
                    }
                ],
                [{"type": "text", "text": "Found the secret marker in `app.py`."}],
            ]
        )

        with tempfile.TemporaryDirectory(prefix="vibeagent-delegate-") as base:
            root = Path(base)
            root.joinpath("app.py").write_text("OPENAI_API_KEY=sk-subagentsecret1234567890\n", encoding="utf-8")
            workspace = create_run_workspace(root)
            action = parse_tool_action("delegate_task", {"task": "Inspect app.py", "max_iterations": 2})

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
            )
            events_text = "\n".join(
                json.dumps(event.raw, ensure_ascii=False)
                for event in read_session_events(root, workspace.run_id)
            )

        self.assertTrue(observation.ok)
        model_payload_text = json.dumps(client.messages[1][-1].content, ensure_ascii=False)
        self.assertNotIn("sk-subagentsecret1234567890", model_payload_text)
        self.assertNotIn("sk-subagentsecret1234567890", events_text)
        self.assertIn("OPENAI_API_KEY=[REDACTED]", model_payload_text)
        self.assertIn("OPENAI_API_KEY=[REDACTED]", events_text)

    def test_subagent_finish_tool_result_uses_shared_redaction_before_completion_event(self) -> None:
        client = DelegationClient(
            [
                [
                    {
                        "type": "tool_call",
                        "id": "finish-1",
                        "name": "finish",
                        "input": {"message": "Done with TOKEN=subagent-secret"},
                    }
                ],
            ]
        )

        with tempfile.TemporaryDirectory(prefix="vibeagent-delegate-") as base:
            root = Path(base)
            workspace = create_run_workspace(root)
            action = parse_tool_action("delegate_task", {"task": "Finish directly", "max_iterations": 1})
            observation = execute_delegate_task_action(
                workspace,
                action,
                client,
                parent_iteration=7,
                subagent_id="delegate-7-1",
                max_output_tokens=2048,
                model_retries=0,
                model_retry_delay_ms=0,
                model_timeout_ms=10_000,
                command_timeout_ms=10_000,
                logger=None,
            )
            events = read_session_events(root, workspace.run_id)
            events_text = "\n".join(json.dumps(event.raw, ensure_ascii=False) for event in events)

        self.assertTrue(observation.ok)
        self.assertEqual(observation.summary, "Done with TOKEN=subagent-secret")
        self.assertNotIn("subagent-secret", events_text)
        subagent_events = [event for event in events if event.type.startswith("subagent_")]
        self.assertEqual(
            [event.type for event in subagent_events],
            ["subagent_started", "subagent_model", "subagent_tool_call", "subagent_tool_result", "subagent_completed"],
        )
        result_event = subagent_events[3]
        self.assertEqual(result_event.payload["subagent_id"], "delegate-7-1")
        self.assertEqual(result_event.payload["parent_iteration"], 7)
        self.assertEqual(result_event.payload["iteration"], 1)
        self.assertEqual(result_event.payload["id"], "finish-1")
        self.assertEqual(result_event.payload["name"], "finish")
        self.assertFalse(result_event.payload["failed"])
        self.assertEqual(result_event.payload["result"]["summary"], "Done with TOKEN=[REDACTED]")

    def test_subagent_rejects_hallucinated_write_tool(self) -> None:
        client = DelegationClient(
            [
                [
                    {
                        "type": "tool_call",
                        "id": "write-1",
                        "name": "write_file",
                        "input": {"path": "owned.txt", "content": "no"},
                    }
                ],
                [{"type": "text", "text": "The requested write is outside read-only delegation."}],
            ]
        )

        with tempfile.TemporaryDirectory(prefix="vibeagent-delegate-") as base:
            root = Path(base)
            workspace = create_run_workspace(root)
            action = parse_tool_action("delegate_task", {"task": "Inspect only", "max_iterations": 2})
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
            )
            write_result = json.loads(client.messages[1][-1].content[0]["content"])

            self.assertFalse(root.joinpath("owned.txt").exists())

        self.assertTrue(observation.ok)
        self.assertEqual(write_result["kind"], "tool_error")
        self.assertIn("not allowed", write_result["message"])

    def test_code_subagent_writes_after_parent_approval_without_recursive_tools(self) -> None:
        client = DelegationClient(
            [
                [
                    {
                        "type": "tool_call",
                        "id": "write-1",
                        "name": "write_file",
                        "input": {"path": "feature.py", "content": "enabled = True\n"},
                    }
                ],
                [{"type": "text", "text": "Implemented `feature.py` and reported the change."}],
            ]
        )

        with tempfile.TemporaryDirectory(prefix="vibeagent-delegate-") as base:
            root = Path(base)
            workspace = create_run_workspace(root)
            action = parse_tool_action(
                "delegate_task",
                {"task": "Implement the feature flag", "mode": "code", "max_iterations": 2},
            )
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
                approval_policy="ask",
            )

            self.assertEqual(root.joinpath("feature.py").read_text(encoding="utf-8"), "enabled = True\n")

        self.assertTrue(observation.ok)
        self.assertEqual(observation.mode, "code")
        self.assertIn("write_file", client.tool_names[0])
        self.assertNotIn("delegate_task", client.tool_names[0])
        self.assertNotIn("ask_user", client.tool_names[0])
        self.assertNotIn("update_plan", client.tool_names[0])
        write_result = json.loads(client.messages[1][-1].content[0]["content"])
        self.assertEqual(write_result["kind"], "write_file")

    def test_code_subagent_respects_parent_denial(self) -> None:
        client = DelegationClient(
            [
                [
                    {
                        "type": "tool_call",
                        "id": "write-1",
                        "name": "write_file",
                        "input": {"path": "denied.py", "content": "changed = True\n"},
                    }
                ],
                [{"type": "text", "text": "The requested change was denied."}],
            ]
        )

        with tempfile.TemporaryDirectory(prefix="vibeagent-delegate-") as base:
            root = Path(base)
            workspace = create_run_workspace(root)
            action = parse_tool_action("delegate_task", {"task": "Make a denied change", "mode": "code"})
            execute_delegate_task_action(
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
                approval_handler=lambda request: ApprovalDecision(approved=False, message="parent denied"),
            )

            self.assertFalse(root.joinpath("denied.py").exists())

        denied_result = json.loads(client.messages[1][-1].content[0]["content"])
        self.assertEqual(denied_result["kind"], "approval_denied")
        self.assertEqual(denied_result["message"], "parent denied")

    def test_plan_mode_rejects_code_subagent_before_model_request(self) -> None:
        client = DelegationClient([])

        with tempfile.TemporaryDirectory(prefix="vibeagent-delegate-") as base:
            workspace = create_run_workspace(Path(base))
            action = parse_tool_action("delegate_task", {"task": "Change code", "mode": "code"})
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
                approval_policy="plan",
            )

        self.assertFalse(observation.ok)
        self.assertEqual(observation.iterations, 0)
        self.assertIn("Plan mode", observation.message)
        self.assertEqual(client.messages, [])

    def test_code_subagent_rejects_hidden_recursive_delegation(self) -> None:
        client = DelegationClient(
            [
                [
                    {
                        "type": "tool_call",
                        "id": "nested-1",
                        "name": "delegate_task",
                        "input": {"task": "Start another agent", "mode": "code"},
                    }
                ],
                [{"type": "text", "text": "Recursive delegation is unavailable."}],
            ]
        )

        with tempfile.TemporaryDirectory(prefix="vibeagent-delegate-") as base:
            workspace = create_run_workspace(Path(base))
            action = parse_tool_action("delegate_task", {"task": "Do focused work", "mode": "code"})
            execute_delegate_task_action(
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
            )
            events = [
                json.loads(line)
                for line in workspace.session_dir.joinpath("events.jsonl").read_text(encoding="utf-8").splitlines()
            ]

        nested_result = json.loads(client.messages[1][-1].content[0]["content"])
        self.assertEqual(nested_result["kind"], "tool_error")
        self.assertIn("cannot ask the user", nested_result["message"])
        self.assertEqual(sum(event["type"] == "subagent_started" for event in events), 1)

    def test_parent_agent_audits_code_subagent_changes_and_uses_parent_approval(self) -> None:
        approvals: list[str] = []

        def approve(request):
            approvals.append(request.action_type)
            return ApprovalDecision(approved=True, message="parent approved")

        client = DelegationClient(
            [
                [
                    {
                        "type": "tool_call",
                        "id": "delegate-1",
                        "name": "delegate_task",
                        "input": {"task": "Create delegated.py", "mode": "code", "max_iterations": 2},
                    }
                ],
                [
                    {
                        "type": "tool_call",
                        "id": "write-1",
                        "name": "write_file",
                        "input": {"path": "delegated.py", "content": "value = 1\n"},
                    }
                ],
                [{"type": "text", "text": "Created `delegated.py`."}],
                [{"type": "text", "text": "The delegated implementation is ready for final review."}],
            ]
        )

        with tempfile.TemporaryDirectory(prefix="vibeagent-delegate-") as base:
            root = Path(base)
            result = run_agent(
                "Delegate the implementation",
                base_dir=root,
                client=client,
                max_iterations=2,
                approval_handler=approve,
            )

            self.assertEqual(root.joinpath("delegated.py").read_text(encoding="utf-8"), "value = 1\n")

        self.assertTrue(result.success)
        self.assertEqual(approvals, ["write_file"])
        self.assertIn("write_file", [observation.kind for observation in result.observations])
        delegated = next(observation for observation in result.observations if observation.kind == "delegate_task")
        self.assertEqual(delegated.mode, "code")
        self.assertIn("final_review", [observation.kind for observation in result.observations])

    def test_parent_agent_receives_subagent_summary_as_tool_result(self) -> None:
        client = DelegationClient(
            [
                [
                    {
                        "type": "tool_call",
                        "id": "delegate-1",
                        "name": "delegate_task",
                        "input": {"task": "Find authentication", "max_iterations": 2},
                    }
                ],
                [{"type": "text", "text": "Auth lives in `app.py:1`."}],
                [{"type": "text", "text": "I found the authentication entry point."}],
            ]
        )

        with tempfile.TemporaryDirectory(prefix="vibeagent-delegate-") as base:
            root = Path(base)
            root.joinpath("app.py").write_text("def authenticate():\n    pass\n", encoding="utf-8")
            result = run_agent("Locate authentication", base_dir=root, client=client, max_iterations=2)
            events = [
                json.loads(line)
                for line in (root / ".vibeagent" / "sessions" / result.run_id / "events.jsonl")
                .read_text(encoding="utf-8")
                .splitlines()
            ]

        self.assertTrue(result.success)
        self.assertTrue(result.observations[0].ok)
        self.assertIn("app.py:1", result.observations[0].summary)
        parent_result = json.loads(client.messages[2][-1].content[0]["content"])
        self.assertEqual(parent_result["kind"], "delegate_task")
        self.assertIn("app.py:1", parent_result["summary"])
        self.assertIn("delegate_task", client.tool_names[0])
        self.assertNotIn("delegate_task", client.tool_names[1])
        self.assertEqual(
            [event["type"] for event in events if event["type"].startswith("subagent_")],
            ["subagent_started", "subagent_model", "subagent_completed"],
        )

    def test_subagent_iteration_limit_returns_failed_observation(self) -> None:
        client = DelegationClient(
            [[{"type": "tool_call", "id": "read-1", "name": "list_files", "input": {}}]]
        )

        with tempfile.TemporaryDirectory(prefix="vibeagent-delegate-") as base:
            workspace = create_run_workspace(Path(base))
            action = parse_tool_action("delegate_task", {"task": "Keep looking", "max_iterations": 1})
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
            )

        self.assertFalse(observation.ok)
        self.assertEqual(observation.iterations, 1)
        self.assertIn("iteration limit", observation.message)

    def test_subagent_empty_finish_is_not_success(self) -> None:
        client = DelegationClient(
            [[{"type": "tool_call", "id": "finish-1", "name": "finish", "input": {"message": ""}}]]
        )

        with tempfile.TemporaryDirectory(prefix="vibeagent-delegate-") as base:
            workspace = create_run_workspace(Path(base))
            action = parse_tool_action("delegate_task", {"task": "Inspect"})
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
            )
            events = [
                json.loads(line)
                for line in workspace.session_dir.joinpath("events.jsonl").read_text(encoding="utf-8").splitlines()
            ]

        self.assertFalse(observation.ok)
        self.assertIn("did not include a report", observation.message)
        event_types = [event["type"] for event in events]
        self.assertLess(event_types.index("subagent_tool_result"), event_types.index("subagent_completed"))

    def test_session_timeline_formats_subagent_lifecycle(self) -> None:
        started = SessionEvent(
            line_number=1,
            type="subagent_started",
            payload={"subagent_id": "delegate-1-1", "task": "Find auth"},
        )
        completed = SessionEvent(
            line_number=2,
            type="subagent_completed",
            payload={"result": {"ok": True, "message": "done"}},
        )
        compacted = SessionEvent(
            line_number=3,
            type="subagent_context_compacted",
            payload={
                "subagent_id": "delegate-1-1",
                "mode": "code",
                "agent": "context-reader",
                "previous_messages": 14,
                "new_messages": 2,
                "previous_chars": 24000,
                "new_chars": 6000,
                "observations": 6,
                "retained_observations": 6,
                "retained_image_tool_results": 1,
                "reason": "context_limit_error",
            },
        )
        main_compacted = SessionEvent(
            line_number=4,
            type="context_compacted",
            payload={
                "previous_messages": 18,
                "new_messages": 2,
                "previous_chars": 32000,
                "new_chars": 8000,
                "observations": 8,
                "retained_observations": 8,
                "reason": "context_limit_error",
            },
        )

        self.assertIn("Find auth", format_session_event_timeline_item(started))
        self.assertIn("delegate-1-1", format_session_event_timeline_item(started))
        self.assertIn("ok=yes", format_session_event_timeline_item(completed))
        compacted_summary = format_session_event_timeline_item(compacted)
        self.assertIn("compacted delegated context", compacted_summary)
        self.assertIn("delegate-1-1", compacted_summary)
        self.assertIn("mode=code", compacted_summary)
        self.assertIn("agent=context-reader", compacted_summary)
        self.assertIn("messages=14->2", compacted_summary)
        self.assertIn("chars=24000->6000", compacted_summary)
        self.assertIn("observations=6", compacted_summary)
        self.assertIn("retained=6", compacted_summary)
        self.assertIn("images=1", compacted_summary)
        self.assertIn("reason=context_limit_error", compacted_summary)
        main_summary = format_session_event_timeline_item(main_compacted)
        self.assertIn("compacted agent context", main_summary)
        self.assertIn("messages=18->2", main_summary)
        self.assertIn("chars=32000->8000", main_summary)
        self.assertIn("reason=context_limit_error", main_summary)

    def test_main_catalog_contains_one_delegate_tool(self) -> None:
        names = [str(tool["name"]) for tool in AGENT_TOOL_DEFINITIONS]

        self.assertEqual(names.count("delegate_task"), 1)


if __name__ == "__main__":
    unittest.main()
