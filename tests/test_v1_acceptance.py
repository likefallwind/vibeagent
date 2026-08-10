from __future__ import annotations

import json
import re
import subprocess
import sys
import tomllib
import unittest
from pathlib import Path

from vibeagent import __version__
from vibeagent.tool_definitions import AGENT_TOOL_DEFINITIONS


ROOT = Path(__file__).resolve().parents[1]
PLAN_PATH = ROOT / "docs" / "vibeagent-1.0.md"
READINESS_PATH = ROOT / "docs" / "vibeagent-1.0-readiness.md"
PYPROJECT_PATH = ROOT / "pyproject.toml"
PACKAGE_PATH = ROOT / "package.json"
BIN_ENTRYPOINT_PATH = ROOT / "bin" / "vibeagent"
DOGFOOD_TESTS = {
    "test_v1_agent_can_read_repair_verify_commit_and_finish",
    "test_v1_agent_can_resume_after_interrupted_failure_and_commit",
    "test_v1_agent_can_complete_repair_with_claude_code_tool_aliases",
    "test_v1_agent_can_create_new_file_with_claude_write_and_commit",
    "test_v1_agent_can_edit_notebook_with_claude_tools_and_commit",
    "test_v1_agent_can_use_claude_mcp_tool_before_repair_and_commit",
    "test_v1_agent_runs_project_hooks_around_claude_edit_and_commits",
    "test_v1_agent_can_manage_claude_background_process_before_repair",
    "test_v1_agent_can_use_web_fetch_before_repair",
    "test_v1_agent_reviews_git_diff_before_commit",
    "test_v1_agent_loads_project_instructions_and_repo_map_before_repair",
    "test_v1_agent_finds_and_runs_focused_tests_before_commit",
    "test_v1_agent_creates_and_checks_checkpoint_before_commit",
    "test_v1_agent_generates_session_handoff_after_verified_commit",
    "test_v1_agent_can_clarify_then_repair_verify_and_commit",
    "test_v1_agent_can_load_project_skill_then_repair_verify_and_commit",
    "test_v1_agent_can_delegate_read_only_investigation_before_repair",
    "test_v1_agent_can_delegate_with_project_agent_profile_before_repair",
    "test_v1_agent_can_delegate_code_subagent_repair_and_commit",
    "test_v1_agent_plan_mode_inspects_without_mutating",
    "test_v1_agent_can_apply_claude_multi_edit_and_commit",
}
CLI_SMOKE_TESTS = {
    "test_v1_cli_dangerously_skip_permissions_can_repair_with_claude_aliases",
    "test_v1_cli_json_can_create_and_check_checkpoint_before_commit",
    "test_v1_cli_json_generates_ready_session_handoff_after_verified_commit",
    "test_v1_cli_json_input_format_can_repair_verify_commit_and_report_ready",
    "test_v1_cli_json_plan_mode_inspects_without_mutating",
    "test_v1_cli_json_can_compact_interrupted_run_and_commit",
    "test_v1_cli_json_can_delegate_code_subagent_repair_and_commit",
    "test_v1_cli_json_can_delegate_read_only_investigation_before_repair_and_commit",
    "test_v1_cli_json_can_delegate_with_project_agent_profile_before_repair_and_commit",
    "test_v1_cli_json_can_load_project_skill_before_repair_and_commit",
    "test_v1_cli_json_can_manage_background_process_before_repair_and_commit",
    "test_v1_cli_json_runs_project_hooks_around_claude_edit_and_commits",
    "test_v1_cli_json_can_use_strict_mcp_config_before_repair_and_commit",
    "test_v1_cli_json_can_use_web_fetch_before_repair_and_commit",
    "test_v1_cli_json_can_repair_verify_commit_and_report_ready",
    "test_v1_cli_json_can_resume_interrupted_run_and_commit",
    "test_v1_cli_json_reports_pending_user_input_for_machine_callers",
    "test_v1_cli_stream_json_disallowed_tools_override_accept_edits",
    "test_v1_cli_stream_json_input_format_can_repair_verify_commit_and_report_ready",
    "test_v1_cli_stream_json_accept_edits_auto_allows_claude_edit",
    "test_v1_cli_stream_json_accept_edits_auto_allows_claude_notebook_edit",
    "test_v1_cli_stream_json_can_repair_with_allowed_tools_and_report_events",
}
PROJECT_COMMAND_TESTS = {
    "test_one_shot_custom_command_expands_to_code_task_with_metadata",
}
LIVE_DOGFOOD_TESTS = {
    "test_prepare_repo_creates_broken_calculator_and_command",
    "test_run_live_dogfood_feeds_ask_mode_approvals_and_reports_run_id",
    "test_audit_repo_fails_before_repair_and_passes_after_commit",
    "test_audit_session_events_requires_live_gate_evidence",
    "test_audit_session_events_rejects_side_effect_before_approval",
    "test_audit_session_events_rejects_side_effect_path_outside_workspace",
    "test_audit_session_events_rejects_secret_leakage",
    "test_audit_session_events_rejects_blocked_command_execution",
    "test_audit_session_events_accepts_complete_live_gate_evidence",
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
    "VA1-GOAL": {
        "tools": set(),
        "tests": {"test_one_shot_goal_continues_until_evaluator_accepts"},
    },
    "VA1-DELEGATE": {
        "tools": {"delegate_task", "Task", "Agent"},
        "tests": {"test_parent_agent_receives_subagent_summary_as_tool_result"},
    },
    "VA1-PLAN": {
        "tools": {"project_overview", "read_file", "tool_search"},
        "tests": {"test_plan_mode_denies_hidden_write_even_with_approving_handler"},
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
            "python3 -m unittest tests.test_v1_acceptance tests.test_v1_dogfood tests.test_v1_cli_smoke tests.test_project_prompt_commands tests.test_v1_live_dogfood -q",
        )

    def test_package_exposes_full_v1_readiness_script(self) -> None:
        package = json.loads((ROOT / "package.json").read_text(encoding="utf-8"))

        self.assertEqual(
            package["scripts"]["test:v1:full"],
            "npm run test:v1 && python3 -m unittest discover -s tests -q",
        )
        self.assertEqual(
            package["scripts"]["test:v1:release"],
            "npm run build && npm run test:install && npm run test:v1:full",
        )

    def test_package_version_metadata_stays_in_sync(self) -> None:
        pyproject = tomllib.loads(PYPROJECT_PATH.read_text(encoding="utf-8"))
        package = json.loads(PACKAGE_PATH.read_text(encoding="utf-8"))

        self.assertEqual(pyproject["project"]["version"], __version__)
        self.assertEqual(package["version"], __version__)

    def test_distribution_entrypoints_target_cli_main(self) -> None:
        pyproject = tomllib.loads(PYPROJECT_PATH.read_text(encoding="utf-8"))
        package = json.loads(PACKAGE_PATH.read_text(encoding="utf-8"))
        bin_entrypoint = BIN_ENTRYPOINT_PATH.read_text(encoding="utf-8")

        self.assertEqual(pyproject["project"]["scripts"]["vibeagent"], "vibeagent.cli:console_main")
        self.assertEqual(package["bin"]["vibeagent"], "./bin/vibeagent")
        self.assertIn("from vibeagent.cli import main", bin_entrypoint)
        self.assertIn("main(sys.argv[1:])", bin_entrypoint)

    def test_npm_bin_entrypoint_runs_from_source_checkout(self) -> None:
        result = subprocess.run(
            [sys.executable, BIN_ENTRYPOINT_PATH.as_posix(), "--version"],
            cwd=ROOT,
            check=False,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout.strip(), f"vibeagent {__version__}")

    def test_acceptance_plan_names_the_dedicated_cli_smoke_tests(self) -> None:
        plan = PLAN_PATH.read_text(encoding="utf-8")
        smoke_source = (ROOT / "tests" / "test_v1_cli_smoke.py").read_text(encoding="utf-8")

        for test_name in CLI_SMOKE_TESTS:
            with self.subTest(test_name=test_name):
                self.assertIn(test_name, plan)
                self.assertIn(f"def {test_name}", smoke_source)

    def test_acceptance_plan_names_project_command_compat_tests(self) -> None:
        plan = PLAN_PATH.read_text(encoding="utf-8")
        source = (ROOT / "tests" / "test_project_prompt_commands.py").read_text(encoding="utf-8")

        for test_name in PROJECT_COMMAND_TESTS:
            with self.subTest(test_name=test_name):
                self.assertIn(test_name, plan)
                self.assertIn(f"def {test_name}", source)

    def test_acceptance_plan_names_live_dogfood_script_tests(self) -> None:
        plan = PLAN_PATH.read_text(encoding="utf-8")
        source = (ROOT / "tests" / "test_v1_live_dogfood.py").read_text(encoding="utf-8")

        for test_name in LIVE_DOGFOOD_TESTS:
            with self.subTest(test_name=test_name):
                self.assertIn(test_name, plan)
                self.assertIn(f"def {test_name}", source)

    def test_readme_links_to_v1_acceptance_plan(self) -> None:
        readme = (ROOT / "README.md").read_text(encoding="utf-8")

        self.assertIn("docs/vibeagent-1.0.md", readme)
        self.assertIn("docs/vibeagent-1.0-readiness.md", readme)

    def test_readme_distinguishes_sandbox_domains_from_webfetch_permissions(self) -> None:
        readme = (ROOT / "README.md").read_text(encoding="utf-8")

        self.assertIn("sandbox network domain allowlists", readme)
        self.assertIn("separate from project", readme)
        self.assertIn("permission `WebFetch(domain:...)` rules", readme)
        self.assertIn("WebFetch(domain:...)", readme)
        self.assertIn("WebFetch(domain:*.python.org)", readme)

    def test_acceptance_plan_links_to_readiness_audit(self) -> None:
        plan = PLAN_PATH.read_text(encoding="utf-8")

        self.assertIn("docs/vibeagent-1.0-readiness.md", plan)
        self.assertIn("Verified 1.0 Exit Criteria", plan)
        self.assertIn(f"VibeAgent `{__version__}`", plan)
        self.assertIn("npm run test:v1:release", plan)

    def test_readiness_audit_names_automated_and_live_provider_gates(self) -> None:
        readiness = READINESS_PATH.read_text(encoding="utf-8")

        self.assertIn("npm run test:v1:release", readiness)
        self.assertIn("npm run build", readiness)
        self.assertIn("python3 -m compileall -q vibeagent", readiness)
        self.assertIn("npm run test:install", readiness)
        self.assertIn("scripts/install_smoke.py", readiness)
        self.assertIn("fresh virtual environment", readiness)
        self.assertIn("python -m vibeagent --version", readiness)
        self.assertIn("vibeagent --version", readiness)
        self.assertIn("npm run test:v1:full", readiness)
        self.assertIn("Live Provider Gate", readiness)
        self.assertIn("Status: `complete-for-v1-release`", readiness)
        self.assertIn(f"Release package version: `{__version__}`", readiness)
        self.assertRegex(readiness, r"- Date: 20\d{2}-\d{2}-\d{2}")
        self.assertRegex(readiness, r"- Session: `20\d{2}-\d{2}-\d{2}T\d{2}-\d{2}-\d{2}-\d{3}Z-[a-f0-9]{8}`")
        self.assertIn("Provider: MiniMax via `MINIMAX_API_KEY`", readiness)
        self.assertIn("Audit result: all repository, approval, failing/passing unittest", readiness)
        self.assertIn("scripts/live_dogfood_v1.py", readiness)
        self.assertIn("python3 -m vibeagent --cwd /tmp/vibeagent-live-dogfood", readiness)

    def test_readme_documents_accept_edits_file_permission_scope(self) -> None:
        readme = (ROOT / "README.md").read_text(encoding="utf-8")

        self.assertIn(
            "`acceptEdits` -> `ask` plus automatic `Write`, `Edit`, `MultiEdit`, and `NotebookEdit` allow rules",
            readme,
        )


if __name__ == "__main__":
    unittest.main()
