from __future__ import annotations

import argparse


def validate_local_option_dependencies(args: argparse.Namespace) -> str | None:
    if args.diff_staged and args.diff is None and args.diff_hunks is None and args.diff_contexts is None:
        return "--staged can only be used with --diff, --diff-hunks, or --diff-contexts."
    if args.command_cwd and not args.command_check:
        return "--command-cwd can only be used with --command-check or --command."
    if args.run_cwd and args.run_command is None and args.run_commands is None and args.check_run_commands is None:
        return "--run-cwd can only be used with --run-command, --run, --run-commands, or --check-run-commands."
    if args.start_cwd and args.start_command is None and args.check_start_command is None:
        return "--start-cwd can only be used with --check-start-command, --start-command, or --start."
    if args.port_host != "127.0.0.1" and args.port_check is None:
        return "--port-host can only be used with --port-check."
    if args.port_timeout_ms != 1000 and args.port_check is None:
        return "--port-timeout-ms can only be used with --port-check."
    if args.http_timeout_ms is not None and args.http_check is None and args.http_fetch is None:
        return "--http-timeout-ms can only be used with --http-check or --http-fetch."
    if args.http_max_body_chars is not None and args.http_check is None and args.http_fetch is None:
        return "--http-max-body-chars can only be used with --http-check or --http-fetch."
    if args.http_contains is not None and args.http_check is None:
        return "--http-contains can only be used with --http-check."
    if args.http_regex and args.http_check is None:
        return "--http-regex can only be used with --http-check."
    search_selected = args.search is not None or args.search_contexts is not None
    if args.search_path and not search_selected:
        return "--search-path can only be used with --search or --search-contexts."
    if args.search_max_matches is not None and not search_selected:
        return "--search-max-matches can only be used with --search or --search-contexts."
    if args.search_regex and not search_selected:
        return "--search-regex can only be used with --search or --search-contexts."
    if args.search_ignore_case and not search_selected:
        return "--search-ignore-case can only be used with --search or --search-contexts."
    if args.search_context_lines is not None and not search_selected:
        return "--search-context-lines can only be used with --search or --search-contexts."
    if args.search_context_max_bytes is not None and args.search_contexts is None:
        return "--search-context-max-bytes can only be used with --search-contexts."
    if args.tool_search_max != 20 and args.tool_search is None:
        return "--tool-search-max can only be used with --tool-search."
    if args.tool_search_category is not None and args.tool_search is None:
        return "--tool-search-category can only be used with --tool-search."
    if args.tool_search_approval != "any" and args.tool_search is None:
        return "--tool-search-approval can only be used with --tool-search."
    if args.find_files_path and args.find_files is None:
        return "--find-files-path can only be used with --find-files."
    if args.find_files_max_matches is not None and args.find_files is None:
        return "--find-files-max-matches can only be used with --find-files."
    if args.find_files_regex and args.find_files is None:
        return "--find-files-regex can only be used with --find-files."
    if args.find_files_case_sensitive and args.find_files is None:
        return "--find-files-case-sensitive can only be used with --find-files."
    if args.find_files_include_dirs and args.find_files is None:
        return "--find-files-include-dirs can only be used with --find-files."
    if args.related_tests_max_paths is not None and args.related_tests is None:
        return "--related-tests-max-paths can only be used with --related-tests."
    if args.related_tests_max_candidates is not None and args.related_tests is None:
        return "--related-tests-max-candidates can only be used with --related-tests."
    focused_tests_selected = args.focused_tests is not None or args.check_focused_tests is not None or args.run_focused_tests is not None
    if args.focused_tests_max_paths is not None and not focused_tests_selected:
        return "--focused-tests-max-paths can only be used with --focused-tests, --check-focused-tests, or --run-focused-tests."
    if args.focused_tests_max_candidates is not None and not focused_tests_selected:
        return "--focused-tests-max-candidates can only be used with --focused-tests, --check-focused-tests, or --run-focused-tests."
    if args.focused_tests_max_commands is not None and not focused_tests_selected:
        return "--focused-tests-max-commands can only be used with --focused-tests, --check-focused-tests, or --run-focused-tests."
    if args.commands_max_commands is not None and not args.commands:
        return "--commands-max-commands can only be used with --commands."
    if args.commands_max_files is not None and not args.commands:
        return "--commands-max-files can only be used with --commands."
    if args.manifests_max_files is not None and not args.manifests:
        return "--manifests-max-files can only be used with --manifests."
    if args.manifests_max_items is not None and not args.manifests:
        return "--manifests-max-items can only be used with --manifests."
    if args.todos_max_items is not None and args.todos is None:
        return "--todos-max-items can only be used with --todos."
    if args.todos_max_files is not None and args.todos is None:
        return "--todos-max-files can only be used with --todos."
    if args.instructions_max_files is not None and not args.instructions:
        return "--instructions-max-files can only be used with --instructions."
    if args.instructions_max_bytes is not None and not args.instructions:
        return "--instructions-max-bytes can only be used with --instructions."
    if args.overview_max_files is not None and not args.overview:
        return "--overview-max-files can only be used with --overview."
    if args.overview_max_commands is not None and not args.overview:
        return "--overview-max-commands can only be used with --overview."
    if args.overview_max_checks is not None and not args.overview:
        return "--overview-max-checks can only be used with --overview."
    if args.repo_map_max_depth is not None and args.repo_map is None:
        return "--repo-map-max-depth can only be used with --repo-map."
    if args.repo_map_max_files is not None and args.repo_map is None:
        return "--repo-map-max-files can only be used with --repo-map."
    if args.repo_map_max_symbols is not None and args.repo_map is None:
        return "--repo-map-max-symbols can only be used with --repo-map."
    if args.glob_max_matches is not None and args.glob is None:
        return "--glob-max-matches can only be used with --glob."
    if args.glob_include_dirs and args.glob is None:
        return "--glob-include-dirs can only be used with --glob."
    if args.tree_max_depth is not None and args.tree is None:
        return "--tree-max-depth can only be used with --tree."
    if args.tree_max_entries is not None and args.tree is None:
        return "--tree-max-entries can only be used with --tree."
    if args.symbols_max is not None and args.symbols is None:
        return "--symbols-max can only be used with --symbols."
    python_symbol_lookup_selected = (
        args.python_defs is not None
        or args.python_refs is not None
        or args.python_ref_contexts is not None
        or args.python_calls is not None
    )
    if args.python_max_matches is not None and not python_symbol_lookup_selected:
        return "--python-max-matches can only be used with --python-defs, --python-refs, --python-ref-contexts, or --python-calls."
    if args.python_def_max_lines is not None and args.python_defs is None:
        return "--python-def-max-lines can only be used with --python-defs."
    if args.python_context_lines is not None and args.python_ref_contexts is None:
        return "--python-context-lines can only be used with --python-ref-contexts."
    if args.python_context_max_bytes is not None and args.python_ref_contexts is None:
        return "--python-context-max-bytes can only be used with --python-ref-contexts."
    if args.python_deps_max_files is not None and args.python_deps is None:
        return "--python-deps-max-files can only be used with --python-deps."
    if args.python_deps_max_imports is not None and args.python_deps is None:
        return "--python-deps-max-imports can only be used with --python-deps."
    if args.python_call_graph_max_files is not None and args.python_call_graph is None:
        return "--python-call-graph-max-files can only be used with --python-call-graph."
    if args.python_call_graph_max_edges is not None and args.python_call_graph is None:
        return "--python-call-graph-max-edges can only be used with --python-call-graph."
    code_symbol_lookup_selected = (
        args.code_refs is not None
        or args.code_ref_contexts is not None
        or args.code_defs is not None
    )
    if args.code_max_matches is not None and not code_symbol_lookup_selected:
        return "--code-max-matches can only be used with --code-refs, --code-ref-contexts, or --code-defs."
    if args.code_def_max_lines is not None and args.code_defs is None:
        return "--code-def-max-lines can only be used with --code-defs."
    if args.code_context_lines is not None and args.code_ref_contexts is None:
        return "--code-context-lines can only be used with --code-ref-contexts."
    if args.code_context_max_bytes is not None and args.code_ref_contexts is None:
        return "--code-context-max-bytes can only be used with --code-ref-contexts."
    if args.read_lines and args.read is None:
        return "--read-lines can only be used with --read."
    if args.read_max_bytes is not None and args.read is None:
        return "--read-max-bytes can only be used with --read."
    if args.read_line_numbers and args.read is None:
        return "--read-line-numbers can only be used with --read."
    if args.read_files_max_bytes is not None and args.read_files is None:
        return "--read-files-max-bytes can only be used with --read-files."
    if args.read_files_line_numbers and args.read_files is None:
        return "--read-files-line-numbers can only be used with --read-files."
    if args.read_ranges_max_bytes is not None and args.read_ranges is None:
        return "--read-ranges-max-bytes can only be used with --read-ranges."
    if args.around_lines != 20 and args.around is None:
        return "--around-lines can only be used with --around."
    if args.around_max_bytes is not None and args.around is None:
        return "--around-max-bytes can only be used with --around."
    if args.around_many_max_bytes is not None and args.around_many is None:
        return "--around-many-max-bytes can only be used with --around-many."
    if args.output_context_lines != 5 and args.output_contexts is None:
        return "--output-context-lines can only be used with --output-contexts."
    if args.output_context_max != 20 and args.output_contexts is None:
        return "--output-context-max can only be used with --output-contexts."
    if args.output_context_max_bytes != 20_000 and args.output_contexts is None:
        return "--output-context-max-bytes can only be used with --output-contexts."
    output_diagnostic_analysis = args.output_diagnostics is not None or args.python_traceback is not None
    if args.output_diagnostic_lines != 2 and not output_diagnostic_analysis:
        return "--output-diagnostic-lines can only be used with --output-diagnostics or --python-traceback."
    if args.output_diagnostic_max != 50 and not output_diagnostic_analysis:
        return "--output-diagnostic-max can only be used with --output-diagnostics or --python-traceback."
    if args.output_diagnostic_context_max != 20 and not output_diagnostic_analysis:
        return "--output-diagnostic-context-max can only be used with --output-diagnostics or --python-traceback."
    if args.output_diagnostic_context_max_bytes != 20_000 and not output_diagnostic_analysis:
        return "--output-diagnostic-context-max-bytes can only be used with --output-diagnostics or --python-traceback."
    session_output_analysis = args.session_output_contexts is not None or args.session_output_diagnostics is not None
    if args.session_output_command_max != 20 and not session_output_analysis:
        return "--session-output-command-max can only be used with --session-output-contexts or --session-output-diagnostics."
    if args.session_output_max_chars != 20_000 and not session_output_analysis:
        return "--session-output-max-chars can only be used with --session-output-contexts or --session-output-diagnostics."
    if args.session_output_context_lines != 5 and not session_output_analysis:
        return "--session-output-context-lines can only be used with --session-output-contexts or --session-output-diagnostics."
    if args.session_output_context_max != 20 and not session_output_analysis:
        return "--session-output-context-max can only be used with --session-output-contexts or --session-output-diagnostics."
    if args.session_output_context_max_bytes != 20_000 and not session_output_analysis:
        return "--session-output-context-max-bytes can only be used with --session-output-contexts or --session-output-diagnostics."
    if args.session_output_diagnostic_max != 50 and args.session_output_diagnostics is None:
        return "--session-output-diagnostic-max can only be used with --session-output-diagnostics."
    if args.checks_max != 20 and not args.checks:
        return "--checks-max can only be used with --checks."
    if args.check_suggested_checks_max != 10 and args.check_suggested_checks is None:
        return "--check-suggested-checks-max can only be used with --check-suggested-checks."
    if args.run_suggested_checks_max != 10 and args.run_suggested_checks is None:
        return "--run-suggested-checks-max can only be used with --run-suggested-checks."
    session_transcript_view = args.transcript is not None
    session_search_view = args.session_search is not None
    session_command_view = args.session_commands is not None or args.session_audit is not None or args.session_handoff is not None
    session_file_view = args.session_files is not None or args.session_audit is not None or args.session_handoff is not None
    session_failure_view = args.session_failures is not None or args.session_audit is not None or args.session_handoff is not None
    session_text_view = session_transcript_view or session_search_view or args.session_failures is not None or args.session_audit is not None or args.session_handoff is not None
    if args.session_transcript_event_max is not None and not session_transcript_view:
        return "--session-transcript-event-max can only be used with --transcript."
    if args.session_search_match_max is not None and not session_search_view:
        return "--session-search-match-max can only be used with --session-search."
    if args.session_search_case_sensitive and not session_search_view:
        return "--session-search-case-sensitive can only be used with --session-search."
    if args.session_max_checks is not None and args.session_verification is None and args.run_session_verification is None and args.session_audit is None and args.session_handoff is None:
        return "--session-max-checks can only be used with --session-verification, --run-session-verification, --session-audit, or --session-handoff."
    if args.session_max_commands is not None and not session_command_view:
        return "--session-max-commands can only be used with --session-commands, --session-audit, or --session-handoff."
    if args.session_max_output_chars is not None and args.session_commands is None and args.session_handoff is None:
        return "--session-max-output-chars can only be used with --session-commands or --session-handoff."
    if args.session_max_files is not None and not session_file_view:
        return "--session-max-files can only be used with --session-files, --session-audit, or --session-handoff."
    if args.session_max_failures is not None and not session_failure_view:
        return "--session-max-failures can only be used with --session-failures, --session-audit, or --session-handoff."
    if args.session_max_text is not None and not session_text_view:
        return "--session-max-text can only be used with --transcript, --session-search, --session-failures, --session-audit, or --session-handoff."
    if args.tail_lines != 80 and args.tail is None:
        return "--tail-lines can only be used with --tail."
    if args.tail_max_bytes is not None and args.tail is None:
        return "--tail-max-bytes can only be used with --tail."
    if args.log_count != 5 and args.log is None:
        return "--log-count can only be used with --log."
    if args.show_path and args.show is None:
        return "--show-path can only be used with --show."
    if args.show_max_chars != 12000 and args.show is None:
        return "--show-max-chars can only be used with --show."
    if args.blame_lines and args.blame is None:
        return "--blame-lines can only be used with --blame."
    if args.blame_max_chars != 12000 and args.blame is None:
        return "--blame-max-chars can only be used with --blame."
    if args.review_max_files != 200 and not args.review:
        return "--review-max-files can only be used with --review."
    if args.review_max_checks != 5 and not args.review:
        return "--review-max-checks can only be used with --review."
    if args.handoff_max_files != 200 and not args.handoff:
        return "--handoff-max-files can only be used with --handoff."
    if args.handoff_max_checks != 10 and not args.handoff:
        return "--handoff-max-checks can only be used with --handoff."
    if args.handoff_max_status_chars != 4_000 and not args.handoff:
        return "--handoff-max-status-chars can only be used with --handoff."
    if args.handoff_max_plan_chars != 4_000 and not args.handoff:
        return "--handoff-max-plan-chars can only be used with --handoff."
    if args.changes_max_files != 200 and not args.changes:
        return "--changes-max-files can only be used with --changes."
    if args.stash_count != 20 and not args.stashes:
        return "--stash-count can only be used with --stashes."
    if args.stash_include_untracked and args.check_git_stash is None and args.git_stash is None:
        return "--stash-include-untracked can only be used with --check-git-stash or --git-stash."
    if args.diff_max_chars != 12_000 and args.diff is None:
        return "--diff-max-chars can only be used with --diff."
    if args.diff_hunks_max_hunks != 80 and args.diff_hunks is None:
        return "--diff-hunks-max-hunks can only be used with --diff-hunks."
    if args.diff_hunks_max_lines != 80 and args.diff_hunks is None:
        return "--diff-hunks-max-lines can only be used with --diff-hunks."
    if args.diff_context_lines != 5 and args.diff_contexts is None:
        return "--diff-context-lines can only be used with --diff-contexts."
    if args.diff_contexts_max_hunks != 80 and args.diff_contexts is None:
        return "--diff-contexts-max-hunks can only be used with --diff-contexts."
    if args.diff_contexts_max_bytes != 20_000 and args.diff_contexts is None:
        return "--diff-contexts-max-bytes can only be used with --diff-contexts."
    if args.git_switch_create and args.check_git_switch is None and args.git_switch is None:
        return "--git-switch-create can only be used with --check-git-switch or --git-switch."
    process_output_analysis = args.process_output_contexts is not None or args.process_output_diagnostics is not None
    if args.process_max_chars is not None and args.process_output is None and not process_output_analysis:
        return "--process-max-chars can only be used with --process-output, --process-output-contexts, or --process-output-diagnostics."
    if args.process_output_context_lines != 5 and not process_output_analysis:
        return "--process-output-context-lines can only be used with --process-output-contexts or --process-output-diagnostics."
    if args.process_output_context_max != 20 and not process_output_analysis:
        return "--process-output-context-max can only be used with --process-output-contexts or --process-output-diagnostics."
    if args.process_output_context_max_bytes != 20000 and not process_output_analysis:
        return "--process-output-context-max-bytes can only be used with --process-output-contexts or --process-output-diagnostics."
    if args.process_output_diagnostic_max != 50 and args.process_output_diagnostics is None:
        return "--process-output-diagnostic-max can only be used with --process-output-diagnostics."
    if args.wait_timeout_ms != 5000 and args.wait_process is None:
        return "--wait-timeout-ms can only be used with --wait-process."
    if args.wait_max_chars is not None and args.wait_process is None:
        return "--wait-max-chars can only be used with --wait-process."
    if args.wait_stdout and args.wait_process is None:
        return "--wait-stdout can only be used with --wait-process."
    if args.wait_stderr and args.wait_process is None:
        return "--wait-stderr can only be used with --wait-process."
    if args.wait_regex and args.wait_process is None:
        return "--wait-regex can only be used with --wait-process."
    write_stdin_target = args.check_write_process is not None or args.write_process is not None
    if args.write_stdin is not None and not write_stdin_target:
        return "--write-stdin can only be used with --check-write-process or --write-process."
    if args.check_write_process is not None and args.write_stdin is None:
        return "--check-write-process requires --write-stdin."
    if args.write_process is not None and args.write_stdin is None:
        return "--write-process requires --write-stdin."
    run_target = (
        args.run_command is not None
        or args.run_commands is not None
        or args.run_suggested_checks is not None
        or args.run_focused_tests is not None
        or args.run_session_verification is not None
    )
    if args.run_timeout_ms != 30000 and not run_target:
        return "--run-timeout-ms can only be used with --run-command, --run, --run-commands, --run-suggested-checks, --run-focused-tests, or --run-session-verification."
    if args.run_max_chars != 12000 and not run_target:
        return "--run-max-chars can only be used with --run-command, --run, --run-commands, --run-suggested-checks, --run-focused-tests, or --run-session-verification."
    if args.run_continue_on_failure and args.run_commands is None and args.run_suggested_checks is None and args.run_focused_tests is None and args.run_session_verification is None:
        return "--run-continue-on-failure can only be used with --run-commands, --run-suggested-checks, --run-focused-tests, or --run-session-verification."
    if args.run_session_no_failed and args.run_session_verification is None:
        return "--run-session-no-failed can only be used with --run-session-verification."
    if args.run_session_no_pending and args.run_session_verification is None:
        return "--run-session-no-pending can only be used with --run-session-verification."
    if args.run_session_no_failed and args.run_session_no_pending:
        return "--run-session-no-failed and --run-session-no-pending cannot be used together."
    run_output_context_target = (
        args.run_command is not None
        or args.run_commands is not None
        or args.run_suggested_checks is not None
        or args.run_focused_tests is not None
        or args.run_session_verification is not None
    )
    if args.run_output_contexts and not run_output_context_target:
        return "--run-output-contexts can only be used with --run-command, --run, --run-commands, --run-suggested-checks, --run-focused-tests, or --run-session-verification."
    if args.run_output_diagnostics and not run_output_context_target:
        return "--run-output-diagnostics can only be used with --run-command, --run, --run-commands, --run-suggested-checks, --run-focused-tests, or --run-session-verification."
    if args.run_output_context_lines != 5 and not run_output_context_target:
        return "--run-output-context-lines can only be used with --run-command, --run, --run-commands, --run-suggested-checks, --run-focused-tests, or --run-session-verification."
    if args.run_output_context_max != 20 and not run_output_context_target:
        return "--run-output-context-max can only be used with --run-command, --run, --run-commands, --run-suggested-checks, --run-focused-tests, or --run-session-verification."
    if args.run_output_context_max_bytes != 20000 and not run_output_context_target:
        return "--run-output-context-max-bytes can only be used with --run-command, --run, --run-commands, --run-suggested-checks, --run-focused-tests, or --run-session-verification."
    if args.run_output_diagnostic_max != 50 and not run_output_context_target:
        return "--run-output-diagnostic-max can only be used with --run-command, --run, --run-commands, --run-suggested-checks, --run-focused-tests, or --run-session-verification."
    return None
