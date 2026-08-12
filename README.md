# VibeAgent

VibeAgent v1 is a project-aware command-line coding agent written in Python. In
coding mode, it treats the directory where you run it as the real project
workspace, asks the configured model provider for a response, and lets the model
call tools when it needs file, Python symbol, call-site, runtime environment, or
command access. Tool results are fed back to the model until the
task finishes or the iteration limit is reached. It also
includes a daily conversation mode for normal chat that does not write files or
run commands.

The current 1.0 usability scope and acceptance gates are tracked in
[`docs/vibeagent-1.0.md`](docs/vibeagent-1.0.md), with release readiness and
the required live-provider dogfood gate tracked in
[`docs/vibeagent-1.0-readiness.md`](docs/vibeagent-1.0-readiness.md).

## Setup

```sh
python3 -m venv .venv
. .venv/bin/activate
python -m pip install -e .
```

VibeAgent installs `jsonschema` as a required runtime dependency for validated
machine-readable agent results.

MiniMax is the default provider. Set a MiniMax API key:

```sh
export MINIMAX_API_KEY="..."
```

The client reads the API key from environment variables automatically.
`MINIMAX_API` and `minimax_api` are also accepted as fallback environment variables.
If you paste a value like `Bearer sk-...`, VibeAgent strips the `Bearer` prefix automatically.
By default VibeAgent calls MiniMax's Anthropic-compatible endpoint at
`https://api.minimaxi.com/anthropic/v1/messages`.

To use Anthropic's Claude Messages API directly:

```sh
export VIBEAGENT_PROVIDER="anthropic"
export ANTHROPIC_API_KEY="..."
```

The Anthropic adapter defaults to `claude-sonnet-5` at
`https://api.anthropic.com/v1/messages`. Override it with `ANTHROPIC_MODEL` and
`ANTHROPIC_BASE_URL`. Anthropic-format gateways can use
`ANTHROPIC_AUTH_TOKEN`; VibeAgent sends that value as a bearer token instead of
an `x-api-key`. Claude 5 requests omit sampling temperature as required by
those models.

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
  "command_timeout_ms": 30000,
  "max_output_tokens": 4096,
  "model_retries": 1,
  "model_retry_delay_ms": 250,
  "model_timeout_ms": 120000,
  "auto_memory_enabled": true
}
```

Only non-secret defaults are read from that file. Provider defaults, execution
limits, and optional cost rates can live there. Keep API keys in environment
variables or pass a temporary `--api-key` for one command.

### Native PowerShell tool

On Linux, macOS, and WSL, opt in to the Claude-compatible native `PowerShell`
tool by installing PowerShell 7 (`pwsh`) and setting:

```sh
export CLAUDE_CODE_USE_POWERSHELL_TOOL=1
```

Windows enables the tool automatically when `pwsh.exe` or `powershell.exe` is
available; set `CLAUDE_CODE_USE_POWERSHELL_TOOL=0` to disable it. The tool runs
with `-NoProfile -NonInteractive`, uses the same workspace sandbox and bounded
output processing as `Bash`, and always follows the normal command approval
flow. It is hidden from the model when disabled, unavailable, or in plan mode.

### Shell working directory

Main-session `Bash`, native `PowerShell`, and interactive `!` commands preserve
their final working directory for later shell commands in the same session. The
directory must remain inside the project or an added working directory; an
outside, deleted, protected, or invalid path resets to the project root and is
reported in the command result. Background Bash commands start in the current
session directory, while subagents intentionally start each command from their
own project root. Set `CLAUDE_BASH_MAINTAIN_PROJECT_WORKING_DIR=1` to disable
carry-over. Valid state is restored on session resume and branch continuation.

### Session shell environment

`SessionStart` and `CwdChanged` hooks receive `CLAUDE_ENV_FILE`, which points to
the private session file `.vibeagent/sessions/<session-id>/environment.sh`.
Hooks can append POSIX `export` statements or replace the file to configure
later foreground, background, interactive, and subagent Bash commands. Ordinary
`export` commands still do not persist because each Bash action uses a separate
process. The environment file is reused on resume and copied for a session
branch, limited to 128 KB, forced to mode `0600` on POSIX, rejected when it is a
symlink, and checked against the same hard command blocks before it is sourced.

Auto memory is enabled by default. VibeAgent stores machine-local Markdown notes
under the main Git worktree's `.vibeagent/memory/` directory, so linked
worktrees share one memory without committing it. At session start it loads at
most the first 200 lines or 25 KB of `MEMORY.md`; topic files are available
through `memory_list` and `memory_read`. `check_memory_write` previews a bounded
diff before `memory_write` requests approval. Writes are atomic, reject path
traversal and symlinks, and redact recognized
credentials. Set `"auto_memory_enabled": false` in project config or export
`VIBEAGENT_DISABLE_AUTO_MEMORY=1` to disable startup loading.
Agent profiles may instead select `memory: user`, `memory: project`, or
`memory: local`. User memory is shared across projects under
`~/.claude/agent-memory/<agent>/`; project and local memory remain isolated
under the corresponding project `.claude/` directories. User memory directories
and files use private `0700` and `0600` modes. `VIBEAGENT_USER_HOME` redirects
user agents, skills, commands, memory, settings, and plugin storage for isolated
development and tests.

Create or update that file from the CLI:

```sh
python -m vibeagent --save-config --cwd ../my-project --provider deepseek --model-name deepseek-reasoner --base-url https://api.deepseek.com --max-iterations 20 --command-timeout-ms 30000 --max-output-tokens 4096 --model-retries 1 --model-retry-delay-ms 250 --model-timeout-ms 120000
```

`--save-config` writes only non-secret defaults: `provider`, `model`, `base_url`,
`max_iterations`, `command_timeout_ms`, `max_output_tokens`, `model_retries`,
`model_retry_delay_ms`, and `model_timeout_ms`; it refuses to write API keys or
approval policy.

## Usage

```sh
python -m vibeagent
```

Interactive coding and chat turns stream user-facing assistant text as it
arrives when the active client supports incremental responses. Thinking blocks,
tool inputs, and protocol events remain hidden. Provider fallback restarts and
normal retries are separated visibly, interrupted text is line-terminated, and
the completed message is not printed a second time. Custom clients without
`complete_stream` retain the non-streaming path. Coding turns with an active
`MessageDisplay` hook deliberately stay non-streaming so raw text cannot bypass
the hook's final display transformation; the session records
`model_streaming_disabled` with that reason.

Confirm the installed package version:

```sh
python -m vibeagent --version
```

For first-class browser verification, install the optional `agent-browser`
runtime and its browser binary:

```sh
npm install -g agent-browser
agent-browser install
```

The deferred tools `browser_open`, `browser_snapshot`, `browser_act`,
`browser_read`, `browser_screenshot`, and `browser_close` then let an agent
exercise a real HTTP(S) UI, inspect accessibility references, fill and click
controls, read DOM/console/error state, capture workspace screenshots, and
release the isolated browser session. Every browser call uses the normal
approval policy. VibeAgent supplies a private per-session name, ignores project
and user `agent-browser` configuration, removes proxy/profile/credential
environment variables, bounds returned text, and locks page navigation to the
approved host. Browser URLs reject credentials, mixed public/private DNS
answers, and link-local, multicast, reserved, or unspecified addresses.
Screenshots are limited to 25 MiB and atomically replace only a non-protected,
non-symlink workspace path. VibeAgent does not install a browser automatically,
reuse a logged-in browser profile, expose JavaScript evaluation, or provide
cookie, credential, upload, proxy, or network-interception operations.

For native VS Code terminal and editor context integration, build and install
the dependency-free extension:

```sh
python3 scripts/build_vscode_extension.py
code --install-extension dist/vibeagent-vscode-1.0.0.vsix
```

The extension contributes an Agent Panel that dispatches and supervises
project-local background agents, displays bounded logs, sends follow-ups,
answers questions, resolves approvals, and lists committed or working-tree
changes. Each visible text file opens as an in-memory base-to-current native
VS Code diff. A confirmed `Apply changes` action copies the exact reviewed
snapshot from a stopped isolated agent into the main worktree as unstaged
changes; independently modified target paths reject the whole operation, while
unrelated main-worktree changes remain untouched. An explicit button opens the
isolated agent worktree in a new VS Code window for further inspection. It also
reuses a primary interactive terminal, opens additional parallel sessions, and
lists recent workspace sessions for exact-ID resume from a bounded Quick Pick.
A startup-activated workspace status item shows the number of open managed
interactive session terminals. Clicking it starts a primary session when the
count is zero or reveals the active, primary, or most recent session without
creating a duplicate.
A selected session plan opens as editable Markdown, and an explicit
`VibeAgent: Execute Reviewed Plan` command resumes the exact recorded session
with the reviewed text as a bounded one-shot task. It also runs a one-shot task
against the active selection, inserts an `@path#Lx-Ly` reference, sends up to
20 bounded diagnostics, and opens the active file against Git `HEAD` in VS
Code's native diff viewer. VibeAgent still runs in a real terminal, so approval
prompts retain their normal TTY behavior. The
extension launches an executable plus argument array without shell command
interpolation; those settings are machine-scoped so repository configuration
cannot replace the executable. Diagnostics are marked untrusted, stripped of
control characters and active `@file` syntax, and bounded before they enter a
task. Building the VSIX is deterministic and includes only an explicit source
allowlist. The extension never opens VS Code or a file manager by itself; its
commands run only after an explicit editor action.

Session history uses the provider-free `--json --sessions` CLI contract through
an argument array without a shell. The extension bounds runtime, stdout,
stderr, item count, and every rendered field before an ID can reach `--resume`;
path-like, duplicate, or malformed catalog values fail closed. The
catalog subprocess does not receive live-context bridge credentials. Resuming
an already open ID reveals its existing terminal, while file references prefer
the active managed VibeAgent terminal and otherwise fall back to the primary
workspace session.

Session inspection uses one provider-free `--json --session-inspect RUN_ID`
call to load a bounded overview, plan, persistent task graph, verification report, file list, and
timeline. The extension validates the returned identity, counts, statuses, and
truncation flags before opening native Markdown for read-only review. Reports
show at most 20 plan items, 50 persistent tasks, 50 checks per verification group, 100 files, and 80
timeline events. Workspace, session, and display-name metadata remain in
trusted extension memory, so editing the document cannot change the exact ID
used by `Resume Inspected Session`.

`Refresh Inspected Session` re-reads that exact out-of-band session ID and
updates the active Markdown document in place. An unchanged generated snapshot
refreshes without confirmation; local document edits require an explicit modal
replacement, cancellation preserves them, and a document or text change while
the modal is open aborts the update instead of overwriting newer input.
The aggregate also includes at most 50 entries from the persistent session task
graph. Invalid IDs, inconsistent status totals or dependencies, corrupt JSON,
and symlinked task stores fail the whole inspector rather than being rendered as
an empty graph.

`Open Inspected File` refreshes the exact session file report, then offers only
currently available regular files no larger than 10 MiB whose real paths remain
inside the real workspace. POSIX and Windows absolute paths, drive-relative
paths, traversal, directories, missing files, and external symlink targets are
excluded. The selected real path is resolved again before VS Code opens it, so
a target change while Quick Pick is active fails closed. This command opens an
editor document only; it never launches a file manager.

While a managed Session Inspector is active, its editor title exposes refresh,
open-file, and continue-task actions; resume and verification remain in the
title overflow menu. The visibility key comes from the extension's private
document registry, so ordinary or edited Markdown cannot activate these controls.

`Continue Inspected Task` refreshes that exact session before selection and
offers only unblocked `pending` or `in_progress` persistent tasks, with active
work listed first. The chosen task is wrapped as bounded, explicitly untrusted
context and passed to a visible one-shot terminal after `--resume RUN_ID`.
Completed and dependency-blocked tasks are excluded, cancellation creates no
terminal, and normal workspace approvals remain in force.

`Run Inspected Verification` refreshes the same trusted session immediately
before execution, shows the current failed and pending checks in a modal
confirmation, and runs at most 10 de-duplicated checks in a visible one-shot
terminal. The launch uses an argument array with the exact stored session ID,
extracts source contexts and diagnostics, does not become a file-reference
target, and does nothing when confirmation is cancelled.

Plan review uses the provider-free `--json --plan RUN_ID` contract through the
same bounded local client. The extension validates the returned session ID,
status, task, item count, item statuses, and text limits before opening an
untitled Markdown editor. Session and workspace execution metadata remain in
trusted extension memory rather than being parsed from editable text. Executing
the review places `--resume RUN_ID` before the bounded task argument and keeps
that one-shot terminal outside interactive file-reference routing.

Session rewind is a separate two-step workflow. `Review Session Rewind` selects
an exact session checkpoint and one of `both`, `code`, or `conversation`, then
opens the checkpoint's bounded staged and unstaged patches as Markdown after a
provider-free preflight. The trusted session, checkpoint, mode, and workspace
identity stay in extension memory rather than editable text. `Execute Reviewed
Rewind` repeats the preflight, requires an explicit modal confirmation, and then
restores code, creates a new conversation branch, or performs both operations.
A conversation branch opens by resuming the exact new session ID returned by the
CLI.

The Agent Panel launches the existing Remote Control service on `127.0.0.1`
without shell interpolation. Its generated bearer token remains in the trusted
extension host and is never sent to the Webview. Webview messages use an action
allowlist and validated IDs; approval and question responses carry the exact
request ID that was rendered, so stale UI actions cannot resolve a newer
interaction. Closing the panel terminates the control service without stopping
the independently supervised background agents.

Change review accepts only a private recorded session root that belongs to the
same Git common directory and matching project subdirectory. It exposes at most
200 project-relative files, omits sensitive and generated paths, and rejects
symlinks, binary/non-UTF-8 content, stale paths, and files over 1 MiB. Absolute
worktree paths remain in the extension host and are not sent to the Webview.
Integration supports regular files, deletions, binary content, and executable
bits within bounded per-file and aggregate limits. It revalidates the snapshot
under the agent transition lock, applies writes atomically, rolls back completed
operations on failure, and never stages or commits the result.

Terminals launched by the extension also receive a private live-context bridge.
As the active editor, selection, dirty state, or diagnostics change, the
extension atomically refreshes an owner-only temporary JSON file authenticated
with a per-bridge 256-bit token. Each VibeAgent turn revalidates the token,
file mode and ownership, exact workspace root, non-sensitive non-symlink file
path, 1,000-line selection limit, and 20-diagnostic limit before adding the
metadata as explicitly untrusted prompt context. The bridge never sends source
text or unsaved buffers, and its credentials are removed from environments
passed to project commands, hooks, MCP servers, LSP servers, and plugin tools.
The temporary bridge directory is removed when the extension deactivates.

Before cutting a release, verify an editable install from outside the source
tree:

```sh
npm run test:install
```

or through the npm compatibility scripts:

```sh
npm run dev
```

Pass a task as arguments to run once without entering the prompt:

```sh
python -m vibeagent --approval allow "inspect the failing tests and fix them"
python -m vibeagent --trust-project-permissions "run the checks allowed by this project's permission rules"
python -m vibeagent --trust-status --cwd ../my-project
python -m vibeagent --trust-project --cwd ../my-project
python -m vibeagent --untrust-project --cwd ../my-project
python -m vibeagent --sandbox-status --cwd ../my-project
python -m vibeagent --chat "explain this repository at a high level"
python -m vibeagent --resume <run-id> --resume-max-files 25 --resume-max-commands 5 --resume-max-checks 20 "continue the previous change"
python -m vibeagent --resume <run-id> --fork-session "try a different implementation"
python -m vibeagent --name auth-refactor "implement the authentication refactor"
python -m vibeagent --session-id <run-id> "continue the previous change"
python -m vibeagent --session-id latest "continue the latest session"
python -m vibeagent --resume -- "continue the latest session"
python -m vibeagent --no-auto-compact "start this task without prior session context"
python -m vibeagent -r <run-id> -p "continue the previous change"
python -m vibeagent -c --permission-mode plan --max-turns 3 "inspect the latest change"
python -m vibeagent -c
python -m vibeagent --compact <run-id> --compact-max-output-chars 0 --compact-max-checks 20 "continue from a compact handoff"
python -m vibeagent --cwd ../my-project --max-iterations 8 --command-timeout-ms 120000 --max-output-tokens 8192 --model-retries 2 --model-retry-delay-ms 500 --model-timeout-ms 120000 "run the release checks"
python -m vibeagent --json --cwd ../my-project "run the release checks"
python -m vibeagent -p --output-format json --max-budget-usd 1.00 --cwd ../my-project "run the release checks"
python -m vibeagent -p --no-session-persistence --output-format json --cwd ../my-project "run an isolated CI check"
python -m vibeagent -p --output-format json --fallback-model backup-model --cwd ../my-project "run the release checks"
python -m vibeagent -p --output-format json --json-schema '{"type":"object","properties":{"summary":{"type":"string"}},"required":["summary"]}' --cwd ../my-project "run the release checks"
python -m vibeagent --output-format stream-json --cwd ../my-project "run the release checks"
python -m vibeagent --brief --cwd ../my-project "implement the change and keep me updated"
python -m vibeagent -p --prompt-suggestions --output-format stream-json --cwd ../my-project "implement the change"
python -m vibeagent -p --output-format stream-json --include-hook-events --cwd ../my-project "audit hook execution"
python -m vibeagent -p --output-format stream-json --include-partial-messages --cwd ../my-project "run the release checks"
python -m vibeagent -p --output-format stream-json --forward-subagent-text --cwd ../my-project "delegate the investigation"
python -m vibeagent --bg --approval auto --cwd ../my-project "run the tests and fix failures"
python -m vibeagent agents --cwd ../my-project
python -m vibeagent --background-agents --cwd ../my-project
python -m vibeagent --background-agent-log <agent-id> --cwd ../my-project
python -m vibeagent --stop-background-agent <agent-id> --cwd ../my-project
python -m vibeagent --attach-background-agent <agent-id> --cwd ../my-project
python -m vibeagent attach <agent-id> --cwd ../my-project
python -m vibeagent --send-background-agent <agent-id> "continue with the focused tests" --cwd ../my-project
python -m vibeagent --respawn-background-agent <agent-id> --cwd ../my-project
python -m vibeagent --remove-background-agent <agent-id> --cwd ../my-project
python -m vibeagent remote-control --cwd ../my-project
python -m vibeagent remote-control --cwd ../my-project --remote-control-host 192.0.2.10 --remote-control-cert ./cert.pem --remote-control-key ./key.pem
python -m vibeagent --cwd ../my-project --add-dir ../shared-lib "update both codebases"
python -m vibeagent --cwd ../my-project --add-dir ../shared-lib --add-dir ../schemas
printf '{"type":"user","text":"inspect the change"}\n' | python -m vibeagent --input-format stream-json -
printf '{"type":"user","text":"inspect the change"}\n' | python -m vibeagent -p --input-format stream-json --output-format stream-json --replay-user-messages -
printf '{"prompt":"inspect the change"}\n' | python -m vibeagent --input-format json -
python -m vibeagent --append-system-prompt "Prefer focused tests before broad suites." "inspect the change"
python -m vibeagent --safe-mode --cwd ../my-project "diagnose startup without project customizations"
python -m vibeagent --settings ./review-settings.json --setting-sources user,project "inspect the change"
python -m vibeagent --plugin-dir ./extensions/team-tools "use the local review plugin"
python -m vibeagent --plugin-dir ./dist/team-tools.zip "test the packaged review plugin"
python -m vibeagent --plugin-url https://plugins.example.com/team-tools.zip "test the remote build artifact"
python -m vibeagent --bare -p "summarize README.md without host customizations"
python -m vibeagent --system-prompt-file ./prompts/reviewer.txt "inspect the change"
python -m vibeagent --append-system-prompt "Be concise." --append-system-prompt-file ./prompts/project-rules.txt
python -m vibeagent -p --append-subagent-system-prompt "Cite exact file paths." "delegate the investigation"
python -m vibeagent --agent reviewer "inspect the change with the reviewer profile"
python -m vibeagent --allowed-tools "Read" --allowed-tools "Bash(git diff:*)" --disallowed-tools "Bash(git push:*)" "inspect the change"
python -m vibeagent --mcp-config docs.mcp.json "use the docs MCP server to check the API"
python -m vibeagent --mcp-config docs.mcp.json --strict-mcp-config "use only this MCP config"
python -m vibeagent --cwd ../my-project --worktree feature-auth "implement authentication"
python -m vibeagent --cwd ../my-project -w feature-auth
python -m vibeagent --provider deepseek --model deepseek-reasoner --base-url https://api.deepseek.com "inspect this repo"
python -m vibeagent --provider anthropic --effort high "inspect this repo thoroughly"
python -m vibeagent --autocompact 200k "inspect a large repository"
python -m vibeagent 'review @src/app.py and @"docs/design notes.md"'
printf "summarize the project risks\n" | python -m vibeagent -
```

`--safe-mode` (or `CLAUDE_CODE_SAFE_MODE=1`) starts a clean diagnostic session.
It disables project instructions, skills, custom agents and commands, plugins,
hooks, MCP servers, LSP configuration, workflows, status-line customization,
and auto-memory while preserving authentication, model selection, built-in
tools, explicit invocation prompts, permissions, and sandbox enforcement.
Custom agent and MCP CLI flags, plus Setup-hook modes, are rejected when the
flag is active. The setting propagates through resume, fork, background, goal,
and subagent execution.

`--bare` is the reproducible scripting boundary. It skips automatic discovery
of project/user instructions, agents, commands, skills, hooks, installed
plugins, MCP servers, auto-memory, and settings files, while retaining built-in
file and shell tools, permissions, model configuration, and explicit system
prompt flags. Unlike safe mode, bare mode permits explicit `--settings`,
`--agents`, `--mcp-config`, `--plugin-dir`, and
`--plugin-url` inputs; invocation plugins may contribute their own commands,
skills, agents, hooks, and MCP servers. The mode remains active across
interactive, one-shot, resumed, forked, ephemeral, worktree, and background
runs without changing normal stdout or machine output.

`--settings JSON_OR_PATH` applies one bounded invocation-only settings object
after the selected files. `--setting-sources user,project,local` selects which
Claude-compatible settings files participate; an empty value disables all file
sources. The same immutable snapshot reaches provider environment setup,
permissions, hooks, sandboxing, agents, plugins, resumed and forked sessions,
subagents, and background continuation. Inline content is never written to
normal settings files or session events; interactive background handoff stores
it in a private mode-`0600` session file.

`--background` / `--bg` detaches one persistent, one-shot coding session and
returns a project-local agent ID immediately. Management commands and the
matching interactive slash commands list agents, read bounded stdout/stderr,
queue a follow-up message, respawn a running or stopped worker, stop a running process
group, attach the same session to a full interactive terminal, or remove its
supervisor record and logs. Follow-ups retain the same
agent ID and resume the same transcript; a message sent while the worker is
active runs as the next turn, while a message sent after exit respawns the
worker automatically. `attach ID` (or `--attach-background-agent ID`) claims a private foreground
lease, waits for an active worker to finish its current turn without consuming
another queued message, and resumes the recorded transcript and worktree in the
normal interactive CLI. This transfers approval prompts and all interactive
commands to the attached terminal. Exiting releases the lease but preserves the
supervisor entry and transcript. Inside an active coding session, `/bg [prompt]`
(or `/background [prompt]`) closes the foreground runtime and starts the next
turn from the same recorded session. Omitting the prompt uses an autonomous
continuation instruction; an Agent View attachment releases its lease before
reusing the existing agent ID. Removal preserves the normal session transcript, so a
generated name such as `background-<agent-id>` remains resumable. This is
autonomous background execution with reply, respawn, and safe terminal attach;
`agents` opens a full-screen project dashboard without adding a terminal UI
dependency. It auto-refreshes grouped `Needs attention`, `Working`, `Stopped`,
and `Completed` sessions; arrow keys select a row, Space peeks at bounded recent
output, Enter attaches, and single-key actions dispatch, reply, stop, respawn,
approve or deny a pending side effect, answer a blocking `AskUserQuestion`, or
confirm removal. Waiting interactions show bounded action risk or described
question options under `Needs attention`; exact request IDs prevent stale
answers from releasing a later request. Dashboard dispatches from a Git project
automatically start in a generated `.vibeagent/worktrees/` worktree so parallel
agents do not write the same checkout; non-Git projects retain their original
directory, and shell `--bg` sessions isolate only when explicitly passed
`--worktree`. The dashboard uses an alternate screen and restores the
original terminal on normal exit, interruption, prompts, and attach. It is
project-scoped; machine-global aggregation across unrelated repositories is not
part of the 1.0 dashboard.

`remote-control` (also `--remote-control`) serves a responsive browser control
plane for the same project-local background agents. It can dispatch tasks,
refresh status and bounded logs, queue follow-ups, approve or deny side effects,
answer structured questions, and stop, respawn, or remove workers. Each launch
generates a 256-bit bearer token and prints it only in the URL fragment, while
the API rejects unauthenticated requests, disables caching and framing, and
applies a restrictive content security policy. The default listener is
`127.0.0.1` on an available port. A non-loopback IPv4 listener is rejected
unless `--remote-control-cert` and `--remote-control-key` provide TLS, so tokens
are not sent over plaintext LAN traffic. This is a self-hosted Remote Control
server for detached VibeAgent sessions; it does not connect to claude.ai, sync
an active foreground conversation, or aggregate unrelated project registries.

Background stdin remains closed. Ask-mode permission requests and model
questions pause through private owner-only request/response files until they are
resolved from Agent View; session-scoped approvals retain their normal matching
semantics. Stop, respawn, removal, and attach treat unresolved input as a live
worker state and cannot accidentally create a second worker or discard it.
Explicit `--api-key` values are rejected for
background launch; provide credentials through the provider environment
instead. Launch records and logs live under
`.vibeagent/background-agents/`: directories use owner-only permissions, files
use owner read/write permissions, and the private launch payload is deleted by
the worker before the task runs. A private bounded config preserves the original
API-key-free CLI options for later turns, an atomic FIFO inbox stores pending
messages, and a per-agent worker token prevents inherited environment variables
from authorizing nested CLI processes. Status uses both the PID start time and
a durable exit marker to avoid mistaking PID reuse or a reaped process for a
running agent. Attachment leases use the same process-identity checks, expose
`attaching` and `attached` states, recover after an attached terminal crashes,
and block conflicting send, respawn, stop, or remove operations.

Coding prompts accept Claude-style `@path` file references. Unquoted paths end
at whitespace; use `@"path with spaces.md"` or `@'path with spaces.md'` when
needed. Append `#5-10` or `#L5-L10` for an inclusive text-file line range, or
`#L5` for one line. Selected lines are numbered in model context, ranges must
stay inside the file and contain at most 1,000 lines, and image references do
not accept line selectors. In an interactive terminal, type `@` plus a path
prefix or file-name fragment and press Tab for bounded project path completion; slash commands use
the same terminal-native completion. Suggestions exclude ignored, sensitive,
protected, and symlinked paths and never launch a GUI file picker. VibeAgent
resolves at most ten unique references inside the active
workspace before calling the model. UTF-8 text is limited to 20 KB per file and
100 KB total; up to two supported images are limited to 5 MB each and 10 MB
total. Missing, escaping, sensitive, binary, oversized, or excess references
fail before the provider call. Session events retain the original task and
bounded file metadata, never injected text or image bytes; image payloads are
removed from model history after the first response while text context survives
compaction.

