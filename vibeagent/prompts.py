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
Use repo_map first for unfamiliar or larger projects when you need a high-level overview of structure and Python symbols.
Use read_files to inspect several small related files together. For large files, read focused slices with read_file start_line and line_count, or use read_file_ranges to inspect several focused slices in one call.
Use file_info before reading or editing paths when size, line count, or binary/text status matters.
Use python_symbols to inspect Python module structure before reading large Python files.
Use python_check to validate Python syntax without executing code after Python edits or before slower test runs.
Use python_dependencies to inspect Python imports and local/external module dependencies before changing shared modules.
Use python_definitions to inspect class/function bodies directly when you know the symbol name.
Use python_calls to inspect call sites separately from ordinary references when changing callable signatures or behavior.
Use python_call_graph to inspect caller-to-callee relationships in a file or directory before broad refactors.
Use python_references to find Python definitions, imports, and references for one identifier before changing shared symbols.
Use list_tree to inspect directory structure, glob to find files by path pattern, and search to find text inside files.
Use scoped search with path, regex, and case_sensitive options to find symbols or call sites efficiently.
Prefer replace_python_definition, multi_edit_file, replace_lines, insert_lines, patch_file, patch_files, or edit_file over write_file for existing files. Use replace_python_definition after inspecting a unique Python class/function definition and replacing the full definition is clearer than line edits. Use write_files when creating or replacing several files at once, replace_lines after reading a focused line range, insert_lines to add text before a known line or append at line_count + 1, multi_edit_file for several exact replacements in one file, patch_file when several nearby lines need to change, and patch_files for coordinated edits across multiple existing files. Use check_patch or check_patches before applying complex unified diffs when context match is uncertain.
Use move_file for renames and delete_file for removing obsolete files; do not use shell commands for simple file lifecycle changes.
Use git_status, git_changes, review_changes, git_diff, git_log, git_show, and git_blame to review repository state, changed-file impact, line attribution, pre-final checks, and recent intent before summarizing non-trivial edits.
Use session_summary to inspect the current or a previous local run when recovering context or diagnosing why a task stopped.
Use suggest_checks or discovered project command hints to choose relevant tests, builds, and dev scripts before running verification.
Use run_command for finite checks, with cwd for subdirectories and timeout_ms for slow tests or builds. Use start_command only for long-running dev servers or watchers, list_processes if you need active process ids, then use read_process to inspect output and stop_process when it is no longer needed.
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
            return f"{base} The background command started. Use read_process with process_id={latest.process_id} to inspect it."
        return f"{base} The background command did not start, so fix the concrete error before finishing."

    if latest.kind == "read_process":
        if latest.ok and latest.running:
            return f"{base} Use the process output to continue, or stop_process if the background command is no longer needed."
        if latest.ok:
            return f"{base} The background command exited. Use its output to decide whether to fix issues or answer directly."
        return f"{base} The process could not be read, so use a valid process id or choose another useful action."

    if latest.kind == "list_processes":
        return f"{base} Use a listed process id with read_process or stop_process, or continue with another useful action."

    if latest.kind == "stop_process":
        return f"{base} The background process was stopped. Continue with the next check or answer directly if the task is complete."

    if latest.kind in {
        "read_file",
        "read_files",
        "read_file_ranges",
        "file_info",
        "repo_map",
        "python_symbols",
        "python_check",
        "python_dependencies",
        "python_definitions",
        "python_calls",
        "python_call_graph",
        "python_references",
        "list_files",
        "list_tree",
        "glob",
    }:
        return (
            f"{base} Do not repeat inspection unless you need specific missing information. "
            "If you already created the requested files, run one appropriate check or answer directly if the task is complete."
        )

    if latest.kind in {"git_status", "git_changes", "review_changes", "suggest_checks", "git_diff", "git_log", "git_show", "git_blame", "session_summary"}:
        return f"{base} Use the repository or session information to decide whether to continue, run a check, or answer directly."

    if latest.kind in {"check_patch", "check_patches"}:
        if latest.ok:
            return f"{base} The patch dry-run succeeded. Apply it if the diff matches the requested change, or continue with the next required step."
        return f"{base} The patch dry-run failed, so fix the patch context or choose another edit tool before applying changes."

    if latest.kind in {"write_file", "write_files", "edit_file", "multi_edit_file", "replace_python_definition", "replace_lines", "insert_lines", "patch_file", "patch_files", "delete_file", "move_file"}:
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
        if observation.kind == "write_file":
            lines.append(f"{index}. write_file {observation.path}: {observation.message}")
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
            lines.append("\n".join(parts))
        elif observation.kind == "read_file":
            lines.append(
                "\n".join(
                    [
                        f"{index}. read_file {observation.path}: {observation.message}",
                        f"content:\n{truncate(observation.content)}",
                    ]
                )
            )
        elif observation.kind == "read_files":
            parts = [f"{index}. read_files: {observation.message}"]
            for file in observation.files:
                parts.append(f"file: {file.path} ok={str(file.ok).lower()} message={file.message}")
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
        elif observation.kind == "search":
            lines.append(
                "\n".join(
                    [
                        (
                            f"{index}. search {observation.query}: {observation.message} "
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
        elif observation.kind == "review_changes":
            parts = [
                (
                    f"{index}. review_changes: {observation.message} "
                    f"ok={str(observation.ok).lower()} "
                    f"diffCheck={str(observation.diff_check_ok).lower()} "
                    f"stagedDiffCheck={str(observation.staged_diff_check_ok).lower()} "
                    f"pythonOk={str(observation.python_ok).lower()} "
                    f"changed={len(observation.files)}/{observation.total_files} "
                    f"python={len(observation.python)}/{observation.python_total} "
                    f"pythonTruncated={str(observation.python_truncated).lower()}"
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
                    f"check: cwd={check.cwd} command={check.command} source={check.source} reason={check.reason}"
                )
            if observation.changed_files:
                parts.append("changed_files:\n" + "\n".join(observation.changed_files[:120]))
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
        elif observation.kind == "multi_edit_file":
            lines.append(
                "\n".join(
                    [
                        f"{index}. multi_edit_file {observation.path}: {observation.message}",
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
        elif observation.kind == "insert_lines":
            lines.append(
                "\n".join(
                    [
                        f"{index}. insert_lines {observation.path}:{observation.line}: {observation.message}",
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
        elif observation.kind == "move_file":
            lines.append(
                f"{index}. move_file {observation.source} -> {observation.destination}: {observation.message}"
            )
        elif observation.kind == "start_command":
            lines.append(
                "\n".join(
                    [
                        f"{index}. start_command: {observation.message}",
                        f"processId: {observation.process_id or 'none'}",
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
                        f"running: {str(observation.running).lower()}",
                        f"exitCode: {observation.exit_code}",
                        f"signal: {observation.signal or 'none'}",
                        f"stdout:\n{truncate(observation.stdout)}",
                        f"stderr:\n{truncate(observation.stderr)}",
                    ]
                )
            )
        elif observation.kind == "list_processes":
            process_lines = [
                (
                    f"- {process.process_id} cwd={process.cwd} running={str(process.running).lower()} "
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
        elif observation.kind == "stop_process":
            lines.append(
                "\n".join(
                    [
                        f"{index}. stop_process {observation.process_id}: {observation.message}",
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
