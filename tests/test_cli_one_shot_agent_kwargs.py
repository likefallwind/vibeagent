from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from vibeagent.cli_one_shot_agent_kwargs import build_one_shot_agent_kwargs
from vibeagent.config import ExecutionConfig
from vibeagent.types import ApprovalRequest
from vibeagent.workspace_permissions import ProjectPermissions


class CliOneShotAgentKwargsTests(unittest.TestCase):
    def test_stream_json_ask_disables_interactive_handlers(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-agent-kwargs-") as base:
            root = Path(base)
            workspace = object()

            kwargs = build_one_shot_agent_kwargs(
                client="client",
                project_root=root,
                execution_config=ExecutionConfig(max_iterations=3, command_timeout_ms=100),
                approval_policy="ask",
                trust_project_permissions=False,
                permission_overrides=None,
                mcp_config_paths=(),
                strict_mcp_config=True,
                machine_output=True,
                stream_json=True,
                prior_context="prior",
                system_prompt="system",
                append_system_prompt="append",
                task_metadata={"source": "project_command"},
                workspace=workspace,
            )

        self.assertEqual(kwargs["client"], "client")
        self.assertEqual(kwargs["max_iterations"], 3)
        self.assertEqual(kwargs["command_timeout_ms"], 100)
        self.assertIsNone(kwargs["approval_handler"])
        self.assertIsNone(kwargs["user_input_handler"])
        self.assertIs(kwargs["workspace"], workspace)
        self.assertTrue(kwargs["strict_mcp_config"])
        self.assertEqual(kwargs["prior_context"], "prior")
        self.assertEqual(kwargs["system_prompt"], "system")
        self.assertEqual(kwargs["append_system_prompt"], "append")
        self.assertEqual(kwargs["task_metadata"], {"source": "project_command"})

    def test_text_output_builds_approval_and_user_input_handlers(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-agent-kwargs-") as base:
            root = Path(base)

            kwargs = build_one_shot_agent_kwargs(
                client=object(),
                project_root=root,
                execution_config=ExecutionConfig(),
                approval_policy="allow",
                trust_project_permissions=False,
                permission_overrides=ProjectPermissions(sources=("cli",)),
                mcp_config_paths=(root / ".mcp.json",),
                strict_mcp_config=False,
                machine_output=False,
                stream_json=False,
                prior_context=None,
                system_prompt=None,
                append_system_prompt=None,
                task_metadata=None,
            )

        decision = kwargs["approval_handler"](
            ApprovalRequest(action_type="write_file", target="note.txt", risk="write")
        )
        self.assertTrue(decision.approved)
        self.assertIsNotNone(kwargs["user_input_handler"])
        self.assertEqual(kwargs["permission_overrides"], ProjectPermissions(sources=("cli",)))
        self.assertEqual(kwargs["mcp_config_paths"], (root / ".mcp.json",))
        self.assertNotIn("workspace", kwargs)

    def test_trust_project_permissions_uses_explicit_or_project_trust(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-agent-kwargs-") as base:
            root = Path(base)

            with patch("vibeagent.cli_one_shot_agent_kwargs.is_project_permissions_trusted", return_value=False):
                explicit = build_one_shot_agent_kwargs(
                    client=object(),
                    project_root=root,
                    execution_config=ExecutionConfig(),
                    approval_policy="deny",
                    trust_project_permissions=True,
                    permission_overrides=None,
                    mcp_config_paths=(),
                    strict_mcp_config=False,
                    machine_output=True,
                    stream_json=False,
                    prior_context=None,
                    system_prompt=None,
                    append_system_prompt=None,
                    task_metadata=None,
                )

            with patch("vibeagent.cli_one_shot_agent_kwargs.is_project_permissions_trusted", return_value=True):
                trusted_file = build_one_shot_agent_kwargs(
                    client=object(),
                    project_root=root,
                    execution_config=ExecutionConfig(),
                    approval_policy="deny",
                    trust_project_permissions=False,
                    permission_overrides=None,
                    mcp_config_paths=(),
                    strict_mcp_config=False,
                    machine_output=True,
                    stream_json=False,
                    prior_context=None,
                    system_prompt=None,
                    append_system_prompt=None,
                    task_metadata=None,
                )

        self.assertTrue(explicit["trust_project_permissions"])
        self.assertTrue(trusted_file["trust_project_permissions"])
