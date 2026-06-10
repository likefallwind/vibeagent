# VibeAgent

VibeAgent v1 is a minimal command-line assistant written in Python. In coding mode,
it treats the directory where you run it as the real project workspace, asks the
configured model provider for a response, and lets the model call tools when it
needs file, Python symbol, call-site, runtime environment, or command access. Tool results are fed back to the model until the
task finishes or the iteration limit is reached. It also
includes a daily conversation mode for normal chat that does not write files or
run commands.

## Setup

```sh
python3 -m venv .venv
. .venv/bin/activate
python -m pip install -e .
```

There are no required third-party runtime dependencies.

MiniMax is the default provider. Set a MiniMax API key:

```sh
export MINIMAX_API_KEY="..."
```

The client reads the API key from environment variables automatically.
`MINIMAX_API` and `minimax_api` are also accepted as fallback environment variables.
If you paste a value like `Bearer sk-...`, VibeAgent strips the `Bearer` prefix automatically.
By default VibeAgent calls MiniMax's Anthropic-compatible endpoint at
`https://api.minimaxi.com/anthropic/v1/messages`.

To use DeepSeek or another OpenAI-compatible tool-calling API, switch provider:

```sh
export VIBEAGENT_PROVIDER="deepseek"
export DEEPSEEK_API_KEY="..."
```

The OpenAI-compatible adapter also accepts:

```sh
export VIBEAGENT_PROVIDER="openai-compatible"
export OPENAI_COMPAT_API_KEY="..."
export OPENAI_COMPAT_BASE_URL="https://api.example.com/v1"
export OPENAI_COMPAT_MODEL="model-name"
```

Project defaults can live in `.vibeagent/config.json`:

```json
{
  "provider": "deepseek",
  "model": "deepseek-reasoner",
  "base_url": "https://api.deepseek.com",
  "max_iterations": 20,
  "command_timeout_ms": 30000
}
```

Only non-secret defaults are read from that file. Provider defaults, execution
limits, and optional cost rates can live there. Keep API keys in environment
variables or pass a temporary `--api-key` for one command.

Create or update that file from the CLI:

```sh
python -m vibeagent --save-config --cwd ../my-project --provider deepseek --model-name deepseek-reasoner --base-url https://api.deepseek.com --max-iterations 20 --command-timeout-ms 30000
```

`--save-config` writes only non-secret defaults: `provider`, `model`, `base_url`,
`max_iterations`, and `command_timeout_ms`; it refuses to write API keys or
approval policy.

## Usage

```sh
python -m vibeagent
```

or through the npm compatibility scripts:

```sh
npm run dev
```

Pass a task as arguments to run once without entering the prompt:

```sh
python -m vibeagent --approval allow "inspect the failing tests and fix them"
python -m vibeagent --chat "explain this repository at a high level"
python -m vibeagent --resume <run-id> "continue the previous change"
python -m vibeagent --resume -- "continue the latest session"
python -m vibeagent --cwd ../my-project --max-iterations 8 --command-timeout-ms 120000 "run the release checks"
python -m vibeagent --json --cwd ../my-project "run the release checks"
python -m vibeagent --provider deepseek --model-name deepseek-reasoner --base-url https://api.deepseek.com "inspect this repo"
printf "summarize the project risks\n" | python -m vibeagent -
```

`--provider`, `--model-name`, `--base-url`, and `--api-key` are per-command
overrides; they do not rewrite environment variables or local config files.

Local inspection commands can also run without entering the prompt:

```sh
python -m vibeagent --doctor --cwd ../my-project
python -m vibeagent --model
python -m vibeagent --sessions --cwd ../my-project
python -m vibeagent --session <run-id> --cwd ../my-project
python -m vibeagent --usage --cwd ../my-project
python -m vibeagent --cost --cwd ../my-project
python -m vibeagent --save-config --cwd ../my-project --provider deepseek --model-name deepseek-reasoner --max-iterations 12
python -m vibeagent --json --doctor --cwd ../my-project
```

