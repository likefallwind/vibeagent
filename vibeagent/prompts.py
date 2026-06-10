from __future__ import annotations

from .types import ChatMessage, Observation
from .workspace import RunWorkspace, read_project_command_hints, read_project_instructions, read_workspace_snapshot


# System prompt defines the tool-use contract for project mode.
SYSTEM_PROMPT = """You are VibeAgent, a project-aware ReAct coding agent.

Use the provided tools only when you need to plan work, inspect the project, search code, edit files, or run commands.
If the user asks a question that can be answered without workspace access, answer directly in text.
When a coding task is complete, either answer directly with a concise summary or call the finish tool.
For multi-step coding tasks, use update_plan to keep a short checklist. Keep exactly one item in_progress while work is active.
Follow project instructions from AGENTS.md when they are provided in the prompt.

All file paths must be relative. Never use absolute paths or "..".
The current project directory is the real workspace. Inspect files before editing existing code.
Use repo_map first for unfamiliar or larger projects when you need a high-level overview of structure and source symbols.
Use read_files to inspect several small related files together. For large files, read focused slices with read_file start_line and line_count, or use read_file_ranges to inspect several focused slices in one call.
Use file_info before reading or editing paths when size, line count, or binary/text status matters.
Use python_symbols to inspect Python module structure before reading large Python files.
Use code_outline to inspect non-Python source structure before reading large JavaScript, TypeScript, Go, Rust, Java, Kotlin, C, or C++ files.
Use environment_info to inspect fixed runtime facts and common tool availability before choosing checks in unfamiliar projects.
Use python_check to validate Python syntax without executing code after Python edits or before slower test runs.
Use config_check to validate JSON and TOML syntax after editing files such as package.json, tsconfig.json, or pyproject.toml.
Use check_json_set before uncertain JSON key updates, then json_set to update one value in an existing JSON file by JSON Pointer instead of string or regex editing when the change is a structured config value. Use check_json_remove before uncertain JSON key or array item removals, then json_remove to remove one value by JSON Pointer. Use check_json_patch before coordinated JSON add, replace, and remove operations in one file, then json_patch to apply them atomically.
Use project_manifests to inspect package.json and pyproject.toml dependencies, scripts, entry points, names, and versions before choosing libraries or framework-specific checks.
Use python_dependencies to inspect Python imports and local/external module dependencies before changing shared Python modules.
Use code_dependencies to inspect imports, includes, and use statements before changing shared JavaScript, TypeScript, Go, Rust, Java, Kotlin, C, or C++ modules.
Use python_definitions to inspect class/function bodies directly when you know the symbol name.
Use code_definitions to inspect non-Python source definitions by exact symbol name before editing shared JavaScript, TypeScript, Go, Rust, Java, Kotlin, C, or C++ code.
Use python_calls to inspect call sites separately from ordinary references when changing callable signatures or behavior.
Use python_call_graph to inspect caller-to-callee relationships in a file or directory before broad refactors.
Use python_references to find Python definitions, imports, and references for one identifier before changing shared symbols.
Use code_references to find non-Python source references for one symbol or literal before changing shared JavaScript, TypeScript, Go, Rust, Java, Kotlin, C, or C++ symbols.
Use python_rename_preview before broad Python renames to inspect the AST-guided diff without writing changes, then use python_rename only after the preview matches the intended scope.
Use project_overview at the start of unfamiliar coding tasks to get a compact project map, git state, manifests, commands, suggested checks, and runtime tool availability in one read-only call.
Use list_tree to inspect directory structure, glob to find files by path pattern, and search to find text inside files.
Use scoped search with path, regex, and case_sensitive options to find symbols or call sites efficiently.
Prefer replace_python_definition, multi_edit_file, regex_replace, replace_lines, insert_lines, append_file, patch_file, patch_files, or edit_file over write_file for existing files. Use replace_python_definition after inspecting a unique Python class/function definition and replacing the full definition is clearer than line edits. Use write_files when creating or replacing several files at once, regex_replace for bounded pattern-based changes in one file, replace_lines after reading a focused line range, insert_lines to add text before a known line, append_file when adding exact text to the end of an existing file, multi_edit_file for several exact replacements in one file, patch_file when several nearby lines need to change, and patch_files for coordinated edits across files or when a unified diff also creates or deletes text files. Use check_write_file or check_write_files before creating or replacing uncertain files. Use check_edit_file before applying uncertain exact replacements. Use check_multi_edit_file before applying complex or uncertain multi_edit_file batches. Use check_replace_python_definition before applying uncertain full Python definition replacements. Use check_replace_lines before applying uncertain line-range replacements. Use check_insert_lines before applying uncertain line insertions. Use check_append_file before appending uncertain text. Use check_regex_replace before applying broad or uncertain regex replacements. Use check_patch or check_patches before applying complex unified diffs when context match is uncertain.
Use create_dir or create_dirs for empty or explicit directories, copy_dir or copy_dirs for copying directory templates or assets, move_dir or move_dirs for directory renames, delete_empty_dir or delete_empty_dirs for removing empty directories, copy_file or copy_files for copying file templates or assets, move_file or move_files for file renames, delete_file or delete_files for removing obsolete files, and set_executable for script executable bits; use check_delete_file or check_delete_files before uncertain file deletions, check_move_file or check_move_files before uncertain file moves, check_copy_file or check_copy_files before uncertain file copies, check_move_dir or check_move_dirs before uncertain directory moves, check_copy_dir or check_copy_dirs before uncertain directory copies, check_create_dir or check_create_dirs before uncertain directory creation, check_delete_empty_dir or check_delete_empty_dirs before uncertain empty-directory deletion, and check_set_executable before uncertain permission changes; do not use shell commands for simple file lifecycle or permission changes.
Use project_overview, git_info, git_status, git_branches, git_changes, git_stashes, review_changes, final_review, git_diff, git_diff_hunks, git_log, git_show, and git_blame to review repository identity, branch/upstream state, local branches, stash entries, changed-file impact, structured hunks, line attribution, pre-final checks, and recent intent before summarizing non-trivial edits. Use final_review before finishing non-trivial code changes to collect blocking issues, warnings, changed files, and suggested verification commands in one read-only report. Use check_git_fetch before uncertain remote synchronization checks, then git_fetch for approved git fetch --prune instead of shelling out to git fetch. Use check_git_pull before updating the current branch from upstream, then git_pull for approved git pull --ff-only instead of shelling out to git pull. Use check_git_push before pushing local commits to upstream, then git_push for approved non-force git push instead of shelling out to git push. Use check_git_switch before uncertain branch switches or new local branches, then git_switch for approved clean-worktree branch changes instead of shelling out to git switch. Use check_git_restore before discarding unstaged tracked-file changes, then git_restore for approved path-scoped git restore instead of shelling out to git restore. Use check_git_stash before saving dirty worktree changes, then git_stash for approved non-runtime git stash push instead of shelling out to git stash. Use check_git_stash_apply before applying an existing stash to a clean worktree, then git_stash_apply for approved git stash apply instead of shelling out to git stash apply; do not drop stash entries automatically. Use check_git_stash_drop before intentionally removing an existing stash entry, then git_stash_drop for approved git stash drop instead of shelling out to git stash drop. Use check_git_stage, check_git_unstage, and check_git_commit before uncertain git-index or local commit changes; use git_stage, git_unstage, and git_commit for approved git-index and local commit changes instead of shelling out to git add, git restore --staged, or git commit.
Use session_summary to inspect the current or a previous local run when recovering context or diagnosing why a task stopped.
Use project_commands to inspect project-defined npm, pyproject, and Makefile commands. Use suggest_checks or discovered project command hints to choose relevant tests, builds, and dev scripts before running verification.
Use command_check before run_command, check_run_commands before run_commands, and check_start_command before start_command when you need to preflight uncertain command cwd, dangerous-command blocks, or executable availability without requesting command execution approval.
Use run_command for one finite check, or run_commands for a short ordered verification sequence such as compile, unit tests, and build; use cwd for subdirectories and timeout_ms for slow tests or builds. Use start_command only for long-running dev servers or watchers, list_processes if you need active process ids, read_process to inspect current output, wait_process to wait briefly for completion or for stdout_contains/stderr_contains readiness output, check_write_process before uncertain write_process calls, write_process to send exact stdin text to an interactive background process, port_check to verify local dev-server ports, http_check to verify local HTTP status, final URL, or response content, check_stop_process before uncertain stop_process calls, and check_stop_all_processes before stop_all_processes when cleaning up several background commands.
Keep tasks small and concrete.
Do not repeat the same list_files action after it already reported an empty directory.
If the directory is empty and the user asks you to create a frontend or website, start writing the needed files.
If the user asks for a file count, use list_files for the relevant path, then answer with the reported total.
If the user asks you to check the result, run an appropriate local command after writing files, then report completion only if it succeeds.
After a relevant check command succeeds, answer with a concise summary on the next turn. Do not keep reading files or running extra checks unless the latest observation shows a concrete error.
Keep each write_file or write_files item content reasonably small so the JSON response is never truncated.
For frontend or website tasks, do not put all HTML, CSS, and JavaScript into one huge file. Create separate files such as index.html, styles.css, and script.js across separate turns.
For frontend or website tasks, write a complete but compact first version instead of an exhaustive long page. Prefer concise sections and reusable CSS classes.
For frontend or website tasks, one successful basic validation is enough: file existence, referenced asset existence, simple HTML parse, or local HTTP 200 checks. After that, answer with a summary.
"""


