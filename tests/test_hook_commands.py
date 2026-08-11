from __future__ import annotations

from contextlib import redirect_stdout
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from tests.user_home_test_case import IsolatedUserHomeTestCase
from vibeagent import commands
from vibeagent.cli import main
from vibeagent.cli_project_interactive_commands import run_interactive_project_command
from vibeagent.command_parsing import LocalCommand, parse_local_command
from vibeagent.hook_commands import format_hooks_report_text, get_hooks_report


def _write_hooks(root: Path, payload: dict[str, object]) -> None:
    path = root / ".vibeagent/hooks.json"
    path.parent.mkdir(parents=True)
    path.write_text(json.dumps(payload), encoding="utf-8")


def _hook_payload() -> dict[str, object]:
    return {
        "PreToolUse": [
            {
                "matcher": "Bash",
                "hooks": [
                    {
                        "type": "command",
                        "command": "API_KEY=supersecretvalue python3 check.py",
                        "timeout_ms": 1234,
                        "async": True,
                    }
                ],
            }
        ],
        "Notification": [
            {
                "matcher": "permission_prompt",
                "hooks": [
                    {
                        "type": "http",
                        "url": "https://example.com/hook?token=urlsecretvalue",
                        "headers": {
                            "Authorization": "Bearer headersecretvalue",
                            "X-Project": "demo",
                        },
                        "allowedEnvVars": ["HOOK_TOKEN"],
                    }
                ],
            }
        ],
        "Setup": [
            {
                "matcher": "init",
                "hooks": [
                    {
                        "type": "mcp_tool",
                        "server": "bootstrap",
                        "tool": "prepare",
                        "input": {"path": "private-path", "mode": "fast"},
                    }
                ],
            }
        ],
    }


class HookCommandTests(IsolatedUserHomeTestCase):
    def test_report_lists_resolved_handlers_without_secret_values(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-hooks-report-") as base:
            root = Path(base)
            _write_hooks(root, _hook_payload())

            report = get_hooks_report(root)
            text = format_hooks_report_text(report)

        self.assertTrue(report["ok"])
        self.assertTrue(report["enabled"])
        self.assertEqual(report["count"], 3)
        self.assertEqual(
            report["events"],
            [
                {"event": "Notification", "count": 1},
                {"event": "PreToolUse", "count": 1},
                {"event": "Setup", "count": 1},
            ],
        )
        handlers = report["hooks"]
        self.assertIsInstance(handlers, list)
        command = next(item for item in handlers if item["handlerType"] == "command")
        http = next(item for item in handlers if item["handlerType"] == "http")
        mcp = next(item for item in handlers if item["handlerType"] == "mcp_tool")
        self.assertEqual(command["target"], "API_KEY=[REDACTED] python3 check.py")
        self.assertEqual(command["timeoutMs"], 1234)
        self.assertTrue(command["async"])
        self.assertEqual(http["headerNames"], ["Authorization", "X-Project"])
        self.assertEqual(http["allowedEnvVars"], ["HOOK_TOKEN"])
        self.assertEqual(http["target"], "https://example.com/hook?token=[REDACTED]")
        self.assertEqual(mcp["target"], "bootstrap/prepare")
        self.assertEqual(mcp["inputKeys"], ["mode", "path"])
        serialized = json.dumps(report)
        for secret in (
            "supersecretvalue",
            "urlsecretvalue",
            "headersecretvalue",
            "private-path",
        ):
            self.assertNotIn(secret, serialized)
            self.assertNotIn(secret, text)
        self.assertIn("PreToolUse matcher='Bash' type=command", text)
        self.assertIn("headerNames: Authorization, X-Project", text)

    def test_invalid_configuration_is_visible_and_nonzero_for_cli(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-hooks-report-") as base:
            root = Path(base)
            _write_hooks(root, {"Setup": [{"matcher": "init", "hooks": []}]})
            report = get_hooks_report(root)
            stdout = io.StringIO()

            with redirect_stdout(stdout):
                exit_code = main(["--cwd", base, "--hooks", "--json"])
            payload = json.loads(stdout.getvalue())

        self.assertFalse(report["ok"])
        self.assertEqual(report["count"], 0)
        self.assertIn("non-empty hooks list", report["error"])
        self.assertEqual(exit_code, 1)
        self.assertFalse(payload["success"])
        self.assertIn("non-empty hooks list", payload["hooks"]["error"])

    def test_hooks_flag_is_provider_free(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-hooks-report-") as base:
            root = Path(base)
            _write_hooks(root, _hook_payload())
            stdout = io.StringIO()

            with (
                patch("vibeagent.cli.create_chat_client") as create_client,
                redirect_stdout(stdout),
            ):
                exit_code = main(["--cwd", base, "--hooks", "--json"])
            payload = json.loads(stdout.getvalue())

        self.assertEqual(exit_code, 0)
        self.assertTrue(payload["success"])
        self.assertEqual(payload["hooks"]["count"], 3)
        create_client.assert_not_called()

    def test_hooks_slash_command_is_parsed_and_dispatched(self) -> None:
        command = parse_local_command("/hooks")
        self.assertEqual(command, LocalCommand(type="hooks"))
        self.assertIsNone(parse_local_command("/hooks extra"))

        output = run_interactive_project_command(
            command,
            {"get_hooks_text": lambda: "resolved hooks"},
            "ask",
        )

        self.assertEqual(output, "resolved hooks")
        self.assertIn("/hooks", commands.get_help_text())


if __name__ == "__main__":
    unittest.main()