Use `/help` to list local commands, `/model` to inspect the configured provider,
model, base URL, and API key source, `/status` to inspect local mode, approval,
and resume state, `/context` to inspect the prompt context sources for coding
tasks, `/init` to create a starter `AGENTS.md`, `/doctor` to inspect local
configuration and workspace diagnostics, `/approval [ask|allow|deny]` to control
the session approval policy, `/resume [run-id|off]` to carry a previous coding
session summary into the next task or clear it, `/compact [run-id]` to explicitly
compact the newest or selected session into context, `/clear` to clear local chat
history and loaded resume context, `/usage` to summarize local session events,
iterations, tool calls, approvals, and recorded token usage, `/cost` to estimate
cost from configured per-million-token rates, and `/exit` to leave the interactive prompt.
Use `/chat` to switch to daily conversation mode and `/code` to switch back to coding
mode. You can also send one-off messages with `/chat <message>` or one-off coding
tasks with `/code <task>`. For generated code, the agent now prefers Python
scripts unless the user asks for another language.

Coding mode works in the current directory:

```sh
cd my-project
python -m vibeagent
```

VibeAgent may read and search `my-project` directly, including bounded repository maps with source outlines, directory tree inspection, path globbing,
file metadata inspection, Python symbol outlines, generic code outlines for common source languages, Python syntax checks, JSON/TOML config syntax checks, Python dependency inspection, generic source import/include inspection, generic source reference lookup, generic source definition excerpts, Python definition excerpts, Python call-site lookup, Python call graph inspection, Python reference lookup, AST-guided Python rename previews, bounded full-file reads with truncation metadata, focused single or batched line-range reads for large files, scoped exact or regex search with total/truncation metadata, dry-run regex replacement previews, structured JSON value update/removal and JSON Patch previews, and dry-run patch validation. It can create or replace several text files in one approved batch, apply AST-guided Python identifier renames after syntax validation, replace a unique Python class/function definition after syntax validation, replace exact text blocks, apply bounded regex replacements, update or remove one JSON value by JSON Pointer, apply multiple JSON add/replace/remove operations atomically, replace focused line ranges, insert text at a known line, append exact text to an existing file, or apply
single-file or multi-file unified diff hunks to existing files, and can safely
copy, move or delete one or several explicit files, adjust executable bits on individual files, create directories, copy directories, move directories, or delete empty directories. It can also inspect git branch/upstream state, list local branches and stashes, `git status`, structured changed-file summaries, pre-final review results with suggested checks, raw and structured `git diff` hunks, bounded untracked text-file previews, line-level `git blame`, fetch and fast-forward pull upstream state with approval, push current-branch commits to upstream with approval, switch or create local branches from a clean worktree with approval, stage or unstage explicit project paths, discard unstaged tracked-file changes with approval, save non-runtime changes to git stash with approval, apply stash entries to a clean worktree with approval, drop explicit stash entries with approval, and create local commits from staged changes with approval
through read-only tools, inspect fixed runtime/tool availability, preflight proposed shell commands, run short ordered verification command batches, inspect project manifests, and suggest relevant test/build commands from project
metadata and current changes. `AGENTS.md` files are included in the coding prompt
with their directory scopes, so nested instructions apply to files below that
directory. Project commands from root or nested `package.json`, `pyproject.toml`,
and `Makefile` files are shown as command hints with their `cwd` and executable availability. Long-running commands can be started as background
processes, inspected through captured stdout/stderr tails, sent exact stdin input, and stopped by
process id. In the CLI, edits, patches, writes, file lifecycle changes, and
command starts/runs ask for approval before execution. Session logs are stored
under `.vibeagent/sessions/<session-id>/events.jsonl`.
For multi-step coding tasks, the model can also maintain a compact task plan;
the latest plan is captured in the run result, session log, `/session` and
`/last` summaries, and `/resume` context. Each coding turn records its task, and
the CLI automatically uses the latest run as compact context for the next coding
turn; `/resume [run-id]` or `/compact [run-id]` can switch that context to an
older session, and `/resume off` or `/clear` clears it before a fresh task. `/usage`
reports locally recorded session usage and token counts when the provider returns
them. `/cost` uses optional `VIBEAGENT_INPUT_USD_PER_MILLION`,
`VIBEAGENT_OUTPUT_USD_PER_MILLION`, `VIBEAGENT_CACHE_CREATION_USD_PER_MILLION`,
and `VIBEAGENT_CACHE_READ_USD_PER_MILLION` values; without those rates it reports
the missing configuration instead of guessing. The model can also inspect compact
session summaries through a read-only tool without exposing full tool payloads.

