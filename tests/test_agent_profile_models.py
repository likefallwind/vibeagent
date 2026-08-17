from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from tests.user_home_test_case import IsolatedUserHomeTestCase
from vibeagent.agent import run_agent
from vibeagent.agent_delegate import execute_delegate_task_action
from vibeagent.types import AssistantResponse, ContentBlock, DelegateTaskAction
from vibeagent.workspace_agents import format_project_agent_catalog, read_project_agents
from vibeagent.workspace_core import create_run_workspace


def _write_agent(
    root: Path,
    name: str,
    *,
    model: str | None = None,
    effort: str | None = None,
) -> None:
    path = root / ".claude/agents" / f"{name}.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    model_line = f"model: {model}\n" if model is not None else ""
    effort_line = f"effort: {effort}\n" if effort is not None else ""
    path.write_text(
        f"---\nname: {name}\ndescription: Model profile\nmode: explore\n"
        f"{model_line}{effort_line}---\n\nMODEL_PROFILE_PROMPT\n",
        encoding="utf-8",
    )


class ConfigurableClient:
    def __init__(
        self,
        responses: list[list[ContentBlock]],
        *,
        root: "ConfigurableClient | None" = None,
        model: str | None = None,
        effort: str | None = None,
    ) -> None:
        self.responses = responses
        self.root = root or self
        self.model = model
        self.effort = effort
        if root is None:
            self.configurations: list[tuple[str | None, str | None]] = []
            self.completions: list[tuple[str | None, str | None]] = []

    def with_agent_profile(self, *, model: str | None, effort: str | None):
        self.root.configurations.append((model, effort))
        return ConfigurableClient(
            self.responses,
            root=self.root,
            model=model or self.model,
            effort=self.effort if effort is None else effort,
        )

    def complete(self, messages, tools=None, **kwargs):
        self.root.completions.append((self.model, self.effort))
        content = self.responses[len(self.root.completions) - 1]
        return AssistantResponse(content=content, raw={"content": content})


class BasicClient:
    def __init__(self) -> None:
        self.calls = 0

    def complete(self, messages, tools=None, **kwargs):
        self.calls += 1
        return AssistantResponse(
            content=[{"type": "text", "text": "unexpected"}],
            raw={},
        )