`--add-dir PATH` grants an interactive or one-shot coding session access to an
additional working directory and can be repeated. Relative values are resolved
from the directory where VibeAgent was invoked, before `--cwd` changes the main
project. The model receives the normalized directory list and uses absolute
paths for file reads, edits, writes, search, repository maps, code lookup, and
command `cwd`; unlisted paths remain outside the workspace. Each additional
root protects its own `.git`, `.vibeagent`, sensitive files, and symlink escape
boundary. When command sandboxing is active, additional roots are mounted with
the same write access as the main project. Additional directories grant file
access only: instructions, hooks, agents, MCP, permissions, sandbox settings,
session state, dedicated Git tools, and project snapshots still come from the
main project. `--add-dir` is not accepted in chat mode, with local inspection
flags, or together with `--worktree`.

Inside an interactive coding session, `/add-dir` lists the active roots,
`/add-dir PATH` adds one, `/add-dir remove PATH` removes one, and `/add-dir
clear` removes all additional roots. Quoted paths with spaces are supported.
Changes apply to subsequent agent turns, background workflows, idle scheduled
tasks, and terminal `@path` completion; files under added roots are suggested as
absolute paths. The latest directory set is recorded in the active session and
restored by interactive or one-shot resume/compact, while unavailable stored
paths are skipped instead of expanding the workspace boundary.

Use `/cd PATH` to switch the main project without leaving the interactive
conversation. Relative and quoted paths are supported. VibeAgent ends the old
project runtime, starts a new session branch under the target project, reloads
its provider and trusted project configuration, and keeps the current mode,
conversation, goal, approval policy, and valid additional roots.

