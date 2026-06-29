import inspect
import json
import os
import re
import subprocess
import tempfile
import time
import unittest
from pathlib import Path
from typing import get_args, get_type_hints
from unittest.mock import patch

from vibeagent.commands import (
    LocalCommand,
    get_append_file_text,
    get_blame_text,
    get_branches_text,
    get_checks_report,
    get_checks_text,
    get_changes_text,
    get_check_checkpoint_delete_text,
    get_check_checkpoint_prune_text,
    get_check_checkpoint_restore_text,
    get_checkpoint_delete_text,
    get_checkpoint_diff_text,
    get_checkpoint_prune_text,
    get_checkpoint_restore_text,
    get_checkpoint_show_text,
    get_checkpoint_status_text,
    get_checkpoint_text,
    get_checkpoints_text,
    get_check_copy_dir_text,
    get_check_copy_dirs_text,
    get_check_copy_file_text,
    get_check_copy_files_text,
    get_check_create_dirs_text,
    get_check_create_dir_text,
    get_check_delete_file_text,
    get_check_delete_files_text,
    get_check_delete_empty_dirs_text,
    get_check_delete_empty_dir_text,
    get_check_edit_file_text,
    get_check_fetch_text,
    get_check_focused_test_commands_text,
    get_check_pull_text,
    get_check_push_text,
    get_check_set_executable_text,
    get_check_stash_text,
    get_check_stash_apply_text,
    get_check_stash_drop_text,
    get_check_switch_text,
    get_check_append_file_text,
    get_check_insert_lines_text,
    get_check_move_dir_text,
    get_check_move_dirs_text,
    get_check_move_file_text,
    get_check_move_files_text,
    get_check_multi_edit_file_text,
    get_check_patch_text,
    get_check_patches_text,
    get_check_write_file_text,
    get_check_write_files_text,
    get_check_run_sequence_text,
    get_check_start_text,
    get_check_stop_all_processes_text,
    get_check_stop_process_text,
    get_check_suggested_checks_text,
    get_check_write_process_text,
    get_check_commit_text,
    get_check_json_patch_text,
    get_check_regex_replace_text,
    get_check_replace_lines_text,
    get_check_replace_python_definition_text,
    get_check_restore_text,
    get_check_stage_text,
    get_check_unstage_text,
    get_check_json_remove_text,
    get_check_json_set_text,
    get_code_defs_text,
    get_code_deps_text,
    get_code_ref_contexts_text,
    get_code_rename_preview_text,
    get_code_rename_text,
    get_code_refs_text,
    get_compact_context,
    get_command_check_text,
    get_commands_text,
    get_config_text,
    get_context_text,
    get_around_text,
    get_around_many_text,
    get_output_contexts_text,
    get_output_diagnostics_text,
    get_python_traceback_text,
    get_commit_text,
    get_config_check_text,
    get_copy_dir_text,
    get_copy_dirs_text,
    get_copy_file_text,
    get_copy_files_text,
    get_cost_text,
    get_create_dirs_text,
    get_create_dir_text,
    get_delete_file_text,
    get_delete_files_text,
    get_delete_empty_dirs_text,
    get_delete_empty_dir_text,
    get_diff_contexts_text,
    get_diff_hunks_text,
    get_diff_text,
    get_doctor_report,
    get_doctor_text,
    get_edit_file_text,
    get_env_text,
    get_fetch_text,
    get_file_info_text,
    get_focused_test_commands_text,
    get_image_info_text,
    get_git_conflicts_text,
    get_git_info_text,
    get_git_status_text,
    get_glob_text,
    get_handoff_text,
    get_http_fetch_text,
    get_http_text,
    get_instructions_text,
    get_insert_lines_text,
    get_json_patch_text,
    get_json_remove_text,
    get_json_set_text,
    get_last_session_text,
    get_log_text,
    get_manifests_text,
    get_model_text,
    get_move_dir_text,
    get_move_dirs_text,
    get_move_file_text,
    get_move_files_text,
    get_multi_edit_file_text,
    get_overview_text,
    get_patch_text,
    get_patches_text,
    get_permissions_text,
    get_permissions_report,
    get_plan_text,
    get_port_text,
    get_pull_text,
    get_push_text,
    get_process_output_contexts_text,
    get_process_output_diagnostics_text,
    get_process_text,
    get_processes_text,
    get_python_call_graph_text,
    get_python_calls_text,
    get_python_check_text,
    get_python_defs_text,
    get_python_deps_text,
    get_python_ref_contexts_text,
    get_python_refs_text,
    get_python_rename_preview_text,
    get_python_rename_text,
    get_read_files_text,
    get_read_ranges_text,
    get_read_text,
    get_related_tests_text,
    get_tail_text,
    get_todos_text,
    get_regex_replace_text,
    get_replace_lines_text,
    get_replace_python_definition_text,
    get_repo_map_text,
    get_review_text,
    get_resume_context,
    get_restore_text,
    get_run_sequence_text,
    get_run_suggested_checks_text,
    get_run_focused_test_commands_text,
    get_run_text,
    get_session_audit_text,
    get_session_commands_text,
    get_session_output_contexts_text,
    get_session_output_diagnostics_text,
    get_session_failures_text,
    get_session_files_text,
    get_session_handoff_text,
    get_session_search_text,
    get_session_verification_text,
    get_session_text,
    get_sessions_text,
    get_search_text,
    get_search_contexts_text,
    get_set_executable_text,
    get_show_text,
    get_start_text,
    get_stash_apply_text,
    get_stash_drop_text,
    get_stash_text,
    get_stage_text,
    get_stashes_text,
    get_status_text,
    get_stop_all_processes_text,
    get_stop_process_text,
    get_switch_text,
    get_symbols_text,
    get_tool_text,
    get_tools_text,
    get_tree_text,
    get_transcript_text,
    get_unstage_text,
    get_usage_text,
    get_wait_process_text,
    get_write_file_text,
    get_write_files_text,
    get_write_process_text,
    init_project_instructions,
    is_exit_command,
    parse_local_command,
)
from vibeagent.types import CheckStopAllProcessesObservation, CheckStopProcessObservation, CheckWriteProcessObservation, FinalReviewObservation, HttpCheckObservation, HttpFetchObservation, ListProcessesObservation, OutputContextResult, OutputDiagnostic, PortCheckObservation, ProcessInfo, ProcessOutputContextsObservation, ProcessOutputDiagnosticsObservation, ReadProcessObservation, StopAllProcessesObservation, StoppedProcessInfo, WaitProcessObservation


def write_session_events(project_root: Path, run_id: str, rows: list[dict], mtime: int | None = None) -> None:
    events_dir = project_root / ".vibeagent" / "sessions" / run_id
    events_dir.mkdir(parents=True, exist_ok=True)
    lines = [json.dumps(row, ensure_ascii=False) for row in rows]
    events_path = events_dir / "events.jsonl"
    events_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    if mtime is not None:
        os.utime(events_path, (mtime, mtime))


