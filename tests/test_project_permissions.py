from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from vibeagent.actions import parse_tool_action
from vibeagent.agent import run_agent
from vibeagent.agent_delegate_tools import execute_delegate_tool_call
from vibeagent.cli_args import parse_args
from vibeagent.prompts import build_messages
from vibeagent.session_timeline_reports import format_session_event_timeline_item
from vibeagent.session_types import SessionEvent
from vibeagent.tool_catalog import format_permissions_report_text, get_permissions_report
from vibeagent.types import ApprovalDecision, AssistantResponse, ChatMessage, ContentBlock
from vibeagent.workspace import create_run_workspace
from vibeagent.workspace_permissions import match_project_permission, read_project_permissions


class PermissionClient:
    def __init__(self, responses: list[list[ContentBlock]]) -> None:
        self.responses = responses
        self.messages: list[list[ChatMessage]] = []

    def complete(self, messages, tools=None, max_tokens=4096, temperature=0.2, timeout_ms=120_000):
        self.messages.append(list(messages))
        content = self.responses[len(self.messages) - 1]
        return AssistantResponse(content=content, raw={"content": content})


def _write_permissions(
    root: Path,
    permissions: dict[str, object],
    *,
    source: str = ".vibeagent/permissions.json",
) -> Path:
    path = root / source
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {"permissions": permissions} if source.startswith(".claude/") else permissions
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


