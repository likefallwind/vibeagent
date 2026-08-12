import json
import tempfile
import unittest
from contextlib import redirect_stderr
import io
from pathlib import Path
from unittest.mock import patch

from vibeagent.agent import run_agent
from vibeagent.agent_delegate import execute_delegate_task_action
from vibeagent.cli_args import parse_args
from vibeagent.cli_validation import validate_cli_args
from vibeagent.interactive_background import create_interactive_background_request
from vibeagent.prompts import BROWSER_SYSTEM_PROMPT, build_messages
from vibeagent.tool_definition_browser import BROWSER_TOOL_NAMES
from vibeagent.types import AssistantResponse, DelegateTaskAction
from vibeagent.workspace_core import create_run_workspace


class RecordingClient:
    def __init__(self, responses):
        self.responses = list(responses)
        self.tools = []

    def complete(self, messages, tools=None, **kwargs):
        self.tools.append(list(tools or []))
        content = self.responses[len(self.tools) - 1]
        return AssistantResponse(content=content, raw={"content": content})


class BrowserModeTests(unittest.TestCase):
    def test_cli_flags_are_mutually_exclusive(self) -> None:
        self.assertEqual(parse_args(["--chrome", "inspect"]).browser_mode, "enabled")
        self.assertEqual(parse_args(["--no-chrome", "inspect"]).browser_mode, "disabled")
        self.assertEqual(parse_args(["inspect"]).browser_mode, "auto")
        with redirect_stderr(io.StringIO()), self.assertRaises(SystemExit):
            parse_args(["--chrome", "--no-chrome", "inspect"])
        self.assertEqual(
            validate_cli_args(parse_args(["--chrome", "--chat", "hello"])),
            "--chrome and --no-chrome are available for coding sessions only.",
        )
        self.assertEqual(
            validate_cli_args(parse_args(["--no-chrome", "--status"])),
            "--chrome and --no-chrome are available for coding sessions only.",
        )

    def test_workspace_rejects_invalid_browser_mode(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-browser-mode-") as base, self.assertRaisesRegex(
            ValueError, "browser_mode must be"
        ):
            create_run_workspace(base, browser_mode="invalid")  # type: ignore[arg-type]

    def test_chrome_eagerly_exposes_browser_tools_and_records_mode(self) -> None:
        client = RecordingClient([[{"type": "text", "text": "Done."}]])
        with tempfile.TemporaryDirectory(prefix="vibeagent-browser-mode-") as base, patch(
            "vibeagent.agent_run_setup.browser_runtime_available", return_value=True
        ):
            root = Path(base)
            result = run_agent(
                "Inspect the UI",
                client=client,
                base_dir=root,
                max_iterations=1,
                browser_mode="enabled",
            )
            events = [
                json.loads(line)
                for line in (root / ".vibeagent" / "sessions" / result.run_id / "events.jsonl")
                .read_text(encoding="utf-8")
                .splitlines()
            ]

        names = {str(tool["name"]) for tool in client.tools[0]}
        self.assertTrue(BROWSER_TOOL_NAMES <= names)
        event = next(item for item in events if item["type"] == "browser_mode")
        self.assertEqual(event["mode"], "enabled")
        self.assertTrue(event["runtime_available"])
        self.assertEqual(set(event["active_tools"]), BROWSER_TOOL_NAMES)

    def test_chrome_fails_before_model_request_when_runtime_is_missing(self) -> None:
        client = RecordingClient([[{"type": "text", "text": "unused"}]])
        with tempfile.TemporaryDirectory(prefix="vibeagent-browser-mode-") as base, patch(
            "vibeagent.agent_run_setup.browser_runtime_available", return_value=False
        ), self.assertRaisesRegex(ValueError, "requires agent-browser"):
            run_agent(
                "Inspect the UI",
                client=client,
                base_dir=Path(base),
                browser_mode="enabled",
            )

        self.assertEqual(client.tools, [])

    def test_chrome_respects_tool_ceiling_and_plan_mode(self) -> None:
        def visible_names(*, approval_policy="ask", tool_names=None) -> set[str]:
            client = RecordingClient([[{"type": "text", "text": "Done."}]])
            with tempfile.TemporaryDirectory(prefix="vibeagent-browser-mode-") as base, patch(
                "vibeagent.agent_run_setup.browser_runtime_available", return_value=True
            ):
                run_agent(
                    "Inspect the UI",
                    client=client,
                    base_dir=Path(base),
                    max_iterations=1,
                    browser_mode="enabled",
                    approval_policy=approval_policy,
                    tool_names=tool_names,
                )
            return {str(tool["name"]) for tool in client.tools[0]}

        self.assertTrue(
            BROWSER_TOOL_NAMES.isdisjoint(
                visible_names(tool_names=frozenset({"Read", "read_file"}))
            )
        )
        self.assertTrue(BROWSER_TOOL_NAMES.isdisjoint(visible_names(approval_policy="plan")))

    def test_no_chrome_blocks_search_activation_and_direct_calls(self) -> None:
        client = RecordingClient(
            [
                [{"type": "tool_call", "id": "search-1", "name": "ToolSearch", "input": {"query": "browser"}}],
                [{"type": "tool_call", "id": "browser-1", "name": "browser_open", "input": {"url": "http://localhost:3000"}}],
                [{"type": "text", "text": "Done."}],
            ]
        )
        with tempfile.TemporaryDirectory(prefix="vibeagent-browser-mode-") as base:
            result = run_agent(
                "Inspect without a browser",
                client=client,
                base_dir=Path(base),
                max_iterations=3,
                browser_mode="disabled",
            )

        for tools in client.tools:
            names = {str(tool["name"]) for tool in tools}
            self.assertTrue(BROWSER_TOOL_NAMES.isdisjoint(names))
        search = next(item for item in result.observations if item.kind == "tool_search")
        self.assertTrue(all(str(match.get("name")) not in BROWSER_TOOL_NAMES for match in search.matches))
        self.assertTrue(any(item.kind == "tool_error" for item in result.observations))

    def test_no_chrome_removes_browser_prompt_guidance(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-browser-mode-") as base:
            root = Path(base)
            automatic = create_run_workspace(root, browser_mode="auto")
            disabled = create_run_workspace(root, browser_mode="disabled")

            automatic_prompt = str(build_messages("Inspect", automatic)[0].content)
            disabled_prompt = str(build_messages("Inspect", disabled)[0].content)

        self.assertIn(BROWSER_SYSTEM_PROMPT, automatic_prompt)
        self.assertNotIn(BROWSER_SYSTEM_PROMPT, disabled_prompt)

    def test_code_subagents_inherit_browser_tool_policy(self) -> None:
        def delegate_tools(mode: str) -> set[str]:
            client = RecordingClient([[{"type": "text", "text": "Done."}]])
            with tempfile.TemporaryDirectory(prefix="vibeagent-browser-subagent-") as base:
                workspace = create_run_workspace(base, browser_mode=mode)
                result = execute_delegate_task_action(
                    workspace,
                    DelegateTaskAction(type="delegate_task", task="Inspect UI", mode="code"),
                    client,
                    parent_iteration=1,
                    subagent_id="browser-agent",
                    max_output_tokens=1024,
                    model_retries=0,
                    model_retry_delay_ms=0,
                    model_timeout_ms=10_000,
                    command_timeout_ms=10_000,
                    logger=None,
                )
                self.assertTrue(result.ok)
            return {str(tool["name"]) for tool in client.tools[0]}

        self.assertTrue(BROWSER_TOOL_NAMES <= delegate_tools("enabled"))
        self.assertTrue(BROWSER_TOOL_NAMES.isdisjoint(delegate_tools("disabled")))

    def test_background_handoff_preserves_browser_mode(self) -> None:
        common = {
            "approval_policy": "ask",
            "model": None,
            "agent": None,
            "dynamic_agent_profiles": (),
            "effort": None,
            "autocompact_tokens": None,
            "system_prompt": None,
            "append_system_prompt": None,
            "additional_directories": (),
        }
        enabled = create_interactive_background_request(
            Path("/project"), "run-1", None, browser_mode="enabled", **common
        )
        disabled = create_interactive_background_request(
            Path("/project"), "run-2", None, browser_mode="disabled", **common
        )

        self.assertIn("--chrome", enabled.argv)
        self.assertIn("--no-chrome", disabled.argv)


if __name__ == "__main__":
    unittest.main()