`--provider`, `--model MODEL` / `--model-name MODEL`, `--base-url`, `--api-key`,
`--effort auto|low|medium|high|xhigh|max`,
`--autocompact auto|TOKENS`,
`--max-iterations`, `--command-timeout-ms`, `--max-output-tokens`,
`--model-retries`, `--model-retry-delay-ms`, and `--model-timeout-ms` are
per-command overrides; they do not rewrite environment variables or local config
files.
`--effort` applies to interactive startup and one-shot code or chat requests.
`CLAUDE_CODE_EFFORT_LEVEL` accepts the same values, takes precedence over the
CLI option and agent profiles, and locks `/effort` for that process. Providers
without an effort request field reject non-automatic levels before the model
request.
`--autocompact` controls proactive coding-context compaction for the main agent
and inherited subagent or workflow sessions. `auto` keeps the built-in
message-count and character thresholds. Explicit values from 100k through 1m
replace the message-count trigger with a conservative estimated-token threshold
that reserves 20k tokens for system, tool, and output overhead. Claude-compatible
forms include `200`, `200k`, `200000`, and `1m`. Context-limit errors still force
compaction and retry regardless of the configured proactive threshold. Interactive
`/status` reports the active setting. This option is separate from
`--no-auto-compact`, which controls loading the latest prior-session handoff.
`--agents JSON` defines up to 100 invocation-scoped agent profiles for coding
sessions. The value is an object keyed by agent name; each definition uses
the normal profile fields plus a required `prompt`, for example
`--agents '{"reviewer":{"description":"Reviews code","prompt":"Inspect evidence only","tools":["Read"]}}'`.
Dynamic profiles use the same structured profile validation as file-backed
`.claude/agents` profiles. In addition to mode, model, effort, tool, skill,
memory, turn, and isolation controls, both forms accept `permissionMode`,
`mcpServers`, `hooks`, `initialPrompt`, `background`, and `color`. Dynamic
profiles override a same-name file profile for that invocation, propagate to
main, nested, background, workflow, and worktree runtimes, and do not create
agent profile files. Hook commands, inline MCP definitions, profile prompts,
and initial prompts stay out of profile catalogs and the main agent's initial
profile list.
For Claude-style scripting compatibility, `-p` / `--print` runs a one-shot task
and prints only the final text in normal text output, `-r` is an alias for
`--resume`, `--session-id RUN_ID` is an alias for `--resume RUN_ID`,
`--session-id latest` resumes the newest session, `-c` resumes the newest
session for a one-shot task,
`--worktree NAME` / `-w NAME` starts a fresh one-shot or interactive coding
session in `.vibeagent/worktrees/NAME` on branch `vibeagent/NAME`, leaving the
source checkout unchanged and preserving the isolated checkout after exit.
Omit `NAME` before `--` to generate one automatically. Non-secret project
defaults are copied into the linked checkout, while API keys remain environment
or command-line configuration. A repository-root `.worktreeinclude` uses Git
ignore syntax to copy matching files only when they are also untracked and
Git-ignored. It applies to CLI and subagent Git worktrees, evaluates patterns
with Git itself, excludes `.git`, `.vibeagent`, and worktree-storage runtime
paths, refuses symlinks and overwrites, and validates 1,000-file, 16 MiB
per-file, and 64 MiB total limits before copying anything. Custom
`WorktreeCreate` hooks own their setup and do not process `.worktreeinclude`.
Worktree launch cannot be combined with chat,
local inspection commands, resume, continue, or compact modes.
`--permission-mode` maps to `--approval`, accepting both VibeAgent values
(`ask`, `allow`, `auto`, `deny`, `dontAsk`, `plan`) and Claude-style values (`default` -> `ask`,
`acceptEdits` -> `ask` plus automatic `Write`, `Edit`, `MultiEdit`, and `NotebookEdit` allow rules,
`bypassPermissions` -> `allow`). `dontAsk` never opens an approval prompt: read-only
actions and trusted explicit allow rules can run, while every other action that
requires approval is denied. `--max-turns` maps to `--max-iterations`.
For unattended policy decisions, `-p --permission-prompt-tool MCP_TOOL` delegates
only unresolved `ask` or `auto` prompts to an advertised MCP tool. References may
use `mcp__SERVER__TOOL`, `SERVER/TOOL`, or a bare name that is unique across all
configured servers. The tool receives `{"tool_name": ACTION_TYPE, "input":
{"target": ..., "risk": ..., "preview": ...}}` and must return one JSON text or
`structuredContent` object containing either `{"behavior":"allow"}` or
`{"behavior":"deny","message":"..."}`. An unchanged `updatedInput` is accepted
for Claude compatibility, but policy tools cannot rewrite VibeAgent actions.
Resolution, transport errors, malformed or ambiguous decisions, and MCP
`isError` results fail closed. The selected policy tool is reserved from ordinary
model MCP calls, while project permission rules, hard command blocks, approval
events, background runs, and resumed turns retain their normal boundaries. Use
`--strict-mcp-config --mcp-config PATH` when automation must trust only an
explicit MCP configuration.
`--debug` emits redacted real-time diagnostics to stderr without changing normal
stdout or machine output. Use the equals form, such as
`--debug='api,mcp,!tools'`, to include or exclude `api`, `tools`, `mcp`, `hooks`,
`permissions`, `agents`, `startup`, and `session` categories; a space-separated
value remains task text for Claude CLI compatibility. `--debug-file PATH`
implicitly enables debugging and appends owner-only JSONL records to a regular,
non-symlink file. Debug file failures warn once without replacing the task
result, and the same options remain active for resumed and background runs.
`-p --max-budget-usd AMOUNT` stops a one-shot coding task when the shared
provider-cost estimate reaches the positive USD limit. Configure at least
`VIBEAGENT_INPUT_USD_PER_MILLION` and
`VIBEAGENT_OUTPUT_USD_PER_MILLION`; cache rates are required when the provider
reports cache usage. Main-agent, profile, subagent, goal-evaluator, and
structured-output calls share one serialized budget gate. Reaching the limit
returns subtype `error_max_budget_usd` without retrying or executing that model
response. Missing rates or provider usage fail closed instead of being treated
as zero cost.
`-p --fallback-model MODEL[,MODEL...]` creates up to ten ordered,
provider-scoped backup models before the coding run. Typed HTTP 503/529 failures
or explicit overload errors activate the first candidate and advance through
later candidates when an active fallback is also overloaded;
authentication, rate-limit, invalid-request, timeout, and ordinary runtime
errors do not. Once activated, the fallback remains sticky across main-agent,
profile, subagent, retry, goal-evaluator, and structured-output calls, avoiding
repeated probes of an overloaded primary. `model_fallback` session events and
the `modelFallback` / `model_fallback` machine result report the candidate list,
selected model/index, total and per-model use counts, overload transitions, and
bounded primary/fallback errors. When combined with
`--max-budget-usd`, all selected models consume the same budget and fallback evidence is
retained even if the response reaches the cost limit.
Bare `--tools` is a provider-free local command that prints the tool catalog.
On a one-shot coding task, `--tools "Read,Bash,Edit"` instead limits both the
model-visible schemas and executable tools. Claude-compatible aliases expand to
their VibeAgent implementations, the ceiling intersects selected main and
subagent profiles, and hidden model calls are rejected at runtime. Use
`--tools ""` to expose no tools or `--tools default` for the normal catalog.
This is separate from `--allowed-tools`, which grants matching operations
without an approval prompt but does not make tools visible or hide them.
An unconditional `--disallowed-tools Edit` rule removes the full compatible
edit alias family from model schemas, delayed activation, `ToolSearch`, and all
subagents, while still rejecting hallucinated calls at runtime. MCP rules can
disable one tool (`mcp__docs__search`) or a whole server (`mcp__docs` or
`mcp__docs__*`). Scoped rules such as `Edit(src/**)`, `Bash(git push:*)`, and
`WebFetch(domain:private.example.com)` stay visible and are evaluated against
the concrete action instead of disabling the whole tool.
`--agent PROFILE` selects one exact project or plugin agent profile for every
coding turn in a one-shot or interactive session. The profile prompt, preloaded
skills, memory namespace, `mode`, `model`, `effort`, `tools`,
`disallowedTools`, `maxTurns`, `permissionMode`, profile-scoped `hooks` and
`mcpServers`, and `initialPrompt` are enforced by the main loop. `model: inherit`
keeps the parent model; another bounded model ID creates a scoped
provider client without mutating the parent session client. Anthropic profiles
send `effort` as `output_config.effort`; MiniMax and OpenAI-compatible providers
reject profile effort explicitly because they do not implement that Claude
request field. Profiles that require `isolation: worktree` are rejected for
main sessions; use `--worktree` to isolate the whole session.
Agent Markdown files now use safe structured YAML frontmatter, so nested hook
and MCP definitions and YAML lists are supported while duplicate keys and
malformed structures are rejected. The field contract follows the
[Claude Code custom subagent documentation](https://code.claude.com/docs/en/sub-agents).
`background: true` forces subagent launches,
including workflow and nested launches, into the background; `color` is carried
through task observations, transcripts, and `ListAgents`. `permissionMode`
supports `default`/`manual`, `acceptEdits`, `auto`, `dontAsk`,
`bypassPermissions`, and `plan`. Parent `allow`, parent `acceptEdits`, and parent
plan constraints take precedence. Project profiles cannot use
`acceptEdits` or `bypassPermissions` until project configuration is trusted,
and VibeAgent hard command/path blocks remain active even under
`bypassPermissions`. Profile `auto` uses VibeAgent's provider-neutral conservative
classifier: workspace-scoped file changes are approved directly, explicit permission
rules and `PreToolUse` decisions retain priority, and other side effects are evaluated
without exposing tool results to the classifier. Profile MCP uses VibeAgent's
validated stdio/HTTP transports, and profile hooks use its bounded command-hook
schema. Under `--strict-mcp-config`, file profiles may reference only explicitly
loaded MCP servers; their inline definitions are ignored. Claude-compatible
plugin profiles ignore `permissionMode`, `mcpServers`,
and `hooks` while retaining the remaining profile fields.
One-shot code tasks can invoke personal skills from
`~/.claude/skills/*/SKILL.md`, project skills from `.claude/skills/*/SKILL.md`
or `.agents/skills/*/SKILL.md`, and legacy prompt commands from the matching
personal or project `.claude/commands/**/*.md` locations, for example:

```bash
python -m vibeagent --cwd ../my-project '/fix "login bug" src/app.py'
```

Built-in slash commands keep precedence. Personal definitions override project
definitions, and a skill overrides a legacy command with the same name. Skill
and command templates expand `$ARGUMENTS`, `$1`-`$9`, and `${1}`-`${9}` before
the agent run, and the session records the selected name, path, and arguments as
task metadata.
`--dangerously-skip-permissions` maps to
`--approval allow` for one-shot coding tasks and cannot be combined with
`--approval` or `--permission-mode`. `--input-format json` reads one JSON object
or array from stdin when the task is `-`; `--input-format stream-json` reads
newline-delimited JSON task records. Structured input accepts simple `text`,
`prompt`, or string `input` records, `message.content`, direct `message.prompt`
/ `message.input` text, SDK-style `messages` arrays, or Responses-style
top-level `input` message arrays and uses `role: "user"` / `type: "user"`
message text as the task when roles are present. System-role text becomes a
one-shot system prompt for that run, and assistant-role text is treated as
caller-supplied prior conversation context in coding mode. A top-level
`schemaVersion` is accepted when it is compatible with the current machine
output schema, and future schema versions are rejected before any provider
call. In coding mode with print mode, matching stream-JSON input and output,
and task `-`, `--replay-user-messages` emits each normalized non-empty user
message before agent events. System, assistant, event, and result records are
not replayed; arbitrary input fields are discarded instead of echoed. Replay
records carry the same run/session identifiers as later events and the final
result. A top-level `session_id` or `sessionId` field resumes that VibeAgent
session in coding mode when neither `--resume` nor `--compact` is provided.
When `-c`, `--resume [run-id]`, or `--compact [run-id]` is provided without a
task, VibeAgent starts the interactive prompt with that context already loaded.
`--system-prompt` or `--system-prompt-file` replaces the default system prompt;
the two replacement forms are mutually exclusive. `--append-system-prompt`
and `--append-system-prompt-file` add extra system-level constraints and may be
combined, with inline text placed before file content. All four options work
for interactive startup and one-shot code or chat modes and are never saved to
project configuration. Relative prompt-file paths are resolved from the
directory where VibeAgent was invoked, before `--cwd` or `--worktree` changes
the active project. Prompt files must be non-empty bounded UTF-8 regular files
and cannot use symbolic links. In print-mode coding tasks,
`--append-subagent-system-prompt` adds one invocation-scoped instruction after
each direct, nested, or resumed subagent's profile and task-specific system prompt. The
text is not persisted in project configuration or session events.
With `--json`, one-shot coding results include `schemaVersion`, the runtime
`version`, `status` (`completed`, `blocked`, `deferred`, or `failed`), matching
`stopReason`, `exitCode`/`exit_code`, `numTurns`, final text as `message` plus
a `result` alias,
`runId` plus a `sessionId` alias, a
`priorContext` object with loaded/source/run id metadata, structured `plan`
items,
`completionReady`, `completionBlockers`, `completionWarnings`,
`completionBlockedCount`,
`latestCompletionBlockers`, `latestCompletionPendingChecks`,
`latestCompletionFailedChecks`, `latestCompletionFinalReviewIssues`,
`latestCompletionFinalReviewChangedFiles`, `latestCompletionToolErrors`,
`latestCompletionCheckpointFailures`, `latestCompletionActiveProcesses`,
`latestCompletionDeniedApprovals`, `changedFiles`, `verificationChecks`,
`pendingVerificationChecks`, and `failedVerificationChecks` fields, plus
`durationMs`, a `usage` report, and a
`cost` report for the current run, so automation can read the same final-review,
blocked-attempt, changed-file, verification, timing, local token-usage, and
configured cost estimate status shown in the text UI.
Deferred print-mode results exit successfully with `stopReason`/`stop_reason`
`tool_deferred` and a redacted `deferredToolUse`/`deferred_tool_use` object
containing the pending call ID, name, and input. Resuming that session replays
the same call before the next model turn. If its tool is no longer available,
the resume exits nonzero with `tool_deferred_unavailable` and `isError` /
`is_error` true.
Machine output also includes Claude-style snake_case aliases for run status,
prior context, completion, latest-completion, changed-file, verification,
pending-user-input, and timing fields where applicable.
Machine-readable error results include `exitCode` and `exit_code` when the
CLI knows the process exit status for that failure.
Budgeted machine results include `budget`, `totalCostUsd`, and
`total_cost_usd`. Successful runs use subtype `success`; exhausted runs omit
the `result` alias, exit nonzero, and use subtype and stop reason
`error_max_budget_usd`.
`-p --json-schema '<schema>'` adds a validated final result to one-shot coding
tasks. VibeAgent completes the normal tool-using workflow first, then asks the
same provider for exactly one JSON value without tools. The schema must be a
bounded Draft-07 object; only resolvable local JSON Pointer references are accepted, and `format`
remains an annotation. Invalid output is corrected with at most three model
attempts. Successful JSON and stream-JSON results include `structuredOutput` /
`structured_output` and attempt-count aliases. Exhaustion returns a nonzero
exit with subtype and stop reason `error_max_structured_output_retries`.
Stream mode also emits redacted
`structured_output_model`, validation-failure, and result events.
`--output-format json` is equivalent to `--json`. `--output-format stream-json`
emits newline-delimited JSON for one-shot tasks: each durable session event is
written as a `type: "event"` record with `schemaVersion`, `version`, a
monotonically increasing `sequence`, `runId`, matching `sessionId` and
`session_id`, and the redacted event payload,
followed by exactly one `type: "result"` record containing the normal code or
chat result, including `schemaVersion` and `version`, with final text available
as both `message` and `result`.
Coding streams also emit one top-level `type: "system", subtype: "init"`
record after the effective tool catalog is known and before the first model
request. It contains bounded provider/model, tool, permission-mode, configured
MCP-server, enabled-plugin, and protocol-capability metadata without credentials.
Retryable model failures emit `type: "system", subtype: "api_retry"` before
their durable raw `model_error` event, with the attempt, configured retry limit,
delay, normalized error category, optional HTTP status, reason, and event UUID.
Explicit `-p --include-hook-events` additionally emits Claude SDK-compatible
top-level `type: "system"` records with subtypes `hook_started`,
`hook_progress`, and `hook_response` before their corresponding durable raw
hook events. `Setup` and `SessionStart` lifecycle records are always included;
other hook events require the flag. Hook IDs remain stable across one execution,
slow command hooks report bounded redacted stdout/stderr progress, and async
hooks emit their response only when they finish or are cancelled.
Metadata discovery failures are reported as bounded redacted init errors and do
not stop the coding run. Existing `type: "event"` records remain unchanged for
consumers that use the lower-level session-event protocol.
`--brief` enables the Claude-compatible `SendUserMessage` tool for coding
sessions. The agent can emit a concise non-blocking progress update and then
continue its current turn; use `AskUserQuestion` when an answer is required.
Messages are limited to 2,000 control-safe characters, redacted before durable
storage, displayed immediately as `Agent update:` in interactive and text
one-shot modes, and emitted as `agent_user_message` records in stream-JSON.
Text one-shot updates use stderr so final stdout remains scriptable, while JSON
output remains one final object. The tool is absent from the default agent
catalog and cannot be activated by a direct call or `ToolSearch` without the
flag; `--tools`, profile restrictions, and deny rules remain authoritative.
`--disable-slash-commands` disables all built-in and custom slash commands and
skills for the coding session. Skill metadata is omitted from prompts, the
`Skill` and `project_skills` tools cannot be discovered or called, and the
boundary is retained by resumed, ephemeral, and background runs. Unlike
`--safe-mode` or `--bare`, other project configuration such as hooks, MCP,
permissions, agents, and instructions remains enabled.
`--verbose` shows the complete coding turn sequence: non-streaming assistant
text plus each redacted, bounded tool call and result. Interactive sessions
write the transcript to the terminal; one-shot sessions use stderr so text,
JSON, and stream-JSON stdout remain machine-readable. The selected
`viewMode: "verbose"` setting enables the same behavior, while an explicit
`--verbose` overrides `default` or `focus`; safe mode ignores the setting.
`-p --prompt-suggestions[=true|false]` makes one tool-free, non-retrying model
request after a successful completed coding turn to predict a concise next user
prompt. The request reuses the completed conversation, active model/fallback,
timeout, and strict cost budget; failures, empty output, controls, or output over
1,000 characters suppress only the suggestion. Sensitive values are redacted
before delivery and the model/result evidence is stored in the session.
Stream-JSON emits the Claude SDK-compatible `prompt_suggestion` record with a
UUID and `session_id` strictly after the final `result`; matching Claude Code,
text and ordinary JSON keep their primary result unchanged. Set
`CLAUDE_CODE_ENABLE_PROMPT_SUGGESTION=false` to disable generation even when the
flag is present.
Explicit `-p --include-partial-messages` additionally emits each provider SSE
event as a `type: "stream_event"` record before the final result. Coding records
include the session identifiers, model iteration, and retry attempt; chat
records include iteration 1 and the retry attempt. Anthropic-compatible streams
are forwarded directly, while OpenAI-compatible chunks are normalized to the
same message/content-block event shape. Truncated and oversized streams fail
instead of returning partial output. Providers or custom clients without
incremental streaming support fail explicitly when this option is selected.
Every `permissions_loaded` event includes the loaded rule count, sources, and trusted
allow sources so CI logs can audit per-run overrides such as `acceptEdits`.
Every line is flushed immediately for CI and process supervisors. Stream mode
never opens
interactive approval or user-input prompts; with the default `--approval ask`,
side-effecting tools are denied unless a trusted permission rule or complete
sandbox auto-approval applies. Use `--approval allow` or
`--dangerously-skip-permissions` only in an appropriately isolated automation
environment. `stream-json` requires a one-shot task and is not accepted for the
interactive prompt or standalone local command flags. Partial messages require
print mode and stream-JSON output. User-message replay additionally requires
stream-JSON stdin, task `-`, and coding mode.
`--forward-subagent-text` requires print mode, stream-JSON output, and a
one-shot coding task. It emits sanitized subagent text and thinking as linked
assistant records, and subagent tool results as linked user records, immediately
after their source events. Every forwarded record includes the subagent ID and
the exact parent `Task`, `Agent`, or `SendMessage` tool-use ID; tool-call blocks
and tool inputs are not forwarded. Set `CLAUDE_CODE_FORWARD_SUBAGENT_TEXT=1`
to enable the same behavior for compatible invocations.
`--allowed-tools`/`--allowedTools` and `--disallowed-tools`/`--disallowedTools`
add Claude-style permission rules for one coding task without editing project
settings. Allowed CLI rules are trusted for that run and can skip side-effect
prompts; disallowed CLI rules take precedence through the normal deny/ask/allow
ordering. These flags accept rules such as `Read`, `Edit(src/**)`,
`Bash(git diff:*)`, or `WebFetch(domain:docs.python.org)`, and can be repeated.
`--json --doctor` keeps the human-readable `text` field and also includes a
structured `doctor` object with provider metadata, executable availability, cost
rate status, and command hard-block self-checks without exposing API key values.
`--model` without a value shows the active model provider configuration.
`--json --model` and `--json --config` include structured provider and
execution-configuration payloads with model/base URL, API-key configured/source
metadata, project-config status, execution limits, and cost-rate status without
exposing API key values.
All local `--json` payloads include top-level `schemaVersion`, runtime
`version`, `exitCode`/`exit_code`, and `stopReason`/`stop_reason` fields.
`--json --save-config` includes a structured `saveConfig` object with the
project config path, created/existing state, written non-secret keys, and the
saved non-secret config snapshot.
`--json --status` and `--json --context` include structured runtime status and
prompt-context payloads with mode, approval policy, resume state, project
instructions, command hints, and workspace snapshot text.
`--json --init [AGENTS.md|CLAUDE.md]` includes a structured `init` object with
the requested instruction file, resolved path, created/no-op state, existence
state, and any validation or write error.
`--json --permissions` likewise includes a structured `permissions` object with
approval-required tools by category, read-only tools, and command hard-block
self-checks.
`--json --tools`, `--json --tool <name>`, and `--json --tool-search <query>`
include structured tool catalog payloads with categories, approval-required
state, required input fields, search matches, property metadata, full input
schemas for single-tool lookups, and missing-tool suggestions. Tool search can
be filtered with `--tool-search-max`, `--tool-search-category`, and
`--tool-search-approval`.
`--json --checks` includes a structured `checks` object with shown and total
suggested verification commands, truncation state, changed files, and the same
message shown in the text UI.
`--json --review` includes a structured `review` object with readiness,
blocking issues, warnings, changed files, running background processes,
syntax-check summaries, suggested verification commands, focused test
commands inferred from changed files, and diff-check output.
`--json --handoff` includes a structured `handoff` object with final-review
readiness, blocking issues, warnings, changed files, running background
processes, suggested verification commands, focused test commands inferred
from changed files, filtered git status, and the latest plan text.
`--json --changes` includes a structured `changes` object with changed-file
counts, staged/unstaged/untracked totals, insertion/deletion totals, truncation
state, and shown file records.
`--json --diff`, `--json --diff-hunks`, and `--json --diff-contexts` include
structured diff payloads with scope, path, truncation, bounded patch text,
hunk metadata, and source contexts.
`--json --git-status`, `--json --conflicts`, `--json --git-info`, `--json --branches`,
`--json --log`, `--json --show`, `--json --blame`, and `--json --stashes`
include structured read-only git payloads with branch, status, commit, bounded
output, conflict markers, blame, and stash fields instead of requiring callers
to parse text.
`--json --check-git-stage`, `--json --git-stage`,
`--json --check-git-unstage`, `--json --git-unstage`,
`--json --check-git-commit`, `--json --git-commit`,
`--json --check-git-restore`, and `--json --git-restore` include structured
git mutation/preflight payloads with explicit paths, status text, commit heads,
bounded restore diffs, and command messages.
`--json --check-git-stash`, `--json --git-stash`,
`--json --check-git-stash-apply`, `--json --git-stash-apply`,
`--json --check-git-stash-drop`, and `--json --git-stash-drop` include
structured stash mutation/preflight payloads with message text, untracked-file
mode, stash refs, worktree-clean state, status text, bounded diffs/patches,
remaining stash counts, and command messages.
`--json --check-git-fetch`, `--json --git-fetch`, `--json --check-git-pull`,
`--json --git-pull`, `--json --check-git-push`, `--json --git-push`,
`--json --check-git-switch`, and `--json --git-switch` include structured
remote synchronization and branch-switch payloads with remote/upstream names,
current refs, ahead/behind counts, worktree-clean state, status text, and
command messages.
`--json --overview`, `--json --repo-map`, `--json --search`,
`--json --search-contexts`, `--json --find-files`, `--json --glob`, `--json --tree`, and
`--json --symbols` include structured project-inspection payloads with project
orientation metadata, matched file or directory paths, bounded tree entries,
source imports, symbol outlines, search snippets, truncation state, and
per-file errors.
`--json --commands`, `--json --related-tests`, `--json --manifests`,
`--json --instructions`, and `--json --todos` include structured project
discovery payloads with command metadata, related-test candidates, manifest
items, instruction sources/text, TODO markers, scanned-file counts, and
truncation state.
`--json --file-info` and `--json --image-info` include structured inspection
payloads with file type, size, line count, binary state, image format,
dimensions, and per-path errors.
`--json --read`, `--json --read-files`, and `--json --read-ranges` include
structured file-content payloads with paths, requested ranges, bounded content,
truncation state, and per-file or per-range errors.
`--json --check-replace-lines`, `--json --replace-lines`,
`--json --check-insert-lines`, `--json --insert-lines`,
`--json --check-append`, and `--json --append` include structured line-edit
payloads with path, affected line positions where applicable, success state,
message, and diff lines for preflight and applied edits.
`--json --check-json-set`, `--json --json-set`,
`--json --check-json-remove`, `--json --json-remove`,
`--json --check-json-patch`, and `--json --json-patch` include structured JSON
mutation payloads with path, JSON Pointer, parsed value or operation list,
success state, message, and diff lines for preflight and applied edits.
`--json --check-write`, `--json --write`, `--json --check-write-files`,
`--json --write-files`, `--json --check-edit`, `--json --edit`,
`--json --check-multi-edit`, `--json --multi-edit`, `--json --check-patch`,
`--json --patch`, `--json --check-patches`, `--json --patches`,
`--json --check-regex-replace`, and `--json --regex-replace` include structured
file mutation payloads with path, file list, or per-file entries, success state,
message, replacement metadata when relevant, and diff lines when the underlying
action reports a preview or edit diff.
`--json --check-delete`, `--json --delete`, `--json --check-delete-files`, and
`--json --delete-files` include structured delete payloads with path or path
list entries, success state, message, and deletion diff lines.
`--json --check-move`, `--json --move`, `--json --check-move-files`,
`--json --move-files`, `--json --check-copy`, `--json --copy`,
`--json --check-copy-files`, `--json --copy-files`, directory move flags, and
directory copy flags include structured transfer payloads with
source/destination pairs, success state, and messages.
`--json --check-mkdir`, `--json --mkdir`, `--json --check-mkdirs`,
`--json --mkdirs`, `--json --check-rmdir`, `--json --rmdir`,
`--json --check-rmdirs`, `--json --rmdirs`, `--json --check-executable`, and
`--json --set-executable` include structured directory lifecycle and
executable-bit payloads with paths, success state, mode data when relevant, and
messages.
`--json --python-check`, `--json --python-deps`, `--json --python-defs`,
`--json --python-refs`, `--json --python-ref-contexts`, `--json --python-calls`,
`--json --python-call-graph`, Python rename flags, and Python definition
replacement flags include structured Python code-intelligence and refactoring
payloads with syntax results, imports, definitions, references, source contexts,
call sites, call-graph edges, rename replacements, replacement diffs,
truncation state, and parse errors.
`--json --config-check` includes structured JSON/YAML/TOML syntax-check
payloads with path scope, checked-file counts, truncation state, per-file
format/status/location/message fields, and the overall check message.
`--json --code-deps`, `--json --code-refs`, `--json --code-ref-contexts`, and
`--json --code-defs`, plus code rename flags, include structured non-Python
code-intelligence and refactoring payloads with imports, dependencies,
definitions, references, source contexts, rename replacements, diffs,
truncation state, and per-definition errors.
`--json --tail`, `--json --around`, and `--json --around-many` include
structured file-context payloads with requested line windows, line counts,
target-line status, bounded content, truncation state, and per-context errors.
`--json --output-contexts`, `--json --output-diagnostics`, and
`--json --python-traceback` include structured diagnostics and source-context
payloads with extracted references, diagnostic severities, output-line numbers,
bounded code snippets, truncation state, and per-context errors.
`--json --command-check`, `--json --check-run-commands`,
`--json --check-suggested-checks`, and `--json --check-focused-tests` include
structured command preflight with cwd validity, hard-block state, executable
availability, missing tools, and command messages. `--json --focused-tests`
includes structured focused-test suggestions with target paths, related-test
totals, command metadata, availability, missing tools, and truncation state.
`--json --run-command`, `--json --run-commands`,
`--json --run-suggested-checks`, and `--json --run-focused-tests` include
structured finite-command payloads with cwd, timeout, stdout/stderr, exit code,
duration, stop-on-failure state, truncation state, and any auto-extracted diagnostics or
source contexts. `--json --check-start-command` includes structured background
command preflight with cwd validity, hard-block state, executable availability,
missing tools, and safety messages. `--json --start-command` includes the
started background process id, pid, cwd, stdout/stderr log paths, and safety
failure messages. `--json --env` includes structured runtime diagnostics with
platform, Python executable/version, git-repo state, and tool availability.
`--json --processes` includes structured background-process list data with
process ids, pids, commands, cwd, running state, exit codes, signals, and
normalized status strings.
`--json --check-stop-process`, `--json --stop-process`,
`--json --check-stop-all-processes`, and `--json --stop-all-processes` include
structured cleanup payloads with process ids, pids, status/result strings, exit
codes, signals, command/cwd metadata when available, and stop messages.
`--json --process-output-contexts` and `--json --process-output-diagnostics`
include structured background-process output analysis with process status,
captured stdout/stderr sizes, extracted references, diagnostic records, bounded
source snippets, truncation state, and per-context errors.
`--json --process-output` and `--json --wait-process` include structured
background-process reads with status, match/timeout state, captured stdout/stderr,
and any auto-extracted diagnostics or source contexts.
`--json --check-write-process` and `--json --write-process` include structured
stdin-write payloads with process ids, pids, running state, command/cwd metadata,
content length, optional `stdinFile` source paths, and write/preflight messages.
`--json --port-check`, `--json --http-check`, and `--json --http-fetch` include
structured local-service verification payloads with reachability, status,
matching state, timeout/body limits, bounded response bodies, and errors.
`--json --usage` includes a structured `usage` object with session, event,
approval, status, and token totals plus an explicit cost-unavailable reason.
`--json --cost` includes a structured `cost` object with usage totals,
configured rates, rate errors, missing-rate state, and provider cost estimates
when enough pricing data is configured.
`--json --checkpoint`, `--json --checkpoints`, `--json --checkpoint-show`,
`--json --checkpoint-diff`, `--json --checkpoint-status`, and checkpoint
preflight/execution flags include structured checkpoint payloads with saved
metadata, patch sizes, match/preflight state, mutation results, and recovery
messages.
`--json --session-rewind-points`, `--json --check-session-rewind`, and
`--json --session-rewind` include structured session-scoped checkpoint choices,
shared code/conversation preflight state, resolved checkpoint identity, mutation
results, and the new branch session ID when conversation history is rewound.
`--json --session-verification` includes a structured `sessionVerification`
object with verified, pending, and failed check groups, truncation state, and
machine-readable command/cwd entries for each shown check.
`--json --session-inspect` includes a structured `sessionInspect` object with a
bounded overview, plan, persistent tasks, verification groups, referenced files, and safe
timeline. Its fixed limits are suitable for one local IDE request without a
provider call.
`--json --session-tasks` includes a structured `sessionTasks` object with
bounded persistent tasks, status and blocked counts, owners, and dependency
edges. Metadata is omitted and stored task text is redacted before output.
`--json --run-session-verification` includes a structured
`runSessionVerification` object with selected failed/pending commands, command
results, stop-on-failure state, and aggregate duration.
`--json --sessions` includes a structured `sessions` object with recent session
run ids, statuses, event counts, last event times, and tasks.
`--json --last` and `--json --session` include a structured `sessionSummary`
object with status, counts, usage, approvals, plan, verification, completion,
checkpoint, model-error, and background-process summaries.
`--json --plan` includes a structured `sessionPlan` object with the latest
task plan status and items.
`--json --transcript` includes a structured `sessionTranscript` object with a
safe timeline summary, event counts, malformed-row counts, and truncation
state.
`--json --session-search` includes a structured `sessionSearch` object with
bounded safe timeline matches and truncation state.
`--json --session-failures` includes a structured `sessionFailures` object with
bounded failed tools, failed commands, denied approvals, malformed events, and
failed final results.
`--json --session-commands` includes a structured `sessionCommands` object with
bounded command result metadata, duration, and stdout/stderr tails.
`--json --session-output-contexts` includes a structured
`sessionOutputContexts` object with command scan counts, extracted
file-reference contexts, source snippets, and truncation state.
`--json --session-output-diagnostics` includes a structured
`sessionOutputDiagnostics` object with extracted diagnostics, source contexts,
and truncation state.
`--json --session-files` includes a structured `sessionFiles` object with
referenced paths, tools, uses, line numbers, counts, and truncation state.
`--json --session-audit` includes a structured `sessionAudit` object with
session readiness, blockers, completion status, verification groups, pending
plan items, failures, command results with duration, referenced files, and active background
processes.
`--json --session-handoff` includes a structured `sessionHandoff` object with
the same readiness audit plus bounded summary, readiness, plan, verification,
failure, file, and command sections with duration for recovery workflows.
One-shot coding commands exit with a nonzero status when `completionReady` is
false, even if the agent run itself returned `success: true`.
JSON error results use `kind: "error"` with `status: "failed"`, and interrupted
runs use `kind: "interrupted"` with `status: "interrupted"`. Successful local
and chat JSON results use `status: "completed"`. Local operation and check
commands return a nonzero CLI status when their top-level result is `ok: no`,
when port/HTTP reachability is `reachable: no`, or when a requested HTTP or
process-output match reports `matched: no`. Checkpoint recovery commands also
return nonzero for missing or invalid checkpoint ids, failed create/restore/delete
results, and `checkpoint-status` mismatches. Explicit session inspection commands
return nonzero when the requested session id is missing or invalid, or when a
latest-session inspector such as `--last` has no session to inspect. Batch
read commands such as `--read-files`, `--read-ranges`, and `--around-many`
return nonzero when any requested file or context could not be read. Output,
process-output, and session-output context extraction commands return nonzero
when referenced source contexts cannot be read. Process listing and process
output inspection commands also return nonzero when the inspected process has a
nonzero exit status or was terminated by a signal. Explicit source-analysis
commands for symbols, dependencies, references, definitions, call graphs, and
rename previews return nonzero when requested source paths cannot be analyzed.
Source-edit preview commands return nonzero when the target definition or path
cannot be resolved.
Tree, image metadata, and read-only git inspection commands return nonzero when
the requested path, revision, or repository state cannot be inspected.

Local inspection commands can also run without entering the prompt:

```sh
python -m vibeagent --doctor --cwd ../my-project
python -m vibeagent --review --cwd ../my-project
python -m vibeagent --review --review-max-files 50 --review-max-checks 10 --cwd ../my-project
python -m vibeagent --handoff --cwd ../my-project
python -m vibeagent --handoff --handoff-max-files 50 --handoff-max-checks 10 --handoff-max-status-chars 6000 --handoff-max-plan-chars 6000 --cwd ../my-project
python -m vibeagent --changes --cwd ../my-project
python -m vibeagent --changes --changes-max-files 50 --cwd ../my-project
python -m vibeagent --diff --cwd ../my-project
python -m vibeagent --diff --diff-max-chars 6000 --cwd ../my-project
python -m vibeagent --diff --staged src/app.py --cwd ../my-project
python -m vibeagent --diff-hunks --cwd ../my-project
python -m vibeagent --diff-hunks --diff-hunks-max-hunks 20 --diff-hunks-max-lines 40 --cwd ../my-project
python -m vibeagent --diff-hunks --staged src/app.py --cwd ../my-project
python -m vibeagent --diff-contexts --staged src/app.py --cwd ../my-project
python -m vibeagent --diff-contexts src/app.py --diff-context-lines 2 --diff-contexts-max-hunks 20 --diff-contexts-max-bytes 12000 --cwd ../my-project
python -m vibeagent --init CLAUDE.md --cwd ../my-project
python -m vibeagent --init-only --cwd ../my-project
python -m vibeagent -p --init "Install dependencies, then inspect the project" --cwd ../my-project
python -m vibeagent -p --maintenance "Refresh generated dependencies" --cwd ../my-project
python -m vibeagent --hooks --cwd ../my-project
python -m vibeagent --model
python -m vibeagent --config --cwd ../my-project
python -m vibeagent --tools
python -m vibeagent -p --tools "Read,Bash,Edit" "Inspect and repair the project"
python -m vibeagent --tool read_file
python -m vibeagent --tool-search verification
python -m vibeagent --tool-search verification --tool-search-category session --tool-search-approval no --tool-search-max 5
python -m vibeagent --permissions --approval deny
python -m vibeagent --checks --cwd ../my-project
python -m vibeagent --checks --checks-max 10 --cwd ../my-project
python -m vibeagent --commands --commands-max-commands 50 --commands-max-files 30 --cwd ../my-project
python -m vibeagent --related-tests src/app.py --related-tests-max-paths 100 --related-tests-max-candidates 200 --cwd ../my-project
python -m vibeagent --focused-tests src/app.py --focused-tests-max-paths 100 --focused-tests-max-candidates 200 --focused-tests-max-commands 50 --cwd ../my-project
python -m vibeagent --check-focused-tests src/app.py --focused-tests-max-commands 10 --cwd ../my-project
python -m vibeagent --run-focused-tests src/app.py --focused-tests-max-commands 10 --run-timeout-ms 120000 --cwd ../my-project
python -m vibeagent --manifests --manifests-max-files 30 --manifests-max-items 500 --cwd ../my-project
python -m vibeagent --command-check "npm test" --command-cwd packages/app --cwd ../my-project
python -m vibeagent --command "npm test" --command-cwd packages/app --cwd ../my-project
python -m vibeagent --run-command "npm test" --run-cwd packages/app --run-timeout-ms 120000 --cwd ../my-project
python -m vibeagent --run "npm test" --run-cwd packages/app --run-timeout-ms 120000 --cwd ../my-project
python -m vibeagent --run-command "npm test" --run-output-contexts --run-output-context-lines 2 --cwd ../my-project
python -m vibeagent --run-command "npm test" --run-output-diagnostics --run-output-context-lines 2 --run-output-diagnostic-max 10 --cwd ../my-project
python -m vibeagent --check-run-commands "npm test" "npm run build" "git diff --check" --cwd ../my-project
python -m vibeagent --run-commands "npm test" "npm run build" "git diff --check" --run-timeout-ms 120000 --cwd ../my-project
python -m vibeagent --check-start-command "npm run dev" --start-cwd packages/app --cwd ../my-project
python -m vibeagent --start-command "npm run dev" --start-cwd packages/app --cwd ../my-project
python -m vibeagent --start "npm run dev" --start-cwd packages/app --cwd ../my-project
python -m vibeagent --port-check 5173 --port-host 127.0.0.1 --port-timeout-ms 2000 --cwd ../my-project
python -m vibeagent --http-check http://127.0.0.1:5173 --http-contains "ready" --http-timeout-ms 2000 --cwd ../my-project
python -m vibeagent --http-fetch http://127.0.0.1:5173 --http-max-body-chars 4000 --cwd ../my-project
python -m vibeagent --overview --overview-max-files 100 --overview-max-commands 30 --overview-max-checks 20 --cwd ../my-project
python -m vibeagent --repo-map src --repo-map-max-depth 3 --repo-map-max-files 80 --repo-map-max-symbols 120 --cwd ../my-project
python -m vibeagent --search "class Agent" --search-path vibeagent --search-max-matches 20 --search-ignore-case --cwd ../my-project
python -m vibeagent --search-contexts "class Agent" --search-path vibeagent --search-context-lines 2 --search-context-max-bytes 12000 --cwd ../my-project
python -m vibeagent --find-files "app" --find-files-path src --find-files-include-dirs --cwd ../my-project
python -m vibeagent --glob "src*" --glob-include-dirs --glob-max-matches 20 --cwd ../my-project
python -m vibeagent --tree src --tree-max-depth 2 --tree-max-entries 80 --cwd ../my-project
python -m vibeagent --symbols src/app.py web/app.ts --symbols-max 120 --cwd ../my-project
python -m vibeagent --file-info src/app.py asset.bin --cwd ../my-project
python -m vibeagent --read vibeagent/cli.py --read-lines 90:130 --read-max-bytes 20000 --cwd ../my-project
python -m vibeagent --read vibeagent/cli.py --read-line-numbers --read-max-bytes 20000 --cwd ../my-project
python -m vibeagent --around src/app.py 42 --around-lines 8 --around-max-bytes 20000 --cwd ../my-project
python -m vibeagent --around-many src/app.py:42:8 tests/test_app.py:17:5 --around-many-max-bytes 20000 --cwd ../my-project
python -m vibeagent --output-contexts "src/app.py:42:8 tests/test_app.py:17" --output-context-lines 3 --output-context-max 10 --output-context-max-bytes 20000 --cwd ../my-project
python -m vibeagent --output-diagnostics "ERROR src/app.py:42:8 failed" --output-diagnostic-lines 2 --output-diagnostic-max 10 --output-diagnostic-context-max 5 --output-diagnostic-context-max-bytes 20000 --cwd ../my-project
python -m vibeagent --python-traceback "ValueError: bad" --output-diagnostic-lines 2 --output-diagnostic-max 10 --output-diagnostic-context-max 5 --output-diagnostic-context-max-bytes 20000 --cwd ../my-project
python -m vibeagent --session-output-contexts --session-output-command-max 10 --session-output-max-chars 12000 --session-output-context-lines 3 --session-output-context-max 10 --session-output-context-max-bytes 20000 --cwd ../my-project
python -m vibeagent --session-output-diagnostics --session-output-command-max 10 --session-output-max-chars 12000 --session-output-context-lines 3 --session-output-context-max 10 --session-output-context-max-bytes 20000 --session-output-diagnostic-max 25 --cwd ../my-project
python -m vibeagent --tail logs/app.log --tail-lines 80 --tail-max-bytes 20000 --cwd ../my-project
python -m vibeagent --todos src --todos-max-items 50 --todos-max-files 500 --cwd ../my-project
python -m vibeagent --read-files src/app.py tests/test_app.py --read-files-max-bytes 20000 --cwd ../my-project
python -m vibeagent --read-files src/app.py tests/test_app.py --read-files-line-numbers --read-files-max-bytes 20000 --cwd ../my-project
python -m vibeagent --read-ranges src/app.py:10:40 tests/test_app.py:1:80 --read-ranges-max-bytes 20000 --cwd ../my-project
python -m vibeagent --python-check src --cwd ../my-project
python -m vibeagent --python-deps src --cwd ../my-project
python -m vibeagent --python-defs Runner.run --python-path src --python-max-matches 10 --python-def-max-lines 80 --cwd ../my-project
python -m vibeagent --python-refs run_agent --python-path src --python-max-matches 50 --cwd ../my-project
python -m vibeagent --python-ref-contexts run_agent --python-path src --python-max-matches 20 --python-context-lines 2 --python-context-max-bytes 12000 --cwd ../my-project
python -m vibeagent --python-calls helper --python-path src --python-max-matches 50 --cwd ../my-project
python -m vibeagent --python-call-graph src --cwd ../my-project
python -m vibeagent --python-rename-preview run_agent execute_agent --python-path src --cwd ../my-project
python -m vibeagent --python-rename run_agent execute_agent --python-path src --cwd ../my-project
python -m vibeagent --check-replace-python-def Runner.run "    def run(self):\n        return 2\n" --python-path src --cwd ../my-project
python -m vibeagent --replace-python-def Runner.run "    def run(self):\n        return 2\n" --python-path src --cwd ../my-project
python -m vibeagent --config-check . --cwd ../my-project
python -m vibeagent --check-json-set package.json /scripts/test '"npm test"' --json-create-missing --cwd ../my-project
python -m vibeagent --json-set package.json /private true --cwd ../my-project
python -m vibeagent --check-json-remove package.json /scripts/dev --cwd ../my-project
python -m vibeagent --json-remove package.json /keywords/0 --cwd ../my-project
python -m vibeagent --check-json-patch package.json '[{"op":"replace","path":"/private","value":true}]' --cwd ../my-project
python -m vibeagent --json-patch package.json '[{"op":"remove","path":"/keywords/0"}]' --cwd ../my-project
python -m vibeagent --check-replace-lines src/app.py 12 14 "return True\n" --cwd ../my-project
python -m vibeagent --replace-lines src/app.py 12 14 "return True\n" --cwd ../my-project
python -m vibeagent --check-insert-lines src/app.py 20 "print('ready')\n" --cwd ../my-project
python -m vibeagent --insert-lines src/app.py 20 "print('ready')\n" --cwd ../my-project
python -m vibeagent --check-append README.md "\nDone\n" --cwd ../my-project
python -m vibeagent --append README.md "\nDone\n" --cwd ../my-project
python -m vibeagent --check-write notes.md "hello\n" --cwd ../my-project
python -m vibeagent --write notes.md "hello\n" --cwd ../my-project
python -m vibeagent --check-write-files notes.md "hello\n" README.tmp "draft\n" --cwd ../my-project
python -m vibeagent --write-files notes.md "hello\n" README.tmp "draft\n" --cwd ../my-project
python -m vibeagent --check-edit src/app.py old new --cwd ../my-project
python -m vibeagent --edit src/app.py old new --cwd ../my-project
python -m vibeagent --check-multi-edit src/app.py old new print log --cwd ../my-project
python -m vibeagent --multi-edit src/app.py old new print log --cwd ../my-project
python -m vibeagent --check-delete obsolete.py --cwd ../my-project
python -m vibeagent --delete obsolete.py --cwd ../my-project
python -m vibeagent --check-delete-files obsolete.py old.txt --cwd ../my-project
python -m vibeagent --delete-files obsolete.py old.txt --cwd ../my-project
python -m vibeagent --check-move old.py pkg/new.py --cwd ../my-project
python -m vibeagent --move old.py pkg/new.py --cwd ../my-project
python -m vibeagent --check-move-files old.py pkg/new.py other.py pkg/other.py --cwd ../my-project
python -m vibeagent --move-files old.py pkg/new.py other.py pkg/other.py --cwd ../my-project
python -m vibeagent --check-copy template.py pkg/template_copy.py --cwd ../my-project
python -m vibeagent --copy template.py pkg/template_copy.py --cwd ../my-project
python -m vibeagent --check-copy-files template.py pkg/template_copy.py config.py pkg/config_copy.py --cwd ../my-project
python -m vibeagent --copy-files template.py pkg/template_copy.py config.py pkg/config_copy.py --cwd ../my-project
python -m vibeagent --check-move-dir old_pkg pkg/new_pkg --cwd ../my-project
python -m vibeagent --move-dir old_pkg pkg/new_pkg --cwd ../my-project
python -m vibeagent --check-move-dirs old_a pkg/a old_b pkg/b --cwd ../my-project
python -m vibeagent --move-dirs old_a pkg/a old_b pkg/b --cwd ../my-project
python -m vibeagent --check-copy-dir template_pkg pkg/template_copy --cwd ../my-project
python -m vibeagent --copy-dir template_pkg pkg/template_copy --cwd ../my-project
python -m vibeagent --check-copy-dirs template_a pkg/template_a_copy template_b pkg/template_b_copy --cwd ../my-project
python -m vibeagent --copy-dirs template_a pkg/template_a_copy template_b pkg/template_b_copy --cwd ../my-project
python -m vibeagent --check-mkdir pkg/generated --cwd ../my-project
python -m vibeagent --mkdir pkg/generated --cwd ../my-project
python -m vibeagent --check-mkdirs pkg/generated assets/icons --cwd ../my-project
python -m vibeagent --mkdirs pkg/generated assets/icons --cwd ../my-project
python -m vibeagent --check-rmdir pkg/generated --cwd ../my-project
python -m vibeagent --rmdir pkg/generated --cwd ../my-project
python -m vibeagent --check-rmdirs pkg/generated assets/icons --cwd ../my-project
python -m vibeagent --rmdirs pkg/generated assets/icons --cwd ../my-project
python -m vibeagent --check-executable scripts/tool.sh true --cwd ../my-project
python -m vibeagent --set-executable scripts/tool.sh false --cwd ../my-project
python -m vibeagent --check-patch src/app.py "@@ -1 +1 @@\n-old\n+new\n" --cwd ../my-project
printf '@@ -1 +1 @@\n-old\n+new\n' | python -m vibeagent --patch src/app.py - --cwd ../my-project
python -m vibeagent --check-patches "--- a/src/app.py\n+++ b/src/app.py\n@@ -1 +1 @@\n-old\n+new\n" --cwd ../my-project
printf '%s\n' "--- a/src/app.py" "+++ b/src/app.py" "@@ -1 +1 @@" "-old" "+new" | python -m vibeagent --patches - --cwd ../my-project
python -m vibeagent --check-regex-replace src/app.py "old_(\\w+)" "new_\\1" --regex-count 5 --cwd ../my-project
python -m vibeagent --regex-replace src/app.py "TODO" "DONE" --regex-ignore-case --cwd ../my-project
python -m vibeagent --code-deps web --cwd ../my-project
python -m vibeagent --code-refs runAgent --code-path web --code-max-matches 50 --cwd ../my-project
python -m vibeagent --code-ref-contexts runAgent --code-path web --code-max-matches 20 --code-context-lines 2 --code-context-max-bytes 12000 --cwd ../my-project
python -m vibeagent --code-defs runAgent --code-path web --code-max-matches 20 --code-def-max-lines 80 --cwd ../my-project
python -m vibeagent --code-rename-preview runAgent executeAgent --code-path web --cwd ../my-project
python -m vibeagent --code-rename runAgent executeAgent --code-path web --cwd ../my-project
python -m vibeagent --git-status --cwd ../my-project
python -m vibeagent --conflicts src --cwd ../my-project
python -m vibeagent --git-info --cwd ../my-project
python -m vibeagent --branches --cwd ../my-project
python -m vibeagent --log src/app.py --log-count 5 --cwd ../my-project
python -m vibeagent --show HEAD --show-path src/app.py --cwd ../my-project
python -m vibeagent --blame src/app.py --blame-lines 20:40 --cwd ../my-project
python -m vibeagent --stashes --stash-count 5 --cwd ../my-project
python -m vibeagent --check-git-fetch origin --cwd ../my-project
python -m vibeagent --git-fetch origin --cwd ../my-project
python -m vibeagent --check-git-pull --cwd ../my-project
python -m vibeagent --git-pull --cwd ../my-project
python -m vibeagent --check-git-push --cwd ../my-project
python -m vibeagent --git-push --cwd ../my-project
python -m vibeagent --check-git-stash "save local work" --stash-include-untracked --cwd ../my-project
python -m vibeagent --git-stash "save local work" --stash-include-untracked --cwd ../my-project
python -m vibeagent --check-git-stash-apply "stash@{0}" --cwd ../my-project
python -m vibeagent --git-stash-apply "stash@{0}" --cwd ../my-project
python -m vibeagent --check-git-stash-drop "stash@{0}" --cwd ../my-project
python -m vibeagent --git-stash-drop "stash@{0}" --cwd ../my-project
python -m vibeagent --check-git-stage src/app.py tests/test_app.py --cwd ../my-project
python -m vibeagent --git-stage src/app.py tests/test_app.py --cwd ../my-project
python -m vibeagent --check-git-unstage src/app.py tests/test_app.py --cwd ../my-project
python -m vibeagent --git-unstage src/app.py tests/test_app.py --cwd ../my-project
python -m vibeagent --check-git-commit "update app flow" --cwd ../my-project
python -m vibeagent --git-commit "update app flow" --cwd ../my-project
python -m vibeagent --check-git-restore src/app.py --cwd ../my-project
python -m vibeagent --git-restore src/app.py --cwd ../my-project
python -m vibeagent --check-git-switch feature/demo --git-switch-create --cwd ../my-project
python -m vibeagent --git-switch feature/demo --cwd ../my-project
python -m vibeagent --env --cwd ../my-project
python -m vibeagent --processes --cwd ../my-project
python -m vibeagent --process-output <process-id> --process-max-chars 4000 --cwd ../my-project
python -m vibeagent --process-output-contexts <process-id> --process-output-context-lines 2 --process-output-context-max 5 --process-output-context-max-bytes 1000 --cwd ../my-project
python -m vibeagent --process-output-diagnostics <process-id> --process-output-context-lines 2 --process-output-diagnostic-max 10 --process-output-context-max 5 --process-output-context-max-bytes 1000 --cwd ../my-project
python -m vibeagent --wait-process <process-id> --wait-timeout-ms 5000 --wait-stdout "ready" --cwd ../my-project
python -m vibeagent --check-write-process <process-id> --write-stdin "hello\n" --cwd ../my-project
python -m vibeagent --write-process <process-id> --write-stdin "hello\n" --cwd ../my-project
python -m vibeagent --write-process <process-id> --write-stdin-file scripts/repl-input.txt --cwd ../my-project
python -m vibeagent --check-stop-process <process-id> --cwd ../my-project
python -m vibeagent --stop-process <process-id> --cwd ../my-project
python -m vibeagent --check-stop-all-processes --cwd ../my-project
python -m vibeagent --stop-all-processes --cwd ../my-project
python -m vibeagent --sessions --cwd ../my-project
python -m vibeagent --session <run-id> --cwd ../my-project
python -m vibeagent --session-inspect <run-id> --cwd ../my-project
python -m vibeagent --session-tasks <run-id> --cwd ../my-project
python -m vibeagent --plan <run-id> --cwd ../my-project
python -m vibeagent --transcript <run-id> --session-transcript-event-max 80 --session-max-text 500 --cwd ../my-project
python -m vibeagent --session-search "AssertionError" --session-search-run <run-id> --session-search-match-max 20 --session-search-case-sensitive --session-max-text 500 --cwd ../my-project
python -m vibeagent --session-commands <run-id> --session-max-commands 10 --session-max-output-chars 2000 --cwd ../my-project
python -m vibeagent --session-files <run-id> --session-max-files 50 --cwd ../my-project
python -m vibeagent --session-failures <run-id> --session-max-failures 20 --session-max-text 500 --cwd ../my-project
python -m vibeagent --session-audit <run-id> --session-max-failures 10 --session-max-files 20 --session-max-commands 10 --session-max-text 300 --cwd ../my-project
python -m vibeagent --session-handoff <run-id> --session-max-failures 20 --session-max-files 50 --session-max-commands 10 --session-max-checks 50 --session-max-output-chars 1000 --session-max-text 500 --cwd ../my-project
python -m vibeagent --checkpoint "before refactor" --cwd ../my-project
python -m vibeagent --checkpoints --cwd ../my-project
python -m vibeagent --checkpoint-show <checkpoint-id> --cwd ../my-project
python -m vibeagent --checkpoint-show latest --cwd ../my-project
python -m vibeagent --checkpoint-diff <checkpoint-id> --cwd ../my-project
python -m vibeagent --checkpoint-status <checkpoint-id> --cwd ../my-project
python -m vibeagent --check-checkpoint-restore <checkpoint-id> --cwd ../my-project
python -m vibeagent --checkpoint-restore <checkpoint-id> --cwd ../my-project
python -m vibeagent --check-checkpoint-delete <checkpoint-id> --cwd ../my-project
python -m vibeagent --checkpoint-delete <checkpoint-id> --cwd ../my-project
python -m vibeagent --check-checkpoint-prune 10 --cwd ../my-project
python -m vibeagent --checkpoint-prune 10 --cwd ../my-project
python -m vibeagent --session-rewind-points <run-id> --cwd ../my-project
python -m vibeagent --check-session-rewind <run-id> <checkpoint-id> both --cwd ../my-project
python -m vibeagent --session-rewind <run-id> <checkpoint-id> both --cwd ../my-project
python -m vibeagent --usage --cwd ../my-project
python -m vibeagent --cost --cwd ../my-project
python -m vibeagent --save-config --cwd ../my-project --provider deepseek --model-name deepseek-reasoner --max-iterations 12 --max-output-tokens 8192 --model-retries 2 --model-retry-delay-ms 500 --model-timeout-ms 120000
python -m vibeagent --json --doctor --cwd ../my-project
```

Use `/help` to list local commands, `/model` to inspect the active interactive
provider and model, `/model <model-name>` to switch the current interactive
process after successfully constructing a replacement client, and `/model default`
to restore the configured model without changing project settings or conversation
history. `/effort` reports the current session reasoning level;
`/effort low|medium|high|xhigh|max` applies an Anthropic effort override, and
`/effort auto` returns to the provider/model default. Effort changes are
atomic, survive later `/model` switches, reach coding, chat, BTW, recap,
workflow, and subagent calls through the shared client, and fail without
replacing the client when the provider does not support effort. Use `/config`
to inspect resolved provider,
execution, project config, and cost-rate settings, `/status` to inspect local mode, approval,
and resume state, `/btw <question>` to ask one tool-free side question using the
current mode's bounded conversation without adding the question or answer to
either conversation history or the persisted coding session, and `/recap` to
generate one concise, tool-free status line from the current mode's conversation.
After three completed turns, VibeAgent also prints a recap when that mode has
been idle for three minutes. Automatic recaps use a separate provider client,
are not persisted, and can be disabled with
`VIBEAGENT_DISABLE_SESSION_RECAP=1`,
`/agents [--max-agents N]` to inspect project agent profile
metadata, `/skills [--max-skills N]` to inspect project skill metadata,
`/tools` to inspect the model tool catalog, `/tool <name>` to
inspect one tool's description and input schema,
`/tool-search [--max N] [--category CATEGORY] [--approval any|yes|no] <query>`
to search tools by name, description, category, approval state, or input fields, `/permissions` to inspect
approval-gated tools and command hard blocks, `/sandbox` to inspect OS command isolation,
`/checks [--max-checks N]` to inspect suggested
test, build, and lint commands without running them,
`/check-suggested-checks [max|--max-checks N]` to preflight those suggested commands,
`/run-suggested-checks [opts] [max|--max-checks N]` to run available suggested commands with optional output diagnostics,
`/commands [--max-commands N] [--max-files N]` to inspect
project-defined commands from manifests, `/related-tests [--max-paths N] [--max-candidates N] -- [path...]` to suggest
likely focused test files for explicit paths or current git changes,
`/focused-tests [--max-paths N] [--max-candidates N] [--max-commands N] -- [path...]` to suggest likely focused test commands for those
paths or current git changes, `/check-focused-tests [--max-paths N] [--max-candidates N] [--max-commands N] -- [path...]` to preflight
those focused commands, `/run-focused-tests [opts] [--max-paths N] [--max-candidates N] [--max-commands N] -- [path...]` to run available focused
test commands with optional output diagnostics, `/manifests [--max-files N] [--max-items N]` to inspect package and
pyproject metadata, `/instructions [--max-files N] [--max-bytes N]` to inspect AGENTS.md and CLAUDE.md sources,
`/todos [--max-items N] [--max-files N] -- [path]` to inspect TODO, FIXME, HACK, XXX, and BUG markers,
`/command [--cwd PATH] -- <cmd>` to preflight
one shell command without running it, `/run [opts] -- <cmd>` to run one finite shell command
with optional output diagnostics and bounded contexts, `! <cmd>` to run a shell command directly from the
interactive prompt, `/check-run-commands [--cwd PATH] -- <cmd> ;; <cmd>` to preview a short ordered
command sequence without running it, `/run-commands [opts] -- <cmd> ;; <cmd>` to run a short
ordered command sequence with optional output diagnostics (`/check-run-seq` and `/run-seq` remain aliases), `/check-start [--cwd PATH] -- <cmd>` to preview starting one long-running
shell command, `/start [--cwd PATH] -- <cmd>` to start one long-running shell command in
the current interactive session, `/port <port> [host] [timeout-ms] [--host HOST] [--timeout-ms N]` to check
whether a local TCP port is reachable, `/http <url> [contains] [--timeout-ms N] [--max-body-chars N] [--contains TEXT] [--regex]` to check HTTP(S)
status and optional response text, `/http-fetch <url> [--timeout-ms N] [--max-body-chars N]` to fetch bounded HTTP
response metadata and body text, `/overview [--max-files N] [--max-commands N] [--max-checks N]` to inspect a compact project
orientation bundle, `/repo-map [path] [--max-depth N] [--max-files N] [--max-symbols N]` to inspect a bounded repository tree and
source symbol map, `/search [--path PATH] [--max-matches N] [--regex] [--ignore-case] [--context-lines N] -- <query>` to search project text with gitignore and
safety filtering, `/search-contexts [--path PATH] [--max-matches N] [--regex] [--ignore-case] [--context-lines N] [--max-bytes N] -- <query>` to search with structured surrounding
source snippets, `/find-files [--path PATH] [--max-matches N] [--regex] [--case-sensitive] [--include-dirs] -- <query>` to find project files by path fragment,
`/glob [--max-matches N] [--include-dirs] -- <pattern>` to find project files or directories by path pattern,
`/tree [path] [--max-depth N] [--max-entries N]` to inspect a bounded project directory tree,
`/symbols [--max-symbols N] -- <path...>` to inspect imports and symbol outlines for source files,
`/file-info <path...>` to inspect file, directory, size, binary, and line metadata,
`/image-info <path...>` to inspect image format, byte size, and dimensions,
`/read [--max-bytes N] -- <path> [start[:end]]` to read one project file or inclusive line range,
`/around [--max-bytes N] -- <path> <line> [context-lines]` to read one line with surrounding context,
`/around-many [--max-bytes N] -- <path:line[:context-lines]...>` to read several line-centered contexts,
`/output-contexts [--context-lines N] [--max-contexts N] [--max-bytes N] -- <text>` to extract file:line references from command output and read contexts,
`/output-diagnostics [--context-lines N] [--max-diagnostics N] [--max-contexts N] [--max-bytes N] -- <text>` to summarize output errors, warnings, failures, and referenced contexts,
`/python-traceback [--context-lines N] [--max-diagnostics N] [--max-contexts N] [--max-bytes N] -- <text>` to summarize Python traceback or pytest exception output,
`/session-output-contexts [run-id] [--max-commands N] [--max-output-chars N] [--context-lines N] [--max-contexts N] [--max-bytes N]` to extract file:line contexts from session command output,
`/session-output-diagnostics [run-id] [--max-commands N] [--max-output-chars N] [--context-lines N] [--max-diagnostics N] [--max-contexts N] [--max-bytes N]` to summarize errors, warnings, failures, and referenced contexts from session command output,
`/tail [--max-bytes N] -- <path> [lines]` to read the last lines of one project file,
`/read-files [--max-bytes N] [--line-numbers] -- <path...>` to read multiple project files in one command,
`/read-ranges [--max-bytes N] -- <path:start[:end]...>` to read multiple focused line ranges,
`/python-check [path]` to check Python syntax,
`/python-deps [path]` to inspect Python imports and dependencies,
`/python-defs [--path PATH] [--max-matches N] [--max-lines N] -- <symbol> [path]` to find Python class/function definitions,
`/python-refs [--path PATH] [--max-matches N] -- <symbol> [path]` to find Python definitions, imports, and references,
`/python-ref-contexts [--path PATH] [--max-matches N] [--context-lines N] [--max-bytes N] -- <symbol> [path]` to find Python references with surrounding source context,
`/python-calls [--path PATH] [--max-matches N] -- <symbol> [path]` to find Python call sites for a symbol,
`/python-call-graph [path]` to inspect Python caller-to-callee edges,
`/python-rename-preview <symbol> <new_name> [path]` to preview a Python symbol rename,
`/python-rename <symbol> <new_name> [path]` to rename a Python symbol,
`/check-replace-python-def <symbol> <content> [path]` to preview replacing one Python definition,
`/replace-python-def <symbol> <content> [path]` to replace one Python definition,
`/config-check [path]` to check JSON/YAML/TOML config syntax,
`/check-json-set [--create-missing] <path> <pointer> <json-value>` to preview a JSON value update,
`/json-set [--create-missing] <path> <pointer> <json-value>` to update one JSON value,
`/check-json-remove <path> <pointer>` to preview a JSON value removal,
`/json-remove <path> <pointer>` to remove one JSON value,
`/check-json-patch <path> <json-ops-array>` to preview JSON Patch operations,
`/json-patch <path> <json-ops-array>` to apply JSON Patch operations,
`/check-replace-lines <path> <start> <end> <text>` to preview a line-range replacement,
`/replace-lines <path> <start> <end> <text>` to replace a line range,
`/check-insert-lines <path> <line> <text>` to preview inserting text before a line,
`/insert-lines <path> <line> <text>` to insert text before a line,
`/check-append <path> <text>` to preview appending text to a file,
`/append <path> <text>` to append text to a file,
`/check-write <path> <text>` to preview writing one file,
`/write <path> <text>` to write one file,
`/check-write-files <path> <text>...` to preview writing multiple files,
`/write-files <path> <text>...` to write multiple files,
`/check-edit <path> <old> <new>` to preview replacing exact text in one file,
`/edit <path> <old> <new>` to replace exact text in one file,
`/check-multi-edit <path> <old> <new>...` to preview multiple exact replacements in one file,
`/multi-edit <path> <old> <new>...` to apply multiple exact replacements in one file,
`/check-delete <path>` to preview deleting one file,
`/delete <path>` to delete one file,
`/check-delete-files <path...>` to preview deleting multiple files,
`/delete-files <path...>` to delete multiple files,
`/check-move <source> <destination>` to preview moving one file,
`/move <source> <destination>` to move one file,
`/check-move-files <source> <destination>...` to preview moving multiple files,
`/move-files <source> <destination>...` to move multiple files,
`/check-copy <source> <destination>` to preview copying one file,
`/copy <source> <destination>` to copy one file,
`/check-copy-files <source> <destination>...` to preview copying multiple files,
`/copy-files <source> <destination>...` to copy multiple files,
`/check-move-dir <source> <destination>` to preview moving one directory,
`/move-dir <source> <destination>` to move one directory,
`/check-move-dirs <source> <destination>...` to preview moving multiple directories,
`/move-dirs <source> <destination>...` to move multiple directories,
`/check-copy-dir <source> <destination>` to preview copying one directory,
`/copy-dir <source> <destination>` to copy one directory,
`/check-copy-dirs <source> <destination>...` to preview copying multiple directories,
`/copy-dirs <source> <destination>...` to copy multiple directories,
`/check-mkdir <path>` to preview creating one directory,
`/mkdir <path>` to create one directory,
`/check-mkdirs <path...>` to preview creating multiple directories,
`/mkdirs <path...>` to create multiple directories,
`/check-rmdir <path>` to preview deleting one empty directory,
`/rmdir <path>` to delete one empty directory,
`/check-rmdirs <path...>` to preview deleting multiple empty directories,
`/rmdirs <path...>` to delete multiple empty directories,
`/check-executable <path> [true|false]` to preview changing one file's executable bit,
`/set-executable <path> [true|false]` to change one file's executable bit,
`/check-patch <path> <patch|->` to preview applying a unified diff hunk to one file,
`/patch <path> <patch|->` to apply a unified diff hunk to one file,
`/check-patches <patch|->` to preview applying a unified diff across files,
`/patches <patch|->` to apply a unified diff across files,
`/check-regex-replace [--ignore-case] [--multiline] [--count N] [--max-replacements N] <path> <pattern> <replacement>` to preview a regex replacement,
`/regex-replace [--ignore-case] [--multiline] [--count N] [--max-replacements N] <path> <pattern> <replacement>` to apply a regex replacement,
`/code-deps [path]` to inspect non-Python source imports and dependencies,
`/code-refs [--path PATH] [--max-matches N] -- <symbol> [path]` to find non-Python source references,
`/code-ref-contexts [--path PATH] [--max-matches N] [--context-lines N] [--max-bytes N] -- <symbol> [path]` to find non-Python source references with surrounding source context,
`/code-defs [--path PATH] [--max-matches N] [--max-lines N] -- <symbol> [path]` to find non-Python source definitions,
`/code-rename-preview <symbol> <new_name> [path]` to preview a non-Python source rename,
`/code-rename <symbol> <new_name> [path]` to rename a non-Python source symbol or literal,
`/git-status` to inspect raw short git status,
`/conflicts [path]` to scan for unmerged git files and conflict marker lines,
`/git-info` to inspect branch, HEAD, upstream, remotes, ahead/behind, and status,
`/branches` to inspect local git branches and the current branch,
`/log [path] [count]` to inspect recent commits, optionally scoped to one path,
`/show [rev] [path]` to inspect one commit with stat and patch output,
`/blame <path> [start[:end]]` to inspect git blame for a file or line range,
`/stashes [count]` to inspect local git stash entries,
`/check-fetch [remote]` to preview selecting a git remote to fetch,
`/fetch [remote]` to run `git fetch --prune` for a configured remote,
`/check-pull` to preview fast-forward pulling the current upstream,
`/pull` to fast-forward pull the current upstream,
`/check-push` to preview pushing the current branch to upstream,
`/push` to push the current branch to upstream,
`/check-stash [--include-untracked] [message]` to preview saving non-runtime changes to git stash,
`/stash [--include-untracked] [message]` to save non-runtime changes to git stash,
`/check-stash-apply <stash@{N}>` to preview applying a stash to a clean worktree,
`/stash-apply <stash@{N}>` to apply a stash to a clean worktree,
`/check-stash-drop <stash@{N}>` to preview deleting a stash entry,
`/stash-drop <stash@{N}>` to delete a stash entry,
`/check-stage <path...>` to preview staging explicit project paths,
`/stage <path...>` to stage explicit project paths,
`/check-unstage <path...>` to preview unstaging explicit project paths,
`/unstage <path...>` to unstage explicit project paths,
`/check-commit <message>` to preview committing currently staged changes,
`/commit <message>` to commit currently staged changes,
`/check-restore <path...>` to preview discarding unstaged tracked-file changes,
`/restore <path...>` to discard unstaged tracked-file changes,
`/check-switch [--create] <branch>` to preview switching or creating a local branch,
`/switch [--create] <branch>` to switch or create a local branch,
`/env` to inspect local OS, runtime, and tool availability,
`/background-agents` to list project-local background coding sessions,
`/background-agent-log <id> [max-chars]` to read bounded output from one session,
`/stop-background-agent <id>` to stop one running background coding session,
`--attach-background-agent <id>` from the shell to take over one session in the full interactive CLI,
`/send-background-agent <id> <message>` to queue a same-session follow-up and respawn the worker if needed,
`/respawn-background-agent <id>` to restart a running or stopped worker from its recorded session,
`/remove-background-agent <id>` to remove one non-running supervisor entry and its logs while preserving the resumable session,
`/processes` to inspect VibeAgent-started background processes,
`/process <id> [chars]` to inspect captured stdout and stderr for one background process,
`/process-output-contexts <id> [chars] [--max-chars N] [--context-lines N] [--max-contexts N] [--max-bytes N]` to extract source contexts for file:line references in background process output,
`/process-output-diagnostics <id> [chars] [--max-chars N] [--context-lines N] [--max-diagnostics N] [--max-contexts N] [--max-bytes N]` to summarize background process errors, warnings, failures, and referenced contexts,
`/wait-process <id> [timeout-ms] [chars] [--timeout-ms N] [--max-chars N] [--stdout TEXT] [--stderr TEXT] [--regex]` to wait for a background process or output match,
`/check-write-process <id> <text> [--stdin-file PATH]` to preview writing stdin text or a project file to one running background process; quote text with spaces,
`/write-process <id> <text> [--stdin-file PATH]` to write stdin text or a project file to one running background process; quote text with spaces,
`/check-stop-process <id>` to preview stopping one VibeAgent-started background process,
`/stop-process <id>` to stop one VibeAgent-started background process,
`/check-stop-processes` or `/check-stop-all-processes` to preview stopping all VibeAgent-started background processes,
`/stop-processes` or `/stop-all-processes` to stop all VibeAgent-started background processes,
`/context` to inspect the prompt context sources for coding
tasks, `/init [AGENTS.md|CLAUDE.md]` to create a starter project instruction
file, `/doctor` to inspect local
configuration, workspace diagnostics, and command hard-block self-checks, `/review [--max-files N] [--max-checks N]` to review current git changes,
syntax checks, suggested verification commands, and focused tests inferred from changed files, `/handoff [--max-files N] [--max-checks N] [--max-status-chars N] [--max-plan-chars N]` to inspect a final
handoff bundle with review status, changed files, suggested checks, focused tests, git status,
and the latest plan, `/changes [--max-files N]` to inspect a structured changed-file summary,
`/diff [--staged] [--max-chars N] [path]` to inspect the current patch,
`/diff-hunks [--staged] [--max-hunks N] [--max-lines N] [path]` to inspect structured git diff hunks,
`/diff-contexts [--staged] [--context-lines N] [--max-hunks N] [--max-bytes N] [path]` to inspect source context around git diff hunks,
`/approval [ask|allow|auto|deny|dontAsk|plan]` to control
the session approval policy, `/system-prompt [text|off]` and
`/append-system-prompt [text|off]` to set or clear session-only system-prompt
instructions for chat and coding turns, `/add-dir [path|remove path|clear]` to
inspect or update session working directories, `/resume [run-id|off]` to carry a previous coding
session handoff into the next task or clear it, `/compact [run-id]` to explicitly
compact the newest or selected session into context, `/branch [name]` to fork
the active coding context into an independent named session, `/rename [name]` to
name the active coding session (or derive a name from its first task), `/export [filename]`
to print or atomically write its safe plain-text transcript, `/plan [run-id]` to inspect
the latest recorded task plan, `/transcript [run-id]` to inspect a safe session
event timeline without dumping full tool payloads, `/checkpoint [label]` to save
current git status, staged and unstaged patch files, and ordinary untracked file
contents under `.vibeagent/checkpoints/`,
`/checkpoints` to list saved checkpoints, `/rewind` to list checkpoints tied to
the active coding session, and `/rewind <id|latest> [both|code|conversation]`
(`/undo` is an alias) to restore code, create a new conversation Session from
the recorded event boundary, or do both. Conversation rewind preserves the
original Session transcript as audit history. It does not reverse command side
effects outside the captured worktree or restore external services and processes.
`/checkpoint-show <id>` inspects one
checkpoint, `/checkpoint-diff <id>` to show the saved staged and unstaged patch
contents, `/checkpoint-status <id>` to compare the current worktree with a saved
checkpoint, `/check-checkpoint-restore <id>` to preview restoring tracked staged
and unstaged changes plus saved untracked files from a checkpoint,
`/checkpoint-restore <id>` to restore those checkpoint contents when the
checkpoint and current worktree are compatible. Checkpoint commands that accept
an id also accept `latest` for the newest saved checkpoint,
`/check-checkpoint-delete <id>` to preview deleting one saved checkpoint snapshot,
`/checkpoint-delete <id>` to delete one saved checkpoint snapshot,
`/check-checkpoint-prune <keep-last>` to preview deleting older checkpoints,
`/checkpoint-prune <keep-last>` to delete older checkpoints while keeping the
newest entries, `/goal <condition>` to start an evaluator-controlled autonomous
coding loop, `/goal` to inspect its state, `/goal clear` to stop it, and
`/list-agents` (or `/peers`) to list reachable local sessions,
`/peer-inbox` to inspect held inbound messages and `/peer-inbox accept|deny
<sender-id|all>` to decide them, and
`/workflows run <script.js>` to start a resumable multi-agent JavaScript
workflow, `/workflows` to list runs, and `/workflows show|resume|stop <id>` to
inspect or control one run, and
`/plugin install <project-path>` to validate and install a local plugin,
`/plugin list|details|enable|disable|uninstall|validate` to manage it, and
`/plugin marketplace add|list|details|update|remove` to manage local and remote
plugin catalogs and install `plugin@marketplace`, and
`/reload-plugins` to refresh plugin-aware runtimes, and
`/clear` to clear the goal, local chat history, and loaded resume context,
`/usage` to summarize local session events,
iterations, tool calls, approvals, and recorded token usage, `/cost` to estimate
cost from configured per-million-token rates, and `/exit` to leave the interactive prompt.
Use `/chat` to switch to daily conversation mode and `/code` to switch back to coding
mode. You can also send one-off messages with `/chat <message>` or one-off coding
tasks with `/code <task>`. For generated code, the agent now prefers Python
scripts unless the user asks for another language.

Interactive shell mode is provider-free: `! pytest -q` executes immediately as
an explicit user command without sending the text to the model. It reuses the
same project-contained cwd checks, command hard blocks, sandbox, timeout, output
bounds, and runtime environment as `/run`. The command and redacted output are
recorded in the current session and included in the next coding turn's resume
context; terminal output remains visible verbatim to the user. A fresh shell
command creates a resumable session when no session is active. Runtime and
session event paths must remain regular non-symlink paths before execution.

Coding mode works in the current directory:

```sh
cd my-project
python -m vibeagent
```

For tasks that explicitly need an isolated checkout, the model can call the
Claude-compatible `EnterWorktree` tool after approval. VibeAgent creates a
linked checkout under `.vibeagent/worktrees/<name>/` on a new
`vibeagent/<name>` branch, or switches to an existing registered worktree from
the same repository. Newly created Git worktrees use the same bounded,
symlink-safe `.worktreeinclude` setup as CLI and isolated-subagent worktrees;
setup failures remove the new worktree and branch before the tool returns.
Every subsequent file, command, and Git tool uses that
worktree as its project root while the original session log remains intact.
`ExitWorktree` returns execution to the main checkout but preserves the linked
worktree, branch, commits, and uncommitted changes for explicit review or
integration; it never merges or deletes them automatically. Coding subagents
cannot switch the parent agent's workspace.

VibeAgent may read and search `my-project` directly, including bounded repository maps with source outlines, directory tree inspection, path-fragment file finding, path globbing,
file metadata inspection, Python symbol outlines, generic code outlines for common source languages, Python syntax checks, JSON/TOML config syntax checks, Python dependency inspection, generic source import/include inspection, generic source reference lookup, generic source definition excerpts, lexical non-Python source rename previews, Python definition excerpts, Python call-site lookup, Python call graph inspection, Python reference lookup, AST-guided Python rename previews, bounded full-file reads with truncation metadata, focused single or batched line-range reads for large files, scoped exact or regex search with total/truncation metadata, structured search contexts for matching source snippets, dry-run regex replacement previews, structured JSON value update/removal and JSON Patch previews, and dry-run patch validation. It can create or replace one or several text files, apply lexical non-Python source renames, apply AST-guided Python identifier renames after syntax validation, replace a unique Python class/function definition after syntax validation, replace exact text blocks, apply bounded regex replacements, update or remove one JSON value by JSON Pointer, apply multiple JSON add/replace/remove operations atomically, replace focused line ranges, insert text at a known line, append exact text to an existing file, or apply
single-file or multi-file unified diff hunks to existing files, and can safely
copy, move or delete one or several explicit files, adjust executable bits on individual files, create directories, copy directories, move directories, or delete empty directories. It can also inspect git branch/upstream state, list local branches and stashes, `git status`, merge/rebase conflict state, structured changed-file summaries, pre-final review results with suggested checks, raw and structured `git diff` hunks, source context around diff hunks, bounded untracked text-file previews, line-level `git blame`, fetch and fast-forward pull upstream state with approval, push current-branch commits to upstream with approval, switch or create local branches from a clean worktree with approval, stage or unstage explicit project paths, discard unstaged tracked-file changes with approval, save non-runtime changes to git stash with approval, apply stash entries to a clean worktree with approval, drop explicit stash entries with approval, and create local commits from staged changes with approval
through read-only tools, inspect fixed runtime/tool availability, preflight proposed shell commands, run short ordered verification command batches, inspect project manifests, suggest likely focused test files and runnable focused test commands for changed paths, preflight and run those focused test commands directly, and suggest relevant test/build commands from project
metadata and current changes. Root `AGENTS.md`, `CLAUDE.md`,
`.claude/CLAUDE.md`, `CLAUDE.local.md`, and unscoped `.claude/rules/**/*.md`
files are included in the initial coding prompt. Nested instruction files and
rules with `paths` frontmatter are loaded once per agent context after a
matching file is read, so directory-specific guidance does not leak into
unrelated work. Main-agent and subagent contexts track loaded sources
independently. When either context is compacted, its lazy-load markers are
cleared so the applicable rules are injected again on the next matching read.
Instruction files support Claude-compatible `@path/to/file` imports relative to
the containing file, including recursive imports up to five levels. Imported
sources inherit the entrypoint's scope, are reported with `reason=include` and
their parent file, and fire `InstructionsLoaded` hooks. Imports inside fenced or
inline code are left literal, HTML comments outside code are omitted from the
injected text, and missing, oversized, cyclic, protected, external, or
symlink-escaped imports fail closed without exposing their content. Per-file and
whole-discovery import count and byte limits bound instruction expansion.
Project commands from root or nested `package.json`, `pyproject.toml`,
and `Makefile` files are shown as command hints with their `cwd` and executable availability. Long-running commands can be started as background
processes, inspected through captured stdout/stderr tails across CLI calls, sent exact stdin input while the starting runtime is still attached, checked
through local TCP and HTTP readiness probes, and stopped individually or all at once. In the CLI, edits, patches, writes, file lifecycle changes, and
command starts/runs ask for approval before execution; when a matching read-only
preview was run first, the approval prompt and session event include a short
preview summary without embedding full file content. Session logs are stored
  under `.vibeagent/sessions/<session-id>/events.jsonl`; workspace creation and
  historical session readers refuse symlink `.vibeagent`, `.vibeagent/sessions`,
  session directories, or `events.jsonl` files so runtime logs are not written
  outside the project or read back through symlink roots.
The interactive approval prompt accepts `y/yes` for one action and `a/always`
to remember an approval for the same action type and target until the current
CLI session ends. Remembered approvals are shared with hooks and coding
subagents in that session, are cleared when `/approval` changes policy, and are
recorded with `scope=session` and `remembered=true` in session events. Denials
are never cached, and MCP discovery/calls always require separate approval.
For multi-step coding tasks, the model maintains a session task graph with the
Claude-compatible `TaskCreate`, `TaskGet`, `TaskList`, and `TaskUpdate` tools.
Tasks have stable IDs, incremental status changes, optional owners and metadata,
and acyclic `blocks`/`blockedBy` dependencies. The graph is atomically stored in
`.vibeagent/sessions/<session-id>/tasks.json`, inherited by subsequent
interactive turns and `--resume` runs, and projected into the run result,
session summaries, and completion checks. `todo_write`/`TodoWrite`,
`todo_read`/`TodoRead`, and `update_plan` remain deferred compatibility tools
for the legacy whole-checklist contract.
The provider-free `--session-tasks [RUN_ID]` command reads this graph without
creating a model client. Its `sessionTasks` JSON omits metadata, redacts and
bounds task text, preserves owners and dependency edges, reports status and
blocked counts, and fails nonzero for missing, corrupt, oversized, cyclic, or
symlinked stores.
VibeAgent also supports Claude-compatible session scheduling through
`CronCreate`, `CronList`, and `CronDelete`. A scheduled prompt uses a standard
five-field local-time cron expression and can be one-shot or recurring. The
scheduler supports lists, ranges, and steps, Vixie cron day-of-month/day-of-week
OR semantics, deterministic jitter, 8-character IDs, and at most 50 tasks per
session. It checks between agent iterations and once per second while the
interactive CLI is idle, never interrupts an active model response, and runs a
missed recurring task once rather than replaying every missed interval.
Recurring schedules expire after seven days with one final fire; one-shot tasks
delete themselves after delivery. Unexpired schedules are atomically stored in
`.vibeagent/sessions/<session-id>/scheduled_tasks.json` and inherited on resume.
Scheduled prompts are task direction only and cannot grant tool approval.
Set `VIBEAGENT_DISABLE_CRON=1` or `CLAUDE_CODE_DISABLE_CRON=1` to hide the cron
tools and stop delivery.
Interactive `/batch <instruction>` researches a large repository change, splits
it into 5 to 30 genuinely independent units with non-overlapping path ownership
and acceptance checks, and shows the complete plan before any side effect. On
explicit approval it starts one background code subagent per unit in an isolated
Git worktree, collects every result, and requires each successful unit to check,
commit, push, and open a pull request. The parent checkout is never used to hide
or replace a failed unit. Batch mode requires a clean Git repository with an
`origin` remote and is rejected in one-shot/print mode because that surface
cannot approve or revise the plan. Approving the unit plan authorizes only the
orchestration decision; normal file, command, Git, network, push, and PR
approvals remain in force for every subagent.
Dynamic workflows let a project-local JavaScript file orchestrate existing
subagents with `await agent(task, options)` and bounded fan-out with
`await pipeline(items, worker, {concurrency})`. Agent options accept `context`,
`mode`, `agent`, `maxIterations`, and `isolation`; the Python side executes each
call through the normal subagent runtime with the current approval policy,
project hooks, permissions, and optional worktree isolation. Workflows run in
the background with at most 16 concurrent and 1,000 total agent calls. Their
explore and worktree-isolated code calls may run concurrently; code calls that
share the parent checkout are serialized to prevent conflicting edits.
Their
source snapshot, results, and call cache live under
`.vibeagent/workflows/<workflow-id>/`; `resume` reruns the saved source and
replays matching completed calls by deterministic call ID before continuing.
The JavaScript VM exposes only `agent`, `pipeline`, and a bounded console;
string code generation is disabled and Node's permission model blocks direct
filesystem, child-process, worker, addon, and WASI access. Node.js 22 or newer
is required only for this feature. Workflow text never grants approval. Because
the workflow is asynchronous, `ask` mode does not open competing terminal
prompts: side effects without a trusted project permission are denied. Use
`/approval allow` before starting a code workflow when that broader policy is
intended. Example:

```js
const reports = await pipeline(
  ["authentication", "database", "tests"],
  (area) => agent(`Inspect ${area} and report concrete risks.`, {mode: "explore"}),
  {concurrency: 3},
);
return reports.map((report) => report.summary);
```
`/goal` keeps one completion condition per session. Each coding turn is followed
by a separate model request with no tools; that evaluator uses only bounded
session evidence and returns a strict achieved/reason decision. A negative
decision becomes guidance for the next coding turn. Active goals survive an
explicit `--resume` or interactive `/resume`, with elapsed time and accounting
reset for the resumed invocation; achieved and cleared goals do not restart.
The condition is limited to 4,000 characters, evaluator text cannot approve
tools, and the normal approval policy remains in force on every coding turn.
One-shot `vibeagent -p "/goal <condition>"` runs until achievement, agent
failure, evaluator error, or interruption in the same process.
VibeAgent supports project-local plugins that package skills, commands, agents,
command hooks, MCP servers, language servers, background monitors, and executables behind one manifest and lifecycle. A plugin uses
the Claude-compatible root layout: optional `.claude-plugin/plugin.json`,
`skills/`, `commands/`, `agents/`, `bin/`, `monitors/monitors.json`,
`hooks/hooks.json`, `.mcp.json`, and `.lsp.json`.
Repeat `--plugin-dir PATH` to load up to 20 local plugin roots or ZIP archives
for one invocation without installing or changing settings. Relative paths
resolve from the launch directory. Directory roots and component paths must be
regular and non-symlinked. ZIP archives are expanded into a private
content-addressed user cache with bounded archive size, entry count, path depth,
file count, and total bytes; traversal, absolute or duplicate paths, encryption,
symbolic links, special files, malformed archives, and unsafe cache trees fail
before a model request. Archives may contain the plugin at the ZIP root or under
one wrapper directory.
Repeat `--plugin-url URLS` to fetch invocation-only plugin ZIPs from public
HTTPS URLs. One flag may contain space-separated URLs, matching the
Claude-compatible CLI contract. VibeAgent rejects credentials, fragments,
non-ZIP paths, private or mixed-scope DNS results, cross-scope or non-HTTPS
redirects, non-identity content encoding, oversized responses, and malformed
archives. Downloads bypass environment proxies, use private `0600` temporary
files, and are removed after the validated content-addressed plugin root is
created. Duplicate URLs are fetched once; local and remote plugins share the
same 20-plugin limit and same-name conflict checks. A failed fetch or invalid
archive stops before provider creation rather than silently running without the
requested extension.
Invocation plugins participate in interactive catalogs, command expansion,
provider-independent agents, skills, hooks, MCP, LSP, monitors, executables,
resume, fork, worktree, background, and nested subagent paths. An invocation
plugin overrides an installed plugin with the same manifest name; duplicate
invocation names fail before a model request. Session events record only the
count, not plugin paths or component contents.
Install a project directory directly or register a local/remote marketplace:

```text
/plugin validate extensions/team-tools
/plugin install extensions/team-tools
/plugin marketplace add extensions/team-marketplace
/plugin marketplace add extensions/team-marketplace --scope user
/plugin install review-tools@team-marketplace
/plugin install review-tools@team-marketplace --scope project
/plugin install review-tools@team-marketplace --scope user
/plugin disable review-tools --scope local
/plugin update review-tools
/plugin marketplace update
/plugin marketplace auto-update team-marketplace on
/plugin marketplace add acme/coding-plugins#v1
/plugin marketplace add https://plugins.example.com/marketplace.json
/plugin config review-tools
/plugin config set review-tools api_endpoint https://api.example.com
/plugin config set review-tools api_token YOUR_TOKEN
/reload-plugins
/plugin list
```

Installation rejects path escapes, symbolic links, non-regular files, more than
5,000 files, or more than 100 MB, then atomically copies the plugin into the
gitignored `.vibeagent/plugins/cache/` store. Reinstall preserves the current
enabled state; disable removes every component from discovery without deleting
the cache; uninstall rolls state and cache removal back together on failure.
Explicit `--scope user`, `--scope project`, and `--scope local` installations
write qualified plugin IDs to `~/.claude/settings.json`,
`.claude/settings.json`, and `.claude/settings.local.json` respectively. Local
declarations override project declarations, which override user declarations.
User plugins and marketplaces use the independent `~/.vibeagent/plugins/`
store and are discovered from every project; a project cache with the same
plugin or marketplace name takes precedence. One project cache may belong to
both project and local scopes, and uninstalling one scope retains that cache
until its last declaration is removed. User settings, state, and cache
mutations use the same rollback transaction. Commands without `--scope` retain
the original project-local installation behavior for compatibility.
The same `VIBEAGENT_USER_HOME` override redirects these user plugin paths.
Plugin skills, commands, and agents use `plugin-name:component` names, while MCP
and LSP servers use `plugin-name.server`. `${CLAUDE_PLUGIN_ROOT}` and
`${CLAUDE_PROJECT_DIR}` are expanded in skill and agent text, command templates,
hooks, MCP configuration, and LSP configuration. Plugin hooks and MCP calls retain normal approval,
permission, and sandbox boundaries. Manifest component paths must be `./`
relative; `hooks` and `mcpServers` may instead contain Claude-compatible inline
objects, which use the same namespacing, variable expansion, user configuration,
and safety checks as JSON-file configurations. Executable files directly under each enabled plugin's `bin/` are
prepended to the scoped `PATH` used by finite commands, background commands,
hooks, command preflights, and Bubblewrap launches. The host process environment
is not modified; disabling a plugin removes its path on the next command, and
same-name executable conflicts resolve deterministically by plugin name.
Plugin monitors may be declared in `monitors/monitors.json`, through an
`experimental.monitors` relative JSON path, or as an inline monitor array. An
`always` monitor starts after session-start hooks; an
`on-skill-invoke:<skill-name>` monitor starts once its plugin skill is loaded.
Every monitor start follows command approval, project permission, blocked-command,
and sandbox policy. Plan and deny modes skip startup. Each stdout line is delivered
to the model as explicitly untrusted runtime evidence, with bounded line and queue
sizes; stderr and exit codes are reported on crashes. Monitor processes receive
`${CLAUDE_PLUGIN_ROOT}`, `${CLAUDE_PLUGIN_DATA}`, `${CLAUDE_PROJECT_DIR}`, the
scoped plugin executable `PATH`, and ordinary environment substitutions. They are
terminated on every agent-run exit, while plugin data persists under
`.vibeagent/plugin-data/`. Disabling a plugin prevents monitors in the next run;
already-started monitors retain their current-run lifecycle. `${user_config.*}`
values declared by a manifest `userConfig` schema are available to monitors and
other plugin components. Shared values are read from
`pluginConfigs[plugin-id].options` in `~/.claude/settings.json`,
`.claude/settings.json`, and `.claude/settings.local.json`; local values win
over project and user values, and `CLAUDE_PLUGIN_OPTION_<KEY>` wins over all
settings. `/plugin config set ... --scope user` writes shared values to the
user settings file and sensitive values to the mode-`0600` protected
`~/.vibeagent/plugins/user-config-credentials.json` store. Without a scope,
shared values and credentials retain their project-local behavior. Sensitive
values are redacted from `/plugin config`, rejected in model-visible skill,
agent, and command content, and delivered to hook, MCP, LSP, and monitor
subprocesses through environment variables. Missing required values keep a new
plugin disabled and block `/plugin enable` until configured.
Plugins may provide Claude-compatible default settings in root `settings.json`
or the manifest `settings` object. Root `settings.json` wins when both exist;
unknown keys are ignored. The supported `agent` setting must name an agent
declared by that plugin and selects its namespaced profile for the main thread
when neither `--agent` nor `.claude/settings.local.json` / `.claude/settings.json`
selects another profile. The explicit CLI flag has highest priority, followed by
local project settings, project settings, then the enabled plugin default. A
unique plugin agent may also be selected by its bare name; ambiguous bare names
fail before the first model request. Multiple enabled plugin defaults likewise
require an explicit or project-level selection. `subagentStatusLine` command
settings customize rows in the interactive terminal subagent panel. VibeAgent
sends the current task snapshot as JSON on stdin and accepts one
`{"id": ..., "content": ...}` JSON object per output line; the default panel
remains available when customization is absent, denied, or fails.
Project and user marketplaces use `.claude-plugin/marketplace.json`,
cache a non-symlink snapshot without Git/runtime metadata, verify each relative
plugin source and manifest identity, support add/list/details/update/remove, and
atomically uninstall marketplace-owned plugins when the catalog is removed.
`/plugin update <name>` refreshes the source marketplace when needed, skips an
installed plugin whose explicit resolved version is unchanged, and atomically
replaces unversioned or newer plugin content while preserving its enabled state.
The plugin manifest version takes precedence over a marketplace entry version.
`/plugin marketplace update [name]` refreshes one or all registered catalogs;
batch refresh continues after individual failures and reports each result.
`/plugin marketplace auto-update <name> <on|off>` controls the persisted,
per-marketplace background updater. It is off by default for local and
third-party marketplaces. Enabled marketplaces refresh after a random delay of
up to ten minutes after interactive startup, update their installed plugins,
and print a `/reload-plugins` notification without initializing a model client.
`DISABLE_AUTOUPDATER=1` disables this work globally, while
`FORCE_AUTOUPDATE_PLUGINS=1` keeps plugin updates enabled when the global updater
is disabled. Background failures retain the last valid catalog and plugin cache
and are reported on the next idle CLI tick.
Remote marketplaces support GitHub `owner/repository[#ref]`, public HTTPS or SSH
Git repositories, and public HTTPS `marketplace.json` files. Remote catalog entries
support `github`, `url`, and `git-subdir` Git sources with optional `ref` or
`sha`, plus `npm` sources with a package, exact version or dist-tag, and optional
registry. npm packages are fetched without executing lifecycle scripts, require
registry-provided SHA-512 integrity or SHA-1 shasum metadata, and are extracted
with the same path, file-count, and size boundaries as other plugins. Network
HTTPS URLs must be credential-free and all Git hosts must resolve publicly.
HTTP redirects are disabled for Git and cannot downgrade JSON downloads. SSH
sources use `ssh-agent`, require a pre-existing strict `known_hosts` entry, disable
passwords, prompts, user SSH configuration, proxies, and local commands, and never
fall back to interactive authentication. Inherited Git configuration injection is
removed and each fetch uses a bounded temporary checkout. Set `VIBEAGENT_PLUGIN_GIT_TIMEOUT_MS`
between 1,000 and 600,000 milliseconds to override the 120-second Git timeout.
LSP configuration accepts a root `.lsp.json`, a manifest-relative JSON path, or
an inline `lspServers` object. Each server declares `command`, optional `args`
and environment/settings fields, and an `extensionToLanguage` map. VibeAgent
uses bounded stdio JSON-RPC processes for definitions, implementations,
references, hover, document symbols, and workspace symbols, and publishes
language-server diagnostics back to the model after successful file edits.
Language-server binaries remain separately installed dependencies. Socket
transport is rejected explicitly; when no enabled plugin claims a file,
`LSP` retains the built-in lexical code-intelligence fallback.
On Linux and macOS, interactive and one-shot CLI sessions register a user-only
Unix socket under `/tmp/vibeagent-<uid>/peers`. `ListAgents` combines current
session subagents with other live local sessions, and `SendMessage` sends plain
text to an exact peer ID or unambiguous peer name. A receiving agent reads
messages between tool calls, while an idle interactive session starts a coding
turn on the next one-second wakeup. Incoming text is always labeled untrusted:
it cannot approve tools, answer permission prompts, execute slash commands,
change configuration or project instructions, or override local safety rules.
`crossSessionInbound` in trusted `.claude/settings.json` or local
`.claude/settings.local.json` accepts `accept`, `hold`, or `refuse`; the
`VIBEAGENT_CROSS_SESSION_INBOUND` environment variable overrides both. Without
an explicit value, matching permission-mode classes deliver and mismatched
classes hold for `/peer-inbox`. Socket and registration paths reject symlinks,
Linux verifies the sender PID with `SO_PEERCRED`, duplicate messages are
throttled, and delivered/held queues are bounded. Set
`VIBEAGENT_DISABLE_CROSS_SESSION=1` to disable registration. This peer-to-peer
transport remains same-machine only and does not provide cross-machine
`SendMessage` replies. The separate authenticated `remote-control` server can
control project-local detached sessions from a browser.
If a successful run finishes while the latest plan still
has `pending` or `in_progress` items, the final result and session summary
include a completion warning and completion blocker. If no plan exists after
multi-step coding work, such as multiple project changes or a project change
followed by a verification command, completion is also blocked while iteration
budget remains so the model can record a concise completed checklist before
finishing. Session
summaries also report the
latest `final_review` readiness, blocking issue count, warning count, changed
file count, and suggested-check count when a final review was recorded. When a
run completes after project-changing tools without a `final_review`, VibeAgent
automatically records a read-only `final_review`; if that review is not ready,
or if its suggested checks were not run after the latest project change, the
agent feeds those completion blockers back to the model and continues while
iteration budget remains. Running background processes reported by the latest
`final_review` also block completion until they are stopped or no longer
running. If the budget is exhausted, the final result and session summary
include the blocker and warning. Session summaries and audits also
report how many attempted completions were blocked and the latest blocker list.
Successful
suggested checks run after the latest project change are also recorded as
verification evidence in the final result and session summary; suggested checks
that are still pending or failed are listed by command. Each coding turn records its task, and
`/sessions` lists recent runs with completion status and a compact task summary.
The CLI automatically uses the latest run as compact context for the next coding
turn; `--resume [run-id]`, `--session-id [run-id|latest]` on one-shot tasks,
and `/resume [run-id|latest]` in the interactive prompt continue the selected
Session ID with a bounded historical resume context, while
`--compact [run-id]` and `/compact [run-id]` load the same compact handoff
context explicitly. Both one-shot forms accept `--resume-max-failures`,
`--resume-max-files`, `--resume-max-commands`, `--resume-max-checks`,
`--resume-max-output-chars`, `--resume-max-text` and the matching
`--compact-max-*` options; the interactive forms use `--max-failures`,
`--max-files`, `--max-commands`, `--max-checks`, `--max-output-chars`, and
`--max-text`. The loaded context is marked as prior-session evidence, not a new
user instruction. Use `--no-auto-compact` for a one-shot coding task that should
not automatically load the latest compact session context. When no run id is supplied, these recovery commands skip
`local-*` sessions created by read-only CLI utilities. `/resume off` or `/clear`
clears it before a fresh task.
`-n/--name <name>` names a new interactive or one-shot coding session at startup.
Consecutive interactive coding prompts and evaluator-driven `/goal` turns reuse
the active Session workspace and run ID, so their plans, transcript, usage, and
rewind points form one coherent history. While that Session remains active in
the current process, its full model/tool conversation is carried into the next
prompt and automatically uses the existing context compaction thresholds. A
startup `--autocompact` value applies to every coding turn and delegated agent in
that process; compaction events record the configured threshold, effective
character threshold, and estimated previous token count. A
redacted, bounded copy of the non-system conversation is also atomically stored
as mode-`0600` session state after safe model/tool boundaries. Explicit
`--resume`, `/resume`, and `--session-id` restore that copy and append the next
turn to the same Session ID. Branches and `--fork-session` restore it into a new
Session ID, while compact modes also create a new Session from the bounded
handoff. Resumed turns rebuild the current system prompt, project snapshot,
permissions, and prompt attachments. Prompt-file text/images, system messages, write/edit payloads,
tool-result content/diffs, and common credentials are not retained verbatim.
Malformed, oversized, mismatched, or symbolic-link conversation state falls
back to the bounded handoff instead of being trusted. `--compact`, `/compact`,
automatic one-shot compaction, `/clear`, and conversation rewind remain explicit
compressed or fresh conversation boundaries.
For isolated automation, `-p --no-session-persistence` runs coding-session
events, hooks, usage accounting, structured output, and stream-json observers
against a private temporary session tree, then removes that tree after final
output. It disables implicit latest-session context. An explicit `--resume` or
`--compact` may still read a stored source session, but never appends to it; the
ephemeral run ID cannot be resumed afterward. Persistent-identity operations
`--name`, `--fork-session`, `--worktree`, and one-shot `/goal` are rejected with
this mode. The option controls resumable session storage, not requested project
edits, commands, commits, plugin data, or background-process records.
Only one agent turn may write a Session at a time. A nonblocking per-turn lease
reports the active owner and asks the caller to wait or fork instead of allowing
concurrent whole-conversation snapshots to overwrite each other; process exit
automatically releases the lease.
`/rename [name]` updates the active session name; without a name it derives a
unique filesystem-safe name from the first coding task. Exact session IDs take
precedence over names during resume, and duplicate or reserved names are rejected.
`/export` prints the active session's redacted readable timeline in the terminal.
`/export <filename>` atomically writes the same bounded plain text under the
project directory, refusing protected, escaping, symbolic-link, and non-regular
targets. It does not invoke a clipboard helper, file manager, or other GUI.
`/branch [name]` creates a new session from the active coding context and switches
the next coding turn into that branch. `--fork-session` provides the same behavior
when combined with `--continue`, `--resume`, or `--session-id`; one-shot JSON adds
`sessionBranch.runId` and `sessionBranch.sourceRunId`. The source transcript is
never modified. Branches copy task, eligible scheduled-task, active-goal, and
additional-directory state, retain explicit parent lineage, appear in
`/sessions`, and can be resumed by exact branch name. An unstarted branch follows
its parent context on resume; after its first task it resumes from its own events.
Tool result payloads sent back to the model and persisted session events redact
common API keys, tokens, passwords, bearer values, and secret query parameters.
Session summaries, handoffs, resumes, transcripts, and command-output tails apply
the same redaction when reading historical events.
`/transcript [run-id] [--max-events N] [--max-text N]` shows a bounded event
timeline for diagnosing what happened in a previous run, and
`/session-search [--run run-id] [--max-matches N] [--case-sensitive] [--max-text N] <query>`
locates known error text, file paths, or tool names in that same safe timeline
without exposing complete tool payloads, including approval targets and any
short approval preview summaries.
`/session-commands [run-id] [--max-commands N] [--max-output-chars N]` shows
bounded stdout/stderr tails from commands that ran in a session, which helps
resume after test or build failures without rerunning them first.
`/session-output-contexts [run-id] [--max-commands N] [--max-output-chars N] [--context-lines N] [--max-contexts N] [--max-bytes N]`
extracts file:line contexts from session command output, and
`/session-output-diagnostics [run-id] [--max-commands N] [--max-output-chars N] [--context-lines N] [--max-diagnostics N] [--max-contexts N] [--max-bytes N]`
summarizes errors, warnings, failures, and referenced contexts from session
command output.
`/session-files [run-id] [--max-files N]` summarizes project paths that a session
read, edited, previewed, moved, or otherwise referenced without showing file
contents. `/session-failures [run-id] [--max-failures N] [--max-text N]` lists
model request errors, failed tools, failed commands, denied approvals, malformed
session rows, and failed or blocked final run results for targeted recovery;
denied approval rows include the target and matching preview summary when one
was recorded.
`/session-verification [run-id] [--max-checks N]` shows the verified, pending,
and failed suggested checks recorded for the newest or selected run.
`/run-session-verification [run-id] [--max-checks N] [--timeout-ms N] [--max-output-chars N] [--no-failed] [--no-pending] [--continue-on-failure] [--output-contexts] [--output-diagnostics] [--context-lines N] [--max-diagnostics N] [--max-contexts N] [--max-bytes N]`
reruns recorded failed and/or pending verification commands for the newest or
selected run using the same command safety rules as local run commands.
`/session-audit [run-id] [--max-failures N] [--max-files N] [--max-commands N] [--max-checks N] [--max-text N]`
shows a finish-time readiness audit with blockers, verification counts, active
background process leftovers, plan status, recent failures, command evidence,
and referenced files.
`/session-handoff [run-id] [--max-failures N] [--max-files N] [--max-commands N] [--max-checks N] [--max-output-chars N] [--max-text N]`
combines the compact summary, finish-readiness blockers, latest plan,
verification status, failures, referenced files, and command output tails into
one recovery bundle. Recent blocked-completion details include the concrete
pending or failed verification commands so resumed work can pick up from the
exact blocker. Sessions whose final agent response returned `success: true` but
did not pass `completionReady` are reported as `blocked`, not `completed`, in
session summaries and usage totals.
Before each coding prompt, VibeAgent automatically saves a Git-backed checkpoint
after recording the prompt and before calling the model. It retains the newest
100 linked checkpoints per Session; a failed prompt checkpoint is retried before
the first approved project mutation or finite command. `/checkpoint [label]`
saves a local handoff snapshot of `git status`, HEAD, unstaged diff, staged diff, and ordinary
untracked file contents for later review or restore; `latest` can be used as the
checkpoint id for the newest saved checkpoint. `/check-checkpoint-restore <id>`
previews the restore constraints before `/checkpoint-restore <id>` rewrites
tracked staged/unstaged changes and saved untracked files. `/usage`
reports locally recorded session usage and token counts when the provider returns
them. `/cost` uses optional `VIBEAGENT_INPUT_USD_PER_MILLION`,
`VIBEAGENT_OUTPUT_USD_PER_MILLION`, `VIBEAGENT_CACHE_CREATION_USD_PER_MILLION`,
and `VIBEAGENT_CACHE_READ_USD_PER_MILLION` values; without those rates it reports
the missing configuration instead of guessing. The model can also inspect compact
session summaries through a read-only tool without exposing full tool payloads.

## User and project hooks

Personal command hooks can be declared in `~/.claude/settings.json` and apply
across projects. Project hooks can be declared in `.vibeagent/hooks.json`,
`.claude/settings.json`, or `.claude/settings.local.json`. Claude settings keep
the hook map under a top-level `hooks` key; `.vibeagent/hooks.json` accepts the
hook map directly or under `hooks`:

```json
{
  "PreToolUse": [
    {
      "matcher": "write_file|edit_file",
      "hooks": [
        {"type": "command", "command": "python3 -m unittest", "timeout_ms": 30000}
      ]
    }
  ]
}
```

Use `/hooks` interactively or `--hooks [--json]` non-interactively to inspect
the resolved event, matcher, handler type, source, timeout, and safe handler
metadata. Command and URL targets are redacted, while HTTP header values,
MCP input values, and injected environment values are never displayed. Invalid
hook configuration is included in the report and makes `--hooks` exit nonzero.

Supported lifecycle events are `Setup`, `SessionStart`, `SessionEnd`, `PreCompact`,
`PostCompact`, `CwdChanged`, `FileChanged`, `ConfigChange`, `InstructionsLoaded`, `MessageDisplay`, `Notification`, `UserPromptExpansion`,
`UserPromptSubmit`,
`PreToolUse`, `PermissionRequest`, `PermissionDenied`, `PostToolUse`, `PostToolUseFailure`, `Stop`,
`StopFailure`,
`SubagentStart`, `SubagentStop`, `TeammateIdle`, `PostToolBatch`, `TaskCreated`, `TaskCompleted`,
`DirectoryAdded`, `Elicitation`, `ElicitationResult`, `WorktreeCreate`, and `WorktreeRemove`. Tool-event
matchers apply to the model tool name, parsed VibeAgent action type, and
Claude-compatible aliases.
`SessionStart` matches `startup` or `resume`; `InstructionsLoaded` matches
`session_start`, `nested_traversal`, or
`path_glob_match`; subagent lifecycle matchers use the selected project profile
name, `Explore`, or `general-purpose`. Plain stdout or structured
`additionalContext` from startup, prompt, and `SubagentStart` hooks enters the
corresponding first model turn. Prompt hooks can exit 2 or return
`decision: block`; `Stop` and `SubagentStop` hooks can return a block reason to continue
the relevant agent, with independent eight-continuation limits. A blocked
subagent `finish` call receives a normal tool result before retrying, preserving
the provider tool protocol. Subagent inputs include `agent_id`, `agent_type`,
and, on stop, `stop_hook_active`, `last_assistant_message`, and
`agent_transcript_path`. Parent lifecycle events remain in the session event log,
while resumable subagent message history is atomically stored under
`.vibeagent/sessions/<session-id>/subagents/` with secret redaction.

`UserPromptExpansion` runs after a direct project, user, or plugin slash command
or skill has expanded and before its first model request. Its matcher receives
the command name, while hook input includes `expansion_type`, `command_name`,
`command_args`, `command_source`, and the original slash-command `prompt`.
`decision: block` or exit code 2 rejects the expansion without calling the main
model; `additionalContext` is appended alongside the expanded prompt. Command,
HTTP, MCP tool, prompt, and experimental agent handlers are supported.

`Notification` hooks currently fire for `permission_prompt` immediately before
an ask-mode approval handler and for `idle_prompt` once an established
interactive session has waited 60 seconds for input. Input includes `message`,
an optional `title`, and `notification_type`; matchers filter on the notification
type. Notification decisions and exit codes never modify the underlying action.
Command, HTTP, and MCP tool handlers are supported, and structured
`systemMessage` output remains user-facing instead of entering model context.
VibeAgent does not open a file manager, browser, or other GUI unless a configured
and approved notification hook explicitly runs such a command.

`FileChanged` hooks watch literal filenames from matcher segments separated by
`|` in the persisted session cwd. They receive an absolute `file_path` and an
`event` of `add`, `change`, or `unlink`; decisions and failures cannot undo the
disk change. Agent runs poll immediately before and after model requests, and an
established interactive session also polls once per idle-input callback.
`watchPaths` returned by `SessionStart`, `CwdChanged`, or `FileChanged` replaces
the session's dynamic watch list; these paths must be absolute, workspace-bound,
free of symbolic-link components, outside `.git` and `.vibeagent`, and are
limited to 100 entries. Static matcher paths remain watched. Command, HTTP, and
MCP tool handlers are supported, `systemMessage` stays user-only, and
`CLAUDE_ENV_FILE` updates affect subsequent Bash commands.

`MessageDisplay` hooks run once for each complete assistant text message that is
actually returned to the user. They receive UUID `turn_id` and `message_id`
fields, `index: 0`, `final: true`, and the original text in `delta`. A successful
`hookSpecificOutput.displayContent` replaces only terminal or print-mode output;
the original `message`/`result`, transcript, resumed conversation, goal evidence,
and model context remain unchanged. Machine-readable output exposes the rendered
value separately as `displayMessage`/`display_message`. Empty replacement text is
honored, failures fall back to the original, matchers are ignored, and command,
HTTP, or MCP tool handlers default to a 10-second timeout. Tool-call-only model
responses do not fire this event.

`TaskCreated` and `TaskCompleted` ignore matchers and run for main-agent,
subagent, and teammate task transitions. Their input includes `task_id`,
`task_subject`, `task_description`, and available teammate/team names. Exit code
2 blocks the transition and returns stderr to the model without changing the
atomic task store. JSON `{"continue": false, "stopReason": "..."}` also blocks
the transition and halts the active turn. Failed or malformed handlers remain
non-blocking.

`PostToolBatch` ignores matchers and fires once after every resolved main-agent
or subagent tool batch, including parallel and resumed deferred batches. Its
`tool_calls` input contains each tool name, original input, provider tool ID,
and the exact serialized `tool_result` content sent back to the model. Returned
`additionalContext` is appended once before the next model request;
`decision: block` or `continue: false` records the completed results and stops
the agent loop before another request. A batch-only Hook does not disable
parallel tool execution.

`TeammateIdle` ignores matchers and runs when a named teammate is about to
finish after either a text response or the `finish` tool. Its input includes
the stable `teammate_name` and persisted `team_name`. Exit code 2 returns stderr
as another teammate turn, while JSON `continue: false` stops the teammate. The
runtime caps repeated idle continuations at eight and preserves provider tool
result pairing when a `finish` call is returned for more work.

`StopFailure` runs instead of `Stop` when the main model request still fails
after all configured retries and context recovery. Matchers filter the
standard error categories `rate_limit`, `overloaded`, `authentication_failed`,
`oauth_org_not_allowed`, `billing_error`, `invalid_request`,
`model_not_found`, `server_error`, `max_output_tokens`, and `unknown`. Input
includes the category in `error`, bounded redacted `error_details`, and the
rendered failure in `last_assistant_message`. Command, HTTP, and MCP tool
handlers are supported. Their output, exit code, and runtime failures are
non-blocking and never replace the original model failure.

`DirectoryAdded` matches `slash_command` or `register_repo_root` and runs in a
background thread after the new absolute directory is available to workspace
and permission checks. It fires for an interactive `/add-dir` addition and the
Python `vibeagent.directory_added_hooks.register_repo_root(...)` API, but not
for startup `--add-dir`, restored session directories, removals, or permission
updates. Command, HTTP, and MCP tool handlers are supported. For `/add-dir`,
structured `systemMessage` output is added to the next code turn and failures
are shown as warnings; SDK output and failures remain session-debug
information. The event cannot block or roll back a successful directory
addition, and uses a 600-second default timeout.

`WorktreeCreate` and `WorktreeRemove` ignore matchers and support command or
HTTP handlers. A configured create handler replaces the default Git worktree
backend for `--worktree` and isolated subagents and must return an existing,
symlink-free directory path. Command handlers print the path as their last
non-empty stdout line; HTTP handlers return `hookSpecificOutput.worktreePath`.
Create failures stop isolation before a model call. Remove handlers receive the
absolute `worktree_path`; failures preserve the directory and remain visible in
the isolation outcome. Because create handlers replace Git setup, they also own
copying any local ignored files; `.worktreeinclude` runs only for the built-in
Git backend.

`PreCompact` and `PostCompact` match `manual` or `auto`. Automatic main-agent
context reduction emits both events around a successful compact operation;
interactive `/compact` does the same around the bounded handoff summary.
`PreCompact` receives `trigger` and empty `custom_instructions`, while
`PostCompact` receives `trigger` and `compact_summary`. `SessionEnd` matches
`clear`, `resume`, `logout`, `prompt_input_exit`,
`bypass_permissions_disabled`, or `other`; VibeAgent emits it for one-shot
termination, interactive exit/EOF, `/clear`, session switching, and branching.
These events cannot block compaction or termination. Session-end handlers share
a 1.5-second default budget, configurable up to 60 seconds through an explicit
hook timeout or `CLAUDE_CODE_SESSIONEND_HOOKS_TIMEOUT_MS`.

`Setup` matches `init` or `maintenance`. `--init-only` runs `Setup(init)` and
then `SessionStart(startup)` before exiting without creating a provider client.
In print mode, `--init` and `--maintenance` run the matching Setup hooks before
the normal session starts; the existing non-print `--init [AGENTS.md|CLAUDE.md]`
command still creates a starter instruction file. Setup cannot block. Only
structured `additionalContext` is added to the first model turn; plain stdout
remains in hook diagnostics. Setup supports command and MCP tool handlers and,
like SessionStart, receives `CLAUDE_ENV_FILE` for later Bash commands.

`CwdChanged` ignores matchers and fires after a main-session shell command
actually changes the effective directory. Its JSON input includes absolute
`old_cwd` and `new_cwd` values, its common `cwd` field is the new directory,
and the hook command runs there. It cannot block or alter the completed
directory transition. `Setup`, `SessionStart`, and `CwdChanged` hook processes also
receive `CLAUDE_ENV_FILE`; changes they write there apply to later Bash
commands in the session.

Every matching command, HTTP, or MCP tool hook requires approval under the
current session policy. Prompt and agent hooks make bounded calls through the
active provider client without a separate tool approval. Command handlers still pass command hard-block checks,
HTTP handlers validate their destination before connecting, and MCP handlers
reuse configured-server and advertised-tool validation. Plan mode records and
skips those three external handler types; prompt and agent hooks still evaluate
in Plan mode. A failed or denied command pre-tool hook blocks the
target tool, as does a denied HTTP or MCP handler approval. A failed post-tool
command hook preserves the target result but
records an additional tool error that prevents an unqualified successful
completion. Hook commands receive a
Claude-compatible JSON object on stdin, `CLAUDE_PROJECT_DIR`, plus `VIBEAGENT_HOOK_EVENT` and
`VIBEAGENT_HOOK_INPUT`; tool hooks also receive `VIBEAGENT_TOOL_NAME` and
`VIBEAGENT_TOOL_TARGET`. Inputs use private temporary files inside the session
directory and are deleted after execution. Results are recorded in the session
timeline with bounded, redacted output. Background subagent hooks and tools
follow the same policy. Ask-mode approval requests use the parent session
approval handler and identify the subagent; allow and deny modes still pass
through the normal permission and command safety checks.

Claude-compatible `type: "prompt"` handlers perform one strict no-tool
`{"ok": true|false, "reason": "..."}` evaluation. Experimental
`type: "agent"` handlers use the same fields and response schema, but can take
up to 50 model turns with bounded read-only file, search, and project-inspection
tools. Agent handlers cannot edit files, run commands, delegate work, or ask the
user; their activity is recorded as Hook events rather than ordinary resumable
subagents. `$ARGUMENTS` expands to the lifecycle input JSON, `model` scopes an
optional model override, and `continueOnBlock` returns a Pre/Post block reason
to the active agent instead of ending that turn. Prompt handlers default to a
30-second timeout and agent handlers to 60 seconds. Both share provider budget
and overload fallback state, and malformed responses, timeouts, or provider
failures are recorded as non-blocking Hook errors.

`PermissionRequest` runs only in ask mode when VibeAgent is about to request
approval for the target tool. Command, HTTP, and MCP tool handlers can return
Claude-compatible `hookSpecificOutput.decision.behavior` set to `allow` or
`deny`; a deny decision requires `message`, and command exit code 2 also denies.
Prompt and agent handlers may inspect the request, but their `{ok, reason}`
result does not grant or deny permission. Multiple command, HTTP, and MCP tool
decisions resolve as `deny > allow`. An allow decision can replace ordinary
user approval and may supply a complete `updatedInput` plus bounded
`updatedPermissions` entries for `addRules`, `replaceRules`, `removeRules`,
`setMode`, `addDirectories`, or `removeDirectories`. Updates can target the
current session or Claude user, project, and local settings. Updated input is
parsed again and re-evaluated against permission rules and workspace safety;
project `deny` and `ask` rules, repeated-approval actions, command hard blocks,
and sandbox safety retain priority. A deny decision may set `interrupt` to halt
the active turn. Handler failures and malformed or rejected updates are
non-blocking and fall back to normal user approval. The input omits
`tool_use_id`, matching Claude's permission event.

`PermissionDenied` runs only when the auto classifier denies a tool call. Its
input includes `tool_name`, `tool_input`, `tool_use_id`, and the classifier
`reason`. Command, HTTP, and MCP tool handlers may return
`hookSpecificOutput: {"hookEventName": "PermissionDenied", "retry": true}` to
tell the model that a materially different call may be attempted; this never
reverses the denied call. Three consecutive or twenty total classifier denials
fall back to an approval prompt in interactive sessions and halt non-interactive
execution. Allowed actions reset the consecutive counter.

Command hooks may set `"async": true` to start after approval without waiting
for completion. `"asyncRewake": true` implies async execution and, when the
hook exits with code 2, starts an agent turn while an interactive session is
idle. Claude-style `timeout` values are seconds; the existing `timeout_ms` form
remains supported, and the two forms are mutually exclusive. Async hooks cannot
block a tool or apply permission decisions because the triggering action has
already continued. A successful JSON result may return `systemMessage`,
top-level `additionalContext`, or
`hookSpecificOutput.additionalContext`. Bounded, redacted `additionalContext`
is injected once on the next model turn, while `systemMessage` is kept out of
model context and exposed through terminal and machine results for the user.
Ordinary results wait for that next turn, while an
`asyncRewake` exit-code-2 result uses stderr, or stdout when stderr is empty, to
wake the idle CLI. Private launch/input files and atomic mode-`0600` state stay
inside the active session and are cleaned after completion. Print-mode teardown
and interactive CLI exit cancel unfinished async hooks; hooks that must outlive
the session must launch their own detached work. Async hook commands retain the
same approval, command hard-block, workspace, and sandbox boundaries as
synchronous hooks. `timeout` defaults to 600 seconds.

HTTP handlers use Claude-compatible `type: "http"`, `url`, `headers`, and
`allowedEnvVars` fields. They POST up to 1 MiB of hook input as JSON without
using environment-configured proxies and process a
successful response body through the existing plain-text or structured hook
output path, so a 2xx `PreToolUse` response can return `permissionDecision`,
`updatedInput`, or `additionalContext`. Header environment references expand
only when explicitly named by `allowedEnvVars`; unlisted references become
empty. URL credentials, malformed ports, reserved transport headers, mixed
local/public DNS answers, and redirects crossing the original network scope are
rejected. Non-2xx responses, connection failures, oversized inputs, and
timeouts are recorded as
bounded non-blocking hook errors; they cannot block a tool unless a 2xx JSON
response returns an explicit decision.

MCP handlers use Claude-compatible `type: "mcp_tool"`, `server`, `tool`, and
optional `input` fields. String input values can reference the hook payload with
`${path.to.value}` placeholders; an exact placeholder preserves JSON types,
while embedded placeholders render compact text. Expansion is bounded by depth,
node count, and 50,000 serialized characters, and missing paths fail without
calling the server. The handler uses the same configured MCP transport, command
hard blocks, tool discovery, approval rules, result redaction, and timeout path
as a normal `mcp_call`. Successful text is processed as ordinary hook stdout,
including structured `PreToolUse` decisions. Missing servers, unavailable tools,
protocol failures, and MCP `isError` results are recorded as non-blocking hook
errors so they do not suppress the triggering action.

Prompt handlers use Claude-compatible `type: "prompt"`, `prompt`, optional
`model`, `timeout`, and `continueOnBlock` fields on `PreToolUse`, `PostToolUse`,
`PostToolUseFailure`, `PermissionRequest`, `PermissionDenied`, `UserPromptSubmit`, `Stop`, and
`SubagentStop`. The full bounded Hook input replaces `$ARGUMENTS`, or is
appended when the placeholder is absent; `\$` preserves a literal dollar sign.
The evaluator runs without tools through the existing provider-neutral client, shared cost budget,
fallback state, and retry path. An explicit model uses the same scoped model
override contract as agent profiles; without one VibeAgent inherits the active
model. Responses must be exactly one JSON object containing boolean `ok`, with
a bounded non-empty `reason` when false. A default false Pre/Post decision ends
the current agent turn; `continueOnBlock: true` returns the reason as tool
feedback so the model can continue. Stop and SubagentStop false decisions feed
the reason into another turn. Model, expansion, and response-validation errors
are bounded, redacted, and non-blocking. Prompt Hook timeout defaults to 30
seconds, and successful usage is included in session cost totals.

Successful `PreToolUse` hooks can return Claude-compatible structured JSON under
`hookSpecificOutput`. `permissionDecision` accepts `allow`, `ask`, `deny`, or
`defer`; multiple results resolve as `deny > defer > ask > allow`. `updatedInput`
replaces the complete model input and is reparsed before profile restrictions,
permission rules, approval previews, checkpoints, and execution. `allow` can
skip ordinary ask-mode target approval but cannot bypass deny/ask permission
rules, Plan or dontAsk ceilings, or command hard blocks. `ask` can require
approval for an otherwise read-only tool. `additionalContext` is included in
the model-visible hook result. Legacy top-level `decision: approve|block` is
also accepted. In `-p` print mode, `defer` atomically preserves the pending tool
batch, exits with `tool_deferred`, and re-runs the same PreToolUse hook on
`--resume`; interactive sessions retain the normal tool-error behavior. Hook
input includes the provider `tool_use_id`. For `AskUserQuestion`, an external UI
can resume with `allow` plus an `updatedInput.answers` map; only hook-updated
input can supply those answers, so the model cannot impersonate the user.

## Command sandbox

Linux and WSL2 command execution can use Bubblewrap OS isolation. Sandboxing is
disabled by default and can be enabled globally through the `sandbox` object in
`~/.claude/settings.json`, per project through `.claude/settings.json` or
`.claude/settings.local.json`, or through `.vibeagent/sandbox.json`:

```json
{
  "sandbox": {
    "enabled": true,
    "failIfUnavailable": true,
    "autoAllowBashIfSandboxed": true,
    "filesystem": {
      "allowWrite": ["./build-cache"],
      "denyWrite": ["./fixtures"],
      "denyRead": ["~/.aws/credentials"]
    },
    "network": {
      "allowedDomains": []
    }
  }
}
```

When active, the host filesystem is mounted read-only, the project and explicit
`allowWrite` paths are writable, `/tmp` and `/run` are isolated, `/dev` is
minimal, and PID/IPC/UTS namespaces are separated. An empty `allowedDomains`
list requests a fully isolated network namespace. The same launcher applies to
finite checks, command batches, hooks, and background processes.

External `allowWrite` paths and `excludedCommands` from user settings are
trusted user choices. The same settings from project files require explicit
project configuration trust. An untrusted project also cannot disable a
user-enabled sandbox, `failIfUnavailable`, or user-requested network isolation.
`denyWrite` and `denyRead` mounts override the writable project mount. Sandbox
paths must be exact; glob paths, `allowRead`, non-empty
sandbox network domain allowlists, and unsupported network options fail closed
rather than claiming partial enforcement. Sandbox network domain allowlists
require a proxy and are not yet implemented; this is separate from project
permission `WebFetch(domain:...)` rules, which match WebFetch request hosts
before approval. If Bubblewrap or network namespaces are unavailable,
`failIfUnavailable: true` blocks execution; otherwise VibeAgent records a
warning and falls back to unsandboxed execution or filesystem-only isolation.
Permission deny/ask rules and command hard blocks still apply; commands that do
not meet strict auto-approval qualification use the normal approval flow.
Use `/sandbox` or `--sandbox-status --json` to inspect effective configuration
and runtime capability.

`autoAllowBashIfSandboxed` defaults to `true`, but VibeAgent auto-approves a
Bash action only after preflighting every concrete command and confirming both
filesystem isolation and a disabled network namespace will actually apply.
Explicit permission `deny` or `ask` rules, Plan/deny session policies,
excluded commands, unavailable-network fallbacks, dynamic discovered command
batches, and sandbox launch warnings continue through normal approval. An
auto-approved action records a `sandbox_auto_approved` session event. The
sandbox report exposes `autoApprovalReady` so automation can distinguish an
enabled sandbox from one currently strong enough to reduce prompts.

## User and project environment

Claude-compatible `env` objects in `~/.claude/settings.json` apply to every
project. Environment values in `.claude/settings.json` and
`.claude/settings.local.json` become active only after the project configuration
is trusted; local values override project values, which override user values.
Variables already present when VibeAgent starts and explicit provider CLI flags
have higher priority than settings values.

The resolved environment is passed without mutating the VibeAgent host process
to provider configuration, finite and background commands, hooks, MCP servers,
plugin LSP servers, and plugin monitors. Names, value sizes, settings file sizes,
regular-file boundaries, and symbolic links are validated before use. Values do
not enter prompts, settings reports, or session events.

## User and project permissions

Fine-grained personal permissions can be declared under the `permissions` key
in `~/.claude/settings.json` and apply across projects. Project permissions can
be declared in `.vibeagent/permissions.json` or under `permissions` in
`.claude/settings.json` and `.claude/settings.local.json`:

```json
{
  "permissions": {
    "deny": ["Read(**/.env)", "Bash(git push *)"],
    "ask": ["WebFetch", "Bash(npm publish *)"],
    "allow": ["Edit(src/**)", "Bash(npm test *)"]
  }
}
```

Rules use `Tool` or `Tool(specifier)` syntax and are evaluated by effect in
`deny`, `ask`, then `allow` order. Common Claude Code names including `Bash`,
`BashOutput`, `KillBash`, `Read`, `Write`, `Edit`, `MultiEdit`,
`NotebookRead`, `NotebookEdit`, `LS`, `Glob`, `Grep`, `ToolSearch`, `Skill`, `WebFetch`, `WebSearch`, `ListMcpResourcesTool`, `ReadMcpResourceTool`, `Task`,
`TaskCreate`, `TaskGet`, `TaskList`, `TaskUpdate`, `TeamCreate`, `TeamDelete`, `CronCreate`, `CronList`, `CronDelete`, `Agent`, `LSP`, `EnterWorktree`, `ExitWorktree`, `AskUserQuestion`, `SendUserMessage`, `EnterPlanMode`, `ExitPlanMode`, `TodoWrite`, and `TodoRead` map to
the corresponding VibeAgent tools; native snake-case tool names are also
accepted. Model tool calls accept the same names with Claude-style field names
normalized before execution.
Claude MCP tool names such as `mcp__docs__search` can be used as model tool
names and permission rules; they match the corresponding `mcp_call`
server/tool pair exactly.
Command patterns support `*`, including the trailing `:*` spelling. File
patterns use project-relative `/`, `*`, and recursive `**` matching. A deny or
ask rule applies when any target in a multi-file operation matches; an allow
rule applies only when every target matches.
`WebFetch(domain:example.com)` and wildcard forms such as
`WebFetch(domain:*.python.org)` match the requested URL host before the fetch
approval/execution path runs.
Per-run CLI overrides use the same rule syntax via `--allowed-tools` and
`--disallowed-tools`. User allow rules are trusted across projects, CLI allow
rules are trusted for that run only, and project-file allow rules still require
explicit project trust. Rules from every scope are merged; `deny` still takes
precedence over `ask` and `allow` regardless of source.

User and project deny and ask rules always take effect. Because repository
settings are untrusted input, project allow rules do not skip side-effect
approval unless a one-shot run explicitly uses `--trust-project-permissions`
(or a library caller passes `trust_project_permissions=True`) or the project
has persistent user trust.
Use `--trust-status`, `--trust-project`, and `--untrust-project` with `--cwd` to
inspect, record, or remove persistent trust. Interactive mode offers the same
trust decision in the terminal when it first sees untrusted allow rules.

Persistent trust is stored outside the repository in
`~/.vibeagent/trusted-projects.json` with the canonical absolute project path;
`VIBEAGENT_TRUST_FILE` can override the location for isolated automation. The
store uses private file permissions and atomic writes, refuses symlink paths,
and fails closed on malformed content. Plan mode, explicit session deny,
workspace boundaries, and command hard blocks still take precedence.
`/permissions` and `--permissions --json` show loaded rule sources, persistent
trust, and errors, and rule matches are recorded in the session timeline.

Example task:

```text
写一个 Python 程序计算 1 到 100 的和并运行。
```

Example chat:

```text
/chat 今天适合学点什么？
```

## MCP servers

Stdio and Streamable HTTP MCP servers can be declared for a shared project in
`.mcp.json`, for every personal project in the top-level `mcpServers` object in
`~/.claude.json`, or privately for one project under that resolved project path
in `~/.claude.json`'s `projects` object:

```json
{
  "mcpServers": {
    "docs": {
      "type": "stdio",
      "command": "npx",
      "args": ["-y", "@example/docs-mcp"],
      "cwd": ".",
      "env": {"DOCS_TOKEN": "${DOCS_TOKEN}"}
    },
    "remote-docs": {
      "type": "http",
      "url": "https://docs.example.com/mcp",
      "headers": {"Authorization": "Bearer ${DOCS_TOKEN}"}
    }
  }
}
```

Manage the same scopes without editing JSON by hand:

```text
/mcp list
/mcp get docs
/mcp add --scope user --env DOCS_TOKEN=${DOCS_TOKEN} docs -- npx -y @example/docs-mcp
/mcp add --transport http --scope project --header Authorization:Bearer-${DOCS_TOKEN} remote-docs -- https://docs.example.com/mcp
/mcp add-json --scope local private-tools '{"command":"python3","args":["tools/server.py"]}'
/mcp remove --scope local private-tools
```

`local` is the default mutation scope. Existing names require `--replace`.
Writes preserve unrelated `~/.claude.json` state and file modes, validate the
new server before mutation, reject symbolic-link paths, and atomically replace
the selected configuration file. The commands run without initializing a model
client, and list/detail output shows environment and header names but not their
values.

The `type` field defaults to `stdio` for compatibility. HTTP servers default to
protocol version `2026-07-28`; set `"protocolVersion": "2025-11-25"` only for a
legacy Streamable HTTP server that requires initialization and session headers.
The same-name scope precedence is local, project, user, then plugin. Commands,
arguments, server environment values, HTTP URLs, and HTTP headers support
`${ENV_NAME}` and `${ENV_NAME:-default}` expansion; a missing variable without
a default invalidates the configuration without exposing a value. Stdio
processes receive `CLAUDE_PROJECT_DIR` for the active project. Redirects are not
followed, response bodies are bounded, and server listings expose only a
query-free endpoint and header names, never header values.

`mcp_servers` reads configuration metadata without starting a process or
opening a connection. `mcp_tools` connects after approval and performs the
transport-appropriate protocol flow plus `tools/list`.
`mcp_call` requires separate approval for every invocation, verifies that the
tool was advertised, sends bounded JSON arguments, enforces per-request
timeouts and output limits, and closes the transport afterward. HTTP responses
may use JSON or request-scoped SSE, and modern tool parameter `x-mcp-header`
annotations are validated and mirrored. Stdio server commands still pass
VibeAgent's hard command-safety checks.
Claude-style model tool names such as `mcp__docs__search` are normalized to
the same `mcp_call` path with the tool input preserved as MCP arguments.
One-shot runs can add extra MCP configuration files with repeated
`--mcp-config PATH` arguments. Relative paths are resolved from `--cwd` or the
current project directory. Extra files cannot redefine an implicitly scoped
server, and each server `cwd` still has to resolve inside the project. Use
`--strict-mcp-config` to ignore user, local, project, and plugin MCP sources and
load only the explicit `--mcp-config` files for that one-shot run.

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
commands such as `!`, `/help`, `/model`, `/config`, `/tools`, `/tool`, `/tool-search`, `/permissions`, `/sandbox`, `/checks`, `/check-suggested-checks`, `/run-suggested-checks`, `/commands`, `/related-tests`, `/focused-tests`, `/check-focused-tests`, `/run-focused-tests`, `/manifests`, `/instructions`, `/todos`, `/command`, `/run`, `/check-run-seq`, `/run-seq`, `/check-start`, `/start`, `/port`, `/http`, `/http-fetch`, `/overview`, `/repo-map`, `/search`, `/search-contexts`, `/find-files`, `/glob`, `/tree`, `/symbols`, `/file-info`, `/image-info`, `/read`, `/around`, `/around-many`, `/output-contexts`, `/output-diagnostics`, `/python-traceback`, `/tail`, `/read-files`, `/read-ranges`, `/python-check`, `/python-deps`, `/python-defs`, `/python-refs`, `/python-ref-contexts`, `/python-calls`, `/python-call-graph`, `/python-rename-preview`, `/python-rename`, `/check-replace-python-def`, `/replace-python-def`, `/config-check`, `/check-json-set`, `/json-set`, `/check-json-remove`, `/json-remove`, `/check-json-patch`, `/json-patch`, `/check-replace-lines`, `/replace-lines`, `/check-insert-lines`, `/insert-lines`, `/check-append`, `/append`, `/check-write`, `/write`, `/check-write-files`, `/write-files`, `/check-edit`, `/edit`, `/check-multi-edit`, `/multi-edit`, `/check-delete`, `/delete`, `/check-delete-files`, `/delete-files`, `/check-move`, `/move`, `/check-move-files`, `/move-files`, `/check-copy`, `/copy`, `/check-copy-files`, `/copy-files`, `/check-move-dir`, `/move-dir`, `/check-move-dirs`, `/move-dirs`, `/check-copy-dir`, `/copy-dir`, `/check-copy-dirs`, `/copy-dirs`, `/check-mkdir`, `/mkdir`, `/check-mkdirs`, `/mkdirs`, `/check-rmdir`, `/rmdir`, `/check-rmdirs`, `/check-executable`, `/set-executable`, `/check-patch`, `/patch`, `/check-patches`, `/patches`, `/check-regex-replace`, `/regex-replace`, `/code-deps`, `/code-refs`, `/code-ref-contexts`, `/code-defs`, `/code-rename-preview`, `/code-rename`, `/git-status`, `/conflicts`, `/git-info`, `/branches`, `/log`, `/show`, `/blame`, `/stashes`, `/check-fetch`, `/fetch`, `/check-pull`, `/pull`, `/check-push`, `/push`, `/check-stash`, `/stash`, `/check-stash-apply`, `/stash-apply`, `/check-stash-drop`, `/stash-drop`, `/check-stage`, `/stage`, `/check-unstage`, `/unstage`, `/check-commit`, `/commit`, `/check-restore`, `/restore`, `/check-switch`, `/switch`, `/env`, `/processes`, `/process`, `/process-output-contexts`, `/process-output-diagnostics`, `/wait-process`, `/check-write-process`, `/write-process`, `/check-stop-process`, `/stop-process`, `/check-stop-processes`, `/check-stop-all-processes`, `/stop-processes`, `/stop-all-processes`, `/status`, `/context`, `/init`, `/doctor`, `/review`, `/handoff`, `/changes`, `/diff`, `/diff-hunks`, `/diff-contexts`, `/clear`, `/usage`, `/cost`, `/approval`, `/plan`, `/transcript`, `/rename`, `/export`, `/session-search`, `/session-commands`, `/session-output-contexts`, `/session-output-diagnostics`, `/session-files`, `/session-failures`, `/session-verification`, `/run-session-verification`, `/session-audit`, `/session-handoff`, `/checkpoint`, `/checkpoints`, `/checkpoint-show`, `/checkpoint-diff`, `/checkpoint-status`, `/check-checkpoint-restore`, `/checkpoint-restore`, `/check-checkpoint-delete`, `/checkpoint-delete`, `/check-checkpoint-prune`, `/checkpoint-prune`, `/resume`,
  `/compact`, `/bg`, `/background`, `/branch`, `/add-dir`, `/cd`, `/goal`, `/effort`, `/btw`, `/recap`, `/chat`, `/code`, and
  `/exit`, then delegates input to the selected mode.
  `/custom-commands` lists prompt templates from personal
  `~/.claude/commands/**/*.md` and project `.claude/commands/**/*.md` or
  `.agents/commands/**/*.md`. Built-in commands take precedence; personal
  commands override project commands, and nested template paths use colon names
  such as `/review:security`. Templates expand
  `$ARGUMENTS`, `$1`-`$9`, and `${1}`-`${9}` into a normal coding task, so any
  resulting model actions still use the current approval policy. Optional
  frontmatter fields `description` and `argument-hint` populate the command
  catalog without exposing template bodies. `/agents` and `/skills` list
  personal, project, and plugin metadata; profile prompts and skill bodies are
  loaded only when selected or invoked.
- `vibeagent/interactive_shell.py`: runs provider-free `!` commands through the
  standard bounded command executor, records redacted `Bash` tool events in the
  active session, and formats direct terminal output.
- `vibeagent/cli_interactive_project_runtime.py`: owns project-scoped peer,
  plugin-update, workflow, monitor, async-hook, and optional LSP cleanup for the
  interactive loop. It provides one idempotent shutdown boundary for exit and
  `/cd` project transitions.
- `vibeagent/background_agent_types.py`,
  `vibeagent/background_agent_store.py`, and
  `vibeagent/background_agent_config.py`: define detached coding-session
  records and validate their private project-local registry, continuation
  config, logs, exit markers, process identity, and bounded status views.
- `vibeagent/background_agent_inbox.py` and
  `vibeagent/background_agent_lock.py`: provide ordered atomic follow-up
  messages and serialize worker exit against concurrent send/respawn requests.
- `vibeagent/background_agent_attachment.py`,
  `vibeagent/background_agent_attach.py`, and
  `vibeagent/cli_background_agent_attach.py`: persist process-bound foreground
  leases, coordinate safe worker handoff at a turn boundary, and resume the
  recorded session/worktree through the normal interactive CLI.
- `vibeagent/agent_view_render.py`, `vibeagent/agent_view_terminal.py`,
  `vibeagent/agent_view_backend.py`, `vibeagent/agent_view.py`, and
  `vibeagent/cli_agent_view.py`: implement the
  dependency-free full-screen project dashboard, responsive bounded layout,
  Unix/Windows key input, approval/question responses,
  dispatch/reply/lifecycle actions, and attach handoff.
- `vibeagent/background_agent_approval.py` and
  `vibeagent/background_agent_input.py`: persist exact private blocking
  interactions so a detached worker can safely resume its original tool call
  after Agent View supplies a permission decision or validated user answer.
- `vibeagent/remote_control_server.py`, `vibeagent/remote_control_assets.py`, and
  `vibeagent/cli_remote_control.py`: expose the same project-local background
  supervisor through a token-authenticated, no-cache browser API and responsive
  control surface; non-loopback listeners require caller-supplied TLS.
- `vibeagent/background_agent_runtime.py` and
  `vibeagent/background_agent_worker.py`: launch or respawn a detached copy of
  the normal one-shot CLI, consume private payloads, continue the same session
  for queued turns, record completion, and implement the management lifecycle
  without duplicating the coding loop.
- `vibeagent/btw.py`: renders a bounded read-only view of the current coding or
  chat conversation, omits binary payloads, and asks one provider question
  without tools or any history/session persistence.
- `vibeagent/session_recap.py`: owns bounded manual and idle conversation
  summaries, per-mode turn and cooldown state, and isolated automatic provider
  calls that never mutate or persist the main conversation.
- `vibeagent/cli_interactive_model.py`,
  `vibeagent/cli_interactive_effort.py`, and
  `vibeagent/cli_interactive_provider_commands.py`: validate session-only model
  and effort overrides, map them to provider capabilities, and keep model/effort/BTW/recap
  provider command execution out of the main interactive loop.
- `vibeagent/agent.py`: orchestrates the ReAct loop. It creates a run
  session, builds model prompts, executes optional tool calls, records events,
  tracks the model's latest task plan, and stops on a plain text answer, a
  `finish` tool call, or the iteration limit. When the model emits several
  explicitly read-only tool calls in one turn, the agent can execute that batch
  concurrently while preserving result order; write, approval-gated, planning,
  user-input, and finish actions stay sequential. The `ask_user` tool can pause
  an interactive coding run for one blocking clarification. Its
  `AskUserQuestion` alias also accepts one to four structured questions with
  short headers, described options, and single- or multi-select answers. The
  answers return to the model in one tool result. JSON output and library runs without a
  user-input handler never read stdin; they return an unavailable-input result
  so the model can surface the unresolved question without guessing. Unexpected tool implementation exceptions
  are converted into `tool_error` observations so the model can recover instead
  of crashing the agent process. Provider request failures are retried according
  to `model_retries`, waiting `model_retry_delay_ms` between attempts. Each
  main-agent and subagent loop also recognizes provider context-limit errors,
  force-compacts accumulated observations, and retries once when compaction
  actually reduces the message history without consuming the normal retry budget.
  Between model turns, histories above 96,000 serialized characters compact
  proactively even when the message-count threshold has not been reached; any
  pending image tool exchange is retained intact until the model consumes it.
  Each request is bounded by `model_timeout_ms`, each failed attempt is recorded as a
  `model_error` event, and unrecovered failures also produce a failed `result`
  event so interrupted sessions remain auditable and resumable. Every run
  records a final `result` session event with
  success/failure, message, iteration count, plan, and tool-step counts for later
  resume and audit. Provider requests start with a compact set of high-frequency
  tool schemas instead of the full catalog; `tool_search`/`ToolSearch` matches and any
  directly called compatible tools are activated for later model turns and
  recorded as session events. Local `/tools`, `/tool`, and `/tool-search`
  commands continue to inspect the complete catalog.
- `vibeagent/agent_delegate.py` and `vibeagent/agent_delegate_loop.py`: prepare
  bounded repository investigations or approval-gated implementation tasks,
  then run their isolated model/tool iteration state. Explore mode exposes only
  the established parallel-safe inspection tools plus `finish`. Code mode
  reuses progressive tool loading, parent approvals, workspace safety, and
  automatic checkpoints while excluding user input, parent-plan/todo updates,
  and recursive delegation. Code-mode steps and observations feed the parent
  completion audit, and both modes record the child lifecycle before returning
  a structured summary.
- `vibeagent/mcp_user_config.py`, `vibeagent/mcp_config_sources.py`,
  `vibeagent/mcp_scope_store.py`, `vibeagent/mcp_command_parsing.py`,
  `vibeagent/mcp_commands.py`, `vibeagent/mcp_config.py`,
  `vibeagent/mcp_stdio.py`, and `vibeagent/mcp_action_executor.py`: load bounded
  user/local/project/plugin MCP scopes with deterministic precedence, manage
  them through atomic provider-free commands, validate transport and environment
  expansion, run newline-delimited JSON-RPC stdio sessions, and expose approved
  tool discovery and calls without leaving MCP subprocesses running.
- `vibeagent/workspace_settings_sources.py`, `vibeagent/workspace_hooks.py`,
  `vibeagent/agent_hook_execution.py`, `vibeagent/agent_hooks.py`, and
  `vibeagent/agent_lifecycle_runtime.py`: load bounded personal and project hook
  configuration, match tool and session lifecycle events, deliver JSON stdin,
  request approval for command hooks, preserve command hard blocks, inject
  bounded lifecycle context, and emit auditable hook results.
- `vibeagent/workspace_permissions.py` and `vibeagent/agent_permissions.py`:
  load bounded personal and project permission rules, match Claude-compatible
  tool/path/command patterns, trust user rules while requiring explicit project
  trust for project allow rules, and centralize deny/ask/allow decisions across
  the main agent, hooks, and subagents.
- `vibeagent/project_trust.py` and `vibeagent/trust_commands.py`: maintain the
  user-owned persistent project-permission trust registry, expose trust/status/
  untrust commands, and keep repository-controlled allow rules inert until the
  user explicitly trusts them.
- `vibeagent/session_approval.py`: caches only user-selected, exact
  action-type-and-target approvals for the current CLI session, marks cache
  hits for audit, and keeps MCP process/tool calls outside the cache.
- `vibeagent/workspace_sandbox.py`, `vibeagent/command_sandbox.py`, and
  `vibeagent/sandbox_commands.py`: load bounded personal and project sandbox
  settings, validate source-aware trusted expansion paths and user security
  floors, diagnose Bubblewrap/network namespace support, and build one
  filesystem/network-isolated launcher for finite and background shell
  commands, including strict per-command auto-approval qualification.
- `vibeagent/workspace_environment.py` and `vibeagent/plugin_environment.py`:
  resolve bounded source-aware settings variables and enabled plugin `bin/`
  paths into per-process environments without mutating the host process.
- `vibeagent/plugin_user_config_schema.py` and
  `vibeagent/plugin_user_config.py`, plus
  `vibeagent/plugin_user_config_store.py`: validate typed manifest options,
  resolve project/local/environment precedence, atomically store shared and
  sensitive values, redact status output, and provide component-scoped
  substitutions and subprocess environments.
- `vibeagent/plugin_monitor_config.py`, `vibeagent/plugin_monitor_process.py`,
  `vibeagent/plugin_monitor_runtime.py`, and
  `vibeagent/agent_plugin_monitors.py`: validate plugin monitor declarations,
  own bounded stdout/stderr process I/O, enforce approved startup and cleanup,
  trigger skill-scoped monitors, and inject untrusted notifications into agent
  turns.
- `vibeagent/chat.py`: builds plain daily conversation prompts and keeps the
  model out of the coding-agent JSON action protocol.
- `vibeagent/cli_model_stream.py`: renders provider text deltas for interactive
  code/chat turns while hiding protocol, thinking, and tool-input events.
- `vibeagent/providers.py`: selects the configured model provider. MiniMax is
  the default; Anthropic uses the native Messages adapter, while DeepSeek and
  other OpenAI-compatible APIs use the OpenAI-compatible adapter.
- `vibeagent/anthropic.py`: native Anthropic Messages API client. It maps the
  provider-neutral conversation and tool contract to Claude message blocks.
- `vibeagent/prompts.py`: owns the system prompt and user message construction.
  Each prompt includes the original task, optional resumed session context,
  scoped `AGENTS.md`/`CLAUDE.md` instructions, discovered project command hints with
  command `cwd` and executable availability, current run directory, workspace file snapshot, and previous observations.
- `vibeagent/prompt_file_mentions.py`: resolves bounded `@path` text and image
  references inside the active workspace, builds provider-neutral prompt blocks,
  and emits content-free session metadata.
- `vibeagent/prompt_file_mention_parsing.py`: recognizes unquoted and quoted
  prompt mentions, canonicalizes optional Claude-style line selectors, dedupes
  structured references, and enforces count and range limits before file I/O.
- `vibeagent/cli_completion.py`: provides bounded terminal-native `@path` and
  slash-command completion, filters candidates through workspace ignore and
  sensitive-path policy, and restores process readline state after each prompt.
- `vibeagent/agent_tool_registry.py`: defines the compact always-available tool
  set, preserves the canonical catalog order, and activates complete schemas
  returned by `tool_search` without changing parser or approval behavior.
- `vibeagent/minimax.py`: MiniMax API client. It reads API configuration from
  environment variables, converts VibeAgent's generic tool blocks to Anthropic-compatible
  MiniMax messages, and normalizes responses back into generic tool blocks.
- `vibeagent/openai_compat.py`: OpenAI-compatible client used by DeepSeek-style
  chat completions APIs. It maps generic tool blocks to `tool_calls` and `role: tool` messages.
- `vibeagent/actions.py`: defines the coding tools, validates tool inputs into
  typed actions, and executes them. Supported actions include `list_files`,
  `list_tree`, `repo_map`, line-range `read_file`, line-centered `read_file_context`, batch line-centered `read_file_contexts`, output-derived `output_contexts`, diagnostic `output_diagnostics`, Python-focused `python_traceback`, tail-focused `tail_file`, batch `read_files`, batch line-range `read_file_ranges`, `file_info`, `image_info`, `view_image`, `python_symbols`, `code_outline`, `lsp_query` (Claude-compatible `LSP` alias), `python_check`, `config_check`, `check_json_set`, `json_set`, `check_json_remove`, `json_remove`, `check_json_patch`, `json_patch`, `python_dependencies`, `code_dependencies`, `code_references`, `code_reference_contexts`, `code_definitions`, `code_rename_preview`, `code_rename`, `python_definitions`, `python_calls`, `python_call_graph`, `python_references`, `python_reference_contexts`, `python_rename_preview`, `python_rename`, path-fragment `find_files`, path-pattern `glob`, scoped/regex/context `search`, `tool_search`, Claude-compatible `EnterWorktree`/`ExitWorktree`, `git_info`, `git_status`, `git_conflicts`, `git_changes`, `git_branches`, `git_stashes`, `check_git_fetch`, `git_fetch`, `check_git_pull`, `git_pull`, `check_git_push`, `git_push`, `check_git_restore`, `git_restore`, `check_git_stash`, `git_stash`, `check_git_stash_apply`, `git_stash_apply`, `check_git_stash_drop`, `git_stash_drop`, `check_git_switch`, `git_switch`, `check_git_stage`, `git_stage`, `check_git_unstage`, `git_unstage`, `check_git_commit`, `git_commit`, `review_changes`, `final_review`, `suggest_checks`, `check_suggested_checks`, `run_suggested_checks`, `project_commands`, `related_tests`, `focused_test_commands`, `project_manifests`, `project_instructions`, `project_skills`, `skill`, `project_todos`, `project_overview`, `command_check`, `check_run_commands`, `run_commands`, `port_check`, `http_check`, `http_fetch`, `environment_info`, `git_diff`, `git_diff_hunks`, `git_diff_contexts`, `git_log`, `git_show`, `git_blame`, `session_summary`, `session_plan`, `session_transcript`, `session_search`, `session_commands`, `session_output_contexts`, `session_output_diagnostics`, `session_files`, `session_failures`, `session_verification`, `run_session_verification`, `session_audit`, `session_handoff`, `check_edit_file`, `edit_file`,
  `web_fetch`, `web_search`, `mcp_resources`, `mcp_read_resource`, `checkpoint_create`, `checkpoint_list`, `checkpoint_show`, `checkpoint_diff`, `checkpoint_status`, `check_checkpoint_restore`, `checkpoint_restore`, `check_checkpoint_delete`, `checkpoint_delete`, `check_checkpoint_prune`, `checkpoint_prune`, `check_multi_edit_file`, `multi_edit_file`, `check_replace_python_definition`, `replace_python_definition`, `check_replace_lines`, `check_insert_lines`, `check_append_file`, `check_regex_replace`, `regex_replace`, `replace_lines`, `insert_lines`, `append_file`, `check_patch`, `check_patches`, `patch_file`, `patch_files`, `check_write_file`, `write_file`, `check_write_files`, `write_files`, `check_delete_file`, `delete_file`, `check_delete_files`, `delete_files`, `check_move_file`, `move_file`, `check_move_files`, `move_files`, `check_copy_file`, `copy_file`, `check_copy_files`, `copy_files`, `check_move_dir`, `move_dir`, `check_move_dirs`, `move_dirs`, `check_copy_dir`, `copy_dir`, `check_copy_dirs`, `copy_dirs`, `check_create_dir`, `create_dir`, `check_create_dirs`, `create_dirs`, `check_delete_empty_dir`, `delete_empty_dir`, `check_delete_empty_dirs`, `delete_empty_dirs`, `check_set_executable`, `set_executable`,
  `run_command`, `check_start_command`, `start_command`, Claude-compatible `Monitor`, `list_processes`, `read_process`, `process_output_contexts`, `process_output_diagnostics`, `wait_process`, `check_write_process`, `write_process`,
  `check_stop_all_processes`, `check_stop_process`, `stop_all_processes`, `stop_process`, `delegate_task`, Claude-compatible `ListAgents`, `TaskCreate`, `TaskGet`, `TaskList`, `TaskUpdate`, `CronCreate`, `CronList`, `CronDelete`, `TaskOutput`, and `TaskStop`, `ask_user`, `update_plan`, `todo_write`, `todo_read`, and `finish`.
- `vibeagent/action_parsing_browser.py`, `vibeagent/browser_runtime.py`, and
  `vibeagent/tool_definition_browser.py`: expose optional approved browser
  navigation, accessibility snapshots, bounded interactions and reads,
  console/error inspection, atomic workspace screenshots, and cleanup through
  an isolated `agent-browser` session without accepting arbitrary CLI options.
- `extensions/vscode/` and `scripts/build_vscode_extension.py`: provide a
  dependency-free VS Code extension for background-agent supervision, exact-ID
  approvals, worktree change review, bounded history lookup, exact-ID resume, persistent task graph inspection,
  parallel terminal management, selected-file references, bounded diagnostic
  handoff, and native Git diff review, plus a deterministic allowlisted VSIX build.
- `vibeagent/background_agent_changes.py`: validates recorded Git worktrees and
  provides bounded, sensitive-path-aware base/current text for Agent Panel
  change review without mutating either checkout.
- `vibeagent/background_agent_integration.py`: applies one exact reviewed
  terminal-agent snapshot to non-conflicting main-worktree paths with bounded
  binary reads, atomic writes, executable-bit preservation, and rollback.
- `vibeagent/ide_context.py`: authenticates, bounds, sanitizes, and formats the
  private VS Code live-context protocol without exposing bridge credentials to
  child project processes.
- `vibeagent/session_tasks.py`, `vibeagent/session_task_store.py`, `vibeagent/session_task_commands.py`, and
  `vibeagent/session_task_graph.py`: manage the session-scoped structured task
  graph, atomic persistence, resume inheritance, dependency invariants, and bounded provider-free inspection.
- `vibeagent/cron_expression.py`, `vibeagent/scheduled_task_store.py`, and
  `vibeagent/scheduled_task_persistence.py`: validate cron expressions, apply
  local-time scheduling and deterministic jitter, atomically persist schedules,
  collect due prompts without catch-up storms, and restore unexpired tasks.
- `vibeagent/goal_state.py`, `vibeagent/goal_evaluator.py`, and
  `vibeagent/goal_loop.py`: persist one session completion goal, evaluate bounded
  evidence without tools, and construct evaluator-guided continuation turns.
- `vibeagent/peer_registry.py`, `vibeagent/peer_protocol.py`, and
  `vibeagent/peer_runtime.py`: register live same-machine sessions, validate and
  deliver bounded Unix-socket messages, enforce inbound controls, and clean up
  per-process inbox state.
- `vibeagent/workspace_memory.py`: manages bounded auto-memory loading and
  approved atomic Markdown writes for the main agent and isolated named-agent
  stores with path, symlink-component, size, and credential-redaction guards.
- `vibeagent/workspace_agents.py` and
  `vibeagent/workspace_agent_profile_parser.py`: discover project agent files
  separately from pure frontmatter parsing and execution-control validation.
- `vibeagent/workspace_instruction_state.py` and
  `vibeagent/agent_instruction_context.py`: atomically track path-scoped
  instruction sources per main-agent or subagent consumer, migrate legacy
  session state, and allow rules to reload after context compaction.
- `vibeagent/workspace.py`: treats the current directory as the project root,
  creates `.vibeagent/sessions/<session-id>/`, resolves relative file paths,
  rejects path escapes, protects `.git/` and `.vibeagent/`, rejects symlink
  runtime session roots, and builds project file snapshots for prompts.
- `vibeagent/types.py`: shared dataclasses and protocols for chat messages,
  actions, command results, observations, and agent status.

The model contract is deliberately narrow and provider-neutral inside VibeAgent:
coding mode accepts plain text responses and uses generic `tool_call` and
`tool_result` blocks only when tools are needed. Provider adapters translate
those blocks to MiniMax Anthropic-compatible messages or OpenAI-compatible
`tool_calls`. Chat mode remains plain text and does not receive tools.

## v1 Boundaries

- Files are read and written only inside the current project directory.
- Command working directories may be project-relative or absolute paths that
  resolve inside the current project; absolute paths outside the project and
  protected `.git/` or `.vibeagent/` directories remain blocked.
- `.git/` and `.vibeagent/` are protected from model file actions.
- Secret-like files such as `.env`, `.env.local`, `.npmrc`, `.pypirc`,
  private keys, certificates, and common key bundles are protected from model
  file actions and omitted from project scans.
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
- `image_info` inspects PNG, JPEG, GIF, and WebP image headers for format, size,
  and dimensions without exposing full binary file contents.
- `view_image` sends one recognized project image to a vision-capable model with
  a 5 MB hard limit. Session events retain only metadata, and the encoded image
  is removed from model history immediately after the first consuming turn.
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
  shallow repo map, git identity/status, manifests, project commands, project
  skill metadata, suggested checks, and runtime tool availability.
- `deep_review` runs independent read-only correctness, security, and test-risk
  reviewers in parallel over the current changes or an explicit base ref. Each
  reviewer inspects surrounding code, requires evidence at real file and line
  locations, and follows bounded root `REVIEW.md` guidance. A final read-only
  verifier checks candidates against the code, removes false positives and
  duplicates, and ranks the surviving findings. One failed reviewer is reported
  without discarding the other reports.
  Interactive and print-mode `/code-review [low|medium|high|xhigh|max]
  [--fix] [target]` expose the workflow directly. Targets can select a local
  file, branch, ref range, or short review scope; review is read-only unless
  `--fix` is explicit. Unsupported cloud `ultra` and GitHub `--comment` modes
  fail before any model request or external write.
  `/simplify [target]` reuses the verified parallel review engine with four
  cleanup-only agents for existing-helper reuse, simplicity, concrete
  efficiency, and abstraction placement. It excludes correctness bugs and
  pre-existing/style-only findings, applies only justified behavior-preserving
  fixes, and then requires focused verification plus `final_review`. Targets
  currently resolve against the local checkout rather than a GitHub PR.
  `/security-review` performs a separate read-only branch review against the
  cached `origin/HEAD` ref. Four parallel agents cover access control,
  injection/execution, sensitive-data exposure, and supply-chain/configuration
  risks; the verifier retains only branch-introduced findings with a concrete
  attacker capability, reachable exploit path, affected asset, and impact.
  Findings use `CRITICAL`, `HIGH`, `MEDIUM`, or `LOW` severity. The command
  fails when the Git/origin/default-ref preflight is unavailable, never fetches
  implicitly, and does not edit or apply fixes.
  `/verify [goal]` turns the requested behavior or current changes into
  observable acceptance criteria, builds the project, runs the real CLI or
  service entry point, and records command, process, port, HTTP, and log
  evidence. UI criteria use `tool_search` to discover the optional native
  `browser_*` tools or a browser-capable project skill/MCP tool; HTTP success
  alone is reported separately and never presented as visual or interaction
  proof. The workflow stops only processes it started and reports
  each criterion as `PASS`, `FAIL`, or `UNVERIFIED`.
  `/run-skill-generator [app]` first proves a selected app's build, launch,
  readiness, driven behavior, observation, and cleanup steps, then records the
  evidence-backed recipe in `.claude/skills/run-<name>/SKILL.md`. It refuses to
  guess between ambiguous apps in print mode, does not persist secrets or
  machine-specific paths, preserves still-valid existing recipe steps, and
  reloads the generated skill through `project_skills` and `skill` before
  reporting success. Monorepo packages can keep recipes under
  `<package>/.claude/skills/` and load them through a directory-qualified name
  such as `apps/web:run-web`. Later `/verify` runs prefer the most specific matching
  `verify` or `run-*` project skill instead of rediscovering launch commands.
- `final_review` is a read-only handoff bundle for non-trivial code changes:
  blocking issues, warnings, running background processes, changed files, and
  suggested verification commands plus focused test commands inferred from
  changed files. It blocks incomplete changed-file reviews,
  incomplete Python or config syntax checks, unresolved merge conflicts,
  incomplete or failed merge-conflict scans, and changed files larger than
  100 MiB before the agent reports completion. It
  also blocks high-confidence secret-like values in changed files, files changed
  by the current session even when git ignores them, or added diff lines without
  echoing the matched secret text, incomplete secret-like value scans, nested git
  repositories left inside the project tree, changed git
  submodule links, tracked changes hidden by project safety filters, changed
  symlinks pointing outside the project or into protected or ignored project
  paths, in-progress git operations such as merge, rebase, cherry-pick, or
  revert, and incomplete safety scans for secret-like diff additions, git
  submodule links, hidden tracked changes, changed symlinks, or git operation
  state, and suggested verification checks whose executables are missing. It
  also reports cached upstream ahead/behind state as a warning without fetching
  from the network.
- `checkpoint_create` writes checkpoint metadata, patch snapshots, and ordinary
  saved untracked files under `.vibeagent/checkpoints/`; model tools can list
  checkpoints, inspect metadata and saved patch text, compare current status,
  preview restore compatibility, and restore tracked staged/unstaged changes
  plus saved untracked file contents after approval when compatibility checks
  pass. Runs also create one best-effort checkpoint automatically before the
  first approved project-changing tool when the workspace has a git HEAD.
  Restore refuses checkpoints whose untracked files were not fully saved,
  refuses worktrees with extra current untracked files, and checkpoint
  untracked-file save, status comparison, and restore refuse symlink paths or
  parents. Checkpoint patch and untracked-manifest reads ignore symlink files.
  Checkpoint create/list/read/delete/prune refuse a symlink `.vibeagent` or
  `.vibeagent/checkpoints` root. Checkpoint listing, delete, and prune only
  accept regular checkpoint directories whose metadata id matches the directory
  name; symlink checkpoints are ignored or refused. `check_checkpoint_delete`
  previews whether one saved checkpoint snapshot can be removed;
  `checkpoint_delete` can remove it after approval, and `checkpoint_prune` can
  remove older checkpoint snapshots after previewing with `check_checkpoint_prune`.
- `session_summary`, `session_plan`, `todo_read`, `session_transcript`, `session_search`, `session_commands`, `session_output_contexts`, `session_output_diagnostics`, `session_files`, `session_failures`, `session_verification`, `run_session_verification`, `session_audit`, and `session_handoff` let the model
  inspect compact session state, the latest task checklist, a safe event
  timeline, targeted timeline matches, bounded command output tails, command-output file:line contexts, command-output diagnostics, referenced path summaries, verification status, structured pending/failed verification commands, approved reruns of recorded verification commands, checkpoint recovery points, finish-readiness blockers, failure summaries, and compact recovery handoff bundles without exposing complete tool payloads.
- `github_pr_context` uses the authenticated `gh` CLI after explicit approval
  to read the current or selected GitHub pull request. It returns bounded PR
  metadata, discussion and inline review comments, latest reviews, changed
  files, and CI status so the agent can verify and address PR feedback locally.
  Repository selection is derived from a local GitHub remote, selectors reject
  option injection, and each GitHub JSON response is capped at 2 MB.
- `github_pr_ci_logs` continues that workflow by reading failed PR checks and
  bounded `gh run view --log-failed` output for matching GitHub Actions runs.
  It deduplicates runs, preserves third-party failed-check metadata without
  inventing logs, rejects cross-repository run links, redacts common credential
  patterns, and limits run count and returned characters before model use.
  GitHub fields and logs are marked as untrusted external evidence in the model
  prompt and cannot override user, system, approval, or project instructions.
- `check_github_pr_comment` locally validates an exact discussion comment or
  inline review reply; `github_pr_comment` publishes it only after matching
  preview and explicit approval. Inline comment IDs come from
  `github_pr_context`. The approval warns that GitHub comments create
  notifications and may trigger repository comment-driven automation.
- `github_issue_context` reads one numbered issue or same-repository GitHub
  issue URL through `gh`, returning bounded title, body, status, labels,
  assignees, milestone, and comments. It requires approval, rejects
  cross-repository issue URLs, and marks all returned issue text as untrusted
  external evidence before model use.
- `check_github_issue_comment` validates the exact issue, remote, and Markdown
  body locally; `github_issue_comment` publishes only after a matching preview
  and explicit approval. It passes the body as one `gh` argument, rejects
  cross-repository issue URLs before execution, and warns that comments can
  notify users or trigger issue-comment workflows.
- `file_info`, `image_info`, `view_image`, `read_file_context`, `read_file_contexts`, `output_contexts`, `output_diagnostics`, `python_traceback`, `tail_file`, `python_dependencies`, `code_dependencies`, `code_references`, `code_reference_contexts`, `code_definitions`, `code_rename_preview`, `python_references`, `python_reference_contexts`, `find_files`, `tool_search`, `session_summary`, `session_plan`, `todo_read`, `session_transcript`, `session_search`, `session_commands`, `session_output_contexts`, `session_output_diagnostics`, `session_files`, `session_failures`, `session_verification`, `session_audit`, `session_handoff`, `checkpoint_list`, `checkpoint_show`, `checkpoint_diff`, `checkpoint_status`, `check_checkpoint_restore`, `check_checkpoint_delete`, `check_checkpoint_prune`, `check_write_file`, `check_write_files`, `check_edit_file`, `check_multi_edit_file`, `check_replace_python_definition`, `check_replace_lines`, `check_insert_lines`, `check_append_file`, `check_delete_file`, `check_delete_files`, `check_move_file`, `check_move_files`, `check_copy_file`, `check_copy_files`, `check_move_dir`, `check_move_dirs`, `check_copy_dir`, `check_copy_dirs`, `check_create_dir`, `check_create_dirs`, `check_delete_empty_dir`, `check_delete_empty_dirs`, `check_set_executable`, `check_git_fetch`, `check_git_pull`, `check_git_push`, `check_git_restore`, `check_git_stash`, `check_git_stash_apply`, `check_git_stash_drop`, `check_git_switch`, `check_git_stage`, `check_git_unstage`, `check_git_commit`, `check_regex_replace`, `check_json_set`, `check_json_remove`, `check_json_patch`, `git_info`, `git_status`, `git_conflicts`, `git_changes`, `git_branches`, `git_stashes`, `review_changes`, `final_review`, `suggest_checks`, `check_suggested_checks`, `project_commands`, `related_tests`, `focused_test_commands`, `project_manifests`, `project_instructions`, `project_todos`, `project_overview`, `command_check`, `check_run_commands`, `port_check`, `http_check`, `http_fetch`, `check_start_command`, `process_output_contexts`, `process_output_diagnostics`, `wait_process`, `check_write_process`, `check_stop_all_processes`, `check_stop_process`, `environment_info`,
  `git_diff`, `git_diff_hunks`, `git_diff_contexts`, `git_log`, `git_show`, and `git_blame` are read-only and do not require approval.
  `suggest_checks` marks each suggested command with whether its main executable is available on `PATH`; the local `/checks` command and `--checks` flag expose suggested-check bounds;
  `check_suggested_checks` preflights those discovered checks without running them, and `run_suggested_checks` runs available discovered checks after approval;
  `project_commands` lists project-defined npm, pyproject, and Makefile commands with cwd and executable availability; the local `/commands` command and `--commands` flag expose command/file bounds;
  `related_tests` suggests likely test files for explicit paths or the current git changes without running them; the local `/related-tests` command and `--related-tests` flag expose target/candidate bounds;
  `focused_test_commands` maps those related test files to likely focused commands without running them; the local focused-test commands and flags expose target/candidate/command bounds;
  `project_manifests` reads package and pyproject dependency/script metadata; the local `/manifests` command and `--manifests` flag expose manifest file/item bounds;
  `project_instructions` reports root and nested `AGENTS.md`, `CLAUDE.md`, `.claude/CLAUDE.md`, `CLAUDE.local.md`, and `.claude/rules/**/*.md` sources with scopes and bounded text; startup includes only root and unscoped rules, while matching nested and `paths`-scoped rules are injected once after file reads; Claude-compatible recursive `@path` imports stay project-contained, inherit entrypoint scope, and expose include/parent metadata; the local `/instructions` command and `--instructions` flag expose `--max-files`/`--max-bytes` and `--instructions-max-files`/`--instructions-max-bytes` bounds respectively;
  `project_skills` discovers bounded metadata from personal `~/.claude/skills/*/SKILL.md`, root project `.claude/skills/*/SKILL.md` and `.agents/skills/*/SKILL.md`, nested package `<scope>/.claude/skills/*/SKILL.md`, plus enabled plugins, while `skill`/`Skill` or `/skill-name` loads one exact available skill on demand and preserves optional invocation arguments for the next model step. Nested skills use directory-qualified names such as `apps/web:deploy`; a loaded root skill also lists available same-name nested variants. Personal skills override same-name project skills, plugin skills remain namespaced, skills override same-name legacy commands, and built-in commands retain highest priority; root and nested skill bodies are captured by ConfigChange-safe session snapshots, excluded from the initial project snapshot, and same-priority duplicates or symlinked skills are refused;
  agent profiles are discovered recursively from project `.claude/agents/` and `.agents/agents/`, user `~/.claude/agents/`, and enabled plugins. Project definitions override same-name user definitions, which override plugins; only bounded metadata enters the main prompt, while `--agent PROFILE`, scoped `agent` settings, or a plugin default setting loads one exact profile for the main coding loop and `delegate_task.agent` loads one for a subagent. Explicit CLI selection overrides `.claude/settings.local.json`, which overrides project `.claude/settings.json`, user `~/.claude/settings.json`, and then one enabled plugin default; plugin root `settings.json` overrides inline manifest `settings`. Safe structured YAML and dynamic JSON profiles enforce `mode`, `model`, `effort`, `tools`, `disallowedTools`, `permissionMode`, `maxTurns`, `skills`, `memory`, `background`, `isolation`, `color`, `initialPrompt`, and profile-scoped command `hooks` plus stdio/HTTP `mcpServers`. Sensitive profile bodies and executable definitions load only after exact selection. Forced background/color metadata survives nested, workflow, transcript, and task-list paths; main initial prompts are prepended only on the first turn. Parent strong permission modes and VibeAgent hard blocks remain ceilings, and untrusted project profiles cannot raise themselves to `acceptEdits` or `bypassPermissions`. Profiles can require `isolation: worktree` for subagents and preload up to 10 named personal, project, or plugin `skills` into the selected agent only (20 KB each, 100 KB total). Scoped model clients preserve the parent client; `inherit` keeps its model, Anthropic sends effort through `output_config.effort`, and providers without that Claude request field reject effort before requesting the model. Main profiles that request worktree isolation fail before the model call and must be paired with the session-level `--worktree` option instead. `memory: user` persists approved agent-specific notes under `~/.claude/agent-memory/<name>/`, `memory: project` uses `.claude/agent-memory/<name>/`, and `memory: local` uses `.claude/agent-memory-local/<name>/`; startup loads at most 200 lines or 25 KB and stateless agents cannot access another memory store. Plugin manifests may declare bounded typed `userConfig` options with defaults, required values, string arrays, numeric ranges, and sensitive storage; project/local/environment precedence, CLI mutation, required-value enable gates, model-visible secret refusal, and hook/MCP/LSP/monitor subprocess environments share one resolver. Tool fields accept native names or Claude-compatible aliases such as `Read` and `Write`; unavailable skills, invalid settings, ambiguous bare plugin names, conflicting plugin defaults, unsupported effort, and unconfigurable custom clients fail before any model request;
`delegate_task`/`Task` can run independent `explore` or `code` work in the background, returning a session-scoped task ID immediately; `-p --append-subagent-system-prompt` appends one invocation-only constraint to every direct, nested, and resumed subagent after profile and task-specific instructions without writing its text to session events; ask-mode tool approvals are routed through the parent handler. `isolation: "worktree"` creates and locks a dedicated Git worktree for a subagent, keeps its edits out of the parent checkout, removes it automatically when clean, and preserves changed worktrees with their branch/path metadata for explicit inspection and integration. Project agent profiles can require the same behavior with `isolation: worktree`. `ListAgents` lists current-session running and resumable instances by exact ID, status, mode, profile, run count, worktree metadata, and foreground/background origin; unlike local `/agents` and model `project_agents`, it does not list profile definitions. Completed results are injected once as structured notifications before a later parent model turn, while explicit `TaskOutput` polling suppresses duplicate delivery. `SendMessage` steers a running subagent or resumes a completed, failed, or `TaskStop`-cancelled subagent in the background under the same ID with its redacted full message history and freshly loaded profile/permission controls. `TaskStop` requests cooperative cancellation, missing task IDs report available session agents, the agent cannot finish successfully while a started task is still running or unread, and run teardown cancels and releases any remaining session tasks. Every foreground and background subagent report is scanned before it reaches the parent: system-like tags, role prefixes, and spoofed harness markers are escaped, permission-setting or instruction-override language receives a visible marker without rewriting the report, and match categories are recorded in `subagent_output_scanned` session events;
  Experimental in-process agent teams are enabled with `VIBEAGENT_EXPERIMENTAL_AGENT_TEAMS=1` (the Claude-compatible `CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1` is also accepted). `TeamCreate` atomically creates the one private session team, and `TeamDelete` removes it only after every named teammate has stopped; both tools are hidden from the initial catalog and `ToolSearch` while teams are disabled. The lead spawns a named teammate with `Agent` and its `name` field; legacy direct named spawns create a compatibility team automatically. Every spawn requires the normal approval flow and runs in the background under that stable session ID. Teammates have independent contexts, inherit the lead's permission handler, share the persistent `TaskCreate`/`TaskGet`/`TaskList`/`TaskUpdate` graph, automatically claim unowned work when moving it to `in_progress` or `completed`, cannot modify work owned by another teammate, and can send task direction to running peers by name or to `lead` with `SendMessage`. Lead-bound messages are injected automatically between turns as untrusted coordination input. Coordination tools remain available when a project agent profile restricts ordinary tools. Only the lead can manage teammates, teammate messages never grant approval, `ListAgents` exposes teammate identity, and normal session teardown cancels remaining teammates and clears team state and pending mail;
  `project_todos` scans project text files for TODO, FIXME, HACK, XXX, and BUG markers;
  `command_check` does the same preflight for one proposed finite command and also reports cwd and block-rule failures;
  `check_run_commands` preflights a short ordered command batch without running it;
  `port_check` checks whether a local TCP host and port are reachable without running shell commands;
  `http_check` checks local/private HTTP(S) status, final URL, and optional response content without running shell commands;
  `http_fetch` fetches bounded local/private HTTP(S) response metadata and body text without running shell commands;
  `web_fetch` fetches bounded readable text from public technical documents after approval, rejects URL credentials and non-public destinations, and revalidates redirects;
  `web_search`/`WebSearch` sends a bounded query to DuckDuckGo after approval, parses result titles, public URLs, and snippets, and supports local allow/block domain filtering before returning results;
  `browser_open`, `browser_snapshot`, `browser_act`, `browser_read`, `browser_screenshot`, and `browser_close` use an optional `agent-browser` executable for approved per-session UI verification. The exposed contract covers navigation, accessibility snapshots, bounded element interaction and reads, console/page errors, atomic workspace screenshots, and cleanup without exposing arbitrary CLI arguments, JavaScript evaluation, browser credentials, uploads, cookies, proxies, or interception. A private empty config and scrubbed process environment prevent repository or inherited browser configuration from widening the contract; approved hosts are DNS-checked and persisted as the session navigation allowlist;
  `mcp_resources`/`ListMcpResourcesTool` follows bounded pagination for concrete MCP resources and RFC 6570 URI templates, while `mcp_read_resource`/`ReadMcpResourceTool` reads only an exact advertised URI or an instance matching an advertised template. Servers that do not implement `resources/templates/list` may return JSON-RPC method-not-found without breaking concrete resource discovery. Resource text is redacted and truncated, binary blobs remain hidden behind metadata, and both operations retain VibeAgent's explicit MCP approval boundary for stdio and HTTP servers;
  `check_start_command` does the same for long-running commands without starting a process;
  `monitor`/`Monitor` starts either an approved background command or an explicitly approved public `ws://`/`wss://` connection. Command sources deliver each complete stdout line; WebSocket sources preserve each text message as one event even when it spans lines, replace binary frames with byte-count placeholders, reject credentials, whitespace, non-ASCII URLs, invalid/duplicate subprotocols, DNS results containing private/link-local/metadata addresses, and messages larger than 1 MiB, and report close codes. Events and final status reach the active agent as untrusted runtime evidence. The default timeout is 300,000 ms and the maximum is 3,600,000 ms; `persistent: true` runs until `TaskStop` or CLI session exit. Active agent turns receive events between model calls, and an idle interactive CLI starts a resumed turn when an event arrives;
  `wait_process` waits for a background process to exit, time out, or emit configured stdout/stderr text or regex without stopping it;
  `check_write_process` validates that a running background process can receive stdin text or project-file-backed stdin without writing input;
  `check_stop_all_processes` previews all tracked background processes without stopping them;
  `check_stop_process` validates a background process id without stopping it.
  Large `git_diff`, `git_show`, and `git_blame` outputs are bounded with truncation metadata.
- Commands run only from the current project directory.
- `run_command` is for one finite check. `run_commands` is for a short ordered
  finite verification sequence and runs commands sequentially, stopping on the
  first failure by default. `run_suggested_checks` discovers suggested
  verification commands and runs the available ones after approval, also
  stopping on the first failure by default. `start_command` is for long-running
  commands such as dev servers and watchers. Both accept an optional project-relative
  `cwd` for package or service subdirectories; `run_command`, `run_commands`, `run_focused_test_commands`, and `run_suggested_checks` accept
  optional per-command `timeout_ms` up to 10 minutes for slower tests or builds,
  and bounded stdout/stderr via `max_output_chars` so large logs do not flood
  the next model turn. When a foreground Bash or PowerShell stream is truncated,
  its complete UTF-8 output is saved as an owner-only artifact under the current
  session and the result includes `stdoutPath` or `stderrPath` plus the original
  byte count. The model can pass that exact path to `read_file`; guessed paths,
  artifacts from another session, symbolic links, and all other protected
  `.vibeagent` files remain unreadable. Short output creates no artifact, and an
  artifact-storage failure is reported separately without replacing the command's
  real exit result. Finite command reports include per-command `durationMs`,
  and batch command reports also include aggregate `durationMs`. Failed finite commands automatically attach diagnostic
  summaries and source context when stdout/stderr contains recognizable
  file:line references. `run_command`, `run_suggested_checks`, `run_focused_test_commands`, and each `run_commands` item can set
  `extract_output_diagnostics` to summarize successful noisy test/lint output into error,
  warning, failure, Python exception, and referenced-source sections, or `extract_output_contexts`
  to include current source context for file:line references found in stdout/stderr.
  Local `--run-command`, `--run-commands`, `--run-focused-tests`, `--run-suggested-checks`, and
  `--run-session-verification` can use
  `--run-output-diagnostics` or `--run-output-contexts` with bounded
  `--run-output-context-lines`, `--run-output-diagnostic-max`, `--run-output-context-max`, and
  `--run-output-context-max-bytes` for the same extraction. `--run-output-diagnostic-max`
  also controls the automatic diagnostics attached to failed run commands.
  Local `--run-session-verification` reruns failed and pending session checks
  with `--session-max-checks`, `--run-timeout-ms`, `--run-max-chars`,
  `--run-session-no-failed`, `--run-session-no-pending`, and
  `--run-continue-on-failure`.
  Direct output analysis commands expose the same bounded source-context controls through
  `/output-contexts`, `/output-diagnostics`, `/python-traceback`,
  `--output-context-max-bytes`, and `--output-diagnostic-context-max-bytes`.
  `list_processes` shows background command ids and status, `read_process`
  and `wait_process` return recent captured output with optional `max_output_chars`
  and preserve exit codes across separate CLI invocations for newly started processes,
  and automatically attach diagnostic summaries plus source context when a
  background process has exited or failed and stdout/stderr contains recognizable
  error lines,
  `process_output_contexts` extracts source snippets for file:line references in recent background stdout/stderr,
  `process_output_diagnostics` summarizes errors, warnings, failures, and referenced source contexts in recent background stdout/stderr,
  `check_write_process` validates that a running background process can receive stdin text or project-file-backed stdin without writing input,
  `write_process` sends exact text or a project-relative `stdin_file` to a running background process stdin after approval when the starting runtime still owns stdin,
  process observations include both VibeAgent process ids and OS pids, and
  `stop_process` / `stop_all_processes` terminate only processes VibeAgent started
  for the current project registry.
- File writes, batch file writes, file edits, JSON value updates/removals/patches, Python renames, Python definition replacements, file patches, file copies, file moves, file deletes, directory lifecycle changes, git fetches, git pulls, git pushes, GitHub pull request creation through `gh`, git restores, git stashes, git stash applies, git stash drops, git branch switches, process stdin writes, and command
  starts/runs require approval in the CLI before execution. Library callers that
  do not provide an approval handler deny those actions by default.
- CLI approval defaults to `ask`; `/approval allow` approves future actions in
  the current session, `/approval deny` rejects them without prompting, and
  `/approval dontAsk` runs trusted pre-approved actions but rejects other
  approval-requiring actions without prompting. `/approval plan` exposes
  read-only agent tools and produces an implementation plan without mutating
  the workspace. During an agent run, `EnterPlanMode` switches the following
  turns to the same read-only catalog. `ExitPlanMode` presents the plan for
  approval; the user can resume with per-action review, allow subsequent
  actions, or keep planning with feedback. The selected mode persists into the
  next interactive turn. A main agent profile that forces `permissionMode:
  plan` hides and rejects `ExitPlanMode` instead of allowing the model to
  weaken that configured boundary.
- Ctrl-C during a running local command, one-shot task, or interactive task
  prints `Interrupted.` instead of a traceback; one-shot and local-command
  invocations exit with status 130, while the interactive prompt returns to the
  next input.
- Some obviously dangerous or disruptive commands, such as `sudo`, `sudoedit`,
  `doas`, `pkexec`, or `reboot` even through path-qualified or wrapped forms
  like `/usr/bin/sudo reboot` and `env sudo reboot`, broad `rm -rf` targets including path-qualified forms like
  `/bin/rm -rf /`, raw device writes, network script pipes like
  `curl ... | bash` or `/usr/bin/curl ... | /bin/bash`, forced
  untracked-directory cleanup like `git clean -ffdx`,
  destructive storage or partition changes like `wipefs -a /dev/sda` or
  `parted /dev/sda mklabel gpt`,
  destructive container or cluster changes like `docker system prune -af`,
  `kubectl delete pod app`, or `helm uninstall release`,
  system mount/swap changes like `mount /dev/sda1 /mnt` or `swapon /swapfile`,
  kernel module or kernel-parameter changes like `modprobe overlay` or
  `sysctl -w net.ipv4.ip_forward=1`,
  service state changes like `systemctl restart ssh` or `service nginx reload`,
  broad process termination like `pkill -f node` or `kill -9 -1`,
  network or firewall state changes like `ip link set eth0 down` or `iptables -F`,
  PowerShell network execution like `pwsh iwr ... | iex` or
  `/usr/bin/pwsh iwr ... | iex`,
  recursive permission or ownership changes of broad paths like
  `chmod -R 777 /`, GUI file openers like `xdg-open .`, `env -i DISPLAY=:0
  xdg-open .`, `kioclient5 exec .`, `exo-open .`, `mimeopen .`,
  `open -a Finder .`, or `explorer.exe .`, GUI app launchers like
  `code .`, `sensible-browser ...`, or `firefox ...`, and common indirect launch forms through `cmd.exe`,
  `cmd /s /c start ...`, `start`, `rundll32
  url.dll,FileProtocolHandler`, PowerShell
  `start .`/`Start-Process`/`saps`/`iex 'explorer.exe .'`/`Start-ThreadJob { xdg-open . }`,
  `python -m webbrowser`,
  `webbrowser.open`, `webbrowser.get().open`, `os.startfile`, `os.system`,
  `os.popen`, `os.spawn*`, `os.exec*`, `os.posix_spawn*`,
  `subprocess.getoutput`, `asyncio.create_subprocess_*`, `pty.spawn`,
  `getattr(..., launcher)`, `importlib.import_module(...).<launcher>`,
  `builtins.__import__(...).<launcher>`, `eval`/`exec` string literals that
  contain blocked Python operations, `eval`/`exec` aliases and literal
  `compile(...)` payloads, obvious `python -c` or Python stdin heredoc
  subprocess GUI opener calls, or obvious `node -e` / `node -p` / Node stdin
  heredoc CommonJS, static ESM, dynamic `import(...)`, or static string-variable
  launcher calls through `child_process`, `shelljs`, or `execa`, are blocked.
  They stay blocked even if a caller approves command execution.
- Project mutation tools reject paths that are themselves symbolic links or that
  pass through symbolic-link parent directories, so a model cannot write, patch,
  move, copy, delete, chmod, or create files through an alternate link target.
- Commands time out after 30 seconds by default.
- Command hard blocks remain defense in depth and do not recognize every
  dangerous shell program. With sandboxing disabled or explicitly bypassed,
  approved commands run with the user's normal OS access. Enable the Bubblewrap
  sandbox for OS-enforced project write boundaries.

## Development

```sh
python -m unittest discover -s tests -t .
npm test
npm run test:v1
```
