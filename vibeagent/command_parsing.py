from __future__ import annotations

import shlex

from .command_checkpoint_parsing import parse_checkpoint_local_command
from .command_session_parsing import parse_session_local_command
from .command_types import LocalCommand, make_local_command


def parse_local_command(value: str) -> LocalCommand | None:
    # Recognize slash commands before sending anything to the model.
    trimmed = value.strip()
    if trimmed == "/exit":
        return LocalCommand(type="exit")
    if trimmed == "/help":
        return LocalCommand(type="help")
    if trimmed == "/model":
        return LocalCommand(type="model")
    if trimmed == "/config":
        return LocalCommand(type="config")
    if trimmed == "/tools":
        return LocalCommand(type="tools")
    if trimmed == "/tool" or trimmed.startswith("/tool "):
        return LocalCommand(type="tool", argument=trimmed[5:].strip() or None)
    if trimmed == "/tool-search" or trimmed.startswith("/tool-search "):
        return LocalCommand(type="tool_search", argument=trimmed[13:].strip() or None)
    if trimmed == "/permissions":
        return LocalCommand(type="permissions")
    if trimmed == "/checks" or trimmed.startswith("/checks "):
        return LocalCommand(type="checks", argument=trimmed[8:].strip() or None)
    if trimmed == "/check-suggested-checks" or trimmed.startswith("/check-suggested-checks "):
        return LocalCommand(type="check_suggested_checks", argument=trimmed[23:].strip() or None)
    if trimmed == "/run-suggested-checks" or trimmed.startswith("/run-suggested-checks "):
        return LocalCommand(type="run_suggested_checks", argument=trimmed[21:].strip() or None)
    if trimmed == "/commands" or trimmed.startswith("/commands "):
        return LocalCommand(type="commands", argument=trimmed[10:].strip() or None)
    if trimmed == "/related-tests" or trimmed.startswith("/related-tests "):
        return LocalCommand(type="related_tests", argument=trimmed[14:].strip() or None)
    if trimmed == "/focused-tests" or trimmed.startswith("/focused-tests "):
        return LocalCommand(type="focused_test_commands", argument=trimmed[15:].strip() or None)
    if trimmed == "/check-focused-tests" or trimmed.startswith("/check-focused-tests "):
        return LocalCommand(type="check_focused_test_commands", argument=trimmed[20:].strip() or None)
    if trimmed == "/run-focused-tests" or trimmed.startswith("/run-focused-tests "):
        return LocalCommand(type="run_focused_test_commands", argument=trimmed[18:].strip() or None)
    if trimmed == "/manifests" or trimmed.startswith("/manifests "):
        return LocalCommand(type="manifests", argument=trimmed[11:].strip() or None)
    if trimmed == "/instructions" or trimmed.startswith("/instructions "):
        return LocalCommand(type="instructions", argument=trimmed[14:].strip() or None)
    if trimmed == "/todos" or trimmed.startswith("/todos "):
        return LocalCommand(type="todos", argument=trimmed[7:].strip() or None)
    if trimmed == "/command" or trimmed.startswith("/command "):
        return LocalCommand(type="command", argument=trimmed[8:].strip() or None)
    if trimmed == "/run" or trimmed.startswith("/run "):
        return LocalCommand(type="run", argument=trimmed[5:].strip() or None)
    if trimmed == "/run-commands" or trimmed.startswith("/run-commands "):
        prefix = "/run-commands"
        return LocalCommand(type="run_sequence", argument=trimmed[len(prefix) :].strip() or None)
    if trimmed == "/run-seq" or trimmed.startswith("/run-seq "):
        return LocalCommand(type="run_sequence", argument=trimmed[9:].strip() or None)
    if trimmed == "/check-run-commands" or trimmed.startswith("/check-run-commands "):
        prefix = "/check-run-commands"
        return LocalCommand(type="check_run_sequence", argument=trimmed[len(prefix) :].strip() or None)
    if trimmed == "/check-run-seq" or trimmed.startswith("/check-run-seq "):
        return LocalCommand(type="check_run_sequence", argument=trimmed[15:].strip() or None)
    if trimmed == "/check-start" or trimmed.startswith("/check-start "):
        return LocalCommand(type="check_start", argument=trimmed[13:].strip() or None)
    if trimmed == "/start" or trimmed.startswith("/start "):
        return LocalCommand(type="start", argument=trimmed[7:].strip() or None)
    if trimmed == "/port" or trimmed.startswith("/port "):
        return LocalCommand(type="port", argument=trimmed[6:].strip() or None)
    if trimmed == "/http" or trimmed.startswith("/http "):
        return LocalCommand(type="http", argument=trimmed[6:].strip() or None)
    if trimmed == "/http-fetch" or trimmed.startswith("/http-fetch "):
        return LocalCommand(type="http_fetch", argument=trimmed[12:].strip() or None)
    if trimmed == "/overview" or trimmed.startswith("/overview "):
        return LocalCommand(type="overview", argument=trimmed[10:].strip() or None)
    if trimmed == "/repo-map" or trimmed.startswith("/repo-map "):
        return LocalCommand(type="repo_map", argument=trimmed[9:].strip() or None)
    if trimmed == "/search" or trimmed.startswith("/search "):
        return LocalCommand(type="search", argument=trimmed[7:].strip() or None)
    if trimmed == "/search-contexts" or trimmed.startswith("/search-contexts "):
        return LocalCommand(type="search_contexts", argument=trimmed[16:].strip() or None)
    if trimmed == "/find-files" or trimmed.startswith("/find-files "):
        return LocalCommand(type="find_files", argument=trimmed[12:].strip() or None)
    if trimmed == "/glob" or trimmed.startswith("/glob "):
        return LocalCommand(type="glob", argument=trimmed[6:].strip() or None)
    if trimmed == "/tree" or trimmed.startswith("/tree "):
        return LocalCommand(type="tree", argument=trimmed[6:].strip() or None)
    if trimmed == "/symbols" or trimmed.startswith("/symbols "):
        return LocalCommand(type="symbols", argument=trimmed[9:].strip() or None)
    if trimmed == "/file-info" or trimmed.startswith("/file-info "):
        return LocalCommand(type="file_info", argument=trimmed[11:].strip() or None)
    if trimmed == "/image-info" or trimmed.startswith("/image-info "):
        return LocalCommand(type="image_info", argument=trimmed[12:].strip() or None)
    if trimmed == "/read" or trimmed.startswith("/read "):
        return LocalCommand(type="read", argument=trimmed[6:].strip() or None)
    if trimmed == "/around" or trimmed.startswith("/around "):
        return LocalCommand(type="around", argument=trimmed[8:].strip() or None)
    if trimmed == "/around-many" or trimmed.startswith("/around-many "):
        return LocalCommand(type="around_many", argument=trimmed[13:].strip() or None)
    if trimmed == "/output-contexts" or trimmed.startswith("/output-contexts "):
        return LocalCommand(type="output_contexts", argument=trimmed[16:].strip() or None)
    if trimmed == "/output-diagnostics" or trimmed.startswith("/output-diagnostics "):
        return LocalCommand(type="output_diagnostics", argument=trimmed[19:].strip() or None)
    if trimmed == "/python-traceback" or trimmed.startswith("/python-traceback "):
        return LocalCommand(type="python_traceback", argument=trimmed[17:].strip() or None)
    if trimmed == "/tail" or trimmed.startswith("/tail "):
        return LocalCommand(type="tail", argument=trimmed[6:].strip() or None)
    if trimmed == "/read-files" or trimmed.startswith("/read-files "):
        return LocalCommand(type="read_files", argument=trimmed[12:].strip() or None)
    if trimmed == "/read-ranges" or trimmed.startswith("/read-ranges "):
        return LocalCommand(type="read_ranges", argument=trimmed[13:].strip() or None)
    if trimmed == "/python-check" or trimmed.startswith("/python-check "):
        return LocalCommand(type="python_check", argument=trimmed[14:].strip() or None)
    if trimmed == "/python-deps" or trimmed.startswith("/python-deps "):
        return LocalCommand(type="python_deps", argument=trimmed[13:].strip() or None)
    if trimmed == "/python-defs" or trimmed.startswith("/python-defs "):
        return LocalCommand(type="python_defs", argument=trimmed[13:].strip() or None)
    if trimmed == "/python-refs" or trimmed.startswith("/python-refs "):
        return LocalCommand(type="python_refs", argument=trimmed[13:].strip() or None)
    if trimmed == "/python-ref-contexts" or trimmed.startswith("/python-ref-contexts "):
        return LocalCommand(type="python_ref_contexts", argument=trimmed[21:].strip() or None)
    if trimmed == "/python-calls" or trimmed.startswith("/python-calls "):
        return LocalCommand(type="python_calls", argument=trimmed[14:].strip() or None)
    if trimmed == "/python-call-graph" or trimmed.startswith("/python-call-graph "):
        return LocalCommand(type="python_call_graph", argument=trimmed[19:].strip() or None)
    if trimmed == "/python-rename-preview" or trimmed.startswith("/python-rename-preview "):
        return LocalCommand(type="python_rename_preview", argument=trimmed[23:].strip() or None)
    if trimmed == "/python-rename" or trimmed.startswith("/python-rename "):
        return LocalCommand(type="python_rename", argument=trimmed[15:].strip() or None)
    if trimmed == "/check-replace-python-def" or trimmed.startswith("/check-replace-python-def "):
        return LocalCommand(type="check_replace_python_definition", argument=trimmed[26:].strip() or None)
    if trimmed == "/replace-python-def" or trimmed.startswith("/replace-python-def "):
        return LocalCommand(type="replace_python_definition", argument=trimmed[20:].strip() or None)
    if trimmed == "/config-check" or trimmed.startswith("/config-check "):
        return LocalCommand(type="config_check", argument=trimmed[14:].strip() or None)
    if trimmed == "/check-json-set" or trimmed.startswith("/check-json-set "):
        return LocalCommand(type="check_json_set", argument=trimmed[16:].strip() or None)
    if trimmed == "/json-set" or trimmed.startswith("/json-set "):
        return LocalCommand(type="json_set", argument=trimmed[10:].strip() or None)
    if trimmed == "/check-json-remove" or trimmed.startswith("/check-json-remove "):
        return LocalCommand(type="check_json_remove", argument=trimmed[19:].strip() or None)
    if trimmed == "/json-remove" or trimmed.startswith("/json-remove "):
        return LocalCommand(type="json_remove", argument=trimmed[13:].strip() or None)
    if trimmed == "/check-json-patch" or trimmed.startswith("/check-json-patch "):
        return LocalCommand(type="check_json_patch", argument=trimmed[18:].strip() or None)
    if trimmed == "/json-patch" or trimmed.startswith("/json-patch "):
        return LocalCommand(type="json_patch", argument=trimmed[12:].strip() or None)
    if trimmed == "/check-replace-lines" or trimmed.startswith("/check-replace-lines "):
        return LocalCommand(type="check_replace_lines", argument=trimmed[21:].strip() or None)
    if trimmed == "/replace-lines" or trimmed.startswith("/replace-lines "):
        return LocalCommand(type="replace_lines", argument=trimmed[15:].strip() or None)
    if trimmed == "/check-insert-lines" or trimmed.startswith("/check-insert-lines "):
        return LocalCommand(type="check_insert_lines", argument=trimmed[20:].strip() or None)
    if trimmed == "/insert-lines" or trimmed.startswith("/insert-lines "):
        return LocalCommand(type="insert_lines", argument=trimmed[14:].strip() or None)
    if trimmed == "/check-append" or trimmed.startswith("/check-append "):
        return LocalCommand(type="check_append_file", argument=trimmed[14:].strip() or None)
    if trimmed == "/append" or trimmed.startswith("/append "):
        return LocalCommand(type="append_file", argument=trimmed[8:].strip() or None)
    if trimmed == "/check-write" or trimmed.startswith("/check-write "):
        return LocalCommand(type="check_write_file", argument=trimmed[13:].strip() or None)
    if trimmed == "/write" or trimmed.startswith("/write "):
        return LocalCommand(type="write_file", argument=trimmed[7:].strip() or None)
    if trimmed == "/check-write-files" or trimmed.startswith("/check-write-files "):
        return LocalCommand(type="check_write_files", argument=trimmed[19:].strip() or None)
    if trimmed == "/write-files" or trimmed.startswith("/write-files "):
        return LocalCommand(type="write_files", argument=trimmed[13:].strip() or None)
    if trimmed == "/check-edit" or trimmed.startswith("/check-edit "):
        return LocalCommand(type="check_edit_file", argument=trimmed[12:].strip() or None)
    if trimmed == "/edit" or trimmed.startswith("/edit "):
        return LocalCommand(type="edit_file", argument=trimmed[6:].strip() or None)
    if trimmed == "/check-multi-edit" or trimmed.startswith("/check-multi-edit "):
        return LocalCommand(type="check_multi_edit_file", argument=trimmed[18:].strip() or None)
    if trimmed == "/multi-edit" or trimmed.startswith("/multi-edit "):
        return LocalCommand(type="multi_edit_file", argument=trimmed[12:].strip() or None)
    if trimmed == "/check-delete" or trimmed.startswith("/check-delete "):
        return LocalCommand(type="check_delete_file", argument=trimmed[14:].strip() or None)
    if trimmed == "/delete" or trimmed.startswith("/delete "):
        return LocalCommand(type="delete_file", argument=trimmed[8:].strip() or None)
    if trimmed == "/check-delete-files" or trimmed.startswith("/check-delete-files "):
        return LocalCommand(type="check_delete_files", argument=trimmed[20:].strip() or None)
    if trimmed == "/delete-files" or trimmed.startswith("/delete-files "):
        return LocalCommand(type="delete_files", argument=trimmed[14:].strip() or None)
    if trimmed == "/check-move" or trimmed.startswith("/check-move "):
        return LocalCommand(type="check_move_file", argument=trimmed[12:].strip() or None)
    if trimmed == "/move" or trimmed.startswith("/move "):
        return LocalCommand(type="move_file", argument=trimmed[6:].strip() or None)
    if trimmed == "/check-move-files" or trimmed.startswith("/check-move-files "):
        return LocalCommand(type="check_move_files", argument=trimmed[18:].strip() or None)
    if trimmed == "/move-files" or trimmed.startswith("/move-files "):
        return LocalCommand(type="move_files", argument=trimmed[12:].strip() or None)
    if trimmed == "/check-copy" or trimmed.startswith("/check-copy "):
        return LocalCommand(type="check_copy_file", argument=trimmed[12:].strip() or None)
    if trimmed == "/copy" or trimmed.startswith("/copy "):
        return LocalCommand(type="copy_file", argument=trimmed[6:].strip() or None)
    if trimmed == "/check-copy-files" or trimmed.startswith("/check-copy-files "):
        return LocalCommand(type="check_copy_files", argument=trimmed[18:].strip() or None)
    if trimmed == "/copy-files" or trimmed.startswith("/copy-files "):
        return LocalCommand(type="copy_files", argument=trimmed[12:].strip() or None)
    if trimmed == "/check-move-dir" or trimmed.startswith("/check-move-dir "):
        return LocalCommand(type="check_move_dir", argument=trimmed[16:].strip() or None)
    if trimmed == "/move-dir" or trimmed.startswith("/move-dir "):
        return LocalCommand(type="move_dir", argument=trimmed[10:].strip() or None)
    if trimmed == "/check-move-dirs" or trimmed.startswith("/check-move-dirs "):
        return LocalCommand(type="check_move_dirs", argument=trimmed[17:].strip() or None)
    if trimmed == "/move-dirs" or trimmed.startswith("/move-dirs "):
        return LocalCommand(type="move_dirs", argument=trimmed[11:].strip() or None)
    if trimmed == "/check-copy-dir" or trimmed.startswith("/check-copy-dir "):
        return LocalCommand(type="check_copy_dir", argument=trimmed[16:].strip() or None)
    if trimmed == "/copy-dir" or trimmed.startswith("/copy-dir "):
        return LocalCommand(type="copy_dir", argument=trimmed[10:].strip() or None)
    if trimmed == "/check-copy-dirs" or trimmed.startswith("/check-copy-dirs "):
        return LocalCommand(type="check_copy_dirs", argument=trimmed[17:].strip() or None)
    if trimmed == "/copy-dirs" or trimmed.startswith("/copy-dirs "):
        return LocalCommand(type="copy_dirs", argument=trimmed[11:].strip() or None)
    if trimmed == "/check-mkdir" or trimmed.startswith("/check-mkdir "):
        return LocalCommand(type="check_create_dir", argument=trimmed[13:].strip() or None)
    if trimmed == "/mkdir" or trimmed.startswith("/mkdir "):
        return LocalCommand(type="create_dir", argument=trimmed[7:].strip() or None)
    if trimmed == "/check-mkdirs" or trimmed.startswith("/check-mkdirs "):
        return LocalCommand(type="check_create_dirs", argument=trimmed[14:].strip() or None)
    if trimmed == "/mkdirs" or trimmed.startswith("/mkdirs "):
        return LocalCommand(type="create_dirs", argument=trimmed[8:].strip() or None)
    if trimmed == "/check-rmdir" or trimmed.startswith("/check-rmdir "):
        return LocalCommand(type="check_delete_empty_dir", argument=trimmed[13:].strip() or None)
    if trimmed == "/rmdir" or trimmed.startswith("/rmdir "):
        return LocalCommand(type="delete_empty_dir", argument=trimmed[7:].strip() or None)
    if trimmed == "/check-rmdirs" or trimmed.startswith("/check-rmdirs "):
        return LocalCommand(type="check_delete_empty_dirs", argument=trimmed[14:].strip() or None)
    if trimmed == "/rmdirs" or trimmed.startswith("/rmdirs "):
        return LocalCommand(type="delete_empty_dirs", argument=trimmed[8:].strip() or None)
    if trimmed == "/check-executable" or trimmed.startswith("/check-executable "):
        return LocalCommand(type="check_set_executable", argument=trimmed[18:].strip() or None)
    if trimmed == "/set-executable" or trimmed.startswith("/set-executable "):
        return LocalCommand(type="set_executable", argument=trimmed[16:].strip() or None)
    if trimmed == "/check-patch" or trimmed.startswith("/check-patch "):
        return LocalCommand(type="check_patch", argument=trimmed[13:].strip() or None)
    if trimmed == "/patch" or trimmed.startswith("/patch "):
        return LocalCommand(type="patch_file", argument=trimmed[7:].strip() or None)
    if trimmed == "/check-patches" or trimmed.startswith("/check-patches "):
        return LocalCommand(type="check_patches", argument=trimmed[15:].strip() or None)
    if trimmed == "/patches" or trimmed.startswith("/patches "):
        return LocalCommand(type="patch_files", argument=trimmed[9:].strip() or None)
    if trimmed == "/check-regex-replace" or trimmed.startswith("/check-regex-replace "):
        return LocalCommand(type="check_regex_replace", argument=trimmed[21:].strip() or None)
    if trimmed == "/regex-replace" or trimmed.startswith("/regex-replace "):
        return LocalCommand(type="regex_replace", argument=trimmed[15:].strip() or None)
    if trimmed == "/code-deps" or trimmed.startswith("/code-deps "):
        return LocalCommand(type="code_deps", argument=trimmed[11:].strip() or None)
    if trimmed == "/code-refs" or trimmed.startswith("/code-refs "):
        return LocalCommand(type="code_refs", argument=trimmed[11:].strip() or None)
    if trimmed == "/code-ref-contexts" or trimmed.startswith("/code-ref-contexts "):
        return LocalCommand(type="code_ref_contexts", argument=trimmed[19:].strip() or None)
    if trimmed == "/code-defs" or trimmed.startswith("/code-defs "):
        return LocalCommand(type="code_defs", argument=trimmed[11:].strip() or None)
    if trimmed == "/code-rename-preview" or trimmed.startswith("/code-rename-preview "):
        return LocalCommand(type="code_rename_preview", argument=trimmed[21:].strip() or None)
    if trimmed == "/code-rename" or trimmed.startswith("/code-rename "):
        return LocalCommand(type="code_rename", argument=trimmed[13:].strip() or None)
    if trimmed == "/git-status":
        return LocalCommand(type="git_status")
    if trimmed == "/conflicts" or trimmed.startswith("/conflicts "):
        return LocalCommand(type="git_conflicts", argument=trimmed[10:].strip() or None)
    if trimmed == "/git-info":
        return LocalCommand(type="git_info")
    if trimmed == "/branches":
        return LocalCommand(type="branches")
    if trimmed == "/log" or trimmed.startswith("/log "):
        return LocalCommand(type="log", argument=trimmed[5:].strip() or None)
    if trimmed == "/show" or trimmed.startswith("/show "):
        return LocalCommand(type="show", argument=trimmed[6:].strip() or None)
    if trimmed == "/blame" or trimmed.startswith("/blame "):
        return LocalCommand(type="blame", argument=trimmed[7:].strip() or None)
    if trimmed == "/stashes" or trimmed.startswith("/stashes "):
        return LocalCommand(type="stashes", argument=trimmed[9:].strip() or None)
    if trimmed == "/check-fetch" or trimmed.startswith("/check-fetch "):
        return LocalCommand(type="check_fetch", argument=trimmed[13:].strip() or None)
    if trimmed == "/fetch" or trimmed.startswith("/fetch "):
        return LocalCommand(type="fetch", argument=trimmed[7:].strip() or None)
    if trimmed == "/check-pull":
        return LocalCommand(type="check_pull")
    if trimmed == "/pull":
        return LocalCommand(type="pull")
    if trimmed == "/check-push":
        return LocalCommand(type="check_push")
    if trimmed == "/push":
        return LocalCommand(type="push")
    if trimmed == "/check-stash" or trimmed.startswith("/check-stash "):
        return LocalCommand(type="check_stash", argument=trimmed[13:].strip() or None)
    if trimmed == "/stash" or trimmed.startswith("/stash "):
        return LocalCommand(type="stash", argument=trimmed[7:].strip() or None)
    if trimmed == "/check-stash-apply" or trimmed.startswith("/check-stash-apply "):
        return LocalCommand(type="check_stash_apply", argument=trimmed[19:].strip() or None)
    if trimmed == "/stash-apply" or trimmed.startswith("/stash-apply "):
        return LocalCommand(type="stash_apply", argument=trimmed[13:].strip() or None)
    if trimmed == "/check-stash-drop" or trimmed.startswith("/check-stash-drop "):
        return LocalCommand(type="check_stash_drop", argument=trimmed[18:].strip() or None)
    if trimmed == "/stash-drop" or trimmed.startswith("/stash-drop "):
        return LocalCommand(type="stash_drop", argument=trimmed[12:].strip() or None)
    if trimmed == "/check-stage" or trimmed.startswith("/check-stage "):
        return LocalCommand(type="check_stage", argument=trimmed[13:].strip() or None)
    if trimmed == "/stage" or trimmed.startswith("/stage "):
        return LocalCommand(type="stage", argument=trimmed[7:].strip() or None)
    if trimmed == "/check-unstage" or trimmed.startswith("/check-unstage "):
        return LocalCommand(type="check_unstage", argument=trimmed[15:].strip() or None)
    if trimmed == "/unstage" or trimmed.startswith("/unstage "):
        return LocalCommand(type="unstage", argument=trimmed[9:].strip() or None)
    if trimmed == "/check-commit" or trimmed.startswith("/check-commit "):
        return LocalCommand(type="check_commit", argument=trimmed[14:].strip() or None)
    if trimmed == "/commit" or trimmed.startswith("/commit "):
        return LocalCommand(type="commit", argument=trimmed[8:].strip() or None)
    if trimmed == "/check-restore" or trimmed.startswith("/check-restore "):
        return LocalCommand(type="check_restore", argument=trimmed[15:].strip() or None)
    if trimmed == "/restore" or trimmed.startswith("/restore "):
        return LocalCommand(type="restore", argument=trimmed[9:].strip() or None)
    if trimmed == "/check-switch" or trimmed.startswith("/check-switch "):
        return LocalCommand(type="check_switch", argument=trimmed[14:].strip() or None)
    if trimmed == "/switch" or trimmed.startswith("/switch "):
        return LocalCommand(type="switch", argument=trimmed[8:].strip() or None)
    if trimmed == "/env":
        return LocalCommand(type="env")
    if trimmed == "/processes":
        return LocalCommand(type="processes")
    if trimmed == "/process" or trimmed.startswith("/process "):
        return LocalCommand(type="process", argument=trimmed[9:].strip() or None)
    if trimmed == "/process-output-contexts" or trimmed.startswith("/process-output-contexts "):
        return LocalCommand(type="process_output_contexts", argument=trimmed[24:].strip() or None)
    process_diagnostics_prefix = "/process-output-diagnostics"
    if trimmed == process_diagnostics_prefix or trimmed.startswith(process_diagnostics_prefix + " "):
        return LocalCommand(type="process_output_diagnostics", argument=trimmed[len(process_diagnostics_prefix) :].strip() or None)
    if trimmed == "/wait-process" or trimmed.startswith("/wait-process "):
        return LocalCommand(type="wait_process", argument=trimmed[13:].strip() or None)
    if trimmed == "/check-write-process" or trimmed.startswith("/check-write-process "):
        return LocalCommand(type="check_write_process", argument=trimmed[21:].strip() or None)
    if trimmed == "/write-process" or trimmed.startswith("/write-process "):
        return LocalCommand(type="write_process", argument=trimmed[14:].strip() or None)
    if trimmed == "/check-stop-process" or trimmed.startswith("/check-stop-process "):
        return LocalCommand(type="check_stop_process", argument=trimmed[20:].strip() or None)
    if trimmed == "/stop-process" or trimmed.startswith("/stop-process "):
        return LocalCommand(type="stop_process", argument=trimmed[13:].strip() or None)
    if trimmed == "/check-stop-processes" or trimmed == "/check-stop-all-processes":
        return LocalCommand(type="check_stop_all_processes")
    if trimmed == "/stop-processes" or trimmed == "/stop-all-processes":
        return LocalCommand(type="stop_all_processes")
    if trimmed == "/status":
        return LocalCommand(type="status")
    if trimmed == "/context":
        return LocalCommand(type="context")
    if trimmed == "/init" or trimmed.startswith("/init "):
        return LocalCommand(type="init", argument=trimmed[6:].strip() or None)
    if trimmed == "/doctor":
        return LocalCommand(type="doctor")
    if trimmed == "/review" or trimmed.startswith("/review "):
        return LocalCommand(type="review", argument=trimmed[8:].strip() or None)
    if trimmed == "/handoff" or trimmed.startswith("/handoff "):
        return LocalCommand(type="handoff", argument=trimmed[9:].strip() or None)
    if trimmed == "/changes" or trimmed.startswith("/changes "):
        return LocalCommand(type="changes", argument=trimmed[9:].strip() or None)
    if trimmed == "/diff" or trimmed.startswith("/diff "):
        return LocalCommand(type="diff", argument=trimmed[6:].strip() or None)
    if trimmed == "/diff-hunks" or trimmed.startswith("/diff-hunks "):
        return LocalCommand(type="diff_hunks", argument=trimmed[12:].strip() or None)
    if trimmed == "/diff-contexts" or trimmed.startswith("/diff-contexts "):
        return LocalCommand(type="diff_contexts", argument=trimmed[14:].strip() or None)
    if trimmed == "/clear":
        return LocalCommand(type="clear")
    if trimmed == "/usage":
        return LocalCommand(type="usage")
    if trimmed == "/cost":
        return LocalCommand(type="cost")
    if trimmed == "/approval" or trimmed.startswith("/approval "):
        return LocalCommand(type="approval", argument=trimmed[9:].strip() or None)
    session_command = parse_session_local_command(trimmed)
    if session_command is not None:
        return session_command
    checkpoint_command = parse_checkpoint_local_command(trimmed)
    if checkpoint_command is not None:
        return checkpoint_command
    if trimmed == "/resume" or trimmed.startswith("/resume "):
        return LocalCommand(type="resume", argument=trimmed[8:].strip() or None)
    if trimmed == "/compact" or trimmed.startswith("/compact "):
        return LocalCommand(type="compact", argument=trimmed[9:].strip() or None)
    if trimmed == "/chat" or trimmed.startswith("/chat "):
        return LocalCommand(type="chat", argument=trimmed[5:].strip() or None)
    if trimmed == "/code" or trimmed.startswith("/code "):
        return LocalCommand(type="code", argument=trimmed[5:].strip() or None)
    return None

def parse_local_path_args(argument: str | list[str] | None, max_paths: int) -> list[str]:
    if argument is None:
        return []
    if isinstance(argument, list):
        paths = [path.strip() for path in argument if path.strip()]
    else:
        try:
            paths = shlex.split(argument)
        except ValueError as error:
            raise ValueError(str(error)) from error
    if len(paths) > max_paths:
        raise ValueError(f"expected at most {max_paths} paths.")
    return paths


def parse_optional_single_path_argument(argument: str | None) -> str | None:
    if not argument or not argument.strip():
        return None
    try:
        parts = shlex.split(argument)
    except ValueError as error:
        raise ValueError(str(error)) from error
    if len(parts) > 1:
        raise ValueError("expected at most one path.")
    return parts[0]