Example task:

```text
写一个 Python 程序计算 1 到 100 的和并运行。
```

Example chat:

```text
/chat 今天适合学点什么？
```

## Architecture

VibeAgent is intentionally small. The runtime is a loop that asks the model for
a response. If the response includes tool calls, VibeAgent executes those calls
in the current project directory and sends tool results back on the next
iteration. If the response is plain text, the loop treats it as the final answer.

High-level flow:

```text
CLI input
  -> provider factory -> MiniMaxClient or OpenAICompatibleClient
  -> code mode: run_agent() -> build_messages() -> client.complete()
     -> plain text answer, or generic tool_call blocks -> execute_action()
     -> generic tool_result blocks appended to history
  -> chat mode: run_chat() -> client.complete() -> plain assistant reply
```

Core modules:

- `vibeagent/cli.py`: interactive command-line entry point. It handles local
  commands such as `/help`, `/model`, `/status`, `/context`, `/init`, `/clear`, `/usage`, `/cost`, `/approval`, `/resume`,
  `/compact`, `/chat`, `/code`, and
  `/exit`, then delegates input to the selected mode.
- `vibeagent/agent.py`: orchestrates the ReAct loop. It creates a run
  session, builds model prompts, executes optional tool calls, records events,
  tracks the model's latest task plan, and stops on a plain text answer, a
  `finish` tool call, or the iteration limit.
- `vibeagent/chat.py`: builds plain daily conversation prompts and keeps the
  model out of the coding-agent JSON action protocol.
- `vibeagent/providers.py`: selects the configured model provider. MiniMax is
  the default; DeepSeek and other OpenAI-compatible APIs use the OpenAI-compatible adapter.
- `vibeagent/prompts.py`: owns the system prompt and user message construction.
  Each prompt includes the original task, optional resumed session context,
  scoped `AGENTS.md` instructions, discovered project command hints with
  command `cwd` and executable availability, current run directory, workspace file snapshot, and previous observations.
- `vibeagent/minimax.py`: MiniMax API client. It reads API configuration from
  environment variables, converts VibeAgent's generic tool blocks to Anthropic-compatible
  MiniMax messages, and normalizes responses back into generic tool blocks.
- `vibeagent/openai_compat.py`: OpenAI-compatible client used by DeepSeek-style
  chat completions APIs. It maps generic tool blocks to `tool_calls` and `role: tool` messages.