class CommandTests(unittest.TestCase):
    def test_is_exit_command_only_treats_exit_as_the_exit_command(self) -> None:
        self.assertTrue(is_exit_command("/exit"))
        self.assertTrue(is_exit_command("  /exit  "))
        self.assertFalse(is_exit_command("exit"))
        self.assertFalse(is_exit_command("/quit"))
        self.assertFalse(is_exit_command("/exit now"))

    def test_parse_local_command_recognizes_local_commands(self) -> None:
        self.assertEqual(parse_local_command("/help"), LocalCommand(type="help"))
        self.assertEqual(parse_local_command("  /model  "), LocalCommand(type="model"))
        self.assertEqual(parse_local_command("/config"), LocalCommand(type="config"))
        self.assertEqual(parse_local_command("/tools"), LocalCommand(type="tools"))
        self.assertEqual(parse_local_command("/tool read_file"), LocalCommand(type="tool", argument="read_file"))
        self.assertEqual(parse_local_command("/tool"), LocalCommand(type="tool"))
        self.assertEqual(parse_local_command("/permissions"), LocalCommand(type="permissions"))
        self.assertEqual(parse_local_command("/checks"), LocalCommand(type="checks"))
        self.assertEqual(parse_local_command("/checks --max-checks 2"), LocalCommand(type="checks", argument="--max-checks 2"))
        self.assertEqual(parse_local_command("/check-suggested-checks"), LocalCommand(type="check_suggested_checks"))
        self.assertEqual(parse_local_command("/check-suggested-checks 2"), LocalCommand(type="check_suggested_checks", argument="2"))
        self.assertEqual(parse_local_command("/run-suggested-checks"), LocalCommand(type="run_suggested_checks"))
        self.assertEqual(parse_local_command("/run-suggested-checks 2"), LocalCommand(type="run_suggested_checks", argument="2"))
        self.assertEqual(parse_local_command("/commands"), LocalCommand(type="commands"))
        self.assertEqual(parse_local_command("/commands --max-commands 2 --max-files 3"), LocalCommand(type="commands", argument="--max-commands 2 --max-files 3"))
        self.assertEqual(parse_local_command("/related-tests src/app.py tests/test_app.py"), LocalCommand(type="related_tests", argument="src/app.py tests/test_app.py"))
        self.assertEqual(parse_local_command("/related-tests"), LocalCommand(type="related_tests"))
        self.assertEqual(parse_local_command("/focused-tests src/app.py tests/test_app.py"), LocalCommand(type="focused_test_commands", argument="src/app.py tests/test_app.py"))
        self.assertEqual(parse_local_command("/focused-tests"), LocalCommand(type="focused_test_commands"))
        self.assertEqual(parse_local_command("/check-focused-tests src/app.py tests/test_app.py"), LocalCommand(type="check_focused_test_commands", argument="src/app.py tests/test_app.py"))
        self.assertEqual(parse_local_command("/check-focused-tests"), LocalCommand(type="check_focused_test_commands"))
        self.assertEqual(parse_local_command("/run-focused-tests src/app.py tests/test_app.py"), LocalCommand(type="run_focused_test_commands", argument="src/app.py tests/test_app.py"))
        self.assertEqual(parse_local_command("/run-focused-tests"), LocalCommand(type="run_focused_test_commands"))
        self.assertEqual(parse_local_command("/manifests"), LocalCommand(type="manifests"))
        self.assertEqual(parse_local_command("/manifests --max-files 2 --max-items 10"), LocalCommand(type="manifests", argument="--max-files 2 --max-items 10"))
        self.assertEqual(parse_local_command("/instructions"), LocalCommand(type="instructions"))
        self.assertEqual(parse_local_command("/instructions --max-files 2 --max-bytes 1000"), LocalCommand(type="instructions", argument="--max-files 2 --max-bytes 1000"))
        self.assertEqual(parse_local_command("/todos"), LocalCommand(type="todos"))
        self.assertEqual(parse_local_command("/todos src"), LocalCommand(type="todos", argument="src"))
        self.assertEqual(parse_local_command("/command python -m unittest"), LocalCommand(type="command", argument="python -m unittest"))
        self.assertEqual(parse_local_command("/command"), LocalCommand(type="command"))
        self.assertEqual(parse_local_command("/run python3 --version"), LocalCommand(type="run", argument="python3 --version"))
        self.assertEqual(parse_local_command("/run"), LocalCommand(type="run"))
        self.assertEqual(parse_local_command("/run-seq python3 --version ;; npm test"), LocalCommand(type="run_sequence", argument="python3 --version ;; npm test"))
        self.assertEqual(parse_local_command("/run-seq"), LocalCommand(type="run_sequence"))
        self.assertEqual(parse_local_command("/check-run-seq python3 --version ;; npm test"), LocalCommand(type="check_run_sequence", argument="python3 --version ;; npm test"))
        self.assertEqual(parse_local_command("/check-run-seq"), LocalCommand(type="check_run_sequence"))
        self.assertEqual(parse_local_command("/check-start npm run dev"), LocalCommand(type="check_start", argument="npm run dev"))
        self.assertEqual(parse_local_command("/check-start"), LocalCommand(type="check_start"))
        self.assertEqual(parse_local_command("/start npm run dev"), LocalCommand(type="start", argument="npm run dev"))
        self.assertEqual(parse_local_command("/start"), LocalCommand(type="start"))
        self.assertEqual(parse_local_command("/port 5173 127.0.0.1 1500"), LocalCommand(type="port", argument="5173 127.0.0.1 1500"))
        self.assertEqual(parse_local_command("/port"), LocalCommand(type="port"))
        self.assertEqual(parse_local_command("/http http://127.0.0.1:5173 ready"), LocalCommand(type="http", argument="http://127.0.0.1:5173 ready"))
        self.assertEqual(parse_local_command("/http"), LocalCommand(type="http"))
        self.assertEqual(parse_local_command("/http-fetch http://127.0.0.1:5173/app"), LocalCommand(type="http_fetch", argument="http://127.0.0.1:5173/app"))
        self.assertEqual(parse_local_command("/http-fetch"), LocalCommand(type="http_fetch"))
        self.assertEqual(parse_local_command("/overview"), LocalCommand(type="overview"))
        self.assertEqual(parse_local_command("/overview --max-files 7"), LocalCommand(type="overview", argument="--max-files 7"))
        self.assertEqual(parse_local_command("/repo-map"), LocalCommand(type="repo_map"))
        self.assertEqual(parse_local_command("/repo-map src"), LocalCommand(type="repo_map", argument="src"))
        self.assertEqual(parse_local_command("/search needle"), LocalCommand(type="search", argument="needle"))
        self.assertEqual(parse_local_command("/search"), LocalCommand(type="search"))
        self.assertEqual(parse_local_command("/search-contexts needle"), LocalCommand(type="search_contexts", argument="needle"))
        self.assertEqual(parse_local_command("/search-contexts"), LocalCommand(type="search_contexts"))
        self.assertEqual(parse_local_command("/glob **/*.py"), LocalCommand(type="glob", argument="**/*.py"))
        self.assertEqual(parse_local_command("/glob"), LocalCommand(type="glob"))
        self.assertEqual(parse_local_command("/tree src"), LocalCommand(type="tree", argument="src"))
        self.assertEqual(parse_local_command("/tree"), LocalCommand(type="tree"))
        self.assertEqual(parse_local_command("/symbols src/app.py web/app.ts"), LocalCommand(type="symbols", argument="src/app.py web/app.ts"))
        self.assertEqual(parse_local_command("/symbols"), LocalCommand(type="symbols"))
        self.assertEqual(parse_local_command("/file-info src/app.py asset.bin"), LocalCommand(type="file_info", argument="src/app.py asset.bin"))
        self.assertEqual(parse_local_command("/file-info"), LocalCommand(type="file_info"))
        self.assertEqual(parse_local_command("/image-info assets/logo.png"), LocalCommand(type="image_info", argument="assets/logo.png"))
        self.assertEqual(parse_local_command("/image-info"), LocalCommand(type="image_info"))
        self.assertEqual(parse_local_command("/read src/app.py 2:4"), LocalCommand(type="read", argument="src/app.py 2:4"))
        self.assertEqual(parse_local_command("/read"), LocalCommand(type="read"))
        self.assertEqual(parse_local_command("/around src/app.py 42 8"), LocalCommand(type="around", argument="src/app.py 42 8"))
        self.assertEqual(parse_local_command("/around"), LocalCommand(type="around"))
        self.assertEqual(parse_local_command("/around-many src/app.py:42:8 tests/test_app.py:17"), LocalCommand(type="around_many", argument="src/app.py:42:8 tests/test_app.py:17"))
        self.assertEqual(parse_local_command("/around-many"), LocalCommand(type="around_many"))
        self.assertEqual(parse_local_command("/output-contexts src/app.py:42:8"), LocalCommand(type="output_contexts", argument="src/app.py:42:8"))
        self.assertEqual(parse_local_command("/output-contexts"), LocalCommand(type="output_contexts"))
        self.assertEqual(parse_local_command("/output-diagnostics src/app.py:42:8 error"), LocalCommand(type="output_diagnostics", argument="src/app.py:42:8 error"))
        self.assertEqual(parse_local_command("/output-diagnostics"), LocalCommand(type="output_diagnostics"))
        self.assertEqual(parse_local_command("/python-traceback Traceback"), LocalCommand(type="python_traceback", argument="Traceback"))
        self.assertEqual(parse_local_command("/python-traceback"), LocalCommand(type="python_traceback"))
        self.assertEqual(parse_local_command("/tail logs/app.log 40"), LocalCommand(type="tail", argument="logs/app.log 40"))
        self.assertEqual(parse_local_command("/tail"), LocalCommand(type="tail"))
        self.assertEqual(parse_local_command("/read-files src/app.py tests/test_app.py"), LocalCommand(type="read_files", argument="src/app.py tests/test_app.py"))
        self.assertEqual(parse_local_command("/read-files"), LocalCommand(type="read_files"))
        self.assertEqual(parse_local_command("/read-ranges src/app.py:2:4 tests/test_app.py:1"), LocalCommand(type="read_ranges", argument="src/app.py:2:4 tests/test_app.py:1"))
        self.assertEqual(parse_local_command("/read-ranges"), LocalCommand(type="read_ranges"))
        self.assertEqual(parse_local_command("/python-check src"), LocalCommand(type="python_check", argument="src"))
        self.assertEqual(parse_local_command("/python-check"), LocalCommand(type="python_check"))
        self.assertEqual(parse_local_command("/python-deps src"), LocalCommand(type="python_deps", argument="src"))
        self.assertEqual(parse_local_command("/python-deps"), LocalCommand(type="python_deps"))
        self.assertEqual(parse_local_command("/python-defs Runner.run src"), LocalCommand(type="python_defs", argument="Runner.run src"))
        self.assertEqual(parse_local_command("/python-defs"), LocalCommand(type="python_defs"))
        self.assertEqual(parse_local_command("/python-refs run_agent src"), LocalCommand(type="python_refs", argument="run_agent src"))
        self.assertEqual(parse_local_command("/python-refs"), LocalCommand(type="python_refs"))
        self.assertEqual(parse_local_command("/python-ref-contexts run_agent src"), LocalCommand(type="python_ref_contexts", argument="run_agent src"))
        self.assertEqual(parse_local_command("/python-ref-contexts"), LocalCommand(type="python_ref_contexts"))
        self.assertEqual(parse_local_command("/python-calls helper src"), LocalCommand(type="python_calls", argument="helper src"))
        self.assertEqual(parse_local_command("/python-calls"), LocalCommand(type="python_calls"))
        self.assertEqual(parse_local_command("/python-call-graph src"), LocalCommand(type="python_call_graph", argument="src"))
        self.assertEqual(parse_local_command("/python-call-graph"), LocalCommand(type="python_call_graph"))
        self.assertEqual(parse_local_command("/python-rename-preview run_agent execute_agent src"), LocalCommand(type="python_rename_preview", argument="run_agent execute_agent src"))
        self.assertEqual(parse_local_command("/python-rename-preview"), LocalCommand(type="python_rename_preview"))
        self.assertEqual(parse_local_command("/python-rename run_agent execute_agent src"), LocalCommand(type="python_rename", argument="run_agent execute_agent src"))
        self.assertEqual(parse_local_command("/python-rename"), LocalCommand(type="python_rename"))
        self.assertEqual(parse_local_command("/check-replace-python-def Runner.run '    def run(self):\\n        return 2\\n' src/app.py"), LocalCommand(type="check_replace_python_definition", argument="Runner.run '    def run(self):\\n        return 2\\n' src/app.py"))
        self.assertEqual(parse_local_command("/check-replace-python-def"), LocalCommand(type="check_replace_python_definition"))
        self.assertEqual(parse_local_command("/replace-python-def Runner.run '    def run(self):\\n        return 2\\n' src/app.py"), LocalCommand(type="replace_python_definition", argument="Runner.run '    def run(self):\\n        return 2\\n' src/app.py"))
        self.assertEqual(parse_local_command("/replace-python-def"), LocalCommand(type="replace_python_definition"))
        self.assertEqual(parse_local_command("/config-check pyproject.toml"), LocalCommand(type="config_check", argument="pyproject.toml"))
        self.assertEqual(parse_local_command("/config-check"), LocalCommand(type="config_check"))
        self.assertEqual(parse_local_command("/check-json-set --create-missing package.json /scripts/test '\"npm test\"'"), LocalCommand(type="check_json_set", argument="--create-missing package.json /scripts/test '\"npm test\"'"))
        self.assertEqual(parse_local_command("/check-json-set"), LocalCommand(type="check_json_set"))
        self.assertEqual(parse_local_command("/json-set package.json /private true"), LocalCommand(type="json_set", argument="package.json /private true"))
        self.assertEqual(parse_local_command("/json-set"), LocalCommand(type="json_set"))
        self.assertEqual(parse_local_command("/check-json-remove package.json /scripts/dev"), LocalCommand(type="check_json_remove", argument="package.json /scripts/dev"))
        self.assertEqual(parse_local_command("/check-json-remove"), LocalCommand(type="check_json_remove"))
        self.assertEqual(parse_local_command("/json-remove package.json /keywords/0"), LocalCommand(type="json_remove", argument="package.json /keywords/0"))
        self.assertEqual(parse_local_command("/json-remove"), LocalCommand(type="json_remove"))
        self.assertEqual(parse_local_command("/check-json-patch package.json '[{\"op\":\"replace\",\"path\":\"/private\",\"value\":true}]'"), LocalCommand(type="check_json_patch", argument="package.json '[{\"op\":\"replace\",\"path\":\"/private\",\"value\":true}]'"))
        self.assertEqual(parse_local_command("/check-json-patch"), LocalCommand(type="check_json_patch"))
        self.assertEqual(parse_local_command("/json-patch package.json '[{\"op\":\"remove\",\"path\":\"/keywords/0\"}]'"), LocalCommand(type="json_patch", argument="package.json '[{\"op\":\"remove\",\"path\":\"/keywords/0\"}]'"))
        self.assertEqual(parse_local_command("/json-patch"), LocalCommand(type="json_patch"))
        self.assertEqual(parse_local_command("/check-replace-lines app.py 2 3 'new\\n'"), LocalCommand(type="check_replace_lines", argument="app.py 2 3 'new\\n'"))
        self.assertEqual(parse_local_command("/check-replace-lines"), LocalCommand(type="check_replace_lines"))
        self.assertEqual(parse_local_command("/replace-lines app.py 2 2 'new\\n'"), LocalCommand(type="replace_lines", argument="app.py 2 2 'new\\n'"))
        self.assertEqual(parse_local_command("/replace-lines"), LocalCommand(type="replace_lines"))
        self.assertEqual(parse_local_command("/check-insert-lines app.py 2 'new\\n'"), LocalCommand(type="check_insert_lines", argument="app.py 2 'new\\n'"))
        self.assertEqual(parse_local_command("/check-insert-lines"), LocalCommand(type="check_insert_lines"))
        self.assertEqual(parse_local_command("/insert-lines app.py 2 'new\\n'"), LocalCommand(type="insert_lines", argument="app.py 2 'new\\n'"))
        self.assertEqual(parse_local_command("/insert-lines"), LocalCommand(type="insert_lines"))
        self.assertEqual(parse_local_command("/check-append app.py 'new\\n'"), LocalCommand(type="check_append_file", argument="app.py 'new\\n'"))
        self.assertEqual(parse_local_command("/check-append"), LocalCommand(type="check_append_file"))
        self.assertEqual(parse_local_command("/append app.py 'new\\n'"), LocalCommand(type="append_file", argument="app.py 'new\\n'"))
        self.assertEqual(parse_local_command("/append"), LocalCommand(type="append_file"))
        self.assertEqual(parse_local_command("/check-write app.py 'new\\n'"), LocalCommand(type="check_write_file", argument="app.py 'new\\n'"))
        self.assertEqual(parse_local_command("/check-write"), LocalCommand(type="check_write_file"))
        self.assertEqual(parse_local_command("/write app.py 'new\\n'"), LocalCommand(type="write_file", argument="app.py 'new\\n'"))
        self.assertEqual(parse_local_command("/write"), LocalCommand(type="write_file"))
        self.assertEqual(parse_local_command("/check-write-files app.py 'a\\n' test.py 'b\\n'"), LocalCommand(type="check_write_files", argument="app.py 'a\\n' test.py 'b\\n'"))
        self.assertEqual(parse_local_command("/check-write-files"), LocalCommand(type="check_write_files"))
        self.assertEqual(parse_local_command("/write-files app.py 'a\\n' test.py 'b\\n'"), LocalCommand(type="write_files", argument="app.py 'a\\n' test.py 'b\\n'"))
        self.assertEqual(parse_local_command("/write-files"), LocalCommand(type="write_files"))
        self.assertEqual(parse_local_command("/check-edit app.py old new"), LocalCommand(type="check_edit_file", argument="app.py old new"))
        self.assertEqual(parse_local_command("/check-edit"), LocalCommand(type="check_edit_file"))
        self.assertEqual(parse_local_command("/edit app.py old new"), LocalCommand(type="edit_file", argument="app.py old new"))
        self.assertEqual(parse_local_command("/edit"), LocalCommand(type="edit_file"))
        self.assertEqual(parse_local_command("/check-multi-edit app.py old new print log"), LocalCommand(type="check_multi_edit_file", argument="app.py old new print log"))
        self.assertEqual(parse_local_command("/check-multi-edit"), LocalCommand(type="check_multi_edit_file"))
        self.assertEqual(parse_local_command("/multi-edit app.py old new print log"), LocalCommand(type="multi_edit_file", argument="app.py old new print log"))
        self.assertEqual(parse_local_command("/multi-edit"), LocalCommand(type="multi_edit_file"))
        self.assertEqual(parse_local_command("/check-delete old.py"), LocalCommand(type="check_delete_file", argument="old.py"))
        self.assertEqual(parse_local_command("/check-delete"), LocalCommand(type="check_delete_file"))
        self.assertEqual(parse_local_command("/delete old.py"), LocalCommand(type="delete_file", argument="old.py"))
        self.assertEqual(parse_local_command("/delete"), LocalCommand(type="delete_file"))
        self.assertEqual(parse_local_command("/check-delete-files old.py other.py"), LocalCommand(type="check_delete_files", argument="old.py other.py"))
        self.assertEqual(parse_local_command("/check-delete-files"), LocalCommand(type="check_delete_files"))
        self.assertEqual(parse_local_command("/delete-files old.py other.py"), LocalCommand(type="delete_files", argument="old.py other.py"))
        self.assertEqual(parse_local_command("/delete-files"), LocalCommand(type="delete_files"))
        self.assertEqual(parse_local_command("/check-move old.py new.py"), LocalCommand(type="check_move_file", argument="old.py new.py"))
        self.assertEqual(parse_local_command("/check-move"), LocalCommand(type="check_move_file"))
        self.assertEqual(parse_local_command("/move old.py new.py"), LocalCommand(type="move_file", argument="old.py new.py"))
        self.assertEqual(parse_local_command("/move"), LocalCommand(type="move_file"))
        self.assertEqual(parse_local_command("/check-move-files old.py new.py other.py other-new.py"), LocalCommand(type="check_move_files", argument="old.py new.py other.py other-new.py"))
        self.assertEqual(parse_local_command("/check-move-files"), LocalCommand(type="check_move_files"))
        self.assertEqual(parse_local_command("/move-files old.py new.py other.py other-new.py"), LocalCommand(type="move_files", argument="old.py new.py other.py other-new.py"))
        self.assertEqual(parse_local_command("/move-files"), LocalCommand(type="move_files"))
        self.assertEqual(parse_local_command("/check-copy template.py new.py"), LocalCommand(type="check_copy_file", argument="template.py new.py"))
        self.assertEqual(parse_local_command("/check-copy"), LocalCommand(type="check_copy_file"))
        self.assertEqual(parse_local_command("/copy template.py new.py"), LocalCommand(type="copy_file", argument="template.py new.py"))
        self.assertEqual(parse_local_command("/copy"), LocalCommand(type="copy_file"))
        self.assertEqual(parse_local_command("/check-copy-files template.py new.py config.py config-copy.py"), LocalCommand(type="check_copy_files", argument="template.py new.py config.py config-copy.py"))
        self.assertEqual(parse_local_command("/check-copy-files"), LocalCommand(type="check_copy_files"))
        self.assertEqual(parse_local_command("/copy-files template.py new.py config.py config-copy.py"), LocalCommand(type="copy_files", argument="template.py new.py config.py config-copy.py"))
        self.assertEqual(parse_local_command("/copy-files"), LocalCommand(type="copy_files"))
        self.assertEqual(parse_local_command("/check-move-dir old_pkg new_pkg"), LocalCommand(type="check_move_dir", argument="old_pkg new_pkg"))
        self.assertEqual(parse_local_command("/check-move-dir"), LocalCommand(type="check_move_dir"))
        self.assertEqual(parse_local_command("/move-dir old_pkg new_pkg"), LocalCommand(type="move_dir", argument="old_pkg new_pkg"))
        self.assertEqual(parse_local_command("/move-dir"), LocalCommand(type="move_dir"))
        self.assertEqual(parse_local_command("/check-move-dirs old_a new_a old_b new_b"), LocalCommand(type="check_move_dirs", argument="old_a new_a old_b new_b"))
        self.assertEqual(parse_local_command("/check-move-dirs"), LocalCommand(type="check_move_dirs"))
        self.assertEqual(parse_local_command("/move-dirs old_a new_a old_b new_b"), LocalCommand(type="move_dirs", argument="old_a new_a old_b new_b"))
        self.assertEqual(parse_local_command("/move-dirs"), LocalCommand(type="move_dirs"))
        self.assertEqual(parse_local_command("/check-copy-dir template_pkg copy_pkg"), LocalCommand(type="check_copy_dir", argument="template_pkg copy_pkg"))
        self.assertEqual(parse_local_command("/check-copy-dir"), LocalCommand(type="check_copy_dir"))
        self.assertEqual(parse_local_command("/copy-dir template_pkg copy_pkg"), LocalCommand(type="copy_dir", argument="template_pkg copy_pkg"))
        self.assertEqual(parse_local_command("/copy-dir"), LocalCommand(type="copy_dir"))
        self.assertEqual(parse_local_command("/check-copy-dirs template_a copy_a template_b copy_b"), LocalCommand(type="check_copy_dirs", argument="template_a copy_a template_b copy_b"))
        self.assertEqual(parse_local_command("/check-copy-dirs"), LocalCommand(type="check_copy_dirs"))
        self.assertEqual(parse_local_command("/copy-dirs template_a copy_a template_b copy_b"), LocalCommand(type="copy_dirs", argument="template_a copy_a template_b copy_b"))
        self.assertEqual(parse_local_command("/copy-dirs"), LocalCommand(type="copy_dirs"))
        self.assertEqual(parse_local_command("/check-mkdir pkg/generated"), LocalCommand(type="check_create_dir", argument="pkg/generated"))
        self.assertEqual(parse_local_command("/check-mkdir"), LocalCommand(type="check_create_dir"))
        self.assertEqual(parse_local_command("/mkdir pkg/generated"), LocalCommand(type="create_dir", argument="pkg/generated"))
        self.assertEqual(parse_local_command("/mkdir"), LocalCommand(type="create_dir"))
        self.assertEqual(parse_local_command("/check-mkdirs pkg/generated assets/icons"), LocalCommand(type="check_create_dirs", argument="pkg/generated assets/icons"))
        self.assertEqual(parse_local_command("/check-mkdirs"), LocalCommand(type="check_create_dirs"))
        self.assertEqual(parse_local_command("/mkdirs pkg/generated assets/icons"), LocalCommand(type="create_dirs", argument="pkg/generated assets/icons"))
        self.assertEqual(parse_local_command("/mkdirs"), LocalCommand(type="create_dirs"))
        self.assertEqual(parse_local_command("/check-rmdir pkg/generated"), LocalCommand(type="check_delete_empty_dir", argument="pkg/generated"))
        self.assertEqual(parse_local_command("/check-rmdir"), LocalCommand(type="check_delete_empty_dir"))
        self.assertEqual(parse_local_command("/rmdir pkg/generated"), LocalCommand(type="delete_empty_dir", argument="pkg/generated"))
        self.assertEqual(parse_local_command("/rmdir"), LocalCommand(type="delete_empty_dir"))
        self.assertEqual(parse_local_command("/check-rmdirs pkg/generated assets/icons"), LocalCommand(type="check_delete_empty_dirs", argument="pkg/generated assets/icons"))
        self.assertEqual(parse_local_command("/check-rmdirs"), LocalCommand(type="check_delete_empty_dirs"))
        self.assertEqual(parse_local_command("/rmdirs pkg/generated assets/icons"), LocalCommand(type="delete_empty_dirs", argument="pkg/generated assets/icons"))
        self.assertEqual(parse_local_command("/rmdirs"), LocalCommand(type="delete_empty_dirs"))
        self.assertEqual(parse_local_command("/check-executable scripts/tool.sh false"), LocalCommand(type="check_set_executable", argument="scripts/tool.sh false"))
        self.assertEqual(parse_local_command("/check-executable"), LocalCommand(type="check_set_executable"))
        self.assertEqual(parse_local_command("/set-executable scripts/tool.sh true"), LocalCommand(type="set_executable", argument="scripts/tool.sh true"))
        self.assertEqual(parse_local_command("/set-executable"), LocalCommand(type="set_executable"))
        self.assertEqual(parse_local_command("/check-patch app.py '@@ -1 +1 @@\\n-old\\n+new\\n'"), LocalCommand(type="check_patch", argument="app.py '@@ -1 +1 @@\\n-old\\n+new\\n'"))
        self.assertEqual(parse_local_command("/check-patch"), LocalCommand(type="check_patch"))
        self.assertEqual(parse_local_command("/patch app.py '@@ -1 +1 @@\\n-old\\n+new\\n'"), LocalCommand(type="patch_file", argument="app.py '@@ -1 +1 @@\\n-old\\n+new\\n'"))
        self.assertEqual(parse_local_command("/patch"), LocalCommand(type="patch_file"))
        self.assertEqual(parse_local_command("/check-patches '--- a/app.py\\n+++ b/app.py\\n@@ -1 +1 @@\\n-old\\n+new\\n'"), LocalCommand(type="check_patches", argument="'--- a/app.py\\n+++ b/app.py\\n@@ -1 +1 @@\\n-old\\n+new\\n'"))
        self.assertEqual(parse_local_command("/check-patches"), LocalCommand(type="check_patches"))
        self.assertEqual(parse_local_command("/patches '--- a/app.py\\n+++ b/app.py\\n@@ -1 +1 @@\\n-old\\n+new\\n'"), LocalCommand(type="patch_files", argument="'--- a/app.py\\n+++ b/app.py\\n@@ -1 +1 @@\\n-old\\n+new\\n'"))
        self.assertEqual(parse_local_command("/patches"), LocalCommand(type="patch_files"))
        self.assertEqual(parse_local_command("/check-regex-replace --ignore-case app.py old 'new\\n'"), LocalCommand(type="check_regex_replace", argument="--ignore-case app.py old 'new\\n'"))
        self.assertEqual(parse_local_command("/check-regex-replace"), LocalCommand(type="check_regex_replace"))
        self.assertEqual(parse_local_command("/regex-replace --count 1 app.py old new"), LocalCommand(type="regex_replace", argument="--count 1 app.py old new"))
        self.assertEqual(parse_local_command("/regex-replace"), LocalCommand(type="regex_replace"))
        self.assertEqual(parse_local_command("/code-deps web"), LocalCommand(type="code_deps", argument="web"))
        self.assertEqual(parse_local_command("/code-deps"), LocalCommand(type="code_deps"))
        self.assertEqual(parse_local_command("/code-refs runAgent web"), LocalCommand(type="code_refs", argument="runAgent web"))
        self.assertEqual(parse_local_command("/code-refs"), LocalCommand(type="code_refs"))
        self.assertEqual(parse_local_command("/code-ref-contexts runAgent web"), LocalCommand(type="code_ref_contexts", argument="runAgent web"))
        self.assertEqual(parse_local_command("/code-ref-contexts"), LocalCommand(type="code_ref_contexts"))
        self.assertEqual(parse_local_command("/code-defs runAgent web"), LocalCommand(type="code_defs", argument="runAgent web"))
        self.assertEqual(parse_local_command("/code-defs"), LocalCommand(type="code_defs"))
        self.assertEqual(parse_local_command("/code-rename-preview runAgent executeAgent web"), LocalCommand(type="code_rename_preview", argument="runAgent executeAgent web"))
        self.assertEqual(parse_local_command("/code-rename-preview"), LocalCommand(type="code_rename_preview"))
        self.assertEqual(parse_local_command("/code-rename runAgent executeAgent web"), LocalCommand(type="code_rename", argument="runAgent executeAgent web"))
        self.assertEqual(parse_local_command("/code-rename"), LocalCommand(type="code_rename"))
        self.assertEqual(parse_local_command("/git-status"), LocalCommand(type="git_status"))
        self.assertEqual(parse_local_command("/conflicts src"), LocalCommand(type="git_conflicts", argument="src"))
        self.assertEqual(parse_local_command("/git-info"), LocalCommand(type="git_info"))
        self.assertEqual(parse_local_command("/branches"), LocalCommand(type="branches"))
        self.assertEqual(parse_local_command("/log"), LocalCommand(type="log"))
        self.assertEqual(parse_local_command("/log app.py 2"), LocalCommand(type="log", argument="app.py 2"))
        self.assertEqual(parse_local_command("/show"), LocalCommand(type="show"))
        self.assertEqual(parse_local_command("/show HEAD app.py"), LocalCommand(type="show", argument="HEAD app.py"))
        self.assertEqual(parse_local_command("/blame app.py 2:2"), LocalCommand(type="blame", argument="app.py 2:2"))
        self.assertEqual(parse_local_command("/blame"), LocalCommand(type="blame"))
        self.assertEqual(parse_local_command("/stashes"), LocalCommand(type="stashes"))
        self.assertEqual(parse_local_command("/stashes 5"), LocalCommand(type="stashes", argument="5"))
        self.assertEqual(parse_local_command("/check-fetch origin"), LocalCommand(type="check_fetch", argument="origin"))
        self.assertEqual(parse_local_command("/check-fetch"), LocalCommand(type="check_fetch"))
        self.assertEqual(parse_local_command("/fetch origin"), LocalCommand(type="fetch", argument="origin"))
        self.assertEqual(parse_local_command("/fetch"), LocalCommand(type="fetch"))
        self.assertEqual(parse_local_command("/check-pull"), LocalCommand(type="check_pull"))
        self.assertEqual(parse_local_command("/pull"), LocalCommand(type="pull"))
        self.assertEqual(parse_local_command("/check-push"), LocalCommand(type="check_push"))
        self.assertEqual(parse_local_command("/push"), LocalCommand(type="push"))
        self.assertEqual(parse_local_command("/check-stash --include-untracked save work"), LocalCommand(type="check_stash", argument="--include-untracked save work"))
        self.assertEqual(parse_local_command("/check-stash"), LocalCommand(type="check_stash"))
        self.assertEqual(parse_local_command("/stash save work"), LocalCommand(type="stash", argument="save work"))
        self.assertEqual(parse_local_command("/stash"), LocalCommand(type="stash"))
        self.assertEqual(parse_local_command("/check-stash-apply stash@{0}"), LocalCommand(type="check_stash_apply", argument="stash@{0}"))
        self.assertEqual(parse_local_command("/check-stash-apply"), LocalCommand(type="check_stash_apply"))
        self.assertEqual(parse_local_command("/stash-apply stash@{0}"), LocalCommand(type="stash_apply", argument="stash@{0}"))
        self.assertEqual(parse_local_command("/stash-apply"), LocalCommand(type="stash_apply"))
        self.assertEqual(parse_local_command("/check-stash-drop stash@{0}"), LocalCommand(type="check_stash_drop", argument="stash@{0}"))
        self.assertEqual(parse_local_command("/check-stash-drop"), LocalCommand(type="check_stash_drop"))
        self.assertEqual(parse_local_command("/stash-drop stash@{0}"), LocalCommand(type="stash_drop", argument="stash@{0}"))
        self.assertEqual(parse_local_command("/stash-drop"), LocalCommand(type="stash_drop"))
        self.assertEqual(parse_local_command("/check-stage app.py tests/test_app.py"), LocalCommand(type="check_stage", argument="app.py tests/test_app.py"))
        self.assertEqual(parse_local_command("/check-stage"), LocalCommand(type="check_stage"))
        self.assertEqual(parse_local_command("/stage app.py"), LocalCommand(type="stage", argument="app.py"))
        self.assertEqual(parse_local_command("/stage"), LocalCommand(type="stage"))
        self.assertEqual(parse_local_command("/check-unstage app.py tests/test_app.py"), LocalCommand(type="check_unstage", argument="app.py tests/test_app.py"))
        self.assertEqual(parse_local_command("/check-unstage"), LocalCommand(type="check_unstage"))
        self.assertEqual(parse_local_command("/unstage app.py"), LocalCommand(type="unstage", argument="app.py"))
        self.assertEqual(parse_local_command("/unstage"), LocalCommand(type="unstage"))
        self.assertEqual(parse_local_command("/check-commit update app"), LocalCommand(type="check_commit", argument="update app"))
        self.assertEqual(parse_local_command("/check-commit"), LocalCommand(type="check_commit"))
        self.assertEqual(parse_local_command("/commit update app"), LocalCommand(type="commit", argument="update app"))
        self.assertEqual(parse_local_command("/commit"), LocalCommand(type="commit"))
        self.assertEqual(parse_local_command("/check-restore app.py tests/test_app.py"), LocalCommand(type="check_restore", argument="app.py tests/test_app.py"))
        self.assertEqual(parse_local_command("/check-restore"), LocalCommand(type="check_restore"))
        self.assertEqual(parse_local_command("/restore app.py"), LocalCommand(type="restore", argument="app.py"))
        self.assertEqual(parse_local_command("/restore"), LocalCommand(type="restore"))
        self.assertEqual(parse_local_command("/check-switch --create feature/demo"), LocalCommand(type="check_switch", argument="--create feature/demo"))
        self.assertEqual(parse_local_command("/check-switch"), LocalCommand(type="check_switch"))
        self.assertEqual(parse_local_command("/switch feature/demo"), LocalCommand(type="switch", argument="feature/demo"))
        self.assertEqual(parse_local_command("/switch"), LocalCommand(type="switch"))
        self.assertEqual(parse_local_command("/env"), LocalCommand(type="env"))
        self.assertEqual(parse_local_command("/processes"), LocalCommand(type="processes"))
        self.assertEqual(parse_local_command("/process bg-1"), LocalCommand(type="process", argument="bg-1"))
        self.assertEqual(parse_local_command("/process bg-1 2000"), LocalCommand(type="process", argument="bg-1 2000"))
        self.assertEqual(parse_local_command("/process"), LocalCommand(type="process"))
        self.assertEqual(parse_local_command("/process-output-contexts bg-1"), LocalCommand(type="process_output_contexts", argument="bg-1"))
        self.assertEqual(parse_local_command("/process-output-contexts bg-1 2000"), LocalCommand(type="process_output_contexts", argument="bg-1 2000"))
        self.assertEqual(parse_local_command("/process-output-contexts"), LocalCommand(type="process_output_contexts"))
        self.assertEqual(parse_local_command("/process-output-diagnostics bg-1"), LocalCommand(type="process_output_diagnostics", argument="bg-1"))
        self.assertEqual(parse_local_command("/process-output-diagnostics bg-1 2000"), LocalCommand(type="process_output_diagnostics", argument="bg-1 2000"))
        self.assertEqual(parse_local_command("/process-output-diagnostics"), LocalCommand(type="process_output_diagnostics"))
        self.assertEqual(parse_local_command("/wait-process bg-1"), LocalCommand(type="wait_process", argument="bg-1"))
        self.assertEqual(parse_local_command("/wait-process bg-1 5000 2000"), LocalCommand(type="wait_process", argument="bg-1 5000 2000"))
        self.assertEqual(parse_local_command("/wait-process"), LocalCommand(type="wait_process"))
        self.assertEqual(parse_local_command("/check-write-process bg-1 hello\\n"), LocalCommand(type="check_write_process", argument="bg-1 hello\\n"))
        self.assertEqual(parse_local_command("/check-write-process"), LocalCommand(type="check_write_process"))
        self.assertEqual(parse_local_command("/write-process bg-1 hello\\n"), LocalCommand(type="write_process", argument="bg-1 hello\\n"))
        self.assertEqual(parse_local_command("/write-process"), LocalCommand(type="write_process"))
        self.assertEqual(parse_local_command("/check-stop-process bg-1"), LocalCommand(type="check_stop_process", argument="bg-1"))
        self.assertEqual(parse_local_command("/check-stop-process"), LocalCommand(type="check_stop_process"))
        self.assertEqual(parse_local_command("/stop-process bg-1"), LocalCommand(type="stop_process", argument="bg-1"))
        self.assertEqual(parse_local_command("/stop-process"), LocalCommand(type="stop_process"))
        self.assertEqual(parse_local_command("/check-stop-processes"), LocalCommand(type="check_stop_all_processes"))
        self.assertEqual(parse_local_command("/check-stop-all-processes"), LocalCommand(type="check_stop_all_processes"))
        self.assertEqual(parse_local_command("/stop-processes"), LocalCommand(type="stop_all_processes"))
        self.assertEqual(parse_local_command("/stop-all-processes"), LocalCommand(type="stop_all_processes"))
        self.assertEqual(parse_local_command("/status"), LocalCommand(type="status"))
        self.assertEqual(parse_local_command("/context"), LocalCommand(type="context"))
        self.assertEqual(parse_local_command("/init"), LocalCommand(type="init"))
        self.assertEqual(parse_local_command("/init CLAUDE.md"), LocalCommand(type="init", argument="CLAUDE.md"))
        self.assertEqual(parse_local_command("/doctor"), LocalCommand(type="doctor"))
        self.assertEqual(parse_local_command("/review"), LocalCommand(type="review"))
        self.assertEqual(parse_local_command("/review --max-files 1 --max-checks 2"), LocalCommand(type="review", argument="--max-files 1 --max-checks 2"))
        self.assertEqual(parse_local_command("/handoff"), LocalCommand(type="handoff"))
        self.assertEqual(parse_local_command("/handoff --max-files 1 --max-checks 2"), LocalCommand(type="handoff", argument="--max-files 1 --max-checks 2"))
        self.assertEqual(parse_local_command("/changes"), LocalCommand(type="changes"))
        self.assertEqual(parse_local_command("/changes --max-files 1"), LocalCommand(type="changes", argument="--max-files 1"))
        self.assertEqual(parse_local_command("/diff"), LocalCommand(type="diff"))
        self.assertEqual(parse_local_command("/diff --staged app.py"), LocalCommand(type="diff", argument="--staged app.py"))
        self.assertEqual(parse_local_command("/diff-hunks"), LocalCommand(type="diff_hunks"))
        self.assertEqual(parse_local_command("/diff-hunks --staged app.py"), LocalCommand(type="diff_hunks", argument="--staged app.py"))
        self.assertEqual(parse_local_command("/diff-contexts --staged app.py"), LocalCommand(type="diff_contexts", argument="--staged app.py"))
        self.assertEqual(parse_local_command("/clear"), LocalCommand(type="clear"))
        self.assertEqual(parse_local_command("/usage"), LocalCommand(type="usage"))
        self.assertEqual(parse_local_command("/cost"), LocalCommand(type="cost"))
        self.assertEqual(parse_local_command("/approval"), LocalCommand(type="approval"))
        self.assertEqual(parse_local_command("/approval allow"), LocalCommand(type="approval", argument="allow"))
        self.assertEqual(parse_local_command("/sessions"), LocalCommand(type="sessions"))
        self.assertEqual(parse_local_command("/last"), LocalCommand(type="last"))
        self.assertEqual(parse_local_command("/plan"), LocalCommand(type="plan"))
        self.assertEqual(parse_local_command("/plan run-1"), LocalCommand(type="plan", argument="run-1"))
        self.assertEqual(parse_local_command("/transcript"), LocalCommand(type="transcript"))
        self.assertEqual(parse_local_command("/transcript run-1"), LocalCommand(type="transcript", argument="run-1"))
        self.assertEqual(parse_local_command("/session-search missing config"), LocalCommand(type="session_search", argument="missing config"))
        self.assertEqual(parse_local_command("/session-search --run run-1 missing config"), LocalCommand(type="session_search", argument="--run run-1 missing config"))
        self.assertEqual(parse_local_command("/session-commands"), LocalCommand(type="session_commands"))
        self.assertEqual(parse_local_command("/session-commands run-1"), LocalCommand(type="session_commands", argument="run-1"))
        self.assertEqual(parse_local_command("/session-output-contexts"), LocalCommand(type="session_output_contexts"))
        self.assertEqual(parse_local_command("/session-output-contexts run-1"), LocalCommand(type="session_output_contexts", argument="run-1"))
        self.assertEqual(parse_local_command("/session-output-diagnostics"), LocalCommand(type="session_output_diagnostics"))
        self.assertEqual(parse_local_command("/session-output-diagnostics run-1"), LocalCommand(type="session_output_diagnostics", argument="run-1"))
        self.assertEqual(parse_local_command("/session-files"), LocalCommand(type="session_files"))
        self.assertEqual(parse_local_command("/session-files run-1"), LocalCommand(type="session_files", argument="run-1"))
        self.assertEqual(parse_local_command("/session-failures"), LocalCommand(type="session_failures"))
        self.assertEqual(parse_local_command("/session-failures run-1"), LocalCommand(type="session_failures", argument="run-1"))
        self.assertEqual(parse_local_command("/session-verification"), LocalCommand(type="session_verification"))
        self.assertEqual(parse_local_command("/session-verification run-1"), LocalCommand(type="session_verification", argument="run-1"))
        self.assertEqual(parse_local_command("/session-audit"), LocalCommand(type="session_audit"))
        self.assertEqual(parse_local_command("/session-audit run-1"), LocalCommand(type="session_audit", argument="run-1"))
        self.assertEqual(parse_local_command("/session-handoff"), LocalCommand(type="session_handoff"))
        self.assertEqual(parse_local_command("/session-handoff run-1"), LocalCommand(type="session_handoff", argument="run-1"))
        self.assertEqual(parse_local_command("/checkpoint"), LocalCommand(type="checkpoint"))
        self.assertEqual(parse_local_command("/checkpoint before refactor"), LocalCommand(type="checkpoint", argument="before refactor"))
        self.assertEqual(parse_local_command("/checkpoints"), LocalCommand(type="checkpoints"))
        self.assertEqual(parse_local_command("/checkpoint-show ckpt-1"), LocalCommand(type="checkpoint_show", argument="ckpt-1"))
        self.assertEqual(parse_local_command("/checkpoint-diff ckpt-1"), LocalCommand(type="checkpoint_diff", argument="ckpt-1"))
        self.assertEqual(parse_local_command("/checkpoint-status ckpt-1"), LocalCommand(type="checkpoint_status", argument="ckpt-1"))
        self.assertEqual(parse_local_command("/check-checkpoint-restore ckpt-1"), LocalCommand(type="check_checkpoint_restore", argument="ckpt-1"))
        self.assertEqual(parse_local_command("/checkpoint-restore ckpt-1"), LocalCommand(type="checkpoint_restore", argument="ckpt-1"))
        self.assertEqual(parse_local_command("/check-checkpoint-delete ckpt-1"), LocalCommand(type="check_checkpoint_delete", argument="ckpt-1"))
        self.assertEqual(parse_local_command("/checkpoint-delete ckpt-1"), LocalCommand(type="checkpoint_delete", argument="ckpt-1"))
        self.assertEqual(parse_local_command("/check-checkpoint-prune 2"), LocalCommand(type="check_checkpoint_prune", argument="2"))
        self.assertEqual(parse_local_command("/checkpoint-prune 2"), LocalCommand(type="checkpoint_prune", argument="2"))
        self.assertEqual(parse_local_command("/session run-1"), LocalCommand(type="session", argument="run-1"))
        self.assertEqual(parse_local_command("/session"), LocalCommand(type="session"))
        self.assertEqual(parse_local_command("/resume run-1"), LocalCommand(type="resume", argument="run-1"))
        self.assertEqual(parse_local_command("/resume off"), LocalCommand(type="resume", argument="off"))
        self.assertEqual(parse_local_command("/resume"), LocalCommand(type="resume"))
        self.assertEqual(parse_local_command("/compact run-1"), LocalCommand(type="compact", argument="run-1"))
        self.assertEqual(parse_local_command("/compact"), LocalCommand(type="compact"))
        self.assertEqual(parse_local_command("/exit"), LocalCommand(type="exit"))
        self.assertEqual(parse_local_command("/chat"), LocalCommand(type="chat"))
        self.assertEqual(parse_local_command("/chat 你好"), LocalCommand(type="chat", argument="你好"))
        self.assertEqual(parse_local_command("/code"), LocalCommand(type="code"))
        self.assertEqual(parse_local_command("/code write a script"), LocalCommand(type="code", argument="write a script"))
        self.assertIsNone(parse_local_command("write a script"))

    def test_parse_local_command_types_match_local_command_literal(self) -> None:
        source = inspect.getsource(parse_local_command)
        returned_types = set(re.findall(r'LocalCommand\(type="([^"]+)"', source))
        literal_types = set(get_args(get_type_hints(LocalCommand)["type"]))

        self.assertEqual(returned_types - literal_types, set())

    def test_help_text_lists_all_parseable_slash_commands(self) -> None:
        from vibeagent.commands import get_help_text

        source = inspect.getsource(parse_local_command)
        slash_commands = set(re.findall(r'trimmed == "(/[^"]+)"', source))
        help_text = get_help_text()

        missing = sorted(command for command in slash_commands if command not in help_text)

        self.assertEqual(missing, [])

    def test_help_text_lists_approval_command(self) -> None:
        from vibeagent.commands import get_help_text

        self.assertIn("/approval [ask|allow|deny]", get_help_text())
        self.assertIn("/config", get_help_text())
        self.assertIn("/resume [run-id|off] [--max-failures N] [--max-files N] [--max-commands N] [--max-checks N]", get_help_text())
        self.assertIn("previous session handoff", get_help_text())
        self.assertIn("/compact [run-id] [--max-failures N] [--max-files N] [--max-commands N] [--max-checks N]", get_help_text())
        self.assertIn("/plan [run-id]", get_help_text())
        self.assertIn("/transcript [run-id]", get_help_text())
        self.assertIn("/session-verification [run-id] [--max-checks N]", get_help_text())
        self.assertIn("/session-audit [run-id] [--max-failures N] [--max-files N] [--max-commands N] [--max-checks N]", get_help_text())
        self.assertIn("/checkpoint [label]", get_help_text())
        self.assertIn("/checkpoints", get_help_text())
        self.assertIn("/checkpoint-show <id>", get_help_text())
        self.assertIn("/checkpoint-diff <id>", get_help_text())
        self.assertIn("/checkpoint-status <id>", get_help_text())
        self.assertIn("/check-checkpoint-restore <id>", get_help_text())
        self.assertIn("/checkpoint-restore <id>", get_help_text())
        self.assertIn("/check-checkpoint-delete <id>", get_help_text())
        self.assertIn("/checkpoint-delete <id>", get_help_text())
        self.assertIn("/check-checkpoint-prune <keep-last>", get_help_text())
        self.assertIn("/checkpoint-prune <keep-last>", get_help_text())
        self.assertIn("/status", get_help_text())
        self.assertIn("/context", get_help_text())
        self.assertIn("/init [AGENTS.md|CLAUDE.md]", get_help_text())
        self.assertIn("/doctor", get_help_text())
        self.assertIn("/review [--max-files N] [--max-checks N]", get_help_text())
        self.assertIn("/handoff [--max-files N] [--max-checks N] [--max-status-chars N] [--max-plan-chars N]", get_help_text())
        self.assertIn("/changes [--max-files N]", get_help_text())
        self.assertIn("/diff [--staged] [--max-chars N] [path]", get_help_text())
        self.assertIn("/diff-hunks [--staged] [--max-hunks N] [--max-lines N] [path]", get_help_text())
        self.assertIn("/diff-contexts [--staged] [--context-lines N] [--max-hunks N] [--max-bytes N] [path]", get_help_text())
        self.assertIn("/clear", get_help_text())
        self.assertIn("/usage", get_help_text())
        self.assertIn("/cost", get_help_text())
        self.assertIn("/tools", get_help_text())
        self.assertIn("/tool <name>", get_help_text())
        self.assertIn("/permissions", get_help_text())
        self.assertIn("/checks [--max-checks N]", get_help_text())
        self.assertIn("/check-suggested-checks [max|--max-checks N]", get_help_text())
        self.assertIn("/run-suggested-checks [opts] [max|--max-checks N]", get_help_text())
        self.assertIn("/commands", get_help_text())
        self.assertIn("/related-tests [--max-paths N] [--max-candidates N] -- [path...]", get_help_text())
        self.assertIn("/focused-tests [--max-paths N] [--max-candidates N] [--max-commands N] -- [path...]", get_help_text())
        self.assertIn("/check-focused-tests [--max-paths N] [--max-candidates N] [--max-commands N] -- [path...]", get_help_text())
        self.assertIn("/run-focused-tests [opts] [--max-paths N] [--max-candidates N] [--max-commands N] -- [path...]", get_help_text())
        self.assertIn("/manifests", get_help_text())
        self.assertIn("/todos [--max-items N] [--max-files N]", get_help_text())
        self.assertIn("/command [--cwd PATH] -- <cmd>", get_help_text())
        self.assertIn("/run [opts] -- <cmd>", get_help_text())
        self.assertIn("/check-run-seq [--cwd PATH] -- <cmd> ;; <cmd>", get_help_text())
        self.assertIn("/run-seq [opts] -- <cmd> ;; <cmd>", get_help_text())
        self.assertIn("/check-start [--cwd PATH] -- <cmd>", get_help_text())
        self.assertIn("/start [--cwd PATH] -- <cmd>", get_help_text())
        self.assertIn("/port <port> [host] [timeout-ms] [--host HOST]", get_help_text())
        self.assertIn("/http <url> [contains] [--timeout-ms N]", get_help_text())
        self.assertIn("/http-fetch <url> [--timeout-ms N]", get_help_text())
        self.assertIn("/overview [--max-files N]", get_help_text())
        self.assertIn("/repo-map [path] [--max-depth N]", get_help_text())
        self.assertIn("/search [--path PATH]", get_help_text())
        self.assertIn("/search-contexts [--path PATH]", get_help_text())
        self.assertIn("/glob [--max-matches N] -- <pattern>", get_help_text())
        self.assertIn("/tree [path] [--max-depth N]", get_help_text())
        self.assertIn("/symbols [--max-symbols N] -- <path...>", get_help_text())
        self.assertIn("/file-info <path...>", get_help_text())
        self.assertIn("/image-info <path...>", get_help_text())
        self.assertIn("/read [--max-bytes N] -- <path> [start[:end]]", get_help_text())
        self.assertIn("/read-files [--max-bytes N] -- <path...>", get_help_text())
        self.assertIn("/read-ranges [--max-bytes N] -- <path:start[:end]...>", get_help_text())
        self.assertIn("/around [--max-bytes N] -- <path> <line> [context-lines]", get_help_text())
        self.assertIn("/around-many [--max-bytes N] -- <path:line[:context-lines]...>", get_help_text())
        self.assertIn("/output-contexts [--context-lines N] [--max-contexts N] [--max-bytes N] -- <text>", get_help_text())
        self.assertIn("/output-diagnostics [--context-lines N] [--max-diagnostics N] [--max-contexts N] [--max-bytes N] -- <text>", get_help_text())
        self.assertIn("/python-traceback [--context-lines N] [--max-diagnostics N] [--max-contexts N] [--max-bytes N] -- <text>", get_help_text())
        self.assertIn("/tail [--max-bytes N] -- <path> [lines]", get_help_text())
        self.assertIn("/python-check [path]", get_help_text())
        self.assertIn("/python-deps [path]", get_help_text())
        self.assertIn("/python-defs [--path PATH] [--max-matches N]", get_help_text())
        self.assertIn("/python-refs [--path PATH] [--max-matches N]", get_help_text())
        self.assertIn("/python-ref-contexts [--path PATH] [--max-matches N]", get_help_text())
        self.assertIn("/python-calls [--path PATH] [--max-matches N]", get_help_text())
        self.assertIn("/python-call-graph [path]", get_help_text())
        self.assertIn("/python-rename-preview <symbol> <new_name> [path]", get_help_text())
        self.assertIn("/python-rename <symbol> <new_name> [path]", get_help_text())
        self.assertIn("/check-replace-python-def <symbol> <content> [path]", get_help_text())
        self.assertIn("/replace-python-def <symbol> <content> [path]", get_help_text())
        self.assertIn("/config-check [path]", get_help_text())
        self.assertIn("/check-json-set [--create-missing] <path> <pointer> <json-value>", get_help_text())
        self.assertIn("/json-set [--create-missing] <path> <pointer> <json-value>", get_help_text())
        self.assertIn("/check-json-remove <path> <pointer>", get_help_text())
        self.assertIn("/json-remove <path> <pointer>", get_help_text())
        self.assertIn("/check-json-patch <path> <json-ops-array>", get_help_text())
        self.assertIn("/json-patch <path> <json-ops-array>", get_help_text())
        self.assertIn("/check-replace-lines <path> <start> <end> <text>", get_help_text())
        self.assertIn("/replace-lines <path> <start> <end> <text>", get_help_text())
        self.assertIn("/check-insert-lines <path> <line> <text>", get_help_text())
        self.assertIn("/insert-lines <path> <line> <text>", get_help_text())
        self.assertIn("/check-append <path> <text>", get_help_text())
        self.assertIn("/append <path> <text>", get_help_text())
        self.assertIn("/check-write <path> <text>", get_help_text())
        self.assertIn("/write <path> <text>", get_help_text())
        self.assertIn("/check-write-files <path> <text>...", get_help_text())
        self.assertIn("/write-files <path> <text>...", get_help_text())
        self.assertIn("/check-edit <path> <old> <new>", get_help_text())
        self.assertIn("/edit <path> <old> <new>", get_help_text())
        self.assertIn("/check-multi-edit <path> <old> <new>...", get_help_text())
        self.assertIn("/multi-edit <path> <old> <new>...", get_help_text())
        self.assertIn("/check-delete <path>", get_help_text())
        self.assertIn("/delete <path>", get_help_text())
        self.assertIn("/check-delete-files <path...>", get_help_text())
        self.assertIn("/delete-files <path...>", get_help_text())
        self.assertIn("/check-move <source> <destination>", get_help_text())
        self.assertIn("/move <source> <destination>", get_help_text())
        self.assertIn("/check-move-files <source> <destination>...", get_help_text())
        self.assertIn("/move-files <source> <destination>...", get_help_text())
        self.assertIn("/check-copy <source> <destination>", get_help_text())
        self.assertIn("/copy <source> <destination>", get_help_text())
        self.assertIn("/check-copy-files <source> <destination>...", get_help_text())
        self.assertIn("/copy-files <source> <destination>...", get_help_text())
        self.assertIn("/check-move-dir <source> <destination>", get_help_text())
        self.assertIn("/move-dir <source> <destination>", get_help_text())
        self.assertIn("/check-move-dirs <source> <destination>...", get_help_text())
        self.assertIn("/move-dirs <source> <destination>...", get_help_text())
        self.assertIn("/check-copy-dir <source> <destination>", get_help_text())
        self.assertIn("/copy-dir <source> <destination>", get_help_text())
        self.assertIn("/check-copy-dirs <source> <destination>...", get_help_text())
        self.assertIn("/copy-dirs <source> <destination>...", get_help_text())
        self.assertIn("/check-mkdir <path>", get_help_text())
        self.assertIn("/mkdir <path>", get_help_text())
        self.assertIn("/check-mkdirs <path...>", get_help_text())
        self.assertIn("/mkdirs <path...>", get_help_text())
        self.assertIn("/check-rmdir <path>", get_help_text())
        self.assertIn("/rmdir <path>", get_help_text())
        self.assertIn("/check-rmdirs <path...>", get_help_text())
        self.assertIn("/rmdirs <path...>", get_help_text())
        self.assertIn("/check-executable <path> [true|false]", get_help_text())
        self.assertIn("/set-executable <path> [true|false]", get_help_text())
        self.assertIn("/check-patch <path> <patch|->", get_help_text())
        self.assertIn("/patch <path> <patch|->", get_help_text())
        self.assertIn("/check-patches <patch|->", get_help_text())
        self.assertIn("/patches <patch|->", get_help_text())
        self.assertIn("/check-regex-replace [opts] <path> <pattern> <replacement>", get_help_text())
        self.assertIn("/regex-replace [opts] <path> <pattern> <replacement>", get_help_text())
        self.assertIn("/code-deps [path]", get_help_text())
        self.assertIn("/code-refs [--path PATH] [--max-matches N]", get_help_text())
        self.assertIn("/code-ref-contexts [--path PATH] [--max-matches N]", get_help_text())
        self.assertIn("/code-defs [--path PATH] [--max-matches N]", get_help_text())
        self.assertIn("/git-status", get_help_text())
        self.assertIn("/git-info", get_help_text())
        self.assertIn("/branches", get_help_text())
        self.assertIn("/log [path] [count]", get_help_text())
        self.assertIn("/show [rev] [path]", get_help_text())
        self.assertIn("/blame <path> [start[:end]]", get_help_text())
        self.assertIn("/stashes [count]", get_help_text())
        self.assertIn("/check-fetch [remote]", get_help_text())
        self.assertIn("/fetch [remote]", get_help_text())
        self.assertIn("/check-pull", get_help_text())
        self.assertIn("/pull", get_help_text())
        self.assertIn("/check-push", get_help_text())
        self.assertIn("/push", get_help_text())
        self.assertIn("/check-stash [--include-untracked] [message]", get_help_text())
        self.assertIn("/stash [--include-untracked] [message]", get_help_text())
        self.assertIn("/check-stash-apply <stash@{N}>", get_help_text())
        self.assertIn("/stash-apply <stash@{N}>", get_help_text())
        self.assertIn("/check-stash-drop <stash@{N}>", get_help_text())
        self.assertIn("/stash-drop <stash@{N}>", get_help_text())
        self.assertIn("/check-stage <path...>", get_help_text())
        self.assertIn("/stage <path...>", get_help_text())
        self.assertIn("/check-unstage <path...>", get_help_text())
        self.assertIn("/unstage <path...>", get_help_text())
        self.assertIn("/check-commit <message>", get_help_text())
        self.assertIn("/commit <message>", get_help_text())
        self.assertIn("/check-restore <path...>", get_help_text())
        self.assertIn("/restore <path...>", get_help_text())
        self.assertIn("/check-switch [--create] <branch>", get_help_text())
        self.assertIn("/switch [--create] <branch>", get_help_text())
        self.assertIn("/env", get_help_text())
        self.assertIn("/processes", get_help_text())
        self.assertIn("/process <id> [chars]", get_help_text())
        self.assertIn("/wait-process <id> [timeout-ms] [chars] [--timeout-ms N]", get_help_text())
        self.assertIn("/check-write-process <id> <text>", get_help_text())
        self.assertIn("/write-process <id> <text>", get_help_text())
        self.assertIn("/check-stop-process <id>", get_help_text())
        self.assertIn("/stop-process <id>", get_help_text())
        self.assertIn("/check-stop-processes", get_help_text())
        self.assertIn("/stop-processes", get_help_text())
        self.assertIn("/session-output-contexts [run-id]", get_help_text())

    def test_get_tools_text_reports_tool_catalog_from_schema(self) -> None:
        text = get_tools_text()

        self.assertIn("Tools:", text)
        self.assertIn("total:", text)
        self.assertIn("approvalRequired:", text)
        self.assertIn("project:", text)
        self.assertIn("list_files", text)
        self.assertIn("read_file", text)
        self.assertIn("edit:", text)
        self.assertIn("write_file", text)
        self.assertIn("git:", text)
        self.assertIn("git_status", text)
        self.assertIn("command:", text)
        self.assertIn("run_command", text)
        self.assertIn("session:", text)
        self.assertIn("update_plan", text)
        self.assertIn("checkpoint:", text)
        self.assertIn("check_checkpoint_delete", text)
        self.assertIn("checkpoint_delete", text)
        self.assertIn("check_checkpoint_prune", text)
        self.assertIn("checkpoint_prune", text)

    def test_get_tool_text_reports_one_tool_schema(self) -> None:
        text = get_tool_text("read_file")

        self.assertIn("Tool: read_file", text)
        self.assertIn("category: project", text)
        self.assertIn("approvalRequired: no", text)
        self.assertIn("description:", text)
        self.assertIn("input:", text)
        self.assertIn("- path: string", text)
        self.assertIn("- start_line: integer", text)

    def test_get_tool_text_reports_approval_required_and_suggestions(self) -> None:
        write_text = get_tool_text("write_file")
        restore_text = get_tool_text("checkpoint_restore")
        check_delete_text = get_tool_text("check_checkpoint_delete")
        delete_text = get_tool_text("checkpoint_delete")
        check_prune_text = get_tool_text("check_checkpoint_prune")
        prune_text = get_tool_text("checkpoint_prune")
        missing_text = get_tool_text("git_pu")

        self.assertIn("approvalRequired: yes", write_text)
        self.assertIn("Tool: checkpoint_restore", restore_text)
        self.assertIn("category: checkpoint", restore_text)
        self.assertIn("approvalRequired: yes", restore_text)
        self.assertIn("Tool: checkpoint_delete", delete_text)
        self.assertIn("Tool: check_checkpoint_delete", check_delete_text)
        self.assertIn("approvalRequired: no", check_delete_text)
        self.assertIn("category: checkpoint", delete_text)
        self.assertIn("approvalRequired: yes", delete_text)
        self.assertIn("Tool: check_checkpoint_prune", check_prune_text)
        self.assertIn("approvalRequired: no", check_prune_text)
        self.assertIn("Tool: checkpoint_prune", prune_text)
        self.assertIn("approvalRequired: yes", prune_text)
        self.assertIn("Tool not found: git_pu", missing_text)
        self.assertIn("git_pull", missing_text)
        self.assertEqual(get_tool_text(None), "Usage: /tool <name>")

    def test_get_permissions_text_reports_approval_and_hard_blocks(self) -> None:
        text = get_permissions_text("deny")

        self.assertIn("Permissions:", text)
        self.assertIn("approvalPolicy: deny", text)
        self.assertIn("approvalRequiredTools:", text)
        self.assertIn("readOnlyTools:", text)
        self.assertIn("edit:", text)
        self.assertIn("write_file", text)
        self.assertIn("checkpoint:", text)
        self.assertIn("checkpoint_restore", text)
        self.assertIn("checkpoint_delete", text)
        self.assertIn("checkpoint_prune", text)
        self.assertIn("git:", text)
        self.assertIn("git_push", text)
        self.assertIn("command:", text)
        self.assertIn("run_command", text)
        self.assertIn("commandHardBlocks:", text)
        self.assertIn("sudo reboot", text)
        self.assertIn("rm -rf /", text)
        self.assertIn("network script", text)
        self.assertIn("xdg-open .", text)
        self.assertIn("explorer.exe .", text)
        self.assertIn("code .", text)
        self.assertIn("firefox http://127.0.0.1:5173", text)
        self.assertIn("GUI application launch", text)

    def test_get_permissions_report_returns_structured_policy(self) -> None:
        report = get_permissions_report("allow")

        self.assertEqual(report["approvalPolicy"], "allow")
        approval_required = report["approvalRequiredTools"]
        self.assertIsInstance(approval_required, dict)
        self.assertGreater(approval_required["count"], 0)
        self.assertIn("write_file", approval_required["tools"])
        self.assertIn("write_file", approval_required["byCategory"]["edit"])
        self.assertIn("run_command", approval_required["byCategory"]["command"])
        self.assertIn("git_push", approval_required["byCategory"]["git"])
        read_only = report["readOnlyTools"]
        self.assertIsInstance(read_only, dict)
        self.assertGreater(read_only["count"], 0)
        self.assertIn("read_file", read_only["tools"])
        hard_blocks = report["commandHardBlocks"]
        self.assertIsInstance(hard_blocks, dict)
        self.assertEqual(hard_blocks["active"], hard_blocks["total"])
        self.assertTrue(any(check["command"] == "code ." and check["active"] for check in hard_blocks["checks"]))

    def test_get_checks_text_reports_suggested_verification_commands(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-commands-") as base:
            root = Path(base)
            subprocess.run(["git", "init"], cwd=root, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            (root / "package.json").write_text('{"scripts":{"test":"node test.js","build":"vite build","dev":"vite"}}\n', encoding="utf-8")
            (root / "tests").mkdir()
            (root / "tests" / "test_app.py").write_text("def test_ok():\n    assert True\n", encoding="utf-8")
            (root / "pkg").mkdir()
            (root / "pkg" / "__init__.py").write_text("", encoding="utf-8")

            text = get_checks_text(root)
            limited = get_checks_text(root, max_checks=1)

        self.assertIn("Checks:", text)
        self.assertIn(f"projectRoot: {root.resolve()}", text)
        self.assertIn("suggestedChecks:", text)
        self.assertIn("changedFiles:", text)
        self.assertIn("commands:", text)
        self.assertIn("npm run test", text)
        self.assertIn("suggestedChecks: 1/", limited)
        self.assertIn("truncated: yes", limited)

        with self.assertRaisesRegex(ValueError, "max_checks must be at most 100"):
            get_checks_text(root, max_checks=101)
        self.assertIn("npm run build", text)
        self.assertIn("python -m unittest discover -s tests", text)
        self.assertIn("python -m compileall -q pkg", text)

    def test_get_checks_report_returns_structured_suggestions(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-commands-") as base:
            root = Path(base)
            subprocess.run(["git", "init"], cwd=root, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            (root / "package.json").write_text('{"scripts":{"test":"node test.js","build":"vite build","dev":"vite"}}\n', encoding="utf-8")
            (root / "tests").mkdir()
            (root / "tests" / "test_app.py").write_text("def test_ok():\n    assert True\n", encoding="utf-8")
            (root / "pkg").mkdir()
            (root / "pkg" / "__init__.py").write_text("", encoding="utf-8")

            report = get_checks_report(root, max_checks=10)

        self.assertEqual(report["projectRoot"], str(root.resolve()))
        suggested = report["suggestedChecks"]
        self.assertIsInstance(suggested, dict)
        self.assertLessEqual(suggested["shown"], suggested["total"])
        self.assertFalse(suggested["truncated"])
        self.assertIsInstance(suggested["commands"], list)
        commands = [item["command"] for item in suggested["commands"] if isinstance(item, dict)]
        self.assertIn("npm run test", commands)
        self.assertIn("python -m unittest discover -s tests", commands)
        self.assertIsInstance(report["changedFiles"], list)
        self.assertIsInstance(report["message"], str)

    def test_get_check_suggested_checks_text_preflights_suggested_commands(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-commands-") as base:
            root = Path(base)
            subprocess.run(["git", "init"], cwd=root, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            (root / "tests").mkdir()
            (root / "tests" / "test_app.py").write_text(
                "import unittest\n\nclass AppTests(unittest.TestCase):\n    def test_ok(self):\n        self.assertTrue(True)\n",
                encoding="utf-8",
            )

            text = get_check_suggested_checks_text(root, "1")
            invalid = get_check_suggested_checks_text(root, "11")

        self.assertIn("Check suggested checks:", text)
        self.assertIn("ok: yes", text)
        self.assertIn("commands: 1/", text)
        self.assertIn("python -m unittest discover -s tests", text)
        self.assertIn("max must be at most 10", invalid)

    def test_get_run_suggested_checks_text_runs_suggested_commands(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-commands-") as base:
            root = Path(base)
            subprocess.run(["git", "init"], cwd=root, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            (root / "tests").mkdir()
            (root / "tests" / "test_app.py").write_text(
                "import unittest\n\nclass AppTests(unittest.TestCase):\n    def test_ok(self):\n        self.assertTrue(True)\n",
                encoding="utf-8",
            )

            text = get_run_suggested_checks_text(root, "1", timeout_ms=10_000, max_output_chars=2_000)

        self.assertIn("Run suggested checks:", text)
        self.assertIn("ok: yes", text)
        self.assertIn("ran: 1", text)
        self.assertIn("python -m unittest discover -s tests", text)
        self.assertIn("exitCode: 0", text)

    def test_get_run_suggested_checks_text_can_extract_output_contexts(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-commands-") as base:
            root = Path(base)
            subprocess.run(["git", "init"], cwd=root, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            (root / "src").mkdir()
            (root / "src" / "app.py").write_text("one\nTwo\nthree\n", encoding="utf-8")
            (root / "tests").mkdir()
            (root / "tests" / "test_app.py").write_text(
                "import unittest\n\nclass AppTests(unittest.TestCase):\n    def test_ok(self):\n        print('src/app.py:2:5: note')\n        self.assertTrue(True)\n",
                encoding="utf-8",
            )

            text = get_run_suggested_checks_text(
                root,
                "1",
                timeout_ms=10_000,
                max_output_chars=2_000,
                extract_output_contexts=True,
                context_lines=0,
                max_bytes_per_context=1000,
            )

        self.assertIn("Run suggested checks:", text)
        self.assertIn("outputContexts: 1/1", text)
        self.assertIn("src/app.py:2:5 [src/app.py:2:5]", text)
        self.assertIn("2: Two", text)

    def test_get_commands_text_reports_project_defined_commands(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-commands-") as base:
            root = Path(base)
            (root / "package.json").write_text('{"scripts":{"test":"node test.js","dev":"vite"}}\n', encoding="utf-8")
            (root / "pyproject.toml").write_text('[project]\n[project.scripts]\ndemo = "demo:main"\n', encoding="utf-8")
            (root / "Makefile").write_text("build:\n\tpython -m compileall demo\n", encoding="utf-8")

            text = get_commands_text(root)

        self.assertIn("Project commands:", text)
        self.assertIn(f"projectRoot: {root.resolve()}", text)
        self.assertIn("commands: 4/4", text)
        self.assertIn("metadataFiles: 3/3", text)
        self.assertIn("npm run test", text)
        self.assertIn("npm run dev", text)
        self.assertIn("demo", text)
        self.assertIn("make build", text)

    def test_get_commands_text_respects_bounds(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-commands-") as base:
            root = Path(base)
            (root / "package.json").write_text('{"scripts":{"test":"node test.js","dev":"vite"}}\n', encoding="utf-8")
            (root / "pyproject.toml").write_text('[project]\n[project.scripts]\ndemo = "demo:main"\n', encoding="utf-8")

            text = get_commands_text(root, max_commands=1, max_files=1)

        self.assertIn("Project commands:", text)
        self.assertIn("commands: 1/2", text)
        self.assertIn("metadataFiles: 1/2", text)
        self.assertIn("truncated: yes", text)
        self.assertIn("npm run dev", text)
        self.assertNotIn("demo", text)

    def test_get_related_tests_text_reports_candidate_files(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-commands-") as base:
            root = Path(base)
            (root / "pkg").mkdir()
            (root / "tests").mkdir()
            (root / "pkg" / "actions.py").write_text("def run():\n    return 1\n", encoding="utf-8")
            (root / "tests" / "test_actions.py").write_text("def test_run():\n    assert True\n", encoding="utf-8")

            text = get_related_tests_text(root, "pkg/actions.py")
            invalid = get_related_tests_text(root, "--bad")

        self.assertIn("Related tests:", text)
        self.assertIn("targetPaths: 1", text)
        self.assertIn("pkg/actions.py", text)
        self.assertIn("tests/test_actions.py", text)
        self.assertIn("Usage: /related-tests [path...]", invalid)
        self.assertIn("options are not supported", invalid)

    def test_get_focused_test_commands_text_reports_commands(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-commands-") as base:
            root = Path(base)
            (root / "pkg").mkdir()
            (root / "tests").mkdir()
            (root / "pkg" / "actions.py").write_text("def run():\n    return 1\n", encoding="utf-8")
            (root / "tests" / "test_actions.py").write_text("def test_run():\n    assert True\n", encoding="utf-8")

            text = get_focused_test_commands_text(root, "pkg/actions.py")
            invalid = get_focused_test_commands_text(root, "--bad")

        self.assertIn("Focused test commands:", text)
        self.assertIn("targetPaths: 1", text)
        self.assertIn("commands: 1/1", text)
        self.assertIn("python -m unittest discover -s tests -p test_actions.py", text)
        self.assertIn("tests/test_actions.py", text)
        self.assertIn("Usage: /focused-tests [path...]", invalid)
        self.assertIn("options are not supported", invalid)

    def test_get_check_focused_test_commands_text_preflights_commands(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-commands-") as base:
            root = Path(base)
            (root / "pkg").mkdir()
            (root / "tests").mkdir()
            (root / "pkg" / "actions.py").write_text("def run():\n    return 1\n", encoding="utf-8")
            (root / "tests" / "test_actions.py").write_text("def test_run():\n    assert True\n", encoding="utf-8")

            text = get_check_focused_test_commands_text(root, "pkg/actions.py")
            invalid = get_check_focused_test_commands_text(root, "--bad")

        self.assertIn("Check focused test commands:", text)
        self.assertIn("targetPaths: 1", text)
        self.assertIn("focusedCommands: 1/1", text)
        self.assertIn("python -m unittest discover -s tests -p test_actions.py", text)
        self.assertIn("ok: yes", text)
        self.assertIn("message: Command preflight passed.", text)
        self.assertIn("Usage: /check-focused-tests [path...]", invalid)
        self.assertIn("options are not supported", invalid)

    def test_get_run_focused_test_commands_text_runs_commands(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-commands-") as base:
            root = Path(base)
            (root / "pkg").mkdir()
            (root / "tests").mkdir()
            (root / "pkg" / "actions.py").write_text("def run():\n    return 1\n", encoding="utf-8")
            (root / "tests" / "test_actions.py").write_text(
                "import unittest\n\nclass ActionTests(unittest.TestCase):\n    def test_run(self):\n        self.assertTrue(True)\n",
                encoding="utf-8",
            )

            text = get_run_focused_test_commands_text(root, "pkg/actions.py", timeout_ms=10_000, max_output_chars=2_000)
            invalid = get_run_focused_test_commands_text(root, "--bad")

        self.assertIn("Run focused test commands:", text)
        self.assertIn("targetPaths: 1", text)
        self.assertIn("focusedCommands: 1/1", text)
        self.assertIn("python -m unittest discover -s tests -p test_actions.py", text)
        self.assertIn("exitCode: 0", text)
        self.assertIn("Usage: /run-focused-tests [path...]", invalid)
        self.assertIn("options are not supported", invalid)

    def test_get_repo_map_text_reports_tree_files_and_symbols(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-commands-") as base:
            root = Path(base)
            (root / "src").mkdir()
            (root / "src" / "app.py").write_text(
                "import os\n\nclass App:\n    pass\n\ndef main():\n    return os.getcwd()\n",
                encoding="utf-8",
            )
            (root / "src" / "web.ts").write_text(
                "import { x } from './x';\nexport function render() { return x; }\n",
                encoding="utf-8",
            )

            text = get_repo_map_text(root, "src")

        self.assertIn("Repo map:", text)
        self.assertIn(f"projectRoot: {root.resolve()}", text)
        self.assertIn("path: src", text)
        self.assertIn("ok: yes", text)
        self.assertIn("tree:", text)
        self.assertIn("src/app.py", text)
        self.assertIn("src/web.ts", text)
        self.assertIn("symbols:", text)
        self.assertIn("src/app.py (python)", text)
        self.assertIn("import os", text)
        self.assertIn("class App", text)
        self.assertIn("function main", text)
        self.assertIn("src/web.ts", text)

    def test_get_search_text_reports_scoped_project_matches_without_sensitive_files(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-commands-") as base:
            root = Path(base)
            (root / "src").mkdir()
            (root / "src" / "app.py").write_text("needle = 'visible'\nprint(needle)\n", encoding="utf-8")
            (root / "other.txt").write_text("needle outside scope\n", encoding="utf-8")
            (root / ".env").write_text("SECRET=needle\n", encoding="utf-8")

            text = get_search_text(root, "needle", path="src")
            usage = get_search_text(root)

        self.assertIn("Search:", text)
        self.assertIn(f"projectRoot: {root.resolve()}", text)
        self.assertIn("query: needle", text)
        self.assertIn("path: src", text)
        self.assertIn("ok: yes", text)
        self.assertIn("matches: 2/2", text)
        self.assertIn("src/app.py:1:", text)
        self.assertIn("src/app.py:2:", text)
        self.assertNotIn("other.txt", text)
        self.assertNotIn(".env", text)
        self.assertEqual(usage, "Usage: /search <query>")

    def test_get_search_contexts_text_reports_structured_contexts_without_sensitive_files(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-commands-") as base:
            root = Path(base)
            (root / "src").mkdir()
            (root / "src" / "app.py").write_text("before\nneedle = 'visible'\nafter\n", encoding="utf-8")
            (root / "other.txt").write_text("needle outside scope\n", encoding="utf-8")
            (root / ".env").write_text("SECRET=needle\n", encoding="utf-8")

            text = get_search_contexts_text(root, "needle", path="src", context_lines=1, max_bytes_per_context=1000)
            usage = get_search_contexts_text(root)

        self.assertIn("Search contexts:", text)
        self.assertIn(f"projectRoot: {root.resolve()}", text)
        self.assertIn("query: needle", text)
        self.assertIn("path: src", text)
        self.assertIn("ok: yes", text)
        self.assertIn("contexts: 1/1", text)
        self.assertIn("path: src/app.py", text)
        self.assertIn("line: 2", text)
        self.assertIn("before", text)
        self.assertIn("needle = 'visible'", text)
        self.assertNotIn("other.txt", text)
        self.assertNotIn(".env", text)
        self.assertEqual(usage, "Usage: /search-contexts <query>")

    def test_get_glob_text_reports_project_file_matches_without_sensitive_files(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-commands-") as base:
            root = Path(base)
            (root / "src").mkdir()
            (root / "tests").mkdir()
            (root / "dist").mkdir()
            (root / "src" / "app.py").write_text("print('ok')\n", encoding="utf-8")
            (root / "tests" / "test_app.py").write_text("def test_ok():\n    assert True\n", encoding="utf-8")
            (root / "dist" / "generated.py").write_text("print('generated')\n", encoding="utf-8")
            (root / ".env").write_text("SECRET=1\n", encoding="utf-8")

            text = get_glob_text(root, "**/*.py")
            usage = get_glob_text(root)

        self.assertIn("Glob:", text)
        self.assertIn(f"projectRoot: {root.resolve()}", text)
        self.assertIn("pattern: **/*.py", text)
        self.assertIn("ok: yes", text)
        self.assertIn("matches: 2/2", text)
        self.assertIn("src/app.py", text)
        self.assertIn("tests/test_app.py", text)
        self.assertNotIn("dist/generated.py", text)
        self.assertNotIn(".env", text)
        self.assertEqual(usage, "Usage: /glob <pattern>")

    def test_get_tree_text_reports_project_tree_without_sensitive_files(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-commands-") as base:
            root = Path(base)
            (root / "src").mkdir()
            (root / "src" / "pkg").mkdir()
            (root / "src" / "app.py").write_text("print('ok')\n", encoding="utf-8")
            (root / "src" / "pkg" / "__init__.py").write_text("", encoding="utf-8")
            (root / ".env").write_text("SECRET=hidden\n", encoding="utf-8")

            text = get_tree_text(root, "src")
            secret = get_tree_text(root, ".env")

        self.assertIn("Tree:", text)
        self.assertIn(f"projectRoot: {root.resolve()}", text)
        self.assertIn("path: src", text)
        self.assertIn("ok: yes", text)
        self.assertIn("entries: 3/3", text)
        self.assertIn("src/app.py", text)
        self.assertIn("src/pkg/", text)
        self.assertIn("src/pkg/__init__.py", text)
        self.assertNotIn(".env", text)
        self.assertIn("ok: no", secret)
        self.assertIn("Path is protected", secret)

    def test_get_symbols_text_reports_python_and_generic_source_outlines(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-commands-") as base:
            root = Path(base)
            (root / "src").mkdir()
            (root / "web").mkdir()
            (root / "src" / "app.py").write_text(
                "import os\n\nclass App:\n    pass\n\ndef main():\n    return os.getcwd()\n",
                encoding="utf-8",
            )
            (root / "web" / "app.ts").write_text(
                "import { readFile } from 'fs';\nexport class View {}\nexport function render() {}\n",
                encoding="utf-8",
            )

            text = get_symbols_text(root, "src/app.py web/app.ts missing.py")
            usage = get_symbols_text(root)

        self.assertIn("Symbols:", text)
        self.assertIn(f"projectRoot: {root.resolve()}", text)
        self.assertIn("files: 2/3", text)
        self.assertIn("symbols: 4", text)
        self.assertIn("imports: 2", text)
        self.assertIn("src/app.py (python)", text)
        self.assertIn("imports: 1: import os", text)
        self.assertIn("class App:3", text)
        self.assertIn("function main:6", text)
        self.assertIn("web/app.ts (typescript)", text)
        self.assertIn("1: import { readFile } from 'fs';", text)
        self.assertIn("class View:2", text)
        self.assertIn("function render:3", text)
        self.assertIn("missing.py (error)", text)
        self.assertEqual(usage, "Usage: /symbols <path...>")

    def test_get_file_info_text_reports_file_directory_binary_missing_and_protected_paths(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-commands-") as base:
            root = Path(base)
            (root / "src").mkdir()
            (root / "src" / "app.py").write_text("one\ntwo\n", encoding="utf-8")
            (root / "asset.bin").write_bytes(b"\x00\x01")
            (root / ".env").write_text("SECRET=hidden\n", encoding="utf-8")

            text = get_file_info_text(root, "src/app.py src asset.bin missing.py .env")
            usage = get_file_info_text(root)

        self.assertIn("File info:", text)
        self.assertIn(f"projectRoot: {root.resolve()}", text)
        self.assertIn("paths: 3/5", text)
        self.assertIn("- src/app.py", text)
        self.assertIn("type: file", text)
        self.assertIn("sizeBytes: 8", text)
        self.assertIn("lineCount: 2", text)
        self.assertIn("binary: no", text)
        self.assertIn("- src", text)
        self.assertIn("type: directory", text)
        self.assertIn("- asset.bin", text)
        self.assertIn("binary: yes", text)
        self.assertIn("- missing.py", text)
        self.assertIn("type: missing", text)
        self.assertIn("Path does not exist: missing.py", text)
        self.assertIn("- .env", text)
        self.assertIn("Path is protected", text)
        self.assertEqual(usage, "Usage: /file-info <path...>")

    def test_get_image_info_text_reports_dimensions_missing_and_protected_paths(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-commands-") as base:
            root = Path(base)
            (root / "assets").mkdir()
            (root / "assets" / "logo.png").write_bytes(
                b"\x89PNG\r\n\x1a\n"
                b"\x00\x00\x00\rIHDR"
                + (13).to_bytes(4, "big")
                + (17).to_bytes(4, "big")
                + b"\x08\x02\x00\x00\x00\x00\x00\x00\x00"
            )
            (root / ".env").write_text("SECRET=hidden\n", encoding="utf-8")

            text = get_image_info_text(root, "assets/logo.png assets missing.png .env")
            usage = get_image_info_text(root)

        self.assertIn("Image info:", text)
        self.assertIn(f"projectRoot: {root.resolve()}", text)
        self.assertIn("images: 1/4", text)
        self.assertIn("- assets/logo.png", text)
        self.assertIn("format: png", text)
        self.assertIn("mimeType: image/png", text)
        self.assertIn("width: 13", text)
        self.assertIn("height: 17", text)
        self.assertIn("- assets", text)
        self.assertIn("Path is not a file: assets", text)
        self.assertIn("- missing.png", text)
        self.assertIn("Path does not exist: missing.png", text)
        self.assertIn("- .env", text)
        self.assertIn("Path is protected", text)
        self.assertEqual(usage, "Usage: /image-info <path...>")

    def test_get_read_text_reports_project_file_line_range_and_protects_sensitive_files(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-commands-") as base:
            root = Path(base)
            (root / "src").mkdir()
            (root / "src" / "app.py").write_text("one\nTwo\nthree\nfour\n", encoding="utf-8")
            (root / ".env").write_text("SECRET=hidden\n", encoding="utf-8")

            text = get_read_text(root, "src/app.py 2:3")
            secret = get_read_text(root, ".env")
            usage = get_read_text(root)

        self.assertIn("Read:", text)
        self.assertIn(f"projectRoot: {root.resolve()}", text)
        self.assertIn("path: src/app.py", text)
        self.assertIn("range: 2:3", text)
        self.assertIn("ok: yes", text)
        self.assertIn("totalBytes:", text)
        self.assertIn("content:", text)
        self.assertIn("2: Two", text)
        self.assertIn("3: three", text)
        self.assertNotIn("1: one", text)
        self.assertIn("ok: no", secret)
        self.assertIn("Path is protected", secret)
        self.assertEqual(usage, "Usage: /read <path> [start[:end]]")

    def test_get_around_text_reports_project_file_context_and_protects_sensitive_files(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-commands-") as base:
            root = Path(base)
            (root / "src").mkdir()
            (root / "src" / "app.py").write_text("one\nTwo\nthree\nfour\n", encoding="utf-8")
            (root / ".env").write_text("SECRET=hidden\n", encoding="utf-8")

            text = get_around_text(root, "src/app.py 3 1")
            secret = get_around_text(root, ".env 1")
            invalid = get_around_text(root, "src/app.py nope")
            usage = get_around_text(root)

        self.assertIn("Around:", text)
        self.assertIn(f"projectRoot: {root.resolve()}", text)
        self.assertIn("path: src/app.py", text)
        self.assertIn("line: 3", text)
        self.assertIn("ok: yes", text)
        self.assertIn("range: 2:4", text)
        self.assertIn("contextLines: 1", text)
        self.assertIn("targetLineExists: yes", text)
        self.assertIn("2: Two", text)
        self.assertIn("3: three", text)
        self.assertIn("4: four", text)
        self.assertNotIn("1: one", text)
        self.assertIn("ok: no", secret)
        self.assertIn("Path is protected", secret)
        self.assertIn("line must be an integer", invalid)
        self.assertEqual(usage, "Usage: /around <path> <line> [context-lines]")

    def test_get_around_many_text_reads_multiple_contexts_and_reports_errors(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-commands-") as base:
            root = Path(base)
            (root / "src").mkdir()
            (root / "src" / "app.py").write_text("one\nTwo\nthree\nfour\n", encoding="utf-8")
            (root / "tests").mkdir()
            (root / "tests" / "test_app.py").write_text("alpha\nbeta\ngamma\n", encoding="utf-8")
            (root / ".env").write_text("SECRET=hidden\n", encoding="utf-8")

            text = get_around_many_text(root, "src/app.py:3:1 tests/test_app.py:2 missing.py:1 .env:1")
            invalid = get_around_many_text(root, "src/app.py:not-a-line")
            usage = get_around_many_text(root)

        self.assertIn("Around many:", text)
        self.assertIn(f"projectRoot: {root.resolve()}", text)
        self.assertIn("contexts: 2/4", text)
        self.assertIn("Context: src/app.py:3", text)
        self.assertIn("range: 2:4", text)
        self.assertIn("2: Two", text)
        self.assertIn("3: three", text)
        self.assertIn("4: four", text)
        self.assertIn("Context: tests/test_app.py:2", text)
        self.assertIn("1: alpha", text)
        self.assertIn("2: beta", text)
        self.assertIn("Context: missing.py:1", text)
        self.assertIn("File does not exist", text)
        self.assertIn("Context: .env:1", text)
        self.assertIn("Path is protected", text)
        self.assertIn("invalid line in context spec", invalid)
        self.assertEqual(usage, "Usage: /around-many <path:line[:context-lines]...>")

    def test_get_output_contexts_text_extracts_references_and_reads_contexts(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-commands-") as base:
            root = Path(base)
            (root / "src").mkdir()
            (root / "src" / "app.py").write_text("one\nTwo\nthree\nfour\n", encoding="utf-8")
            (root / "tests").mkdir()
            (root / "tests" / "test_app.py").write_text("alpha\nbeta\ngamma\n", encoding="utf-8")
            output = f'  File "{root / "src" / "app.py"}", line 3, in main\ntests/test_app.py:2:5: assertion failed'

            text = get_output_contexts_text(root, output, context_lines=1, max_contexts=10, max_bytes_per_context=1000)
            usage = get_output_contexts_text(root)

        self.assertIn("Output contexts:", text)
        self.assertIn(f"projectRoot: {root.resolve()}", text)
        self.assertIn("contexts: 2/2", text)
        self.assertIn("totalRefs: 2", text)
        self.assertIn("Context: src/app.py:3", text)
        self.assertIn("raw: ", text)
        self.assertIn("2: Two", text)
        self.assertIn("3: three", text)
        self.assertIn("Context: tests/test_app.py:2:5", text)
        self.assertIn("2: beta", text)
        self.assertEqual(usage, "Usage: /output-contexts <text>")

    def test_get_output_diagnostics_text_summarizes_diagnostics_and_reads_contexts(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-commands-") as base:
            root = Path(base)
            (root / "src").mkdir()
            (root / "src" / "app.py").write_text("one\nTwo\nthree\nfour\n", encoding="utf-8")
            output = "warning: src/app.py:2:3 check this\nERROR src/app.py:3 failed\nall good"

            text = get_output_diagnostics_text(
                root,
                output,
                context_lines=0,
                max_diagnostics=10,
                max_contexts=10,
                max_bytes_per_context=1000,
            )
            usage = get_output_diagnostics_text(root)

        self.assertIn("Output diagnostics:", text)
        self.assertIn(f"projectRoot: {root.resolve()}", text)
        self.assertIn("diagnostics: 2/2", text)
        self.assertIn("contexts: 2/2", text)
        self.assertIn("totalRefs: 2", text)
        self.assertIn("- warning outputLine=1 src/app.py:2:3", text)
        self.assertIn("- error outputLine=2 src/app.py:3", text)
        self.assertIn("Context: src/app.py:2:3", text)
        self.assertIn("2: Two", text)
        self.assertIn("Context: src/app.py:3", text)
        self.assertIn("3: three", text)
        self.assertEqual(usage, "Usage: /output-diagnostics <text>")

    def test_get_python_traceback_text_summarizes_exception_and_reads_frame_context(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-commands-") as base:
            root = Path(base)
            (root / "src").mkdir()
            (root / "src" / "app.py").write_text("one\nraise ValueError('bad')\nthree\n", encoding="utf-8")
            output = "\n".join(
                [
                    "Traceback (most recent call last):",
                    f'  File "{root / "src" / "app.py"}", line 2, in run',
                    "    raise ValueError('bad')",
                    "ValueError: bad",
                ]
            )

            text = get_python_traceback_text(
                root,
                output,
                context_lines=0,
                max_diagnostics=10,
                max_contexts=10,
                max_bytes_per_context=1000,
            )
            usage = get_python_traceback_text(root)

        self.assertIn("Python traceback:", text)
        self.assertIn("diagnostics: 3/3", text)
        self.assertIn("contexts: 1/1", text)
        self.assertIn("totalRefs: 1", text)
        self.assertIn("- error outputLine=1: Traceback (most recent call last):", text)
        self.assertIn("- info outputLine=2 src/app.py:2", text)
        self.assertIn("- error outputLine=4: ValueError: bad", text)
        self.assertIn("Context: src/app.py:2", text)
        self.assertIn("2: raise ValueError('bad')", text)
        self.assertEqual(usage, "Usage: /python-traceback <text>")

    def test_get_tail_text_reports_project_file_tail_and_protects_sensitive_files(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-commands-") as base:
            root = Path(base)
            (root / "logs").mkdir()
            (root / "logs" / "app.log").write_text("one\ntwo\nthree\nfour\n", encoding="utf-8")
            (root / ".env").write_text("SECRET=hidden\n", encoding="utf-8")

            text = get_tail_text(root, "logs/app.log 2")
            secret = get_tail_text(root, ".env")
            invalid = get_tail_text(root, "logs/app.log 0")
            usage = get_tail_text(root)

        self.assertIn("Tail:", text)
        self.assertIn(f"projectRoot: {root.resolve()}", text)
        self.assertIn("path: logs/app.log", text)
        self.assertIn("ok: yes", text)
        self.assertIn("lines: 2/4", text)
        self.assertIn("startLine: 3", text)
        self.assertIn("requestedLines: 2", text)
        self.assertIn("3: three", text)
        self.assertIn("4: four", text)
        self.assertNotIn("1: one", text)
        self.assertIn("ok: no", secret)
        self.assertIn("Path is protected", secret)
        self.assertIn("lines must be at least 1", invalid)
        self.assertEqual(usage, "Usage: /tail <path> [lines]")

    def test_get_read_files_text_reads_multiple_project_files_and_reports_errors(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-commands-") as base:
            root = Path(base)
            (root / "src").mkdir()
            (root / "src" / "app.py").write_text("print('app')\n", encoding="utf-8")
            (root / "tests").mkdir()
            (root / "tests" / "test_app.py").write_text("def test_app():\n    assert True\n", encoding="utf-8")
            (root / ".env").write_text("SECRET=hidden\n", encoding="utf-8")

            text = get_read_files_text(root, "src/app.py tests/test_app.py missing.py .env")
            usage = get_read_files_text(root)
            too_many = get_read_files_text(root, [f"{index}.py" for index in range(21)])

        self.assertIn("Read files:", text)
        self.assertIn(f"projectRoot: {root.resolve()}", text)
        self.assertIn("files: 2/4", text)
        self.assertIn("maxBytesPerFile: 20000", text)
        self.assertIn("File: src/app.py", text)
        self.assertIn("ok: yes", text)
        self.assertIn("print('app')", text)
        self.assertIn("File: tests/test_app.py", text)
        self.assertIn("def test_app():", text)
        self.assertIn("File: missing.py", text)
        self.assertIn("File does not exist", text)
        self.assertIn("File: .env", text)
        self.assertIn("Path is protected", text)
        self.assertEqual(usage, "Usage: /read-files <path...>")
        self.assertIn("expected at most 20 paths", too_many)

    def test_get_read_ranges_text_reads_multiple_focused_ranges_and_reports_errors(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-commands-") as base:
            root = Path(base)
            (root / "src").mkdir()
            (root / "src" / "app.py").write_text("one\nTwo\nthree\nfour\n", encoding="utf-8")
            (root / "tests").mkdir()
            (root / "tests" / "test_app.py").write_text("alpha\nbeta\ngamma\n", encoding="utf-8")
            (root / ".env").write_text("SECRET=hidden\n", encoding="utf-8")

            text = get_read_ranges_text(root, "src/app.py:2:3 tests/test_app.py:1 missing.py:1 .env:1")
            usage = get_read_ranges_text(root)
            invalid = get_read_ranges_text(root, "src/app.py:4:2")

        self.assertIn("Read ranges:", text)
        self.assertIn(f"projectRoot: {root.resolve()}", text)
        self.assertIn("ranges: 2/4", text)
        self.assertIn("Range: src/app.py:2:3", text)
        self.assertIn("2: Two", text)
        self.assertIn("3: three", text)
        self.assertNotIn("1: one", text)
        self.assertIn("Range: tests/test_app.py:1:1", text)
        self.assertIn("1: alpha", text)
        self.assertIn("Range: missing.py:1:1", text)
        self.assertIn("File does not exist", text)
        self.assertIn("Range: .env:1:1", text)
        self.assertIn("Path is protected", text)
        self.assertEqual(usage, "Usage: /read-ranges <path:start[:end]...>")
        self.assertIn("end line must be greater than or equal to start line", invalid)

    def test_get_read_ranges_text_applies_max_bytes_per_range(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-commands-") as base:
            root = Path(base)
            (root / "large.txt").write_text(f"{'x' * 1200}\n", encoding="utf-8")

            text = get_read_ranges_text(root, "large.txt:1:1", max_bytes_per_range=1000)
            too_small = get_read_ranges_text(root, "large.txt:1:1", max_bytes_per_range=999)

        self.assertIn("maxBytesPerRange: 1000", text)
        self.assertIn("maxBytes: 1000", text)
        self.assertIn("truncated: yes", text)
        self.assertIn("[file truncated]", text)
        self.assertIn("max_bytes_per_range must be at least 1000", too_small)

    def test_get_python_check_and_config_check_text_report_syntax_results(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-commands-") as base:
            root = Path(base)
            (root / "src").mkdir()
            (root / "src" / "ok.py").write_text("print('ok')\n", encoding="utf-8")
            (root / "src" / "bad.py").write_text("def broken(:\n    pass\n", encoding="utf-8")
            (root / "good.json").write_text('{"ok": true}\n', encoding="utf-8")
            (root / "bad.json").write_text('{"bad": }\n', encoding="utf-8")

            python_text = get_python_check_text(root, "src")
            config_text = get_config_check_text(root)
            python_usage = get_python_check_text(root, "src extra")
            config_usage = get_config_check_text(root, "good.json extra")

        self.assertIn("Python check:", python_text)
        self.assertIn(f"projectRoot: {root.resolve()}", python_text)
        self.assertIn("ok: no", python_text)
        self.assertIn("path: src", python_text)
        self.assertIn("files: 2/2", python_text)
        self.assertIn("src/ok.py: ok", python_text)
        self.assertIn("src/bad.py: failed", python_text)
        self.assertIn("line", python_text)
        self.assertIn("Config check:", config_text)
        self.assertIn("ok: no", config_text)
        self.assertIn("good.json (json): ok", config_text)
        self.assertIn("bad.json (json): failed", config_text)
        self.assertIn("Usage: /python-check [path]", python_usage)
        self.assertIn("expected at most one path", python_usage)
        self.assertIn("Usage: /config-check [path]", config_usage)
        self.assertIn("expected at most one path", config_usage)

    def test_get_python_deps_defs_and_refs_text_report_python_matches(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-commands-") as base:
            root = Path(base)
            (root / "src").mkdir()
            (root / "src" / "__init__.py").write_text("", encoding="utf-8")
            (root / "src" / "helper.py").write_text("def helper():\n    return 1\n", encoding="utf-8")
            (root / "src" / "app.py").write_text(
                "import os\n"
                "from src.helper import helper\n\n"
                "class Runner:\n"
                "    def run(self):\n"
                "        return helper()\n\n"
                "def run_agent():\n"
                "    runner = Runner()\n"
                "    return runner.run()\n",
                encoding="utf-8",
            )
            (root / "web").mkdir()
            (root / "web" / "app.ts").write_text("function run_agent() {}\n", encoding="utf-8")

            deps_text = get_python_deps_text(root, "src")
            defs_text = get_python_defs_text(root, "Runner.run src")
            refs_text = get_python_refs_text(root, "run_agent src")
            ref_contexts_text = get_python_ref_contexts_text(root, "run_agent src", max_matches=1, context_lines=1, max_bytes_per_context=1000)
            flag_defs_text = get_python_defs_text(root, symbol="helper", path="src")
            missing_usage = get_python_refs_text(root)
            missing_context_usage = get_python_ref_contexts_text(root)
            too_many_usage = get_python_defs_text(root, "run_agent src extra")

        self.assertIn("Python dependencies:", deps_text)
        self.assertIn(f"projectRoot: {root.resolve()}", deps_text)
        self.assertIn("path: src", deps_text)
        self.assertIn("files: 3/3", deps_text)
        self.assertIn("src/app.py", deps_text)
        self.assertIn("external: os", deps_text)
        self.assertIn("local:", deps_text)
        self.assertIn("Python definitions:", defs_text)
        self.assertIn("symbol: Runner.run", defs_text)
        self.assertIn("definitions: 1/1", defs_text)
        self.assertIn("src/app.py:5", defs_text)
        self.assertIn("Runner.run", defs_text)
        self.assertIn("Python references:", refs_text)
        self.assertIn("symbol: run_agent", refs_text)
        self.assertIn("references: 1/1", refs_text)
        self.assertIn("src/app.py:8", refs_text)
        self.assertNotIn("web/app.ts", refs_text)
        self.assertIn("Python reference contexts:", ref_contexts_text)
        self.assertIn("contexts: 1/1", ref_contexts_text)
        self.assertIn("contextLines: 1", ref_contexts_text)
        self.assertIn("src/app.py:8", ref_contexts_text)
        self.assertIn("def run_agent", ref_contexts_text)
        self.assertIn("symbol: helper", flag_defs_text)
        self.assertIn("Usage: /python-refs <symbol> [path]", missing_usage)
        self.assertIn("requires a symbol", missing_usage)
        self.assertIn("Usage: /python-ref-contexts <symbol> [path]", missing_context_usage)
        self.assertIn("Usage: /python-defs <symbol> [path]", too_many_usage)
        self.assertIn("expected a symbol and optional path", too_many_usage)

    def test_get_python_calls_and_call_graph_text_report_python_edges(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-commands-") as base:
            root = Path(base)
            (root / "src").mkdir()
            (root / "src" / "app.py").write_text(
                "def helper():\n"
                "    return 1\n\n"
                "class Runner:\n"
                "    def run(self):\n"
                "        return helper()\n\n"
                "def run_agent():\n"
                "    runner = Runner()\n"
                "    return runner.run()\n",
                encoding="utf-8",
            )

            calls_text = get_python_calls_text(root, "helper src")
            graph_text = get_python_call_graph_text(root, "src")
            flag_calls_text = get_python_calls_text(root, symbol="Runner", path="src")
            missing_usage = get_python_calls_text(root)
            too_many_usage = get_python_call_graph_text(root, "src extra")

        self.assertIn("Python calls:", calls_text)
        self.assertIn(f"projectRoot: {root.resolve()}", calls_text)
        self.assertIn("symbol: helper", calls_text)
        self.assertIn("path: src", calls_text)
        self.assertIn("calls: 1/1", calls_text)
        self.assertIn("Runner.run -> helper", calls_text)
        self.assertIn("Python call graph:", graph_text)
        self.assertIn("path: src", graph_text)
        self.assertIn("edges: 3/3", graph_text)
        self.assertIn("Runner.run -> helper", graph_text)
        self.assertIn("run_agent -> Runner", graph_text)
        self.assertIn("run_agent -> runner.run", graph_text)
        self.assertIn("symbol: Runner", flag_calls_text)
        self.assertIn("Usage: /python-calls <symbol> [path]", missing_usage)
        self.assertIn("requires a symbol", missing_usage)
        self.assertIn("Usage: /python-call-graph [path]", too_many_usage)
        self.assertIn("expected at most one path", too_many_usage)

    def test_get_python_rename_preview_and_rename_text_report_and_apply_replacements(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-commands-") as base:
            root = Path(base)
            (root / "src").mkdir()
            app = root / "src" / "app.py"
            app.write_text(
                "def run_agent():\n"
                "    return 1\n\n"
                "value = run_agent()\n",
                encoding="utf-8",
            )

            preview_text = get_python_rename_preview_text(root, "run_agent execute_agent src")
            before_apply = app.read_text(encoding="utf-8")
            rename_text = get_python_rename_text(root, "run_agent execute_agent src")
            after_apply = app.read_text(encoding="utf-8")
            flag_preview_usage = get_python_rename_preview_text(root, symbol="execute_agent", new_name="run_agent", path="src")
            missing_usage = get_python_rename_preview_text(root)
            too_many_usage = get_python_rename_text(root, "execute_agent run_agent src extra")

        self.assertIn("Python rename preview:", preview_text)
        self.assertIn(f"projectRoot: {root.resolve()}", preview_text)
        self.assertIn("rename: run_agent -> execute_agent", preview_text)
        self.assertIn("path: src", preview_text)
        self.assertIn("replacements: 2", preview_text)
        self.assertIn("src/app.py: replacements=2", preview_text)
        self.assertIn("-def run_agent():", preview_text)
        self.assertIn("+def execute_agent():", preview_text)
        self.assertIn("def run_agent()", before_apply)
        self.assertIn("Python rename:", rename_text)
        self.assertIn("Renamed run_agent to execute_agent", rename_text)
        self.assertIn("def execute_agent()", after_apply)
        self.assertIn("value = execute_agent()", after_apply)
        self.assertIn("rename: execute_agent -> run_agent", flag_preview_usage)
        self.assertIn("Usage: /python-rename-preview <symbol> <new_name> [path]", missing_usage)
        self.assertIn("requires symbol and new_name", missing_usage)
        self.assertIn("Usage: /python-rename <symbol> <new_name> [path]", too_many_usage)
        self.assertIn("expected symbol, new_name, and optional path", too_many_usage)

    def test_get_replace_python_definition_text_preview_and_apply_changes(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-commands-") as base:
            root = Path(base)
            (root / "src").mkdir()
            app = root / "src" / "app.py"
            app.write_text(
                "def helper():\n"
                "    return 1\n\n"
                "class Runner:\n"
                "    def run(self):\n"
                "        return helper()\n",
                encoding="utf-8",
            )

            replacement = "    def run(self):\\n        value = helper()\\n        return value + 1\\n"
            preview_text = get_check_replace_python_definition_text(root, f"Runner.run '{replacement}' src")
            before_apply = app.read_text(encoding="utf-8")
            replace_text = get_replace_python_definition_text(root, f"Runner.run '{replacement}' src")
            after_apply = app.read_text(encoding="utf-8")
            flag_preview = get_check_replace_python_definition_text(
                root,
                symbol="Runner.run",
                content="    def run(self):\n        return 3\n",
                path="src/app.py",
            )
            missing = get_replace_python_definition_text(root, "Runner.missing '    def missing(self):\\n        return 1\\n' src")
            bad_syntax = get_check_replace_python_definition_text(root, "Runner.run '    def run(self):\\n        return (\\n' src")
            missing_usage = get_check_replace_python_definition_text(root)
            too_many_usage = get_replace_python_definition_text(root, "Runner.run 'def run():\\n    return 1\\n' src extra")

        self.assertIn("Check replace Python definition:", preview_text)
        self.assertIn(f"projectRoot: {root.resolve()}", preview_text)
        self.assertIn("ok: yes", preview_text)
        self.assertIn("symbol: Runner.run", preview_text)
        self.assertIn("path: src", preview_text)
        self.assertIn("definition: Runner.run", preview_text)
        self.assertIn("definitionPath: src/app.py", preview_text)
        self.assertIn("    def run(self):", preview_text)
        self.assertIn("+        return value + 1", preview_text)
        self.assertIn("return helper()", before_apply)
        self.assertIn("Replace Python definition:", replace_text)
        self.assertIn("Replaced Python definition Runner.run", replace_text)
        self.assertIn("return value + 1", after_apply)
        self.assertIn("path: src/app.py", flag_preview)
        self.assertIn("ok: yes", flag_preview)
        self.assertIn("Replace Python definition:", missing)
        self.assertIn("ok: no", missing)
        self.assertIn("Python definition not found", missing)
        self.assertIn("Check replace Python definition:", bad_syntax)
        self.assertIn("ok: no", bad_syntax)
        self.assertIn("syntax error", bad_syntax)
        self.assertIn("Usage: /check-replace-python-def <symbol> <content> [path]", missing_usage)
        self.assertIn("requires symbol and content", missing_usage)
        self.assertIn("Usage: /replace-python-def <symbol> <content> [path]", too_many_usage)
        self.assertIn("expected symbol, content, and optional path", too_many_usage)

    def test_get_json_set_and_remove_text_preview_and_apply_changes(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-commands-") as base:
            root = Path(base)
            package = root / "package.json"
            package.write_text(
                json.dumps(
                    {
                        "scripts": {"test": "old", "dev": "vite"},
                        "private": False,
                        "keywords": ["agent", "cli"],
                    },
                    indent=2,
                )
                + "\n",
                encoding="utf-8",
            )

            preview_set = get_check_json_set_text(root, "package.json /scripts/test '\"npm test\"'")
            before_set = package.read_text(encoding="utf-8")
            applied_set = get_json_set_text(root, "package.json /private true")
            after_set = json.loads(package.read_text(encoding="utf-8"))
            preview_remove = get_check_json_remove_text(root, "package.json /scripts/dev")
            before_remove = package.read_text(encoding="utf-8")
            applied_remove = get_json_remove_text(root, "package.json /keywords/0")
            after_remove = json.loads(package.read_text(encoding="utf-8"))
            create_missing = get_check_json_set_text(root, "--create-missing package.json /nested/value 3")
            bad_value = get_json_set_text(root, "package.json /private not-json")
            bad_remove_usage = get_json_remove_text(root, "package.json /a /b")

        self.assertIn("Check JSON set:", preview_set)
        self.assertIn(f"projectRoot: {root.resolve()}", preview_set)
        self.assertIn("ok: yes", preview_set)
        self.assertIn("path: package.json", preview_set)
        self.assertIn("pointer: /scripts/test", preview_set)
        self.assertIn("-    \"test\": \"old\"", preview_set)
        self.assertIn("+    \"test\": \"npm test\"", preview_set)
        self.assertIn('"test": "old"', before_set)
        self.assertIn("JSON set:", applied_set)
        self.assertTrue(after_set["private"])
        self.assertIn("Check JSON remove:", preview_remove)
        self.assertIn("pointer: /scripts/dev", preview_remove)
        self.assertIn('"dev": "vite"', before_remove)
        self.assertIn("JSON remove:", applied_remove)
        self.assertEqual(after_remove["keywords"], ["cli"])
        self.assertIn("ok: yes", create_missing)
        self.assertIn("Usage: /json-set [--create-missing] <path> <pointer> <json-value>", bad_value)
        self.assertIn("JSON value is invalid", bad_value)
        self.assertIn("Usage: /json-remove <path> <pointer>", bad_remove_usage)
        self.assertIn("expected path and pointer", bad_remove_usage)

    def test_get_json_patch_text_preview_and_apply_changes(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-commands-") as base:
            root = Path(base)
            package = root / "package.json"
            package.write_text(
                json.dumps(
                    {
                        "scripts": {"test": "npm test"},
                        "private": False,
                        "keywords": ["agent"],
                    },
                    indent=2,
                )
                + "\n",
                encoding="utf-8",
            )
            operations = '[{"op":"add","path":"/scripts/dev","value":"vite"},{"op":"replace","path":"/private","value":true},{"op":"add","path":"/keywords/-","value":"cli"}]'

            preview = get_check_json_patch_text(root, f"package.json '{operations}'")
            before = package.read_text(encoding="utf-8")
            applied = get_json_patch_text(root, f"package.json '{operations}'")
            after = json.loads(package.read_text(encoding="utf-8"))
            bad_json = get_check_json_patch_text(root, "package.json not-json")
            bad_operation = get_json_patch_text(root, 'package.json \'[{"op":"remove"}]\'')

        self.assertIn("Check JSON patch:", preview)
        self.assertIn(f"projectRoot: {root.resolve()}", preview)
        self.assertIn("ok: yes", preview)
        self.assertIn("path: package.json", preview)
        self.assertIn("operations: 3", preview)
        self.assertIn("+    \"dev\": \"vite\"", preview)
        self.assertIn('"private": false', before)
        self.assertIn("JSON patch:", applied)
        self.assertEqual(after["scripts"]["dev"], "vite")
        self.assertTrue(after["private"])
        self.assertEqual(after["keywords"], ["agent", "cli"])
        self.assertIn("Usage: /check-json-patch <path> <json-ops-array>", bad_json)
        self.assertIn("JSON operations array is invalid", bad_json)
        self.assertIn("Usage: /json-patch <path> <json-ops-array>", bad_operation)
        self.assertIn("operation 1 requires a non-empty path", bad_operation)

    def test_get_line_edit_text_preview_and_apply_changes(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-commands-") as base:
            root = Path(base)
            app = root / "app.py"
            app.write_text("one\nold\nthree\n", encoding="utf-8")

            preview_replace = get_check_replace_lines_text(root, "app.py 2 2 'two\\n'")
            before_replace = app.read_text(encoding="utf-8")
            replaced = get_replace_lines_text(root, "app.py 2 2 'two\\n'")
            after_replace = app.read_text(encoding="utf-8")
            preview_insert = get_check_insert_lines_text(root, "app.py 3 'inserted\\n'")
            before_insert = app.read_text(encoding="utf-8")
            inserted = get_insert_lines_text(root, "app.py 3 'inserted\\n'")
            after_insert = app.read_text(encoding="utf-8")
            preview_append = get_check_append_file_text(root, "app.py 'tail\\n'")
            before_append = app.read_text(encoding="utf-8")
            appended = get_append_file_text(root, "app.py 'tail\\n'")
            after_append = app.read_text(encoding="utf-8")
            bad_range = get_replace_lines_text(root, "app.py 3 2 'bad\\n'")
            bad_insert = get_insert_lines_text(root, "app.py 2 ''")
            bad_append = get_append_file_text(root, "app.py")

        self.assertIn("Check replace lines:", preview_replace)
        self.assertIn(f"projectRoot: {root.resolve()}", preview_replace)
        self.assertIn("ok: yes", preview_replace)
        self.assertIn("range: 2-2", preview_replace)
        self.assertIn("+two", preview_replace)
        self.assertEqual(before_replace, "one\nold\nthree\n")
        self.assertIn("Replace lines:", replaced)
        self.assertEqual(after_replace, "one\ntwo\nthree\n")
        self.assertIn("Check insert lines:", preview_insert)
        self.assertIn("line: 3", preview_insert)
        self.assertEqual(before_insert, "one\ntwo\nthree\n")
        self.assertIn("Insert lines:", inserted)
        self.assertEqual(after_insert, "one\ntwo\ninserted\nthree\n")
        self.assertIn("Check append:", preview_append)
        self.assertEqual(before_append, "one\ntwo\ninserted\nthree\n")
        self.assertIn("Append:", appended)
        self.assertEqual(after_append, "one\ntwo\ninserted\nthree\ntail\n")
        self.assertIn("Usage: /replace-lines <path> <start> <end> <text>", bad_range)
        self.assertIn("end must be greater than or equal to start", bad_range)
        self.assertIn("Usage: /insert-lines <path> <line> <text>", bad_insert)
        self.assertIn("requires non-empty text", bad_insert)
        self.assertIn("Usage: /append <path> <text>", bad_append)
        self.assertIn("expected path and text", bad_append)

    def test_get_write_file_text_preview_and_apply_changes(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-commands-") as base:
            root = Path(base)
            note = root / "note.txt"

            preview_create = get_check_write_file_text(root, "note.txt 'hello\\n'")
            exists_after_preview = note.exists()
            created = get_write_file_text(root, "note.txt 'hello\\n'")
            after_create = note.read_text(encoding="utf-8")
            preview_replace = get_check_write_file_text(root, "note.txt 'bye\\n'")
            before_replace = note.read_text(encoding="utf-8")
            replaced = get_write_file_text(root, "note.txt 'bye\\n'")
            after_replace = note.read_text(encoding="utf-8")
            empty = get_write_file_text(root, "empty.txt ''")
            empty_text = (root / "empty.txt").read_text(encoding="utf-8")
            bad_usage = get_write_file_text(root, "note.txt")

        self.assertIn("Check write:", preview_create)
        self.assertIn(f"projectRoot: {root.resolve()}", preview_create)
        self.assertIn("ok: yes", preview_create)
        self.assertIn("path: note.txt", preview_create)
        self.assertIn("+hello", preview_create)
        self.assertFalse(exists_after_preview)
        self.assertIn("Write:", created)
        self.assertEqual(after_create, "hello\n")
        self.assertIn("Check write:", preview_replace)
        self.assertIn("-hello", preview_replace)
        self.assertIn("+bye", preview_replace)
        self.assertEqual(before_replace, "hello\n")
        self.assertIn("Write:", replaced)
        self.assertEqual(after_replace, "bye\n")
        self.assertIn("Write:", empty)
        self.assertEqual(empty_text, "")
        self.assertIn("Usage: /write <path> <text>", bad_usage)
        self.assertIn("expected path and text", bad_usage)

    def test_get_write_files_text_preview_and_apply_changes(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-commands-") as base:
            root = Path(base)
            first = root / "first.txt"
            second = root / "second.txt"

            preview_create = get_check_write_files_text(root, "first.txt 'hello\\n' second.txt 'world\\n'")
            first_exists_after_preview = first.exists()
            second_exists_after_preview = second.exists()
            created = get_write_files_text(root, files=["first.txt", "hello\\n", "second.txt", "world\\n"])
            first_after_create = first.read_text(encoding="utf-8")
            second_after_create = second.read_text(encoding="utf-8")
            preview_replace = get_check_write_files_text(root, "first.txt 'bye\\n' second.txt ''")
            first_before_replace = first.read_text(encoding="utf-8")
            replaced = get_write_files_text(root, "first.txt 'bye\\n' second.txt ''")
            first_after_replace = first.read_text(encoding="utf-8")
            second_after_replace = second.read_text(encoding="utf-8")
            bad_usage = get_write_files_text(root, "first.txt 'ok\\n' second.txt")
            protected_preview = get_check_write_files_text(root, ".vibeagent/blocked.txt secret")

        self.assertIn("Check write files:", preview_create)
        self.assertIn(f"projectRoot: {root.resolve()}", preview_create)
        self.assertIn("ok: yes", preview_create)
        self.assertIn("files: 2", preview_create)
        self.assertIn("first.txt: ok", preview_create)
        self.assertIn("+hello", preview_create)
        self.assertFalse(first_exists_after_preview)
        self.assertFalse(second_exists_after_preview)
        self.assertIn("Write files:", created)
        self.assertIn("ok: yes", created)
        self.assertEqual(first_after_create, "hello\n")
        self.assertEqual(second_after_create, "world\n")
        self.assertIn("Check write files:", preview_replace)
        self.assertIn("-hello", preview_replace)
        self.assertIn("+bye", preview_replace)
        self.assertEqual(first_before_replace, "hello\n")
        self.assertIn("Write files:", replaced)
        self.assertEqual(first_after_replace, "bye\n")
        self.assertEqual(second_after_replace, "")
        self.assertIn("Usage: /write-files <path> <text>...", bad_usage)
        self.assertIn("expected path and text pairs", bad_usage)
        self.assertIn("Check write files:", protected_preview)
        self.assertIn("ok: no", protected_preview)
        self.assertIn("Path is protected", protected_preview)

    def test_get_edit_file_text_preview_and_apply_changes(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-commands-") as base:
            root = Path(base)
            target = root / "app.py"
            target.write_text("value = 'old'\nprint(value)\n", encoding="utf-8")

            preview = get_check_edit_file_text(root, "app.py old new")
            content_after_preview = target.read_text(encoding="utf-8")
            edited = get_edit_file_text(root, "app.py old new")
            content_after_edit = target.read_text(encoding="utf-8")
            preview_delete = get_check_edit_file_text(root, "app.py \"print(value)\\n\" ''")
            content_after_delete_preview = target.read_text(encoding="utf-8")
            deleted = get_edit_file_text(root, "app.py \"print(value)\\n\" ''")
            content_after_delete = target.read_text(encoding="utf-8")
            missing_old = get_edit_file_text(root, "app.py missing replacement")
            empty_old = get_edit_file_text(root, "app.py '' replacement")
            bad_usage = get_edit_file_text(root, "app.py only-old")

        self.assertIn("Check edit:", preview)
        self.assertIn(f"projectRoot: {root.resolve()}", preview)
        self.assertIn("ok: yes", preview)
        self.assertIn("path: app.py", preview)
        self.assertIn("-value = 'old'", preview)
        self.assertIn("+value = 'new'", preview)
        self.assertEqual(content_after_preview, "value = 'old'\nprint(value)\n")
        self.assertIn("Edit:", edited)
        self.assertIn("ok: yes", edited)
        self.assertEqual(content_after_edit, "value = 'new'\nprint(value)\n")
        self.assertIn("Check edit:", preview_delete)
        self.assertIn("-print(value)", preview_delete)
        self.assertEqual(content_after_delete_preview, "value = 'new'\nprint(value)\n")
        self.assertIn("Edit:", deleted)
        self.assertEqual(content_after_delete, "value = 'new'\n")
        self.assertIn("Edit:", missing_old)
        self.assertIn("ok: no", missing_old)
        self.assertIn("Old text was not found", missing_old)
        self.assertIn("Usage: /edit <path> <old> <new>", empty_old)
        self.assertIn("requires non-empty old text", empty_old)
        self.assertIn("Usage: /edit <path> <old> <new>", bad_usage)
        self.assertIn("expected path, old text, and new text", bad_usage)

    def test_get_multi_edit_file_text_preview_and_apply_changes(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-commands-") as base:
            root = Path(base)
            target = root / "app.py"
            target.write_text("value = 'old'\nprint(value)\n", encoding="utf-8")

            preview = get_check_multi_edit_file_text(root, "app.py old new print log")
            content_after_preview = target.read_text(encoding="utf-8")
            edited = get_multi_edit_file_text(root, "app.py old new print log")
            content_after_edit = target.read_text(encoding="utf-8")
            preview_delete = get_check_multi_edit_file_text(root, "app.py \"log(value)\\n\" '' new final")
            content_after_delete_preview = target.read_text(encoding="utf-8")
            deleted = get_multi_edit_file_text(root, path="app.py", edits=["log(value)\n", "", "new", "final"])
            content_after_delete = target.read_text(encoding="utf-8")
            missing_old = get_multi_edit_file_text(root, "app.py missing replacement value ignored")
            empty_old = get_multi_edit_file_text(root, "app.py '' replacement")
            bad_usage = get_multi_edit_file_text(root, "app.py old new dangling")

        self.assertIn("Check multi edit:", preview)
        self.assertIn(f"projectRoot: {root.resolve()}", preview)
        self.assertIn("ok: yes", preview)
        self.assertIn("path: app.py", preview)
        self.assertIn("-value = 'old'", preview)
        self.assertIn("+log(value)", preview)
        self.assertEqual(content_after_preview, "value = 'old'\nprint(value)\n")
        self.assertIn("Multi edit:", edited)
        self.assertIn("ok: yes", edited)
        self.assertEqual(content_after_edit, "value = 'new'\nlog(value)\n")
        self.assertIn("Check multi edit:", preview_delete)
        self.assertIn("-log(value)", preview_delete)
        self.assertIn("+value = 'final'", preview_delete)
        self.assertEqual(content_after_delete_preview, "value = 'new'\nlog(value)\n")
        self.assertIn("Multi edit:", deleted)
        self.assertEqual(content_after_delete, "value = 'final'\n")
        self.assertIn("Multi edit:", missing_old)
        self.assertIn("ok: no", missing_old)
        self.assertIn("old text was not found", missing_old)
        self.assertIn("Usage: /multi-edit <path> <old> <new>...", empty_old)
        self.assertIn("requires non-empty old text", empty_old)
        self.assertIn("Usage: /multi-edit <path> <old> <new>...", bad_usage)
        self.assertIn("expected old/new pairs", bad_usage)

    def test_get_delete_file_text_preview_and_apply_changes(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-commands-") as base:
            root = Path(base)
            obsolete = root / "obsolete.py"
            obsolete.write_text("print('remove')\n", encoding="utf-8")
            protected = root / ".vibeagent" / "blocked.py"
            protected.parent.mkdir()
            protected.write_text("secret\n", encoding="utf-8")

            preview = get_check_delete_file_text(root, "obsolete.py")
            exists_after_preview = obsolete.exists()
            deleted = get_delete_file_text(root, "obsolete.py")
            exists_after_delete = obsolete.exists()
            missing = get_delete_file_text(root, "obsolete.py")
            bad_usage = get_delete_file_text(root, "obsolete.py extra.py")
            protected_preview = get_check_delete_file_text(root, ".vibeagent/blocked.py")

        self.assertIn("Check delete:", preview)
        self.assertIn(f"projectRoot: {root.resolve()}", preview)
        self.assertIn("ok: yes", preview)
        self.assertIn("path: obsolete.py", preview)
        self.assertIn("-print('remove')", preview)
        self.assertTrue(exists_after_preview)
        self.assertIn("Delete:", deleted)
        self.assertIn("ok: yes", deleted)
        self.assertIn("-print('remove')", deleted)
        self.assertFalse(exists_after_delete)
        self.assertIn("Delete:", missing)
        self.assertIn("ok: no", missing)
        self.assertIn("Usage: /delete <path>", bad_usage)
        self.assertIn("expected one path", bad_usage)
        self.assertIn("Check delete:", protected_preview)
        self.assertIn("ok: no", protected_preview)
        self.assertIn("Path is protected", protected_preview)

    def test_get_delete_files_text_preview_and_apply_changes(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-commands-") as base:
            root = Path(base)
            first = root / "first.py"
            second = root / "second.py"
            first.write_text("remove first\n", encoding="utf-8")
            second.write_text("remove second\n", encoding="utf-8")
            protected = root / ".vibeagent" / "blocked.py"
            protected.parent.mkdir()
            protected.write_text("secret\n", encoding="utf-8")

            preview = get_check_delete_files_text(root, "first.py second.py")
            exists_after_preview = [first.exists(), second.exists()]
            deleted = get_delete_files_text(root, paths=["first.py", "second.py"])
            exists_after_delete = [first.exists(), second.exists()]
            missing = get_delete_files_text(root, paths=["first.py", "missing.py"])
            bad_usage = get_delete_files_text(root)
            protected_preview = get_check_delete_files_text(root, ".vibeagent/blocked.py")

        self.assertIn("Check delete files:", preview)
        self.assertIn(f"projectRoot: {root.resolve()}", preview)
        self.assertIn("ok: yes", preview)
        self.assertIn("paths: 2", preview)
        self.assertIn("- first.py", preview)
        self.assertIn("- second.py", preview)
        self.assertIn("-remove first", preview)
        self.assertEqual(exists_after_preview, [True, True])
        self.assertIn("Delete files:", deleted)
        self.assertIn("ok: yes", deleted)
        self.assertEqual(exists_after_delete, [False, False])
        self.assertIn("Delete files:", missing)
        self.assertIn("ok: no", missing)
        self.assertIn("missing.py", missing)
        self.assertIn("Usage: /delete-files <path...>", bad_usage)
        self.assertIn("requires at least one path", bad_usage)
        self.assertIn("Check delete files:", protected_preview)
        self.assertIn("ok: no", protected_preview)
        self.assertIn("Path is protected", protected_preview)

    def test_get_move_and_copy_file_text_preview_and_apply_changes(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-commands-") as base:
            root = Path(base)
            (root / "src").mkdir()
            (root / "pkg").mkdir()
            source = root / "src" / "old.py"
            source.write_text("VALUE = 1\n", encoding="utf-8")
            template = root / "template.py"
            template.write_text("TEMPLATE = True\n", encoding="utf-8")

            move_preview = get_check_move_file_text(root, "src/old.py pkg/new.py")
            move_source_exists_after_preview = source.exists()
            move_destination_exists_after_preview = (root / "pkg" / "new.py").exists()
            moved = get_move_file_text(root, "src/old.py pkg/new.py")
            move_source_exists_after_apply = source.exists()
            moved_content = (root / "pkg" / "new.py").read_text(encoding="utf-8")
            copy_preview = get_check_copy_file_text(root, "template.py pkg/template_copy.py")
            copy_destination_exists_after_preview = (root / "pkg" / "template_copy.py").exists()
            copied = get_copy_file_text(root, "template.py pkg/template_copy.py")
            source_content_after_copy = template.read_text(encoding="utf-8")
            copied_content = (root / "pkg" / "template_copy.py").read_text(encoding="utf-8")
            bad_move = get_move_file_text(root, "pkg/new.py")
            missing_copy = get_copy_file_text(root, "missing.py pkg/missing.py")

        self.assertIn("Check move:", move_preview)
        self.assertIn(f"projectRoot: {root.resolve()}", move_preview)
        self.assertIn("ok: yes", move_preview)
        self.assertIn("source: src/old.py", move_preview)
        self.assertIn("destination: pkg/new.py", move_preview)
        self.assertTrue(move_source_exists_after_preview)
        self.assertFalse(move_destination_exists_after_preview)
        self.assertIn("Move:", moved)
        self.assertIn("ok: yes", moved)
        self.assertFalse(move_source_exists_after_apply)
        self.assertEqual(moved_content, "VALUE = 1\n")
        self.assertIn("Check copy:", copy_preview)
        self.assertIn("ok: yes", copy_preview)
        self.assertFalse(copy_destination_exists_after_preview)
        self.assertIn("Copy:", copied)
        self.assertEqual(source_content_after_copy, "TEMPLATE = True\n")
        self.assertEqual(copied_content, "TEMPLATE = True\n")
        self.assertIn("Usage: /move <source> <destination>", bad_move)
        self.assertIn("expected source and destination", bad_move)
        self.assertIn("Copy:", missing_copy)
        self.assertIn("ok: no", missing_copy)
        self.assertIn("missing.py", missing_copy)

    def test_get_move_and_copy_files_text_preview_and_apply_changes(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-commands-") as base:
            root = Path(base)
            (root / "pkg").mkdir()
            (root / "src").mkdir()
            (root / "src" / "old_a.py").write_text("A = 1\n", encoding="utf-8")
            (root / "src" / "old_b.py").write_text("B = 2\n", encoding="utf-8")
            (root / "template.py").write_text("TEMPLATE = True\n", encoding="utf-8")
            (root / "config.py").write_text("CONFIG = True\n", encoding="utf-8")

            move_preview = get_check_move_files_text(root, "src/old_a.py pkg/a.py src/old_b.py pkg/b.py")
            move_source_a_exists_after_preview = (root / "src" / "old_a.py").exists()
            move_destination_a_exists_after_preview = (root / "pkg" / "a.py").exists()
            moved = get_move_files_text(root, transfers=["src/old_a.py", "pkg/a.py", "src/old_b.py", "pkg/b.py"])
            move_source_a_exists_after_apply = (root / "src" / "old_a.py").exists()
            moved_a_content = (root / "pkg" / "a.py").read_text(encoding="utf-8")
            moved_b_content = (root / "pkg" / "b.py").read_text(encoding="utf-8")
            copy_preview = get_check_copy_files_text(root, "template.py pkg/template_copy.py config.py pkg/config_copy.py")
            copy_destination_exists_after_preview = (root / "pkg" / "template_copy.py").exists()
            copied = get_copy_files_text(root, transfers=["template.py", "pkg/template_copy.py", "config.py", "pkg/config_copy.py"])
            template_content_after_copy = (root / "template.py").read_text(encoding="utf-8")
            copied_template_content = (root / "pkg" / "template_copy.py").read_text(encoding="utf-8")
            copied_config_content = (root / "pkg" / "config_copy.py").read_text(encoding="utf-8")
            bad_move = get_move_files_text(root, "pkg/a.py pkg/a2.py extra.py")
            missing_copy = get_copy_files_text(root, "missing.py pkg/missing.py template.py pkg/template_again.py")

        self.assertIn("Check move files:", move_preview)
        self.assertIn(f"projectRoot: {root.resolve()}", move_preview)
        self.assertIn("ok: yes", move_preview)
        self.assertIn("transfers: 2", move_preview)
        self.assertIn("src/old_a.py -> pkg/a.py", move_preview)
        self.assertTrue(move_source_a_exists_after_preview)
        self.assertFalse(move_destination_a_exists_after_preview)
        self.assertIn("Move files:", moved)
        self.assertIn("ok: yes", moved)
        self.assertFalse(move_source_a_exists_after_apply)
        self.assertEqual(moved_a_content, "A = 1\n")
        self.assertEqual(moved_b_content, "B = 2\n")
        self.assertIn("Check copy files:", copy_preview)
        self.assertIn("ok: yes", copy_preview)
        self.assertIn("template.py -> pkg/template_copy.py", copy_preview)
        self.assertFalse(copy_destination_exists_after_preview)
        self.assertIn("Copy files:", copied)
        self.assertIn("transfers: 2", copied)
        self.assertEqual(template_content_after_copy, "TEMPLATE = True\n")
        self.assertEqual(copied_template_content, "TEMPLATE = True\n")
        self.assertEqual(copied_config_content, "CONFIG = True\n")
        self.assertIn("Usage: /move-files <source> <destination>...", bad_move)
        self.assertIn("expected source and destination pairs", bad_move)
        self.assertIn("Copy files:", missing_copy)
        self.assertIn("ok: no", missing_copy)
        self.assertIn("missing.py", missing_copy)

    def test_get_move_and_copy_dir_text_preview_and_apply_changes(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-commands-") as base:
            root = Path(base)
            (root / "pkg").mkdir()
            (root / "old_pkg").mkdir()
            (root / "old_pkg" / "module.py").write_text("VALUE = 1\n", encoding="utf-8")
            (root / "template_pkg").mkdir()
            (root / "template_pkg" / "module.py").write_text("TEMPLATE = True\n", encoding="utf-8")

            move_preview = get_check_move_dir_text(root, "old_pkg pkg/new_pkg")
            move_source_exists_after_preview = (root / "old_pkg").is_dir()
            move_destination_exists_after_preview = (root / "pkg" / "new_pkg").exists()
            moved = get_move_dir_text(root, "old_pkg pkg/new_pkg")
            move_source_exists_after_apply = (root / "old_pkg").exists()
            moved_content = (root / "pkg" / "new_pkg" / "module.py").read_text(encoding="utf-8")
            copy_preview = get_check_copy_dir_text(root, "template_pkg pkg/template_copy")
            copy_destination_exists_after_preview = (root / "pkg" / "template_copy").exists()
            copied = get_copy_dir_text(root, "template_pkg pkg/template_copy")
            source_content_after_copy = (root / "template_pkg" / "module.py").read_text(encoding="utf-8")
            copied_content = (root / "pkg" / "template_copy" / "module.py").read_text(encoding="utf-8")
            bad_move = get_move_dir_text(root, "pkg/new_pkg")
            missing_copy = get_copy_dir_text(root, "missing_pkg pkg/missing_pkg")

        self.assertIn("Check move dir:", move_preview)
        self.assertIn(f"projectRoot: {root.resolve()}", move_preview)
        self.assertIn("ok: yes", move_preview)
        self.assertIn("source: old_pkg", move_preview)
        self.assertIn("destination: pkg/new_pkg", move_preview)
        self.assertTrue(move_source_exists_after_preview)
        self.assertFalse(move_destination_exists_after_preview)
        self.assertIn("Move dir:", moved)
        self.assertIn("ok: yes", moved)
        self.assertFalse(move_source_exists_after_apply)
        self.assertEqual(moved_content, "VALUE = 1\n")
        self.assertIn("Check copy dir:", copy_preview)
        self.assertIn("ok: yes", copy_preview)
        self.assertFalse(copy_destination_exists_after_preview)
        self.assertIn("Copy dir:", copied)
        self.assertEqual(source_content_after_copy, "TEMPLATE = True\n")
        self.assertEqual(copied_content, "TEMPLATE = True\n")
        self.assertIn("Usage: /move-dir <source> <destination>", bad_move)
        self.assertIn("expected source and destination", bad_move)
        self.assertIn("Copy dir:", missing_copy)
        self.assertIn("ok: no", missing_copy)
        self.assertIn("missing_pkg", missing_copy)

    def test_get_move_and_copy_dirs_text_preview_and_apply_changes(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-commands-") as base:
            root = Path(base)
            (root / "pkg").mkdir()
            for name, content in (("old_a", "A = 1\n"), ("old_b", "B = 2\n"), ("template_a", "TA = True\n"), ("template_b", "TB = True\n")):
                directory = root / name
                directory.mkdir()
                (directory / "module.py").write_text(content, encoding="utf-8")

            move_preview = get_check_move_dirs_text(root, "old_a pkg/a old_b pkg/b")
            move_source_a_exists_after_preview = (root / "old_a").is_dir()
            move_destination_a_exists_after_preview = (root / "pkg" / "a").exists()
            moved = get_move_dirs_text(root, transfers=["old_a", "pkg/a", "old_b", "pkg/b"])
            move_source_a_exists_after_apply = (root / "old_a").exists()
            moved_a_content = (root / "pkg" / "a" / "module.py").read_text(encoding="utf-8")
            moved_b_content = (root / "pkg" / "b" / "module.py").read_text(encoding="utf-8")
            copy_preview = get_check_copy_dirs_text(root, "template_a pkg/template_a_copy template_b pkg/template_b_copy")
            copy_destination_exists_after_preview = (root / "pkg" / "template_a_copy").exists()
            copied = get_copy_dirs_text(root, transfers=["template_a", "pkg/template_a_copy", "template_b", "pkg/template_b_copy"])
            template_a_content_after_copy = (root / "template_a" / "module.py").read_text(encoding="utf-8")
            copied_template_a_content = (root / "pkg" / "template_a_copy" / "module.py").read_text(encoding="utf-8")
            copied_template_b_content = (root / "pkg" / "template_b_copy" / "module.py").read_text(encoding="utf-8")
            bad_move = get_move_dirs_text(root, "pkg/a pkg/a2 extra")
            missing_copy = get_copy_dirs_text(root, "missing_dir pkg/missing_dir template_a pkg/template_again")

        self.assertIn("Check move dirs:", move_preview)
        self.assertIn(f"projectRoot: {root.resolve()}", move_preview)
        self.assertIn("ok: yes", move_preview)
        self.assertIn("transfers: 2", move_preview)
        self.assertIn("old_a -> pkg/a", move_preview)
        self.assertTrue(move_source_a_exists_after_preview)
        self.assertFalse(move_destination_a_exists_after_preview)
        self.assertIn("Move dirs:", moved)
        self.assertIn("ok: yes", moved)
        self.assertFalse(move_source_a_exists_after_apply)
        self.assertEqual(moved_a_content, "A = 1\n")
        self.assertEqual(moved_b_content, "B = 2\n")
        self.assertIn("Check copy dirs:", copy_preview)
        self.assertIn("ok: yes", copy_preview)
        self.assertIn("template_a -> pkg/template_a_copy", copy_preview)
        self.assertFalse(copy_destination_exists_after_preview)
        self.assertIn("Copy dirs:", copied)
        self.assertIn("transfers: 2", copied)
        self.assertEqual(template_a_content_after_copy, "TA = True\n")
        self.assertEqual(copied_template_a_content, "TA = True\n")
        self.assertEqual(copied_template_b_content, "TB = True\n")
        self.assertIn("Usage: /move-dirs <source> <destination>...", bad_move)
        self.assertIn("expected source and destination pairs", bad_move)
        self.assertIn("Copy dirs:", missing_copy)
        self.assertIn("ok: no", missing_copy)
        self.assertIn("missing_dir", missing_copy)

    def test_get_directory_text_preview_and_apply_changes(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-commands-") as base:
            root = Path(base)
            (root / "nonempty").mkdir()
            (root / "nonempty" / "file.txt").write_text("data\n", encoding="utf-8")

            mkdir_preview = get_check_create_dir_text(root, "pkg/generated")
            exists_after_mkdir_preview = (root / "pkg" / "generated").exists()
            mkdir = get_create_dir_text(root, "pkg/generated")
            exists_after_mkdir = (root / "pkg" / "generated").is_dir()
            rmdir_preview = get_check_delete_empty_dir_text(root, "pkg/generated")
            exists_after_rmdir_preview = (root / "pkg" / "generated").is_dir()
            rmdir = get_delete_empty_dir_text(root, "pkg/generated")
            exists_after_rmdir = (root / "pkg" / "generated").exists()
            bad_mkdir = get_create_dir_text(root, "pkg/generated extra")
            nonempty_rmdir = get_delete_empty_dir_text(root, "nonempty")
            protected_mkdir = get_check_create_dir_text(root, ".vibeagent/newdir")

        self.assertIn("Check mkdir:", mkdir_preview)
        self.assertIn(f"projectRoot: {root.resolve()}", mkdir_preview)
        self.assertIn("ok: yes", mkdir_preview)
        self.assertIn("path: pkg/generated", mkdir_preview)
        self.assertFalse(exists_after_mkdir_preview)
        self.assertIn("Mkdir:", mkdir)
        self.assertIn("ok: yes", mkdir)
        self.assertTrue(exists_after_mkdir)
        self.assertIn("Check rmdir:", rmdir_preview)
        self.assertIn("ok: yes", rmdir_preview)
        self.assertTrue(exists_after_rmdir_preview)
        self.assertIn("Rmdir:", rmdir)
        self.assertIn("ok: yes", rmdir)
        self.assertFalse(exists_after_rmdir)
        self.assertIn("Usage: /mkdir <path>", bad_mkdir)
        self.assertIn("expected one path", bad_mkdir)
        self.assertIn("Rmdir:", nonempty_rmdir)
        self.assertIn("ok: no", nonempty_rmdir)
        self.assertIn("not empty", nonempty_rmdir)
        self.assertIn("Check mkdir:", protected_mkdir)
        self.assertIn("ok: no", protected_mkdir)
        self.assertIn("Path is protected", protected_mkdir)

    def test_get_batch_directory_text_preview_and_apply_changes(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-commands-") as base:
            root = Path(base)
            (root / "nonempty").mkdir()
            (root / "nonempty" / "file.txt").write_text("data\n", encoding="utf-8")

            mkdirs_preview = get_check_create_dirs_text(root, "pkg/generated assets/icons")
            mkdirs_exist_after_preview = [(root / "pkg" / "generated").exists(), (root / "assets" / "icons").exists()]
            mkdirs = get_create_dirs_text(root, paths=["pkg/generated", "assets/icons"])
            mkdirs_exist_after_apply = [(root / "pkg" / "generated").is_dir(), (root / "assets" / "icons").is_dir()]
            rmdirs_preview = get_check_delete_empty_dirs_text(root, "pkg/generated assets/icons")
            rmdirs_exist_after_preview = [(root / "pkg" / "generated").is_dir(), (root / "assets" / "icons").is_dir()]
            rmdirs = get_delete_empty_dirs_text(root, paths=["pkg/generated", "assets/icons"])
            rmdirs_exist_after_apply = [(root / "pkg" / "generated").exists(), (root / "assets" / "icons").exists()]
            bad_mkdirs = get_create_dirs_text(root)
            nonempty_rmdirs = get_delete_empty_dirs_text(root, "nonempty missing")
            protected_mkdirs = get_check_create_dirs_text(root, ".vibeagent/newdir")

        self.assertIn("Check mkdirs:", mkdirs_preview)
        self.assertIn(f"projectRoot: {root.resolve()}", mkdirs_preview)
        self.assertIn("ok: yes", mkdirs_preview)
        self.assertIn("paths: 2", mkdirs_preview)
        self.assertIn("- pkg/generated", mkdirs_preview)
        self.assertIn("- assets/icons", mkdirs_preview)
        self.assertEqual(mkdirs_exist_after_preview, [False, False])
        self.assertIn("Mkdirs:", mkdirs)
        self.assertIn("ok: yes", mkdirs)
        self.assertEqual(mkdirs_exist_after_apply, [True, True])
        self.assertIn("Check rmdirs:", rmdirs_preview)
        self.assertIn("ok: yes", rmdirs_preview)
        self.assertEqual(rmdirs_exist_after_preview, [True, True])
        self.assertIn("Rmdirs:", rmdirs)
        self.assertIn("ok: yes", rmdirs)
        self.assertEqual(rmdirs_exist_after_apply, [False, False])
        self.assertIn("Usage: /mkdirs <path...>", bad_mkdirs)
        self.assertIn("requires at least one path", bad_mkdirs)
        self.assertIn("Rmdirs:", nonempty_rmdirs)
        self.assertIn("ok: no", nonempty_rmdirs)
        self.assertIn("missing", nonempty_rmdirs)
        self.assertIn("Check mkdirs:", protected_mkdirs)
        self.assertIn("ok: no", protected_mkdirs)
        self.assertIn("Path is protected", protected_mkdirs)

    def test_get_executable_text_preview_and_apply_changes(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-commands-") as base:
            root = Path(base)
            script = root / "tool.sh"
            script.write_text("#!/bin/sh\necho hi\n", encoding="utf-8")
            script.chmod(0o644)

            preview = get_check_set_executable_text(root, "tool.sh true")
            mode_after_preview = script.stat().st_mode
            applied = get_set_executable_text(root, "tool.sh true")
            mode_after_apply = script.stat().st_mode
            unset_preview = get_check_set_executable_text(root, "tool.sh false")
            mode_after_unset_preview = script.stat().st_mode
            unset = get_set_executable_text(root, "tool.sh false")
            mode_after_unset = script.stat().st_mode
            default_true = get_check_set_executable_text(root, "tool.sh")
            bad_bool = get_check_set_executable_text(root, "tool.sh maybe")
            bad_usage = get_set_executable_text(root, "tool.sh true extra")
            protected_preview = get_check_set_executable_text(root, ".vibeagent/blocked.sh true")

        self.assertIn("Check executable:", preview)
        self.assertIn(f"projectRoot: {root.resolve()}", preview)
        self.assertIn("ok: yes", preview)
        self.assertIn("path: tool.sh", preview)
        self.assertIn("executable: yes", preview)
        self.assertIn("modeBefore:", preview)
        self.assertIn("modeAfter:", preview)
        self.assertFalse(mode_after_preview & 0o111)
        self.assertIn("Set executable:", applied)
        self.assertIn("ok: yes", applied)
        self.assertTrue(mode_after_apply & 0o111)
        self.assertIn("Check executable:", unset_preview)
        self.assertIn("executable: no", unset_preview)
        self.assertTrue(mode_after_unset_preview & 0o111)
        self.assertIn("Set executable:", unset)
        self.assertFalse(mode_after_unset & 0o111)
        self.assertIn("executable: yes", default_true)
        self.assertIn("Usage: /check-executable <path> [true|false]", bad_bool)
        self.assertIn("executable must be true or false", bad_bool)
        self.assertIn("Usage: /set-executable <path> [true|false]", bad_usage)
        self.assertIn("expected path and optional executable value", bad_usage)
        self.assertIn("Check executable:", protected_preview)
        self.assertIn("ok: no", protected_preview)
        self.assertIn("Path is protected", protected_preview)

    def test_get_patch_text_preview_and_apply_changes(self) -> None:
        patch_text = "@@ -1 +1 @@\\n-name = 'old'\\n+name = 'new'\\n"
        with tempfile.TemporaryDirectory(prefix="vibeagent-commands-") as base:
            root = Path(base)
            app = root / "app.py"
            app.write_text("name = 'old'\n", encoding="utf-8")

            preview = get_check_patch_text(root, f"app.py \"{patch_text}\"")
            content_after_preview = app.read_text(encoding="utf-8")
            applied = get_patch_text(root, path="app.py", patch=patch_text)
            content_after_apply = app.read_text(encoding="utf-8")
            invalid = get_check_patch_text(root, "app.py '@@ -1 +1 @@\\n-missing\\n+new\\n'")
            bad_usage = get_patch_text(root, "app.py")
            protected = get_check_patch_text(root, ".vibeagent/blocked.py '@@ -1 +1 @@\\n-a\\n+b\\n'")

        self.assertIn("Check patch:", preview)
        self.assertIn(f"projectRoot: {root.resolve()}", preview)
        self.assertIn("ok: yes", preview)
        self.assertIn("path: app.py", preview)
        self.assertIn("diff:", preview)
        self.assertIn("+name = 'new'", preview)
        self.assertEqual(content_after_preview, "name = 'old'\n")
        self.assertIn("Patch:", applied)
        self.assertIn("ok: yes", applied)
        self.assertEqual(content_after_apply, "name = 'new'\n")
        self.assertIn("Check patch:", invalid)
        self.assertIn("ok: no", invalid)
        self.assertIn("context did not match", invalid)
        self.assertIn("Usage: /patch <path> <patch|->", bad_usage)
        self.assertIn("expected path and patch", bad_usage)
        self.assertIn("Check patch:", protected)
        self.assertIn("ok: no", protected)
        self.assertIn("Path is protected", protected)

    def test_get_patches_text_preview_and_apply_changes(self) -> None:
        patch_text = (
            "--- a/app.py\\n"
            "+++ b/app.py\\n"
            "@@ -1 +1 @@\\n"
            "-name = 'old'\\n"
            "+name = 'new'\\n"
            "--- a/config.py\\n"
            "+++ b/config.py\\n"
            "@@ -1 +1 @@\\n"
            "-debug = False\\n"
            "+debug = True\\n"
        )
        with tempfile.TemporaryDirectory(prefix="vibeagent-commands-") as base:
            root = Path(base)
            app = root / "app.py"
            config = root / "config.py"
            app.write_text("name = 'old'\n", encoding="utf-8")
            config.write_text("debug = False\n", encoding="utf-8")

            preview = get_check_patches_text(root, f"\"{patch_text}\"")
            app_after_preview = app.read_text(encoding="utf-8")
            config_after_preview = config.read_text(encoding="utf-8")
            applied = get_patches_text(root, patch=patch_text)
            app_after_apply = app.read_text(encoding="utf-8")
            config_after_apply = config.read_text(encoding="utf-8")
            invalid = get_check_patches_text(root, "'@@ -1 +1 @@\\n-old\\n+new\\n'")
            bad_usage = get_patches_text(root)
            protected = get_check_patches_text(root, "'--- a/.vibeagent/blocked.py\\n+++ b/.vibeagent/blocked.py\\n@@ -1 +1 @@\\n-a\\n+b\\n'")

        self.assertIn("Check patches:", preview)
        self.assertIn(f"projectRoot: {root.resolve()}", preview)
        self.assertIn("ok: yes", preview)
        self.assertIn("files: 2", preview)
        self.assertIn("paths:", preview)
        self.assertIn("- app.py", preview)
        self.assertIn("- config.py", preview)
        self.assertIn("+debug = True", preview)
        self.assertEqual(app_after_preview, "name = 'old'\n")
        self.assertEqual(config_after_preview, "debug = False\n")
        self.assertIn("Patches:", applied)
        self.assertIn("ok: yes", applied)
        self.assertEqual(app_after_apply, "name = 'new'\n")
        self.assertEqual(config_after_apply, "debug = True\n")
        self.assertIn("Check patches:", invalid)
        self.assertIn("ok: no", invalid)
        self.assertIn("file headers", invalid)
        self.assertIn("Usage: /patches <patch|->", bad_usage)
        self.assertIn("requires a patch", bad_usage)
        self.assertIn("Check patches:", protected)
        self.assertIn("ok: no", protected)
        self.assertIn("Path is protected", protected)

    def test_get_regex_replace_text_preview_and_apply_changes(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-commands-") as base:
            root = Path(base)
            app = root / "app.py"
            app.write_text("alpha beta\nAlpha beta\nalpha beta\n", encoding="utf-8")

            preview = get_check_regex_replace_text(root, "--ignore-case --count 2 app.py alpha gamma")
            before = app.read_text(encoding="utf-8")
            applied = get_regex_replace_text(root, "--ignore-case --count 2 app.py alpha gamma")
            after = app.read_text(encoding="utf-8")
            multiline_preview = get_check_regex_replace_text(root, "--multiline app.py '^gamma' 'start'")
            bad_pattern = get_regex_replace_text(root, "app.py '(' new")
            bad_count = get_check_regex_replace_text(root, "--count nope app.py old new")
            bad_usage = get_regex_replace_text(root, "app.py old")

        self.assertIn("Check regex replace:", preview)
        self.assertIn(f"projectRoot: {root.resolve()}", preview)
        self.assertIn("ok: yes", preview)
        self.assertIn("pattern: alpha", preview)
        self.assertIn("count: 2", preview)
        self.assertIn("replacements: 2", preview)
        self.assertIn("+gamma beta", preview)
        self.assertEqual(before, "alpha beta\nAlpha beta\nalpha beta\n")
        self.assertIn("Regex replace:", applied)
        self.assertEqual(after, "gamma beta\ngamma beta\nalpha beta\n")
        self.assertIn("Check regex replace:", multiline_preview)
        self.assertIn("ok: yes", multiline_preview)
        self.assertIn("Regex replace:", bad_pattern)
        self.assertIn("ok: no", bad_pattern)
        self.assertIn("Invalid regex pattern", bad_pattern)
        self.assertIn("Usage: /check-regex-replace [--ignore-case] [--multiline] [--count N] [--max-replacements N] <path> <pattern> <replacement>", bad_count)
        self.assertIn("count must be a non-negative integer", bad_count)
        self.assertIn("Usage: /regex-replace [--ignore-case] [--multiline] [--count N] [--max-replacements N] <path> <pattern> <replacement>", bad_usage)
        self.assertIn("expected path, pattern, and replacement", bad_usage)

    def test_get_code_deps_text_reports_non_python_imports(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-commands-") as base:
            root = Path(base)
            (root / "web").mkdir()
            (root / "web" / "app.ts").write_text("import React from 'react';\nexport { helper } from './helper';\n", encoding="utf-8")
            (root / "web" / "helper.ts").write_text("export const helper = 1;\n", encoding="utf-8")
            (root / "pkg").mkdir()
            (root / "pkg" / "app.py").write_text("import os\n", encoding="utf-8")

            text = get_code_deps_text(root, "web")
            usage = get_code_deps_text(root, "web extra")

        self.assertIn("Code dependencies:", text)
        self.assertIn(f"projectRoot: {root.resolve()}", text)
        self.assertIn("ok: yes", text)
        self.assertIn("path: web", text)
        self.assertIn("files: 2/2", text)
        self.assertIn("web/app.ts (typescript): ok", text)
        self.assertIn("dependencies: ./helper, react", text)
        self.assertIn("line 1 import: react", text)
        self.assertIn("line 2 export: ./helper", text)
        self.assertIn("web/helper.ts (typescript): ok", text)
        self.assertNotIn("pkg/app.py", text)
        self.assertIn("Usage: /code-deps [path]", usage)
        self.assertIn("expected at most one path", usage)

    def test_get_code_refs_and_defs_text_report_non_python_matches(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-commands-") as base:
            root = Path(base)
            (root / "web").mkdir()
            (root / "web" / "app.ts").write_text(
                "export function runAgent() {\n"
                "  return helper();\n"
                "}\n"
                "runAgent();\n",
                encoding="utf-8",
            )
            (root / "web" / "helper.ts").write_text("export const helper = () => 1;\n", encoding="utf-8")
            (root / "pkg").mkdir()
            (root / "pkg" / "app.py").write_text("def runAgent():\n    pass\n", encoding="utf-8")

            refs_text = get_code_refs_text(root, "runAgent web")
            ref_contexts_text = get_code_ref_contexts_text(root, "runAgent web", max_matches=1, context_lines=1, max_bytes_per_context=1000)
            defs_text = get_code_defs_text(root, "runAgent web")
            rename_preview_text = get_code_rename_preview_text(root, "runAgent executeAgent web", max_replacements=1)
            before_rename = (root / "web" / "app.ts").read_text(encoding="utf-8")
            rename_text = get_code_rename_text(root, "runAgent executeAgent web")
            after_rename = (root / "web" / "app.ts").read_text(encoding="utf-8")
            python_content = (root / "pkg" / "app.py").read_text(encoding="utf-8")
            flag_refs_text = get_code_refs_text(root, symbol="helper", path="web")
            missing_usage = get_code_refs_text(root)
            missing_context_usage = get_code_ref_contexts_text(root)
            missing_rename_usage = get_code_rename_preview_text(root)
            too_many_usage = get_code_defs_text(root, "runAgent web extra")

        self.assertIn("Code references:", refs_text)
        self.assertIn(f"projectRoot: {root.resolve()}", refs_text)
        self.assertIn("symbol: runAgent", refs_text)
        self.assertIn("path: web", refs_text)
        self.assertIn("references: 2/2", refs_text)
        self.assertIn("web/app.ts:1", refs_text)
        self.assertIn("web/app.ts:4", refs_text)
        self.assertNotIn("pkg/app.py", refs_text)
        self.assertIn("Code reference contexts:", ref_contexts_text)
        self.assertIn("contexts: 1/2", ref_contexts_text)
        self.assertIn("truncated: yes", ref_contexts_text)
        self.assertIn("contextLines: 1", ref_contexts_text)
        self.assertIn("web/app.ts:1", ref_contexts_text)
        self.assertIn("return helper", ref_contexts_text)
        self.assertIn("Code definitions:", defs_text)
        self.assertIn("definitions: 1/1", defs_text)
        self.assertIn("web/app.ts:1", defs_text)
        self.assertIn("function runAgent", defs_text)
        self.assertIn("Code rename preview:", rename_preview_text)
        self.assertIn("rename: runAgent -> executeAgent", rename_preview_text)
        self.assertIn("replacements: 2", rename_preview_text)
        self.assertIn("truncated: yes", rename_preview_text)
        self.assertIn("-export function runAgent", rename_preview_text)
        self.assertIn("runAgent", before_rename)
        self.assertIn("Code rename:", rename_text)
        self.assertIn("rename: runAgent -> executeAgent", rename_text)
        self.assertIn("executeAgent", after_rename)
        self.assertNotIn("runAgent", after_rename)
        self.assertIn("def runAgent", python_content)
        self.assertIn("symbol: helper", flag_refs_text)
        self.assertIn("Usage: /code-refs <symbol> [path]", missing_usage)
        self.assertIn("requires a symbol", missing_usage)
        self.assertIn("Usage: /code-ref-contexts <symbol> [path]", missing_context_usage)
        self.assertIn("Usage: /code-rename-preview <symbol> <new_name> [path]", missing_rename_usage)
        self.assertIn("Usage: /code-defs <symbol> [path]", too_many_usage)
        self.assertIn("expected a symbol and optional path", too_many_usage)

    def test_get_branches_text_reports_current_and_local_branches(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-commands-") as base:
            root = Path(base)
            subprocess.run(["git", "init"], cwd=root, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            (root / "app.py").write_text("print('ok')\n", encoding="utf-8")
            subprocess.run(["git", "add", "app.py"], cwd=root, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            subprocess.run(
                ["git", "-c", "user.name=Test", "-c", "user.email=test@example.com", "commit", "-m", "initial"],
                cwd=root,
                check=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
            subprocess.run(["git", "branch", "-M", "main"], cwd=root, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            subprocess.run(["git", "branch", "feature/work"], cwd=root, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

            text = get_branches_text(root)

        self.assertIn("Branches:", text)
        self.assertIn(f"projectRoot: {root.resolve()}", text)
        self.assertIn("ok: yes", text)
        self.assertIn("current: main", text)
        self.assertIn("branches: 2/2", text)
        self.assertIn("* main", text)
        self.assertIn("- feature/work", text)
        self.assertIn("Found 2 local git branch(es).", text)

    def test_get_log_text_reports_recent_commits_and_path_scope(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-commands-") as base:
            root = Path(base)
            subprocess.run(["git", "init"], cwd=root, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            subprocess.run(["git", "config", "user.name", "Test"], cwd=root, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=root, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            (root / "app.py").write_text("print('one')\n", encoding="utf-8")
            subprocess.run(["git", "add", "app.py"], cwd=root, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            subprocess.run(["git", "commit", "-m", "initial app"], cwd=root, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            (root / "other.py").write_text("print('two')\n", encoding="utf-8")
            subprocess.run(["git", "add", "other.py"], cwd=root, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            subprocess.run(["git", "commit", "-m", "add other"], cwd=root, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

            text = get_log_text(root, max_count=2)
            scoped = get_log_text(root, "app.py 1")
            invalid = get_log_text(root, "../outside.py")

        self.assertIn("Log:", text)
        self.assertIn(f"projectRoot: {root.resolve()}", text)
        self.assertIn("ok: yes", text)
        self.assertIn("path: .", text)
        self.assertIn("maxCount: 2", text)
        self.assertIn("add other", text)
        self.assertIn("initial app", text)
        self.assertIn("path: app.py", scoped)
        self.assertIn("maxCount: 1", scoped)
        self.assertIn("initial app", scoped)
        self.assertNotIn("add other", scoped)
        self.assertIn("ok: no", invalid)
        self.assertIn("escapes", invalid)

    def test_get_show_text_reports_revision_patch_and_rejects_unsafe_inputs(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-commands-") as base:
            root = Path(base)
            subprocess.run(["git", "init"], cwd=root, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            subprocess.run(["git", "config", "user.name", "Test"], cwd=root, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=root, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            (root / "app.py").write_text("print('one')\n", encoding="utf-8")
            subprocess.run(["git", "add", "app.py"], cwd=root, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            subprocess.run(["git", "commit", "-m", "initial app"], cwd=root, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            (root / "app.py").write_text("print('two')\n", encoding="utf-8")
            subprocess.run(["git", "add", "app.py"], cwd=root, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            subprocess.run(["git", "commit", "-m", "update app"], cwd=root, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

            text = get_show_text(root, "HEAD app.py")
            invalid_rev = get_show_text(root, "--stat")
            invalid_path = get_show_text(root, "HEAD ../outside.py")

        self.assertIn("Show:", text)
        self.assertIn(f"projectRoot: {root.resolve()}", text)
        self.assertIn("ok: yes", text)
        self.assertIn("rev: HEAD", text)
        self.assertIn("path: app.py", text)
        self.assertIn("update app", text)
        self.assertIn("-print('one')", text)
        self.assertIn("+print('two')", text)
        self.assertIn("ok: no", invalid_rev)
        self.assertIn("must not start", invalid_rev)
        self.assertIn("ok: no", invalid_path)
        self.assertIn("escapes", invalid_path)

    def test_get_blame_text_reports_line_range_and_rejects_unsafe_paths(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-commands-") as base:
            root = Path(base)
            subprocess.run(["git", "init"], cwd=root, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            subprocess.run(["git", "config", "user.name", "Test"], cwd=root, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=root, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            (root / "app.py").write_text("alpha\nbeta\n", encoding="utf-8")
            subprocess.run(["git", "add", "app.py"], cwd=root, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            subprocess.run(["git", "commit", "-m", "initial app"], cwd=root, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            (root / "app.py").write_text("alpha\nbeta changed\n", encoding="utf-8")
            subprocess.run(["git", "add", "app.py"], cwd=root, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            subprocess.run(["git", "commit", "-m", "update beta"], cwd=root, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

            text = get_blame_text(root, "app.py 2:2")
            invalid = get_blame_text(root, "../outside.py")
            usage = get_blame_text(root)

        self.assertIn("Blame:", text)
        self.assertIn(f"projectRoot: {root.resolve()}", text)
        self.assertIn("ok: yes", text)
        self.assertIn("path: app.py", text)
        self.assertIn("range: 2:2", text)
        self.assertIn("beta changed", text)
        self.assertNotIn("alpha", text)
        self.assertIn("ok: no", invalid)
        self.assertIn("escapes", invalid)
        self.assertEqual(usage, "Usage: /blame <path> [start[:end]]")

    def test_get_stashes_text_reports_local_stash_entries(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-commands-") as base:
            root = Path(base)
            subprocess.run(["git", "init"], cwd=root, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            subprocess.run(["git", "config", "user.name", "Test"], cwd=root, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=root, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            (root / "app.py").write_text("print('one')\n", encoding="utf-8")
            subprocess.run(["git", "add", "app.py"], cwd=root, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            subprocess.run(["git", "commit", "-m", "initial app"], cwd=root, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            (root / "app.py").write_text("print('stash')\n", encoding="utf-8")
            subprocess.run(["git", "stash", "push", "-m", "save local app"], cwd=root, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

            text = get_stashes_text(root)
            limited = get_stashes_text(root, "1")
            invalid = get_stashes_text(root, "many")

        self.assertIn("Stashes:", text)
        self.assertIn(f"projectRoot: {root.resolve()}", text)
        self.assertIn("ok: yes", text)
        self.assertIn("entries: 1/1", text)
        self.assertIn("stash@{0}", text)
        self.assertIn("save local app", text)
        self.assertIn("maxEntries: 1", limited)
        self.assertIn("Usage: /stashes [count]", invalid)
        self.assertIn("invalid count", invalid)

    def test_get_git_status_text_reports_short_status(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-commands-") as base:
            base_path = Path(base)
            root = base_path / "work"
            not_repo = base_path / "not-a-repo"
            root.mkdir()
            not_repo.mkdir()
            subprocess.run(["git", "init", "--initial-branch", "main"], cwd=root, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            subprocess.run(["git", "config", "user.name", "Test"], cwd=root, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=root, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            (root / "app.txt").write_text("base\n", encoding="utf-8")
            subprocess.run(["git", "add", "app.txt"], cwd=root, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            subprocess.run(["git", "commit", "-m", "initial"], cwd=root, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            (root / "app.txt").write_text("changed\n", encoding="utf-8")

            text = get_git_status_text(root)
            outside = get_git_status_text(not_repo)

        self.assertIn("Git status:", text)
        self.assertIn(f"projectRoot: {root.resolve()}", text)
        self.assertIn("ok: yes", text)
        self.assertIn("status:", text)
        self.assertIn("M app.txt", text)
        self.assertIn("ok: no", outside)

    def test_get_git_conflicts_text_reports_unmerged_files_and_markers(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-commands-") as base:
            root = Path(base)
            subprocess.run(["git", "init", "--initial-branch", "main"], cwd=root, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            subprocess.run(["git", "config", "user.name", "Test"], cwd=root, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=root, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            (root / "app.txt").write_text("base\n", encoding="utf-8")
            subprocess.run(["git", "add", "app.txt"], cwd=root, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            subprocess.run(["git", "commit", "-m", "initial"], cwd=root, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            subprocess.run(["git", "switch", "-c", "feature"], cwd=root, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            (root / "app.txt").write_text("feature\n", encoding="utf-8")
            subprocess.run(["git", "commit", "-am", "feature"], cwd=root, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            subprocess.run(["git", "switch", "main"], cwd=root, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            (root / "app.txt").write_text("main\n", encoding="utf-8")
            subprocess.run(["git", "commit", "-am", "main"], cwd=root, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            subprocess.run(["git", "merge", "feature"], cwd=root, check=False, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

            text = get_git_conflicts_text(root, "app.txt")
            invalid = get_git_conflicts_text(root, "app.txt other.txt")

        self.assertIn("Git conflicts:", text)
        self.assertIn(f"projectRoot: {root.resolve()}", text)
        self.assertIn("ok: yes", text)
        self.assertIn("path: app.txt", text)
        self.assertIn("unmerged: 1/1", text)
        self.assertIn("markers: 3/3", text)
        self.assertIn("UU app.txt", text)
        self.assertIn("app.txt:1 [<<<<<<<]", text)
        self.assertIn("Usage: /conflicts [path]", invalid)

    def test_get_git_info_text_reports_branch_upstream_remotes_and_status(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-commands-") as base:
            base_path = Path(base)
            root = base_path / "work"
            remote = base_path / "remote.git"
            root.mkdir()
            subprocess.run(["git", "init", "--initial-branch", "main"], cwd=root, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            subprocess.run(["git", "config", "user.name", "Test"], cwd=root, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=root, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            (root / "app.txt").write_text("base\n", encoding="utf-8")
            subprocess.run(["git", "add", "app.txt"], cwd=root, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            subprocess.run(["git", "commit", "-m", "initial"], cwd=root, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            subprocess.run(["git", "init", "--bare", remote.as_posix()], check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            subprocess.run(["git", "remote", "add", "origin", remote.as_posix()], cwd=root, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            subprocess.run(["git", "push", "-u", "origin", "main"], cwd=root, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            (root / "app.txt").write_text("changed\n", encoding="utf-8")
            not_repo = base_path / "not-a-repo"
            not_repo.mkdir()

            text = get_git_info_text(root)
            outside = get_git_info_text(not_repo)

        self.assertIn("Git info:", text)
        self.assertIn(f"projectRoot: {root.resolve()}", text)
        self.assertIn("ok: yes", text)
        self.assertIn("isGitRepo: yes", text)
        self.assertIn("branch: main", text)
        self.assertRegex(text, r"head: [0-9a-f]{7,}")
        self.assertIn("upstream: origin/main", text)
        self.assertIn("ahead: 0", text)
        self.assertIn("behind: 0", text)
        self.assertIn("origin (fetch):", text)
        self.assertIn(remote.as_posix(), text)
        self.assertIn("status:", text)
        self.assertIn("M app.txt", text)
        self.assertIn("ok: no", outside)
        self.assertIn("isGitRepo: no", outside)

    def test_get_fetch_pull_push_text_manage_configured_upstream(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-commands-") as base:
            base_path = Path(base)
            root = base_path / "work"
            remote = base_path / "remote.git"
            remote_work = base_path / "remote-work"
            root.mkdir()
            subprocess.run(["git", "init", "--initial-branch", "main"], cwd=root, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            subprocess.run(["git", "config", "user.name", "Test"], cwd=root, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=root, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            (root / "app.txt").write_text("base\n", encoding="utf-8")
            subprocess.run(["git", "add", "app.txt"], cwd=root, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            subprocess.run(["git", "commit", "-m", "initial"], cwd=root, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            subprocess.run(["git", "init", "--bare", remote.as_posix()], check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            subprocess.run(["git", "remote", "add", "origin", remote.as_posix()], cwd=root, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            subprocess.run(["git", "push", "-u", "origin", "main"], cwd=root, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            subprocess.run(
                ["git", "clone", "--branch", "main", remote.as_posix(), remote_work.as_posix()],
                check=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
            subprocess.run(["git", "config", "user.name", "Test"], cwd=remote_work, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=remote_work, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            (remote_work / "remote.txt").write_text("remote update\n", encoding="utf-8")
            subprocess.run(["git", "add", "remote.txt"], cwd=remote_work, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            subprocess.run(["git", "commit", "-m", "remote update"], cwd=remote_work, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            subprocess.run(["git", "push", "origin", "main"], cwd=remote_work, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

            checked_fetch = get_check_fetch_text(root)
            fetched = get_fetch_text(root, "origin")
            checked_pull = get_check_pull_text(root)
            pulled = get_pull_text(root)
            remote_content_after_pull = (root / "remote.txt").read_text(encoding="utf-8")
            (root / "local.txt").write_text("local update\n", encoding="utf-8")
            subprocess.run(["git", "add", "local.txt"], cwd=root, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            subprocess.run(["git", "commit", "-m", "local update"], cwd=root, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            head_after_local_commit = subprocess.run(["git", "rev-parse", "HEAD"], cwd=root, check=True, stdout=subprocess.PIPE, text=True).stdout.strip()
            checked_push = get_check_push_text(root)
            pushed = get_push_text(root)
            remote_main = subprocess.run(["git", "ls-remote", remote.as_posix(), "refs/heads/main"], check=True, stdout=subprocess.PIPE, text=True).stdout
            usage_fetch = get_check_fetch_text(root, "origin extra")

        self.assertIn("Check fetch:", checked_fetch)
        self.assertIn(f"projectRoot: {root.resolve()}", checked_fetch)
        self.assertIn("ok: yes", checked_fetch)
        self.assertIn("remote: origin", checked_fetch)
        self.assertIn("behind: 0", checked_fetch)
        self.assertIn("Fetch:", fetched)
        self.assertIn("ok: yes", fetched)
        self.assertIn("remote: origin", fetched)
        self.assertIn("behindBefore: 0", fetched)
        self.assertIn("behindAfter: 1", fetched)
        self.assertIn("Check pull:", checked_pull)
        self.assertIn("ok: yes", checked_pull)
        self.assertIn("behind: 1", checked_pull)
        self.assertIn("worktreeClean: yes", checked_pull)
        self.assertIn("Pull:", pulled)
        self.assertIn("ok: yes", pulled)
        self.assertIn("behindBefore: 1", pulled)
        self.assertIn("behindAfter: 0", pulled)
        self.assertEqual(remote_content_after_pull, "remote update\n")
        self.assertIn("Check push:", checked_push)
        self.assertIn("ok: yes", checked_push)
        self.assertIn("ahead: 1", checked_push)
        self.assertIn("Push:", pushed)
        self.assertIn("ok: yes", pushed)
        self.assertIn("aheadBefore: 1", pushed)
        self.assertIn(head_after_local_commit, remote_main)
        self.assertIn("Usage: /check-fetch [remote]", usage_fetch)
        self.assertIn("expected at most one remote name", usage_fetch)

    def test_get_check_stash_and_stash_text_save_non_runtime_changes(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-commands-") as base:
            root = Path(base)
            subprocess.run(["git", "init"], cwd=root, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            subprocess.run(["git", "config", "user.name", "Test"], cwd=root, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=root, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            (root / "app.py").write_text("print('old')\n", encoding="utf-8")
            subprocess.run(["git", "add", "app.py"], cwd=root, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            subprocess.run(["git", "commit", "-m", "initial"], cwd=root, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            (root / "app.py").write_text("print('new')\n", encoding="utf-8")
            (root / "extra.txt").write_text("untracked\n", encoding="utf-8")

            checked = get_check_stash_text(root, "--include-untracked save local work")
            status_after_check = subprocess.run(["git", "status", "--short"], cwd=root, check=True, stdout=subprocess.PIPE, text=True).stdout
            stashed = get_stash_text(root, "--include-untracked save local work")
            status_after_stash = subprocess.run(["git", "status", "--short"], cwd=root, check=True, stdout=subprocess.PIPE, text=True).stdout
            stash_list = subprocess.run(["git", "stash", "list"], cwd=root, check=True, stdout=subprocess.PIPE, text=True).stdout
            usage_check = get_check_stash_text(root, "--bad")
            default_preview = get_check_stash_text(root)

        self.assertIn("Check stash:", checked)
        self.assertIn(f"projectRoot: {root.resolve()}", checked)
        self.assertIn("ok: yes", checked)
        self.assertIn("messageText: save local work", checked)
        self.assertIn("includeUntracked: yes", checked)
        self.assertIn(" M app.py", checked)
        self.assertIn("?? extra.txt", checked)
        self.assertIn("-print('old')", checked)
        self.assertIn("+print('new')", checked)
        self.assertIn(" M app.py", status_after_check)
        self.assertIn("?? extra.txt", status_after_check)
        self.assertIn("Stash:", stashed)
        self.assertIn("ok: yes", stashed)
        self.assertIn("stashRef: stash@{0}", stashed)
        self.assertEqual(status_after_stash, "")
        self.assertIn("save local work", stash_list)
        self.assertIn("Usage: /check-stash [--include-untracked] [message]", usage_check)
        self.assertIn("unsupported option", usage_check)
        self.assertIn("ok: no", default_preview)
        self.assertIn("No stashable", default_preview)

    def test_get_check_stash_apply_and_stash_apply_text_apply_existing_stash(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-commands-") as base:
            root = Path(base)
            subprocess.run(["git", "init"], cwd=root, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            subprocess.run(["git", "config", "user.name", "Test"], cwd=root, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=root, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            (root / "app.py").write_text("print('old')\n", encoding="utf-8")
            subprocess.run(["git", "add", "app.py"], cwd=root, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            subprocess.run(["git", "commit", "-m", "initial"], cwd=root, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            (root / "app.py").write_text("print('new')\n", encoding="utf-8")
            subprocess.run(["git", "stash", "push", "-m", "save app"], cwd=root, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

            checked = get_check_stash_apply_text(root, "stash@{0}")
            content_after_check = (root / "app.py").read_text(encoding="utf-8")
            applied = get_stash_apply_text(root, "stash@{0}")
            content_after_apply = (root / "app.py").read_text(encoding="utf-8")
            status_after_apply = subprocess.run(["git", "status", "--short"], cwd=root, check=True, stdout=subprocess.PIPE, text=True).stdout
            stash_list_after_apply = subprocess.run(["git", "stash", "list"], cwd=root, check=True, stdout=subprocess.PIPE, text=True).stdout
            usage_check = get_check_stash_apply_text(root)
            usage_apply = get_stash_apply_text(root)
            invalid = get_check_stash_apply_text(root, "bad-ref")

        self.assertIn("Check stash apply:", checked)
        self.assertIn(f"projectRoot: {root.resolve()}", checked)
        self.assertIn("ok: yes", checked)
        self.assertIn("stashRef: stash@{0}", checked)
        self.assertIn("worktreeClean: yes", checked)
        self.assertIn("-print('old')", checked)
        self.assertIn("+print('new')", checked)
        self.assertEqual(content_after_check, "print('old')\n")
        self.assertIn("Stash apply:", applied)
        self.assertIn("ok: yes", applied)
        self.assertIn("stashRef: stash@{0}", applied)
        self.assertIn("Applied stash@{0}.", applied)
        self.assertEqual(content_after_apply, "print('new')\n")
        self.assertIn(" M app.py", status_after_apply)
        self.assertIn("save app", stash_list_after_apply)
        self.assertIn("Usage: /check-stash-apply <stash@{N}>", usage_check)
        self.assertIn("stash ref is required", usage_check)
        self.assertIn("Usage: /stash-apply <stash@{N}>", usage_apply)
        self.assertIn("stash ref is required", usage_apply)
        self.assertIn("ok: no", invalid)
        self.assertIn("stash_ref must look like", invalid)

    def test_get_check_stash_drop_and_stash_drop_text_delete_existing_stash(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-commands-") as base:
            root = Path(base)
            subprocess.run(["git", "init"], cwd=root, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            subprocess.run(["git", "config", "user.name", "Test"], cwd=root, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=root, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            (root / "app.py").write_text("print('old')\n", encoding="utf-8")
            subprocess.run(["git", "add", "app.py"], cwd=root, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            subprocess.run(["git", "commit", "-m", "initial"], cwd=root, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            (root / "app.py").write_text("print('new')\n", encoding="utf-8")
            subprocess.run(["git", "stash", "push", "-m", "save app"], cwd=root, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

            checked = get_check_stash_drop_text(root, "stash@{0}")
            stash_list_after_check = subprocess.run(["git", "stash", "list"], cwd=root, check=True, stdout=subprocess.PIPE, text=True).stdout
            dropped = get_stash_drop_text(root, "stash@{0}")
            stash_list_after_drop = subprocess.run(["git", "stash", "list"], cwd=root, check=True, stdout=subprocess.PIPE, text=True).stdout
            usage_check = get_check_stash_drop_text(root)
            usage_drop = get_stash_drop_text(root)
            invalid = get_check_stash_drop_text(root, "bad-ref")

        self.assertIn("Check stash drop:", checked)
        self.assertIn(f"projectRoot: {root.resolve()}", checked)
        self.assertIn("ok: yes", checked)
        self.assertIn("stashRef: stash@{0}", checked)
        self.assertIn("summary:", checked)
        self.assertIn("save app", checked)
        self.assertIn("-print('old')", checked)
        self.assertIn("+print('new')", checked)
        self.assertIn("save app", stash_list_after_check)
        self.assertIn("Stash drop:", dropped)
        self.assertIn("ok: yes", dropped)
        self.assertIn("remainingTotal: 0", dropped)
        self.assertIn("Dropped stash@{0}.", dropped)
        self.assertEqual(stash_list_after_drop, "")
        self.assertIn("Usage: /check-stash-drop <stash@{N}>", usage_check)
        self.assertIn("stash ref is required", usage_check)
        self.assertIn("Usage: /stash-drop <stash@{N}>", usage_drop)
        self.assertIn("stash ref is required", usage_drop)
        self.assertIn("ok: no", invalid)
        self.assertIn("stash_ref must look like", invalid)

    def test_get_check_stage_and_stage_text_manage_git_index_for_explicit_paths(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-commands-") as base:
            root = Path(base)
            subprocess.run(["git", "init"], cwd=root, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            subprocess.run(["git", "config", "user.name", "Test"], cwd=root, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=root, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            (root / "app.py").write_text("print('old')\n", encoding="utf-8")
            subprocess.run(["git", "add", "app.py"], cwd=root, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            subprocess.run(["git", "commit", "-m", "initial"], cwd=root, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            (root / "app.py").write_text("print('new')\n", encoding="utf-8")

            checked = get_check_stage_text(root, "app.py")
            status_after_check = subprocess.run(["git", "status", "--short"], cwd=root, check=True, stdout=subprocess.PIPE, text=True).stdout
            staged = get_stage_text(root, "app.py")
            status_after_stage = subprocess.run(["git", "status", "--short"], cwd=root, check=True, stdout=subprocess.PIPE, text=True).stdout
            usage_check = get_check_stage_text(root)
            usage_stage = get_stage_text(root)

        self.assertIn("Check stage:", checked)
        self.assertIn(f"projectRoot: {root.resolve()}", checked)
        self.assertIn("ok: yes", checked)
        self.assertIn("paths: 1", checked)
        self.assertIn("- app.py", checked)
        self.assertIn(" M app.py", checked)
        self.assertIn(" M app.py", status_after_check)
        self.assertIn("Stage:", staged)
        self.assertIn("ok: yes", staged)
        self.assertIn("M  app.py", staged)
        self.assertIn("M  app.py", status_after_stage)
        self.assertIn("Usage: /check-stage <path...>", usage_check)
        self.assertIn("path is required", usage_check)
        self.assertIn("Usage: /stage <path...>", usage_stage)
        self.assertIn("path is required", usage_stage)

    def test_get_check_unstage_and_unstage_text_manage_git_index_for_explicit_paths(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-commands-") as base:
            root = Path(base)
            subprocess.run(["git", "init"], cwd=root, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            subprocess.run(["git", "config", "user.name", "Test"], cwd=root, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=root, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            (root / "app.py").write_text("print('old')\n", encoding="utf-8")
            subprocess.run(["git", "add", "app.py"], cwd=root, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            subprocess.run(["git", "commit", "-m", "initial"], cwd=root, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            (root / "app.py").write_text("print('new')\n", encoding="utf-8")
            subprocess.run(["git", "add", "app.py"], cwd=root, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

            checked = get_check_unstage_text(root, "app.py")
            status_after_check = subprocess.run(["git", "status", "--short"], cwd=root, check=True, stdout=subprocess.PIPE, text=True).stdout
            unstaged = get_unstage_text(root, "app.py")
            status_after_unstage = subprocess.run(["git", "status", "--short"], cwd=root, check=True, stdout=subprocess.PIPE, text=True).stdout
            usage_check = get_check_unstage_text(root)
            usage_unstage = get_unstage_text(root)

        self.assertIn("Check unstage:", checked)
        self.assertIn(f"projectRoot: {root.resolve()}", checked)
        self.assertIn("ok: yes", checked)
        self.assertIn("paths: 1", checked)
        self.assertIn("- app.py", checked)
        self.assertIn("M  app.py", checked)
        self.assertIn("M  app.py", status_after_check)
        self.assertIn("Unstage:", unstaged)
        self.assertIn("ok: yes", unstaged)
        self.assertIn(" M app.py", unstaged)
        self.assertIn(" M app.py", status_after_unstage)
        self.assertIn("Usage: /check-unstage <path...>", usage_check)
        self.assertIn("path is required", usage_check)
        self.assertIn("Usage: /unstage <path...>", usage_unstage)
        self.assertIn("path is required", usage_unstage)

    def test_get_check_commit_and_commit_text_use_staged_changes(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-commands-") as base:
            root = Path(base)
            subprocess.run(["git", "init"], cwd=root, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            subprocess.run(["git", "config", "user.name", "Test"], cwd=root, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=root, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            (root / "app.py").write_text("print('old')\n", encoding="utf-8")
            subprocess.run(["git", "add", "app.py"], cwd=root, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            subprocess.run(["git", "commit", "-m", "initial"], cwd=root, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            (root / "app.py").write_text("print('new')\n", encoding="utf-8")
            subprocess.run(["git", "add", "app.py"], cwd=root, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            head_before = subprocess.run(["git", "rev-parse", "--short", "HEAD"], cwd=root, check=True, stdout=subprocess.PIPE, text=True).stdout.strip()

            checked = get_check_commit_text(root, "update app")
            head_after_check = subprocess.run(["git", "rev-parse", "--short", "HEAD"], cwd=root, check=True, stdout=subprocess.PIPE, text=True).stdout.strip()
            committed = get_commit_text(root, "update app")
            head_after_commit = subprocess.run(["git", "rev-parse", "--short", "HEAD"], cwd=root, check=True, stdout=subprocess.PIPE, text=True).stdout.strip()
            status_after_commit = subprocess.run(["git", "status", "--short"], cwd=root, check=True, stdout=subprocess.PIPE, text=True).stdout
            usage_check = get_check_commit_text(root)
            usage_commit = get_commit_text(root)

        self.assertIn("Check commit:", checked)
        self.assertIn(f"projectRoot: {root.resolve()}", checked)
        self.assertIn("ok: yes", checked)
        self.assertIn(f"headBefore: {head_before}", checked)
        self.assertIn(f"headAfter: {head_before}", checked)
        self.assertEqual(head_after_check, head_before)
        self.assertIn("Staged changes can be committed.", checked)
        self.assertIn("Commit:", committed)
        self.assertIn("ok: yes", committed)
        self.assertIn(f"headBefore: {head_before}", committed)
        self.assertNotEqual(head_after_commit, head_before)
        self.assertIn(f"headAfter: {head_after_commit}", committed)
        self.assertEqual(status_after_commit, "")
        self.assertIn("Usage: /check-commit <message>", usage_check)
        self.assertIn("message is required", usage_check)
        self.assertIn("Usage: /commit <message>", usage_commit)
        self.assertIn("message is required", usage_commit)

    def test_get_check_restore_and_restore_text_discard_unstaged_tracked_changes(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-commands-") as base:
            root = Path(base)
            subprocess.run(["git", "init"], cwd=root, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            subprocess.run(["git", "config", "user.name", "Test"], cwd=root, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=root, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            (root / "app.py").write_text("print('old')\n", encoding="utf-8")
            subprocess.run(["git", "add", "app.py"], cwd=root, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            subprocess.run(["git", "commit", "-m", "initial"], cwd=root, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            (root / "app.py").write_text("print('new')\n", encoding="utf-8")
            (root / "untracked.txt").write_text("keep me\n", encoding="utf-8")

            checked = get_check_restore_text(root, "app.py")
            content_after_check = (root / "app.py").read_text(encoding="utf-8")
            restored = get_restore_text(root, "app.py")
            content_after_restore = (root / "app.py").read_text(encoding="utf-8")
            untracked_exists_after_restore = (root / "untracked.txt").exists()
            usage_check = get_check_restore_text(root)
            usage_restore = get_restore_text(root)

        self.assertIn("Check restore:", checked)
        self.assertIn(f"projectRoot: {root.resolve()}", checked)
        self.assertIn("ok: yes", checked)
        self.assertIn("paths: 1", checked)
        self.assertIn("- app.py", checked)
        self.assertIn("-print('old')", checked)
        self.assertIn("+print('new')", checked)
        self.assertEqual(content_after_check, "print('new')\n")
        self.assertIn("Restore:", restored)
        self.assertIn("ok: yes", restored)
        self.assertIn("Restored unstaged changes", restored)
        self.assertIn("-print('old')", restored)
        self.assertIn("+print('new')", restored)
        self.assertEqual(content_after_restore, "print('old')\n")
        self.assertTrue(untracked_exists_after_restore)
        self.assertIn("Usage: /check-restore <path...>", usage_check)
        self.assertIn("path is required", usage_check)
        self.assertIn("Usage: /restore <path...>", usage_restore)
        self.assertIn("path is required", usage_restore)

    def test_get_check_switch_and_switch_text_manage_local_branches(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-commands-") as base:
            root = Path(base)
            subprocess.run(["git", "init"], cwd=root, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            subprocess.run(["git", "config", "user.name", "Test"], cwd=root, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=root, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            (root / "app.py").write_text("print('old')\n", encoding="utf-8")
            subprocess.run(["git", "add", "app.py"], cwd=root, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            subprocess.run(["git", "commit", "-m", "initial"], cwd=root, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            subprocess.run(["git", "branch", "-m", "main"], cwd=root, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

            checked_create = get_check_switch_text(root, "--create feature/demo")
            branch_after_check = subprocess.run(["git", "branch", "--show-current"], cwd=root, check=True, stdout=subprocess.PIPE, text=True).stdout.strip()
            switched_create = get_switch_text(root, "--create feature/demo")
            branch_after_switch = subprocess.run(["git", "branch", "--show-current"], cwd=root, check=True, stdout=subprocess.PIPE, text=True).stdout.strip()
            switched_main = get_switch_text(root, "main")
            branch_after_main = subprocess.run(["git", "branch", "--show-current"], cwd=root, check=True, stdout=subprocess.PIPE, text=True).stdout.strip()
            (root / "app.py").write_text("print('dirty')\n", encoding="utf-8")
            checked_dirty = get_check_switch_text(root, "feature/demo")
            usage_check = get_check_switch_text(root)
            usage_switch = get_switch_text(root)

        self.assertIn("Check switch:", checked_create)
        self.assertIn(f"projectRoot: {root.resolve()}", checked_create)
        self.assertIn("ok: yes", checked_create)
        self.assertIn("branch: feature/demo", checked_create)
        self.assertIn("create: yes", checked_create)
        self.assertIn("branchExists: no", checked_create)
        self.assertEqual(branch_after_check, "main")
        self.assertIn("Switch:", switched_create)
        self.assertIn("ok: yes", switched_create)
        self.assertIn("currentBefore: main", switched_create)
        self.assertIn("currentAfter: feature/demo", switched_create)
        self.assertEqual(branch_after_switch, "feature/demo")
        self.assertIn("Switch:", switched_main)
        self.assertIn("currentAfter: main", switched_main)
        self.assertEqual(branch_after_main, "main")
        self.assertIn("Check switch:", checked_dirty)
        self.assertIn("ok: no", checked_dirty)
        self.assertIn("worktreeClean: no", checked_dirty)
        self.assertIn("uncommitted changes", checked_dirty)
        self.assertIn("Usage: /check-switch [--create] <branch>", usage_check)
        self.assertIn("branch is required", usage_check)
        self.assertIn("Usage: /switch [--create] <branch>", usage_switch)
        self.assertIn("branch is required", usage_switch)

    def test_get_env_text_reports_runtime_and_tool_availability(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-commands-") as base:
            root = Path(base)
            text = get_env_text(root)

        self.assertIn("Environment:", text)
        self.assertIn(f"projectRoot: {root.resolve()}", text)
        self.assertIn("ok: yes", text)
        self.assertIn("platform:", text)
        self.assertIn("pythonVersion:", text)
        self.assertIn("pythonExecutable:", text)
        self.assertIn("gitRepo:", text)
        self.assertIn("tools:", text)
        self.assertIn("python:", text)
        self.assertIn("git:", text)

    def test_get_processes_text_reports_background_process_registry(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-commands-") as base:
            root = Path(base)
            text = get_processes_text(root)

        self.assertIn("Processes:", text)
        self.assertIn(f"projectRoot: {root.resolve()}", text)
        self.assertIn("processes:", text)
        self.assertIn("running:", text)
        self.assertIn("message: Found", text)

    def test_get_process_text_reports_captured_process_output_or_usage(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-commands-") as base:
            root = Path(base)
            missing = get_process_text(root, "missing 2000")
            usage = get_process_text(root)
            invalid = get_process_text(root, "missing many")
            too_small = get_process_text(root, "missing 999")

        self.assertIn("Process:", missing)
        self.assertIn(f"projectRoot: {root.resolve()}", missing)
        self.assertIn("ok: no", missing)
        self.assertIn("processId: missing", missing)
        self.assertIn("maxOutputChars: 2000", missing)
        self.assertIn("Unknown background process id.", missing)
        self.assertIn("stdout: none", missing)
        self.assertIn("stderr: none", missing)
        self.assertIn("Usage: /process <id> [chars]", usage)
        self.assertIn("process id is required", usage)
        self.assertIn("invalid max chars", invalid)
        self.assertIn("max chars must be at least 1000", too_small)

    def test_get_process_output_contexts_text_reports_contexts_or_usage(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-commands-") as base:
            root = Path(base)
            missing = get_process_output_contexts_text(root, "missing 2000")
            usage = get_process_output_contexts_text(root)
            invalid = get_process_output_contexts_text(root, "missing many")
            too_small = get_process_output_contexts_text(root, "missing 999")
            observation = ProcessOutputContextsObservation(
                kind="process_output_contexts",
                process_id="bg-1",
                pid=1234,
                ok=True,
                running=False,
                exit_code=7,
                signal=None,
                contexts=[
                    OutputContextResult(
                        path="src/app.py",
                        line=2,
                        column=5,
                        raw="src/app.py:2:5",
                        ok=True,
                        content="2: print('ok')\n",
                        message="Read src/app.py:2.",
                        context_lines=0,
                        start_line=2,
                        end_line=2,
                        line_count=1,
                        total_lines=3,
                        target_line_exists=True,
                        truncated=False,
                        max_bytes=1000,
                    )
                ],
                total_refs=1,
                truncated=False,
                stdout_chars=24,
                stderr_chars=0,
                max_output_chars=2000,
                message="Extracted 1/1 output context(s) from process bg-1.",
            )
            with patch("vibeagent.commands.execute_action", return_value=observation):
                rendered = get_process_output_contexts_text(
                    root,
                    "bg-1 2000",
                    context_lines=0,
                    max_contexts=5,
                    max_bytes_per_context=1000,
                )

        self.assertIn("Process output contexts:", missing)
        self.assertIn(f"projectRoot: {root.resolve()}", missing)
        self.assertIn("ok: no", missing)
        self.assertIn("processId: missing", missing)
        self.assertIn("maxOutputChars: 2000", missing)
        self.assertIn("Unknown background process id.", missing)
        self.assertIn("Usage: /process-output-contexts <id> [chars]", usage)
        self.assertIn("process id is required", usage)
        self.assertIn("invalid max chars", invalid)
        self.assertIn("max chars must be at least 1000", too_small)
        self.assertIn("status: exited(7)", rendered)
        self.assertIn("contexts: 1/1", rendered)
        self.assertIn("Context: src/app.py:2:5", rendered)
        self.assertIn("print('ok')", rendered)

    def test_get_process_output_diagnostics_text_reports_diagnostics_or_usage(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-commands-") as base:
            root = Path(base)
            missing = get_process_output_diagnostics_text(root, "missing 2000")
            usage = get_process_output_diagnostics_text(root)
            invalid = get_process_output_diagnostics_text(root, "missing many")
            too_small = get_process_output_diagnostics_text(root, "missing 999")
            observation = ProcessOutputDiagnosticsObservation(
                kind="process_output_diagnostics",
                process_id="bg-1",
                pid=1234,
                ok=True,
                running=False,
                exit_code=None,
                signal="SIGTERM",
                diagnostics=[
                    OutputDiagnostic(
                        severity="error",
                        output_line=1,
                        text="ERROR src/app.py:2:5 failed",
                        path="src/app.py",
                        line=2,
                        column=5,
                        raw="src/app.py:2:5",
                    )
                ],
                contexts=[
                    OutputContextResult(
                        path="src/app.py",
                        line=2,
                        column=5,
                        raw="src/app.py:2:5",
                        ok=True,
                        content="2: print('ok')\n",
                        message="Read src/app.py:2.",
                        context_lines=0,
                        start_line=2,
                        end_line=2,
                        line_count=1,
                        total_lines=3,
                        target_line_exists=True,
                        truncated=False,
                        max_bytes=1000,
                    )
                ],
                total_diagnostics=1,
                total_refs=1,
                diagnostics_truncated=False,
                contexts_truncated=False,
                stdout_chars=32,
                stderr_chars=0,
                max_output_chars=2000,
                message="Extracted 1/1 diagnostic(s) and 1/1 source context(s) from process bg-1.",
            )
            with patch("vibeagent.commands.execute_action", return_value=observation):
                rendered = get_process_output_diagnostics_text(
                    root,
                    "bg-1 2000",
                    context_lines=0,
                    max_diagnostics=5,
                    max_contexts=5,
                    max_bytes_per_context=1000,
                )

        self.assertIn("Process output diagnostics:", missing)
        self.assertIn(f"projectRoot: {root.resolve()}", missing)
        self.assertIn("ok: no", missing)
        self.assertIn("processId: missing", missing)
        self.assertIn("maxOutputChars: 2000", missing)
        self.assertIn("Unknown background process id.", missing)
        self.assertIn("Usage: /process-output-diagnostics <id> [chars]", usage)
        self.assertIn("process id is required", usage)
        self.assertIn("invalid max chars", invalid)
        self.assertIn("max chars must be at least 1000", too_small)
        self.assertIn("status: signaled(SIGTERM)", rendered)
        self.assertIn("diagnostics: 1/1", rendered)
        self.assertIn("error outputLine=1 src/app.py:2:5", rendered)
        self.assertIn("Context: src/app.py:2:5", rendered)
        self.assertIn("print('ok')", rendered)

    def test_get_process_text_renders_auto_output_diagnostics(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-commands-") as base:
            root = Path(base)
            observation = ReadProcessObservation(
                kind="read_process",
                process_id="bg-1",
                pid=1234,
                ok=True,
                running=False,
                exit_code=3,
                signal=None,
                stdout="",
                stderr="ERROR src/app.py:2:5 failed\n",
                max_output_chars=2000,
                message="Process bg-1 is exited.",
                output_diagnostics=[
                    OutputDiagnostic(
                        severity="error",
                        output_line=1,
                        text="ERROR src/app.py:2:5 failed",
                        path="src/app.py",
                        line=2,
                        column=5,
                        raw="src/app.py:2:5",
                    )
                ],
                output_diagnostic_total=1,
            )
            with patch("vibeagent.commands.execute_action", return_value=observation):
                rendered = get_process_text(root, "bg-1 2000")

        self.assertIn("Process:", rendered)
        self.assertIn("status: exited(3)", rendered)
        self.assertIn("outputDiagnostics: 1/1", rendered)
        self.assertIn("error outputLine=1 src/app.py:2:5", rendered)

    def test_get_wait_process_text_reports_wait_result_or_usage(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-commands-") as base:
            root = Path(base)
            missing = get_wait_process_text(root, "missing 5000 2000")
            usage = get_wait_process_text(root)
            invalid_timeout = get_wait_process_text(root, "missing soon")
            too_small_timeout = get_wait_process_text(root, "missing 99")
            too_small_output = get_wait_process_text(root, "missing 5000 999")

        self.assertIn("Wait process:", missing)
        self.assertIn(f"projectRoot: {root.resolve()}", missing)
        self.assertIn("ok: no", missing)
        self.assertIn("processId: missing", missing)
        self.assertIn("timedOut: no", missing)
        self.assertIn("matched: no", missing)
        self.assertIn("timeoutMs: 5000", missing)
        self.assertIn("maxOutputChars: 2000", missing)
        self.assertIn("Unknown background process id.", missing)
        self.assertIn("stdout: none", missing)
        self.assertIn("stderr: none", missing)
        self.assertIn("Usage: /wait-process <id> [timeout-ms] [chars]", usage)
        self.assertIn("process id is required", usage)
        self.assertIn("invalid timeout ms", invalid_timeout)
        self.assertIn("timeout ms must be at least 100", too_small_timeout)
        self.assertIn("max chars must be at least 1000", too_small_output)

    def test_get_wait_process_text_renders_auto_output_diagnostics(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-commands-") as base:
            root = Path(base)
            observation = WaitProcessObservation(
                kind="wait_process",
                process_id="bg-1",
                pid=1234,
                ok=True,
                running=False,
                timed_out=False,
                matched=False,
                matched_stream=None,
                matched_pattern=None,
                timeout_ms=5000,
                exit_code=3,
                signal=None,
                stdout="",
                stderr="ERROR src/app.py:2:5 failed\n",
                max_output_chars=2000,
                message="Process bg-1 is exited.",
                output_diagnostics=[
                    OutputDiagnostic(
                        severity="error",
                        output_line=1,
                        text="ERROR src/app.py:2:5 failed",
                        path="src/app.py",
                        line=2,
                        column=5,
                        raw="src/app.py:2:5",
                    )
                ],
                output_diagnostic_total=1,
            )
            with patch("vibeagent.commands.execute_action", return_value=observation):
                rendered = get_wait_process_text(root, "bg-1 5000 2000")

        self.assertIn("Wait process:", rendered)
        self.assertIn("status: exited(3)", rendered)
        self.assertIn("outputDiagnostics: 1/1", rendered)
        self.assertIn("error outputLine=1 src/app.py:2:5", rendered)

    def test_get_write_process_text_reports_write_result_or_usage(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-commands-") as base:
            root = Path(base)
            missing = get_write_process_text(root, "missing hello\\n")
            usage = get_write_process_text(root)
            missing_content = get_write_process_text(root, "missing")

        self.assertIn("Write process:", missing)
        self.assertIn(f"projectRoot: {root.resolve()}", missing)
        self.assertIn("ok: no", missing)
        self.assertIn("processId: missing", missing)
        self.assertIn("pid: .", missing)
        self.assertIn("running: no", missing)
        self.assertIn("command: .", missing)
        self.assertIn("cwd: .", missing)
        self.assertIn("contentChars: 6", missing)
        self.assertIn("Unknown background process id.", missing)
        self.assertIn("Usage: /write-process <id> <text>", usage)
        self.assertIn("process id is required", usage)
        self.assertIn("stdin text is required", missing_content)

    def test_get_check_write_process_text_reports_preflight_result_or_usage(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-commands-") as base:
            root = Path(base)
            observation = CheckWriteProcessObservation(
                kind="check_write_process",
                process_id="bg-1",
                pid=123,
                ok=True,
                running=True,
                command="python3 repl.py",
                cwd=".",
                content_chars=6,
                message="Process bg-1 can receive stdin.",
            )
            with patch("vibeagent.commands.execute_action", return_value=observation):
                rendered = get_check_write_process_text(root, "bg-1 hello\\n")

            usage = get_check_write_process_text(root)
            missing_content = get_check_write_process_text(root, "bg-1")

        self.assertIn("Check write process:", rendered)
        self.assertIn(f"projectRoot: {root.resolve()}", rendered)
        self.assertIn("ok: yes", rendered)
        self.assertIn("processId: bg-1", rendered)
        self.assertIn("pid: 123", rendered)
        self.assertIn("running: yes", rendered)
        self.assertIn("command: python3 repl.py", rendered)
        self.assertIn("cwd: .", rendered)
        self.assertIn("contentChars: 6", rendered)
        self.assertIn("can receive stdin", rendered)
        self.assertIn("Usage: /check-write-process <id> <text>", usage)
        self.assertIn("process id is required", usage)
        self.assertIn("stdin text is required", missing_content)

    def test_get_check_stop_process_text_reports_preflight_or_usage(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-commands-") as base:
            root = Path(base)
            observation = CheckStopProcessObservation(
                kind="check_stop_process",
                process_id="bg-1",
                pid=123,
                ok=True,
                command="npm run dev",
                cwd="web",
                running=True,
                exit_code=None,
                signal=None,
                message="Process bg-1 is running and can be stopped.",
            )
            missing_observation = CheckStopProcessObservation(
                kind="check_stop_process",
                process_id="missing",
                pid=None,
                ok=False,
                command=None,
                cwd=None,
                running=False,
                exit_code=None,
                signal=None,
                message="Unknown background process id.",
            )
            with patch("vibeagent.commands.execute_action", return_value=observation) as execute_action:
                text = get_check_stop_process_text(root, "bg-1")
            with patch("vibeagent.commands.execute_action", return_value=missing_observation):
                missing = get_check_stop_process_text(root, "missing")
            usage = get_check_stop_process_text(root)

            action = execute_action.call_args.args[1]

        self.assertIn("Check stop process:", text)
        self.assertIn(f"projectRoot: {root.resolve()}", text)
        self.assertIn("ok: yes", text)
        self.assertIn("processId: bg-1", text)
        self.assertIn("pid: 123", text)
        self.assertIn("status: running", text)
        self.assertIn("command: npm run dev", text)
        self.assertIn("cwd: web", text)
        self.assertIn("running and can be stopped", text)
        self.assertEqual(action.type, "check_stop_process")
        self.assertEqual(action.process_id, "bg-1")
        self.assertIn("Check stop process:", missing)
        self.assertIn("ok: no", missing)
        self.assertIn("processId: missing", missing)
        self.assertIn("pid: .", missing)
        self.assertIn("status: unknown", missing)
        self.assertIn("Unknown background process id.", missing)
        self.assertIn("Usage: /check-stop-process <id>", usage)
        self.assertIn("process id is required", usage)

    def test_get_stop_process_text_reports_stop_result_or_usage(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-commands-") as base:
            root = Path(base)
            missing = get_stop_process_text(root, "missing")
            usage = get_stop_process_text(root)

        self.assertIn("Stop process:", missing)
        self.assertIn(f"projectRoot: {root.resolve()}", missing)
        self.assertIn("ok: no", missing)
        self.assertIn("processId: missing", missing)
        self.assertIn("pid: .", missing)
        self.assertIn("result: unknown", missing)
        self.assertIn("Unknown background process id.", missing)
        self.assertIn("Usage: /stop-process <id>", usage)
        self.assertIn("process id is required", usage)

    def test_get_check_stop_all_processes_text_reports_processes_without_stopping(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-commands-") as base:
            root = Path(base)
            observation = CheckStopAllProcessesObservation(
                kind="check_stop_all_processes",
                ok=True,
                processes=[
                    ProcessInfo(
                        process_id="bg-1",
                        pid=123,
                        command="npm run dev",
                        cwd="web",
                        running=True,
                        exit_code=None,
                        signal=None,
                    )
                ],
                running_count=1,
                message="stop_all_processes would stop 1 background process(es), 1 still running.",
            )
            empty_observation = CheckStopAllProcessesObservation(
                kind="check_stop_all_processes",
                ok=True,
                processes=[],
                running_count=0,
                message="stop_all_processes would stop 0 background process(es), 0 still running.",
            )
            with patch("vibeagent.commands.execute_action", return_value=observation) as execute_action:
                text = get_check_stop_all_processes_text(root)
            with patch("vibeagent.commands.execute_action", return_value=empty_observation):
                empty = get_check_stop_all_processes_text(root)

            action = execute_action.call_args.args[1]

        self.assertIn("Check stop processes:", text)
        self.assertIn(f"projectRoot: {root.resolve()}", text)
        self.assertIn("ok: yes", text)
        self.assertIn("processes: 1", text)
        self.assertIn("running: 1", text)
        self.assertIn("bg-1: pid=123; status=running; cwd=web; command=npm run dev", text)
        self.assertIn("would stop 1 background process", text)
        self.assertEqual(action.type, "check_stop_all_processes")
        self.assertIn("processes: 0", empty)
        self.assertIn("items: none", empty)

    def test_get_stop_all_processes_text_reports_stopped_processes(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-commands-") as base:
            root = Path(base)
            observation = StopAllProcessesObservation(
                kind="stop_all_processes",
                ok=True,
                stopped=[
                    StoppedProcessInfo(
                        process_id="bg-1",
                        pid=123,
                        command="npm run dev",
                        cwd="web",
                        ok=True,
                        exit_code=-15,
                        signal="SIGTERM",
                        message="Stopped process bg-1.",
                    )
                ],
                message="Stopped 1 background process(es).",
            )
            empty_observation = StopAllProcessesObservation(
                kind="stop_all_processes",
                ok=True,
                stopped=[],
                message="Stopped 0 background process(es).",
            )
            with patch("vibeagent.commands.execute_action", return_value=observation) as execute_action:
                text = get_stop_all_processes_text(root)
            with patch("vibeagent.commands.execute_action", return_value=empty_observation):
                empty = get_stop_all_processes_text(root)

            action = execute_action.call_args.args[1]

        self.assertIn("Stop processes:", text)
        self.assertIn(f"projectRoot: {root.resolve()}", text)
        self.assertIn("ok: yes", text)
        self.assertIn("stopped: 1", text)
        self.assertIn("- bg-1", text)
        self.assertIn("pid: 123", text)
        self.assertIn("command: npm run dev", text)
        self.assertIn("cwd: web", text)
        self.assertIn("result: signaled(SIGTERM)", text)
        self.assertIn("Stopped 1 background process(es).", text)
        self.assertEqual(action.type, "stop_all_processes")
        self.assertIn("stopped: 0", empty)
        self.assertIn("processes: none", empty)

    def test_get_manifests_text_reports_package_and_pyproject_metadata(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-commands-") as base:
            root = Path(base)
            (root / "package.json").write_text(
                json.dumps(
                    {
                        "name": "web",
                        "version": "1.2.3",
                        "scripts": {"test": "node test.js"},
                        "dependencies": {"react": "^19.0.0"},
                    }
                ),
                encoding="utf-8",
            )
            (root / "pyproject.toml").write_text(
                '[project]\nname = "demo"\nversion = "0.1.0"\ndependencies = ["requests"]\n[project.scripts]\ndemo = "demo:main"\n',
                encoding="utf-8",
            )

            text = get_manifests_text(root)

        self.assertIn("Manifests:", text)
        self.assertIn(f"projectRoot: {root.resolve()}", text)
        self.assertIn("ok: yes", text)
        self.assertIn("files: 2/2", text)
        self.assertIn("package.json", text)
        self.assertIn("name=web version=1.2.3", text)
        self.assertIn("scripts: test = node test.js", text)
        self.assertIn("dependencies: react = ^19.0.0", text)
        self.assertIn("pyproject.toml", text)
        self.assertIn("name=demo version=0.1.0", text)
        self.assertIn("dependencies: requests", text)
        self.assertIn("scripts: demo = demo:main", text)

    def test_get_manifests_text_respects_bounds(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-commands-") as base:
            root = Path(base)
            (root / "package.json").write_text(
                json.dumps(
                    {
                        "name": "web",
                        "version": "1.2.3",
                        "scripts": {"test": "node test.js"},
                        "dependencies": {"react": "^19.0.0"},
                    }
                ),
                encoding="utf-8",
            )
            (root / "pyproject.toml").write_text(
                '[project]\nname = "demo"\nversion = "0.1.0"\ndependencies = ["requests"]\n',
                encoding="utf-8",
            )

            text = get_manifests_text(root, max_files=1, max_items=1)

        self.assertIn("Manifests:", text)
        self.assertIn("files: 1/2", text)
        self.assertIn("scannedFiles: 1/2", text)
        self.assertIn("truncated: yes", text)
        self.assertIn("package.json", text)
        self.assertNotIn("pyproject.toml", text)

    def test_get_instructions_text_reports_instruction_sources_and_text(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-commands-") as base:
            root = Path(base)
            (root / "AGENTS.md").write_text("Use Python.\n", encoding="utf-8")
            (root / "pkg").mkdir()
            (root / "pkg" / "CLAUDE.md").write_text("Use unittest.\n", encoding="utf-8")

            text = get_instructions_text(root)

        self.assertIn("Project instructions:", text)
        self.assertIn(f"projectRoot: {root.resolve()}", text)
        self.assertIn("ok: yes", text)
        self.assertIn("files: 2/2", text)
        self.assertIn("AGENTS.md (scope=.", text)
        self.assertIn("pkg/CLAUDE.md (scope=pkg", text)
        self.assertIn("File: AGENTS.md", text)
        self.assertIn("Use Python.", text)
        self.assertIn("Use unittest.", text)

    def test_get_instructions_text_respects_bounds(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-commands-") as base:
            root = Path(base)
            (root / "AGENTS.md").write_text("A" * 200, encoding="utf-8")
            (root / "pkg").mkdir()
            (root / "pkg" / "CLAUDE.md").write_text("Use unittest.\n", encoding="utf-8")

            text = get_instructions_text(root, max_files=1, max_bytes=80)

        self.assertIn("Project instructions:", text)
        self.assertIn("files: 1/2", text)
        self.assertIn("scannedFiles: 1/2", text)
        self.assertIn("truncated: yes", text)
        self.assertIn("File: AGENTS.md", text)
        self.assertIn("AAAAAAAAAAAAAAAAAAAA", text)
        self.assertNotIn("Use unittest.", text)

    def test_get_todos_text_reports_project_todo_markers(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-commands-") as base:
            root = Path(base)
            (root / "src").mkdir()
            (root / "src" / "app.py").write_text("# TODO: wire cache\n", encoding="utf-8")
            (root / "docs.md").write_text("FIXME: document flags\n", encoding="utf-8")

            text = get_todos_text(root, path="src")

        self.assertIn("Project TODOs:", text)
        self.assertIn(f"projectRoot: {root.resolve()}", text)
        self.assertIn("path: src", text)
        self.assertIn("todos: 1/1", text)
        self.assertIn("src/app.py:1 [TODO] # TODO: wire cache", text)
        self.assertNotIn("docs.md", text)

    def test_get_todos_text_applies_item_and_file_bounds(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-commands-") as base:
            root = Path(base)
            (root / "src").mkdir()
            (root / "src" / "a.py").write_text("# TODO: first\n# FIXME: second\n", encoding="utf-8")
            (root / "src" / "b.py").write_text("# TODO: third\n", encoding="utf-8")

            item_limited = get_todos_text(root, path="src", max_items=1, max_files=10)
            file_limited = get_todos_text(root, path="src", max_items=10, max_files=1)

        self.assertIn("todos: 1/3", item_limited)
        self.assertIn("scannedFiles: 2/2", item_limited)
        self.assertIn("truncated: yes", item_limited)
        self.assertIn("src/a.py:1 [TODO] # TODO: first", item_limited)
        self.assertNotIn("second", item_limited)
        self.assertIn("scannedFiles: 1/2", file_limited)
        self.assertIn("truncated: yes", file_limited)

    def test_get_command_check_text_reports_preflight_without_running_command(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-commands-") as base:
            root = Path(base)
            (root / "src").mkdir()

            ok_text = get_command_check_text(root, "python3 --version", cwd="src")
            blocked_text = get_command_check_text(root, "sudo reboot")
            missing_text = get_command_check_text(root, "definitely_missing_vibeagent_tool --version")
            invalid_cwd_text = get_command_check_text(root, "python3 --version", cwd="../outside")

        self.assertIn("Command check:", ok_text)
        self.assertIn("ok: yes", ok_text)
        self.assertIn("cwd: src", ok_text)
        self.assertIn("executableAvailable: yes", ok_text)
        self.assertIn("ok: no", blocked_text)
        self.assertIn("blocked: yes", blocked_text)
        self.assertIn("high-risk command", blocked_text)
        self.assertIn("missingTool: definitely_missing_vibeagent_tool", missing_text)
        self.assertIn("cwdOk: no", invalid_cwd_text)
        self.assertEqual(get_command_check_text(root), "Usage: /command <shell command>")

    def test_get_run_text_runs_finite_command_with_safety_checks(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-commands-") as base:
            root = Path(base)
            (root / "src").mkdir()

            ok_text = get_run_text(root, "python3 -c \"print('hello')\"", cwd="src", timeout_ms=5000, max_output_chars=2000)
            blocked_text = get_run_text(root, "sudo reboot")
            invalid_cwd_text = get_run_text(root, "python3 --version", cwd="../outside")
            usage = get_run_text(root)

        self.assertIn("Run:", ok_text)
        self.assertIn(f"projectRoot: {root.resolve()}", ok_text)
        self.assertIn("command: python3 -c \"print('hello')\"", ok_text)
        self.assertIn("cwd: src", ok_text)
        self.assertIn("ok: yes", ok_text)
        self.assertIn("exitCode: 0", ok_text)
        self.assertIn("timedOut: no", ok_text)
        self.assertIn("timeoutMs: 5000", ok_text)
        self.assertIn("maxOutputChars: 2000", ok_text)
        self.assertIn("stdout:", ok_text)
        self.assertIn("hello", ok_text)
        self.assertIn("stderr: none", ok_text)
        self.assertIn("ok: no", blocked_text)
        self.assertIn("exitCode: .", blocked_text)
        self.assertIn("Command blocked", blocked_text)
        self.assertIn("ok: no", invalid_cwd_text)
        self.assertIn("escapes", invalid_cwd_text)
        self.assertEqual(usage, "Usage: /run <shell command>")

    def test_get_run_text_can_extract_output_contexts(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-commands-") as base:
            root = Path(base)
            (root / "src").mkdir()
            (root / "src" / "app.py").write_text("one\nTwo\nthree\n", encoding="utf-8")

            text = get_run_text(
                root,
                "python3 -c \"print('src/app.py:2:5: note')\"",
                timeout_ms=5000,
                max_output_chars=2000,
                extract_output_contexts=True,
                context_lines=0,
                max_bytes_per_context=1000,
            )

        self.assertIn("outputContexts: 1/1", text)
        self.assertIn("src/app.py:2:5 [src/app.py:2:5]", text)
        self.assertIn("2: Two", text)

    def test_get_run_text_can_extract_output_diagnostics(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-commands-") as base:
            root = Path(base)
            (root / "src").mkdir()
            (root / "src" / "app.py").write_text("one\nTwo\nthree\n", encoding="utf-8")

            text = get_run_text(
                root,
                "python3 -c \"print('ERROR src/app.py:2:5 failed')\"",
                timeout_ms=5000,
                max_output_chars=2000,
                extract_output_diagnostics=True,
                context_lines=0,
                max_bytes_per_context=1000,
            )

        self.assertIn("outputDiagnostics: 1/1", text)
        self.assertIn("outputDiagnosticsTruncated: no", text)
        self.assertIn("error outputLine=1 src/app.py:2:5", text)
        self.assertIn("2: Two", text)

    def test_get_run_text_auto_extracts_output_diagnostics_for_failed_command(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-commands-") as base:
            root = Path(base)
            (root / "src").mkdir()
            (root / "src" / "app.py").write_text("one\nTwo\nthree\n", encoding="utf-8")

            text = get_run_text(
                root,
                "python3 -c \"import sys; print('ERROR src/app.py:2:5 failed', file=sys.stderr); sys.exit(1)\"",
                timeout_ms=5000,
                max_output_chars=2000,
                context_lines=0,
                max_bytes_per_context=1000,
            )

        self.assertIn("ok: no", text)
        self.assertIn("exitCode: 1", text)
        self.assertIn("outputDiagnostics: 1/1", text)
        self.assertIn("error outputLine=1 src/app.py:2:5", text)
        self.assertIn("outputContexts: 1/1", text)
        self.assertIn("2: Two", text)

    def test_get_run_sequence_text_runs_ordered_commands_and_stops_on_failure(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-commands-") as base:
            root = Path(base)

            ok_text = get_run_sequence_text(
                root,
                "python3 -c \"print('one')\" ;; python3 -c \"print('two')\"",
                timeout_ms=5000,
                max_output_chars=2000,
            )
            failed_text = get_run_sequence_text(
                root,
                "python3 -c \"import sys; sys.exit(3)\" ;; python3 -c \"print('skip')\"",
                timeout_ms=5000,
                max_output_chars=2000,
            )
            continued_text = get_run_sequence_text(
                root,
                "python3 -c \"import sys; sys.exit(3)\" ;; python3 -c \"print('after')\"",
                timeout_ms=5000,
                max_output_chars=2000,
                stop_on_failure=False,
            )
            blocked_text = get_run_sequence_text(root, "sudo reboot ;; python3 --version")
            usage = get_run_sequence_text(root)

        self.assertIn("Run sequence:", ok_text)
        self.assertIn(f"projectRoot: {root.resolve()}", ok_text)
        self.assertIn("ok: yes", ok_text)
        self.assertIn("commands: 2/2", ok_text)
        self.assertIn("stopOnFailure: yes", ok_text)
        self.assertIn("stoppedEarly: no", ok_text)
        self.assertIn("index: 1", ok_text)
        self.assertIn("index: 2", ok_text)
        self.assertIn("one", ok_text)
        self.assertIn("two", ok_text)
        self.assertIn("ok: no", failed_text)
        self.assertIn("commands: 1/2", failed_text)
        self.assertIn("stoppedEarly: yes", failed_text)
        self.assertNotIn("skip", failed_text)
        self.assertIn("commands: 2/2", continued_text)
        self.assertIn("stopOnFailure: no", continued_text)
        self.assertIn("after", continued_text)
        self.assertIn("Command blocked", blocked_text)
        self.assertIn("Usage: /run-seq <cmd> ;; <cmd>", usage)
        self.assertIn("at least one command is required", usage)

    def test_get_run_sequence_text_can_extract_output_contexts(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-commands-") as base:
            root = Path(base)
            (root / "src").mkdir()
            (root / "src" / "app.py").write_text("one\nTwo\nthree\n", encoding="utf-8")

            text = get_run_sequence_text(
                root,
                "python3 -c \"print('src/app.py:2:5: note')\"",
                timeout_ms=5000,
                max_output_chars=2000,
                extract_output_contexts=True,
                context_lines=0,
                max_bytes_per_context=1000,
            )

        self.assertIn("Run sequence:", text)
        self.assertIn("outputContexts: 1/1", text)
        self.assertIn("src/app.py:2:5 [src/app.py:2:5]", text)
        self.assertIn("2: Two", text)

    def test_get_check_run_sequence_text_preflights_ordered_commands(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-commands-") as base:
            root = Path(base)
            (root / "src").mkdir()

            text = get_check_run_sequence_text(root, "python3 --version ;; sudo reboot", cwd="src")
            invalid_cwd = get_check_run_sequence_text(root, "python3 --version", cwd="../outside")
            usage = get_check_run_sequence_text(root)

        self.assertIn("Check run sequence:", text)
        self.assertIn(f"projectRoot: {root.resolve()}", text)
        self.assertIn("ok: no", text)
        self.assertIn("commands: 2/2", text)
        self.assertIn("index: 1", text)
        self.assertIn("command: python3 --version", text)
        self.assertIn("cwd: src", text)
        self.assertIn("executableAvailable: yes", text)
        self.assertIn("index: 2", text)
        self.assertIn("command: sudo reboot", text)
        self.assertIn("blocked: yes", text)
        self.assertIn("high-risk command", text)
        self.assertIn("cwdOk: no", invalid_cwd)
        self.assertIn("escapes", invalid_cwd)
        self.assertIn("Usage: /check-run-seq <cmd> ;; <cmd>", usage)
        self.assertIn("at least one command is required", usage)

    def test_get_check_start_text_reports_preflight_without_starting_process(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-commands-") as base:
            root = Path(base)
            (root / "src").mkdir()

            ok_text = get_check_start_text(root, "python3 -m http.server", cwd="src")
            blocked_text = get_check_start_text(root, "sudo reboot")
            missing_text = get_check_start_text(root, "definitely_missing_vibeagent_tool --version")
            invalid_cwd_text = get_check_start_text(root, "python3 -m http.server", cwd="../outside")
            usage = get_check_start_text(root)

        self.assertIn("Check start:", ok_text)
        self.assertIn(f"projectRoot: {root.resolve()}", ok_text)
        self.assertIn("command: python3 -m http.server", ok_text)
        self.assertIn("cwd: src", ok_text)
        self.assertIn("ok: yes", ok_text)
        self.assertIn("cwdOk: yes", ok_text)
        self.assertIn("blocked: no", ok_text)
        self.assertIn("executableAvailable: yes", ok_text)
        self.assertIn("Check start:", blocked_text)
        self.assertIn("ok: no", blocked_text)
        self.assertIn("blocked: yes", blocked_text)
        self.assertIn("high-risk command", blocked_text)
        self.assertIn("ok: no", missing_text)
        self.assertIn("executableAvailable: no", missing_text)
        self.assertIn("missingTool: definitely_missing_vibeagent_tool", missing_text)
        self.assertIn("ok: no", invalid_cwd_text)
        self.assertIn("cwdOk: no", invalid_cwd_text)
        self.assertIn("escapes", invalid_cwd_text)
        self.assertEqual(usage, "Usage: /check-start <shell command>")

    def test_get_start_text_reports_background_start_or_safety_failure(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-commands-") as base:
            root = Path(base)
            (root / "src").mkdir()

            blocked_text = get_start_text(root, "sudo reboot")
            invalid_cwd_text = get_start_text(root, "python3 -m http.server", cwd="../outside")
            usage = get_start_text(root)

        self.assertIn("Start:", blocked_text)
        self.assertIn(f"projectRoot: {root.resolve()}", blocked_text)
        self.assertIn("command: sudo reboot", blocked_text)
        self.assertIn("ok: no", blocked_text)
        self.assertIn("processId: .", blocked_text)
        self.assertIn("pid: .", blocked_text)
        self.assertIn("Command blocked", blocked_text)
        self.assertIn("ok: no", invalid_cwd_text)
        self.assertIn("escapes", invalid_cwd_text)
        self.assertEqual(usage, "Usage: /start <shell command>")

    def test_get_port_text_reports_reachability_or_usage(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-commands-") as base:
            root = Path(base)
            observation = PortCheckObservation(
                kind="port_check",
                ok=True,
                host="127.0.0.1",
                port=5173,
                timeout_ms=1500,
                reachable=True,
                error=None,
                message="Port is reachable.",
            )
            with patch("vibeagent.commands.execute_action", return_value=observation) as execute_action:
                text = get_port_text(root, "5173 127.0.0.1 1500")
            with patch("vibeagent.commands.execute_action", return_value=observation) as default_host_execute_action:
                get_port_text(root, "5173 2000")

            action = execute_action.call_args.args[1]
            default_host_action = default_host_execute_action.call_args.args[1]
            usage = get_port_text(root)
            invalid = get_port_text(root, "0")
            invalid_timeout = get_port_text(root, "5173 127.0.0.1 soon")

        self.assertIn("Port:", text)
        self.assertIn(f"projectRoot: {root.resolve()}", text)
        self.assertIn("ok: yes", text)
        self.assertIn("host: 127.0.0.1", text)
        self.assertIn("port: 5173", text)
        self.assertIn("reachable: yes", text)
        self.assertIn("timeoutMs: 1500", text)
        self.assertEqual(action.type, "port_check")
        self.assertEqual(action.port, 5173)
        self.assertEqual(action.host, "127.0.0.1")
        self.assertEqual(action.timeout_ms, 1500)
        self.assertEqual(default_host_action.host, "127.0.0.1")
        self.assertEqual(default_host_action.timeout_ms, 2000)
        self.assertIn("Usage: /port <port> [host] [timeout-ms]", usage)
        self.assertIn("port is required", usage)
        self.assertIn("port must be between 1 and 65535", invalid)
        self.assertIn("invalid timeout ms", invalid_timeout)

    def test_get_http_text_reports_status_body_or_usage(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-commands-") as base:
            root = Path(base)
            observation = HttpCheckObservation(
                kind="http_check",
                ok=True,
                url="http://127.0.0.1:5173",
                final_url="http://127.0.0.1:5173/",
                status=200,
                reason="OK",
                timeout_ms=1500,
                reachable=True,
                matched=True,
                matched_pattern="ready",
                body="ready\n",
                body_truncated=False,
                max_body_chars=1000,
                error=None,
                message="HTTP URL is reachable.",
            )
            with patch("vibeagent.commands.execute_action", return_value=observation) as execute_action:
                text = get_http_text(root, "http://127.0.0.1:5173 ready", timeout_ms=1500, max_body_chars=1000)

            action = execute_action.call_args.args[1]
            usage = get_http_text(root)
            invalid = get_http_text(root, "file:///tmp/index.html")
            invalid_contains = get_http_text(root, url="http://127.0.0.1:5173", contains="")

        self.assertIn("HTTP:", text)
        self.assertIn(f"projectRoot: {root.resolve()}", text)
        self.assertIn("ok: yes", text)
        self.assertIn("url: http://127.0.0.1:5173", text)
        self.assertIn("finalUrl: http://127.0.0.1:5173/", text)
        self.assertIn("status: 200", text)
        self.assertIn("matched: yes", text)
        self.assertIn("matchedPattern: ready", text)
        self.assertIn("body:", text)
        self.assertIn("ready", text)
        self.assertEqual(action.type, "http_check")
        self.assertEqual(action.url, "http://127.0.0.1:5173")
        self.assertEqual(action.contains, "ready")
        self.assertEqual(action.timeout_ms, 1500)
        self.assertEqual(action.max_body_chars, 1000)
        self.assertIn("Usage: /http <url> [contains]", usage)
        self.assertIn("url is required", usage)
        self.assertIn("url must be an http or https URL", invalid)
        self.assertIn("contains must be a non-empty string", invalid_contains)

    def test_get_http_fetch_text_reports_status_metadata_body_or_usage(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-commands-") as base:
            root = Path(base)
            observation = HttpFetchObservation(
                kind="http_fetch",
                ok=True,
                url="http://127.0.0.1:5173/app",
                final_url="http://127.0.0.1:5173/app",
                status=200,
                reason="OK",
                content_type="text/html; charset=utf-8",
                timeout_ms=2500,
                reachable=True,
                body="<main>ready</main>\n",
                body_truncated=False,
                max_body_chars=4000,
                error=None,
                message="HTTP URL was fetched.",
            )
            with patch("vibeagent.commands.execute_action", return_value=observation) as execute_action:
                text = get_http_fetch_text(root, "http://127.0.0.1:5173/app", timeout_ms=2500, max_body_chars=4000)

            action = execute_action.call_args.args[1]
            usage = get_http_fetch_text(root)
            invalid = get_http_fetch_text(root, "file:///tmp/index.html")
            extra = get_http_fetch_text(root, "http://127.0.0.1:5173/app extra")
            invalid_body_cap = get_http_fetch_text(root, url="http://127.0.0.1:5173/app", max_body_chars=0)

        self.assertIn("HTTP fetch:", text)
        self.assertIn(f"projectRoot: {root.resolve()}", text)
        self.assertIn("ok: yes", text)
        self.assertIn("url: http://127.0.0.1:5173/app", text)
        self.assertIn("status: 200", text)
        self.assertIn("contentType: text/html; charset=utf-8", text)
        self.assertIn("maxBodyChars: 4000", text)
        self.assertIn("body:", text)
        self.assertIn("<main>ready</main>", text)
        self.assertEqual(action.type, "http_fetch")
        self.assertEqual(action.url, "http://127.0.0.1:5173/app")
        self.assertEqual(action.timeout_ms, 2500)
        self.assertEqual(action.max_body_chars, 4000)
        self.assertIn("Usage: /http-fetch <url>", usage)
        self.assertIn("url is required", usage)
        self.assertIn("url must be an http or https URL", invalid)
        self.assertIn("accepts only one URL", extra)
        self.assertIn("max_body_chars must be at least 1", invalid_body_cap)

    def test_get_overview_text_reports_project_orientation_bundle(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-commands-") as base:
            root = Path(base)
            subprocess.run(["git", "init"], cwd=root, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            (root / "package.json").write_text('{"scripts":{"test":"node test.js","build":"vite build"}}\n', encoding="utf-8")
            (root / "pkg").mkdir()
            (root / "pkg" / "__init__.py").write_text("", encoding="utf-8")
            (root / "tests").mkdir()
            (root / "tests" / "test_app.py").write_text("def test_ok():\n    assert True\n", encoding="utf-8")

            text = get_overview_text(root)

        self.assertIn("Overview:", text)
        self.assertIn(f"projectRoot: {root.resolve()}", text)
        self.assertIn("gitRepo: yes", text)
        self.assertIn("files:", text)
        self.assertIn("commands:", text)
        self.assertIn("manifests:", text)
        self.assertIn("suggestedChecks:", text)
        self.assertIn("tools:", text)
        self.assertIn("npm run test", text)
        self.assertIn("python -m unittest discover -s tests", text)
        self.assertIn("package.json", text)

    def test_get_status_text_reports_local_runtime_state(self) -> None:
        text = get_status_text("chat", "allow", "run-1", chat_turns=2)

        self.assertIn("Status:", text)
        self.assertIn("mode: chat", text)
        self.assertIn("approval: allow", text)
        self.assertIn("resume: run-1", text)
        self.assertIn("chatTurns: 2", text)

    def test_get_context_text_reports_prompt_context_sources(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-commands-") as base:
            root = Path(base)
            (root / "AGENTS.md").write_text("Use unittest.\n", encoding="utf-8")
            (root / "CLAUDE.md").write_text("Keep context short.\n", encoding="utf-8")
            (root / "package.json").write_text('{"scripts":{"test":"node test.js"}}\n', encoding="utf-8")
            (root / "src").mkdir()
            (root / "src" / "app.py").write_text("print('ok')\n", encoding="utf-8")

            text = get_context_text(root, resume_run_id="run-1", resume_context="session: run-1\nfinal: done")

        self.assertIn("Context:", text)
        self.assertIn(f"projectRoot: {root.resolve()}", text)
        self.assertIn("resume: run-1", text)
        self.assertIn("resumeChars:", text)
        self.assertIn("Project instructions:", text)
        self.assertIn("Use unittest.", text)
        self.assertIn("Keep context short.", text)
        self.assertIn("Project command hints:", text)
        self.assertIn("npm run test", text)
        self.assertIn("Workspace snapshot:", text)
        self.assertIn("src/app.py", text)

    def test_init_project_instructions_creates_agents_md_without_overwriting(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-commands-") as base:
            root = Path(base)
            (root / "package.json").write_text('{"scripts":{"test":"node test.js"}}\n', encoding="utf-8")
            (root / "src").mkdir()
            (root / "src" / "app.py").write_text("print('ok')\n", encoding="utf-8")

            created = init_project_instructions(root)
            content = (root / "AGENTS.md").read_text(encoding="utf-8")
            second = init_project_instructions(root)

        self.assertEqual(created, "Created AGENTS.md.")
        self.assertEqual(second, "AGENTS.md already exists; no changes made.")
        self.assertIn("# Repository Guidelines", content)
        self.assertIn("src", content)
        self.assertIn("npm run test", content)
        self.assertIn("Do not commit API keys", content)

    def test_init_project_instructions_creates_claude_md_without_overwriting(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-commands-") as base:
            root = Path(base)
            (root / "pyproject.toml").write_text('[project]\nname = "demo"\n', encoding="utf-8")

            created = init_project_instructions(root, "CLAUDE.md")
            content = (root / "CLAUDE.md").read_text(encoding="utf-8")
            second = init_project_instructions(root, "claude")
            invalid = init_project_instructions(root, "../CLAUDE.md")

        self.assertEqual(created, "Created CLAUDE.md.")
        self.assertEqual(second, "CLAUDE.md already exists; no changes made.")
        self.assertEqual(invalid, "Usage: /init [AGENTS.md|CLAUDE.md]")
        self.assertIn("# Repository Guidelines", content)
        self.assertIn("pyproject.toml", content)
        self.assertFalse((root / "AGENTS.md").exists())

    def test_get_config_text_reports_resolved_config_without_exposing_keys(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-commands-") as base:
            root = Path(base)
            (root / ".vibeagent").mkdir()
            (root / ".vibeagent" / "config.json").write_text(
                json.dumps(
                    {
                        "provider": "deepseek",
                        "model": "deepseek-reasoner",
                        "max_iterations": 12,
                        "command_timeout_ms": 45000,
                        "max_output_tokens": 8192,
                        "model_retries": 0,
                        "model_retry_delay_ms": 0,
                        "model_timeout_ms": 45000,
                    }
                ),
                encoding="utf-8",
            )

            text = get_config_text(
                root,
                {
                    "VIBEAGENT_PROVIDER": "deepseek",
                    "VIBEAGENT_MODEL": "deepseek-reasoner",
                    "OPENAI_COMPAT_API_KEY": "secret-key",
                    "VIBEAGENT_INPUT_USD_PER_MILLION": "1",
                },
            )

        self.assertIn("Config:", text)
        self.assertIn(f"projectRoot: {root.resolve()}", text)
        self.assertIn("projectConfig: yes", text)
        self.assertIn("provider: deepseek", text)
        self.assertIn("model: deepseek-reasoner", text)
        self.assertIn("apiKey: configured via OPENAI_COMPAT_API_KEY", text)
        self.assertIn("maxIterations: 12", text)
        self.assertIn("commandTimeoutMs: 45000", text)
        self.assertIn("maxOutputTokens: 8192", text)
        self.assertIn("modelRetries: 0", text)
        self.assertIn("modelRetryDelayMs: 0", text)
        self.assertIn("modelTimeoutMs: 45000", text)
        self.assertIn("costRates: 1/4 configured", text)
        self.assertNotIn("secret-key", text)

    def test_get_config_text_reads_project_config_when_env_is_omitted(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-commands-") as base:
            root = Path(base)
            (root / ".vibeagent").mkdir()
            (root / ".vibeagent" / "config.json").write_text(
                json.dumps(
                    {
                        "provider": "deepseek",
                        "model": "deepseek-reasoner",
                        "input_usd_per_million": "0.25",
                    }
                ),
                encoding="utf-8",
            )

            with unittest.mock.patch.dict(os.environ, {"OPENAI_COMPAT_API_KEY": "secret-key"}, clear=True):
                text = get_config_text(root)

        self.assertIn("projectConfig: yes", text)
        self.assertIn("provider: deepseek", text)
        self.assertIn("model: deepseek-reasoner", text)
        self.assertIn("apiKey: configured via OPENAI_COMPAT_API_KEY", text)
        self.assertIn("costRates: 1/4 configured", text)
        self.assertNotIn("secret-key", text)

    def test_get_plan_text_reports_newest_or_selected_session_plan(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-commands-") as base:
            root = Path(base)
            write_session_events(
                root,
                "old-run",
                [{"type": "tool_result", "iteration": 1, "result": {"kind": "update_plan", "plan": [{"step": "Old", "status": "completed"}]}}],
                mtime=100,
            )
            write_session_events(
                root,
                "new-run",
                [
                    {"type": "task", "task": "Finish CLI plan command."},
                    {
                        "type": "tool_result",
                        "iteration": 1,
                        "result": {
                            "kind": "update_plan",
                            "plan": [
                                {"step": "Inspect sessions", "status": "completed"},
                                {"step": "Add plan command", "status": "in_progress"},
                            ],
                        },
                    },
                ],
                mtime=200,
            )

            newest = get_plan_text(root)
            selected = get_plan_text(root, "old-run")
            missing = get_plan_text(root, "missing")

        self.assertIn("session: new-run", newest)
        self.assertIn("task: Finish CLI plan command.", newest)
        self.assertIn("completed: Inspect sessions", newest)
        self.assertIn("in_progress: Add plan command", newest)
        self.assertIn("session: old-run", selected)
        self.assertIn("completed: Old", selected)
        self.assertEqual(missing, "Session not found: missing")

    def test_get_transcript_text_reports_newest_or_selected_session_timeline(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-commands-") as base:
            root = Path(base)
            write_session_events(root, "old-run", [{"type": "task", "task": "Old task"}], mtime=100)
            write_session_events(
                root,
                "new-run",
                [
                    {"type": "task", "task": "Old hidden task"},
                    {"type": "task", "task": "New task"},
                ],
                mtime=200,
            )

            newest = get_transcript_text(root, max_events=1, max_text=80)
            selected = get_transcript_text(root, "old-run")
            missing = get_transcript_text(root, "missing")

        self.assertIn("Transcript:", newest)
        self.assertIn("session: new-run", newest)
        self.assertIn("shown: 1/2", newest)
        self.assertIn("older event(s) omitted", newest)
        self.assertIn("New task", newest)
        self.assertNotIn("Old hidden task", newest)
        self.assertIn("session: old-run", selected)
        self.assertIn("Old task", selected)
        self.assertEqual(missing, "Session not found: missing")

    def test_get_session_search_text_reports_newest_or_selected_session_matches(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-commands-") as base:
            root = Path(base)
            write_session_events(root, "old-run", [{"type": "task", "task": "Old missing task"}], mtime=100)
            write_session_events(
                root,
                "new-run",
                [
                    {"type": "task", "task": "New task"},
                    {
                        "type": "tool_call",
                        "iteration": 1,
                        "id": "1",
                        "name": "read_file",
                        "input": {"path": "SECRET_PATH"},
                    },
                    {
                        "type": "tool_result",
                        "iteration": 1,
                        "id": "1",
                        "name": "read_file",
                        "result": {"kind": "read_file", "ok": False, "message": "Missing config file."},
                    },
                    {"type": "task", "task": "missing lowercase task"},
                ],
                mtime=200,
            )

            newest = get_session_search_text(root, "missing", max_matches=1, max_text=80)
            selected = get_session_search_text(root, "--run old-run missing")
            case_sensitive = get_session_search_text(root, "missing", max_matches=10, case_sensitive=True)
            missing = get_session_search_text(root, "missing", "missing")
            usage = get_session_search_text(root)

        self.assertIn("Session search:", newest)
        self.assertIn("session: new-run", newest)
        self.assertIn("shown: 1/", newest)
        self.assertIn("Missing config file.", newest)
        self.assertNotIn("missing lowercase task", newest)
        self.assertNotIn("SECRET_PATH", newest)
        self.assertIn("session: old-run", selected)
        self.assertIn("Old missing task", selected)
        self.assertIn("caseSensitive: yes", case_sensitive)
        self.assertNotIn("Missing config file.", case_sensitive)
        self.assertIn("missing lowercase task", case_sensitive)
        self.assertEqual(missing, "Session not found: missing")
        self.assertEqual(usage, "Usage: /session-search [--run run-id] <query>")

    def test_get_session_commands_text_reports_newest_or_selected_command_outputs(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-commands-") as base:
            root = Path(base)
            write_session_events(
                root,
                "old-run",
                [
                    {
                        "type": "tool_result",
                        "iteration": 1,
                        "name": "run_command",
                        "result": {
                            "kind": "run_command",
                            "result": {
                                "command": "python3 old.py",
                                "exit_code": 0,
                                "stdout": "old ok\n",
                                "stderr": "",
                                "timed_out": False,
                                "signal": None,
                                "cwd": ".",
                            },
                        },
                    }
                ],
                mtime=100,
            )
            write_session_events(
                root,
                "new-run",
                [
                    {
                        "type": "tool_result",
                        "iteration": 1,
                        "name": "run_command",
                        "result": {
                            "kind": "run_command",
                            "result": {
                                "command": "python3 -m unittest",
                                "exit_code": 1,
                                "stdout": "failed\n",
                                "stderr": "traceback\n",
                                "timed_out": False,
                                "signal": None,
                                "cwd": ".",
                            },
                        },
                    }
                ],
                mtime=200,
            )

            newest = get_session_commands_text(root)
            selected = get_session_commands_text(root, "old-run")
            missing = get_session_commands_text(root, "missing")

        self.assertIn("Command results:", newest)
        self.assertIn("session: new-run", newest)
        self.assertIn("python3 -m unittest", newest)
        self.assertIn("failed", newest)
        self.assertIn("session: old-run", selected)
        self.assertIn("python3 old.py", selected)
        self.assertEqual(missing, "Session not found: missing")

    def test_get_session_output_contexts_text_reads_contexts_from_newest_or_selected_session(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-commands-") as base:
            root = Path(base)
            (root / "src").mkdir()
            (root / "src" / "app.py").write_text("one\nTwo\nthree\nfour\n", encoding="utf-8")
            write_session_events(
                root,
                "new-run",
                [
                    {
                        "type": "tool_result",
                        "iteration": 1,
                        "name": "run_command",
                        "result": {
                            "kind": "run_command",
                            "result": {
                                "command": "python3 -m unittest",
                                "exit_code": 1,
                                "stdout": "src/app.py:3:5: failed\n",
                                "stderr": "",
                                "timed_out": False,
                                "signal": None,
                                "cwd": ".",
                            },
                        },
                    }
                ],
                mtime=200,
            )

            newest = get_session_output_contexts_text(root, context_lines=1, max_contexts=10, max_bytes_per_context=1000)
            missing = get_session_output_contexts_text(root, "missing")

        self.assertIn("Session output contexts:", newest)
        self.assertIn("session: new-run", newest)
        self.assertIn("commands: 1/1", newest)
        self.assertIn("contexts: 1/1", newest)
        self.assertIn("Context: src/app.py:3:5", newest)
        self.assertIn("2: Two", newest)
        self.assertIn("3: three", newest)
        self.assertIn("Session not found: missing", missing)

    def test_get_session_output_diagnostics_text_reads_diagnostics_from_newest_or_selected_session(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-commands-") as base:
            root = Path(base)
            (root / "src").mkdir()
            (root / "src" / "app.py").write_text("one\nTwo\nthree\nfour\n", encoding="utf-8")
            write_session_events(
                root,
                "new-run",
                [
                    {
                        "type": "tool_result",
                        "iteration": 1,
                        "name": "run_command",
                        "result": {
                            "kind": "run_command",
                            "result": {
                                "command": "python3 -m unittest",
                                "exit_code": 1,
                                "stdout": "ERROR src/app.py:3:5 failed\n",
                                "stderr": "",
                                "timed_out": False,
                                "signal": None,
                                "cwd": ".",
                            },
                        },
                    }
                ],
                mtime=200,
            )

            newest = get_session_output_diagnostics_text(root, context_lines=1, max_diagnostics=10, max_contexts=10, max_bytes_per_context=1000)
            missing = get_session_output_diagnostics_text(root, "missing")

        self.assertIn("Session output diagnostics:", newest)
        self.assertIn("session: new-run", newest)
        self.assertIn("commands: 1/1", newest)
        self.assertIn("diagnostics: 1/1", newest)
        self.assertIn("error outputLine=", newest)
        self.assertIn("Context: src/app.py:3:5", newest)
        self.assertIn("2: Two", newest)
        self.assertIn("3: three", newest)
        self.assertIn("Session not found: missing", missing)

    def test_get_session_files_text_reports_newest_or_selected_file_references(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-commands-") as base:
            root = Path(base)
            write_session_events(
                root,
                "old-run",
                [{"type": "tool_call", "iteration": 1, "name": "read_file", "input": {"path": "old.py"}}],
                mtime=100,
            )
            write_session_events(
                root,
                "new-run",
                [
                    {
                        "type": "tool_call",
                        "iteration": 1,
                        "name": "write_file",
                        "input": {"path": "src/app.py", "content": "SECRET_CONTENT"},
                    }
                ],
                mtime=200,
            )

            newest = get_session_files_text(root)
            selected = get_session_files_text(root, "old-run")
            missing = get_session_files_text(root, "missing")

        self.assertIn("Session files:", newest)
        self.assertIn("session: new-run", newest)
        self.assertIn("src/app.py", newest)
        self.assertNotIn("SECRET_CONTENT", newest)
        self.assertIn("session: old-run", selected)
        self.assertIn("old.py", selected)
        self.assertEqual(missing, "Session not found: missing")

    def test_get_session_failures_text_reports_newest_or_selected_failures(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-commands-") as base:
            root = Path(base)
            write_session_events(
                root,
                "old-run",
                [{"type": "tool_result", "iteration": 1, "name": "read_file", "result": {"kind": "read_file", "ok": False, "message": "Old missing"}}],
                mtime=100,
            )
            write_session_events(
                root,
                "new-run",
                [
                    {
                        "type": "tool_result",
                        "iteration": 1,
                        "name": "run_command",
                        "result": {
                            "kind": "run_command",
                            "result": {
                                "command": "python3 -m unittest",
                                "exit_code": 1,
                                "stdout": "",
                                "stderr": "AssertionError",
                                "timed_out": False,
                                "signal": None,
                                "cwd": ".",
                            },
                        },
                    }
                ],
                mtime=200,
            )

            newest = get_session_failures_text(root)
            selected = get_session_failures_text(root, "old-run")
            missing = get_session_failures_text(root, "missing")

        self.assertIn("Session failures:", newest)
        self.assertIn("session: new-run", newest)
        self.assertIn("python3 -m unittest", newest)
        self.assertIn("session: old-run", selected)
        self.assertIn("Old missing", selected)
        self.assertEqual(missing, "Session not found: missing")

    def test_get_session_verification_text_reports_newest_or_selected_checks(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-commands-") as base:
            root = Path(base)
            write_session_events(
                root,
                "old-run",
                [
                    {
                        "type": "result",
                        "success": True,
                        "status": "completed",
                        "iterations": 1,
                        "message": "Old result",
                        "verification_checks": ["python3 -m unittest"],
                    }
                ],
                mtime=100,
            )
            write_session_events(
                root,
                "new-run",
                [
                    {
                        "type": "result",
                        "success": True,
                        "status": "completed",
                        "iterations": 1,
                        "message": "New result",
                        "pending_verification_checks": ["npm test", "npm run lint"],
                        "failed_verification_checks": ["npm run build (exit=1)", "mypy . (exit=1)"],
                    }
                ],
                mtime=200,
            )

            newest = get_session_verification_text(root)
            limited = get_session_verification_text(root, max_checks=1)
            selected = get_session_verification_text(root, "old-run")
            missing = get_session_verification_text(root, "missing")

        self.assertIn("Session verification:", newest)
        self.assertIn("pendingChecks: 2/2", newest)
        self.assertIn("npm test", newest)
        self.assertIn("npm run lint", newest)
        self.assertIn("failedChecks:", newest)
        self.assertIn("npm run build (exit=1)", newest)
        self.assertIn("pendingChecks: 1/2", limited)
        self.assertIn("truncated: yes", limited)
        self.assertNotIn("npm run lint", limited)
        self.assertIn("verified:", selected)
        self.assertIn("python3 -m unittest", selected)
        self.assertNotIn("npm test", selected)
        self.assertEqual(missing, "Session not found: missing")

    def test_get_session_audit_text_reports_newest_or_selected_readiness(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-commands-") as base:
            root = Path(base)
            write_session_events(
                root,
                "old-run",
                [
                    {
                        "type": "result",
                        "success": True,
                        "status": "completed",
                        "iterations": 1,
                        "message": "Old done",
                        "verification_checks": ["pytest tests/test_one.py", "pytest tests/test_two.py"],
                        "pending_verification_checks": ["npm test", "npm run build"],
                        "failed_verification_checks": ["ruff check", "mypy ."],
                    }
                ],
                mtime=100,
            )
            write_session_events(
                root,
                "new-run",
                [
                    {"type": "task", "task": "New task"},
                    {
                        "type": "tool_result",
                        "iteration": 1,
                        "name": "run_command",
                        "result": {
                            "kind": "run_command",
                            "result": {
                                "command": "python3 -m unittest",
                                "exit_code": 1,
                                "stdout": "",
                                "stderr": "AssertionError",
                                "timed_out": False,
                                "signal": None,
                                "cwd": ".",
                            },
                        },
                    },
                    {"type": "result", "success": False, "status": "failed", "iterations": 1, "message": "New failed"},
                ],
                mtime=200,
            )
            write_session_events(
                root,
                "local-audit",
                [{"type": "task", "task": "Local audit command"}],
                mtime=300,
            )

            newest = get_session_audit_text(root)
            selected = get_session_audit_text(root, "old-run", max_checks=1)
            missing = get_session_audit_text(root, "missing")

        self.assertIn("Session audit:", newest)
        self.assertIn("session: new-run", newest)
        self.assertNotIn("Local audit command", newest)
        self.assertIn("ready: no", newest)
        self.assertIn("python3 -m unittest", newest)
        self.assertIn("session: old-run", selected)
        self.assertIn("ready: no", selected)
        self.assertIn("verified: 2", selected)
        self.assertIn("pytest tests/test_one.py", selected)
        self.assertNotIn("pytest tests/test_two.py", selected)
        self.assertIn("verifiedChecksOmitted: 1", selected)
        self.assertIn("pending: 2", selected)
        self.assertIn("failed: 2", selected)
        self.assertIn("npm test", selected)
        self.assertNotIn("npm run build", selected)
        self.assertIn("pendingChecksOmitted: 1", selected)
        self.assertIn("ruff check", selected)
        self.assertNotIn("mypy .", selected)
        self.assertIn("failedChecksOmitted: 1", selected)
        self.assertEqual(missing, "Session not found: missing")

    def test_get_session_handoff_text_reports_newest_or_selected_bundle(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-commands-") as base:
            root = Path(base)
            write_session_events(
                root,
                "old-run",
                [{"type": "task", "task": "Old task"}],
                mtime=100,
            )
            write_session_events(
                root,
                "new-run",
                [
                    {"type": "task", "task": "New task"},
                    {
                        "type": "tool_call",
                        "iteration": 1,
                        "name": "write_file",
                        "input": {"path": "src/app.py", "content": "SECRET_CONTENT"},
                    },
                ],
                mtime=200,
            )
            write_session_events(
                root,
                "local-handoff",
                [{"type": "task", "task": "Local handoff command"}],
                mtime=300,
            )

            newest = get_session_handoff_text(root)
            selected = get_session_handoff_text(root, "old-run")
            missing = get_session_handoff_text(root, "missing")

        self.assertIn("Session handoff:", newest)
        self.assertIn("session: new-run", newest)
        self.assertIn("New task", newest)
        self.assertNotIn("Local handoff command", newest)
        self.assertIn("src/app.py", newest)
        self.assertNotIn("SECRET_CONTENT", newest)
        self.assertIn("session: old-run", selected)
        self.assertIn("Old task", selected)
        self.assertEqual(missing, "Session not found: missing")

    def test_get_session_detail_text_respects_limit_options(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-commands-") as base:
            root = Path(base)
            write_session_events(
                root,
                "run-1",
                [
                    {"type": "task", "task": "Limit session views"},
                    {"type": "tool_call", "iteration": 1, "name": "read_file", "input": {"path": "src/one.py"}},
                    {"type": "tool_call", "iteration": 2, "name": "read_file", "input": {"path": "src/two.py"}},
                    {
                        "type": "tool_result",
                        "iteration": 1,
                        "name": "run_command",
                        "result": {
                            "kind": "run_command",
                            "result": {
                                "command": "python3 first.py",
                                "exit_code": 1,
                                "stdout": "first failure output\n",
                                "stderr": "",
                                "timed_out": False,
                                "signal": None,
                                "cwd": ".",
                            },
                        },
                    },
                    {
                        "type": "tool_result",
                        "iteration": 2,
                        "name": "run_command",
                        "result": {
                            "kind": "run_command",
                            "result": {
                                "command": "python3 second.py",
                                "exit_code": 2,
                                "stdout": "second failure output\n",
                                "stderr": "",
                                "timed_out": False,
                                "signal": None,
                                "cwd": ".",
                            },
                        },
                    },
                    {
                        "type": "result",
                        "success": True,
                        "status": "completed",
                        "iterations": 2,
                        "message": "Needs verification.",
                        "verification_checks": ["pytest tests/test_one.py", "pytest tests/test_two.py"],
                        "pending_verification_checks": ["npm test", "npm run build"],
                        "failed_verification_checks": ["ruff check (exit=1)", "mypy . (exit=1)"],
                    },
                ],
            )

            commands = get_session_commands_text(root, "run-1", max_commands=1, max_output_chars=6)
            files = get_session_files_text(root, "run-1", max_files=1)
            failures = get_session_failures_text(root, "run-1", max_failures=1, max_text=80)
            audit = get_session_audit_text(root, "run-1", max_failures=1, max_files=1, max_commands=1, max_text=80)
            handoff = get_session_handoff_text(
                root,
                "run-1",
                max_failures=1,
                max_files=1,
                max_commands=1,
                max_checks=1,
                max_output_chars=6,
                max_text=80,
            )

        self.assertIn("shown: 1/2", commands)
        self.assertIn("older command result(s) omitted", commands)
        self.assertIn("python3 second.py", commands)
        self.assertNotIn("python3 first.py", commands)
        self.assertIn("shown: 1/2", files)
        self.assertIn("src/one.py", files)
        self.assertNotIn("src/two.py", files)
        self.assertIn("shown: 1/2", failures)
        self.assertIn("older failure(s) omitted", failures)
        self.assertIn("python3 second.py", failures)
        self.assertNotIn("python3 first.py", failures)
        self.assertIn("shown: 1/2", audit)
        self.assertIn("python3 second.py", audit)
        self.assertNotIn("python3 first.py", audit)
        self.assertIn("shown: 1/2", handoff)
        self.assertIn("older failure(s) omitted", handoff)
        self.assertIn("older command result(s) omitted", handoff)
        self.assertIn("verified: 1/2", handoff)
        self.assertIn("pendingChecks: 1/2", handoff)
        self.assertIn("failedChecks: 1/2", handoff)
        self.assertIn("truncated: yes", handoff)
        verification_section = handoff.split("  failures:", 1)[0].split("  verification:", 1)[1]
        self.assertNotIn("pytest tests/test_two.py", verification_section)

    def test_checkpoint_commands_create_list_and_show_saved_diffs(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-commands-") as base:
            root = Path(base)
            subprocess.run(["git", "init"], cwd=root, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=root, check=True)
            subprocess.run(["git", "config", "user.name", "Test User"], cwd=root, check=True)
            (root / "app.py").write_text("print('old')\n", encoding="utf-8")
            subprocess.run(["git", "add", "app.py"], cwd=root, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            subprocess.run(["git", "commit", "-m", "initial"], cwd=root, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            (root / "app.py").write_text("print('new')\n", encoding="utf-8")
            (root / "new.txt").write_text("untracked\n", encoding="utf-8")

            created = get_checkpoint_text(root, "before tests")
            checkpoint_id = next(line.split(":", 1)[1].strip() for line in created.splitlines() if line.strip().startswith("id:"))
            listed = get_checkpoints_text(root)
            shown = get_checkpoint_show_text(checkpoint_id, root)
            diff = get_checkpoint_diff_text(checkpoint_id, root)
            matching_status = get_checkpoint_status_text(checkpoint_id, root)
            restore_preview = get_check_checkpoint_restore_text(checkpoint_id, root)
            (root / "app.py").write_text("print('newer')\n", encoding="utf-8")
            changed_status = get_checkpoint_status_text(checkpoint_id, root)
            checkpoint_dir = root / ".vibeagent" / "checkpoints" / checkpoint_id
            metadata = json.loads((checkpoint_dir / "metadata.json").read_text(encoding="utf-8"))
            unstaged_patch = (checkpoint_dir / "unstaged.patch").read_text(encoding="utf-8")
            untracked_manifest_exists = (checkpoint_dir / "untracked_manifest.json").is_file()
            untracked_file_saved = (checkpoint_dir / "untracked_files" / "new.txt").is_file()
            invalid = get_checkpoint_show_text("../bad", root)
            missing = get_checkpoint_show_text("missing", root)

        self.assertIn("Checkpoint:", created)
        self.assertIn("created: yes", created)
        self.assertIn("label: before tests", created)
        self.assertIn("changedFiles: 2", created)
        self.assertIn("unstagedFiles: 1", created)
        self.assertIn("untrackedFiles: 1", created)
        self.assertEqual(metadata["label"], "before tests")
        self.assertIn("head", metadata)
        self.assertIn("-print('old')", unstaged_patch)
        self.assertIn("+print('new')", unstaged_patch)
        self.assertIn("Checkpoints:", listed)
        self.assertIn(checkpoint_id, listed)
        self.assertIn("Checkpoint:", shown)
        self.assertIn(f"id: {checkpoint_id}", shown)
        self.assertIn("gitStatus:", shown)
        self.assertIn("app.py", shown)
        self.assertIn("new.txt", shown)
        self.assertIn("untrackedSavedFiles: 1", shown)
        self.assertIn("untrackedSkippedFiles: 0", shown)
        self.assertIn("savedUntrackedPaths:", shown)
        self.assertIn("    - new.txt", shown)
        self.assertIn("unstaged.patch", shown)
        self.assertIn("Checkpoint diff:", diff)
        self.assertIn("Staged patch:", diff)
        self.assertIn("no staged changes", diff)
        self.assertIn("Unstaged patch:", diff)
        self.assertIn("-print('old')", diff)
        self.assertIn("+print('new')", diff)
        self.assertIn("Checkpoint status:", matching_status)
        self.assertIn("matches: yes", matching_status)
        self.assertIn("statusMatches: yes", matching_status)
        self.assertIn("stagedPatchMatches: yes", matching_status)
        self.assertIn("unstagedPatchMatches: yes", matching_status)
        self.assertIn("untrackedFileMatches: yes", matching_status)
        self.assertIn("Check checkpoint restore:", restore_preview)
        self.assertIn("ok: yes", restore_preview)
        self.assertEqual(metadata["untracked_saved_files"], 1)
        self.assertEqual(metadata["untracked_skipped_files"], 0)
        self.assertTrue(untracked_manifest_exists)
        self.assertTrue(untracked_file_saved)
        self.assertIn("matches: no", changed_status)
        self.assertIn("unstagedPatchMatches: no", changed_status)
        self.assertIn("Current worktree differs from checkpoint.", changed_status)
        self.assertEqual(invalid, "Invalid checkpoint id: ../bad")
        self.assertEqual(missing, "Checkpoint not found: missing")
        self.assertEqual(get_checkpoint_diff_text("../bad", root), "Invalid checkpoint id: ../bad")
        self.assertEqual(get_checkpoint_diff_text("missing", root), "Checkpoint not found: missing")
        self.assertEqual(get_checkpoint_status_text("../bad", root), "Invalid checkpoint id: ../bad")
        self.assertEqual(get_checkpoint_status_text("missing", root), "Checkpoint not found: missing")

    def test_checkpoint_restore_replays_tracked_staged_and_unstaged_diffs(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-commands-") as base:
            root = Path(base)
            subprocess.run(["git", "init"], cwd=root, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=root, check=True)
            subprocess.run(["git", "config", "user.name", "Test User"], cwd=root, check=True)
            (root / "app.py").write_text("base\n", encoding="utf-8")
            subprocess.run(["git", "add", "app.py"], cwd=root, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            subprocess.run(["git", "commit", "-m", "initial"], cwd=root, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            (root / "app.py").write_text("staged\n", encoding="utf-8")
            subprocess.run(["git", "add", "app.py"], cwd=root, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            (root / "app.py").write_text("unstaged\n", encoding="utf-8")

            created = get_checkpoint_text(root, "tracked restore")
            checkpoint_id = next(line.split(":", 1)[1].strip() for line in created.splitlines() if line.strip().startswith("id:"))
            saved_status = get_checkpoint_status_text(checkpoint_id, root)
            (root / "app.py").write_text("broken\n", encoding="utf-8")

            preview = get_check_checkpoint_restore_text(checkpoint_id, root)
            restored = get_checkpoint_restore_text(checkpoint_id, root)
            final_status = get_checkpoint_status_text(checkpoint_id, root)
            final_content = (root / "app.py").read_text(encoding="utf-8")
            staged_diff = subprocess.run(["git", "diff", "--staged"], cwd=root, check=True, stdout=subprocess.PIPE, text=True).stdout
            unstaged_diff = subprocess.run(["git", "diff"], cwd=root, check=True, stdout=subprocess.PIPE, text=True).stdout

        self.assertIn("matches: yes", saved_status)
        self.assertIn("Check checkpoint restore:", preview)
        self.assertIn("ok: yes", preview)
        self.assertIn("Checkpoint restore:", restored)
        self.assertIn("restored: yes", restored)
        self.assertIn("matches: yes", final_status)
        self.assertEqual(final_content, "unstaged\n")
        self.assertIn("+staged", staged_diff)
        self.assertIn("-staged", unstaged_diff)
        self.assertIn("+unstaged", unstaged_diff)

    def test_checkpoint_restore_replays_saved_untracked_files(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-commands-") as base:
            root = Path(base)
            subprocess.run(["git", "init"], cwd=root, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=root, check=True)
            subprocess.run(["git", "config", "user.name", "Test User"], cwd=root, check=True)
            (root / "app.py").write_text("base\n", encoding="utf-8")
            subprocess.run(["git", "add", "app.py"], cwd=root, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            subprocess.run(["git", "commit", "-m", "initial"], cwd=root, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            (root / "app.py").write_text("checkpoint\n", encoding="utf-8")
            (root / "notes.txt").write_text("saved note\n", encoding="utf-8")

            created = get_checkpoint_text(root, "with untracked")
            checkpoint_id = next(line.split(":", 1)[1].strip() for line in created.splitlines() if line.strip().startswith("id:"))
            saved_status = get_checkpoint_status_text(checkpoint_id, root)
            (root / "extra.txt").write_text("extra\n", encoding="utf-8")
            blocked = get_check_checkpoint_restore_text(checkpoint_id, root)
            (root / "extra.txt").unlink()
            (root / "app.py").write_text("broken\n", encoding="utf-8")
            (root / "notes.txt").write_text("dirty note\n", encoding="utf-8")

            changed_status = get_checkpoint_status_text(checkpoint_id, root)
            preview = get_check_checkpoint_restore_text(checkpoint_id, root)
            restored = get_checkpoint_restore_text(checkpoint_id, root)
            final_status = get_checkpoint_status_text(checkpoint_id, root)
            final_app = (root / "app.py").read_text(encoding="utf-8")
            final_note = (root / "notes.txt").read_text(encoding="utf-8")

        self.assertIn("matches: yes", saved_status)
        self.assertIn("untrackedFileMatches: yes", saved_status)
        self.assertIn("ok: no", blocked)
        self.assertIn("extra untracked files", blocked)
        self.assertIn("matches: no", changed_status)
        self.assertIn("untrackedFileMatches: no", changed_status)
        self.assertIn("ok: yes", preview)
        self.assertIn("Checkpoint restore:", restored)
        self.assertIn("restored: yes", restored)
        self.assertIn("matches: yes", final_status)
        self.assertIn("untrackedFileMatches: yes", final_status)
        self.assertEqual(final_app, "checkpoint\n")
        self.assertEqual(final_note, "saved note\n")

    def test_checkpoint_delete_removes_saved_checkpoint(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-commands-") as base:
            root = Path(base)
            subprocess.run(["git", "init"], cwd=root, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=root, check=True)
            subprocess.run(["git", "config", "user.name", "Test User"], cwd=root, check=True)
            (root / "app.py").write_text("base\n", encoding="utf-8")
            subprocess.run(["git", "add", "app.py"], cwd=root, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            subprocess.run(["git", "commit", "-m", "initial"], cwd=root, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            (root / "app.py").write_text("changed\n", encoding="utf-8")

            created = get_checkpoint_text(root, "delete me")
            checkpoint_id = next(line.split(":", 1)[1].strip() for line in created.splitlines() if line.strip().startswith("id:"))
            preview = get_check_checkpoint_delete_text(checkpoint_id, root)
            listed_after_preview = get_checkpoints_text(root)
            deleted = get_checkpoint_delete_text(checkpoint_id, root)
            listed = get_checkpoints_text(root)
            preview_missing = get_check_checkpoint_delete_text(checkpoint_id, root)
            preview_invalid = get_check_checkpoint_delete_text("../bad", root)
            missing = get_checkpoint_delete_text(checkpoint_id, root)
            invalid = get_checkpoint_delete_text("../bad", root)

        self.assertIn("Check checkpoint delete:", preview)
        self.assertIn("canDelete: yes", preview)
        self.assertIn("would remove", preview)
        self.assertIn("total: 1", listed_after_preview)
        self.assertIn("Checkpoint delete:", deleted)
        self.assertIn("deleted: yes", deleted)
        self.assertIn("Deleted checkpoint", deleted)
        self.assertIn("total: 0", listed)
        self.assertIn("canDelete: no", preview_missing)
        self.assertIn("Checkpoint not found", preview_missing)
        self.assertIn("Invalid checkpoint id", preview_invalid)
        self.assertIn("deleted: no", missing)
        self.assertIn("Checkpoint not found", missing)
        self.assertIn("Invalid checkpoint id", invalid)

    def test_checkpoint_prune_previews_and_removes_old_checkpoints(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-commands-") as base:
            root = Path(base)
            subprocess.run(["git", "init"], cwd=root, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=root, check=True)
            subprocess.run(["git", "config", "user.name", "Test User"], cwd=root, check=True)
            (root / "app.py").write_text("base\n", encoding="utf-8")
            subprocess.run(["git", "add", "app.py"], cwd=root, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            subprocess.run(["git", "commit", "-m", "initial"], cwd=root, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            for label in ("one", "two", "three"):
                (root / "app.py").write_text(f"{label}\n", encoding="utf-8")
                get_checkpoint_text(root, label)
                time.sleep(0.002)

            preview = get_check_checkpoint_prune_text("1", root)
            pruned = get_checkpoint_prune_text("1", root)
            listed = get_checkpoints_text(root)
            pruned_all = get_checkpoint_prune_text(0, root)
            listed_after_all = get_checkpoints_text(root)
            invalid = get_checkpoint_prune_text("-1", root)

        self.assertIn("Check checkpoint prune:", preview)
        self.assertIn("deleteCount: 2", preview)
        self.assertIn("checkpoints:", preview)
        self.assertIn("Checkpoint prune:", pruned)
        self.assertIn("deleted: 2", pruned)
        self.assertIn("total: 1", listed)
        self.assertIn("deleted: 1", pruned_all)
        self.assertIn("total: 0", listed_after_all)
        self.assertIn("keep-last must be at least 0", invalid)

    def test_get_doctor_text_reports_local_diagnostics_without_exposing_keys(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-commands-") as base:
            root = Path(base)
            (root / ".git").mkdir()
            (root / "AGENTS.md").write_text("Use unittest.\n", encoding="utf-8")
            (root / "CLAUDE.md").write_text("Use concise output.\n", encoding="utf-8")
            (root / ".vibeagent" / "sessions").mkdir(parents=True)
            (root / ".vibeagent" / "config.json").write_text('{"provider":"minimax"}\n', encoding="utf-8")

            text = get_doctor_text(
                root,
                {
                    "VIBEAGENT_PROVIDER": "minimax",
                    "MINIMAX_API_KEY": "secret-key",
                    "MINIMAX_MODEL": "custom-model",
                    "VIBEAGENT_INPUT_USD_PER_MILLION": "1",
                    "VIBEAGENT_OUTPUT_USD_PER_MILLION": "2",
                },
            )

        self.assertIn("Doctor:", text)
        self.assertIn(f"projectRoot: {root.resolve()}", text)
        self.assertIn("provider: minimax", text)
        self.assertIn("model: custom-model", text)
        self.assertIn("apiKey: configured via MINIMAX_API_KEY", text)
        self.assertIn("sessionsDir: yes", text)
        self.assertIn("projectConfig: yes", text)
        self.assertIn("gitRepo: yes", text)
        self.assertIn("agentsMd: yes", text)
        self.assertIn("claudeMd: yes", text)
        self.assertIn("costRates: 2/4 configured", text)
        self.assertIn("executables:", text)
        self.assertIn("commandHardBlocks: 8/8 active", text)
        self.assertIn("sudo reboot: active", text)
        self.assertIn("code .: active", text)
        self.assertIn("GUI application launch", text)
        self.assertNotIn("secret-key", text)

    def test_get_doctor_report_returns_structured_diagnostics_without_exposing_keys(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-commands-") as base:
            root = Path(base)
            (root / ".vibeagent" / "sessions").mkdir(parents=True)

            report = get_doctor_report(
                root,
                {
                    "VIBEAGENT_PROVIDER": "minimax",
                    "MINIMAX_API_KEY": "secret-key",
                    "MINIMAX_MODEL": "custom-model",
                    "VIBEAGENT_INPUT_USD_PER_MILLION": "1",
                },
            )

        self.assertEqual(report["projectRoot"], str(root.resolve()))
        self.assertTrue(report["sessionsDir"])
        provider = report["provider"]
        self.assertIsInstance(provider, dict)
        self.assertTrue(provider["ok"])
        self.assertEqual(provider["name"], "minimax")
        self.assertEqual(provider["model"], "custom-model")
        self.assertEqual(provider["apiKeySource"], "MINIMAX_API_KEY")
        self.assertNotIn("secret-key", json.dumps(report, ensure_ascii=False))
        cost_rates = report["costRates"]
        self.assertIsInstance(cost_rates, dict)
        self.assertTrue(cost_rates["ok"])
        self.assertEqual(cost_rates["configured"], 1)
        hard_blocks = report["commandHardBlocks"]
        self.assertIsInstance(hard_blocks, dict)
        self.assertEqual(hard_blocks["active"], hard_blocks["total"])
        self.assertTrue(any(check["command"] == "code ." and check["active"] for check in hard_blocks["checks"]))

    def test_get_doctor_text_reports_invalid_provider_and_cost_rates(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-commands-") as base:
            text = get_doctor_text(
                base,
                {
                    "VIBEAGENT_PROVIDER": "unknown",
                    "VIBEAGENT_INPUT_USD_PER_MILLION": "bad",
                },
            )

        self.assertIn("provider: Unsupported VIBEAGENT_PROVIDER: unknown", text)
        self.assertIn("costRates: invalid", text)
        self.assertIn("VIBEAGENT_INPUT_USD_PER_MILLION must be a non-negative decimal.", text)

    def test_get_review_text_reports_current_changes_and_suggested_checks(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-commands-") as base:
            root = Path(base)
            subprocess.run(["git", "init"], cwd=root, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            (root / "package.json").write_text('{"scripts":{"test":"node test.js"}}\n', encoding="utf-8")
            (root / "pkg").mkdir()
            (root / "pkg" / "__init__.py").write_text("", encoding="utf-8")

            text = get_review_text(root)
            limited = get_review_text(root, max_files=1, max_checks=1)

        self.assertIn("Review:", text)
        self.assertIn("changedFiles: 2", text)
        self.assertIn("diffCheck: pass", text)
        self.assertIn("config: pass", text)
        self.assertIn("files:", text)
        self.assertIn("package.json", text)
        self.assertIn("pkg/__init__.py", text)
        self.assertIn("suggestedChecks:", text)
        self.assertIn("npm run test", text)
        self.assertIn("package.json", limited)
        self.assertNotIn("pkg/__init__.py", limited)

        with self.assertRaisesRegex(ValueError, "max_checks must be at most 50"):
            get_review_text(root, max_checks=51)

    def test_get_changes_text_reports_structured_changed_file_summary(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-commands-") as base:
            root = Path(base)
            subprocess.run(["git", "init"], cwd=root, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=root, check=True)
            subprocess.run(["git", "config", "user.name", "Test User"], cwd=root, check=True)
            (root / "app.py").write_text("print('old')\n", encoding="utf-8")
            (root / "staged.py").write_text("print('stage old')\n", encoding="utf-8")
            subprocess.run(["git", "add", "app.py", "staged.py"], cwd=root, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            subprocess.run(["git", "commit", "-m", "initial"], cwd=root, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            (root / "app.py").write_text("print('new')\n", encoding="utf-8")
            (root / "staged.py").write_text("print('stage new')\n", encoding="utf-8")
            subprocess.run(["git", "add", "staged.py"], cwd=root, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            (root / "new.txt").write_text("untracked\n", encoding="utf-8")

            text = get_changes_text(root)
            limited = get_changes_text(root, max_files=1)

        self.assertIn("Changes:", text)
        self.assertIn(f"projectRoot: {root.resolve()}", text)
        self.assertIn("ok: yes", text)
        self.assertIn("changedFiles: 3", text)
        self.assertIn("stagedFiles: 1", text)
        self.assertIn("unstagedFiles: 1", text)
        self.assertIn("untrackedFiles: 1", text)
        self.assertIn("insertions: 2", text)
        self.assertIn("deletions: 2", text)
        self.assertIn("app.py (unstaged, +1, -1)", text)
        self.assertIn("staged.py (staged, +1, -1)", text)
        self.assertIn("new.txt (unstaged, untracked)", text)
        self.assertIn("shownFiles: 1/3", limited)
        self.assertIn("truncated: yes", limited)
        self.assertEqual(limited.count("    - "), 1)
        with self.assertRaisesRegex(ValueError, "max_files must be at most 500"):
            get_changes_text(root, max_files=501)

    def test_get_review_text_reports_syntax_blockers(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-commands-") as base:
            root = Path(base)
            subprocess.run(["git", "init"], cwd=root, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            (root / "bad.py").write_text("def bad(:\n", encoding="utf-8")
            (root / "package.json").write_text("{bad", encoding="utf-8")

            text = get_review_text(root)

        self.assertIn("ready: no", text)
        self.assertIn("blockingIssues:", text)
        self.assertIn("Changed Python files have syntax errors.", text)
        self.assertIn("Changed config files have syntax errors.", text)
        self.assertIn("pythonFailures:", text)
        self.assertIn("bad.py: failed", text)
        self.assertIn("configFailures:", text)
        self.assertIn("package.json: failed", text)

    def test_get_review_text_reports_running_background_processes(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-commands-") as base:
            root = Path(base)
            subprocess.run(["git", "init"], cwd=root, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            observation = ListProcessesObservation(
                kind="list_processes",
                processes=[
                    ProcessInfo(
                        process_id="bg-review",
                        pid=12345,
                        command="npm run dev",
                        cwd=str(root),
                        running=True,
                        exit_code=None,
                        signal=None,
                    )
                ],
                message="Found 1 background process(es).",
            )
            with patch("vibeagent.commands.list_background_processes", return_value=observation):
                text = get_review_text(root)

        self.assertIn("warnings:", text)
        self.assertIn("1 background process(es) still running", text)
        self.assertIn("runningProcesses:", text)
        self.assertIn("bg-review: pid=12345", text)
        self.assertIn("npm run dev", text)

    def test_get_handoff_text_reports_final_review_and_latest_plan(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-commands-") as base:
            root = Path(base)
            subprocess.run(["git", "init"], cwd=root, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            (root / "package.json").write_text('{"scripts":{"test":"node test.js"}}\n', encoding="utf-8")
            (root / "app.py").write_text("print('ok')\n", encoding="utf-8")
            write_session_events(
                root,
                "run-1",
                [
                    {
                        "type": "tool_result",
                        "iteration": 1,
                        "result": {
                            "kind": "update_plan",
                            "plan": [
                                {"step": "Inspect changes", "status": "completed"},
                                {"step": "Run tests", "status": "in_progress"},
                            ],
                        },
                    }
                ],
            )

            text = get_handoff_text(root)
            limited = get_handoff_text(root, max_files=1, max_checks=1, max_status_chars=20, max_plan_chars=20)

        self.assertIn("Handoff:", text)
        self.assertIn(f"projectRoot: {root.resolve()}", text)
        self.assertIn("ready: yes", text)
        self.assertIn("changedFiles: 2", text)
        self.assertIn("files:", text)
        self.assertIn("package.json", text)
        self.assertIn("app.py", text)
        self.assertIn("suggestedChecks:", text)
        self.assertIn("npm run test", text)
        self.assertIn("gitStatus:", text)
        self.assertNotIn(".vibeagent", text)
        self.assertIn("Latest plan:", text)
        self.assertIn("completed: Inspect changes", text)
        self.assertIn("in_progress: Run tests", text)
        self.assertIn("Message: Final review ready:", text)
        self.assertIn("files:", limited)
        self.assertIn("suggestedChecks: 1/", limited)
        self.assertIn("[context output truncated]", limited)

        with self.assertRaisesRegex(ValueError, "max_checks must be at most 50"):
            get_handoff_text(root, max_checks=51)

    def test_get_handoff_text_uses_latest_session_with_plan(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-commands-") as base:
            root = Path(base)
            subprocess.run(["git", "init"], cwd=root, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            write_session_events(
                root,
                "older-run",
                [
                    {
                        "type": "tool_result",
                        "iteration": 1,
                        "result": {
                            "kind": "update_plan",
                            "plan": [{"step": "Keep this plan", "status": "in_progress"}],
                        },
                    }
                ],
            )
            write_session_events(root, "newer-run", [{"type": "task", "task": "No plan"}])
            os.utime(root / ".vibeagent" / "sessions" / "older-run" / "events.jsonl", (100, 100))
            os.utime(root / ".vibeagent" / "sessions" / "newer-run" / "events.jsonl", (200, 200))

            text = get_handoff_text(root)

        self.assertIn("Latest plan:", text)
        self.assertIn("session: older-run", text)
        self.assertIn("in_progress: Keep this plan", text)
        self.assertNotIn("session: newer-run", text)

    def test_get_handoff_text_reports_no_plan_without_plan_sessions(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-commands-") as base:
            root = Path(base)
            subprocess.run(["git", "init"], cwd=root, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            write_session_events(root, "run-1", [{"type": "task", "task": "No plan"}])

            text = get_handoff_text(root)

        self.assertIn("Latest plan:", text)
        self.assertIn("No sessions with plans found.", text)
        self.assertNotIn("session: run-1", text)

    def test_get_handoff_text_reports_running_background_processes(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-commands-") as base:
            root = Path(base)
            observation = FinalReviewObservation(
                kind="final_review",
                ok=True,
                ready=True,
                blocking_issues=[],
                warnings=["1 background process(es) still running; stop them before finishing if no longer needed."],
                running_processes=[
                    ProcessInfo(
                        process_id="bg-handoff",
                        pid=23456,
                        command="python3 -m http.server",
                        cwd=str(root),
                        running=True,
                        exit_code=None,
                        signal=None,
                    )
                ],
                files=[],
                total_files=0,
                suggested_checks=[],
                suggested_checks_total=0,
                suggested_checks_truncated=False,
                diff_check="",
                staged_diff_check="",
                status="",
                message="Final review ready: 0 changed file(s), 0 suggested check(s).",
            )
            with patch("vibeagent.commands.execute_action", return_value=observation):
                text = get_handoff_text(root)

        self.assertIn("warnings:", text)
        self.assertIn("runningProcesses:", text)
        self.assertIn("bg-handoff: pid=23456", text)
        self.assertIn("python3 -m http.server", text)

    def test_get_diff_text_reports_unstaged_or_staged_diff(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-commands-") as base:
            root = Path(base)
            subprocess.run(["git", "init"], cwd=root, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=root, check=True)
            subprocess.run(["git", "config", "user.name", "Test User"], cwd=root, check=True)
            (root / "app.py").write_text("print('old')\n", encoding="utf-8")
            subprocess.run(["git", "add", "app.py"], cwd=root, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            subprocess.run(["git", "commit", "-m", "initial"], cwd=root, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            (root / "app.py").write_text("print('new')\n", encoding="utf-8")
            unstaged = get_diff_text(root, "app.py")
            subprocess.run(["git", "add", "app.py"], cwd=root, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            staged = get_diff_text(root, "--staged app.py")
            truncated = get_diff_text(root, "--staged app.py", max_chars=100)
            invalid = get_diff_text(root, "--bad")

        self.assertIn("Diff:", unstaged)
        self.assertIn("scope: unstaged", unstaged)
        self.assertIn("path: app.py", unstaged)
        self.assertIn("-print('old')", unstaged)
        self.assertIn("+print('new')", unstaged)
        self.assertIn("scope: staged", staged)
        self.assertIn("+print('new')", staged)
        self.assertIn("truncated: yes", truncated)
        self.assertIn("[diff output truncated]", truncated)
        self.assertEqual(invalid, "Usage: /diff [--staged|--cached] [path]")

    def test_get_diff_hunks_text_reports_structured_unstaged_or_staged_hunks(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-commands-") as base:
            root = Path(base)
            subprocess.run(["git", "init"], cwd=root, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=root, check=True)
            subprocess.run(["git", "config", "user.name", "Test User"], cwd=root, check=True)
            (root / "app.py").write_text("first\nold\nlast\n", encoding="utf-8")
            subprocess.run(["git", "add", "app.py"], cwd=root, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            subprocess.run(["git", "commit", "-m", "initial"], cwd=root, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            (root / "app.py").write_text("first\nnew\nlast\n", encoding="utf-8")
            unstaged = get_diff_hunks_text(root, "app.py")
            limited = get_diff_hunks_text(root, "app.py", max_hunks=1, max_lines_per_hunk=1)
            subprocess.run(["git", "add", "app.py"], cwd=root, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            staged = get_diff_hunks_text(root, "--staged app.py")
            invalid = get_diff_hunks_text(root, "--bad")
            bad_limit = get_diff_hunks_text(root, "app.py", max_hunks=501)

        self.assertIn("Diff hunks:", unstaged)
        self.assertIn("ok: yes", unstaged)
        self.assertIn("scope: unstaged", unstaged)
        self.assertIn("path: app.py", unstaged)
        self.assertIn("hunks: 1/1", unstaged)
        self.assertIn("file: app.py", unstaged)
        self.assertIn("added: 1", unstaged)
        self.assertIn("deleted: 1", unstaged)
        self.assertIn("-old", unstaged)
        self.assertIn("+new", unstaged)
        self.assertIn("linesTruncated: yes", limited)
        self.assertIn("scope: staged", staged)
        self.assertIn("+new", staged)
        self.assertEqual(invalid, "Usage: /diff-hunks [--staged|--cached] [--max-hunks N] [--max-lines N] [path]")
        self.assertIn("Error: max_hunks must be at most 500.", bad_limit)

    def test_get_diff_contexts_text_reports_source_context_for_hunks(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-commands-") as base:
            root = Path(base)
            subprocess.run(["git", "init"], cwd=root, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=root, check=True)
            subprocess.run(["git", "config", "user.name", "Test User"], cwd=root, check=True)
            (root / "app.py").write_text("before\nold\nafter\n", encoding="utf-8")
            subprocess.run(["git", "add", "app.py"], cwd=root, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            subprocess.run(["git", "commit", "-m", "initial"], cwd=root, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            (root / "app.py").write_text("before\nnew\nafter\n", encoding="utf-8")

            text = get_diff_contexts_text(root, "app.py", context_lines=1)
            invalid = get_diff_contexts_text(root, "--bad")
            bad_limit = get_diff_contexts_text(root, "app.py", max_bytes_per_context=999)

        self.assertIn("Diff contexts:", text)
        self.assertIn("ok: yes", text)
        self.assertIn("scope: unstaged", text)
        self.assertIn("path: app.py", text)
        self.assertIn("contexts: 1/1", text)
        self.assertIn("contextOk: yes", text)
        self.assertIn("source:", text)
        self.assertIn("2: new", text)
        self.assertEqual(invalid, "Usage: /diff-contexts [--staged|--cached] [--context-lines N] [--max-hunks N] [--max-bytes N] [path]")
        self.assertIn("Error: max_bytes_per_context must be at least 1000.", bad_limit)

    def test_get_usage_text_reports_local_session_usage(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-commands-") as base:
            root = Path(base)
            session_dir = root / ".vibeagent" / "sessions" / "run-1"
            session_dir.mkdir(parents=True)
            (session_dir / "events.jsonl").write_text(
                "\n".join(
                    [
                        json.dumps({"type": "model", "iteration": 1, "content": [{"type": "text", "text": "Done."}]}),
                        json.dumps({"type": "tool_call", "iteration": 1, "name": "read_file", "input": {"path": "SECRET_PATH"}}),
                    ]
                )
                + "\n",
                encoding="utf-8",
            )

            text = get_usage_text(root)

        self.assertIn("Usage:", text)
        self.assertIn("sessions: 1", text)
        self.assertIn("events: 2", text)
        self.assertIn("toolCalls: 1", text)
        self.assertIn("cost: unavailable", text)
        self.assertNotIn("SECRET_PATH", text)

    def test_get_cost_text_estimates_with_env_rates(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-commands-") as base:
            root = Path(base)
            session_dir = root / ".vibeagent" / "sessions" / "run-1"
            session_dir.mkdir(parents=True)
            (session_dir / "events.jsonl").write_text(
                json.dumps(
                    {
                        "type": "model",
                        "iteration": 1,
                        "usage": {"input_tokens": 100, "output_tokens": 50},
                        "content": [{"type": "text", "text": "Done."}],
                    }
                )
                + "\n",
                encoding="utf-8",
            )

            text = get_cost_text(
                root,
                {
                    "VIBEAGENT_INPUT_USD_PER_MILLION": "1",
                    "VIBEAGENT_OUTPUT_USD_PER_MILLION": "2",
                },
            )

        self.assertIn("Cost:", text)
        self.assertIn("estimatedCostUsd: $0.000200", text)

    def test_get_model_text_reports_model_configuration_without_exposing_the_key(self) -> None:
        text = get_model_text(
            {
                "VIBEAGENT_PROVIDER": "minimax",
                "MINIMAX_API_KEY": "secret-key",
                "MINIMAX_MODEL": "custom-model",
                "MINIMAX_BASE_URL": "https://example.com/v1/",
            }
        )

        self.assertIn("Model provider: minimax", text)
        self.assertIn("model: custom-model", text)
        self.assertIn("baseUrl: https://example.com/v1", text)
        self.assertIn("apiKey: configured via MINIMAX_API_KEY", text)
        self.assertNotIn("secret-key", text)

    def test_get_model_text_reports_deepseek_configuration(self) -> None:
        text = get_model_text(
            {
                "VIBEAGENT_PROVIDER": "deepseek",
                "DEEPSEEK_API_KEY": "secret-key",
                "DEEPSEEK_MODEL": "deepseek-reasoner",
            }
        )

        self.assertIn("Model provider: deepseek", text)
        self.assertIn("model: deepseek-reasoner", text)
        self.assertIn("baseUrl: https://api.deepseek.com", text)
        self.assertIn("apiKey: configured via DEEPSEEK_API_KEY", text)
        self.assertNotIn("secret-key", text)

    def test_session_commands_render_compact_session_output(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-commands-") as base:
            root = Path(base)
            session_dir = root / ".vibeagent" / "sessions" / "run-1"
            session_dir.mkdir(parents=True)
            (session_dir / "events.jsonl").write_text(
                "\n".join(
                    [
                        json.dumps({"type": "task", "task": "Build a CLI."}),
                        json.dumps(
                            {
                                "type": "tool_result",
                                "iteration": 1,
                                "name": "finish",
                                "result": {"kind": "finish", "message": "Done."},
                            }
                        ),
                        json.dumps(
                            {
                                "type": "result",
                                "success": True,
                                "status": "completed",
                                "iterations": 1,
                                "message": "Done.",
                                "verification_checks": ["python3 -m unittest", "npm run build"],
                            }
                        ),
                    ]
                )
                + "\n",
                encoding="utf-8",
            )
            os.utime(session_dir / "events.jsonl", (100, 100))
            local_dir = root / ".vibeagent" / "sessions" / "local-handoff"
            local_dir.mkdir(parents=True)
            (local_dir / "events.jsonl").write_text(
                json.dumps({"type": "task", "task": "Local handoff command."}) + "\n",
                encoding="utf-8",
            )
            os.utime(local_dir / "events.jsonl", (200, 200))

            sessions_text = get_sessions_text(root)
            session_text = get_session_text("run-1", root)
            last_text = get_last_session_text(root)
            selected, context, resume_text = get_resume_context(None, root)
            compact_selected, compact_context, compact_text = get_compact_context(None, root)
            limited_selected, limited_context, limited_text = get_compact_context("run-1", root, max_checks=1)

        self.assertIn("run-1", sessions_text)
        self.assertIn("local-handoff", sessions_text)
        self.assertIn("Session: run-1", session_text)
        self.assertIn("status: completed", session_text)
        self.assertIn("task: Build a CLI.", session_text)
        self.assertIn("final: Done.", last_text)
        self.assertNotIn("Local handoff command.", last_text)
        self.assertEqual(selected, "run-1")
        self.assertIn("Resume context:", context or "")
        self.assertIn("sourceSession: run-1", context or "")
        self.assertIn("Historical session evidence for continuation", context or "")
        self.assertIn("Session handoff:", context or "")
        self.assertIn("task: Build a CLI.", context or "")
        self.assertIn("final: Done.", context or "")
        self.assertEqual(resume_text, "Resume context loaded from session run-1.")
        self.assertEqual(compact_selected, "run-1")
        self.assertEqual(compact_context, context)
        self.assertEqual(compact_text, "Compacted context loaded from session run-1.")
        self.assertEqual(limited_selected, "run-1")
        self.assertEqual(limited_text, "Compacted context loaded from session run-1.")
        limited_verification = (limited_context or "").split("  failures:", 1)[0].split("  verification:", 1)[1]
        self.assertIn("verified: 1/2", limited_verification)
        self.assertIn("python3 -m unittest", limited_verification)
        self.assertNotIn("npm run build", limited_verification)

    def test_session_command_requires_run_id(self) -> None:
        self.assertEqual(get_session_text(None), "Usage: /session <run-id>")

    def test_session_command_rejects_path_like_run_id(self) -> None:
        self.assertEqual(get_session_text("../bad"), "Invalid session id: ../bad")
        self.assertEqual(get_resume_context("../bad")[2], "Invalid session id: ../bad")
        self.assertEqual(get_compact_context("../bad")[2], "Invalid session id: ../bad")
        self.assertEqual(get_resume_context("off"), (None, None, "Resume context cleared."))


if __name__ == "__main__":
    unittest.main()
