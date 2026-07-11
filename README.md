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
  "command_timeout_ms": 30000,
  "max_output_tokens": 4096,
  "model_retries": 1,
  "model_retry_delay_ms": 250,
  "model_timeout_ms": 120000
}
```

Only non-secret defaults are read from that file. Provider defaults, execution
limits, and optional cost rates can live there. Keep API keys in environment
variables or pass a temporary `--api-key` for one command.

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
python -m vibeagent --output-format stream-json --cwd ../my-project "run the release checks"
printf '{"type":"user","text":"inspect the change"}\n' | python -m vibeagent --input-format stream-json -
printf '{"prompt":"inspect the change"}\n' | python -m vibeagent --input-format json -
python -m vibeagent --append-system-prompt "Prefer focused tests before broad suites." "inspect the change"
python -m vibeagent --allowed-tools "Read" --allowed-tools "Bash(git diff:*)" --disallowed-tools "Bash(git push:*)" "inspect the change"
python -m vibeagent --mcp-config docs.mcp.json "use the docs MCP server to check the API"
python -m vibeagent --mcp-config docs.mcp.json --strict-mcp-config "use only this MCP config"
python -m vibeagent --provider deepseek --model deepseek-reasoner --base-url https://api.deepseek.com "inspect this repo"
printf "summarize the project risks\n" | python -m vibeagent -
```