class ProjectPermissionConfigTests(unittest.TestCase):
    def test_cli_requires_explicit_flag_to_trust_allow_rules(self) -> None:
        default = parse_args(["inspect"])
        trusted = parse_args(["--trust-project-permissions", "inspect"])

        self.assertFalse(default.trust_project_permissions)
        self.assertTrue(trusted.trust_project_permissions)

    def test_loads_all_sources_and_uses_deny_ask_allow_precedence(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-permissions-") as base:
            root = Path(base)
            _write_permissions(root, {"allow": ["Bash(npm test *)"]}, source=".claude/settings.json")
            _write_permissions(root, {"ask": ["Bash(npm *)"]}, source=".claude/settings.local.json")
            _write_permissions(root, {"deny": ["Bash(npm publish *)"]})
            config = read_project_permissions(create_run_workspace(root))
            test_action = parse_tool_action("run_command", {"command": "npm test -- --runInBand"})
            exact_test_action = parse_tool_action("run_command", {"command": "npm test"})
            publish_action = parse_tool_action("run_command", {"command": "npm publish --access public"})

        self.assertIsNone(config.error)
        self.assertEqual(len(config.rules), 3)
        self.assertEqual(match_project_permission(config, "run_command", test_action).effect, "ask")
        self.assertEqual(match_project_permission(config, "run_command", exact_test_action).effect, "ask")
        self.assertEqual(match_project_permission(config, "run_command", publish_action).effect, "deny")

    def test_matches_claude_path_aliases_and_requires_all_allow_subjects(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-permissions-") as base:
            root = Path(base)
            _write_permissions(
                root,
                {
                    "deny": ["Read(**/.env)"],
                    "allow": ["Edit(src/**)"],
                },
            )
            config = read_project_permissions(create_run_workspace(root))
            root_secret = parse_tool_action("read_file", {"path": ".env"})
            nested_secret = parse_tool_action("read_file", {"path": "apps/api/.env"})
            allowed_writes = parse_tool_action(
                "write_files",
                {"files": [{"path": "src/a.py", "content": "a"}, {"path": "src/b.py", "content": "b"}]},
            )
            mixed_writes = parse_tool_action(
                "write_files",
                {"files": [{"path": "src/a.py", "content": "a"}, {"path": "docs/b.md", "content": "b"}]},
            )

        self.assertEqual(match_project_permission(config, "read_file", root_secret).effect, "deny")
        self.assertEqual(match_project_permission(config, "read_file", nested_secret).effect, "deny")
        self.assertEqual(match_project_permission(config, "write_files", allowed_writes).effect, "allow")
        self.assertIsNone(match_project_permission(config, "write_files", mixed_writes))

    def test_invalid_and_symlinked_configs_fail_closed(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-permissions-") as base:
            root = Path(base)
            _write_permissions(root, {"deny": ["Read("]})
            invalid = read_project_permissions(create_run_workspace(root))

        self.assertIn("rule is invalid", invalid.error or "")

        with tempfile.TemporaryDirectory(prefix="vibeagent-permissions-") as base:
            root = Path(base)
            external = root / "external.json"
            external.write_text("{}", encoding="utf-8")
            linked = root / ".claude/settings.json"
            linked.parent.mkdir(parents=True)
            linked.symlink_to(external)
            symlinked = read_project_permissions(create_run_workspace(root))

        self.assertIn("symbolic link", symlinked.error or "")


class ProjectPermissionExecutionTests(unittest.TestCase):
    def test_deny_rule_blocks_read_only_tool_without_prompt(self) -> None:
        client = PermissionClient(
            [
                [{"type": "tool_call", "id": "read-1", "name": "read_file", "input": {"path": ".env"}}],
                [{"type": "text", "text": "The project rule denied the read."}],
            ]
        )
        with tempfile.TemporaryDirectory(prefix="vibeagent-permissions-") as base:
            root = Path(base)
            root.joinpath(".env").write_text("SECRET=value\n", encoding="utf-8")
            _write_permissions(root, {"deny": ["Read(**/.env)"]})
            result = run_agent("Read .env", base_dir=root, client=client, max_iterations=2)

        self.assertEqual(result.observations[0].kind, "approval_denied")
        self.assertIn("Read(**/.env)", result.observations[0].message)

    def test_allow_rule_skips_prompt_but_session_deny_still_wins(self) -> None:
        untrusted_client = PermissionClient(
            [
                [{"type": "tool_call", "id": "write-1", "name": "write_file", "input": {"path": "src/app.py", "content": "x = 0\n"}}],
                [{"type": "text", "text": "Created src/app.py after approval."}],
            ]
        )
        untrusted_approvals: list[str] = []

        def approve_untrusted(request):
            untrusted_approvals.append(request.target)
            return ApprovalDecision(approved=True, message="approved")

        with tempfile.TemporaryDirectory(prefix="vibeagent-permissions-") as base:
            root = Path(base)
            _write_permissions(root, {"allow": ["Edit(src/**)"]})
            run_agent(
                "Write app",
                base_dir=root,
                client=untrusted_client,
                max_iterations=2,
                approval_handler=approve_untrusted,
            )

        self.assertEqual(untrusted_approvals, ["src/app.py"])

        allowed_client = PermissionClient(
            [
                [{"type": "tool_call", "id": "write-1", "name": "write_file", "input": {"path": "src/app.py", "content": "x = 1\n"}}],
                [{"type": "text", "text": "Created src/app.py."}],
            ]
        )
        with tempfile.TemporaryDirectory(prefix="vibeagent-permissions-") as base:
            root = Path(base)
            _write_permissions(root, {"allow": ["Edit(src/**)"]})
            allowed = run_agent(
                "Write app",
                base_dir=root,
                client=allowed_client,
                max_iterations=2,
                trust_project_permissions=True,
            )
            content = root.joinpath("src/app.py").read_text(encoding="utf-8")

        self.assertEqual(content, "x = 1\n")
        self.assertEqual(allowed.observations[0].kind, "write_file")

        denied_client = PermissionClient(
            [
                [{"type": "tool_call", "id": "write-1", "name": "write_file", "input": {"path": "src/app.py", "content": "x = 2\n"}}],
                [{"type": "text", "text": "Session policy denied the write."}],
            ]
        )
        with tempfile.TemporaryDirectory(prefix="vibeagent-permissions-") as base:
            root = Path(base)
            _write_permissions(root, {"allow": ["Edit(src/**)"]})
            denied = run_agent(
                "Write app",
                base_dir=root,
                client=denied_client,
                max_iterations=2,
                approval_policy="deny",
            )

        self.assertEqual(denied.observations[0].kind, "approval_denied")
        self.assertIn("session policy", denied.observations[0].message)

    def test_ask_rule_prompts_for_read_only_tools_and_disables_parallel_bypass(self) -> None:
        client = PermissionClient(
            [
                [
                    {"type": "tool_call", "id": "read-1", "name": "read_file", "input": {"path": "a.txt"}},
                    {"type": "tool_call", "id": "read-2", "name": "read_file", "input": {"path": "b.txt"}},
                ],
                [{"type": "text", "text": "Read both approved files."}],
            ]
        )
        approvals: list[str] = []

        def approve(request):
            approvals.append(request.target)
            return ApprovalDecision(approved=True, message="approved")

        with tempfile.TemporaryDirectory(prefix="vibeagent-permissions-") as base:
            root = Path(base)
            root.joinpath("a.txt").write_text("a", encoding="utf-8")
            root.joinpath("b.txt").write_text("b", encoding="utf-8")
            _write_permissions(root, {"ask": ["Read"]})
            result = run_agent("Read both", base_dir=root, client=client, max_iterations=2, approval_handler=approve)

        self.assertEqual(approvals, ["a.txt", "b.txt"])
        self.assertEqual([item.kind for item in result.observations[:2]], ["read_file", "read_file"])

    def test_invalid_config_and_bash_deny_rule_block_execution_and_hooks(self) -> None:
        invalid_client = PermissionClient(
            [
                [{"type": "tool_call", "id": "read-1", "name": "read_file", "input": {"path": "a.txt"}}],
                [{"type": "text", "text": "Invalid permissions blocked the tool."}],
            ]
        )
        with tempfile.TemporaryDirectory(prefix="vibeagent-permissions-") as base:
            root = Path(base)
            root.joinpath("a.txt").write_text("a", encoding="utf-8")
            _write_permissions(root, {"deny": "Read"})
            invalid = run_agent("Read a", base_dir=root, client=invalid_client, max_iterations=2)

        self.assertEqual(invalid.observations[0].kind, "approval_denied")
        self.assertIn("configuration is invalid", invalid.observations[0].message)

        hook_client = PermissionClient(
            [
                [{"type": "tool_call", "id": "write-1", "name": "write_file", "input": {"path": "app.py", "content": "x = 1\n"}}],
                [{"type": "text", "text": "The denied hook blocked the write."}],
            ]
        )
        with tempfile.TemporaryDirectory(prefix="vibeagent-permissions-") as base:
            root = Path(base)
            _write_permissions(root, {"deny": ["Bash(python3 *)"], "allow": ["write_file"]})
            hook_path = root / ".vibeagent/hooks.json"
            hook_path.write_text(
                json.dumps(
                    {
                        "PreToolUse": [
                            {
                                "matcher": "write_file",
                                "hooks": [{"type": "command", "command": "python3 -V"}],
                            }
                        ]
                    }
                ),
                encoding="utf-8",
            )
            hook_result = run_agent(
                "Write app",
                base_dir=root,
                client=hook_client,
                max_iterations=2,
                trust_project_permissions=True,
            )
            exists = root.joinpath("app.py").exists()

        self.assertFalse(exists)
        self.assertEqual(hook_result.observations[0].kind, "tool_error")
        self.assertIn("Bash(python3 *)", hook_result.observations[0].message)

    def test_trusted_allow_rule_cannot_bypass_command_hard_blocks(self) -> None:
        client = PermissionClient(
            [
                [{"type": "tool_call", "id": "command-1", "name": "run_command", "input": {"command": "sudo reboot"}}],
                [{"type": "text", "text": "The command hard block rejected sudo."}],
            ]
        )
        with tempfile.TemporaryDirectory(prefix="vibeagent-permissions-") as base:
            root = Path(base)
            _write_permissions(root, {"allow": ["Bash(sudo *)"]})
            result = run_agent(
                "Run sudo",
                base_dir=root,
                client=client,
                max_iterations=2,
                trust_project_permissions=True,
            )

        self.assertEqual(result.observations[0].kind, "run_command")
        self.assertIsNone(result.observations[0].result.exit_code)
        self.assertIn("Command blocked", result.observations[0].result.stderr)

    def test_explore_subagent_obeys_read_deny_rule(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-permissions-") as base:
            root = Path(base)
            root.joinpath("secret.txt").write_text("secret", encoding="utf-8")
            _write_permissions(root, {"deny": ["Read(secret.txt)"]})
            workspace = create_run_workspace(root)
            permissions = read_project_permissions(workspace)
            execution = execute_delegate_tool_call(
                workspace,
                mode="explore",
                tool_name="read_file",
                tool_input={"path": "secret.txt"},
                active_tool_names=set(),
                observations=[],
                steps=[],
                iteration=1,
                command_timeout_ms=10_000,
                logger=None,
                approval_handler=None,
                approval_policy="ask",
                auto_checkpoint_attempted=False,
                permissions=permissions,
            )

        self.assertIsNotNone(execution.observation)
        self.assertEqual(execution.observation.kind, "approval_denied")

    def test_permissions_report_prompt_and_timeline_expose_rule_source(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-permissions-") as base:
            root = Path(base)
            _write_permissions(root, {"deny": ["Bash(git push *)"], "allow": ["Edit(src/**)"]})
            report = get_permissions_report("ask", root)
            text = format_permissions_report_text(report)
            prompt = "\n".join(
                str(message.content)
                for message in build_messages("Inspect permissions", create_run_workspace(root))
            )

        project = report["projectPermissions"]
        self.assertEqual(project["count"], 2)
        self.assertIn(".vibeagent/permissions.json", project["sources"])
        self.assertTrue(project["allowRulesRequireExplicitTrust"])
        self.assertIn("deny: Bash(git push *)", text)
        self.assertIn("allow: Edit(src/**)", prompt)

        loaded = SessionEvent(
            line_number=1,
            type="permissions_loaded",
            payload={"sources": [".vibeagent/permissions.json"], "count": 2, "error": None},
        )
        evaluated = SessionEvent(
            line_number=2,
            type="permission_rule_evaluated",
            payload={
                "tool": "run_command",
                "effect": "deny",
                "rule": "Bash(git push *)",
                "source": ".vibeagent/permissions.json",
            },
        )
        self.assertIn("count=2", format_session_event_timeline_item(loaded))
        summary = format_session_event_timeline_item(evaluated)
        self.assertIn("deny run_command", summary)
        self.assertIn("Bash(git push *)", summary)


if __name__ == "__main__":
    unittest.main()
