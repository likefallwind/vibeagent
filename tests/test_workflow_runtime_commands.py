from __future__ import annotations

import unittest

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


if __name__ == "__main__":
    unittest.main()
