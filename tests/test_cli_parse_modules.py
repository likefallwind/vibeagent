from __future__ import annotations

import argparse
import unittest

from vibeagent import cli_parsing
from vibeagent.cli_parse_core import build_focused_tests_kwargs, parse_cli_json_value, timeout_ms
from vibeagent.cli_parse_code_intel import (
    parse_interactive_python_call_graph_argument,
    parse_interactive_python_symbol_argument,
    parse_interactive_test_paths_argument,
)
from vibeagent.cli_parse_cwd_command import (
    parse_interactive_check_run_sequence_argument as parse_cwd_check_run_sequence_argument,
    parse_interactive_cwd_command_argument,
)
from vibeagent.cli_parse_discovery import (
    parse_interactive_glob_argument,
    parse_interactive_overview_argument,
    parse_interactive_search_argument,
)
from vibeagent.cli_parse_diff_git import build_diff_argument, parse_interactive_diff_argument
from vibeagent.cli_parse_process_run import parse_interactive_wait_process_argument
from vibeagent.cli_parse_runtime_checks import parse_interactive_http_argument, parse_interactive_port_argument
from vibeagent.cli_parse_read import (
    parse_interactive_read_argument,
    parse_interactive_read_files_argument,
    parse_interactive_tree_argument,
)
from vibeagent import cli_parse_run
from vibeagent.cli_parse_run import (
    parse_interactive_check_run_sequence_argument,
    parse_interactive_run_argument,
    parse_interactive_run_sequence_argument,
)
from vibeagent.cli_parse_session import (
    parse_interactive_session_detail_argument,
    parse_interactive_run_session_verification_argument,
    parse_interactive_session_search_argument,
    parse_interactive_transcript_argument,
)
from vibeagent.cli_session_args import add_session_limit_arguments, add_session_local_arguments
from vibeagent.cli_parse_tool_search import parse_interactive_tool_search_argument
from vibeagent.cli_project_local_flags import build_check_suggested_kwargs, build_run_suggested_kwargs, kwargs_without_argument


