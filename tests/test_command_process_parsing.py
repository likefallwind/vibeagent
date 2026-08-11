import unittest

from vibeagent.command_parsing import LocalCommand, parse_local_command
from vibeagent.command_process_parsing import parse_process_local_command


class CommandProcessParsingTests(unittest.TestCase):
    def test_process_parser_recognizes_process_commands(self) -> None:
        cases = {
            "/env": LocalCommand(type="env"),
            "/background-agents": LocalCommand(type="background_agents"),
            "/background-agent-log abc123": LocalCommand(type="background_agent_log", argument="abc123"),
            "/stop-background-agent abc123": LocalCommand(type="stop_background_agent", argument="abc123"),
            "/remove-background-agent abc123": LocalCommand(type="remove_background_agent", argument="abc123"),
            "/processes": LocalCommand(type="processes"),
            "/process bg-1": LocalCommand(type="process", argument="bg-1"),
            "/process bg-1 2000": LocalCommand(type="process", argument="bg-1 2000"),
            "/process": LocalCommand(type="process"),
            "/process-output-contexts bg-1": LocalCommand(type="process_output_contexts", argument="bg-1"),
            "/process-output-contexts bg-1 2000": LocalCommand(type="process_output_contexts", argument="bg-1 2000"),
            "/process-output-contexts": LocalCommand(type="process_output_contexts"),
            "/process-output-diagnostics bg-1": LocalCommand(type="process_output_diagnostics", argument="bg-1"),
            "/process-output-diagnostics bg-1 2000": LocalCommand(type="process_output_diagnostics", argument="bg-1 2000"),
            "/process-output-diagnostics": LocalCommand(type="process_output_diagnostics"),
            "/wait-process bg-1": LocalCommand(type="wait_process", argument="bg-1"),
            "/wait-process bg-1 5000 2000": LocalCommand(type="wait_process", argument="bg-1 5000 2000"),
            "/wait-process": LocalCommand(type="wait_process"),
            "/check-write-process bg-1 hello\\n": LocalCommand(type="check_write_process", argument="bg-1 hello\\n"),
            "/check-write-process": LocalCommand(type="check_write_process"),
            "/write-process bg-1 hello\\n": LocalCommand(type="write_process", argument="bg-1 hello\\n"),
            "/write-process": LocalCommand(type="write_process"),
            "/check-stop-process bg-1": LocalCommand(type="check_stop_process", argument="bg-1"),
            "/check-stop-process": LocalCommand(type="check_stop_process"),
            "/stop-process bg-1": LocalCommand(type="stop_process", argument="bg-1"),
            "/stop-process": LocalCommand(type="stop_process"),
            "/check-stop-processes": LocalCommand(type="check_stop_all_processes"),
            "/check-stop-all-processes": LocalCommand(type="check_stop_all_processes"),
            "/stop-processes": LocalCommand(type="stop_all_processes"),
            "/stop-all-processes": LocalCommand(type="stop_all_processes"),
        }

        for raw, expected in cases.items():
            with self.subTest(raw=raw):
                self.assertEqual(parse_process_local_command(raw), expected)
                self.assertEqual(parse_local_command(raw), expected)

    def test_process_parser_ignores_other_commands(self) -> None:
        self.assertIsNone(parse_process_local_command("/session run-1"))
        self.assertIsNone(parse_process_local_command("process bg-1"))


if __name__ == "__main__":
    unittest.main()
