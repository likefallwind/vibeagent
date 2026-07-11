from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from vibeagent.actions import parse_tool_action
from vibeagent.action_tool_aliases import CLAUDE_TOOL_ACTION_ALIASES, CLAUDE_TOOL_ALIASES
from vibeagent.agent import run_agent
from vibeagent.agent_delegate_tools import execute_delegate_tool_call
from vibeagent.cli_args import parse_args
from vibeagent.cli_permission_overrides import (
    ALLOWED_TOOLS_SOURCE,
    DISALLOWED_TOOLS_SOURCE,
    build_permission_overrides,
)
from vibeagent.prompts import build_messages
from vibeagent.session_timeline_reports import format_session_event_timeline_item
from vibeagent.session_types import SessionEvent
from vibeagent.tool_catalog import format_permissions_report_text, get_permissions_report
from vibeagent.types import ApprovalDecision, AssistantResponse, ChatMessage, ContentBlock
from vibeagent.workspace import create_run_workspace
from vibeagent.workspace_permissions import (
    match_project_permission,
    merge_project_permissions,
    read_project_permissions,
)


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
    def test_claude_action_aliases_are_permission_rule_aliases(self) -> None:
        self.assertLessEqual(set(CLAUDE_TOOL_ACTION_ALIASES), set(CLAUDE_TOOL_ALIASES))

    def test_cli_requires_explicit_flag_to_trust_allow_rules(self) -> None:
        default = parse_args(["inspect"])
        trusted = parse_args(["--trust-project-permissions", "inspect"])
        allowed = parse_args(["--allowedTools", "Read", "--allowed-tools", "Bash(git diff:*)", "inspect"])
        disallowed = parse_args(["--disallowedTools", "Edit(src/**)", "inspect"])

        self.assertFalse(default.trust_project_permissions)
        self.assertTrue(trusted.trust_project_permissions)
        self.assertEqual(allowed.allowed_tools, ["Read", "Bash(git diff:*)"])
        self.assertEqual(disallowed.disallowed_tools, ["Edit(src/**)"])

    def test_cli_permission_overrides_merge_as_trusted_allow_source(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-permissions-") as base:
            root = Path(base)
            _write_permissions(root, {"allow": ["Edit(src/**)"]})
            workspace = create_run_workspace(root)
            overrides = build_permission_overrides(
                parse_args(
                    [
                        "--allowed-tools",
                        "Read,Bash(git diff:*)",
                        "--disallowed-tools",
                        "Edit(src/**)",
                        "inspect",
                    ]
                )
            )
            merged = merge_project_permissions(read_project_permissions(workspace), overrides)

            read_action = parse_tool_action("read_file", {"path": "README.md"})
            write_action = parse_tool_action("write_file", {"path": "src/app.py", "content": "x = 1\n"})

        self.assertEqual([rule.raw for rule in overrides.rules], ["Read", "Bash(git diff:*)", "Edit(src/**)"])
        self.assertIn(ALLOWED_TOOLS_SOURCE, merged.sources)
        self.assertIn(DISALLOWED_TOOLS_SOURCE, merged.sources)
        self.assertEqual(merged.trusted_allow_sources, (ALLOWED_TOOLS_SOURCE,))
        self.assertEqual(match_project_permission(merged, "read_file", read_action).effect, "allow")
        self.assertEqual(match_project_permission(merged, "write_file", write_action).effect, "deny")

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
                    "allow": ["Edit(src/**)", "read_file(docs/*)"],
                },
            )
            config = read_project_permissions(create_run_workspace(root))
            root_secret = parse_tool_action("read_file", {"path": ".env"})
            nested_secret = parse_tool_action("read_file", {"path": "apps/api/.env"})
            shallow_doc = parse_tool_action("read_file", {"path": "docs/guide.md"})
            nested_doc = parse_tool_action("read_file", {"path": "docs/archive/guide.md"})
            allowed_writes = parse_tool_action(
                "write_files",
                {"files": [{"path": "src/a.py", "content": "a"}, {"path": "src/b.py", "content": "b"}]},
            )
            mixed_writes = parse_tool_action(
                "write_files",
                {"files": [{"path": "src/a.py", "content": "a"}, {"path": "docs/b.md", "content": "b"}]},
            )

        self.assertEqual(match_project_permission(config, "Read", root_secret).effect, "deny")
        self.assertEqual(match_project_permission(config, "Read", nested_secret).effect, "deny")
        self.assertEqual(match_project_permission(config, "read_file", shallow_doc).effect, "allow")
        self.assertIsNone(match_project_permission(config, "read_file", nested_doc))
        self.assertEqual(match_project_permission(config, "write_files", allowed_writes).effect, "allow")
        self.assertIsNone(match_project_permission(config, "write_files", mixed_writes))

    def test_matches_claude_notebook_aliases_to_file_tools(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-permissions-") as base:
            root = Path(base)
            _write_permissions(
                root,
                {
                    "deny": ["NotebookRead(secrets/**)"],
                    "allow": ["NotebookEdit(notebooks/**)"],
                },
            )
            _write_permissions(root, {"allow": ["NotebookEdit(shallow/*)"]}, source=".claude/settings.local.json")
            config = read_project_permissions(create_run_workspace(root))
            denied_read = parse_tool_action("read_file", {"path": "secrets/model.ipynb"})
            allowed_write = parse_tool_action(
                "write_file",
                {"path": "notebooks/demo.ipynb", "content": "{}\n"},
            )
            mixed_write = parse_tool_action(
                "write_files",
                {
                    "files": [
                        {"path": "notebooks/demo.ipynb", "content": "{}\n"},
                        {"path": "src/demo.py", "content": "x = 1\n"},
                    ]
                },
            )
            shallow_write = parse_tool_action("write_file", {"path": "shallow/demo.ipynb", "content": "{}\n"})
            nested_shallow_write = parse_tool_action(
                "write_file",
                {"path": "shallow/archive/demo.ipynb", "content": "{}\n"},
            )

        self.assertEqual(match_project_permission(config, "NotebookRead", denied_read).effect, "deny")
        self.assertEqual(match_project_permission(config, "NotebookEdit", allowed_write).effect, "allow")
        self.assertIsNone(match_project_permission(config, "write_files", mixed_write))
        self.assertEqual(match_project_permission(config, "NotebookEdit", shallow_write).effect, "allow")
        self.assertIsNone(match_project_permission(config, "NotebookEdit", nested_shallow_write))

    def test_matches_claude_runtime_aliases(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-permissions-") as base:
            root = Path(base)
            _write_permissions(
                root,
                {
                    "deny": ["KillBash(proc-deny)"],
                    "allow": ["BashOutput(proc-1)", "KillBash(proc-1)"],
                },
            )
            config = read_project_permissions(create_run_workspace(root))
            output_allowed = parse_tool_action("BashOutput", {"bash_id": "proc-1"})
            kill_allowed = parse_tool_action("KillBash", {"bash_id": "proc-1"})
            kill_denied = parse_tool_action("KillBash", {"bash_id": "proc-deny"})
            kill_unmatched = parse_tool_action("KillBash", {"bash_id": "proc-2"})

        self.assertEqual(match_project_permission(config, "BashOutput", output_allowed).effect, "allow")
        self.assertEqual(match_project_permission(config, "KillBash", kill_allowed).effect, "allow")
        self.assertEqual(match_project_permission(config, "KillBash", kill_denied).effect, "deny")
        self.assertIsNone(match_project_permission(config, "KillBash", kill_unmatched))

    def test_matches_claude_search_and_plan_aliases(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-permissions-") as base:
            root = Path(base)
            _write_permissions(
                root,
                {
                    "deny": ["TodoWrite", "ExitPlanMode"],
                    "allow": ["LS(src)", "Glob(src/**/*.py)", "Glob(shallow/*)", "glob(internal/*)", "Grep(needle)", "TodoRead"],
                },
            )
            config = read_project_permissions(create_run_workspace(root))
            list_action = parse_tool_action("LS", {"path": "src"})
            glob_action = parse_tool_action("Glob", {"path": "src", "pattern": "**/*.py"})
            shallow_glob_action = parse_tool_action("Glob", {"path": "shallow", "pattern": "*.py"})
            nested_shallow_glob_action = parse_tool_action("Glob", {"path": "shallow/nested", "pattern": "*.py"})
            internal_glob_action = parse_tool_action("glob", {"pattern": "internal/*.py"})
            nested_internal_glob_action = parse_tool_action("glob", {"pattern": "internal/nested/*.py"})
            grep_action = parse_tool_action("Grep", {"pattern": "needle"})
            todo_read = parse_tool_action("TodoRead", {})
            todo_write = parse_tool_action("TodoWrite", {"todos": [{"content": "Ship", "status": "completed"}]})

        self.assertEqual(match_project_permission(config, "LS", list_action).effect, "allow")
        self.assertEqual(match_project_permission(config, "Glob", glob_action).effect, "allow")
        self.assertEqual(match_project_permission(config, "Glob", shallow_glob_action).effect, "allow")
        self.assertIsNone(match_project_permission(config, "Glob", nested_shallow_glob_action))
        self.assertEqual(match_project_permission(config, "glob", internal_glob_action).effect, "allow")
        self.assertIsNone(match_project_permission(config, "glob", nested_internal_glob_action))
        self.assertEqual(match_project_permission(config, "Grep", grep_action).effect, "allow")
        self.assertEqual(match_project_permission(config, "TodoRead", todo_read).effect, "allow")
        self.assertEqual(match_project_permission(config, "TodoWrite", todo_write).effect, "deny")

    def test_matches_claude_mcp_tool_names(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-permissions-") as base:
            root = Path(base)
            _write_permissions(root, {"allow": ["mcp__docs__search"]}, source=".claude/settings.json")
            config = read_project_permissions(create_run_workspace(root))
            allowed = parse_tool_action("mcp__docs__search", {"query": "python"})
            wrong_server = parse_tool_action("mcp__repo__search", {"query": "python"})
            wrong_tool = parse_tool_action("mcp__docs__lookup", {"query": "python"})

        self.assertEqual(match_project_permission(config, "mcp__docs__search", allowed).effect, "allow")
        self.assertIsNone(match_project_permission(config, "mcp__repo__search", wrong_server))
        self.assertIsNone(match_project_permission(config, "mcp__docs__lookup", wrong_tool))

    def test_web_fetch_domain_rules_accept_claude_and_internal_names(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-permissions-") as base:
            root = Path(base)
            _write_permissions(
                root,
                {
                    "deny": ["web_fetch(domain:private.example.com)"],
                    "allow": ["WebFetch(domain:*.python.org)", "web_fetch(domain:docs.example.com)"],
                },
            )
            config = read_project_permissions(create_run_workspace(root))
            docs_python = parse_tool_action("WebFetch", {"url": "https://docs.python.org/3/"})
            docs_example = parse_tool_action("web_fetch", {"url": "https://docs.example.com/page"})
            private = parse_tool_action("WebFetch", {"url": "https://private.example.com/secret"})
            unrelated = parse_tool_action("web_fetch", {"url": "https://example.net/"})

        self.assertEqual(match_project_permission(config, "WebFetch", docs_python).effect, "allow")
        self.assertEqual(match_project_permission(config, "web_fetch", docs_example).effect, "allow")
        self.assertEqual(match_project_permission(config, "WebFetch", private).effect, "deny")
        self.assertIsNone(match_project_permission(config, "web_fetch", unrelated))

    def test_cli_permission_overrides_match_claude_mcp_tool_names(self) -> None:
        overrides = build_permission_overrides(
            parse_args(["--allowed-tools", "mcp__docs__search", "--disallowed-tools", "mcp__docs__delete", "inspect"])
        )
        search = parse_tool_action("mcp__docs__search", {"query": "python"})
        delete = parse_tool_action("mcp__docs__delete", {"id": "page-1"})

        self.assertEqual(match_project_permission(overrides, "mcp__docs__search", search).effect, "allow")
        self.assertEqual(match_project_permission(overrides, "mcp__docs__delete", delete).effect, "deny")

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

    def test_deny_rule_blocks_claude_alias_tool_name_without_prompt(self) -> None:
        client = PermissionClient(
            [
                [{"type": "tool_call", "id": "read-1", "name": "Read", "input": {"file_path": ".env"}}],
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

    def test_cli_allowed_tools_skip_prompt_without_trusting_project_allow_rules(self) -> None:
        untrusted_project_client = PermissionClient(
            [
                [{"type": "tool_call", "id": "write-1", "name": "write_file", "input": {"path": "project.py", "content": "x = 0\n"}}],
                [{"type": "text", "text": "Project allow still needed approval."}],
            ]
        )
        approvals: list[str] = []

        def approve(request):
            approvals.append(request.target)
            return ApprovalDecision(approved=True, message="approved")

        with tempfile.TemporaryDirectory(prefix="vibeagent-permissions-") as base:
            root = Path(base)
            _write_permissions(root, {"allow": ["Edit(project.py)"]})
            run_agent(
                "Write project.py",
                base_dir=root,
                client=untrusted_project_client,
                max_iterations=2,
                approval_handler=approve,
                permission_overrides=build_permission_overrides(parse_args(["--allowed-tools", "Edit(cli.py)", "write"])),
            )

        self.assertEqual(approvals, ["project.py"])

        cli_allowed_client = PermissionClient(
            [
                [{"type": "tool_call", "id": "write-1", "name": "write_file", "input": {"path": "cli.py", "content": "x = 1\n"}}],
                [{"type": "text", "text": "CLI allow skipped approval."}],
            ]
        )
        with tempfile.TemporaryDirectory(prefix="vibeagent-permissions-") as base:
            root = Path(base)
            result = run_agent(
                "Write cli.py",
                base_dir=root,
                client=cli_allowed_client,
                max_iterations=2,
                approval_handler=None,
                permission_overrides=build_permission_overrides(parse_args(["--allowed-tools", "Edit(cli.py)", "write"])),
            )
            content = root.joinpath("cli.py").read_text(encoding="utf-8")

        self.assertEqual(result.observations[0].kind, "write_file")
        self.assertEqual(content, "x = 1\n")
        prompt = "\n".join(str(message.content) for message in cli_allowed_client.messages[0])
        self.assertIn("allow: Edit(cli.py)", prompt)
        self.assertIn(ALLOWED_TOOLS_SOURCE, prompt)

    def test_cli_disallowed_tools_override_project_and_cli_allow_rules(self) -> None:
        client = PermissionClient(
            [
                [{"type": "tool_call", "id": "write-1", "name": "write_file", "input": {"path": "src/app.py", "content": "x = 1\n"}}],
                [{"type": "text", "text": "The CLI deny blocked the write."}],
            ]
        )
        with tempfile.TemporaryDirectory(prefix="vibeagent-permissions-") as base:
            root = Path(base)
            _write_permissions(root, {"allow": ["Edit(src/**)"]})
            result = run_agent(
                "Write app",
                base_dir=root,
                client=client,
                max_iterations=2,
                approval_handler=lambda request: ApprovalDecision(approved=True, message="approved"),
                trust_project_permissions=True,
                permission_overrides=build_permission_overrides(
                    parse_args(["--allowed-tools", "Edit(src/**)", "--disallowed-tools", "Edit(src/**)", "write"])
                ),
            )
            exists = root.joinpath("src/app.py").exists()

        self.assertFalse(exists)
        self.assertEqual(result.observations[0].kind, "approval_denied")
        self.assertIn(DISALLOWED_TOOLS_SOURCE, result.observations[0].message)

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