def build_messages(
    task: str,
    workspace: RunWorkspace,
    observations: list[Observation] | None = None,
    prior_context: str | None = None,
) -> list[ChatMessage]:
    # Assemble initial context for the model: goal and current workspace state.
    snapshot = read_workspace_snapshot(workspace)
    project_instructions = read_project_instructions(workspace)
    command_hints = read_project_command_hints(workspace)
    chunks = [f"User task:\n{task}"]
    if prior_context:
        chunks.append(f"Previous session context:\n{prior_context}")
    if project_instructions:
        chunks.append(
            "\n".join(
                [
                    "Project instructions from AGENTS.md files:",
                    "Apply each file's instructions to its listed scope. More specific scopes override broader ones when they conflict.",
                    project_instructions,
                ]
            )
        )
    if command_hints:
        chunks.append(
            "\n".join(
                [
                    "Project command hints:",
                    "These commands were discovered from project metadata. Prefer them for checks when relevant, and pass the listed Cwd as the command cwd.",
                    command_hints,
                ]
            )
        )
    chunks.extend(
        [
            f"Project directory:\n{workspace.root}",
            f"Session directory:\n{workspace.session_dir}",
            f"Project files:\n{snapshot}",
            get_next_action_instruction(task, observations or []),
        ]
    )
    content = "\n\n".join(chunks)
    return [
        ChatMessage(role="system", content=SYSTEM_PROMPT),
        ChatMessage(role="user", content=content),
    ]


def get_next_action_instruction(task: str, observations: list[Observation]) -> str:
    base = "Choose the next response: call a tool if needed, or answer directly if the task is complete."
    if not observations:
        return base

    latest = observations[-1]
    if latest.kind == "run_command":
        result = latest.result
        if result.exit_code == 0 and not result.timed_out:
            return (
                f"{base} The latest command succeeded. If it checked the requested work, your next action must be "
                "a concise final answer. Do not run another check unless the output contains a concrete error."
            )
        return f"{base} The latest command failed or timed out, so fix the concrete error before finishing."

    if latest.kind == "start_command":
        if latest.ok:
            return f"{base} The background command started. Use read_process or wait_process with process_id={latest.process_id} to inspect readiness or prompts."
        return f"{base} The background command did not start, so fix the concrete error before finishing."

    if latest.kind == "read_process":
        if latest.ok and latest.running:
            return f"{base} Use the process output to continue, write_process if the process is waiting for input, or stop_process if it is no longer needed."
        if latest.ok:
            return f"{base} The background command exited. Use its output to decide whether to fix issues or answer directly."
        return f"{base} The process could not be read, so use a valid process id or choose another useful action."

    if latest.kind == "list_processes":
        return f"{base} Use a listed process id with read_process, wait_process, write_process, or stop_process; use check_stop_all_processes if cleaning up all background commands."

    if latest.kind == "check_write_process":
        if latest.ok:
            return f"{base} The process can receive stdin. Use write_process only if sending that input is necessary."
        return f"{base} The process cannot receive stdin, so inspect its output or choose another useful action."

    if latest.kind == "write_process":
        if latest.ok:
            return f"{base} Input was sent. Use wait_process or read_process to inspect the result."
        return f"{base} Input was not sent, so inspect the process state or choose another useful action."

    if latest.kind == "stop_process":
        return f"{base} The background process was stopped. Continue with the next check or answer directly if the task is complete."

    if latest.kind == "stop_all_processes":
        return f"{base} All tracked background processes were stopped. Continue with the next check or answer directly if the task is complete."

    if latest.kind in {
        "read_file",
        "read_files",
        "read_file_ranges",
        "file_info",
        "repo_map",
        "python_symbols",
        "code_outline",
        "python_check",
        "config_check",
        "check_json_set",
        "check_json_remove",
        "check_json_patch",
        "python_dependencies",
        "code_dependencies",
        "code_references",
        "code_definitions",
        "python_definitions",
        "python_calls",
        "python_call_graph",
        "python_references",
        "python_rename_preview",
        "project_commands",
        "git_branches",
        "check_git_fetch",
        "check_git_pull",
        "check_git_push",
        "check_git_restore",
        "git_stashes",
        "check_git_stash",
        "check_git_stash_apply",
        "check_git_stash_drop",
        "check_git_switch",
        "final_review",
        "command_check",
        "check_run_commands",
        "check_start_command",
        "port_check",
        "http_check",
        "wait_process",
        "check_write_process",
        "check_stop_all_processes",
        "check_stop_process",
        "environment_info",
        "list_files",
        "list_tree",
        "glob",
    }:
        return (
            f"{base} Do not repeat inspection unless you need specific missing information. "
            "If you already created the requested files, run one appropriate check or answer directly if the task is complete."
        )

    if latest.kind in {
        "git_info",
        "git_status",
        "git_branches",
        "check_git_fetch",
        "git_fetch",
        "check_git_pull",
        "git_pull",
        "check_git_push",
        "git_push",
        "check_git_restore",
        "git_restore",
        "git_stashes",
        "check_git_stash",
        "git_stash",
        "check_git_stash_apply",
        "git_stash_apply",
        "check_git_stash_drop",
        "git_stash_drop",
        "check_git_switch",
        "git_switch",
        "git_changes",
        "review_changes",
        "final_review",
        "suggest_checks",
        "project_commands",
        "project_manifests",
        "command_check",
        "check_start_command",
        "port_check",
        "http_check",
        "wait_process",
        "check_write_process",
        "check_stop_all_processes",
        "check_stop_process",
        "environment_info",
        "git_diff",
        "git_diff_hunks",
        "git_log",
        "git_show",
        "git_blame",
        "session_summary",
    }:
        return f"{base} Use the repository or session information to decide whether to continue, run a check, or answer directly."

    if latest.kind in {
        "check_patch",
        "check_patches",
        "check_regex_replace",
        "check_write_file",
        "check_write_files",
        "check_edit_file",
        "check_multi_edit_file",
        "check_replace_python_definition",
        "check_replace_lines",
        "check_insert_lines",
        "check_append_file",
        "check_json_set",
        "check_json_remove",
        "check_json_patch",
        "check_delete_file",
        "check_delete_files",
        "check_move_file",
        "check_move_files",
        "check_copy_file",
        "check_copy_files",
        "check_move_dir",
        "check_move_dirs",
        "check_copy_dir",
        "check_copy_dirs",
        "check_create_dir",
        "check_create_dirs",
        "check_delete_empty_dir",
        "check_delete_empty_dirs",
        "check_set_executable",
        "check_git_stage",
        "check_git_unstage",
        "check_git_commit",
        "check_run_commands",
    }:
        if latest.ok:
            return f"{base} The dry-run succeeded. Apply it if the diff or validation result matches the requested change, or continue with the next required step."
        return f"{base} The dry-run failed, so fix the context or choose another edit tool before applying changes."

    if latest.kind in {"project_overview", "write_file", "write_files", "edit_file", "multi_edit_file", "replace_python_definition", "python_rename", "regex_replace", "json_set", "json_remove", "json_patch", "replace_lines", "insert_lines", "append_file", "patch_file", "patch_files", "delete_file", "delete_files", "move_file", "move_files", "copy_file", "copy_files", "move_dir", "move_dirs", "copy_dir", "copy_dirs", "create_dir", "create_dirs", "delete_empty_dir", "delete_empty_dirs", "set_executable", "git_fetch", "git_pull", "git_push", "git_restore", "git_stash", "git_stash_apply", "git_stash_drop", "git_switch", "git_stage", "git_unstage", "git_commit", "run_commands"}:
        return f"{base} Continue with the next required file, run one appropriate check, or answer directly if the task is complete."

    if latest.kind == "update_plan":
        return f"{base} Continue with the current in-progress plan item, or update the plan again if the work changed."

    return f"{base} If the task is complete, answer directly or use finish."


