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
        self.assertTrue((CORE_AGENT_TOOL_NAMES - {"ExitPlanMode"}).issubset(setup.active_tool_names))
        self.assertEqual([message.role for message in setup.messages[:2]], ["system", "user"])
        self.assertTrue(setup.project_permissions.enabled)
        self.assertEqual(setup.task_metadata, {"api_key": "secret-token"})
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

    def test_prepare_agent_run_merges_additional_roots_into_supplied_workspace(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-run-setup-") as base:
            parent = Path(base)
            root = parent / "main"
            first = parent / "first"
            second = parent / "second"
            for path in (root, first, second):
                path.mkdir()
            workspace = create_run_workspace(root, "run-1", additional_roots=(first,))

            setup = prepare_agent_run(
                "Inspect roots",
                base_dir=None,
                workspace=workspace,
                prior_context=None,
                approval_policy="ask",
                task_metadata=None,
                trust_project_permissions=False,
                permission_overrides=None,
                mcp_config_paths=(Path("extra.mcp.json"),),
                strict_mcp_config=False,
                system_prompt=None,
                append_system_prompt=None,
                additional_directories=(second, first),
            )

        self.assertEqual(setup.workspace.additional_roots, (first.resolve(), second.resolve()))
        self.assertEqual(setup.workspace.mcp_config_paths, (root.resolve() / "extra.mcp.json",))

    def test_prepare_agent_run_records_prompt_file_metadata_but_keeps_original_task(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-run-setup-") as base:
            root = Path(base)
            (root / "app.py").write_text("REFERENCE_BODY = 42\n", encoding="utf-8")
            setup = prepare_agent_run(
                "Review @app.py",
                base_dir=root,
                workspace=None,
                prior_context=None,
                approval_policy="ask",
                task_metadata=None,
                trust_project_permissions=False,
                permission_overrides=None,
                mcp_config_paths=(),
                strict_mcp_config=False,
                system_prompt=None,
                append_system_prompt=None,
            )
            events_text = setup.workspace.session_dir.joinpath("events.jsonl").read_text(encoding="utf-8")
            events = [json.loads(line) for line in events_text.splitlines()]

        self.assertEqual(events[0]["type"], "task")
        self.assertEqual(events[0]["task"], "Review @app.py")
        loaded = next(event for event in events if event["type"] == "prompt_files_loaded")
        self.assertEqual(loaded["files"], [{"path": "app.py", "kind": "text", "bytes": 20, "truncated": False}])
        self.assertNotIn("REFERENCE_BODY", events_text)
        self.assertIn("REFERENCE_BODY = 42", str(setup.messages[1].content))

    def test_prepare_agent_run_injects_only_selected_prompt_file_lines(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-run-setup-") as base:
            root = Path(base)
            source = "OUTSIDE_BEFORE\nSELECTED_ONE\nSELECTED_TWO\nOUTSIDE_AFTER\n"
            (root / "app.py").write_text(source, encoding="utf-8")
            setup = prepare_agent_run(
                "Review @app.py#2-3",
                base_dir=root,
                workspace=None,
                prior_context=None,
                approval_policy="ask",
                task_metadata=None,
                trust_project_permissions=False,
                permission_overrides=None,
                mcp_config_paths=(),
                strict_mcp_config=False,
                system_prompt=None,
                append_system_prompt=None,
            )
            events_text = setup.workspace.session_dir.joinpath("events.jsonl").read_text(encoding="utf-8")
            events = [json.loads(line) for line in events_text.splitlines()]

        prompt = str(setup.messages[1].content)
        loaded = next(event for event in events if event["type"] == "prompt_files_loaded")
        self.assertEqual(events[0]["task"], "Review @app.py#2-3")
        self.assertEqual(
            loaded["files"],
            [
                {
                    "path": "app.py",
                    "kind": "text",
                    "bytes": len(source.encode("utf-8")),
                    "truncated": False,
                    "start_line": 2,
                    "end_line": 3,
                }
            ],
        )
        self.assertIn("2: SELECTED_ONE", prompt)
        self.assertIn("3: SELECTED_TWO", prompt)
        self.assertNotIn("OUTSIDE_BEFORE", prompt)
        self.assertNotIn("OUTSIDE_AFTER", prompt)
        self.assertNotIn("SELECTED_ONE", events_text)

    def test_prepare_agent_run_grants_file_access_without_loading_additional_configuration(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-run-setup-") as base:
            parent = Path(base)
            root = parent / "main"
            shared = parent / "shared"
            root.mkdir()
            shared.mkdir()
            (root / "CLAUDE.md").write_text("MAIN_PROJECT_INSTRUCTION", encoding="utf-8")
            (shared / "CLAUDE.md").write_text("SHARED_CONFIG_MUST_NOT_LOAD", encoding="utf-8")
            reference = shared / "reference.txt"
            reference.write_text("SHARED_REFERENCE_BODY", encoding="utf-8")

            setup = prepare_agent_run(
                f"Review @{reference}",
                base_dir=root,
                workspace=None,
                prior_context=None,
                approval_policy="ask",
                task_metadata=None,
                trust_project_permissions=False,
                permission_overrides=None,
                mcp_config_paths=(),
                strict_mcp_config=False,
                system_prompt=None,
                append_system_prompt=None,
                additional_directories=(shared,),
            )
            events = [
                json.loads(line)
                for line in setup.workspace.session_dir.joinpath("events.jsonl").read_text(encoding="utf-8").splitlines()
            ]

        prompt = str(setup.messages[1].content)
        task_event = next(event for event in events if event["type"] == "task")
        self.assertEqual(setup.workspace.additional_roots, (shared.resolve(),))
        self.assertIn("MAIN_PROJECT_INSTRUCTION", prompt)
        self.assertIn("SHARED_REFERENCE_BODY", prompt)
        self.assertNotIn("SHARED_CONFIG_MUST_NOT_LOAD", prompt)
        self.assertIn(str(shared.resolve()), prompt)
        self.assertEqual(task_event["additional_directories"], [str(shared.resolve())])


if __name__ == "__main__":
    unittest.main()
