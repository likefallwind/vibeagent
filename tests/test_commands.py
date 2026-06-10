import json
import tempfile
import unittest
from pathlib import Path

from vibeagent.commands import (
    LocalCommand,
    get_compact_context,
    get_context_text,
    get_cost_text,
    get_doctor_text,
    get_last_session_text,
    get_model_text,
    get_resume_context,
    get_session_text,
    get_sessions_text,
    get_status_text,
    get_usage_text,
    init_project_instructions,
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
        self.assertEqual(parse_local_command("/status"), LocalCommand(type="status"))
        self.assertEqual(parse_local_command("/context"), LocalCommand(type="context"))
        self.assertEqual(parse_local_command("/init"), LocalCommand(type="init"))
        self.assertEqual(parse_local_command("/doctor"), LocalCommand(type="doctor"))
        self.assertEqual(parse_local_command("/clear"), LocalCommand(type="clear"))
        self.assertEqual(parse_local_command("/usage"), LocalCommand(type="usage"))
        self.assertEqual(parse_local_command("/cost"), LocalCommand(type="cost"))
        self.assertEqual(parse_local_command("/approval"), LocalCommand(type="approval"))
        self.assertEqual(parse_local_command("/approval allow"), LocalCommand(type="approval", argument="allow"))
        self.assertEqual(parse_local_command("/sessions"), LocalCommand(type="sessions"))
        self.assertEqual(parse_local_command("/last"), LocalCommand(type="last"))
        self.assertEqual(parse_local_command("/session run-1"), LocalCommand(type="session", argument="run-1"))
        self.assertEqual(parse_local_command("/session"), LocalCommand(type="session"))
        self.assertEqual(parse_local_command("/resume run-1"), LocalCommand(type="resume", argument="run-1"))
        self.assertEqual(parse_local_command("/resume off"), LocalCommand(type="resume", argument="off"))
        self.assertEqual(parse_local_command("/resume"), LocalCommand(type="resume"))
        self.assertEqual(parse_local_command("/compact run-1"), LocalCommand(type="compact", argument="run-1"))
        self.assertEqual(parse_local_command("/compact"), LocalCommand(type="compact"))
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
        self.assertIn("/compact [run-id]", get_help_text())
        self.assertIn("/status", get_help_text())
        self.assertIn("/context", get_help_text())
        self.assertIn("/init", get_help_text())
        self.assertIn("/doctor", get_help_text())
        self.assertIn("/clear", get_help_text())
        self.assertIn("/usage", get_help_text())
        self.assertIn("/cost", get_help_text())

    def test_get_status_text_reports_local_runtime_state(self) -> None:
        text = get_status_text("chat", "allow", "run-1", chat_turns=2)

        self.assertIn("Status:", text)
        self.assertIn("mode: chat", text)
        self.assertIn("approval: allow", text)
        self.assertIn("resume: run-1", text)
        self.assertIn("chatTurns: 2", text)

    def test_get_context_text_reports_prompt_context_sources(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-commands-") as base:
            root = Path(base)
            (root / "AGENTS.md").write_text("Use unittest.\n", encoding="utf-8")
            (root / "package.json").write_text('{"scripts":{"test":"node test.js"}}\n', encoding="utf-8")
            (root / "src").mkdir()
            (root / "src" / "app.py").write_text("print('ok')\n", encoding="utf-8")

            text = get_context_text(root, resume_run_id="run-1", resume_context="session: run-1\nfinal: done")

        self.assertIn("Context:", text)
        self.assertIn(f"projectRoot: {root.resolve()}", text)
        self.assertIn("resume: run-1", text)
        self.assertIn("resumeChars:", text)
        self.assertIn("AGENTS.md:", text)
        self.assertIn("Use unittest.", text)
        self.assertIn("Project command hints:", text)
        self.assertIn("npm run test", text)
        self.assertIn("Workspace snapshot:", text)
        self.assertIn("src/app.py", text)

    def test_init_project_instructions_creates_agents_md_without_overwriting(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-commands-") as base:
            root = Path(base)
            (root / "package.json").write_text('{"scripts":{"test":"node test.js"}}\n', encoding="utf-8")
            (root / "src").mkdir()
            (root / "src" / "app.py").write_text("print('ok')\n", encoding="utf-8")

            created = init_project_instructions(root)
            content = (root / "AGENTS.md").read_text(encoding="utf-8")
            second = init_project_instructions(root)

        self.assertEqual(created, "Created AGENTS.md.")
        self.assertEqual(second, "AGENTS.md already exists; no changes made.")
        self.assertIn("# Repository Guidelines", content)
        self.assertIn("src", content)
        self.assertIn("npm run test", content)
        self.assertIn("Do not commit API keys", content)

    def test_get_doctor_text_reports_local_diagnostics_without_exposing_keys(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-commands-") as base:
            root = Path(base)
            (root / ".git").mkdir()
            (root / "AGENTS.md").write_text("Use unittest.\n", encoding="utf-8")
            (root / ".vibeagent" / "sessions").mkdir(parents=True)
            (root / ".vibeagent" / "config.json").write_text('{"provider":"minimax"}\n', encoding="utf-8")

            text = get_doctor_text(
                root,
                {
                    "VIBEAGENT_PROVIDER": "minimax",
                    "MINIMAX_API_KEY": "secret-key",
                    "MINIMAX_MODEL": "custom-model",
                    "VIBEAGENT_INPUT_USD_PER_MILLION": "1",
                    "VIBEAGENT_OUTPUT_USD_PER_MILLION": "2",
                },
            )

        self.assertIn("Doctor:", text)
        self.assertIn(f"projectRoot: {root.resolve()}", text)
        self.assertIn("provider: minimax", text)
        self.assertIn("model: custom-model", text)
        self.assertIn("apiKey: configured via MINIMAX_API_KEY", text)
        self.assertIn("sessionsDir: yes", text)
        self.assertIn("projectConfig: yes", text)
        self.assertIn("gitRepo: yes", text)
        self.assertIn("agentsMd: yes", text)
        self.assertIn("costRates: 2/4 configured", text)
        self.assertIn("executables:", text)
        self.assertNotIn("secret-key", text)

    def test_get_doctor_text_reports_invalid_provider_and_cost_rates(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-commands-") as base:
            text = get_doctor_text(
                base,
                {
                    "VIBEAGENT_PROVIDER": "unknown",
                    "VIBEAGENT_INPUT_USD_PER_MILLION": "bad",
                },
            )

        self.assertIn("provider: Unsupported VIBEAGENT_PROVIDER: unknown", text)
        self.assertIn("costRates: invalid", text)
        self.assertIn("VIBEAGENT_INPUT_USD_PER_MILLION must be a non-negative decimal.", text)

    def test_get_usage_text_reports_local_session_usage(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-commands-") as base:
            root = Path(base)
            session_dir = root / ".vibeagent" / "sessions" / "run-1"
            session_dir.mkdir(parents=True)
            (session_dir / "events.jsonl").write_text(
                "\n".join(
                    [
                        json.dumps({"type": "model", "iteration": 1, "content": [{"type": "text", "text": "Done."}]}),
                        json.dumps({"type": "tool_call", "iteration": 1, "name": "read_file", "input": {"path": "SECRET_PATH"}}),
                    ]
                )
                + "\n",
                encoding="utf-8",
            )

            text = get_usage_text(root)

        self.assertIn("Usage:", text)
        self.assertIn("sessions: 1", text)
        self.assertIn("events: 2", text)
        self.assertIn("toolCalls: 1", text)
        self.assertIn("cost: unavailable", text)
        self.assertNotIn("SECRET_PATH", text)

    def test_get_cost_text_estimates_with_env_rates(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-commands-") as base:
            root = Path(base)
            session_dir = root / ".vibeagent" / "sessions" / "run-1"
            session_dir.mkdir(parents=True)
            (session_dir / "events.jsonl").write_text(
                json.dumps(
                    {
                        "type": "model",
                        "iteration": 1,
                        "usage": {"input_tokens": 100, "output_tokens": 50},
                        "content": [{"type": "text", "text": "Done."}],
                    }
                )
                + "\n",
                encoding="utf-8",
            )

            text = get_cost_text(
                root,
                {
                    "VIBEAGENT_INPUT_USD_PER_MILLION": "1",
                    "VIBEAGENT_OUTPUT_USD_PER_MILLION": "2",
                },
            )

        self.assertIn("Cost:", text)
        self.assertIn("estimatedCostUsd: $0.000200", text)

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
            compact_selected, compact_context, compact_text = get_compact_context(None, root)

        self.assertIn("run-1", sessions_text)
        self.assertIn("Session: run-1", session_text)
        self.assertIn("status: completed", session_text)
        self.assertIn("task: Build a CLI.", session_text)
        self.assertIn("final: Done.", last_text)
        self.assertEqual(selected, "run-1")
        self.assertIn("task: Build a CLI.", context or "")
        self.assertIn("final: Done.", context or "")
        self.assertEqual(resume_text, "Resume context loaded from session run-1.")
        self.assertEqual(compact_selected, "run-1")
        self.assertEqual(compact_context, context)
        self.assertEqual(compact_text, "Compacted context loaded from session run-1.")

    def test_session_command_requires_run_id(self) -> None:
        self.assertEqual(get_session_text(None), "Usage: /session <run-id>")

    def test_session_command_rejects_path_like_run_id(self) -> None:
        self.assertEqual(get_session_text("../bad"), "Invalid session id: ../bad")
        self.assertEqual(get_resume_context("../bad")[2], "Invalid session id: ../bad")
        self.assertEqual(get_compact_context("../bad")[2], "Invalid session id: ../bad")
        self.assertEqual(get_resume_context("off"), (None, None, "Resume context cleared."))


if __name__ == "__main__":
    unittest.main()
