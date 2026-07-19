from __future__ import annotations

import unittest

from vibeagent import MACHINE_OUTPUT_SCHEMA_VERSION, __version__
from vibeagent.cli_machine_output import machine_result_status_fields, machine_runtime_fields


class CliMachineOutputTests(unittest.TestCase):
    def test_machine_runtime_fields_include_schema_and_version(self) -> None:
        self.assertEqual(
            machine_runtime_fields(),
            {
                "schemaVersion": MACHINE_OUTPUT_SCHEMA_VERSION,
                "version": __version__,
            },
        )

    def test_machine_result_status_fields_include_aliases(self) -> None:
        without_exit = machine_result_status_fields(status="failed", stop_reason="failed")
        with_exit = machine_result_status_fields(status="completed", stop_reason="completed", exit_code=0)

        self.assertEqual(without_exit, {"status": "failed", "stopReason": "failed", "stop_reason": "failed"})
        self.assertEqual(
            with_exit,
            {
                "status": "completed",
                "stopReason": "completed",
                "stop_reason": "completed",
                "exitCode": 0,
                "exit_code": 0,
            },
        )


if __name__ == "__main__":
    unittest.main()
