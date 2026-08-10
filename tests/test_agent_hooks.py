import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from vibeagent.actions import parse_tool_action
from vibeagent.agent import run_agent
from vibeagent.session_timeline_reports import format_session_event_timeline_item
from vibeagent.session_types import SessionEvent
from vibeagent.types import ApprovalDecision, AssistantResponse, ChatMessage, ContentBlock
from vibeagent.workspace import create_run_workspace
from vibeagent.workspace_hooks import matching_project_hooks, read_project_hooks


class HookClient:
    def __init__(self, responses: list[list[ContentBlock]]) -> None:
        self.responses = responses
        self.messages: list[list[ChatMessage]] = []

    def complete(self, messages, tools=None, max_tokens=4096, temperature=0.2, timeout_ms=120_000):
        self.messages.append(list(messages))
        content = self.responses[len(self.messages) - 1]
        return AssistantResponse(content=content, raw={"content": content})


def _write_hooks(root: Path, hooks: dict[str, object], *, claude: bool = False) -> Path:
    path = root / (".claude/settings.json" if claude else ".vibeagent/hooks.json")
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {"hooks": hooks} if claude else hooks
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


def _command_hook(command: str, matcher: str = ".*", timeout_ms: int = 10_000) -> dict[str, object]:
    return {
        "matcher": matcher,
        "hooks": [{"type": "command", "command": command, "timeout_ms": timeout_ms}],
    }


def _approve(_request) -> ApprovalDecision:
    return ApprovalDecision(approved=True, message="approved")


