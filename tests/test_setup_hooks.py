from __future__ import annotations

from contextlib import redirect_stdout
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from tests.user_home_test_case import IsolatedUserHomeTestCase
from vibeagent import cli as cli_module
from vibeagent.agent import run_agent
from vibeagent.types import ApprovalDecision, AssistantResponse, ChatMessage, ContentBlock
from vibeagent.workspace import create_run_workspace
from vibeagent.workspace_hooks import read_project_hooks


HOOK_SCRIPT = """from __future__ import annotations
import json
import os
from pathlib import Path
import sys

payload = json.load(sys.stdin)
with Path('setup-inputs.jsonl').open('a', encoding='utf-8') as stream:
    stream.write(json.dumps(payload, sort_keys=True) + '\\n')
if payload['hook_event_name'] == 'Setup':
    with Path(os.environ['CLAUDE_ENV_FILE']).open('a', encoding='utf-8') as stream:
        stream.write('export SETUP_HOOK_VALUE=ready\\n')
    print(json.dumps({'hookSpecificOutput': {
        'hookEventName': 'Setup',
        'additionalContext': 'Setup dependencies are ready.',
    }}))
"""


def _write_setup_hooks(root: Path) -> None:
    (root / "setup-hook.py").write_text(HOOK_SCRIPT, encoding="utf-8")
    config = root / ".vibeagent/hooks.json"
    config.parent.mkdir(parents=True)
    config.write_text(
        json.dumps(
            {
                "Setup": [
                    {
                        "matcher": "init|maintenance",
                        "hooks": [
                            {"type": "command", "command": "python3 setup-hook.py"}
                        ],
                    }
                ],
                "SessionStart": [
                    {
                        "matcher": "startup",
                        "hooks": [
                            {"type": "command", "command": "python3 setup-hook.py"}
                        ],
                    }
                ],
            }
        ),
        encoding="utf-8",
    )


def _approve(_request) -> ApprovalDecision:
    return ApprovalDecision(True, "approved")


class _Client:
    def __init__(self) -> None:
        self.messages: list[list[ChatMessage]] = []

    def complete(
        self,
        messages: list[ChatMessage],
        tools=None,
        max_tokens=4096,
        temperature=0.2,
        timeout_ms=120_000,
    ) -> AssistantResponse:
        self.messages.append(list(messages))
        content: list[ContentBlock] = [{"type": "text", "text": "done"}]
        return AssistantResponse(content=content, raw={"content": content})


