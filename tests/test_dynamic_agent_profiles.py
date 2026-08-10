from __future__ import annotations

from dataclasses import replace
import json
from pathlib import Path
import tempfile
import unittest

from tests.test_project_agents import ProfileClient, _write_agent
from tests.user_home_test_case import IsolatedUserHomeTestCase
from vibeagent.actions import parse_tool_action
from vibeagent.agent import run_agent
from vibeagent.agent_delegate import execute_delegate_task_action
from vibeagent.dynamic_agent_profiles import parse_dynamic_agent_profiles
from vibeagent.prompts import build_messages
from vibeagent.types import ApprovalDecision
from vibeagent.workspace import create_run_workspace, read_project_agent, read_project_agents


class DynamicAgentProfileTests(IsolatedUserHomeTestCase):
    def test_parser_reuses_profile_validation_and_rejects_malformed_definitions(self) -> None:
        profiles = parse_dynamic_agent_profiles(
            json.dumps(
                {
                    "reviewer": {
                        "description": "Reviews focused code",
                        "prompt": "Inspect evidence only.",
                        "mode": "explore",
                        "tools": ["Read"],
                        "maxTurns": 4,
                    }
                }
            )
        )

        self.assertEqual(len(profiles), 1)
        self.assertEqual(profiles[0].name, "reviewer")
        self.assertEqual(profiles[0].tools, ("Read", "read_file"))
        self.assertEqual(profiles[0].max_turns, 4)
        for payload, message in (
            ("[]", "JSON object"),
            ('{"bad":{"description":"Bad"}}', "prompt field"),
            ('{"bad":{"description":"Bad","prompt":"x","unknown":true}}', "unknown field"),
            ('{"bad":{"description":"Bad","prompt":"x","tools":[1]}}', "strings only"),
            ('{"bad":{"description":"Bad","prompt":"x","mode":"code","tools":["not-real"]}}', "unknown tool"),
            ('{"bad":{"description":"First","description":"Second","prompt":"x"}}', "duplicate object key"),
        ):
            with self.subTest(payload=payload), self.assertRaisesRegex(ValueError, message):
                parse_dynamic_agent_profiles(payload)

    def test_dynamic_profile_overrides_disk_profile_without_exposing_prompt_in_catalog(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-dynamic-agent-") as base:
            root = Path(base)
            _write_agent(
                root,
                ".claude/agents",
                "reviewer",
                "Disk reviewer",
                "DISK_PRIVATE_PROMPT",
                tools="Read",
            )
            profiles = parse_dynamic_agent_profiles(
                json.dumps(
                    {
                        "reviewer": {
                            "description": "Invocation reviewer",
                            "prompt": "DYNAMIC_PRIVATE_PROMPT",
                            "tools": ["Read"],
                        }
                    }
                )
            )
            workspace = replace(
                create_run_workspace(root, "run-1"),
                dynamic_agent_profiles=profiles,
            )

            catalog = read_project_agents(workspace)
            loaded = read_project_agent(workspace, "reviewer")
            messages = build_messages("Inspect", workspace)

        self.assertEqual(catalog["total"], 1)
        self.assertEqual(catalog["agents"][0]["source"], "cli")
        self.assertEqual(catalog["agents"][0]["description"], "Invocation reviewer")
        self.assertNotIn("prompt", catalog["agents"][0])
        self.assertEqual(loaded["prompt"], "DYNAMIC_PRIVATE_PROMPT")
        self.assertNotIn("DYNAMIC_PRIVATE_PROMPT", str(messages[1].content))

    def test_dynamic_profile_controls_delegated_prompt_mode_and_tools(self) -> None:
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
                [{"type": "text", "text": "Dynamic review complete."}],
            ]
        )
        profiles = parse_dynamic_agent_profiles(
            json.dumps(
                {
                    "reviewer": {
                        "description": "Reviews one file",
                        "prompt": "DYNAMIC_REVIEW_INSTRUCTION",
                        "mode": "explore",
                        "tools": ["Read"],
                    }
                }
            )
        )
        with tempfile.TemporaryDirectory(prefix="vibeagent-dynamic-agent-") as base:
            root = Path(base)
            root.joinpath("README.md").write_text("# Demo\n", encoding="utf-8")
            workspace = replace(
                create_run_workspace(root, "run-1"),
                dynamic_agent_profiles=profiles,
            )
            observation = execute_delegate_task_action(
                workspace,
                parse_tool_action(
                    "delegate_task",
                    {"task": "Review README", "agent": "reviewer", "mode": "code"},
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
                approval_handler=lambda request: ApprovalDecision(True, "approved"),
            )

        self.assertTrue(observation.ok)
        self.assertEqual(observation.mode, "explore")
        self.assertEqual(observation.agent, "reviewer")
        self.assertEqual(set(client.tool_names[0]), {"Read", "finish", "read_file"})
        self.assertIn("DYNAMIC_REVIEW_INSTRUCTION", str(client.messages[0][0].content))

    def test_dynamic_profile_can_be_selected_as_the_main_agent(self) -> None:
        client = ProfileClient([[{"type": "text", "text": "Main dynamic review complete."}]])
        profiles = parse_dynamic_agent_profiles(
            json.dumps(
                {
                    "reviewer": {
                        "description": "Reviews as the main agent",
                        "prompt": "DYNAMIC_MAIN_REVIEWER_INSTRUCTION",
                        "tools": ["Read"],
                    }
                }
            )
        )
        with tempfile.TemporaryDirectory(prefix="vibeagent-dynamic-agent-") as base:
            result = run_agent(
                "Review",
                base_dir=Path(base),
                client=client,
                max_iterations=1,
                agent="reviewer",
                dynamic_agent_profiles=profiles,
            )

        self.assertTrue(result.success)
        self.assertIn("DYNAMIC_MAIN_REVIEWER_INSTRUCTION", str(client.messages[0][0].content))
        self.assertEqual(set(client.tool_names[0]), {"Read", "finish", "read_file"})

    def test_nested_subagent_can_select_another_dynamic_profile(self) -> None:
        client = ProfileClient(
            [
                [
                    {
                        "type": "tool_call",
                        "id": "nested-1",
                        "name": "Task",
                        "input": {
                            "prompt": "Inspect one concern",
                            "subagent_type": "reviewer",
                        },
                    }
                ],
                [{"type": "text", "text": "Nested dynamic review complete."}],
                [{"type": "text", "text": "Coordinator collected the review."}],
            ]
        )
        profiles = parse_dynamic_agent_profiles(
            json.dumps(
                {
                    "coordinator": {
                        "description": "Coordinates reviews",
                        "prompt": "DYNAMIC_COORDINATOR_INSTRUCTION",
                        "tools": ["Task"],
                    },
                    "reviewer": {
                        "description": "Reviews evidence",
                        "prompt": "DYNAMIC_NESTED_REVIEWER_INSTRUCTION",
                    },
                }
            )
        )
        with tempfile.TemporaryDirectory(prefix="vibeagent-dynamic-agent-") as base:
            workspace = replace(
                create_run_workspace(Path(base), "run-1"),
                dynamic_agent_profiles=profiles,
            )
            observation = execute_delegate_task_action(
                workspace,
                parse_tool_action(
                    "delegate_task",
                    {"task": "Coordinate review", "agent": "coordinator"},
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
            )

        self.assertTrue(observation.ok)
        self.assertIn("DYNAMIC_COORDINATOR_INSTRUCTION", str(client.messages[0][0].content))
        self.assertIn("DYNAMIC_NESTED_REVIEWER_INSTRUCTION", str(client.messages[1][0].content))
        self.assertIn("Nested dynamic review complete", str(client.messages[2][-1].content))


if __name__ == "__main__":
    unittest.main()
