from __future__ import annotations

import os
import socket
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

from vibeagent.action_parsing import ActionParseError
from vibeagent.actions import execute_action, parse_tool_action
from vibeagent.agent_approval import build_approval_request
from vibeagent.agent_tool_registry import tool_available_for_policy
from vibeagent.browser_runtime import MAX_BROWSER_OUTPUT_CHARS
from vibeagent.prompt_observation_runtime import format_runtime_observation
from vibeagent.tool_definitions import AGENT_TOOL_DEFINITIONS
from vibeagent.types import BrowserAction, BrowserObservation
from vibeagent.workspace import create_run_workspace


class BrowserToolContractTests(unittest.TestCase):
    def test_browser_tool_family_is_discoverable_and_hidden_in_plan_mode(self) -> None:
        names = {str(item["name"]) for item in AGENT_TOOL_DEFINITIONS}
        browser_names = {
            "browser_open",
            "browser_snapshot",
            "browser_act",
            "browser_read",
            "browser_screenshot",
            "browser_close",
        }
        self.assertTrue(browser_names <= names)
        for name in browser_names:
            self.assertFalse(tool_available_for_policy(name, "plan"), name)

    def test_parses_supported_browser_contracts(self) -> None:
        cases = [
            ("browser_open", {"url": "http://127.0.0.1:8000"}, "open"),
            ("browser_snapshot", {"interactive": True, "compact": True, "depth": 4}, "snapshot"),
            ("browser_act", {"operation": "fill", "selector": "@e1", "text": "hello"}, "fill"),
            ("browser_act", {"operation": "select", "selector": "@e2", "values": ["a", "b"]}, "select"),
            ("browser_act", {"operation": "wait", "milliseconds": 250}, "wait"),
            ("browser_read", {"operation": "get_attribute", "selector": "@e3", "attribute": "href"}, "get_attribute"),
            ("browser_read", {"operation": "console"}, "console"),
            ("browser_screenshot", {"path": "artifacts/page.png", "full": True}, "screenshot"),
            ("browser_close", {}, "close"),
        ]
        for name, payload, operation in cases:
            with self.subTest(name=name, operation=operation):
                action = parse_tool_action(name, payload)
                self.assertIsInstance(action, BrowserAction)
                self.assertEqual(action.operation, operation)
                self.assertIsNotNone(build_approval_request(action))

    def test_rejects_unsafe_or_incomplete_browser_inputs(self) -> None:
        cases = [
            ("browser_open", {"url": "file:///tmp/page.html"}, "http or https"),
            ("browser_open", {"url": "https://user:secret@example.com"}, "credentials"),
            ("browser_act", {"operation": "click"}, "requires selector"),
            ("browser_act", {"operation": "wait", "selector": "@e1", "milliseconds": 1}, "exactly one"),
            ("browser_act", {"operation": "scroll", "direction": "diagonal"}, "direction"),
            ("browser_read", {"operation": "get_attribute", "selector": "@e1"}, "requires attribute"),
            ("browser_screenshot", {"path": "page.svg"}, "must have no extension"),
        ]
        for name, payload, message in cases:
            with self.subTest(name=name, payload=payload):
                with self.assertRaisesRegex(ActionParseError, message):
                    parse_tool_action(name, payload)


class BrowserRuntimeTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory(prefix="vibeagent-browser-")
        self.root = Path(self.temp.name).resolve()
        self.workspace = create_run_workspace(self.root, "browser-test")

    def tearDown(self) -> None:
        self.temp.cleanup()

    def test_navigation_is_session_isolated_domain_limited_and_environment_scrubbed(self) -> None:
        calls: list[tuple[list[str], dict[str, object]]] = []

        def run(command, **kwargs):
            calls.append((command, kwargs))
            return subprocess.CompletedProcess(command, 0, "opened\n", "")

        host_environment = {
            "PATH": os.environ.get("PATH", ""),
            "HOME": os.environ.get("HOME", ""),
            "OPENAI_API_KEY": "secret",
            "HTTP_PROXY": "http://proxy.invalid",
            "AGENT_BROWSER_PROFILE": "Default",
            "AGENT_BROWSER_HEADED": "true",
        }
        with (
            patch("vibeagent.browser_runtime.shutil.which", return_value="/usr/bin/agent-browser"),
            patch("vibeagent.browser_runtime.subprocess.run", side_effect=run),
            patch.dict(os.environ, host_environment, clear=True),
        ):
            opened = execute_action(
                self.workspace,
                parse_tool_action("browser_open", {"url": "http://localhost:4173/login"}),
            )
            clicked = execute_action(
                self.workspace,
                parse_tool_action("browser_act", {"operation": "click", "selector": "@e2"}),
            )

        self.assertTrue(opened.ok)
        self.assertTrue(clicked.ok)
        self.assertEqual(len(calls), 2)
        first_command, first_kwargs = calls[0]
        second_command, _ = calls[1]
        self.assertIn("--session", first_command)
        self.assertIn("--config", first_command)
        self.assertEqual(first_command[first_command.index("--allowed-domains") + 1], "localhost")
        self.assertEqual(second_command[second_command.index("--allowed-domains") + 1], "localhost")
        environment = first_kwargs["env"]
        self.assertNotIn("OPENAI_API_KEY", environment)
        self.assertNotIn("HTTP_PROXY", environment)
        self.assertNotIn("AGENT_BROWSER_PROFILE", environment)
        self.assertEqual(environment["AGENT_BROWSER_HEADED"], "false")
        self.assertIn("/vab-", environment["AGENT_BROWSER_SOCKET_DIR"])
        self.assertTrue(environment["XDG_CACHE_HOME"].endswith("/browser/cache"))
        self.assertTrue(environment["XDG_RUNTIME_DIR"].endswith("/browser/runtime"))
        self.assertIs(subprocess.DEVNULL, first_kwargs["stdin"])

    def test_runtime_maps_operations_and_bounds_output(self) -> None:
        completed = subprocess.CompletedProcess(["agent-browser"], 0, "x" * (MAX_BROWSER_OUTPUT_CHARS + 50), "")
        with (
            patch("vibeagent.browser_runtime.shutil.which", return_value="agent-browser"),
            patch("vibeagent.browser_runtime.subprocess.run", return_value=completed) as run,
        ):
            observation = execute_action(
                self.workspace,
                parse_tool_action(
                    "browser_read",
                    {"operation": "get_attribute", "selector": "@e1", "attribute": "href"},
                ),
            )

        command = run.call_args.args[0]
        self.assertEqual(command[-4:], ["get", "attr", "@e1", "href"])
        self.assertTrue(observation.ok)
        self.assertTrue(observation.output_truncated)
        self.assertLessEqual(len(observation.output), MAX_BROWSER_OUTPUT_CHARS + 40)
        formatted = format_runtime_observation(1, observation) or ""
        self.assertIn("browser get_attribute", formatted)
        self.assertIn("untrusted external browser/page content", formatted)

    def test_runtime_rewrites_config_and_rejects_invalid_domain_state(self) -> None:
        runtime_dir = self.workspace.session_dir / "browser"
        runtime_dir.mkdir(parents=True)
        (runtime_dir / "config.json").write_text('{"profile":"Default"}', encoding="utf-8")
        (runtime_dir / "domains.json").write_text('["*.example.com"]', encoding="utf-8")
        with (
            patch("vibeagent.browser_runtime.shutil.which", return_value="agent-browser"),
            patch("vibeagent.browser_runtime.subprocess.run") as run,
        ):
            observation = execute_action(
                self.workspace,
                parse_tool_action("browser_snapshot", {}),
            )

        self.assertFalse(observation.ok)
        self.assertIn("allowed-domain state is invalid", observation.error or "")
        self.assertEqual((runtime_dir / "config.json").read_text(encoding="utf-8"), "{}")
        run.assert_not_called()

    def test_navigation_rejects_link_local_and_mixed_scope_resolution(self) -> None:
        action = parse_tool_action("browser_open", {"url": "http://example.test"})
        with (
            patch("vibeagent.browser_runtime.shutil.which", return_value="agent-browser"),
            patch(
                "vibeagent.browser_runtime.socket.getaddrinfo",
                return_value=[(socket.AF_INET, socket.SOCK_STREAM, 6, "", ("169.254.169.254", 80))],
            ),
            patch("vibeagent.browser_runtime.subprocess.run") as run,
        ):
            link_local = execute_action(self.workspace, action)
        self.assertFalse(link_local.ok)
        self.assertIn("link-local", link_local.error or "")
        run.assert_not_called()

        with (
            patch("vibeagent.browser_runtime.shutil.which", return_value="agent-browser"),
            patch(
                "vibeagent.browser_runtime.socket.getaddrinfo",
                return_value=[
                    (socket.AF_INET, socket.SOCK_STREAM, 6, "", ("127.0.0.1", 80)),
                    (socket.AF_INET, socket.SOCK_STREAM, 6, "", ("8.8.8.8", 80)),
                ],
            ),
            patch("vibeagent.browser_runtime.subprocess.run") as run,
        ):
            mixed = execute_action(self.workspace, action)
        self.assertFalse(mixed.ok)
        self.assertIn("consistently", mixed.error or "")
        run.assert_not_called()

    def test_screenshot_is_atomically_written_inside_workspace(self) -> None:
        def run(command, **_kwargs):
            Path(command[-1]).write_bytes(b"\x89PNG\r\n\x1a\nimage")
            return subprocess.CompletedProcess(command, 0, "saved", "")

        with (
            patch("vibeagent.browser_runtime.shutil.which", return_value="agent-browser"),
            patch("vibeagent.browser_runtime.subprocess.run", side_effect=run),
        ):
            observation = execute_action(
                self.workspace,
                parse_tool_action("browser_screenshot", {"path": "artifacts/page", "full": True}),
            )

        self.assertTrue(observation.ok)
        self.assertEqual(observation.path, "artifacts/page")
        self.assertEqual((self.root / "artifacts/page").read_bytes(), b"\x89PNG\r\n\x1a\nimage")
        self.assertEqual(list((self.root / "artifacts").glob(".vibeagent-browser-*")), [])

    def test_screenshot_rejects_protected_and_symlink_paths_before_launch(self) -> None:
        outside = self.root.parent / f"{self.root.name}-outside.png"
        link = self.root / "linked.png"
        link.symlink_to(outside)
        with (
            patch("vibeagent.browser_runtime.shutil.which", return_value="agent-browser"),
            patch("vibeagent.browser_runtime.subprocess.run") as run,
        ):
            protected = execute_action(
                self.workspace,
                parse_tool_action("browser_screenshot", {"path": ".vibeagent/page.png"}),
            )
            symlinked = execute_action(
                self.workspace,
                parse_tool_action("browser_screenshot", {"path": "linked.png"}),
            )

        self.assertFalse(protected.ok)
        self.assertFalse(symlinked.ok)
        self.assertIn("protected", protected.error or "")
        self.assertIn("project directory", symlinked.error or "")
        run.assert_not_called()

    def test_missing_browser_dependency_is_a_structured_failure(self) -> None:
        action = parse_tool_action("browser_snapshot", {})
        with patch("vibeagent.browser_runtime.shutil.which", return_value=None):
            observation = execute_action(self.workspace, action)
        self.assertIsInstance(observation, BrowserObservation)
        self.assertFalse(observation.ok)
        self.assertIn("not installed", observation.error or "")


if __name__ == "__main__":
    unittest.main()
