from __future__ import annotations

from dataclasses import replace
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import Mock

from tests.test_mcp import MCP_SERVER_SOURCE
from tests.test_project_agents import ProfileClient
from tests.user_home_test_case import IsolatedUserHomeTestCase
from vibeagent.actions import parse_tool_action
from vibeagent.agent import run_agent
from vibeagent.agent_delegate import execute_delegate_task_action
from vibeagent.agent_delegate_profile import load_delegate_profile_runtime
from vibeagent.dynamic_agent_profiles import parse_dynamic_agent_profiles
from vibeagent.types import ApprovalDecision
from vibeagent.workspace import create_run_workspace, format_project_agent_catalog, read_project_agents
from vibeagent.workspace_agent_profile_parser import parse_agent_content
from vibeagent.workspace_permissions import ProjectPermissions, permission_rules_from_values


def _profiles(definition: dict[str, object]):
    return parse_dynamic_agent_profiles(json.dumps({"worker": definition}))


def _delegate(root: Path, definition: dict[str, object], client: ProfileClient, **kwargs):
    workspace = replace(
        create_run_workspace(root, "run-1"),
        dynamic_agent_profiles=_profiles(definition),
    )
    return execute_delegate_task_action(
        workspace,
        parse_tool_action(
            "delegate_task",
            {"task": "Perform the bounded task", "agent": "worker", "mode": "code"},
        ),
        client,
        parent_iteration=1,
        subagent_id="delegate-1-1",
        max_output_tokens=2048,
        model_retries=0,
        model_retry_delay_ms=0,
        model_timeout_ms=10_000,
        command_timeout_ms=10_000,
        logger=None,
        **kwargs,
    )


