from __future__ import annotations

import unittest

from vibeagent import command_hard_blocks
from vibeagent import workflow_context_commands
from vibeagent import workflow_doctor_commands
from vibeagent import workflow_init_commands
from vibeagent import workflow_commands
from vibeagent.workflow_runtime_commands import (
    blocked_command_examples,
    build_project_instructions_template,
    format_context_report_text,
    format_doctor_report_text,
    format_init_report_text,
    format_status_report_text,
    get_command_hard_block_report,
    get_context_report,
    get_context_text,
    get_doctor_report,
    get_doctor_text,
    get_init_report,
    get_status_report,
    get_status_text,
    init_project_instructions,
    normalize_project_instructions_file_name,
)


class WorkflowRuntimeCommandModuleTests(unittest.TestCase):
    def test_workflow_commands_reexports_runtime_helpers(self) -> None:
        self.assertIs(blocked_command_examples, command_hard_blocks.blocked_command_examples)
        self.assertIs(get_command_hard_block_report, command_hard_blocks.get_command_hard_block_report)
        self.assertIs(get_doctor_report, workflow_doctor_commands.get_doctor_report)
        self.assertIs(get_doctor_text, workflow_doctor_commands.get_doctor_text)
        self.assertIs(format_doctor_report_text, workflow_doctor_commands.format_doctor_report_text)
        self.assertIs(get_init_report, workflow_init_commands.get_init_report)
        self.assertIs(init_project_instructions, workflow_init_commands.init_project_instructions)
        self.assertIs(format_init_report_text, workflow_init_commands.format_init_report_text)
        self.assertIs(normalize_project_instructions_file_name, workflow_init_commands.normalize_project_instructions_file_name)
        self.assertIs(build_project_instructions_template, workflow_init_commands.build_project_instructions_template)
        self.assertIs(get_context_report, workflow_context_commands.get_context_report)
        self.assertIs(get_context_text, workflow_context_commands.get_context_text)
        self.assertIs(format_context_report_text, workflow_context_commands.format_context_report_text)
        self.assertIs(workflow_commands.blocked_command_examples, blocked_command_examples)
        self.assertIs(workflow_commands.get_command_hard_block_report, get_command_hard_block_report)
        self.assertIs(workflow_commands.get_status_report, get_status_report)
        self.assertIs(workflow_commands.get_status_text, get_status_text)
        self.assertIs(workflow_commands.format_status_report_text, format_status_report_text)
        self.assertIs(workflow_commands.get_context_report, get_context_report)
        self.assertIs(workflow_commands.get_context_text, get_context_text)
        self.assertIs(workflow_commands.format_context_report_text, format_context_report_text)
        self.assertIs(workflow_commands.get_init_report, get_init_report)
        self.assertIs(workflow_commands.init_project_instructions, init_project_instructions)
        self.assertIs(workflow_commands.format_init_report_text, format_init_report_text)
        self.assertIs(workflow_commands.normalize_project_instructions_file_name, normalize_project_instructions_file_name)
        self.assertIs(workflow_commands.get_doctor_report, get_doctor_report)
        self.assertIs(workflow_commands.get_doctor_text, get_doctor_text)
        self.assertIs(workflow_commands.format_doctor_report_text, format_doctor_report_text)
        self.assertIs(workflow_commands.build_project_instructions_template, build_project_instructions_template)

    def test_hard_block_examples_return_a_copy(self) -> None:
        examples = blocked_command_examples()
        examples.append("echo should not alter hard-block examples")

        self.assertNotIn("echo should not alter hard-block examples", blocked_command_examples())

    def test_hard_block_report_covers_all_examples(self) -> None:
        report = get_command_hard_block_report()

        self.assertEqual(report["total"], len(blocked_command_examples()))
        self.assertEqual(report["active"], report["total"])
        self.assertTrue(
            any(
                check["command"] == "sensible-browser http://127.0.0.1:5173"
                and check["active"]
                for check in report["checks"]
            )
        )


if __name__ == "__main__":
    unittest.main()
