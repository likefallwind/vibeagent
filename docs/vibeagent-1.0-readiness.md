# VibeAgent 1.0 Readiness Audit

This audit records the automated readiness gate and the live-provider dogfood
evidence for calling VibeAgent 1.0 complete.

## Automated Gate

Run from a clean worktree:

```sh
npm run test:v1:release
```

The release suite also covers bounded coding-prompt `@path` references for
UTF-8 text and images, including workspace/sensitive-file rejection, metadata-
only event persistence, redacted conversation checkpoints that exclude prompt
attachments, one-turn image payload cleanup, and compaction-safe text context.
Text references support exact numbered `#5-10`, `#L5-L10`, and
single-line selectors with strict file and 1,000-line boundaries. Interactive
terminals add bounded Tab completion for safe project paths and slash commands
without opening a GUI; non-TTY input remains unchanged.
Permission rule text is redacted before it becomes model-visible
or enters session events, and terminal trust previews are redacted and limited
to 20 displayed rules while the original rule remains available for matching.
System prompts support replacement and append text or bounded UTF-8 file
inputs in both interactive and one-shot modes. Replacement text and file forms
are mutually exclusive, append sources compose deterministically, relative
paths use the invocation directory, and symbolic-link inputs are rejected.
Startup-level `--add-dir` grants bounded multi-root file, search, code-intel,
prompt-reference, and command-cwd access without treating added roots as
configuration, session, or Git roots. Every root keeps protected/sensitive-path
and symlink boundaries, overlapping roots use the most specific boundary, and
the command sandbox binds each explicitly granted root.
Interactive `/add-dir` can list, add, remove, or clear roots without restarting;
the active set is shared with agent turns, workflows, idle scheduled tasks, and
absolute-path completion. Directory changes are session events, and resume or
compact restores the latest valid set while ignoring unavailable stored paths.

That release gate expands to:

```sh
npm run build
npm run test:install
npm run test:v1:full
```

This gate must run:

- `python3 -m compileall -q vibeagent`
- `python3 scripts/install_smoke.py`
- `npm run test:v1`
- `python3 -m unittest discover -s tests -t . -q`

Passing this gate proves all package modules compile, the package installs from
outside the repository, both CLI entrypoints start, and the deterministic 1.0
acceptance suite, real CLI smoke paths, and full unit suite are internally
consistent.

## Automated Evidence

The automated suite currently covers these 1.0 surfaces:

- Install smoke: `scripts/install_smoke.py` creates a fresh virtual environment
  from outside the checkout, installs the package editable, and verifies both
  `python -m vibeagent --version` and `vibeagent --version`.
- Core ReAct loop: inspect, edit, run checks, repair, review, commit, finish.
- Built-in `/code-review` expansion in interactive and print modes: bounded
  effort/target parsing, verified multi-agent review, read-only default behavior,
  explicit `--fix`, and fail-closed unsupported cloud/comment options before
  any model request or external write.
- Built-in `/simplify` expansion in interactive and print modes: four parallel
  cleanup reviewers, independent candidate verification, strict separation from
  correctness review, bounded local targets, a behavior-preserving edit contract,
  focused checks, and final review.
- Built-in `/security-review` expansion in interactive and print modes: cached
  `origin/HEAD` preflight, four isolated security domains, exploitability-aware
  verification, security severity levels, strict read-only behavior, and
  argument rejection before provider creation.
- Built-in `/verify` and `/run-skill-generator` expansion in interactive and
  print modes: bounded goals and app hints, observable runtime evidence,
  process ownership and cleanup, fail-closed UI claims, ambiguity handling,
  secret-free root or package-level `.claude/skills/run-<name>/SKILL.md`
  generation, directory-qualified discovery, and exact skill reload before
  completion.
- Nested monorepo skills: bounded package discovery, names such as
  `apps/web:deploy`, direct slash-command and `skill` tool invocation,
  same-name root variant guidance, agent-profile preloading, ConfigChange-safe
  snapshots, blocked-change rollback, and old-session snapshot migration.
- Interactive `/batch` expansion: bounded required instructions, clean
  Git/origin preflight contract, 5-30 disjoint work units, explicit plan approval,
  background worktree isolation, per-unit checks/commit/push/PR requirements, and
  one-shot refusal before provider creation.
