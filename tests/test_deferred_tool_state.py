from __future__ import annotations

import json
import os
import shlex
import tempfile
import unittest
from pathlib import Path

from vibeagent.agent import run_agent
from vibeagent.agent_result import AgentResult
from vibeagent.cli_result_payloads import (
    build_code_result_payload,
    code_result_exit_code,
    code_result_stop_reason,
)
from vibeagent.cli_one_shot_output import one_shot_code_exit_code
from vibeagent.deferred_tool_state import (
    DeferredToolState,
    clear_deferred_tool_state,
    read_deferred_tool_state,
    write_deferred_tool_state,
)
from vibeagent.session_conversation import read_session_conversation
from vibeagent.types import ApprovalDecision, AssistantResponse, ChatMessage, ContentBlock
from vibeagent.workspace import create_run_workspace


class DeferredClient:
    def __init__(self, responses: list[list[ContentBlock]]) -> None:
        self.responses = responses
        self.messages: list[list[ChatMessage]] = []

    def complete(self, messages, tools=None, max_tokens=4096, temperature=0.2, timeout_ms=120_000):
        self.messages.append(list(messages))
        content = self.responses[len(self.messages) - 1]
        return AssistantResponse(content=content, raw={"content": content})


class PriorContext:
    def to_json(self) -> None:
        return None


def _approve(_request) -> ApprovalDecision:
    return ApprovalDecision(approved=True, message="approved")


def _hook_command(payload: dict[str, object]) -> str:
    code = f"import json; print(json.dumps({payload!r}))"
    return f"python3 -c {shlex.quote(code)}"


def _write_hook(root: Path, decision: str, matcher: str = "write_file") -> None:
    _write_hook_payload(
        root,
        {
            "hookSpecificOutput": {
                "hookEventName": "PreToolUse",
                "permissionDecision": decision,
            }
        },
        matcher,
    )


def _write_hook_payload(
    root: Path,
    payload: dict[str, object],
    matcher: str,
) -> None:
    path = root / ".vibeagent/hooks.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(
            {
                "PreToolUse": [
                    {
                        "matcher": matcher,
                        "hooks": [
                            {
                                "type": "command",
                                "command": _hook_command(payload),
                            }
                        ],
                    }
                ]
            }
        ),
        encoding="utf-8",
    )


def _write_call(path: str = "later.py") -> ContentBlock:
    return {
        "type": "tool_call",
        "id": "write-1",
        "name": "write_file",
        "input": {"path": path, "content": "value = 'original'\n"},
    }


