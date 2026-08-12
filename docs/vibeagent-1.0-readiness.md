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
Interactive `/cd PATH` switches the main project in place: the old project's
background runtime is closed, target configuration is reloaded, and the
conversation continues in a new target-local session branch.
Top-level `--background` / `--bg` launches a persistent one-shot coding session
in a detached process group and returns its project-local ID. Provider-free CLI
flags and interactive slash commands list sessions, read bounded logs, stop a
running agent, queue follow-up turns, respawn a running or stopped worker under the
same agent ID, and remove its private supervisor files without deleting the
resumable transcript. `agents` opens a dependency-free full-screen project
dashboard with grouped auto-refresh, stable keyboard selection, bounded log
peek, option-safe dispatch, reply, stop, respawn, confirmed removal, and attach
handoff after restoring the alternate screen. Dashboard dispatch automatically
adds a generated worktree in Git projects, while non-Git projects and ordinary
shell background launches keep their existing explicit isolation behavior.
Ask-mode permission requests and
structured `AskUserQuestion` calls publish private exact-ID interactions,
appear as `Needs attention`, and resume the blocked tool call after the dashboard
approves, denies, or validates a numbered, multi-select, or free-text answer.
`attach ID` (also
`--attach-background-agent ID`) acquires a private
process-bound lease, lets an active worker finish its current turn at a safe
handoff boundary, and restores the same transcript and effective worktree in the
full interactive CLI with normal approval prompts. Lease states are visible as
`attaching` or `attached`; terminal exit releases the lease, stale foreground
processes are recovered by PID start-time validation, and conflicting lifecycle
commands are rejected. Interactive `/bg [prompt]` and `/background [prompt]`
close the foreground runtime and resume the same coding session autonomously;
an Agent View attachment releases its lease before reusing the existing agent
ID. Model, effort, approval, prompt, dynamic-agent, and additional-directory
state carry into newly detached sessions. An atomic FIFO inbox and transition
lock prevent send/exit races, the effective worktree root and API-key-free launch options survive later
turns, and a private random worker token rejects nested CLI processes that only
inherit the supervisor environment. The worker consumes an owner-only launch
payload before running, records a durable exit status, validates PID start
times, closes stdin, retains the selected approval policy, and requires
credentials from the environment instead of persisted `--api-key` arguments.
This release does not claim machine-global aggregation across unrelated project
registries.
Self-hosted `remote-control` starts a project-scoped browser control plane for
the same detached supervisors. A generated 256-bit token authorizes bounded
state/log reads plus dispatch, reply, approval, structured-answer, stop,
respawn, and removal operations through the existing transition locks and
validators. Static assets carry no token, API responses are no-store and
frame-denied under a restrictive CSP, and non-loopback IPv4 binds require an
explicit regular-file TLS certificate/key pair. Real loopback HTTP tests cover
authentication and every route, Node parses the delivered JavaScript, and
headless-browser checks cover connected desktop and mobile layouts without
horizontal overflow. This self-hosted surface does not claim claude.ai/mobile
account integration, active foreground conversation sync, or cross-project
aggregation.
Optional first-class browser tools use an installed `agent-browser` runtime to
exercise the application being developed rather than opening a GUI through a
shell command. Six deferred tools cover approved navigation, accessibility
snapshots, bounded controls and DOM/console/error reads, atomic workspace
screenshots, and explicit close. Each VibeAgent session gets an isolated browser
name, private empty config, scrubbed proxy/profile/credential environment, and
an approved-host navigation allowlist. URL credentials, link-local/reserved
destinations, and mixed public/private DNS answers are refused; tool output is
bounded to 30,000 characters and screenshots to 25 MiB inside safe workspace
paths. Deterministic tests mock only the external process boundary, while a
real local Chromium smoke opens a fixture page, snapshots it, fills and clicks
controls, reads the changed DOM and clean console/error state, writes a
screenshot whose pixels are inspected, and closes the browser.
The dependency-free VS Code extension adds an editor-native path without
replacing VibeAgent's terminal approval boundary. Commands launch an interactive
primary session, additional parallel sessions, or an exact recent session from
a bounded workspace-history Quick Pick; they pass the active file or exact selected lines as a quoted `@path`
reference, hand off at most 20 sanitized diagnostics as explicitly untrusted
evidence, and compare the active file with Git `HEAD` in VS Code's diff viewer.
Machine-scoped executable configuration prevents a repository from replacing
the launch command, argument arrays avoid shell interpolation, and workspace
path validation prevents outside-file references. The deterministic VSIX build
contains only declared runtime files. An isolated VS Code Server install under
`/tmp` accepts the package and lists `vibeagent.vibeagent-vscode@1.0.0`; no real
user extension directory or GUI is touched by that verification.
History lookup runs the provider-free JSON CLI through an argument array with
no shell or live-context credentials. A timeout, byte limits, item/field bounds,
duplicate checks, and path/control rejection protect Quick Pick and `--resume`;
already open IDs are focused instead of duplicated, and editor references route
to the active managed terminal before the primary workspace session. A
startup-activated status item derives its per-workspace open-terminal count
from that same managed-terminal registry, excludes one-shot terminals, and starts or reveals a
session without maintaining a second lifecycle model.
Session Inspector adds a one-request, provider-free review surface over stored
session evidence. It validates a bounded overview, up to 20 plan items, 50 persistent tasks, 50
checks per verification group, 100 referenced files, and 80 timeline events
before rendering native Markdown. Trusted workspace, session, and display-name
metadata remain outside the document, and `Resume Inspected Session` uses the
exact stored ID regardless of document edits. Managed inspector editors expose
refresh, open-file, and continue-task title actions plus resume and verification
in the overflow menu; a private URI registry controls visibility, leaving
ordinary or edited Markdown unaffected.
The adjacent refresh action re-reads that exact out-of-band session and updates
the active inspector in place under the same 250,000-character rendering cap.
Unchanged generated snapshots need no prompt, while local document edits require
a modal replacement confirmation; cancellation or a document/text race leaves
the newer content untouched.
The inspector also includes up to 50 entries from the persistent `TaskCreate`
graph. Numeric IDs, unique shown tasks, status totals, owners, dependencies,
blocked flags, and the 100-task store ceiling are validated before rendering;
corrupt or symlinked task stores fail closed instead of appearing empty.
The adjacent file-navigation action refreshes the exact report and exposes only
currently available regular files up to 10 MiB whose real paths remain inside
the real workspace. It filters cross-platform absolute/drive-relative paths,
traversal, directories, missing files, and external symlinks, then re-resolves
the selected target and active inspector before opening an editor document.
The adjacent task-continuation action refreshes that exact graph, exposes only
unblocked pending or in-progress entries with active work first, and launches
the selected task in a visible one-shot resumed terminal. Stored task fields
are bounded and explicitly framed as untrusted context, while the validated
session ID remains out of band; completed and dependency-blocked tasks are
excluded and cancellation is inert.
The adjacent verification action refreshes the same session before showing a
modal confirmation, then launches at most 10 de-duplicated failed and pending
checks in a visible one-shot terminal with bounded source-context and diagnostic
extraction. It uses the exact out-of-band session ID and an argument array with
no shell; cancellation creates no terminal.
The extension also provides an Agent Panel over a temporary loopback Remote
Control process. The extension host retains its bearer token while the
CSP-restricted Webview receives only bounded state and logs. A validated message
allowlist supports dispatch, follow-up, exact-ID approval and question answers,
worktree change inspection, native base-to-current diffs, explicit isolated
worktree opening, confirmed exact-snapshot application, and lifecycle actions.
Application is limited to terminal isolated agents, rejects stale or truncated
reviews and independently modified main target paths before mutation, preserves
unrelated main changes, and leaves successful files unstaged. Bounded regular
files, binary content, deletions, and executable bits use atomic writes with
rollback after partial failure. Change inspection verifies shared Git
identity and project scope, filters sensitive/generated paths, and keeps bounded
file content and absolute roots out of the Webview. Closing the panel terminates the control process, with a
bounded force-kill fallback, without terminating supervised agents.
Interactive terminals additionally receive a private live-context bridge. The
extension atomically writes active-file metadata, the exact selected line range,
dirty state, and bounded sanitized diagnostics to an owner-only temporary file
with a random 256-bit token. Python rechecks that token, ownership, mode, exact
workspace, sensitive/protected/symlink boundaries, and all payload limits on
every turn before adding explicitly untrusted context. Source text and unsaved
buffers never cross the bridge, its credentials are removed from project child
process environments, and extension shutdown removes the temporary directory.

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
- VS Code integration: machine-scoped exact process launch, interactive TTY
  approvals, bounded session history, exact-ID resume, parallel/primary
  terminal routing, active-file and half-open selection references, quoted paths,
  bounded sanitized diagnostics, native Git diff routing, deterministic VSIX
  packaging, token-isolated Agent Panel control, exact-ID interactions, bounded
  worktree review and virtual documents, exact-snapshot conflict-safe
  integration and rollback, process cleanup, and isolated VS Code Server installation.