- `vibeagent/actions.py`: defines the coding tools, validates tool inputs into
  typed actions, and executes them. Supported actions include `list_files`,
  `list_tree`, `repo_map`, line-range `read_file`, batch `read_files`, batch line-range `read_file_ranges`, `file_info`, `python_symbols`, `code_outline`, `python_check`, `config_check`, `check_json_set`, `json_set`, `check_json_remove`, `json_remove`, `check_json_patch`, `json_patch`, `python_dependencies`, `code_dependencies`, `code_references`, `code_definitions`, `python_definitions`, `python_calls`, `python_call_graph`, `python_references`, `python_rename_preview`, `python_rename`, path-pattern `glob`, scoped/regex/context `search`, `git_info`, `git_status`, `git_changes`, `git_branches`, `git_stashes`, `check_git_fetch`, `git_fetch`, `check_git_pull`, `git_pull`, `check_git_push`, `git_push`, `check_git_restore`, `git_restore`, `check_git_stash`, `git_stash`, `check_git_stash_apply`, `git_stash_apply`, `check_git_stash_drop`, `git_stash_drop`, `check_git_switch`, `git_switch`, `check_git_stage`, `git_stage`, `check_git_unstage`, `git_unstage`, `check_git_commit`, `git_commit`, `review_changes`, `final_review`, `suggest_checks`, `project_commands`, `project_manifests`, `project_overview`, `command_check`, `check_run_commands`, `run_commands`, `port_check`, `http_check`, `environment_info`, `git_diff`, `git_diff_hunks`, `git_log`, `git_show`, `git_blame`, `session_summary`, `check_edit_file`, `edit_file`,
  `check_multi_edit_file`, `multi_edit_file`, `check_replace_python_definition`, `replace_python_definition`, `check_replace_lines`, `check_insert_lines`, `check_append_file`, `check_regex_replace`, `regex_replace`, `replace_lines`, `insert_lines`, `append_file`, `check_patch`, `check_patches`, `patch_file`, `patch_files`, `check_write_file`, `write_file`, `check_write_files`, `write_files`, `check_delete_file`, `delete_file`, `check_delete_files`, `delete_files`, `check_move_file`, `move_file`, `check_move_files`, `move_files`, `check_copy_file`, `copy_file`, `check_copy_files`, `copy_files`, `check_move_dir`, `move_dir`, `check_move_dirs`, `move_dirs`, `check_copy_dir`, `copy_dir`, `check_copy_dirs`, `copy_dirs`, `check_create_dir`, `create_dir`, `check_create_dirs`, `create_dirs`, `check_delete_empty_dir`, `delete_empty_dir`, `check_delete_empty_dirs`, `delete_empty_dirs`, `check_set_executable`, `set_executable`,
  `run_command`, `check_start_command`, `start_command`, `list_processes`, `read_process`, `wait_process`, `check_write_process`, `write_process`,
  `check_stop_all_processes`, `check_stop_process`, `stop_all_processes`, `stop_process`, `update_plan`, and `finish`.
- `vibeagent/workspace.py`: treats the current directory as the project root,
  creates `.vibeagent/sessions/<session-id>/`, resolves relative file paths,
  rejects path escapes, protects `.git/` and `.vibeagent/`, and builds project
  file snapshots for prompts.
- `vibeagent/types.py`: shared dataclasses and protocols for chat messages,
  actions, command results, observations, and agent status.

The model contract is deliberately narrow and provider-neutral inside VibeAgent:
coding mode accepts plain text responses and uses generic `tool_call` and
`tool_result` blocks only when tools are needed. Provider adapters translate
those blocks to MiniMax Anthropic-compatible messages or OpenAI-compatible
`tool_calls`. Chat mode remains plain text and does not receive tools.

## v1 Boundaries

- Files are read and written only inside the current project directory.
- `.git/` and `.vibeagent/` are protected from model file actions.
- Project scans skip common generated directories plus root and nested `.gitignore` patterns.
- Multi-file patches are atomic and can modify existing text files, create new
  text files, or delete text files; they do not rename files.
- File copies, moves, and deletes are limited to explicit project files and still
  honor `.git/` and `.vibeagent/` protection. Batch copies, moves, and deletions
  validate all requested files before copying, moving, or removing any file.
- Directory lifecycle tools create, copy, or move project-relative directories and
  delete only empty directories, while still honoring `.git/` and `.vibeagent/`
  protection and refusing destination overwrites. Directory copies also refuse
  symbolic links and very large directory trees.
- Executable-bit changes are limited to individual project files and still
  honor `.git/` and `.vibeagent/` protection.
- Git staging tools modify only the local git index for explicit project-relative
  paths and require approval.
- Git restore discards only unstaged changes for explicit tracked
  project-relative paths, requires approval, and does not delete untracked files
  or change the git index. `check_git_restore` previews the diff that would be
  discarded without changing files.
- Git stash saves non-runtime changes with explicit pathspecs, requires
  approval, excludes `.vibeagent/`, and includes untracked files only when
  requested. `check_git_stash` previews the tracked diff and status without
  creating a stash; `git_stashes` lists recent stash entries.
- Git stash apply requires a clean worktree, accepts only `stash@{N}` references,
  requires approval, and does not drop stash entries. `check_git_stash_apply`
  previews the stash patch without changing files.
