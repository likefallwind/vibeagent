from __future__ import annotations

import json
import re
import unittest
from pathlib import Path

from vibeagent.tool_definitions import AGENT_TOOL_DEFINITIONS


ROOT = Path(__file__).resolve().parents[1]
PLAN_PATH = ROOT / "docs" / "vibeagent-1.0.md"
DOGFOOD_TESTS = {
    "test_v1_agent_can_read_repair_verify_commit_and_finish",
    "test_v1_agent_can_resume_after_interrupted_failure_and_commit",
    "test_v1_agent_can_complete_repair_with_claude_code_tool_aliases",
    "test_v1_agent_can_delegate_read_only_investigation_before_repair",
}

EXPECTED_GATES = {
    "VA1-READ": {
        "tools": {"project_overview", "repo_map", "read_file", "read_file_context", "search", "project_instructions"},
        "tests": {"test_run_agent_includes_project_instruction_files_in_initial_prompt"},
    },
    "VA1-EDIT": {
        "tools": {"check_write_file", "write_file", "check_edit_file", "edit_file", "multi_edit_file"},
        "tests": {"test_run_agent_writes_multiple_files_with_approval"},
    },
    "VA1-RUN": {
        "tools": {"command_check", "check_run_commands", "run_command", "run_commands", "focused_test_commands", "run_suggested_checks"},
        "tests": {"test_run_agent_continues_after_pending_suggested_check_is_run"},
    },
    "VA1-REPAIR": {
        "tools": {"write_file", "run_command"},
        "tests": {"test_run_agent_repairs_a_failing_script_and_finishes"},
    },
    "VA1-REVIEW": {
        "tools": {"final_review", "suggest_checks", "run_suggested_checks"},
        "tests": {"test_run_agent_continues_after_pending_suggested_check_is_run"},
    },
    "VA1-COMMIT": {
        "tools": {"check_git_stage", "git_stage", "check_git_commit", "git_commit"},
        "tests": {"test_run_agent_keeps_verification_after_stage_and_commit"},
    },
    "VA1-RESUME": {
        "tools": {"session_summary", "session_verification", "run_session_verification", "session_handoff"},
        "tests": {"test_run_agent_uses_existing_session_verification_on_resume"},
    },
    "VA1-DELEGATE": {
        "tools": {"delegate_task", "Task", "Agent"},
        "tests": {"test_parent_agent_receives_subagent_summary_as_tool_result"},
    },
    "VA1-SAFETY": {
        "tools": {"command_check", "final_review", "check_git_push"},
        "tests": {"test_run_agent_returns_blocked_command_as_tool_result"},
    },
}


class V1AcceptanceTests(unittest.TestCase):
    def test_acceptance_plan_lists_exactly_the_v1_gates(self) -> None:
        text = PLAN_PATH.read_text(encoding="utf-8")
        gates = set(re.findall(r"\bVA1-[A-Z]+\b", text))

        self.assertEqual(gates, set(EXPECTED_GATES))

    def test_acceptance_gate_tools_exist_in_agent_tool_catalog(self) -> None:
        tool_names = {str(tool["name"]) for tool in AGENT_TOOL_DEFINITIONS}

        for gate, evidence in EXPECTED_GATES.items():
            missing = evidence["tools"] - tool_names
            with self.subTest(gate=gate):
                self.assertEqual(missing, set())

    def test_acceptance_gate_evidence_names_existing_regressions(self) -> None:
        test_sources = "\n".join(path.read_text(encoding="utf-8") for path in sorted((ROOT / "tests").glob("test_*.py")))

        for gate, evidence in EXPECTED_GATES.items():
            missing = {name for name in evidence["tests"] if f"def {name}" not in test_sources}
            with self.subTest(gate=gate):
                self.assertEqual(missing, set())

    def test_acceptance_plan_names_the_dedicated_dogfood_tests(self) -> None:
        plan = PLAN_PATH.read_text(encoding="utf-8")
        dogfood_source = (ROOT / "tests" / "test_v1_dogfood.py").read_text(encoding="utf-8")

        for test_name in DOGFOOD_TESTS:
            with self.subTest(test_name=test_name):
                self.assertIn(test_name, plan)
                self.assertIn(f"def {test_name}", dogfood_source)

    def test_package_exposes_fast_v1_acceptance_script(self) -> None:
        package = json.loads((ROOT / "package.json").read_text(encoding="utf-8"))

        self.assertEqual(
            package["scripts"]["test:v1"],
            "python3 -m unittest tests.test_v1_acceptance tests.test_v1_dogfood -q",
        )

    def test_readme_links_to_v1_acceptance_plan(self) -> None:
        readme = (ROOT / "README.md").read_text(encoding="utf-8")

        self.assertIn("docs/vibeagent-1.0.md", readme)


if __name__ == "__main__":
    unittest.main()