- Session inspector: real CLI aggregation from one event snapshot, fixed report
  bounds, invalid or missing-session failure, deeply validated JavaScript
  parsing, native Markdown review, close invalidation, and exact-ID resume.
- Persistent session task graph: provider-free `sessionTasks` JSON, metadata
  omission, text redaction and bounds, owner/dependency preservation, missing,
  corrupt, cyclic, and symlink failure, inspector aggregation, deep JavaScript
  validation, and native Markdown rendering.
- IDE verification rerun: fresh exact-session inspection, bounded modal command
  preview, cancel-without-execution, and visible untracked terminal launch with
  exact argument-array flags and source-linked output analysis.
- IDE live context: atomic authenticated JavaScript payloads, Python protocol
  validation, sensitive and symlink rejection, untrusted diagnostic redaction,
  no source-buffer transfer, and bridge-secret stripping for child processes.
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
- Real CLI JSON and stream-json entrypoints, stdin input formats, normalized
  user-message replay with matching run/session identity and non-user/raw-field
  filtering, resume, compact, permission overrides, `acceptEdits`, non-interactive `dontAsk`
  with trusted pre-approval and default denial, bounded invocation-scoped
  `--agents` definitions inherited by delegated runtimes, invocation-scoped
  `--append-subagent-system-prompt` constraints inherited by direct, nested, and resumed
  delegates, safe structured agent YAML, profile permission modes, scoped command hooks and stdio/HTTP MCP,
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
  blocks, redacted resumable output, pre-execution session-path validation, and
  exact private artifact references when finite output exceeds the inline
  bound.
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
  permissions, environment propagation, hooks, sandbox checks, and a
  Claude-compatible `--safe-mode` diagnostic boundary that suppresses custom
  instructions, agents, skills, commands, plugins, hooks, MCP, LSP, workflows,
  status-line customization, and auto-memory without weakening permissions.
- Invocation settings: Claude-compatible `--settings` accepts a bounded inline
  JSON object or file, while `--setting-sources` selects user, project, and local
  files. One immutable override reaches provider environment, permissions,
  hooks, sandbox, agents, plugins, resume, fork, background, and subagents
  without recording setting contents in session events.
- Invocation plugins: repeatable `--plugin-dir` validates up to 20 local
  non-symlink plugin roots or ZIP archives and loads their skills, commands,
  agents, hooks, MCP, LSP, monitors, executables, and default settings without
  installation. ZIP roots are materialized in a private content-addressed user
  cache after bounded traversal, duplicate, encryption, link, special-file,
  count, depth, and byte checks. The same roots reach interactive catalogs,
  resume, fork, worktree, background, and subagents; explicit same-name plugins
  override installed versions and events disclose only the count.
- Recoverable command output: truncated finite Bash and PowerShell streams are
  retained as private current-session artifacts with exact `read_file`
  references and total byte counts. Invalid references, cross-session paths,
  symbolic links, and unrelated protected runtime files fail closed, while
  artifact write errors preserve the actual command result.

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
