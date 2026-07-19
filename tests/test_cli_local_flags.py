import io
import json
import subprocess
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import patch

from vibeagent import MACHINE_OUTPUT_SCHEMA_VERSION, __version__
from vibeagent.cli import main


class CliLocalFlagTests(unittest.TestCase):
    def test_main_runs_local_flags_without_creating_client(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
            stdout = io.StringIO()

            with (
                patch("vibeagent.cli.create_chat_client") as create_chat_client,
                patch("vibeagent.cli.get_doctor_text", return_value="Doctor:\n  provider: minimax") as get_doctor_text,
                redirect_stdout(stdout),
            ):
                exit_code = main(["--cwd", base, "--doctor"])

        self.assertEqual(exit_code, 0)
        self.assertIn("Doctor:", stdout.getvalue())
        self.assertEqual(get_doctor_text.call_args.args[0], Path(base).resolve())
        create_chat_client.assert_not_called()

    def test_main_runs_local_flag_with_json_output(self) -> None:
        stdout = io.StringIO()
        report = {
            "ok": True,
            "provider": "minimax",
            "model": "MiniMax-M2.7",
            "baseUrl": "https://api.minimaxi.com/anthropic",
            "apiKeyConfigured": True,
            "apiKeySource": "MINIMAX_API_KEY",
            "error": "",
            "message": "Resolved model provider configuration.",
        }
        rendered = "Model provider: minimax"

        with (
            patch("vibeagent.cli.create_chat_client") as create_chat_client,
            patch("vibeagent.cli.get_model_report", return_value=report) as get_model_report,
            patch("vibeagent.cli.format_model_report_text", return_value=rendered) as format_model_report_text,
            redirect_stdout(stdout),
        ):
            exit_code = main(["--json", "--model"])

        payload = json.loads(stdout.getvalue())
        self.assertEqual(exit_code, 0)
        self.assertEqual(payload["kind"], "local")
        self.assertEqual(payload["schemaVersion"], MACHINE_OUTPUT_SCHEMA_VERSION)
        self.assertEqual(payload["version"], __version__)
        self.assertTrue(payload["success"])
        self.assertEqual(payload["status"], "completed")
        self.assertEqual(payload["text"], rendered)
        self.assertEqual(payload["model"], report)
        get_model_report.assert_called_once()
        format_model_report_text.assert_called_once_with(report)
        create_chat_client.assert_not_called()

    def test_main_local_config_flag_reports_json_without_creating_client(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
            stdout = io.StringIO()
            report = {
                "projectRoot": str(Path(base).resolve()),
                "projectConfig": False,
                "projectConfigError": "",
                "provider": {"ok": True, "name": "deepseek", "model": "deepseek-reasoner", "baseUrl": "https://api.deepseek.com", "apiKeyConfigured": False, "apiKeySource": "", "error": ""},
                "execution": {"ok": True, "maxIterations": 9, "commandTimeoutMs": 120000, "maxOutputTokens": 8192, "modelRetries": 2, "modelRetryDelayMs": 25, "modelTimeoutMs": 45000, "error": ""},
                "costRates": {"ok": True, "configured": 0, "total": 4, "errors": []},
            }
            rendered = "Config:\n  provider: deepseek"

            with (
                patch.dict("vibeagent.cli.os.environ", {}, clear=True),
                patch("vibeagent.cli.create_chat_client") as create_chat_client,
                patch("vibeagent.cli.get_config_report", return_value=report) as get_config_report,
                patch("vibeagent.cli.format_config_report_text", return_value=rendered) as format_config_report_text,
                redirect_stdout(stdout),
            ):
                exit_code = main(
                    [
                        "--json",
                        "--cwd",
                        base,
                        "--config",
                        "--provider",
                        "deepseek",
                        "--model-name",
                        "deepseek-reasoner",
                        "--max-iterations",
                        "9",
                        "--command-timeout-ms",
                        "120000",
                        "--max-output-tokens",
                        "8192",
                        "--model-retries",
                        "2",
                        "--model-retry-delay-ms",
                        "25",
                        "--model-timeout-ms",
                        "45000",
                    ]
                )

        payload = json.loads(stdout.getvalue())
        provider_env = get_config_report.call_args.args[1]
        self.assertEqual(exit_code, 0)
        self.assertTrue(payload["success"])
        self.assertEqual(payload["status"], "completed")
        self.assertEqual(payload["text"], rendered)
        self.assertEqual(payload["config"], report)
        self.assertEqual(get_config_report.call_args.args[0], Path(base).resolve())
        self.assertEqual(provider_env["VIBEAGENT_PROVIDER"], "deepseek")
        self.assertEqual(provider_env["OPENAI_COMPAT_MODEL"], "deepseek-reasoner")
        self.assertEqual(get_config_report.call_args.kwargs["max_iterations"], 9)
        self.assertEqual(get_config_report.call_args.kwargs["command_timeout_ms"], 120000)
        self.assertEqual(get_config_report.call_args.kwargs["max_output_tokens"], 8192)
        self.assertEqual(get_config_report.call_args.kwargs["model_retries"], 2)
        self.assertEqual(get_config_report.call_args.kwargs["model_retry_delay_ms"], 25)
        self.assertEqual(get_config_report.call_args.kwargs["model_timeout_ms"], 45000)
        format_config_report_text.assert_called_once_with(report)
        create_chat_client.assert_not_called()

    def test_main_local_model_flag_uses_provider_overrides(self) -> None:
        stdout = io.StringIO()

        with (
            patch("vibeagent.cli.create_chat_client") as create_chat_client,
            patch("vibeagent.cli.get_model_text", return_value="Model provider: deepseek") as get_model_text,
            redirect_stdout(stdout),
        ):
            exit_code = main(
                [
                    "--model",
                    "--provider",
                    "deepseek",
                    "--model-name",
                    "deepseek-reasoner",
                    "--base-url",
                    "https://deepseek.example",
                    "--api-key",
                    "secret-key",
                ]
            )

        provider_env = get_model_text.call_args.args[0]
        self.assertEqual(exit_code, 0)
        self.assertIn("Model provider: deepseek", stdout.getvalue())
        self.assertEqual(provider_env["VIBEAGENT_PROVIDER"], "deepseek")
        self.assertEqual(provider_env["OPENAI_COMPAT_MODEL"], "deepseek-reasoner")
        self.assertEqual(provider_env["OPENAI_COMPAT_BASE_URL"], "https://deepseek.example")
        self.assertEqual(provider_env["OPENAI_COMPAT_API_KEY"], "secret-key")
        create_chat_client.assert_not_called()

    def test_main_local_model_flag_uses_project_provider_config(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
            config_dir = Path(base) / ".vibeagent"
            config_dir.mkdir()
            (config_dir / "config.json").write_text(
                json.dumps({"provider": "deepseek", "model": "deepseek-reasoner"}),
                encoding="utf-8",
            )
            stdout = io.StringIO()

            with (
                patch.dict("vibeagent.cli.os.environ", {}, clear=True),
                patch("vibeagent.cli.create_chat_client") as create_chat_client,
                patch("vibeagent.cli.get_model_text", return_value="Model provider: deepseek") as get_model_text,
                redirect_stdout(stdout),
            ):
                exit_code = main(["--cwd", base, "--model"])

        provider_env = get_model_text.call_args.args[0]
        self.assertEqual(exit_code, 0)
        self.assertIn("Model provider: deepseek", stdout.getvalue())
        self.assertEqual(provider_env["VIBEAGENT_PROVIDER"], "deepseek")
        self.assertEqual(provider_env["VIBEAGENT_MODEL"], "deepseek-reasoner")
        create_chat_client.assert_not_called()

    def test_main_local_model_flag_exits_nonzero_for_invalid_provider(self) -> None:
        stdout = io.StringIO()

        with (
            patch.dict("vibeagent.cli.os.environ", {"VIBEAGENT_PROVIDER": "unknown"}, clear=True),
            patch("vibeagent.cli.create_chat_client") as create_chat_client,
            redirect_stdout(stdout),
        ):
            exit_code = main(["--model"])

        self.assertEqual(exit_code, 1)
        self.assertIn("Unsupported VIBEAGENT_PROVIDER: unknown", stdout.getvalue())
        create_chat_client.assert_not_called()

    def test_main_local_config_flag_reports_resolved_config_without_creating_client(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
            stdout = io.StringIO()

            with (
                patch.dict("vibeagent.cli.os.environ", {}, clear=True),
                patch("vibeagent.cli.create_chat_client") as create_chat_client,
                patch("vibeagent.cli.get_config_text", return_value="Config:\n  provider: deepseek") as get_config_text,
                redirect_stdout(stdout),
            ):
                exit_code = main(
                    [
                        "--cwd",
                        base,
                        "--config",
                        "--provider",
                        "deepseek",
                        "--model-name",
                        "deepseek-reasoner",
                        "--max-iterations",
                        "9",
                        "--command-timeout-ms",
                        "120000",
                        "--max-output-tokens",
                        "8192",
                        "--model-retries",
                        "2",
                        "--model-retry-delay-ms",
                        "25",
                        "--model-timeout-ms",
                        "45000",
                    ]
                )

        provider_env = get_config_text.call_args.args[1]
        self.assertEqual(exit_code, 0)
        self.assertIn("Config:", stdout.getvalue())
        self.assertEqual(get_config_text.call_args.args[0], Path(base).resolve())
        self.assertEqual(provider_env["VIBEAGENT_PROVIDER"], "deepseek")
        self.assertEqual(provider_env["OPENAI_COMPAT_MODEL"], "deepseek-reasoner")
        self.assertEqual(get_config_text.call_args.kwargs["max_iterations"], 9)
        self.assertEqual(get_config_text.call_args.kwargs["command_timeout_ms"], 120000)
        self.assertEqual(get_config_text.call_args.kwargs["max_output_tokens"], 8192)
        self.assertEqual(get_config_text.call_args.kwargs["model_retries"], 2)
        self.assertEqual(get_config_text.call_args.kwargs["model_retry_delay_ms"], 25)
        self.assertEqual(get_config_text.call_args.kwargs["model_timeout_ms"], 45000)
        create_chat_client.assert_not_called()

    def test_main_save_config_writes_non_secret_project_defaults(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
            stdout = io.StringIO()

            with (
                patch("vibeagent.cli.create_chat_client") as create_chat_client,
                redirect_stdout(stdout),
            ):
                exit_code = main(
                    [
                        "--cwd",
                        base,
                        "--save-config",
                        "--provider",
                        "deepseek",
                        "--model-name",
                        "deepseek-reasoner",
                        "--base-url",
                        "https://deepseek.example",
                        "--max-iterations",
                        "15",
                        "--command-timeout-ms",
                        "60000",
                        "--max-output-tokens",
                        "8192",
                        "--model-retries",
                        "2",
                        "--model-retry-delay-ms",
                        "25",
                        "--model-timeout-ms",
                        "60000",
                    ]
                )
            data = json.loads((Path(base) / ".vibeagent" / "config.json").read_text(encoding="utf-8"))

        self.assertEqual(exit_code, 0)
        self.assertEqual(stdout.getvalue(), "Saved .vibeagent/config.json.\n")
        self.assertEqual(data["provider"], "deepseek")
        self.assertEqual(data["model"], "deepseek-reasoner")
        self.assertEqual(data["base_url"], "https://deepseek.example")
        self.assertEqual(data["max_iterations"], 15)
        self.assertEqual(data["command_timeout_ms"], 60000)
        self.assertEqual(data["max_output_tokens"], 8192)
        self.assertEqual(data["model_retries"], 2)
        self.assertEqual(data["model_retry_delay_ms"], 25)
        self.assertEqual(data["model_timeout_ms"], 60000)
        self.assertNotIn("api_key", data)
        create_chat_client.assert_not_called()

    def test_main_save_config_accepts_model_alias(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
            stdout = io.StringIO()

            with (
                patch("vibeagent.cli.create_chat_client") as create_chat_client,
                redirect_stdout(stdout),
            ):
                exit_code = main(["--cwd", base, "--save-config", "--provider", "minimax", "--model", "MiniMax-custom"])
            data = json.loads((Path(base) / ".vibeagent" / "config.json").read_text(encoding="utf-8"))

        self.assertEqual(exit_code, 0)
        self.assertEqual(data["provider"], "minimax")
        self.assertEqual(data["model"], "MiniMax-custom")
        create_chat_client.assert_not_called()

    def test_main_save_config_rejects_api_key_without_writing_secret(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
            stdout = io.StringIO()

            with (
                patch("vibeagent.cli.create_chat_client") as create_chat_client,
                redirect_stdout(stdout),
            ):
                exit_code = main(["--cwd", base, "--save-config", "--provider", "deepseek", "--api-key", "secret-key"])
            config_path = Path(base) / ".vibeagent" / "config.json"

        self.assertEqual(exit_code, 1)
        self.assertIn("--save-config does not write API keys", stdout.getvalue())
        self.assertFalse(config_path.exists())
        create_chat_client.assert_not_called()

    def test_main_save_config_with_json_output(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
            stdout = io.StringIO()

            with (
                patch("vibeagent.cli.create_chat_client") as create_chat_client,
                redirect_stdout(stdout),
            ):
                exit_code = main(
                    [
                        "--json",
                        "--cwd",
                        base,
                        "--save-config",
                        "--provider",
                        "minimax",
                        "--model-name",
                        "MiniMax-M2.7",
                        "--max-iterations",
                        "9",
                    ]
                )

        payload = json.loads(stdout.getvalue())
        self.assertEqual(exit_code, 0)
        self.assertEqual(payload["kind"], "local")
        self.assertTrue(payload["success"])
        self.assertEqual(payload["status"], "completed")
        self.assertEqual(payload["text"], "Saved .vibeagent/config.json.")
        report = payload["saveConfig"]
        self.assertTrue(report["ok"])
        self.assertTrue(report["created"])
        self.assertFalse(report["existedBefore"])
        self.assertTrue(report["exists"])
        self.assertEqual(report["projectRoot"], str(Path(base).resolve()))
        self.assertEqual(report["path"], str(Path(base).resolve() / ".vibeagent" / "config.json"))
        self.assertEqual(report["writtenKeys"], ["provider", "model", "max_iterations"])
        self.assertEqual(report["config"]["provider"], "minimax")
        self.assertEqual(report["config"]["model"], "MiniMax-M2.7")
        self.assertEqual(report["config"]["max_iterations"], 9)
        self.assertNotIn("api_key", json.dumps(report, ensure_ascii=False))
        create_chat_client.assert_not_called()

    def test_main_local_session_flag_uses_requested_run_id_and_cwd(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
            stdout = io.StringIO()

            with (
                patch("vibeagent.cli.create_chat_client") as create_chat_client,
                patch("vibeagent.cli.get_session_text", return_value="Session: run-1") as get_session_text,
                redirect_stdout(stdout),
            ):
                exit_code = main(["--cwd", base, "--session", " run-1 "])

        self.assertEqual(exit_code, 0)
        self.assertIn("Session: run-1", stdout.getvalue())
        get_session_text.assert_called_once_with("run-1", Path(base).resolve())
        create_chat_client.assert_not_called()

    def test_main_local_status_flag_uses_approval_setting(self) -> None:
        stdout = io.StringIO()

        with (
            patch("vibeagent.cli.create_chat_client") as create_chat_client,
            redirect_stdout(stdout),
        ):
            exit_code = main(["--approval", "deny", "--status"])

        self.assertEqual(exit_code, 0)
        self.assertIn("Status:", stdout.getvalue())
        self.assertIn(f"version: {__version__}", stdout.getvalue())
        self.assertIn("approval: deny", stdout.getvalue())
        create_chat_client.assert_not_called()

    def test_main_local_status_flag_reports_json_payload(self) -> None:
        stdout = io.StringIO()
        report = {
            "version": __version__,
            "mode": "code",
            "approval": "deny",
            "resume": "",
            "chatTurns": 0,
            "message": "Runtime status resolved.",
        }

        with (
            patch("vibeagent.cli.create_chat_client") as create_chat_client,
            patch("vibeagent.cli.get_status_report", return_value=report) as get_status_report,
            patch("vibeagent.cli.format_status_report_text", return_value="Status:\n  approval: deny"),
            redirect_stdout(stdout),
        ):
            exit_code = main(["--json", "--approval", "deny", "--status"])

        payload = json.loads(stdout.getvalue())
        self.assertEqual(exit_code, 0)
        self.assertTrue(payload["success"])
        self.assertEqual(payload["runtimeStatus"], report)
        self.assertEqual(payload["runtimeStatus"]["version"], __version__)
        self.assertIn("Status:", payload["text"])
        get_status_report.assert_called_once_with("code", "deny", None, chat_turns=0)
        create_chat_client.assert_not_called()

    def test_main_local_context_flag_reports_json_payload(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
            stdout = io.StringIO()
            report = {
                "projectRoot": str(Path(base).resolve()),
                "resume": "",
                "resumeChars": 0,
                "instructions": {"found": False, "text": "No AGENTS.md or CLAUDE.md instructions found."},
                "commandHints": {"found": False, "text": "No project command hints found."},
                "workspaceSnapshot": {"text": "."},
                "message": "Prompt context resolved.",
            }

            with (
                patch("vibeagent.cli.create_chat_client") as create_chat_client,
                patch("vibeagent.cli.get_context_report", return_value=report) as get_context_report,
                patch("vibeagent.cli.format_context_report_text", return_value="Context:\n  resume: none"),
                redirect_stdout(stdout),
            ):
                exit_code = main(["--json", "--cwd", base, "--context"])

        payload = json.loads(stdout.getvalue())
        self.assertEqual(exit_code, 0)
        self.assertTrue(payload["success"])
        self.assertEqual(payload["context"], report)
        self.assertIn("Context:", payload["text"])
        get_context_report.assert_called_once_with(Path(base).resolve())
        create_chat_client.assert_not_called()

    def test_main_local_context_flag_defaults_to_current_directory(self) -> None:
        stdout = io.StringIO()
        report = {
            "projectRoot": str(Path.cwd().resolve()),
            "resume": "",
            "resumeChars": 0,
            "instructions": {"found": False, "text": "No AGENTS.md or CLAUDE.md instructions found."},
            "commandHints": {"found": False, "text": "No project command hints found."},
            "workspaceSnapshot": {"text": "."},
            "message": "Prompt context resolved.",
        }

        with (
            patch("vibeagent.cli.create_chat_client") as create_chat_client,
            patch("vibeagent.cli.get_context_report", return_value=report) as get_context_report,
            patch("vibeagent.cli.format_context_report_text", return_value="Context:\n  resume: none"),
            redirect_stdout(stdout),
        ):
            exit_code = main(["--json", "--context"])

        payload = json.loads(stdout.getvalue())
        self.assertEqual(exit_code, 0)
        self.assertTrue(payload["success"])
        self.assertEqual(payload["context"], report)
        get_context_report.assert_called_once_with(".")
        create_chat_client.assert_not_called()

    def test_main_runs_doctor_json_with_structured_payload(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
            stdout = io.StringIO()

            with (
                patch.dict(
                    "vibeagent.cli.os.environ",
                    {
                        "VIBEAGENT_PROVIDER": "minimax",
                        "MINIMAX_API_KEY": "secret-key",
                    },
                    clear=True,
                ),
                patch("vibeagent.cli.create_chat_client") as create_chat_client,
                redirect_stdout(stdout),
            ):
                exit_code = main(["--json", "--cwd", base, "--doctor"])

        payload = json.loads(stdout.getvalue())
        self.assertEqual(exit_code, 0)
        self.assertEqual(payload["kind"], "local")
        self.assertEqual(payload["status"], "completed")
        self.assertTrue(payload["success"])
        self.assertIn("Doctor:", payload["text"])
        doctor = payload["doctor"]
        self.assertEqual(doctor["version"], __version__)
        self.assertIn(f"version: {__version__}", payload["text"])
        self.assertEqual(doctor["projectRoot"], str(Path(base).resolve()))
        self.assertEqual(doctor["provider"]["apiKeySource"], "MINIMAX_API_KEY")
        self.assertNotIn("secret-key", json.dumps(payload, ensure_ascii=False))
        self.assertEqual(doctor["commandHardBlocks"]["active"], doctor["commandHardBlocks"]["total"])
        self.assertTrue(any(check["command"] == "code ." and check["active"] for check in doctor["commandHardBlocks"]["checks"]))
        self.assertTrue(any(check["command"] == "cmd.exe /c explorer.exe ." and check["active"] for check in doctor["commandHardBlocks"]["checks"]))
        self.assertTrue(any(check["command"] == "rundll32 url.dll,FileProtocolHandler ." and check["active"] for check in doctor["commandHardBlocks"]["checks"]))
        self.assertTrue(
            any(
                check["command"] == "/mnt/c/Windows/System32/WindowsPowerShell/v1.0/powershell.exe -Command Start-Process ."
                and check["active"]
                for check in doctor["commandHardBlocks"]["checks"]
            )
        )
        self.assertTrue(any(check["command"] == "python3 -m webbrowser http://127.0.0.1:5173" and check["active"] for check in doctor["commandHardBlocks"]["checks"]))
        self.assertTrue(any(check["command"] == "python3 -c \"import webbrowser; webbrowser.open('http://127.0.0.1:5173')\"" and check["active"] for check in doctor["commandHardBlocks"]["checks"]))
        self.assertTrue(any(check["command"] == "python3 -c \"import webbrowser; webbrowser.get().open('http://127.0.0.1:5173')\"" and check["active"] for check in doctor["commandHardBlocks"]["checks"]))
        self.assertTrue(any(check["command"] == "python3 -c \"import os; os.startfile('.')\"" and check["active"] for check in doctor["commandHardBlocks"]["checks"]))
        self.assertTrue(any(check["command"] == "python3 -c \"import os; os.system('xdg-open .')\"" and check["active"] for check in doctor["commandHardBlocks"]["checks"]))
        self.assertTrue(any(check["command"] == "python3 - <<'PY'\nimport subprocess\nsubprocess.run(['xdg-open', '.'])\nPY" and check["active"] for check in doctor["commandHardBlocks"]["checks"]))
        self.assertTrue(any(check["command"] == "node -e \"require('child_process').exec('xdg-open .')\"" and check["active"] for check in doctor["commandHardBlocks"]["checks"]))
        self.assertTrue(any(check["command"] == "node -e \"const {exec}=require('child_process'); const cmd='xdg-open .'; exec(cmd)\"" and check["active"] for check in doctor["commandHardBlocks"]["checks"]))
        self.assertTrue(any(check["command"] == "node - <<'JS'\nrequire('child_process').exec('xdg-open .')\nJS" and check["active"] for check in doctor["commandHardBlocks"]["checks"]))
        self.assertTrue(any(check["command"] == "node -e \"require('shelljs').exec('xdg-open .')\"" and check["active"] for check in doctor["commandHardBlocks"]["checks"]))
        self.assertTrue(any(check["command"] == "node -e \"require('execa').execaCommand('xdg-open .')\"" and check["active"] for check in doctor["commandHardBlocks"]["checks"]))
        self.assertTrue(
            any(
                check["command"] == "node --input-type=module -e \"import { exec } from 'node:child_process'; exec('xdg-open .')\""
                and check["active"]
                for check in doctor["commandHardBlocks"]["checks"]
            )
        )
        self.assertTrue(
            any(
                check["command"] == "node --input-type=module -e \"import { execaCommand } from 'execa'; execaCommand('xdg-open .')\""
                and check["active"]
                for check in doctor["commandHardBlocks"]["checks"]
            )
        )
        self.assertTrue(
            any(
                check["command"] == "node --input-type=module -e \"const cp = await import('node:child_process'); cp.exec('xdg-open .')\""
                and check["active"]
                for check in doctor["commandHardBlocks"]["checks"]
            )
        )
        self.assertTrue(
            any(
                check["command"] == "node --input-type=module -e \"const { execaCommand } = await import('execa'); execaCommand('xdg-open .')\""
                and check["active"]
                for check in doctor["commandHardBlocks"]["checks"]
            )
        )
        create_chat_client.assert_not_called()

    def test_main_runs_doctor_json_formats_report_without_rerunning_text(self) -> None:
        report = {"projectRoot": "/tmp/project", "provider": {"ok": True}, "costRates": {"ok": True}, "executables": {}, "commandHardBlocks": {}}
        stdout = io.StringIO()

        with (
            patch("vibeagent.cli.create_chat_client") as create_chat_client,
            patch("vibeagent.cli.get_doctor_report", return_value=report) as get_doctor_report,
            patch("vibeagent.cli.format_doctor_report_text", return_value="Doctor:\n  provider: minimax") as format_doctor_report_text,
            patch("vibeagent.cli.get_doctor_text") as get_doctor_text,
            redirect_stdout(stdout),
        ):
            exit_code = main(["--json", "--doctor"])

        payload = json.loads(stdout.getvalue())
        self.assertEqual(exit_code, 0)
        self.assertEqual(payload["doctor"], report)
        self.assertEqual(payload["text"], "Doctor:\n  provider: minimax")
        get_doctor_report.assert_called_once()
        format_doctor_report_text.assert_called_once_with(report)
        get_doctor_text.assert_not_called()
        create_chat_client.assert_not_called()

    def test_main_runs_tools_local_flag_without_creating_client(self) -> None:
        stdout = io.StringIO()

        with (
            patch("vibeagent.cli.create_chat_client") as create_chat_client,
            redirect_stdout(stdout),
        ):
            exit_code = main(["--tools"])

        self.assertEqual(exit_code, 0)
        self.assertIn("Tools:", stdout.getvalue())
        self.assertIn("list_files", stdout.getvalue())
        self.assertIn("run_command", stdout.getvalue())
        create_chat_client.assert_not_called()

    def test_main_runs_tools_local_flag_with_json_output(self) -> None:
        stdout = io.StringIO()
        report = {
            "ok": True,
            "total": 1,
            "approvalRequired": {"total": 1, "tools": ["write_file"]},
            "readOnly": {"total": 0, "tools": []},
            "categories": [{"name": "edit", "total": 1, "tools": ["write_file"]}],
            "tools": [{"name": "write_file", "category": "edit", "approvalRequired": True}],
            "message": "Found 1 model tool(s).",
        }

        with (
            patch("vibeagent.cli.create_chat_client") as create_chat_client,
            patch("vibeagent.cli.get_tools_report", return_value=report) as get_tools_report,
            patch("vibeagent.cli.format_tools_report_text", return_value="Tools:\n  total: 1\n  approvalRequired: 1"),
            redirect_stdout(stdout),
        ):
            exit_code = main(["--json", "--tools"])

        payload = json.loads(stdout.getvalue())
        self.assertEqual(exit_code, 0)
        self.assertEqual(payload["kind"], "local")
        self.assertTrue(payload["success"])
        self.assertEqual(payload["status"], "completed")
        self.assertIn("Tools:", payload["text"])
        self.assertEqual(payload["tools"], report)
        get_tools_report.assert_called_once_with()
        create_chat_client.assert_not_called()

    def test_main_runs_tool_search_local_flag_without_creating_client(self) -> None:
        stdout = io.StringIO()

        with (
            patch("vibeagent.cli.create_chat_client") as create_chat_client,
            redirect_stdout(stdout),
        ):
            exit_code = main(["--tool-search", "verification"])

        self.assertEqual(exit_code, 0)
        self.assertIn("Tool search:", stdout.getvalue())
        self.assertIn("session_verification", stdout.getvalue())
        create_chat_client.assert_not_called()

    def test_main_runs_tool_search_local_flag_with_json_output(self) -> None:
        stdout = io.StringIO()
        report = {
            "ok": True,
            "query": "read",
            "matches": [{"name": "read_file", "category": "project", "approvalRequired": False}],
            "total": 1,
            "shown": 1,
            "truncated": False,
            "category": None,
            "approvalRequired": None,
            "suggestions": ["read_file"],
            "message": "Found 1 matching tool(s).",
        }

        with (
            patch("vibeagent.cli.create_chat_client") as create_chat_client,
            patch("vibeagent.cli.get_tool_search_report", return_value=report) as get_tool_search_report,
            patch("vibeagent.cli.format_tool_search_report_text", return_value="Tool search:\n  matches: 1/1"),
            redirect_stdout(stdout),
        ):
            exit_code = main(["--json", "--tool-search", "read"])

        payload = json.loads(stdout.getvalue())
        self.assertEqual(exit_code, 0)
        self.assertEqual(payload["kind"], "local")
        self.assertTrue(payload["success"])
        self.assertEqual(payload["status"], "completed")
        self.assertEqual(payload["toolSearch"], report)
        get_tool_search_report.assert_called_once_with("read", max_matches=20, category=None, approval_required=None)
        create_chat_client.assert_not_called()

    def test_main_runs_filtered_tool_search_local_flag_with_json_output(self) -> None:
        stdout = io.StringIO()

        with (
            patch("vibeagent.cli.create_chat_client") as create_chat_client,
            redirect_stdout(stdout),
        ):
            exit_code = main(
                [
                    "--json",
                    "--tool-search",
                    "verification",
                    "--tool-search-max",
                    "3",
                    "--tool-search-category",
                    "session",
                    "--tool-search-approval",
                    "no",
                ]
            )

        payload = json.loads(stdout.getvalue())
        matches = payload["toolSearch"]["matches"]
        self.assertEqual(exit_code, 0)
        self.assertEqual(payload["toolSearch"]["shown"], 3)
        self.assertTrue(all(match["category"] == "session" for match in matches))
        self.assertTrue(all(not match["approvalRequired"] for match in matches))
        create_chat_client.assert_not_called()

    def test_tool_search_filter_options_require_tool_search(self) -> None:
        stdout = io.StringIO()

        with (
            patch("vibeagent.cli.create_chat_client") as create_chat_client,
            redirect_stdout(stdout),
        ):
            exit_code = main(["--json", "--tool-search-category", "session"])

        payload = json.loads(stdout.getvalue())
        self.assertEqual(exit_code, 2)
        self.assertEqual(payload["kind"], "error")
        self.assertEqual(payload["error"], "--tool-search-category can only be used with --tool-search.")
        create_chat_client.assert_not_called()

    def test_main_runs_review_local_flag_without_creating_client(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
            stdout = io.StringIO()

            with (
                patch("vibeagent.cli.create_chat_client") as create_chat_client,
                patch("vibeagent.cli.get_review_report", return_value={"ready": True}) as get_review_report,
                patch("vibeagent.cli.format_review_report_text", return_value="Review:\n  ready: yes") as format_review_report_text,
                redirect_stdout(stdout),
            ):
                exit_code = main(["--cwd", base, "--review"])

        self.assertEqual(exit_code, 0)
        self.assertIn("Review:", stdout.getvalue())
        get_review_report.assert_called_once_with(Path(base).resolve(), max_files=200, max_checks=5)
        format_review_report_text.assert_called_once_with({"ready": True})
        create_chat_client.assert_not_called()

    def test_main_runs_review_local_flag_with_limits_without_creating_client(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
            stdout = io.StringIO()

            with (
                patch("vibeagent.cli.create_chat_client") as create_chat_client,
                patch("vibeagent.cli.get_review_report", return_value={"ready": True}) as get_review_report,
                patch("vibeagent.cli.format_review_report_text", return_value="Review:\n  ready: yes") as format_review_report_text,
                redirect_stdout(stdout),
            ):
                exit_code = main(["--cwd", base, "--review", "--review-max-files", "1", "--review-max-checks", "2"])

        self.assertEqual(exit_code, 0)
        self.assertIn("Review:", stdout.getvalue())
        get_review_report.assert_called_once_with(Path(base).resolve(), max_files=1, max_checks=2)
        format_review_report_text.assert_called_once_with({"ready": True})
        create_chat_client.assert_not_called()

    def test_main_runs_review_local_flag_with_json_output(self) -> None:
        stdout = io.StringIO()
        review = {"ready": False, "blockingIssues": ["Changed Python files have syntax errors."]}

        with (
            patch("vibeagent.cli.create_chat_client") as create_chat_client,
            patch("vibeagent.cli.get_review_report", return_value=review),
            patch("vibeagent.cli.format_review_report_text", return_value="Review:\n  ready: no"),
            redirect_stdout(stdout),
        ):
            exit_code = main(["--json", "--review"])

        payload = json.loads(stdout.getvalue())
        self.assertEqual(exit_code, 1)
        self.assertEqual(
            payload,
            {
                "kind": "local",
                "schemaVersion": MACHINE_OUTPUT_SCHEMA_VERSION,
                "version": __version__,
                "success": False,
                "exitCode": 1,
                "exit_code": 1,
                "status": "failed",
                "stopReason": "failed",
                "stop_reason": "failed",
                "text": "Review:\n  ready: no",
                "review": review,
            },
        )
        create_chat_client.assert_not_called()

    def test_main_runs_review_json_with_structured_payload(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
            root = Path(base)
            subprocess.run(["git", "init"], cwd=root, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            (root / "package.json").write_text('{"scripts":{"test":"node test.js"}}\n', encoding="utf-8")
            stdout = io.StringIO()

            with redirect_stdout(stdout):
                exit_code = main(["--json", "--cwd", base, "--review", "--review-max-files", "10", "--review-max-checks", "5"])

        payload = json.loads(stdout.getvalue())
        self.assertEqual(exit_code, 0)
        self.assertEqual(payload["kind"], "local")
        self.assertEqual(payload["version"], __version__)
        self.assertEqual(payload["status"], "completed")
        self.assertTrue(payload["success"])
        self.assertIn("Review:", payload["text"])
        review = payload["review"]
        self.assertEqual(review["projectRoot"], str(root.resolve()))
        self.assertTrue(review["ready"])
        self.assertEqual(review["changedFiles"]["total"], 1)
        commands = [item["command"] for item in review["suggestedChecks"]["commands"] if isinstance(item, dict)]
        self.assertIn("npm run test", commands)

    def test_main_runs_handoff_local_flag_without_creating_client(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
            stdout = io.StringIO()

            with (
                patch("vibeagent.cli.create_chat_client") as create_chat_client,
                patch("vibeagent.cli.get_handoff_report", return_value={"ready": True}) as get_handoff_report,
                patch("vibeagent.cli.format_handoff_report_text", return_value="Handoff:\n  ready: yes") as format_handoff_report_text,
                redirect_stdout(stdout),
            ):
                exit_code = main(["--cwd", base, "--handoff"])

        self.assertEqual(exit_code, 0)
        self.assertIn("Handoff:", stdout.getvalue())
        get_handoff_report.assert_called_once_with(
            Path(base).resolve(),
            max_files=200,
            max_checks=10,
            max_status_chars=4000,
            max_plan_chars=4000,
        )
        format_handoff_report_text.assert_called_once_with({"ready": True})
        create_chat_client.assert_not_called()

    def test_main_runs_handoff_local_flag_with_limits_without_creating_client(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
            stdout = io.StringIO()

            with (
                patch("vibeagent.cli.create_chat_client") as create_chat_client,
                patch("vibeagent.cli.get_handoff_report", return_value={"ready": True}) as get_handoff_report,
                patch("vibeagent.cli.format_handoff_report_text", return_value="Handoff:\n  ready: yes") as format_handoff_report_text,
                redirect_stdout(stdout),
            ):
                exit_code = main(
                    [
                        "--cwd",
                        base,
                        "--handoff",
                        "--handoff-max-files",
                        "1",
                        "--handoff-max-checks",
                        "2",
                        "--handoff-max-status-chars",
                        "3000",
                        "--handoff-max-plan-chars",
                        "4000",
                    ]
                )

        self.assertEqual(exit_code, 0)
        self.assertIn("Handoff:", stdout.getvalue())
        get_handoff_report.assert_called_once_with(
            Path(base).resolve(),
            max_files=1,
            max_checks=2,
            max_status_chars=3000,
            max_plan_chars=4000,
        )
        format_handoff_report_text.assert_called_once_with({"ready": True})
        create_chat_client.assert_not_called()

    def test_main_runs_handoff_local_flag_with_json_output(self) -> None:
        stdout = io.StringIO()
        handoff = {"ready": False, "blockingIssues": ["Suggested checks have not been run."]}

        with (
            patch("vibeagent.cli.create_chat_client") as create_chat_client,
            patch("vibeagent.cli.get_handoff_report", return_value=handoff),
            patch("vibeagent.cli.format_handoff_report_text", return_value="Handoff:\n  ready: no"),
            redirect_stdout(stdout),
        ):
            exit_code = main(["--json", "--handoff"])

        payload = json.loads(stdout.getvalue())
        self.assertEqual(exit_code, 1)
        self.assertEqual(
            payload,
            {
                "kind": "local",
                "schemaVersion": MACHINE_OUTPUT_SCHEMA_VERSION,
                "version": __version__,
                "success": False,
                "exitCode": 1,
                "exit_code": 1,
                "status": "failed",
                "stopReason": "failed",
                "stop_reason": "failed",
                "text": "Handoff:\n  ready: no",
                "handoff": handoff,
            },
        )
        create_chat_client.assert_not_called()

    def test_main_runs_handoff_json_with_structured_payload(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
            root = Path(base)
            subprocess.run(["git", "init"], cwd=root, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            (root / "package.json").write_text('{"scripts":{"test":"node test.js"}}\n', encoding="utf-8")
            stdout = io.StringIO()

            with redirect_stdout(stdout):
                exit_code = main(["--json", "--cwd", base, "--handoff", "--handoff-max-files", "10", "--handoff-max-checks", "5"])

        payload = json.loads(stdout.getvalue())
        self.assertEqual(exit_code, 0)
        self.assertEqual(payload["kind"], "local")
        self.assertEqual(payload["version"], __version__)
        self.assertEqual(payload["status"], "completed")
        self.assertTrue(payload["success"])
        self.assertIn("Handoff:", payload["text"])
        handoff = payload["handoff"]
        self.assertEqual(handoff["projectRoot"], str(root.resolve()))
        self.assertTrue(handoff["ready"])
        self.assertEqual(handoff["changedFiles"]["total"], 1)
        commands = [item["command"] for item in handoff["suggestedChecks"]["commands"] if isinstance(item, dict)]
        self.assertIn("npm run test", commands)
        self.assertEqual(handoff["blockingIssues"], [])