class ProjectHookConfigTests(unittest.TestCase):
    def test_cwd_changed_ignores_configured_matcher(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-hooks-") as base:
            root = Path(base)
            _write_hooks(
                root,
                {"CwdChanged": [_command_hook("python3 -V", "never-match")]},
            )
            config = read_project_hooks(create_run_workspace(root))

        cwd_hook = next(hook for hook in config.hooks if hook.event == "CwdChanged")
        self.assertEqual(cwd_hook.matcher, ".*")

    def test_loads_vibeagent_and_claude_hook_sources_with_matchers(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-hooks-") as base:
            root = Path(base)
            _write_hooks(root, {"PreToolUse": [_command_hook("python3 -V", "write_.*")]})
            _write_hooks(root, {"PostToolUse": [_command_hook("python3 -V", "read_file")]}, claude=True)
            workspace = create_run_workspace(root)

            config = read_project_hooks(workspace)

        self.assertIsNone(config.error)
        self.assertEqual(len(config.hooks), 2)
        self.assertEqual(len(matching_project_hooks(config, "PreToolUse", "write_file")), 1)
        self.assertEqual(len(matching_project_hooks(config, "PreToolUse", "read_file")), 0)
        self.assertEqual(set(config.sources), {".vibeagent/hooks.json", ".claude/settings.json"})

    def test_matchers_accept_claude_and_internal_tool_names_for_same_action(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-hooks-") as base:
            root = Path(base)
            _write_hooks(
                root,
                {
                    "PreToolUse": [
                        _command_hook("python3 -V", "Write"),
                        _command_hook("python3 -V", "write_file"),
                    ]
                },
            )
            config = read_project_hooks(create_run_workspace(root))
            write_action = parse_tool_action("Write", {"file_path": "app.py", "content": "x = 1\n"})

        self.assertEqual(len(matching_project_hooks(config, "PreToolUse", "Write", write_action)), 2)
        self.assertEqual(len(matching_project_hooks(config, "PreToolUse", "write_file", write_action)), 2)

    def test_matchers_accept_claude_mcp_alias_for_generic_mcp_call_action(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-hooks-") as base:
            root = Path(base)
            _write_hooks(
                root,
                {
                    "PreToolUse": [
                        _command_hook("python3 -V", "mcp__docs__search"),
                        _command_hook("python3 -V", "mcp_call"),
                    ]
                },
            )
            config = read_project_hooks(create_run_workspace(root))
            generic = parse_tool_action("mcp_call", {"server": "docs", "name": "search", "arguments": {"q": "api"}})
            alias = parse_tool_action("mcp__docs__search", {"q": "api"})
            other = parse_tool_action("mcp_call", {"server": "docs", "name": "lookup", "arguments": {"q": "api"}})

        self.assertEqual(len(matching_project_hooks(config, "PreToolUse", "mcp_call", generic)), 2)
        self.assertEqual(len(matching_project_hooks(config, "PreToolUse", "mcp__docs__search", alias)), 2)
        self.assertEqual(len(matching_project_hooks(config, "PreToolUse", "mcp_call", other)), 1)

    def test_invalid_matcher_and_symlink_config_are_reported(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-hooks-") as base:
            root = Path(base)
            _write_hooks(root, {"PreToolUse": [_command_hook("python3 -V", "[")]})
            workspace = create_run_workspace(root)
            invalid = read_project_hooks(workspace)

        self.assertIn("matcher is invalid", invalid.error or "")

        with tempfile.TemporaryDirectory(prefix="vibeagent-hooks-") as base:
            root = Path(base)
            external = root / "external.json"
            external.write_text("{}", encoding="utf-8")
            linked = root / ".vibeagent/hooks.json"
            linked.parent.mkdir(parents=True)
            linked.symlink_to(external)
            workspace = create_run_workspace(root)
            symlinked = read_project_hooks(workspace)

        self.assertIn("symbolic link", symlinked.error or "")


class AgentHookExecutionTests(unittest.TestCase):
    def test_sandboxed_hook_command_is_auto_approved(self) -> None:
        client = HookClient(
            [
                [{"type": "tool_call", "id": "write-1", "name": "write_file", "input": {"path": "app.py", "content": "x = 1\n"}}],
                [{"type": "text", "text": "Created app.py."}],
            ]
        )
        approvals: list[str] = []

        def approve(request):
            approvals.append(request.target)
            return ApprovalDecision(approved=True, message="approved")

        with tempfile.TemporaryDirectory(prefix="vibeagent-hooks-") as base:
            root = Path(base)
            _write_hooks(root, {"PreToolUse": [_command_hook("python3 -V", "write_file")]})
            with patch(
                "vibeagent.agent_permissions.sandbox_auto_approval_reason",
                side_effect=lambda _workspace, action: "sandboxed" if action.type == "run_command" else None,
            ):
                result = run_agent(
                    "Create app.py",
                    base_dir=root,
                    client=client,
                    max_iterations=2,
                    approval_handler=approve,
                )
            events_path = root / ".vibeagent" / "sessions" / result.run_id / "events.jsonl"
            events = [json.loads(line) for line in events_path.read_text(encoding="utf-8").splitlines()]

        self.assertTrue(result.success)
        self.assertEqual(approvals, ["app.py"])
        self.assertEqual(sum(event["type"] == "sandbox_auto_approved" for event in events), 1)

    def test_pre_and_post_hooks_run_with_context_around_approved_write(self) -> None:
        hook_command = (
            "python3 -c \"import os,pathlib; "
            "pathlib.Path('hooks.log').open('a').write(os.environ['VIBEAGENT_HOOK_EVENT'] + ':' + "
            "os.environ['VIBEAGENT_TOOL_NAME'] + '\\\\n')\""
        )
        client = HookClient(
            [
                [{"type": "tool_call", "id": "write-1", "name": "write_file", "input": {"path": "app.py", "content": "x = 1\n"}}],
                [{"type": "text", "text": "Created app.py."}],
            ]
        )
        approvals: list[str] = []

        def approve(request):
            approvals.append(request.target)
            return ApprovalDecision(approved=True, message="approved")

        with tempfile.TemporaryDirectory(prefix="vibeagent-hooks-") as base:
            root = Path(base)
            _write_hooks(
                root,
                {
                    "PreToolUse": [_command_hook(hook_command, "write_file")],
                    "PostToolUse": [_command_hook(hook_command, "write_file")],
                },
            )
            result = run_agent("Create app.py", base_dir=root, client=client, max_iterations=2, approval_handler=approve)
            hook_log = root.joinpath("hooks.log").read_text(encoding="utf-8")
            app_content = root.joinpath("app.py").read_text(encoding="utf-8")

        self.assertTrue(result.success)
        self.assertEqual(app_content, "x = 1\n")
        self.assertEqual(hook_log.splitlines(), ["PreToolUse:write_file", "PostToolUse:write_file"])
        self.assertEqual(len(approvals), 3)
        payload = json.loads(client.messages[1][-1].content[0]["content"])
        self.assertEqual([hook["status"] for hook in payload["hooks"]], ["passed", "passed"])

    def test_cwd_changed_hook_runs_in_new_directory_with_transition_input(self) -> None:
        hook_command = (
            "python3 -c \"import json,os,pathlib,sys; "
            "payload=json.load(sys.stdin); "
            "pathlib.Path('cwd-hook.json').write_text(json.dumps({"
            "'cwd': os.getcwd(), 'old': payload['old_cwd'], 'new': payload['new_cwd']}))\""
        )
        client = HookClient(
            [
                [{"type": "tool_call", "id": "bash-1", "name": "Bash", "input": {"command": "cd src"}}],
                [{"type": "text", "text": "Changed directory."}],
            ]
        )
        with tempfile.TemporaryDirectory(prefix="vibeagent-hooks-") as base:
            root = Path(base)
            (root / "src").mkdir()
            _write_hooks(root, {"CwdChanged": [_command_hook(hook_command)]})

            result = run_agent(
                "Enter src",
                base_dir=root,
                client=client,
                max_iterations=2,
                approval_handler=_approve,
            )
            payload = json.loads((root / "src" / "cwd-hook.json").read_text(encoding="utf-8"))

        self.assertTrue(result.success)
        self.assertEqual(payload["cwd"], str((root / "src").resolve()))
        self.assertEqual(payload["old"], str(root.resolve()))
        self.assertEqual(payload["new"], str((root / "src").resolve()))

    def test_internal_hook_matcher_runs_for_claude_tool_alias(self) -> None:
        hook_command = "python3 -c \"import pathlib; pathlib.Path('hooks.log').write_text('ran', encoding='utf-8')\""
        client = HookClient(
            [
                [{"type": "tool_call", "id": "write-1", "name": "Write", "input": {"file_path": "app.py", "content": "x = 1\n"}}],
                [{"type": "text", "text": "Created app.py."}],
            ]
        )
        with tempfile.TemporaryDirectory(prefix="vibeagent-hooks-") as base:
            root = Path(base)
            _write_hooks(root, {"PreToolUse": [_command_hook(hook_command, "write_file")]})
            result = run_agent("Create app.py", base_dir=root, client=client, max_iterations=2, approval_handler=_approve)

            hook_log = root.joinpath("hooks.log").read_text(encoding="utf-8")
            app_content = root.joinpath("app.py").read_text(encoding="utf-8")

        self.assertTrue(result.success)
        self.assertEqual(hook_log, "ran")
        self.assertEqual(app_content, "x = 1\n")

    def test_failing_pre_hook_blocks_target_tool(self) -> None:
        client = HookClient(
            [
                [{"type": "tool_call", "id": "write-1", "name": "write_file", "input": {"path": "blocked.py", "content": "bad = True\n"}}],
                [{"type": "text", "text": "The pre-hook blocked the write."}],
            ]
        )
        with tempfile.TemporaryDirectory(prefix="vibeagent-hooks-") as base:
            root = Path(base)
            _write_hooks(root, {"PreToolUse": [_command_hook("python3 -c \"raise SystemExit(7)\"", "write_file")]})
            result = run_agent("Write blocked.py", base_dir=root, client=client, max_iterations=2, approval_handler=_approve)

            self.assertFalse(root.joinpath("blocked.py").exists())

        self.assertEqual(result.observations[0].kind, "tool_error")
        self.assertIn("exited with code 7", result.observations[0].message)
        payload = json.loads(client.messages[1][-1].content[0]["content"])
        self.assertEqual(payload["hooks"][0]["exit_code"], 7)

    def test_denied_pre_hook_blocks_tool_after_target_approval(self) -> None:
        decisions = iter([True, False])

        def decide(_request):
            approved = next(decisions)
            return ApprovalDecision(approved=approved, message="approved" if approved else "hook denied")

        client = HookClient(
            [
                [{"type": "tool_call", "id": "write-1", "name": "write_file", "input": {"path": "denied.py", "content": "x = 1\n"}}],
                [{"type": "text", "text": "Hook approval was denied."}],
            ]
        )
        with tempfile.TemporaryDirectory(prefix="vibeagent-hooks-") as base:
            root = Path(base)
            _write_hooks(root, {"PreToolUse": [_command_hook("python3 -V", "write_file")]})
            result = run_agent("Write denied.py", base_dir=root, client=client, max_iterations=2, approval_handler=decide)

            self.assertFalse(root.joinpath("denied.py").exists())

        self.assertEqual(result.observations[0].kind, "tool_error")
        self.assertEqual(result.observations[0].message, "hook denied")

    def test_failing_post_hook_preserves_write_and_adds_completion_failure(self) -> None:
        client = HookClient(
            [
                [{"type": "tool_call", "id": "write-1", "name": "write_file", "input": {"path": "kept.py", "content": "kept = True\n"}}],
                [{"type": "text", "text": "The file was written but its post-hook failed."}],
            ]
        )
        with tempfile.TemporaryDirectory(prefix="vibeagent-hooks-") as base:
            root = Path(base)
            _write_hooks(root, {"PostToolUse": [_command_hook("python3 -c \"raise SystemExit(9)\"", "write_file")]})
            result = run_agent("Write kept.py", base_dir=root, client=client, max_iterations=2, approval_handler=_approve)

            self.assertEqual(root.joinpath("kept.py").read_text(encoding="utf-8"), "kept = True\n")

        kinds = [observation.kind for observation in result.observations]
        self.assertLess(kinds.index("write_file"), kinds.index("tool_error"))
        hook_error = next(observation for observation in result.observations if observation.kind == "tool_error")
        self.assertIn("PostToolUse", hook_error.tool)
        self.assertTrue(any("1 tool error" in blocker for blocker in result.completion_blockers))
        payload = json.loads(client.messages[1][-1].content[0]["content"])
        self.assertEqual(payload["kind"], "write_file")
        self.assertFalse(payload["hooks"][0]["ok"])

    def test_failure_hook_runs_for_failed_tool_and_plan_mode_skips_commands(self) -> None:
        marker_command = "python3 -c \"from pathlib import Path; Path('failure-hook').write_text('ran')\""
        failed_client = HookClient(
            [
                [{"type": "tool_call", "id": "read-1", "name": "read_file", "input": {"path": "missing.txt"}}],
                [{"type": "text", "text": "The read failed."}],
            ]
        )
        with tempfile.TemporaryDirectory(prefix="vibeagent-hooks-") as base:
            root = Path(base)
            _write_hooks(root, {"PostToolUseFailure": [_command_hook(marker_command, "read_file")]})
            run_agent("Read missing", base_dir=root, client=failed_client, max_iterations=2, approval_handler=_approve)
            self.assertEqual(root.joinpath("failure-hook").read_text(encoding="utf-8"), "ran")

        plan_client = HookClient(
            [
                [{"type": "tool_call", "id": "read-1", "name": "read_file", "input": {"path": "app.py"}}],
                [{"type": "text", "text": "Planned after reading app.py."}],
            ]
        )
        with tempfile.TemporaryDirectory(prefix="vibeagent-hooks-") as base:
            root = Path(base)
            root.joinpath("app.py").write_text("x = 1\n", encoding="utf-8")
            _write_hooks(root, {"PreToolUse": [_command_hook(marker_command, "read_file")]})
            result = run_agent("Plan app.py", base_dir=root, client=plan_client, max_iterations=2, approval_policy="plan")

            self.assertFalse(root.joinpath("failure-hook").exists())

        self.assertEqual(result.observations[0].kind, "read_file")
        payload = json.loads(plan_client.messages[1][-1].content[0]["content"])
        self.assertEqual(payload["hooks"][0]["status"], "skipped")

    def test_invalid_config_fails_closed_and_hard_blocked_hook_cannot_run_target(self) -> None:
        invalid_client = HookClient(
            [
                [{"type": "tool_call", "id": "read-1", "name": "read_file", "input": {"path": "app.py"}}],
                [{"type": "text", "text": "The hook configuration is invalid."}],
            ]
        )
        with tempfile.TemporaryDirectory(prefix="vibeagent-hooks-") as base:
            root = Path(base)
            root.joinpath("app.py").write_text("x = 1\n", encoding="utf-8")
            _write_hooks(root, {"PreToolUse": [_command_hook("python3 -V", "[")]})
            invalid_result = run_agent("Read app.py", base_dir=root, client=invalid_client, max_iterations=2)

        self.assertEqual(invalid_result.observations[0].kind, "tool_error")
        self.assertIn("hook configuration is invalid", invalid_result.observations[0].message)

        blocked_client = HookClient(
            [
                [{"type": "tool_call", "id": "write-1", "name": "write_file", "input": {"path": "unsafe.py", "content": "x = 1\n"}}],
                [{"type": "text", "text": "The dangerous hook was blocked."}],
            ]
        )
        with tempfile.TemporaryDirectory(prefix="vibeagent-hooks-") as base:
            root = Path(base)
            _write_hooks(root, {"PreToolUse": [_command_hook("sudo reboot", "write_file")]})
            blocked_result = run_agent(
                "Write unsafe.py",
                base_dir=root,
                client=blocked_client,
                max_iterations=2,
                approval_handler=_approve,
            )
            self.assertFalse(root.joinpath("unsafe.py").exists())

        self.assertEqual(blocked_result.observations[0].kind, "tool_error")
        hook_payload = json.loads(blocked_client.messages[1][-1].content[0]["content"])["hooks"][0]
        self.assertFalse(hook_payload["ok"])

    def test_hooks_disable_parallel_bypass_and_apply_inside_code_subagent(self) -> None:
        marker_command = "python3 -c \"from pathlib import Path; Path('hook-count').open('a').write('x')\""
        parallel_client = HookClient(
            [
                [
                    {"type": "tool_call", "id": "read-1", "name": "read_file", "input": {"path": "a.txt"}},
                    {"type": "tool_call", "id": "read-2", "name": "read_file", "input": {"path": "b.txt"}},
                ],
                [{"type": "text", "text": "Read both files through hooks."}],
            ]
        )
        with tempfile.TemporaryDirectory(prefix="vibeagent-hooks-") as base:
            root = Path(base)
            root.joinpath("a.txt").write_text("a", encoding="utf-8")
            root.joinpath("b.txt").write_text("b", encoding="utf-8")
            _write_hooks(root, {"PreToolUse": [_command_hook(marker_command, "read_file")]})
            result = run_agent("Read both", base_dir=root, client=parallel_client, max_iterations=2, approval_handler=_approve)
            marker = root.joinpath("hook-count").read_text(encoding="utf-8")

        self.assertEqual(marker, "xx")
        self.assertEqual([observation.kind for observation in result.observations[:2]], ["read_file", "read_file"])

        delegate_client = HookClient(
            [
                [
                    {
                        "type": "tool_call",
                        "id": "delegate-1",
                        "name": "delegate_task",
                        "input": {"task": "Create child.py", "mode": "code", "max_iterations": 2},
                    }
                ],
                [{"type": "tool_call", "id": "write-1", "name": "write_file", "input": {"path": "child.py", "content": "child = True\n"}}],
                [{"type": "text", "text": "Created child.py."}],
                [{"type": "text", "text": "Delegated change complete."}],
            ]
        )
        with tempfile.TemporaryDirectory(prefix="vibeagent-hooks-") as base:
            root = Path(base)
            _write_hooks(root, {"PreToolUse": [_command_hook(marker_command, "write_file")]})
            run_agent("Delegate write", base_dir=root, client=delegate_client, max_iterations=2, approval_handler=_approve)
            child_content = root.joinpath("child.py").read_text(encoding="utf-8")
            child_hook_marker = root.joinpath("hook-count").read_text(encoding="utf-8")

        self.assertEqual(child_content, "child = True\n")
        self.assertEqual(child_hook_marker, "x")

    def test_hooks_wrap_parent_delegate_tool(self) -> None:
        marker_command = (
            "python3 -c \"import os; from pathlib import Path; "
            "Path('delegate-hooks').open('a').write(os.environ['VIBEAGENT_HOOK_EVENT'] + '\\\\n')\""
        )
        client = HookClient(
            [
                [
                    {
                        "type": "tool_call",
                        "id": "delegate-1",
                        "name": "delegate_task",
                        "input": {"task": "Inspect the project", "mode": "explore", "max_iterations": 1},
                    }
                ],
                [{"type": "text", "text": "The project contains a Python package."}],
                [{"type": "text", "text": "Delegated inspection complete."}],
            ]
        )
        with tempfile.TemporaryDirectory(prefix="vibeagent-hooks-") as base:
            root = Path(base)
            _write_hooks(
                root,
                {
                    "PreToolUse": [_command_hook(marker_command, "delegate_task")],
                    "PostToolUse": [_command_hook(marker_command, "delegate_task")],
                },
            )
            result = run_agent("Inspect via delegate", base_dir=root, client=client, max_iterations=2, approval_handler=_approve)
            events = root.joinpath("delegate-hooks").read_text(encoding="utf-8").splitlines()

        self.assertTrue(result.success)
        self.assertEqual(events, ["PreToolUse", "PostToolUse"])
        payload = json.loads(client.messages[2][-1].content[0]["content"])
        self.assertEqual([hook["status"] for hook in payload["hooks"]], ["passed", "passed"])

    def test_session_timeline_formats_hook_lifecycle(self) -> None:
        loaded = SessionEvent(
            line_number=1,
            type="hooks_loaded",
            payload={"sources": [".vibeagent/hooks.json"], "count": 2, "error": None},
        )
        completed = SessionEvent(
            line_number=2,
            type="hook_completed",
            payload={
                "event": "PreToolUse",
                "tool": "write_file",
                "source": ".vibeagent/hooks.json",
                "result": {"status": "passed", "message": "PreToolUse hook exited with code 0."},
            },
        )

        self.assertIn("count=2", format_session_event_timeline_item(loaded))
        summary = format_session_event_timeline_item(completed)
        self.assertIn("PreToolUse write_file", summary)
        self.assertIn("status=passed", summary)


if __name__ == "__main__":
    unittest.main()