class SetupHookTests(IsolatedUserHomeTestCase):
    def test_print_init_and_maintenance_arguments_select_setup_trigger(self) -> None:
        init_args = cli_module.parse_args(["-p", "--init", "inspect project"])
        maintenance_args = cli_module.parse_args(
            ["-p", "--maintenance", "update dependencies"]
        )
        local_init_args = cli_module.parse_args(["--init"])
        conflict_args = cli_module.parse_args(
            ["-p", "--maintenance", "--init", "inspect"]
        )

        self.assertEqual(init_args.task, ["inspect project"])
        self.assertIsNone(init_args.init)
        self.assertEqual(init_args.setup_trigger, "init")
        self.assertFalse(cli_module.has_local_flag(init_args))
        self.assertIsNone(cli_module.validate_cli_args(init_args))
        self.assertEqual(
            cli_module.build_one_shot_kwargs_from_args(init_args)["setup_trigger"],
            "init",
        )
        self.assertEqual(maintenance_args.setup_trigger, "maintenance")
        self.assertIsNone(cli_module.validate_cli_args(maintenance_args))
        self.assertEqual(local_init_args.init, "")
        self.assertTrue(cli_module.has_local_flag(local_init_args))
        self.assertIsNone(cli_module.validate_cli_args(local_init_args))
        self.assertEqual(
            cli_module.validate_cli_args(conflict_args),
            "--init and --maintenance cannot be combined.",
        )

    def test_maintenance_requires_print_mode_coding_task(self) -> None:
        no_print = cli_module.parse_args(["--maintenance", "inspect"])
        no_task = cli_module.parse_args(["-p", "--maintenance"])
        chat = cli_module.parse_args(["-p", "--maintenance", "--chat", "hello"])

        for args in (no_print, no_task, chat):
            with self.subTest(args=args):
                self.assertEqual(
                    cli_module.validate_cli_args(args),
                    "--maintenance requires a one-shot coding task with --print.",
                )

    def test_setup_rejects_http_and_model_handlers(self) -> None:
        invalid_handlers = (
            {"type": "http", "url": "https://example.com/hook"},
            {"type": "prompt", "prompt": "prepare"},
            {"type": "agent", "prompt": "prepare"},
        )
        for handler in invalid_handlers:
            with self.subTest(handler=handler), tempfile.TemporaryDirectory(
                prefix="vibeagent-setup-"
            ) as base:
                root = Path(base)
                config = root / ".vibeagent/hooks.json"
                config.parent.mkdir()
                config.write_text(
                    json.dumps(
                        {
                            "Setup": [
                                {"matcher": "init", "hooks": [handler]}
                            ]
                        }
                    ),
                    encoding="utf-8",
                )
                hooks = read_project_hooks(create_run_workspace(root))

            self.assertIsNotNone(hooks.error)
            self.assertIn("command or mcp_tool", hooks.error or "")

    def test_setup_context_and_environment_reach_print_mode_agent(self) -> None:
        client = _Client()
        with tempfile.TemporaryDirectory(prefix="vibeagent-setup-") as base:
            root = Path(base)
            _write_setup_hooks(root)

            result = run_agent(
                "inspect setup",
                client=client,
                base_dir=root,
                max_iterations=1,
                approval_handler=_approve,
                setup_trigger="maintenance",
            )
            inputs = [
                json.loads(line)
                for line in (root / "setup-inputs.jsonl")
                .read_text(encoding="utf-8")
                .splitlines()
            ]
            environment = (
                root / ".vibeagent/sessions" / result.run_id / "environment.sh"
            ).read_text(encoding="utf-8")

        self.assertTrue(result.success, result.message)
        self.assertEqual([item["hook_event_name"] for item in inputs], ["Setup", "SessionStart"])
        self.assertEqual(inputs[0]["trigger"], "maintenance")
        self.assertEqual(inputs[1]["source"], "startup")
        self.assertIn("export SETUP_HOOK_VALUE=ready", environment)
        initial_user = client.messages[0][1].content
        self.assertIsInstance(initial_user, str)
        self.assertIn("Setup hook context:\nSetup dependencies are ready.", initial_user)

    def test_setup_plain_stdout_is_debug_only_and_exit_two_cannot_block(self) -> None:
        client = _Client()
        with tempfile.TemporaryDirectory(prefix="vibeagent-setup-") as base:
            root = Path(base)
            config = root / ".vibeagent/hooks.json"
            config.parent.mkdir()
            config.write_text(
                json.dumps(
                    {
                        "Setup": [
                            {
                                "matcher": "init",
                                "hooks": [
                                    {
                                        "type": "command",
                                        "command": (
                                            "python3 -c \"import sys; "
                                            "print('debug setup output'); "
                                            "print('setup warning', file=sys.stderr); "
                                            "raise SystemExit(2)\""
                                        ),
                                    }
                                ],
                            }
                        ]
                    }
                ),
                encoding="utf-8",
            )

            result = run_agent(
                "continue after setup",
                client=client,
                base_dir=root,
                max_iterations=1,
                approval_handler=_approve,
                setup_trigger="init",
            )

        self.assertTrue(result.success, result.message)
        initial_user = client.messages[0][1].content
        self.assertIsInstance(initial_user, str)
        self.assertNotIn("debug setup output", initial_user)
        self.assertNotIn("setup warning", initial_user)

    def test_init_only_runs_setup_then_session_start_without_model(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-setup-") as base:
            root = Path(base)
            _write_setup_hooks(root)
            stdout = io.StringIO()

            with patch("vibeagent.cli.create_chat_client") as create_client, redirect_stdout(stdout):
                exit_code = cli_module.main(
                    ["--cwd", base, "--approval", "allow", "--init-only", "--json"]
                )
            payload = json.loads(stdout.getvalue())
            inputs = [
                json.loads(line)
                for line in (root / "setup-inputs.jsonl")
                .read_text(encoding="utf-8")
                .splitlines()
            ]
            session_id = payload["setup"]["sessionId"]
            environment = (
                root / ".vibeagent/sessions" / session_id / "environment.sh"
            ).read_text(encoding="utf-8")

        self.assertEqual(exit_code, 0)
        self.assertTrue(payload["success"])
        self.assertEqual(payload["setup"]["trigger"], "init")
        self.assertEqual(payload["setup"]["setupHooks"], 1)
        self.assertEqual(payload["setup"]["sessionStartHooks"], 1)
        self.assertEqual(payload["setup"]["failedHooks"], 0)
        self.assertEqual([item["hook_event_name"] for item in inputs], ["Setup", "SessionStart"])
        self.assertEqual(inputs[0]["trigger"], "init")
        self.assertEqual(inputs[1]["source"], "startup")
        self.assertIn("export SETUP_HOOK_VALUE=ready", environment)
        create_client.assert_not_called()


if __name__ == "__main__":
    unittest.main()
