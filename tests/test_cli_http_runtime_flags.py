import io
import json
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import patch

from vibeagent.cli import main


class CliHttpRuntimeFlagTests(unittest.TestCase):
    def test_main_runs_port_check_local_flag_without_creating_client(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
            stdout = io.StringIO()

            with (
                patch("vibeagent.cli.create_chat_client") as create_chat_client,
                patch("vibeagent.cli.get_port_text", return_value="Port:\n  ok: yes") as get_port_text,
                redirect_stdout(stdout),
            ):
                exit_code = main(["--cwd", base, "--port-check", "5173", "--port-host", "127.0.0.1", "--port-timeout-ms", "1500"])

        self.assertEqual(exit_code, 0)
        self.assertIn("Port:", stdout.getvalue())
        get_port_text.assert_called_once_with(Path(base).resolve(), port=5173, host="127.0.0.1", timeout_ms=1500)
        create_chat_client.assert_not_called()

    def test_main_port_check_local_flag_exits_nonzero_when_not_ok(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
            stdout = io.StringIO()

            with (
                patch("vibeagent.cli.create_chat_client") as create_chat_client,
                patch("vibeagent.cli.get_port_text", return_value="Port:\n  ok: yes\n  reachable: no"),
                redirect_stdout(stdout),
            ):
                exit_code = main(["--cwd", base, "--port-check", "5173"])

        self.assertEqual(exit_code, 1)
        self.assertIn("Port:", stdout.getvalue())
        self.assertIn("reachable: no", stdout.getvalue())
        create_chat_client.assert_not_called()

    def test_main_port_check_json_outputs_structured_payload(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
            stdout = io.StringIO()
            report = {
                "projectRoot": str(Path(base).resolve()),
                "ok": True,
                "host": "127.0.0.1",
                "port": 5173,
                "reachable": True,
                "timeoutMs": 1500,
                "error": None,
                "message": "Port is reachable.",
            }

            with (
                patch("vibeagent.cli.create_chat_client") as create_chat_client,
                patch("vibeagent.cli.get_port_report", return_value=report) as get_port_report,
                patch("vibeagent.cli.format_port_report_text", return_value="Port:\n  ok: yes\n  reachable: yes") as format_port_report,
                redirect_stdout(stdout),
            ):
                exit_code = main(["--json", "--cwd", base, "--port-check", "5173", "--port-host", "127.0.0.1", "--port-timeout-ms", "1500"])

        payload = json.loads(stdout.getvalue())
        self.assertEqual(exit_code, 0)
        self.assertTrue(payload["success"])
        self.assertEqual(payload["port"], report)
        get_port_report.assert_called_once_with(Path(base).resolve(), port=5173, host="127.0.0.1", timeout_ms=1500)
        format_port_report.assert_called_once_with(report)
        create_chat_client.assert_not_called()

    def test_main_runs_http_check_local_flag_without_creating_client(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
            stdout = io.StringIO()

            with (
                patch("vibeagent.cli.create_chat_client") as create_chat_client,
                patch("vibeagent.cli.get_http_text", return_value="HTTP:\n  ok: yes") as get_http_text,
                redirect_stdout(stdout),
            ):
                exit_code = main(
                    [
                        "--cwd",
                        base,
                        "--http-check",
                        "http://127.0.0.1:5173",
                        "--http-contains",
                        "ready",
                        "--http-timeout-ms",
                        "1500",
                        "--http-max-body-chars",
                        "1000",
                        "--http-regex",
                    ]
                )

        self.assertEqual(exit_code, 0)
        self.assertIn("HTTP:", stdout.getvalue())
        get_http_text.assert_called_once_with(
            Path(base).resolve(),
            url="http://127.0.0.1:5173",
            contains="ready",
            timeout_ms=1500,
            max_body_chars=1000,
            regex=True,
        )
        create_chat_client.assert_not_called()

    def test_main_http_check_local_flag_reports_json_failure_status(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
            stdout = io.StringIO()
            report = {
                "projectRoot": str(Path(base).resolve()),
                "ok": False,
                "url": "http://127.0.0.1:5173",
                "finalUrl": "http://127.0.0.1:5173/",
                "status": 200,
                "reason": "OK",
                "reachable": True,
                "matched": False,
                "matchedPattern": "ready",
                "timeoutMs": 2000,
                "maxBodyChars": 2000,
                "body": "not ready\n",
                "bodyTruncated": False,
                "error": None,
                "message": "HTTP URL is reachable but did not match.",
            }

            with (
                patch("vibeagent.cli.create_chat_client") as create_chat_client,
                patch("vibeagent.cli.get_http_report", return_value=report) as get_http_report,
                patch("vibeagent.cli.format_http_report_text", return_value="HTTP:\n  ok: no\n  reachable: yes\n  matched: no") as format_http_report,
                redirect_stdout(stdout),
            ):
                exit_code = main(
                    [
                        "--json",
                        "--cwd",
                        base,
                        "--http-check",
                        "http://127.0.0.1:5173",
                        "--http-contains",
                        "ready",
                    ]
                )

        self.assertEqual(exit_code, 1)
        payload = json.loads(stdout.getvalue())
        self.assertEqual(payload["kind"], "local")
        self.assertFalse(payload["success"])
        self.assertEqual(payload["status"], "failed")
        self.assertIn("matched: no", payload["text"])
        self.assertEqual(payload["http"], report)
        get_http_report.assert_called_once_with(
            Path(base).resolve(),
            url="http://127.0.0.1:5173",
            contains="ready",
            timeout_ms=2000,
            max_body_chars=2000,
            regex=False,
        )
        format_http_report.assert_called_once_with(report)
        create_chat_client.assert_not_called()

    def test_main_runs_http_fetch_local_flag_without_creating_client(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
            stdout = io.StringIO()

            with (
                patch("vibeagent.cli.create_chat_client") as create_chat_client,
                patch("vibeagent.cli.get_http_fetch_text", return_value="HTTP fetch:\n  ok: yes") as get_http_fetch_text,
                redirect_stdout(stdout),
            ):
                exit_code = main(
                    [
                        "--cwd",
                        base,
                        "--http-fetch",
                        "http://127.0.0.1:5173/app",
                        "--http-timeout-ms",
                        "2500",
                        "--http-max-body-chars",
                        "4000",
                    ]
                )

        self.assertEqual(exit_code, 0)
        self.assertIn("HTTP fetch:", stdout.getvalue())
        get_http_fetch_text.assert_called_once_with(
            Path(base).resolve(),
            url="http://127.0.0.1:5173/app",
            timeout_ms=2500,
            max_body_chars=4000,
        )
        create_chat_client.assert_not_called()

    def test_main_http_fetch_json_outputs_structured_payload(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
            stdout = io.StringIO()
            report = {
                "projectRoot": str(Path(base).resolve()),
                "ok": True,
                "url": "http://127.0.0.1:5173/app",
                "finalUrl": "http://127.0.0.1:5173/app",
                "status": 200,
                "reason": "OK",
                "contentType": "text/html; charset=utf-8",
                "reachable": True,
                "timeoutMs": 2500,
                "maxBodyChars": 4000,
                "body": "<main>ready</main>\n",
                "bodyTruncated": False,
                "error": None,
                "message": "HTTP URL was fetched.",
            }

            with (
                patch("vibeagent.cli.create_chat_client") as create_chat_client,
                patch("vibeagent.cli.get_http_fetch_report", return_value=report) as get_http_fetch_report,
                patch("vibeagent.cli.format_http_fetch_report_text", return_value="HTTP fetch:\n  ok: yes") as format_http_fetch_report,
                redirect_stdout(stdout),
            ):
                exit_code = main(
                    [
                        "--json",
                        "--cwd",
                        base,
                        "--http-fetch",
                        "http://127.0.0.1:5173/app",
                        "--http-timeout-ms",
                        "2500",
                        "--http-max-body-chars",
                        "4000",
                    ]
                )

        payload = json.loads(stdout.getvalue())
        self.assertEqual(exit_code, 0)
        self.assertTrue(payload["success"])
        self.assertEqual(payload["httpFetch"], report)
        get_http_fetch_report.assert_called_once_with(
            Path(base).resolve(),
            url="http://127.0.0.1:5173/app",
            timeout_ms=2500,
            max_body_chars=4000,
        )
        format_http_fetch_report.assert_called_once_with(report)
        create_chat_client.assert_not_called()

    def test_main_parses_interactive_port_options(self) -> None:
        stdout = io.StringIO()

        with (
            patch(
                "builtins.input",
                side_effect=[
                    "/port 5173 --host 0.0.0.0 --timeout-ms 1500",
                    "/exit",
                ],
            ),
            patch("vibeagent.cli.create_chat_client") as create_chat_client,
            patch("vibeagent.cli.get_port_text", return_value="Port:\n  reachable: yes") as get_port_text,
            redirect_stdout(stdout),
        ):
            exit_code = main()

        output = stdout.getvalue()
        self.assertEqual(exit_code, 0)
        self.assertIn("Port:", output)
        get_port_text.assert_called_once_with(port=5173, host="0.0.0.0", timeout_ms=1500)
        create_chat_client.assert_not_called()

    def test_main_reports_interactive_port_option_errors(self) -> None:
        stdout = io.StringIO()

        with (
            patch(
                "builtins.input",
                side_effect=[
                    "/port --host 127.0.0.1",
                    "/port 5173 --timeout-ms 99",
                    "/port 5173 --host",
                    "/port 5173 --unknown 1",
                    "/port 5173 extra --host 127.0.0.1",
                    "/exit",
                ],
            ),
            patch("vibeagent.cli.create_chat_client") as create_chat_client,
            patch("vibeagent.cli.get_port_text") as get_port_text,
            redirect_stdout(stdout),
        ):
            exit_code = main()

        output = stdout.getvalue()
        self.assertEqual(exit_code, 0)
        self.assertIn("Usage: /port <port> [host] [timeout-ms]", output)
        self.assertIn("port is required.", output)
        self.assertIn("--timeout-ms must be at least 100.", output)
        self.assertIn("--host requires a value.", output)
        self.assertIn("Unknown option: --unknown", output)
        get_port_text.assert_not_called()
        create_chat_client.assert_not_called()

    def test_main_parses_interactive_http_options(self) -> None:
        stdout = io.StringIO()

        with (
            patch(
                "builtins.input",
                side_effect=[
                    "/http http://127.0.0.1:5173 ready --timeout-ms 1500 --max-body-chars 1000 --regex",
                    "/http-fetch --timeout-ms 2500 --max-body-chars 4000 -- http://127.0.0.1:5173/app",
                    "/exit",
                ],
            ),
            patch("vibeagent.cli.create_chat_client") as create_chat_client,
            patch("vibeagent.cli.get_http_text", return_value="HTTP:\n  matched: yes") as get_http_text,
            patch("vibeagent.cli.get_http_fetch_text", return_value="HTTP fetch:\n  ok: yes") as get_http_fetch_text,
            redirect_stdout(stdout),
        ):
            exit_code = main()

        output = stdout.getvalue()
        self.assertEqual(exit_code, 0)
        self.assertIn("HTTP:", output)
        self.assertIn("HTTP fetch:", output)
        get_http_text.assert_called_once_with(
            url="http://127.0.0.1:5173",
            contains="ready",
            timeout_ms=1500,
            max_body_chars=1000,
            regex=True,
        )
        get_http_fetch_text.assert_called_once_with(
            url="http://127.0.0.1:5173/app",
            timeout_ms=2500,
            max_body_chars=4000,
        )
        create_chat_client.assert_not_called()

    def test_main_reports_interactive_http_option_errors(self) -> None:
        stdout = io.StringIO()

        with (
            patch(
                "builtins.input",
                side_effect=[
                    "/http --timeout-ms 99 -- http://127.0.0.1:5173",
                    "/http http://127.0.0.1:5173 --contains",
                    "/http --contains ready http://127.0.0.1:5173 positional",
                    "/http --contains ready",
                    "/http http://127.0.0.1:5173 --unknown 1",
                    "/http-fetch --max-body-chars 0 -- http://127.0.0.1:5173/app",
                    "/http-fetch http://127.0.0.1:5173/app extra --timeout-ms 1000",
                    "/exit",
                ],
            ),
            patch("vibeagent.cli.create_chat_client") as create_chat_client,
            patch("vibeagent.cli.get_http_text") as get_http_text,
            patch("vibeagent.cli.get_http_fetch_text") as get_http_fetch_text,
            redirect_stdout(stdout),
        ):
            exit_code = main()

        output = stdout.getvalue()
        self.assertEqual(exit_code, 0)
        self.assertIn("Usage: /http <url> [contains]", output)
        self.assertIn("--timeout-ms must be at least 100.", output)
        self.assertIn("--contains requires a value.", output)
        self.assertIn("provide either --contains or positional contains, not both.", output)
        self.assertIn("url is required.", output)
        self.assertIn("Unknown option: --unknown", output)
        self.assertIn("Usage: /http-fetch <url>", output)
        self.assertIn("--max-body-chars must be a positive integer.", output)
        get_http_text.assert_not_called()
        get_http_fetch_text.assert_not_called()
        create_chat_client.assert_not_called()