class AgentProfileExtendedContractTests(IsolatedUserHomeTestCase):
    def test_structured_yaml_frontmatter_supports_current_extended_fields(self) -> None:
        metadata, prompt = parse_agent_content(
            Path("worker.md"),
            """---
name: worker
description: Runs a controlled review
mode: code
tools: [Read, mcp__profile__echo]
permissionMode: dontAsk
mcpServers:
  - existing
  - profile:
      command: python
      args: [server.py]
hooks:
  PreToolUse:
    - matcher: Read
      hooks:
        - type: command
          command: python validate.py
initialPrompt: Start with repository policy.
background: true
color: cyan
---

PRIVATE_PROFILE_PROMPT
""",
        )

        self.assertEqual(prompt, "PRIVATE_PROFILE_PROMPT")
        self.assertEqual(metadata["permission_mode"], "dontAsk")
        self.assertEqual(metadata["mcp_servers"][0], "existing")
        self.assertEqual(metadata["mcp_servers"][1]["profile"]["args"], ["server.py"])
        self.assertIsInstance(metadata["hooks"], dict)
        self.assertEqual(metadata["initial_prompt"], "Start with repository policy.")
        self.assertTrue(metadata["background"])
        self.assertEqual(metadata["color"], "cyan")

    def test_extended_parser_rejects_duplicate_yaml_and_invalid_values(self) -> None:
        invalid_profiles = (
            ("name: worker\nname: duplicate", "duplicate key"),
            ("name: worker\ndescription: Test\nbackground: 'true'", "background must be a boolean"),
            ("name: worker\ndescription: Test\ncolor: black", "color must be"),
            ("name: worker\ndescription: Test\npermissionMode: unsafe", "permissionMode must be"),
            ("name: worker\ndescription: Test\nmcpServers: [missing, missing]", "duplicate server"),
        )
        for frontmatter, error in invalid_profiles:
            with self.subTest(error=error), self.assertRaisesRegex(ValueError, error):
                parse_agent_content(
                    Path("worker.md"),
                    f"---\n{frontmatter}\n---\n\nPrompt\n",
                )

    def test_catalog_exposes_controls_without_hook_or_mcp_secrets(self) -> None:
        profiles = _profiles(
            {
                "description": "Controlled worker",
                "prompt": "PRIVATE_PROFILE_PROMPT",
                "mcpServers": [
                    {
                        "private": {
                            "command": "PRIVATE_MCP_COMMAND",
                            "env": {"TOKEN": "PRIVATE_MCP_TOKEN"},
                        }
                    }
                ],
                "hooks": {
                    "PreToolUse": [
                        {
                            "matcher": "Read",
                            "hooks": [{"type": "command", "command": "PRIVATE_HOOK_COMMAND"}],
                        }
                    ]
                },
                "initialPrompt": "PRIVATE_INITIAL_PROMPT",
                "permissionMode": "dontAsk",
                "background": True,
                "color": "green",
            }
        )
        with tempfile.TemporaryDirectory(prefix="vibeagent-agent-contract-") as base:
            workspace = replace(
                create_run_workspace(Path(base), "run-1"),
                dynamic_agent_profiles=profiles,
            )
            catalog = read_project_agents(workspace)
            formatted = format_project_agent_catalog(workspace)

        text = json.dumps(catalog, sort_keys=True) + str(formatted)
        self.assertIn("private", text)
        self.assertIn("permissionMode=dontAsk", text)
        self.assertIn("background=true", text)
        for secret in (
            "PRIVATE_PROFILE_PROMPT",
            "PRIVATE_MCP_COMMAND",
            "PRIVATE_MCP_TOKEN",
            "PRIVATE_HOOK_COMMAND",
            "PRIVATE_INITIAL_PROMPT",
        ):
            self.assertNotIn(secret, text)

    def test_main_profile_prepends_initial_prompt_once(self) -> None:
        profiles = _profiles(
            {
                "description": "Main worker",
                "prompt": "MAIN_PROFILE_SYSTEM_PROMPT",
                "initialPrompt": "INITIAL_PROFILE_USER_TURN",
            }
        )
        client = ProfileClient([[{"type": "text", "text": "done"}]])
        with tempfile.TemporaryDirectory(prefix="vibeagent-agent-contract-") as base:
            result = run_agent(
                "USER_TASK",
                base_dir=Path(base),
                client=client,
                max_iterations=1,
                agent="worker",
                dynamic_agent_profiles=profiles,
            )

        self.assertTrue(result.success)
        user_message = str(client.messages[0][1].content)
        self.assertIn("INITIAL_PROFILE_USER_TURN", user_message)
        self.assertIn("USER_TASK", user_message)
        self.assertLess(user_message.index("INITIAL_PROFILE_USER_TURN"), user_message.index("USER_TASK"))

    def test_main_profile_permission_mode_and_session_hook_apply_before_model(self) -> None:
        client = ProfileClient(
            [
                [
                    {
                        "type": "tool_call",
                        "id": "edit-1",
                        "name": "Edit",
                        "input": {
                            "file_path": "value.py",
                            "old_string": "VALUE = 1",
                            "new_string": "VALUE = 2",
                        },
                    }
                ],
                [{"type": "text", "text": "main edit complete"}],
            ]
        )
        with tempfile.TemporaryDirectory(prefix="vibeagent-agent-contract-") as base:
            root = Path(base)
            root.joinpath("value.py").write_text("VALUE = 1\n", encoding="utf-8")
            root.joinpath("hook.py").write_text(
                "from pathlib import Path\nPath('session.marker').write_text('started', encoding='utf-8')\n",
                encoding="utf-8",
            )
            profiles = _profiles(
                {
                    "description": "Main controlled editor",
                    "prompt": "Edit the requested value.",
                    "mode": "code",
                    "tools": ["Edit"],
                    "permissionMode": "acceptEdits",
                    "hooks": {
                        "SessionStart": [
                            {
                                "hooks": [
                                    {
                                        "type": "command",
                                        "command": f"{sys.executable} hook.py",
                                    }
                                ]
                            }
                        ]
                    },
                }
            )
            approvals: list[str] = []

            def approve_hook(request):
                approvals.append(request.target)
                return ApprovalDecision(True, "approved")

            result = run_agent(
                "Edit value.py",
                base_dir=root,
                client=client,
                max_iterations=2,
                agent="worker",
                dynamic_agent_profiles=profiles,
                approval_policy="ask",
                approval_handler=approve_hook,
            )
            content = root.joinpath("value.py").read_text(encoding="utf-8")
            marker = root.joinpath("session.marker").read_text(encoding="utf-8")

        self.assertTrue(result.success)
        self.assertEqual(content, "VALUE = 2\n")
        self.assertEqual(marker, "started")
        self.assertEqual(len(approvals), 1)
        self.assertIn("SessionStart hook", approvals[0])

    def test_main_profile_forced_plan_mode_cannot_exit(self) -> None:
        client = ProfileClient(
            [
                [
                    {
                        "type": "tool_call",
                        "id": "exit-1",
                        "name": "ExitPlanMode",
                        "input": {"plan": "Write value.py."},
                    }
                ]
            ]
        )
        profiles = _profiles(
            {
                "description": "Read-only planner",
                "prompt": "Plan without editing.",
                "mode": "code",
                "tools": ["Read", "ExitPlanMode"],
                "permissionMode": "plan",
            }
        )
        approvals: list[str] = []

        with tempfile.TemporaryDirectory(prefix="vibeagent-agent-contract-") as base:
            result = run_agent(
                "Plan value.py",
                base_dir=Path(base),
                client=client,
                max_iterations=1,
                agent="worker",
                dynamic_agent_profiles=profiles,
                approval_policy="ask",
                approval_handler=lambda request: (
                    approvals.append(request.action_type)
                    or ApprovalDecision(True, "approved")
                ),
            )

        exposed = set(client.tool_names[0])
        self.assertNotIn("ExitPlanMode", exposed)
        self.assertEqual(result.observations[0].kind, "tool_error")
        self.assertEqual(result.approval_policy, "plan")
        self.assertEqual(approvals, [])

    def test_main_profile_inline_mcp_server_runs_through_real_protocol(self) -> None:
        client = ProfileClient(
            [
                [
                    {
                        "type": "tool_call",
                        "id": "tools-1",
                        "name": "mcp_tools",
                        "input": {"server": "profile", "timeout_ms": 2_000},
                    }
                ],
                [
                    {
                        "type": "tool_call",
                        "id": "call-1",
                        "name": "mcp__profile__echo",
                        "input": {"message": "main-scoped"},
                    }
                ],
                [{"type": "text", "text": "main MCP complete"}],
            ]
        )
        with tempfile.TemporaryDirectory(prefix="vibeagent-agent-contract-") as base:
            root = Path(base)
            root.joinpath("mcp_server.py").write_text(MCP_SERVER_SOURCE, encoding="utf-8")
            profiles = _profiles(
                {
                    "description": "Main MCP worker",
                    "prompt": "Use the private MCP server.",
                    "mode": "code",
                    "tools": ["mcp__profile__echo"],
                    "mcpServers": [
                        {
                            "profile": {
                                "command": sys.executable,
                                "args": ["mcp_server.py"],
                                "cwd": ".",
                            }
                        }
                    ],
                }
            )
            result = run_agent(
                "Use the scoped server",
                base_dir=root,
                client=client,
                max_iterations=3,
                agent="worker",
                dynamic_agent_profiles=profiles,
                approval_policy="allow",
                approval_handler=lambda _request: ApprovalDecision(True, "approved"),
            )

        self.assertTrue(result.success)
        self.assertIn("mcp__profile__echo", client.tool_names[1])
        self.assertIn('"message": "main-scoped"', str(client.messages[2][-1].content))

    def test_accept_edits_profile_uses_trusted_scoped_edit_permission(self) -> None:
        client = ProfileClient(
            [
                [
                    {
                        "type": "tool_call",
                        "id": "edit-1",
                        "name": "Edit",
                        "input": {
                            "file_path": "value.py",
                            "old_string": "VALUE = 1",
                            "new_string": "VALUE = 2",
                        },
                    }
                ],
                [{"type": "text", "text": "edited"}],
            ]
        )
        with tempfile.TemporaryDirectory(prefix="vibeagent-agent-contract-") as base:
            root = Path(base)
            root.joinpath("value.py").write_text("VALUE = 1\n", encoding="utf-8")
            observation = _delegate(
                root,
                {
                    "description": "Edits one file",
                    "prompt": "Edit the requested value.",
                    "mode": "code",
                    "tools": ["Edit"],
                    "permissionMode": "acceptEdits",
                },
                client,
                approval_policy="ask",
                approval_handler=Mock(side_effect=AssertionError("must not prompt")),
            )
            content = root.joinpath("value.py").read_text(encoding="utf-8")

        self.assertTrue(observation.ok)
        self.assertEqual(content, "VALUE = 2\n")

    def test_untrusted_project_profile_cannot_raise_its_permission_mode(self) -> None:
        client = ProfileClient([[{"type": "text", "text": "must not run"}]])
        with tempfile.TemporaryDirectory(prefix="vibeagent-agent-contract-") as base:
            root = Path(base)
            profile = root / ".claude/agents/worker.md"
            profile.parent.mkdir(parents=True)
            profile.write_text(
                "---\nname: worker\ndescription: Unsafe project profile\n"
                "mode: code\npermissionMode: bypassPermissions\n---\n\nDo work.\n",
                encoding="utf-8",
            )
            observation = execute_delegate_task_action(
                create_run_workspace(root, "run-1"),
                parse_tool_action(
                    "delegate_task",
                    {"task": "Perform the task", "agent": "worker", "mode": "code"},
                ),
                client,
                parent_iteration=1,
                subagent_id="delegate-1-1",
                max_output_tokens=2048,
                model_retries=0,
                model_retry_delay_ms=0,
                model_timeout_ms=10_000,
                command_timeout_ms=10_000,
                logger=None,
                approval_policy="ask",
            )

        self.assertFalse(observation.ok)
        self.assertIn("requires trusted project configuration", observation.message)
        self.assertEqual(client.messages, [])

    def test_dont_ask_and_auto_profiles_conservatively_deny_unapproved_edits(self) -> None:
        for permission_mode in ("dontAsk", "auto"):
            client = ProfileClient(
                [
                    [
                        {
                            "type": "tool_call",
                            "id": "edit-1",
                            "name": "Edit",
                            "input": {
                                "file_path": "value.py",
                                "old_string": "VALUE = 1",
                                "new_string": "VALUE = 2",
                            },
                        }
                    ],
                    [{"type": "text", "text": "denial observed"}],
                ]
            )
            with self.subTest(permission_mode=permission_mode), tempfile.TemporaryDirectory(
                prefix="vibeagent-agent-contract-"
            ) as base:
                root = Path(base)
                root.joinpath("value.py").write_text("VALUE = 1\n", encoding="utf-8")
                observation = _delegate(
                    root,
                    {
                        "description": "Cannot prompt",
                        "prompt": "Try the requested edit.",
                        "mode": "code",
                        "tools": ["Edit"],
                        "permissionMode": permission_mode,
                    },
                    client,
                    approval_policy="ask",
                    approval_handler=Mock(side_effect=AssertionError("must not prompt")),
                )
                content = root.joinpath("value.py").read_text(encoding="utf-8")

            self.assertTrue(observation.ok)
            self.assertEqual(content, "VALUE = 1\n")
            self.assertIn("approval_denied", str(client.messages[1][-1].content))

    def test_bypass_profile_uses_trusted_rules_without_disabling_hard_blocks(self) -> None:
        client = ProfileClient(
            [
                [
                    {
                        "type": "tool_call",
                        "id": "edit-1",
                        "name": "Edit",
                        "input": {
                            "file_path": "value.py",
                            "old_string": "VALUE = 1",
                            "new_string": "VALUE = 2",
                        },
                    }
                ],
                [{"type": "text", "text": "bypass edit complete"}],
            ]
        )
        with tempfile.TemporaryDirectory(prefix="vibeagent-agent-contract-") as base:
            root = Path(base)
            root.joinpath("value.py").write_text("VALUE = 1\n", encoding="utf-8")
            observation = _delegate(
                root,
                {
                    "description": "Explicit bypass worker",
                    "prompt": "Edit the requested value.",
                    "mode": "code",
                    "tools": ["Edit"],
                    "permissionMode": "bypassPermissions",
                },
                client,
                approval_policy="ask",
                approval_handler=Mock(side_effect=AssertionError("must not prompt")),
            )
            content = root.joinpath("value.py").read_text(encoding="utf-8")

        self.assertTrue(observation.ok)
        self.assertEqual(content, "VALUE = 2\n")

    def test_bypass_profile_preserves_explicit_deny_precedence(self) -> None:
        client = ProfileClient(
            [
                [
                    {
                        "type": "tool_call",
                        "id": "edit-1",
                        "name": "Edit",
                        "input": {
                            "file_path": "value.py",
                            "old_string": "VALUE = 1",
                            "new_string": "VALUE = 2",
                        },
                    }
                ],
                [{"type": "text", "text": "denial observed"}],
            ]
        )
        deny_source = "test explicit deny"
        permissions = ProjectPermissions(
            rules=permission_rules_from_values("deny", ("Edit",), deny_source),
            sources=(deny_source,),
        )
        with tempfile.TemporaryDirectory(prefix="vibeagent-agent-contract-") as base:
            root = Path(base)
            root.joinpath("value.py").write_text("VALUE = 1\n", encoding="utf-8")
            observation = _delegate(
                root,
                {
                    "description": "Explicit bypass worker",
                    "prompt": "Edit the requested value.",
                    "mode": "code",
                    "tools": ["Edit"],
                    "permissionMode": "bypassPermissions",
                },
                client,
                approval_policy="ask",
                approval_handler=Mock(side_effect=AssertionError("must not prompt")),
                permissions=permissions,
            )
            content = root.joinpath("value.py").read_text(encoding="utf-8")

        self.assertTrue(observation.ok)
        self.assertEqual(content, "VALUE = 1\n")
        self.assertIn("blocked by the selected project agent profile", str(client.messages[1][-1].content))

    def test_strict_mcp_config_ignores_inline_servers_from_file_profiles(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-agent-contract-") as base:
            root = Path(base)
            profile = root / ".claude/agents/worker.md"
            profile.parent.mkdir(parents=True)
            profile.write_text(
                "---\nname: worker\ndescription: File profile\n"
                "mcpServers:\n  - hidden:\n      command: python\n      args: [server.py]\n"
                "---\n\nUse configured tools.\n",
                encoding="utf-8",
            )
            workspace = create_run_workspace(root, "run-1", strict_mcp_config=True)
            action = parse_tool_action(
                "delegate_task",
                {"task": "Perform the task", "agent": "worker", "mode": "code"},
            )
            runtime = load_delegate_profile_runtime(workspace, action)

        self.assertIsNone(runtime.error)
        self.assertEqual(runtime.mcp_servers, ())
        self.assertIsNone(runtime.workspace)

    def test_profile_plan_mode_converts_its_own_code_profile_to_read_only(self) -> None:
        client = ProfileClient([[{"type": "text", "text": "read-only plan complete"}]])
        with tempfile.TemporaryDirectory(prefix="vibeagent-agent-contract-") as base:
            observation = _delegate(
                Path(base),
                {
                    "description": "Plans without changes",
                    "prompt": "Inspect and plan only.",
                    "mode": "code",
                    "permissionMode": "plan",
                },
                client,
                approval_policy="ask",
                approval_handler=None,
            )

        self.assertTrue(observation.ok)
        self.assertEqual(observation.mode, "explore")
        self.assertNotIn("Edit", client.tool_names[0])

    def test_profile_hook_is_scoped_to_selected_subagent(self) -> None:
        client = ProfileClient(
            [
                [
                    {
                        "type": "tool_call",
                        "id": "read-1",
                        "name": "Read",
                        "input": {"file_path": "README.md"},
                    }
                ],
                [{"type": "text", "text": "read complete"}],
            ]
        )
        with tempfile.TemporaryDirectory(prefix="vibeagent-agent-contract-") as base:
            root = Path(base)
            root.joinpath("README.md").write_text("# Test\n", encoding="utf-8")
            root.joinpath("hook.py").write_text(
                "from pathlib import Path\nPath('hook.marker').write_text('ran', encoding='utf-8')\n",
                encoding="utf-8",
            )
            observation = _delegate(
                root,
                {
                    "description": "Reads with validation",
                    "prompt": "Read the file.",
                    "tools": ["Read"],
                    "hooks": {
                        "PreToolUse": [
                            {
                                "matcher": "Read",
                                "hooks": [
                                    {
                                        "type": "command",
                                        "command": f"{sys.executable} hook.py",
                                    }
                                ],
                            }
                        ]
                    },
                },
                client,
                approval_policy="allow",
                approval_handler=lambda _request: ApprovalDecision(True, "approved"),
            )
            self.assertTrue(
                root.joinpath("hook.marker").exists(),
                f"observation={observation!r} messages={client.messages!r}",
            )
            marker = root.joinpath("hook.marker").read_text(encoding="utf-8")

        self.assertTrue(observation.ok)
        self.assertEqual(marker, "ran")

    def test_inline_mcp_server_is_available_only_inside_selected_subagent(self) -> None:
        client = ProfileClient(
            [
                [
                    {
                        "type": "tool_call",
                        "id": "tools-1",
                        "name": "mcp_tools",
                        "input": {"server": "profile", "timeout_ms": 2_000},
                    }
                ],
                [
                    {
                        "type": "tool_call",
                        "id": "call-1",
                        "name": "mcp__profile__echo",
                        "input": {"message": "scoped"},
                    }
                ],
                [{"type": "text", "text": "MCP complete"}],
            ]
        )
        with tempfile.TemporaryDirectory(prefix="vibeagent-agent-contract-") as base:
            root = Path(base)
            root.joinpath("mcp_server.py").write_text(MCP_SERVER_SOURCE, encoding="utf-8")
            observation = _delegate(
                root,
                {
                    "description": "Uses one private MCP server",
                    "prompt": "Use the scoped MCP server.",
                    "mode": "code",
                    "tools": ["mcp__profile__echo"],
                    "mcpServers": [
                        {
                            "profile": {
                                "command": sys.executable,
                                "args": ["mcp_server.py"],
                                "cwd": ".",
                            }
                        }
                    ],
                },
                client,
                approval_policy="allow",
                approval_handler=lambda _request: ApprovalDecision(True, "approved"),
            )
            parent_catalog = format_project_agent_catalog(create_run_workspace(root, "parent-run"))

        self.assertTrue(observation.ok)
        self.assertIn(
            "mcp__profile__echo",
            client.tool_names[1],
            str(client.messages[1][-1].content),
        )
        self.assertIn('"message": "scoped"', str(client.messages[2][-1].content))
        self.assertIsNone(parent_catalog)


if __name__ == "__main__":
    unittest.main()
