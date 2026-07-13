from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from vibeagent.agent_core_tools import CORE_AGENT_TOOL_NAMES
from vibeagent.agent_run_setup import prepare_agent_run
from vibeagent.workspace import create_run_workspace


class AgentRunSetupTests(unittest.TestCase):
    def test_prepare_agent_run_initializes_workspace_events_and_core_tools(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-run-setup-") as base:
            root = Path(base)
            permissions_path = root / ".vibeagent" / "permissions.json"
            permissions_path.parent.mkdir(parents=True, exist_ok=True)
            permissions_path.write_text(json.dumps({"deny": ["Bash(git push *)"]}), encoding="utf-8")
            setup = prepare_agent_run(
                "Inspect setup",
                base_dir=root,
                workspace=None,
                prior_context="previous context",
                approval_policy="ask",
                task_metadata={"api_key": "secret-token"},
                trust_project_permissions=False,
                permission_overrides=None,
                mcp_config_paths=(),
                strict_mcp_config=False,
                system_prompt=None,
                append_system_prompt=None,
            )
            events = [
                json.loads(line)
                for line in (setup.workspace.session_dir / "events.jsonl").read_text(encoding="utf-8").splitlines()
            ]

        self.assertEqual(setup.workspace.root, root.resolve())
        self.assertTrue(CORE_AGENT_TOOL_NAMES.issubset(setup.active_tool_names))
        self.assertEqual([message.role for message in setup.messages[:2]], ["system", "user"])
        self.assertTrue(setup.project_permissions.enabled)
        self.assertEqual(setup.project_permissions.allow_rules_trusted, False)
        self.assertIn("task", [event["type"] for event in events])
        self.assertIn("permissions_loaded", [event["type"] for event in events])
        self.assertIn("tool_catalog_initialized", [event["type"] for event in events])
        task_event = next(event for event in events if event["type"] == "task")
        self.assertEqual(task_event["task"], "Inspect setup")
        self.assertNotIn("secret-token", json.dumps(task_event))

    def test_prepare_agent_run_updates_supplied_workspace_mcp_and_trust_flags(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-run-setup-") as base:
            root = Path(base)
            workspace = create_run_workspace(root, "run-1")
            setup = prepare_agent_run(
                "Inspect trusted setup",
                base_dir=None,
                workspace=workspace,
                prior_context=None,
                approval_policy="plan",
                task_metadata=None,
                trust_project_permissions=True,
                permission_overrides=None,
                mcp_config_paths=(Path("extra.mcp.json"),),
                strict_mcp_config=True,
                system_prompt=None,
                append_system_prompt=None,
            )

        self.assertTrue(setup.workspace.project_config_trusted)
        self.assertEqual(setup.workspace.mcp_config_paths, (root.resolve() / "extra.mcp.json",))
        self.assertTrue(setup.workspace.strict_mcp_config)
        self.assertTrue(setup.project_permissions.allow_rules_trusted)


if __name__ == "__main__":
    unittest.main()
