import io
import json
import unittest
from contextlib import redirect_stdout
from unittest.mock import patch

from vibeagent import MACHINE_OUTPUT_SCHEMA_VERSION, __version__
from vibeagent.cli import main


class CliPermissionFlagTests(unittest.TestCase):
    def test_main_rejects_invalid_permission_override_rule(self) -> None:
        stdout = io.StringIO()

        with (
            patch("vibeagent.cli.create_chat_client") as create_chat_client,
            redirect_stdout(stdout),
        ):
            exit_code = main(["--json", "--allowed-tools", "Read(", "inspect"])

        payload = json.loads(stdout.getvalue())
        self.assertEqual(exit_code, 2)
        self.assertEqual(payload["kind"], "error")
        self.assertEqual(payload["schemaVersion"], MACHINE_OUTPUT_SCHEMA_VERSION)
        self.assertEqual(payload["version"], __version__)
        self.assertIn("permission rule is invalid", payload["error"])
        self.assertEqual(payload["stopReason"], "failed")
        self.assertEqual(payload["stop_reason"], "failed")
        create_chat_client.assert_not_called()

    def test_main_rejects_permission_overrides_without_code_task(self) -> None:
        cases = [
            ["--json", "--allowed-tools", "Read"],
            ["--json", "--allowed-tools", "Read", "--chat", "hello"],
            ["--json", "--disallowed-tools", "Edit", "--permissions"],
            ["--json", "--permission-mode", "acceptEdits"],
        ]
        for argv in cases:
            with self.subTest(argv=argv):
                stdout = io.StringIO()
                with (
                    patch("vibeagent.cli.create_chat_client") as create_chat_client,
                    redirect_stdout(stdout),
                ):
                    exit_code = main(argv)

                payload = json.loads(stdout.getvalue())
                self.assertEqual(exit_code, 2)
                self.assertIn("can only be used with one-shot coding tasks", payload["error"])
                create_chat_client.assert_not_called()


if __name__ == "__main__":
    unittest.main()