`--provider`, `--model MODEL` / `--model-name MODEL`, `--base-url`, `--api-key`,
`--max-iterations`, `--command-timeout-ms`, `--max-output-tokens`,
`--model-retries`, `--model-retry-delay-ms`, and `--model-timeout-ms` are
per-command overrides; they do not rewrite environment variables or local config
files.
For Claude-style scripting compatibility, `-p` / `--print` runs a one-shot task
and prints only the final text in normal text output, `-r` is an alias for
`--resume`, `--session-id RUN_ID` is an alias for `--resume RUN_ID`,
`--session-id latest` resumes the newest session, `-c` resumes the newest
session for a one-shot task,
`--permission-mode` maps to `--approval`, accepting both VibeAgent values
(`ask`, `allow`, `deny`, `plan`) and Claude-style values (`default` -> `ask`,
`acceptEdits`/`bypassPermissions` -> `allow`), and `--max-turns` maps to
`--max-iterations`. `--dangerously-skip-permissions` maps to
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
`session_id` or `sessionId` field resumes that VibeAgent session in coding mode
when neither `--resume` nor `--compact` is provided.
When `-c`, `--resume [run-id]`, or `--compact [run-id]` is provided without a
task, VibeAgent starts the interactive prompt with that context already loaded.
`--system-prompt` replaces the default one-shot system prompt for a command;
`--append-system-prompt` keeps the default prompt and adds extra system-level
constraints. Both options work in one-shot code and chat modes and are never
saved to project configuration.
With `--json`, one-shot coding results include `status` (`completed`,
`blocked`, or `failed`), matching `stopReason`, `numTurns`, final text as
`message` plus a `result` alias, `runId` plus a `sessionId` alias, a
`priorContext` object with loaded/source/run id metadata, structured `plan`
items,
`completionReady`, `completionBlockers`, `completionWarnings`,
`completionBlockedCount`,
`latestCompletionBlockers`, `latestCompletionPendingChecks`,
`latestCompletionFailedChecks`, `latestCompletionFinalReviewChangedFiles`,
`changedFiles`, `verificationChecks`, `pendingVerificationChecks`, and
`failedVerificationChecks` fields, plus `durationMs`, a `usage` report, and a
`cost` report for the current run, so automation can read the same final-review,
blocked-attempt, changed-file, verification, timing, local token-usage, and
configured cost estimate status shown in the text UI.
Machine output also includes Claude-style snake_case aliases for key run
fields: `session_id`, `num_turns`, `duration_ms`, and `stop_reason` where
applicable.
`--output-format json` is equivalent to `--json`. `--output-format stream-json`
emits newline-delimited JSON for one-shot tasks: each durable session event is
written as a `type: "event"` record with a monotonically increasing `sequence`,
`runId`, matching `sessionId` and `session_id`, and the redacted event payload,
followed by exactly one `type: "result"` record containing the normal code or
chat result, with final text available as both `message` and `result`. Every
line is flushed immediately for CI and process supervisors. Stream mode never
opens
interactive approval or user-input prompts; with the default `--approval ask`,
side-effecting tools are denied unless a trusted permission rule or complete
sandbox auto-approval applies. Use `--approval allow` or
`--dangerously-skip-permissions` only in an appropriately isolated automation
environment. `stream-json` requires a one-shot task and is not accepted for the
interactive prompt or standalone local command flags.
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
content length, and write/preflight messages.
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
`--json --session-verification` includes a structured `sessionVerification`
object with verified, pending, and failed check groups, truncation state, and
machine-readable command/cwd entries for each shown check.
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
python -m vibeagent --model
python -m vibeagent --config --cwd ../my-project
python -m vibeagent --tools
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
python -m vibeagent --check-stop-process <process-id> --cwd ../my-project
python -m vibeagent --stop-process <process-id> --cwd ../my-project
python -m vibeagent --check-stop-all-processes --cwd ../my-project
python -m vibeagent --stop-all-processes --cwd ../my-project
python -m vibeagent --sessions --cwd ../my-project
python -m vibeagent --session <run-id> --cwd ../my-project
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
python -m vibeagent --usage --cwd ../my-project
python -m vibeagent --cost --cwd ../my-project
python -m vibeagent --save-config --cwd ../my-project --provider deepseek --model-name deepseek-reasoner --max-iterations 12 --max-output-tokens 8192 --model-retries 2 --model-retry-delay-ms 500 --model-timeout-ms 120000
python -m vibeagent --json --doctor --cwd ../my-project
```

Use `/help` to list local commands, `/model` to inspect the configured provider,
model, base URL, and API key source, `/config` to inspect resolved provider,
execution, project config, and cost-rate settings, `/status` to inspect local mode, approval,
and resume state, `/tools` to inspect the model tool catalog, `/tool <name>` to
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
with optional output diagnostics and bounded contexts, `/check-run-commands [--cwd PATH] -- <cmd> ;; <cmd>` to preview a short ordered
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
`/processes` to inspect VibeAgent-started background processes,
`/process <id> [chars]` to inspect captured stdout and stderr for one background process,
`/process-output-contexts <id> [chars] [--max-chars N] [--context-lines N] [--max-contexts N] [--max-bytes N]` to extract source contexts for file:line references in background process output,
`/process-output-diagnostics <id> [chars] [--max-chars N] [--context-lines N] [--max-diagnostics N] [--max-contexts N] [--max-bytes N]` to summarize background process errors, warnings, failures, and referenced contexts,
`/wait-process <id> [timeout-ms] [chars] [--timeout-ms N] [--max-chars N] [--stdout TEXT] [--stderr TEXT] [--regex]` to wait for a background process or output match,
`/check-write-process <id> <text>` to preview writing stdin text to one running background process,
`/write-process <id> <text>` to write stdin text to one running background process,
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
`/approval [ask|allow|deny|plan]` to control
the session approval policy, `/system-prompt [text|off]` and
`/append-system-prompt [text|off]` to set or clear session-only system-prompt
instructions for chat and coding turns, `/resume [run-id|off]` to carry a previous coding
session handoff into the next task or clear it, `/compact [run-id]` to explicitly
compact the newest or selected session into context, `/plan [run-id]` to inspect
the latest recorded task plan, `/transcript [run-id]` to inspect a safe session
event timeline without dumping full tool payloads, `/checkpoint [label]` to save
current git status, staged and unstaged patch files, and ordinary untracked file
contents under `.vibeagent/checkpoints/`,
`/checkpoints` to list saved checkpoints, `/checkpoint-show <id>` to inspect one
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
newest entries,
`/clear` to clear local chat
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

VibeAgent may read and search `my-project` directly, including bounded repository maps with source outlines, directory tree inspection, path-fragment file finding, path globbing,
file metadata inspection, Python symbol outlines, generic code outlines for common source languages, Python syntax checks, JSON/TOML config syntax checks, Python dependency inspection, generic source import/include inspection, generic source reference lookup, generic source definition excerpts, lexical non-Python source rename previews, Python definition excerpts, Python call-site lookup, Python call graph inspection, Python reference lookup, AST-guided Python rename previews, bounded full-file reads with truncation metadata, focused single or batched line-range reads for large files, scoped exact or regex search with total/truncation metadata, structured search contexts for matching source snippets, dry-run regex replacement previews, structured JSON value update/removal and JSON Patch previews, and dry-run patch validation. It can create or replace one or several text files, apply lexical non-Python source renames, apply AST-guided Python identifier renames after syntax validation, replace a unique Python class/function definition after syntax validation, replace exact text blocks, apply bounded regex replacements, update or remove one JSON value by JSON Pointer, apply multiple JSON add/replace/remove operations atomically, replace focused line ranges, insert text at a known line, append exact text to an existing file, or apply
single-file or multi-file unified diff hunks to existing files, and can safely
copy, move or delete one or several explicit files, adjust executable bits on individual files, create directories, copy directories, move directories, or delete empty directories. It can also inspect git branch/upstream state, list local branches and stashes, `git status`, merge/rebase conflict state, structured changed-file summaries, pre-final review results with suggested checks, raw and structured `git diff` hunks, source context around diff hunks, bounded untracked text-file previews, line-level `git blame`, fetch and fast-forward pull upstream state with approval, push current-branch commits to upstream with approval, switch or create local branches from a clean worktree with approval, stage or unstage explicit project paths, discard unstaged tracked-file changes with approval, save non-runtime changes to git stash with approval, apply stash entries to a clean worktree with approval, drop explicit stash entries with approval, and create local commits from staged changes with approval
through read-only tools, inspect fixed runtime/tool availability, preflight proposed shell commands, run short ordered verification command batches, inspect project manifests, suggest likely focused test files and runnable focused test commands for changed paths, preflight and run those focused test commands directly, and suggest relevant test/build commands from project
metadata and current changes. `AGENTS.md` and `CLAUDE.md` files are included in
the coding prompt with their directory scopes, so nested instructions apply to
files below that directory. Project commands from root or nested `package.json`, `pyproject.toml`,
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
For multi-step coding tasks, the model can also maintain a compact task plan;
the latest plan is captured in the run result, session log, `/session` and
`/last` summaries, and `/resume` context. `todo_write`/`TodoWrite` are
Claude-compatible aliases for replacing that same plan, and
`todo_read`/`TodoRead` read the latest plan from the current session. If a
successful run finishes while the latest plan still
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
and `/resume [run-id|latest]` in the interactive prompt load a bounded
historical resume context, while
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
`/checkpoint [label]` saves a local
handoff snapshot of `git status`, HEAD, unstaged diff, staged diff, and ordinary
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

## Project hooks

Project command hooks can be declared in `.vibeagent/hooks.json`,
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

Supported lifecycle events are `PreToolUse`, `PostToolUse`, and
`PostToolUseFailure`; matchers are regular expressions applied to the VibeAgent
tool name. Every matching hook command requires approval under the current
session policy and still passes command hard-block checks. Plan mode records and
skips command hooks. A failed or denied pre-tool hook blocks the target tool; a
failed post-tool hook preserves the target result but records an additional
tool error that prevents an unqualified successful completion. Hook commands
receive `VIBEAGENT_HOOK_EVENT`, `VIBEAGENT_TOOL_NAME`, and
`VIBEAGENT_TOOL_TARGET` environment variables and are recorded in the session
timeline with bounded output.

## Command sandbox

Linux and WSL2 command execution can use Bubblewrap OS isolation. Sandboxing is
disabled by default and can be enabled in `.vibeagent/sandbox.json` or through
the `sandbox` object in `.claude/settings.json` and
`.claude/settings.local.json`:

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

External `allowWrite` paths and `excludedCommands` require explicit project
configuration trust. `denyWrite` and `denyRead` mounts override the writable
project mount. Sandbox paths must be exact; glob paths, `allowRead`, non-empty
domain allowlists, and unsupported network options fail closed rather than
claiming partial enforcement. Domain allowlists require a proxy and are not yet
implemented. If Bubblewrap or network namespaces are unavailable,
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

## Project permissions

Fine-grained project permissions can be declared in `.vibeagent/permissions.json`
or under the `permissions` key in `.claude/settings.json` and
`.claude/settings.local.json`:

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
`NotebookRead`, `NotebookEdit`, `LS`, `Glob`, `Grep`, `WebFetch`, `Task`,
`Agent`, `AskUserQuestion`, `ExitPlanMode`, `TodoWrite`, and `TodoRead` map to
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
Per-run CLI overrides use the same rule syntax via `--allowed-tools` and
`--disallowed-tools`. CLI allow rules are trusted for that run only; project
file allow rules still require explicit project trust.

Project deny and ask rules always take effect. Because repository settings are
untrusted input, allow rules do not skip side-effect approval unless a one-shot
run explicitly uses `--trust-project-permissions` (or a library caller passes
`trust_project_permissions=True`) or the project has persistent user trust.
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

Project-scoped stdio MCP servers can be declared in `.mcp.json`:

```json
{
  "mcpServers": {
    "docs": {
      "command": "npx",
      "args": ["-y", "@example/docs-mcp"],
      "cwd": ".",
      "env": {"DOCS_TOKEN": "${DOCS_TOKEN}"}
    }
  }
}
```

`mcp_servers` reads configuration metadata without starting a process or
exposing argument and environment values. `mcp_tools` starts one server after
approval and performs the MCP initialization plus `tools/list` flow.
`mcp_call` requires separate approval for every invocation, verifies that the
tool was advertised, sends bounded JSON arguments, enforces per-request
timeouts and output limits, and terminates the stdio server afterward. MCP
server commands still pass VibeAgent's hard command-safety checks.
Claude-style model tool names such as `mcp__docs__search` are normalized to
the same `mcp_call` path with the tool input preserved as MCP arguments.
One-shot runs can add extra MCP configuration files with repeated
`--mcp-config PATH` arguments. Relative paths are resolved from `--cwd` or the
current project directory. Server names must be unique across `.mcp.json` and
all extra files, and each server `cwd` still has to resolve inside the project.
Use `--strict-mcp-config` to ignore project `.mcp.json` and load only the
explicit `--mcp-config` files for that one-shot run.

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
commands such as `/help`, `/model`, `/config`, `/tools`, `/tool`, `/tool-search`, `/permissions`, `/sandbox`, `/checks`, `/check-suggested-checks`, `/run-suggested-checks`, `/commands`, `/related-tests`, `/focused-tests`, `/check-focused-tests`, `/run-focused-tests`, `/manifests`, `/instructions`, `/todos`, `/command`, `/run`, `/check-run-seq`, `/run-seq`, `/check-start`, `/start`, `/port`, `/http`, `/http-fetch`, `/overview`, `/repo-map`, `/search`, `/search-contexts`, `/find-files`, `/glob`, `/tree`, `/symbols`, `/file-info`, `/image-info`, `/read`, `/around`, `/around-many`, `/output-contexts`, `/output-diagnostics`, `/python-traceback`, `/tail`, `/read-files`, `/read-ranges`, `/python-check`, `/python-deps`, `/python-defs`, `/python-refs`, `/python-ref-contexts`, `/python-calls`, `/python-call-graph`, `/python-rename-preview`, `/python-rename`, `/check-replace-python-def`, `/replace-python-def`, `/config-check`, `/check-json-set`, `/json-set`, `/check-json-remove`, `/json-remove`, `/check-json-patch`, `/json-patch`, `/check-replace-lines`, `/replace-lines`, `/check-insert-lines`, `/insert-lines`, `/check-append`, `/append`, `/check-write`, `/write`, `/check-write-files`, `/write-files`, `/check-edit`, `/edit`, `/check-multi-edit`, `/multi-edit`, `/check-delete`, `/delete`, `/check-delete-files`, `/delete-files`, `/check-move`, `/move`, `/check-move-files`, `/move-files`, `/check-copy`, `/copy`, `/check-copy-files`, `/copy-files`, `/check-move-dir`, `/move-dir`, `/check-move-dirs`, `/move-dirs`, `/check-copy-dir`, `/copy-dir`, `/check-copy-dirs`, `/copy-dirs`, `/check-mkdir`, `/mkdir`, `/check-mkdirs`, `/mkdirs`, `/check-rmdir`, `/rmdir`, `/check-rmdirs`, `/check-executable`, `/set-executable`, `/check-patch`, `/patch`, `/check-patches`, `/patches`, `/check-regex-replace`, `/regex-replace`, `/code-deps`, `/code-refs`, `/code-ref-contexts`, `/code-defs`, `/code-rename-preview`, `/code-rename`, `/git-status`, `/conflicts`, `/git-info`, `/branches`, `/log`, `/show`, `/blame`, `/stashes`, `/check-fetch`, `/fetch`, `/check-pull`, `/pull`, `/check-push`, `/push`, `/check-stash`, `/stash`, `/check-stash-apply`, `/stash-apply`, `/check-stash-drop`, `/stash-drop`, `/check-stage`, `/stage`, `/check-unstage`, `/unstage`, `/check-commit`, `/commit`, `/check-restore`, `/restore`, `/check-switch`, `/switch`, `/env`, `/processes`, `/process`, `/process-output-contexts`, `/process-output-diagnostics`, `/wait-process`, `/check-write-process`, `/write-process`, `/check-stop-process`, `/stop-process`, `/check-stop-processes`, `/check-stop-all-processes`, `/stop-processes`, `/stop-all-processes`, `/status`, `/context`, `/init`, `/doctor`, `/review`, `/handoff`, `/changes`, `/diff`, `/diff-hunks`, `/diff-contexts`, `/clear`, `/usage`, `/cost`, `/approval`, `/plan`, `/transcript`, `/session-search`, `/session-commands`, `/session-output-contexts`, `/session-output-diagnostics`, `/session-files`, `/session-failures`, `/session-verification`, `/run-session-verification`, `/session-audit`, `/session-handoff`, `/checkpoint`, `/checkpoints`, `/checkpoint-show`, `/checkpoint-diff`, `/checkpoint-status`, `/check-checkpoint-restore`, `/checkpoint-restore`, `/check-checkpoint-delete`, `/checkpoint-delete`, `/check-checkpoint-prune`, `/checkpoint-prune`, `/resume`,
  `/compact`, `/chat`, `/code`, and
  `/exit`, then delegates input to the selected mode.
  `/custom-commands` lists prompt templates from `.claude/commands/**/*.md`
  and `.agents/commands/**/*.md`. Built-in commands take precedence; nested
  template paths use colon names such as `/review:security`. Templates expand
  `$ARGUMENTS`, `$1`-`$9`, and `${1}`-`${9}` into a normal coding task, so any
  resulting model actions still use the current approval policy. Optional
  frontmatter fields `description` and `argument-hint` populate the command
  catalog without exposing template bodies.
- `vibeagent/agent.py`: orchestrates the ReAct loop. It creates a run
  session, builds model prompts, executes optional tool calls, records events,
  tracks the model's latest task plan, and stops on a plain text answer, a
  `finish` tool call, or the iteration limit. When the model emits several
  explicitly read-only tool calls in one turn, the agent can execute that batch
  concurrently while preserving result order; write, approval-gated, planning,
  user-input, and finish actions stay sequential. The `ask_user` tool can pause
  an interactive coding run for one blocking clarification and return the answer
  to the model as a normal tool result. JSON output and library runs without a
  user-input handler never read stdin; they return an unavailable-input result
  so the model can surface the unresolved question without guessing. Unexpected tool implementation exceptions
  are converted into `tool_error` observations so the model can recover instead
  of crashing the agent process. Provider request failures are retried according
  to `model_retries`, waiting `model_retry_delay_ms` between attempts. Each
  request is bounded by `model_timeout_ms`, each failed attempt is recorded as a
  `model_error` event, and unrecovered failures also produce a failed `result`
  event so interrupted sessions remain auditable and resumable. Every run
  records a final `result` session event with
  success/failure, message, iteration count, plan, and tool-step counts for later
  resume and audit. Provider requests start with a compact set of high-frequency
  tool schemas instead of the full catalog; `tool_search` matches and any
  directly called compatible tools are activated for later model turns and
  recorded as session events. Local `/tools`, `/tool`, and `/tool-search`
  commands continue to inspect the complete catalog.
- `vibeagent/agent_delegate.py`: runs bounded repository investigations or
  approval-gated implementation tasks for `delegate_task` in an isolated
  message history. Explore mode exposes only the established parallel-safe
  inspection tools plus `finish`. Code mode reuses progressive tool loading,
  parent approvals, workspace safety, and automatic checkpoints while excluding
  user input, parent-plan updates, and recursive delegation. Code-mode steps and
  observations feed the parent completion audit, and both modes record the child
  model/tool lifecycle before returning a structured summary.
- `vibeagent/mcp_config.py`, `vibeagent/mcp_stdio.py`, and
  `vibeagent/mcp_action_executor.py`: validate project MCP configuration, run
  newline-delimited JSON-RPC stdio sessions, and expose approved tool discovery
  and calls without leaving MCP subprocesses running.
- `vibeagent/workspace_hooks.py` and `vibeagent/agent_hooks.py`: load bounded
  project hook configuration, match tool lifecycle events, request approval for
  command hooks, preserve command hard blocks, and emit auditable hook results.
- `vibeagent/workspace_permissions.py` and `vibeagent/agent_permissions.py`:
  load bounded project permission rules, match Claude-compatible tool/path/
  command patterns, enforce explicit trust for allow rules, and centralize
  deny/ask/allow decisions across the main agent, hooks, and subagents.
- `vibeagent/project_trust.py` and `vibeagent/trust_commands.py`: maintain the
  user-owned persistent project-permission trust registry, expose trust/status/
  untrust commands, and keep repository-controlled allow rules inert until the
  user explicitly trusts them.
- `vibeagent/session_approval.py`: caches only user-selected, exact
  action-type-and-target approvals for the current CLI session, marks cache
  hits for audit, and keeps MCP process/tool calls outside the cache.
- `vibeagent/workspace_sandbox.py`, `vibeagent/command_sandbox.py`, and
  `vibeagent/sandbox_commands.py`: load bounded sandbox settings, validate
  trusted expansion paths, diagnose Bubblewrap/network namespace support, and
  build one filesystem/network-isolated launcher for finite and background
  shell commands, including strict per-command auto-approval qualification.
- `vibeagent/chat.py`: builds plain daily conversation prompts and keeps the
  model out of the coding-agent JSON action protocol.
- `vibeagent/providers.py`: selects the configured model provider. MiniMax is
  the default; DeepSeek and other OpenAI-compatible APIs use the OpenAI-compatible adapter.
- `vibeagent/prompts.py`: owns the system prompt and user message construction.
  Each prompt includes the original task, optional resumed session context,
  scoped `AGENTS.md`/`CLAUDE.md` instructions, discovered project command hints with
  command `cwd` and executable availability, current run directory, workspace file snapshot, and previous observations.
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
  `list_tree`, `repo_map`, line-range `read_file`, line-centered `read_file_context`, batch line-centered `read_file_contexts`, output-derived `output_contexts`, diagnostic `output_diagnostics`, Python-focused `python_traceback`, tail-focused `tail_file`, batch `read_files`, batch line-range `read_file_ranges`, `file_info`, `image_info`, `view_image`, `python_symbols`, `code_outline`, `python_check`, `config_check`, `check_json_set`, `json_set`, `check_json_remove`, `json_remove`, `check_json_patch`, `json_patch`, `python_dependencies`, `code_dependencies`, `code_references`, `code_reference_contexts`, `code_definitions`, `code_rename_preview`, `code_rename`, `python_definitions`, `python_calls`, `python_call_graph`, `python_references`, `python_reference_contexts`, `python_rename_preview`, `python_rename`, path-fragment `find_files`, path-pattern `glob`, scoped/regex/context `search`, `tool_search`, `git_info`, `git_status`, `git_conflicts`, `git_changes`, `git_branches`, `git_stashes`, `check_git_fetch`, `git_fetch`, `check_git_pull`, `git_pull`, `check_git_push`, `git_push`, `check_git_restore`, `git_restore`, `check_git_stash`, `git_stash`, `check_git_stash_apply`, `git_stash_apply`, `check_git_stash_drop`, `git_stash_drop`, `check_git_switch`, `git_switch`, `check_git_stage`, `git_stage`, `check_git_unstage`, `git_unstage`, `check_git_commit`, `git_commit`, `review_changes`, `final_review`, `suggest_checks`, `check_suggested_checks`, `run_suggested_checks`, `project_commands`, `related_tests`, `focused_test_commands`, `project_manifests`, `project_instructions`, `project_skills`, `skill`, `project_todos`, `project_overview`, `command_check`, `check_run_commands`, `run_commands`, `port_check`, `http_check`, `http_fetch`, `environment_info`, `git_diff`, `git_diff_hunks`, `git_diff_contexts`, `git_log`, `git_show`, `git_blame`, `session_summary`, `session_plan`, `session_transcript`, `session_search`, `session_commands`, `session_output_contexts`, `session_output_diagnostics`, `session_files`, `session_failures`, `session_verification`, `run_session_verification`, `session_audit`, `session_handoff`, `check_edit_file`, `edit_file`,
  `web_fetch`, `checkpoint_create`, `checkpoint_list`, `checkpoint_show`, `checkpoint_diff`, `checkpoint_status`, `check_checkpoint_restore`, `checkpoint_restore`, `check_checkpoint_delete`, `checkpoint_delete`, `check_checkpoint_prune`, `checkpoint_prune`, `check_multi_edit_file`, `multi_edit_file`, `check_replace_python_definition`, `replace_python_definition`, `check_replace_lines`, `check_insert_lines`, `check_append_file`, `check_regex_replace`, `regex_replace`, `replace_lines`, `insert_lines`, `append_file`, `check_patch`, `check_patches`, `patch_file`, `patch_files`, `check_write_file`, `write_file`, `check_write_files`, `write_files`, `check_delete_file`, `delete_file`, `check_delete_files`, `delete_files`, `check_move_file`, `move_file`, `check_move_files`, `move_files`, `check_copy_file`, `copy_file`, `check_copy_files`, `copy_files`, `check_move_dir`, `move_dir`, `check_move_dirs`, `move_dirs`, `check_copy_dir`, `copy_dir`, `check_copy_dirs`, `copy_dirs`, `check_create_dir`, `create_dir`, `check_create_dirs`, `create_dirs`, `check_delete_empty_dir`, `delete_empty_dir`, `check_delete_empty_dirs`, `delete_empty_dirs`, `check_set_executable`, `set_executable`,
  `run_command`, `check_start_command`, `start_command`, `list_processes`, `read_process`, `process_output_contexts`, `process_output_diagnostics`, `wait_process`, `check_write_process`, `write_process`,
  `check_stop_all_processes`, `check_stop_process`, `stop_all_processes`, `stop_process`, `delegate_task`, `ask_user`, `update_plan`, `todo_write`, `todo_read`, and `finish`.
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
- `file_info`, `image_info`, `view_image`, `read_file_context`, `read_file_contexts`, `output_contexts`, `output_diagnostics`, `python_traceback`, `tail_file`, `python_dependencies`, `code_dependencies`, `code_references`, `code_reference_contexts`, `code_definitions`, `code_rename_preview`, `python_references`, `python_reference_contexts`, `find_files`, `tool_search`, `session_summary`, `session_plan`, `todo_read`, `session_transcript`, `session_search`, `session_commands`, `session_output_contexts`, `session_output_diagnostics`, `session_files`, `session_failures`, `session_verification`, `session_audit`, `session_handoff`, `checkpoint_list`, `checkpoint_show`, `checkpoint_diff`, `checkpoint_status`, `check_checkpoint_restore`, `check_checkpoint_delete`, `check_checkpoint_prune`, `check_write_file`, `check_write_files`, `check_edit_file`, `check_multi_edit_file`, `check_replace_python_definition`, `check_replace_lines`, `check_insert_lines`, `check_append_file`, `check_delete_file`, `check_delete_files`, `check_move_file`, `check_move_files`, `check_copy_file`, `check_copy_files`, `check_move_dir`, `check_move_dirs`, `check_copy_dir`, `check_copy_dirs`, `check_create_dir`, `check_create_dirs`, `check_delete_empty_dir`, `check_delete_empty_dirs`, `check_set_executable`, `check_git_fetch`, `check_git_pull`, `check_git_push`, `check_git_restore`, `check_git_stash`, `check_git_stash_apply`, `check_git_stash_drop`, `check_git_switch`, `check_git_stage`, `check_git_unstage`, `check_git_commit`, `check_regex_replace`, `check_json_set`, `check_json_remove`, `check_json_patch`, `git_info`, `git_status`, `git_conflicts`, `git_changes`, `git_branches`, `git_stashes`, `review_changes`, `final_review`, `suggest_checks`, `check_suggested_checks`, `project_commands`, `related_tests`, `focused_test_commands`, `project_manifests`, `project_instructions`, `project_todos`, `project_overview`, `command_check`, `check_run_commands`, `port_check`, `http_check`, `http_fetch`, `check_start_command`, `process_output_contexts`, `process_output_diagnostics`, `wait_process`, `check_write_process`, `check_stop_all_processes`, `check_stop_process`, `environment_info`,
  `git_diff`, `git_diff_hunks`, `git_diff_contexts`, `git_log`, `git_show`, and `git_blame` are read-only and do not require approval.
  `suggest_checks` marks each suggested command with whether its main executable is available on `PATH`; the local `/checks` command and `--checks` flag expose suggested-check bounds;
  `check_suggested_checks` preflights those discovered checks without running them, and `run_suggested_checks` runs available discovered checks after approval;
  `project_commands` lists project-defined npm, pyproject, and Makefile commands with cwd and executable availability; the local `/commands` command and `--commands` flag expose command/file bounds;
  `related_tests` suggests likely test files for explicit paths or the current git changes without running them; the local `/related-tests` command and `--related-tests` flag expose target/candidate bounds;
  `focused_test_commands` maps those related test files to likely focused commands without running them; the local focused-test commands and flags expose target/candidate/command bounds;
  `project_manifests` reads package and pyproject dependency/script metadata; the local `/manifests` command and `--manifests` flag expose manifest file/item bounds;
  `project_instructions` reads AGENTS.md and CLAUDE.md instruction sources with scopes and bounded text; the local `/instructions` command and `--instructions` flag expose `--max-files`/`--max-bytes` and `--instructions-max-files`/`--instructions-max-bytes` bounds respectively;
  `project_skills` discovers bounded metadata from `.claude/skills/*/SKILL.md` and `.agents/skills/*/SKILL.md`, while `skill` loads one exact available skill on demand; skill bodies are excluded from the initial project snapshot and duplicate or symlinked skills are refused;
  project agent profiles are discovered from `.claude/agents/*.md` and `.agents/agents/*.md`; only bounded metadata enters the main prompt, while `delegate_task.agent` loads one exact profile body on demand and enforces its mode and optional built-in-tool allowlist at both schema and runtime boundaries. A profile uses frontmatter such as `name: test-writer`, `description: Writes focused tests`, `mode: code`, and `tools: read_file, write_file`, followed by its scoped system instructions;
  `project_todos` scans project text files for TODO, FIXME, HACK, XXX, and BUG markers;
  `command_check` does the same preflight for one proposed finite command and also reports cwd and block-rule failures;
  `check_run_commands` preflights a short ordered command batch without running it;
  `port_check` checks whether a local TCP host and port are reachable without running shell commands;
  `http_check` checks local/private HTTP(S) status, final URL, and optional response content without running shell commands;
  `http_fetch` fetches bounded local/private HTTP(S) response metadata and body text without running shell commands;
  `web_fetch` fetches bounded readable text from public technical documents after approval, rejects URL credentials and non-public destinations, and revalidates redirects;
  `check_start_command` does the same for long-running commands without starting a process;
  `wait_process` waits for a background process to exit, time out, or emit configured stdout/stderr text or regex without stopping it;
  `check_write_process` validates that a running background process can receive stdin without writing input;
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
  the next model turn. Finite command reports include per-command `durationMs`,
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
  `check_write_process` validates that a running background process can receive stdin without writing input,
  `write_process` sends exact text to a running background process stdin after approval when the starting runtime still owns stdin,
  process observations include both VibeAgent process ids and OS pids, and
  `stop_process` / `stop_all_processes` terminate only processes VibeAgent started
  for the current project registry.
- File writes, batch file writes, file edits, JSON value updates/removals/patches, Python renames, Python definition replacements, file patches, file copies, file moves, file deletes, directory lifecycle changes, git fetches, git pulls, git pushes, git restores, git stashes, git stash applies, git stash drops, git branch switches, process stdin writes, and command
  starts/runs require approval in the CLI before execution. Library callers that
  do not provide an approval handler deny those actions by default.
- CLI approval defaults to `ask`; `/approval allow` approves future actions in
  the current session, `/approval deny` rejects them without prompting, and
  `/approval plan` exposes read-only agent tools and produces an implementation
  plan without mutating the workspace.
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
  url.dll,FileProtocolHandler`, PowerShell `start .`/`Start-Process`/`saps`,
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
python -m unittest discover -s tests
npm test
```