class CliParseModuleTests(unittest.TestCase):
    def test_compat_module_reexports_split_helpers(self) -> None:
        self.assertIs(cli_parsing.timeout_ms, timeout_ms)
        self.assertIs(cli_parsing.parse_cli_json_value, parse_cli_json_value)
        self.assertIs(cli_parsing.build_diff_argument, build_diff_argument)
        self.assertIs(cli_parsing.parse_interactive_diff_argument, parse_interactive_diff_argument)
        self.assertIs(cli_parsing.parse_interactive_transcript_argument, parse_interactive_transcript_argument)
        self.assertIs(cli_parsing.parse_interactive_run_session_verification_argument, parse_interactive_run_session_verification_argument)
        self.assertIs(cli_parsing.parse_interactive_session_detail_argument, parse_interactive_session_detail_argument)
        self.assertIs(cli_parsing.parse_interactive_session_search_argument, parse_interactive_session_search_argument)
        self.assertIs(cli_parsing.parse_interactive_http_argument, parse_interactive_http_argument)
        self.assertIs(cli_parsing.parse_interactive_port_argument, parse_interactive_port_argument)
        self.assertIs(cli_parsing.parse_interactive_search_argument, parse_interactive_search_argument)
        self.assertIs(cli_parsing.parse_interactive_glob_argument, parse_interactive_glob_argument)
        self.assertIs(cli_parsing.parse_interactive_overview_argument, parse_interactive_overview_argument)
        self.assertIs(cli_parsing.parse_interactive_read_argument, parse_interactive_read_argument)
        self.assertIs(cli_parsing.parse_interactive_read_files_argument, parse_interactive_read_files_argument)
        self.assertIs(cli_parsing.parse_interactive_tree_argument, parse_interactive_tree_argument)
        self.assertIs(cli_parsing.parse_interactive_python_call_graph_argument, parse_interactive_python_call_graph_argument)
        self.assertIs(cli_parsing.parse_interactive_python_symbol_argument, parse_interactive_python_symbol_argument)
        self.assertIs(cli_parsing.parse_interactive_test_paths_argument, parse_interactive_test_paths_argument)
        self.assertIs(cli_parsing.parse_interactive_run_argument, parse_interactive_run_argument)
        self.assertIs(cli_parsing.parse_interactive_run_sequence_argument, parse_interactive_run_sequence_argument)
        self.assertIs(cli_parsing.parse_interactive_wait_process_argument, parse_interactive_wait_process_argument)
        self.assertIs(cli_parsing.parse_interactive_cwd_command_argument, parse_interactive_cwd_command_argument)
        self.assertIs(cli_parsing.parse_interactive_check_run_sequence_argument, parse_cwd_check_run_sequence_argument)
        self.assertIs(cli_parse_run.parse_interactive_wait_process_argument, parse_interactive_wait_process_argument)
        self.assertIs(cli_parse_run.parse_interactive_cwd_command_argument, parse_interactive_cwd_command_argument)
        self.assertIs(cli_parse_run.parse_interactive_check_run_sequence_argument, parse_cwd_check_run_sequence_argument)
        self.assertIs(parse_interactive_check_run_sequence_argument, parse_cwd_check_run_sequence_argument)
        self.assertIs(cli_parsing.parse_interactive_tool_search_argument, parse_interactive_tool_search_argument)

    def test_core_helpers_keep_existing_behavior(self) -> None:
        args = argparse.Namespace(
            focused_tests_max_paths=2,
            focused_tests_max_candidates=None,
            focused_tests_max_commands=3,
        )

        self.assertEqual(parse_cli_json_value('{"ok": true}'), {"ok": True})
        self.assertEqual(timeout_ms("100"), 100)
        self.assertEqual(build_focused_tests_kwargs(args), {"max_paths": 2, "max_commands": 3})

    def test_project_suggested_check_kwargs_preserve_cli_defaults(self) -> None:
        args = argparse.Namespace(
            check_suggested_checks="",
            check_suggested_checks_max=4,
            run_suggested_checks="pytest",
            run_suggested_checks_max=5,
            run_timeout_ms=30_000,
            run_max_chars=12_000,
            run_continue_on_failure=False,
            run_output_contexts=True,
            run_output_diagnostics=False,
            run_output_context_lines=2,
            run_output_diagnostic_max=3,
            run_output_context_max=4,
            run_output_context_max_bytes=500,
        )

        self.assertEqual(build_check_suggested_kwargs(args), {"argument": None, "max_checks": 4})
        self.assertEqual(
            build_run_suggested_kwargs(args),
            {
                "argument": "pytest",
                "max_checks": 5,
                "timeout_ms": 30_000,
                "max_output_chars": 12_000,
                "stop_on_failure": True,
                "extract_output_contexts": True,
                "extract_output_diagnostics": False,
                "context_lines": 2,
                "max_diagnostics": 3,
                "max_contexts": 4,
                "max_bytes_per_context": 500,
            },
        )
        self.assertEqual(kwargs_without_argument({"argument": "pytest", "max_checks": 5}), {"max_checks": 5})

    def test_session_arg_helpers_register_limits_and_local_flags(self) -> None:
        parser = argparse.ArgumentParser()
        local = parser.add_mutually_exclusive_group()
        add_session_limit_arguments(
            parser,
            positive_int=cli_parsing.positive_int,
            nonnegative_int=cli_parsing.nonnegative_int,
        )
        add_session_local_arguments(parser, local)

        args = parser.parse_args(
            [
                "--session-output-command-max",
                "3",
                "--session-output-context-lines",
                "0",
                "--session-max-output-chars",
                "0",
                "--session-handoff",
                "run-1",
            ]
        )

        self.assertEqual(args.session_output_command_max, 3)
        self.assertEqual(args.session_output_context_lines, 0)
        self.assertEqual(args.session_max_output_chars, 0)
        self.assertEqual(args.session_handoff, "run-1")

    def test_diff_and_session_parsers_keep_existing_behavior(self) -> None:
        diff_arg, max_chars, error = parse_interactive_diff_argument("--max-chars=5 --staged src/app.py")
        query, run_id, kwargs, search_error = parse_interactive_session_search_argument(
            "--run run-1 --max-matches 2 --case-sensitive failure"
        )
        spaced_query, spaced_run_id, spaced_kwargs, spaced_error = parse_interactive_session_search_argument(
            '--run " run-2 " needle'
        )

        self.assertEqual(build_diff_argument("src/app.py", True, ["extra.py"]), "--staged src/app.py extra.py")
        self.assertEqual((diff_arg, max_chars, error), ("--staged src/app.py", 5, None))
        self.assertEqual((query, run_id, kwargs, search_error), ("failure", "run-1", {"max_matches": 2, "case_sensitive": True}, None))
        self.assertEqual((spaced_query, spaced_run_id, spaced_kwargs, spaced_error), ("needle", "run-2", {}, None))

    def test_session_run_id_parsers_normalize_optional_run_ids(self) -> None:
        transcript_run_id, transcript_kwargs, transcript_error = parse_interactive_transcript_argument('" run-1 "')
        blank_transcript_run_id, blank_transcript_kwargs, blank_transcript_error = parse_interactive_transcript_argument('"   "')
        detail_run_id, detail_kwargs, detail_error = parse_interactive_session_detail_argument(
            '" run-2 " --max-commands 3',
            "Usage: /session-commands [run-id] [--max-commands N]",
            {"--max-commands": ("max_commands", False)},
        )
        verify_run_id, verify_kwargs, verify_error = parse_interactive_run_session_verification_argument(
            '" run-3 " --max-checks 2'
        )

        self.assertEqual((transcript_run_id, transcript_kwargs, transcript_error), ("run-1", {}, None))
        self.assertEqual((blank_transcript_run_id, blank_transcript_kwargs, blank_transcript_error), (None, {}, None))
        self.assertEqual((detail_run_id, detail_kwargs, detail_error), ("run-2", {"max_commands": 3}, None))
        self.assertEqual((verify_run_id, verify_kwargs, verify_error), ("run-3", {"max_checks": 2}, None))

    def test_run_session_verification_parser_accepts_options(self) -> None:
        run_id, kwargs, error = parse_interactive_run_session_verification_argument(
            "--max-checks=2 --timeout-ms 1000 --max-output-chars 2000 --no-failed "
            "--continue-on-failure --output-contexts --output-diagnostics --context-lines 0 "
            "--max-diagnostics 3 --max-contexts=4 --max-bytes 1000 run-1"
        )
        bad_run_id, bad_kwargs, bad_error = parse_interactive_run_session_verification_argument(
            "--no-failed --no-pending"
        )
        valued_flag_run_id, valued_flag_kwargs, valued_flag_error = parse_interactive_run_session_verification_argument(
            "--output-contexts=true run-1"
        )

        self.assertEqual(run_id, "run-1")
        self.assertEqual(
            kwargs,
            {
                "max_checks": 2,
                "timeout_ms": 1000,
                "max_output_chars": 2000,
                "include_failed": False,
                "stop_on_failure": False,
                "extract_output_contexts": True,
                "extract_output_diagnostics": True,
                "context_lines": 0,
                "max_diagnostics": 3,
                "max_contexts": 4,
                "max_bytes_per_context": 1000,
            },
        )
        self.assertIsNone(error)
        self.assertIsNone(bad_run_id)
        self.assertEqual(bad_kwargs, {})
        self.assertIn("cannot be used together", bad_error or "")
        self.assertIsNone(valued_flag_run_id)
        self.assertEqual(valued_flag_kwargs, {})
        self.assertIn("--output-contexts does not take a value", valued_flag_error or "")

    def test_tool_search_parser_accepts_filters(self) -> None:
        query, kwargs, error = parse_interactive_tool_search_argument(
            "--max=3 --category session --approval no verification"
        )
        any_query, any_kwargs, any_error = parse_interactive_tool_search_argument(
            "--category=project --approval=any tool search"
        )

        self.assertEqual(query, "verification")
        self.assertEqual(kwargs, {"max_matches": 3, "category": "session", "approval_required": False})
        self.assertIsNone(error)
        self.assertEqual(any_query, "tool search")
        self.assertEqual(any_kwargs, {"category": "project", "approval_required": None})
        self.assertIsNone(any_error)

    def test_tool_search_parser_rejects_unknown_category(self) -> None:
        query, kwargs, error = parse_interactive_tool_search_argument("--category missing verification")

        self.assertIsNone(query)
        self.assertEqual(kwargs, {})
        self.assertIn("Usage: /tool-search", error or "")
        self.assertIn("--category must be one of:", error or "")

    def test_tool_search_parser_rejects_unknown_approval_filter(self) -> None:
        query, kwargs, error = parse_interactive_tool_search_argument("--approval maybe verification")

        self.assertIsNone(query)
        self.assertEqual(kwargs, {})
        self.assertIn("Usage: /tool-search", error or "")
        self.assertIn("--approval must be one of: any, yes, no.", error or "")

    def test_runtime_check_parsers_keep_existing_behavior(self) -> None:
        port, port_kwargs, port_error, port_handled = parse_interactive_port_argument("--host 0.0.0.0 --timeout-ms 1500 5173")
        url, http_kwargs, http_error, http_handled = parse_interactive_http_argument(
            "--timeout-ms=2000 --max-body-chars 100 --contains ready --regex http://127.0.0.1:8000"
        )

        self.assertEqual((port, port_kwargs, port_error, port_handled), (5173, {"host": "0.0.0.0", "timeout_ms": 1500}, None, True))
        self.assertEqual(
            (url, http_kwargs, http_error, http_handled),
            ("http://127.0.0.1:8000", {"timeout_ms": 2000, "max_body_chars": 100, "contains": "ready", "regex": True}, None, True),
        )

    def test_discovery_parsers_keep_existing_behavior(self) -> None:
        query, search_kwargs, search_error, search_handled = parse_interactive_search_argument(
            "--path vibeagent --regex --context-lines 2 --max-bytes 100 -- TODO",
            include_max_bytes=True,
        )
        pattern, glob_kwargs, glob_error, glob_handled = parse_interactive_glob_argument("--include-dirs --max-matches=4 -- *.py")
        overview_kwargs, overview_error, overview_handled = parse_interactive_overview_argument(
            "--max-files 3 --max-commands=2 --max-checks 1"
        )

        self.assertEqual(
            (query, search_kwargs, search_error, search_handled),
            ("TODO", {"path": "vibeagent", "regex": True, "context_lines": 2, "max_bytes_per_context": 100}, None, True),
        )
        self.assertEqual((pattern, glob_kwargs, glob_error, glob_handled), ("*.py", {"include_dirs": True, "max_matches": 4}, None, True))
        self.assertEqual((overview_kwargs, overview_error, overview_handled), ({"max_files": 3, "max_commands": 2, "max_checks": 1}, None, True))

    def test_read_parsers_keep_existing_behavior(self) -> None:
        read_arg, read_kwargs, read_error, read_handled = parse_interactive_read_argument(
            "--line-numbers --max-bytes 80 -- src/app.py 10:12"
        )
        paths, files_kwargs, files_error, files_handled = parse_interactive_read_files_argument(
            "--line-numbers=false --max-bytes=200 -- a.py b.py"
        )
        tree_path, tree_kwargs, tree_error, tree_handled = parse_interactive_tree_argument(
            "--max-depth 2 --max-entries=5 src"
        )

        self.assertEqual((read_arg, read_kwargs, read_error, read_handled), ("src/app.py 10:12", {"show_line_numbers": True, "max_bytes": 80}, None, True))
        self.assertEqual((paths, files_kwargs, files_error, files_handled), (["a.py", "b.py"], {"show_line_numbers": False, "max_bytes_per_file": 200}, None, True))
        self.assertEqual((tree_path, tree_kwargs, tree_error, tree_handled), ("src", {"max_depth": 2, "max_entries": 5}, None, True))

    def test_code_intel_parsers_keep_existing_behavior(self) -> None:
        path_arg, test_kwargs, test_error, test_handled = parse_interactive_test_paths_argument(
            "--max-paths 2 --max-candidates=3 --max-commands 4 -- src/app.py tests/test_app.py",
            "Usage: /run-focused-tests [path...]",
            include_max_commands=True,
        )
        symbol, path, symbol_kwargs, symbol_error, symbol_handled = parse_interactive_python_symbol_argument(
            "--path src/app.py --max-matches 5 --context-lines 2 --max-bytes=100 -- handle_request",
            command_name="python-ref-contexts",
            include_context=True,
        )
        graph_path, graph_kwargs, graph_error, graph_handled = parse_interactive_python_call_graph_argument(
            "--max-files 2 --max-edges=7 -- src/app.py"
        )

        self.assertEqual((path_arg, test_kwargs, test_error, test_handled), ("src/app.py tests/test_app.py", {"max_paths": 2, "max_candidates": 3, "max_commands": 4}, None, True))
        self.assertEqual((symbol, path, symbol_kwargs, symbol_error, symbol_handled), ("handle_request", "src/app.py", {"max_matches": 5, "context_lines": 2, "max_bytes_per_context": 100}, None, True))
        self.assertEqual((graph_path, graph_kwargs, graph_error, graph_handled), ("src/app.py", {"max_files": 2, "max_edges": 7}, None, True))

    def test_run_parsers_keep_existing_behavior(self) -> None:
        command, kwargs, error, handled = parse_interactive_run_argument(
            "--timeout-ms 1000 --max-chars=80 --cwd src --output-contexts -- python -m unittest"
        )
        commands, seq_kwargs, seq_error, seq_handled = parse_interactive_run_sequence_argument(
            "--continue-on-failure --timeout-ms=2000 -- echo one ;; echo two"
        )
        preview_commands, cwd, preview_error, preview_handled = parse_interactive_check_run_sequence_argument(
            "--cwd src -- echo one ;; echo two"
        )

        self.assertEqual(
            (command, kwargs, error, handled),
            (
                "python -m unittest",
                {"timeout_ms": 1000, "max_output_chars": 80, "cwd": "src", "extract_output_contexts": True},
                None,
                True,
            ),
        )
        self.assertEqual(
            (commands, seq_kwargs, seq_error, seq_handled),
            (["echo one", "echo two"], {"stop_on_failure": False, "timeout_ms": 2000}, None, True),
        )
        self.assertEqual(
            (preview_commands, cwd, preview_error, preview_handled),
            (["echo one", "echo two"], "src", None, True),
        )


if __name__ == "__main__":
    unittest.main()