- Main-session shell cwd persistence: Bash, native PowerShell, and interactive
  shell commands carry a validated working directory across turns and resume;
  background Bash starts there, subagents stay isolated, outside paths reset,
  opt-out is supported, and `CwdChanged` hooks receive the transition.
- Session Bash environment persistence: private bounded `CLAUDE_ENV_FILE`
  state is exposed to `SessionStart` and `CwdChanged` hooks, loaded by later
  foreground/background/interactive/subagent Bash commands, inherited by
  branches, and rejected on symlink, oversized, unreadable, or hard-blocked
  content.
- Claude-compatible tool aliases: `Read`, `Edit`, `MultiEdit`, `Write`,
  `NotebookRead`, `NotebookEdit`, `Bash`, `PowerShell`, `BashOutput`, `KillBash`, `Monitor`,
  `TaskCreate`, `TaskGet`, `TaskList`, `TaskUpdate`, `TeamCreate`, `TeamDelete`, `TodoWrite`, `TodoRead`,
  `CronCreate`, `CronList`, `CronDelete`, `WebFetch`, `Task`, `TaskOutput`,
  `TaskStop`, `Agent`, `EnterPlanMode`, and `ExitPlanMode`, including
  approval-mode selection, keep-planning feedback, and forced-plan locking.
- Structured `AskUserQuestion` batches with one to four questions, short
  headers, described choices, single/multi-select terminal input, consolidated
  tool results, session evidence, and per-question machine output.
- MCP resource discovery and reading over stdio and Streamable HTTP, including
  cursor pagination for concrete resources and RFC 6570 URI templates, exact
  advertised-URI or matching-template enforcement, method-not-found fallback
  for older concrete-only servers, bounded redacted text, hidden binary blobs,
  Claude-compatible aliases, and explicit approvals.
- Real CLI JSON and stream-json entrypoints, stdin input formats, resume,
  compact, permission overrides, `acceptEdits`, non-interactive `dontAsk`
  with trusted pre-approval and default denial, bounded invocation-scoped
  `--agents` definitions inherited by delegated runtimes, safe structured agent
  YAML, profile permission modes, scoped command hooks and stdio/HTTP MCP,
  initial prompts, forced background execution, task color, disallowed tools, one-shot
  `--tools` visibility and execution ceilings inherited by subagents, global
  deny alias-family removal across schemas, tool search, MCP wildcards, and
  every subagent path while scoped deny rules retain action-level matching,
  shared provider-cost budgets, ordered sticky overload-model fallback chains,
  opt-in incremental provider SSE output with bounded parsing, retry metadata,
  Anthropic/MiniMax and OpenAI-compatible accumulation, wrapper preservation, and
  pending-user-input output.
- Interactive model selection: `/model` reports the active configured or
  session-overridden model, `/model <name>` maps an override to the current
  provider and replaces the shared client only after successful construction,
  and `/model default` restores configuration while coding/chat history remains
  intact and project settings remain unchanged.
- Interactive effort selection: `/effort` reports `auto` or the current
  session override, supported Anthropic clients accept `low`, `medium`, `high`,
  `xhigh`, and `max`, `/effort auto` rebuilds the provider/model default client,
  and later model switches preserve the override. Invalid or unsupported
  changes atomically keep the prior client and effort state.
- Interactive provider streaming: code and chat turns render only assistant
  text deltas, hide thinking and tool inputs, delimit retries and same-attempt
  fallback restarts, close interrupted lines, suppress duplicate final text,
  preserve the existing path for clients without streaming support, and disable
  raw coding streams when a merged `MessageDisplay` hook must transform output.
- Durable main-session conversation continuity: private atomic checkpoints at
  safe model/tool boundaries, fresh system/project context on every prompt,
  explicit resume and branch restoration, corrupt-state handoff fallback, and
  compact/clear/rewind boundaries that do not replay detailed history.
- Ephemeral `/btw` side questions: the current coding or chat conversation is
  rendered into a bounded read-only transcript with binary payloads omitted;
  the provider receives no tools, and neither the question nor answer mutates
  in-memory conversation history or persisted session state.