- Git stash drop accepts only `stash@{N}` references, requires approval, and
  permanently removes the selected stash entry. `check_git_stash_drop` previews
  the stash summary and patch without changing refs.
- Git fetch uses configured remotes only, runs `git fetch --prune`, may contact
  the remote, updates local remote-tracking refs, and requires approval.
  `check_git_fetch` validates remote selection and reports current ahead/behind
  state without contacting the remote. Git remote URLs shown to the model are
  credential-redacted.
- Git pull updates only the current branch from its configured upstream, uses
  `git pull --ff-only`, requires approval, and refuses dirty worktrees or
  divergent local commits. `check_git_pull` validates the same conditions
  without contacting the remote or changing files.
- Git push updates only the current branch's configured upstream, requires
  approval, refuses dirty worktrees, refuses cached behind/diverged state, and
  never force-pushes. `check_git_push` validates the same conditions without
  contacting the remote or changing refs.
- Git branch switching is local, requires approval, validates branch names with
  git itself, and refuses to switch or create branches while the worktree has
  uncommitted changes.
- Git commits are local, require approval, use currently staged changes only,
  and pass `--no-verify` so project hooks do not run implicitly.
- Reading or text-mutating binary/non-UTF-8 files fails as a tool result instead
  of crashing; use `file_info` to inspect type and size before reading or editing.
- `append_file` appends exact text to an existing UTF-8 file and does not add an
  implicit newline.
- `regex_replace` applies Python regular expression replacements to one existing
  UTF-8 file and refuses writes above the requested replacement bound.
- `json_set` updates one value, `json_remove` removes one object key or array
  item, and `json_patch` applies several add/replace/remove operations
  atomically in an existing UTF-8 JSON file using JSON Pointers. JSON writes
  rewrite valid JSON with two-space indentation; `json_set` can optionally
  create missing object keys.
  `check_write_file`, `check_write_files`, `check_edit_file`,
  `check_multi_edit_file`, `check_replace_lines`, `check_insert_lines`,
  `check_append_file`, `check_delete_file`, `check_delete_files`, `check_replace_python_definition`,
  `check_regex_replace`, `check_json_set`, `check_json_remove`, and `check_json_patch` preview
  their respective file diffs without writing changes. `check_move_file`,
  `check_move_files`, `check_copy_file`, and `check_copy_files` validate file
  transfers without changing files. `check_move_dir`, `check_move_dirs`,
  `check_copy_dir`, and `check_copy_dirs` validate directory transfers without
  changing files.
  `check_create_dir`, `check_create_dirs`, `check_delete_empty_dir`,
  `check_delete_empty_dirs`, and `check_set_executable` validate directory
  creation, empty-directory deletion, and executable-bit changes without
  changing files. Batch directory creation and empty-directory deletion validate
  every requested target before changing any directory.
  `check_git_fetch`, `check_git_pull`, `check_git_push`, `check_git_restore`, `check_git_stash`, `check_git_stash_apply`, `check_git_stash_drop`, `check_git_switch`, `check_git_stage`,
  `check_git_unstage`, and `check_git_commit` validate git remote, restore, stash save/apply/drop, branch,
  index, and local commit changes without contacting remotes, changing HEAD,
  changing the index, or creating commits.
- Full-file reads are bounded and report truncation metadata; use line-range
  reads for focused inspection of large files.
- `project_overview` is a read-only orientation bundle for unfamiliar tasks:
  shallow repo map, git identity/status, manifests, project commands, suggested
  checks, and runtime tool availability.
- `final_review` is a read-only handoff bundle for non-trivial code changes:
  blocking issues, warnings, changed files, and suggested verification commands.