class DeferredToolStateTests(unittest.TestCase):
    def test_tool_hook_receives_provider_tool_use_id(self) -> None:
        payload = {
            "hookSpecificOutput": {
                "hookEventName": "PreToolUse",
                "permissionDecision": "defer",
            }
        }
        code = (
            "import json,pathlib,sys; data=json.load(sys.stdin); "
            "pathlib.Path('hook-tool-id').write_text(data['tool_use_id']); "
            f"print(json.dumps({payload!r}))"
        )
        command = f"python3 -c {shlex.quote(code)}"
        with tempfile.TemporaryDirectory(prefix="vibeagent-deferred-") as base:
            root = Path(base)
            hooks_path = root / ".vibeagent/hooks.json"
            hooks_path.parent.mkdir(parents=True)
            hooks_path.write_text(
                json.dumps(
                    {
                        "PreToolUse": [
                            {
                                "matcher": "write_file",
                                "hooks": [{"type": "command", "command": command}],
                            }
                        ]
                    }
                ),
                encoding="utf-8",
            )
            run_agent(
                "Write later.py",
                base_dir=root,
                client=DeferredClient([[_write_call()]]),
                max_iterations=1,
                approval_handler=_approve,
                defer_tool_calls=True,
            )

            self.assertEqual((root / "hook-tool-id").read_text(encoding="utf-8"), "write-1")

    def test_state_is_private_exact_and_model_payload_is_sanitized(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-deferred-") as base:
            workspace = create_run_workspace(Path(base), run_id="run-1")
            state = DeferredToolState((_write_call(),), (), 0)

            write_deferred_tool_state(workspace, state)
            restored = read_deferred_tool_state(workspace)
            path = workspace.session_dir / "deferred_tool_use.json"

            self.assertEqual(os.stat(path).st_mode & 0o777, 0o600)
            self.assertIsNotNone(restored)
            assert restored is not None
            self.assertEqual(
                restored.tool_calls[0]["input"]["content"],
                "value = 'original'\n",
            )
            self.assertEqual(
                restored.pending_tool_use["input"]["content"],
                {"redacted": True, "type": "string", "chars": 19, "lines": 1},
            )

            clear_deferred_tool_state(workspace)
            self.assertIsNone(read_deferred_tool_state(workspace))

    def test_agent_defers_without_tool_result_and_resumes_same_call(self) -> None:
        first_client = DeferredClient([[_write_call()]])
        with tempfile.TemporaryDirectory(prefix="vibeagent-deferred-") as base:
            root = Path(base)
            _write_hook(root, "defer")
            first = run_agent(
                "Write later.py",
                base_dir=root,
                client=first_client,
                max_iterations=2,
                approval_handler=_approve,
                defer_tool_calls=True,
            )
            workspace = create_run_workspace(root, run_id=first.run_id)
            state = read_deferred_tool_state(workspace)
            persisted = read_session_conversation(root, first.run_id)

            self.assertFalse((root / "later.py").exists())
            self.assertEqual(first.stop_reason, "tool_deferred")
            self.assertTrue(first.success)
            self.assertEqual(first.status, "deferred")
            self.assertEqual(first.observations, [])
            self.assertIsNotNone(state)
            self.assertFalse(
                any(
                    isinstance(message.content, list)
                    and any(block.get("type") == "tool_result" for block in message.content)
                    for message in persisted
                )
            )

            _write_hook(root, "allow")
            resumed_client = DeferredClient(
                [[{"type": "text", "text": "Deferred write completed."}]]
            )
            resumed = run_agent(
                "Continue the deferred call",
                workspace=workspace,
                client=resumed_client,
                max_iterations=2,
                approval_handler=_approve,
                prior_messages=persisted,
                deferred_tool_state=state,
                defer_tool_calls=True,
            )

            self.assertEqual(
                (root / "later.py").read_text(encoding="utf-8"),
                "value = 'original'\n",
            )
            self.assertIsNone(read_deferred_tool_state(workspace))

        sent = resumed_client.messages[0]
        assistant_call = next(
            message
            for message in sent
            if message.role == "assistant" and isinstance(message.content, list)
        )
        self.assertEqual(assistant_call.content[0]["id"], "write-1")
        self.assertTrue(
            any(
                message.role == "user"
                and isinstance(message.content, list)
                and message.content[0].get("tool_call_id") == "write-1"
                for message in sent
            )
        )
        self.assertIsNone(resumed.stop_reason)

    def test_deferred_question_resumes_with_hook_supplied_answer(self) -> None:
        question = {
            "question": "Which framework?",
            "header": "Framework",
            "options": [
                {"label": "React", "description": "Use React."},
                {"label": "Vue", "description": "Use Vue."},
            ],
            "multiSelect": False,
        }
        call: ContentBlock = {
            "type": "tool_call",
            "id": "ask-1",
            "name": "AskUserQuestion",
            "input": {"questions": [question]},
        }
        with tempfile.TemporaryDirectory(prefix="vibeagent-deferred-") as base:
            root = Path(base)
            _write_hook(root, "defer", "AskUserQuestion")
            first = run_agent(
                "Choose framework",
                base_dir=root,
                client=DeferredClient([[call]]),
                max_iterations=1,
                approval_handler=_approve,
                defer_tool_calls=True,
            )
            workspace = create_run_workspace(root, run_id=first.run_id)
            state = read_deferred_tool_state(workspace)
            assert state is not None
            self.assertEqual(
                state.pending_tool_use["input"]["questions"][0]["question"],
                "Which framework?",
            )

            _write_hook_payload(
                root,
                {
                    "hookSpecificOutput": {
                        "hookEventName": "PreToolUse",
                        "permissionDecision": "allow",
                        "updatedInput": {
                            "questions": [question],
                            "answers": {"Which framework?": "React"},
                        },
                    }
                },
                "AskUserQuestion",
            )
            resumed = run_agent(
                "Continue with answer",
                workspace=workspace,
                client=DeferredClient(
                    [[{"type": "text", "text": "Selected React."}]]
                ),
                max_iterations=1,
                approval_handler=_approve,
                user_input_handler=None,
                prior_messages=read_session_conversation(root, first.run_id),
                deferred_tool_state=state,
                defer_tool_calls=True,
            )

        answer = next(item for item in resumed.observations if item.kind == "ask_user")
        self.assertFalse(answer.cancelled)
        self.assertEqual(answer.answer, "React")

    def test_resume_reports_unavailable_before_hook_runs(self) -> None:
        first_client = DeferredClient([[_write_call()]])
        with tempfile.TemporaryDirectory(prefix="vibeagent-deferred-") as base:
            root = Path(base)
            _write_hook(root, "defer")
            first = run_agent(
                "Write later.py",
                base_dir=root,
                client=first_client,
                max_iterations=1,
                approval_handler=_approve,
                defer_tool_calls=True,
            )
            workspace = create_run_workspace(root, run_id=first.run_id)
            state = read_deferred_tool_state(workspace)
            assert state is not None
            _write_hook(root, "allow")

            unavailable = run_agent(
                "Continue without Write",
                workspace=workspace,
                client=DeferredClient([]),
                max_iterations=1,
                approval_handler=_approve,
                tool_names=frozenset({"Read"}),
                deferred_tool_state=state,
                defer_tool_calls=True,
            )

            self.assertEqual(unavailable.stop_reason, "tool_deferred_unavailable")
            self.assertFalse(unavailable.success)
            self.assertTrue(unavailable.is_error)
            self.assertIsNotNone(read_deferred_tool_state(workspace))

    def test_resume_preserves_completed_results_in_a_deferred_batch(self) -> None:
        first_client = DeferredClient(
            [
                [
                    {
                        "type": "tool_call",
                        "id": "read-1",
                        "name": "read_file",
                        "input": {"path": "source.txt"},
                    },
                    _write_call(),
                ]
            ]
        )
        with tempfile.TemporaryDirectory(prefix="vibeagent-deferred-") as base:
            root = Path(base)
            (root / "source.txt").write_text("before\n", encoding="utf-8")
            _write_hook(root, "defer")
            first = run_agent(
                "Read then write",
                base_dir=root,
                client=first_client,
                max_iterations=1,
                approval_handler=_approve,
                defer_tool_calls=True,
            )
            workspace = create_run_workspace(root, run_id=first.run_id)
            state = read_deferred_tool_state(workspace)
            assert state is not None
            self.assertEqual(state.next_tool_index, 1)
            self.assertEqual(len(state.completed_tool_results), 1)
            self.assertEqual([item.kind for item in first.observations], ["read_file"])

            (root / "source.txt").write_text("after\n", encoding="utf-8")
            _write_hook(root, "allow")
            resumed_client = DeferredClient(
                [[{"type": "text", "text": "Batch completed."}]]
            )
            run_agent(
                "Continue batch",
                workspace=workspace,
                client=resumed_client,
                max_iterations=1,
                approval_handler=_approve,
                prior_messages=read_session_conversation(root, first.run_id),
                deferred_tool_state=state,
                defer_tool_calls=True,
            )
            events = [
                json.loads(line)
                for line in (workspace.session_dir / "events.jsonl")
                .read_text(encoding="utf-8")
                .splitlines()
            ]

        read_calls = [
            event
            for event in events
            if event["type"] == "tool_call" and event["name"] == "read_file"
        ]
        self.assertEqual(len(read_calls), 1)
        result_message = next(
            message
            for message in resumed_client.messages[0]
            if message.role == "user" and isinstance(message.content, list)
        )
        self.assertEqual(
            [block["tool_call_id"] for block in result_message.content],
            ["read-1", "write-1"],
        )

    def test_machine_payload_exposes_deferred_contract(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-deferred-") as base:
            result = AgentResult(
                success=True,
                message="Tool call deferred: Write.",
                run_dir=Path(base),
                run_id="run-1",
                iterations=1,
                observations=[],
                steps=[],
                status="deferred",
                completion_ready=False,
                stop_reason="tool_deferred",
                deferred_tool_use={"id": "write-1", "name": "Write", "input": {}},
            )
            payload = build_code_result_payload(result, PriorContext())

        self.assertEqual(code_result_stop_reason(result), "tool_deferred")
        self.assertEqual(code_result_exit_code(result), 0)
        self.assertEqual(one_shot_code_exit_code(result), 0)
        self.assertEqual(payload["stopReason"], "tool_deferred")
        self.assertEqual(payload["deferred_tool_use"]["id"], "write-1")
        self.assertEqual(payload["subtype"], "success")
        self.assertFalse(payload["is_error"])


if __name__ == "__main__":
    unittest.main()