- Manual and idle session recaps: `/recap` generates one bounded, tool-free
  status line without changing conversation history; code and chat modes keep
  separate eligibility state, and three completed turns followed by three idle
  minutes trigger an unpersisted recap through a dedicated provider client.
  Failed automatic attempts wait at least 60 seconds before retry, and
  `VIBEAGENT_DISABLE_SESSION_RECAP=1` disables automatic delivery.
- Interactive `/branch [name]` and resumed `--fork-session`, including immutable
  source events, independent first-turn workspaces, state inheritance, named
  resume, branch discovery, bounded lineage fallback, and malformed/cyclic
  metadata rejection.
- Interactive and one-shot system-prompt text/file inputs, including bounded
  UTF-8 reads, deterministic structured-input merging, and machine-readable
  validation failures before provider creation.
- Interactive and one-shot additional working directories, including
  invocation-relative CLI resolution, model-visible absolute roots, core file
  and command execution, configuration isolation, sandbox mounts, and rejection
  of unlisted, protected, sensitive, symlink-escaping, or worktree-conflicting
  paths. Interactive add/remove/clear changes, external-root completion, session
  event persistence, and interactive, one-shot, resume, and compact restoration
  are covered directly.
- Provider-free interactive `!` shell mode with bounded execution, hard command
  blocks, redacted resumable output, and pre-execution session-path validation.
- User and project integrations: `~/.claude/settings.json`, trusted project and
  local settings environments, user/local MCP scopes in `~/.claude.json`,
  `.mcp.json`, provider-free scoped MCP management, strict MCP config,
  `.claude/skills`, `.claude/agents`, tool and session lifecycle hooks, project
  slash commands, checkpoints, session handoff, focused tests, code-mode
  subagents, and background read-only subagent lifecycle control.
- Claude-compatible asynchronous command hooks: `async` returns control after
  approved process startup and keeps private current-session state. Bounded
  redacted `additionalContext` reaches a later model turn exactly once, while
  `systemMessage` is exposed only to terminal or machine users. `asyncRewake`
  wakes an idle interactive session only for exit code 2; print-mode and CLI
  teardown cancel unfinished hooks, and all async decisions remain non-blocking
  under the normal command safety and sandbox path.
- Claude-compatible HTTP hooks: approved handlers POST lifecycle JSON to a
  validated local or public endpoint without environment proxies, cap request
  input at 1 MiB, expand only explicitly allowlisted
  environment variables in bounded headers, consume 2xx plain or structured
  decisions, reject credential-bearing and cross-network-scope URLs, and record
  non-2xx, connection, and timeout failures without blocking the triggering
  action.
- Claude-compatible MCP tool hooks: approved handlers expand bounded typed
  `${path}` values from lifecycle input, call an advertised tool on a configured
  stdio or HTTP MCP server through the normal command and transport safety path,
  feed successful plain or structured output into Hook decisions, and keep
  missing servers, protocol failures, and `isError` results non-blocking.
- Claude-compatible prompt hooks: supported lifecycle and tool events expand
  bounded `$ARGUMENTS`, run one strict no-tool `{ok, reason}` evaluation through
  the shared provider budget/fallback path, honor scoped model and 30-second
  default timeout settings, halt default Pre/Post blocks, feed
  `continueOnBlock` and Stop/SubagentStop reasons back for another turn, and
  keep model or validation failures non-blocking.
- Experimental Claude-compatible agent hooks: the same supported events and
  strict decision schema can run up to 50 read-only inspection turns, with a
  60-second default timeout, no mutation, command, delegation, or user-input
  tools, Hook-specific audit events, shared provider budget/fallback state, and
  the same block, feedback, and non-blocking failure semantics as prompt hooks.
- Claude-compatible `PermissionRequest` hooks: command, HTTP, MCP tool, prompt,
  and experimental agent handlers run only at a real ask-mode approval boundary;
  prompt and agent results are advisory, command/HTTP/MCP deny wins over allow,
  allow decisions can replace input and apply bounded session or persisted rule,
  mode, and additional-directory updates, deny can interrupt the active turn,
  updated actions are rechecked against project rules and workspace safety, and
  malformed or failed updates fall back to ordinary user approval with bounded
  audit evidence.
