import json
import tempfile
import unittest
from pathlib import Path

from vibeagent.commands import (
    LocalCommand,
    get_last_session_text,
    get_model_text,
    get_resume_context,
    get_session_text,
    get_sessions_text,
    is_exit_command,
    parse_local_command,
)


class CommandTests(unittest.TestCase):
    def test_is_exit_command_only_treats_exit_as_the_exit_command(self) -> None:
        self.assertTrue(is_exit_command("/exit"))
        self.assertTrue(is_exit_command("  /exit  "))
        self.assertFalse(is_exit_command("exit"))
        self.assertFalse(is_exit_command("/quit"))
        self.assertFalse(is_exit_command("/exit now"))

    def test_parse_local_command_recognizes_local_commands(self) -> None:
        self.assertEqual(parse_local_command("/help"), LocalCommand(type="help"))
        self.assertEqual(parse_local_command("  /model  "), LocalCommand(type="model"))
        self.assertEqual(parse_local_command("/approval"), LocalCommand(type="approval"))
        self.assertEqual(parse_local_command("/approval allow"), LocalCommand(type="approval", argument="allow"))
        self.assertEqual(parse_local_command("/sessions"), LocalCommand(type="sessions"))
        self.assertEqual(parse_local_command("/last"), LocalCommand(type="last"))
        self.assertEqual(parse_local_command("/session run-1"), LocalCommand(type="session", argument="run-1"))
        self.assertEqual(parse_local_command("/session"), LocalCommand(type="session"))
        self.assertEqual(parse_local_command("/resume run-1"), LocalCommand(type="resume", argument="run-1"))
        self.assertEqual(parse_local_command("/resume off"), LocalCommand(type="resume", argument="off"))
        self.assertEqual(parse_local_command("/resume"), LocalCommand(type="resume"))
        self.assertEqual(parse_local_command("/exit"), LocalCommand(type="exit"))
        self.assertEqual(parse_local_command("/chat"), LocalCommand(type="chat"))
        self.assertEqual(parse_local_command("/chat 你好"), LocalCommand(type="chat", argument="你好"))
        self.assertEqual(parse_local_command("/code"), LocalCommand(type="code"))
        self.assertEqual(parse_local_command("/code write a script"), LocalCommand(type="code", argument="write a script"))
        self.assertIsNone(parse_local_command("write a script"))

    def test_help_text_lists_approval_command(self) -> None:
        from vibeagent.commands import get_help_text

        self.assertIn("/approval [ask|allow|deny]", get_help_text())
        self.assertIn("/resume [run-id|off]", get_help_text())

    def test_get_model_text_reports_model_configuration_without_exposing_the_key(self) -> None:
        text = get_model_text(
            {
                "VIBEAGENT_PROVIDER": "minimax",
                "MINIMAX_API_KEY": "secret-key",
                "MINIMAX_MODEL": "custom-model",
                "MINIMAX_BASE_URL": "https://example.com/v1/",
            }
        )

        self.assertIn("Model provider: minimax", text)
        self.assertIn("model: custom-model", text)
        self.assertIn("baseUrl: https://example.com/v1", text)
        self.assertIn("apiKey: configured via MINIMAX_API_KEY", text)
        self.assertNotIn("secret-key", text)

    def test_get_model_text_reports_deepseek_configuration(self) -> None:
        text = get_model_text(
            {
                "VIBEAGENT_PROVIDER": "deepseek",
                "DEEPSEEK_API_KEY": "secret-key",
                "DEEPSEEK_MODEL": "deepseek-reasoner",
            }
        )

        self.assertIn("Model provider: deepseek", text)
        self.assertIn("model: deepseek-reasoner", text)
        self.assertIn("baseUrl: https://api.deepseek.com", text)
        self.assertIn("apiKey: configured via DEEPSEEK_API_KEY", text)
        self.assertNotIn("secret-key", text)

    def test_session_commands_render_compact_session_output(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-commands-") as base:
            root = Path(base)
            session_dir = root / ".vibeagent" / "sessions" / "run-1"
            session_dir.mkdir(parents=True)
            (session_dir / "events.jsonl").write_text(
                "\n".join(
                    [
                        json.dumps({"type": "task", "task": "Build a CLI."}),
                        json.dumps(
                            {
                                "type": "tool_result",
                                "iteration": 1,
                                "name": "finish",
                                "result": {"kind": "finish", "message": "Done."},
                            }
                        ),
                    ]
                )
                + "\n",
                encoding="utf-8",
            )

            sessions_text = get_sessions_text(root)
            session_text = get_session_text("run-1", root)
            last_text = get_last_session_text(root)
            selected, context, resume_text = get_resume_context(None, root)

        self.assertIn("run-1", sessions_text)
        self.assertIn("Session: run-1", session_text)
        self.assertIn("status: completed", session_text)
        self.assertIn("task: Build a CLI.", session_text)
        self.assertIn("final: Done.", last_text)
        self.assertEqual(selected, "run-1")
        self.assertIn("task: Build a CLI.", context or "")
        self.assertIn("final: Done.", context or "")
        self.assertEqual(resume_text, "Resume context loaded from session run-1.")

    def test_session_command_requires_run_id(self) -> None:
        self.assertEqual(get_session_text(None), "Usage: /session <run-id>")

    def test_session_command_rejects_path_like_run_id(self) -> None:
        self.assertEqual(get_session_text("../bad"), "Invalid session id: ../bad")
        self.assertEqual(get_resume_context("../bad")[2], "Invalid session id: ../bad")
        self.assertEqual(get_resume_context("off"), (None, None, "Resume context cleared."))


if __name__ == "__main__":
    unittest.main()