class AgentProfileModelTests(IsolatedUserHomeTestCase):
    def test_catalog_parses_model_effort_and_rejects_invalid_values(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-profile-model-") as base:
            root = Path(base)
            _write_agent(root, "tuned", model="claude-opus-5", effort="medium")
            _write_agent(root, "bad-model", model="bad model")
            _write_agent(root, "bad-effort", effort="adaptive")

            catalog = read_project_agents(create_run_workspace(root))
            formatted = format_project_agent_catalog(create_run_workspace(root))

        agents = {str(item["name"]): item for item in catalog["agents"]}
        self.assertEqual(agents["tuned"]["model"], "claude-opus-5")
        self.assertEqual(agents["tuned"]["effort"], "medium")
        self.assertIn("model=claude-opus-5, effort=medium", formatted or "")
        self.assertTrue(agents["tuned"]["available"])
        self.assertFalse(agents["bad-model"]["available"])
        self.assertIn("valid model ID", str(agents["bad-model"]["message"]))
        self.assertFalse(agents["bad-effort"]["available"])
        self.assertIn("low, medium", str(agents["bad-effort"]["message"]))

    def test_main_profile_configures_model_and_effort_before_first_turn(self) -> None:
        client = ConfigurableClient([[{"type": "text", "text": "Profiled."}]])
        with tempfile.TemporaryDirectory(prefix="vibeagent-profile-model-") as base:
            root = Path(base)
            _write_agent(root, "tuned", model="claude-opus-5", effort="medium")

            result = run_agent(
                "Inspect",
                client,
                base_dir=root,
                agent="tuned",
                max_iterations=1,
                model_retries=0,
            )
            events = [
                json.loads(line)
                for line in root.joinpath(
                    ".vibeagent", "sessions", result.run_id, "events.jsonl"
                ).read_text(encoding="utf-8").splitlines()
            ]

        self.assertTrue(result.success)
        self.assertEqual(client.configurations, [("claude-opus-5", "medium")])
        self.assertEqual(client.completions, [("claude-opus-5", "medium")])
        loaded = next(event for event in events if event["type"] == "main_agent_profile_loaded")
        self.assertEqual((loaded["model"], loaded["effort"]), ("claude-opus-5", "medium"))

    def test_inherit_model_keeps_parent_model_while_applying_effort(self) -> None:
        client = ConfigurableClient(
            [[{"type": "text", "text": "Inherited."}]],
            model="parent-model",
        )
        with tempfile.TemporaryDirectory(prefix="vibeagent-profile-model-") as base:
            root = Path(base)
            _write_agent(root, "tuned", model="inherit", effort="low")

            run_agent(
                "Inspect",
                client,
                base_dir=root,
                agent="tuned",
                max_iterations=1,
                model_retries=0,
            )

        self.assertEqual(client.configurations, [(None, "low")])
        self.assertEqual(client.completions, [("parent-model", "low")])

    def test_subagent_profile_uses_configured_client_without_mutating_parent(self) -> None:
        client = ConfigurableClient([[{"type": "text", "text": "Reviewed."}]])
        with tempfile.TemporaryDirectory(prefix="vibeagent-profile-model-") as base:
            root = Path(base)
            _write_agent(root, "tuned", model="review-model", effort="high")
            workspace = create_run_workspace(root, "run-1")

            with patch.dict(
                "os.environ",
                {
                    "VIBEAGENT_SUBAGENT_MODEL": "",
                    "CLAUDE_CODE_SUBAGENT_MODEL": "environment-model",
                },
            ):
                result = execute_delegate_task_action(
                    workspace,
                    DelegateTaskAction(
                        type="delegate_task",
                        task="Review",
                        agent="tuned",
                    ),
                    client,
                    parent_iteration=1,
                    subagent_id="delegate-1-1",
                    max_output_tokens=1024,
                    model_retries=0,
                    model_retry_delay_ms=0,
                    model_timeout_ms=10_000,
                    command_timeout_ms=10_000,
                    logger=None,
                )

        self.assertTrue(result.ok)
        self.assertEqual(client.configurations, [("review-model", "high")])
        self.assertEqual(client.completions, [("review-model", "high")])
        self.assertIsNone(client.model)
        self.assertIsNone(client.effort)

    def test_environment_model_configures_unprofiled_subagent_and_audit_event(self) -> None:
        client = ConfigurableClient([[{"type": "text", "text": "Reviewed."}]])
        with tempfile.TemporaryDirectory(prefix="vibeagent-profile-model-") as base:
            root = Path(base)
            workspace = create_run_workspace(root, "run-env")
            with patch.dict(
                "os.environ",
                {
                    "VIBEAGENT_SUBAGENT_MODEL": "",
                    "CLAUDE_CODE_SUBAGENT_MODEL": "fast-review-model",
                },
            ):
                result = execute_delegate_task_action(
                    workspace,
                    DelegateTaskAction(type="delegate_task", task="Review"),
                    client,
                    parent_iteration=1,
                    subagent_id="delegate-env",
                    max_output_tokens=1024,
                    model_retries=0,
                    model_retry_delay_ms=0,
                    model_timeout_ms=10_000,
                    command_timeout_ms=10_000,
                    logger=None,
                )
            events = [
                json.loads(line)
                for line in (workspace.session_dir / "events.jsonl")
                .read_text(encoding="utf-8")
                .splitlines()
            ]

        self.assertTrue(result.ok)
        self.assertEqual(client.configurations, [("fast-review-model", None)])
        self.assertEqual(client.completions, [("fast-review-model", None)])
        started = next(event for event in events if event["type"] == "subagent_started")
        self.assertEqual(started["model"], "fast-review-model")
        self.assertEqual(started["model_source"], "CLAUDE_CODE_SUBAGENT_MODEL")

    def test_invocation_settings_environment_configures_subagent_model(self) -> None:
        client = ConfigurableClient([[{"type": "text", "text": "Reviewed."}]])
        with tempfile.TemporaryDirectory(prefix="vibeagent-profile-model-") as base:
            workspace = create_run_workspace(
                Path(base),
                "run-settings-env",
                setting_sources=(),
                settings_override_json=(
                    '{"env":{"CLAUDE_CODE_SUBAGENT_MODEL":"settings-model"}}'
                ),
            )
            with patch.dict("os.environ", {}, clear=True):
                result = execute_delegate_task_action(
                    workspace,
                    DelegateTaskAction(type="delegate_task", task="Review"),
                    client,
                    parent_iteration=1,
                    subagent_id="delegate-settings-env",
                    max_output_tokens=1024,
                    model_retries=0,
                    model_retry_delay_ms=0,
                    model_timeout_ms=10_000,
                    command_timeout_ms=10_000,
                    logger=None,
                )

        self.assertTrue(result.ok)
        self.assertEqual(client.configurations, [("settings-model", None)])
        self.assertEqual(client.completions, [("settings-model", None)])

    def test_profile_inherit_overrides_environment_model(self) -> None:
        client = ConfigurableClient(
            [[{"type": "text", "text": "Inherited."}]],
            model="parent-model",
        )
        with tempfile.TemporaryDirectory(prefix="vibeagent-profile-model-") as base:
            root = Path(base)
            _write_agent(root, "inherited", model="inherit")
            with patch.dict(
                "os.environ",
                {
                    "VIBEAGENT_SUBAGENT_MODEL": "",
                    "CLAUDE_CODE_SUBAGENT_MODEL": "environment-model",
                },
            ):
                result = execute_delegate_task_action(
                    create_run_workspace(root, "run-inherit"),
                    DelegateTaskAction(
                        type="delegate_task",
                        task="Review",
                        agent="inherited",
                    ),
                    client,
                    parent_iteration=1,
                    subagent_id="delegate-inherit",
                    max_output_tokens=1024,
                    model_retries=0,
                    model_retry_delay_ms=0,
                    model_timeout_ms=10_000,
                    command_timeout_ms=10_000,
                    logger=None,
                )

        self.assertTrue(result.ok)
        self.assertEqual(client.configurations, [])
        self.assertEqual(client.completions, [("parent-model", None)])

    def test_environment_model_applies_to_named_teammate(self) -> None:
        client = ConfigurableClient([[{"type": "text", "text": "Teammate done."}]])
        with tempfile.TemporaryDirectory(prefix="vibeagent-profile-model-") as base:
            root = Path(base)
            workspace = create_run_workspace(root, "run-teammate")
            with patch.dict(
                "os.environ",
                {
                    "VIBEAGENT_EXPERIMENTAL_AGENT_TEAMS": "1",
                    "VIBEAGENT_SUBAGENT_MODEL": "",
                    "CLAUDE_CODE_SUBAGENT_MODEL": "teammate-model",
                },
            ):
                result = execute_delegate_task_action(
                    workspace,
                    DelegateTaskAction(
                        type="delegate_task",
                        task="Review",
                        teammate_name="reviewer",
                    ),
                    client,
                    parent_iteration=1,
                    subagent_id="reviewer",
                    max_output_tokens=1024,
                    model_retries=0,
                    model_retry_delay_ms=0,
                    model_timeout_ms=10_000,
                    command_timeout_ms=10_000,
                    logger=None,
                )
            events = [
                json.loads(line)
                for line in (workspace.session_dir / "events.jsonl")
                .read_text(encoding="utf-8")
                .splitlines()
            ]

        self.assertTrue(result.ok)
        self.assertEqual(client.completions, [("teammate-model", None)])
        spawned = next(event for event in events if event["type"] == "teammate_spawned")
        self.assertEqual(spawned["model"], "teammate-model")
        self.assertEqual(spawned["model_source"], "CLAUDE_CODE_SUBAGENT_MODEL")

    def test_unsupported_profile_override_fails_before_model_request(self) -> None:
        client = BasicClient()
        with tempfile.TemporaryDirectory(prefix="vibeagent-profile-model-") as base:
            root = Path(base)
            _write_agent(root, "tuned", effort="low")
            with self.assertRaisesRegex(ValueError, "does not support"):
                run_agent("Inspect", client, base_dir=root, agent="tuned")

            result = execute_delegate_task_action(
                create_run_workspace(root, "run-2"),
                DelegateTaskAction(type="delegate_task", task="Review", agent="tuned"),
                client,
                parent_iteration=1,
                subagent_id="delegate-1-1",
                max_output_tokens=1024,
                model_retries=0,
                model_retry_delay_ms=0,
                model_timeout_ms=10_000,
                command_timeout_ms=10_000,
                logger=None,
            )

        self.assertFalse(result.ok)
        self.assertIn("does not support", result.message)
        self.assertEqual(client.calls, 0)

    def test_invalid_environment_model_fails_before_subagent_model_request(self) -> None:
        client = BasicClient()
        with tempfile.TemporaryDirectory(prefix="vibeagent-profile-model-") as base:
            with patch.dict(
                "os.environ",
                {
                    "VIBEAGENT_SUBAGENT_MODEL": "",
                    "CLAUDE_CODE_SUBAGENT_MODEL": "bad model",
                },
            ):
                result = execute_delegate_task_action(
                    create_run_workspace(Path(base), "run-invalid-env"),
                    DelegateTaskAction(type="delegate_task", task="Review"),
                    client,
                    parent_iteration=1,
                    subagent_id="delegate-invalid-env",
                    max_output_tokens=1024,
                    model_retries=0,
                    model_retry_delay_ms=0,
                    model_timeout_ms=10_000,
                    command_timeout_ms=10_000,
                    logger=None,
                )

        self.assertFalse(result.ok)
        self.assertIn("must be a valid model ID", result.message)
        self.assertEqual(client.calls, 0)


if __name__ == "__main__":
    unittest.main()