- Claude-compatible compaction and termination hooks: `PreCompact` and
  `PostCompact` wrap automatic main-agent and interactive manual compaction with
  trigger and bounded summary input; `SessionEnd` receives the documented exit
  reason for one-shot termination, interactive exit, clear, resume, and branch
  paths. These events are non-blocking, reject model handlers, and enforce the
  shared 1.5-second default session-end budget with a 60-second ceiling.
- Claude-compatible task lifecycle hooks: `TaskCreated` and `TaskCompleted`
  ignore matchers, receive stable task identity and available team context, and
  can block main-agent, subagent, and teammate task transitions before the
  atomic task store changes. Exit-code-2 feedback continues the model while
  `continue: false` halts the active turn.
- Claude-compatible post-batch hooks: `PostToolBatch` runs once after resolved
  parallel, sequential, deferred-resume, and delegated batches with the exact
  provider-facing tool results; it can inject next-turn context or stop before
  the next model request without forcing tools to execute sequentially.
- Claude-compatible teammate idle hooks: matcher-free `TeammateIdle` runs at
  text and `finish` completion boundaries with stable teammate/team identity;
  exit code 2 feeds bounded continuation work back to the teammate, while
  `continue: false` stops it without violating provider tool-result ordering.
- Claude-compatible failed-turn hooks: `StopFailure` classifies exhausted main
  model API failures into the documented matcher categories and sends bounded,
  redacted failure details to command, HTTP, or MCP tool handlers. Hook output,
  exit status, and runtime failures cannot replace the original failed result;
  successful retries never fire the event.
- Claude-compatible worktree lifecycle hooks: command and HTTP
  `WorktreeCreate` handlers replace the default Git backend for CLI and
  subagent isolation and return a validated directory; `WorktreeRemove`
  handlers receive the same absolute path during cleanup. Missing, failed, or
  unsafe create paths fail before model execution.
- Claude-compatible directory-added hooks: matcher-aware `DirectoryAdded`
  runs command, HTTP, or MCP tool handlers in the background after interactive
  `/add-dir` and Python `register_repo_root(...)` registration. Slash-command
  `systemMessage` output enters the next code turn, while failures never roll
  back the registered workspace root.
- Claude-compatible prompt-expansion hooks: `UserPromptExpansion` matches direct
  slash commands and skills by command name, exposes the original invocation
  and expansion metadata to all five handler types, injects
  `additionalContext` beside the expanded prompt, and can reject the command
  before the first main-model request.
- Claude-compatible notification hooks: matcher-aware `Notification` emits
  `permission_prompt` before ask-mode approval handling and one `idle_prompt`
  after 60 seconds of established interactive-session input wait. Command,
  HTTP, and MCP tool handlers receive the documented message, title, and type;
  decisions and failures are non-blocking, while `systemMessage` remains
  user-only.
- Claude-compatible watched-file hooks: `FileChanged` treats `|`-separated
  matcher segments as literal filenames in the session cwd, detects bounded
  `add`, `change`, and `unlink` events at active-agent and interactive-idle
  boundaries, exposes `CLAUDE_ENV_FILE`, and keeps decisions non-blocking.
  SessionStart, CwdChanged, and FileChanged `watchPaths` atomically replace a
  workspace-scoped, symlink-free dynamic list while static matcher paths remain.
- Claude-compatible assistant display hooks: matcher-free `MessageDisplay` runs
  once for each completed assistant text response, passes stable UUID identifiers
  and the full original delta, and honors bounded `displayContent` replacement.
  The rendered channel is separate from transcripts, resumed conversations,
  model context, goal evidence, and canonical machine-result text; failed hooks
  fall back to the original display.
- Experimental agent teams: feature-gated Claude-compatible `TeamCreate` and
  `TeamDelete`, one atomically persisted private session team, active-teammate
  cleanup refusal, approved named teammates, independent background contexts,
  stable session identities, shared task ownership and dependencies, peer and
  lead mailboxes, automatic lead delivery, compatibility creation for legacy
  named spawns, and teardown cancellation and cleanup.
- Session scheduling: standard local-time cron expressions, deterministic
  jitter, one-shot and recurring delivery, idle CLI wakeups, seven-day expiry,
  no-catch-up behavior, atomic persistence, and filtered resume restoration.