- `file_info`, `python_dependencies`, `code_dependencies`, `code_references`, `code_definitions`, `check_write_file`, `check_write_files`, `check_edit_file`, `check_multi_edit_file`, `check_replace_python_definition`, `check_replace_lines`, `check_insert_lines`, `check_append_file`, `check_delete_file`, `check_delete_files`, `check_move_file`, `check_move_files`, `check_copy_file`, `check_copy_files`, `check_move_dir`, `check_move_dirs`, `check_copy_dir`, `check_copy_dirs`, `check_create_dir`, `check_create_dirs`, `check_delete_empty_dir`, `check_delete_empty_dirs`, `check_set_executable`, `check_git_fetch`, `check_git_pull`, `check_git_push`, `check_git_restore`, `check_git_stash`, `check_git_stash_apply`, `check_git_stash_drop`, `check_git_switch`, `check_git_stage`, `check_git_unstage`, `check_git_commit`, `check_regex_replace`, `check_json_set`, `check_json_remove`, `check_json_patch`, `git_info`, `git_status`, `git_changes`, `git_branches`, `git_stashes`, `review_changes`, `final_review`, `suggest_checks`, `project_commands`, `project_manifests`, `project_overview`, `command_check`, `check_run_commands`, `port_check`, `http_check`, `check_start_command`, `wait_process`, `check_write_process`, `check_stop_all_processes`, `check_stop_process`, `environment_info`,
  `git_diff`, `git_diff_hunks`, `git_log`, `git_show`, and `git_blame` are read-only and do not require approval.
  `suggest_checks` marks each suggested command with whether its main executable is available on `PATH`;
  `project_commands` lists project-defined npm, pyproject, and Makefile commands with cwd and executable availability;
  `project_manifests` reads package and pyproject dependency/script metadata;
  `command_check` does the same preflight for one proposed finite command and also reports cwd and block-rule failures;
  `check_run_commands` preflights a short ordered command batch without running it;
  `port_check` checks whether a local TCP host and port are reachable without running shell commands;
  `http_check` checks HTTP(S) status, final URL, and optional response content without running shell commands;
  `check_start_command` does the same for long-running commands without starting a process;
  `wait_process` waits for a background process to exit, time out, or emit configured stdout/stderr text or regex without stopping it;
  `check_write_process` validates that a running background process can receive stdin without writing input;
  `check_stop_all_processes` previews all tracked background processes without stopping them;
  `check_stop_process` validates a background process id without stopping it.
  Large `git_diff`, `git_show`, and `git_blame` outputs are bounded with truncation metadata.
- Commands run only from the current project directory.
- `run_command` is for one finite check. `run_commands` is for a short ordered
  finite verification sequence and runs commands sequentially, stopping on the
  first failure by default. `start_command` is for long-running
  commands such as dev servers and watchers. Both accept an optional project-relative
  `cwd` for package or service subdirectories; `run_command` and `run_commands` also accept
  optional per-command `timeout_ms` up to 10 minutes for slower tests or builds,
  and bounded stdout/stderr via `max_output_chars` so large logs do not flood
  the next model turn.
  `list_processes` shows background command ids and status, `read_process`
  and `wait_process` return recent captured output with optional `max_output_chars`,
  `write_process` sends exact text to a running background process stdin after approval,
  process observations include both VibeAgent process ids and OS pids, and
  `stop_process` / `stop_all_processes` terminate only processes VibeAgent started
  in the current Python runtime.
- File writes, batch file writes, file edits, JSON value updates/removals/patches, Python renames, Python definition replacements, file patches, file copies, file moves, file deletes, directory lifecycle changes, git fetches, git pulls, git pushes, git restores, git stashes, git stash applies, git stash drops, git branch switches, process stdin writes, and command
  starts/runs require approval in the CLI before execution. Library callers that
  do not provide an approval handler deny those actions by default.
- CLI approval defaults to `ask`; `/approval allow` approves future actions in
  the current session, and `/approval deny` rejects them without prompting.
- Some obviously dangerous commands, such as `sudo`, broad `rm -rf` targets,
  raw device writes, and network script pipes like `curl ... | bash`, are
  blocked. They stay blocked even if a caller approves command execution.
- Commands time out after 30 seconds by default.
- V1 is a local development prototype, not a strong OS sandbox. It does not try
  to block every dangerous shell command.

## Development

```sh
python -m unittest discover -s tests
npm test
```