def format_observations(observations: list[Observation]) -> str:
    # Serialize prior observations in compact human-readable lines for next-turn reasoning.
    if not observations:
        return "No observations yet."

    lines: list[str] = []
    for index, observation in enumerate(observations, start=1):
        if observation.kind == "check_write_file":
            lines.append(
                "\n".join(
                    [
                        f"{index}. check_write_file {observation.path}: {observation.message}",
                        f"diff:\n{truncate(observation.diff)}",
                    ]
                )
            )
        elif observation.kind == "write_file":
            lines.append(f"{index}. write_file {observation.path}: {observation.message}")
        elif observation.kind == "check_write_files":
            parts = [f"{index}. check_write_files: {observation.message} ok={str(observation.ok).lower()}"]
            for file in observation.files:
                parts.append(
                    "\n".join(
                        [
                            f"file: {file.path} ok={str(file.ok).lower()} message={file.message}",
                            f"diff:\n{truncate(file.diff)}",
                        ]
                    )
                )
            lines.append("\n".join(parts))
        elif observation.kind == "write_files":
            parts = [f"{index}. write_files: {observation.message} ok={str(observation.ok).lower()}"]
            for file in observation.files:
                parts.append(f"file: {file.path} ok={str(file.ok).lower()} message={file.message}")
            lines.append("\n".join(parts))
        elif observation.kind == "list_files":
            lines.append(
                "\n".join(
                    [
                        f"{index}. list_files {observation.path}: {observation.message}",
                        *observation.files[:120],
                    ]
                )
            )
        elif observation.kind == "list_tree":
            lines.append(
                "\n".join(
                    [
                        (
                            f"{index}. list_tree {observation.path}: {observation.message} "
                            f"maxDepth={observation.max_depth} truncated={str(observation.truncated).lower()}"
                        ),
                        *observation.entries[:160],
                    ]
                )
            )
        elif observation.kind == "repo_map":
            parts = [
                (
                    f"{index}. repo_map {observation.path}: {observation.message} "
                    f"files={len(observation.files)}/{observation.total_files} "
                    f"treeEntries={len(observation.tree)}/{observation.total_tree_entries} "
                    f"truncated={str(observation.truncated).lower()}"
                )
            ]
            if observation.tree:
                parts.append("tree:\n" + "\n".join(observation.tree[:120]))
            if observation.files:
                parts.append("files:\n" + "\n".join(observation.files[:120]))
            for file in observation.python_files[:40]:
                parts.append(f"python: {file.path} ok={str(file.ok).lower()} message={file.message}")
                if file.imports:
                    parts.append("imports:\n" + "\n".join(file.imports[:20]))
                if file.symbols:
                    parts.append(
                        "symbols:\n"
                        + "\n".join(
                            (
                                f"- {symbol.kind} {symbol.name} "
                                f"line={symbol.line} parent={symbol.parent or '.'}"
                            )
                            for symbol in file.symbols[:60]
                        )
                    )
            for file in [item for item in observation.code_files if item.language != "python"][:40]:
                parts.append(
                    (
                        f"source: {file.path} language={file.language or '.'} "
                        f"ok={str(file.ok).lower()} message={file.message}"
                    )
                )
                if file.imports:
                    parts.append("imports:\n" + "\n".join(file.imports[:20]))
                if file.symbols:
                    parts.append(
                        "symbols:\n"
                        + "\n".join(
                            (
                                f"- {symbol.kind} {symbol.name} "
                                f"line={symbol.line} parent={symbol.parent or '.'}"
                            )
                            for symbol in file.symbols[:60]
                        )
                    )
            lines.append("\n".join(parts))
        elif observation.kind == "read_file":
            lines.append(
                "\n".join(
                    [
                        (
                            f"{index}. read_file {observation.path}: {observation.message} "
                            f"truncated={str(observation.truncated).lower()} "
                            f"bytes={observation.total_bytes if observation.total_bytes is not None else 'unknown'} "
                            f"maxBytes={observation.max_bytes}"
                        ),
                        f"content:\n{truncate(observation.content)}",
                    ]
                )
            )
        elif observation.kind == "read_files":
            parts = [f"{index}. read_files: {observation.message}"]
            for file in observation.files:
                byte_count = file.total_bytes if file.total_bytes is not None else "unknown"
                parts.append(
                    (
                        f"file: {file.path} ok={str(file.ok).lower()} "
                        f"truncated={str(file.truncated).lower()} bytes={byte_count} "
                        f"maxBytes={file.max_bytes} message={file.message}"
                    )
                )
                if file.ok:
                    parts.append(f"content:\n{truncate(file.content)}")
            lines.append("\n".join(parts))
        elif observation.kind == "read_file_ranges":
            parts = [f"{index}. read_file_ranges: {observation.message}"]
            for item in observation.ranges:
                parts.append(
                    (
                        f"range: {item.path}:{item.start_line}+{item.line_count} "
                        f"ok={str(item.ok).lower()} message={item.message}"
                    )
                )
                if item.ok:
                    parts.append(f"content:\n{truncate(item.content)}")
            lines.append("\n".join(parts))
        elif observation.kind == "file_info":
            parts = [f"{index}. file_info: {observation.message}"]
            for file in observation.files:
                size = "unknown" if file.size_bytes is None else str(file.size_bytes)
                line_count = "unknown" if file.line_count is None else str(file.line_count)
                binary = "unknown" if file.is_binary is None else str(file.is_binary).lower()
                parts.append(
                    (
                        f"file: {file.path} ok={str(file.ok).lower()} exists={str(file.exists).lower()} "
                        f"isFile={str(file.is_file).lower()} isDir={str(file.is_dir).lower()} "
                        f"sizeBytes={size} lineCount={line_count} binary={binary} message={file.message}"
                    )
                )
            lines.append("\n".join(parts))
        elif observation.kind == "python_symbols":
            parts = [f"{index}. python_symbols: {observation.message}"]
            for file in observation.files:
                parts.append(f"file: {file.path} ok={str(file.ok).lower()} message={file.message}")
                if file.imports:
                    parts.append("imports:\n" + "\n".join(file.imports[:40]))
                if file.symbols:
                    parts.append(
                        "symbols:\n"
                        + "\n".join(
                            (
                                f"- {symbol.kind} {symbol.name} "
                                f"line={symbol.line} endLine={symbol.end_line or 'unknown'} "
                                f"parent={symbol.parent or '.'}"
                            )
                            for symbol in file.symbols[:120]
                        )
                    )
            lines.append("\n".join(parts))
        elif observation.kind == "code_outline":
            parts = [f"{index}. code_outline: {observation.message}"]
            for file in observation.files:
                parts.append(
                    (
                        f"file: {file.path} language={file.language or '.'} "
                        f"ok={str(file.ok).lower()} message={file.message}"
                    )
                )
                if file.imports:
                    parts.append("imports:\n" + "\n".join(file.imports[:40]))
                if file.symbols:
                    parts.append(
                        "symbols:\n"
                        + "\n".join(
                            (
                                f"- {symbol.kind} {symbol.name} "
                                f"line={symbol.line} parent={symbol.parent or '.'}"
                            )
                            for symbol in file.symbols[:120]
                        )
                    )
            lines.append("\n".join(parts))
        elif observation.kind == "python_check":
            parts = [
                (
                    f"{index}. python_check {observation.path or '.'}: {observation.message} "
                    f"checked={len(observation.files)}/{observation.total} "
                    f"truncated={str(observation.truncated).lower()}"
                )
            ]
            for file in observation.files[:120]:
                location = ""
                if file.line is not None:
                    location = f" line={file.line} column={file.column or 'unknown'}"
                parts.append(f"file: {file.path} ok={str(file.ok).lower()}{location} message={file.message}")
            lines.append("\n".join(parts))
        elif observation.kind == "config_check":
            parts = [
                (
                    f"{index}. config_check {observation.path or '.'}: {observation.message} "
                    f"checked={len(observation.files)}/{observation.total} "
                    f"truncated={str(observation.truncated).lower()}"
                )
            ]
            for file in observation.files[:120]:
                location = ""
                if file.line is not None:
                    location = f" line={file.line} column={file.column or 'unknown'}"
                parts.append(
                    (
                        f"file: {file.path} format={file.format} ok={str(file.ok).lower()}"
                        f"{location} message={file.message}"
                    )
                )
            lines.append("\n".join(parts))
        elif observation.kind == "python_dependencies":
            parts = [
                (
                    f"{index}. python_dependencies {observation.path or '.'}: {observation.message} "
                    f"files={len(observation.files)}/{observation.total} "
                    f"truncated={str(observation.truncated).lower()}"
                )
            ]
            for file in observation.files[:80]:
                parts.append(
                    (
                        f"file: {file.path} module={file.module or '.'} ok={str(file.ok).lower()} "
                        f"local={','.join(file.local_modules[:20]) or '-'} "
                        f"external={','.join(file.external_modules[:20]) or '-'} "
                        f"message={file.message}"
                    )
                )
                for import_ref in file.imports[:80]:
                    parts.append(
                        (
                            f"import: line={import_ref.line} kind={import_ref.kind} "
                            f"module={import_ref.module or '.'} name={import_ref.name or '-'} "
                            f"target={import_ref.target or '.'} local={str(import_ref.local).lower()}"
                        )
                    )
            lines.append("\n".join(parts))
        elif observation.kind == "code_dependencies":
            parts = [
                (
                    f"{index}. code_dependencies {observation.path or '.'}: {observation.message} "
                    f"files={len(observation.files)}/{observation.total} "
                    f"truncated={str(observation.truncated).lower()}"
                )
            ]
            for file in observation.files[:80]:
                parts.append(
                    (
                        f"file: {file.path} language={file.language} ok={str(file.ok).lower()} "
                        f"dependencies={','.join(file.dependencies[:40]) or '-'} "
                        f"message={file.message}"
                    )
                )
                for import_ref in file.imports[:80]:
                    parts.append(
                        (
                            f"import: line={import_ref.line} kind={import_ref.kind} "
                            f"source={import_ref.source or '.'} raw={import_ref.raw}"
                        )
                    )
            lines.append("\n".join(parts))
        elif observation.kind == "code_references":
            parts = [
                (
                    f"{index}. code_references {observation.symbol}: {observation.message} "
                    f"shown={len(observation.references)}/{observation.total} "
                    f"path={observation.path or '.'} "
                    f"truncated={str(observation.truncated).lower()}"
                )
            ]
            for reference in observation.references[:160]:
                parts.append(
                    (
                        f"reference: {reference.path}:{reference.line}:{reference.column} "
                        f"language={reference.language} context={reference.context}"
                    )
                )
            lines.append("\n".join(parts))
        elif observation.kind == "code_definitions":
            parts = [
                (
                    f"{index}. code_definitions {observation.symbol}: {observation.message} "
                    f"path={observation.path or '.'} truncated={str(observation.truncated).lower()}"
                )
            ]
            for definition in observation.definitions[:80]:
                parts.append(
                    (
                        f"definition: {definition.path}:{definition.line}-{definition.end_line} "
                        f"language={definition.language} {definition.kind} {definition.name} "
                        f"truncated={str(definition.truncated).lower()}"
                    )
                )
                parts.append("content:\n" + truncate(definition.content))
            if observation.errors:
                parts.append("errors:\n" + "\n".join(observation.errors[:20]))
            lines.append("\n".join(parts))
        elif observation.kind == "python_definitions":
            parts = [
                (
                    f"{index}. python_definitions {observation.symbol}: {observation.message} "
                    f"path={observation.path or '.'} truncated={str(observation.truncated).lower()}"
                )
            ]
            for definition in observation.definitions[:80]:
                parts.append(
                    (
                        f"definition: {definition.path}:{definition.line}-{definition.end_line} "
                        f"{definition.kind} {definition.qualified_name} "
                        f"truncated={str(definition.truncated).lower()}"
                    )
                )
                parts.append("content:\n" + truncate(definition.content))
            if observation.errors:
                parts.append("errors:\n" + "\n".join(observation.errors[:20]))
            lines.append("\n".join(parts))
        elif observation.kind == "python_calls":
            parts = [
                (
                    f"{index}. python_calls {observation.symbol}: {observation.message} "
                    f"path={observation.path or '.'} truncated={str(observation.truncated).lower()}"
                )
            ]
            for call in observation.calls[:120]:
                parts.append(
                    (
                        f"{call.path}:{call.line}:{call.column}: "
                        f"caller={call.caller or '.'} callee={call.callee} {call.context}"
                    )
                )
            if observation.errors:
                parts.append("errors:\n" + "\n".join(observation.errors[:20]))
            lines.append("\n".join(parts))
        elif observation.kind == "python_call_graph":
            parts = [
                (
                    f"{index}. python_call_graph {observation.path or '.'}: {observation.message} "
                    f"truncated={str(observation.truncated).lower()}"
                )
            ]
            for edge in observation.edges[:160]:
                parts.append(
                    (
                        f"{edge.path}:{edge.line}:{edge.column}: "
                        f"caller={edge.caller or '.'} callee={edge.callee} {edge.context}"
                    )
                )
            if observation.errors:
                parts.append("errors:\n" + "\n".join(observation.errors[:20]))
            lines.append("\n".join(parts))
        elif observation.kind == "python_references":
            parts = [
                (
                    f"{index}. python_references {observation.symbol}: {observation.message} "
                    f"path={observation.path or '.'} truncated={str(observation.truncated).lower()}"
                )
            ]
            for reference in observation.references[:160]:
                parts.append(
                    (
                        f"{reference.path}:{reference.line}:{reference.column}: "
                        f"{reference.kind} {reference.context}"
                    )
                )
            if observation.errors:
                parts.append("errors:\n" + "\n".join(observation.errors[:20]))
            lines.append("\n".join(parts))
        elif observation.kind == "python_rename_preview":
            parts = [
                (
                    f"{index}. python_rename_preview {observation.symbol}->{observation.new_name}: "
                    f"{observation.message} path={observation.path or '.'} "
                    f"files={len(observation.files)}/{observation.total_files} "
                    f"replacements={observation.total_replacements} "
                    f"truncated={str(observation.truncated).lower()}"
                )
            ]
            for file in observation.files[:40]:
                parts.append(
                    (
                        f"file: {file.path} replacements={len(file.replacements)} "
                        f"truncated={str(file.truncated).lower()}"
                    )
                )
                for replacement in file.replacements[:80]:
                    parts.append(
                        (
                            f"replace: {replacement.path}:{replacement.line}:{replacement.column}-"
                            f"{replacement.end_column} kind={replacement.kind} "
                            f"{replacement.old}->{replacement.new} {replacement.context}"
                        )
                    )
                parts.append(f"diff:\n{truncate(file.diff)}")
            if observation.errors:
                parts.append("errors:\n" + "\n".join(observation.errors[:20]))
            lines.append("\n".join(parts))
        elif observation.kind == "python_rename":
            parts = [
                (
                    f"{index}. python_rename {observation.symbol}->{observation.new_name}: "
                    f"{observation.message} path={observation.path or '.'} "
                    f"files={len(observation.files)}/{observation.total_files} "
                    f"replacements={observation.total_replacements}"
                )
            ]
            for file in observation.files[:40]:
                parts.append(f"file: {file.path} replacements={len(file.replacements)}")
            if observation.diff:
                parts.append(f"diff:\n{truncate(observation.diff)}")
            if observation.errors:
                parts.append("errors:\n" + "\n".join(observation.errors[:20]))
            lines.append("\n".join(parts))
        elif observation.kind == "search":
            lines.append(
                "\n".join(
                    [
                        (
                            f"{index}. search {observation.query}: {observation.message} "
                            f"ok={str(observation.ok).lower()} "
                            f"shown={len(observation.matches)}/{observation.total} "
                            f"truncated={str(observation.truncated).lower()} "
                            f"path={observation.path or '.'} regex={str(observation.regex).lower()} "
                            f"caseSensitive={str(observation.case_sensitive).lower()} "
                            f"contextLines={observation.context_lines}"
                        ),
                        *observation.matches[:80],
                    ]
                )
            )
        elif observation.kind == "glob":
            lines.append(
                "\n".join(
                    [
                        f"{index}. glob {observation.pattern}: {observation.message}",
                        *observation.matches[:120],
                    ]
                )
            )
        elif observation.kind == "git_status":
            lines.append(
                "\n".join(
                    [
                        f"{index}. git_status: {observation.message}",
                        f"status:\n{truncate(observation.status)}",
                    ]
                )
            )
        elif observation.kind == "git_info":
            parts = [
                (
                    f"{index}. git_info: {observation.message} "
                    f"branch={observation.branch or 'detached'} head={observation.head or 'unknown'} "
                    f"upstream={observation.upstream or 'none'} ahead={observation.ahead} behind={observation.behind}"
                )
            ]
            for remote in observation.remotes[:20]:
                parts.append(f"remote: {remote.name} {remote.kind} {remote.url}")
            if observation.status.strip():
                parts.append(f"status:\n{truncate(observation.status)}")
            lines.append("\n".join(parts))
        elif observation.kind == "git_changes":
            parts = [f"{index}. git_changes: {observation.message}"]
            for file in observation.files[:120]:
                parts.append(
                    (
                        f"file: {file.path} status={file.status or '..'} "
                        f"staged={str(file.staged).lower()} unstaged={str(file.unstaged).lower()} "
                        f"untracked={str(file.untracked).lower()} "
                        f"stagedLines=+{file.staged_insertions}/-{file.staged_deletions} "
                        f"unstagedLines=+{file.unstaged_insertions}/-{file.unstaged_deletions} "
                        f"binary={str(file.binary).lower()}"
                    )
                )
            if observation.status.strip():
                parts.append(f"status:\n{truncate(observation.status)}")
            lines.append("\n".join(parts))
        elif observation.kind == "git_branches":
            parts = [
                (
                    f"{index}. git_branches: {observation.message} "
                    f"current={observation.current or 'detached'} shown={len(observation.branches)}/{observation.total} "
                    f"truncated={str(observation.truncated).lower()}"
                )
            ]
            for branch in observation.branches[:120]:
                marker = "*" if branch.current else "-"
                parts.append(f"{marker} {branch.name}")
            if observation.status.strip():
                parts.append(f"status:\n{truncate(observation.status)}")
            lines.append("\n".join(parts))
        elif observation.kind == "check_git_fetch":
            lines.append(
                "\n".join(
                    [
                        f"{index}. check_git_fetch {observation.remote or 'default remote'}: {observation.message}",
                        f"ok: {str(observation.ok).lower()}",
                        f"remoteUrl: {observation.remote_url or 'none'}",
                        f"branch: {observation.branch or 'detached'}",
                        f"upstream: {observation.upstream or 'none'}",
                        f"aheadBehind: {observation.ahead}/{observation.behind}",
                    ]
                )
            )
        elif observation.kind == "git_fetch":
            lines.append(
                "\n".join(
                    [
                        f"{index}. git_fetch {observation.remote or 'default remote'}: {observation.message}",
                        f"ok: {str(observation.ok).lower()}",
                        f"remoteUrl: {observation.remote_url or 'none'}",
                        f"branch: {observation.branch or 'detached'}",
                        f"upstream: {observation.upstream or 'none'}",
                        (
                            "aheadBehind: "
                            f"{observation.ahead_before}/{observation.behind_before}"
                            f" -> {observation.ahead_after}/{observation.behind_after}"
                        ),
                    ]
                )
            )
        elif observation.kind == "check_git_pull":
            lines.append(
                "\n".join(
                    [
                        f"{index}. check_git_pull {observation.upstream or 'no upstream'}: {observation.message}",
                        f"ok: {str(observation.ok).lower()}",
                        f"remoteBranch: {observation.remote or 'none'}/{observation.branch or 'none'}",
                        f"current: {observation.current or 'detached'}",
                        f"aheadBehind: {observation.ahead}/{observation.behind}",
                        f"worktreeClean: {str(observation.worktree_clean).lower()}",
                        f"status:\n{truncate(observation.status)}",
                    ]
                )
            )
        elif observation.kind == "git_pull":
            lines.append(
                "\n".join(
                    [
                        f"{index}. git_pull {observation.upstream or 'no upstream'}: {observation.message}",
                        f"ok: {str(observation.ok).lower()}",
                        f"remoteBranch: {observation.remote or 'none'}/{observation.branch or 'none'}",
                        f"current: {observation.current_before or 'detached'} -> {observation.current_after or 'detached'}",
                        (
                            "aheadBehind: "
                            f"{observation.ahead_before}/{observation.behind_before}"
                            f" -> {observation.ahead_after}/{observation.behind_after}"
                        ),
                        f"status:\n{truncate(observation.status)}",
                    ]
                )
            )
        elif observation.kind == "check_git_push":
            lines.append(
                "\n".join(
                    [
                        f"{index}. check_git_push {observation.upstream or 'no upstream'}: {observation.message}",
                        f"ok: {str(observation.ok).lower()}",
                        f"remoteBranch: {observation.remote or 'none'}/{observation.branch or 'none'}",
                        f"current: {observation.current or 'detached'}",
                        f"aheadBehind: {observation.ahead}/{observation.behind}",
                        f"worktreeClean: {str(observation.worktree_clean).lower()}",
                        f"status:\n{truncate(observation.status)}",
                    ]
                )
            )
        elif observation.kind == "git_push":
            lines.append(
                "\n".join(
                    [
                        f"{index}. git_push {observation.upstream or 'no upstream'}: {observation.message}",
                        f"ok: {str(observation.ok).lower()}",
                        f"remoteBranch: {observation.remote or 'none'}/{observation.branch or 'none'}",
                        f"current: {observation.current or 'detached'}",
                        f"aheadBehindBefore: {observation.ahead_before}/{observation.behind_before}",
                        f"status:\n{truncate(observation.status)}",
                    ]
                )
            )
        elif observation.kind in {"check_git_restore", "git_restore"}:
            lines.append(
                "\n".join(
                    [
                        f"{index}. {observation.kind}: {observation.message}",
                        f"ok: {str(observation.ok).lower()}",
                        f"paths: {', '.join(observation.paths)}",
                        f"diff:\n{truncate(observation.diff)}",
                        f"status:\n{truncate(observation.status)}",
                    ]
                )
            )
        elif observation.kind == "git_stashes":
            parts = [
                (
                    f"{index}. git_stashes: {observation.message} "
                    f"shown={len(observation.entries)}/{observation.total} "
                    f"truncated={str(observation.truncated).lower()}"
                )
            ]
            for entry in observation.entries[:50]:
                parts.append(f"stash: {entry.name} {entry.summary}")
            lines.append("\n".join(parts))
        elif observation.kind in {"check_git_stash", "git_stash"}:
            stash_ref = f"\nstashRef: {observation.stash_ref}" if observation.kind == "git_stash" else ""
            lines.append(
                "\n".join(
                    [
                        f"{index}. {observation.kind}: {observation.message}",
                        f"ok: {str(observation.ok).lower()}",
                        f"messageText: {observation.message_text}",
                        f"includeUntracked: {str(observation.include_untracked).lower()}{stash_ref}",
                        f"diff:\n{truncate(observation.diff)}",
                        f"status:\n{truncate(observation.status)}",
                    ]
                )
            )
        elif observation.kind in {"check_git_stash_apply", "git_stash_apply"}:
            worktree = (
                f"\nworktreeClean: {str(observation.worktree_clean).lower()}"
                if observation.kind == "check_git_stash_apply"
                else ""
            )
            lines.append(
                "\n".join(
                    [
                        f"{index}. {observation.kind} {observation.stash_ref}: {observation.message}",
                        f"ok: {str(observation.ok).lower()}{worktree}",
                        f"patch:\n{truncate(observation.patch)}",
                        f"status:\n{truncate(observation.status)}",
                    ]
                )
            )
        elif observation.kind in {"check_git_stash_drop", "git_stash_drop"}:
            remaining = (
                f"\nremainingTotal: {observation.remaining_total}"
                if observation.kind == "git_stash_drop"
                else ""
            )
            lines.append(
                "\n".join(
                    [
                        f"{index}. {observation.kind} {observation.stash_ref}: {observation.message}",
                        f"ok: {str(observation.ok).lower()}{remaining}",
                        f"summary: {observation.summary}",
                        f"patch:\n{truncate(observation.patch)}",
                    ]
                )
            )
        elif observation.kind == "check_git_switch":
            lines.append(
                "\n".join(
                    [
                        f"{index}. check_git_switch {observation.branch}: {observation.message}",
                        f"ok: {str(observation.ok).lower()}",
                        f"create: {str(observation.create).lower()}",
                        f"currentBefore: {observation.current_before or 'detached'}",
                        f"branchExists: {str(observation.branch_exists).lower()}",
                        f"worktreeClean: {str(observation.worktree_clean).lower()}",
                        f"status:\n{truncate(observation.status)}",
                    ]
                )
            )
        elif observation.kind == "git_switch":
            lines.append(
                "\n".join(
                    [
                        f"{index}. git_switch {observation.branch}: {observation.message}",
                        f"ok: {str(observation.ok).lower()}",
                        f"create: {str(observation.create).lower()}",
                        f"currentBefore: {observation.current_before or 'detached'}",
                        f"currentAfter: {observation.current_after or 'detached'}",
                        f"status:\n{truncate(observation.status)}",
                    ]
                )
            )
        elif observation.kind in {"check_git_stage", "git_stage", "check_git_unstage", "git_unstage"}:
            parts = [
                (
                    f"{index}. {observation.kind}: {observation.message} "
                    f"ok={str(observation.ok).lower()} paths={', '.join(observation.paths)}"
                )
            ]
            if observation.status.strip():
                parts.append(f"status:\n{truncate(observation.status)}")
            lines.append("\n".join(parts))
        elif observation.kind in {"check_git_commit", "git_commit"}:
            parts = [
                (
                    f"{index}. {observation.kind}: {observation.message} ok={str(observation.ok).lower()} "
                    f"head={observation.head_before or 'none'}->{observation.head_after or 'none'}"
                )
            ]
            if observation.status.strip():
                parts.append(f"status:\n{truncate(observation.status)}")
            lines.append("\n".join(parts))
        elif observation.kind == "review_changes":
            parts = [
                (
                    f"{index}. review_changes: {observation.message} "
                    f"ok={str(observation.ok).lower()} "
                    f"diffCheck={str(observation.diff_check_ok).lower()} "
                    f"stagedDiffCheck={str(observation.staged_diff_check_ok).lower()} "
                    f"pythonOk={str(observation.python_ok).lower()} "
                    f"configOk={str(observation.config_ok).lower()} "
                    f"changed={len(observation.files)}/{observation.total_files} "
                    f"python={len(observation.python)}/{observation.python_total} "
                    f"pythonTruncated={str(observation.python_truncated).lower()} "
                    f"config={len(observation.config)}/{observation.config_total} "
                    f"configTruncated={str(observation.config_truncated).lower()} "
                    f"suggestedChecks={len(observation.suggested_checks)}/{observation.suggested_checks_total} "
                    f"suggestedChecksTruncated={str(observation.suggested_checks_truncated).lower()} "
                    f"diffHunks={len(observation.diff_hunks)}/{observation.diff_hunks_total} "
                    f"diffHunksTruncated={str(observation.diff_hunks_truncated).lower()} "
                    f"stagedDiffHunks={len(observation.staged_diff_hunks)}/{observation.staged_diff_hunks_total} "
                    f"stagedDiffHunksTruncated={str(observation.staged_diff_hunks_truncated).lower()} "
                    f"untrackedPreviews={len(observation.untracked_previews)}/{observation.untracked_previews_total} "
                    f"untrackedPreviewsTruncated={str(observation.untracked_previews_truncated).lower()}"
                )
            ]
            for file in observation.files[:120]:
                parts.append(
                    (
                        f"file: {file.path} status={file.status or '..'} "
                        f"staged={str(file.staged).lower()} unstaged={str(file.unstaged).lower()} "
                        f"untracked={str(file.untracked).lower()}"
                    )
                )
            for file in observation.python[:120]:
                location = ""
                if file.line is not None:
                    location = f" line={file.line} column={file.column or 'unknown'}"
                parts.append(f"python: {file.path} ok={str(file.ok).lower()}{location} message={file.message}")
            for file in observation.config[:120]:
                location = ""
                if file.line is not None:
                    location = f" line={file.line} column={file.column or 'unknown'}"
                parts.append(
                    (
                        f"config: {file.path} format={file.format} ok={str(file.ok).lower()}"
                        f"{location} message={file.message}"
                    )
                )
            for check in observation.suggested_checks[:40]:
                parts.append(
                    (
                        f"check: cwd={check.cwd} command={check.command} "
                        f"available={str(check.available).lower()} missingTool={check.missing_tool or '.'} "
                        f"source={check.source} reason={check.reason}"
                    )
                )
            for hunk in observation.diff_hunks[:40]:
                parts.append(
                    (
                        f"diff_hunk: {hunk.file} old={hunk.old_start},{hunk.old_count} "
                        f"new={hunk.new_start},{hunk.new_count} added={hunk.added} "
                        f"deleted={hunk.deleted} linesTruncated={str(hunk.lines_truncated).lower()}"
                    )
                )
            for hunk in observation.staged_diff_hunks[:40]:
                parts.append(
                    (
                        f"staged_diff_hunk: {hunk.file} old={hunk.old_start},{hunk.old_count} "
                        f"new={hunk.new_start},{hunk.new_count} added={hunk.added} "
                        f"deleted={hunk.deleted} linesTruncated={str(hunk.lines_truncated).lower()}"
                    )
                )
            for preview in observation.untracked_previews[:40]:
                parts.append(
                    (
                        f"untracked_preview: {preview.path} size={preview.size_bytes} "
                        f"binary={str(preview.is_binary).lower()} "
                        f"truncated={str(preview.truncated).lower()} message={preview.message}"
                    )
                )
                if preview.content:
                    parts.append(f"untracked_content {preview.path}:\n{truncate(preview.content, 4000)}")
            if observation.diff_check.strip():
                parts.append(f"diff_check:\n{truncate(observation.diff_check)}")
            if observation.staged_diff_check.strip():
                parts.append(f"staged_diff_check:\n{truncate(observation.staged_diff_check)}")
            if observation.status.strip():
                parts.append(f"status:\n{truncate(observation.status)}")
            lines.append("\n".join(parts))
        elif observation.kind == "final_review":
            parts = [
                (
                    f"{index}. final_review: {observation.message} "
                    f"ok={str(observation.ok).lower()} "
                    f"ready={str(observation.ready).lower()} "
                    f"blocking={len(observation.blocking_issues)} "
                    f"warnings={len(observation.warnings)} "
                    f"changed={len(observation.files)}/{observation.total_files} "
                    f"suggestedChecks={len(observation.suggested_checks)}/{observation.suggested_checks_total} "
                    f"suggestedChecksTruncated={str(observation.suggested_checks_truncated).lower()}"
                )
            ]
            for issue in observation.blocking_issues[:20]:
                parts.append(f"blocking_issue: {issue}")
            for warning in observation.warnings[:20]:
                parts.append(f"warning: {warning}")
            for file in observation.files[:120]:
                parts.append(
                    (
                        f"file: {file.path} status={file.status or '..'} "
                        f"staged={str(file.staged).lower()} unstaged={str(file.unstaged).lower()} "
                        f"untracked={str(file.untracked).lower()}"
                    )
                )
            for check in observation.suggested_checks[:40]:
                parts.append(
                    (
                        f"check: cwd={check.cwd} command={check.command} "
                        f"available={str(check.available).lower()} missingTool={check.missing_tool or '.'} "
                        f"source={check.source} reason={check.reason}"
                    )
                )
            if observation.diff_check.strip():
                parts.append(f"diff_check:\n{truncate(observation.diff_check)}")
            if observation.staged_diff_check.strip():
                parts.append(f"staged_diff_check:\n{truncate(observation.staged_diff_check)}")
            if observation.status.strip():
                parts.append(f"status:\n{truncate(observation.status)}")
            lines.append("\n".join(parts))
        elif observation.kind == "suggest_checks":
            parts = [
                (
                    f"{index}. suggest_checks: {observation.message} "
                    f"shown={len(observation.checks)}/{observation.total} "
                    f"truncated={str(observation.truncated).lower()}"
                )
            ]
            for check in observation.checks:
                parts.append(
                    (
                        f"check: cwd={check.cwd} command={check.command} "
                        f"available={str(check.available).lower()} missingTool={check.missing_tool or '.'} "
                        f"source={check.source} reason={check.reason}"
                    )
                )
            if observation.changed_files:
                parts.append("changed_files:\n" + "\n".join(observation.changed_files[:120]))
            lines.append("\n".join(parts))
        elif observation.kind == "project_commands":
            parts = [
                (
                    f"{index}. project_commands: {observation.message} "
                    f"shown={len(observation.commands)}/{observation.total} "
                    f"files={observation.scanned_files}/{observation.total_files} "
                    f"truncated={str(observation.truncated).lower()}"
                )
            ]
            for command in observation.commands:
                parts.append(
                    (
                        f"command: cwd={command.cwd} command={command.command} "
                        f"available={str(command.available).lower()} missingTool={command.missing_tool or '.'} "
                        f"source={command.source} file={command.file} detail={command.detail}"
                    )
                )
            lines.append("\n".join(parts))
        elif observation.kind == "project_manifests":
            parts = [
                (
                    f"{index}. project_manifests: {observation.message} "
                    f"files={observation.scanned_files}/{observation.total_files} "
                    f"items={observation.total_items} "
                    f"truncated={str(observation.truncated).lower()}"
                )
            ]
            for manifest in observation.manifests[:40]:
                parts.append(
                    (
                        f"manifest: {manifest.path} kind={manifest.kind} ok={str(manifest.ok).lower()} "
                        f"name={manifest.name or '.'} version={manifest.version or '.'} "
                        f"items={len(manifest.items)}/{manifest.item_count} "
                        f"truncated={str(manifest.truncated).lower()} message={manifest.message}"
                    )
                )
                for item in manifest.items[:120]:
                    parts.append(f"item: group={item.group} name={item.name} value={item.value or '.'}")
            lines.append("\n".join(parts))
        elif observation.kind == "project_overview":
            parts = [
                (
                    f"{index}. project_overview: {observation.message} "
                    f"root={observation.project_root} "
                    f"git={str(observation.is_git_repo).lower()} "
                    f"branch={observation.git_branch or '.'} head={observation.git_head or '.'} "
                    f"upstream={observation.git_upstream or '.'} "
                    f"ahead={observation.git_ahead} behind={observation.git_behind}"
                ),
                (
                    f"repo: files={len(observation.files)}/{observation.total_files} "
                    f"tree={len(observation.tree)}/{observation.total_tree_entries} "
                    f"truncated={str(observation.repo_truncated).lower()}"
                ),
            ]
            if observation.git_status.strip():
                parts.append(f"git_status:\n{truncate(observation.git_status, 2000)}")
            if observation.tree:
                parts.append("tree:\n" + "\n".join(observation.tree[:80]))
            if observation.commands:
                parts.append(
                    (
                        f"commands shown={len(observation.commands)}/{observation.commands_total} "
                        f"truncated={str(observation.commands_truncated).lower()}"
                    )
                )
                for command in observation.commands[:40]:
                    parts.append(
                        (
                            f"command: cwd={command.cwd} command={command.command} "
                            f"available={str(command.available).lower()} missingTool={command.missing_tool or '.'} "
                            f"source={command.source} file={command.file}"
                        )
                    )
            if observation.manifests:
                parts.append(
                    (
                        f"manifests shown={len(observation.manifests)}/{observation.manifest_files_total} "
                        f"truncated={str(observation.manifests_truncated).lower()}"
                    )
                )
                for manifest in observation.manifests[:20]:
                    parts.append(
                        (
                            f"manifest: {manifest.path} kind={manifest.kind} ok={str(manifest.ok).lower()} "
                            f"name={manifest.name or '.'} items={manifest.item_count}"
                        )
                    )
            if observation.suggested_checks:
                parts.append(
                    (
                        f"suggested_checks shown={len(observation.suggested_checks)}/{observation.suggested_checks_total} "
                        f"truncated={str(observation.suggested_checks_truncated).lower()}"
                    )
                )
                for check in observation.suggested_checks[:20]:
                    parts.append(
                        (
                            f"check: cwd={check.cwd} command={check.command} "
                            f"available={str(check.available).lower()} missingTool={check.missing_tool or '.'} "
                            f"reason={check.reason}"
                        )
                    )
            if observation.tools:
                parts.append(
                    "tools: "
                    + ", ".join(
                        f"{tool.name}={'yes' if tool.available else 'no'}"
                        for tool in observation.tools[:20]
                    )
                )
            lines.append("\n".join(parts))
        elif observation.kind in {"command_check", "check_start_command"}:
            lines.append(
                "\n".join(
                    [
                        f"{index}. {observation.kind}: {observation.message}",
                        f"ok: {str(observation.ok).lower()}",
                        f"command: {observation.command}",
                        f"cwd: {observation.cwd}",
                        f"cwdOk: {str(observation.cwd_ok).lower()}",
                        f"blocked: {str(observation.blocked).lower()}",
                        f"blockReason: {observation.block_reason or 'none'}",
                        f"executableAvailable: {str(observation.executable_available).lower()}",
                        f"missingTool: {observation.missing_tool or 'none'}",
                    ]
                )
            )
        elif observation.kind == "check_run_commands":
            parts = [
                f"{index}. check_run_commands: {observation.message}",
                f"ok: {str(observation.ok).lower()}",
            ]
            for check in observation.checks:
                parts.extend(
                    [
                        f"command: {check.command}",
                        f"cwd: {check.cwd}",
                        f"ok: {str(check.ok).lower()} cwdOk={str(check.cwd_ok).lower()} blocked={str(check.blocked).lower()} executableAvailable={str(check.executable_available).lower()}",
                        f"blockReason: {check.block_reason or 'none'} missingTool={check.missing_tool or 'none'} message={check.message}",
                    ]
                )
            lines.append("\n".join(parts))
        elif observation.kind == "port_check":
            lines.append(
                "\n".join(
                    [
                        f"{index}. port_check {observation.host}:{observation.port}: {observation.message}",
                        f"ok: {str(observation.ok).lower()}",
                        f"reachable: {str(observation.reachable).lower()}",
                        f"timeoutMs: {observation.timeout_ms}",
                        f"error: {observation.error or 'none'}",
                    ]
                )
            )
        elif observation.kind == "http_check":
            parts = [
                f"{index}. http_check {observation.url}: {observation.message}",
                f"ok: {str(observation.ok).lower()}",
                f"reachable: {str(observation.reachable).lower()}",
                f"status: {observation.status if observation.status is not None else 'none'}",
                f"reason: {observation.reason or 'none'}",
                f"finalUrl: {observation.final_url or 'none'}",
                f"timeoutMs: {observation.timeout_ms}",
                f"matched: {str(observation.matched).lower()}",
                f"matchedPattern: {observation.matched_pattern or 'none'}",
                f"bodyTruncated: {str(observation.body_truncated).lower()}",
                f"maxBodyChars: {observation.max_body_chars}",
                f"error: {observation.error or 'none'}",
            ]
            if observation.body:
                parts.append(f"body:\n{observation.body}")
            lines.append("\n".join(parts))
        elif observation.kind == "environment_info":
            parts = [
                (
                    f"{index}. environment_info: {observation.message} "
                    f"ok={str(observation.ok).lower()} "
                    f"projectRoot={observation.project_root} "
                    f"python={observation.python_version} "
                    f"platform={observation.platform} "
                    f"gitRepo={str(observation.is_git_repo).lower()}"
                ),
                f"pythonExecutable: {observation.python_executable or 'unknown'}",
            ]
            for tool in observation.tools:
                parts.append(
                    (
                        f"tool: {tool.name} available={str(tool.available).lower()} "
                        f"path={tool.path or '.'} version={tool.version or '.'} message={tool.message}"
                    )
                )
            lines.append("\n".join(parts))
        elif observation.kind == "git_diff":
            lines.append(
                "\n".join(
                    [
                        f"{index}. git_diff {observation.path or '.'}: {observation.message}",
                        f"staged: {str(observation.staged).lower()}",
                        f"maxOutputChars: {observation.max_output_chars}",
                        f"truncated: {str(observation.truncated).lower()}",
                        f"diff:\n{truncate(observation.diff)}",
                    ]
                )
            )
        elif observation.kind == "git_diff_hunks":
            parts = [
                (
                    f"{index}. git_diff_hunks {observation.path or '.'}: {observation.message} "
                    f"shown={len(observation.hunks)}/{observation.total_hunks} "
                    f"staged={str(observation.staged).lower()} "
                    f"truncated={str(observation.truncated).lower()}"
                )
            ]
            for hunk in observation.hunks[:120]:
                parts.append(
                    (
                        f"hunk: {hunk.file} old={hunk.old_start},{hunk.old_count} "
                        f"new={hunk.new_start},{hunk.new_count} "
                        f"added={hunk.added} deleted={hunk.deleted} context={hunk.context} "
                        f"linesTruncated={str(hunk.lines_truncated).lower()}"
                    )
                )
                if hunk.lines:
                    parts.append("lines:\n" + truncate("\n".join(hunk.lines)))
            lines.append("\n".join(parts))
        elif observation.kind == "git_log":
            lines.append(
                "\n".join(
                    [
                        f"{index}. git_log {observation.path or '.'}: {observation.message}",
                        f"maxCount: {observation.max_count}",
                        f"log:\n{truncate(observation.log)}",
                    ]
                )
            )
        elif observation.kind == "git_show":
            target = f"{observation.rev} -- {observation.path}" if observation.path else observation.rev
            lines.append(
                "\n".join(
                    [
                        f"{index}. git_show {target}: {observation.message}",
                        f"maxOutputChars: {observation.max_output_chars}",
                        f"truncated: {str(observation.truncated).lower()}",
                        f"output:\n{truncate(observation.output)}",
                    ]
                )
            )
        elif observation.kind == "git_blame":
            line_range = ""
            if observation.start_line is not None:
                line_range = f":{observation.start_line}+{observation.line_count or 120}"
            lines.append(
                "\n".join(
                    [
                        f"{index}. git_blame {observation.path}{line_range}: {observation.message}",
                        f"maxOutputChars: {observation.max_output_chars}",
                        f"truncated: {str(observation.truncated).lower()}",
                        f"blame:\n{truncate(observation.blame)}",
                    ]
                )
            )
        elif observation.kind == "session_summary":
            lines.append(
                "\n".join(
                    [
                        f"{index}. session_summary {observation.run_id}: {observation.message}",
                        f"ok: {str(observation.ok).lower()}",
                        f"summary:\n{truncate(observation.summary)}",
                        f"recent:\n{truncate(chr(10).join(observation.recent_sessions))}",
                    ]
                )
            )
        elif observation.kind == "edit_file":
            lines.append(
                "\n".join(
                    [
                        f"{index}. edit_file {observation.path}: {observation.message}",
                        f"diff:\n{truncate(observation.diff)}",
                    ]
                )
            )
        elif observation.kind == "check_edit_file":
            lines.append(
                "\n".join(
                    [
                        f"{index}. check_edit_file {observation.path}: {observation.message}",
                        f"diff:\n{truncate(observation.diff)}",
                    ]
                )
            )
        elif observation.kind == "multi_edit_file":
            lines.append(
                "\n".join(
                    [
                        f"{index}. multi_edit_file {observation.path}: {observation.message}",
                        f"diff:\n{truncate(observation.diff)}",
                    ]
                )
            )
        elif observation.kind == "check_multi_edit_file":
            lines.append(
                "\n".join(
                    [
                        f"{index}. check_multi_edit_file {observation.path}: {observation.message}",
                        f"diff:\n{truncate(observation.diff)}",
                    ]
                )
            )
        elif observation.kind == "check_replace_lines":
            lines.append(
                "\n".join(
                    [
                        (
                            f"{index}. check_replace_lines {observation.path}:"
                            f"{observation.start_line}-{observation.end_line}: {observation.message}"
                        ),
                        f"diff:\n{truncate(observation.diff)}",
                    ]
                )
            )
        elif observation.kind == "check_replace_python_definition":
            target = observation.definition_path or observation.path or "."
            lines.append(
                "\n".join(
                    [
                        (
                            f"{index}. check_replace_python_definition {observation.symbol} in {target}: "
                            f"{observation.message}"
                        ),
                        f"qualifiedName: {observation.qualified_name or '.'}",
                        f"lines: {observation.start_line or '?'}-{observation.end_line or '?'}",
                        f"diff:\n{truncate(observation.diff)}",
                    ]
                )
            )
        elif observation.kind == "replace_python_definition":
            target = observation.definition_path or observation.path or "."
            lines.append(
                "\n".join(
                    [
                        (
                            f"{index}. replace_python_definition {observation.symbol} in {target}: "
                            f"{observation.message}"
                        ),
                        f"qualifiedName: {observation.qualified_name or '.'}",
                        f"lines: {observation.start_line or '?'}-{observation.end_line or '?'}",
                        f"diff:\n{truncate(observation.diff)}",
                    ]
                )
            )
        elif observation.kind == "replace_lines":
            lines.append(
                "\n".join(
                    [
                        (
                            f"{index}. replace_lines {observation.path}:{observation.start_line}-{observation.end_line}: "
                            f"{observation.message}"
                        ),
                        f"diff:\n{truncate(observation.diff)}",
                    ]
                )
            )
        elif observation.kind == "check_insert_lines":
            lines.append(
                "\n".join(
                    [
                        f"{index}. check_insert_lines {observation.path}:{observation.line}: {observation.message}",
                        f"diff:\n{truncate(observation.diff)}",
                    ]
                )
            )
        elif observation.kind == "insert_lines":
            lines.append(
                "\n".join(
                    [
                        f"{index}. insert_lines {observation.path}:{observation.line}: {observation.message}",
                        f"diff:\n{truncate(observation.diff)}",
                    ]
                )
            )
        elif observation.kind == "check_append_file":
            lines.append(
                "\n".join(
                    [
                        f"{index}. check_append_file {observation.path}: {observation.message}",
                        f"diff:\n{truncate(observation.diff)}",
                    ]
                )
            )
        elif observation.kind == "append_file":
            lines.append(
                "\n".join(
                    [
                        f"{index}. append_file {observation.path}: {observation.message}",
                        f"diff:\n{truncate(observation.diff)}",
                    ]
                )
            )
        elif observation.kind == "regex_replace":
            lines.append(
                "\n".join(
                    [
                        (
                            f"{index}. regex_replace {observation.path}: {observation.message} "
                            f"replacements={observation.replacements} count={observation.count}"
                        ),
                        f"diff:\n{truncate(observation.diff)}",
                    ]
                )
            )
        elif observation.kind == "check_regex_replace":
            lines.append(
                "\n".join(
                    [
                        (
                            f"{index}. check_regex_replace {observation.path}: {observation.message} "
                            f"replacements={observation.replacements} count={observation.count}"
                        ),
                        f"diff:\n{truncate(observation.diff)}",
                    ]
                )
            )
        elif observation.kind in {"check_json_set", "json_set", "check_json_remove", "json_remove"}:
            lines.append(
                "\n".join(
                    [
                        f"{index}. {observation.kind} {observation.path} {observation.pointer}: {observation.message}",
                        f"diff:\n{truncate(observation.diff)}",
                    ]
                )
            )
        elif observation.kind in {"check_json_patch", "json_patch"}:
            lines.append(
                "\n".join(
                    [
                        f"{index}. {observation.kind} {observation.path}: {observation.message} operations={observation.operation_count}",
                        f"diff:\n{truncate(observation.diff)}",
                    ]
                )
            )
        elif observation.kind == "check_patch":
            lines.append(
                "\n".join(
                    [
                        f"{index}. check_patch {observation.path}: {observation.message}",
                        f"diff:\n{truncate(observation.diff)}",
                    ]
                )
            )
        elif observation.kind == "check_patches":
            lines.append(
                "\n".join(
                    [
                        f"{index}. check_patches {', '.join(observation.files) or 'no files'}: {observation.message}",
                        f"diff:\n{truncate(observation.diff)}",
                    ]
                )
            )
        elif observation.kind == "patch_file":
            lines.append(
                "\n".join(
                    [
                        f"{index}. patch_file {observation.path}: {observation.message}",
                        f"diff:\n{truncate(observation.diff)}",
                    ]
                )
            )
        elif observation.kind == "patch_files":
            lines.append(
                "\n".join(
                    [
                        f"{index}. patch_files {', '.join(observation.files) or 'no files'}: {observation.message}",
                        f"diff:\n{truncate(observation.diff)}",
                    ]
                )
            )
        elif observation.kind == "delete_file":
            lines.append(
                "\n".join(
                    [
                        f"{index}. delete_file {observation.path}: {observation.message}",
                        f"diff:\n{truncate(observation.diff)}",
                    ]
                )
            )
        elif observation.kind == "check_delete_file":
            lines.append(
                "\n".join(
                    [
                        f"{index}. check_delete_file {observation.path}: {observation.message}",
                        f"diff:\n{truncate(observation.diff)}",
                    ]
                )
            )
        elif observation.kind in {"check_delete_files", "delete_files"}:
            lines.append(
                "\n".join(
                    [
                        f"{index}. {observation.kind} {', '.join(observation.paths)}: {observation.message}",
                        f"diff:\n{truncate(observation.diff)}",
                    ]
                )
            )
        elif observation.kind == "move_file":
            lines.append(
                f"{index}. move_file {observation.source} -> {observation.destination}: {observation.message}"
            )
        elif observation.kind == "check_move_file":
            lines.append(
                f"{index}. check_move_file {observation.source} -> {observation.destination}: {observation.message}"
            )
        elif observation.kind in {"check_move_files", "move_files"}:
            transfers = ", ".join(
                f"{transfer.source} -> {transfer.destination}" for transfer in observation.transfers
            )
            lines.append(f"{index}. {observation.kind} {transfers}: {observation.message}")
        elif observation.kind == "copy_file":
            lines.append(
                f"{index}. copy_file {observation.source} -> {observation.destination}: {observation.message}"
            )
        elif observation.kind == "check_copy_file":
            lines.append(
                f"{index}. check_copy_file {observation.source} -> {observation.destination}: {observation.message}"
            )
        elif observation.kind in {"check_copy_files", "copy_files"}:
            transfers = ", ".join(
                f"{transfer.source} -> {transfer.destination}" for transfer in observation.transfers
            )
            lines.append(f"{index}. {observation.kind} {transfers}: {observation.message}")
        elif observation.kind == "check_move_dir":
            lines.append(
                f"{index}. check_move_dir {observation.source} -> {observation.destination}: {observation.message}"
            )
        elif observation.kind == "move_dir":
            lines.append(
                f"{index}. move_dir {observation.source} -> {observation.destination}: {observation.message}"
            )
        elif observation.kind in {"check_move_dirs", "move_dirs"}:
            transfers = ", ".join(
                f"{transfer.source} -> {transfer.destination}" for transfer in observation.transfers
            )
            lines.append(f"{index}. {observation.kind} {transfers}: {observation.message}")
        elif observation.kind == "check_copy_dir":
            lines.append(
                f"{index}. check_copy_dir {observation.source} -> {observation.destination}: {observation.message}"
            )
        elif observation.kind == "copy_dir":
            lines.append(
                f"{index}. copy_dir {observation.source} -> {observation.destination}: {observation.message}"
            )
        elif observation.kind in {"check_copy_dirs", "copy_dirs"}:
            transfers = ", ".join(
                f"{transfer.source} -> {transfer.destination}" for transfer in observation.transfers
            )
            lines.append(f"{index}. {observation.kind} {transfers}: {observation.message}")
        elif observation.kind == "check_create_dir":
            lines.append(f"{index}. check_create_dir {observation.path}: {observation.message}")
        elif observation.kind == "create_dir":
            lines.append(f"{index}. create_dir {observation.path}: {observation.message}")
        elif observation.kind == "check_create_dirs":
            lines.append(f"{index}. check_create_dirs {', '.join(observation.paths)}: {observation.message}")
        elif observation.kind == "create_dirs":
            lines.append(f"{index}. create_dirs {', '.join(observation.paths)}: {observation.message}")
        elif observation.kind == "check_delete_empty_dir":
            lines.append(f"{index}. check_delete_empty_dir {observation.path}: {observation.message}")
        elif observation.kind == "delete_empty_dir":
            lines.append(f"{index}. delete_empty_dir {observation.path}: {observation.message}")
        elif observation.kind == "check_delete_empty_dirs":
            lines.append(f"{index}. check_delete_empty_dirs {', '.join(observation.paths)}: {observation.message}")
        elif observation.kind == "delete_empty_dirs":
            lines.append(f"{index}. delete_empty_dirs {', '.join(observation.paths)}: {observation.message}")
        elif observation.kind == "check_set_executable":
            lines.append(
                (
                    f"{index}. check_set_executable {observation.path}: {observation.message} "
                    f"ok={str(observation.ok).lower()} executable={str(observation.executable).lower()} "
                    f"mode={observation.mode_before or '?'}->{observation.mode_after or '?'}"
                )
            )
        elif observation.kind == "set_executable":
            lines.append(
                (
                    f"{index}. set_executable {observation.path}: {observation.message} "
                    f"ok={str(observation.ok).lower()} executable={str(observation.executable).lower()} "
                    f"mode={observation.mode_before or '?'}->{observation.mode_after or '?'}"
                )
            )
        elif observation.kind == "start_command":
            lines.append(
                "\n".join(
                    [
                        f"{index}. start_command: {observation.message}",
                        f"processId: {observation.process_id or 'none'}",
                        f"pid: {observation.pid or 'none'}",
                        f"command: {observation.command}",
                        f"cwd: {observation.cwd}",
                        f"stdoutPath: {observation.stdout_path or 'none'}",
                        f"stderrPath: {observation.stderr_path or 'none'}",
                    ]
                )
            )
        elif observation.kind == "read_process":
            lines.append(
                "\n".join(
                    [
                        f"{index}. read_process {observation.process_id}: {observation.message}",
                        f"pid: {observation.pid or 'none'}",
                        f"running: {str(observation.running).lower()}",
                        f"exitCode: {observation.exit_code}",
                        f"signal: {observation.signal or 'none'}",
                        f"maxOutputChars: {observation.max_output_chars}",
                        f"stdout:\n{truncate(observation.stdout)}",
                        f"stderr:\n{truncate(observation.stderr)}",
                    ]
                )
            )
        elif observation.kind == "wait_process":
            lines.append(
                "\n".join(
                    [
                        f"{index}. wait_process {observation.process_id}: {observation.message}",
                        f"pid: {observation.pid or 'none'}",
                        f"running: {str(observation.running).lower()}",
                        f"timedOut: {str(observation.timed_out).lower()}",
                        f"matched: {str(observation.matched).lower()}",
                        f"matchedStream: {observation.matched_stream or 'none'}",
                        f"matchedPattern: {observation.matched_pattern or 'none'}",
                        f"timeoutMs: {observation.timeout_ms}",
                        f"exitCode: {observation.exit_code}",
                        f"signal: {observation.signal or 'none'}",
                        f"maxOutputChars: {observation.max_output_chars}",
                        f"stdout:\n{truncate(observation.stdout)}",
                        f"stderr:\n{truncate(observation.stderr)}",
                    ]
                )
            )
        elif observation.kind == "check_write_process":
            lines.append(
                "\n".join(
                    [
                        f"{index}. check_write_process {observation.process_id}: {observation.message}",
                        f"pid: {observation.pid or 'none'}",
                        f"ok: {str(observation.ok).lower()}",
                        f"running: {str(observation.running).lower()}",
                        f"cwd: {observation.cwd or 'none'}",
                        f"contentChars: {observation.content_chars}",
                        f"command: {observation.command or 'none'}",
                    ]
                )
            )
        elif observation.kind == "write_process":
            lines.append(
                "\n".join(
                    [
                        f"{index}. write_process {observation.process_id}: {observation.message}",
                        f"pid: {observation.pid or 'none'}",
                        f"ok: {str(observation.ok).lower()}",
                        f"running: {str(observation.running).lower()}",
                        f"cwd: {observation.cwd or 'none'}",
                        f"contentChars: {observation.content_chars}",
                        f"command: {observation.command or 'none'}",
                    ]
                )
            )
        elif observation.kind == "list_processes":
            process_lines = [
                (
                    f"- {process.process_id} pid={process.pid} cwd={process.cwd} running={str(process.running).lower()} "
                    f"exitCode={process.exit_code} signal={process.signal or 'none'} command={process.command}"
                )
                for process in observation.processes
            ]
            lines.append(
                "\n".join(
                    [
                        f"{index}. list_processes: {observation.message}",
                        *process_lines,
                    ]
                )
            )
        elif observation.kind == "check_stop_all_processes":
            process_lines = [
                (
                    f"- {process.process_id} pid={process.pid} cwd={process.cwd} running={str(process.running).lower()} "
                    f"exitCode={process.exit_code} signal={process.signal or 'none'} command={process.command}"
                )
                for process in observation.processes
            ]
            lines.append(
                "\n".join(
                    [
                        f"{index}. check_stop_all_processes: {observation.message}",
                        f"ok: {str(observation.ok).lower()}",
                        f"runningCount: {observation.running_count}",
                        *process_lines,
                    ]
                )
            )
        elif observation.kind == "check_stop_process":
            lines.append(
                "\n".join(
                    [
                        f"{index}. check_stop_process {observation.process_id}: {observation.message}",
                        f"ok: {str(observation.ok).lower()}",
                        f"pid: {observation.pid or 'none'}",
                        f"running: {str(observation.running).lower()}",
                        f"exitCode: {observation.exit_code}",
                        f"signal: {observation.signal or 'none'}",
                        f"cwd: {observation.cwd or 'none'}",
                        f"command: {observation.command or 'none'}",
                    ]
                )
            )
        elif observation.kind == "stop_all_processes":
            stopped_lines = [
                (
                    f"- {process.process_id} pid={process.pid} cwd={process.cwd} ok={str(process.ok).lower()} "
                    f"exitCode={process.exit_code} signal={process.signal or 'none'} command={process.command}"
                )
                for process in observation.stopped
            ]
            lines.append(
                "\n".join(
                    [
                        f"{index}. stop_all_processes: {observation.message}",
                        f"ok: {str(observation.ok).lower()}",
                        *stopped_lines,
                    ]
                )
            )
        elif observation.kind == "stop_process":
            lines.append(
                "\n".join(
                    [
                        f"{index}. stop_process {observation.process_id}: {observation.message}",
                        f"pid: {observation.pid or 'none'}",
                        f"exitCode: {observation.exit_code}",
                        f"signal: {observation.signal or 'none'}",
                    ]
                )
            )
        elif observation.kind == "finish":
            lines.append(f"{index}. finish: {observation.message}")
        elif observation.kind == "tool_error":
            lines.append(f"{index}. tool_error {observation.tool}: {observation.message}")
        elif observation.kind == "update_plan":
            lines.append(
                "\n".join(
                    [
                        f"{index}. update_plan: {observation.message}",
                        *[f"- {item.status}: {item.step}" for item in observation.plan],
                    ]
                )
            )
        elif observation.kind == "run_commands":
            parts = [
                f"{index}. run_commands: {observation.message}",
                f"ok: {str(observation.ok).lower()}",
                f"stoppedEarly: {str(observation.stopped_early).lower()}",
            ]
            for result in observation.results:
                parts.extend(
                    [
                        f"command: {result.command}",
                        f"cwd: {result.cwd}",
                        f"exitCode: {result.exit_code}",
                        f"timedOut: {str(result.timed_out).lower()}",
                        f"timeoutMs: {result.timeout_ms}",
                        f"maxOutputChars: {result.max_output_chars}",
                        f"stdoutTruncated: {str(result.stdout_truncated).lower()} stderrTruncated={str(result.stderr_truncated).lower()} signal={result.signal or 'none'}",
                        f"stdout:\n{truncate(result.stdout)}",
                        f"stderr:\n{truncate(result.stderr)}",
                    ]
                )
            lines.append("\n".join(parts))
        else:
            result = observation.result
            lines.append(
                "\n".join(
                    [
                        f"{index}. run_command: {result.command}",
                        f"cwd: {result.cwd}",
                        f"exitCode: {result.exit_code}",
                        f"timedOut: {str(result.timed_out).lower()}",
                        f"timeoutMs: {result.timeout_ms}",
                        f"maxOutputChars: {result.max_output_chars}",
                        f"stdoutTruncated: {str(result.stdout_truncated).lower()}",
                        f"stderrTruncated: {str(result.stderr_truncated).lower()}",
                        f"signal: {result.signal or 'none'}",
                        f"stdout:\n{truncate(result.stdout)}",
                        f"stderr:\n{truncate(result.stderr)}",
                    ]
                )
            )

    return "\n\n".join(lines)


def truncate(value: str, max_length: int = 4_000) -> str:
    # Truncate long stdout/stderr fields so prompt context stays within practical size.
    if not value:
        return ""
    if len(value) <= max_length:
        return value
    return f"{value[:max_length]}\n[truncated]"