- Reactive command monitors: Bash-equivalent approval, bounded default and
  maximum timeouts, persistent session mode, redacted line-at-a-time untrusted
  events, active-turn delivery, idle CLI wakeups, one-time exit delivery,
  `TaskStop` cancellation, and session-exit process cleanup.
- Reactive WebSocket monitors: mutually exclusive `ws`/`command` sources,
  per-connection approval, public-only DNS validation, credential and protocol
  rejection, pinned resolved-address connection without environment proxies,
  multiline text-message preservation, binary byte-count placeholders, 1 MiB
  message limits, close-code events, and the shared timeout/wakeup/stop lifecycle.
- Autonomous goals: one persisted completion condition, strict bounded no-tool
  evaluation after each coding turn, evaluator-guided continuation, interactive
  status and clearing, explicit resume restoration, and one-shot looping.
- Same-machine peer messaging: live Unix-socket discovery through `ListAgents`,
  plain-text `SendMessage` delivery, sender-process verification, bounded
  queues, accept/hold/refuse controls, held inbox decisions, active-turn
  injection, idle interactive wakeups, and permission-boundary preservation.
- Scoped instructions: nested instruction files and path rules load independently
  in main and subagent contexts and become eligible for reload after compaction.
- Safety boundaries: workspace path guards, approval policy, hard command
  blocks, final-review blockers, protected files, source-aware user/project
  permissions, environment propagation, hooks, and sandbox checks.

The source of truth for exact test names and gates is
[`docs/vibeagent-1.0.md`](vibeagent-1.0.md).

## Live Provider Gate

Before declaring 1.0 complete, run at least one live-provider dogfood against a
throwaway repository, not this fixture suite. The run must use the installed CLI
entrypoint and a real provider configuration.

Prepare the throwaway repository and print the command with:

```sh
python3 scripts/live_dogfood_v1.py --prepare --force --print-command
```

Minimum command shape printed by the script:

```sh
python3 -m vibeagent --cwd /tmp/vibeagent-live-dogfood --approval ask --max-iterations 20 "Inspect this repo with read-only tools, run `python -m unittest discover -s tests` to observe the failing test before editing, fix the failure, rerun unittest until it passes, review, commit, rerun any final suggested checks, and finish only when final_review is ready."
```

The live dogfood is passing only if all of these are true:

- The agent inspects repository state before editing.
- The agent asks for approval before side effects when `--approval ask` is used.
- The agent edits only files inside the target workspace.
- The agent runs the relevant failing and passing checks.
- `final_review` is ready before completion.
- The final git worktree is clean and contains one intentional local commit.
- `session_handoff` for the run is ready after completion.
- The run transcript has no secret leakage, unsafe command execution, or
  unapproved mutation.

After the live run completes, audit local outcomes with:

```sh
python3 scripts/live_dogfood_v1.py --audit --run-id <run-id>
```

To run and audit in one reproducible command, use:

```sh
python3 scripts/live_dogfood_v1.py --prepare --force --run --audit-after-run
```

The audit checks both repository state and session transcript evidence: ask-mode
approval policy, inspection before side effects, approval requests and approved
decisions, prior approval for side effects, workspace-bound side-effect paths,
transcript secret leakage, blocked command execution, agent-run failing and
passing unittest verification, ready final review, ready completion, and ready
session handoff.

## Current Decision

Status: `complete-for-v1-release`.

Release package version: `1.0.0`.

Reason: the automated 1.0 gate is broad and passing, the install smoke proves
the packaged CLI entrypoints from outside the checkout, and the live-provider
dogfood gate passed on a non-fixture throwaway repository.

Live provider evidence:

- Date: 2026-08-08
- Provider: MiniMax via `MINIMAX_API_KEY`
- Throwaway repo: `/tmp/vibeagent-live-dogfood`
- Session: `2026-08-08T02-51-11-792Z-db4de4e5`
- Command:
  `python3 scripts/live_dogfood_v1.py --prepare --force --run --audit-after-run --approval-count 30 --run-timeout-ms 600000`
- Audit result: all repository, approval, failing/passing unittest,
  `final_review`, completion, and handoff checks passed.
